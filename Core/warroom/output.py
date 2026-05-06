import re
import unicodedata
from collections.abc import Callable

from .state import (
    _dedupe_keep_order,
    _normalize_delivery_freedom_mode,
    _normalize_war_room_operating_contract,
)


def _war_room_output_is_usable(war_room_output: dict):
    if not isinstance(war_room_output, dict) or not war_room_output:
        return False
    status = str(war_room_output.get("deliberation_status") or "").strip().upper()
    seed = str(war_room_output.get("usable_answer_seed") or "").strip()
    try:
        confidence = float(war_room_output.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return status == "COMPLETED" and bool(seed) and confidence >= 0.45


def _strip_korean_case_particle(term: str):
    value = str(term or "").strip()
    suffixes = ["\uc740", "\ub294", "\uc774", "\uac00", "\uc744", "\ub97c", "\uc5d0", "\uc5d0\uc11c", "\uc73c\ub85c", "\ub85c"]
    for suffix in suffixes:
        if len(value) > len(suffix) + 1 and value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def _alignment_terms_from_user_input(user_input: str):
    normalized = unicodedata.normalize("NFKC", str(user_input or "").lower())
    tokens = re.findall(r"[A-Za-z0-9_\-]{2,}|[\uac00-\ud7a3]{2,}", normalized)
    stopwords = {"the", "and", "that", "this", "what", "why", "how", "user", "assistant"}
    terms = []
    for token in tokens:
        stripped = _strip_korean_case_particle(token)
        if stripped and stripped not in stopwords and len(stripped) >= 2:
            terms.append(stripped)
    return _dedupe_keep_order(terms)[:12]


def _alignment_term_in_text(term: str, text: str):
    term_value = unicodedata.normalize("NFKC", str(term or "").lower()).strip()
    text_value = unicodedata.normalize("NFKC", str(text or "").lower())
    if not term_value or not text_value:
        return False
    return term_value in text_value


def _war_room_seed_alignment_issue(
    user_input: str,
    war_room_output: dict,
    recent_context: str = "",
    *,
    user_turn_targets_assistant_reply: Callable[[str, str], bool] | None = None,
):
    user_text = str(user_input or "").strip()
    seed_text = str((war_room_output or {}).get("usable_answer_seed") or "").strip()
    if not user_text or not seed_text:
        return ""
    if callable(user_turn_targets_assistant_reply) and user_turn_targets_assistant_reply(user_text, recent_context):
        return ""
    user_terms = _alignment_terms_from_user_input(user_text)
    matched_terms = [term for term in user_terms if _alignment_term_in_text(term, seed_text)]
    if len(user_terms) >= 3 and not matched_terms:
        return "WarRoom seed does not share a concrete anchor with the current user turn."
    return ""


def _build_warroom_answer_seed_packet(
    state: dict,
    *,
    looks_like_generic_non_answer_text: Callable[[str], bool] | None = None,
):
    output = state.get("war_room_output", {}) if isinstance(state, dict) else {}
    if not isinstance(output, dict):
        return {}
    seed = str(output.get("usable_answer_seed") or "").strip()
    if not seed:
        return {}
    if callable(looks_like_generic_non_answer_text) and looks_like_generic_non_answer_text(seed):
        return {}
    return {
        "lane": "warroom",
        "warroom_answer_seed": seed,
        "reasoning_summary": str(output.get("reasoning_summary") or "").strip(),
        "missing_items": output.get("missing_items", []) if isinstance(output.get("missing_items"), list) else [],
        "answer_boundary": "warroom_seed_only: do not expose internal deliberation labels.",
    }


def _response_strategy_from_war_room_output(
    user_input: str,
    war_room_output: dict,
    operation_plan: dict,
    war_room_contract: dict,
    existing_strategy: dict | None = None,
):
    existing_strategy = existing_strategy if isinstance(existing_strategy, dict) else {}
    output = war_room_output if isinstance(war_room_output, dict) else {}
    contract = _normalize_war_room_operating_contract(war_room_contract)
    phase3_handoff = contract.get("phase3_handoff", {}) if isinstance(contract.get("phase3_handoff"), dict) else {}
    speaker_posture = str(phase3_handoff.get("speaker_posture") or "").strip()
    if speaker_posture == "conversation_partner":
        reply_mode = "casual_reaction"
        delivery_mode = "supportive_free"
    elif speaker_posture == "practical_planner":
        reply_mode = "grounded_answer"
        delivery_mode = "proposal"
    else:
        reply_mode = str(existing_strategy.get("reply_mode") or "grounded_answer").strip() or "grounded_answer"
        delivery_mode = _normalize_delivery_freedom_mode(
            str(existing_strategy.get("delivery_freedom_mode") or "").strip(),
            reply_mode=reply_mode,
        )
        if delivery_mode == "grounded":
            delivery_mode = "supportive_free" if operation_plan.get("plan_type") == "warroom_deliberation" else delivery_mode

    missing_items = output.get("missing_items", []) if isinstance(output.get("missing_items"), list) else []
    duty_checklist = output.get("duty_checklist", []) if isinstance(output.get("duty_checklist"), list) else []
    must_avoid = existing_strategy.get("must_avoid_claims", []) if isinstance(existing_strategy.get("must_avoid_claims"), list) else []
    must_avoid.extend([
        "Do not report the user's speech as 'the user said...' instead of answering.",
        "Do not expose lanes, judges, internal packets, or OperationPlan.",
        "Do not fall into long generic limitation text.",
    ])

    return {
        "reply_mode": reply_mode,
        "delivery_freedom_mode": delivery_mode,
        "answer_goal": str(operation_plan.get("user_goal") or existing_strategy.get("answer_goal") or "Deliver the current request within the allowed reasoning boundary.").strip(),
        "tone_strategy": str(existing_strategy.get("tone_strategy") or "Natural, direct, and free of internal report tone.").strip(),
        "evidence_brief": str(output.get("reasoning_summary") or operation_plan.get("evidence_policy") or "Use free reasoning to shape the answer boundary without pretending it is evidence.").strip(),
        "reasoning_brief": str(output.get("reasoning_summary") or "WarRoom decided free reasoning matters more than a tool for this current turn.").strip(),
        "direct_answer_seed": str(output.get("usable_answer_seed") or existing_strategy.get("direct_answer_seed") or "").strip(),
        "must_include_facts": _dedupe_keep_order([
            str(operation_plan.get("user_goal") or "").strip(),
            *[str(item).strip() for item in duty_checklist[:2] if str(item).strip()],
        ]),
        "must_avoid_claims": _dedupe_keep_order([str(item).strip() for item in must_avoid if str(item).strip()]),
        "answer_outline": [
            "Answer the user's question directly.",
            "If needed, explain the reasoning in one or two sentences.",
            "Name missing gaps only when truly necessary.",
        ],
        "uncertainty_policy": (
            "Missing gap: " + " / ".join(str(item).strip() for item in missing_items[:2] if str(item).strip())
            if missing_items
            else "Do not present speculation as fact, but do not dodge the answer itself."
        ),
    }


def _fallback_war_room_output(
    user_input: str,
    operation_plan: dict,
    response_strategy: dict,
    war_room_contract: dict,
    recent_context: str = "",
    *,
    looks_like_generic_non_answer_text: Callable[[str], bool] | None = None,
    looks_like_user_parroting_report: Callable[[str, str], bool] | None = None,
    war_room_seed_alignment_issue: Callable[[str, dict, str], str] | None = None,
    is_emotional_vent_turn: Callable[..., bool] | None = None,
):
    seed = str(response_strategy.get("direct_answer_seed") or "").strip()

    def _seed_has_alignment_issue(candidate: str) -> bool:
        if not callable(war_room_seed_alignment_issue):
            return False
        return bool(war_room_seed_alignment_issue(
            user_input,
            {"deliberation_status": "COMPLETED", "usable_answer_seed": candidate, "confidence": 1.0},
            recent_context,
        ))

    if (
        not seed
        or (callable(looks_like_generic_non_answer_text) and looks_like_generic_non_answer_text(seed))
        or (callable(looks_like_user_parroting_report) and looks_like_user_parroting_report(seed, user_input))
        or _seed_has_alignment_issue(seed)
    ):
        seed = ""
    if (
        not seed
        or (callable(looks_like_generic_non_answer_text) and looks_like_generic_non_answer_text(seed))
        or _seed_has_alignment_issue(seed)
    ):
        if callable(is_emotional_vent_turn) and is_emotional_vent_turn(user_input, recent_context, {}):
            seed = (
                "\uadf8\uac74 \uc9c4\uc9dc \ub2f5\ub2f5\ud560 \ub9cc\ud574. "
                "\ub0b4\uac00 \uc9c0\uae08 \ubc18\ubcf5\ud558\uac70\ub098 \ud5db\ub3cc\uace0 \uc788\ub2e4\ub294 \uc810\ubd80\ud130 \uc778\uc815\ud558\uace0, "
                "\ubc14\ub85c \ud604\uc7ac \ubb38\uc81c\uc5d0 \ubd99\uc5b4\uc11c \ub9d0\ud560\uac8c."
            )
        else:
            seed = (
                "\uc9c0\uae08\uc740 \ub2f5\uc744 \uafb8\uba70\ub0b4\uae30\ubcf4\ub2e4, "
                "\ub0b4\uac00 \ud655\uc2e4\ud788 \uc544\ub294 \uac83\uacfc \ubd80\uc871\ud55c \uac83\uc744 \uc9e7\uac8c \uac00\ub974\ub294 \uac8c \ub9de\uc544."
            )
    contract = _normalize_war_room_operating_contract(war_room_contract)
    missing = contract.get("deficiency", {}).get("missing_items", []) if isinstance(contract.get("deficiency"), dict) else []
    return {
        "deliberation_status": "COMPLETED",
        "reasoning_summary": str(contract.get("reason", {}).get("why_discussion_is_useful") or operation_plan.get("evidence_policy") or "This turn needs free reasoning without a tool.").strip(),
        "usable_answer_seed": seed,
        "duty_checklist": [
            "Answer the user's question directly.",
            "Do not conflate fact and interpretation.",
            "Avoid internal report tone.",
        ],
        "missing_items": missing if isinstance(missing, list) else [],
        "confidence": 0.62,
    }
