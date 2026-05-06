import unittest

import Core.nodes as nodes


class StrategistToolContractTests(unittest.TestCase):
    def test_required_tool_is_promoted_to_first_class_tool_request(self):
        strategist_output = {
            "action_plan": {
                "current_step_goal": "Execute the selected recall tool once.",
                "required_tool": "tool_search_field_memos(query='써니 누나', limit=8)",
                "next_steps_forecast": [],
                "operation_contract": {},
            }
        }

        normalized = nodes._ensure_tool_request_in_strategist_payload(strategist_output)
        decision = nodes._decision_from_strategist_tool_contract(normalized, {})

        self.assertEqual(normalized["tool_request"]["tool_name"], "tool_search_field_memos")
        self.assertEqual(normalized["tool_request"]["tool_args"], {"query": "써니 누나", "limit": 8})
        self.assertEqual(decision["action"], "call_tool")
        self.assertEqual(decision["tool_name"], "tool_search_field_memos")
        self.assertEqual(decision["tool_args"], {"query": "써니 누나", "limit": 8})
        self.assertEqual(decision["instruction"], 'tool_search_field_memos(query="써니 누나", limit=8)')

    def test_unanchored_topic_guard_ignores_operational_memo_text(self):
        decision = nodes._make_auditor_decision(
            "phase_3",
            memo="Blocked unrelated old topic drift and re-anchored to the current user request.",
        )

        self.assertFalse(nodes._decision_uses_unanchored_topic(decision, "써니의 누나는 누군지 기억해?", {}))


if __name__ == "__main__":
    unittest.main()
