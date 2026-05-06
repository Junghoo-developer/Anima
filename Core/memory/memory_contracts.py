"""Memory writer authority contracts.

These constants document boundaries before the legacy MemoryBuffer/FieldMemo
modules are split. They are intentionally declarative and do not change runtime
behavior by themselves.
"""

from __future__ import annotations


WORKING_MEMORY_WRITER_FIELDS = {
    "turn_summary",
    "dialogue_state",
    "temporal_context",
    "memory_writer",
    "evidence_state",
    "response_contract",
    "user_model_delta",
}

CODE_OBSERVED_MEMORY_FIELDS = {
    "source_ids",
    "tool_calls",
    "timestamps",
    "execution_status",
    "evidence_ledger",
    "used_sources",
}

FIELDMEMO_WRITER_FIELDS = {
    "memo_kind",
    "summary",
    "known_facts",
    "entities",
    "events",
    "place_refs",
    "proposed_branch_path",
    "branch_hint",
    "source_turn_id",
    "source_dream_id",
    "source_phase_ids",
    "confidence",
    "truth_note",
}

INTERNAL_MEMORY_TEXT_MARKERS = {
    "answer mode policy",
    "answer_mode_policy",
    "answer_not_ready",
    "blocked unrelated old topic",
    "current approved evidence boundary",
    "current_goal_answer_seed",
    "current user ask",
    "current user turn",
    "deliver the best grounded answer",
    "direct evidence for the current answer",
    "fieldmemo filter",
    "final decision",
    "finalize_recommendation",
    "goal contract",
    "grounded source",
    "grounded recall",
    "insufficient_evidence",
    "internal_trace",
    "memory.referent_fact",
    "respond to the current user turn directly without broadening the goal",
    "read one stronger grounded source",
    "missing slots",
    "normalized goal",
    "tool_pass_to_phase_3",
    "tool_call_119_rescue",
    "tool_search",
    "phase_",
    "phase 0",
    "phase 1",
    "phase 2",
    "phase 3",
    "public parametric knowledge",
    "replan",
    "requires grounding",
    "analysis_report",
    "operation_plan",
    "judge_speaker_packet",
    "fallback planner",
    "source_judgments",
    "usable_field_memo_facts",
    "use the facts supplied",
}


__all__ = [
    "CODE_OBSERVED_MEMORY_FIELDS",
    "FIELDMEMO_WRITER_FIELDS",
    "INTERNAL_MEMORY_TEXT_MARKERS",
    "WORKING_MEMORY_WRITER_FIELDS",
]
