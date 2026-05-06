import unittest
from pathlib import Path

from Core.midnight import run_night
from Core.midnight.future import run_future_assembly
from Core.midnight.past import approve_coreego, assemble_coreego, design_coreego
from Core.midnight.present import check_present_facts, raise_present_problems, summarize_day_memory
from Core.midnight.recall.random import auditor as random_auditor
from Core.midnight.recall.random import cosine_similarity
from Core.midnight.recall.random import formatter as random_formatter
from Core.midnight.recall.random import invoke
from Core.midnight.recall.recent import auditor as recent_auditor
from Core.midnight.recall.recent import formatter as recent_formatter
from Core.midnight.recall.recent import prepare_empty_seconddreams


class MidnightRecallDepartmentTests(unittest.TestCase):
    def _dream_rows(self):
        return [
            {
                "dream_key": "dream::1",
                "summary": "SongRyeon repeated an identity answer.",
                "created_at": "2026-05-05T01:02:03",
            },
            {
                "dream_key": "dream::2",
                "summary": "The field loop needed a memory source boundary.",
                "created_at": "2026-05-05T03:04:05",
            },
        ]

    def test_recent_recall_prepares_formats_and_audits_day_memory(self):
        dreams = self._dream_rows()
        empty = prepare_empty_seconddreams(dreams)
        formatted = recent_formatter.format(dreams, source_persona="정후")
        audited = recent_auditor.audit(formatted, source_persona="송련")

        self.assertEqual(len(empty), 1)
        self.assertEqual(empty[0].branch_path, "2026/05/05")
        self.assertEqual(empty[0].source_dream_keys, ["dream::1", "dream::2"])
        self.assertEqual(formatted.source_persona, "정후")
        self.assertEqual(audited.source_persona, "송련")
        self.assertEqual(audited.citations, ["dream::1", "dream::2"])

    def test_recent_recall_rejects_missing_source_persona(self):
        with self.assertRaises(ValueError):
            recent_formatter.format([], source_persona="")
        with self.assertRaises(ValueError):
            recent_auditor.audit({"formatted_items": [], "source_persona": ""}, source_persona="")

    def test_random_recall_cosine_similarity_and_persona_filter(self):
        result = invoke(
            "memory identity source",
            persona_filter="diary",
            sources=[
                {
                    "source_id": "diary::strong",
                    "source_type": "Diary",
                    "text": "memory identity source boundary",
                    "embedding": [1, 1, 0],
                },
                {
                    "source_id": "diary::weak",
                    "source_type": "Diary",
                    "text": "unrelated note",
                    "embedding": [0, 0, 1],
                },
                {
                    "source_id": "sd::filtered",
                    "source_type": "SecondDream",
                    "text": "memory identity source boundary",
                    "embedding": [1, 1, 0],
                },
            ],
            embedding_provider=lambda text: [1, 1, 0],
        )

        self.assertAlmostEqual(cosine_similarity([1, 1, 0], [1, 1, 0]), 1.0)
        self.assertEqual([item["source_id"] for item in result.results], ["diary::strong", "diary::weak"])
        self.assertEqual(result.source_persona_map["diary::strong"], "정후")

    def test_random_recall_formatter_and_auditor_require_persona(self):
        result = invoke(
            "identity",
            sources=[{"source_id": "graph::1", "source_type": "GraphNode", "text": "identity context"}],
        )
        formatted = random_formatter.format(result, source_persona="future_recall_formatter")
        audited = random_auditor.audit(formatted, source_persona="future_recall_auditor")

        self.assertEqual(formatted.source_persona, "future_recall_formatter")
        self.assertEqual(audited.source_persona, "future_recall_auditor")
        self.assertEqual(audited.citations, ["graph::1"])
        with self.assertRaises(ValueError):
            random_formatter.format(result, source_persona="")
        with self.assertRaises(ValueError):
            random_auditor.audit(formatted, source_persona="")

    def test_random_recall_supports_semantic_axis_after_r8(self):
        result = invoke(
            "identity",
            axis="semantic",
            sources=[{"source_id": "concept::1", "source_type": "ConceptCluster", "text": "identity semantic memory"}],
        )

        self.assertEqual(result.axis, "semantic")
        self.assertEqual(result.results[0]["source_id"], "concept::1")

    def test_recall_present_past_future_chain(self):
        dreams = self._dream_rows()
        empty = prepare_empty_seconddreams(dreams)[0]
        formatted = recent_formatter.format(dreams, source_persona="정후")
        audited = recent_auditor.audit(formatted, source_persona="송련")
        summary = summarize_day_memory(empty_seconddream=empty, recall_formatter_output=formatted)
        problems = raise_present_problems(empty_seconddream=empty, recall_auditor_output=audited)
        present = check_present_facts(summary=summary, problems=problems, source_data=formatted.formatted_items)
        design = design_coreego()
        past = approve_coreego(assembly_output=assemble_coreego(unresolved_second_dreams=[present.__dict__], design_packet=design))
        future = run_future_assembly(
            past_input=past,
            present_input=present,
            source_persona="future_decision_maker",
            recall_invoke=lambda query, persona_filter=None: invoke(
                query,
                persona_filter=persona_filter,
                sources=[{"source_id": "diary::1", "source_type": "Diary", "text": query}],
            ),
        )

        self.assertEqual(future["decision"]["status"], "approved")
        self.assertEqual(future["decision"]["dreamhint"]["source_persona"], "future_decision_maker")

    def test_run_night_no_longer_raises_not_implemented(self):
        packet = run_night(
            unprocessed_dreams=self._dream_rows(),
            random_sources=[{"source_id": "diary::night", "source_type": "Diary", "text": "identity answer source"}],
        )

        self.assertEqual(packet["status"], "completed")
        self.assertIn("recent", packet)
        self.assertIn("future", packet)

    def test_r5_mock_names_are_removed_from_live_recall_code(self):
        root = Path(__file__).resolve().parents[1]
        markers = ["EmptySecondDream" + "Mock", "RecallFormatterOutput" + "Mock", "RecallAuditorOutput" + "Mock"]
        for path in (root / "Core").rglob("*.py"):
            if "_archive_v3_midnight" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for marker in markers:
                self.assertNotIn(marker, text, f"{marker} still appears in {path}")


if __name__ == "__main__":
    unittest.main()
