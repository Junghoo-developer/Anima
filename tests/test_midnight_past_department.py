import unittest

from Core.midnight.future import build_future_witness
from Core.midnight.past import (
    PastAssemblyOutput,
    approve_coreego,
    assemble_coreego,
    assemble_local_council,
    build_time_branch_specs,
    cleanup_shared_accord,
    design_coreego,
    persist_change_proposal,
    persist_election,
    persist_time_branch_window,
    verify_shared_accord_removed,
)


class FakeSession:
    def __init__(self, shared_accord_count=0):
        self.calls = []
        self.shared_accord_count = shared_accord_count

    def run(self, query, **params):
        self.calls.append((query, params))
        if "RETURN count(acc) AS count" in query:
            return [{"count": self.shared_accord_count}]
        return []


class MidnightPastDepartmentTests(unittest.TestCase):
    def test_coreego_nodes_are_callable_and_output_future_contract(self):
        design = design_coreego(
            night_context={"observed_graph": {"labels": ["CoreEgo"], "relationships": ["HAS_TIME_BRANCH"]}}
        )
        local = assemble_local_council(
            council_key="Time/2026/05",
            branch_path="Time/2026/05",
            subordinate_second_dreams=[{"summary": "The field loop needs identity grounding."}],
        )
        assembled = assemble_coreego(
            unresolved_second_dreams=[
                {
                    "dream_id": "sd::1",
                    "topic": "CoreEgo:SongRyeon",
                    "summary": "SongRyeon needs stable identity context.",
                }
            ],
            local_submissions=[local],
            design_packet=design,
        )
        approved = approve_coreego(
            assembly_output=assembled,
            local_reports=[{"council_key": "Time/2026/05", "vote": True}],
        )

        self.assertIsInstance(approved, PastAssemblyOutput)
        self.assertTrue(approved.election_result)
        self.assertIn("rationale", approved.change_proposal)
        self.assertIn("importance", approved.change_proposal)
        self.assertIn("election", approved.change_proposal)

        witness = build_future_witness(past_input=approved)
        self.assertIn("Election result: pass", witness["witness_summary"])

    def test_shared_accord_cleanup_and_verify_cypher(self):
        session = FakeSession(shared_accord_count=0)
        cleanup_shared_accord(session)

        self.assertTrue(verify_shared_accord_removed(session))
        joined = "\n".join(query for query, _ in session.calls)
        self.assertIn('MATCH (acc {kind: "shared_accord", name: $accord_name})', joined)
        self.assertIn("DETACH DELETE acc", joined)
        self.assertEqual(session.calls[0][1]["accord_name"], "허정후-송련 어코드")

    def test_verify_shared_accord_removed_detects_remaining_node(self):
        session = FakeSession(shared_accord_count=1)

        self.assertFalse(verify_shared_accord_removed(session))

    def test_time_branch_sliding_window_persistence(self):
        session = FakeSession()
        specs = persist_time_branch_window(session, ["2026-05-01", "2026-05-02", "2026-06-01"])
        joined = "\n".join(query for query, _ in session.calls)

        self.assertIn("2026", {spec["branch_path"] for spec in specs})
        self.assertIn("2026/05", {spec["branch_path"] for spec in specs})
        self.assertIn("2026/05/01", {spec["branch_path"] for spec in specs})
        self.assertIn("HAS_TIME_BRANCH", joined)
        self.assertIn("HAS_CHILD_TIME_BRANCH", joined)
        self.assertIn("NEXT_SIBLING", joined)

    def test_build_time_branch_specs_dedupes_year_month_day(self):
        specs = build_time_branch_specs(["2026-05-01", "2026-05-01"])

        self.assertEqual([spec["branch_path"] for spec in specs], ["2026", "2026/05", "2026/05/01"])

    def test_change_proposal_persists_rationale_and_importance_separately(self):
        session = FakeSession()
        proposal = persist_change_proposal(
            session,
            {
                "target_node_id": "CoreEgo:SongRyeon",
                "attr_name": "identity_context",
                "new_value": "Keep SongRyeon identity stable.",
                "rationale": {
                    "summary": "The field loop hallucinated identity.",
                    "evidence_keys": ["sd::1"],
                    "sources": ["SecondDream:sd::1"],
                },
                "importance": {"score": 0.8, "sources": ["SecondDream:sd::1"]},
            },
        )
        joined = "\n".join(query for query, _ in session.calls)

        self.assertIn("MERGE (cr:ChangeRationale", joined)
        self.assertIn("MERGE (ci:ChangeImportance", joined)
        self.assertIn("JUSTIFIES", joined)
        self.assertIn("WEIGHS", joined)
        self.assertEqual(proposal["importance"]["score"], 0.8)

    def test_election_pass_fail_and_emergency_branch(self):
        assembled = assemble_coreego(
            unresolved_second_dreams=[{"dream_id": "sd::1", "summary": "proposal"}],
        )
        passed = approve_coreego(
            assembly_output=assembled,
            local_reports=[
                {"council_key": "a", "vote": True},
                {"council_key": "b", "vote": True},
                {"council_key": "c", "vote": False},
            ],
        )
        failed = approve_coreego(
            assembly_output=assembled,
            local_reports=[
                {"council_key": "a", "vote": True},
                {"council_key": "b", "vote": False},
            ],
        )

        self.assertTrue(passed.election_result)
        self.assertFalse(failed.election_result)
        with self.assertRaises(NotImplementedError):
            approve_coreego(assembly_output=assembled, election_rounds=3)

    def test_persist_election_writes_election_node(self):
        session = FakeSession()
        assembled = assemble_coreego(unresolved_second_dreams=[{"dream_id": "sd::1", "summary": "proposal"}])
        approved = approve_coreego(assembly_output=assembled)
        election = persist_election(session, approved.change_proposal["election"])
        joined = "\n".join(query for query, _ in session.calls)

        self.assertIn("MERGE (el:Election", joined)
        self.assertIn("VOTES_ON", joined)
        self.assertEqual(election["result"], "pass")


if __name__ == "__main__":
    unittest.main()
