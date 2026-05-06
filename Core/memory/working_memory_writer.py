"""WorkingMemoryWriter boundary.

This module owns the short-term memory writer prompt, JSON normalization, and
internal-text sanitization helpers. `Core.memory_buffer` still owns persistence
and compatibility methods; it delegates writer work here.
"""

from __future__ import annotations

import builtins
import json
import os
import sys
import unicodedata
from typing import Any

import ollama

from .memory_sanitizer import looks_like_internal_memory_text


def _safe_print(message: str) -> None:
    text = str(message)
    try:
        builtins.print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        builtins.print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def dedupe_keep_order(items: Any, limit: int | None = None) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items or []:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if limit and len(result) >= limit:
            break
    return result


def shorten_text(text: Any, limit: int = 240) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(limit - 3, 0)].rstrip() + "..."


def memory_safe_text(text: Any, limit: int = 180) -> str:
    value = unicodedata.normalize("NFKC", str(text or "").strip())
    if not value or looks_like_internal_memory_text(value):
        return ""
    return shorten_text(value, limit)


def json_object_from_text(text: Any) -> dict:
    value = str(text or "").strip()
    if not value:
        return {}
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        pass
    start = value.find("{")
    end = value.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        loaded = json.loads(value[start : end + 1])
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def memory_facts_from_analysis(analysis_report: dict, limit: int = 3) -> list[str]:
    if not isinstance(analysis_report, dict):
        return []
    facts: list[str] = []
    for key in ("current_turn_facts", "usable_field_memo_facts", "accepted_facts", "verified_facts"):
        values = analysis_report.get(key, [])
        if isinstance(values, list):
            facts.extend(str(item).strip() for item in values if str(item).strip())
    evidences = analysis_report.get("evidences", [])
    if isinstance(evidences, list):
        for item in evidences:
            if not isinstance(item, dict):
                continue
            fact = str(item.get("extracted_fact") or item.get("fact") or "").strip()
            if fact:
                facts.append(fact)
    judgments = analysis_report.get("source_judgments", [])
    if isinstance(judgments, list):
        for judgment in judgments:
            if not isinstance(judgment, dict):
                continue
            for fact in judgment.get("accepted_facts", []) or []:
                if str(fact or "").strip():
                    facts.append(str(fact).strip())
    return dedupe_keep_order([fact for fact in facts if not looks_like_internal_memory_text(fact)], limit=limit)


def normalize_pending_dialogue_act(value: Any) -> dict:
    source = value if isinstance(value, dict) else {}
    kind = str(source.get("kind") or "none").strip()
    allowed = {
        "none",
        "question",
        "offer",
        "playful_action",
        "correction_target",
        "user_requested_action",
        "continuation",
    }
    if kind not in allowed:
        kind = "none"
    try:
        expires_after_turns = max(0, min(int(source.get("expires_after_turns", 0) or 0), 3))
    except (TypeError, ValueError):
        expires_after_turns = 0
    return {
        "kind": kind,
        "target": memory_safe_text(source.get("target"), 180),
        "expected_user_responses": dedupe_keep_order(
            [
                memory_safe_text(item, 40)
                for item in (source.get("expected_user_responses", []) if isinstance(source.get("expected_user_responses"), list) else [])
                if memory_safe_text(item, 40)
            ],
            limit=8,
        ),
        "expires_after_turns": expires_after_turns,
        "confidence": max(0.0, min(safe_float(source.get("confidence"), 0.0), 1.0)),
    }


def normalize_memory_writer_draft(value: Any) -> dict:
    source = value if isinstance(value, dict) else {}
    recommendation = str(source.get("field_memo_write_recommendation") or "skip").strip()
    if recommendation not in {"write", "skip"}:
        recommendation = "skip"
    return {
        "user_dialogue_act": memory_safe_text(source.get("user_dialogue_act"), 60),
        "assistant_last_move": memory_safe_text(source.get("assistant_last_move"), 60),
        "conversation_mode": memory_safe_text(source.get("conversation_mode"), 80),
        "short_term_context": memory_safe_text(source.get("short_term_context"), 520),
        "active_topic": memory_safe_text(source.get("active_topic"), 180),
        "unresolved_user_request": memory_safe_text(source.get("unresolved_user_request"), 180),
        "assistant_obligation_next_turn": memory_safe_text(source.get("assistant_obligation_next_turn"), 220),
        "pending_dialogue_act": normalize_pending_dialogue_act(source.get("pending_dialogue_act")),
        "ephemeral_notes": dedupe_keep_order(
            [
                memory_safe_text(item, 160)
                for item in (source.get("ephemeral_notes", []) if isinstance(source.get("ephemeral_notes"), list) else [])
                if memory_safe_text(item, 160)
            ],
            limit=5,
        ),
        "durable_fact_candidates": dedupe_keep_order(
            [
                memory_safe_text(item, 220)
                for item in (source.get("durable_fact_candidates", []) if isinstance(source.get("durable_fact_candidates"), list) else [])
                if memory_safe_text(item, 220)
            ],
            limit=6,
        ),
        "field_memo_write_recommendation": recommendation,
        "confidence": max(0.0, min(safe_float(source.get("confidence"), 0.0), 1.0)),
    }


def build_working_memory_writer_prompt(
    *,
    previous: dict,
    final_state: dict,
    user_input: str,
    final_answer: str,
    evidence_facts: list[str],
    recent_raw_turns: list[dict],
) -> dict:
    return {
        "role": "WorkingMemoryWriter",
        "task": (
            "Write the next short-term memory state from meaning, not from keyword rules. "
            "Decide what is still active, what was only ephemeral dialogue, and whether the turn contains "
            "possible durable fact proposals. These proposals are not FieldMemo write permission."
        ),
        "strict_rules": [
            "Return one JSON object only.",
            "Do not copy internal planner phrases, phase names, tool names, answer_mode_policy text, or operation contracts.",
            "Short acknowledgements, laughter, frustration, playful commands, and repair turns are usually ephemeral unless they contain a stable fact.",
            "If the assistant offered or asked something that a short next reply can accept, write pending_dialogue_act.",
            "If no pending act exists, set pending_dialogue_act.kind to none.",
            "durable_fact_candidates are short-term proposals only; FieldMemoWriter must independently validate durable memory from grounded turn facts.",
            "field_memo_write_recommendation is advisory only and never grants write permission.",
        ],
        "schema": {
            "user_dialogue_act": "short semantic label",
            "assistant_last_move": "short semantic label",
            "conversation_mode": "short semantic label",
            "short_term_context": "1-3 sentences of the live conversational situation",
            "active_topic": "compact current topic, not raw user wording",
            "unresolved_user_request": "what the assistant still owes next, if any",
            "assistant_obligation_next_turn": "specific next-turn obligation, if any",
            "pending_dialogue_act": {
                "kind": "none | question | offer | playful_action | correction_target | user_requested_action | continuation",
                "target": "what the pending act is about",
                "expected_user_responses": ["short replies that would continue it"],
                "expires_after_turns": 0,
                "confidence": 0.0,
            },
            "ephemeral_notes": ["non-durable interaction notes"],
            "durable_fact_candidates": ["stable facts only"],
            "field_memo_write_recommendation": "write | skip (advisory only)",
            "confidence": 0.0,
        },
        "recent_raw_turns": recent_raw_turns,
        "previous_working_memory": previous,
        "current_turn": {"user_input": user_input, "assistant_answer": final_answer},
        "evidence_facts": evidence_facts,
        "phase_outcome": {
            "delivery_status": str(final_state.get("delivery_status") or ""),
            "used_sources": final_state.get("used_sources", []),
        },
    }


def write_working_memory_with_llm(
    *,
    model_name: str,
    previous: dict,
    final_state: dict,
    user_input: str,
    final_answer: str,
    evidence_facts: list[str],
    recent_raw_turns: list[dict],
) -> dict:
    if str(os.getenv("ANIMA_DISABLE_MEMORY_WRITER", "")).strip() == "1":
        return {}
    prompt = build_working_memory_writer_prompt(
        previous=previous,
        final_state=final_state,
        user_input=user_input,
        final_answer=final_answer,
        evidence_facts=evidence_facts,
        recent_raw_turns=recent_raw_turns,
    )
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a short-term memory writer. Return valid JSON only.",
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=False, default=str),
                },
            ],
            format="json",
            options={"temperature": 0},
        )
        content = response.get("message", {}).get("content", "") if isinstance(response, dict) else ""
        return normalize_memory_writer_draft(json_object_from_text(content))
    except Exception as exc:
        _safe_print(f"[WorkingMemoryWriter] skipped: {exc}")
        return {}


__all__ = [
    "build_working_memory_writer_prompt",
    "dedupe_keep_order",
    "json_object_from_text",
    "memory_facts_from_analysis",
    "memory_safe_text",
    "normalize_memory_writer_draft",
    "normalize_pending_dialogue_act",
    "safe_float",
    "shorten_text",
    "write_working_memory_with_llm",
]
