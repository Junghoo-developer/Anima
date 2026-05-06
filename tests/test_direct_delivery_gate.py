import unittest

import Core.nodes as nodes


class DirectDeliveryGateTests(unittest.TestCase):
    def test_generic_limiter_seed_is_not_meaningful_delivery_seed(self):
        self.assertFalse(
            nodes._has_meaningful_delivery_seed("지금 확인된 근거만으로는 단정하기 어려워.")
        )

    def test_answer_not_ready_strategy_never_counts_as_usable_seed(self):
        strategy = {
            "reply_mode": "cautious_minimal",
            "delivery_freedom_mode": "answer_not_ready",
            "direct_answer_seed": "지금 확인된 근거만으로는 단정하기 어려워.",
        }

        self.assertFalse(nodes._has_usable_response_seed(strategy, "오모리에 대해 알려줘"))

    def test_clean_failure_strategy_never_counts_as_usable_seed(self):
        strategy = {
            "reply_mode": "cautious_minimal",
            "delivery_freedom_mode": "clean_failure",
            "direct_answer_seed": "With the evidence currently available, I cannot settle that yet.",
        }

        self.assertFalse(nodes._has_usable_response_seed(strategy, "What is your name?"))

    def test_preferred_decision_routers_are_removed(self):
        self.assertFalse(hasattr(nodes, "_preferred_decision_from_operation_plan"))
        self.assertFalse(hasattr(nodes, "_preferred_decision_from_strategist"))

    def test_generic_continue_seed_is_not_meaningful_delivery_seed(self):
        self.assertFalse(
            nodes._has_meaningful_delivery_seed("좋아, 방금 흐름 그대로 이어가자.")
        )

    def test_social_reentry_no_longer_phase3_on_strategy_shape_alone(self):
        strategy = {
            "reply_mode": "continue_previous_offer",
            "delivery_freedom_mode": "proposal",
            "answer_goal": "Continue the immediately preceding thread without repeating the whole setup.",
            "direct_answer_seed": "좋아, 방금 흐름 그대로 이어가자.",
        }

        self.assertFalse(
            nodes._strategy_supports_direct_phase3(
                strategy,
                user_input="go on",
                recent_context="assistant: 좋아, 방금 흐름 그대로 이어가자.",
            )
        )

    def test_progress_contract_no_longer_upgrades_phase3_on_generic_continue_strategy(self):
        strategist_output = {
            "response_strategy": {
                "reply_mode": "continue_previous_offer",
                "delivery_freedom_mode": "proposal",
                "direct_answer_seed": "좋아, 방금 흐름 그대로 이어가자.",
            }
        }

        decision = nodes._apply_progress_contract(
            {"action": "plan_with_strategist"},
            stalled_repeats=1,
            same_operation_repeats=0,
            user_input="오모리에 대해서 다시 말해줘",
            analysis_data={},
            strategist_output=strategist_output,
            working_memory={},
            execution_trace={},
        )

        self.assertEqual(decision["action"], "plan_with_strategist")


if __name__ == "__main__":
    unittest.main()
