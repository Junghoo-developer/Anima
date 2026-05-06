import argparse
import os
from datetime import datetime, timezone

import ollama
from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

EMBEDDING_MODEL = os.getenv("ANIMA_PAST_RECORD_EMBEDDING_MODEL", "mxbai-embed-large")
EMBEDDING_DIMENSIONS = int(os.getenv("ANIMA_PAST_RECORD_EMBEDDING_DIMENSIONS", "1024"))
DEFAULT_CHUNK_CHARS = int(os.getenv("ANIMA_PAST_RECORD_CHUNK_CHARS", "240"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("ANIMA_PAST_RECORD_CHUNK_OVERLAP", "50"))


def chunk_text(text: str, *, chunk_chars: int = DEFAULT_CHUNK_CHARS, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[dict]:
    """Split raw PastRecord text into small character windows for embedding.

    mxbai-embed-large has a short effective sequence length. Character windows
    are deliberately conservative for Korean text; the full source remains on
    PastRecord and can still be read after a chunk hit.
    """
    normalized = str(text or "").strip()
    if not normalized:
        return []

    chunk_chars = max(80, int(chunk_chars or DEFAULT_CHUNK_CHARS))
    overlap = max(0, min(int(overlap or 0), chunk_chars - 1))
    step = max(1, chunk_chars - overlap)

    chunks = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_chars, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append({
                "chunk_index": len(chunks),
                "start_char": start,
                "end_char": end,
                "text": chunk,
            })
        if end >= len(normalized):
            break
        start += step
    return chunks


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PastRecordEmbedder:
    def __init__(self, *, chunk_chars: int = DEFAULT_CHUNK_CHARS, overlap: int = DEFAULT_CHUNK_OVERLAP):
        print("[System] PastRecord raw text chunk embedding module starting...")
        print(f"  - embedding_model={EMBEDDING_MODEL} ({EMBEDDING_DIMENSIONS} dims)")
        print(f"  - chunk_chars={chunk_chars}, overlap={overlap}")
        self.chunk_chars = chunk_chars
        self.overlap = overlap
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def _get_embedding(self, text: str):
        if not text or len(text.strip()) < 2:
            return None
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text.strip())
        vector = response.get("embedding") if isinstance(response, dict) else None
        if not isinstance(vector, list) or not vector:
            return None
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"{EMBEDDING_MODEL} returned {len(vector)} dims; expected {EMBEDDING_DIMENSIONS}"
            )
        return [float(value) for value in vector]

    def setup_vector_index(self):
        print("Step 1: ensuring PastRecordChunk constraints and vector index...")
        statements = [
            "CREATE CONSTRAINT past_record_chunk_id IF NOT EXISTS FOR (c:PastRecordChunk) REQUIRE c.id IS UNIQUE",
            f"""
            CREATE VECTOR INDEX past_record_chunk_embedding IF NOT EXISTS
            FOR (c:PastRecordChunk) ON (c.embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {EMBEDDING_DIMENSIONS},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
            """,
        ]
        with self.driver.session() as session:
            for statement in statements:
                session.run(statement)
        print("  OK: PastRecordChunk index is ready.")

    def _fetch_records(self, *, force: bool = False, limit: int = 0) -> list[dict]:
        cypher = """
        MATCH (p:PastRecord)
        WHERE p.content IS NOT NULL
          AND (
              $force = true
              OR NOT (p)-[:HAS_CHUNK]->(:PastRecordChunk)
              OR EXISTS {
                  MATCH (p)-[:HAS_CHUNK]->(c:PastRecordChunk)
                  WHERE c.embedding IS NULL OR coalesce(size(c.embedding), 0) = 0
              }
          )
        RETURN elementId(p) AS node_id,
               coalesce(p.id, elementId(p)) AS record_id,
               coalesce(p.date, '') AS date,
               coalesce(p.role, '') AS role,
               coalesce(p.source_table, '') AS source_table,
               p.content AS content,
               labels(p) AS labels
        ORDER BY coalesce(p.date, ''), coalesce(p.id, '')
        """
        with self.driver.session() as session:
            rows = session.run(cypher, force=bool(force)).data()
        if limit and limit > 0:
            rows = rows[:limit]
        return rows

    def _replace_chunks_for_record(self, session, record: dict, chunks: list[dict]):
        session.run(
            """
            MATCH (p:PastRecord) WHERE elementId(p) = $node_id
            OPTIONAL MATCH (p)-[:HAS_CHUNK]->(old:PastRecordChunk)
            DETACH DELETE old
            """,
            node_id=record["node_id"],
        )

        created_at = _utc_now()
        source_labels = [str(label) for label in record.get("labels", []) or []]
        for chunk in chunks:
            chunk_id = f"{record['record_id']}::chunk::{chunk['chunk_index']:04d}"
            vector = self._get_embedding(chunk["text"])
            if not vector:
                print(f"    - skipped empty embedding for chunk {chunk['chunk_index']}")
                continue
            session.run(
                """
                MATCH (p:PastRecord) WHERE elementId(p) = $node_id
                MERGE (c:PastRecordChunk {id: $chunk_id})
                SET c.text = $text,
                    c.embedding = $embedding,
                    c.embedding_model = $embedding_model,
                    c.embedding_dimensions = $embedding_dimensions,
                    c.chunk_index = $chunk_index,
                    c.start_char = $start_char,
                    c.end_char = $end_char,
                    c.chunk_chars = $chunk_chars,
                    c.chunk_overlap = $chunk_overlap,
                    c.source_record_id = $record_id,
                    c.source_table = $source_table,
                    c.source_labels = $source_labels,
                    c.date = $date,
                    c.role = $role,
                    c.created_at = coalesce(c.created_at, $created_at),
                    c.updated_at = $created_at
                MERGE (p)-[:HAS_CHUNK]->(c)
                """,
                node_id=record["node_id"],
                chunk_id=chunk_id,
                text=chunk["text"],
                embedding=vector,
                embedding_model=EMBEDDING_MODEL,
                embedding_dimensions=EMBEDDING_DIMENSIONS,
                chunk_index=chunk["chunk_index"],
                start_char=chunk["start_char"],
                end_char=chunk["end_char"],
                chunk_chars=self.chunk_chars,
                chunk_overlap=self.overlap,
                record_id=record["record_id"],
                source_table=record.get("source_table") or "",
                source_labels=source_labels,
                date=record.get("date") or "",
                role=record.get("role") or "",
                created_at=created_at,
            )

        session.run(
            """
            MATCH (p:PastRecord) WHERE elementId(p) = $node_id
            SET p.chunk_embedding_model = $embedding_model,
                p.chunk_embedding_dimensions = $embedding_dimensions,
                p.chunk_count = $chunk_count,
                p.chunked_at = $chunked_at
            """,
            node_id=record["node_id"],
            embedding_model=EMBEDDING_MODEL,
            embedding_dimensions=EMBEDDING_DIMENSIONS,
            chunk_count=len(chunks),
            chunked_at=created_at,
        )

    def process_past_records(self, *, force: bool = False, limit: int = 0):
        print("\nStep 2: finding PastRecord nodes that need chunk embeddings...")
        records = self._fetch_records(force=force, limit=limit)
        if not records:
            print("  OK: all PastRecord nodes already have chunk embeddings.")
            return

        print(f"  Found {len(records)} PastRecord nodes to chunk.")
        success_records = 0
        total_chunks = 0
        with self.driver.session() as session:
            for i, record in enumerate(records, 1):
                content = record.get("content") or ""
                labels = record.get("labels", []) or []
                label_text = "/".join(str(label) for label in labels)
                chunks = chunk_text(content, chunk_chars=self.chunk_chars, overlap=self.overlap)
                print(
                    f"  [{i}/{len(records)}] {record.get('date') or 'unknown-date'} "
                    f"{label_text or 'PastRecord'} -> {len(chunks)} chunks"
                )
                if not chunks:
                    continue
                try:
                    self._replace_chunks_for_record(session, record, chunks)
                except Exception as exc:
                    print(f"    ERROR: chunk embedding failed for {record.get('record_id')}: {exc}")
                    continue
                success_records += 1
                total_chunks += len(chunks)

        print(f"\nDone: chunked {success_records} PastRecord nodes into {total_chunks} PastRecordChunk nodes.")


def parse_args():
    parser = argparse.ArgumentParser(description="Create PastRecordChunk embeddings for Neo4j raw memory records.")
    parser.add_argument("--force", action="store_true", help="Delete and rebuild existing chunks for all PastRecord nodes.")
    parser.add_argument("--limit", type=int, default=0, help="Process at most N PastRecord nodes.")
    parser.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS, help="Characters per embedding chunk.")
    parser.add_argument("--overlap", type=int, default=DEFAULT_CHUNK_OVERLAP, help="Overlapping characters between chunks.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    embedder = PastRecordEmbedder(chunk_chars=args.chunk_chars, overlap=args.overlap)
    try:
        embedder.setup_vector_index()
        embedder.process_past_records(force=args.force, limit=args.limit)
    finally:
        embedder.close()
