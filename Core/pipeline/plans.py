"""Plan and board normalization helpers for the ANIMA field-loop pipeline.

This module owns structural defaults for operation/action/goal packets. It must
not decide user intent or choose routing; callers provide those meanings and
these helpers only normalize shape, defaults, and bounded list fields.
"""

from __future__ import annotations


STRATEGIST_GOAL_TARGETS = {
    "memory_recall",
    "public_parametric",
    "self_kernel",
    "continuation",
    "feedback",
    "artifact_hint",
    "ambiguous",
}


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


def empty_operation_contract():
    return {
        "operation_kind": "unspecified",
        "target_scope": "",
        "source_lane": "",
        "search_subject": "",
        "missing_slot": "",
        "query_seed_candidates": [],
        "evidence_boundary": "",
        "query_variant": "",
        "novelty_requirement": "",
    }


def empty_operation_plan():
    return {
        "plan_type": "direct_delivery",
        "source_lane": "none",
        "output_act": "answer",
        "user_goal": "",
        "executor_instruction": "",
        "evidence_policy": "Use only the boundary that can be answered in the current turn.",
        "success_criteria": [],
        "rejection_criteria": [],
        "delivery_shape": "direct_answer",
        "confidence": 0.5,
    }


def normalize_operation_plan(plan: dict | None):
    base = empty_operation_plan()
    if not isinstance(plan, dict):
        return base

    plan_type = str(plan.get("plan_type") or "").strip()
    if plan_type not in {
        "direct_delivery",
        "warroom_deliberation",
        "tool_evidence",
        "recent_dialogue_review",
        "raw_source_analysis",
    }:
        plan_type = "direct_delivery"
    base["plan_type"] = plan_type

    source_lane = str(plan.get("source_lane") or "").strip()
    if source_lane not in {
        "none",
        "recent_dialogue_review",
        "field_memo_review",
        "memory_search",
        "scroll_source",
        "artifact_read",
        "warroom",
    }:
        source_lane = {
            "recent_dialogue_review": "recent_dialogue_review",
            "tool_evidence": "memory_search",
            "raw_source_analysis": "artifact_read",
            "warroom_deliberation": "warroom",
        }.get(plan_type, "none")
    base["source_lane"] = source_lane

    output_act = str(plan.get("output_act") or "").strip()
    if output_act not in {
        "answer",
        "summarize",
        "self_critique",
        "diagnose_bug",
        "apologize_and_repair",
        "deliver_findings",
        "answer_identity_slot",
        "answer_memory_recall",
        "answer_narrative_fact",
        "self_analysis_snapshot",
        "execute_game",
        "ask_one_question",
        "propose_next_step",
    }:
        output_act = (
            "summarize"
            if plan_type == "recent_dialogue_review"
            else "deliver_findings"
            if plan_type == "tool_evidence"
            else "answer"
        )
    base["output_act"] = output_act

    for key in ("user_goal", "executor_instruction", "evidence_policy", "delivery_shape"):
        base[key] = str(plan.get(key) or "").strip() or base[key]
    for key in ("success_criteria", "rejection_criteria"):
        values = plan.get(key, [])
        if not isinstance(values, list):
            values = [values]
        base[key] = _dedupe_keep_order([str(item).strip() for item in values if str(item).strip()])[:6]
    try:
        confidence = float(plan.get("confidence", base["confidence"]) or base["confidence"])
    except (TypeError, ValueError):
        confidence = base["confidence"]
    base["confidence"] = max(0.0, min(1.0, confidence))
    return base


def empty_goal_lock():
    return {
        "user_goal_core": "",
        "answer_shape": "direct_answer",
        "must_not_expand_to": [],
    }


def empty_strategist_goal():
    return {
        "user_goal_core": "",
        "answer_mode_target": "ambiguous",
        "success_criteria": [],
        "scope": "narrow",
    }


def normalize_strategist_goal(goal: dict | str | None):
    base = empty_strategist_goal()
    if isinstance(goal, str):
        base["user_goal_core"] = goal.strip()
        return base
    if not isinstance(goal, dict):
        return base

    base["user_goal_core"] = str(goal.get("user_goal_core") or "").strip()

    answer_mode_target = str(goal.get("answer_mode_target") or "").strip()
    if answer_mode_target not in STRATEGIST_GOAL_TARGETS:
        answer_mode_target = "ambiguous"
    base["answer_mode_target"] = answer_mode_target

    success_criteria = goal.get("success_criteria", [])
    if not isinstance(success_criteria, list):
        success_criteria = [success_criteria]
    base["success_criteria"] = _dedupe_keep_order(
        [str(item).strip() for item in success_criteria if str(item).strip()]
    )[:5]

    scope = str(goal.get("scope") or "").strip()
    if scope not in {"narrow", "broad"}:
        scope = "narrow"
    base["scope"] = scope
    return base


def strategist_answer_mode_target_from_policy(policy: dict | None):
    if not isinstance(policy, dict):
        return "ambiguous"
    raw = str(
        policy.get("preferred_answer_mode")
        or policy.get("answer_mode_preference")
        or policy.get("answer_mode_target")
        or policy.get("mode")
        or ""
    ).strip()
    mapping = {
        "grounded_recall": "memory_recall",
        "memory_recall": "memory_recall",
        "grounded_memory_recall": "memory_recall",
        "private_memory_recall": "memory_recall",
        "public_parametric_knowledge": "public_parametric",
        "public_parametric": "public_parametric",
        "self_kernel": "self_kernel",
        "self_identity": "self_kernel",
        "identity_direct": "self_kernel",
        "continuation": "continuation",
        "continue_previous_offer": "continuation",
        "recent_dialogue_review": "continuation",
        "feedback": "feedback",
        "correction_or_feedback": "feedback",
        "artifact_hint": "artifact_hint",
        "artifact_read": "artifact_hint",
    }
    return mapping.get(raw, "ambiguous")


def strategist_goal_from_goal_lock(
    goal_lock: dict | None,
    *,
    answer_mode_target: str = "ambiguous",
    success_criteria: list | None = None,
    scope: str = "narrow",
):
    normalized_lock = normalize_goal_lock(goal_lock if isinstance(goal_lock, dict) else {})
    return normalize_strategist_goal(
        {
            "user_goal_core": normalized_lock.get("user_goal_core", ""),
            "answer_mode_target": answer_mode_target,
            "success_criteria": success_criteria if isinstance(success_criteria, list) else [],
            "scope": scope,
        }
    )


def normalize_goal_lock(goal_lock: dict | None):
    base = empty_goal_lock()
    if not isinstance(goal_lock, dict):
        return base
    base["user_goal_core"] = str(goal_lock.get("user_goal_core") or "").strip()
    answer_shape = str(goal_lock.get("answer_shape") or "").strip()
    if not answer_shape:
        answer_shape = "direct_answer"
    base["answer_shape"] = answer_shape
    must_not_expand_to = goal_lock.get("must_not_expand_to", [])
    if isinstance(must_not_expand_to, list):
        base["must_not_expand_to"] = _dedupe_keep_order(
            [str(item).strip() for item in must_not_expand_to if str(item).strip()]
        )[:5]
    return base


def normalize_convergence_state(value: str):
    normalized = str(value or "").strip()
    if normalized in {"gathering", "synthesizing", "deliverable", "deepen_one_axis"}:
        return normalized
    return "gathering"


def normalize_delivery_readiness(value: str):
    normalized = str(value or "").strip()
    if normalized in {"deliver_now", "need_one_more_source", "need_reframe", "need_targeted_deeper_read"}:
        return normalized
    return "need_reframe"


def normalize_short_string_list(items, limit: int = 3):
    if not isinstance(items, list):
        return []
    return _dedupe_keep_order([str(item).strip() for item in items if str(item).strip()])[:limit]


def normalize_operation_contract(contract: dict | None):
    base = empty_operation_contract()
    if not isinstance(contract, dict):
        return base
    operation_kind = str(contract.get("operation_kind") or "").strip()
    if operation_kind not in {
        "unspecified",
        "search_new_source",
        "read_same_source_deeper",
        "review_personal_history",
        "extract_feature_summary",
        "compare_with_user_goal",
        "review_recent_dialogue",
        "deliver_now",
    }:
        operation_kind = "unspecified"
    base["operation_kind"] = operation_kind
    base["target_scope"] = str(contract.get("target_scope") or "").strip()
    source_lane = str(contract.get("source_lane") or "").strip()
    if source_lane not in {
        "",
        "none",
        "field_memo",
        "memory",
        "diary",
        "gemini_chat",
        "songryeon_chat",
        "artifact",
        "db_schema",
        "recent_context",
        "capability_boundary",
        "mixed_private_sources",
    }:
        source_lane = ""
    base["source_lane"] = source_lane
    base["search_subject"] = str(contract.get("search_subject") or "").strip()
    base["missing_slot"] = str(contract.get("missing_slot") or "").strip()
    seeds = contract.get("query_seed_candidates", [])
    if not isinstance(seeds, list):
        seeds = [seeds] if str(seeds or "").strip() else []
    base["query_seed_candidates"] = _dedupe_keep_order(
        [str(seed).strip() for seed in seeds if str(seed).strip()]
    )[:5]
    base["evidence_boundary"] = str(contract.get("evidence_boundary") or "").strip()
    base["query_variant"] = str(contract.get("query_variant") or "").strip()
    base["novelty_requirement"] = str(contract.get("novelty_requirement") or "").strip()
    return base


def empty_action_plan():
    return {
        "current_step_goal": "",
        "required_tool": "",
        "next_steps_forecast": [],
        "operation_contract": empty_operation_contract(),
    }


def normalize_action_plan(action_plan: dict | None):
    base = empty_action_plan()
    if not isinstance(action_plan, dict):
        return base
    base["current_step_goal"] = str(action_plan.get("current_step_goal") or "").strip()
    base["required_tool"] = str(action_plan.get("required_tool") or "").strip()
    next_steps = action_plan.get("next_steps_forecast", [])
    if isinstance(next_steps, list):
        base["next_steps_forecast"] = _dedupe_keep_order([str(step).strip() for step in next_steps if str(step).strip()])[:3]
    base["operation_contract"] = normalize_operation_contract(action_plan.get("operation_contract", {}))
    return base


def empty_critic_report():
    return {
        "situational_brief": "",
        "analytical_thought": "",
        "source_judgments": [],
        "open_questions": [],
        "objections": [],
        "recommended_action": "insufficient_evidence",
    }


def empty_advocate_report():
    return {
        "defense_strategy": "",
        "summary_of_position": "",
        "supported_pair_ids": [],
        "response_contract": {},
    }


def empty_verdict_board():
    return {
        "answer_now": False,
        "requires_search": False,
        "approved_fact_ids": [],
        "approved_pair_ids": [],
        "rejected_pair_ids": [],
        "held_pair_ids": [],
        "judge_notes": [],
        "final_answer_brief": "",
    }


__all__ = [
    "empty_operation_contract",
    "empty_operation_plan",
    "normalize_operation_plan",
    "empty_goal_lock",
    "normalize_goal_lock",
    "empty_strategist_goal",
    "normalize_strategist_goal",
    "strategist_answer_mode_target_from_policy",
    "strategist_goal_from_goal_lock",
    "normalize_convergence_state",
    "normalize_delivery_readiness",
    "normalize_short_string_list",
    "normalize_operation_contract",
    "empty_action_plan",
    "normalize_action_plan",
    "empty_critic_report",
    "empty_advocate_report",
    "empty_verdict_board",
]
