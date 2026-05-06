import unittest

import Core.nodes as nodes
from Core.state import empty_anima_state


class StrategyArbitrationTests(unittest.TestCase):
    def test_merge_strategy_audits_keeps_inputs_without_mutation(self):
        arbitration = {
            "audit_kind": "critic_strategist_arbitration",
            "has_blocking_conflict": True,
            "pairs": [{"topic": "goal_slots", "conflict": True}],
        }
        satisfaction = {
            "approved_for_phase3": False,
            "strategy_satisfied": False,
            "next_action": "plan_with_strategist",
        }

        merged = nodes._merge_strategy_audits(arbitration, satisfaction)

        self.assertEqual(merged["audit_kind"], "merged_strategy_audit")
        self.assertEqual(len(merged["audits"]), 2)
        self.assertEqual(merged["audits"][0]["audit_kind"], "critic_strategist_arbitration")
        arbitration["pairs"][0]["topic"] = "mutated"
        self.assertEqual(merged["audits"][0]["pairs"][0]["topic"], "goal_slots")

    def test_blocking_conflict_when_missing_slots_meet_direct_delivery(self):
        state = empty_anima_state()
        state["user_input"] = "Tell me what you know about OMORI."
        state["tool_carryover"] = {}

        strategist_output = {
            "operation_plan": {
                "plan_type": "direct_delivery",
                "source_lane": "field_memo_review",
                "output_act": "answer_narrative_fact",
                "user_goal": "Recall OMORI facts.",
            },
            "goal_lock": {
                "user_goal_core": "Recall OMORI facts.",
                "answer_shape": "fact_brief",
                "must_not_expand_to": [],
            },
            "delivery_readiness": "deliver_now",
            "action_plan": {
                "current_step_goal": "Answer now.",
                "required_tool": "",
                "next_steps_forecast": [],
                "operation_contract": {},
            },
            "response_strategy": {
                "direct_answer_seed": "Sunny, Mari, Basil...",
                "must_include_facts": [],
                "must_avoid_claims": [],
            },
        }
        analysis_data = {
            "contract_status": "missing_slot",
            "missing_slots": ["current_goal_answer_seed"],
            "filled_slots": {},
            "rejected_sources": [],
            "replan_directive_for_strategist": "Gather one source that directly answers the current goal.",
            "can_answer_user_goal": False,
            "usable_field_memo_facts": [],
            "investigation_status": "EXPANSION_REQUIRED",
        }

        audit = nodes._build_strategy_arbitration_audit(state, strategist_output, analysis_data)

        self.assertEqual(audit["audit_kind"], "critic_strategist_arbitration")
        self.assertFalse(audit["has_blocking_conflict"])
        self.assertEqual(audit["blocking_topics"], [])

        decision = nodes._decision_from_strategy_arbitration_audit(
            audit,
            loop_count=0,
            reasoning_budget=2,
        )
        self.assertIsNone(decision)

    def test_no_blocking_conflict_when_contract_is_satisfied(self):
        state = empty_anima_state()
        state["user_input"] = "Recall my name."
        state["tool_carryover"] = {}

        strategist_output = {
            "operation_plan": {
                "plan_type": "direct_delivery",
                "source_lane": "field_memo_review",
                "output_act": "answer_identity_slot",
                "user_goal": "Answer the user's name.",
            },
            "goal_lock": {
                "user_goal_core": "Answer the user's name.",
                "answer_shape": "direct_answer",
                "must_not_expand_to": [],
            },
            "delivery_readiness": "deliver_now",
            "action_plan": {
                "current_step_goal": "Answer the name directly.",
                "required_tool": "",
                "next_steps_forecast": [],
                "operation_contract": {},
            },
            "response_strategy": {
                "direct_answer_seed": "Your name is Heo Jeonghu.",
                "must_include_facts": ["The user identified their name as Heo Jeonghu."],
                "must_avoid_claims": [],
            },
        }
        analysis_data = {
            "contract_status": "satisfied",
            "missing_slots": [],
            "filled_slots": {"identity.name": "Heo Jeonghu"},
            "rejected_sources": [],
            "replan_directive_for_strategist": "",
            "can_answer_user_goal": True,
            "usable_field_memo_facts": ["The user identified their name as Heo Jeonghu."],
            "investigation_status": "COMPLETED",
        }

        audit = nodes._build_strategy_arbitration_audit(state, strategist_output, analysis_data)

        self.assertFalse(audit["has_blocking_conflict"])
        self.assertEqual(audit["recommended_action"], "none")

        decision = nodes._decision_from_strategy_arbitration_audit(
            audit,
            loop_count=0,
            reasoning_budget=2,
        )
        self.assertIsNone(decision)

    def test_source_validity_does_not_block_when_lane_still_has_usable_material(self):
        state = empty_anima_state()
        state["user_input"] = "Do you remember who the protagonist of OMORI is?"
        state["tool_carryover"] = {}

        strategist_output = {
            "operation_plan": {
                "plan_type": "tool_evidence",
                "source_lane": "field_memo_review",
                "output_act": "answer_narrative_fact",
                "user_goal": "Identify the protagonist of OMORI.",
            },
            "goal_lock": {
                "user_goal_core": "Identify the protagonist of OMORI.",
                "answer_shape": "direct_answer",
                "must_not_expand_to": [],
            },
            "delivery_readiness": "need_one_more_source",
            "action_plan": {
                "current_step_goal": "Read one stronger OMORI memo.",
                "required_tool": "tool_search_field_memos(query='OMORI protagonist', limit=8)",
                "next_steps_forecast": [],
                "operation_contract": {},
            },
            "response_strategy": {
                "direct_answer_seed": "",
                "must_include_facts": [],
                "must_avoid_claims": [],
            },
        }
        analysis_data = {
            "contract_status": "wrong_source",
            "missing_slots": ["protagonist.name"],
            "filled_slots": {},
            "rejected_sources": [{"source_id": "memo_bad_1"}],
            "replan_directive_for_strategist": "Stay on OMORI memory, but narrow to protagonist-identifying evidence.",
            "can_answer_user_goal": False,
            "usable_field_memo_facts": ["Sunny is one of the central OMORI characters."],
            "field_memo_judgments": [
                {
                    "memo_id": "memo_good_1",
                    "relevance": "direct",
                    "usable_for_current_goal": True,
                    "accepted_facts": ["Sunny is one of the central OMORI characters."],
                    "rejected_facts": [],
                    "rejection_reason": "",
                    "recommended_followup_query": ["OMORI protagonist Sunny"],
                },
                {
                    "memo_id": "memo_bad_1",
                    "relevance": "irrelevant",
                    "usable_for_current_goal": False,
                    "accepted_facts": [],
                    "rejected_facts": ["Mari died after falling down the stairs."],
                    "rejection_reason": "This fact does not directly identify the protagonist.",
                    "recommended_followup_query": ["OMORI protagonist Sunny"],
                },
            ],
            "source_judgments": [
                {
                    "source_id": "memo_good_1",
                    "source_type": "field_memo",
                    "accepted_facts": ["Sunny is one of the central OMORI characters."],
                }
            ],
            "investigation_status": "EXPANSION_REQUIRED",
        }

        audit = nodes._build_strategy_arbitration_audit(state, strategist_output, analysis_data)

        self.assertEqual(audit["mode"], "thin_controller_observe_only")
        self.assertEqual(audit["pairs"], [])


if __name__ == "__main__":
    unittest.main()
