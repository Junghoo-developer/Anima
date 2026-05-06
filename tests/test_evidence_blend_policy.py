import unittest

import Core.nodes as nodes


class EvidenceBlendPolicyTests(unittest.TestCase):
    def test_public_knowledge_turn_allows_parametric_blend(self):
        self.assertTrue(nodes._turn_allows_parametric_knowledge_blend("오모리에 대해서 알려줘"))
        self.assertFalse(nodes._turn_requires_grounded_delivery("오모리에 대해서 알려줘"))

    def test_current_turn_teaching_facts_support_relationship_goal(self):
        contract = nodes._derive_user_goal_contract(
            "써니와 오모리와의 상관관계를 유추해봐",
            source_lane="direct_dialogue",
        )
        facts = nodes._extract_current_turn_grounding_facts(
            "오모리는 게임의 이름이자 써니의 다른 자아야. 오모리는 써니를 죄책감으로부터 보호하기 위한 또다른 인격이라고 할 수 있어.",
            contract,
        )

        self.assertTrue(facts)
        self.assertTrue(nodes._contract_satisfied_by_facts(contract, facts, ""))

    def test_strategy_supports_direct_phase3_for_public_knowledge_without_seed(self):
        self.assertTrue(
            nodes._strategy_supports_direct_phase3(
                {},
                "오모리에 대해서 알려줘",
                "",
            )
        )

    def test_phase3_payload_marks_public_knowledge_as_ready(self):
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

        self.assertTrue(payload["parametric_knowledge_allowed"])
        self.assertTrue(payload["ready_for_delivery"])
        self.assertEqual(payload["fallback_action"], "public_knowledge_answer")

    def test_phase3_payload_promotes_current_turn_user_facts(self):
        state = {
            "user_input": (
                "오모리는 게임의 이름이자 써니의 다른 자아야. "
                "오모리는 써니를 죄책감으로부터 보호하기 위한 써니의 또다른 인격이라고 할 수 있어."
            ),
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

        self.assertTrue(payload["current_turn_facts"])
        self.assertTrue(payload["ready_for_delivery"])
        self.assertEqual(payload["fallback_action"], "current_turn_grounding")


if __name__ == "__main__":
    unittest.main()
