"""Clean failure packet helpers for phase 3 delivery.

This module turns already-read-but-insufficient source material into a small
failure packet. It does not decide routing or invent missing facts.
"""

from __future__ import annotations

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


def clean_failure_missing_items(raw_slots: list[str] | None):
    labels = {
        "memory.referent_fact": "the specific remembered event being referenced",
        "user.canonical_name": "the grounded identity fact being asked for",
        "character.identity": "the character identity fact being asked for",
        "character.fictionality": "whether the character is fictional or real",
        "character.relationship": "the relationship being asked about",
        "story.narrative_fact": "the story fact being asked for",
        "user.pattern_snapshot": "grounded observations about the visible pattern",
        "system.failure_or_fix": "the concrete system failure or fix",
        "current_goal_answer_seed": "usable evidence for the current answer",
    }
    cleaned = []
    for raw in raw_slots or []:
        text = str(raw or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in labels:
            cleaned.append(labels[lowered])
            continue
        if "." in text or "_" in text:
            cleaned.append("usable evidence for the current answer")
            continue
        cleaned.append(text)
    return _dedupe_keep_order(cleaned)[:5]


def build_clean_failure_packet(
    state: dict,
    analysis_data: dict,
    raw_read_report: dict,
    operation_plan: dict,
    user_goal: str,
    missing_slots: list[str] | None = None,
    rejected_sources: list[dict] | None = None,
    *,
    analysis_has_answer_relevant_evidence: Callable[[dict | None], bool],
    analysis_reports_relevance_gap: Callable[[dict | None], bool],
    compact_user_facing_summary: Callable[[str, int], str],
    normalize_short_string_list: Callable[..., list[str]],
    grounded_findings_from_analysis: Callable[..., list[str]],
):
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    raw_read_report = raw_read_report if isinstance(raw_read_report, dict) else {}
    operation_plan = operation_plan if isinstance(operation_plan, dict) else {}
    status = str(analysis_data.get("investigation_status") or "").upper()
    read_mode = str(raw_read_report.get("read_mode") or "").strip()
    items = raw_read_report.get("items", [])
    item_count = len(items) if isinstance(items, list) else 0
    source_was_read = bool(item_count or read_mode or status in {"COMPLETED", "INCOMPLETE", "EXPANSION_REQUIRED"})
    if not source_was_read:
        return {}

    no_direct_answer = (
        not analysis_has_answer_relevant_evidence(analysis_data)
        or analysis_reports_relevance_gap(analysis_data)
        or bool(analysis_data.get("can_answer_user_goal") is False)
        or status in {"INCOMPLETE", "EXPANSION_REQUIRED"}
    )
    if not no_direct_answer:
        return {}

    compact_goal = compact_user_facing_summary(user_goal or state.get("user_input", ""), 140) or "the current question"
    source_summary = (
        str(raw_read_report.get("source_summary") or "").strip()
        or str(analysis_data.get("situational_brief") or "").strip()
    )
    source_summary = compact_user_facing_summary(source_summary, 220)

    missing = []
    for raw in (
        missing_slots
        or analysis_data.get("unfilled_slots")
        or analysis_data.get("missing_slots")
        or analysis_data.get("missing_info")
        or []
    ):
        normalized = str(raw or "").strip()
        if normalized:
            missing.append(normalized)
    missing = clean_failure_missing_items(_dedupe_keep_order(missing)[:5])

    rejected = rejected_sources if isinstance(rejected_sources, list) else []
    if not rejected:
        for judgment in analysis_data.get("source_judgments", []) or []:
            if not isinstance(judgment, dict):
                continue
            status_text = str(judgment.get("source_status") or "").strip().lower()
            objection = str(judgment.get("objection_reason") or "").strip()
            search_needed = str(judgment.get("search_needed") or "").strip().lower() == "true"
            if status_text not in {"pass", "completed"} or objection or search_needed:
                rejected.append({
                    "source_id": str(judgment.get("source_id") or judgment.get("memo_id") or "").strip(),
                    "reason": compact_user_facing_summary(objection or "current_goal_not_answered", 180),
                    "missing_info": normalize_short_string_list(judgment.get("missing_info", []) or [], limit=3),
                })
    rejected = [item for item in rejected if isinstance(item, dict)][:6]

    failure_kind = "missing_direct_answer"
    if rejected and not grounded_findings_from_analysis(analysis_data, limit=1):
        failure_kind = "irrelevant_source"
    if read_mode == "field_memo_review":
        failure_kind = "field_memo_no_answer"
    elif read_mode == "recent_dialogue_review":
        failure_kind = "recent_dialogue_no_answer"

    read_scope_bits = []
    if read_mode:
        read_scope_bits.append(f"read_mode={read_mode}")
    if item_count:
        read_scope_bits.append(f"items={item_count}")
    source_lane = str(operation_plan.get("source_lane") or "").strip()
    if source_lane:
        read_scope_bits.append(f"source_lane={source_lane}")
    read_scope = ", ".join(read_scope_bits) if read_scope_bits else "source_read"

    if read_mode == "field_memo_review":
        seed = (
            f"I read FieldMemo candidates, but did not find a memo that directly answers `{compact_goal}`. "
            "I will exclude irrelevant candidates from the answer evidence."
        )
    elif read_mode == "full_raw_review":
        seed = (
            f"I read the raw source, but did not find direct evidence for `{compact_goal}`. "
            "I will not summarize unrelated source content as if it answered the question."
        )
    else:
        seed = (
            f"I checked the available material, but direct evidence for `{compact_goal}` is still insufficient. "
            "I will not treat unrelated candidates as evidence."
        )
    if missing:
        seed += " Missing: " + " / ".join(missing[:3]) + "."

    return {
        "clean_failure": True,
        "failure_kind": failure_kind,
        "user_goal": compact_goal,
        "read_scope": read_scope,
        "source_summary": source_summary,
        "missing_slots": missing,
        "rejected_sources": rejected,
        "message_seed": seed,
        "answer_boundary": "clean_failure_only: do not summarize rejected source contents as findings.",
    }


__all__ = [
    "build_clean_failure_packet",
    "clean_failure_missing_items",
]
