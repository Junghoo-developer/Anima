"""Bounded runtime context packets.

These packets contain observable runtime facts. They are prompt material, not
identity material and not routing authority.

V3/V4 role note:
- This module owns -1s cumulative context-packet assembly.
- The public runtime packet remains `RuntimeContext.v1`.
- The live -1s handoff is `ThinkingHandoff.v1`; the old four-slot
  `SThinkingPacket.v1` remains supported as a one-season compatibility input.
"""

from __future__ import annotations

import json
from typing import Any

from .runtime_profile import build_runtime_profile


def _clip_text(value: Any, limit: int = 600) -> str:
    text = str(value or "").strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _clip_mapping(mapping: Any, limit: int = 12, value_limit: int = 240) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        return {}
    packet: dict[str, Any] = {}
    for idx, (key, value) in enumerate(mapping.items()):
        if idx >= limit:
            break
        key_text = _clip_text(key, 100)
        if isinstance(value, dict):
            packet[key_text] = _clip_mapping(value, 8, value_limit)
        elif isinstance(value, list):
            packet[key_text] = [_clip_text(item, value_limit) for item in value[:6]]
        else:
            packet[key_text] = _clip_text(value, value_limit)
    return packet


def _first_string(values: Any) -> str:
    if isinstance(values, list):
        for value in values:
            text = _clip_text(value, 180)
            if text:
                return text
    return _clip_text(values, 180)


def _clip_list(values: Any, *, limit: int = 8, text_limit: int = 180) -> list[str]:
    if isinstance(values, list):
        source = values
    elif values:
        source = [values]
    else:
        source = []
    clipped: list[str] = []
    for value in source:
        text = _clip_text(value, text_limit)
        if text:
            clipped.append(text)
        if len(clipped) >= limit:
            break
    return clipped


def compact_s_thinking_cycle(packet: dict[str, Any] | None, *, cycle: int | None = None) -> dict[str, Any]:
    """Compress one completed -1s packet into the history row.

    The row is deliberately tiny and contains only -1s-owned material. It must
    not include -1a plans, tool arguments, source dumps, or final answer text.
    """
    source = packet if isinstance(packet, dict) else {}
    if not source:
        return {}
    if any(key in source for key in ("goal_state", "next_node", "what_is_missing", "next_node_reason")):
        try:
            cycle_num = int(cycle or 0)
        except (TypeError, ValueError):
            cycle_num = 0
        target = _clip_text(source.get("next_node") or source.get("recipient"), 40)
        if target == "119":
            target = "phase_119"
        row = {
            "cycle": max(cycle_num, 1),
            "domain": _clip_text(source.get("goal_state") or source.get("evidence_state"), 80),
            "next_node": target,
            "main_gap": _first_string(source.get("what_is_missing", [])),
            "brief_thought": _clip_text(source.get("next_node_reason") or source.get("goal_state"), 120),
        }
        if not any(str(row.get(key) or "").strip() for key in ("domain", "next_node", "main_gap", "brief_thought")):
            return {}
        return row

    situation = source.get("situation_thinking", {})
    if not isinstance(situation, dict):
        situation = {}
    loop_summary = source.get("loop_summary", {})
    if not isinstance(loop_summary, dict):
        loop_summary = {}
    routing = source.get("routing_decision", {})
    if not isinstance(routing, dict):
        routing = {}
    try:
        cycle_num = int(cycle or 0)
    except (TypeError, ValueError):
        cycle_num = 0
    row = {
        "cycle": max(cycle_num, 1),
        "domain": _clip_text(situation.get("domain"), 80),
        "next_node": _clip_text(routing.get("next_node"), 40),
        "main_gap": _first_string(loop_summary.get("gaps", [])),
        "brief_thought": _clip_text(situation.get("user_intent"), 120),
    }
    if not any(str(row.get(key) or "").strip() for key in ("domain", "next_node", "main_gap", "brief_thought")):
        return {}
    return row


def _same_compact_cycle(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    keys = ("cycle", "domain", "next_node", "main_gap", "brief_thought")
    return all(str(left.get(key) or "") == str(right.get(key) or "") for key in keys)


def normalize_s_thinking_history(packet: dict[str, Any] | None, *, history_limit: int = 5) -> dict[str, Any]:
    source = packet if isinstance(packet, dict) else {}
    history = source.get("history_compact", [])
    if not isinstance(history, list):
        history = []
    compact_history: list[dict[str, Any]] = []
    for idx, item in enumerate(history):
        if not isinstance(item, dict):
            continue
        try:
            cycle_num = int(item.get("cycle") or idx + 1)
        except (TypeError, ValueError):
            cycle_num = idx + 1
        row = {
            "cycle": max(cycle_num, 1),
            "domain": _clip_text(item.get("domain"), 80),
            "next_node": _clip_text(item.get("next_node"), 40),
            "main_gap": _clip_text(item.get("main_gap"), 180),
            "brief_thought": _clip_text(item.get("brief_thought"), 120),
        }
        if any(str(row.get(key) or "").strip() for key in ("domain", "next_node", "main_gap", "brief_thought")):
            compact_history.append(row)
    if history_limit > 0:
        compact_history = compact_history[-history_limit:]
    current = source.get("current", {})
    if not isinstance(current, dict):
        current = {}
    return {
        "schema": "SThinkingHistory.v1",
        "history_compact": compact_history,
        "current": current,
    }


def _normalize_current_s_thinking_packet(current: dict[str, Any] | None) -> dict[str, Any]:
    source = current if isinstance(current, dict) else {}
    if not source:
        return {}
    if any(key in source for key in ("producer", "recipient", "goal_state", "next_node", "what_we_know")):
        target = _clip_text(source.get("next_node") or source.get("recipient"), 40)
        if target == "119":
            target = "phase_119"
        recipient = _clip_text(source.get("recipient") or target, 40)
        if recipient == "119":
            recipient = "phase_119"
        return {
            "schema": "ThinkingHandoff.v1",
            "producer": _clip_text(source.get("producer"), 40) or "-1s",
            "recipient": recipient or target or "-1a",
            "goal_state": _clip_text(source.get("goal_state"), 220),
            "evidence_state": _clip_text(source.get("evidence_state"), 260),
            "what_we_know": _clip_list(source.get("what_we_know", []), limit=8, text_limit=220),
            "what_is_missing": _clip_list(source.get("what_is_missing", []), limit=8, text_limit=180),
            "next_node": target or recipient or "-1a",
            "next_node_reason": _clip_text(source.get("next_node_reason"), 220),
            "constraints_for_next_node": _clip_list(source.get("constraints_for_next_node", []), limit=6, text_limit=180),
        }
    situation = source.get("situation_thinking", {})
    situation = situation if isinstance(situation, dict) else {}
    loop_summary = source.get("loop_summary", {})
    loop_summary = loop_summary if isinstance(loop_summary, dict) else {}
    next_direction = source.get("next_direction", {})
    next_direction = next_direction if isinstance(next_direction, dict) else {}
    routing = source.get("routing_decision", {})
    routing = routing if isinstance(routing, dict) else {}
    next_node = _clip_text(routing.get("next_node"), 40)
    if next_node == "119":
        next_node = "phase_119"
    goal_parts = [
        _clip_text(situation.get("domain"), 80),
        _clip_text(situation.get("user_intent"), 100),
    ]
    return {
        "schema": "ThinkingHandoff.v1",
        "producer": "-1s",
        "recipient": next_node or "-1a",
        "goal_state": " | ".join(part for part in goal_parts if part),
        "evidence_state": _clip_text(loop_summary.get("current_evidence_state"), 260),
        "what_we_know": [],
        "what_is_missing": _clip_list(loop_summary.get("gaps", []), limit=8, text_limit=180),
        "next_node": next_node or "-1a",
        "next_node_reason": _clip_text(routing.get("reason"), 220),
        "constraints_for_next_node": _clip_list(next_direction.get("avoid", []), limit=6, text_limit=180),
    }


def append_cycle_to_history(
    history: dict[str, Any] | None,
    previous_packet: dict[str, Any] | None,
    *,
    cycle: int | None = None,
    history_limit: int = 5,
) -> list[dict[str, Any]]:
    normalized = normalize_s_thinking_history(history, history_limit=history_limit)
    rows = list(normalized.get("history_compact", []))
    row = compact_s_thinking_cycle(previous_packet, cycle=cycle)
    if row:
        if not rows or not _same_compact_cycle(rows[-1], row):
            rows.append(row)
    if history_limit > 0:
        rows = rows[-history_limit:]
    return rows


def build_cumulative_s_thinking_packet(
    *,
    current: dict[str, Any] | None,
    previous_history: dict[str, Any] | None = None,
    previous_packet: dict[str, Any] | None = None,
    cycle: int | None = None,
    history_limit: int = 5,
) -> dict[str, Any]:
    """Build `history_compact + current` for -1s prompt and state storage."""
    history = normalize_s_thinking_history(previous_history, history_limit=history_limit)
    rows = append_cycle_to_history(
        history,
        previous_packet,
        cycle=cycle,
        history_limit=history_limit,
    ) if previous_packet else list(history.get("history_compact", []))
    return {
        "schema": "SThinkingHistory.v1",
        "history_compact": rows[-history_limit:] if history_limit > 0 else rows,
        "current": _normalize_current_s_thinking_packet(current),
    }


def s_thinking_history_for_prompt(packet: dict[str, Any] | None) -> str:
    compact = normalize_s_thinking_history(packet)
    try:
        return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        return str(compact)


def build_runtime_context_packet(state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return bounded runtime facts for prompts.

    This packet intentionally excludes raw messages, search results, tool
    caches, delivery packets, and self-identity claims. It is suitable as a
    future common prompt surface for nodes that need observable runtime context.
    """
    state = state if isinstance(state, dict) else {}
    return {
        "schema": "RuntimeContext.v1",
        "runtime_profile": build_runtime_profile(state),
        "short_context": {
            "recent_context": _clip_text(state.get("recent_context"), 900),
            "user_state": _clip_text(state.get("user_state"), 360),
            "user_char": _clip_text(state.get("user_char"), 360),
            "songryeon_thoughts": _clip_text(state.get("songryeon_thoughts"), 420),
            "tactical_briefing": _clip_text(state.get("tactical_briefing"), 420),
        },
        "activity_trace": {
            "evidence_ledger": _clip_mapping(state.get("evidence_ledger", {}), 8, 220),
            "execution_status": _clip_text(state.get("execution_status"), 80),
            "delivery_status": _clip_text(state.get("delivery_status"), 80),
            "loop_count": state.get("loop_count", 0),
        },
    }


def runtime_context_packet_for_prompt(state: dict[str, Any] | None = None) -> str:
    packet = build_runtime_context_packet(state)
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


__all__ = [
    "append_cycle_to_history",
    "build_cumulative_s_thinking_packet",
    "build_runtime_context_packet",
    "compact_s_thinking_cycle",
    "normalize_s_thinking_history",
    "runtime_context_packet_for_prompt",
    "s_thinking_history_for_prompt",
]
