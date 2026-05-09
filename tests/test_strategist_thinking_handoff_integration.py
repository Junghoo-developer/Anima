import unittest

import Core.nodes as nodes
from Core.state import empty_anima_state


class _FakeStructuredResult:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, **_kwargs):
        return dict(self.payload)


class _FakeStrategistLLM:
    def __init__(self, payload=None):
        self.payload = payload or {}
        self.messages = None
        self.invoked = False

    def with_structured_output(self, _schema):
        return self

    def invoke(self, messages):
        self.invoked = True
        self.messages = messages
        return _FakeStructuredResult(self.payload)


def _strategist_payload():
    return {
        "case_theory": "Use the handoff fact.",
        "strategist_goal": {
            "user_goal_core": "Answer from fact f1.",
            "answer_mode_target": "memory_recall",
            "success_criteria": ["cite f1"],
            "scope": "narrow",
        },
        "operation_plan": {
            "plan_type": "direct_delivery",
            "source_lane": "none",
            "output_act": "answer_narrative_fact",
            "user_goal": "Answer from fact f1.",
        },
        "goal_lock": {
            "user_goal_core": "Answer from fact f1.",
            "answer_shape": "fact_brief",
            "must_not_expand_to": [],
        },
        "convergence_state": "deliverable",
        "achieved_findings": ["Sunny is the protagonist."],
        "delivery_readiness": "deliver_now",
        "next_frontier": [],
        "action_plan": {
            "current_step_goal": "Use fact f1 directly.",
            "required_tool": "",
            "next_steps_forecast": [],
        },
        "response_strategy": {
            "reply_mode": "grounded_answer",
            "answer_goal": "Answer from f1.",
            "tone_strategy": "short",
            "evidence_brief": "f1",
            "reasoning_brief": "fact id known",
            "direct_answer_seed": "",
            "must_include_facts": ["f1: Sunny is the protagonist."],
            "must_avoid_claims": [],
            "answer_outline": [],
            "uncertainty_policy": "",
        },
        "war_room_contract": {},
        "candidate_pairs": [
            {
                "pair_id": "pair_1",
                "fact_ids": ["f1"],
                "paired_fact_digest": "Sunny fact",
                "subjective": {
                    "claim_text": "f1 can answer the user.",
                    "claim_kind": "interpretation",
                    "confidence": 0.8,
                    "answer_policy": "allowed",
                },
            }
        ],
    }


def _state_with_handoff_fact():
    state = empty_anima_state()
    state["user_input"] = "Who is Sunny?"
    state["s_thinking_packet"] = {
        "schema": "ThinkingHandoff.v1",
        "producer": "-1s",
        "recipient": "-1a",
        "goal_state": "Answer from known fact.",
        "evidence_state": "one fact available",
        "what_we_know": ["Sunny is the protagonist."],
        "what_is_missing": [],
        "next_node": "-1a",
        "next_node_reason": "Plan a direct answer.",
        "constraints_for_next_node": ["cite fact ids"],
    }
    state["reasoning_board"] = {
        "fact_cells": [
            {
                "fact_id": "f1",
                "extracted_fact": "Sunny is the protagonist.",
                "source_id": "source_1",
                "source_type": "memory_node",
                "excerpt": "Sunny is the protagonist.",
            }
        ],
    }
    state["start_gate_switches"] = {
        "answer_mode_policy": {
            "question_class": "requesting_memory_recall",
            "preferred_answer_mode": "grounded_answer",
            "grounded_delivery_required": True,
        }
    }
    return state


class StrategistThinkingHandoffIntegrationTests(unittest.TestCase):
    def test_strategist_uses_handoff_and_fact_cells_prompt_surface(self):
        fake = _FakeStrategistLLM(_strategist_payload())
        original = nodes.llm
        try:
            nodes.llm = fake
            result = nodes._base_phase_minus_1a_thinker(_state_with_handoff_fact())
        finally:
            nodes.llm = original

        prompt = fake.messages[0].content
        self.assertIn("[s_thinking_packet]", prompt)
        self.assertIn("[fact_cells]", prompt)
        self.assertIn('"fact_id": "f1"', prompt)
        self.assertNotIn("[analysis_report]", prompt)
        self.assertEqual(result["strategist_output"]["action_plan"]["current_step_goal"], "Use fact f1 directly.")
        self.assertIn("f1: Sunny is the protagonist.", result["strategist_output"]["response_strategy"]["must_include_facts"])

    def test_empty_handoff_and_empty_fact_cells_take_fallback_without_llm(self):
        fake = _FakeStrategistLLM(_strategist_payload())
        state = empty_anima_state()
        state["user_input"] = "Acknowledge this."
        state["s_thinking_packet"] = {
            "schema": "ThinkingHandoff.v1",
            "what_we_know": [],
            "what_is_missing": ["No direct source yet."],
            "next_node": "-1a",
        }
        state["start_gate_switches"] = {
            "answer_mode_policy": {
                "question_class": "providing_current_memory",
                "preferred_answer_mode": "current_turn_grounding",
                "grounded_delivery_required": False,
                "direct_delivery_allowed": True,
            },
            "current_turn_facts": [],
        }
        original = nodes.llm
        try:
            nodes.llm = fake
            result = nodes._base_phase_minus_1a_thinker(state)
        finally:
            nodes.llm = original

        self.assertFalse(fake.invoked)
        self.assertEqual(result["strategist_output"]["delivery_readiness"], "deliver_now")

    def test_strategist_output_still_updates_reasoning_board_after_planning(self):
        fake = _FakeStrategistLLM(_strategist_payload())
        original = nodes.llm
        try:
            nodes.llm = fake
            result = nodes._base_phase_minus_1a_thinker(_state_with_handoff_fact())
        finally:
            nodes.llm = original

        board = result["reasoning_board"]
        self.assertEqual(board["candidate_pairs"][0]["fact_ids"], ["f1"])
        self.assertEqual(board["strategist_plan"]["action_plan"]["current_step_goal"], "Use fact f1 directly.")


if __name__ == "__main__":
    unittest.main()
