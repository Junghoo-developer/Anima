"""Memory text sanitizers.

These helpers block internal workflow text from becoming memory material. They
do not decide what facts are true; they only detect strings that are plainly
runtime instructions or schema leakage.
"""

from __future__ import annotations

import unicodedata
from typing import Any

from .memory_contracts import INTERNAL_MEMORY_TEXT_MARKERS

DURABLE_MEMORY_MEANING_FIELD_KEYS = {
    "active_offer",
    "active_task",
    "answer_goal",
    "answer_shape_hint",
    "auditor_instruction",
    "current_goal_answer_seed",
    "current_step_goal",
    "direct_answer_seed",
    "final_answer_brief",
    "requested_assistant_move",
    "requested_move",
    "safe_reply_candidate",
}

RAW_MEMORY_TEXT_KEYS = {
    "assistant_response",
    "final_answer",
    "raw_user_input",
    "user_input",
}


def _normalize_text(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def looks_like_internal_memory_text(text: Any) -> bool:
    normalized = _normalize_text(text).lower()
    if not normalized:
        return False
    return any(str(marker).lower() in normalized for marker in INTERNAL_MEMORY_TEXT_MARKERS)


def sanitize_memory_text(text: Any, *, key: str = "") -> str:
    normalized = _normalize_text(text)
    if str(key or "") in RAW_MEMORY_TEXT_KEYS:
        return normalized
    if str(key or "") in DURABLE_MEMORY_MEANING_FIELD_KEYS:
        return ""
    if looks_like_internal_memory_text(normalized):
        return ""
    return normalized


def filter_internal_memory_texts(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    filtered = []
    for value in values:
        sanitized = sanitize_memory_text(value)
        if sanitized:
            filtered.append(sanitized)
    return filtered


def sanitize_memory_trace_value(value: Any, *, key: str = "") -> Any:
    """Remove workflow-language leakage from durable memory payloads.

    This is not a semantic classifier. It only blocks fields and strings that
    are known runtime instructions/schema residue before they reach Dream,
    TurnProcess, PhaseSnapshot, or MySQL trace backups.
    """
    key_text = str(key or "")
    if key_text in DURABLE_MEMORY_MEANING_FIELD_KEYS:
        if isinstance(value, list):
            return []
        if isinstance(value, dict):
            return {}
        return ""
    if isinstance(value, dict):
        return {
            child_key: sanitize_memory_trace_value(child_value, key=str(child_key or ""))
            for child_key, child_value in value.items()
        }
    if isinstance(value, list):
        return [sanitize_memory_trace_value(item, key=key_text) for item in value]
    if isinstance(value, str):
        return sanitize_memory_text(value, key=key_text)
    return value


def sanitize_durable_turn_record(record: Any) -> dict[str, Any]:
    """Sanitize Dream/TurnProcess top-level records before persistence."""
    cleaned = sanitize_memory_trace_value(record, key="durable_turn_record")
    if not isinstance(cleaned, dict):
        return {}
    for field in ("active_task", "active_offer", "requested_move"):
        cleaned[field] = ""
    return cleaned


__all__ = [
    "DURABLE_MEMORY_MEANING_FIELD_KEYS",
    "RAW_MEMORY_TEXT_KEYS",
    "filter_internal_memory_texts",
    "looks_like_internal_memory_text",
    "sanitize_durable_turn_record",
    "sanitize_memory_text",
    "sanitize_memory_trace_value",
]
