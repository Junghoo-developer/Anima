import unittest

import Core.nodes as nodes
from Core.pipeline.rescue import RESCUE_USER_FACING_LABELS
from Core.state import empty_anima_state


class RescueHandoffPacketTests(unittest.TestCase):
    def test_phase119_preserves_verified_partial_facts(self):
        state = empty_anima_state()
        state["user_input"] = "내 기억에서 이거 확인해줘"
        state["raw_read_report"] = {
            "read_mode": "full_raw_review",
            "source_summary": "diary and memo candidates were read",
            "items": [{"source_id": "good_diary", "source_type": "diary", "observed_fact": "source was read"}],
        }
        state["analysis_report"] = {
            "investigation_status": "INCOMPLETE",
            "can_answer_user_goal": False,
            "contract_status": "missing_slot",
            "missing_slots": ["the specific remembered event"],
            "evidences": [
                {
                    "source_id": "good_diary",
                    "source_type": "diary",
                    "extracted_fact": "The user is interested in agent development.",
                },
                {
                    "source_id": "bad_memo",
                    "source_type": "field_memo",
                    "extracted_fact": "Rejected memo claim should not survive.",
                },
            ],
            "source_judgments": [
                {
                    "source_id": "partial_chat",
                    "source_type": "gemini_chat",
                    "source_status": "insufficient",
                    "accepted_facts": ["The user mentioned studying linear algebra."],
                    "contested_facts": [],
                    "objection_reason": "does not answer the whole current goal",
                    "missing_info": ["specific remembered event"],
                    "search_needed": False,
                }
            ],
            "field_memo_judgments": [
                {
                    "memo_id": "good_memo",
                    "usable_for_current_goal": True,
                    "accepted_facts": ["SongRyeon is the assistant name."],
                },
                {
                    "memo_id": "bad_memo",
                    "usable_for_current_goal": False,
                    "accepted_facts": [],
                    "rejection_reason": "wrong goal",
                },
            ],
            "usable_field_memo_facts": ["The user identified Heo Jeonghu as ANIMA's creator."],
            "rejected_sources": [{"source_id": "bad_memo", "source_type": "field_memo", "reason": "wrong goal"}],
        }

        result = nodes.phase_119_rescue(state)
        handoff = result["rescue_handoff_packet"]
        analysis = result["analysis_report"]

        preserved_text = " ".join(item["extracted_fact"] for item in handoff["preserved_evidences"])
        self.assertIn("agent development", preserved_text)
        self.assertIn("linear algebra", preserved_text)
        self.assertNotIn("Rejected memo claim", preserved_text)
        self.assertIn("The user identified Heo Jeonghu as ANIMA's creator.", handoff["preserved_field_memo_facts"])
        self.assertIn("SongRyeon is the assistant name.", handoff["preserved_field_memo_facts"])
        self.assertEqual(analysis["evidences"], handoff["preserved_evidences"])
        self.assertEqual(analysis["usable_field_memo_facts"], handoff["preserved_field_memo_facts"])
        self.assertEqual(analysis["rejected_only"], handoff["rejected_only"])
        self.assertIn(handoff["user_facing_label"], RESCUE_USER_FACING_LABELS)
        self.assertEqual(handoff["user_facing_label"], "기억 못 찾음")
        self.assertNotIn(
            result["response_strategy"]["direct_answer_seed"],
            result["response_strategy"]["must_include_facts"],
        )

    def test_phase3_contract_receives_rescue_handoff_without_internal_trigger(self):
        state = empty_anima_state()
        state["user_input"] = "그래서 뭐는 확실해?"
        handoff = {
            "schema": "RescueHandoffPacket.v1",
            "trigger": "budget_exceeded",
            "attempted_path": ["internal path"],
            "preserved_evidences": [
                {
                    "source_id": "diary-1",
                    "source_type": "diary",
                    "extracted_fact": "The user is interested in agent development.",
                }
            ],
            "preserved_field_memo_facts": ["SongRyeon is the assistant name."],
            "rejected_only": [{"source_id": "bad", "reason": "wrong goal"}],
            "what_we_know": [
                "The user is interested in agent development.",
                "SongRyeon is the assistant name.",
            ],
            "what_we_failed": ["the exact remembered event"],
            "speaker_tone_hint": "사과 + 부분정보",
            "user_facing_label": "재시도 필요",
        }
        state["rescue_handoff_packet"] = handoff

        contract = nodes._build_phase3_speaker_judge_contract(
            state,
            {
                "ready_for_delivery": False,
                "answer_mode": "clean_failure",
                "accepted_facts": [],
                "current_turn_facts": [],
                "clean_failure_packet": {
                    "message_seed": "확인된 부분만 말하고, 부족한 부분은 단정하지 않기",
                    "missing_slots": ["the exact remembered event"],
                },
                "rescue_handoff_packet": handoff,
                "forbidden_claims": [],
                "missing_slots": ["the exact remembered event"],
                "user_goal": "state what is certain",
                "output_act": "answer",
            },
        )

        self.assertIn("The user is interested in agent development.", contract["FACTS_ALLOWED"])
        self.assertIn("SongRyeon is the assistant name.", contract["FACTS_ALLOWED"])
        self.assertEqual(
            contract["RESCUE_HANDOFF"]["what_we_know"],
            [
                "The user is interested in agent development.",
                "SongRyeon is the assistant name.",
            ],
        )
        self.assertEqual(
            contract["RESCUE_HANDOFF"]["label_policy"],
            "user_facing_label is a coarse enum; transform it into natural Korean instead of quoting it.",
        )
        self.assertIn(contract["RESCUE_HANDOFF"]["user_facing_label"], RESCUE_USER_FACING_LABELS)
        self.assertNotIn("trigger", contract["RESCUE_HANDOFF"])
        self.assertNotIn("budget_exceeded", str(contract["IF_NOT_READY"]))


if __name__ == "__main__":
    unittest.main()
