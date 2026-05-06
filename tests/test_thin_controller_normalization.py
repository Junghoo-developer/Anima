import unittest

import Core.field_memo as field_memo
import Core.nodes as nodes
from Core.field_memo import build_field_memo_candidate, should_create_field_memo
from Core.state import empty_anima_state


class ThinControllerNormalizationTests(unittest.TestCase):
    def test_start_gate_memory_reset_routes_direct_without_raw_goal_or_tool(self):
        text = "\uc548\ub155 \uc0b4\uc9dd \ubbf8\uc548\ud558\uc9c0\ub9cc \ub124 \uc774\uc804\uc758 \uae30\uc5b5\uc744 \uc804\ubd80 \uc18c\uac70\ud558\uace0 \uc654\uc5b4"
        state = empty_anima_state()
        state["user_input"] = text
        state["recent_context"] = ""
        state["working_memory"] = {}
        state["reasoning_plan"] = {"preferred_path": "delivery_contract", "reasoning_budget": 1}

        original = nodes._llm_start_gate_turn_contract
        try:
            nodes._llm_start_gate_turn_contract = lambda *args, **kwargs: nodes._normalize_start_gate_turn_contract(
                {
                    "user_intent": "providing_current_memory",
                    "normalized_goal": "Acknowledge the memory reset disclosure and orient to the new start.",
                    "answer_mode_preference": "current_turn_grounding",
                    "requires_grounding": False,
                    "direct_delivery_allowed": True,
                    "needs_planning": False,
                    "current_turn_facts": ["The user says the assistant's previous memories were erased."],
                    "rationale": "The current turn supplies the relevant fact.",
                    "contract_source": "test_llm_contract",
                },
                text,
                "",
            )
            result = nodes.phase_minus_1s_start_gate(state)
        finally:
            nodes._llm_start_gate_turn_contract = original
        switches = result["start_gate_switches"]

        self.assertEqual(result["auditor_decision"]["action"], "phase_3")
        self.assertEqual(switches["ops_next_hop"], "phase_3")
        self.assertFalse(switches["force_tool_first"])
        self.assertEqual(switches["requested_move"], "")
        self.assertEqual(switches["direct_strategy"], "")
        self.assertNotEqual(switches["normalized_goal"], text)
        self.assertEqual(switches["start_gate_turn_contract"]["user_intent"], "providing_current_memory")
        packet = result["s_thinking_packet"]
        self.assertEqual(packet["schema"], "SThinkingPacket.v1")
        self.assertEqual(packet["routing_decision"]["next_node"], "phase_3")
        self.assertEqual(packet["situation_thinking"]["domain"], "continuation")
        self.assertNotIn(text, str(packet))
        self.assertIn("do not write tool names or queries in -1s", packet["next_direction"]["avoid"])

    def test_start_gate_llm_contract_blocks_story_share_recall_search(self):
        text = (
            "Let me tell you an old memory: in kindergarten my teacher asked every child "
            "what job they dreamed of, and I felt resistance because adults seemed irresponsible."
        )
        contract = nodes._normalize_start_gate_turn_contract(
            {
                "user_intent": "providing_current_memory",
                "normalized_goal": "Respond to the current autobiographical memory being shared.",
                "answer_mode_preference": "current_turn_grounding",
                "requires_grounding": False,
                "direct_delivery_allowed": True,
                "needs_planning": False,
                "current_turn_facts": ["The user is sharing a childhood memory and their reaction to it."],
                "rationale": "This is a current-turn disclosure, not a recall request.",
                "contract_source": "test_llm_contract",
            },
            text,
            "",
        )

        switches = nodes._build_start_gate_switches(
            text,
            "",
            {},
            {},
            {"preferred_path": "delivery_contract", "reasoning_budget": 1},
            contract,
        )

        self.assertEqual(switches["ops_next_hop"], "phase_3")
        self.assertFalse(switches["requires_grounding"])
        self.assertEqual(switches["answer_mode_policy"]["question_class"], "providing_current_memory")
        self.assertFalse(
            nodes._start_gate_requests_memory_recall(
                {"start_gate_switches": switches},
                text,
            )
        )

    def test_start_gate_contract_is_only_recall_authority_for_auditor(self):
        text = "Let me tell you an old memory about kindergarten."
        providing_state = {
            "start_gate_contract": {
                "turn_contract": {
                    "user_intent": "providing_current_memory",
                    "answer_mode_preference": "current_turn_grounding",
                    "requires_grounding": False,
                    "direct_delivery_allowed": True,
                }
            }
        }
        recall_state = {
            "start_gate_contract": {
                "turn_contract": {
                    "user_intent": "requesting_memory_recall",
                    "answer_mode_preference": "grounded_recall",
                    "requires_grounding": True,
                    "direct_delivery_allowed": False,
                }
            }
        }

        self.assertFalse(nodes._start_gate_requests_memory_recall(providing_state, text))
        self.assertTrue(nodes._start_gate_requests_memory_recall(recall_state, text))

    def test_start_gate_never_compiles_tool_first_or_tool_query(self):
        switches = nodes._build_start_gate_switches(
            "search OMORI",
            "",
            {},
            {},
            {"preferred_path": "tool_first", "reasoning_budget": 1},
        )

        self.assertIn(switches["ops_next_hop"], {"-1a_thinker", "phase_3"})
        self.assertFalse(switches["force_tool_first"])
        self.assertEqual(switches["direct_strategy"], "")
        self.assertEqual(switches["requested_move"], "")

    def test_start_gate_planning_packet_is_abstract_not_tool_query(self):
        state = empty_anima_state()
        state["user_input"] = "Search my old records about Sunny."
        state["recent_context"] = ""
        state["working_memory"] = {}
        state["reasoning_plan"] = {"preferred_path": "tool_first", "reasoning_budget": 1}

        original = nodes._llm_start_gate_turn_contract
        try:
            nodes._llm_start_gate_turn_contract = lambda *args, **kwargs: nodes._normalize_start_gate_turn_contract(
                {
                    "user_intent": "requesting_memory_recall",
                    "normalized_goal": "Recall stored memory about Sunny.",
                    "answer_mode_preference": "grounded_recall",
                    "requires_grounding": True,
                    "direct_delivery_allowed": False,
                    "needs_planning": True,
                    "current_turn_facts": [],
                    "rationale": "Stored memory must be checked before answering.",
                },
                state["user_input"],
                "",
            )
            result = nodes.phase_minus_1s_start_gate(state)
        finally:
            nodes._llm_start_gate_turn_contract = original

        packet = result["s_thinking_packet"]
        self.assertEqual(packet["routing_decision"]["next_node"], "-1a")
        self.assertEqual(packet["situation_thinking"]["domain"], "memory_recall")
        self.assertIn("direct evidence required", " ".join(packet["situation_thinking"]["key_facts_needed"]))
        self.assertNotIn("tool_search", str(packet))
        self.assertNotIn("Sunny", str(packet["next_direction"]))

    def test_start_gate_accumulates_previous_s_thinking_history(self):
        state = empty_anima_state()
        state["user_input"] = "Search my diary again."
        state["recent_context"] = ""
        state["working_memory"] = {}
        state["loop_count"] = 2
        state["reasoning_plan"] = {"preferred_path": "tool_first", "reasoning_budget": 2}
        state["s_thinking_packet"] = {
            "schema": "SThinkingPacket.v1",
            "situation_thinking": {
                "user_intent": "requesting_memory_recall",
                "domain": "memory_recall",
                "key_facts_needed": ["diary fact"],
            },
            "loop_summary": {
                "attempted_so_far": ["start_gate_contract"],
                "current_evidence_state": "requires_grounding=True",
                "gaps": ["diary evidence was not found"],
            },
            "next_direction": {"suggested_focus": "try a different memory angle", "avoid": []},
            "routing_decision": {"next_node": "-1a", "reason": "needs planning"},
        }

        original = nodes._llm_start_gate_turn_contract
        captured = {}
        try:
            def fake_start_gate(user_input, recent_context, working_memory, reasoning_plan, s_thinking_history=None):
                captured["history"] = s_thinking_history
                return nodes._normalize_start_gate_turn_contract(
                    {
                        "user_intent": "requesting_memory_recall",
                        "normalized_goal": "Recall stored diary material without repeating the same gap.",
                        "answer_mode_preference": "grounded_recall",
                        "requires_grounding": True,
                        "direct_delivery_allowed": False,
                        "needs_planning": True,
                        "current_turn_facts": [],
                        "rationale": "Stored memory must be checked before answering.",
                    },
                    user_input,
                    recent_context,
                )

            nodes._llm_start_gate_turn_contract = fake_start_gate
            result = nodes.phase_minus_1s_start_gate(state)
        finally:
            nodes._llm_start_gate_turn_contract = original

        self.assertEqual(captured["history"]["history_compact"][0]["domain"], "memory_recall")
        self.assertEqual(captured["history"]["history_compact"][0]["main_gap"], "diary evidence was not found")
        self.assertEqual(result["s_thinking_history"]["history_compact"][0]["next_node"], "-1a")
        self.assertEqual(result["s_thinking_history"]["current"]["schema"], "SThinkingPacket.v1")
        self.assertEqual(result["s_thinking_history"]["current"]["routing_decision"]["next_node"], "-1a")

    def test_operation_plan_does_not_route_from_raw_investigate_wording(self):
        plan = nodes._derive_operation_plan(
            "Please investigate OMORI.",
            {},
            {"current_step_goal": "Answer only if an executable source plan exists.", "required_tool": ""},
            {},
            {},
            "",
            {},
        )

        self.assertEqual(plan["plan_type"], "direct_delivery")
        self.assertEqual(plan["source_lane"], "none")

    def test_operation_plan_uses_required_tool_as_source_authority(self):
        plan = nodes._derive_operation_plan(
            "Tell me what I said about Sunny.",
            {},
            {
                "current_step_goal": "Execute the selected FieldMemo search.",
                "required_tool": "tool_search_field_memos(query='Sunny OMORI', limit=8)",
            },
            {},
            {},
            "",
            {},
        )

        self.assertEqual(plan["plan_type"], "tool_evidence")
        self.assertEqual(plan["source_lane"], "field_memo_review")

    def test_fast_start_gate_no_longer_semantically_routes_identity(self):
        review = nodes._fast_start_gate_assessment(
            "What is your name?",
            "",
            {},
            {},
        )

        self.assertEqual(review["recommended_handler"], "-1a_thinker")
        self.assertNotEqual(review["answerability"], "special_case")

    def test_policy_bundle_and_branch_cannot_route_supervisor(self):
        self.assertFalse(hasattr(nodes, "_lookup_ops_policy_bundle"))
        self.assertFalse(hasattr(nodes, "_branch_guided_next_hop"))
        self.assertFalse(hasattr(nodes, "_build_ops_decision_from_switchboard"))

    def test_warroom_contract_does_not_reclassify_raw_user_move(self):
        contract = nodes._derive_war_room_operating_contract(
            "ask me a question now",
            {},
            {"current_step_goal": "Plan answer boundary.", "required_tool": ""},
            {"delivery_freedom_mode": "proposal", "reply_mode": "ask_user_question_now"},
            {},
        )

        self.assertEqual(contract["freedom"]["reason"], "no_tool_needed")
        self.assertNotIn(
            "requested move",
            contract["freedom"]["why_this_freedom"].lower(),
        )
        self.assertEqual(nodes._classify_requested_assistant_move("ask me a question"), "")

    def test_supervisor_switchboard_never_routes_direct_policy(self):
        self.assertFalse(hasattr(nodes, "_switchboard_direct_response_allowed"))
        self.assertFalse(hasattr(nodes, "_switchboard_planner_handoff"))

    def test_failed_search_turn_does_not_create_field_memo(self):
        final_state = {
            "search_results": "[FieldMemo result] no direct answer",
            "analysis_report": {
                "investigation_status": "INCOMPLETE",
                "missing_slots": ["memory.referent_fact"],
                "usable_field_memo_facts": [],
            },
            "response_strategy": {"reply_mode": "cautious_minimal"},
        }

        self.assertFalse(should_create_field_memo(final_state, "Do you remember that?", "", {}))
        self.assertIsNone(build_field_memo_candidate(final_state, "Do you remember that?", "", {}))

    def test_verified_fact_packet_creates_field_memo(self):
        final_state = {
            "analysis_report": {
                "accepted_facts": ["The user says the assistant's previous memories were erased before this turn."],
            }
        }

        original = field_memo._field_memo_writer_decision
        try:
            field_memo._field_memo_writer_decision = lambda **kwargs: {
                "should_write": True,
                "memo_kind": "verified_fact_packet",
                "known_facts": kwargs["candidate_facts"],
                "summary": "The user says the assistant's previous memories were erased before this turn.",
                "confidence": 0.9,
            }
            candidate = build_field_memo_candidate(final_state, "I erased your previous memories.", "Okay.", {})
        finally:
            field_memo._field_memo_writer_decision = original

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["memo_kind"], "verified_fact_packet")
        self.assertIn("previous memories were erased", " ".join(candidate["known_facts"]))

    def test_current_turn_start_gate_facts_create_verified_field_memo(self):
        final_state = {
            "start_gate_contract": {
                "current_turn_facts": ["The user says Heo Jeonghu created ANIMA."],
                "answer_mode_policy": {
                    "preferred_answer_mode": "current_turn_grounding",
                    "current_turn_grounding_ready": True,
                    "grounded_delivery_required": False,
                },
                "turn_contract": {
                    "answer_mode_preference": "current_turn_grounding",
                    "current_turn_facts": ["The user says Heo Jeonghu created ANIMA."],
                },
            },
            "response_strategy": {
                "must_include_facts": ["The user says Heo Jeonghu created ANIMA."],
            },
        }

        original = field_memo._field_memo_writer_decision
        try:
            field_memo._field_memo_writer_decision = lambda **kwargs: {
                "should_write": True,
                "memo_kind": "project_fact",
                "known_facts": kwargs["candidate_facts"],
                "summary": "The user says Heo Jeonghu created ANIMA.",
                "entities": ["Heo Jeonghu", "ANIMA"],
                "confidence": 0.9,
            }
            candidate = build_field_memo_candidate(
                final_state,
                "Heo Jeonghu, meaning me, created ANIMA.",
                "Okay, I will remember that as the current local fact.",
                {},
            )
        finally:
            field_memo._field_memo_writer_decision = original

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["memo_kind"], "project_fact")
        self.assertIn("Heo Jeonghu created ANIMA", " ".join(candidate["known_facts"]))

    def test_working_memory_writer_durable_fact_cannot_feed_field_memo_by_itself(self):
        final_state = {}
        working_memory = {
            "memory_writer": {
                "field_memo_write_recommendation": "write",
                "durable_fact_candidates": ["The user says SongRyeon's Song means pine tree."],
            }
        }

        original = field_memo._field_memo_writer_decision
        try:
            field_memo._field_memo_writer_decision = lambda **kwargs: {
                "should_write": True,
                "memo_kind": "identity_fact",
                "known_facts": kwargs["candidate_facts"],
                "summary": "SongRyeon's Song means pine tree.",
                "entities": ["SongRyeon"],
                "confidence": 0.9,
            }
            candidate = build_field_memo_candidate(
                final_state,
                "SongRyeon's Song means pine tree.",
                "Got it.",
                working_memory,
            )
        finally:
            field_memo._field_memo_writer_decision = original

        self.assertFalse(should_create_field_memo(final_state, "SongRyeon's Song means pine tree.", "Got it.", working_memory))
        self.assertIsNone(candidate)

    def test_working_memory_writer_proposals_are_advisory_to_field_memo_writer(self):
        final_state = {
            "start_gate_contract": {
                "current_turn_facts": ["The user says SongRyeon's Song means pine tree."],
                "answer_mode_policy": {
                    "preferred_answer_mode": "current_turn_grounding",
                    "current_turn_grounding_ready": True,
                    "grounded_delivery_required": False,
                },
                "turn_contract": {
                    "answer_mode_preference": "current_turn_grounding",
                    "current_turn_facts": ["The user says SongRyeon's Song means pine tree."],
                },
            }
        }
        working_memory = {
            "memory_writer": {
                "field_memo_write_recommendation": "write",
                "durable_fact_candidates": ["The user joked that SongRyeon is a goldfish."],
            }
        }

        captured = {}
        original = field_memo._field_memo_writer_decision
        try:
            def fake_writer(**kwargs):
                captured.update(kwargs)
                return {
                    "should_write": True,
                    "memo_kind": "identity_fact",
                    "known_facts": kwargs["candidate_facts"],
                    "summary": "SongRyeon's Song means pine tree.",
                    "entities": ["SongRyeon"],
                    "confidence": 0.9,
                }
            field_memo._field_memo_writer_decision = fake_writer
            candidate = build_field_memo_candidate(
                final_state,
                "SongRyeon's Song means pine tree.",
                "Got it.",
                working_memory,
            )
        finally:
            field_memo._field_memo_writer_decision = original

        self.assertIsNotNone(candidate)
        self.assertEqual(captured["candidate_facts"], ["The user says SongRyeon's Song means pine tree."])
        self.assertNotIn("goldfish", " ".join(candidate["known_facts"]))

    def test_field_memo_writer_can_skip_ephemeral_ack_even_with_candidate_fact(self):
        final_state = {
            "analysis_report": {
                "accepted_facts": ["The user gave a short acknowledgement to the assistant's previous offer."],
            }
        }

        original = field_memo._field_memo_writer_decision
        try:
            field_memo._field_memo_writer_decision = lambda **kwargs: {
                "should_write": False,
                "memo_kind": "skip_ephemeral",
                "known_facts": [],
                "not_memory_reason": "This is an ephemeral acknowledgement, not a durable fact.",
                "confidence": 0.95,
            }
            candidate = build_field_memo_candidate(final_state, "ㅇㅇ", "네?", {})
        finally:
            field_memo._field_memo_writer_decision = original

        self.assertIsNone(candidate)


if __name__ == "__main__":
    unittest.main()
