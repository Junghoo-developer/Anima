"""Phase 3 source-summary packet helpers.

These helpers shape source review material into packets phase 3 can speak from.
They do not route the graph, call tools, or decide policy; callers provide the
small semantic callbacks that still live near the public graph wrappers.
"""

from __future__ import annotations

import re
from typing import Callable

from .contracts import RecentDialogueBrief


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


def parse_search_result_hits(
    raw_reference: str,
    *,
    compact_user_facing_summary: Callable[[str, int], str],
):
    text = str(raw_reference or "").strip()
    if not text:
        return "", []
    keyword = ""
    hits = []
    current_hit = None
    for raw_line in text.splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue
        if not keyword and "query:" in line.lower():
            keyword_match = re.search(r"query:\s*(.+)$", line, flags=re.IGNORECASE)
            if keyword_match:
                keyword = str(keyword_match.group(1) or "").strip()
            continue
        if "source:" in line.lower() or "source=" in line.lower():
            hit_match = re.search(
                r"source[:=]\s*([^\]|]+)(?:\|([^\]]+))?.*?(?:score[:=]\s*([0-9.]+))?",
                line,
                flags=re.IGNORECASE,
            )
            if hit_match:
                try:
                    score = float(str(hit_match.group(3) or "").strip())
                except (TypeError, ValueError):
                    score = None
                current_hit = {
                    "source_type": str(hit_match.group(1) or "").strip(),
                    "source_date": str(hit_match.group(2) or "").strip(),
                    "score": score,
                    "summary": "",
                }
                hits.append(current_hit)
            continue
        if current_hit is not None and ("summary:" in line.lower() or line.startswith("- ")):
            summary = re.sub(r"^\s*(?:summary:|-)\s*", "", line, flags=re.IGNORECASE).strip()
            current_hit["summary"] = compact_user_facing_summary(summary, limit=170)
            continue
    return keyword, hits[:3]


def format_findings_first_delivery(
    user_input: str,
    judge_speaker_packet: dict,
    *,
    compact_user_facing_summary: Callable[[str, int], str],
    extract_explicit_search_keyword: Callable[[str], str],
):
    packet = judge_speaker_packet if isinstance(judge_speaker_packet, dict) else {}
    delivery_packet = packet.get("delivery_packet", {}) if isinstance(packet.get("delivery_packet"), dict) else {}
    raw_reference = str(delivery_packet.get("raw_reference_excerpt") or packet.get("raw_reference_excerpt") or "").strip()
    keyword, hits = parse_search_result_hits(
        raw_reference,
        compact_user_facing_summary=compact_user_facing_summary,
    )

    if hits:
        keyword_text = keyword or extract_explicit_search_keyword(user_input) or "requested search term"
        intro = f"Search findings for '{keyword_text}':"
        if len(hits) == 1:
            hit = hits[0]
            source_label = " ".join([part for part in [hit.get("source_type"), hit.get("source_date")] if part]).strip()
            score = hit.get("score")
            score_text = f" (score {score:.3f})" if isinstance(score, float) else ""
            lines = [
                intro,
                f"1. {source_label}{score_text}: {hit.get('summary') or 'No usable summary was available.'}",
            ]
        else:
            lines = [intro]
            for idx, hit in enumerate(hits, start=1):
                source_label = " ".join([part for part in [hit.get("source_type"), hit.get("source_date")] if part]).strip()
                score = hit.get("score")
                score_text = f" (score {score:.3f})" if isinstance(score, float) else ""
                lines.append(f"{idx}. {source_label}{score_text}: {hit.get('summary') or 'No usable summary was available.'}")
        return "\n".join([line for line in lines if line]).strip()

    approved_fact_cells = packet.get("approved_fact_cells", []) if isinstance(packet.get("approved_fact_cells"), list) else []
    fact_texts = []
    for fact in approved_fact_cells[:3]:
        if not isinstance(fact, dict):
            continue
        text = str(fact.get("extracted_fact") or fact.get("excerpt") or "").strip()
        if text:
            fact_texts.append(compact_user_facing_summary(text, limit=150))
    fact_texts = _dedupe_keep_order(fact_texts)[:3]
    answer_brief = compact_user_facing_summary(str(packet.get("final_answer_brief") or "").strip(), limit=180)
    if not fact_texts and not answer_brief:
        return ""

    keyword_text = extract_explicit_search_keyword(user_input) or "requested search term"
    lines = [f"Search findings for '{keyword_text}':"]
    if answer_brief:
        lines.append(answer_brief)
    for fact in fact_texts:
        if answer_brief and fact in answer_brief:
            continue
        lines.append(f"- {fact}")
    return "\n".join([line for line in lines if line]).strip()


def extract_turns_from_recent_dialogue_report(raw_read_report: dict, max_turns: int = 6):
    report = raw_read_report if isinstance(raw_read_report, dict) else {}
    turns = []
    for item in report.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        source_type = str(item.get("source_type") or "").strip()
        source_id = str(item.get("source_id") or "").strip()
        if source_type not in {"recent_chat_turn", "recent_chat_hint"} and not source_id.startswith("recent_turn_"):
            continue
        raw_text = str(item.get("observed_fact") or item.get("excerpt") or "").strip()
        matched = re.match(r"^\s*(user|assistant)\s*:\s*(.*)$", raw_text, re.IGNORECASE | re.DOTALL)
        if not matched:
            continue
        role = matched.group(1).lower().strip()
        content = re.sub(r"\s+", " ", matched.group(2).strip())
        if content:
            turns.append({"role": role, "content": content})
    return turns[-max_turns:]


def recent_dialogue_brief_text(
    turns: list[dict],
    user_input: str = "",
    *,
    compact_user_facing_summary: Callable[[str, int], str],
):
    if not turns:
        return ""
    lines = ["Recent dialogue only:"]
    for idx, turn in enumerate(turns, start=1):
        role = str(turn.get("role") or "").strip().lower()
        role_label = "user" if role == "user" else "assistant" if role == "assistant" else role or "record"
        content = compact_user_facing_summary(str(turn.get("content") or "").strip(), limit=170)
        if content:
            lines.append(f"{idx}. {role_label}: {content}")

    last_user = next((turn for turn in reversed(turns) if turn.get("role") == "user"), {})
    last_assistant = next((turn for turn in reversed(turns) if turn.get("role") == "assistant"), {})
    anchor_parts = []
    if last_user.get("content"):
        anchor_parts.append(f"last user: {compact_user_facing_summary(last_user['content'], 120)}")
    if last_assistant.get("content"):
        anchor_parts.append(f"last assistant: {compact_user_facing_summary(last_assistant['content'], 120)}")
    if anchor_parts:
        lines.append("Anchor: " + " / ".join(anchor_parts) + ".")
    if user_input:
        lines.append("Use only this recent-dialogue packet; do not invent older memory.")
    return "\n".join([line for line in lines if line]).strip()


def build_recent_dialogue_brief(
    raw_read_report: dict,
    analysis_data: dict | None = None,
    user_input: str = "",
    *,
    compact_user_facing_summary: Callable[[str, int], str],
):
    report = raw_read_report if isinstance(raw_read_report, dict) else {}
    if str(report.get("read_mode") or "").strip() != "recent_dialogue_review":
        return {}
    turns = extract_turns_from_recent_dialogue_report(report)
    confirmed = [f"{turn.get('role')}: {turn.get('content')}" for turn in turns if turn.get("content")]
    unknown_slots = []
    if not turns:
        unknown_slots.append("No concrete user/assistant raw turns were recovered from recent_context.")
    if not bool(report.get("reviewed_all_input")):
        unknown_slots.append("The recent-dialogue reader did not confirm full input coverage.")
    user_facing = recent_dialogue_brief_text(
        turns,
        user_input=user_input,
        compact_user_facing_summary=compact_user_facing_summary,
    )
    if not user_facing and unknown_slots:
        user_facing = "Recent raw turns were not recovered, so do not infer the recent dialogue from long-term memory."
    continuation_anchor = ""
    if turns:
        last = turns[-1]
        continuation_anchor = f"{last.get('role')}: {compact_user_facing_summary(last.get('content', ''), 180)}"
    payload = RecentDialogueBrief(
        user_facing_recent_dialogue_brief=user_facing,
        recent_turns=turns,
        confirmed_turns=confirmed,
        continuation_anchor=continuation_anchor,
        unknown_slots=unknown_slots,
        answer_boundary="recent_dialogue_only: do not speak analysis_report.situational_brief as dialogue.",
    ).model_dump()
    if isinstance(analysis_data, dict):
        payload["analysis_status"] = str(analysis_data.get("investigation_status") or "").strip()
    return payload


def field_memo_analysis_brief_for_delivery(analysis_data: dict):
    """Deprecated: FieldMemo now forwards facts, not answer-shaped seeds."""
    del analysis_data
    return ""


def split_field_memo_fact_blob(value: str) -> list[str]:
    text = str(value or "").strip()
    if not text or text in {"(none)", "(?\ub181\uc4ec)", "(unknown)"}:
        return []
    parts = [part.strip() for part in re.split(r"\s*/\s*", text) if part.strip()]
    cleaned = []
    for part in parts:
        if part.startswith(("memo_level=", "summary_scope=", "unknown_slots=")):
            continue
        if part.startswith("known_facts="):
            part = part.split("=", 1)[1].strip()
        if part:
            cleaned.append(part)
    return cleaned


def build_field_memo_user_brief(
    raw_read_report: dict,
    analysis_data: dict | None = None,
    *,
    compact_user_facing_summary: Callable[[str, int], str],
):
    report = raw_read_report if isinstance(raw_read_report, dict) else {}
    if str(report.get("read_mode") or "").strip() != "field_memo_review":
        return {}
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    if "field_memo_judgments" in analysis_data:
        memo_ids = []
        rejected_ids = []
        for judgment in analysis_data.get("field_memo_judgments", []) or []:
            if not isinstance(judgment, dict):
                continue
            memo_id = str(judgment.get("memo_id") or "").strip()
            if memo_id:
                memo_ids.append(memo_id)
            if not judgment.get("usable_for_current_goal") and memo_id:
                rejected_ids.append(memo_id)
        facts = _dedupe_keep_order([
            str(fact).strip()
            for fact in analysis_data.get("usable_field_memo_facts", []) or []
            if str(fact).strip()
        ])[:4]
        if not facts:
            return {
                "lane": "field_memo_review",
                "matched_memo_ids": _dedupe_keep_order(memo_ids),
                "rejected_memo_ids": _dedupe_keep_order(rejected_ids),
                "user_facing_memory_brief": "FieldMemo candidates were read, but no memo directly usable for this question passed the filter.",
                "known_facts": [],
                "unknown_slots": analysis_data.get("missing_slots") or ["no current-goal usable FieldMemo"],
                "filled_slots": analysis_data.get("filled_slots", {}),
                "unfilled_slots": analysis_data.get("unfilled_slots", analysis_data.get("missing_slots", [])),
                "rejected_sources": analysis_data.get("rejected_sources", []),
                "goal_contract": analysis_data.get("goal_contract", {}),
                "contract_status": analysis_data.get("contract_status", "unknown"),
                "replan_directive_for_strategist": analysis_data.get("replan_directive_for_strategist", ""),
                "answer_boundary": "field_memo_filtered_only: rejected memos must not be used as answer evidence.",
            }
        return {
            "lane": "field_memo_review",
            "matched_memo_ids": _dedupe_keep_order(memo_ids),
            "rejected_memo_ids": _dedupe_keep_order(rejected_ids),
            "user_facing_memory_brief": "FieldMemo facts that passed the current-goal filter:\n" + "\n".join(f"- {fact}" for fact in facts),
            "known_facts": facts,
            "accepted_facts": facts,
            "usable_field_memo_facts": facts,
            "unknown_slots": [],
            "filled_slots": analysis_data.get("filled_slots", {}),
            "unfilled_slots": analysis_data.get("unfilled_slots", []),
            "rejected_sources": analysis_data.get("rejected_sources", []),
            "goal_contract": analysis_data.get("goal_contract", {}),
            "contract_status": analysis_data.get("contract_status", "unknown"),
            "replan_directive_for_strategist": analysis_data.get("replan_directive_for_strategist", ""),
            "answer_boundary": "field_memo_filtered_only: FieldMemo is a recall aid, not audited truth.",
        }
    facts = []
    unknowns = []
    memo_ids = []
    ignored_kinds = {"field_failure", "interaction_repair", "policy_observation", "recall_note"}
    for item in report.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("source_type") or "").strip() != "field_memo":
            continue
        source_id = str(item.get("source_id") or "").strip()
        memo_kind = str(item.get("memo_kind") or "").strip()
        if memo_kind in ignored_kinds:
            continue
        known_fact_blob = str(item.get("known_facts") or "").strip()
        summary = str(item.get("summary") or "").strip()
        observed = str(item.get("observed_fact") or item.get("excerpt") or "").strip()
        if source_id:
            memo_ids.append(source_id)
        item_facts = [
            compact_user_facing_summary(fact, limit=180)
            for fact in split_field_memo_fact_blob(known_fact_blob)
        ]
        if not item_facts and summary:
            item_facts = [compact_user_facing_summary(summary, limit=180)]
        facts.extend(item_facts)
        unknown_blob = str(item.get("unknown_slots") or "").strip()
        if unknown_blob:
            unknowns.extend(
                compact_user_facing_summary(fact, limit=180)
                for fact in split_field_memo_fact_blob(unknown_blob)
            )
        elif observed:
            unknown_match = re.search(r"unknown_slots=([^/]+)", observed)
            if unknown_match:
                unknowns.append(compact_user_facing_summary(unknown_match.group(1), limit=120))
    facts = _dedupe_keep_order(facts)[:4]
    unknowns = _dedupe_keep_order([item for item in unknowns if item])[:3]
    if not facts:
        return {
            "lane": "field_memo_review",
            "matched_memo_ids": _dedupe_keep_order(memo_ids),
            "user_facing_memory_brief": "No directly usable FieldMemo fact was found yet.",
            "known_facts": [],
            "unknown_slots": ["no matching FieldMemo"],
            "answer_boundary": "field_memo_only",
        }
    lines = ["Relevant FieldMemo facts:"]
    lines.extend(f"- {fact}" for fact in facts)
    if unknowns:
        lines.append("Still uncertain from memo evidence: " + " / ".join(unknowns))
    return {
        "lane": "field_memo_review",
        "matched_memo_ids": _dedupe_keep_order(memo_ids),
        "user_facing_memory_brief": "\n".join(lines).strip(),
        "known_facts": facts,
        "accepted_facts": facts,
        "usable_field_memo_facts": facts,
        "unknown_slots": unknowns,
        "answer_boundary": "field_memo_only: FieldMemo is a recall aid, not audited truth.",
    }


def build_findings_first_packet(
    user_input: str,
    judge_speaker_packet: dict,
    *,
    format_findings_first_delivery: Callable[[str, dict], str],
):
    direct_text = format_findings_first_delivery(user_input, judge_speaker_packet)
    if not direct_text:
        return {}
    packet = judge_speaker_packet if isinstance(judge_speaker_packet, dict) else {}
    return {
        "lane": "findings_first",
        "findings_first_packet": {
            "user_facing_findings_brief": direct_text,
            "approved_fact_cells": packet.get("approved_fact_cells", []),
            "answer_boundary": "retrieved_findings_only",
        },
    }


def build_grounded_source_findings_packet(
    raw_read_report: dict,
    analysis_data: dict,
    user_input: str,
    *,
    analysis_has_answer_relevant_evidence: Callable[[dict], bool],
    grounded_findings_from_analysis: Callable[..., list[str]],
    compact_user_facing_summary: Callable[[str, int], str],
):
    del user_input
    if not analysis_has_answer_relevant_evidence(analysis_data):
        return {}

    facts = grounded_findings_from_analysis(analysis_data, limit=5)
    if not facts and isinstance(raw_read_report, dict):
        for item in raw_read_report.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            fact = str(item.get("observed_fact") or item.get("excerpt") or "").strip()
            if fact:
                facts.append(fact)
    facts = _dedupe_keep_order([compact_user_facing_summary(fact, limit=220) for fact in facts if str(fact).strip()])[:5]
    if not facts:
        return {}

    source_summary = ""
    if isinstance(raw_read_report, dict):
        source_summary = compact_user_facing_summary(str(raw_read_report.get("source_summary") or "").strip(), limit=180)

    lines = ["Direct findings from the source:"]
    if source_summary:
        lines.append(f"Source scope: {source_summary}")
    for idx, fact in enumerate(facts, start=1):
        lines.append(f"{idx}. {fact}")

    return {
        "lane": "findings_first",
        "source_lane": "grounded_source",
        "output_act": "deliver_findings",
        "findings_first_packet": {
            "user_facing_findings_brief": "\n".join(lines).strip(),
            "approved_fact_cells": [],
            "answer_boundary": "grounded_source_findings_only",
        },
    }


__all__ = [
    "build_field_memo_user_brief",
    "build_findings_first_packet",
    "build_grounded_source_findings_packet",
    "build_recent_dialogue_brief",
    "extract_turns_from_recent_dialogue_report",
    "field_memo_analysis_brief_for_delivery",
    "format_findings_first_delivery",
    "parse_search_result_hits",
    "recent_dialogue_brief_text",
    "split_field_memo_fact_blob",
]
