import json

from langchain_core.messages import AIMessage, SystemMessage

from Core.evidence_ledger import evidence_ledger_for_prompt
from Core.pipeline.structured_io import invoke_structured_with_repair, validate_warroom_output

from .contracts import WarRoomDeliberationOutput
from .state import (
    _derive_war_room_operating_contract,
    _normalize_war_room_operating_contract,
    _normalize_war_room_state,
    _upsert_war_room_agent_note,
)


def run_phase_warroom_deliberator(
    state,
    *,
    llm,
    operation_plan_from_state,
    normalize_action_plan,
    working_memory_packet_for_prompt,
    attach_ledger_event,
    war_room_output_is_usable,
    war_room_seed_alignment_issue,
    response_strategy_from_war_room_output,
    fallback_war_room_output,
):
    print("[WarRoom] Running no-tool deliberation lane...")
    user_input = str(state.get("user_input") or "")
    recent_context = str(state.get("recent_context") or "")
    working_memory = state.get("working_memory", {}) if isinstance(state.get("working_memory", {}), dict) else {}
    strategist_output = state.get("strategist_output", {}) if isinstance(state.get("strategist_output", {}), dict) else {}
    response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = state.get("response_strategy", {}) if isinstance(state.get("response_strategy", {}), dict) else {}
    response_strategy = json.loads(json.dumps(response_strategy, ensure_ascii=False)) if isinstance(response_strategy, dict) else {}
    previous_war_room_output = state.get("war_room_output", {}) if isinstance(state.get("war_room_output", {}), dict) else {}
    previous_alignment_issue = war_room_seed_alignment_issue(user_input, previous_war_room_output, recent_context) if previous_war_room_output else ""
    strategy_seed = str(response_strategy.get("direct_answer_seed") or "").strip()
    if strategy_seed:
        strategy_seed_issue = war_room_seed_alignment_issue(
            user_input,
            {
                "deliberation_status": "COMPLETED",
                "usable_answer_seed": strategy_seed,
                "confidence": 1.0,
            },
            recent_context,
        )
        if strategy_seed_issue:
            response_strategy["direct_answer_seed"] = ""
            response_strategy["reasoning_brief"] = (
                str(response_strategy.get("reasoning_brief") or "").strip()
                + f" Previous direct_answer_seed was rejected before WarRoom: {strategy_seed_issue}"
            ).strip()
    operation_plan = operation_plan_from_state(state, strategist_output)
    war_room = _normalize_war_room_state(state.get("war_room", {}))
    war_room_contract = _normalize_war_room_operating_contract(
        strategist_output.get("war_room_contract")
        or war_room.get("operating_contract")
        or _derive_war_room_operating_contract(
            user_input,
            state.get("analysis_report", {}) if isinstance(state.get("analysis_report", {}), dict) else {},
            normalize_action_plan(strategist_output.get("action_plan", {})),
            response_strategy,
            state.get("start_gate_review", {}) if isinstance(state.get("start_gate_review", {}), dict) else {},
        )
    )

    prompt = (
        "You are ANIMA WarRoom: a no-tool free-reasoning lane.\n"
        "This is not a search node. Using -1a's allowed freedom/duty/gap contract, reason about what this current turn needs.\n"
        "Do not write a long final answer. Produce a usable_answer_seed that phase_3 can say naturally.\n"
        "Do not report the user speech as 'the user said...'.\n\n"
        f"[user_input]\n{user_input}\n\n"
        f"[recent_context]\n{recent_context}\n\n"
        f"[working_memory]\n{working_memory_packet_for_prompt(working_memory)}\n\n"
        f"[evidence_ledger]\n{evidence_ledger_for_prompt(state.get('evidence_ledger', {}))}\n\n"
        f"[operation_plan]\n{json.dumps(operation_plan, ensure_ascii=False, indent=2)}\n\n"
        f"[war_room_contract]\n{json.dumps(war_room_contract, ensure_ascii=False, indent=2)}\n\n"
        f"[response_strategy]\n{json.dumps(response_strategy, ensure_ascii=False, indent=2)}\n\n"
        f"[previous_war_room_output]\n{json.dumps(previous_war_room_output, ensure_ascii=False, indent=2) if previous_war_room_output else 'N/A'}\n\n"
        f"[judge_rejection_reason]\n{previous_alignment_issue or str(state.get('self_correction_memo') or '') or 'N/A'}\n\n"
        "Rules:\n"
        "1. deliberation_status must be COMPLETED, NEEDS_REPLAN, or INSUFFICIENT.\n"
        "2. If a tool is truly required, choose NEEDS_REPLAN and explain missing_items.\n"
        "3. If no tool is needed, choose COMPLETED and write usable_answer_seed in natural Korean.\n"
        "4. usable_answer_seed must be a sentence the user can hear, not an internal report.\n"
        "5. If judge_rejection_reason exists, do not repeat the rejected seed; attach current user details/emotion directly.\n"
    )

    structured_failure = {}
    result = invoke_structured_with_repair(
        llm=llm,
        schema=WarRoomDeliberationOutput,
        messages=[SystemMessage(content=prompt)],
        node_name="warroom_deliberator",
        repair_prompt="Return valid WarRoomDeliberationOutput JSON only. Do not write a final answer outside the schema.",
        max_repairs=1,
    )
    if result.ok:
        war_room_output, structured_failure = validate_warroom_output(result.value)
    else:
        structured_failure = result.failure
        war_room_output = {}

    if structured_failure:
        print(f"[WarRoom] structured output error: {structured_failure.get('summary', '')}")
        war_room_output = {
            "deliberation_status": "INSUFFICIENT",
            "reasoning_summary": "WarRoom structured output failed; no free-text output is allowed to cross the graph boundary.",
            "usable_answer_seed": "",
            "duty_checklist": [],
            "missing_items": ["structured_warroom_output"],
            "confidence": 0.0,
            "structured_failure": structured_failure,
        }
        response_strategy["direct_answer_seed"] = ""
    elif not war_room_output_is_usable(war_room_output):
        fallback = fallback_war_room_output(user_input, operation_plan, response_strategy, war_room_contract, recent_context)
        if not str(war_room_output.get("usable_answer_seed") or "").strip():
            war_room_output = fallback
        else:
            war_room_output["confidence"] = max(float(war_room_output.get("confidence", 0.0) or 0.0), 0.5)

    alignment_issue = war_room_seed_alignment_issue(user_input, war_room_output, recent_context)
    if alignment_issue:
        war_room_output["alignment_issue"] = alignment_issue
        war_room_output["needs_judge_refinement"] = True
    else:
        war_room_output["alignment_issue"] = ""
        war_room_output["needs_judge_refinement"] = False
    try:
        prior_revision = int(previous_war_room_output.get("revision_count", 0) or 0) if previous_war_room_output else 0
    except (TypeError, ValueError):
        prior_revision = 0
    war_room_output["revision_count"] = prior_revision + 1

    response_strategy = response_strategy_from_war_room_output(
        user_input,
        war_room_output,
        operation_plan,
        war_room_contract,
        response_strategy,
    )
    war_room["operating_contract"] = war_room_contract
    war_room = _upsert_war_room_agent_note(war_room, {
        "agent_name": "war_room",
        "used_freedom": True,
        "freedom_scope": str(war_room_contract.get("freedom", {}).get("scope") or "bounded_speculation"),
        "shortage_reason": str(war_room_output.get("reasoning_summary") or ""),
        "missing_items": war_room_output.get("missing_items", []) if isinstance(war_room_output.get("missing_items"), list) else [],
        "why_no_tool": str(war_room_contract.get("reason", {}).get("why_tool_is_not_primary") or ""),
        "allowed_output_boundary": str(war_room_contract.get("phase3_handoff", {}).get("allowed_output_boundary") or ""),
    })
    if structured_failure:
        war_room["structured_failure"] = structured_failure
    result = {
        "war_room_output": war_room_output,
        "response_strategy": response_strategy,
        "operation_plan": operation_plan,
        "war_room": war_room,
        "loop_count": int(state.get("loop_count", 0) or 0) + 1,
        "messages": [AIMessage(content="war_room_deliberation_completed")],
    }
    return attach_ledger_event(
        result,
        state,
        source_kind="warroom_output",
        producer_node="warroom_deliberator",
        source_ref=str(war_room_output.get("deliberation_status") or "warroom"),
        content=war_room_output,
        confidence=float(war_room_output.get("confidence", 0.6) or 0.6) if isinstance(war_room_output, dict) else 0.6,
    )


__all__ = ["run_phase_warroom_deliberator"]
