import copy
from typing import Any, Dict, List


READINESS_SCHEMA = "ReadinessDecision.v1"

READINESS_STATUSES = {
    "unknown",
    "ready_for_direct_answer",
    "ready_with_current_turn_facts",
    "ready_with_identity_context",
    "needs_memory_recall",
    "needs_tool_evidence",
    "needs_context_repair",
    "needs_planning",
    "needs_warroom",
    "clean_failure",
}


def _compact_list(values: Any, limit: int = 6) -> List[str]:
    if not isinstance(values, list):
        values = [values] if str(values or "").strip() else []
    compacted = []
    seen = set()
    for raw in values:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        compacted.append(text)
    return compacted[:limit]


def normalize_readiness_decision(decision: Dict[str, Any] | None) -> Dict[str, Any]:
    packet = decision if isinstance(decision, dict) else {}
    status = str(packet.get("status") or "unknown").strip()
    if status not in READINESS_STATUSES:
        status = "unknown"
    return {
        "schema": str(packet.get("schema") or READINESS_SCHEMA),
        "status": status,
        "reason": str(packet.get("reason") or "").strip(),
        "missing_evidence": _compact_list(packet.get("missing_evidence", [])),
        "allowed_next_hop": str(packet.get("allowed_next_hop") or "").strip(),
        "retry_budget": int(packet.get("retry_budget", 0) or 0),
        "user_facing_failure_seed": str(packet.get("user_facing_failure_seed") or "").strip(),
        "source": str(packet.get("source") or "").strip(),
        "legacy_action": str(packet.get("legacy_action") or "").strip(),
    }


def readiness_from_auditor_action(
    action: str,
    *,
    memo: str = "",
    tool_name: str = "",
    tool_args: Dict[str, Any] | None = None,
    retry_budget: int = 0,
) -> Dict[str, Any]:
    normalized_action = str(action or "").strip()
    normalized_tool = str(tool_name or "").strip()
    normalized_args = copy.deepcopy(tool_args or {})
    memo_text = str(memo or "").strip()

    if normalized_action == "phase_3":
        status = "ready_for_direct_answer"
        next_hop = "phase_3"
    elif normalized_action == "call_tool":
        status = "needs_memory_recall" if normalized_tool == "tool_search_field_memos" else "needs_tool_evidence"
        next_hop = "0_supervisor"
    elif normalized_action == "warroom_deliberation":
        status = "needs_warroom"
        next_hop = "warroom_deliberator"
    elif normalized_action in {"plan_with_strategist", "plan_more", "internal_reasoning"}:
        status = "needs_planning"
        next_hop = "-1a_thinker" if normalized_action == "plan_with_strategist" else "phase_2a"
    elif normalized_action in {"phase_119", "answer_not_ready", "clean_failure"}:
        status = "clean_failure"
        next_hop = "phase_119" if normalized_action == "phase_119" else "phase_3"
    else:
        status = "unknown"
        next_hop = ""

    missing = []
    if normalized_action == "call_tool" and normalized_tool:
        missing.append(f"tool_result:{normalized_tool}")
    elif normalized_action in {"answer_not_ready", "clean_failure", "phase_119"}:
        missing.append("direct answer-ready evidence")
    elif normalized_action in {"plan_with_strategist", "plan_more", "internal_reasoning"}:
        missing.append("stable plan or answer boundary")

    return normalize_readiness_decision(
        {
            "status": status,
            "reason": memo_text,
            "missing_evidence": missing,
            "allowed_next_hop": next_hop,
            "retry_budget": retry_budget,
            "user_facing_failure_seed": memo_text if status == "clean_failure" else "",
            "source": "auditor_action_adapter",
            "legacy_action": normalized_action,
            "tool_name": normalized_tool,
            "tool_args": normalized_args,
        }
    )


def readiness_from_delivery_payload(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    packet = payload if isinstance(payload, dict) else {}
    if not packet:
        return normalize_readiness_decision({"source": "delivery_payload_adapter"})

    answer_mode = str(packet.get("answer_mode") or "").strip()
    fallback_action = str(packet.get("fallback_action") or "").strip()
    source_lane = str(packet.get("source_lane") or packet.get("lane") or "").strip()
    ready = bool(packet.get("ready_for_delivery"))
    missing = _compact_list(packet.get("missing_slots", []))
    clean_failure = packet.get("clean_failure_packet", {})
    failure_seed = str(clean_failure.get("message_seed") or "").strip() if isinstance(clean_failure, dict) else ""

    if ready:
        if answer_mode == "current_turn_grounding":
            status = "ready_with_current_turn_facts"
        elif answer_mode == "identity_direct":
            status = "ready_with_identity_context"
        else:
            status = "ready_for_direct_answer"
        next_hop = "phase_3"
    elif fallback_action == "replan_or_search_more" and source_lane == "field_memo_review":
        status = "needs_memory_recall"
        next_hop = "-1a_thinker"
    elif fallback_action in {"re_deliberate"} or answer_mode == "warroom_synthesis":
        status = "needs_warroom"
        next_hop = "warroom_deliberator"
    elif fallback_action in {"ask_for_recent_context"}:
        status = "needs_context_repair"
        next_hop = "phase_3"
    elif fallback_action in {"search_more_or_report_limit"}:
        status = "needs_tool_evidence"
        next_hop = "0_supervisor"
    elif fallback_action == "clean_failure" or clean_failure:
        status = "clean_failure"
        next_hop = "phase_3"
    else:
        status = "needs_planning"
        next_hop = "-1a_thinker"

    return normalize_readiness_decision(
        {
            "status": status,
            "reason": str(packet.get("answer_boundary") or packet.get("contract_status") or "").strip(),
            "missing_evidence": missing,
            "allowed_next_hop": next_hop,
            "retry_budget": 0,
            "user_facing_failure_seed": failure_seed,
            "source": "delivery_payload_adapter",
            "legacy_action": fallback_action,
        }
    )
