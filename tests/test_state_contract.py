import unittest

from Core.state import (
    ANIMA_STATE_DEFAULTS,
    LONG_LIVED_FIELDS,
    TURN_LIVED_FIELDS,
    anima_state_keys,
    build_initial_anima_state,
    cleanup_turn_lived_fields,
    empty_anima_state,
    get_strategist_goal,
    normalize_anima_state,
)


class StateContractTests(unittest.TestCase):
    def test_empty_state_covers_typed_dict_contract(self):
        state = empty_anima_state()
        self.assertEqual(set(anima_state_keys()), set(state.keys()))

    def test_build_initial_state_preserves_required_inputs(self):
        state = build_initial_anima_state(
            user_input="테스트",
            current_time="2026-04-24 21:00",
            time_gap=12.5,
            recent_context="recent",
            global_tolerance=0.8,
            user_state="focused",
            user_char="direct",
            songryeon_thoughts="notes",
            tactical_briefing="brief",
            biolink_status="stable",
            working_memory={"active_task": "inspect"},
        )
        self.assertEqual(state["user_input"], "테스트")
        self.assertEqual(state["working_memory"]["active_task"], "inspect")
        self.assertEqual(state["operation_plan"], {})
        self.assertEqual(state["strategist_goal"], {})
        self.assertEqual(state["normalized_goal"], {})
        self.assertEqual(state["strategy_audit"], {})
        self.assertEqual(state["war_room_output"], {})
        self.assertEqual(state["s_thinking_history"], {})
        self.assertEqual(state["delivery_review_rejections"], 0)

    def test_normalize_anima_state_backfills_missing_contract_fields(self):
        state = normalize_anima_state({"user_input": "hi", "analysis_report": {"foo": "bar"}})
        self.assertEqual(state["user_input"], "hi")
        self.assertEqual(state["analysis_report"], {"foo": "bar"})
        self.assertEqual(state["operation_plan"], ANIMA_STATE_DEFAULTS["operation_plan"])
        self.assertEqual(state["strategist_goal"], ANIMA_STATE_DEFAULTS["strategist_goal"])
        self.assertEqual(state["used_sources"], [])

    def test_strategist_goal_uses_one_season_normalized_goal_alias(self):
        state = empty_anima_state()
        state["normalized_goal"] = {
            "user_goal_core": "Answer the current turn.",
            "answer_mode_target": "ambiguous",
            "success_criteria": [],
            "scope": "narrow",
        }

        self.assertEqual(get_strategist_goal(state)["user_goal_core"], "Answer the current turn.")

        state["strategist_goal"] = {
            "user_goal_core": "Use the V3 strategist goal.",
            "answer_mode_target": "public_parametric",
            "success_criteria": ["answer directly"],
            "scope": "narrow",
        }
        self.assertEqual(get_strategist_goal(state)["user_goal_core"], "Use the V3 strategist goal.")

    def test_turn_lived_cleanup_preserves_long_lived_contract(self):
        self.assertFalse(LONG_LIVED_FIELDS & TURN_LIVED_FIELDS)
        state = empty_anima_state()
        state["user_input"] = "hello"
        state["working_memory"] = {"turn_summary": "stable context"}
        state["analysis_report"] = {"investigation_status": "COMPLETED"}
        state["strategist_goal"] = {"user_goal_core": "temporary"}
        state["normalized_goal"] = {"user_goal_core": "legacy temporary"}
        state["s_thinking_history"] = {"history_compact": [{"cycle": 1}], "current": {"x": "y"}}
        state["raw_read_report"] = {"read_mode": "field_memo_review"}
        state["messages"] = ["assistant answer"]
        state["used_sources"] = ["source-1"]
        state["delivery_review_rejections"] = 3

        cleaned = cleanup_turn_lived_fields(state)

        self.assertEqual(cleaned["user_input"], "hello")
        self.assertEqual(cleaned["working_memory"], {"turn_summary": "stable context"})
        self.assertEqual(cleaned["strategist_goal"], {})
        self.assertEqual(cleaned["normalized_goal"], {})
        self.assertEqual(cleaned["s_thinking_history"], {})
        self.assertEqual(cleaned["analysis_report"], {})
        self.assertEqual(cleaned["raw_read_report"], {})
        self.assertEqual(cleaned["messages"], [])
        self.assertEqual(cleaned["used_sources"], [])
        self.assertEqual(cleaned["delivery_review_rejections"], 0)


if __name__ == "__main__":
    unittest.main()
