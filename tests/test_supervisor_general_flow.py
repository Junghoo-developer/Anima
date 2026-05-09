import unittest

from langchain_core.messages import AIMessage

from Core.pipeline.supervisor import run_phase_0_supervisor
from Core.state import empty_anima_state


class _FakeSupervisorLlm:
    def __init__(self, responses):
        self.responses = list(responses)
        self.messages = []

    def bind_tools(self, _tools):
        return self

    def invoke(self, messages):
        self.messages.append(messages)
        if self.responses:
            return self.responses.pop(0)
        return AIMessage(content="no tool")


def _run_supervisor(state, fake):
    return run_phase_0_supervisor(
        state,
        llm_supervisor=fake,
        available_tools=[],
        planned_operation_contract_from_state=lambda _state: {
            "operation_kind": "search_new_source",
            "target_scope": "diary",
        },
        execution_trace_after_supervisor=lambda _state, tool, args: {"tool": tool, "args": args or {}},
        build_direct_tool_message=lambda _instruction: None,
        build_supervisor_tool_message=lambda tool_name, tool_args, _user_input, _operation_contract=None: AIMessage(
            content="",
            tool_calls=[{"name": tool_name, "args": tool_args, "id": "tool_1"}],
        ),
        ops_tool_cards=lambda: [{"name": "tool_search_memory"}],
        ops_node_cards=lambda: [{"name": "phase_1"}],
        print_fn=lambda *_args, **_kwargs: None,
    )


class SupervisorGeneralFlowTests(unittest.TestCase):
    def test_general_llm_flow_creates_tool_call_without_direct_instruction(self):
        state = empty_anima_state()
        state["user_input"] = "내 일기를 검색해봐"
        state["auditor_instruction"] = "choose one safe search tool"
        fake = _FakeSupervisorLlm([
            AIMessage(content="", tool_calls=[{"name": "tool_search_memory", "args": {"query": "일기", "limit": 5}, "id": "x"}])
        ])

        result = _run_supervisor(state, fake)

        self.assertEqual(result["execution_status"], "tool_call_ready")
        self.assertEqual(result["messages"][0].tool_calls[0]["name"], "tool_search_memory")
        self.assertEqual(result["messages"][0].tool_calls[0]["args"]["query"], "일기")

    def test_legacy_strategist_tool_request_no_longer_shortcuts_supervisor(self):
        state = empty_anima_state()
        state["user_input"] = "search"
        state["strategist_output"] = {
            "tool_request": {
                "should_call_tool": True,
                "tool_name": "tool_search_field_memos",
                "tool_args": {"query": "legacy"},
            }
        }
        fake = _FakeSupervisorLlm([
            AIMessage(content="", tool_calls=[{"name": "tool_search_memory", "args": {"query": "fresh"}, "id": "x"}])
        ])

        result = _run_supervisor(state, fake)

        self.assertTrue(fake.messages)
        self.assertEqual(result["messages"][0].tool_calls[0]["args"]["query"], "fresh")

    def test_fact_cells_are_projected_into_supervisor_prompt(self):
        state = empty_anima_state()
        state["reasoning_board"] = {
            "fact_cells": [
                {
                    "fact_id": "f1",
                    "extracted_fact": "정후는 일기를 이주했다.",
                    "source_id": "diary_1",
                    "source_type": "PastRecord:Diary",
                    "excerpt": "일기 원문",
                }
            ]
        }
        fake = _FakeSupervisorLlm([AIMessage(content="no tool")])

        _run_supervisor(state, fake)
        prompt = fake.messages[0][0].content

        self.assertIn("[fact_cells]", prompt)
        self.assertIn('"fact_id": "f1"', prompt)
        self.assertIn("정후는 일기를 이주했다.", prompt)

    def test_thinking_handoff_missing_items_are_projected_into_supervisor_prompt(self):
        state = empty_anima_state()
        state["s_thinking_packet"] = {
            "schema": "ThinkingHandoff.v1",
            "what_is_missing": ["date-specific source"],
        }
        fake = _FakeSupervisorLlm([AIMessage(content="no tool")])

        _run_supervisor(state, fake)
        prompt = fake.messages[0][0].content

        self.assertIn("[s_thinking_packet_what_is_missing]", prompt)
        self.assertIn("date-specific source", prompt)

    def test_legacy_s_thinking_gaps_are_still_projected_for_one_season(self):
        state = empty_anima_state()
        state["s_thinking_packet"] = {"loop_summary": {"gaps": ["legacy gap"]}}
        fake = _FakeSupervisorLlm([AIMessage(content="no tool")])

        _run_supervisor(state, fake)
        prompt = fake.messages[0][0].content

        self.assertIn("legacy gap", prompt)

    def test_three_empty_llm_attempts_block_cleanly(self):
        state = empty_anima_state()
        fake = _FakeSupervisorLlm([
            AIMessage(content="no tool"),
            AIMessage(content="still no tool"),
            AIMessage(content="final no tool"),
        ])

        result = _run_supervisor(state, fake)

        self.assertEqual(result["execution_status"], "blocked")
        self.assertEqual(len(fake.messages), 3)


if __name__ == "__main__":
    unittest.main()
