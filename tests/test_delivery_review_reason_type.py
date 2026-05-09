import unittest

from Core.pipeline.contracts import DeliveryReview
from Core.pipeline.delivery_review import normalize_delivery_review


class DeliveryReviewReasonTypeTests(unittest.TestCase):
    def test_delivery_review_schema_has_new_default_fields(self):
        review = DeliveryReview().model_dump(by_alias=True)

        self.assertEqual(review["reason_type"], "")
        self.assertEqual(review["evidence_refs"], [])
        self.assertEqual(review["delta"], "")

    def test_normalize_delivery_review_rejects_invalid_reason_type(self):
        review = normalize_delivery_review({"verdict": "remand", "reason_type": "made_up", "remand_target": "-1a"})

        self.assertEqual(review["reason_type"], "")
        self.assertEqual(review["remand_target"], "-1a")

    def test_hallucination_reason_type_routes_to_minus_1s(self):
        review = normalize_delivery_review({"verdict": "remand", "reason_type": "hallucination", "remand_target": ""})

        self.assertEqual(review["remand_target"], "-1s")

    def test_tool_misuse_reason_type_routes_to_minus_1a(self):
        review = normalize_delivery_review({"verdict": "remand", "reason_type": "tool_misuse", "remand_target": ""})

        self.assertEqual(review["remand_target"], "-1a")

    def test_empty_reason_type_preserves_legacy_remand_target(self):
        review = normalize_delivery_review({"verdict": "remand", "reason_type": "", "remand_target": "-1a"})

        self.assertEqual(review["remand_target"], "-1a")

    def test_evidence_refs_are_string_only_deduped_and_trimmed(self):
        review = normalize_delivery_review(
            {
                "verdict": "remand",
                "reason_type": "omission",
                "evidence_refs": [
                    "fact_1",
                    "fact_1",
                    7,
                    {"bad": "ref"},
                    "fact_2",
                    "fact_3",
                    "fact_4",
                    "fact_5",
                    "fact_6",
                    "fact_7",
                    "fact_8",
                    "fact_9",
                ],
                "delta": "x" * 400,
            }
        )

        self.assertEqual(review["evidence_refs"], [f"fact_{idx}" for idx in range(1, 9)])
        self.assertLessEqual(len(review["delta"]), 280)
        self.assertEqual(review["remand_target"], "-1s")


if __name__ == "__main__":
    unittest.main()
