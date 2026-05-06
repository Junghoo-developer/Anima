"""Runtime activity context for the ANIMA field-loop pipeline.

This module tracks what actually happened in the runtime: executed tools,
source ids, and tool carryover state. It should not decide user meaning or
compose answer text.
"""

from __future__ import annotations

import json
import re
from typing import Any


def _dedupe_keep_order(items: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def normalize_execution_trace(trace: dict | None) -> dict[str, Any]:
    if not isinstance(trace, dict):
        trace = {}
    source_ids = trace.get("source_ids", [])
    if not isinstance(source_ids, list):
        source_ids = []
    return {
        "operation_kind": str(trace.get("operation_kind") or "").strip(),
        "target_scope": str(trace.get("target_scope") or "").strip(),
        "query_variant": str(trace.get("query_variant") or "").strip(),
        "novelty_requirement": str(trace.get("novelty_requirement") or "").strip(),
        "executed_tool": str(trace.get("executed_tool") or "").strip(),
        "tool_args_signature": str(trace.get("tool_args_signature") or "").strip(),
        "read_mode": str(trace.get("read_mode") or "").strip(),
        "read_focus": str(trace.get("read_focus") or "").strip(),
        "analysis_focus": str(trace.get("analysis_focus") or "").strip(),
        "source_ids": _dedupe_keep_order([str(item).strip() for item in source_ids if str(item).strip()])[:8],
        "evidence_count": max(int(trace.get("evidence_count", 0) or 0), 0),
    }


def empty_tool_carryover_state() -> dict[str, Any]:
    return {
        "version": "tool_carryover_v1",
        "last_tool": "",
        "last_query": "",
        "last_target_id": "",
        "last_direction": "",
        "last_limit": 0,
        "origin_source_id": "",
        "origin_query": "",
        "axis": "time",
        "source_ids": [],
        "candidate_ids": [],
        "last_result_summary": "",
        "available_followups": [],
        "scroll_history": [],
        "recommended_next_scroll": {},
    }


def normalize_tool_carryover_state(carryover: dict | None) -> dict[str, Any]:
    base = empty_tool_carryover_state()
    if not isinstance(carryover, dict):
        return base

    for key in (
        "version",
        "last_tool",
        "last_query",
        "last_target_id",
        "last_direction",
        "origin_source_id",
        "origin_query",
        "axis",
        "last_result_summary",
    ):
        base[key] = str(carryover.get(key) or base.get(key) or "").strip()

    try:
        base["last_limit"] = max(int(carryover.get("last_limit", 0) or 0), 0)
    except (TypeError, ValueError):
        base["last_limit"] = 0

    for key in ("source_ids", "candidate_ids", "available_followups"):
        values = carryover.get(key, [])
        if not isinstance(values, list):
            values = [values] if values else []
        base[key] = _dedupe_keep_order([str(item).strip() for item in values if str(item).strip()])[:12]

    history = carryover.get("scroll_history", [])
    if not isinstance(history, list):
        history = []
    normalized_history = []
    for item in history[-8:]:
        if not isinstance(item, dict):
            continue
        raw_source_ids = item.get("source_ids", [])
        normalized_history.append({
            "target_id": str(item.get("target_id") or "").strip(),
            "direction": str(item.get("direction") or "").strip(),
            "limit": int(item.get("limit", 0) or 0) if str(item.get("limit", "")).strip().isdigit() else 0,
            "source_ids": (
                _dedupe_keep_order([str(src).strip() for src in raw_source_ids if str(src).strip()])[:8]
                if isinstance(raw_source_ids, list)
                else []
            ),
        })
    base["scroll_history"] = normalized_history

    recommended = carryover.get("recommended_next_scroll", {})
    if isinstance(recommended, dict):
        base["recommended_next_scroll"] = {
            "target_id": str(recommended.get("target_id") or "").strip(),
            "direction": str(recommended.get("direction") or "").strip(),
            "limit": int(recommended.get("limit", 0) or 0) if str(recommended.get("limit", "")).strip().isdigit() else 0,
            "reason": str(recommended.get("reason") or "").strip(),
        }
    return base


def source_id_looks_scrollable(source_id: str) -> bool:
    value = str(source_id or "").strip()
    if not value or value == "current_user_turn":
        return False
    lowered = value.lower()
    if any(token in lowered for token in ["pastrecord", "diary", "chat", "episode", "#slide_"]):
        return True
    return bool(re.search(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}", value))


def source_ids_from_working_memory(working_memory: dict | None) -> list[str]:
    working_memory = working_memory if isinstance(working_memory, dict) else {}
    evidence_state = working_memory.get("evidence_state", {})
    if not isinstance(evidence_state, dict):
        evidence_state = {}
    last_turn = working_memory.get("last_turn", {})
    if not isinstance(last_turn, dict):
        last_turn = {}
    tool_carryover = normalize_tool_carryover_state(working_memory.get("tool_carryover", {}))
    return _dedupe_keep_order(
        list(tool_carryover.get("source_ids", []))
        + list(evidence_state.get("active_source_ids", []))
        + list(last_turn.get("used_sources", []))
    )[:12]


def tool_carryover_from_working_memory(working_memory: dict | None) -> dict[str, Any]:
    working_memory = working_memory if isinstance(working_memory, dict) else {}
    carryover = normalize_tool_carryover_state(working_memory.get("tool_carryover", {}))
    wm_source_ids = source_ids_from_working_memory(working_memory)
    carryover["source_ids"] = _dedupe_keep_order(list(carryover.get("source_ids", [])) + wm_source_ids)[:12]
    if not carryover.get("origin_source_id"):
        carryover["origin_source_id"] = next((src for src in carryover["source_ids"] if source_id_looks_scrollable(src)), "")
    return carryover


def tool_carryover_from_state(state: dict | None) -> dict[str, Any]:
    state = state if isinstance(state, dict) else {}
    carryover = normalize_tool_carryover_state(state.get("tool_carryover", {}))
    working_carryover = tool_carryover_from_working_memory(state.get("working_memory", {}))
    execution_trace = normalize_execution_trace(state.get("execution_trace", {}))
    used_sources = state.get("used_sources", [])
    if not isinstance(used_sources, list):
        used_sources = []
    merged_sources = _dedupe_keep_order(
        list(carryover.get("source_ids", []))
        + list(working_carryover.get("source_ids", []))
        + list(execution_trace.get("source_ids", []))
        + [str(src).strip() for src in used_sources if str(src).strip()]
    )[:12]
    carryover["source_ids"] = merged_sources
    carryover["candidate_ids"] = _dedupe_keep_order(list(carryover.get("candidate_ids", [])) + merged_sources)[:12]
    if not carryover.get("origin_source_id"):
        carryover["origin_source_id"] = (
            working_carryover.get("origin_source_id")
            or next((src for src in merged_sources if source_id_looks_scrollable(src)), "")
        )
    if not carryover.get("last_target_id"):
        carryover["last_target_id"] = carryover.get("origin_source_id", "")
    return carryover


def extract_source_ids_from_tool_result(result_str: str, exact_dates: list | None = None) -> list[str]:
    explicit = [str(item).strip() for item in (exact_dates or []) if str(item).strip()]
    text = str(result_str or "")
    date_like = re.findall(r"\b\d{4}[-./]\d{1,2}[-./]\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?\b", text)
    graph_ids = re.findall(r"\b(?:PastRecord|Diary|Chat|Dream|TurnProcess)[A-Za-z0-9_:#./-]{0,80}\b", text)
    return _dedupe_keep_order(explicit + date_like + graph_ids)[:12]


def tool_query_from_args(tool_name: str, tool_args: dict | None) -> str:
    args = tool_args if isinstance(tool_args, dict) else {}
    for key in ("keyword", "query", "target_date", "target_id", "artifact_hint", "keyword_z", "dummy_keyword"):
        value = args.get(key)
        if value:
            return str(value).strip()
    return str(tool_name or "").strip()


def stable_action_signature(tool_name: str, tool_args: dict) -> str:
    try:
        serialized_args = json.dumps(tool_args, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        serialized_args = str(tool_args)
    return f"{tool_name}:{serialized_args}"


def update_tool_carryover_after_tool(
    state: dict | None,
    current_carryover: dict | None,
    tool_name: str,
    tool_args: dict | None,
    result_str: str,
    exact_dates: list | None = None,
) -> dict[str, Any]:
    state_carryover = tool_carryover_from_state(state or {})
    carryover = normalize_tool_carryover_state(current_carryover)
    for key in (
        "last_tool",
        "last_query",
        "last_target_id",
        "last_direction",
        "origin_source_id",
        "origin_query",
        "axis",
        "last_result_summary",
    ):
        if not carryover.get(key):
            carryover[key] = state_carryover.get(key, "")
    if not carryover.get("last_limit"):
        carryover["last_limit"] = state_carryover.get("last_limit", 0)
    carryover["source_ids"] = _dedupe_keep_order(
        list(carryover.get("source_ids", [])) + list(state_carryover.get("source_ids", []))
    )[:12]
    carryover["candidate_ids"] = _dedupe_keep_order(
        list(carryover.get("candidate_ids", [])) + list(state_carryover.get("candidate_ids", []))
    )[:12]
    carryover["available_followups"] = _dedupe_keep_order(
        list(carryover.get("available_followups", [])) + list(state_carryover.get("available_followups", []))
    )[:8]
    args = tool_args if isinstance(tool_args, dict) else {}
    source_ids = extract_source_ids_from_tool_result(result_str, exact_dates)
    query = tool_query_from_args(tool_name, args)
    target_id = str(args.get("target_id") or "").strip()
    direction = str(args.get("direction") or "").strip()
    try:
        limit = max(int(args.get("limit", 0) or 0), 0)
    except (TypeError, ValueError):
        limit = 0

    carryover["last_tool"] = str(tool_name or "").strip()
    carryover["last_query"] = query
    carryover["last_target_id"] = target_id or (source_ids[0] if source_ids else carryover.get("last_target_id", ""))
    carryover["last_direction"] = direction
    carryover["last_limit"] = limit
    carryover["source_ids"] = _dedupe_keep_order(source_ids + list(carryover.get("source_ids", [])))[:12]
    carryover["candidate_ids"] = _dedupe_keep_order(source_ids + list(carryover.get("candidate_ids", [])))[:12]
    carryover["last_result_summary"] = str(result_str or "").strip().replace("\n", " ")[:360]

    if tool_name in {"tool_search_memory", "tool_search_field_memos"}:
        if not carryover.get("origin_source_id"):
            carryover["origin_source_id"] = next((src for src in source_ids if source_id_looks_scrollable(src)), "")
        if not carryover.get("origin_query"):
            carryover["origin_query"] = query
    elif tool_name == "tool_scroll_chat_log":
        if not carryover.get("origin_source_id"):
            carryover["origin_source_id"] = target_id or next((src for src in source_ids if source_id_looks_scrollable(src)), "")
        history = carryover.get("scroll_history", [])
        if not isinstance(history, list):
            history = []
        history.append({
            "target_id": target_id or carryover.get("origin_source_id", ""),
            "direction": direction or "both",
            "limit": limit or 15,
            "source_ids": source_ids,
        })
        carryover["scroll_history"] = history[-8:]

    anchor = carryover.get("origin_source_id") or carryover.get("last_target_id") or (
        carryover.get("source_ids", [""])[0] if carryover.get("source_ids") else ""
    )
    if anchor:
        carryover["recommended_next_scroll"] = {
            "target_id": anchor,
            "direction": "both",
            "limit": 20,
            "reason": "Use the anchored source id as the time-axis origin, then inspect nearby chat/log context.",
        }
        carryover["available_followups"] = _dedupe_keep_order(
            list(carryover.get("available_followups", []))
            + ["scroll_around_origin", "scroll_past_from_origin", "scroll_future_from_origin", "deliver_findings"]
        )[:8]
    return normalize_tool_carryover_state(carryover)


def tool_carryover_anchor_id(
    state_or_working_memory: dict | None,
    *,
    tool_carryover_from_state_fn=tool_carryover_from_state,
    tool_carryover_from_working_memory_fn=tool_carryover_from_working_memory,
) -> str:
    data = state_or_working_memory if isinstance(state_or_working_memory, dict) else {}
    if "working_memory" in data or "execution_trace" in data or "used_sources" in data:
        carryover = tool_carryover_from_state_fn(data)
    else:
        carryover = tool_carryover_from_working_memory_fn(data)
    candidates = [
        carryover.get("origin_source_id", ""),
        carryover.get("last_target_id", ""),
        *(carryover.get("source_ids", []) if isinstance(carryover.get("source_ids"), list) else []),
        *(carryover.get("candidate_ids", []) if isinstance(carryover.get("candidate_ids"), list) else []),
    ]
    return next((str(item).strip() for item in candidates if source_id_looks_scrollable(str(item).strip())), "")


__all__ = [
    "empty_tool_carryover_state",
    "extract_source_ids_from_tool_result",
    "normalize_execution_trace",
    "normalize_tool_carryover_state",
    "source_id_looks_scrollable",
    "source_ids_from_working_memory",
    "stable_action_signature",
    "tool_carryover_anchor_id",
    "tool_carryover_from_state",
    "tool_carryover_from_working_memory",
    "tool_query_from_args",
    "update_tool_carryover_after_tool",
]
