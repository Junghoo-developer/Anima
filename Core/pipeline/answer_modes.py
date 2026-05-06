"""Answer-mode policy helpers for the field loop.

The answer-mode policy distinguishes public parametric knowledge, current-turn
grounding, and grounded memory recall. This module keeps the existing policy
shape while moving the cluster out of Core.nodes.
"""

from __future__ import annotations

import unicodedata
from typing import Callable


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


def answer_mode_policy_for_turn(
    user_input: str,
    recent_context: str = "",
    goal_contract: dict | None = None,
    *,
    is_memory_state_disclosure_turn: Callable[[str], bool],
    looks_like_current_turn_memory_story_share: Callable[[str], bool],
    looks_like_memo_recall_turn: Callable[[str], bool],
    extract_explicit_search_keyword: Callable[[str], str],
    extract_artifact_hint: Callable[[str], str],
    is_recent_dialogue_review_turn: Callable[[str, str], bool],
    is_assistant_investigation_request_turn: Callable[[str], bool],
):
    del goal_contract
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    lowered = text.lower()
    if not text:
        return {
            "question_class": "empty_turn",
            "preferred_answer_mode": "generic_dialogue",
            "grounded_delivery_required": False,
            "parametric_knowledge_allowed": False,
            "current_turn_grounding_ready": False,
        }

    if is_memory_state_disclosure_turn(text):
        return {
            "question_class": "current_turn_memory_state_disclosure",
            "preferred_answer_mode": "current_turn_grounding",
            "grounded_delivery_required": False,
            "parametric_knowledge_allowed": False,
            "current_turn_grounding_ready": True,
        }

    teaching_markers = [
        " is ",
        " are ",
        " means ",
        "\uc740 ",
        "\ub294 ",
        "\uc774\ub2e4",
        "\uc57c",
        "\ub77c\uace0",
    ]
    if looks_like_current_turn_memory_story_share(text) or (
        "?" not in text and any(marker in lowered for marker in teaching_markers)
    ):
        return {
            "question_class": "current_turn_teaching",
            "preferred_answer_mode": "current_turn_grounding",
            "grounded_delivery_required": False,
            "parametric_knowledge_allowed": False,
            "current_turn_grounding_ready": True,
        }

    explicit_grounding = bool(
        looks_like_memo_recall_turn(text)
        or extract_explicit_search_keyword(text)
        or extract_artifact_hint(text)
        or is_recent_dialogue_review_turn(text, recent_context)
        or is_assistant_investigation_request_turn(text)
    )
    if explicit_grounding:
        return {
            "question_class": "grounded_memory_recall" if looks_like_memo_recall_turn(text) else "grounded_recall_or_review",
            "preferred_answer_mode": "grounded_answer",
            "grounded_delivery_required": True,
            "parametric_knowledge_allowed": False,
            "current_turn_grounding_ready": False,
        }

    general_ask = any(marker in lowered for marker in [
        "who",
        "what",
        "explain",
        "describe",
        "relationship",
        "\ub4f1\uc7a5\uc778\ubb3c",
        "\uc8fc\uc778\uacf5",
        "\ub204\uad6c",
        "\ubb34\uc5c7",
        "\uc124\uba85",
        "\uc54c\ub824",
        "\ub300\ud574",
    ])
    if general_ask:
        relation_ask = any(marker in lowered for marker in ["relationship", "relation", "between", "\uad00\uacc4"])
        return {
            "question_class": "public_relation_inference" if relation_ask else "public_knowledge_explainer",
            "preferred_answer_mode": "public_parametric_knowledge",
            "grounded_delivery_required": False,
            "parametric_knowledge_allowed": True,
            "current_turn_grounding_ready": False,
        }

    return {
        "question_class": "generic_dialogue",
        "preferred_answer_mode": "generic_dialogue",
        "grounded_delivery_required": False,
        "parametric_knowledge_allowed": False,
        "current_turn_grounding_ready": False,
    }


def answer_mode_policy_from_state(
    state: dict | None,
    analysis_data: dict | None = None,
    *,
    answer_mode_policy_for_turn: Callable[..., dict],
):
    state = state if isinstance(state, dict) else {}
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    for candidate in (
        state.get("answer_mode_policy"),
        (state.get("start_gate_contract", {}) if isinstance(state.get("start_gate_contract", {}), dict) else {}).get("answer_mode_policy"),
        (state.get("start_gate_switches", {}) if isinstance(state.get("start_gate_switches", {}), dict) else {}).get("answer_mode_policy"),
    ):
        if isinstance(candidate, dict) and candidate:
            return dict(candidate)
    user_input = str(state.get("user_input") or "")
    recent_context = str(state.get("recent_context") or "")
    goal_contract = analysis_data.get("goal_contract", {}) if isinstance(analysis_data, dict) else {}
    if not isinstance(goal_contract, dict):
        goal_contract = {}
    return answer_mode_policy_for_turn(user_input, recent_context, goal_contract)


def answer_mode_policy_allows_direct_phase3(policy: dict | None):
    packet = policy if isinstance(policy, dict) else {}
    if bool(packet.get("grounded_delivery_required")):
        return False
    if "direct_delivery_allowed" in packet:
        return bool(packet.get("direct_delivery_allowed"))
    return str(packet.get("preferred_answer_mode") or "").strip() in {
        "public_parametric_knowledge",
        "current_turn_grounding",
    }


def response_strategy_from_answer_mode_policy(
    user_input: str,
    policy: dict | None,
    current_turn_facts: list[str] | None = None,
):
    packet = policy if isinstance(policy, dict) else {}
    preferred_mode = str(packet.get("preferred_answer_mode") or "").strip()
    question_class = str(packet.get("question_class") or "generic_dialogue").strip() or "generic_dialogue"
    facts = _dedupe_keep_order([str(fact).strip() for fact in (current_turn_facts or []) if str(fact).strip()])[:4]
    user_text = str(user_input or "").strip()

    if preferred_mode == "public_parametric_knowledge":
        return {
            "reply_mode": "grounded_answer",
            "delivery_freedom_mode": "supportive_free",
            "answer_goal": "Answer the public-knowledge question directly without forcing private-memory retrieval.",
            "tone_strategy": "Natural, direct, and concise. Use public knowledge plainly and do not mention retrieval failure.",
            "evidence_brief": f"Answer mode policy: {question_class}; public parametric knowledge is allowed for this turn.",
            "reasoning_brief": "The user is asking about a public topic, not asking for personal memory or a stored source.",
            "direct_answer_seed": "",
            "must_include_facts": [],
            "must_avoid_claims": [
                "Do not claim the answer came from stored memory or retrieved sources.",
                "Do not open a memory-search loop unless the user explicitly asks for memory, search, or prior conversation.",
                "Do not lead with 'I cannot confirm from memory' for broad public-knowledge topics.",
                "Do not invent named entities, character names, locations, or Korean localizations when answering from public knowledge.",
                "Do not treat a previous assistant public-knowledge answer as evidence when the user challenges it.",
            ],
            "answer_outline": [
                "Answer the user's public-knowledge question directly.",
                "Use retrieved or current-turn facts only as optional supporting material if present.",
                "For named lists, include only high-confidence canonical names and omit uncertain names.",
                "Keep uncertainty honest without turning it into a retrieval failure.",
            ],
            "uncertainty_policy": "Use general public knowledge, but for named entities say you are unsure instead of inventing roles, locations, or names.",
        }

    if preferred_mode == "current_turn_grounding":
        return {
            "reply_mode": "grounded_answer",
            "delivery_freedom_mode": "grounded",
            "answer_goal": "Use the facts supplied in the current user turn as admissible grounding for the answer.",
            "tone_strategy": "Direct and natural. Treat the user's provided fact as the local source unless contradicted later.",
            "evidence_brief": " / ".join(facts) if facts else f"Current user turn: {user_text}",
            "reasoning_brief": "The current turn itself supplies enough admissible material to answer without a memory search.",
            "direct_answer_seed": "",
            "must_include_facts": facts,
            "must_avoid_claims": [
                "Do not discard user-provided current-turn facts just because they were not retrieved from memory.",
                "Do not claim the fact is stored memory unless it was actually retrieved.",
                "Do not turn the current-turn teaching fact into a clean_failure fallback.",
            ],
            "answer_outline": [
                "Use the user-provided fact first.",
                "Answer the immediate implication of that fact.",
                "Mark uncertainty only outside the supplied fact.",
            ],
            "uncertainty_policy": "The current turn can ground the local answer; do not overextend beyond it.",
        }

    return {}


def turn_allows_parametric_knowledge_blend(
    user_input: str,
    recent_context: str = "",
    *,
    answer_mode_policy_for_turn: Callable[..., dict],
):
    policy = answer_mode_policy_for_turn(user_input, recent_context)
    return bool(policy.get("parametric_knowledge_allowed"))


def extract_current_turn_grounding_facts(
    user_input: str,
    contract: dict | None = None,
    *,
    is_memory_state_disclosure_turn: Callable[[str], bool],
    looks_like_current_turn_memory_story_share: Callable[[str], bool],
    compact_user_facing_summary: Callable[[str, int], str],
):
    del contract
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    if not text:
        return []
    if text.endswith("?") or "?" in text:
        return []
    if is_memory_state_disclosure_turn(text):
        return ["The user says the assistant previous memories were erased or reset before this turn."]
    if looks_like_current_turn_memory_story_share(text):
        return [compact_user_facing_summary(text, 260)]
    lowered = text.lower()
    request_markers = ["who", "what", "why", "how", "explain", "describe", "tell me", "\uc124\uba85", "\ub9d0\ud574", "\uc54c\ub824"]
    if any(marker in lowered for marker in request_markers):
        return []
    if len(text) >= 8:
        return [compact_user_facing_summary(text, 260)]
    return []


__all__ = [
    "answer_mode_policy_allows_direct_phase3",
    "answer_mode_policy_for_turn",
    "answer_mode_policy_from_state",
    "extract_current_turn_grounding_facts",
    "response_strategy_from_answer_mode_policy",
    "turn_allows_parametric_knowledge_blend",
]
