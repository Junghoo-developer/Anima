"""Strategy payload normalization helpers.

This module used to synthesize direct response strategies from deterministic
turn-family heuristics. In thin-controller mode it must not decide user meaning
or write answer seeds. It now only preserves/normalizes strategist payload shape.
"""

import json
from typing import Callable


def ensure_social_turn_strategist_delivery(
    strategist_payload: dict,
    user_input: str,
    recent_context: str,
    working_memory: dict,
    analysis_data: dict,
    *,
    normalize_action_plan: Callable[[dict], dict],
    normalize_short_string_list: Callable[..., list],
    has_meaningful_strategy: Callable[[dict], bool],
    has_meaningful_delivery_seed: Callable[[str, str], bool],
    looks_like_generic_non_answer_text: Callable[[str], bool],
    looks_like_user_parroting_report: Callable[[str, str], bool],
    is_social_repair_turn: Callable[[str, str, dict], bool],
    is_casual_social_turn: Callable[[str], bool],
    is_persona_preference_turn: Callable[[str], bool],
    is_retry_previous_answer_turn: Callable[[str, str, dict], bool],
    is_directive_or_correction_turn: Callable[[str], bool],
    recent_context_last_assistant_turn: Callable[[str], str],
    social_repair_strategy: Callable[[str, str, dict], dict],
    persona_preference_strategy: Callable[[str, dict], dict],
    social_turn_strategy: Callable[[str], dict],
):
    del (
        analysis_data,
        normalize_short_string_list,
        has_meaningful_strategy,
        has_meaningful_delivery_seed,
        looks_like_generic_non_answer_text,
        looks_like_user_parroting_report,
        is_social_repair_turn,
        is_casual_social_turn,
        is_persona_preference_turn,
        is_retry_previous_answer_turn,
        is_directive_or_correction_turn,
        recent_context_last_assistant_turn,
        social_repair_strategy,
        persona_preference_strategy,
        social_turn_strategy,
    )
    if not isinstance(strategist_payload, dict):
        strategist_payload = {}

    normalized = json.loads(json.dumps(strategist_payload, ensure_ascii=False))
    normalized["action_plan"] = normalize_action_plan(normalized.get("action_plan", {}))
    response_strategy = normalized.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        normalized["response_strategy"] = {}
    return normalized


def ensure_direct_delivery_response_strategy(
    strategist_payload: dict,
    user_input: str,
    recent_context: str,
    working_memory: dict,
    analysis_data: dict,
    start_gate_review: dict | None = None,
    *,
    has_meaningful_strategy: Callable[[dict], bool],
    has_usable_response_seed: Callable[[dict, str], bool],
    normalize_action_plan: Callable[[dict], dict],
    normalize_operation_plan: Callable[[dict], dict],
    empty_operation_plan: Callable[[], dict],
    derive_operation_plan: Callable[..., dict],
    fallback_response_strategy: Callable[[dict], dict],
    minimal_direct_dialogue_strategy: Callable[[str, dict], dict],
    normalize_short_string_list: Callable[..., list],
):
    del (
        fallback_response_strategy,
        minimal_direct_dialogue_strategy,
        normalize_short_string_list,
    )
    if not isinstance(strategist_payload, dict):
        strategist_payload = {}

    normalized = json.loads(json.dumps(strategist_payload, ensure_ascii=False))
    response_strategy = normalized.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    if has_meaningful_strategy(response_strategy) and has_usable_response_seed(response_strategy, user_input):
        return normalized

    action_plan = normalize_action_plan(normalized.get("action_plan", {}))
    operation_plan = normalize_operation_plan(normalized.get("operation_plan", {}))
    if not operation_plan or operation_plan == empty_operation_plan():
        operation_plan = derive_operation_plan(
            user_input,
            analysis_data,
            action_plan,
            response_strategy,
            working_memory,
            recent_context,
            start_gate_review if isinstance(start_gate_review, dict) else {},
        )

    if str(operation_plan.get("plan_type") or "").strip() != "direct_delivery":
        normalized["action_plan"] = action_plan
        normalized["operation_plan"] = operation_plan
        return normalized
    normalized["action_plan"] = action_plan
    normalized["operation_plan"] = operation_plan
    return normalized
