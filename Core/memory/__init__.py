"""Memory writer boundary helpers for ANIMA.

This package is the future home for WorkingMemoryWriter and FieldMemoWriter
contracts. It currently exposes non-invasive contracts and sanitizers so the
legacy modules can be migrated safely.
"""

from .memory_contracts import (
    CODE_OBSERVED_MEMORY_FIELDS,
    FIELDMEMO_WRITER_FIELDS,
    INTERNAL_MEMORY_TEXT_MARKERS,
    WORKING_MEMORY_WRITER_FIELDS,
)
from .memory_sanitizer import (
    DURABLE_MEMORY_MEANING_FIELD_KEYS,
    RAW_MEMORY_TEXT_KEYS,
    filter_internal_memory_texts,
    looks_like_internal_memory_text,
    sanitize_durable_turn_record,
    sanitize_memory_text,
    sanitize_memory_trace_value,
)
from .working_memory_writer import (
    build_working_memory_writer_prompt,
    memory_facts_from_analysis,
    memory_safe_text,
    normalize_memory_writer_draft,
    normalize_pending_dialogue_act,
    write_working_memory_with_llm,
)
from .field_memo_writer import (
    FieldMemoWriterDecision,
    build_field_memo_writer_prompt,
    normalize_field_memo_writer_decision,
    working_memory_durable_fact_candidates,
    write_field_memo_decision,
)

__all__ = [
    "CODE_OBSERVED_MEMORY_FIELDS",
    "FIELDMEMO_WRITER_FIELDS",
    "INTERNAL_MEMORY_TEXT_MARKERS",
    "WORKING_MEMORY_WRITER_FIELDS",
    "DURABLE_MEMORY_MEANING_FIELD_KEYS",
    "RAW_MEMORY_TEXT_KEYS",
    "filter_internal_memory_texts",
    "FieldMemoWriterDecision",
    "build_field_memo_writer_prompt",
    "build_working_memory_writer_prompt",
    "looks_like_internal_memory_text",
    "memory_facts_from_analysis",
    "memory_safe_text",
    "normalize_field_memo_writer_decision",
    "normalize_memory_writer_draft",
    "normalize_pending_dialogue_act",
    "sanitize_memory_text",
    "sanitize_memory_trace_value",
    "sanitize_durable_turn_record",
    "working_memory_durable_fact_candidates",
    "write_field_memo_decision",
    "write_working_memory_with_llm",
]
