import unittest

from Core.pipeline.packets import compact_s_thinking_packet_for_prompt
from Core.pipeline.start_gate import _build_s_thinking_packet


class ThinkingHandoffV1Tests(unittest.TestCase):
    def test_build_s_thinking_packet_emits_thinking_handoff_v1(self):
        packet = _build_s_thinking_packet(
            start_gate_contract={
                "normalized_goal": "Answer from verified memory evidence.",
                "current_turn_facts": ["The user asks about stored diary access."],
                "requires_grounding": True,
                "needs_planning": True,
                "turn_contract": {"answer_mode_preference": "grounded_recall"},
                "answer_mode_policy": {},
            },
            start_gate_review={},
            start_gate_switches={},
            reasoning_plan={"reasoning_budget": 2},
            next_node="-1a",
            route_reason="Stored evidence is required.",
            analysis_report={
                "investigation_status": "COMPLETED",
                "contract_status": "satisfied",
                "evidences": [{"source_id": "d1", "source_type": "diary", "extracted_fact": "The diary exists."}],
                "source_judgments": [{"accepted_facts": ["The user wrote diary records."]}],
                "usable_field_memo_facts": ["The assistant can search configured records."],
            },
        )

        self.assertEqual(packet["schema"], "ThinkingHandoff.v1")
        for key in (
            "producer",
            "recipient",
            "goal_state",
            "evidence_state",
            "what_we_know",
            "what_is_missing",
            "next_node",
            "next_node_reason",
            "constraints_for_next_node",
        ):
            self.assertIn(key, packet)
        self.assertEqual(packet["producer"], "-1s")
        self.assertEqual(packet["recipient"], "-1a")
        self.assertIn("The diary exists.", packet["what_we_know"])
        self.assertIn("do not write tool names or queries in -1s", packet["constraints_for_next_node"])

    def test_build_s_thinking_packet_keeps_empty_fields_present(self):
        packet = _build_s_thinking_packet(
            start_gate_contract={"normalized_goal": "", "turn_contract": {}, "answer_mode_policy": {}},
            start_gate_review={},
            start_gate_switches={},
            reasoning_plan={},
            next_node="phase_3",
            route_reason="",
            analysis_report={},
        )

        self.assertEqual(packet["schema"], "ThinkingHandoff.v1")
        self.assertEqual(packet["next_node"], "phase_3")
        self.assertIsInstance(packet["what_we_know"], list)
        self.assertIsInstance(packet["what_is_missing"], list)

    def test_compact_s_thinking_packet_preserves_thinking_handoff_fields(self):
        compact = compact_s_thinking_packet_for_prompt(
            {
                "schema": "ThinkingHandoff.v1",
                "producer": "-1s",
                "recipient": "phase_3",
                "goal_state": "g" * 500,
                "evidence_state": "evidence ready",
                "what_we_know": [f"fact-{idx}" for idx in range(12)],
                "what_is_missing": [f"gap-{idx}" for idx in range(12)],
                "next_node": "phase_3",
                "next_node_reason": "r" * 500,
                "constraints_for_next_node": [f"avoid-{idx}" for idx in range(12)],
            },
            role="strategist",
        )

        self.assertEqual(compact["schema"], "ThinkingHandoff.v1")
        self.assertEqual(compact["next_node"], "phase_3")
        self.assertLessEqual(len(compact["goal_state"]), 220)
        self.assertEqual(len(compact["what_we_know"]), 8)
        self.assertEqual(len(compact["constraints_for_next_node"]), 6)

    def test_compact_s_thinking_packet_maps_old_schema_to_thinking_handoff(self):
        compact = compact_s_thinking_packet_for_prompt(
            {
                "schema": "SThinkingPacket.v1",
                "situation_thinking": {"user_intent": "requesting_memory_recall", "domain": "memory_recall"},
                "loop_summary": {
                    "current_evidence_state": "requires_grounding=True",
                    "gaps": ["stored evidence missing"],
                },
                "next_direction": {"avoid": ["do not write final answer text"]},
                "routing_decision": {"next_node": "119", "reason": "budget exhausted"},
            }
        )

        self.assertEqual(compact["schema"], "ThinkingHandoff.v1")
        self.assertEqual(compact["next_node"], "phase_119")
        self.assertEqual(compact["recipient"], "phase_119")
        self.assertIn("stored evidence missing", compact["what_is_missing"])


if __name__ == "__main__":
    unittest.main()
