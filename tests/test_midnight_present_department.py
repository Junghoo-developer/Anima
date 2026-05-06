import unittest
from pathlib import Path

from Core.midnight.future import build_future_field_critique, build_future_witness
from Core.midnight.past import PastAssemblyOutput
from Core.midnight.present import (
    PresentSecondDreamOutput,
    build_seconddream_payload,
    check_present_facts,
    persist_seconddream,
    raise_present_problems,
    summarize_day_memory,
)
from Core.midnight.recall.recent import (
    EmptySecondDream,
    RecallAuditorOutput,
    RecallFormatterOutput,
    auditor,
    formatter,
    prepare_empty_seconddreams,
)


class FakeSession:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        return []


class MidnightPresentDepartmentTests(unittest.TestCase):
    def _present_output(self):
        empty = EmptySecondDream(
            seconddream_key="seconddream::2026-05-05::1",
            branch_path="2026/05/05",
            created_at=1,
        )
        formatted = RecallFormatterOutput(
            formatted_items=[
                {"dream_key": "dream::1", "summary": "The field loop repeated the assistant identity answer."},
                {"dream_key": "dream::2", "summary": "Memory recall lacked a stable source boundary."},
            ],
            source_dream_keys=["dream::1", "dream::2"],
            source_persona="recent_recall_formatter",
        )
        criticized = RecallAuditorOutput(
            criticized_items=[
                {"kind": "supply_topic", "topic": "identity source boundary"},
                {"kind": "field_loop_problem", "problem": "answer repetition"},
            ],
            source_persona="recent_recall_auditor",
            citations=["dream::1", "dream::2"],
        )
        summary = summarize_day_memory(empty_seconddream=empty, recall_formatter_output=formatted)
        problems = raise_present_problems(empty_seconddream=empty, recall_auditor_output=criticized)
        output = check_present_facts(
            summary=summary,
            problems=problems,
            source_data=[
                {"text": summary.summary},
                {"text": "identity source boundary"},
                {"text": "answer repetition"},
            ],
        )
        return empty, formatted, criticized, summary, problems, output

    def test_present_nodes_are_callable_and_output_future_contract(self):
        empty, _formatted, _criticized, summary, problems, output = self._present_output()

        self.assertEqual(summary.seconddream_key, empty.seconddream_key)
        self.assertIn("field loop repeated", summary.summary)
        self.assertIn("identity source boundary", problems.supply_topics)
        self.assertIsInstance(output, PresentSecondDreamOutput)
        self.assertEqual(output.seconddream_key, empty.seconddream_key)
        self.assertEqual(output.audit["source_persona"], "recent_recall_formatter")

    def test_fact_checker_rejects_missing_source_persona(self):
        with self.assertRaises(ValueError):
            check_present_facts(
                summary={"seconddream_key": "sd::bad", "summary": "summary", "source_persona": ""},
                problems={"supply_topics": [], "field_loop_problems": [], "source_persona": ""},
                source_data=[],
            )

    def test_seconddream_persistence_writes_required_graph_shape(self):
        empty, formatted, _criticized, _summary, _problems, output = self._present_output()
        session = FakeSession()
        payload = persist_seconddream(
            session,
            {
                "seconddream_key": output.seconddream_key,
                "summary": output.summary,
                "problems": output.problems,
                "audit": output.audit,
                "source_persona": output.audit["source_persona"],
                "branch_path": empty.branch_path,
                "source_dream_keys": formatted.source_dream_keys,
                "created_at": empty.created_at,
            },
        )
        joined = "\n".join(query for query, _ in session.calls)

        self.assertEqual(payload["source_persona"], "recent_recall_formatter")
        self.assertIn("MERGE (sd:SecondDream", joined)
        self.assertIn("MERGE (tb:TimeBranch", joined)
        self.assertIn("GUIDES_BRANCH", joined)
        self.assertIn("AUDITED_FROM", joined)
        self.assertIn("CONTAINS_TOPIC", joined)
        self.assertIn("topic.embedding = coalesce(topic.embedding, [])", joined)
        self.assertEqual(session.calls[0][1]["governor_key"], "night_government_v1")

    def test_build_seconddream_payload_requires_source_persona(self):
        with self.assertRaises(ValueError):
            build_seconddream_payload(
                seconddream_key="sd::bad",
                summary="summary",
                problems=[],
                audit={},
                source_persona="",
                branch_path="2026/05/05",
            )

    def test_recent_recall_body_is_callable(self):
        self.assertEqual(prepare_empty_seconddreams(), [])
        formatted = formatter.format([{"dream_key": "dream::raw", "summary": "raw day item"}])
        audited = auditor.audit(formatted)

        self.assertEqual(formatted.formatted_items[0]["summary"], "raw day item")
        self.assertEqual(formatted.source_dream_keys, ["dream::raw"])
        self.assertEqual(audited.criticized_items[0]["summary"], "raw day item")
        self.assertEqual(audited.source_persona, "system")

    def test_future_department_accepts_present_output(self):
        _empty, _formatted, _criticized, _summary, _problems, output = self._present_output()
        witness = build_future_witness(
            past_input=PastAssemblyOutput(
                past_assembly_thought="Past assembly approved present analysis.",
                election_result=True,
                change_proposal={},
                election_rounds=0,
            )
        )
        critic = build_future_field_critique(witness_packet=witness, present_input=output)

        self.assertEqual(critic["present_summary"], output.summary)
        self.assertIn("identity source boundary", critic["missing_topics"])

    def test_present_mock_input_is_removed_from_live_future_contracts(self):
        root = Path(__file__).resolve().parents[1]
        marker = "PresentSecondDream" + "MockInput"
        for path in (root / "Core").rglob("*.py"):
            if "_archive_v3_midnight" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(marker, text, f"{marker} still appears in {path}")
        for path in (root / "tests").rglob("*.py"):
            if path.name == Path(__file__).name:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(marker, text, f"{marker} still appears in {path}")

    def test_old_route_policy_and_tool_doctrine_are_not_live_code(self):
        root = Path(__file__).resolve().parents[1]
        forbidden = ["Route" + "Policy", "Tool" + "Doctrine"]
        for folder_name in ["Core", "tools"]:
            for path in (root / folder_name).rglob("*.py"):
                if "_archive_v3_midnight" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8")
                for marker in forbidden:
                    self.assertNotIn(marker, text, f"{marker} still appears in {path}")


if __name__ == "__main__":
    unittest.main()
