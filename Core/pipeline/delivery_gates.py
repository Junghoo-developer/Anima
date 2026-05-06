"""Phase 3 delivery gate helpers.

These helpers decide whether grounded turns may proceed to phase 3 or must
return to planning/tool work. They keep routing semantics supplied by Core.nodes
callbacks while moving the gate body out of the graph god-file.
"""

from __future__ import annotations

from typing import Any, Callable


def turn_requires_grounded_delivery(
    user_input: str,
    recent_context: str = "",
    *,
    answer_mode_policy_for_turn: Callable[..., dict],
):
    policy = answer_mode_policy_for_turn(user_input, recent_context)
    return bool(policy.get("grounded_delivery_required"))


def field_memo_answer_ready_for_phase3(
    raw_read_report: dict,
    analysis_data: dict,
    user_input: str,
    *,
    build_field_memo_user_brief: Callable[..., dict],
    field_memo_packet_ready_for_delivery: Callable[..., bool],
):
    packet = build_field_memo_user_brief(raw_read_report, analysis_data)
    return field_memo_packet_ready_for_delivery(packet, analysis_data, user_input)


def recent_dialogue_ready_for_phase3(
    raw_read_report: dict,
    analysis_data: dict,
    user_input: str,
    *,
    build_recent_dialogue_brief: Callable[..., dict],
):
    packet = build_recent_dialogue_brief(raw_read_report, analysis_data, user_input=user_input)
    brief = str(packet.get("user_facing_recent_dialogue_brief") or "").strip()
    turns = packet.get("recent_turns", []) if isinstance(packet, dict) else []
    return bool(brief and isinstance(turns, list) and turns)


def grounded_source_ready_for_phase3(
    state: dict,
    analysis_data: dict,
    user_input: str,
    *,
    field_memo_answer_ready_for_phase3: Callable[[dict, dict, str], bool],
    recent_dialogue_ready_for_phase3: Callable[[dict, dict, str], bool],
    analysis_has_answer_relevant_evidence: Callable[[dict | None], bool],
    operation_plan_from_state: Callable[..., dict],
):
    raw_read_report = state.get("raw_read_report", {}) if isinstance(state, dict) else {}
    if not isinstance(raw_read_report, dict):
        raw_read_report = {}
    read_mode = str(raw_read_report.get("read_mode") or "").strip()
    status = str((analysis_data or {}).get("investigation_status") or "").upper()

    if read_mode == "field_memo_review":
        return field_memo_answer_ready_for_phase3(raw_read_report, analysis_data, user_input)
    if read_mode == "recent_dialogue_review":
        return recent_dialogue_ready_for_phase3(raw_read_report, analysis_data, user_input)
    if read_mode in {"full_raw_review", "artifact_fast_path"}:
        return status == "COMPLETED" and analysis_has_answer_relevant_evidence(analysis_data)

    strategist_output = state.get("strategist_output", {}) if isinstance(state, dict) else {}
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    operation_plan = operation_plan_from_state(state, strategist_output)
    source_lane = str(operation_plan.get("source_lane") or "").strip()
    if source_lane in {"memory_search", "scroll_source", "artifact_read"}:
        return status == "COMPLETED" and analysis_has_answer_relevant_evidence(analysis_data)
    return False


def phase3_delivery_payload_for_gate(
    state: dict,
    strategist_output: dict,
    analysis_data: dict,
    *,
    phase3_reference_policy: Callable[[str, int], dict],
    build_judge_speaker_packet: Callable[..., dict],
    build_phase3_lane_delivery_packet: Callable[[dict, dict], dict],
    build_phase3_delivery_payload: Callable[[dict, dict, dict], dict],
):
    temp_state = dict(state)
    if isinstance(strategist_output, dict) and strategist_output:
        temp_state["strategist_output"] = strategist_output
    if isinstance(analysis_data, dict) and analysis_data:
        temp_state["analysis_report"] = analysis_data

    response_strategy = temp_state.get("response_strategy", {})
    if isinstance(strategist_output, dict) and isinstance(strategist_output.get("response_strategy"), dict):
        response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}

    reasoning_board = temp_state.get("reasoning_board", {})
    if not isinstance(reasoning_board, dict):
        reasoning_board = {}
    phase3_reference = phase3_reference_policy(
        temp_state.get("search_results", ""),
        int(temp_state.get("loop_count", 0) or 0),
    )
    judge_packet = build_judge_speaker_packet(
        reasoning_board=reasoning_board,
        response_strategy=response_strategy,
        phase3_reference_policy=phase3_reference,
    )
    lane_packet = build_phase3_lane_delivery_packet(temp_state, judge_packet)
    delivery_payload = build_phase3_delivery_payload(temp_state, judge_packet, lane_packet)
    return delivery_payload


def phase3_delivery_payload_ready_for_gate(
    state: dict,
    strategist_output: dict,
    analysis_data: dict,
    *,
    phase3_delivery_payload_for_gate: Callable[[dict, dict, dict], dict],
):
    payload = phase3_delivery_payload_for_gate(state, strategist_output, analysis_data)
    return bool(isinstance(payload, dict) and payload.get("ready_for_delivery")), payload


def guard_phase3_decision_for_grounded_turn(
    state: dict,
    decision: dict,
    strategist_output: dict,
    analysis_data: dict,
    working_memory: dict,
    loop_count: int,
    reasoning_budget: int,
    response_strategy: dict | None = None,
    *,
    answer_mode_policy_from_state: Callable[[dict, dict], dict],
    short_term_context_strategy_is_usable: Callable[[dict, str, dict], bool],
    phase3_delivery_payload_ready_for_gate: Callable[[dict, dict, dict], tuple[bool, dict]],
    war_room_output_is_usable: Callable[[dict], bool],
    war_room_seed_alignment_issue: Callable[[str, dict, str], bool],
    soft_reasoning_budget_limit: Callable[[int], tuple[int, int]],
    decision_from_strategist_tool_contract: Callable[[dict, dict], dict | None],
    start_gate_requests_memory_recall: Callable[[dict, str], bool],
    compiled_memory_recall_queries: Callable[..., list[str]],
    tool_carryover_from_state: Callable[[dict], dict],
    make_auditor_decision: Callable[..., dict],
    gemini_scroll_candidate_from_state: Callable[..., dict | None],
    logger: Callable[[str], Any] | None = None,
):
    if not isinstance(decision, dict) or str(decision.get("action") or "").strip() != "phase_3":
        return decision

    user_input = str(state.get("user_input") or "")
    recent_context = str(state.get("recent_context") or "")
    answer_mode_policy = answer_mode_policy_from_state(state, analysis_data)
    if not bool(answer_mode_policy.get("grounded_delivery_required")):
        return decision

    phase3_strategy = response_strategy if isinstance(response_strategy, dict) else {}
    if not phase3_strategy and isinstance(strategist_output, dict):
        phase3_strategy = strategist_output.get("response_strategy", {}) if isinstance(strategist_output.get("response_strategy"), dict) else {}
    if short_term_context_strategy_is_usable(phase3_strategy, user_input, working_memory):
        return decision

    try:
        payload_ready, delivery_payload = phase3_delivery_payload_ready_for_gate(
            state,
            strategist_output,
            analysis_data,
        )
    except Exception as exc:
        if logger:
            logger(f"[phase3 delivery payload gate error] {exc}")
        payload_ready, delivery_payload = False, {}
    if payload_ready:
        payload_mode = str((delivery_payload or {}).get("answer_mode") or "").strip()
        payload_readiness = (delivery_payload or {}).get("readiness_decision", {})
        payload_status = str(payload_readiness.get("status") or "").strip() if isinstance(payload_readiness, dict) else ""
        if payload_mode not in {"current_turn_grounding", "public_parametric_knowledge", "generic_dialogue"} and payload_status not in {
            "ready_with_current_turn_facts",
            "ready_with_identity_context",
        }:
            return decision

    war_room_output = state.get("war_room_output", {})
    if isinstance(war_room_output, dict) and war_room_output_is_usable(war_room_output):
        if not war_room_seed_alignment_issue(user_input, war_room_output, recent_context):
            payload = delivery_payload if isinstance(delivery_payload, dict) else {}
            if str(payload.get("lane") or "").strip() == "warroom":
                return decision

    raw_read_report = state.get("raw_read_report", {})
    read_mode = str(raw_read_report.get("read_mode") or "").strip() if isinstance(raw_read_report, dict) else ""
    budget_limit, soft_limit = soft_reasoning_budget_limit(reasoning_budget)

    if not analysis_data:
        strategist_tool_decision = decision_from_strategist_tool_contract(strategist_output, analysis_data)
        if strategist_tool_decision:
            return strategist_tool_decision
        if start_gate_requests_memory_recall(state, user_input):
            recall_queries = compiled_memory_recall_queries(
                user_input,
                recent_context=recent_context,
                working_memory=working_memory,
                analysis_data=analysis_data,
                tool_carryover=tool_carryover_from_state(state),
            )
            if not recall_queries:
                return make_auditor_decision(
                    "plan_with_strategist",
                    memo="The start-gate contract requires grounded recall, but no safe recall query has been planned yet.",
                )
            recall_query = recall_queries[0]
            return make_auditor_decision(
                "call_tool",
                memo="Grounded recall request cannot go straight to phase_3 without a ready FieldMemo fact packet.",
                tool_name="tool_search_field_memos",
                tool_args={"query": recall_query, "limit": 6},
            )
        if loop_count > 0:
            return make_auditor_decision(
                "clean_failure",
                memo="Grounded delivery still has no analysis packet or executable source plan after a planning pass.",
            )
        return make_auditor_decision(
            "plan_with_strategist",
            memo="The contract requires grounding, so -1a must plan evidence gathering instead of the guard compiling a raw search.",
        )

    if read_mode == "field_memo_review" and loop_count <= soft_limit + 1:
        return make_auditor_decision(
            "plan_with_strategist",
            memo="FieldMemo candidates exist, but no usable FieldMemo facts satisfy the current user goal yet.",
        )

    if read_mode == "full_raw_review":
        gemini_scroll = gemini_scroll_candidate_from_state(
            state,
            memo=(
                "Memory search hit a Gemini chat node, but the current item did not answer the user goal. "
                "Scroll around that chat timestamp before declaring the search irrelevant."
            ),
        )
        if gemini_scroll:
            return gemini_scroll

    if loop_count <= max(soft_limit, budget_limit):
        return make_auditor_decision(
            "plan_with_strategist",
            memo="Phase_3 delivery was blocked because the source was read but the user's grounded success condition is not satisfied yet.",
        )

    return make_auditor_decision(
        "clean_failure",
        memo="Grounded delivery is still missing usable evidence after the safe retry budget.",
    )


__all__ = [
    "field_memo_answer_ready_for_phase3",
    "grounded_source_ready_for_phase3",
    "guard_phase3_decision_for_grounded_turn",
    "phase3_delivery_payload_for_gate",
    "phase3_delivery_payload_ready_for_gate",
    "recent_dialogue_ready_for_phase3",
    "turn_requires_grounded_delivery",
]
