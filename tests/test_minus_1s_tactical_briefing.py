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
        return _FakeStructuredResult({
            "user_intent": "other",
            "normalized_goal": "Answer the current turn.",
            "answer_mode_preference": "generic_dialogue",
            "requires_grounding": False,
            "direct_delivery_allowed": False,
            "needs_planning": True,
            "current_turn_facts": [],
            "rationale": "test",
        })


class Minus1sTacticalBriefingTests(unittest.TestCase):
    def test_empty_tactical_briefing_omits_block(self):
        fake = _FakeStartGateLLM()
        original = nodes.llm
        try:
            nodes.llm = fake
            nodes._llm_start_gate_turn_contract("hello", "", {}, {}, {}, tactical_briefing="")
        finally:
            nodes.llm = original

        self.assertNotIn("[tactical_briefing]", fake.messages[1].content)

    def test_nonempty_tactical_briefing_is_included_for_minus_1s(self):
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
                tactical_briefing="DreamHint: prefer a warm memory boundary.",
            )
        finally:
            nodes.llm = original

        self.assertIn("[tactical_briefing]", fake.messages[1].content)
        self.assertIn("DreamHint", fake.messages[1].content)
        self.assertIn("advisory context only", fake.messages[0].content)

    def test_tactical_briefing_argument_is_optional(self):
        fake = _FakeStartGateLLM()
        original = nodes.llm
        try:
            nodes.llm = fake
            result = nodes._llm_start_gate_turn_contract("hello", "", {}, {}, {})
        finally:
            nodes.llm = original

        self.assertEqual(result["schema"], "StartGateTurnContract.v1")
        self.assertNotIn("[tactical_briefing]", fake.messages[1].content)


if __name__ == "__main__":
    unittest.main()
