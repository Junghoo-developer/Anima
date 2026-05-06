import unittest

import Core.nodes as nodes
from Core.state import empty_anima_state


class PublicKnowledgeContractTests(unittest.TestCase):
    def test_public_knowledge_payload_sets_answer_mode(self):
        state = {
            "user_input": "오모리에 대해서 알려줘",
            "recent_context": "",
            "analysis_report": {},
            "raw_read_report": {},
            "strategist_output": {},
        }
        payload = nodes._build_phase3_delivery_payload(
            state,
            {},
            {
                "lane": "generic",
                "source_lane": "direct_dialogue",
                "output_act": "answer_narrative_fact",
                "generic_delivery_packet": {
                    "final_answer_brief": "",
                    "answer_boundary": "generic_judge_packet",
                },
            },
        )

        self.assertTrue(payload["ready_for_delivery"])
        self.assertTrue(payload["parametric_knowledge_allowed"])
        self.assertEqual(payload["answer_mode"], "public_parametric_knowledge")
        self.assertEqual(payload["fallback_action"], "public_knowledge_answer")

    def test_public_knowledge_contract_creates_answer_mandate(self):
        state = empty_anima_state()
        state["user_input"] = "오모리에 대해서 알려줘"
        contract = nodes._build_phase3_speaker_judge_contract(
            state,
            {
                "ready_for_delivery": True,
                "answer_mode": "public_parametric_knowledge",
                "parametric_knowledge_allowed": True,
                "answer_seed": "",
                "accepted_facts": [],
                "current_turn_facts": [],
                "clean_failure_packet": {},
                "forbidden_claims": [],
                "missing_slots": [],
                "user_goal": "오모리에 대해서 알려줘",
                "output_act": "answer_narrative_fact",
                "fallback_action": "public_knowledge_answer",
                "answer_boundary": "public_parametric_knowledge + loop evidence blend",
            },
        )

        self.assertTrue(contract["READY"])
        self.assertEqual(contract["ANSWER_MODE"], "public_parametric_knowledge")
        self.assertTrue(contract["PARAMETRIC_ANSWER_MANDATE"])
        self.assertEqual(contract["SAY_THIS"], "")
        self.assertIn("PUBLIC_KNOWLEDGE_SAFETY_POLICY", contract)
        self.assertIn("highly confident are canonical", contract["PUBLIC_KNOWLEDGE_SAFETY_POLICY"]["named_entity_rule"])
        self.assertIn("untrusted", contract["PUBLIC_KNOWLEDGE_SAFETY_POLICY"]["challenge_rule"])
        self.assertIn(
            "For public-knowledge turns, do not collapse into generic retrieval failure unless a private-memory search was actually required.",
            contract["DO_NOT_SAY"],
        )

if __name__ == "__main__":
    unittest.main()
