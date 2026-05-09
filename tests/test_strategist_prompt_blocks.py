import unittest

from Core.prompt_builders import build_phase_minus_1a_prompt


def _prompt():
    return build_phase_minus_1a_prompt(
        user_input="user asks",
        recent_context="recent",
        user_state="state",
        user_char="char",
        time_gap=1.0,
        tolerance=0.9,
        bio_status="stable",
        songryeon_thoughts="thoughts",
        working_memory_packet="wm",
        tool_carryover_packet="carry",
        start_gate_review_packet="gate",
        fact_cells_packet='[{"fact_id":"f1","extracted_fact":"known fact"}]',
        auditor_memo="memo",
        war_room_packet="war",
        answer_mode_policy_packet="policy",
        evidence_ledger_packet="ledger",
        s_thinking_packet='{"schema":"ThinkingHandoff.v1","next_node":"-1a"}',
        strategist_goal_packet="goal",
    )


class StrategistPromptBlocksTests(unittest.TestCase):
    def test_old_large_blocks_are_not_present(self):
        prompt = _prompt()

        self.assertNotIn("[tactical_briefing]", prompt)
        self.assertNotIn("[analysis_report]", prompt)
        self.assertNotIn("[raw_read_report]", prompt)
        self.assertNotIn("[reasoning_board]", prompt)

    def test_fact_cells_block_is_present(self):
        prompt = _prompt()

        self.assertIn("[fact_cells]", prompt)
        self.assertIn('"fact_id":"f1"', prompt)

    def test_s_thinking_packet_block_is_preserved(self):
        prompt = _prompt()

        self.assertIn("[s_thinking_packet]", prompt)
        self.assertIn("ThinkingHandoff.v1", prompt)

    def test_prompt_rules_prioritize_handoff_and_forbid_fact_rejudgment(self):
        prompt = _prompt()

        self.assertIn("primary case state", prompt)
        self.assertIn("Do not re-judge facts", prompt)
        self.assertIn("Fact judgment authority belongs to -1s", prompt)

    def test_old_signature_arguments_are_rejected(self):
        with self.assertRaises(TypeError):
            build_phase_minus_1a_prompt(
                user_input="user asks",
                recent_context="recent",
                user_state="state",
                user_char="char",
                time_gap=1.0,
                tolerance=0.9,
                bio_status="stable",
                songryeon_thoughts="thoughts",
                tactical_briefing="old",
                working_memory_packet="wm",
                tool_carryover_packet="carry",
                start_gate_review_packet="gate",
                reasoning_board_packet="board",
                auditor_memo="memo",
                analysis_packet="analysis",
                raw_read_packet="raw",
                war_room_packet="war",
            )


if __name__ == "__main__":
    unittest.main()
