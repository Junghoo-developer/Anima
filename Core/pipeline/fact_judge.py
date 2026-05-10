"""Phase 2b fact judge for the ANIMA field loop.

Phase 2b turns the phase 2a raw-read report into a structured evidence report.
It should judge source coverage and fact usability, then hand the packet onward;
it should not execute tools or write the final user-facing answer.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .structured_io import invoke_structured_with_repair


def _fallback_analysis_from_raw_read_report(raw_read_report: dict[str, Any]) -> dict[str, Any]:
    """Preserve phase 2a observations when structured 2b output fails."""
    raw_read_report = raw_read_report if isinstance(raw_read_report, dict) else {}
    raw_items = raw_read_report.get("items", [])
    if not isinstance(raw_items, list):
        raw_items = []

    evidences: list[dict[str, str]] = []
    source_judgments: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        observed_fact = str(item.get("observed_fact") or item.get("excerpt") or "").strip()
        if not observed_fact:
            continue
        source_id = str(item.get("source_id") or "").strip() or f"raw_item_{idx}"
        source_type = str(item.get("source_type") or "").strip() or "raw_source"
        evidences.append(
            {
                "source_id": source_id,
                "source_type": source_type,
                "extracted_fact": observed_fact,
            }
        )
        source_judgments.append(
            {
                "source_id": source_id,
                "source_type": source_type,
                "source_status": "ambiguous",
                "accepted_facts": [observed_fact],
                "contested_facts": [],
                "objection_reason": "Structured phase_2b output failed; this fact is preserved from phase_2a raw observation and still needs cautious delivery.",
                "missing_info": [],
                "search_needed": False,
            }
        )

    if not evidences:
        return {
            "evidences": [],
            "source_judgments": [],
            "analytical_thought": "Structured output failed and phase_2a provided no usable raw observations.",
            "situational_brief": "Phase_2b fallback found no raw observations to preserve.",
            "investigation_status": "INCOMPLETE",
            "can_answer_user_goal": False,
            "contract_status": "missing_slot",
            "missing_slots": ["usable raw observations"],
            "filled_slots": {},
            "unfilled_slots": ["usable raw observations"],
            "rejected_sources": [],
        }

    source_summary = str(raw_read_report.get("source_summary") or "").strip()
    return {
        "evidences": evidences,
        "source_judgments": source_judgments,
        "analytical_thought": (
            "Structured output failed, so phase_2b preserved phase_2a raw observations as cautious grounded facts."
        ),
        "situational_brief": source_summary or f"Phase_2b fallback preserved {len(evidences)} raw observations.",
        "investigation_status": "COMPLETED",
        "can_answer_user_goal": True,
        "contract_status": "satisfied",
        "missing_slots": [],
        "filled_slots": {"raw_observations": len(evidences)},
        "unfilled_slots": [],
        "rejected_sources": [],
    }


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

    result = invoke_structured_with_repair(
        llm=llm,
        schema=analysis_report_schema,
        messages=[
            SystemMessage(content=sys_prompt),
            HumanMessage(content="Return the AnalysisReport structured packet for the raw-read report above. Do not answer the user."),
        ],
        node_name="phase_2b_fact_judge",
        repair_prompt=(
            "Return valid AnalysisReport JSON only. Use keys from the schema, including "
            "evidences, source_judgments, analytical_thought, situational_brief, "
            "investigation_status, can_answer_user_goal, contract_status, missing_slots, "
            "filled_slots, and unfilled_slots. Do not return analysis_summary, key_entities, "
            "a bare date, number, or final answer."
        ),
        max_repairs=2,
    )
    try:
        if not result.ok:
            raise ValueError(result.failure.get("summary", "structured output failed"))
        analysis_dict = normalize_analysis_with_source_relay(result.value, source_relay_packet)
        analysis_dict = enforce_field_memo_judgments(analysis_dict, raw_read_report, state["user_input"])
        reasoning_board = build_reasoning_board_from_analysis(state, analysis_dict)
        status = analysis_dict.get("investigation_status", "UNKNOWN")
        brief = analysis_dict.get("situational_brief", "")
        print_fn(f"  [Phase 2b] status={status} | brief={brief[:120]}")
        fake_ai_message = AIMessage(content=json.dumps(analysis_dict, ensure_ascii=False))
    except Exception as exc:
        print_fn(f"[Phase 2b] structured output error: {exc}")
        analysis_dict = _fallback_analysis_from_raw_read_report(raw_read_report)
        if not result.ok:
            analysis_dict["structured_failure"] = result.failure
        analysis_dict = enforce_field_memo_judgments(analysis_dict, raw_read_report, state["user_input"])
        reasoning_board = build_reasoning_board_from_analysis(state, analysis_dict)
        fake_ai_message = AIMessage(content=json.dumps(analysis_dict, ensure_ascii=False))

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
