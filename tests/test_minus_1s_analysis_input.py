import unittest

import Core.nodes as nodes


class _FakeStructuredResult:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, **_kwargs):
        return dict(self.payload)


class _FakeStartGateLLM:
    def __init__(self):
        self.messages = None

    def with_structured_output(self, _schema):
        return self

    def invoke(self, messages):
        self.messages = messages
        return _FakeStructuredResult(
            {
                "user_intent": "other",
                "normalized_goal": "Answer the current turn.",
                "answer_mode_preference": "generic_dialogue",
                "requires_grounding": False,
                "direct_delivery_allowed": False,
                "needs_planning": True,
                "current_turn_facts": [],
                "rationale": "test",
            }
        )


class Minus1sAnalysisInputTests(unittest.TestCase):
    def test_empty_analysis_report_omits_compact_block(self):
        fake = _FakeStartGateLLM()
        original = nodes.llm
        try:
            nodes.llm = fake
            nodes._llm_start_gate_turn_contract("hello", "", {}, {}, {}, analysis_report={})
        finally:
            nodes.llm = original

        human = fake.messages[1].content
        self.assertNotIn("[analysis_report_compact]", human)

    def test_nonempty_analysis_report_adds_compact_block(self):
        fake = _FakeStartGateLLM()
        original = nodes.llm
        try:
            nodes.llm = fake
            nodes._llm_start_gate_turn_contract(
                "hello",
                "",
                {},
                {},
                {},
                analysis_report={
                    "investigation_status": "COMPLETED",
                    "contract_status": "satisfied",
                    "can_answer_user_goal": True,
                    "missing_slots": [],
                    "situational_brief": "Evidence satisfies the answer boundary.",
                    "analytical_thought": "hidden bulk should not appear",
                    "evidences": [{"extracted_fact": "bulk fact should not appear in -1s status packet"}],
                },
            )
        finally:
            nodes.llm = original

        human = fake.messages[1].content
        self.assertIn("[analysis_report_compact]", human)
        self.assertIn('"investigation_status":"COMPLETED"', human)
        self.assertIn('"contract_status":"satisfied"', human)
        self.assertIn('"can_answer_user_goal":true', human)
        self.assertNotIn("hidden bulk", human)

    def test_analysis_report_argument_is_optional(self):
        fake = _FakeStartGateLLM()
        original = nodes.llm
        try:
            nodes.llm = fake
            result = nodes._llm_start_gate_turn_contract("hello", "", {}, {}, {})
        finally:
            nodes.llm = original

        self.assertEqual(result["schema"], "StartGateTurnContract.v1")
        self.assertNotIn("[analysis_report_compact]", fake.messages[1].content)


if __name__ == "__main__":
    unittest.main()
