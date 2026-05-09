import unittest

from langchain_core.messages import AIMessage

from Core.pipeline.delivery_review import run_phase3_delivery_review
from Core.state import empty_anima_state


class _FakeStructuredResult:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, **_kwargs):
        return dict(self.payload)


class _FakeReviewLLM:
    def __init__(self, payload):
        self.payload = payload

    def with_structured_output(self, _schema):
        return self

    def invoke(self, _messages):
        return _FakeStructuredResult(self.payload)


def _attach(result, *_args, **_kwargs):
    return result


class DeliveryReviewHallucinationFlowTests(unittest.TestCase):
    def test_hallucination_reason_type_remands_to_minus_1s(self):
        state = empty_anima_state()
        state["messages"] = [AIMessage(content="The diary says the user moved to Mars.")]
        state["speaker_review"] = {"delivery_ok": True, "should_remand": False, "issues": []}
        state["delivery_status"] = "delivered"
        state["reasoning_board"] = {
            "fact_cells": [
                {
                    "fact_id": "fact_1",
                    "source_id": "diary::1",
                    "source_type": "Diary",
                    "excerpt": "The user studied linear algebra.",
                    "extracted_fact": "The user studied linear algebra.",
                }
            ]
        }

        result = run_phase3_delivery_review(
            state,
            llm=_FakeReviewLLM(
                {
                    "verdict": "remand",
                    "reason": "Unsupported claim.",
                    "reason_type": "hallucination",
                    "evidence_refs": [],
                    "delta": "Re-evaluate the answer against the known fact cells.",
                    "issues_found": ["unsupported Mars claim"],
                    "remand_target": "",
                    "remand_guidance": "",
                }
            ),
            attach_ledger_event=_attach,
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result["delivery_review"]["verdict"], "remand")
        self.assertEqual(result["delivery_review"]["reason_type"], "hallucination")
        self.assertEqual(result["delivery_review"]["remand_target"], "-1s")
        self.assertEqual(result["loop_count"], 1)

    def test_approved_review_resets_rejection_counter(self):
        state = empty_anima_state()
        state["messages"] = [AIMessage(content="The user studied linear algebra.")]
        state["speaker_review"] = {"delivery_ok": True, "should_remand": False, "issues": []}
        state["delivery_status"] = "delivered"
        state["delivery_review_rejections"] = 2
        state["reasoning_board"] = {
            "fact_cells": [
                {
                    "fact_id": "fact_1",
                    "source_id": "diary::1",
                    "source_type": "Diary",
                    "excerpt": "The user studied linear algebra.",
                    "extracted_fact": "The user studied linear algebra.",
                }
            ]
        }

        result = run_phase3_delivery_review(
            state,
            llm=_FakeReviewLLM(
                {
                    "verdict": "approve",
                    "reason": "Supported by fact_1.",
                    "reason_type": "",
                    "evidence_refs": ["fact_1"],
                    "delta": "",
                    "issues_found": [],
                    "remand_target": "",
                    "remand_guidance": "",
                }
            ),
            attach_ledger_event=_attach,
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result["delivery_review"]["verdict"], "approve")
        self.assertEqual(result["delivery_review"]["remand_target"], "")
        self.assertEqual(result["delivery_review_rejections"], 0)


if __name__ == "__main__":
    unittest.main()
