"""Prompt and relay packet helpers for the ANIMA field-loop pipeline.

These helpers shape internal source packets for prompts and downstream judges.
They must preserve key names and payload shape unless a behavior change is
intended and covered by tests.
"""

from __future__ import annotations

import json

from .plans import (
    empty_action_plan,
    empty_advocate_report,
    empty_critic_report,
    empty_verdict_board,
    normalize_action_plan,
    normalize_convergence_state,
    normalize_delivery_readiness,
    normalize_goal_lock,
    normalize_operation_plan,
    normalize_short_string_list,
)
from ..warroom.state import _normalize_war_room_operating_contract


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


def _clip_text(value, limit: int = 1200):
    text = str(value or "").strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _clip_string_list(values, limit: int = 6, text_limit: int = 240):
    if not isinstance(values, list):
        return []
    return [
        item
        for item in (_clip_text(value, text_limit) for value in values[:limit])
        if item
    ]


def _clip_list(values, limit: int = 8):
    if not isinstance(values, list):
        return []
    return values[: max(limit, 0)]


def _clip_mapping(mapping, limit: int = 16, value_limit: int = 240):
    if not isinstance(mapping, dict):
        return {}
    packet = {}
    for idx, (key, value) in enumerate(mapping.items()):
        if idx >= limit:
            break
        key_text = _clip_text(key, 120)
        if isinstance(value, (str, int, float, bool)) or value is None:
            packet[key_text] = _clip_text(value, value_limit)
        elif isinstance(value, list):
            packet[key_text] = _clip_string_list(value, 6, value_limit)
        elif isinstance(value, dict):
            packet[key_text] = _clip_mapping(value, 8, value_limit)
        else:
            packet[key_text] = _clip_text(value, value_limit)
    return packet


def _compact_source_judgments_for_prompt(values, limit: int = 8):
    projected = []
    for judgment in _clip_list(values, limit):
        if not isinstance(judgment, dict):
            continue
        projected.append({
            "source_id": _clip_text(judgment.get("source_id"), 160),
            "source_type": _clip_text(judgment.get("source_type"), 80),
            "source_status": _clip_text(judgment.get("source_status") or judgment.get("status"), 80),
            "accepted_facts": _clip_string_list(judgment.get("accepted_facts", []), 5, 260),
            "contested_facts": _clip_string_list(judgment.get("contested_facts", []), 4, 260),
            "missing_info": _clip_string_list(judgment.get("missing_info", []), 4, 220),
            "objection_reason": _clip_text(judgment.get("objection_reason"), 320),
            "search_needed": bool(judgment.get("search_needed", False)),
        })
    return projected


def _compact_field_memo_judgments_for_prompt(values, limit: int = 8):
    projected = []
    for judgment in _clip_list(values, limit):
        if not isinstance(judgment, dict):
            continue
        projected.append({
            "memo_id": _clip_text(judgment.get("memo_id"), 180),
            "relevance": _clip_text(judgment.get("relevance"), 80),
            "evidence_kind": _clip_text(judgment.get("evidence_kind"), 80),
            "usable_for_current_goal": bool(judgment.get("usable_for_current_goal")),
            "accepted_facts": _clip_string_list(judgment.get("accepted_facts", []), 5, 260),
            "rejected_facts": _clip_string_list(judgment.get("rejected_facts", []), 4, 220),
            "rejection_reason": _clip_text(judgment.get("rejection_reason"), 260),
            "recommended_followup_query": _clip_string_list(judgment.get("recommended_followup_query", []), 3, 180),
        })
    return projected


def _compact_evidence_items_for_prompt(values, limit: int = 10):
    projected = []
    for item in _clip_list(values, limit):
        if not isinstance(item, dict):
            continue
        projected.append({
            "source_id": _clip_text(item.get("source_id"), 160),
            "source_type": _clip_text(item.get("source_type"), 80),
            "extracted_fact": _clip_text(item.get("extracted_fact") or item.get("fact") or item.get("excerpt"), 280),
        })
    return projected


def _compact_rejected_sources_for_prompt(values, limit: int = 6):
    projected = []
    for item in _clip_list(values, limit):
        if isinstance(item, dict):
            projected.append({
                "source_id": _clip_text(item.get("source_id"), 160),
                "source_type": _clip_text(item.get("source_type"), 80),
                "reason": _clip_text(item.get("reason") or item.get("rejection_reason"), 260),
            })
        else:
            text = _clip_text(item, 260)
            if text:
                projected.append(text)
    return projected


def compact_s_thinking_packet_for_prompt(packet: dict, *, role: str = "general"):
    source = packet if isinstance(packet, dict) else {}
    situation = source.get("situation_thinking", {})
    if not isinstance(situation, dict):
        situation = {}
    loop_summary = source.get("loop_summary", {})
    if not isinstance(loop_summary, dict):
        loop_summary = {}
    next_direction = source.get("next_direction", {})
    if not isinstance(next_direction, dict):
        next_direction = {}
    routing = source.get("routing_decision", {})
    if not isinstance(routing, dict):
        routing = {}
    return {
        "schema": _clip_text(source.get("schema"), 80) or "SThinkingPacket.v1",
        "situation_thinking": {
            "user_intent": _clip_text(situation.get("user_intent"), 80),
            "domain": _clip_text(situation.get("domain"), 80),
            "key_facts_needed": _clip_string_list(situation.get("key_facts_needed", []), 4, 140),
        },
        "loop_summary": {
            "attempted_so_far": _clip_string_list(loop_summary.get("attempted_so_far", []), 5, 80),
            "current_evidence_state": _clip_text(loop_summary.get("current_evidence_state"), 180),
            "gaps": _clip_string_list(loop_summary.get("gaps", []), 4, 140),
        },
        "next_direction": {
            "suggested_focus": _clip_text(next_direction.get("suggested_focus"), 180),
            "avoid": _clip_string_list(next_direction.get("avoid", []), 4, 120),
        },
        "routing_decision": {
            "next_node": _clip_text(routing.get("next_node"), 40),
            "reason": _clip_text(routing.get("reason"), 220 if role == "strategist" else 160),
        },
    }


def s_thinking_packet_for_prompt(packet: dict, *, role: str = "general"):
    if not isinstance(packet, dict) or not packet:
        return "No s_thinking_packet is available."
    try:
        return json.dumps(compact_s_thinking_packet_for_prompt(packet, role=role), ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


def compact_rescue_handoff_for_prompt(packet: dict, *, role: str = "phase_3"):
    source = packet if isinstance(packet, dict) else {}
    return {
        "schema": _clip_text(source.get("schema"), 80) or "RescueHandoffPacket.v1",
        "attempted_path_summary": _clip_string_list(source.get("attempted_path", []), 4, 80),
        "preserved_evidences": _compact_evidence_items_for_prompt(source.get("preserved_evidences", []), limit=6),
        "preserved_field_memo_facts": _clip_string_list(source.get("preserved_field_memo_facts", []), 6, 220),
        "rejected_only": _compact_rejected_sources_for_prompt(source.get("rejected_only", []), limit=4),
        "what_we_know": _clip_string_list(source.get("what_we_know", []), 6, 220),
        "what_we_failed": _clip_string_list(source.get("what_we_failed", []), 4, 160),
        "speaker_tone_hint": _clip_text(source.get("speaker_tone_hint"), 80),
        "user_facing_label": _clip_text(source.get("user_facing_label"), 80),
    }


def compact_raw_read_report_for_prompt(
    raw_read_report: dict,
    *,
    item_limit: int = 12,
    excerpt_limit: int = 900,
    observed_fact_limit: int = 700,
    known_facts_limit: int = 700,
    item_summary_limit: int = 360,
    source_summary_limit: int = 900,
    coverage_notes_limit: int = 900,
):
    if not isinstance(raw_read_report, dict):
        return {}
    items = []
    for item in _clip_list(raw_read_report.get("items", []), item_limit):
        if not isinstance(item, dict):
            continue
        items.append({
            "source_id": _clip_text(item.get("source_id"), 180),
            "source_type": _clip_text(item.get("source_type"), 80),
            "excerpt": _clip_text(item.get("excerpt"), excerpt_limit),
            "observed_fact": _clip_text(item.get("observed_fact"), observed_fact_limit),
            "known_facts": _clip_text(item.get("known_facts"), known_facts_limit),
            "summary": _clip_text(item.get("summary"), item_summary_limit),
            "memo_kind": _clip_text(item.get("memo_kind"), 80),
        })
    return {
        "read_mode": _clip_text(raw_read_report.get("read_mode"), 80),
        "reviewed_all_input": bool(raw_read_report.get("reviewed_all_input", False)),
        "source_summary": _clip_text(raw_read_report.get("source_summary"), source_summary_limit),
        "items": items,
        "coverage_notes": _clip_text(raw_read_report.get("coverage_notes"), coverage_notes_limit),
    }


def compact_analysis_for_prompt(analysis_data: dict, include_thought: bool = True, *, role: str = "general"):
    if not isinstance(analysis_data, dict):
        return {}
    role = str(role or "general").strip()
    status_packet = {
        "investigation_status": _clip_text(analysis_data.get("investigation_status"), 80),
        "contract_status": _clip_text(analysis_data.get("contract_status"), 80),
        "can_answer_user_goal": bool(analysis_data.get("can_answer_user_goal", False)),
        "missing_slots": _clip_string_list(analysis_data.get("missing_slots", []), 5, 120),
        "unfilled_slots": _clip_string_list(analysis_data.get("unfilled_slots", analysis_data.get("missing_slots", [])), 5, 120),
        "situational_brief": _clip_text(analysis_data.get("situational_brief"), 360),
    }
    if role in {"start_gate", "-1s"}:
        return status_packet
    if role in {"strategist", "-1a"}:
        packet = {
            **status_packet,
            "evidences": _compact_evidence_items_for_prompt(analysis_data.get("evidences", []), limit=8),
            "usable_field_memo_facts": _clip_string_list(analysis_data.get("usable_field_memo_facts", []), 6, 220),
            "replan_directive_for_strategist": _clip_text(analysis_data.get("replan_directive_for_strategist"), 300),
        }
        if include_thought:
            packet["analytical_thought"] = _clip_text(analysis_data.get("analytical_thought"), 420)
        return packet
    if role in {"readiness", "auditor", "-1b"}:
        packet = {
            **status_packet,
            "evidences": _compact_evidence_items_for_prompt(analysis_data.get("evidences", []), limit=8),
            "source_judgments": _compact_source_judgments_for_prompt(analysis_data.get("source_judgments", []), limit=6),
            "usable_field_memo_facts": _clip_string_list(analysis_data.get("usable_field_memo_facts", []), 5, 220),
            "rejected_sources": _compact_rejected_sources_for_prompt(analysis_data.get("rejected_sources", []), limit=4),
        }
        if include_thought:
            packet["analytical_thought"] = _clip_text(analysis_data.get("analytical_thought"), 360)
        return packet
    if role in {"delivery", "phase_3"}:
        accepted_facts = []
        for judgment in analysis_data.get("source_judgments", []) or []:
            if isinstance(judgment, dict):
                accepted_facts.extend(judgment.get("accepted_facts", []) or [])
        return {
            "investigation_status": status_packet["investigation_status"],
            "contract_status": status_packet["contract_status"],
            "usable_field_memo_facts": _clip_string_list(analysis_data.get("usable_field_memo_facts", []), 6, 220),
            "accepted_facts": _clip_string_list(accepted_facts, 6, 220),
        }

    packet = {
        "evidences": _compact_evidence_items_for_prompt(analysis_data.get("evidences", [])),
        "source_judgments": _compact_source_judgments_for_prompt(analysis_data.get("source_judgments", [])),
        "field_memo_judgments": _compact_field_memo_judgments_for_prompt(analysis_data.get("field_memo_judgments", [])),
        "usable_field_memo_facts": _clip_string_list(analysis_data.get("usable_field_memo_facts", []), 8, 260),
        "rejected_field_memo_ids": _clip_string_list(analysis_data.get("rejected_field_memo_ids", []), 8, 180),
        "goal_contract": _clip_mapping(analysis_data.get("goal_contract", {}), 16, 240),
        "contract_status": _clip_text(analysis_data.get("contract_status"), 80),
        "missing_slots": _clip_string_list(analysis_data.get("missing_slots", []), 8, 160),
        "filled_slots": _clip_mapping(analysis_data.get("filled_slots", {}), 12, 240),
        "unfilled_slots": _clip_string_list(analysis_data.get("unfilled_slots", analysis_data.get("missing_slots", [])), 8, 160),
        "rejected_sources": _compact_rejected_sources_for_prompt(analysis_data.get("rejected_sources", [])),
        "replan_directive_for_strategist": _clip_text(analysis_data.get("replan_directive_for_strategist"), 480),
        "situational_brief": _clip_text(analysis_data.get("situational_brief"), 700),
        "investigation_status": _clip_text(analysis_data.get("investigation_status"), 80),
        "can_answer_user_goal": bool(analysis_data.get("can_answer_user_goal", False)),
    }
    if include_thought:
        packet["analytical_thought"] = _clip_text(analysis_data.get("analytical_thought"), 900)
    return packet


def compact_working_memory_for_prompt(working_memory: dict, *, role: str = "general"):
    if not isinstance(working_memory, dict) or not working_memory:
        return {}

    dialogue = working_memory.get("dialogue_state", {}) if isinstance(working_memory.get("dialogue_state", {}), dict) else {}
    temporal = working_memory.get("temporal_context", {}) if isinstance(working_memory.get("temporal_context", {}), dict) else {}
    writer = working_memory.get("memory_writer", {}) if isinstance(working_memory.get("memory_writer", {}), dict) else {}
    evidence = working_memory.get("evidence_state", {}) if isinstance(working_memory.get("evidence_state", {}), dict) else {}
    response = working_memory.get("response_contract", {}) if isinstance(working_memory.get("response_contract", {}), dict) else {}

    pending = dialogue.get("pending_dialogue_act", {})
    if not isinstance(pending, dict):
        pending = {}

    role = str(role or "general").strip()
    pending_packet = {
        "kind": _clip_text(pending.get("kind"), 60),
        "target": _clip_text(pending.get("target"), 180 if role == "phase_3" else 220),
        "expected_user_responses": _clip_string_list(pending.get("expected_user_responses", []), 5 if role == "phase_3" else 8, 40),
        "expires_after_turns": pending.get("expires_after_turns", 0),
        "confidence": pending.get("confidence", 0.0),
    }

    if role in {"start_gate", "-1s"}:
        return {
            "dialogue_state": {
                "user_dialogue_act": _clip_text(dialogue.get("user_dialogue_act"), 80),
                "pending_dialogue_act": pending_packet,
                "continuation_expected": bool(dialogue.get("continuation_expected")),
            },
            "memory_writer": {
                "short_term_context": _clip_text(writer.get("short_term_context"), 260),
                "assistant_obligation_next_turn": _clip_text(writer.get("assistant_obligation_next_turn"), 180),
            },
            "evidence_state": {
                "last_investigation_status": _clip_text(evidence.get("last_investigation_status"), 80),
                "verdict_action": _clip_text(evidence.get("verdict_action"), 80),
                "unresolved_questions": _clip_string_list(evidence.get("unresolved_questions", []), 3, 160),
            },
        }

    if role in {"strategist", "-1a"}:
        return {
            "dialogue_state": {
                "user_dialogue_act": _clip_text(dialogue.get("user_dialogue_act"), 80),
                "assistant_last_move": _clip_text(dialogue.get("assistant_last_move"), 80),
                "pending_question": _clip_text(dialogue.get("pending_question"), 140),
                "pending_dialogue_act": pending_packet,
                "continuation_expected": bool(dialogue.get("continuation_expected")),
            },
            "memory_writer": {
                "active_topic": _clip_text(writer.get("active_topic"), 140),
                "unresolved_user_request": _clip_text(writer.get("unresolved_user_request"), 180),
            },
            "evidence_state": {
                "last_investigation_status": _clip_text(evidence.get("last_investigation_status"), 80),
                "verdict_action": _clip_text(evidence.get("verdict_action"), 80),
                "active_source_ids": _clip_string_list(evidence.get("active_source_ids", []), 4, 120),
                "evidence_facts": _clip_string_list(evidence.get("evidence_facts", []), 4, 180),
                "unresolved_questions": _clip_string_list(evidence.get("unresolved_questions", []), 3, 160),
            },
        }

    if role in {"readiness", "auditor", "-1b"}:
        return {
            "turn_summary": _clip_text(working_memory.get("turn_summary"), 260),
            "response_contract": {
                "reply_mode": _clip_text(response.get("reply_mode"), 80),
                "answer_goal": _clip_text(response.get("answer_goal"), 180),
                "must_include_facts": _clip_string_list(response.get("must_include_facts", []), 4, 180),
                "must_avoid_claims": _clip_string_list(response.get("must_avoid_claims", []), 4, 180),
            },
        }

    if role in {"fact_judge", "2b"}:
        return {
            "evidence_state": {
                "last_investigation_status": _clip_text(evidence.get("last_investigation_status"), 80),
                "verdict_action": _clip_text(evidence.get("verdict_action"), 80),
                "active_source_ids": _clip_string_list(evidence.get("active_source_ids", []), 6, 120),
                "evidence_facts": _clip_string_list(evidence.get("evidence_facts", []), 6, 200),
                "unresolved_questions": _clip_string_list(evidence.get("unresolved_questions", []), 5, 180),
            },
        }

    if role in {"delivery", "phase_3"}:
        return {
            "short_term_context": _clip_text(writer.get("short_term_context"), 360),
            "assistant_obligation_next_turn": _clip_text(writer.get("assistant_obligation_next_turn"), 220),
            "pending_dialogue_act": pending_packet,
            "dialogue_state": {
                "user_dialogue_act": _clip_text(dialogue.get("user_dialogue_act"), 80),
                "assistant_last_move": _clip_text(dialogue.get("assistant_last_move"), 80),
                "continuation_expected": bool(dialogue.get("continuation_expected")),
            },
        }

    return {
        "turn_summary": _clip_text(working_memory.get("turn_summary"), 360),
        "dialogue_state": {
            "user_dialogue_act": _clip_text(dialogue.get("user_dialogue_act"), 80),
            "assistant_last_move": _clip_text(dialogue.get("assistant_last_move"), 80),
            "pending_question": _clip_text(dialogue.get("pending_question"), 180),
            "pending_dialogue_act": {
                "kind": _clip_text(pending.get("kind"), 60),
                "target": _clip_text(pending.get("target"), 220),
                "expected_user_responses": _clip_string_list(pending.get("expected_user_responses", []), 8, 40),
                "expires_after_turns": pending.get("expires_after_turns", 0),
                "confidence": pending.get("confidence", 0.0),
            },
            "conversation_mode": _clip_text(dialogue.get("conversation_mode"), 100),
            "continuation_expected": bool(dialogue.get("continuation_expected")),
            "initiative_requested": bool(dialogue.get("initiative_requested")),
            "task_reset_applied": bool(dialogue.get("task_reset_applied")),
        },
        "temporal_context": {
            "continuity_score": temporal.get("continuity_score", 0.0),
            "topic_shift_score": temporal.get("topic_shift_score", 0.0),
            "topic_reset_confidence": temporal.get("topic_reset_confidence", 0.0),
            "carry_over_strength": temporal.get("carry_over_strength", 0.0),
            "carry_over_allowed": bool(temporal.get("carry_over_allowed")),
            "current_input_anchor": _clip_text(temporal.get("current_input_anchor"), 180),
        },
        "memory_writer": {
            "short_term_context": _clip_text(writer.get("short_term_context"), 420),
            "active_topic": _clip_text(writer.get("active_topic"), 180),
            "unresolved_user_request": _clip_text(writer.get("unresolved_user_request"), 220),
            "assistant_obligation_next_turn": _clip_text(writer.get("assistant_obligation_next_turn"), 260),
            "ephemeral_notes": _clip_string_list(writer.get("ephemeral_notes", []), 4, 180),
            "durable_fact_candidates": _clip_string_list(writer.get("durable_fact_candidates", []), 4, 220),
        },
        "evidence_state": {
            "last_investigation_status": _clip_text(evidence.get("last_investigation_status"), 80),
            "verdict_action": _clip_text(evidence.get("verdict_action"), 80),
            "active_source_ids": _clip_string_list(evidence.get("active_source_ids", []), 6, 160),
            "evidence_facts": _clip_string_list(evidence.get("evidence_facts", []), 5, 240),
            "unresolved_questions": _clip_string_list(evidence.get("unresolved_questions", []), 4, 220),
        },
        "response_contract": {
            "reply_mode": _clip_text(response.get("reply_mode"), 80),
            "answer_goal": _clip_text(response.get("answer_goal"), 220),
            "must_include_facts": _clip_string_list(response.get("must_include_facts", []), 5, 240),
            "must_avoid_claims": _clip_string_list(response.get("must_avoid_claims", []), 5, 240),
        },
    }


def raw_read_report_packet_for_prompt(raw_read_report: dict):
    if not raw_read_report:
        return "No raw-read report is available."
    packet = compact_raw_read_report_for_prompt(raw_read_report)
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


def build_source_relay_packet(raw_read_report: dict):
    if not isinstance(raw_read_report, dict) or not raw_read_report:
        return {
            "read_mode": "empty",
            "reviewed_all_input": False,
            "global_source_summary": "",
            "global_coverage_notes": "",
            "source_packets": [],
        }

    read_mode = str(raw_read_report.get("read_mode") or "").strip() or "empty"
    reviewed_all_input = bool(raw_read_report.get("reviewed_all_input", False))
    global_source_summary = str(raw_read_report.get("source_summary") or "").strip()
    global_coverage_notes = str(raw_read_report.get("coverage_notes") or "").strip()
    grouped = {}

    for item in raw_read_report.get("items", []):
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id") or "").strip() or "unknown_source"
        source_type = str(item.get("source_type") or "").strip() or "unknown"
        key = (source_id, source_type)
        packet = grouped.setdefault(key, {
            "source_id": source_id,
            "source_type": source_type,
            "source_summary": "",
            "coverage_notes": "",
            "must_forward_facts": [],
            "quoted_excerpts": [],
            "coverage_complete": reviewed_all_input,
        })
        observed_fact = str(item.get("observed_fact") or "").strip()
        excerpt = str(item.get("excerpt") or "").strip()
        if observed_fact and observed_fact not in packet["must_forward_facts"]:
            packet["must_forward_facts"].append(observed_fact)
        if excerpt and excerpt not in packet["quoted_excerpts"]:
            packet["quoted_excerpts"].append(excerpt)

    source_packets = []
    if grouped:
        multi_source = len(grouped) > 1
        for (_, _), packet in grouped.items():
            source_id = packet["source_id"]
            source_type = packet["source_type"]
            packet["source_summary"] = (
                f"{source_type} source `{source_id}` was reviewed by phase_2a."
                if multi_source else
                (global_source_summary or f"{source_type} source `{source_id}` was reviewed by phase_2a.")
            )
            packet["coverage_notes"] = global_coverage_notes or "phase_2a completed a raw read pass for this source."
            packet["must_forward_facts"] = packet["must_forward_facts"][:6]
            packet["quoted_excerpts"] = packet["quoted_excerpts"][:3]
            source_packets.append(packet)

    if not source_packets and read_mode == "current_turn_only":
        source_packets.append({
            "source_id": "current_user_turn",
            "source_type": "current_turn",
            "source_summary": global_source_summary or "The current user turn was reviewed as the only available raw source.",
            "coverage_notes": global_coverage_notes or "No external raw source was available in this turn.",
            "must_forward_facts": [],
            "quoted_excerpts": [],
            "coverage_complete": reviewed_all_input,
        })

    return {
        "read_mode": read_mode,
        "reviewed_all_input": reviewed_all_input,
        "global_source_summary": global_source_summary,
        "global_coverage_notes": global_coverage_notes,
        "source_packets": source_packets,
    }


def source_relay_packet_for_prompt(source_relay_packet: dict):
    if not isinstance(source_relay_packet, dict) or not source_relay_packet:
        return "No source relay packet is available."
    packet = compact_source_relay_packet_for_prompt(source_relay_packet)
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


def compact_source_relay_packet_for_prompt(source_relay_packet: dict):
    packet = source_relay_packet if isinstance(source_relay_packet, dict) else {}
    source_packets = []
    for source in _clip_list(packet.get("source_packets", []), 12):
        if not isinstance(source, dict):
            continue
        source_packets.append({
            "source_id": _clip_text(source.get("source_id"), 180),
            "source_type": _clip_text(source.get("source_type"), 80),
            "source_summary": _clip_text(source.get("source_summary"), 900),
            "coverage_notes": _clip_text(source.get("coverage_notes"), 900),
            "must_forward_facts": _clip_string_list(source.get("must_forward_facts", []), 6, 700),
            "quoted_excerpts": _clip_string_list(source.get("quoted_excerpts", []), 3, 700),
            "coverage_complete": bool(source.get("coverage_complete", False)),
        })
    return {
        "read_mode": _clip_text(packet.get("read_mode"), 80),
        "reviewed_all_input": bool(packet.get("reviewed_all_input", False)),
        "global_source_summary": _clip_text(packet.get("global_source_summary"), 900),
        "global_coverage_notes": _clip_text(packet.get("global_coverage_notes"), 900),
        "source_packets": source_packets,
    }


def normalize_analysis_with_source_relay(analysis_dict: dict, source_relay_packet: dict):
    if not isinstance(analysis_dict, dict):
        analysis_dict = {}
    if not isinstance(source_relay_packet, dict):
        source_relay_packet = {}

    normalized = json.loads(json.dumps(analysis_dict, ensure_ascii=False))
    source_packets = source_relay_packet.get("source_packets", [])
    if not isinstance(source_packets, list):
        source_packets = []

    judgments = normalized.get("source_judgments", [])
    if not isinstance(judgments, list):
        judgments = []
    judgment_map = {}
    for judgment in judgments:
        if not isinstance(judgment, dict):
            continue
        key = (
            str(judgment.get("source_id") or "").strip(),
            str(judgment.get("source_type") or "").strip(),
        )
        judgment_map[key] = judgment

    normalized_judgments = []
    for packet in source_packets:
        if not isinstance(packet, dict):
            continue
        source_id = str(packet.get("source_id") or "").strip() or "unknown_source"
        source_type = str(packet.get("source_type") or "").strip() or "unknown"
        key = (source_id, source_type)
        existing = judgment_map.get(key, {})
        accepted_facts = existing.get("accepted_facts", [])
        if not isinstance(accepted_facts, list):
            accepted_facts = []
        contested_facts = existing.get("contested_facts", [])
        if not isinstance(contested_facts, list):
            contested_facts = []
        missing_info = existing.get("missing_info", [])
        if not isinstance(missing_info, list):
            missing_info = []

        must_forward_facts = [
            str(fact).strip()
            for fact in packet.get("must_forward_facts", [])
            if str(fact).strip()
        ]
        if not accepted_facts and must_forward_facts:
            accepted_facts = must_forward_facts[:3]

        source_status = str(existing.get("source_status") or "").strip().lower()
        if source_status not in {"pass", "objection", "ambiguous", "insufficient"}:
            source_status = "pass" if accepted_facts else "ambiguous"

        normalized_judgments.append({
            "source_id": source_id,
            "source_type": source_type,
            "source_status": source_status,
            "accepted_facts": _dedupe_keep_order([str(f).strip() for f in accepted_facts if str(f).strip()])[:5],
            "contested_facts": _dedupe_keep_order([str(f).strip() for f in contested_facts if str(f).strip()])[:5],
            "objection_reason": str(existing.get("objection_reason") or "").strip(),
            "missing_info": _dedupe_keep_order([str(f).strip() for f in missing_info if str(f).strip()])[:4],
            "search_needed": bool(existing.get("search_needed", False)),
        })

    normalized["source_judgments"] = normalized_judgments

    evidences = normalized.get("evidences", [])
    if not isinstance(evidences, list):
        evidences = []
    existing_evidence_keys = {
        (
            str(item.get("source_id") or "").strip(),
            str(item.get("extracted_fact") or "").strip(),
        )
        for item in evidences
        if isinstance(item, dict)
    }
    for judgment in normalized_judgments:
        source_id = str(judgment.get("source_id") or "").strip()
        source_type = str(judgment.get("source_type") or "").strip()
        for fact in judgment.get("accepted_facts", []):
            key = (source_id, str(fact).strip())
            if not key[1] or key in existing_evidence_keys:
                continue
            evidences.append({
                "source_id": source_id,
                "source_type": source_type,
                "extracted_fact": str(fact).strip(),
            })
            existing_evidence_keys.add(key)
    normalized["evidences"] = evidences
    return normalized


def analysis_packet_for_prompt(analysis_data: dict, include_thought: bool = True, *, role: str = "general"):
    if not analysis_data:
        return "No structured phase_2 analysis report is available."

    packet = compact_analysis_for_prompt(analysis_data, include_thought=include_thought, role=role)

    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


def working_memory_packet_for_prompt(working_memory: dict, *, role: str = "general"):
    if not working_memory:
        return "No structured working memory is available."
    packet = compact_working_memory_for_prompt(working_memory, role=role)
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


def answer_mode_policy_packet_for_prompt(policy: dict | None):
    packet = policy if isinstance(policy, dict) else {}
    if not packet:
        return "N/A"
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


def strategy_packet_for_prompt(strategy_data: dict):
    if not strategy_data:
        return "No -1a strategy packet is available."
    packet = {
        "reply_mode": strategy_data.get("reply_mode", ""),
        "delivery_freedom_mode": strategy_data.get("delivery_freedom_mode", ""),
        "answer_goal": strategy_data.get("answer_goal", ""),
        "tone_strategy": strategy_data.get("tone_strategy", ""),
        "evidence_brief": strategy_data.get("evidence_brief", ""),
        "reasoning_brief": strategy_data.get("reasoning_brief", ""),
        "direct_answer_seed": strategy_data.get("direct_answer_seed", ""),
        "must_include_facts": strategy_data.get("must_include_facts", []),
        "must_avoid_claims": strategy_data.get("must_avoid_claims", []),
        "answer_outline": strategy_data.get("answer_outline", []),
        "uncertainty_policy": strategy_data.get("uncertainty_policy", ""),
    }
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


def verdict_packet_for_prompt(board: dict):
    if not isinstance(board, dict) or not board:
        return "No verdict board is available."
    verdict = board.get("verdict_board", {})
    if not isinstance(verdict, dict) or not verdict:
        return "No verdict board is available."
    try:
        return json.dumps(verdict, ensure_ascii=False, indent=2)
    except TypeError:
        return str(verdict)


def judge_speaker_packet_for_prompt(judge_speaker_packet: dict):
    if not isinstance(judge_speaker_packet, dict) or not judge_speaker_packet:
        return "No judge-speaker packet is available."
    delivery_packet = judge_speaker_packet.get("delivery_packet", {})
    if isinstance(delivery_packet, dict) and delivery_packet:
        payload = {
            "speaker_mode": judge_speaker_packet.get("speaker_mode", ""),
            "answer_now": judge_speaker_packet.get("answer_now", False),
            "requires_search": judge_speaker_packet.get("requires_search", False),
            "judge_notes": judge_speaker_packet.get("judge_notes", []),
            "delivery_packet": delivery_packet,
        }
        try:
            return json.dumps(payload, ensure_ascii=False, indent=2)
        except TypeError:
            return str(payload)
    try:
        return json.dumps(judge_speaker_packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(judge_speaker_packet)


def strategist_output_packet_for_prompt(strategist_output: dict):
    if not strategist_output:
        return "No -1a strategist output is available."

    response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}

    packet = {
        "case_theory": str(strategist_output.get("case_theory") or "").strip(),
        "operation_plan": normalize_operation_plan(strategist_output.get("operation_plan", {})),
        "goal_lock": normalize_goal_lock(strategist_output.get("goal_lock", {})),
        "convergence_state": normalize_convergence_state(strategist_output.get("convergence_state", "")),
        "achieved_findings": normalize_short_string_list(strategist_output.get("achieved_findings", []), limit=3),
        "delivery_readiness": normalize_delivery_readiness(strategist_output.get("delivery_readiness", "")),
        "next_frontier": normalize_short_string_list(strategist_output.get("next_frontier", []), limit=3),
        "action_plan": normalize_action_plan(strategist_output.get("action_plan", {})),
        "response_strategy": response_strategy,
        "war_room_contract": _normalize_war_room_operating_contract(strategist_output.get("war_room_contract", {})),
        "candidate_pair_count": len(strategist_output.get("candidate_pairs", []))
        if isinstance(strategist_output.get("candidate_pairs"), list)
        else 0,
    }
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


def _compact_fact_cells_for_prompt(values, limit: int = 8):
    projected = []
    for fact in _clip_list(values, limit):
        if not isinstance(fact, dict):
            continue
        projected.append({
            "fact_id": _clip_text(fact.get("fact_id"), 120),
            "claim": _clip_text(fact.get("claim") or fact.get("fact") or fact.get("text"), 260),
            "source_id": _clip_text(fact.get("source_id"), 140),
            "status": _clip_text(fact.get("status") or fact.get("audit_status"), 80),
        })
    return projected


def _compact_candidate_pairs_for_prompt(values, limit: int = 8):
    projected = []
    for pair in _clip_list(values, limit):
        if not isinstance(pair, dict):
            continue
        projected.append({
            "pair_id": _clip_text(pair.get("pair_id"), 120),
            "claim": _clip_text(pair.get("claim") or pair.get("text") or pair.get("answer_claim"), 260),
            "supporting_fact_ids": _clip_string_list(pair.get("supporting_fact_ids", []), 4, 80),
            "audit_status": _clip_text(pair.get("audit_status"), 80),
            "risk": _clip_text(pair.get("risk") or pair.get("objection"), 180),
        })
    return projected


def _compact_strategy_plan_for_prompt(plan):
    source = plan if isinstance(plan, dict) else {"case_theory": "", "action_plan": empty_action_plan()}
    action_plan = source.get("action_plan", {})
    if not isinstance(action_plan, dict):
        action_plan = {}
    return {
        "case_theory": _clip_text(source.get("case_theory"), 280),
        "action_plan": {
            "current_step_goal": _clip_text(action_plan.get("current_step_goal"), 220),
            "required_tool": _clip_text(action_plan.get("required_tool"), 120),
            "tool_query": _clip_text(action_plan.get("tool_query"), 180),
            "next_steps_forecast": _clip_string_list(action_plan.get("next_steps_forecast", []), 4, 160),
        },
    }


def _compact_verdict_board_for_prompt(verdict):
    source = verdict if isinstance(verdict, dict) else empty_verdict_board()
    return {
        "verdict": _clip_text(source.get("verdict") or source.get("status"), 80),
        "approved_fact_ids": _clip_string_list(source.get("approved_fact_ids", []), 8, 80),
        "rejected_fact_ids": _clip_string_list(source.get("rejected_fact_ids", []), 8, 80),
        "notes": _clip_string_list(source.get("notes", []), 4, 180),
    }


def compact_reasoning_board_for_prompt(board: dict, approved_only: bool = False, *, role: str = "general"):
    if not isinstance(board, dict) or not board:
        return {}
    fact_map = {
        str(fact.get("fact_id") or "").strip(): fact
        for fact in board.get("fact_cells", [])
        if isinstance(fact, dict)
    }

    if approved_only:
        final_fact_ids = board.get("final_fact_ids") or []
        final_pair_ids = set(board.get("final_pair_ids", []))
        approved_pairs = []
        for pair in board.get("candidate_pairs", []):
            if not isinstance(pair, dict):
                continue
            if pair.get("audit_status") != "approved":
                continue
            if final_pair_ids and pair.get("pair_id") not in final_pair_ids:
                continue
            approved_pairs.append(pair)
        return {
            "final_fact_cells": _compact_fact_cells_for_prompt([fact_map[fid] for fid in final_fact_ids if fid in fact_map], 8),
            "approved_pairs": _compact_candidate_pairs_for_prompt(approved_pairs, 8),
            "must_avoid_claims": _clip_string_list(board.get("must_avoid_claims", []), 6, 220),
            "direct_answer_seed": _clip_text(board.get("direct_answer_seed"), 320),
            "open_questions": _clip_string_list(board.get("open_questions", []), 4, 180),
            "strategist_plan": _compact_strategy_plan_for_prompt(board.get("strategist_plan", {})),
            "critic_report": _clip_mapping(board.get("critic_report", empty_critic_report()), 8, 220),
            "verdict_board": _compact_verdict_board_for_prompt(board.get("verdict_board", {})),
        }

    role = str(role or "general").strip()
    if role in {"strategist", "-1a"}:
        return {
            "fact_cells": _compact_fact_cells_for_prompt(board.get("fact_cells", []), 8),
            "candidate_pair_count": len(board.get("candidate_pairs", [])) if isinstance(board.get("candidate_pairs", []), list) else 0,
            "open_questions": _clip_string_list(board.get("open_questions", []), 4, 180),
            "search_requests": _clip_string_list(board.get("search_requests", []), 4, 180),
            "must_avoid_claims": _clip_string_list(board.get("must_avoid_claims", []), 4, 180),
            "strategist_plan": _compact_strategy_plan_for_prompt(board.get("strategist_plan", {})),
            "verdict_board": _compact_verdict_board_for_prompt(board.get("verdict_board", {})),
        }
    if role in {"readiness", "auditor", "-1b"}:
        return {
            "final_fact_ids": _clip_string_list(board.get("final_fact_ids", []), 8, 80),
            "final_pair_ids": _clip_string_list(board.get("final_pair_ids", []), 8, 80),
            "candidate_pair_count": len(board.get("candidate_pairs", [])) if isinstance(board.get("candidate_pairs", []), list) else 0,
            "must_avoid_claims": _clip_string_list(board.get("must_avoid_claims", []), 6, 200),
            "direct_answer_seed": _clip_text(board.get("direct_answer_seed"), 260),
            "open_questions": _clip_string_list(board.get("open_questions", []), 4, 180),
            "strategist_plan": _compact_strategy_plan_for_prompt(board.get("strategist_plan", {})),
            "critic_report": _clip_mapping(board.get("critic_report", empty_critic_report()), 6, 180),
            "verdict_board": _compact_verdict_board_for_prompt(board.get("verdict_board", {})),
        }
    if role in {"delivery", "phase_3"}:
        return compact_reasoning_board_for_prompt(board, approved_only=True, role="phase_3")

    return {
        "fact_cells": _compact_fact_cells_for_prompt(board.get("fact_cells", []), 12),
        "candidate_pairs": _compact_candidate_pairs_for_prompt(board.get("candidate_pairs", []), 12),
        "open_questions": _clip_string_list(board.get("open_questions", []), 8, 220),
        "search_requests": _clip_string_list(board.get("search_requests", []), 8, 220),
        "final_fact_ids": _clip_string_list(board.get("final_fact_ids", []), 12, 100),
        "final_pair_ids": _clip_string_list(board.get("final_pair_ids", []), 12, 100),
        "must_avoid_claims": _clip_string_list(board.get("must_avoid_claims", []), 8, 220),
        "direct_answer_seed": _clip_text(board.get("direct_answer_seed"), 420),
        "strategist_plan": _compact_strategy_plan_for_prompt(board.get("strategist_plan", {})),
        "critic_report": _clip_mapping(board.get("critic_report", empty_critic_report()), 8, 220),
        "advocate_report": _clip_mapping(board.get("advocate_report", empty_advocate_report()), 8, 220),
        "verdict_board": _compact_verdict_board_for_prompt(board.get("verdict_board", {})),
    }


def reasoning_board_packet_for_prompt(board: dict, approved_only: bool = False, *, role: str = "general"):
    if not isinstance(board, dict) or not board:
        return "No reasoning board is available."

    packet = compact_reasoning_board_for_prompt(board, approved_only=approved_only, role=role)

    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


__all__ = [
    "raw_read_report_packet_for_prompt",
    "build_source_relay_packet",
    "compact_s_thinking_packet_for_prompt",
    "s_thinking_packet_for_prompt",
    "compact_rescue_handoff_for_prompt",
    "compact_source_relay_packet_for_prompt",
    "source_relay_packet_for_prompt",
    "normalize_analysis_with_source_relay",
    "compact_analysis_for_prompt",
    "compact_raw_read_report_for_prompt",
    "analysis_packet_for_prompt",
    "compact_working_memory_for_prompt",
    "working_memory_packet_for_prompt",
    "answer_mode_policy_packet_for_prompt",
    "strategy_packet_for_prompt",
    "verdict_packet_for_prompt",
    "judge_speaker_packet_for_prompt",
    "strategist_output_packet_for_prompt",
    "compact_reasoning_board_for_prompt",
    "reasoning_board_packet_for_prompt",
]
