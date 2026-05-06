"""Phase -1s thin start gate for the ANIMA field loop.

The start gate builds the initial thin contract for the current turn. It should
not choose concrete tools, write search queries, or compose the final answer.
"""

from __future__ import annotations

from typing import Any, Callable

from ..runtime.context_packet import build_cumulative_s_thinking_packet


def _string_list(values: Any, *, limit: int = 6) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values[: max(limit, 0)]:
        text = str(value or "").strip()
        if text:
            result.append(text)
    return result


def _thinking_domain(turn_contract: dict[str, Any], answer_mode_policy: dict[str, Any]) -> str:
    """Map existing LLM/policy contracts into the V3 broad domain slot.

    This deliberately avoids raw user-text matching. It only condenses fields
    already produced by the start-gate contract/policy layer.
    """
    answer_mode = str(
        turn_contract.get("answer_mode_preference")
        or answer_mode_policy.get("preferred_answer_mode")
        or ""
    ).strip()
    user_intent = str(turn_contract.get("user_intent") or answer_mode_policy.get("question_class") or "").strip()
    if answer_mode in {"grounded_recall", "memory_recall", "grounded_answer"}:
        return "memory_recall"
    if answer_mode == "public_parametric_knowledge":
        return "public_parametric"
    if user_intent == "correction_or_feedback":
        return "feedback"
    if user_intent == "capability_boundary_question":
        return "self_kernel"
    if user_intent == "task_or_tool_request":
        return "artifact_hint"
    if user_intent in {"direct_social", "providing_current_memory"}:
        return "continuation"
    return "ambiguous"


def _build_s_thinking_packet(
    *,
    start_gate_contract: dict[str, Any],
    start_gate_review: dict[str, Any],
    start_gate_switches: dict[str, Any],
    reasoning_plan: dict[str, Any],
    next_node: str,
    route_reason: str,
) -> dict[str, Any]:
    turn_contract = start_gate_contract.get("turn_contract", {})
    if not isinstance(turn_contract, dict):
        turn_contract = {}
    answer_mode_policy = start_gate_contract.get("answer_mode_policy", {})
    if not isinstance(answer_mode_policy, dict):
        answer_mode_policy = {}

    current_turn_facts = _string_list(start_gate_contract.get("current_turn_facts", []), limit=6)
    attempted = ["start_gate_contract"]
    if start_gate_review:
        attempted.append("fast_gate_review")
    gaps: list[str] = []
    if bool(start_gate_contract.get("requires_grounding")):
        gaps.append("stored or external evidence has not been read yet")
    if bool(start_gate_contract.get("needs_planning")):
        gaps.append("a planner must choose the next action")
    if not gaps and not current_turn_facts:
        gaps.append("no explicit current-turn facts were extracted")

    key_facts_needed = _string_list(
        start_gate_switches.get("key_facts_needed")
        or start_gate_switches.get("missing_facts")
        or [],
        limit=6,
    )
    if not key_facts_needed and bool(start_gate_contract.get("requires_grounding")):
        key_facts_needed = ["direct evidence required by the start-gate contract"]

    suggested_focus = (
        "prepare direct delivery from the approved current contract"
        if next_node == "phase_3"
        else "plan the next action from the normalized goal and evidence boundary"
    )
    avoid = [
        "do not write tool names or queries in -1s",
        "do not copy raw user wording as the goal",
        "do not write final answer text in -1s",
    ]

    return {
        "schema": "SThinkingPacket.v1",
        "situation_thinking": {
            "user_intent": str(start_gate_contract.get("user_intent") or turn_contract.get("user_intent") or "").strip(),
            "domain": _thinking_domain(turn_contract, answer_mode_policy),
            "key_facts_needed": key_facts_needed,
        },
        "loop_summary": {
            "attempted_so_far": attempted,
            "current_evidence_state": (
                f"current_turn_facts={len(current_turn_facts)}; "
                f"requires_grounding={bool(start_gate_contract.get('requires_grounding'))}; "
                f"reasoning_budget={reasoning_plan.get('reasoning_budget', '')}"
            ),
            "gaps": gaps,
        },
        "next_direction": {
            "suggested_focus": suggested_focus,
            "avoid": avoid,
        },
        "routing_decision": {
            "next_node": next_node,
            "reason": str(route_reason or "").strip(),
        },
    }


def _history_cycle_from_state(state: dict[str, Any]) -> int:
    history = state.get("s_thinking_history", {})
    rows = history.get("history_compact", []) if isinstance(history, dict) else []
    if not isinstance(rows, list):
        rows = []
    try:
        loop_count = int(state.get("loop_count", 0) or 0)
    except (TypeError, ValueError):
        loop_count = 0
    return max(loop_count, len(rows) + 1, 1)


def _analysis_report_allows_delivery(analysis_report: Any) -> bool:
    analysis = analysis_report if isinstance(analysis_report, dict) else {}
    if not analysis:
        return False
    status = str(analysis.get("investigation_status") or "").strip().upper()
    contract_status = str(analysis.get("contract_status") or "").strip().lower()
    if bool(analysis.get("can_answer_user_goal")):
        return True
    if contract_status in {"satisfied", "completed", "complete"}:
        return True
    if status == "COMPLETED":
        missing = analysis.get("missing_slots", []) or analysis.get("unfilled_slots", [])
        if not isinstance(missing, list):
            missing = [missing] if str(missing or "").strip() else []
        return not any(str(item or "").strip() for item in missing)
    return False


def _start_gate_budget_exhausted(state: dict[str, Any], reasoning_budget: int) -> bool:
    try:
        loop_count = int(state.get("loop_count", 0) or 0)
    except (TypeError, ValueError):
        loop_count = 0
    return loop_count >= max(int(reasoning_budget or 1), 1) + 2


def run_phase_minus_1s_start_gate(
    state: dict[str, Any],
    *,
    plan_reasoning_budget: Callable[[str, str, dict[str, Any]], dict[str, Any]],
    resolve_reasoning_budget: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    fast_start_gate_assessment: Callable[[str, str, dict[str, Any], dict[str, Any]], dict[str, Any]],
    llm_start_gate_turn_contract: Callable[..., dict[str, Any]],
    build_start_gate_switches: Callable[..., dict[str, Any]],
    make_auditor_decision: Callable[..., dict[str, Any]],
    extract_current_turn_grounding_facts: Callable[..., list[Any]],
    response_strategy_from_answer_mode_policy: Callable[[str, dict[str, Any], list[Any]], dict[str, Any]],
    attach_ledger_event: Callable[..., dict[str, Any]],
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Build the thin start-gate contract and route to phase 3 or -1a."""
    print_fn("[Phase -1s-start] Building thin start-gate contract...")

    user_input = str(state.get("user_input") or "")
    recent_context = str(state.get("recent_context") or "")
    working_memory = state.get("working_memory", {})
    if not isinstance(working_memory, dict):
        working_memory = {}
    incoming_s_thinking_history = build_cumulative_s_thinking_packet(
        current={},
        previous_history=state.get("s_thinking_history", {}),
        previous_packet=state.get("s_thinking_packet", {}),
        cycle=_history_cycle_from_state(state),
    )

    reasoning_plan = state.get("reasoning_plan", {})
    if not isinstance(reasoning_plan, dict) or not reasoning_plan:
        reasoning_plan = plan_reasoning_budget(user_input, recent_context, working_memory)
    reasoning_budget = resolve_reasoning_budget(state, reasoning_plan)

    start_gate_review = fast_start_gate_assessment(user_input, recent_context, working_memory, reasoning_plan)
    start_gate_turn_contract = llm_start_gate_turn_contract(
        user_input,
        recent_context,
        working_memory,
        reasoning_plan,
        incoming_s_thinking_history,
    )
    start_gate_switches = build_start_gate_switches(
        user_input,
        recent_context,
        working_memory,
        start_gate_review,
        reasoning_plan,
        start_gate_turn_contract,
    )
    start_gate_contract = {
        "schema": "ThinStartGateContract.v1",
        "normalized_goal": str(start_gate_switches.get("normalized_goal") or "").strip(),
        "turn_contract": start_gate_switches.get("start_gate_turn_contract", {}),
        "user_intent": str((start_gate_switches.get("start_gate_turn_contract", {}) or {}).get("user_intent") or "").strip(),
        "current_turn_facts": list(start_gate_switches.get("current_turn_facts", []) or []),
        "answer_mode_policy": start_gate_switches.get("answer_mode_policy", {}),
        "requires_grounding": bool(start_gate_switches.get("requires_grounding")),
        "direct_delivery_allowed": bool(start_gate_switches.get("direct_delivery_allowed")),
        "needs_planning": bool(start_gate_switches.get("needs_planning")),
    }
    analysis_delivery_allowed = _analysis_report_allows_delivery(state.get("analysis_report", {}))
    budget_exhausted = _start_gate_budget_exhausted(state, reasoning_budget)

    if budget_exhausted and not start_gate_contract["direct_delivery_allowed"] and not analysis_delivery_allowed:
        memo = "The reasoning budget is exhausted, so -1s sends the turn to phase_119 with preserved runtime context."
        s_thinking_packet = _build_s_thinking_packet(
            start_gate_contract=start_gate_contract,
            start_gate_review=start_gate_review,
            start_gate_switches=start_gate_switches,
            reasoning_plan=reasoning_plan,
            next_node="119",
            route_reason=memo,
        )
        s_thinking_history = build_cumulative_s_thinking_packet(
            current=s_thinking_packet,
            previous_history=incoming_s_thinking_history,
        )
        decision = make_auditor_decision("phase_119", memo=memo)
        return attach_ledger_event({
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "readiness_decision": decision.get("readiness_decision", {}),
            "self_correction_memo": memo,
            "start_gate_review": start_gate_review,
            "start_gate_switches": start_gate_switches,
            "start_gate_contract": start_gate_contract,
            "s_thinking_packet": s_thinking_packet,
            "s_thinking_history": s_thinking_history,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }, state, source_kind="start_gate_contract", producer_node="-1s_start_gate", source_ref="budget_exhausted", content=start_gate_contract, confidence=0.8)

    if start_gate_contract["direct_delivery_allowed"] or analysis_delivery_allowed:
        memo = str(start_gate_switches.get("memo") or "").strip() or "thin start gate produced a normalized goal contract only."
        route_reason = (
            f"{memo} Route directly because phase_2 evidence satisfies the current answer boundary."
            if analysis_delivery_allowed and not start_gate_contract["direct_delivery_allowed"]
            else f"{memo} Route directly because answer_mode_policy allows delivery without private-memory retrieval."
        )
        s_thinking_packet = _build_s_thinking_packet(
            start_gate_contract=start_gate_contract,
            start_gate_review=start_gate_review,
            start_gate_switches=start_gate_switches,
            reasoning_plan=reasoning_plan,
            next_node="phase_3",
            route_reason=route_reason,
        )
        s_thinking_history = build_cumulative_s_thinking_packet(
            current=s_thinking_packet,
            previous_history=incoming_s_thinking_history,
        )
        decision = make_auditor_decision(
            "phase_3",
            memo=route_reason,
        )
        current_turn_facts = extract_current_turn_grounding_facts(
            user_input,
            start_gate_switches.get("goal_contract", {}),
        )
        if start_gate_contract.get("current_turn_facts"):
            current_turn_facts = list(start_gate_contract.get("current_turn_facts") or [])
        return attach_ledger_event({
            "response_strategy": response_strategy_from_answer_mode_policy(
                user_input,
                start_gate_contract["answer_mode_policy"],
                current_turn_facts,
            ),
            "answer_mode_policy": start_gate_contract["answer_mode_policy"],
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "readiness_decision": decision.get("readiness_decision", {}),
            "self_correction_memo": decision.get("reasoning") or decision.get("memo") or "",
            "start_gate_review": start_gate_review,
            "start_gate_switches": start_gate_switches,
            "start_gate_contract": start_gate_contract,
            "s_thinking_packet": s_thinking_packet,
            "s_thinking_history": s_thinking_history,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }, state, source_kind="start_gate_contract", producer_node="-1s_start_gate", source_ref="direct_delivery_allowed", content=start_gate_contract, confidence=0.8)

    memo = str(start_gate_switches.get("memo") or start_gate_review.get("why_short") or reasoning_plan.get("rationale") or "").strip()
    if not memo:
        memo = "Tiny gate produced only a thin contract; route to the next node."

    planner_memo = (
        f"{memo} | thin-controller start gate: route to -1a; do not execute tools or deliver from heuristics."
        if memo
        else "thin-controller start gate: route to -1a; do not execute tools or deliver from heuristics."
    )
    decision = make_auditor_decision("plan_with_strategist", memo=planner_memo)
    memo = planner_memo
    s_thinking_packet = _build_s_thinking_packet(
        start_gate_contract=start_gate_contract,
        start_gate_review=start_gate_review,
        start_gate_switches=start_gate_switches,
        reasoning_plan=reasoning_plan,
        next_node="-1a",
        route_reason=memo,
    )
    s_thinking_history = build_cumulative_s_thinking_packet(
        current=s_thinking_packet,
        previous_history=incoming_s_thinking_history,
    )
    return attach_ledger_event({
        "auditor_instruction": decision["instruction"],
        "auditor_decision": decision,
        "readiness_decision": decision.get("readiness_decision", {}),
        "self_correction_memo": memo,
        "start_gate_review": start_gate_review,
        "start_gate_switches": start_gate_switches,
        "start_gate_contract": start_gate_contract,
        "s_thinking_packet": s_thinking_packet,
        "s_thinking_history": s_thinking_history,
        "reasoning_budget": reasoning_budget,
        "reasoning_plan": reasoning_plan,
    }, state, source_kind="start_gate_contract", producer_node="-1s_start_gate", source_ref="needs_planning", content=start_gate_contract, confidence=0.8)


__all__ = ["run_phase_minus_1s_start_gate"]
