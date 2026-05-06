import unittest

import Core.nodes as nodes
from Core.state import empty_anima_state


class FieldMemoDeliveryGateTests(unittest.TestCase):
    def test_field_memo_candidates_are_not_auto_accepted_without_2b_judgment(self):
        raw_read_report = {
            "read_mode": "field_memo_review",
            "items": [
                {
                    "source_id": "memo_creator",
                    "source_type": "field_memo",
                    "memo_kind": "verified_fact_packet",
                    "known_facts": "The user identified Heo Jeonghu as ANIMA's creator.",
                    "summary": "Creator identity memo.",
                    "observed_fact": "Heo Jeonghu created ANIMA.",
                }
            ],
        }

        result = nodes._enforce_field_memo_judgments(
            {"source_judgments": [], "field_memo_judgments": []},
            raw_read_report,
            "Who made ANIMA?",
        )

        self.assertFalse(result["can_answer_user_goal"])
        self.assertEqual(result["usable_field_memo_facts"], [])
        self.assertFalse(result["field_memo_judgments"][0]["usable_for_current_goal"])
        self.assertIn("phase_2b did not accept", result["field_memo_judgments"][0]["rejection_reason"])

    def test_field_memo_direct_2b_judgment_is_the_acceptance_authority(self):
        raw_read_report = {
            "read_mode": "field_memo_review",
            "items": [
                {
                    "source_id": "memo_creator",
                    "source_type": "field_memo",
                    "memo_kind": "verified_fact_packet",
                    "known_facts": "The user identified Heo Jeonghu as ANIMA's creator.",
                    "summary": "Creator identity memo.",
                    "observed_fact": "Heo Jeonghu created ANIMA.",
                }
            ],
        }

        result = nodes._enforce_field_memo_judgments(
            {
                "field_memo_judgments": [
                    {
                        "memo_id": "memo_creator",
                        "relevance": "direct",
                        "evidence_kind": "fact_packet",
                        "usable_for_current_goal": True,
                        "accepted_facts": ["The user identified Heo Jeonghu as ANIMA's creator."],
                        "rejected_facts": [],
                        "rejection_reason": "",
                        "recommended_followup_query": [],
                    }
                ]
            },
            raw_read_report,
            "Who made ANIMA?",
        )

        self.assertEqual(
            result["usable_field_memo_facts"],
            ["The user identified Heo Jeonghu as ANIMA's creator."],
        )
        self.assertTrue(result["field_memo_judgments"][0]["usable_for_current_goal"])

    def test_ready_gate_uses_usable_facts_without_answer_brief(self):
        packet = {
            "lane": "field_memo_review",
            "can_answer_user_goal": True,
            "contract_status": "satisfied",
            "missing_slots": [],
            "known_facts": ["The user identified Heo Jeonghu as ANIMA's creator."],
            "goal_contract": {},
        }
        analysis = {
            "can_answer_user_goal": True,
            "contract_status": "satisfied",
            "missing_slots": [],
            "usable_field_memo_facts": ["The user identified Heo Jeonghu as ANIMA's creator."],
        }

        self.assertTrue(nodes._field_memo_packet_ready_for_delivery(packet, analysis, "Who made ANIMA?"))

    def test_phase3_payload_forwards_facts_not_answer_seed(self):
        state = empty_anima_state()
        state["user_input"] = "Who made ANIMA?"
        state["raw_read_report"] = {"read_mode": "field_memo_review", "items": []}
        state["analysis_report"] = {
            "can_answer_user_goal": True,
            "contract_status": "satisfied",
            "missing_slots": [],
            "usable_field_memo_facts": ["The user identified Heo Jeonghu as ANIMA's creator."],
            "field_memo_judgments": [
                {
                    "memo_id": "memo_creator",
                    "usable_for_current_goal": True,
                    "accepted_facts": ["The user identified Heo Jeonghu as ANIMA's creator."],
                }
            ],
        }
        packet = {
            "lane": "field_memo_review",
            "contract_status": "satisfied",
            "missing_slots": [],
            "known_facts": ["The user identified Heo Jeonghu as ANIMA's creator."],
            "field_memo_recall_packet": {
                "known_facts": ["The user identified Heo Jeonghu as ANIMA's creator."],
            },
        }

        payload = nodes._build_phase3_delivery_payload(state, {}, packet)

        self.assertTrue(payload["ready_for_delivery"])
        self.assertEqual(payload["answer_seed"], "")
        self.assertIn("The user identified Heo Jeonghu as ANIMA's creator.", payload["accepted_facts"])


if __name__ == "__main__":
    unittest.main()
