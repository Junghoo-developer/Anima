import unittest

from Core.pipeline.delivery_review import build_delivery_review_context
from Core.pipeline.packets import _compact_fact_cells_for_prompt


class DeliveryReviewFactCellsTests(unittest.TestCase):
    def test_delivery_review_context_includes_compact_fact_cells(self):
        state = {
            "reasoning_board": {
                "fact_cells": [
                    {
                        "fact_id": f"fact_{idx}",
                        "source_id": f"source_{idx}",
                        "source_type": "diary",
                        "excerpt": "excerpt text",
                        "extracted_fact": f"verified fact {idx}",
                        "confidence": 0.9,
                    }
                    for idx in range(12)
                ]
            }
        }

        context = build_delivery_review_context(state, final_answer="answer")

        self.assertIn("fact_cells_for_review", context)
        self.assertEqual(len(context["fact_cells_for_review"]), 10)
        self.assertEqual(context["fact_cells_for_review"][0]["extracted_fact"], "verified fact 0")
        self.assertIn("excerpt", context["fact_cells_for_review"][0])

    def test_compact_fact_cells_prefers_extracted_fact(self):
        compact = _compact_fact_cells_for_prompt(
            [
                {
                    "fact_id": "fact_1",
                    "extracted_fact": "the real extracted fact",
                    "claim": "legacy claim should lose",
                    "source_id": "source_1",
                    "source_type": "diary",
                    "excerpt": "literal excerpt",
                }
            ]
        )

        self.assertEqual(compact[0]["extracted_fact"], "the real extracted fact")
        self.assertEqual(compact[0]["source_type"], "diary")
        self.assertEqual(compact[0]["excerpt"], "literal excerpt")
        self.assertNotIn("claim", compact[0])
        self.assertNotIn("status", compact[0])

    def test_compact_fact_cells_accepts_legacy_claim_fallback(self):
        compact = _compact_fact_cells_for_prompt(
            [{"fact_id": "legacy_1", "claim": "legacy fact text", "source_id": "old"}]
        )

        self.assertEqual(compact[0]["extracted_fact"], "legacy fact text")
        self.assertEqual(compact[0]["source_id"], "old")

    def test_delivery_review_context_empty_fact_cells_for_empty_board(self):
        context = build_delivery_review_context({"reasoning_board": {}}, final_answer="answer")

        self.assertEqual(context["fact_cells_for_review"], [])


if __name__ == "__main__":
    unittest.main()
