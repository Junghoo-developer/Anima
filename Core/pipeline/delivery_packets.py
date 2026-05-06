"""Judge-speaker delivery packet assembly for phase 3.

This module translates approved reasoning board material into the compact
delivery packet consumed by phase 3. It must not call tools, route the graph, or
invent meaning beyond the supplied board/strategy/reference packets.
"""

from __future__ import annotations

import unicodedata

from .delivery_review import (
    looks_like_generic_non_answer_text as _looks_like_generic_non_answer_text,
    looks_like_internal_delivery_leak as _looks_like_internal_delivery_leak,
)
from .plans import empty_action_plan
from ..warroom.state import (
    _derive_war_room_operating_contract,
    _normalize_delivery_freedom_mode,
    _normalize_war_room_operating_contract,
)


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


def _looks_like_generic_delivery_seed(text: str) -> bool:
    lowered = unicodedata.normalize("NFKC", str(text or "")).lower()
    generic_markers = [
        "directly answer",
        "final answer",
        "current request",
        "current user turn",
        "summarize the retrieved results",
        "retrieved findings",
        "respond to the current user turn",
    ]
    return any(marker in lowered for marker in generic_markers)


def _fact_delivery_brief(facts: list[dict]) -> str:
    snippets = []
    for fact in facts[:3]:
        if not isinstance(fact, dict):
            continue
        text = str(fact.get("extracted_fact") or fact.get("excerpt") or "").strip()
        if not text:
            continue
        snippets.append(text)
    snippets = _dedupe_keep_order(snippets)
    if not snippets:
        return ""
    if len(snippets) == 1:
        return f"Use this grounded fact: {snippets[0]}"
    return "Use these grounded facts: " + " / ".join(snippets)


def build_judge_speaker_packet(reasoning_board: dict, response_strategy: dict, phase3_reference_policy: dict):
    board = reasoning_board if isinstance(reasoning_board, dict) else {}
    strategy = response_strategy if isinstance(response_strategy, dict) else {}
    verdict = board.get("verdict_board", {}) if isinstance(board.get("verdict_board"), dict) else {}
    fact_map = {
        str(fact.get("fact_id") or "").strip(): fact
        for fact in board.get("fact_cells", [])
        if isinstance(fact, dict)
    }
    approved_fact_ids = verdict.get("approved_fact_ids", []) if isinstance(verdict.get("approved_fact_ids"), list) else []
    approved_pair_ids = set(verdict.get("approved_pair_ids", [])) if isinstance(verdict.get("approved_pair_ids"), list) else set()
    approved_fact_cells = [fact_map[fid] for fid in approved_fact_ids if fid in fact_map]

    approved_claims = []
    for pair in board.get("candidate_pairs", []):
        if not isinstance(pair, dict):
            continue
        if pair.get("audit_status") != "approved":
            continue
        pair_id = str(pair.get("pair_id") or "").strip()
        if approved_pair_ids and pair_id not in approved_pair_ids:
            continue
        subjective = pair.get("subjective", {}) if isinstance(pair.get("subjective"), dict) else {}
        claim_text = str(subjective.get("claim_text") or "").strip()
        if not claim_text:
            continue
        approved_claims.append({
            "pair_id": pair_id,
            "paired_fact_digest": str(pair.get("paired_fact_digest") or "").strip(),
            "claim_text": claim_text,
            "answer_policy": str(subjective.get("answer_policy") or "cautious").strip(),
            "uncertainty_note": str(subjective.get("uncertainty_note") or "").strip(),
        })

    raw_reference = ""
    reference_mode = ""
    followup_instruction = ""
    if isinstance(phase3_reference_policy, dict):
        raw_reference = str(phase3_reference_policy.get("raw_reference") or "").strip()
        reference_mode = str(phase3_reference_policy.get("mode") or "").strip()
        followup_instruction = str(phase3_reference_policy.get("followup_instruction") or "").strip()

    verdict_answer_brief = str(verdict.get("final_answer_brief") or "").strip()
    strategy_answer_seed = str(strategy.get("direct_answer_seed") or "").strip()

    if verdict_answer_brief and _looks_like_internal_delivery_leak(verdict_answer_brief) and strategy_answer_seed:
        answer_brief = strategy_answer_seed
    else:
        answer_brief = verdict_answer_brief or strategy_answer_seed
    if approved_fact_cells and (not answer_brief or _looks_like_generic_delivery_seed(answer_brief)):
        synthesized_brief = _fact_delivery_brief(approved_fact_cells)
        if synthesized_brief:
            answer_brief = synthesized_brief
    judge_notes = verdict.get("judge_notes", []) if isinstance(verdict.get("judge_notes"), list) else []
    must_avoid_claims = board.get("must_avoid_claims", []) if isinstance(board.get("must_avoid_claims"), list) else []
    reply_mode = str(strategy.get("reply_mode") or "").strip()
    delivery_freedom_mode = _normalize_delivery_freedom_mode(
        str(strategy.get("delivery_freedom_mode") or "").strip(),
        reply_mode=reply_mode,
    )
    strategist_plan = board.get("strategist_plan", {}) if isinstance(board.get("strategist_plan"), dict) else {}
    advocate_report = board.get("advocate_report", {}) if isinstance(board.get("advocate_report"), dict) else {}
    response_contract = advocate_report.get("response_contract", {}) if isinstance(advocate_report.get("response_contract"), dict) else {}
    war_room_contract = _normalize_war_room_operating_contract(
        response_contract.get("war_room_contract")
        or strategist_plan.get("war_room_contract")
        or _derive_war_room_operating_contract(
            "",
            {},
            empty_action_plan(),
            strategy,
        )
    )
    phase3_handoff = war_room_contract.get("phase3_handoff", {}) if isinstance(war_room_contract.get("phase3_handoff"), dict) else {}
    forbidden_patterns = phase3_handoff.get("forbidden_output_patterns", []) if isinstance(phase3_handoff.get("forbidden_output_patterns"), list) else []

    grounded_mode = bool(approved_fact_cells or approved_claims or answer_brief or raw_reference)
    has_objective_delivery = bool(answer_brief or approved_fact_cells or approved_claims)

    if has_objective_delivery and delivery_freedom_mode in {"grounded", "proposal", "identity_direct", "supportive_free"}:
        followup_instruction = ""
    elif _looks_like_generic_non_answer_text(followup_instruction):
        if delivery_freedom_mode in {"proposal", "identity_direct"} and answer_brief:
            followup_instruction = ""
        elif reply_mode == "grounded_answer" and answer_brief and (approved_fact_cells or approved_claims):
            followup_instruction = ""

    delivery_packet = {
        "reply_mode": reply_mode or ("grounded_answer" if grounded_mode else "cautious_minimal"),
        "delivery_freedom_mode": delivery_freedom_mode,
        "final_answer_brief": answer_brief,
        "approved_fact_cells": approved_fact_cells,
        "approved_claims": approved_claims,
        "followup_instruction": followup_instruction,
        "raw_reference_excerpt": raw_reference,
        "war_room_contract": war_room_contract,
        "hard_constraints": [
            "Do not mention internal node names, war room, or judge packet internals.",
            "Do not invent facts beyond approved facts, approved claims, or the final answer brief.",
            "If the final answer brief is enough, answer directly instead of adding a generic narrowing follow-up.",
        ] + [f"Forbidden output pattern: {pattern}" for pattern in forbidden_patterns],
    }

    return {
        "speaker_mode": "grounded_mode" if grounded_mode else "direct_dialogue_mode",
        "reply_mode": delivery_packet["reply_mode"],
        "delivery_freedom_mode": delivery_freedom_mode,
        "answer_now": bool(verdict.get("answer_now", False)),
        "requires_search": bool(verdict.get("requires_search", False)),
        "final_answer_brief": answer_brief,
        "approved_fact_cells": approved_fact_cells,
        "approved_claims": approved_claims,
        "must_avoid_claims": _dedupe_keep_order([str(item).strip() for item in must_avoid_claims if str(item).strip()]),
        "judge_notes": _dedupe_keep_order([str(note).strip() for note in judge_notes if str(note).strip()]),
        "tone_strategy": str(strategy.get("tone_strategy") or "").strip(),
        "uncertainty_policy": str(strategy.get("uncertainty_policy") or "").strip(),
        "answer_outline": strategy.get("answer_outline", []) if isinstance(strategy.get("answer_outline"), list) else [],
        "reference_mode": reference_mode,
        "followup_instruction": followup_instruction,
        "raw_reference_excerpt": raw_reference,
        "war_room_contract": war_room_contract,
        "delivery_packet": delivery_packet,
    }


__all__ = ["build_judge_speaker_packet"]
