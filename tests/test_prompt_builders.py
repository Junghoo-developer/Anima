import unittest

from Core.prompt_builders import (
    build_phase_2b_prompt,
    build_phase3_sys_prompt,
    build_phase3_sys_prompt_cautious_minimal,
    build_phase3_sys_prompt_current_turn_grounding,
    build_phase3_sys_prompt_memory_recall,
    build_phase3_sys_prompt_public_parametric,
    build_phase3_sys_prompt_self_kernel,
    build_phase3_sys_prompt_simple_continuation,
    build_phase_minus_1a_prompt,
    compact_phase3_contract_for_prompt,
)


class PromptBuilderTests(unittest.TestCase):
    def test_phase_minus_1a_prompt_contains_tool_query_rule(self):
        prompt = build_phase_minus_1a_prompt(
            user_input="질문",
            recent_context="문맥",
            user_state="state",
            user_char="char",
            time_gap=1.0,
            tolerance=0.5,
            bio_status="stable",
            songryeon_thoughts="thoughts",
            working_memory_packet="wm",
            tool_carryover_packet="carry",
            strategist_goal_packet='{"user_goal_core":"answer compactly"}',
            start_gate_review_packet="gate",
            answer_mode_policy_packet='{"preferred_answer_mode":"public_parametric_knowledge"}',
            fact_cells_packet='[{"fact_id":"f1","extracted_fact":"verified"}]',
            auditor_memo="memo",
            war_room_packet="war",
        )
        self.assertIn("Do not pass the whole user sentence as a search query", prompt)
        self.assertIn("[user_input]\n질문", prompt)
        self.assertIn("[answer_mode_policy]\n{\"preferred_answer_mode\":\"public_parametric_knowledge\"}", prompt)
        self.assertIn("[fact_cells]\n[{\"fact_id\":\"f1\",\"extracted_fact\":\"verified\"}]", prompt)
        self.assertIn("[strategist_goal]\n{\"user_goal_core\":\"answer compactly\"}", prompt)
        self.assertIn("goal_contract -> strategist_goal -> action_plan", prompt)
        self.assertIn("ThinkingHandoff.v1", prompt)
        self.assertIn("public_parametric_knowledge", prompt)
        self.assertNotIn("[analysis_report]", prompt)
        self.assertNotIn("[raw_read_report]", prompt)
        self.assertNotIn("[reasoning_board]", prompt)
        self.assertNotIn("[tactical_briefing]", prompt)
        self.assertNotIn("Rules:\n1. Treat phase_2", prompt)

    def test_phase_2b_prompt_deprecates_answer_shaped_field_memo_brief(self):
        prompt = build_phase_2b_prompt(
            analysis_mode="tool_grounded",
            user_input="이름을 말해",
            raw_read_packet="raw",
            auditor_memo="memo",
            working_memory_packet="wm",
            operation_contract_packet="contract",
            execution_trace_packet="trace",
            tool_carryover_packet="carry",
            critic_lens_prompt="lens",
            source_relay_prompt="relay",
        )
        self.assertIn("usable_field_memo_facts", prompt)
        self.assertIn("[source_relay_packet]\nrelay", prompt)
        self.assertNotIn("10. Treat critic_lens_packet", prompt)

    def test_phase3_mode_prompts_are_short_and_mode_specific(self):
        contract = '{"answer_mode":"public_parametric_knowledge"}'
        prompts = [
            build_phase3_sys_prompt_public_parametric(contract),
            build_phase3_sys_prompt_self_kernel(contract),
            build_phase3_sys_prompt_memory_recall(contract),
            build_phase3_sys_prompt_current_turn_grounding(contract),
            build_phase3_sys_prompt_simple_continuation(contract),
            build_phase3_sys_prompt_cautious_minimal(contract),
        ]

        for prompt in prompts:
            self.assertIn("[PHASE3_PROMPT_CONTRACT]", prompt)
            self.assertIn("Common footer", prompt)
            self.assertNotIn("Behavior rules", prompt)
            self.assertLessEqual(prompt.count("\n1."), 1)
            self.assertLessEqual(prompt.count("\n5."), 1)
            self.assertNotIn("\n6.", prompt)

        self.assertIn("canonical", prompts[0])
        self.assertIn("identity", prompts[1])
        self.assertIn("facts_allowed", prompts[2])
        self.assertIn("current-turn", prompts[3])
        self.assertIn("pending_dialogue_act", prompts[4])
        self.assertIn("user_facing_label", prompts[5])

        routed = build_phase3_sys_prompt("public_parametric_knowledge", contract)
        self.assertIn("public_parametric_knowledge", routed)

    def test_phase3_prompt_contract_hides_internal_policy_bulk(self):
        compact = compact_phase3_contract_for_prompt({
            "READY": True,
            "ANSWER_MODE": "memory_recall",
            "USER_GOAL": "remember the name",
            "SAY_THIS": "송련",
            "FACTS_ALLOWED": ["Name is Songryeon"],
            "CURRENT_TURN_FACTS_ALLOWED": ["current"],
            "PARAMETRIC_KNOWLEDGE_ALLOWED": False,
            "EVIDENCE_LEDGER": {"events": ["hidden"]},
            "ANSWER_MODE_POLICY": {"grounded_delivery_required": True},
            "RESCUE_HANDOFF": {"what_we_know": ["known"], "trigger": "budget_exceeded"},
            "SHORT_TERM_CONTEXT": {"assistant_obligation_next_turn": "answer"},
        })

        self.assertEqual(compact["schema"], "Phase3PromptContract.v1")
        self.assertEqual(compact["answer_mode"], "memory_recall")
        self.assertIn("Name is Songryeon", compact["facts_allowed"])
        dumped = str(compact)
        self.assertNotIn("EVIDENCE_LEDGER", dumped)
        self.assertNotIn("ANSWER_MODE_POLICY", dumped)
        self.assertNotIn("budget_exceeded", dumped)


if __name__ == "__main__":
    unittest.main()
