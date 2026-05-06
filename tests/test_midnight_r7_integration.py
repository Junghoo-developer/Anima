import unittest
from pathlib import Path

from Core import tools as live_tools
from Core.midnight import run_night


class FakeLiveSession:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        if "MATCH (d:Dream)" in query and "AUDITED_FROM" in query:
            return [
                {
                    "dream_key": "dream::live::1",
                    "summary": "The live field loop needs identity context.",
                    "content": "",
                    "created_at": "2026-05-05T01:00:00",
                    "source_persona": "정후",
                }
            ]
        if "'Diary' AS source_type" in query:
            return [
                {
                    "source_id": "diary::live::1",
                    "source_type": "Diary",
                    "text": "identity context and memory recall support",
                    "summary": "identity context",
                    "source_persona": "정후",
                }
            ]
        if "'SecondDream' AS source_type" in query:
            return [
                {
                    "source_id": "seconddream::live::1",
                    "source_type": "SecondDream",
                    "text": "present department noted identity context",
                    "summary": "present identity context",
                    "source_persona": "송련",
                }
            ]
        if "head(labels(n)) AS source_type" in query:
            return [
                {
                    "source_id": "graph::live::1",
                    "source_type": "GraphNode",
                    "text": "night government graph note",
                    "summary": "graph note",
                    "source_persona": "system",
                }
            ]
        return []


class MidnightR7IntegrationTests(unittest.TestCase):
    def test_run_night_uses_live_session_and_persists_chain(self):
        session = FakeLiveSession()
        packet = run_night(graph_session=session, persist=True, source_persona="night_government_v1")
        joined = "\n".join(query for query, _ in session.calls)

        self.assertEqual(packet["status"], "completed")
        self.assertEqual(packet["recent"]["unprocessed_count"], 1)
        self.assertIsNotNone(packet["persisted_seconddream"])
        self.assertIsNotNone(packet["persisted_change_proposal"])
        self.assertIsNotNone(packet["persisted_election"])
        self.assertIsNotNone(packet["future"]["persisted_dreamhint"])
        self.assertIn("MERGE (sd:SecondDream", joined)
        self.assertIn("MERGE (dh:DreamHint", joined)
        self.assertIn("MATCH (d:Diary)", joined)
        self.assertIn("archive_at", joined)
        self.assertIn("persist_seconddream", {item["operation"] for item in packet["graph_operations_log"]})
        self.assertIn("persist_dreamhint", {item["operation"] for item in packet["graph_operations_log"]})

    def test_run_night_does_not_cleanup_shared_accord_by_default(self):
        session = FakeLiveSession()
        run_night(graph_session=session, persist=True, source_persona="night_government_v1")
        joined = "\n".join(query for query, _ in session.calls)

        self.assertNotIn("DETACH DELETE acc", joined)

    def test_r7_migration_scripts_document_backup_migration_verify_and_rollback(self):
        root = Path(__file__).resolve().parents[1]
        backup = (root / "tools" / "r7_backup_and_migration.ps1").read_text(encoding="utf-8")
        migration = (root / "tools" / "r7_migration.cypher").read_text(encoding="utf-8")
        rollback = (root / "tools" / "r7_migration_rollback.cypher").read_text(encoding="utf-8")
        verify = (root / "tools" / "r7_verify.cypher").read_text(encoding="utf-8")

        self.assertIn("neo4j-admin database dump", backup)
        self.assertIn("tools/r7_migration.cypher", backup)
        self.assertIn("SET n:TimeBranch", migration)
        self.assertIn("SET n:NightGovernmentState", migration)
        self.assertIn('name: "허정후-송련 어코드"', migration)
        self.assertIn("topic.embedding", migration)
        self.assertIn("SET n:GovernorBranch", rollback)
        self.assertIn("GovernorBranch_remaining", verify)

    def test_field_loop_has_active_dreamhint_tool_registered(self):
        tool_names = {tool.name for tool in live_tools.available_tools}

        self.assertIn("tool_search_dreamhints", tool_names)


if __name__ == "__main__":
    unittest.main()
