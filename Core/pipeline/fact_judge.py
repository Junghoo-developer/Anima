"""Phase 2b fact judge for the ANIMA field loop.

Phase 2b turns the phase 2a raw-read report into a structured evidence report.
It should judge source coverage and fact usability, then hand the packet onward;
it should not execute tools or write the final user-facing answer.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


def run_phase_2_analyzer(
    state: dict[str, Any],
    *,
    llm: Any,
    analysis_report_schema: Any,
    build_phase_2b_prompt: Callable[..., str],
    working_memory_packet_for_prompt: Callable[[dict[str, Any]], dict[str, Any]],
    raw_read_report_packet_for_prompt: Callable[[dict[str, Any]], dict[str, Any]],
    build_source_relay_packet: Callable[[dict[str, Any]], dict[str, Any]],
    source_relay_packet_for_prompt: Callable[[dict[str, Any]], str],
    planned_operation_contract_from_state: Callable[[dict[str, Any]], dict[str, Any]],
    normalize_execution_trace: Callable[[dict[str, Any]], dict[str, Any]],
    tool_carryover_from_state: Callable[[dict[str, Any]], dict[str, Any]],
    evidence_ledger_for_prompt: Callable[[dict[str, Any]], str],
    normalize_analysis_with_source_relay: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    enforce_field_memo_judgments: Callable[[dict[str, Any], dict[str, Any], str], dict[str, Any]],
    build_reasoning_board_from_analysis: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    war_room_from_critic: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]],
    execution_trace_after_phase2b: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    attach_ledger_event: Callable[..., dict[str, Any]],
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Build the structured phase 2b evidence report from phase 2a output."""
    print_fn("[Phase 2b] Building structured evidence report from phase_2a raw read...")

    current_loop = state.get("loop_count", 0)
    auditor_memo = state.get("self_correction_memo", "")
    working_memory_packet = working_memory_packet_for_prompt(state.get("working_memory", {}), role="fact_judge")
    raw_read_report = state.get("raw_read_report", {})
    raw_read_packet = raw_read_report_packet_for_prompt(raw_read_report)
    source_relay_packet = build_source_relay_packet(raw_read_report)
    source_relay_prompt = source_relay_packet_for_prompt(source_relay_packet)
    operation_contract_packet = json.dumps(
        planned_operation_contract_from_state(state),
        ensure_ascii=False,
        indent=2,
    )
    execution_trace_packet = json.dumps(
        normalize_execution_trace(state.get("execution_trace", {})),
        ensure_ascii=False,
        indent=2,
    )
    tool_carryover_packet = json.dumps(
        tool_carryover_from_state(state),
        ensure_ascii=False,
        indent=2,
    )
    evidence_ledger_packet = evidence_ledger_for_prompt(state.get("evidence_ledger", {}))
    critic_lens_packet = state.get("critic_lens_packet", {})
    if not isinstance(critic_lens_packet, dict):
        critic_lens_packet = {}
    critic_lens_prompt = json.dumps(critic_lens_packet, ensure_ascii=False, indent=2) if critic_lens_packet else "N/A"
    read_mode = str(raw_read_report.get("read_mode") or "").strip()
    analysis_mode = (
        "recent_dialogue_review"
        if read_mode == "recent_dialogue_review"
        else "internal_reasoning_only"
        if read_mode == "current_turn_only"
        else "tool_grounded"
    )

    sys_prompt = build_phase_2b_prompt(
        analysis_mode=analysis_mode,
        user_input=state["user_input"],
        raw_read_packet=raw_read_packet,
        auditor_memo=auditor_memo,
        working_memory_packet=working_memory_packet,
        operation_contract_packet=operation_contract_packet,
        execution_trace_packet=execution_trace_packet,
        tool_carryover_packet=tool_carryover_packet,
        critic_lens_prompt=critic_lens_prompt,
        source_relay_prompt=source_relay_prompt,
        evidence_ledger_packet=evidence_ledger_packet,
    )

    structured_llm = llm.with_structured_output(analysis_report_schema)
    try:
        response_obj = structured_llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=state["user_input"]),
        ])
        analysis_dict = normalize_analysis_with_source_relay(response_obj.model_dump(), source_relay_packet)
        analysis_dict = enforce_field_memo_judgments(analysis_dict, raw_read_report, state["user_input"])
        reasoning_board = build_reasoning_board_from_analysis(state, analysis_dict)
        status = analysis_dict.get("investigation_status", "UNKNOWN")
        brief = analysis_dict.get("situational_brief", "")
        print_fn(f"  [Phase 2b] status={status} | brief={brief[:120]}")
        fake_ai_message = AIMessage(content=json.dumps(analysis_dict, ensure_ascii=False))
    except Exception as exc:
        print_fn(f"[Phase 2b] structured output error: {exc}")
        analysis_dict = {
            "evidences": [],
            "source_judgments": [],
            "analytical_thought": "Structured output failed, so phase_2b used a minimal fallback analysis.",
            "situational_brief": "Phase_2b fallback was used because structured output failed.",
            "investigation_status": "INCOMPLETE",
        }
        analysis_dict = enforce_field_memo_judgments(analysis_dict, raw_read_report, state["user_input"])
        reasoning_board = build_reasoning_board_from_analysis(state, analysis_dict)
        fake_ai_message = AIMessage(content="phase_2_fallback_seed")

    war_room = war_room_from_critic(state, analysis_dict, raw_read_report)
    result = {
        "analysis_report": analysis_dict,
        "reasoning_board": reasoning_board,
        "war_room": war_room,
        "critic_lens_packet": {},
        "execution_trace": execution_trace_after_phase2b(state, analysis_dict),
        "loop_count": current_loop + 1,
        "messages": [fake_ai_message],
    }
    return attach_ledger_event(
        result,
        state,
        source_kind="judge_packet",
        producer_node="phase_2_analyzer",
        source_ref=str(analysis_dict.get("investigation_status") or "analysis_report"),
        content={
            "investigation_status": analysis_dict.get("investigation_status", ""),
            "contract_status": analysis_dict.get("contract_status", ""),
            "accepted_facts": analysis_dict.get("usable_field_memo_facts", []) or analysis_dict.get("evidences", []),
            "missing_slots": analysis_dict.get("missing_slots", []),
            "source_judgments": analysis_dict.get("source_judgments", []),
        },
        confidence=0.82,
    )


__all__ = ["run_phase_2_analyzer"]
