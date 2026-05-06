import unittest

from Core.memory_buffer import MemoryBuffer
from Core.pipeline.continuation import llm_short_term_context_material, working_memory_active_task
from main import SongRyeonAgentV5


class MemoryBufferSanitizationTests(unittest.TestCase):
    def _buffer(self):
        buffer = MemoryBuffer.__new__(MemoryBuffer)
        buffer.working_memory = buffer._default_working_memory()
        buffer.history = []
        buffer.build_temporal_context_signal = lambda *args, **kwargs: {
            "current_input_anchor": "",
            "continuity_score": 0.0,
            "topic_shift_score": 0.0,
            "topic_reset_confidence": 0.0,
            "carry_over_strength": 0.0,
            "active_task_bias": 0.0,
            "carry_over_allowed": False,
            "candidate_parent_turn_ids": [],
            "recent_match_briefs": [],
        }
        buffer._write_working_memory_with_llm = lambda **kwargs: {}
        return buffer

    def test_internal_answer_goal_does_not_become_active_task(self):
        buffer = self._buffer()
        internal_goal = "Use the facts supplied in the current user turn as admissible grounding for the answer."
        user_input = "I want to study linear algebra and probability so I can work on agent models."
        final_state = {
            "response_strategy": {
                "reply_mode": "grounded_answer",
                "answer_goal": internal_goal,
                "must_include_facts": [],
                "must_avoid_claims": [],
                "direct_answer_seed": "",
            },
            "analysis_report": {},
            "reasoning_board": {},
        }
        buffer._write_working_memory_with_llm = lambda **kwargs: {
            "user_dialogue_act": "statement",
            "assistant_last_move": "answer",
            "conversation_mode": "general_dialogue",
            "short_term_context": user_input,
            "active_topic": "agent model study plan",
            "unresolved_user_request": user_input,
            "assistant_obligation_next_turn": "",
            "pending_dialogue_act": {"kind": "none", "target": "", "expected_user_responses": [], "expires_after_turns": 0, "confidence": 0.0},
            "ephemeral_notes": [],
            "durable_fact_candidates": [],
            "field_memo_write_recommendation": "skip",
            "confidence": 0.9,
        }

        working_memory = buffer.build_working_memory_from_turn(final_state, user_input, "That sounds serious.")

        self.assertEqual(working_memory["dialogue_state"]["active_task"], "")
        self.assertEqual(working_memory["memory_writer"]["unresolved_user_request"], user_input)
        self.assertNotIn("Use the facts supplied", working_memory["turn_summary"])
        self.assertEqual(working_memory["response_contract"]["answer_goal"], "")

        buffer.working_memory = working_memory
        prompt_memory = buffer.get_working_memory_string()
        self.assertNotIn("Use the facts supplied", prompt_memory)
        self.assertIn("unresolved_user_request", prompt_memory)
        self.assertIn(user_input, prompt_memory)

    def test_loaded_internal_active_task_is_scrubbed(self):
        buffer = self._buffer()
        snapshot = buffer._default_working_memory()
        snapshot["dialogue_state"]["active_task"] = "Read one stronger grounded source needed to answer the current user ask directly."
        snapshot["turn_summary"] = "active_task=Read one stronger grounded source needed to answer the current user ask directly."

        normalized = buffer._normalize_working_memory(snapshot)

        self.assertEqual(normalized["dialogue_state"]["active_task"], "")
        self.assertNotIn("Read one stronger", normalized["turn_summary"])

    def test_llm_writer_pending_dialogue_act_replaces_active_offer(self):
        buffer = self._buffer()
        buffer._write_working_memory_with_llm = lambda **kwargs: {
            "user_dialogue_act": "playful_confirmation",
            "assistant_last_move": "playful_offer",
            "conversation_mode": "playful_dialogue",
            "short_term_context": "The assistant offered to perform a playful blub-blub action and the user accepted.",
            "active_topic": "playful blub-blub action",
            "unresolved_user_request": "perform the playful blub-blub action",
            "assistant_obligation_next_turn": "perform the playful blub-blub action directly",
            "pending_dialogue_act": {
                "kind": "playful_action",
                "target": "perform blub-blub",
                "expected_user_responses": ["yes", "do it"],
                "expires_after_turns": 1,
                "confidence": 0.9,
            },
            "ephemeral_notes": ["The confirmation itself is not a durable fact."],
            "durable_fact_candidates": [],
            "field_memo_write_recommendation": "skip",
            "confidence": 0.9,
        }

        working_memory = buffer.build_working_memory_from_turn({}, "yes", "Sure, I will do it.")

        self.assertEqual(working_memory["dialogue_state"]["active_offer"], "")
        self.assertEqual(working_memory["dialogue_state"]["active_task"], "")
        self.assertEqual(working_memory["dialogue_state"]["pending_dialogue_act"]["kind"], "playful_action")
        self.assertEqual(
            working_memory["memory_writer"]["assistant_obligation_next_turn"],
            "perform the playful blub-blub action directly",
        )
        self.assertEqual(working_memory_active_task(working_memory), "")
        materials = llm_short_term_context_material(
            working_memory,
            looks_like_internal_phase3_seed=lambda _text: False,
            compact_user_facing_summary=lambda text, _limit: text,
        )
        self.assertIn("perform the playful blub-blub action directly", materials)

    def test_llm_writer_durable_proposals_do_not_become_evidence_facts(self):
        buffer = self._buffer()
        buffer._write_working_memory_with_llm = lambda **kwargs: {
            "user_dialogue_act": "statement",
            "assistant_last_move": "answer",
            "conversation_mode": "general_dialogue",
            "short_term_context": "The user taught a possible identity fact.",
            "active_topic": "SongRyeon name meaning",
            "unresolved_user_request": "",
            "assistant_obligation_next_turn": "",
            "pending_dialogue_act": {"kind": "none", "target": "", "expected_user_responses": [], "expires_after_turns": 0, "confidence": 0.0},
            "ephemeral_notes": [],
            "durable_fact_candidates": ["SongRyeon's Song means pine tree."],
            "field_memo_write_recommendation": "write",
            "confidence": 0.9,
        }

        working_memory = buffer.build_working_memory_from_turn({}, "Song means pine tree.", "Got it.")

        self.assertIn("SongRyeon's Song means pine tree.", working_memory["memory_writer"]["durable_fact_candidates"])
        self.assertNotIn("SongRyeon's Song means pine tree.", working_memory["evidence_state"]["evidence_facts"])

        buffer.working_memory = working_memory
        prompt_memory = buffer.get_working_memory_string()
        self.assertIn("writer_proposed_durable_fact_candidates_unverified", prompt_memory)

    def test_dream_trace_sanitizer_removes_internal_strategy_text(self):
        agent = SongRyeonAgentV5.__new__(SongRyeonAgentV5)
        trace = {
            "response_strategy": {
                "reply_mode": "grounded_answer",
                "answer_goal": "Use the facts supplied in the current user turn as admissible grounding for the answer.",
                "direct_answer_seed": "Deliver the best grounded answer using the current approved evidence boundary.",
                "must_include_facts": ["The user wants to study linear algebra."],
            },
            "user_input": "I want to study linear algebra.",
        }

        sanitized = agent._sanitize_memory_trace_value(trace, key="trace_data")

        self.assertEqual(sanitized["response_strategy"]["answer_goal"], "")
        self.assertEqual(sanitized["response_strategy"]["direct_answer_seed"], "")
        self.assertEqual(sanitized["response_strategy"]["must_include_facts"], ["The user wants to study linear algebra."])
        self.assertEqual(sanitized["user_input"], "I want to study linear algebra.")

    def test_canonical_turn_keeps_blank_active_task_blank(self):
        agent = SongRyeonAgentV5.__new__(SongRyeonAgentV5)
        working_memory = {
            "turn_summary": "The user shared a project goal.",
            "dialogue_state": {
                "active_task": "",
                "active_offer": "",
                "user_dialogue_act": "statement",
            },
            "response_contract": {},
        }
        final_state = {
            "analysis_report": {
                "accepted_facts": ["The user wants to study agent development."],
            },
            "strategist_output": {},
            "response_strategy": {},
        }

        record = agent._build_canonical_turn_record(
            "I want to study agent development.",
            "That sounds like a serious direction.",
            final_state,
            working_memory,
        )

        self.assertEqual(record["dream_record"]["active_task"], "")
        self.assertEqual(record["turn_process"]["active_task"], "")

    def test_canonical_turn_does_not_persist_dialogue_control_fields(self):
        agent = SongRyeonAgentV5.__new__(SongRyeonAgentV5)
        working_memory = {
            "turn_summary": "Deliver the best grounded answer using the current approved evidence boundary.",
            "dialogue_state": {
                "active_task": "Read one stronger grounded source needed to answer the current user ask directly.",
                "active_offer": "Continue the immediately preceding thread.",
                "requested_move": "memory_recall",
                "user_dialogue_act": "question_or_request",
            },
            "response_contract": {},
        }
        final_state = {
            "analysis_report": {
                "requested_assistant_move": "tool_search_field_memos",
                "accepted_facts": ["The user asked what SongRyeon's name is."],
            },
            "strategist_output": {},
            "response_strategy": {},
        }

        record = agent._build_canonical_turn_record(
            "What is your name?",
            "My name is SongRyeon.",
            final_state,
            working_memory,
        )

        self.assertEqual(record["dream_record"]["turn_summary"], "The user asked what SongRyeon's name is.")
        for section in ("dream_record", "turn_process"):
            self.assertEqual(record[section]["active_task"], "")
            self.assertEqual(record[section]["active_offer"], "")
            self.assertEqual(record[section]["requested_move"], "")


if __name__ == "__main__":
    unittest.main()
