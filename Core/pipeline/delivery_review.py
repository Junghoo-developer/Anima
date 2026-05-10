"""Phase 3 delivery review and seed-sanitizing helpers.

These helpers inspect delivery material before the phase 3 speaker uses it.
They are structural filters only: they do not choose routes, call tools, or
rewrite the user's meaning.
"""

from __future__ import annotations

import json
import re
import unicodedata

from langchain_core.messages import HumanMessage, SystemMessage

from ..prompt_builders import build_delivery_review_sys_prompt
from .contracts import DELIVERY_REVIEW_REASON_TYPES, DeliveryReview
from .packets import _compact_fact_cells_for_prompt
from .structured_io import invoke_structured_with_repair, validate_delivery_review

DELIVERY_REVIEW_SCHEMA = "DeliveryReview.v1"
DELIVERY_REVIEW_VERDICTS = {"approve", "remand", "sos_119"}
DELIVERY_REVIEW_REMAND_TARGETS = {"", "-1a", "-1s"}
DELIVERY_REVIEW_REASON_TYPE_SET = set(DELIVERY_REVIEW_REASON_TYPES)


def _compact_text(value, limit: int = 500):
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _compact_list(values, limit: int = 8, text_limit: int = 240):
    if not isinstance(values, list):
        values = [values] if str(values or "").strip() else []
    result = []
    seen = set()
    for value in values:
        text = _compact_text(value, text_limit)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _compact_evidence_refs(values, limit: int = 8, text_limit: int = 120):
    if not isinstance(values, list):
        return []
    result = []
    seen = set()
    for value in values:
        if not isinstance(value, str):
            continue
        text = _compact_text(value, text_limit)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _infer_reason_type_from_issues(values):
    text = " ".join(str(value or "") for value in values if str(value or "").strip()).lower()
    if "hallucination" in text or "unsupported" in text:
        return "hallucination"
    if "missing" in text or "omit" in text:
        return "omission"
    return ""


def _safe_jsonable(value):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return str(value)


def _compact_fact_item(value, text_limit: int = 260):
    if isinstance(value, dict):
        fact_text = (
            value.get("claim")
            or value.get("fact")
            or value.get("text")
            or value.get("summary")
            or value.get("content")
            or value.get("observed_fact")
            or value.get("accepted_fact")
        )
        item = {
            "fact": _compact_text(fact_text or value, text_limit),
        }
        source = value.get("source") or value.get("source_id") or value.get("source_ref") or value.get("id")
        if source:
            item["source"] = _compact_text(source, 120)
        status = value.get("status") or value.get("source_status") or value.get("judgment")
        if status:
            item["status"] = _compact_text(status, 80)
        return item
    return {"fact": _compact_text(value, text_limit)}


def _compact_fact_items(values, limit: int = 8, text_limit: int = 260):
    if not isinstance(values, list):
        values = [values] if str(values or "").strip() else []
    result = []
    seen = set()
    for value in values:
        item = _compact_fact_item(value, text_limit)
        key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if not item.get("fact") or key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def _analysis_review_projection(analysis_report: dict | None):
    analysis = analysis_report if isinstance(analysis_report, dict) else {}
    return {
        "contract_status": _compact_text(analysis.get("contract_status"), 80),
        "investigation_status": _compact_text(analysis.get("investigation_status"), 80),
        "can_answer_user_goal": bool(analysis.get("can_answer_user_goal")),
        "evidences": _compact_fact_items(analysis.get("evidences", []), 10, 260),
        "usable_field_memo_facts": _compact_list(analysis.get("usable_field_memo_facts", []), 10, 240),
        "accepted_facts": _compact_list(analysis.get("accepted_facts", []), 10, 240),
        "source_judgments": _compact_fact_items(analysis.get("source_judgments", []), 6, 220),
        "missing_slots": _compact_list(analysis.get("missing_slots", []) or analysis.get("unfilled_slots", []), 6, 120),
    }


def _response_strategy_review_projection(response_strategy: dict | None):
    strategy = response_strategy if isinstance(response_strategy, dict) else {}
    return {
        "delivery_freedom_mode": _compact_text(strategy.get("delivery_freedom_mode"), 80),
        "reply_mode": _compact_text(strategy.get("reply_mode"), 80),
        "answer_mode": _compact_text(strategy.get("answer_mode") or strategy.get("preferred_answer_mode"), 80),
        "must_include_facts": _compact_list(strategy.get("must_include_facts", []), 10, 240),
        "must_avoid_claims": _compact_list(strategy.get("must_avoid_claims", []), 10, 220),
        "uncertainty_policy": _compact_text(strategy.get("uncertainty_policy"), 180),
    }


def _rescue_review_projection(rescue_handoff_packet: dict | None):
    rescue = rescue_handoff_packet if isinstance(rescue_handoff_packet, dict) else {}
    return {
        "preserved_evidences": _compact_fact_items(rescue.get("preserved_evidences", []), 8, 240),
        "preserved_field_memo_facts": _compact_list(rescue.get("preserved_field_memo_facts", []), 8, 220),
        "what_we_know": _compact_list(rescue.get("what_we_know", []), 6, 220),
        "what_we_failed": _compact_list(rescue.get("what_we_failed", []), 4, 160),
        "speaker_tone_hint": _compact_text(rescue.get("speaker_tone_hint"), 80),
        "user_facing_label": _compact_text(rescue.get("user_facing_label"), 80),
    }


def _review_to_dict(review_obj):
    if isinstance(review_obj, dict):
        return _safe_jsonable(review_obj)
    if hasattr(review_obj, "model_dump"):
        try:
            return review_obj.model_dump(by_alias=True)
        except TypeError:
            return review_obj.model_dump()
    if hasattr(review_obj, "dict"):
        try:
            return review_obj.dict(by_alias=True)
        except TypeError:
            return review_obj.dict()
    content = getattr(review_obj, "content", None)
    if isinstance(content, str):
        try:
            return json.loads(content)
        except Exception:
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if match:
                return json.loads(match.group(0))
    return {}


def _allowed_fact_ids_from_review_context(context: dict | None):
    packet = context if isinstance(context, dict) else {}
    facts = packet.get("fact_cells_for_review", [])
    if not isinstance(facts, list):
        return []
    return [
        str(item.get("fact_id") or "").strip()
        for item in facts
        if isinstance(item, dict) and str(item.get("fact_id") or "").strip()
    ]


def normalize_delivery_review(packet: dict | None):
    """Normalize the future post-phase3 -1b review packet.

    This contract is intentionally unable to create tool queries. It may only
    approve the produced answer, remand it to a reasoning/planning surface, or
    send the turn to the rescue boundary.
    """
    packet = packet if isinstance(packet, dict) else {}
    verdict = str(packet.get("verdict") or "approve").strip()
    if verdict not in DELIVERY_REVIEW_VERDICTS:
        verdict = "approve"
    target = str(packet.get("remand_target") or "").strip()
    if target not in DELIVERY_REVIEW_REMAND_TARGETS:
        target = ""
    reason_type = str(packet.get("reason_type") or "").strip()
    if reason_type not in DELIVERY_REVIEW_REASON_TYPE_SET:
        reason_type = ""
    evidence_refs = _compact_evidence_refs(packet.get("evidence_refs", []), 8, 120)
    delta = _compact_text(packet.get("delta"), 280)
    if verdict == "approve":
        target = ""
    elif verdict == "sos_119":
        target = ""
    elif reason_type in {"hallucination", "omission", "contradiction", "thought_gap"}:
        target = "-1s"
    elif reason_type == "tool_misuse":
        target = "-1a"
    guidance = _compact_text(packet.get("remand_guidance"), 700)
    if not guidance and delta:
        guidance = delta
    if re.search(r"\btool_[a-zA-Z0-9_]+\s*\(", guidance):
        guidance = "Reviewer cannot author tool calls; remand target must decide any further action."
    return {
        "schema": str(packet.get("schema") or DELIVERY_REVIEW_SCHEMA),
        "verdict": verdict,
        "reason": _compact_text(packet.get("reason"), 700),
        "reason_type": reason_type,
        "evidence_refs": evidence_refs,
        "delta": delta,
        "issues_found": _compact_list(packet.get("issues_found", []), 8, 220),
        "remand_target": target,
        "remand_guidance": guidance,
    }


def delivery_review_from_speaker_guard(
    speaker_review: dict | None,
    *,
    delivery_status: str = "",
    loop_count: int = 0,
    hard_stop: int = 0,
):
    """Convert the current speaker guard into the new post-delivery contract."""
    review = speaker_review if isinstance(speaker_review, dict) else {}
    should_remand = bool(review.get("should_remand"))
    issues = _compact_list(review.get("issues", []), 8, 220)
    missing = _compact_list(review.get("missing_for_delivery", []), 8, 220)
    status = str(delivery_status or "").strip().lower()
    if should_remand:
        if hard_stop and loop_count >= hard_stop:
            return normalize_delivery_review({
                "verdict": "sos_119",
                "reason": "Phase 3 answer was rejected and retry budget is exhausted.",
                "issues_found": issues + missing,
                "remand_guidance": "Preserve approved evidence and prepare a clean rescue handoff.",
            })
        return normalize_delivery_review({
            "verdict": "remand",
            "reason": "Phase 3 answer was rejected by the speaker guard.",
            "issues_found": issues + missing,
            "remand_target": "-1a",
            "remand_guidance": "Revise the delivery plan without creating new tool queries in the reviewer.",
        })
    return normalize_delivery_review({
        "verdict": "approve",
        "reason": "Phase 3 answer passed the speaker guard." if status == "delivered" else "No blocking speaker issue found.",
        "issues_found": [],
    })


def build_delivery_review_context(state: dict | None, final_answer: str = ""):
    """Build the bounded input packet for the post-phase3 -1b reviewer."""
    state = state if isinstance(state, dict) else {}
    payload = state.get("phase3_delivery_payload", {})
    if not isinstance(payload, dict):
        payload = {}
    readiness = state.get("readiness_decision", {})
    if not isinstance(readiness, dict):
        readiness = {}
    speaker_review = state.get("speaker_review", {})
    if not isinstance(speaker_review, dict):
        speaker_review = {}
    reasoning_board = state.get("reasoning_board", {})
    if not isinstance(reasoning_board, dict):
        reasoning_board = {}
    return {
        "schema": "DeliveryReviewContext.v1",
        "user_input": _compact_text(state.get("user_input"), 1200),
        "final_answer": _compact_text(final_answer, 2000),
        "speaker_review": speaker_review,
        "readiness_decision": readiness,
        "analysis_report": _analysis_review_projection(state.get("analysis_report", {})),
        "response_strategy": _response_strategy_review_projection(state.get("response_strategy", {})),
        "rescue_handoff_packet": _rescue_review_projection(state.get("rescue_handoff_packet", {})),
        "fact_cells_for_review": _compact_fact_cells_for_prompt(reasoning_board.get("fact_cells", []), limit=10),
        "phase3_delivery_summary": {
            "answer_mode": _compact_text(payload.get("answer_mode"), 120),
            "ready_for_delivery": bool(payload.get("ready_for_delivery")),
            "fallback_action": _compact_text(payload.get("fallback_action"), 120),
            "source_lane": _compact_text(payload.get("source_lane") or payload.get("lane"), 120),
        },
    }


def build_delivery_review_prompt(context: dict | None):
    packet = context if isinstance(context, dict) else {}
    try:
        context_prompt = json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        context_prompt = str(packet)
    return build_delivery_review_sys_prompt(context_prompt)


def run_delivery_review_llm(llm, context: dict | None):
    """Ask the -1b reviewer LLM for a DeliveryReview.v1 packet."""
    if llm is None:
        return None
    packet = context if isinstance(context, dict) else {}
    prompt = build_delivery_review_prompt(packet)
    result = invoke_structured_with_repair(
        llm=llm,
        schema=DeliveryReview,
        messages=[
            SystemMessage(content=prompt),
            HumanMessage(content=str(packet.get("final_answer") or "")),
        ],
        node_name="-1b_delivery_review",
        repair_prompt="Return valid DeliveryReview.v1 JSON only. Do not invent fact_ids or tool calls.",
        max_repairs=1,
    )
    if not result.ok:
        failure_review = normalize_delivery_review({
            "verdict": "remand",
            "reason": "DeliveryReview structured output failed.",
            "reason_type": "thought_gap",
            "delta": result.failure.get("summary", ""),
            "issues_found": ["structured_output_failure"],
            "remand_target": "-1s",
        })
        failure_review["structured_failure"] = result.failure
        return failure_review
    review = normalize_delivery_review(result.value)
    return validate_delivery_review(review, _allowed_fact_ids_from_review_context(packet))


def _merge_review_with_speaker_guard(llm_review: dict | None, guard_review: dict | None):
    guard = normalize_delivery_review(guard_review or {})
    if not isinstance(llm_review, dict) or not llm_review:
        return guard
    review = normalize_delivery_review(llm_review)
    if guard.get("verdict") == "sos_119":
        return guard
    if guard.get("verdict") == "remand" and review.get("verdict") == "approve":
        merged = dict(guard)
        merged["issues_found"] = _compact_list(
            list(guard.get("issues_found", [])) + ["LLM reviewer approved, but deterministic speaker guard blocked delivery."],
            8,
            220,
        )
        if not merged.get("reason_type"):
            merged["reason_type"] = _infer_reason_type_from_issues(merged.get("issues_found", []))
        return normalize_delivery_review(merged)
    if guard.get("verdict") == "remand" and not review.get("reason_type"):
        enriched = dict(review)
        inferred = _infer_reason_type_from_issues(
            list(review.get("issues_found", [])) + list(guard.get("issues_found", []))
        )
        if inferred:
            enriched["reason_type"] = inferred
            if not enriched.get("delta"):
                enriched["delta"] = guard.get("reason") or "The speaker guard found a delivery issue."
            return normalize_delivery_review(enriched)
    return review


def run_phase3_delivery_review(
    state: dict | None,
    *,
    llm=None,
    attach_ledger_event,
    print_fn=print,
):
    """Review the produced phase_3 answer as the new post-delivery gate.

    The primary reviewer is an LLM constrained to DeliveryReview.v1. The
    deterministic speaker guard remains as a safety fallback and hard blocker
    for obvious internal-report leaks.
    """
    state = state if isinstance(state, dict) else {}
    messages = state.get("messages", [])
    final_answer = ""
    if isinstance(messages, list) and messages:
        last_message = messages[-1]
        final_answer = str(getattr(last_message, "content", "") or "")

    loop_count = int(state.get("loop_count", 0) or 0)
    try:
        reasoning_budget = max(int(state.get("reasoning_budget", 1)), 0)
    except (TypeError, ValueError):
        reasoning_budget = 1
    hard_stop = max(reasoning_budget, 1) + 2
    speaker_review = state.get("speaker_review", {})
    guard_review = delivery_review_from_speaker_guard(
        speaker_review if isinstance(speaker_review, dict) else {},
        delivery_status=str(state.get("delivery_status") or ""),
        loop_count=loop_count,
        hard_stop=hard_stop,
    )
    review_context = build_delivery_review_context(state, final_answer=final_answer)
    llm_review = None
    llm_error = ""
    try:
        llm_review = run_delivery_review_llm(llm, review_context)
    except Exception as exc:
        llm_error = _compact_text(exc, 260)
    delivery_review = _merge_review_with_speaker_guard(llm_review, guard_review)
    if llm_error:
        delivery_review = dict(delivery_review)
        issues = list(delivery_review.get("issues_found", []))
        issues.append(f"LLM reviewer fallback used: {llm_error}")
        delivery_review["issues_found"] = _compact_list(issues, 8, 220)
        delivery_review = normalize_delivery_review(delivery_review)
    verdict = str(delivery_review.get("verdict") or "").strip()
    try:
        prior_rejections = max(int(state.get("delivery_review_rejections", 0) or 0), 0)
    except (TypeError, ValueError):
        prior_rejections = 0
    rejection_count = prior_rejections
    if verdict == "approve":
        rejection_count = 0
    elif verdict == "remand":
        rejection_count = prior_rejections + 1
        if rejection_count > 3:
            delivery_review = normalize_delivery_review({
                "verdict": "sos_119",
                "reason": "Delivery review rejected the answer more than three times in one turn.",
                "issues_found": delivery_review.get("issues_found", []),
                "remand_guidance": "Preserve approved evidence and prepare a clean rescue handoff.",
            })
            verdict = "sos_119"
    print_fn(f"[Delivery Review] verdict={verdict or 'approve'} | reason={delivery_review.get('reason', '')}")

    result = {
        "delivery_review": delivery_review,
        "delivery_review_context": review_context,
        "delivery_review_rejections": rejection_count,
    }
    if verdict == "remand":
        result["loop_count"] = loop_count + 1
    return attach_ledger_event(
        result,
        state,
        source_kind="delivery_review",
        producer_node="-1b_delivery_review",
        source_ref=verdict or "approve",
        content=delivery_review,
        confidence=0.9,
    )


def normalize_user_facing_text(text: str):
    normalized = unicodedata.normalize("NFC", str(text or ""))
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def looks_like_internal_delivery_leak(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    if not normalized:
        return False
    internal_markers = [
        "speaker review", "judge", "critic", "advocate",
        "speaker packet", "judge_speaker_packet", "phase_",
        "current_goal_answer_seed", "answer_not_ready", "source_judgments",
    ]
    return any(marker in normalized for marker in internal_markers)


def build_speaker_review(judge_speaker_packet: dict, user_input: str = "", recent_context_excerpt: str = ""):
    packet = judge_speaker_packet if isinstance(judge_speaker_packet, dict) else {}
    delivery_packet = packet.get("delivery_packet", {}) if isinstance(packet.get("delivery_packet"), dict) else {}
    if delivery_packet:
        packet = {
            **packet,
            "reply_mode": delivery_packet.get("reply_mode", packet.get("reply_mode", "")),
            "delivery_freedom_mode": delivery_packet.get("delivery_freedom_mode", packet.get("delivery_freedom_mode", "")),
            "final_answer_brief": delivery_packet.get("final_answer_brief", packet.get("final_answer_brief", "")),
            "approved_fact_cells": delivery_packet.get("approved_fact_cells", packet.get("approved_fact_cells", [])),
            "approved_claims": delivery_packet.get("approved_claims", packet.get("approved_claims", [])),
            "followup_instruction": delivery_packet.get("followup_instruction", packet.get("followup_instruction", "")),
            "raw_reference_excerpt": delivery_packet.get("raw_reference_excerpt", packet.get("raw_reference_excerpt", "")),
        }
    speaker_mode = str(packet.get("speaker_mode") or "").strip()
    reply_mode = str(packet.get("reply_mode") or "").strip()
    delivery_freedom_mode = str(packet.get("delivery_freedom_mode") or "").strip()
    final_answer_brief = str(packet.get("final_answer_brief") or "").strip()
    followup_instruction = str(packet.get("followup_instruction") or "").strip()
    approved_fact_cells = packet.get("approved_fact_cells", []) if isinstance(packet.get("approved_fact_cells"), list) else []
    approved_claims = packet.get("approved_claims", []) if isinstance(packet.get("approved_claims"), list) else []
    reference_mode = str(packet.get("reference_mode") or "").strip()

    issues = []
    missing_for_delivery = []

    if looks_like_internal_delivery_leak(final_answer_brief):
        issues.append("final_answer_brief is too weak for direct delivery.")

    has_delivery_seed = bool(final_answer_brief or followup_instruction or approved_fact_cells or approved_claims)
    if not has_delivery_seed and reply_mode != "ask_user_question_now":
        missing_for_delivery.append("A concrete follow-up instruction is missing.")

    if reply_mode == "grounded_answer" and not (final_answer_brief or approved_fact_cells or approved_claims):
        missing_for_delivery.append("grounded_answer needs at least one grounded fact or claim.")

    if speaker_mode == "grounded_mode" and not (approved_fact_cells or approved_claims or final_answer_brief):
        issues.append("grounded_mode was selected without enough approved delivery material.")

    if reference_mode == "hidden_large_raw" and not (final_answer_brief or followup_instruction):
        missing_for_delivery.append("A direct dialogue path still needs a clearer follow-up intent.")

    if not str(user_input or "").strip() and not str(recent_context_excerpt or "").strip():
        issues.append("Neither the current user input nor recent context is available for speaker delivery.")

    delivery_ok = not issues and not missing_for_delivery
    if delivery_ok:
        suggested_action = "deliver_now"
    elif missing_for_delivery and not approved_fact_cells and not approved_claims:
        suggested_action = "strengthen_response_strategy"
    elif followup_instruction:
        suggested_action = "followup_only"
    else:
        suggested_action = "remand_to_judge"

    return {
        "delivery_ok": delivery_ok,
        "should_remand": not delivery_ok,
        "issues": issues,
        "missing_for_delivery": missing_for_delivery,
        "suggested_action": suggested_action,
        "reply_mode": reply_mode,
        "delivery_freedom_mode": delivery_freedom_mode,
    }


def looks_like_generic_non_answer_text(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    if not normalized:
        return False
    markers = [
        "narrow the scope", "be more specific", "tell me more",
        "next best step", "next_best_action", "next best action",
        "directly pass this to phase", "grounded findings",
        "current request", "current system", "question number", "item name",
        "answer_not_ready", "direct evidence for the current answer",
        "\uc9c0\uae08 \ud655\uc778\ub41c \uadfc\uac70\ub9cc\uc73c\ub85c\ub294 \ub2e8\uc815\ud558\uae30 \uc5b4\ub824\uc6cc",
        "\ud655\uc778\ub41c \uadfc\uac70\ub9cc\uc73c\ub85c\ub294",
        "\ubc29\uae08 \ud750\ub984 \uadf8\ub300\ub85c \uc774\uc5b4\uac00",
        "\ud750\ub984 \uadf8\ub300\ub85c",
    ]
    return any(marker in normalized for marker in markers)


def looks_like_user_parroting_report(text: str, user_input: str):
    normalized_text = normalize_user_facing_text(text)
    normalized_user = normalize_user_facing_text(user_input)
    if not normalized_text or not normalized_user:
        return False
    lowered = unicodedata.normalize("NFKC", normalized_text).lower()
    if "user:" not in lowered and "the user" not in lowered:
        return False
    return normalized_user in normalized_text


def is_generic_continue_seed(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "").strip()).lower()
    if not normalized:
        return False
    markers = [
        "pick up the previous thread",
        "continue the immediately preceding thread",
        "continue the previous thread",
        "continue the previously proposed move",
        "previous assistant offer",
        "follow-up acknowledgement",
        "grounded findings that matter here",
        "deliver the grounded findings directly",
    ]
    return any(marker in normalized for marker in markers)


def has_meaningful_delivery_seed(text: str, user_input: str = ""):
    normalized_text = normalize_user_facing_text(text)
    if not normalized_text:
        return False
    if is_generic_continue_seed(normalized_text):
        return False
    if looks_like_internal_delivery_leak(normalized_text):
        return False
    if looks_like_generic_non_answer_text(normalized_text):
        return False
    if user_input and looks_like_user_parroting_report(normalized_text, user_input):
        return False
    return True


def sanitize_response_strategy_for_phase3(response_strategy: dict, user_input: str = ""):
    """Keep internal strategy prose out of the final speaker prompt."""
    if not isinstance(response_strategy, dict):
        return {}
    try:
        strategy = json.loads(json.dumps(response_strategy, ensure_ascii=False))
    except Exception:
        strategy = dict(response_strategy)
    seed = str(strategy.get("direct_answer_seed") or "").strip()
    if seed and not has_meaningful_delivery_seed(seed, user_input):
        strategy["direct_answer_seed"] = ""
    return strategy


__all__ = [
    "DELIVERY_REVIEW_SCHEMA",
    "DELIVERY_REVIEW_VERDICTS",
    "build_delivery_review_context",
    "build_delivery_review_prompt",
    "delivery_review_from_speaker_guard",
    "normalize_delivery_review",
    "run_delivery_review_llm",
    "run_phase3_delivery_review",
    "normalize_user_facing_text",
    "looks_like_internal_delivery_leak",
    "build_speaker_review",
    "looks_like_generic_non_answer_text",
    "looks_like_user_parroting_report",
    "is_generic_continue_seed",
    "has_meaningful_delivery_seed",
    "sanitize_response_strategy_for_phase3",
]
