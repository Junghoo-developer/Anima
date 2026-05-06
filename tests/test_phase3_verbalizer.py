import unittest

import Core.nodes as nodes
from Core.state import empty_anima_state


class Phase3VerbalizerTests(unittest.TestCase):
    def test_speaker_contract_keeps_internal_seed_out_of_say_this(self):
        state = empty_anima_state()
        state["user_input"] = "Tell me about OMORI again."
        payload = {
            "lane": "field_memo_review",
            "ready_for_delivery": True,
            "answer_seed": "FieldMemo filter says this is directly about Sunny and Mari.",
            "accepted_facts": [
                "Sunny is one of the central OMORI characters.",
                "Mari is Sunny's older sister.",
            ],
            "clean_failure_packet": {},
            "forbidden_claims": [],
            "missing_slots": [],
            "user_goal": "Talk about OMORI again.",
            "output_act": "answer_narrative_fact",
            "fallback_action": "direct_dialogue_or_replan",
            "answer_boundary": "field_memo_filtered_only",
        }

        contract = nodes._build_phase3_speaker_judge_contract(state, payload)

        self.assertEqual(contract["SAY_THIS"], "")
        self.assertEqual(
            contract["FACTS_ALLOWED"],
            [
                "Sunny is one of the central OMORI characters.",
                "Mari is Sunny's older sister.",
            ],
        )

    def test_speaker_contract_exposes_short_term_context_policy(self):
        state = empty_anima_state()
        state["user_input"] = "yes"
        state["working_memory"] = {
            "dialogue_state": {
                "pending_dialogue_act": {
                    "kind": "playful_action",
                    "target": "perform the playful blub-blub action",
                    "expected_user_responses": ["yes"],
                    "confidence": 0.9,
                }
            },
            "memory_writer": {
                "short_term_context": "The assistant offered a playful blub-blub action.",
                "assistant_obligation_next_turn": "perform the playful blub-blub action directly",
            },
        }
        payload = {
            "ready_for_delivery": True,
            "answer_mode": "generic_dialogue",
            "answer_seed": "",
            "accepted_facts": [],
            "current_turn_facts": [],
            "clean_failure_packet": {},
            "forbidden_claims": [],
            "missing_slots": [],
            "user_goal": "Continue the playful action.",
            "output_act": "answer",
        }

        contract = nodes._build_phase3_speaker_judge_contract(state, payload)

        self.assertEqual(
            contract["SHORT_TERM_CONTEXT"]["assistant_obligation_next_turn"],
            "perform the playful blub-blub action directly",
        )
        self.assertIn("assistant_obligation_next_turn", contract["SHORT_TERM_CONTEXT_POLICY"]["priority"])

    def test_continue_previous_offer_without_material_is_remanded(self):
        review = nodes._build_speaker_review(
            {
                "reply_mode": "continue_previous_offer",
                "delivery_freedom_mode": "proposal",
                "delivery_packet": {
                    "reply_mode": "continue_previous_offer",
                    "delivery_freedom_mode": "proposal",
                    "final_answer_brief": "",
                    "approved_fact_cells": [],
                    "approved_claims": [],
                    "followup_instruction": "",
                    "raw_reference_excerpt": "",
                },
            },
            user_input="Tell me about OMORI again.",
            recent_context_excerpt="assistant: Sure, we can continue.",
        )

        self.assertFalse(review["delivery_ok"])
        self.assertEqual(review["suggested_action"], "strengthen_response_strategy")


if __name__ == "__main__":
    unittest.main()
