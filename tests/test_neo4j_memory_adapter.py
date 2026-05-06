import unittest
from contextlib import contextmanager

from Core.adapters import neo4j_memory
from Core.adapters.neo4j_memory import (
    normalize_source_type,
    read_full_source,
    scroll_chat_log,
    search_memory,
)
from Core.tools import available_tools
from tools import toolbox
from embed_past_records import chunk_text


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def run(self, query, **params):
        self.calls.append({"query": query, "params": params})
        return list(self.rows)


class FakeResult(list):
    def data(self):
        return list(self)


class FakeSingle:
    def __init__(self, value):
        self.value = value

    def single(self):
        return self.value


class SchemaSession:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append({"query": query, "params": params})
        if "db.labels" in query:
            return FakeSingle({"labels": ["PastRecord", "Diary"]})
        if "db.relationshipTypes" in query:
            return FakeSingle({"rels": ["NEXT"]})
        if "db.propertyKeys" in query:
            return FakeSingle({"props": ["id", "date", "content"]})
        return FakeSingle({})


class RoutingSession:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append({"query": query, "params": params})
        if "past_record_chunk_embedding" in query:
            return FakeResult(
                [
                    {
                        "node_id": "vec-1",
                        "labels": ["PastRecord", "Diary"],
                        "date": "2026-04-27",
                        "role": "",
                        "content": "Agent study plan and linear algebra notes from chunk 2.",
                        "score": 0.71,
                        "chunk_id": "chunk-1",
                        "chunk_index": 2,
                    }
                ]
            )
        if "past_record_embedding" in query:
            return FakeResult([])
        if "CONTAINS" in query:
            return FakeResult(
                [
                    {
                        "node_id": "lex-1",
                        "labels": ["PastRecord", "GeminiChat"],
                        "date": "2026-04-28",
                        "role": "user",
                        "content": "I searched for agent development ideas.",
                        "score": 0.999,
                    }
                ]
            )
        return FakeResult([])


def fake_session_factory(rows, holder):
    @contextmanager
    def _factory():
        session = FakeSession(rows)
        holder.append(session)
        yield session

    return _factory


def routing_session_factory(holder):
    @contextmanager
    def _factory():
        session = RoutingSession()
        holder.append(session)
        yield session

    return _factory


def schema_session_factory(holder):
    @contextmanager
    def _factory():
        session = SchemaSession()
        holder.append(session)
        yield session

    return _factory


class Neo4jMemoryAdapterTests(unittest.TestCase):
    def test_normalize_source_type_accepts_canonical_and_korean_aliases(self):
        self.assertEqual(normalize_source_type("diary"), "diary")
        self.assertEqual(normalize_source_type("일기장"), "diary")
        self.assertEqual(normalize_source_type("GeminiChat"), "gemini")
        self.assertEqual(normalize_source_type("송련"), "songryeon")
        self.assertEqual(normalize_source_type("PastRecord"), "raw")

    def test_read_full_source_uses_canonical_diary_query(self):
        sessions = []
        text, ids = read_full_source(
            "diary",
            "2026-04-27",
            session_factory=fake_session_factory([{"content": "Diary body"}], sessions),
        )

        self.assertEqual(ids, ["2026-04-27"])
        self.assertIn("[USER_DIARY]", text)
        self.assertIn("Diary body", text)
        self.assertIn("r:Diary", sessions[0].calls[0]["query"])
        self.assertEqual(sessions[0].calls[0]["params"]["alt_date"], "2026 4 27")

    def test_read_full_source_formats_chat_roles(self):
        sessions = []
        text, ids = read_full_source(
            "gemini",
            "2026-04-27",
            session_factory=fake_session_factory(
                [
                    {"role": "user", "content": "User turn"},
                    {"role": "model", "content": "Model turn"},
                ],
                sessions,
            ),
        )

        self.assertEqual(ids, ["2026-04-27"])
        self.assertIn("[EXTERNAL_ASSISTANT]", text)
        self.assertIn("[user]: User turn", text)
        self.assertIn("[Gemini]: Model turn", text)
        self.assertIn("r:GeminiChat", sessions[0].calls[0]["query"])

    def test_toolbox_read_full_source_delegates_to_adapter(self):
        sessions = []
        original = toolbox.get_db_session
        toolbox.get_db_session = fake_session_factory([{"content": "Delegated diary"}], sessions)
        try:
            text, ids = toolbox.read_full_source("일기장", "2026-04-27")
        finally:
            toolbox.get_db_session = original

        self.assertEqual(ids, ["2026-04-27"])
        self.assertIn("Delegated diary", text)

    def test_scroll_chat_log_formats_context_sections(self):
        sessions = []
        rows = [
            {"id": "2026-04-27-1", "speaker": "user", "content": "before turn", "tag": "context_before"},
            {"id": "2026-04-27-2", "speaker": "assistant", "content": "anchor turn", "tag": "target_hit"},
            {"id": "2026-04-27-3", "speaker": "user", "content": "after turn", "tag": "context_after"},
        ]
        text, ids = scroll_chat_log(
            "2026-04-27",
            direction="both",
            limit=8,
            session_factory=fake_session_factory(rows, sessions),
        )

        self.assertEqual(ids, ["2026-04-27-1", "2026-04-27-2", "2026-04-27-3"])
        self.assertIn("[context scroll result]", text)
        self.assertIn("[anchor]", text)
        self.assertIn("[before 1]", text)
        self.assertIn("[after 1]", text)
        self.assertEqual(sessions[0].calls[0]["params"]["a_id"], "2026 4 27")

    def test_search_memory_uses_adapter_queries_and_formats_candidates(self):
        sessions = []
        text, ids = search_memory(
            "agent",
            session_factory=routing_session_factory(sessions),
            embedding_provider=lambda _: {"mxbai-embed-large": [1.0, 0.0]},
        )

        self.assertEqual(ids, ["2026-04-28", "2026-04-27"])
        self.assertIn("Root-first memory search results", text)
        self.assertIn("[source: GeminiChat|2026-04-28]", text)
        self.assertIn("[source: Diary|2026-04-27]", text)
        self.assertIn("past_record_chunk_embedding", sessions[0].calls[0]["query"])
        self.assertIn("CONTAINS", sessions[0].calls[-1]["query"])
        self.assertIn("linear algebra notes from chunk", text)

    def test_chunk_text_uses_overlap_and_keeps_full_coverage(self):
        text = "".join(str(idx % 10) for idx in range(190))
        chunks = chunk_text(text, chunk_chars=80, overlap=20)

        self.assertEqual([chunk["start_char"] for chunk in chunks], [0, 60, 120])
        self.assertEqual([chunk["end_char"] for chunk in chunks], [80, 140, 190])
        self.assertEqual(chunks[1]["text"], text[60:140])
        self.assertEqual(chunks[-1]["text"], text[120:190])

    def test_toolbox_search_memory_delegates_to_adapter(self):
        sessions = []
        original_session = toolbox.get_db_session
        original_embedding = neo4j_memory._default_embedding_provider
        toolbox.get_db_session = routing_session_factory(sessions)
        neo4j_memory._default_embedding_provider = lambda _: {"mxbai-embed-large": [1.0, 0.0]}
        try:
            text, ids = toolbox.search_memory("agent")
        finally:
            toolbox.get_db_session = original_session
            neo4j_memory._default_embedding_provider = original_embedding

        self.assertEqual(ids, ["2026-04-28", "2026-04-27"])
        self.assertIn("Root-first memory search results", text)

    def test_scan_db_schema_uses_adapter_boundary(self):
        sessions = []
        text, ids = neo4j_memory.scan_db_schema(session_factory=schema_session_factory(sessions))

        self.assertEqual(ids, [])
        self.assertIn("[live DB schema scan]", text)
        self.assertIn("PastRecord", text)
        self.assertIn("NEXT", text)
        self.assertEqual(len(sessions[0].calls), 3)

    def test_toolbox_scan_db_schema_delegates_to_adapter(self):
        sessions = []
        original = toolbox.get_db_session
        toolbox.get_db_session = schema_session_factory(sessions)
        try:
            text, ids = toolbox.scan_db_schema()
        finally:
            toolbox.get_db_session = original

        self.assertEqual(ids, [])
        self.assertIn("[live DB schema scan]", text)
        self.assertEqual(len(sessions[0].calls), 3)

    def test_live_tool_registry_does_not_expose_retired_u_function_tools(self):
        names = [tool.name for tool in available_tools]
        self.assertNotIn("tool_scan_trend_u_function", names)
        self.assertNotIn("tool_scan_trend_u_function_3d", names)
        self.assertIn("tool_read_full_diary", names)


if __name__ == "__main__":
    unittest.main()
