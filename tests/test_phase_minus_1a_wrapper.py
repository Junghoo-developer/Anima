import unittest
from unittest.mock import patch

import Core.nodes as nodes
from Core.state import empty_anima_state


class PhaseMinus1AWrapperTests(unittest.TestCase):
    def test_wrapper_preserves_base_strategist_output_without_postprocessing(self):
        state = empty_anima_state()
        state["user_input"] = "오모리에 대해 말해봐"
        state["analysis_report"] = {
            "investigation_status": "INCOMPLETE",
            "situational_brief": "근거가 아직 얇다.",
        }
        base_result = {
            "strategist_output": {
                "case_theory": "base theory",
                "operation_plan": {
                    "plan_type": "tool_evidence",
                    "source_lane": "field_memo_review",
                    "output_act": "answer_narrative_fact",
                    "user_goal": "오모리에 대해 말해봐",
                },
                "goal_lock": {
                    "user_goal_core": "오모리에 대해 말해봐",
                    "answer_shape": "fact_brief",
                    "must_not_expand_to": [],
                },
                "convergence_state": "gathering",
                "achieved_findings": [],
                "delivery_readiness": "need_one_more_source",
                "next_frontier": ["오모리 관련 근거 1개 더 찾기"],
                "action_plan": {
                    "current_step_goal": "오모리 관련 근거를 하나 더 확보한다.",
                    "required_tool": "tool_search_field_memos(query='오모리', limit=8)",
                    "next_steps_forecast": ["근거 확보 후 짧게 요약한다."],
                    "operation_contract": {},
                },
                "response_strategy": {
                    "reply_mode": "grounded_answer",
                    "direct_answer_seed": "",
                },
                "war_room_contract": {},
                "candidate_pairs": [],
            },
            "response_strategy": {
                "reply_mode": "grounded_answer",
                "direct_answer_seed": "",
            },
            "reasoning_board": {"candidate_pairs": [], "fact_cells": []},
            "war_room": {},
            "thought_logs": [],
        }

        with patch.object(nodes, "_previous_phase_minus_1a_thinker", return_value=base_result), patch.object(
            nodes,
            "_build_strategist_objection_packet",
            return_value={"has_objection": False},
        ) as objection_builder, patch.object(
            nodes,
            "_ensure_social_turn_strategist_delivery",
            side_effect=AssertionError("postprocessing should not run"),
        ), patch.object(
            nodes,
            "_ensure_direct_delivery_response_strategy",
            side_effect=AssertionError("postprocessing should not run"),
        ), patch.object(
            nodes,
            "_ensure_operation_plan_in_strategist_payload",
            side_effect=AssertionError("postprocessing should not run"),
        ), patch.object(
            nodes,
            "_ensure_operation_contract_in_strategist_payload",
            side_effect=AssertionError("postprocessing should not run"),
        ), patch.object(
            nodes,
            "_ensure_war_room_contract_in_strategist_payload",
            side_effect=AssertionError("postprocessing should not run"),
        ), patch.object(
            nodes,
            "_ensure_strategist_continuity_fields",
            side_effect=AssertionError("postprocessing should not run"),
        ), patch.object(
            nodes,
            "_force_findings_first_delivery_strategy",
            side_effect=AssertionError("postprocessing should not run"),
        ):
            result = nodes.phase_minus_1a_thinker(state)

        self.assertEqual(result["strategist_output"], base_result["strategist_output"])
        self.assertEqual(result["response_strategy"], base_result["strategist_output"]["response_strategy"])
        self.assertEqual(
            result["operation_plan"]["plan_type"],
            base_result["strategist_output"]["operation_plan"]["plan_type"],
        )
        self.assertEqual(result["strategist_objection_packet"], {"has_objection": False})
        objection_builder.assert_called_once_with(
            base_result["strategist_output"],
            state["analysis_report"],
            state["user_input"],
        )


if __name__ == "__main__":
    unittest.main()
