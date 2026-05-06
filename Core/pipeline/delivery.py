"""Phase 3 delivery for the ANIMA field loop.

Phase 3 turns the approved judge/speaker contract into the final user-facing
assistant message. It should not choose tools or reopen evidence planning.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..prompt_builders import build_phase3_sys_prompt, compact_phase3_contract_for_prompt


def run_phase_3_validator(
    state: dict[str, Any],
    *,
    llm: Any,
    sanitize_response_strategy_for_phase3: Callable[[dict[str, Any], str], dict[str, Any]],
    phase3_recent_context_excerpt: Callable[..., str],
    phase3_reference_policy: Callable[[str, int], dict[str, Any]],
    build_judge_speaker_packet: Callable[..., dict[str, Any]],
    build_phase3_lane_delivery_packet: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    build_phase3_delivery_payload: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]],
    build_phase3_speaker_judge_contract: Callable[..., dict[str, Any]],
    normalize_readiness_decision: Callable[[dict[str, Any] | None], dict[str, Any]],
    normalize_user_facing_text: Callable[[str], str],
    attach_ledger_event: Callable[..., dict[str, Any]],
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Generate the final assistant response from the approved delivery packet."""
    response_strategy = sanitize_response_strategy_for_phase3(
        state.get("response_strategy", {}),
        state.get("user_input", ""),
    )
    reasoning_board = state.get("reasoning_board", {})
    loop_count = state.get("loop_count", 0)
    phase3_recent_context = phase3_recent_context_excerpt(state.get("recent_context", ""))
    phase3_reference_policy_packet = phase3_reference_policy(state.get("search_results", ""), loop_count)
    judge_speaker_packet = build_judge_speaker_packet(
        reasoning_board=reasoning_board,
        response_strategy=response_strategy,
        phase3_reference_policy=phase3_reference_policy_packet,
    )
    delivery_packet = judge_speaker_packet.get("delivery_packet", {}) if isinstance(judge_speaker_packet.get("delivery_packet"), dict) else {}
    if not delivery_packet:
        delivery_packet = {
            "reply_mode": judge_speaker_packet.get("reply_mode", ""),
            "delivery_freedom_mode": judge_speaker_packet.get("delivery_freedom_mode", ""),
            "final_answer_brief": judge_speaker_packet.get("final_answer_brief", ""),
            "approved_fact_cells": judge_speaker_packet.get("approved_fact_cells", []),
            "approved_claims": judge_speaker_packet.get("approved_claims", []),
            "followup_instruction": judge_speaker_packet.get("followup_instruction", ""),
            "raw_reference_excerpt": judge_speaker_packet.get("raw_reference_excerpt", ""),
            "hard_constraints": [],
        }
    grounded_mode = judge_speaker_packet.get("speaker_mode") == "grounded_mode"
    delivery_freedom_mode = str(delivery_packet.get("delivery_freedom_mode") or judge_speaker_packet.get("delivery_freedom_mode") or "grounded").strip() or "grounded"
    supervisor_memo = state.get("supervisor_instructions", "")
    if "[119 rescue]" in supervisor_memo:
        supervisor_memo = str(supervisor_memo).replace("[119 rescue]", "").strip()
    elif not state.get("rescue_handoff_packet"):
        supervisor_memo = ""
    phase3_delivery_packet = build_phase3_lane_delivery_packet(state, judge_speaker_packet)
    phase3_delivery_payload = build_phase3_delivery_payload(state, judge_speaker_packet, phase3_delivery_packet)
    speaker_judge_contract = build_phase3_speaker_judge_contract(
        state,
        phase3_delivery_payload,
        phase3_recent_context=phase3_recent_context,
        delivery_freedom_mode=delivery_freedom_mode,
        grounded_mode=grounded_mode,
        supervisor_memo=supervisor_memo,
    )
    if grounded_mode:
        print_fn("[Phase 3] Generating final answer from grounded judge packet...")
    else:
        print_fn("[Phase 3] Generating direct conversational answer...")

    prompt_contract = compact_phase3_contract_for_prompt(speaker_judge_contract)
    speaker_contract_prompt = json.dumps(prompt_contract, ensure_ascii=False, indent=2)
    sys_prompt = build_phase3_sys_prompt(
        str(prompt_contract.get("answer_mode") or speaker_judge_contract.get("ANSWER_MODE") or ""),
        speaker_contract_prompt,
    )

    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=state["user_input"]),
    ])

    raw_text = response.content if isinstance(response.content, str) else str(response.content)
    normalized_text = normalize_user_facing_text(raw_text)
    final_message = AIMessage(content=normalized_text if normalized_text else raw_text)

    print_fn("[Phase 3] Final response generated.")
    result = {
        "messages": [final_message],
        "phase3_delivery_packet": phase3_delivery_packet,
        "phase3_delivery_payload": phase3_delivery_payload,
        "phase3_speaker_contract": speaker_judge_contract,
        "readiness_decision": normalize_readiness_decision(
            phase3_delivery_payload.get("readiness_decision", {})
        ),
    }
    return attach_ledger_event(
        result,
        state,
        source_kind="assistant_turn",
        producer_node="phase_3_validator",
        source_ref="final_answer",
        content={
            "final_answer": final_message.content,
            "answer_mode": speaker_judge_contract.get("ANSWER_MODE", ""),
            "ready": speaker_judge_contract.get("READY", False),
            "readiness_decision": result["readiness_decision"],
        },
        confidence=1.0,
    )


__all__ = ["run_phase_3_validator"]
