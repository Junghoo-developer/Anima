import unittest

import Core.nodes as nodes
from Core.pipeline.contracts import StrategistReasoningOutput
from Core.pipeline.plans import (
    normalize_strategist_goal,
    strategist_answer_mode_target_from_policy,
    strategist_goal_from_goal_lock,
)
from Core.pipeline.strategy import run_phase_minus_1a_thinker


class StrategistGoalMigrationTests(unittest.TestCase):
    def test_contract_schema_contains_strategist_goal(self):
        fields = StrategistReasoningOutput.model_fields
        self.assertIn("strategist_goal", fields)
        schema = StrategistReasoningOutput.model_json_schema()
        self.assertIn("StrategistGoal", schema.get("$defs", {}))

    def test_strategist_goal_normalizer_bounds_legacy_alias_shape(self):
        normalized = normalize_strategist_goal(
            {
                "user_goal_core": " Answer compactly. ",
                "answer_mode_target": "made_up",
                "success_criteria": ["one", "one", "two", "three", "four", "five", "six"],
                "scope": "too_big",
            }
        )

        self.assertEqual(normalized["user_goal_core"], "Answer compactly.")
        self.assertEqual(normalized["answer_mode_target"], "ambiguous")
        self.assertEqual(normalized["success_criteria"], ["one", "two", "three", "four", "five"])
        self.assertEqual(normalized["scope"], "narrow")

    def test_answer_mode_policy_maps_to_strategist_goal_target_without_raw_intent_classifier(self):
        self.assertEqual(
            strategist_answer_mode_target_from_policy({"preferred_answer_mode": "grounded_recall"}),
            "memory_recall",
        )
        self.assertEqual(
            strategist_answer_mode_target_from_policy({"preferred_answer_mode": "public_parametric_knowledge"}),
            "public_parametric",
        )
        self.assertEqual(strategist_answer_mode_target_from_policy({}), "ambiguous")

    def test_sanitizer_writes_strategist_goal_and_legacy_alias(self):
        user_input = "오모리의 주인공 이름은?"
        payload = {
            "operation_plan": {
                "plan_type": "direct_delivery",
                "source_lane": "none",
                "output_act": "answer_narrative_fact",
                "user_goal": user_input,
            },
            "goal_lock": {
                "user_goal_core": user_input,
                "answer_shape": "direct_answer",
                "must_not_expand_to": [],
            },
            "action_plan": {
                "current_step_goal": user_input,
                "required_tool": "",
                "next_steps_forecast": [],
            },
            "strategist_goal": {
                "user_goal_core": user_input,
                "answer_mode_target": "ambiguous",
                "success_criteria": [],
                "scope": "narrow",
            },
        }

        sanitized = nodes._sanitize_strategist_goal_fields(
            payload,
            user_input,
            {"answer_mode_policy": {"preferred_answer_mode": "public_parametric_knowledge"}},
        )

        self.assertEqual(sanitized["strategist_goal"], sanitized["normalized_goal"])
        self.assertEqual(sanitized["strategist_goal"]["answer_mode_target"], "public_parametric")
        self.assertNotEqual(sanitized["strategist_goal"]["user_goal_core"], user_input)
        self.assertNotEqual(sanitized["operation_plan"]["user_goal"], user_input)
        self.assertNotEqual(sanitized["action_plan"]["current_step_goal"], user_input)

    def test_phase_minus_1a_wrapper_exposes_top_level_aliases_without_mutating_output(self):
        base_output = {
            "strategist_output": {
                "operation_plan": {"plan_type": "direct_delivery", "user_goal": "legacy goal"},
                "goal_lock": {
                    "user_goal_core": "Answer the current turn.",
                    "answer_shape": "direct_answer",
                    "must_not_expand_to": [],
                },
                "response_strategy": {},
            },
            "reasoning_board": {},
        }

        def previous(_state):
            return dict(base_output)

        result = run_phase_minus_1a_thinker(
            {},
            previous_phase_minus_1a_thinker=previous,
            build_strategist_objection_packet=lambda *_args: {},
            normalize_operation_plan=lambda plan: plan,
            attach_ledger_event=lambda result, *_args, **_kwargs: result,
        )

        self.assertNotIn("strategist_goal", result["strategist_output"])
        self.assertEqual(result["strategist_goal"], result["normalized_goal"])
        self.assertEqual(result["strategist_goal"]["user_goal_core"], "Answer the current turn.")


if __name__ == "__main__":
    unittest.main()
