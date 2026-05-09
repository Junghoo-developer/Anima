import unittest

import Core.nodes as nodes
from Core.pipeline.contracts import StrategistReasoningOutput
from Core.prompt_builders import build_phase_minus_1a_prompt
from Core.state import empty_anima_state


class StrategistNoToolRequestTests(unittest.TestCase):
    def test_strategist_reasoning_output_schema_has_no_tool_request(self):
        self.assertNotIn("tool_request", StrategistReasoningOutput.model_fields)
        self.assertNotIn("tool_request", StrategistReasoningOutput.model_json_schema().get("properties", {}))

    def test_deprecated_ensure_helper_does_not_promote_required_tool(self):
        payload = {
            "action_plan": {
                "current_step_goal": "Ask phase 0 for one source.",
                "required_tool": "tool_search_memory(query='x')",
                "next_steps_forecast": [],
            }
        }

        normalized = nodes._ensure_tool_request_in_strategist_payload(payload)

        self.assertNotIn("tool_request", normalized)
        self.assertEqual(normalized["action_plan"]["required_tool"], "tool_search_memory(query='x')")

    def test_deprecated_ensure_helper_preserves_legacy_read_side_tool_request(self):
        payload = {
            "tool_request": {
                "should_call_tool": True,
                "tool_name": "tool_search_field_memos",
                "tool_args": {"query": "legacy", "limit": 5},
            }
        }

        normalized = nodes._ensure_tool_request_in_strategist_payload(payload)

        self.assertEqual(normalized["tool_request"]["tool_name"], "tool_search_field_memos")
        self.assertEqual(normalized["tool_request"]["tool_args"]["query"], "legacy")

    def test_fallback_strategist_output_does_not_emit_tool_request(self):
        state = empty_anima_state()
        state["user_input"] = "내 일기에서 아무거나 찾아봐"
        strategist_output, _board = nodes._base_fallback_strategist_output(
            state["user_input"],
            {"what_is_missing": ["one source needed"], "next_node": "-1a"},
            {},
            {},
        )

        self.assertNotIn("tool_request", strategist_output)
        self.assertIn("operation_contract", strategist_output["action_plan"])

    def test_phase_minus_1a_prompt_forbids_tool_call_authorship(self):
        prompt = build_phase_minus_1a_prompt(
            user_input="search",
            recent_context="",
            user_state="",
            user_char="",
            time_gap=0,
            tolerance=1,
            bio_status="",
            songryeon_thoughts="",
            working_memory_packet="{}",
            tool_carryover_packet="{}",
            start_gate_review_packet="{}",
            fact_cells_packet="[]",
            auditor_memo="",
            war_room_packet="{}",
        )

        self.assertIn("Do not author tool calls", prompt)
        self.assertIn("Phase 0 supervisor decides exact tool name", prompt)


if __name__ == "__main__":
    unittest.main()
