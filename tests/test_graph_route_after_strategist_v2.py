import unittest

import Core.graph as graph
from Core.state import empty_anima_state


class GraphRouteAfterStrategistV2Tests(unittest.TestCase):
    def test_tool_evidence_plan_without_tool_request_routes_to_supervisor(self):
        state = empty_anima_state()
        state["strategist_output"] = {
            "operation_plan": {
                "plan_type": "tool_evidence",
                "source_lane": "memory_search",
            },
            "action_plan": {
                "required_tool": "",
                "operation_contract": {"operation_kind": "search_new_source"},
            },
            "response_strategy": {},
        }

        self.assertEqual(graph.route_after_strategist(state), "0_supervisor")

    def test_non_deliverable_direct_plan_routes_to_supervisor_not_start_gate(self):
        state = empty_anima_state()
        state["strategist_output"] = {
            "operation_plan": {"plan_type": "direct_delivery", "source_lane": "none"},
            "action_plan": {"required_tool": ""},
            "delivery_readiness": "need_one_more_source",
            "response_strategy": {"answer_goal": "needs source"},
        }

        self.assertEqual(graph.route_after_strategist(state), "0_supervisor")

    def test_no_tool_delivery_contract_routes_to_phase3(self):
        state = empty_anima_state()
        state["strategist_output"] = {
            "operation_plan": {"plan_type": "direct_delivery", "source_lane": "none"},
            "action_plan": {"required_tool": ""},
            "delivery_readiness": "deliver_now",
            "response_strategy": {"must_include_facts": ["capability boundary answer"]},
        }

        self.assertEqual(graph.route_after_strategist(state), "phase_3")

    def test_legacy_tool_request_routes_to_supervisor_for_one_season(self):
        state = empty_anima_state()
        state["strategist_output"] = {
            "tool_request": {
                "should_call_tool": True,
                "tool_name": "tool_search_memory",
                "tool_args": {"query": "legacy"},
            }
        }

        self.assertEqual(graph.route_after_strategist(state), "0_supervisor")


if __name__ == "__main__":
    unittest.main()
