import unittest

import Core.nodes as nodes
from Core.field_memo import looks_like_memo_recall_turn
from Core.state import empty_anima_state


class AnswerModePolicyTests(unittest.TestCase):
    def test_public_knowledge_explainer_policy(self):
        policy = nodes._answer_mode_policy_for_turn("Explain OMORI.", "")

        self.assertEqual(policy["question_class"], "public_knowledge_explainer")
        self.assertEqual(policy["preferred_answer_mode"], "public_parametric_knowledge")
        self.assertTrue(policy["parametric_knowledge_allowed"])
        self.assertFalse(policy["grounded_delivery_required"])

    def test_current_turn_teaching_policy(self):
        policy = nodes._answer_mode_policy_for_turn("OMORI is Sunny's alter ego.")

        self.assertEqual(policy["question_class"], "current_turn_teaching")
        self.assertEqual(policy["preferred_answer_mode"], "current_turn_grounding")
        self.assertTrue(policy["current_turn_grounding_ready"])
        self.assertFalse(policy["grounded_delivery_required"])

    def test_memory_reset_disclosure_is_current_turn_grounding(self):
        text = "Sorry, I erased all of your previous memories before coming here."
        policy = nodes._answer_mode_policy_for_turn(text, "")

        self.assertEqual(policy["question_class"], "current_turn_memory_state_disclosure")
        self.assertEqual(policy["preferred_answer_mode"], "current_turn_grounding")
        self.assertTrue(policy["current_turn_grounding_ready"])
        self.assertFalse(policy["grounded_delivery_required"])

    def test_autobiographical_memory_story_is_not_recall_search(self):
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
                "rationale": "This is a present-turn disclosure, not a recall request.",
            },
            text,
            "",
        )

        self.assertEqual(contract["user_intent"], "providing_current_memory")
        self.assertEqual(contract["answer_mode_preference"], "current_turn_grounding")
        self.assertFalse(contract["requires_grounding"])
        self.assertFalse(looks_like_memo_recall_turn(text))
        self.assertEqual(nodes._compiled_memory_recall_queries(text), [])

    def test_grounded_memory_recall_policy(self):
        policy = nodes._answer_mode_policy_for_turn("Do you remember what I said earlier?", "")

        self.assertEqual(policy["question_class"], "grounded_memory_recall")
        self.assertEqual(policy["preferred_answer_mode"], "grounded_answer")
        self.assertFalse(policy["parametric_knowledge_allowed"])
        self.assertTrue(policy["grounded_delivery_required"])

    def test_public_relation_inference_policy(self):
        policy = nodes._answer_mode_policy_for_turn("Explain the relationship between Sunny and OMORI.", "")

        self.assertEqual(policy["question_class"], "public_relation_inference")
        self.assertEqual(policy["preferred_answer_mode"], "public_parametric_knowledge")
        self.assertTrue(policy["parametric_knowledge_allowed"])
        self.assertFalse(policy["grounded_delivery_required"])

    def test_start_gate_contract_is_the_memory_recall_boundary(self):
        self.assertTrue(
            nodes._start_gate_requests_memory_recall(
                {
                    "start_gate_contract": {
                        "turn_contract": {
                            "user_intent": "requesting_memory_recall",
                            "answer_mode_preference": "grounded_recall",
                            "requires_grounding": True,
                        }
                    }
                },
                "Do you remember OMORI?",
            )
        )

    def test_retired_heuristic_shims_are_removed(self):
        retired_names = [
            "_turn_needs_total_war" + "_evidence",
            "_rescue_answer_not_ready" + "_decision",
            "_extract_operation_target" + "_scope",
            "_fallback_strategist" + "_output",
        ]
        for name in retired_names:
            self.assertFalse(hasattr(nodes, name), name)

    def test_requires_grounding_alone_is_not_memory_recall(self):
        state = {
            "start_gate_contract": {
                "turn_contract": {
                    "user_intent": "other",
                    "answer_mode_preference": "generic_dialogue",
                    "requires_grounding": True,
                }
            }
        }

        self.assertFalse(nodes._start_gate_requests_memory_recall(state, "What is your name?"))

    def test_fallback_start_gate_grounded_review_is_not_memory_recall(self):
        contract = nodes._fallback_start_gate_turn_contract("search OMORI in the raw records")

        self.assertEqual(contract["user_intent"], "task_or_tool_request")
        self.assertEqual(contract["answer_mode_preference"], "generic_dialogue")
        self.assertTrue(contract["requires_grounding"])
        self.assertFalse(
            nodes._start_gate_requests_memory_recall(
                {"start_gate_contract": {"turn_contract": contract}},
                "search OMORI in the raw records",
            )
        )

    def test_fallback_strategist_uses_public_policy_instead_of_answer_not_ready(self):
        strategist_output, _ = nodes._base_fallback_strategist_output(
            "Explain OMORI.",
            {},
            {},
            {},
        )

        self.assertEqual(
            strategist_output["answer_mode_policy"]["preferred_answer_mode"],
            "public_parametric_knowledge",
        )
        self.assertEqual(strategist_output["delivery_readiness"], "deliver_now")
        self.assertNotEqual(
            strategist_output["response_strategy"]["delivery_freedom_mode"],
            "answer_not_ready",
        )

    def test_fallback_strategist_does_not_copy_raw_memory_reset_disclosure_into_goal_fields(self):
        text = "Sorry, I erased all of your previous memories before coming here."
        strategist_output, _ = nodes._base_fallback_strategist_output(
            text,
            {},
            {},
            {},
        )

        action_plan = strategist_output["action_plan"]
        operation_plan = strategist_output["operation_plan"]
        self.assertEqual(strategist_output["delivery_readiness"], "deliver_now")
        self.assertEqual(action_plan["required_tool"], "")
        self.assertNotIn(text, action_plan["current_step_goal"])
        self.assertNotIn(text, operation_plan["user_goal"])
        self.assertEqual(
            operation_plan["user_goal"],
            "Acknowledge the user's memory reset disclosure and orient to the new start.",
        )

    def test_fallback_strategist_uses_llm_short_term_context_when_no_tool_exists(self):
        working_memory = {
            "dialogue_state": {
                "continuation_expected": True,
                "pending_dialogue_act": {
                    "kind": "playful_action",
                    "target": "perform the playful blub-blub action",
                    "expected_user_responses": ["yes"],
                    "expires_after_turns": 1,
                    "confidence": 0.9,
                },
            },
            "memory_writer": {
                "short_term_context": "The assistant jokingly offered to perform a playful blub-blub action.",
                "assistant_obligation_next_turn": "perform the playful blub-blub action directly",
                "unresolved_user_request": "continue the playful action",
            },
        }

        strategist_output, _ = nodes._base_fallback_strategist_output(
            "yes",
            {},
            working_memory,
            {},
        )

        self.assertEqual(strategist_output["delivery_readiness"], "deliver_now")
        self.assertEqual(strategist_output["action_plan"]["required_tool"], "")
        self.assertIn("short-term context", strategist_output["action_plan"]["current_step_goal"])
        self.assertIn(
            "perform the playful blub-blub action directly",
            strategist_output["response_strategy"]["direct_answer_seed"],
        )

    def test_fallback_strategist_does_not_hardcode_identity_seed_or_search(self):
        strategist_output, _ = nodes._base_fallback_strategist_output(
            "What is your name?",
            {},
            {},
            {},
        )

        self.assertEqual(strategist_output["delivery_readiness"], "deliver_now")
        self.assertEqual(strategist_output["action_plan"]["required_tool"], "")
        self.assertNotEqual(
            strategist_output["response_strategy"]["delivery_freedom_mode"],
            "identity_direct",
        )
        self.assertEqual(strategist_output["response_strategy"]["direct_answer_seed"], "")

    def test_start_gate_does_not_reopen_tool_loop_for_memory_reset_disclosure(self):
        text = "Sorry, I erased all of your previous memories before coming here."
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
                    "normalized_goal": "Acknowledge the memory reset disclosure.",
                    "answer_mode_preference": "current_turn_grounding",
                    "requires_grounding": False,
                    "direct_delivery_allowed": True,
                    "needs_planning": False,
                    "current_turn_facts": ["The user says prior memories were erased."],
                },
                text,
                "",
            )
            result = nodes.phase_minus_1s_start_gate(state)
        finally:
            nodes._llm_start_gate_turn_contract = original

        self.assertEqual(result["s_thinking_packet"]["next_node"], "phase_3")
        self.assertEqual(result["auditor_decision"]["action"], "phase_3")

    def test_phase3_payload_exposes_policy(self):
        state = {
            "user_input": "Explain OMORI.",
            "recent_context": "",
            "analysis_report": {},
            "raw_read_report": {},
            "strategist_output": {},
        }
        payload = nodes._build_phase3_delivery_payload(
            state,
            {},
            {
                "lane": "generic",
                "source_lane": "direct_dialogue",
                "output_act": "answer_narrative_fact",
                "generic_delivery_packet": {
                    "final_answer_brief": "",
                    "answer_boundary": "generic_judge_packet",
                },
            },
        )

        self.assertEqual(payload["question_class"], "public_knowledge_explainer")
        self.assertEqual(payload["answer_mode_policy"]["preferred_answer_mode"], "public_parametric_knowledge")

    def test_speaker_contract_exposes_policy(self):
        state = empty_anima_state()
        state["user_input"] = "Explain OMORI."
        contract = nodes._build_phase3_speaker_judge_contract(
            state,
            {
                "ready_for_delivery": True,
                "question_class": "public_knowledge_explainer",
                "answer_mode": "public_parametric_knowledge",
                "answer_mode_policy": {
                    "question_class": "public_knowledge_explainer",
                    "preferred_answer_mode": "public_parametric_knowledge",
                    "grounded_delivery_required": False,
                    "parametric_knowledge_allowed": True,
                    "current_turn_grounding_ready": False,
                },
                "parametric_knowledge_allowed": True,
                "answer_seed": "",
                "accepted_facts": [],
                "current_turn_facts": [],
                "clean_failure_packet": {},
                "forbidden_claims": [],
                "missing_slots": [],
                "user_goal": "Explain OMORI.",
                "output_act": "answer_narrative_fact",
                "fallback_action": "public_knowledge_answer",
                "answer_boundary": "public_parametric_knowledge + loop evidence blend",
            },
        )

        self.assertEqual(contract["QUESTION_CLASS"], "public_knowledge_explainer")
        self.assertEqual(contract["ANSWER_MODE_POLICY"]["preferred_answer_mode"], "public_parametric_knowledge")


if __name__ == "__main__":
    unittest.main()
