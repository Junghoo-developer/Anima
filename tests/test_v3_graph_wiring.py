import inspect
import unittest

from langchain_core.messages import AIMessage

import Core.nodes as nodes
import Core.graph as graph
from Core.pipeline.supervisor import run_phase_0_supervisor
from Core.state import empty_anima_state


class _NoopSupervisorLlm:
    def bind_tools(self, _tools):
        return self


class V3GraphWiringTests(unittest.TestCase):
    def test_graph_source_no_longer_registers_old_pre_delivery_auditor(self):
        source = inspect.getsource(graph)

        self.assertNotIn('workflow.add_node("-1b_auditor"', source)
        self.assertNotIn('workflow.add_edge("phase_2", "-1b_auditor")', source)
        self.assertNotIn('workflow.add_edge("warroom_deliberator", "-1b_auditor")', source)
        self.assertIn('workflow.add_edge("phase_2", "-1s_start_gate")', source)
        self.assertIn('workflow.add_edge("warroom_deliberator", "-1s_start_gate")', source)
        self.assertIn('"phase_3": "phase_3"', source)

    def test_s_thinking_router_uses_start_gate_routing_decision(self):
        state = empty_anima_state()
        state["s_thinking_packet"] = {"routing_decision": {"next_node": "phase_3"}}
        self.assertEqual(graph.route_after_s_thinking(state), "phase_3")

        state["s_thinking_packet"] = {"routing_decision": {"next_node": "-1a"}}
        self.assertEqual(graph.route_after_s_thinking(state), "-1a_thinker")

        state["s_thinking_packet"] = {"routing_decision": {"next_node": "119"}}
        self.assertEqual(graph.route_after_s_thinking(state), "phase_119")

    def test_strategist_routes_tool_request_to_supervisor_otherwise_start_gate(self):
        state = empty_anima_state()
        state["strategist_output"] = {
            "tool_request": {
                "should_call_tool": True,
                "tool_name": "tool_search_field_memos",
                "tool_args": {"query": "sunny", "limit": 6},
            }
        }
        self.assertEqual(graph.route_after_strategist(state), "0_supervisor")

        state["strategist_output"] = {"tool_request": {"should_call_tool": False}}
        self.assertEqual(graph.route_after_strategist(state), "-1s_start_gate")

    def test_strategist_routes_no_tool_delivery_contract_to_phase3(self):
        state = empty_anima_state()
        state["strategist_output"] = {
            "operation_plan": {
                "plan_type": "direct_delivery",
                "source_lane": "none",
                "output_act": "answer",
            },
            "action_plan": {"required_tool": ""},
            "delivery_readiness": "deliver_now",
            "convergence_state": "deliverable",
            "tool_request": {"should_call_tool": False},
            "response_strategy": {
                "reply_mode": "cautious_minimal",
                "answer_goal": "Explain the current capability boundary directly.",
                "must_include_facts": ["This is a capability-boundary answer, not a search result."],
                "must_avoid_claims": ["Do not pretend a search happened."],
            },
        }
        state["operation_plan"] = state["strategist_output"]["operation_plan"]
        state["response_strategy"] = state["strategist_output"]["response_strategy"]

        self.assertEqual(graph.route_after_strategist(state), "phase_3")

    def test_strategist_rejects_non_deliverable_clean_failure_seed(self):
        state = empty_anima_state()
        state["strategist_output"] = {
            "operation_plan": {
                "plan_type": "direct_delivery",
                "source_lane": "none",
                "output_act": "answer",
            },
            "action_plan": {"required_tool": ""},
            "delivery_readiness": "need_reframe",
            "convergence_state": "gathering",
            "tool_request": {},
            "response_strategy": {
                "reply_mode": "cautious_minimal",
                "direct_answer_seed": "With the evidence currently available, I cannot settle that yet.",
                "must_include_facts": [],
            },
        }
        state["operation_plan"] = state["strategist_output"]["operation_plan"]
        state["response_strategy"] = state["strategist_output"]["response_strategy"]

        self.assertEqual(graph.route_after_strategist(state), "-1s_start_gate")

    def test_strategist_keeps_source_plan_without_tool_out_of_phase3(self):
        state = empty_anima_state()
        state["strategist_output"] = {
            "operation_plan": {
                "plan_type": "tool_evidence",
                "source_lane": "memory_search",
                "output_act": "answer_memory_recall",
            },
            "action_plan": {"required_tool": ""},
            "tool_request": {"should_call_tool": False},
            "response_strategy": {
                "reply_mode": "grounded_answer",
                "answer_goal": "Answer after a memory search.",
            },
        }
        state["operation_plan"] = state["strategist_output"]["operation_plan"]
        state["response_strategy"] = state["strategist_output"]["response_strategy"]

        self.assertEqual(graph.route_after_strategist(state), "-1s_start_gate")

    def test_capability_boundary_question_becomes_no_tool_delivery_contract(self):
        strategist_output, _reasoning_board = nodes._base_fallback_strategist_output(
            "너 내 일기를 검색할 수 있어?",
            {},
            {},
            {},
            start_gate_switches={
                "answer_mode_policy": {
                    "question_class": "capability_boundary_question",
                    "preferred_answer_mode": "generic_dialogue",
                    "grounded_delivery_required": False,
                    "direct_delivery_allowed": False,
                },
                "start_gate_turn_contract": {
                    "user_intent": "capability_boundary_question",
                    "answer_mode_preference": "generic_dialogue",
                    "requires_grounding": False,
                    "direct_delivery_allowed": False,
                    "needs_planning": True,
                },
            },
        )
        state = empty_anima_state()
        state["strategist_output"] = strategist_output
        state["operation_plan"] = strategist_output["operation_plan"]
        state["response_strategy"] = strategist_output["response_strategy"]

        self.assertEqual(strategist_output["tool_request"], {})
        self.assertEqual(strategist_output["delivery_readiness"], "deliver_now")
        self.assertIn("memory/source access boundary", strategist_output["action_plan"]["current_step_goal"])
        self.assertEqual(strategist_output["response_strategy"]["direct_answer_seed"], "")
        self.assertIn("date-specific diary reads", strategist_output["response_strategy"]["evidence_brief"])
        self.assertTrue(
            any(
                "A capability answer is not itself a search" in fact
                for fact in strategist_output["response_strategy"]["must_include_facts"]
            )
        )
        self.assertEqual(graph.route_after_strategist(state), "phase_3")

    def test_phase3_payload_receives_no_tool_strategy_facts_without_seed(self):
        strategist_output, _reasoning_board = nodes._base_fallback_strategist_output(
            "너 내 일기를 검색할 수 있어?",
            {},
            {},
            {},
            start_gate_switches={
                "answer_mode_policy": {
                    "question_class": "capability_boundary_question",
                    "preferred_answer_mode": "generic_dialogue",
                    "grounded_delivery_required": False,
                    "direct_delivery_allowed": False,
                },
                "start_gate_turn_contract": {
                    "user_intent": "capability_boundary_question",
                    "answer_mode_preference": "generic_dialogue",
                    "requires_grounding": False,
                    "direct_delivery_allowed": False,
                    "needs_planning": True,
                },
            },
        )
        state = empty_anima_state()
        state["user_input"] = "너 내 일기를 검색할 수 있어?"
        state["strategist_output"] = strategist_output
        state["operation_plan"] = strategist_output["operation_plan"]
        state["response_strategy"] = strategist_output["response_strategy"]

        payload = nodes._build_phase3_delivery_payload(
            state,
            {},
            {
                "lane": "generic",
                "source_lane": "none",
                "output_act": "answer",
                "generic_delivery_packet": {"final_answer_brief": ""},
            },
        )
        contract = nodes._build_phase3_speaker_judge_contract(state, payload)

        self.assertEqual(payload["answer_seed"], "")
        self.assertTrue(payload["ready_for_delivery"])
        self.assertEqual(payload["fallback_action"], "direct_strategy_facts")
        self.assertTrue(
            any("configured grounded records" in fact for fact in contract["FACTS_ALLOWED"])
        )
        self.assertTrue(
            any("diary search is impossible" in claim for claim in contract["DO_NOT_SAY"])
        )

    def test_supervisor_blocked_or_empty_returns_to_start_gate(self):
        state = empty_anima_state()
        self.assertEqual(graph.route_after_supervisor(state), "-1s_start_gate")

        state["execution_status"] = "blocked"
        self.assertEqual(graph.route_after_supervisor(state), "-1s_start_gate")

    def test_supervisor_executes_strategist_tool_request_without_auditor_instruction(self):
        state = empty_anima_state()
        state["user_input"] = "search memory"
        state["strategist_output"] = {
            "tool_request": {
                "should_call_tool": True,
                "tool_name": "tool_search_field_memos",
                "tool_args": {"query": "sunny", "limit": 6},
                "rationale": "Search compact field memos.",
            }
        }

        result = run_phase_0_supervisor(
            state,
            llm_supervisor=_NoopSupervisorLlm(),
            available_tools=[],
            planned_operation_contract_from_state=lambda _state: {},
            execution_trace_after_supervisor=lambda _state, tool, args: {"tool": tool, "args": args or {}},
            build_direct_tool_message=lambda instruction: None,
            build_supervisor_tool_message=lambda tool_name, tool_args, user_input, operation_contract=None: AIMessage(
                content="",
                tool_calls=[{"name": tool_name, "args": tool_args, "id": "test_tool"}],
            ),
            ops_tool_cards=lambda: [],
            ops_node_cards=lambda: [],
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result["execution_status"], "tool_call_ready")
        self.assertEqual(result["messages"][0].tool_calls[0]["name"], "tool_search_field_memos")
        self.assertEqual(result["messages"][0].tool_calls[0]["args"]["query"], "sunny")


if __name__ == "__main__":
    unittest.main()
