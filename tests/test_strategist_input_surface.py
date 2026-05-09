import unittest

from Core.pipeline.strategy import project_state_for_strategist


def _fact_cell(idx: int, *, claim_only: bool = False):
    cell = {
        "fact_id": f"fact_{idx}",
        "source_id": f"source_{idx}",
        "source_type": "memory_node",
        "excerpt": f"excerpt {idx}",
    }
    if claim_only:
        cell["claim"] = f"legacy claim {idx}"
    else:
        cell["extracted_fact"] = f"verified fact {idx}"
    return cell


class StrategistInputSurfaceTests(unittest.TestCase):
    def test_projection_removes_judge_and_advisory_surfaces(self):
        projected = project_state_for_strategist({
            "analysis_report": {"investigation_status": "COMPLETED"},
            "raw_read_report": {"items": [{"excerpt": "raw"}]},
            "reasoning_board": {"fact_cells": [_fact_cell(0)]},
            "tactical_briefing": "DreamHint advisory",
        })

        self.assertNotIn("analysis_report", projected)
        self.assertNotIn("raw_read_report", projected)
        self.assertNotIn("reasoning_board", projected)
        self.assertNotIn("tactical_briefing", projected)

    def test_projection_exposes_v4_fact_cells_for_strategist(self):
        projected = project_state_for_strategist({
            "reasoning_board": {"fact_cells": [_fact_cell(0)]},
        })

        self.assertIn("fact_cells_for_strategist", projected)
        self.assertEqual(
            set(projected["fact_cells_for_strategist"][0].keys()),
            {"fact_id", "extracted_fact", "source_id", "source_type", "excerpt"},
        )
        self.assertEqual(projected["fact_cells_for_strategist"][0]["extracted_fact"], "verified fact 0")

    def test_empty_reasoning_board_projects_empty_fact_cells(self):
        projected = project_state_for_strategist({"reasoning_board": {}})

        self.assertEqual(projected["fact_cells_for_strategist"], [])

    def test_fact_cells_for_strategist_are_limited_to_ten(self):
        projected = project_state_for_strategist({
            "reasoning_board": {"fact_cells": [_fact_cell(idx) for idx in range(11)]},
        })

        self.assertEqual(len(projected["fact_cells_for_strategist"]), 10)

    def test_s_thinking_handoff_is_projected_for_strategist(self):
        projected = project_state_for_strategist({
            "s_thinking_packet": {
                "schema": "ThinkingHandoff.v1",
                "producer": "-1s",
                "recipient": "-1a",
                "goal_state": "Answer a memory question.",
                "evidence_state": "missing evidence",
                "what_we_know": ["The user asked for a source check."],
                "what_is_missing": ["direct source"],
                "next_node": "-1a",
                "next_node_reason": "needs a plan",
                "constraints_for_next_node": ["use one tool at most"],
            },
        })

        packet = projected["s_thinking_packet"]
        self.assertEqual(packet["schema"], "ThinkingHandoff.v1")
        self.assertEqual(packet["next_node"], "-1a")
        self.assertEqual(packet["what_we_know"], ["The user asked for a source check."])

    def test_legacy_claim_fact_cell_falls_back_to_extracted_fact(self):
        projected = project_state_for_strategist({
            "reasoning_board": {"fact_cells": [_fact_cell(3, claim_only=True)]},
        })

        self.assertEqual(projected["fact_cells_for_strategist"][0]["extracted_fact"], "legacy claim 3")


if __name__ == "__main__":
    unittest.main()
