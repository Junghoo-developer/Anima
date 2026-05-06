import json
from typing import Any


def _dedupe_keep_order(items):
    seen = set()
    result = []
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _is_clean_failure_action(action: Any) -> bool:
    return str(action or "").strip() in {"answer_not_ready", "clean_failure"}


def _normalize_delivery_freedom_mode(mode: str, reply_mode: str = ""):
    normalized_mode = str(mode or "").strip()
    if normalized_mode == "answer_not_ready":
        return "clean_failure"
    if normalized_mode in {"grounded", "supportive_free", "proposal", "identity_direct", "clean_failure"}:
        return normalized_mode

    normalized_reply_mode = str(reply_mode or "").strip()
    if normalized_reply_mode in {"continue_previous_offer", "ask_user_question_now"}:
        return "proposal"
    if normalized_reply_mode == "casual_reaction":
        return "supportive_free"
    if normalized_reply_mode == "cautious_minimal":
        return "clean_failure"
    return "grounded"


def _empty_operation_contract():
    return {
        "operation_kind": "unspecified",
        "target_scope": "",
        "query_variant": "",
        "novelty_requirement": "",
    }


def _normalize_operation_contract(contract: dict | None):
    base = _empty_operation_contract()
    if not isinstance(contract, dict):
        return base
    operation_kind = str(contract.get("operation_kind") or "").strip()
    if operation_kind not in {
        "unspecified",
        "search_new_source",
        "read_same_source_deeper",
        "extract_feature_summary",
        "compare_with_user_goal",
        "review_recent_dialogue",
        "deliver_now",
    }:
        operation_kind = "unspecified"
    base["operation_kind"] = operation_kind
    base["target_scope"] = str(contract.get("target_scope") or "").strip()
    base["query_variant"] = str(contract.get("query_variant") or "").strip()
    base["novelty_requirement"] = str(contract.get("novelty_requirement") or "").strip()
    return base


def _empty_action_plan():
    return {
        "current_step_goal": "",
        "required_tool": "",
        "next_steps_forecast": [],
        "operation_contract": _empty_operation_contract(),
    }


def _normalize_action_plan(action_plan: dict | None):
    base = _empty_action_plan()
    if not isinstance(action_plan, dict):
        return base
    base["current_step_goal"] = str(action_plan.get("current_step_goal") or "").strip()
    base["required_tool"] = str(action_plan.get("required_tool") or "").strip()
    next_steps = action_plan.get("next_steps_forecast", [])
    if isinstance(next_steps, list):
        base["next_steps_forecast"] = _dedupe_keep_order([str(step).strip() for step in next_steps if str(step).strip()])[:3]
    base["operation_contract"] = _normalize_operation_contract(action_plan.get("operation_contract", {}))
    return base


def _has_meaningful_strategy(strategy_data: dict):
    if not isinstance(strategy_data, dict) or not strategy_data:
        return False
    keys = [
        "reply_mode",
        "answer_goal",
        "evidence_brief",
        "reasoning_brief",
        "direct_answer_seed",
    ]
    if any(str(strategy_data.get(key) or "").strip() for key in keys):
        return True
    return bool(strategy_data.get("must_include_facts") or strategy_data.get("answer_outline"))


def _empty_war_room_operating_contract():
    return {
        "freedom": {
            "granted": False,
            "scope": "none",
            "reason": "none",
            "why_this_freedom": "No non-tool reasoning freedom has been earned yet.",
        },
        "duty": {
            "must_label_hypotheses": True,
            "must_separate_fact_and_interpretation": True,
            "must_report_missing_info": True,
            "must_not_upgrade_guess_to_fact": True,
            "speech_duty": "Deliver only the final user-facing answer, not an internal report.",
        },
        "reason": {
            "why_tool_is_not_primary": "",
            "why_discussion_is_useful": "",
            "decision_basis": "",
        },
        "deficiency": {
            "missing_items": [],
            "risk_if_ignored": "",
            "next_best_action": "",
        },
        "phase3_handoff": {
            "speaker_posture": "grounded_answer",
            "allowed_output_boundary": "Naturalize only confirmed facts and lightweight interpretation.",
            "forbidden_output_patterns": [
                "Report-style phrases like 'the user said...'",
                "Internal judge, lane, packet, or phase labels",
                "Unsupported missing-slot conclusions",
            ],
            "recent_context_use": "Use prior flow only as context, not as confirmed evidence.",
        },
    }


def _normalize_war_room_operating_contract(contract: dict | None):
    base = _empty_war_room_operating_contract()
    if not isinstance(contract, dict):
        return base

    for section in ("freedom", "duty", "reason", "deficiency", "phase3_handoff"):
        value = contract.get(section)
        if isinstance(value, dict):
            base[section].update(value)

    base["freedom"]["granted"] = bool(base["freedom"].get("granted"))
    scope = str(base["freedom"].get("scope") or "none").strip()
    if scope not in {"none", "planning_only", "bounded_speculation", "direct_empathy"}:
        scope = "none"
    base["freedom"]["scope"] = scope

    freedom_reason = str(base["freedom"].get("reason") or "none").strip()
    if freedom_reason not in {
        "none",
        "no_tool_needed",
        "no_suitable_tool",
        "tool_would_not_help",
        "user_requested_direct_thinking",
        "evidence_gap",
    }:
        freedom_reason = "none"
    base["freedom"]["reason"] = freedom_reason

    for key in (
        "must_label_hypotheses",
        "must_separate_fact_and_interpretation",
        "must_report_missing_info",
        "must_not_upgrade_guess_to_fact",
    ):
        base["duty"][key] = bool(base["duty"].get(key))

    missing_items = base["deficiency"].get("missing_items", [])
    if not isinstance(missing_items, list):
        missing_items = [missing_items]
    base["deficiency"]["missing_items"] = _dedupe_keep_order(
        [str(item).strip() for item in missing_items if str(item).strip()]
    )[:5]

    forbidden = base["phase3_handoff"].get("forbidden_output_patterns", [])
    if not isinstance(forbidden, list):
        forbidden = [forbidden]
    base["phase3_handoff"]["forbidden_output_patterns"] = _dedupe_keep_order(
        [str(item).strip() for item in forbidden if str(item).strip()]
    )[:8]
    return base


def _derive_war_room_operating_contract(
    user_input: str,
    analysis_data: dict | None,
    action_plan: dict | None,
    response_strategy: dict | None,
    start_gate_review: dict | None = None,
):
    del user_input
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    response_strategy = response_strategy if isinstance(response_strategy, dict) else {}
    action_plan = _normalize_action_plan(action_plan if isinstance(action_plan, dict) else {})
    start_gate_review = start_gate_review if isinstance(start_gate_review, dict) else {}

    status = str(analysis_data.get("investigation_status") or "").upper()
    required_tool = str(action_plan.get("required_tool") or "").strip()
    reply_mode = str(response_strategy.get("reply_mode") or "").strip()
    delivery_mode = _normalize_delivery_freedom_mode(
        str(response_strategy.get("delivery_freedom_mode") or "").strip(),
        reply_mode=reply_mode,
    )

    if required_tool:
        granted = False
        scope = "none"
        freedom_reason = "evidence_gap"
    elif delivery_mode == "supportive_free":
        granted = True
        scope = "direct_empathy"
        freedom_reason = "no_tool_needed"
    elif delivery_mode in {"proposal", "identity_direct"}:
        granted = True
        scope = "bounded_speculation"
        freedom_reason = "no_tool_needed"
    elif delivery_mode == "clean_failure":
        granted = True
        scope = "planning_only"
        freedom_reason = "no_suitable_tool" if not required_tool else "evidence_gap"
    else:
        granted = not required_tool
        scope = "planning_only" if granted else "none"
        freedom_reason = "no_tool_needed" if status == "COMPLETED" or not required_tool else "evidence_gap"

    missing_items = _war_room_missing_items_from_analysis(analysis_data)
    if status in {"INCOMPLETE", "EXPANSION_REQUIRED"} and not missing_items:
        missing_items.append("Evidence is still insufficient to settle the current turn safely.")
    if required_tool and required_tool not in missing_items:
        missing_items.append(f"Required tool call: {required_tool}")

    if required_tool:
        why_tool = f"A tool is primary here: {required_tool}"
    elif delivery_mode == "supportive_free":
        why_tool = "The turn calls for social/emotional response, so natural dialogue is primary."
    else:
        why_tool = "First define what can be said from the current information."

    speaker_posture = {
        "supportive_free": "conversation_partner",
        "proposal": "practical_planner",
        "identity_direct": "direct_identity_answer",
        "clean_failure": "transparent_limiter",
        "grounded": "grounded_answer",
    }.get(delivery_mode, "grounded_answer")

    forbidden = [
        "Report-style restatement of the user input",
        "Repeating the user turn instead of answering",
        "Internal judge/lane/packet labels",
        "Unsupported missing-slot conclusions",
    ]
    if delivery_mode == "supportive_free":
        allowed_boundary = "Engage naturally with the current emotional/contextual flow without inventing facts."
    elif delivery_mode == "proposal":
        allowed_boundary = "Offer 1-3 concrete next actions based on confirmed context."
    elif delivery_mode == "clean_failure":
        allowed_boundary = "Name only the missing item and the smallest useful next step."
    else:
        allowed_boundary = "Convert confirmed facts and light interpretation into natural user-facing speech."

    return _normalize_war_room_operating_contract({
        "freedom": {
            "granted": granted,
            "scope": scope,
            "reason": freedom_reason,
            "why_this_freedom": why_tool,
        },
        "duty": {
            "must_label_hypotheses": scope != "direct_empathy",
            "must_separate_fact_and_interpretation": True,
            "must_report_missing_info": delivery_mode == "clean_failure" or status in {"INCOMPLETE", "EXPANSION_REQUIRED"},
            "must_not_upgrade_guess_to_fact": True,
            "speech_duty": "The final answer must be conversational, not an internal analysis report.",
        },
        "reason": {
            "why_tool_is_not_primary": why_tool,
            "why_discussion_is_useful": "The discussion should clarify current reasoning boundaries and the next conversational move.",
            "decision_basis": str(start_gate_review.get("why_short") or response_strategy.get("reasoning_brief") or action_plan.get("current_step_goal") or "").strip(),
        },
        "deficiency": {
            "missing_items": missing_items,
            "risk_if_ignored": "If ignored, phase_3 may confuse an internal summary for an answer or overstate unsupported facts.",
            "next_best_action": str(action_plan.get("current_step_goal") or response_strategy.get("answer_goal") or "Answer briefly within the current allowed boundary.").strip(),
        },
        "phase3_handoff": {
            "speaker_posture": speaker_posture,
            "allowed_output_boundary": allowed_boundary,
            "forbidden_output_patterns": forbidden,
            "recent_context_use": "Use prior flow and tone only as supporting context, not as confirmed evidence.",
        },
    })


def _empty_war_room_state():
    return {
        "freedom": {
            "granted": False,
            "granted_by": "",
            "scope": "none",
            "reason": "none",
            "note": "No freedom is granted by default until a node explicitly earns it.",
        },
        "duty": {
            "must_label_hypotheses": True,
            "must_separate_fact_and_opinion": True,
            "must_report_missing_info": True,
            "must_not_upgrade_guess_to_fact": True,
            "boundary_note": "Facts and opinions must stay separate at all times.",
        },
        "epistemic_debt": {
            "debt_kind": [],
            "missing_items": [],
            "why_tool_not_used": "",
            "next_best_action": "",
        },
        "operating_contract": _empty_war_room_operating_contract(),
        "agent_notes": [],
    }


def _normalize_war_room_state(war_room: dict | None):
    base = _empty_war_room_state()
    if not isinstance(war_room, dict):
        return base
    for section in ("freedom", "duty", "epistemic_debt"):
        value = war_room.get(section)
        if isinstance(value, dict):
            base[section].update(value)
    notes = war_room.get("agent_notes", [])
    if isinstance(notes, list):
        base["agent_notes"] = [note for note in notes if isinstance(note, dict)]
    base["operating_contract"] = _normalize_war_room_operating_contract(war_room.get("operating_contract"))
    return base


def _war_room_missing_items_from_analysis(analysis_data: dict):
    missing_items = []
    if not isinstance(analysis_data, dict):
        return missing_items

    for item in analysis_data.get("evidences", []) if isinstance(analysis_data.get("evidences"), list) else []:
        if not isinstance(item, dict):
            continue
        extracted_fact = str(item.get("extracted_fact") or "").strip()
        if extracted_fact:
            break

    analytical_thought = str(analysis_data.get("analytical_thought") or "").strip()
    if analytical_thought and str(analysis_data.get("investigation_status") or "").upper() in {"EXPANSION_REQUIRED", "INCOMPLETE"}:
        missing_items.append(analytical_thought)

    return _dedupe_keep_order([item for item in missing_items if item])[:4]


def _upsert_war_room_agent_note(war_room: dict, note: dict):
    war_room = _normalize_war_room_state(war_room)
    agent_name = str((note or {}).get("agent_name") or "").strip()
    if not agent_name:
        return war_room
    notes = [existing for existing in war_room.get("agent_notes", []) if str(existing.get("agent_name") or "").strip() != agent_name]
    notes.append(note)
    war_room["agent_notes"] = notes[-6:]
    return war_room


def _war_room_from_critic(state: dict, analysis_data: dict, raw_read_report: dict):
    war_room = _normalize_war_room_state(state.get("war_room", {}))
    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    internal_reasoning_only = str((raw_read_report or {}).get("read_mode") or "").strip() == "current_turn_only"
    missing_items = _war_room_missing_items_from_analysis(analysis_data)

    if internal_reasoning_only:
        reason = "tool_would_not_help"
        scope = "planning_only"
        why_no_tool = "The current turn can be examined directly without external retrieval."
    else:
        reason = "none"
        scope = "none"
        why_no_tool = ""

    debt_kind = []
    if status in {"INCOMPLETE", "EXPANSION_REQUIRED"}:
        debt_kind.append("evidence_gap")
    if internal_reasoning_only:
        debt_kind.append("tool_gap")

    war_room["freedom"] = {
        "granted": internal_reasoning_only,
        "granted_by": "phase_2b",
        "scope": scope,
        "reason": reason,
        "note": "phase_2b used no-tool reasoning only because the current turn itself was the main evidence source." if internal_reasoning_only else "phase_2b stayed grounded in retrieved or provided sources.",
    }
    war_room["epistemic_debt"] = {
        "debt_kind": _dedupe_keep_order(debt_kind),
        "missing_items": missing_items,
        "why_tool_not_used": why_no_tool,
        "next_best_action": "Answer now with current evidence." if status == "COMPLETED" else "Hand the diagnosed gap to -1a so the strategist can plan the next step.",
    }
    return _upsert_war_room_agent_note(war_room, {
        "agent_name": "phase_2b",
        "used_freedom": internal_reasoning_only,
        "freedom_scope": scope,
        "shortage_reason": str((analysis_data or {}).get("situational_brief") or "").strip() or "phase_2b identified remaining gaps before a confident answer.",
        "missing_items": missing_items,
        "why_no_tool": why_no_tool or "phase_2b relied on the current turn because no stronger external source was required yet.",
        "allowed_output_boundary": "Only fact-grounded criticism and clearly labeled uncertainty are allowed.",
    })


def _war_room_after_advocate(war_room: dict, analysis_data: dict, strategist_output: dict, reasoning_board: dict):
    war_room = _normalize_war_room_state(war_room)
    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    candidate_pairs = reasoning_board.get("candidate_pairs", []) if isinstance(reasoning_board, dict) else []
    response_strategy = strategist_output.get("response_strategy", {}) if isinstance(strategist_output, dict) else {}
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    action_plan = _normalize_action_plan(strategist_output.get("action_plan", {})) if isinstance(strategist_output, dict) else _empty_action_plan()
    case_theory = str((strategist_output or {}).get("case_theory") or "").strip() if isinstance(strategist_output, dict) else ""
    operating_contract = _normalize_war_room_operating_contract(
        (strategist_output or {}).get("war_room_contract") if isinstance(strategist_output, dict) else None
    )
    used_freedom = bool(
        candidate_pairs
        or _has_meaningful_strategy(response_strategy)
        or action_plan.get("current_step_goal")
        or action_plan.get("required_tool")
        or case_theory
    )
    scope = str(operating_contract.get("freedom", {}).get("scope") or ("bounded_speculation" if candidate_pairs else "planning_only"))
    missing_items = operating_contract.get("deficiency", {}).get("missing_items", []) or war_room.get("epistemic_debt", {}).get("missing_items", [])
    freedom_reason = str(operating_contract.get("freedom", {}).get("reason") or ("evidence_gap" if status in {"INCOMPLETE", "EXPANSION_REQUIRED"} else "no_tool_needed"))

    war_room["freedom"] = {
        "granted": bool(operating_contract.get("freedom", {}).get("granted", used_freedom)),
        "granted_by": "-1a",
        "scope": scope,
        "reason": freedom_reason,
        "note": str(operating_contract.get("freedom", {}).get("why_this_freedom") or "-1a used limited reasoning freedom to assemble a defensible response plan from approved facts."),
    }
    duty_contract = operating_contract.get("duty", {}) if isinstance(operating_contract.get("duty"), dict) else {}
    war_room["duty"].update({
        "must_label_hypotheses": bool(duty_contract.get("must_label_hypotheses", True)),
        "must_separate_fact_and_opinion": bool(duty_contract.get("must_separate_fact_and_interpretation", True)),
        "must_report_missing_info": bool(duty_contract.get("must_report_missing_info", True)),
        "must_not_upgrade_guess_to_fact": bool(duty_contract.get("must_not_upgrade_guess_to_fact", True)),
        "boundary_note": str(duty_contract.get("speech_duty") or "Claims must stay anchored to facts, and guesses must remain labeled as guesses."),
    })
    deficiency = operating_contract.get("deficiency", {}) if isinstance(operating_contract.get("deficiency"), dict) else {}
    reason_contract = operating_contract.get("reason", {}) if isinstance(operating_contract.get("reason"), dict) else {}
    debt_kind = list(war_room.get("epistemic_debt", {}).get("debt_kind", []))
    if status in {"INCOMPLETE", "EXPANSION_REQUIRED"} and "evidence_gap" not in debt_kind:
        debt_kind.append("evidence_gap")
    if freedom_reason in {"no_suitable_tool", "tool_would_not_help"} and "tool_gap" not in debt_kind:
        debt_kind.append("tool_gap")
    war_room["epistemic_debt"] = {
        "debt_kind": _dedupe_keep_order(debt_kind),
        "missing_items": list(missing_items)[:4],
        "why_tool_not_used": str(reason_contract.get("why_tool_is_not_primary") or "").strip(),
        "next_best_action": str(deficiency.get("next_best_action") or action_plan.get("current_step_goal") or "").strip(),
    }
    war_room["operating_contract"] = operating_contract
    phase3_handoff = operating_contract.get("phase3_handoff", {}) if isinstance(operating_contract.get("phase3_handoff"), dict) else {}
    return _upsert_war_room_agent_note(war_room, {
        "agent_name": "-1a",
        "used_freedom": used_freedom,
        "freedom_scope": scope,
        "shortage_reason": case_theory or str((analysis_data or {}).get("analytical_thought") or "").strip() or "-1a had to shape a response under incomplete certainty.",
        "missing_items": list(missing_items)[:4],
        "why_no_tool": war_room["epistemic_debt"]["why_tool_not_used"] or "When -1a skips tools, it must explain the epistemic gap and hand an explicit plan to -1b instead of improvising.",
        "allowed_output_boundary": str(phase3_handoff.get("allowed_output_boundary") or "Only defended, fact-anchored response planning is allowed here."),
    })


def _war_room_after_judge(war_room: dict, decision: dict, analysis_data: dict, reasoning_board: dict):
    war_room = _normalize_war_room_state(war_room)
    verdict = reasoning_board.get("verdict_board", {}) if isinstance(reasoning_board, dict) else {}
    action = str((decision or {}).get("action") or "").strip()
    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    requires_search = bool(verdict.get("requires_search")) if isinstance(verdict, dict) else False
    answer_now = bool(verdict.get("answer_now")) if isinstance(verdict, dict) else False
    judge_notes = verdict.get("judge_notes", []) if isinstance(verdict.get("judge_notes"), list) else []
    missing_items = war_room.get("epistemic_debt", {}).get("missing_items", [])

    if action == "call_tool":
        freedom = {
            "granted": False,
            "granted_by": "-1b",
            "scope": "none",
            "reason": "evidence_gap",
            "note": "The judge requires more evidence before allowing delivery.",
        }
    elif action == "plan_more":
        freedom = {
            "granted": True,
            "granted_by": "-1b",
            "scope": "planning_only",
            "reason": "no_suitable_tool",
            "note": "The judge allows another planning pass because the current tools do not fit the case cleanly.",
        }
    elif _is_clean_failure_action(action):
        freedom = {
            "granted": True,
            "granted_by": "-1b",
            "scope": "planning_only",
            "reason": "no_suitable_tool" if requires_search else "evidence_gap",
            "note": "The judge prefers transparent limits over pretending to be ready.",
        }
    elif action == "warroom_deliberation":
        freedom = {
            "granted": True,
            "granted_by": "-1b",
            "scope": "bounded_speculation",
            "reason": "tool_would_not_help",
            "note": "The judge approved a no-tool WarRoom deliberation lane instead of forcing a fake evidence read.",
        }
    else:
        freedom = {
            "granted": True,
            "granted_by": "-1b",
            "scope": "bounded_speculation" if status in {"INCOMPLETE", "EXPANSION_REQUIRED"} and not requires_search else "planning_only",
            "reason": "evidence_gap" if status in {"INCOMPLETE", "EXPANSION_REQUIRED"} else "no_tool_needed",
            "note": "The judge allows delivery within the approved response boundary.",
        }

    debt_kind = list(war_room.get("epistemic_debt", {}).get("debt_kind", []))
    if requires_search and "evidence_gap" not in debt_kind:
        debt_kind.append("evidence_gap")

    next_best_action = str((decision or {}).get("instruction") or "").strip()
    if action == "phase_3" or answer_now:
        next_best_action = "Deliver the approved answer now."
    elif action == "plan_more":
        next_best_action = "Run one more planning cycle before delivery."
    elif action == "warroom_deliberation":
        next_best_action = "Run the WarRoom deliberation lane and return with a user-facing answer seed."
    elif _is_clean_failure_action(action):
        next_best_action = "Explain the limitation clearly and ask for the smallest useful clarification."

    if action == "call_tool":
        why_tool_not_used = "The judge selected a tool because the current evidence boundary was too weak."
    elif action == "warroom_deliberation":
        why_tool_not_used = "The judge selected WarRoom deliberation because tool retrieval would not add the missing kind of value."
    elif action == "plan_more" or _is_clean_failure_action(action):
        why_tool_not_used = "The judge kept the case in planning mode because better grounding was still needed."
    else:
        why_tool_not_used = "The judge determined that another tool call was unnecessary for this turn."

    war_room["freedom"] = freedom
    war_room["epistemic_debt"] = {
        "debt_kind": _dedupe_keep_order(debt_kind),
        "missing_items": list(missing_items)[:4],
        "why_tool_not_used": why_tool_not_used,
        "next_best_action": next_best_action,
    }
    return _upsert_war_room_agent_note(war_room, {
        "agent_name": "-1b",
        "used_freedom": bool(freedom.get("granted")),
        "freedom_scope": str(freedom.get("scope") or "none"),
        "shortage_reason": str((decision or {}).get("memo") or "").strip() or "The judge did not record a detailed shortage memo.",
        "missing_items": list(missing_items)[:4],
        "why_no_tool": war_room["epistemic_debt"]["why_tool_not_used"],
        "allowed_output_boundary": "Only what the judge approved may reach phase_3." + (f" Judge notes: {' / '.join(judge_notes[:2])}" if judge_notes else ""),
    })


def _war_room_packet_for_prompt(war_room: dict):
    normalized = _normalize_war_room_state(war_room)
    try:
        return json.dumps(normalized, ensure_ascii=False, indent=2)
    except TypeError:
        return str(normalized)


__all__ = [
    "_derive_war_room_operating_contract",
    "_empty_war_room_operating_contract",
    "_empty_war_room_state",
    "_normalize_war_room_operating_contract",
    "_normalize_war_room_state",
    "_upsert_war_room_agent_note",
    "_war_room_after_advocate",
    "_war_room_after_judge",
    "_war_room_from_critic",
    "_war_room_missing_items_from_analysis",
    "_war_room_packet_for_prompt",
]
