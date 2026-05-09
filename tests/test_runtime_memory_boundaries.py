import json
import unittest

from Core.memory import (
    FIELDMEMO_WRITER_FIELDS,
    WORKING_MEMORY_WRITER_FIELDS,
    build_field_memo_writer_prompt,
    build_working_memory_writer_prompt,
    filter_internal_memory_texts,
    looks_like_internal_memory_text,
    normalize_field_memo_writer_decision,
    normalize_memory_writer_draft,
    sanitize_memory_text,
    sanitize_memory_trace_value,
)
from Core.runtime import (
    append_cycle_to_history,
    build_cumulative_s_thinking_packet,
    build_runtime_context_packet,
    build_runtime_profile,
    compact_s_thinking_cycle,
    cleanup_turn_lived_fields,
    normalize_s_thinking_history,
    s_thinking_history_for_prompt,
)


class RuntimeMemoryBoundaryTests(unittest.TestCase):
    def test_runtime_profile_is_activity_context_not_identity(self):
        profile = build_runtime_profile({
            "current_time": "2026-05-01",
            "execution_status": "completed",
            "delivery_status": "ready",
        })

        profile_text = json.dumps(profile, ensure_ascii=False)
        self.assertEqual(profile["schema"], "RuntimeProfile.v1")
        self.assertEqual(profile["activity_status"]["execution_status"], "completed")
        self.assertIn("Do not claim DB/search/tool access", profile["provenance_policy"])
        self.assertNotIn("assistant_name", profile_text)
        self.assertNotIn("SongRyeon", profile_text)

    def test_runtime_context_packet_excludes_bulk_turn_artifacts(self):
        state = {
            "current_time": "2026-05-01",
            "recent_context": "recent context",
            "search_results": "x" * 5000,
            "tool_result_cache": {"huge": "x" * 5000},
            "messages": ["raw transcript"],
            "phase3_delivery_packet": {"internal": "seed"},
            "evidence_ledger": {"events": [{"kind": "tool_result", "source": "a"}]},
        }

        packet = build_runtime_context_packet(state)
        packet_text = json.dumps(packet, ensure_ascii=False)

        self.assertEqual(packet["schema"], "RuntimeContext.v1")
        self.assertIn("runtime_profile", packet)
        self.assertNotIn("self_kernel", packet)
        self.assertNotIn("search_results", packet_text)
        self.assertNotIn("tool_result_cache", packet_text)
        self.assertNotIn("phase3_delivery_packet", packet_text)
        self.assertNotIn("raw transcript", packet_text)

    def test_s_thinking_history_compacts_only_start_gate_outputs(self):
        previous = {
            "schema": "SThinkingPacket.v1",
            "situation_thinking": {
                "user_intent": "requesting_memory_recall",
                "domain": "memory_recall",
                "key_facts_needed": ["stored fact"],
            },
            "loop_summary": {
                "attempted_so_far": ["start_gate_contract"],
                "current_evidence_state": "requires_grounding=True",
                "gaps": ["direct evidence has not been read yet", "secondary gap"],
            },
            "next_direction": {"suggested_focus": "plan", "avoid": ["no tool names"]},
            "routing_decision": {"next_node": "-1a", "reason": "needs planning"},
        }
        row = compact_s_thinking_cycle(previous, cycle=2)

        self.assertEqual(row["cycle"], 2)
        self.assertEqual(row["domain"], "memory_recall")
        self.assertEqual(row["next_node"], "-1a")
        self.assertEqual(row["main_gap"], "direct evidence has not been read yet")
        self.assertNotIn("key_facts_needed", row)
        self.assertNotIn("suggested_focus", row)

        history = build_cumulative_s_thinking_packet(
            current={"schema": "SThinkingPacket.v1", "routing_decision": {"next_node": "phase_3"}},
            previous_history={},
            previous_packet=previous,
            cycle=2,
        )
        self.assertEqual(history["schema"], "SThinkingHistory.v1")
        self.assertEqual(len(history["history_compact"]), 1)
        self.assertEqual(history["current"]["next_node"], "phase_3")

        normalized = normalize_s_thinking_history({
            "history_compact": [row] * 10,
            "current": {"ok": True},
        })
        self.assertEqual(len(normalized["history_compact"]), 5)

        appended = append_cycle_to_history(history, previous, cycle=2)
        self.assertEqual(len(appended), 1)
        prompt = s_thinking_history_for_prompt(history)
        self.assertIn("SThinkingHistory.v1", prompt)
        self.assertNotIn("tool_search", prompt)

    def test_cleanup_boundary_is_available_from_runtime_package(self):
        cleaned = cleanup_turn_lived_fields({
            "user_input": "hello",
            "working_memory": {"turn_summary": "keep"},
            "analysis_report": {"status": "drop"},
            "messages": ["drop"],
        })

        self.assertEqual(cleaned["user_input"], "hello")
        self.assertEqual(cleaned["working_memory"], {"turn_summary": "keep"})
        self.assertEqual(cleaned["analysis_report"], {})
        self.assertEqual(cleaned["messages"], [])

    def test_memory_contracts_declare_writer_separation(self):
        self.assertIn("memory_writer", WORKING_MEMORY_WRITER_FIELDS)
        self.assertIn("response_contract", WORKING_MEMORY_WRITER_FIELDS)
        self.assertIn("known_facts", FIELDMEMO_WRITER_FIELDS)
        self.assertIn("proposed_branch_path", FIELDMEMO_WRITER_FIELDS)
        self.assertNotIn("official_branch_path", FIELDMEMO_WRITER_FIELDS)

    def test_memory_sanitizer_blocks_internal_strategy_text(self):
        internal = "Read one stronger grounded source using the current approved evidence boundary."
        clean = "SongRyeon's Song means pine tree."

        self.assertTrue(looks_like_internal_memory_text(internal))
        self.assertFalse(looks_like_internal_memory_text(clean))
        self.assertEqual(sanitize_memory_text(internal), "")
        self.assertEqual(filter_internal_memory_texts([internal, clean]), [clean])

    def test_memory_trace_sanitizer_strips_dialogue_control_fields(self):
        trace = {
            "user_input": "phase_3라는 단어를 질문에 넣어도 원문은 보존된다.",
            "dialogue_state": {
                "active_task": "Read one stronger grounded source needed to answer the current user ask directly.",
                "active_offer": "Continue the immediately preceding thread.",
                "requested_move": "memory_recall",
            },
            "response_strategy": {
                "answer_goal": "Deliver the best grounded answer using the current approved evidence boundary.",
                "must_include_facts": ["SongRyeon's name is SongRyeon."],
            },
        }

        cleaned = sanitize_memory_trace_value(trace, key="trace_data")

        self.assertEqual(cleaned["user_input"], "phase_3라는 단어를 질문에 넣어도 원문은 보존된다.")
        self.assertEqual(cleaned["dialogue_state"]["active_task"], "")
        self.assertEqual(cleaned["dialogue_state"]["active_offer"], "")
        self.assertEqual(cleaned["dialogue_state"]["requested_move"], "")
        self.assertEqual(cleaned["response_strategy"]["answer_goal"], "")
        self.assertEqual(cleaned["response_strategy"]["must_include_facts"], ["SongRyeon's name is SongRyeon."])

    def test_memory_package_exposes_writer_boundaries(self):
        wm_prompt = build_working_memory_writer_prompt(
            previous={},
            final_state={},
            user_input="hello",
            final_answer="hi",
            evidence_facts=[],
            recent_raw_turns=[],
        )
        field_prompt = build_field_memo_writer_prompt(
            final_state={},
            user_input="hello",
            final_answer="hi",
            working_memory={},
            canonical_turn={},
            candidate_facts=["The user said hello."],
        )

        self.assertEqual(wm_prompt["role"], "WorkingMemoryWriter")
        self.assertEqual(field_prompt["role"], "FieldMemoWriter")
        self.assertEqual(normalize_memory_writer_draft({"field_memo_write_recommendation": "write"})["field_memo_write_recommendation"], "write")
        self.assertFalse(
            normalize_field_memo_writer_decision(
                {"should_write": True, "memo_kind": "identity_fact", "known_facts": ["invented"], "confidence": 0.9},
                ["allowed fact"],
            )["should_write"]
        )


if __name__ == "__main__":
    unittest.main()
