import unittest

import Core.nodes as nodes
from Core.readiness import readiness_from_auditor_action, readiness_from_delivery_payload
from Core.state import empty_anima_state


class ReadinessDecisionTests(unittest.TestCase):
    def test_auditor_action_maps_to_typed_readiness(self):
        call_tool = readiness_from_auditor_action(
            "call_tool",
            memo="Need memo recall.",
            tool_name="tool_search_field_memos",
            tool_args={"query": "songryeon"},
        )
        self.assertEqual(call_tool["status"], "needs_memory_recall")
        self.assertEqual(call_tool["allowed_next_hop"], "0_supervisor")

        clean_failure = readiness_from_auditor_action("answer_not_ready", memo="No direct evidence.")
        self.assertEqual(clean_failure["status"], "clean_failure")
        self.assertEqual(clean_failure["allowed_next_hop"], "phase_3")

        canonical_failure = readiness_from_auditor_action("clean_failure", memo="No direct evidence.")
        self.assertEqual(canonical_failure["status"], "clean_failure")
        self.assertEqual(canonical_failure["allowed_next_hop"], "phase_3")

    def test_delivery_freedom_mode_canonicalizes_clean_failure(self):
        self.assertEqual(
            nodes._normalize_delivery_freedom_mode("answer_not_ready"),
            "clean_failure",
        )
        self.assertEqual(
            nodes._normalize_delivery_freedom_mode("", reply_mode="cautious_minimal"),
            "clean_failure",
        )

    def test_make_auditor_decision_keeps_legacy_action_and_adds_readiness(self):
        decision = nodes._make_auditor_decision("warroom_deliberation", memo="Tool would not help.")

        self.assertEqual(decision["action"], "warroom_deliberation")
        self.assertEqual(decision["readiness_decision"]["status"], "needs_warroom")
        self.assertEqual(decision["readiness_decision"]["legacy_action"], "warroom_deliberation")

    def test_delivery_payload_maps_ready_modes(self):
        current_turn = readiness_from_delivery_payload(
            {
                "ready_for_delivery": True,
                "answer_mode": "current_turn_grounding",
                "fallback_action": "current_turn_grounding",
            }
        )
        self.assertEqual(current_turn["status"], "ready_with_current_turn_facts")

        field_gap = readiness_from_delivery_payload(
            {
                "ready_for_delivery": False,
                "source_lane": "field_memo_review",
                "fallback_action": "replan_or_search_more",
                "missing_slots": ["usable evidence"],
            }
        )
        self.assertEqual(field_gap["status"], "needs_memory_recall")
        self.assertEqual(field_gap["missing_evidence"], ["usable evidence"])

    def test_phase3_payload_and_contract_expose_readiness(self):
        state = empty_anima_state()
        state["user_input"] = "Explain OMORI."
        payload = nodes._build_phase3_delivery_payload(
            state,
            {},
            {
                "lane": "generic",
                "source_lane": "direct_dialogue",
                "output_act": "answer",
                "generic_delivery_packet": {
                    "final_answer_brief": "",
                    "answer_boundary": "generic_payload",
                },
            },
        )
        contract = nodes._build_phase3_speaker_judge_contract(state, payload)

        self.assertIn("readiness_decision", payload)
        self.assertIn("READINESS_DECISION", contract)
        self.assertEqual(contract["READINESS_DECISION"]["status"], "ready_for_direct_answer")

    def test_state_contract_contains_readiness_decision(self):
        state = empty_anima_state()
        self.assertIn("readiness_decision", state)
        self.assertEqual(state["readiness_decision"], {})


if __name__ == "__main__":
    unittest.main()
