import unittest

import Core.nodes as nodes


class _FakeStructuredResult:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self):
        return dict(self._payload)


class _FakePlannerLLM:
    def __init__(self, payload):
        self._payload = payload

    def with_structured_output(self, _schema):
        return self

    def invoke(self, _messages):
        return _FakeStructuredResult(self._payload)


class LlmFirstSimplificationTests(unittest.TestCase):
    def test_recent_context_anchor_query_ignores_active_offer_noise(self):
        query = nodes._recent_context_anchor_query(
            "",
            {
                "dialogue_state": {
                    "active_offer": "좋아, 방금 흐름 그대로 이어가자.",
                    "active_task": "Continue the immediately preceding thread.",
                    "current_topic": "",
                    "last_user_goal": "",
                }
            },
        )

        self.assertEqual(query, "")

    def test_fresh_information_request_is_not_followup_acceptance(self):
        working_memory = {
            "dialogue_state": {
                "active_offer": "좋아, 방금 흐름 그대로 이어가자.",
            }
        }

        self.assertFalse(
            nodes._is_followup_offer_acceptance_turn(
                "오모리라는 게임을 설명해줘",
                working_memory,
            )
        )

    def test_short_explicit_continue_still_counts_as_followup_acceptance(self):
        working_memory = {
            "dialogue_state": {
                "active_offer": "좋아, 방금 흐름 그대로 이어가자.",
            }
        }

        self.assertTrue(nodes._is_followup_offer_acceptance_turn("go on", working_memory))

    def test_short_ack_does_not_accept_last_assistant_answer_as_offer(self):
        working_memory = {
            "dialogue_state": {},
            "last_turn": {
                "assistant_answer": "My name is SongRyeon.",
            },
        }

        self.assertFalse(nodes._is_followup_offer_acceptance_turn("yes", working_memory))

    def test_pending_dialogue_act_can_accept_short_reply(self):
        working_memory = {
            "dialogue_state": {
                "pending_dialogue_act": {
                    "kind": "playful_action",
                    "target": "perform the playful blub-blub action",
                    "expected_user_responses": ["yes", "do it"],
                    "expires_after_turns": 1,
                    "confidence": 0.9,
                },
            },
        }

        self.assertTrue(nodes._is_followup_offer_acceptance_turn("yes", working_memory))

        strategy = nodes._offer_acceptance_strategy("yes", working_memory)

        self.assertIn("perform the playful blub-blub action", " ".join(strategy["must_include_facts"]))

    def test_tool_planner_prefers_structured_llm_over_deterministic_recall(self):
        original_llm = nodes.llm
        try:
            nodes.llm = _FakePlannerLLM(
                {
                    "should_call_tool": True,
                    "tool_name": "tool_search_field_memos",
                    "tool_args": {"query": "써니 오모리", "limit": 8},
                    "rationale": "Use the compact entity query first.",
                }
            )

            candidate = nodes._strategist_tool_request_from_context(
                "그럼 써니는 누구인지 기억나?",
                {},
                {"dialogue_state": {"active_offer": "좋아, 방금 흐름 그대로 이어가자."}},
                recent_context="assistant: 좋아, 방금 흐름 그대로 이어가자.",
                tool_carryover={},
            )
        finally:
            nodes.llm = original_llm

        self.assertEqual(candidate["tool_name"], "tool_search_field_memos")
        self.assertEqual(candidate["tool_args"]["query"], "써니 오모리")

    def test_public_question_does_not_compile_memory_recall_query(self):
        queries = nodes._compiled_memory_recall_queries(
            "Who is Sunny in OMORI?",
            recent_context="assistant: 좋아, 방금 흐름 그대로 이어가자.\nuser: Who is Sunny in OMORI?",
            working_memory={
                "dialogue_state": {
                    "active_offer": "좋아, 방금 흐름 그대로 이어가자.",
                    "active_task": "Continue the immediately preceding thread.",
                    "current_topic": "",
                    "last_user_goal": "",
                }
            },
            tool_carryover={"origin_query": "continue previous offer", "last_query": "go on"},
        )

        self.assertEqual(queries, [])

    def test_memory_reset_disclosure_does_not_compile_tool_query(self):
        text = "안녕 살짝 미안하지만 네 이전의 기억을 전부 소거하고 왔어"

        self.assertEqual(nodes._compiled_memory_recall_queries(text), [])
        self.assertTrue(nodes._search_query_is_overbroad_or_instruction(text))
        self.assertIsNone(
            nodes._strategist_tool_request_from_context(
                text,
                {},
                {},
                recent_context="",
                tool_carryover={},
            )
        )

    def test_deterministic_strategist_fallback_only_handles_explicit_search(self):
        self.assertIsNone(
            nodes._deterministic_strategist_tool_request_from_context(
                "Who is Sunny in OMORI?",
                {"dialogue_state": {}},
                tool_carryover={},
            )
        )

        candidate = nodes._deterministic_strategist_tool_request_from_context(
            "search OMORI",
            {"dialogue_state": {}},
            tool_carryover={},
        )

        self.assertEqual(candidate["tool_name"], "tool_search_memory")
        self.assertEqual(candidate["tool_args"]["keyword"], "OMORI")


if __name__ == "__main__":
    unittest.main()
