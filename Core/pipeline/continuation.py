"""Continuation and short-term conversational context helpers."""

import re
import unicodedata
from typing import Callable


def _dedupe_keep_order(items):
    seen = set()
    result = []
    for item in items:
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def has_substantive_dialogue_anchor(user_input: str):
    normalized = unicodedata.normalize("NFKC", str(user_input or "").strip())
    if not normalized:
        return False
    content = re.sub(r"[\s!?.~,\b\"'<>]+", "", normalized)
    if len(content) < 8:
        return False
    if len(normalized) > 35:
        return True
    if re.search(r"\d", normalized):
        return True
    word_like = re.findall(r"[A-Za-z0-9_\-]{2,}|[\uac00-\ud7a3]{2,}", normalized.lower())
    return len(word_like) >= 3


def is_short_affirmation(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip().lower())
    if not text:
        return False
    compact = re.sub(r"[\s!~.]+", "", text)
    affirmations = {
        "ok",
        "okay",
        "yes",
        "yep",
        "\uc751",
        "\uc74c",
        "\uadf8\ub798",
        "\uc88b\uc544",
        "\uc88b\uc2b5\ub2c8\ub2e4",
        "\u3131\u3131",
        "\u3147\u3147",
    }
    return compact in affirmations


def working_memory_pending_dialogue_act(working_memory: dict):
    if not isinstance(working_memory, dict):
        return {}
    dialogue_state = working_memory.get("dialogue_state", {})
    if not isinstance(dialogue_state, dict):
        return {}
    act = dialogue_state.get("pending_dialogue_act", {})
    if not isinstance(act, dict):
        return {}
    kind = str(act.get("kind") or "none").strip()
    target = str(act.get("target") or "").strip()
    try:
        confidence = float(act.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    try:
        expires_after_turns = int(act.get("expires_after_turns", 0) or 0)
    except (TypeError, ValueError):
        expires_after_turns = 0
    if kind == "none" or not target or confidence < 0.35 or expires_after_turns <= 0:
        return {}
    return {
        "kind": kind,
        "target": target,
        "expected_user_responses": [
            str(item).strip()
            for item in (act.get("expected_user_responses", []) if isinstance(act.get("expected_user_responses"), list) else [])
            if str(item).strip()
        ],
        "confidence": confidence,
        "expires_after_turns": expires_after_turns,
    }


def working_memory_expects_continuation(working_memory: dict):
    if not isinstance(working_memory, dict):
        return False
    dialogue_state = working_memory.get("dialogue_state", {})
    if not isinstance(dialogue_state, dict):
        return False
    if working_memory_pending_dialogue_act(working_memory):
        return True
    return bool(dialogue_state.get("continuation_expected"))


def working_memory_active_task(working_memory: dict):
    if not isinstance(working_memory, dict):
        return ""
    dialogue_state = working_memory.get("dialogue_state", {})
    if isinstance(dialogue_state, dict):
        active_task = str(dialogue_state.get("active_task") or "").strip()
        if active_task:
            return active_task
    return ""


def working_memory_active_offer(working_memory: dict):
    if not isinstance(working_memory, dict):
        return ""
    dialogue_state = working_memory.get("dialogue_state", {})
    if not isinstance(dialogue_state, dict):
        return ""
    return str(dialogue_state.get("active_offer") or "").strip()


def pending_dialogue_act_anchor(working_memory: dict):
    act = working_memory_pending_dialogue_act(working_memory)
    if not act:
        return "", ""
    return str(act.get("target") or "").strip(), f"pending_dialogue_act:{act.get('kind') or 'unknown'}"


def pending_dialogue_act_accepts_current_turn(user_input: str, working_memory: dict):
    act = working_memory_pending_dialogue_act(working_memory)
    if not act:
        return False
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    compact = re.sub(r"\s+", "", text)
    expected = [
        unicodedata.normalize("NFKC", str(item or "").strip()).lower()
        for item in act.get("expected_user_responses", [])
        if str(item or "").strip()
    ]
    expected_compact = [re.sub(r"\s+", "", item) for item in expected if item]
    return bool(text and (text in expected or compact in expected_compact))


def working_memory_writer_packet(working_memory: dict):
    if not isinstance(working_memory, dict):
        return {}
    writer = working_memory.get("memory_writer", {})
    return writer if isinstance(writer, dict) else {}


def llm_short_term_context_material(
    working_memory: dict,
    *,
    looks_like_internal_phase3_seed: Callable[[str], bool],
    compact_user_facing_summary: Callable[[str, int], str],
):
    writer = working_memory_writer_packet(working_memory)
    pending = working_memory_pending_dialogue_act(working_memory)
    materials = []
    for key in (
        "assistant_obligation_next_turn",
        "unresolved_user_request",
        "active_topic",
        "short_term_context",
    ):
        text = str(writer.get(key) or "").strip()
        if text and not looks_like_internal_phase3_seed(text):
            materials.append(text)
    if pending.get("target"):
        materials.insert(0, str(pending.get("target") or "").strip())
    return _dedupe_keep_order([compact_user_facing_summary(item, 240) for item in materials if item])[:5]


def short_term_context_response_strategy(
    user_input: str,
    working_memory: dict,
    *,
    looks_like_internal_phase3_seed: Callable[[str], bool],
    compact_user_facing_summary: Callable[[str, int], str],
):
    materials = llm_short_term_context_material(
        working_memory,
        looks_like_internal_phase3_seed=looks_like_internal_phase3_seed,
        compact_user_facing_summary=compact_user_facing_summary,
    )
    if not materials:
        return {}
    pending = working_memory_pending_dialogue_act(working_memory)
    obligation = str(working_memory_writer_packet(working_memory).get("assistant_obligation_next_turn") or "").strip()
    seed = obligation if obligation and not looks_like_internal_phase3_seed(obligation) else materials[0]
    return {
        "reply_mode": "continue_previous_offer" if pending else "grounded_answer",
        "delivery_freedom_mode": "supportive_free",
        "answer_goal": "Use the LLM-authored short-term context to answer the current turn without repeating the previous answer.",
        "tone_strategy": "Natural and direct. Resolve the pending conversational obligation before adding new explanation.",
        "evidence_brief": " / ".join(materials[:3]),
        "reasoning_brief": "WorkingMemoryWriter supplied short-term context for this follow-up; treat it as conversational context, not durable fact.",
        "direct_answer_seed": seed,
        "must_include_facts": materials[:3],
        "must_avoid_claims": [
            "Do not repeat the previous assistant answer as if it were a new answer.",
            "Do not answer only the raw short acknowledgement when a pending obligation exists.",
            "Do not claim the short-term context is a retrieved long-term memory.",
            "Do not expose WorkingMemory, pending_dialogue_act, or internal contracts.",
        ],
        "answer_outline": [
            "Respond to the user's current utterance in the context of the previous turn.",
            "Fulfill the pending obligation or unresolved request if one exists.",
            "Keep it brief unless the user asked for detail.",
        ],
        "uncertainty_policy": "If the short-term context is not enough, ask one concrete clarifying question rather than restarting the loop.",
    }


def short_term_context_strategy_is_usable(
    response_strategy: dict | None,
    user_input: str,
    working_memory: dict,
    *,
    looks_like_internal_phase3_seed: Callable[[str], bool],
    compact_user_facing_summary: Callable[[str, int], str],
    has_meaningful_delivery_seed: Callable[[str, str], bool],
):
    strategy = response_strategy if isinstance(response_strategy, dict) else {}
    if not strategy:
        return False
    materials = llm_short_term_context_material(
        working_memory,
        looks_like_internal_phase3_seed=looks_like_internal_phase3_seed,
        compact_user_facing_summary=compact_user_facing_summary,
    )
    if not materials:
        return False
    reasoning = str(strategy.get("reasoning_brief") or "").strip()
    answer_goal = str(strategy.get("answer_goal") or "").strip()
    seed = str(strategy.get("direct_answer_seed") or "").strip()
    if (
        "WorkingMemoryWriter supplied short-term context" not in reasoning
        and "LLM-authored short-term context" not in answer_goal
        and seed not in materials
    ):
        return False
    return has_meaningful_delivery_seed(seed, user_input) or bool(strategy.get("must_include_facts"))


def working_memory_direct_answer_seed(working_memory: dict):
    if not isinstance(working_memory, dict):
        return ""
    response_contract = working_memory.get("response_contract", {})
    if not isinstance(response_contract, dict):
        return ""
    return str(response_contract.get("direct_answer_seed") or "").strip()


def working_memory_pending_question(working_memory: dict):
    if not isinstance(working_memory, dict):
        return ""
    dialogue_state = working_memory.get("dialogue_state", {})
    if not isinstance(dialogue_state, dict):
        return ""
    return str(dialogue_state.get("pending_question") or "").strip()


def working_memory_last_assistant_answer(working_memory: dict):
    if not isinstance(working_memory, dict):
        return ""
    last_turn = working_memory.get("last_turn", {})
    if not isinstance(last_turn, dict):
        return ""
    return str(last_turn.get("assistant_answer") or "").strip()


def recent_context_last_assistant_turn(
    recent_context: str,
    *,
    extract_recent_raw_turns_from_context: Callable[..., list],
):
    turns = extract_recent_raw_turns_from_context(recent_context, max_turns=4)
    for turn in reversed(turns):
        if not isinstance(turn, dict):
            continue
        if str(turn.get("role") or "").strip().lower() != "assistant":
            continue
        content = str(turn.get("content") or "").strip()
        if content:
            return content
    return ""


def previous_delivery_anchor(
    user_input: str,
    recent_context: str,
    working_memory: dict,
    *,
    extract_recent_raw_turns_from_context: Callable[..., list],
    is_generic_continue_seed: Callable[[str], bool],
):
    pending_anchor, pending_source = pending_dialogue_act_anchor(working_memory)
    if pending_anchor:
        return pending_anchor, pending_source

    active_offer = working_memory_active_offer(working_memory)
    if active_offer and not is_generic_continue_seed(active_offer):
        return active_offer, "active_offer"

    direct_answer_seed = working_memory_direct_answer_seed(working_memory)
    if direct_answer_seed and not is_generic_continue_seed(direct_answer_seed):
        return direct_answer_seed, "direct_answer_seed"

    pending_question = working_memory_pending_question(working_memory)
    if pending_question:
        return pending_question, "pending_question"

    last_assistant = working_memory_last_assistant_answer(working_memory)
    if last_assistant:
        return last_assistant, "last_assistant_answer"

    assistant_turn = recent_context_last_assistant_turn(
        recent_context,
        extract_recent_raw_turns_from_context=extract_recent_raw_turns_from_context,
    )
    if assistant_turn:
        return assistant_turn, "recent_assistant_turn"

    if active_offer:
        return active_offer, "active_offer"

    if direct_answer_seed:
        return direct_answer_seed, "direct_answer_seed"

    active_task = working_memory_active_task(working_memory)
    if active_task and active_task != str(user_input or "").strip():
        return active_task, "active_task"

    return "", ""


def is_retry_previous_answer_turn(
    user_input: str,
    recent_context: str,
    working_memory: dict,
    *,
    extract_artifact_hint: Callable[[str], object],
    extract_explicit_search_keyword: Callable[[str], object],
    is_assistant_investigation_request_turn: Callable[[str], bool],
    is_recent_dialogue_review_turn: Callable[[str, str], bool],
    is_directive_or_correction_turn: Callable[[str], bool],
    extract_recent_raw_turns_from_context: Callable[..., list],
    is_generic_continue_seed: Callable[[str], bool],
):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    if extract_artifact_hint(text) or extract_explicit_search_keyword(text):
        return False
    if is_assistant_investigation_request_turn(text) or is_recent_dialogue_review_turn(text, recent_context):
        return False
    previous_anchor, _ = previous_delivery_anchor(
        user_input,
        recent_context,
        working_memory,
        extract_recent_raw_turns_from_context=extract_recent_raw_turns_from_context,
        is_generic_continue_seed=is_generic_continue_seed,
    )
    if not previous_anchor:
        return False
    retry_markers = ["retry", "again", "redo", "say it again", "\ub2e4\uc2dc", "\uc9c1\uc811"]
    return is_directive_or_correction_turn(text) or any(marker in text for marker in retry_markers)


def working_memory_temporal_context(working_memory: dict):
    if not isinstance(working_memory, dict):
        return {}
    temporal = working_memory.get("temporal_context", {})
    return temporal if isinstance(temporal, dict) else {}


def temporal_context_prefers_current_input(working_memory: dict):
    temporal = working_memory_temporal_context(working_memory)
    topic_reset = float(temporal.get("topic_reset_confidence", 0.0) or 0.0)
    carry_over = float(temporal.get("carry_over_strength", 0.0) or 0.0)
    topic_shift = float(temporal.get("topic_shift_score", 0.0) or 0.0)
    return topic_reset >= 0.55 or topic_shift >= 0.65 or carry_over <= 0.25


def temporal_context_allows_carry_over(working_memory: dict):
    temporal = working_memory_temporal_context(working_memory)
    if not temporal:
        return True
    return bool(temporal.get("carry_over_allowed")) and not temporal_context_prefers_current_input(working_memory)


def recent_hint_budget_from_working_memory(working_memory: dict):
    temporal = working_memory_temporal_context(working_memory)
    if not temporal:
        return 2
    topic_reset = float(temporal.get("topic_reset_confidence", 0.0) or 0.0)
    carry_over = float(temporal.get("carry_over_strength", 0.0) or 0.0)
    topic_shift = float(temporal.get("topic_shift_score", 0.0) or 0.0)
    if topic_reset >= 0.75 or carry_over <= 0.2:
        return 0
    if topic_shift >= 0.6:
        return 1
    return 2


def recent_context_invites_continuation(recent_context: str):
    text = str(recent_context or "").strip()
    if not text:
        return False
    tail = unicodedata.normalize("NFKC", text[-500:]).lower()
    markers = ["?", "tell me", "explain", "continue", "more", "\ub9d0\ud574", "\uc124\uba85", "\uacc4\uc18d"]
    return any(marker in tail for marker in markers)


def is_followup_ack_turn(user_input: str, recent_context: str):
    return is_short_affirmation(user_input) and recent_context_invites_continuation(recent_context)


def base_followup_context_expected(
    user_input: str,
    recent_context: str,
    working_memory: dict,
    *,
    is_followup_offer_acceptance_turn: Callable[[str, dict], bool],
):
    if temporal_context_prefers_current_input(working_memory):
        return False
    if is_followup_offer_acceptance_turn(user_input, working_memory):
        return True
    return is_short_affirmation(user_input) and (
        recent_context_invites_continuation(recent_context)
        or working_memory_expects_continuation(working_memory)
    )


def casual_social_user_facing_seed(user_input: str):
    text = str(user_input or "").strip()
    normalized = unicodedata.normalize("NFKC", text).lower()
    if any(marker in normalized for marker in ["hello", "hi", "yo", "\uc548\ub155"]):
        return "Hey, I am here."
    if any(marker in normalized for marker in ["thanks", "thank", "\uace0\ub9c8\uc6cc", "\uac10\uc0ac"]):
        return "Thanks. I will keep going naturally."
    if normalized in {"ok", "okay", "yes", "yep", "\uc751", "\uadf8\ub798", "\uc88b\uc544", "\u3131\u3131"}:
        return "Okay, I will continue."
    return "I hear you."


def social_turn_strategy(user_input: str):
    user_text = str(user_input or "").strip()
    return {
        "reply_mode": "casual_reaction",
        "delivery_freedom_mode": "supportive_free",
        "answer_goal": "Respond naturally to the light social turn.",
        "tone_strategy": "Warm, brief, and conversational.",
        "evidence_brief": f"Current user turn: {user_text}",
        "reasoning_brief": "This is a light social turn, so do not convert it into analysis or retrieval.",
        "direct_answer_seed": casual_social_user_facing_seed(user_text),
        "must_include_facts": [f"Current user turn: {user_text}"] if user_text else [],
        "must_avoid_claims": [
            "Do not call tools for a light social turn.",
            "Do not expose internal workflow terms.",
        ],
        "answer_outline": ["Reply naturally and briefly."],
        "uncertainty_policy": "Keep it simple when there is no factual claim to verify.",
    }


def user_turn_targets_assistant_reply(
    text: str,
    recent_context: str = "",
    *,
    extract_recent_raw_turns_from_context: Callable[..., list],
):
    normalized = unicodedata.normalize("NFKC", str(text or "").strip()).lower()
    if not normalized:
        return False
    if any(marker in normalized for marker in ["you", "your", "assistant", "songryeon", "\ub108", "\ub124", "\uc1a1\ub828", "3\ucc28"]):
        return True
    recent_assistant = recent_context_last_assistant_turn(
        recent_context,
        extract_recent_raw_turns_from_context=extract_recent_raw_turns_from_context,
    )
    return bool(recent_assistant and any(marker in normalized for marker in ["that", "it", "\uadf8\uac70", "\ubc29\uae08", "\uc544\uae4c"]))


def is_social_repair_turn(
    user_input: str,
    recent_context: str = "",
    working_memory: dict | None = None,
    *,
    extract_artifact_hint: Callable[[str], object],
    is_directive_or_correction_turn: Callable[[str], bool],
    extract_recent_raw_turns_from_context: Callable[..., list],
):
    del working_memory
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text or extract_artifact_hint(text):
        return False
    if any(token in text for token in ["search ", "tool_", "schema", "db", "chat log"]):
        return False
    if not user_turn_targets_assistant_reply(
        text,
        recent_context,
        extract_recent_raw_turns_from_context=extract_recent_raw_turns_from_context,
    ):
        return False
    repair_markers = ["weird", "wrong", "awkward", "repeat", "not that", "sorry", "\uc774\uc0c1", "\uc5b4\uc0c9", "\ubc18\ubcf5", "\uc544\ub2c8", "\ud2c0\ub838", "\ubd88\ud3b8"]
    return any(marker in text for marker in repair_markers) or is_directive_or_correction_turn(text)


def social_repair_strategy(
    user_input: str,
    recent_context: str,
    working_memory: dict,
    *,
    extract_recent_raw_turns_from_context: Callable[..., list],
):
    del working_memory
    user_text = str(user_input or "").strip()
    recent_assistant = recent_context_last_assistant_turn(
        recent_context,
        extract_recent_raw_turns_from_context=extract_recent_raw_turns_from_context,
    )
    must_include = [f"Current user correction: {user_text}"] if user_text else []
    if recent_assistant:
        must_include.append(f"Previous assistant answer to repair: {recent_assistant}")
    return {
        "reply_mode": "social_repair",
        "delivery_freedom_mode": "supportive_free",
        "answer_goal": "Acknowledge the user correction and answer the immediate request naturally.",
        "tone_strategy": "Brief, accountable, and conversational.",
        "evidence_brief": " / ".join(must_include),
        "reasoning_brief": "The user is reacting to the assistant behavior, so repair the response instead of opening retrieval.",
        "direct_answer_seed": "You are right, I missed the immediate intent. I will answer that directly.",
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "Do not repeat the previous failed answer.",
            "Do not expose phase or judge terminology.",
            "Do not call tools for a social repair unless the user explicitly asks.",
        ],
        "answer_outline": ["Acknowledge briefly.", "Answer or perform the immediate corrected action."],
        "uncertainty_policy": "If the corrected action is playful or local, respond locally without retrieval.",
    }


def accepted_offer_execution_seed(active_offer: str):
    del active_offer
    return ""


def offer_acceptance_strategy(user_input: str, working_memory: dict):
    user_text = str(user_input or "").strip()
    active_offer, active_offer_source = pending_dialogue_act_anchor(working_memory)
    if not active_offer:
        active_offer = working_memory_active_offer(working_memory)
        active_offer_source = "active_offer" if active_offer else ""
    must_include = [f"Current follow-up acceptance: {user_text}"]
    if active_offer:
        source_label = active_offer_source or "working_memory"
        must_include.append(f"Pending continuation from {source_label}: {active_offer}")

    direct_seed = "\uc88b\uc544, \ubc29\uae08 \uc81c\uc548\ud588\ub358 \uac78 \ubc14\ub85c \uc774\uc5b4\uac08\uac8c."
    if active_offer:
        direct_seed = accepted_offer_execution_seed(active_offer) or f"\uc88b\uc544, \ubc29\uae08 \uc81c\uc548\ud588\ub358 \uac78 \ubc14\ub85c \uc774\uc5b4\uac08\uac8c. {active_offer}"

    return {
        "reply_mode": "continue_previous_offer",
        "delivery_freedom_mode": "proposal",
        "answer_goal": "Carry out or restate the assistant's most recent concrete proposal instead of restarting the conversation.",
        "tone_strategy": "Assume the user is approving the previous proposal and move forward clearly.",
        "evidence_brief": f"Follow-up acceptance turn: {user_text}",
        "reasoning_brief": "The user appears to be approving or pointing back to the assistant's last concrete offer, so the answer should continue that offer directly.",
        "direct_answer_seed": direct_seed,
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "Do not pretend the previous offer is unknown.",
            "Do not restart planning from zero.",
            "Do not ask a generic narrowing question before continuing the accepted offer.",
        ],
        "answer_outline": [
            "Briefly restate the accepted offer.",
            "Continue or execute it directly.",
            "Keep the momentum instead of reopening clarification.",
        ],
        "uncertainty_policy": "If the acceptance is brief but a previous concrete offer exists, treat it as approval and continue.",
    }


def retry_previous_answer_strategy(
    user_input: str,
    recent_context: str,
    working_memory: dict,
    *,
    extract_recent_raw_turns_from_context: Callable[..., list],
    is_generic_continue_seed: Callable[[str], bool],
):
    user_text = str(user_input or "").strip()
    previous_anchor, anchor_source = previous_delivery_anchor(
        user_input,
        recent_context,
        working_memory,
        extract_recent_raw_turns_from_context=extract_recent_raw_turns_from_context,
        is_generic_continue_seed=is_generic_continue_seed,
    )
    active_task = working_memory_active_task(working_memory)

    must_include = [f"Retry request: {user_text}"]
    if active_task and active_task != user_text:
        must_include.append(f"Previous active task: {active_task}")
    if previous_anchor:
        must_include.append(f"Previous delivery anchor from {anchor_source}: {previous_anchor}")

    direct_seed = "Retry the previous answer directly, improving on the failed last attempt instead of asking another generic clarification question."
    if active_task and previous_anchor:
        direct_seed = (
            f"Retry the previous task directly: {active_task}. "
            f"Use this earlier assistant payload only as an anchor, not as text to repeat verbatim: {previous_anchor}"
        )
    elif previous_anchor:
        direct_seed = (
            "Retry the previous answer directly. "
            f"Use this earlier assistant payload as the anchor, but do not repeat it verbatim if it was a failed clarification: {previous_anchor}"
        )

    return {
        "reply_mode": "continue_previous_offer",
        "delivery_freedom_mode": "grounded",
        "answer_goal": "Retry the previously requested answer directly instead of reopening planning or asking another generic clarification question.",
        "tone_strategy": "Acknowledge the retry briefly if needed, then answer more directly and concretely.",
        "evidence_brief": f"Retry/correction turn: {user_text}",
        "reasoning_brief": "The user is asking for another attempt at the immediately previous answer. The assistant should redo the task more directly instead of re-entering the war room.",
        "direct_answer_seed": direct_seed,
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "Do not repeat the same failed clarification question.",
            "Do not act as if the previous answer anchor is unknown.",
            "Do not reopen planning or tool search unless the user explicitly requested investigation.",
        ],
        "answer_outline": [
            "Retry the answer directly.",
            "Improve on the last failed attempt.",
            "Only ask one precise follow-up if the retry is impossible without it.",
        ],
        "uncertainty_policy": "Prefer a better direct retry over another vague clarification request.",
    }


def is_followup_offer_acceptance_turn(
    user_input: str,
    working_memory: dict,
    *,
    extract_artifact_hint: Callable[[str], object],
    extract_explicit_search_keyword: Callable[[str], object],
    is_assistant_investigation_request_turn: Callable[[str], bool],
    is_creative_story_request_turn: Callable[[str], bool],
    is_directive_or_correction_turn: Callable[[str], bool],
):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    if extract_artifact_hint(text):
        return False
    if extract_explicit_search_keyword(text):
        return False
    if is_assistant_investigation_request_turn(text):
        return False
    if is_creative_story_request_turn(text):
        return False
    if is_directive_or_correction_turn(text):
        return False

    if pending_dialogue_act_accepts_current_turn(user_input, working_memory):
        return True

    active_offer = working_memory_active_offer(working_memory)
    if not active_offer:
        return False

    if is_short_affirmation(text):
        return True

    fresh_request_markers = [
        "\uc124\uba85\ud574",
        "\uc54c\ub824\uc918",
        "\ub9d0\ud574\uc918",
        "\ub204\uad6c",
        "\ubb34\uc5c7",
        "\uc65c",
        "\uc5b4\ub5a4",
        "\uc720\ucd94",
        "\ubd84\uc11d",
        "\uc694\uc57d",
        "\uc815\ub9ac",
        "\uc0c1\uad00\uad00\uacc4",
        "\uad00\uacc4",
        "explain",
        "describe",
        "summarize",
        "analyze",
        "relationship",
        "who",
        "what",
        "why",
    ]
    if any(marker in text for marker in fresh_request_markers):
        return False
    if has_substantive_dialogue_anchor(text):
        return False

    explicit_continue_markers = [
        "\u3131\u3131",
        "\u3147\u3147",
        "\u314e\u3147",
        "\uacc4\uc18d",
        "\uc774\uc5b4\uc11c",
        "\uadf8\uac70",
        "\uadf8\uac78\ub85c",
        "\uadf8\ub300\ub85c",
        "\uc9c4\ud589",
        "\uc2dc\uc791",
        "\ubc14\ub85c \ud574",
        "go on",
        "continue",
        "keep going",
    ]
    return len(text) <= 16 and any(marker in text for marker in explicit_continue_markers)
