"""FieldMemoWriter boundary.

This module owns durable FieldMemo writer prompting and decision normalization.
`Core.field_memo` still owns candidate assembly, persistence, retrieval, and
compatibility monkey-patch points during the migration.
"""

from __future__ import annotations

import json
import os
import unicodedata
from typing import Any, List

import ollama
from pydantic import BaseModel, Field


class FieldMemoWriterDecision(BaseModel):
    should_write: bool = False
    memo_kind: str = "skip_ephemeral"
    title: str = ""
    summary: str = ""
    known_facts: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    events: List[str] = Field(default_factory=list)
    place_refs: List[str] = Field(default_factory=list)
    causal_links: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    branch_path: str = ""
    root_entity: str = ""
    truth_maintenance_note: str = ""
    confidence: float = 0.0
    not_memory_reason: str = ""


def _norm(text: Any) -> str:
    return unicodedata.normalize("NFKC", str(text or "")).strip()


def _trim(text: Any, limit: int = 320) -> str:
    value = _norm(text)
    if len(value) <= limit:
        return value
    return value[: max(limit - 3, 0)].rstrip() + "..."


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return json.dumps(str(value), ensure_ascii=False)


def _json_object_from_text(text: Any) -> dict:
    value = _norm(text)
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _dedupe_keep_order(items: Any, limit: int | None = None) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items or []:
        text = _norm(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if limit and len(result) >= limit:
            break
    return result


def _looks_like_low_trust_fact(text: str) -> bool:
    normalized = _norm(text).lower()
    if not normalized:
        return True
    low_trust_markers = [
        "answer_not_ready",
        "current_goal_answer_seed",
        "memory.referent_fact",
        "missing_slot",
        "unfilled_slot",
        "field_memo_empty",
        "tool_search_field_memos",
        "tool_search_memory",
        "search result",
        "no direct answer",
        "not enough evidence",
    ]
    return any(marker in normalized for marker in low_trust_markers)


def working_memory_durable_fact_candidates(working_memory: dict | None) -> list[str]:
    working_memory = working_memory if isinstance(working_memory, dict) else {}
    memory_writer = working_memory.get("memory_writer", {})
    if not isinstance(memory_writer, dict):
        return []
    recommendation = _norm(memory_writer.get("field_memo_write_recommendation")).lower()
    if recommendation != "write":
        return []
    facts = memory_writer.get("durable_fact_candidates", [])
    if not isinstance(facts, list):
        return []
    clean = [
        fact
        for fact in (_norm(item) for item in facts)
        if fact and not _looks_like_low_trust_fact(fact)
    ]
    return _dedupe_keep_order(clean, limit=8)


def normalize_field_memo_writer_decision(value: Any, candidate_facts: list[str]) -> dict:
    source = value if isinstance(value, dict) else {}
    allowed_kinds = {
        "durable_fact",
        "verified_fact_packet",
        "identity_fact",
        "project_fact",
        "user_preference",
        "correction_to_existing_fact",
        "skip_ephemeral",
    }
    memo_kind = _norm(source.get("memo_kind") or "skip_ephemeral")
    if memo_kind not in allowed_kinds:
        memo_kind = "skip_ephemeral"
    known_facts = _dedupe_keep_order(source.get("known_facts", []) if isinstance(source.get("known_facts"), list) else [], limit=8)
    candidate_set = set(candidate_facts)
    known_facts = [fact for fact in known_facts if fact in candidate_set]
    confidence = max(0.0, min(_safe_float(source.get("confidence"), 0.0), 1.0))
    decision = {
        "should_write": bool(source.get("should_write")) and memo_kind != "skip_ephemeral" and bool(known_facts) and confidence >= 0.5,
        "memo_kind": memo_kind,
        "title": _trim(source.get("title"), 80),
        "summary": _trim(source.get("summary"), 520),
        "known_facts": _dedupe_keep_order(known_facts, limit=8),
        "entities": _dedupe_keep_order(source.get("entities", []) if isinstance(source.get("entities"), list) else [], limit=8),
        "events": _dedupe_keep_order(source.get("events", []) if isinstance(source.get("events"), list) else [], limit=8),
        "place_refs": _dedupe_keep_order(source.get("place_refs", []) if isinstance(source.get("place_refs"), list) else [], limit=8),
        "causal_links": _dedupe_keep_order(source.get("causal_links", []) if isinstance(source.get("causal_links"), list) else [], limit=8),
        "open_questions": _dedupe_keep_order(source.get("open_questions", []) if isinstance(source.get("open_questions"), list) else [], limit=6),
        "branch_path": _trim(source.get("branch_path"), 160),
        "root_entity": _trim(source.get("root_entity"), 120),
        "truth_maintenance_note": _trim(source.get("truth_maintenance_note"), 260),
        "confidence": confidence,
        "not_memory_reason": _trim(source.get("not_memory_reason"), 260),
    }
    try:
        return FieldMemoWriterDecision(**decision).model_dump()
    except Exception:
        return {"should_write": False, "memo_kind": "skip_ephemeral", "known_facts": [], "confidence": 0.0}


def build_field_memo_writer_prompt(
    *,
    final_state: dict,
    user_input: str,
    final_answer: str,
    working_memory: dict,
    canonical_turn: dict,
    candidate_facts: list[str],
    recent_context: str = "",
) -> dict:
    return {
        "role": "FieldMemoWriter",
        "task": (
            "Decide whether this completed turn deserves a durable FieldMemo. "
            "Use semantic judgment. Do not store ephemeral acknowledgements, laughter, playful commands, "
            "assistant repair chatter, search attempts, or internal strategy text as memory."
        ),
        "strict_rules": [
            "Return one JSON object only.",
            "known_facts must be selected from candidate_facts; do not promote working_memory_proposals to facts.",
            "If this is only an interaction repair, short acknowledgement, failed search, or answer_not_ready, set should_write=false.",
            "Do not use phase names, tool names, answer goals, or operation plans as known facts.",
            "Write only durable facts, user preferences, project facts, identity facts, or corrections to existing facts.",
            "WorkingMemory is short-term situation state, not durable evidence.",
            "branch_path/root_entity are only classification hints; the night branch authority assigns official branch paths.",
        ],
        "schema": {
            "should_write": False,
            "memo_kind": "durable_fact | verified_fact_packet | identity_fact | project_fact | user_preference | correction_to_existing_fact | skip_ephemeral",
            "title": "",
            "summary": "",
            "known_facts": [],
            "entities": [],
            "events": [],
            "place_refs": [],
            "causal_links": [],
            "open_questions": [],
            "branch_path": "",
            "root_entity": "",
            "truth_maintenance_note": "",
            "confidence": 0.0,
            "not_memory_reason": "",
        },
        "candidate_facts": candidate_facts,
        "working_memory_proposals": working_memory_durable_fact_candidates(working_memory),
        "current_turn": {"user_input": user_input, "assistant_answer": final_answer},
        "working_memory": working_memory,
        "canonical_turn": canonical_turn,
        "recent_context": _trim(recent_context, 1800),
        "phase_outcome": {
            "delivery_status": _norm(final_state.get("delivery_status")),
            "used_sources": final_state.get("used_sources", []),
        },
    }


def write_field_memo_decision(
    *,
    final_state: dict,
    user_input: str,
    final_answer: str,
    working_memory: dict,
    canonical_turn: dict,
    candidate_facts: list[str],
    recent_context: str = "",
    model_name: str = "",
) -> dict:
    if not candidate_facts:
        return {"should_write": False, "memo_kind": "skip_ephemeral", "known_facts": [], "confidence": 0.0}
    prompt = build_field_memo_writer_prompt(
        final_state=final_state,
        user_input=user_input,
        final_answer=final_answer,
        working_memory=working_memory,
        canonical_turn=canonical_turn,
        candidate_facts=candidate_facts,
        recent_context=recent_context,
    )
    try:
        response = ollama.chat(
            model=model_name or os.getenv("ANIMA_MEMORY_MODEL", "gemma4:e4b").strip() or "gemma4:e4b",
            messages=[
                {"role": "system", "content": "You are a durable memory writer. Return valid JSON only."},
                {"role": "user", "content": _safe_json(prompt)},
            ],
            format="json",
            options={"temperature": 0},
        )
        content = response.get("message", {}).get("content", "") if isinstance(response, dict) else ""
        return normalize_field_memo_writer_decision(_json_object_from_text(content), candidate_facts)
    except Exception as exc:
        print(f"[FieldMemoWriter] skipped: {exc}")
        return {"should_write": False, "memo_kind": "skip_ephemeral", "known_facts": [], "confidence": 0.0}


__all__ = [
    "FieldMemoWriterDecision",
    "build_field_memo_writer_prompt",
    "normalize_field_memo_writer_decision",
    "working_memory_durable_fact_candidates",
    "write_field_memo_decision",
]
