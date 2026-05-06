import unittest

import Core.nodes as nodes
from Core.state import empty_anima_state


class FollowupBypassGateTests(unittest.TestCase):
    def test_followup_reasoning_plan_no_longer_prefers_blind_delivery(self):
        plan = nodes._fallback_reasoning_budget_plan(
            "ㅇㅋ",
            {"dialogue_state": {"continuation_expected": True}},
        )

        self.assertEqual(plan["preferred_path"], "internal_reasoning")
        self.assertGreaterEqual(int(plan["reasoning_budget"]), 1)

    def test_fast_start_gate_followup_routes_to_strategist(self):
        review = nodes._fast_start_gate_assessment(
            "ㅇㅋ",
            "assistant: 어떤 부분부터 볼까?",
            {},
            {},
        )

        self.assertEqual(review["answerability"], "needs_planning")
        self.assertEqual(review["recommended_handler"], "-1a_thinker")

    def test_old_pre_delivery_auditors_are_removed_from_nodes_api(self):
        self.assertFalse(hasattr(nodes, "phase_minus_1b_lite_auditor"))
        self.assertFalse(hasattr(nodes, "phase_minus_1b_auditor"))

    def test_grounding_guard_allows_llm_short_term_context_strategy(self):
        state = empty_anima_state()
        state["user_input"] = "yes"
        state["recent_context"] = "assistant: Want me to perform the playful blub-blub action?"
        state["start_gate_switches"] = {
            "answer_mode_policy": {
                "grounded_delivery_required": True,
                "preferred_answer_mode": "grounded_recall",
            }
        }
        working_memory = {
            "dialogue_state": {
                "pending_dialogue_act": {
                    "kind": "playful_action",
                    "target": "perform the playful blub-blub action",
                    "expected_user_responses": ["yes"],
                    "expires_after_turns": 1,
                    "confidence": 0.9,
                },
            },
            "memory_writer": {
                "short_term_context": "The assistant offered to perform a playful blub-blub action.",
                "assistant_obligation_next_turn": "perform the playful blub-blub action directly",
            },
        }
        strategy = nodes._short_term_context_response_strategy("yes", working_memory)
        decision = nodes._make_auditor_decision("phase_3", memo="deliver short-term context")

        guarded = nodes._guard_phase3_decision_for_grounded_turn(
            state,
            decision,
            {},
            {},
            working_memory,
            loop_count=0,
            reasoning_budget=1,
            response_strategy=strategy,
        )

        self.assertIs(guarded, decision)

    def test_grounding_guard_clean_fails_after_unproductive_planning_pass(self):
        state = empty_anima_state()
        state["user_input"] = "Check this against grounded evidence."
        state["start_gate_switches"] = {
            "answer_mode_policy": {
                "grounded_delivery_required": True,
                "preferred_answer_mode": "grounded_answer",
                "question_class": "grounded_recall_or_review",
            },
            "start_gate_turn_contract": {
                "user_intent": "other",
                "answer_mode_preference": "generic_dialogue",
                "requires_grounding": True,
            },
        }
        decision = nodes._make_auditor_decision("phase_3", memo="try delivery")

        guarded = nodes._guard_phase3_decision_for_grounded_turn(
            state,
            decision,
            {"action_plan": {"current_step_goal": "No executable source plan.", "required_tool": ""}},
            {},
            {},
            loop_count=1,
            reasoning_budget=1,
            response_strategy={},
        )

        self.assertEqual(guarded["action"], "clean_failure")
        self.assertIn("no analysis packet", guarded["memo"])


if __name__ == "__main__":
    unittest.main()
