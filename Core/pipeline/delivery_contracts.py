"""Phase 3 speaker contract assembly helpers.

These helpers turn a delivery payload into the structured contract used by the
phase 3 speaker prompt. They should preserve contract keys and avoid any graph
routing or tool decisions.
"""

from __future__ import annotations

import unicodedata
from typing import Callable

from ..evidence_ledger import evidence_ledger_for_contract
from ..readiness import normalize_readiness_decision
from .packets import compact_rescue_handoff_for_prompt, compact_working_memory_for_prompt


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


def looks_like_internal_phase3_seed(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    if not normalized:
        return False
    markers = [
        "fieldmemo",
        "field memo",
        "answer_not_ready",
        "current_goal_answer_seed",
        "memory.referent_fact",
        "direct evidence for the current answer",
        "respond to the current user turn",
        "phase_",
        "source_judgments",
        "contract_status",
    ]
    return any(marker in normalized for marker in markers)


def verbalize_field_memo_delivery_seed(
    delivery_payload: dict,
    *,
    compact_user_facing_summary: Callable[[str, int], str],
):
    payload = delivery_payload if isinstance(delivery_payload, dict) else {}
    facts = payload.get("accepted_facts", [])
    if not isinstance(facts, list):
        facts = []
    facts = _dedupe_keep_order([
        compact_user_facing_summary(str(fact).strip(), 180)
        for fact in facts
        if str(fact).strip()
    ])[:6]
    if facts:
        return "Known from memory: " + " / ".join(facts[:4])
    seed = str(payload.get("answer_seed") or "").strip()
    if seed and not looks_like_internal_phase3_seed(seed):
        return seed
    return ""


def verbalize_grounded_delivery_seed(
    delivery_payload: dict,
    *,
    compact_user_facing_summary: Callable[[str, int], str],
):
    payload = delivery_payload if isinstance(delivery_payload, dict) else {}
    lane = str(payload.get("lane") or "").strip()
    if lane == "field_memo_review":
        return verbalize_field_memo_delivery_seed(
            payload,
            compact_user_facing_summary=compact_user_facing_summary,
        )
    facts = payload.get("accepted_facts", [])
    if not isinstance(facts, list):
        facts = []
    facts = _dedupe_keep_order([
        compact_user_facing_summary(str(fact).strip(), 180)
        for fact in facts
        if str(fact).strip()
    ])[:4]
    if facts:
        return "Grounded facts: " + " / ".join(facts)
    seed = str(payload.get("answer_seed") or "").strip()
    if seed and not looks_like_internal_phase3_seed(seed):
        return seed
    return ""


def build_phase3_speaker_judge_contract(
    state: dict,
    delivery_payload: dict,
    phase3_recent_context: str = "",
    delivery_freedom_mode: str = "",
    grounded_mode: bool = False,
    supervisor_memo: str = "",
    *,
    compact_user_facing_summary: Callable[[str, int], str],
):
    payload = delivery_payload if isinstance(delivery_payload, dict) else {}
    clean_failure = payload.get("clean_failure_packet", {})
    if not isinstance(clean_failure, dict):
        clean_failure = {}
    rescue_handoff = payload.get("rescue_handoff_packet", {})
    if not isinstance(rescue_handoff, dict):
        rescue_handoff = state.get("rescue_handoff_packet", {})
    if not isinstance(rescue_handoff, dict):
        rescue_handoff = {}

    user_input = str(state.get("user_input") or "").strip()
    ready = bool(payload.get("ready_for_delivery"))
    parametric_knowledge_allowed = bool(payload.get("parametric_knowledge_allowed"))
    answer_mode = str(payload.get("answer_mode") or "").strip() or (
        "public_parametric_knowledge" if parametric_knowledge_allowed and ready else "grounded_answer"
    )
    answer_seed = str(payload.get("answer_seed") or "").strip()
    failure_seed = str(clean_failure.get("message_seed") or "").strip()
    if rescue_handoff and not failure_seed:
        failure_seed = str(rescue_handoff.get("user_facing_label") or "").strip()
    if ready:
        say_this = ""
        if answer_seed and not looks_like_internal_phase3_seed(answer_seed):
            say_this = answer_seed
    else:
        say_this = failure_seed
    public_knowledge_mandate = bool(
        ready
        and answer_mode == "public_parametric_knowledge"
        and parametric_knowledge_allowed
    )
    question_class = str(payload.get("question_class") or "").strip() or "generic_dialogue"
    answer_mode_policy = payload.get("answer_mode_policy", {})
    if not isinstance(answer_mode_policy, dict):
        answer_mode_policy = {}
    readiness_decision = normalize_readiness_decision(payload.get("readiness_decision", {}))

    accepted_facts = payload.get("accepted_facts", [])
    if not isinstance(accepted_facts, list):
        accepted_facts = []
    rescue_fact_candidates = []
    for item in rescue_handoff.get("preserved_evidences", []) or []:
        if isinstance(item, dict):
            fact = str(item.get("extracted_fact") or item.get("observed_fact") or "").strip()
            if fact:
                rescue_fact_candidates.append(fact)
    rescue_fact_candidates.extend(
        str(fact).strip()
        for fact in rescue_handoff.get("preserved_field_memo_facts", []) or []
        if str(fact).strip()
    )
    rescue_fact_candidates.extend(
        str(fact).strip()
        for fact in rescue_handoff.get("what_we_know", []) or []
        if str(fact).strip()
    )
    accepted_facts = list(accepted_facts) + rescue_fact_candidates
    accepted_facts = _dedupe_keep_order(
        [
            compact_user_facing_summary(str(fact).strip(), 220)
            for fact in accepted_facts
            if str(fact).strip()
        ]
    )[:6]
    current_turn_facts = payload.get("current_turn_facts", [])
    if not isinstance(current_turn_facts, list):
        current_turn_facts = []
    current_turn_facts = _dedupe_keep_order(
        [
            compact_user_facing_summary(str(fact).strip(), 220)
            for fact in current_turn_facts
            if str(fact).strip()
        ]
    )[:4]

    forbidden = payload.get("forbidden_claims", [])
    if not isinstance(forbidden, list):
        forbidden = []
    forbidden = _dedupe_keep_order(
        [
            *[str(item).strip() for item in forbidden if str(item).strip()],
            "Do not mention internal packet names, phase numbers, judge labels, or search lanes.",
            "If SAY_THIS is empty, do not summarize reference material as a substitute answer.",
            "Do not invent facts outside FACTS_ALLOWED unless public knowledge is explicitly allowed.",
            "Do not pretend to know when the user's question has not been answered.",
            "Do not call it a search failure unless a real search/read failure occurred.",
            "For public-knowledge turns, do not collapse into generic retrieval failure unless a private-memory search was actually required.",
        ]
    )[:10]

    missing_slots = payload.get("missing_slots", [])
    if not isinstance(missing_slots, list):
        missing_slots = [missing_slots] if str(missing_slots or "").strip() else []
    missing_slots = [str(slot).strip() for slot in missing_slots if str(slot).strip()]

    short_term_context_packet = compact_working_memory_for_prompt(
        state.get("working_memory", {}),
        role="phase_3",
    )
    rescue_contract_packet = compact_rescue_handoff_for_prompt(rescue_handoff, role="phase_3")

    return {
        "schema": "SpeakerJudgeContract.v1",
        "role": "phase3_speaker_contract",
        "mode": "grounded_mode" if grounded_mode else "direct_dialogue_mode",
        "delivery_freedom_mode": str(delivery_freedom_mode or payload.get("answer_boundary") or "").strip(),
        "READY": ready,
        "USER_INPUT": user_input,
        "USER_GOAL": str(payload.get("user_goal") or user_input or "").strip(),
        "QUESTION_CLASS": question_class,
        "OUTPUT_ACT": str(payload.get("output_act") or "answer").strip(),
        "ANSWER_MODE": answer_mode,
        "READINESS_DECISION": readiness_decision,
        "SAY_THIS": say_this,
        "FACTS_ALLOWED": accepted_facts,
        "CURRENT_TURN_FACTS_ALLOWED": current_turn_facts,
        "PARAMETRIC_KNOWLEDGE_ALLOWED": parametric_knowledge_allowed,
        "PARAMETRIC_ANSWER_MANDATE": public_knowledge_mandate,
        "EVIDENCE_BLEND_POLICY": {
            "priority_order": [
                "current_turn_user_facts",
                "accepted_grounded_facts",
                "model_public_knowledge_when_allowed",
            ],
            "never_claim_as_memory": [
                "Do not pretend the answer came from stored memory if it comes from general model knowledge.",
                "Do not override direct user-provided facts with weaker recalled summaries.",
            ],
        },
        "EVIDENCE_LEDGER": evidence_ledger_for_contract(state.get("evidence_ledger", {})),
        "EVIDENCE_LEDGER_POLICY": {
            "purpose": "Observed runtime activity log, not a closed semantic ontology.",
            "must_do": [
                "Use event ids/source refs only as provenance for activities that actually happened.",
                "If no db_query/tool_result event exists, do not claim the answer came from DB or search.",
                "Runtime profile context may be used when relevant, but do not present it as retrieved memory.",
            ],
        },
        "PUBLIC_KNOWLEDGE_SAFETY_POLICY": {
            "named_entity_rule": (
                "For lists of characters, people, places, titles, or proper nouns, include only names "
                "you are highly confident are canonical. Do not invent, mistranslate, or Korean-localize names."
            ),
            "challenge_rule": (
                "If the user challenges a prior public-knowledge claim, treat the prior assistant answer as "
                "untrusted unless independently high-confidence; correct or retract uncertain claims."
            ),
            "uncertain_entity_rule": (
                "If a named entity is unfamiliar or low-confidence, say you do not recognize it as canonical "
                "instead of fabricating a role, identity, or location."
            ),
        },
        "PUBLIC_KNOWLEDGE_TOPIC_HINT": compact_user_facing_summary(
            str(payload.get("user_goal") or user_input or ""),
            180,
        ),
        "ANSWER_MODE_POLICY": {
            "question_class": question_class,
            "preferred_answer_mode": str(answer_mode_policy.get("preferred_answer_mode") or ""),
            "grounded_delivery_required": bool(answer_mode_policy.get("grounded_delivery_required")),
            "parametric_knowledge_allowed": bool(answer_mode_policy.get("parametric_knowledge_allowed")),
            "current_turn_grounding_ready": bool(answer_mode_policy.get("current_turn_grounding_ready")),
        },
        "RESCUE_HANDOFF": {
            "label_policy": "user_facing_label is a coarse enum; transform it into natural Korean instead of quoting it.",
            "what_we_know": rescue_contract_packet.get("what_we_know", []),
            "what_we_failed": rescue_contract_packet.get("what_we_failed", []),
            "speaker_tone_hint": str(rescue_contract_packet.get("speaker_tone_hint") or "").strip(),
            "user_facing_label": compact_user_facing_summary(rescue_contract_packet.get("user_facing_label", ""), 180),
        },
        "SHORT_TERM_CONTEXT": short_term_context_packet,
        "SHORT_TERM_CONTEXT_POLICY": {
            "purpose": "Use this only as immediate conversational context from WorkingMemoryWriter.",
            "use_when": [
                "The current user turn is a short acknowledgement, correction, pushback, pronoun, or continuation.",
                "assistant_obligation_next_turn or pending_dialogue_act.target says what the assistant should do next.",
                "The user asks for the assistant's thought about the immediately previous user statement.",
            ],
            "priority": [
                "assistant_obligation_next_turn",
                "pending_dialogue_act.target",
                "unresolved_user_request",
                "short_term_context",
            ],
            "do_not": [
                "Do not repeat the previous answer just because it appears in context.",
                "Do not call short-term context long-term memory.",
                "Do not expose WorkingMemoryWriter or pending_dialogue_act labels.",
            ],
        },
        "DO_NOT_SAY": forbidden,
        "IF_NOT_READY": {
            "fallback_action": str(payload.get("fallback_action") or "clean_failure").strip(),
            "missing_slots": missing_slots,
            "message_seed": failure_seed,
            "answer_boundary": str(payload.get("answer_boundary") or "").strip(),
        },
        "STYLE": {
            "voice": "Natural Korean. No report tone. Speak directly to the user.",
            "job": "Do not fabricate facts; only make the final wording smoother and more conversational.",
            "if_seed_is_good": "Use SAY_THIS as the center and lightly naturalize it.",
            "if_seed_is_bad": "Do not copy a bad seed; use IF_NOT_READY.message_seed or a clean direct answer instead.",
            "if_public_knowledge_mode": "Answer from public knowledge when confident; do not invent retrieval failure.",
        },
        "RECENT_CONTEXT_HINT": compact_user_facing_summary(phase3_recent_context, 420),
        "SUPERVISOR_MEMO": compact_user_facing_summary(supervisor_memo, 240) if supervisor_memo else "",
    }


__all__ = [
    "looks_like_internal_phase3_seed",
    "verbalize_field_memo_delivery_seed",
    "verbalize_grounded_delivery_seed",
    "build_phase3_speaker_judge_contract",
]
