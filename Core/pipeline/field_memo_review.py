"""FieldMemo review and delivery-gate helpers.

This module filters FieldMemo candidates into current-goal usable facts. It
keeps the existing deterministic guard behavior but removes the review cluster
from the graph god-file.
"""

from __future__ import annotations

import json
import re
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


def field_memo_evidence_text(item: dict):
    """Text allowed to prove a user-facing fact."""
    if not isinstance(item, dict):
        return ""
    fields = [
        "summary",
        "known_facts",
        "observed_fact",
        "excerpt",
    ]
    return " ".join(str(item.get(field) or "") for field in fields)


def field_memo_metadata_text(item: dict):
    if not isinstance(item, dict):
        return ""
    fields = [
        "source_id",
        "source_type",
        "memo_kind",
        "summary_scope",
        "branch_path",
        "root_entity",
        "unknown_slots",
    ]
    return " ".join(str(item.get(field) or "") for field in fields)


def field_memo_text(item: dict):
    if not isinstance(item, dict):
        return ""
    fields = [
        "source_id",
        "memo_kind",
        "summary_scope",
        "branch_path",
        "root_entity",
        "summary",
        "known_facts",
        "unknown_slots",
        "observed_fact",
        "excerpt",
    ]
    return " ".join(str(item.get(field) or "") for field in fields)


def rejected_sources_from_field_memo_judgments(judgments: list[dict]):
    rejected = []
    for judgment in judgments or []:
        if not isinstance(judgment, dict) or judgment.get("usable_for_current_goal"):
            continue
        memo_id = str(judgment.get("memo_id") or "").strip()
        if not memo_id:
            continue
        rejected.append({
            "source_id": memo_id,
            "source_type": "field_memo",
            "evidence_kind": str(judgment.get("evidence_kind") or "unknown").strip(),
            "relevance": str(judgment.get("relevance") or "irrelevant").strip(),
            "reason": str(judgment.get("rejection_reason") or "not usable for current goal").strip(),
        })
    return rejected


def field_memo_tokens(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "").lower())
    tokens = re.findall(r"[A-Za-z0-9_\-]{2,}|[\uac00-\ud7a3]{2,}", normalized)
    stopwords = {
        "assistant", "fieldmemo", "known", "facts", "unknown", "slots",
        "memo", "level", "summary", "query", "search", "result",
    }
    return {token for token in tokens if token not in stopwords and len(token) >= 2}


def field_memo_facts_from_item(
    item: dict,
    *,
    split_field_memo_fact_blob: Callable[[str], list[str]],
    compact_user_facing_summary: Callable[[str, int], str],
):
    facts = split_field_memo_fact_blob(str((item or {}).get("known_facts") or ""))
    summary = str((item or {}).get("summary") or "").strip()
    observed = str((item or {}).get("observed_fact") or (item or {}).get("excerpt") or "").strip()
    if not facts and summary:
        facts = [compact_user_facing_summary(summary, limit=220)]
    if not facts and observed:
        facts = [compact_user_facing_summary(observed, limit=220)]
    return _dedupe_keep_order([fact for fact in facts if fact])[:5]


def field_memo_evidence_kind(
    item: dict,
    *,
    split_field_memo_fact_blob: Callable[[str], list[str]],
    compact_user_facing_summary: Callable[[str, int], str],
):
    memo_kind = str((item or {}).get("memo_kind") or "").strip().lower()
    summary_scope = str((item or {}).get("summary_scope") or "").strip().lower()
    branch_path = str((item or {}).get("branch_path") or "").strip().lower()
    trace_markers = {"field_failure", "policy_observation", "recall_note", "search_result"}
    if memo_kind in trace_markers or any(marker in " ".join([memo_kind, summary_scope, branch_path]) for marker in ["tool", "routing", "failure"]):
        return "non_fact_trace"
    if memo_kind in {"verified_fact_packet", "user_correction_fact", "layered_synthesis", "synthesismemo", "narrative_note", "field_observation"}:
        return "fact_packet"
    if field_memo_facts_from_item(
        item,
        split_field_memo_fact_blob=split_field_memo_fact_blob,
        compact_user_facing_summary=compact_user_facing_summary,
    ):
        return "fact_packet"
    return "unknown"


def judge_field_memo_item_for_goal(
    item: dict,
    user_input: str,
    *,
    split_field_memo_fact_blob: Callable[[str], list[str]],
    compact_user_facing_summary: Callable[[str, int], str],
    derive_user_goal_contract: Callable[..., dict],
    contract_satisfied_by_facts: Callable[..., bool],
):
    del user_input, derive_user_goal_contract, contract_satisfied_by_facts
    source_id = str((item or {}).get("source_id") or "").strip() or "unknown_field_memo"
    evidence_kind = field_memo_evidence_kind(
        item,
        split_field_memo_fact_blob=split_field_memo_fact_blob,
        compact_user_facing_summary=compact_user_facing_summary,
    )
    facts = field_memo_facts_from_item(
        item,
        split_field_memo_fact_blob=split_field_memo_fact_blob,
        compact_user_facing_summary=compact_user_facing_summary,
    )
    status = str((item or {}).get("status") or "active").strip().lower()
    if status in {"rejected", "superseded"}:
        return {
            "memo_id": source_id,
            "relevance": "irrelevant",
            "evidence_kind": evidence_kind,
            "usable_for_current_goal": False,
            "accepted_facts": [],
            "rejected_facts": facts,
            "rejection_reason": f"FieldMemo status is {status}.",
            "recommended_followup_query": [],
        }
    if evidence_kind == "non_fact_trace":
        return {
            "memo_id": source_id,
            "relevance": "irrelevant",
            "evidence_kind": evidence_kind,
            "usable_for_current_goal": False,
            "accepted_facts": [],
            "rejected_facts": facts,
            "rejection_reason": "FieldMemo is a trace/search/failure event, not a verified fact packet.",
            "recommended_followup_query": [],
        }
    if not facts:
        return {
            "memo_id": source_id,
            "relevance": "irrelevant",
            "evidence_kind": evidence_kind,
            "usable_for_current_goal": False,
            "accepted_facts": [],
            "rejected_facts": [],
            "rejection_reason": "FieldMemo has no usable known_facts or summary.",
            "recommended_followup_query": [],
        }
    return {
        "memo_id": source_id,
        "relevance": "indirect",
        "evidence_kind": evidence_kind,
        "usable_for_current_goal": False,
        "accepted_facts": [],
        "rejected_facts": facts,
        "rejection_reason": "FieldMemo is only a retrieval candidate; phase_2b did not accept it for the current goal.",
        "recommended_followup_query": [],
    }


def field_memo_judgments_from_source_judgments(
    source_judgments: list[dict],
    item_ids: set[str],
    *,
    normalize_short_string_list: Callable[..., list[str]],
):
    normalized = []
    for judgment in source_judgments or []:
        if not isinstance(judgment, dict):
            continue
        source_type = str(judgment.get("source_type") or "").strip()
        source_id = str(judgment.get("source_id") or judgment.get("memo_id") or "").strip()
        if source_type != "field_memo" and source_id not in item_ids:
            continue
        accepted = _dedupe_keep_order(
            [str(fact).strip() for fact in judgment.get("accepted_facts", []) or [] if str(fact).strip()]
        )[:5]
        rejected = _dedupe_keep_order(
            [
                str(fact).strip()
                for fact in (judgment.get("rejected_facts", []) or judgment.get("contested_facts", []) or [])
                if str(fact).strip()
            ]
        )[:5]
        status_text = str(judgment.get("source_status") or "").strip().lower()
        objection = str(judgment.get("objection_reason") or judgment.get("rejection_reason") or "").strip()
        search_needed = str(judgment.get("search_needed") or "").strip().lower() == "true"
        usable = bool(accepted) and not objection and not search_needed
        if status_text:
            usable = usable and status_text in {"pass", "completed", "supported", "accepted", "relevant"}
        if status_text in {"fail", "failed", "objection", "rejected", "irrelevant"}:
            usable = False
        normalized.append({
            "memo_id": source_id or "unknown_field_memo",
            "relevance": "direct" if usable else "rejected_by_phase_2b",
            "evidence_kind": "phase_2b_fact_packet",
            "usable_for_current_goal": usable,
            "accepted_facts": accepted if usable else [],
            "rejected_facts": [] if usable else rejected or accepted,
            "rejection_reason": "" if usable else objection or "phase_2b did not accept this FieldMemo for the current goal.",
            "recommended_followup_query": normalize_short_string_list(judgment.get("missing_info", []) or [], limit=4),
        })
    return normalized


def field_memo_judgments_from_analysis_judgments(
    field_memo_judgments: list[dict],
    item_ids: set[str],
    *,
    normalize_short_string_list: Callable[..., list[str]],
):
    allowed_evidence_kinds = {
        "self_report",
        "identity_note",
        "narrative",
        "creative_worldbuilding",
        "tool_event",
        "search_result",
        "conversation_context",
        "fact_packet",
        "non_fact_trace",
        "phase_2b_fact_packet",
        "unknown",
    }
    normalized = []
    for judgment in field_memo_judgments or []:
        if not isinstance(judgment, dict):
            continue
        memo_id = str(judgment.get("memo_id") or judgment.get("source_id") or "").strip()
        if item_ids and memo_id not in item_ids:
            continue
        relevance = str(judgment.get("relevance") or "irrelevant").strip()
        if relevance not in {"direct", "indirect", "irrelevant"}:
            relevance = "irrelevant"
        evidence_kind = str(judgment.get("evidence_kind") or "unknown").strip()
        if evidence_kind not in allowed_evidence_kinds:
            evidence_kind = "unknown"
        accepted = _dedupe_keep_order(
            [str(fact).strip() for fact in judgment.get("accepted_facts", []) or [] if str(fact).strip()]
        )[:5]
        rejected = _dedupe_keep_order(
            [str(fact).strip() for fact in judgment.get("rejected_facts", []) or [] if str(fact).strip()]
        )[:5]
        rejection_reason = str(judgment.get("rejection_reason") or "").strip()
        usable = (
            bool(judgment.get("usable_for_current_goal"))
            and bool(accepted)
            and relevance in {"direct", "indirect"}
            and not rejection_reason
        )
        normalized.append({
            "memo_id": memo_id or "unknown_field_memo",
            "relevance": relevance if usable else "irrelevant",
            "evidence_kind": evidence_kind,
            "usable_for_current_goal": usable,
            "accepted_facts": accepted if usable else [],
            "rejected_facts": [] if usable else rejected or accepted,
            "rejection_reason": "" if usable else rejection_reason or "phase_2b did not accept this FieldMemo for the current goal.",
            "recommended_followup_query": normalize_short_string_list(
                judgment.get("recommended_followup_query", []) or [],
                limit=4,
            ),
        })
    return normalized


def enforce_field_memo_judgments(
    analysis_dict: dict,
    raw_read_report: dict,
    user_input: str,
    *,
    split_field_memo_fact_blob: Callable[[str], list[str]],
    compact_user_facing_summary: Callable[[str, int], str],
    derive_user_goal_contract: Callable[..., dict],
    contract_satisfied_by_facts: Callable[..., bool],
    contract_status_packet: Callable[..., tuple],
    filled_slots_from_contract: Callable[..., dict],
    normalize_short_string_list: Callable[..., list[str]],
):
    if not isinstance(analysis_dict, dict):
        analysis_dict = {}
    if not isinstance(raw_read_report, dict):
        return analysis_dict
    if str(raw_read_report.get("read_mode") or "").strip() != "field_memo_review":
        return analysis_dict

    normalized = json.loads(json.dumps(analysis_dict, ensure_ascii=False))
    items = [item for item in raw_read_report.get("items", []) or [] if isinstance(item, dict)]
    item_ids = {str(item.get("source_id") or "").strip() for item in items if str(item.get("source_id") or "").strip()}
    judgments = field_memo_judgments_from_analysis_judgments(
        normalized.get("field_memo_judgments", []) or [],
        item_ids,
        normalize_short_string_list=normalize_short_string_list,
    )
    if not judgments:
        judgments = field_memo_judgments_from_source_judgments(
            normalized.get("source_judgments", []) or [],
            item_ids,
            normalize_short_string_list=normalize_short_string_list,
        )
    if not judgments:
        judgments = [
            judge_field_memo_item_for_goal(
                item,
                user_input,
                split_field_memo_fact_blob=split_field_memo_fact_blob,
                compact_user_facing_summary=compact_user_facing_summary,
                derive_user_goal_contract=derive_user_goal_contract,
                contract_satisfied_by_facts=contract_satisfied_by_facts,
            )
            for item in items
        ]
    usable_judgments = [item for item in judgments if item.get("usable_for_current_goal")]
    usable_facts = []
    for judgment in usable_judgments:
        usable_facts.extend(str(fact).strip() for fact in judgment.get("accepted_facts", []) or [] if str(fact).strip())
    usable_facts = _dedupe_keep_order(usable_facts)[:8]
    rejected_ids = [
        str(item.get("memo_id") or "").strip()
        for item in judgments
        if not item.get("usable_for_current_goal") and str(item.get("memo_id") or "").strip()
    ]

    goal_contract = derive_user_goal_contract(user_input, source_lane="field_memo_review")
    contract_status, missing_slots, replan_directive = contract_status_packet(
        goal_contract,
        usable_facts,
        "",
    )
    filled_slots = filled_slots_from_contract(goal_contract, usable_facts, "")
    unfilled_slots = missing_slots if not filled_slots else []
    rejected_sources = rejected_sources_from_field_memo_judgments(judgments)
    can_answer = bool(usable_facts and contract_status == "satisfied")

    normalized["field_memo_judgments"] = judgments
    normalized["usable_field_memo_facts"] = usable_facts
    normalized["rejected_field_memo_ids"] = _dedupe_keep_order(rejected_ids)
    normalized["can_answer_user_goal"] = can_answer
    normalized["goal_contract"] = goal_contract
    normalized["contract_status"] = contract_status
    normalized["missing_slots"] = missing_slots
    normalized["filled_slots"] = filled_slots
    normalized["unfilled_slots"] = unfilled_slots
    normalized["rejected_sources"] = rejected_sources
    normalized["replan_directive_for_strategist"] = replan_directive

    non_field_judgments = [
        item for item in normalized.get("source_judgments", []) or []
        if isinstance(item, dict) and str(item.get("source_type") or "").strip() != "field_memo"
    ]
    field_source_judgments = []
    for judgment in judgments:
        accepted = _dedupe_keep_order([str(f).strip() for f in judgment.get("accepted_facts", []) or [] if str(f).strip()])[:5]
        rejected = _dedupe_keep_order([str(f).strip() for f in judgment.get("rejected_facts", []) or [] if str(f).strip()])[:5]
        field_source_judgments.append({
            "source_id": str(judgment.get("memo_id") or "").strip(),
            "source_type": "field_memo",
            "source_status": "pass" if judgment.get("usable_for_current_goal") else "objection",
            "accepted_facts": accepted,
            "contested_facts": rejected,
            "objection_reason": str(judgment.get("rejection_reason") or "").strip(),
            "missing_info": _dedupe_keep_order([str(q).strip() for q in judgment.get("recommended_followup_query", []) or [] if str(q).strip()])[:4],
            "search_needed": not bool(judgment.get("usable_for_current_goal")),
        })
    normalized["source_judgments"] = non_field_judgments + field_source_judgments

    non_field_evidences = [
        item for item in normalized.get("evidences", []) or []
        if isinstance(item, dict) and str(item.get("source_type") or "").strip() != "field_memo"
    ]
    field_evidences = []
    for judgment in usable_judgments:
        source_id = str(judgment.get("memo_id") or "").strip()
        for fact in judgment.get("accepted_facts", []) or []:
            fact_text = str(fact).strip()
            if source_id and fact_text:
                field_evidences.append({
                    "source_id": source_id,
                    "source_type": "field_memo",
                    "extracted_fact": fact_text,
                })
    normalized["evidences"] = non_field_evidences + field_evidences

    if can_answer:
        normalized["investigation_status"] = "COMPLETED"
        normalized["situational_brief"] = "FieldMemo usable facts: " + " / ".join(usable_facts[:4])
        normalized["analytical_thought"] = (
            str(normalized.get("analytical_thought") or "").strip()
            + "\nFieldMemo filter: only current-goal usable memo facts were forwarded."
        ).strip()
    else:
        normalized["investigation_status"] = "INCOMPLETE"
        rejected_count = len(rejected_ids)
        missing_text = f" Missing: {', '.join(missing_slots)}." if missing_slots else ""
        normalized["situational_brief"] = (
            f"Read {len(items)} FieldMemo candidates, but none directly answer the current goal. "
            f"Excluded {rejected_count} irrelevant candidates from phase_3 evidence.{missing_text}"
        )
        normalized["analytical_thought"] = (
            str(normalized.get("analytical_thought") or "").strip()
            + "\nFieldMemo filter: no memo survived the current-goal relevance gate or goal contract slot check."
        ).strip()
    return normalized


def field_memo_review_has_concrete_memos(raw_read_report: dict):
    report = raw_read_report if isinstance(raw_read_report, dict) else {}
    if str(report.get("read_mode") or "").strip() != "field_memo_review":
        return False
    for item in report.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("source_type") or "").strip() != "field_memo":
            continue
        source_id = str(item.get("source_id") or "").strip()
        observed = str(item.get("observed_fact") or item.get("excerpt") or "").strip()
        if source_id and source_id != "field_memo_empty" and observed:
            return True
    return False


def field_memo_packet_ready_for_delivery(
    packet: dict,
    analysis_data: dict | None = None,
    user_input: str = "",
    *,
    derive_user_goal_contract: Callable[..., dict],
    contract_satisfied_by_facts: Callable[..., bool],
):
    packet = packet if isinstance(packet, dict) else {}
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    if packet.get("can_answer_user_goal") is False:
        return False
    if analysis_data and analysis_data.get("can_answer_user_goal") is False:
        return False
    contract = packet.get("goal_contract") if isinstance(packet, dict) else {}
    if not isinstance(contract, dict) or not contract:
        contract = derive_user_goal_contract(user_input, source_lane="field_memo_review")
    contract_status = str((analysis_data or {}).get("contract_status") or packet.get("contract_status") or "").strip()
    missing_slots = packet.get("missing_slots", packet.get("unknown_slots", []))
    if not isinstance(missing_slots, list):
        missing_slots = [missing_slots] if str(missing_slots or "").strip() else []
    missing_slots = [str(slot).strip() for slot in missing_slots if str(slot).strip()]
    facts = []
    for source in (
        (analysis_data or {}).get("usable_field_memo_facts", []),
        (analysis_data or {}).get("accepted_facts", []),
        packet.get("usable_field_memo_facts", []),
        packet.get("accepted_facts", []),
        packet.get("known_facts", []),
        (packet.get("field_memo_recall_packet", {}) if isinstance(packet.get("field_memo_recall_packet", {}), dict) else {}).get("known_facts", []),
    ):
        if isinstance(source, list):
            facts.extend(str(fact).strip() for fact in source if str(fact).strip())
    facts = _dedupe_keep_order(facts)[:8]
    if not facts:
        return False
    if contract_status and contract_status != "satisfied":
        return False
    if missing_slots:
        return False
    return contract_satisfied_by_facts(contract, facts, "")


__all__ = [
    "enforce_field_memo_judgments",
    "field_memo_evidence_kind",
    "field_memo_evidence_text",
    "field_memo_facts_from_item",
    "field_memo_judgments_from_analysis_judgments",
    "field_memo_judgments_from_source_judgments",
    "field_memo_metadata_text",
    "field_memo_packet_ready_for_delivery",
    "field_memo_review_has_concrete_memos",
    "field_memo_text",
    "field_memo_tokens",
    "judge_field_memo_item_for_goal",
    "rejected_sources_from_field_memo_judgments",
]
