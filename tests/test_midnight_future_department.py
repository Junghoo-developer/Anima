import unittest
from pathlib import Path

from Core.midnight.future import (
    PastAssemblyMockInput,
    build_future_field_critique,
    build_future_witness,
    make_future_decision,
    run_future_assembly,
)
from Core.midnight.present import PresentSecondDreamOutput
from Core.midnight.future.dreamhint_persistence import (
    build_active_dreamhint_query,
    build_dreamhint_payload,
    fetch_active_dreamhints,
    persist_dreamhint,
)
from Core.midnight.recall.random import RandomRecallResult, invoke


class FakeSession:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        return []


class MidnightFutureDepartmentTests(unittest.TestCase):
    def test_future_nodes_are_callable_and_approve_dreamhint(self):
        calls = []

        def fake_recall(query, persona_filter=None):
            calls.append((query, persona_filter))
            return RandomRecallResult(
                results=[{"source_id": "diary::1", "text": "The field loop repeated an answer."}],
                source_persona_map={"diary::1": "user_diary"},
                query=query,
                persona_filter=persona_filter,
            )

        past = PastAssemblyMockInput(
            past_assembly_thought="Past assembly approved a field-loop repair.",
            election_result=True,
            change_proposal={"branch_path": "Time/2026/05/field-loop", "action": "add advisory"},
        )
        present = PresentSecondDreamOutput(
            seconddream_key="sd::present::1",
            summary="The day showed repetition and weak memory recall.",
            problems=["answer repetition", {"topic": "memory recall weakness"}],
            audit={"gaps": ["canonical identity context"]},
        )

        witness = build_future_witness(past_input=past, previous_decision_thought="Prior decision stayed narrow.")
        critic = build_future_field_critique(
            witness_packet=witness,
            present_input=present,
            recall_invoke=fake_recall,
        )
        decision = make_future_decision(
            witness_packet=witness,
            critic_packet=critic,
            source_persona="future_decision_maker",
            branch_path="Time/2026/05/field-loop",
        )

        self.assertEqual(witness["next_node"], "field_critic")
        self.assertEqual(critic["next_node"], "decision_maker")
        self.assertEqual(decision["status"], "approved")
        self.assertEqual(decision["dreamhint"]["source_persona"], "future_decision_maker")
        self.assertEqual(calls[0][0], "answer repetition; memory recall weakness; canonical identity context")

    def test_future_cycle_remands_when_random_recall_is_empty(self):
        past = PastAssemblyMockInput("Past thought exists.", True, {})
        present = PresentSecondDreamOutput("sd::present::2", "summary", ["missing support"], {})
        witness = build_future_witness(past_input=past)
        critic = build_future_field_critique(witness_packet=witness, present_input=present)
        decision = make_future_decision(
            witness_packet=witness,
            critic_packet=critic,
            source_persona="future_decision_maker",
        )

        self.assertEqual(critic["next_node"], "future_witness")
        self.assertEqual(decision["decision"], "remand")
        self.assertEqual(decision["remand_target"], "field_critic")

    def test_dreamhint_persistence_writes_required_graph_shape(self):
        session = FakeSession()
        payload = build_dreamhint_payload(
            hint_text="Use a short advisory for the field loop.",
            source_persona="future_decision_maker",
            branch_path="Time/2026/05/field-loop",
            cites_past_thought=["past-thought-1"],
            recall_result_refs=["recall-result-1"],
            created_at=1,
            archive_at=None,
        )

        persisted = persist_dreamhint(session, payload)
        joined_queries = "\n".join(query for query, _ in session.calls)

        self.assertEqual(persisted["source_persona"], "future_decision_maker")
        self.assertIn("MERGE (dh:DreamHint", joined_queries)
        self.assertIn("MERGE (tb:TimeBranch", joined_queries)
        self.assertIn("GUIDES_BRANCH", joined_queries)
        self.assertIn("CITES_PAST_THOUGHT", joined_queries)
        self.assertIn("LINKS_RECALL_RESULT", joined_queries)
        self.assertIn("dh.archive_at = $archive_at", joined_queries)
        self.assertIsNone(persisted["archive_at"])
        self.assertEqual(session.calls[0][1]["governor_key"], "night_government_v1")

    def test_active_dreamhint_query_filters_archived_and_expired_hints(self):
        query, params = build_active_dreamhint_query(branch_path="Time/2026/05/field-loop", limit=3)

        self.assertIn("coalesce(dh.archive_at, 9999999999999) > timestamp()", query)
        self.assertIn("coalesce(dh.expires_at, 9999999999999) > timestamp()", query)
        self.assertEqual(params["branch_path"], "Time/2026/05/field-loop")
        self.assertEqual(params["limit"], 3)

    def test_fetch_active_dreamhints_uses_active_filter(self):
        class HintSession(FakeSession):
            def run(self, query, **params):
                super().run(query, **params)
                return [{"dreamhint_key": "dh::1", "hint_text": "active"}]

        session = HintSession()
        rows = fetch_active_dreamhints(session, limit=1)
        joined = "\n".join(query for query, _ in session.calls)

        self.assertEqual(rows[0]["dreamhint_key"], "dh::1")
        self.assertIn("archive_at", joined)

    def test_dreamhint_rejects_missing_source_persona(self):
        with self.assertRaises(ValueError):
            build_dreamhint_payload(
                hint_text="missing persona should fail",
                source_persona="",
                branch_path="Time/2026/05/field-loop",
            )

    def test_run_future_assembly_can_persist_with_mock_inputs(self):
        session = FakeSession()
        result = run_future_assembly(
            past_input=PastAssemblyMockInput("Past thought.", True, {}),
            present_input=PresentSecondDreamOutput("sd::present::3", "summary", [], {}),
            source_persona="future_decision_maker",
            branch_path="Time/2026/05/field-loop",
            session=session,
        )

        self.assertEqual(result["decision"]["status"], "approved")
        self.assertIsNotNone(result["persisted_dreamhint"])
        self.assertTrue(session.calls)

    def test_random_recall_ranks_injected_sources(self):
        result = invoke(
            "identity drift",
            persona_filter="diary",
            sources=[
                {
                    "source_id": "diary::identity",
                    "source_type": "Diary",
                    "text": "identity drift and memory recall repair",
                },
                {
                    "source_id": "sd::other",
                    "source_type": "SecondDream",
                    "text": "unrelated cooking note",
                },
            ],
        )

        self.assertEqual(result.results[0]["source_id"], "diary::identity")
        self.assertEqual(result.source_persona_map, {"diary::identity": "정후"})
        self.assertEqual(result.query, "identity drift")
        self.assertEqual(result.persona_filter, "diary")

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
