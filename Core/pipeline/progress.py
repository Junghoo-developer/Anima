"""Progress and observe-only arbitration helpers for the field loop.

These helpers track repeated runtime states and preserve audit telemetry. They
must not route the graph, rewrite decisions, or synthesize answer text.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from .plans import (
    empty_operation_contract,
    normalize_action_plan,
    normalize_operation_contract,
    normalize_operation_plan,
)
from .runtime_context import normalize_execution_trace
from ..warroom.state import _normalize_war_room_operating_contract


def normalize_progress_markers(markers: dict | None) -> dict[str, Any]:
    if not isinstance(markers, dict):
        markers = {}
    return {
        "last_combined_signature": str(markers.get("last_combined_signature") or "").strip(),
        "last_operation_signature": str(markers.get("last_operation_signature") or "").strip(),
        "last_refresh_analysis_signature": str(markers.get("last_refresh_analysis_signature") or "").strip(),
        "last_stage": str(markers.get("last_stage") or "").strip(),
        "stalled_repeats": max(int(markers.get("stalled_repeats", 0) or 0), 0),
        "same_operation_repeats": max(int(markers.get("same_operation_repeats", 0) or 0), 0),
    }


def signature_digest(payload: Any) -> str:
    try:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        raw = str(payload)
    return hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()


def raw_progress_signature(raw_read_report: dict) -> str:
    if not isinstance(raw_read_report, dict) or not raw_read_report:
        return ""
    items = []
    for item in raw_read_report.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "source_id": str(item.get("source_id") or "").strip(),
                "source_type": str(item.get("source_type") or "").strip(),
                "observed_fact": str(item.get("observed_fact") or item.get("extracted_fact") or "").strip(),
                "excerpt": str(item.get("excerpt") or "").strip()[:160],
            }
        )
    payload = {
        "read_mode": str(raw_read_report.get("read_mode") or "").strip(),
        "reviewed_all_input": bool(raw_read_report.get("reviewed_all_input")),
        "source_summary": str(raw_read_report.get("source_summary") or "").strip(),
        "coverage_notes": str(raw_read_report.get("coverage_notes") or "").strip(),
        "items": items,
    }
    return signature_digest(payload)


def analysis_progress_signature(analysis_data: dict) -> str:
    if not isinstance(analysis_data, dict) or not analysis_data:
        return ""
    evidences = []
    for item in analysis_data.get("evidences", []) or []:
        if not isinstance(item, dict):
            continue
        evidences.append(
            {
                "source_id": str(item.get("source_id") or "").strip(),
                "source_type": str(item.get("source_type") or "").strip(),
                "fact": str(item.get("extracted_fact") or "").strip(),
            }
        )
    payload = {
        "status": str(analysis_data.get("investigation_status") or "").strip().upper(),
        "situational_brief": str(analysis_data.get("situational_brief") or "").strip(),
        "analytical_thought": str(analysis_data.get("analytical_thought") or "").strip(),
        "evidences": evidences,
    }
    return signature_digest(payload)


def strategy_progress_signature(strategist_output: dict) -> str:
    if not isinstance(strategist_output, dict) or not strategist_output:
        return ""
    action_plan = normalize_action_plan(strategist_output.get("action_plan", {}))
    response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    payload = {
        "case_theory": str(strategist_output.get("case_theory") or "").strip(),
        "operation_plan": normalize_operation_plan(strategist_output.get("operation_plan", {})),
        "action_plan": {
            "current_step_goal": str(action_plan.get("current_step_goal") or "").strip(),
            "required_tool": str(action_plan.get("required_tool") or "").strip(),
            "next_steps_forecast": [str(step).strip() for step in action_plan.get("next_steps_forecast", []) if str(step).strip()],
            "operation_contract": normalize_operation_contract(action_plan.get("operation_contract", {})),
        },
        "response_strategy": {
            "reply_mode": str(response_strategy.get("reply_mode") or "").strip(),
            "answer_goal": str(response_strategy.get("answer_goal") or "").strip(),
            "direct_answer_seed": str(response_strategy.get("direct_answer_seed") or "").strip(),
        },
        "war_room_contract": _normalize_war_room_operating_contract(strategist_output.get("war_room_contract", {})),
    }
    return signature_digest(payload)


def operation_contract_from_action_plan(action_plan: dict | None) -> dict[str, Any]:
    normalized_action_plan = normalize_action_plan(action_plan if isinstance(action_plan, dict) else {})
    return normalize_operation_contract(normalized_action_plan.get("operation_contract", {}))


def operation_contract_signature(operation_contract: dict | None) -> str:
    normalized = normalize_operation_contract(operation_contract if isinstance(operation_contract, dict) else {})
    if normalized == empty_operation_contract():
        return ""
    return signature_digest(normalized)


def execution_trace_signature(execution_trace: dict | None) -> str:
    normalized = normalize_execution_trace(execution_trace if isinstance(execution_trace, dict) else {})
    if not any(normalized.values()):
        return ""
    return signature_digest(normalized)


def with_execution_trace_contract(execution_trace: dict | None, operation_contract: dict | None) -> dict[str, Any]:
    normalized_trace = normalize_execution_trace(execution_trace if isinstance(execution_trace, dict) else {})
    normalized_contract = normalize_operation_contract(operation_contract if isinstance(operation_contract, dict) else {})
    for key in ("operation_kind", "target_scope", "query_variant", "novelty_requirement"):
        if normalized_contract.get(key):
            normalized_trace[key] = normalized_contract[key]
    return normalized_trace


def same_tool_call_as_execution(decision: dict | None, execution_trace: dict | None) -> bool:
    if not isinstance(decision, dict):
        return False
    if str(decision.get("action") or "").strip() != "call_tool":
        return False
    normalized_trace = normalize_execution_trace(execution_trace if isinstance(execution_trace, dict) else {})
    tool_name = str(decision.get("tool_name") or "").strip()
    if not tool_name or tool_name != normalized_trace.get("executed_tool"):
        return False
    tool_args = decision.get("tool_args", {}) if isinstance(decision.get("tool_args"), dict) else {}
    return signature_digest(tool_args) == normalized_trace.get("tool_args_signature")


def advance_progress_markers(
    markers: dict | None,
    state: dict,
    analysis_data: dict,
    strategist_output: dict,
    stage: str,
) -> dict[str, Any]:
    normalized = normalize_progress_markers(markers)
    raw_sig = raw_progress_signature(state.get("raw_read_report", {}))
    analysis_sig = analysis_progress_signature(analysis_data)
    strategy_sig = strategy_progress_signature(strategist_output)
    operation_signature = signature_digest({
        "operation_contract": operation_contract_from_action_plan(
            strategist_output.get("action_plan", {}) if isinstance(strategist_output, dict) else {}
        ),
        "execution_trace": normalize_execution_trace(state.get("execution_trace", {})),
    })
    combined_signature = signature_digest(
        {
            "stage": stage,
            "raw": raw_sig,
            "analysis": analysis_sig,
            "strategy": strategy_sig,
            "used_sources": sorted(str(item).strip() for item in state.get("used_sources", []) if str(item).strip()),
            "execution_status": str(state.get("execution_status") or "").strip().lower(),
        }
    )

    stalled_repeats = 0
    if combined_signature and combined_signature == normalized.get("last_combined_signature") and stage == normalized.get("last_stage"):
        stalled_repeats = int(normalized.get("stalled_repeats", 0) or 0) + 1

    same_operation_repeats = 0
    if operation_signature and operation_signature == normalized.get("last_operation_signature") and stage == normalized.get("last_stage"):
        same_operation_repeats = int(normalized.get("same_operation_repeats", 0) or 0) + 1

    return {
        "last_combined_signature": combined_signature,
        "last_operation_signature": operation_signature,
        "last_refresh_analysis_signature": normalized.get("last_refresh_analysis_signature", ""),
        "last_stage": stage,
        "stalled_repeats": stalled_repeats,
        "same_operation_repeats": same_operation_repeats,
    }


def analysis_refresh_signature(analysis_data: dict) -> str:
    return analysis_progress_signature(analysis_data)


def analysis_refresh_allowed(progress_markers: dict | None, analysis_data: dict) -> bool:
    normalized = normalize_progress_markers(progress_markers)
    analysis_signature = analysis_refresh_signature(analysis_data)
    if not analysis_signature:
        return False
    return analysis_signature != str(normalized.get("last_refresh_analysis_signature") or "").strip()


def mark_analysis_refresh(progress_markers: dict | None, analysis_data: dict) -> dict[str, Any]:
    normalized = normalize_progress_markers(progress_markers)
    analysis_signature = analysis_refresh_signature(analysis_data)
    if analysis_signature:
        normalized["last_refresh_analysis_signature"] = analysis_signature
    return normalized


def apply_progress_contract(
    decision: dict | None,
    *,
    stalled_repeats: int,
    same_operation_repeats: int,
    user_input: str,
    analysis_data: dict,
    strategist_output: dict,
    working_memory: dict,
    execution_trace: dict | None = None,
) -> dict | None:
    del stalled_repeats, same_operation_repeats, user_input, analysis_data, strategist_output, working_memory, execution_trace
    return decision


def merge_strategy_audits(*audits: dict) -> dict[str, Any]:
    packets = []
    for audit in audits:
        if isinstance(audit, dict) and audit:
            packets.append(copy.deepcopy(audit))
    if not packets:
        return {}
    if len(packets) == 1:
        return packets[0]
    return {
        "audit_kind": "merged_strategy_audit",
        "audits": packets,
    }


def _compact_user_facing_summary(text: str, limit: int = 120) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 3, 0)].rstrip() + "..."


def build_strategy_arbitration_audit(
    state: dict,
    strategist_output: dict,
    analysis_data: dict,
) -> dict[str, Any]:
    del strategist_output, analysis_data
    user_input = str((state or {}).get("user_input") or "").strip() if isinstance(state, dict) else ""
    return {
        "audit_kind": "critic_strategist_arbitration",
        "mode": "thin_controller_observe_only",
        "user_goal": _compact_user_facing_summary(user_input, 120),
        "has_blocking_conflict": False,
        "recommended_action": "none",
        "blocking_topics": [],
        "audit_memo": "Thin-controller mode records arbitration context but does not override the auditor decision.",
        "pairs": [],
    }


def decision_from_strategy_arbitration_audit(
    audit: dict,
    *,
    loop_count: int,
    reasoning_budget: int,
) -> None:
    del audit, loop_count, reasoning_budget
    return None


__all__ = [
    "advance_progress_markers",
    "analysis_progress_signature",
    "analysis_refresh_allowed",
    "analysis_refresh_signature",
    "apply_progress_contract",
    "build_strategy_arbitration_audit",
    "decision_from_strategy_arbitration_audit",
    "execution_trace_signature",
    "mark_analysis_refresh",
    "merge_strategy_audits",
    "normalize_progress_markers",
    "operation_contract_from_action_plan",
    "operation_contract_signature",
    "raw_progress_signature",
    "same_tool_call_as_execution",
    "signature_digest",
    "strategy_progress_signature",
    "with_execution_trace_contract",
]
