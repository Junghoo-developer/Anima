import unittest

from Core.midnight import run_night
from Core.midnight.recall.random import invoke
from Core.midnight.semantic import (
    ARCHIVE_REVIVAL_SOURCES,
    approve_semantic_coreego,
    design_semantic_coreego,
    persist_concept_cluster,
    persist_semantic_branch,
    persist_timebucket_bridge,
    propose_semantic_branches,
    run_semantic_assembly,
)
from Core.midnight.semantic.persistence import build_concept_cluster_spec, build_semantic_branch_spec


class FakeSemanticSession:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        if "MATCH (sb:SemanticBranch)" in query:
            return [
                {
                    "source_id": "CoreEgo/Semantic/identity",
                    "source_type": "SemanticBranch",
                    "text": "identity context semantic branch",
                    "summary": "identity branch",
                    "source_persona": "송련",
                    "branch_path": "CoreEgo/Semantic/identity",
                }
            ]
        if "MATCH (cc:ConceptCluster)" in query:
            return [
                {
                    "source_id": "concept_cluster::identity",
                    "source_type": "ConceptCluster",
                    "text": "identity fact cluster",
                    "summary": "identity facts",
                    "source_persona": "송련",
                    "branch_path": "CoreEgo/Semantic/identity",
                }
            ]
        return []


class MidnightSemanticDepartmentTests(unittest.TestCase):
    def test_semantic_assembly_runs_and_revives_archive_concepts(self):
        packet = run_semantic_assembly(
            sources=[
                {
                    "source_id": "concept::1",
                    "source_type": "ConceptCluster",
                    "text": "SongRyeon identity memory boundary",
                    "source_persona": "송련",
                }
            ]
        )

        self.assertEqual(packet["status"], "completed")
        self.assertEqual(packet["axis"], "semantic")
        self.assertTrue(packet["self"]["branch_specs"])
        self.assertIn("rem_governor.py", " ".join(ARCHIVE_REVIVAL_SOURCES))
        self.assertEqual(packet["approval"]["change_proposal"]["axis"], "semantic")

    def test_semantic_branch_and_concept_persistence_shape(self):
        session = FakeSemanticSession()
        branch = build_semantic_branch_spec(
            branch_path="CoreEgo/Semantic/identity",
            title="identity",
            summary="identity semantic branch",
        )
        cluster = build_concept_cluster_spec(
            branch_path=branch.branch_path,
            title="identity facts",
            summary="facts about identity",
            facts=["SongRyeon needs stable identity context."],
            source_refs=["sd::1"],
            source_persona="송련",
        )
        persist_semantic_branch(session, branch)
        persist_concept_cluster(session, cluster)
        persist_timebucket_bridge(
            session,
            semantic_branch_path=branch.branch_path,
            time_bucket_key="2026/05/05",
        )
        joined = "\n".join(query for query, _ in session.calls)

        self.assertIn("MERGE (sb:SemanticBranch", joined)
        self.assertIn("HAS_SEMANTIC_BRANCH", joined)
        self.assertIn("MERGE (cc:ConceptCluster", joined)
        self.assertIn("CURATES", joined)
        self.assertIn("OBSERVES_TIME_BUCKET", joined)

    def test_semantic_axis_random_recall_uses_semantic_sources(self):
        session = FakeSemanticSession()
        result = invoke("identity semantic", axis="semantic", session=session)
        joined = "\n".join(query for query, _ in session.calls)

        self.assertEqual(result.axis, "semantic")
        self.assertTrue(result.results)
        self.assertIn("SemanticBranch", joined)
        self.assertIn("ConceptCluster", joined)
        self.assertEqual(result.source_persona_map[result.results[0]["source_id"]], "송련")

    def test_semantic_coreego_seats_are_callable(self):
        design = design_semantic_coreego(
            semantic_branches=[{"branch_path": "CoreEgo/Semantic/identity"}],
            concept_clusters=[{"cluster_key": "concept_cluster::identity"}],
        )
        self_packet = propose_semantic_branches(
            recall_results=[
                {
                    "source_id": "concept::1",
                    "source_type": "ConceptCluster",
                    "text": "identity and memory source boundary",
                    "source_persona": "송련",
                }
            ],
            design_packet=design,
        )
        approval = approve_semantic_coreego(
            self_packet=self_packet,
            local_reports=[{"council_key": "semantic::identity", "vote": True}],
        )

        self.assertEqual(design["axis"], "semantic")
        self.assertTrue(self_packet["branch_specs"])
        self.assertTrue(approval["election_result"])
        self.assertEqual(approval["change_proposal"]["axis"], "semantic")

    def test_run_night_can_include_semantic_axis(self):
        packet = run_night(
            unprocessed_dreams=[
                {
                    "dream_key": "dream::1",
                    "summary": "The field loop needs identity context.",
                    "created_at": "2026-05-05T01:00:00",
                }
            ],
            random_sources=[{"source_id": "diary::1", "source_type": "Diary", "text": "identity context"}],
            semantic_sources=[
                {
                    "source_id": "concept::1",
                    "source_type": "ConceptCluster",
                    "text": "identity context semantic branch",
                    "source_persona": "송련",
                }
            ],
            include_semantic=True,
        )

        self.assertEqual(packet["status"], "completed")
        self.assertIsNotNone(packet["semantic"])
        self.assertEqual(packet["semantic"]["axis"], "semantic")


if __name__ == "__main__":
    unittest.main()
