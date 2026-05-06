import math
import re
import unicodedata
from collections.abc import Callable

import ollama

from Core.adapters import neo4j_connection


def normalize_source_type(source_type: str) -> str:
    text = unicodedata.normalize("NFKC", str(source_type or "").strip()).lower()
    compact = re.sub(r"[\s_\-:/\\]+", "", text)
    if compact in {"diary", "journal", "userdiary", "pastdiary", "일기", "일기장"}:
        return "diary"
    if compact in {"gemini", "geminichat", "geminichats", "제미나이", "제미니"}:
        return "gemini"
    if compact in {"songryeon", "songryeonchat", "songryeonchats", "송련", "송련채팅"}:
        return "songryeon"
    if compact in {"raw", "pastrecord", "pastrecords", "memory", "메모리", "기억"}:
        return "raw"
    return compact


def _alternate_date_id(value: str) -> str:
    raw = str(value or "").strip()
    match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", raw)
    if not match:
        return raw
    year, month, day = match.groups()
    return f"{year} {int(month)} {int(day)}"


def _role_label(role: str, source_type: str) -> str:
    normalized_role = str(role or "").strip().lower()
    if normalized_role == "user":
        return "user"
    if source_type == "gemini":
        return "Gemini"
    if source_type == "songryeon":
        return "SongRyeon"
    return normalized_role or source_type


def _labels_for_source(source_type: str) -> str:
    if source_type == "diary":
        return "r:PastRecord OR r:Diary"
    if source_type == "gemini":
        return "r:PastRecord OR r:GeminiChat"
    if source_type == "songryeon":
        return "r:PastRecord OR r:SongryeonChat OR r:SongRyeonChat"
    if source_type == "raw":
        return "r:PastRecord"
    return ""


def read_full_source(
    source_type: str,
    target_date: str,
    *,
    session_factory: Callable | None = None,
) -> tuple[str, list[str]]:
    canonical = normalize_source_type(source_type)
    label_filter = _labels_for_source(canonical)
    if not label_filter:
        return (
            f"Unsupported source_type: {source_type!r}. Use one of diary, gemini, songryeon, or raw.",
            [],
        )

    target = str(target_date or "").strip()
    if not target:
        return "No target date/id was provided for read_full_source.", []

    alt_target = _alternate_date_id(target)
    return_role = canonical in {"gemini", "songryeon", "raw"}
    return_clause = "r.role AS role, r.content AS content" if return_role else "r.content AS content"
    cypher = f"""
    MATCH (r)
    WHERE ({label_filter})
      AND (
           trim(coalesce(r.date, '')) STARTS WITH $date
        OR trim(coalesce(r.date, '')) = $alt_date
        OR trim(coalesce(r.date, '')) STARTS WITH ($alt_date + ' ')
        OR trim(coalesce(r.id, '')) STARTS WITH $date
        OR trim(coalesce(r.id, '')) = $alt_date
        OR trim(coalesce(r.id, '')) STARTS WITH ($alt_date + ' ')
      )
    RETURN {return_clause}
    ORDER BY coalesce(r.date, r.id, '') ASC
    """

    session_factory = session_factory or neo4j_connection.get_db_session
    try:
        with session_factory() as session:
            records = list(session.run(cypher, date=target, alt_date=alt_target))
    except Exception as exc:
        return f"Full source read failed: {exc}", []

    if not records:
        return f"No {canonical} source was found for date/id '{target}'.", []

    title = f"[{target} {canonical} full source]"
    if canonical == "songryeon":
        warning = "[INTERNAL_SELF] This is SongRyeon's own live conversation record; do not confuse it with the user's diary."
    elif canonical == "gemini":
        warning = "[EXTERNAL_ASSISTANT] This is a Gemini conversation record; do not treat Gemini's words as the user's words."
    elif canonical == "diary":
        warning = "[USER_DIARY] This is the user's diary/source record."
    else:
        warning = "[RAW_MEMORY] This is a raw memory source and still needs phase 2 judgment."

    lines = [warning, title, "--- source records start ---"]
    for record in records:
        content = str(record.get("content") or "").strip()
        if not content:
            continue
        if return_role:
            lines.append(f"[{_role_label(record.get('role'), canonical)}]: {content}")
        else:
            lines.append(content)

    if len(lines) == 3:
        return f"{title}\nNo readable content was found in matched records.", [target]
    return "\n\n".join(lines).strip(), [target]


def _cosine_similarity(v1, v2) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


def _result_data(result):
    if hasattr(result, "data"):
        return result.data()
    return list(result or [])


def _compact_text(text, limit=180) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "").strip())
    normalized = re.sub(
        r"\s*(?:item searched|searched item)\s*$",
        "",
        normalized,
        flags=re.IGNORECASE,
    ).strip()
    normalized = normalized.strip(" -|")
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "..."


def _source_type_from_labels(labels, role="") -> str:
    label_set = {str(label).strip() for label in (labels or []) if str(label).strip()}
    if "Diary" in label_set:
        return "Diary"
    if "GeminiChat" in label_set:
        return "GeminiChat"
    if "SongryeonChat" in label_set or "SongRyeonChat" in label_set:
        return "SongRyeonChat"
    if str(role).strip() == "assistant":
        return "SongRyeonChat"
    if str(role).strip() == "user":
        return "UserChat"
    return "PastRecord"


def _merge_search_hits(*hit_groups):
    merged = []
    seen = set()
    for group in hit_groups:
        for item in group or []:
            if not isinstance(item, dict):
                continue
            key = (
                str(item.get("node_id") or "").strip(),
                str(item.get("date") or "").strip(),
                _compact_text(item.get("content") or "", limit=80),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    merged.sort(key=lambda row: float(row.get("score") or 0.0), reverse=True)
    return merged


def _default_embedding_provider(keyword: str) -> dict[str, list[float]]:
    query_vectors = {}
    for model_name in ("mxbai-embed-large", "nomic-embed-text"):
        try:
            response = ollama.embeddings(model=model_name, prompt=keyword)
            embedding = response.get("embedding")
            if isinstance(embedding, list) and embedding:
                query_vectors[model_name] = embedding
        except Exception:
            continue
    return query_vectors


def search_memory(
    keyword: str,
    *,
    session_factory: Callable | None = None,
    embedding_provider: Callable[[str], dict[str, list[float]]] | None = None,
) -> tuple[str, list[str]]:
    """Search raw Neo4j PastRecord nodes without topic-specific classification."""
    keyword = str(keyword or "").strip()
    if not keyword:
        return "Search keyword is empty.", []

    session_factory = session_factory or neo4j_connection.get_db_session
    embedding_provider = embedding_provider or _default_embedding_provider

    try:
        query_vectors = embedding_provider(keyword) or {}
    except Exception as exc:
        return f"Memory search embedding failed: {exc}", []

    raw_hits = []
    chunk_hits = []
    lexical_hits = []

    try:
        with session_factory() as session:
            if "mxbai-embed-large" in query_vectors:
                try:
                    chunk_hits = _result_data(
                        session.run(
                            """
                            CALL db.index.vector.queryNodes('past_record_chunk_embedding', 8, $query_vector)
                            YIELD node, score
                            WHERE score >= 0.30
                            MATCH (record:PastRecord)-[:HAS_CHUNK]->(node)
                            RETURN elementId(record) AS node_id,
                                   labels(record) AS labels,
                                   coalesce(record.date, node.date, '') AS date,
                                   coalesce(record.role, node.role, '') AS role,
                                   coalesce(node.text, record.content, '') AS content,
                                   score,
                                   elementId(node) AS chunk_id,
                                   coalesce(node.chunk_index, 0) AS chunk_index
                            ORDER BY score DESC LIMIT 8
                            """,
                            query_vector=query_vectors["mxbai-embed-large"],
                        )
                    )
                except Exception:
                    chunk_hits = []

            if "mxbai-embed-large" in query_vectors and not chunk_hits:
                try:
                    raw_hits = _result_data(
                        session.run(
                            """
                            CALL db.index.vector.queryNodes('past_record_embedding', 6, $query_vector)
                            YIELD node, score
                            WHERE score >= 0.30
                            RETURN elementId(node) AS node_id,
                                   labels(node) AS labels,
                                   coalesce(node.date, '') AS date,
                                   coalesce(node.role, '') AS role,
                                   coalesce(node.content, '') AS content,
                                   score
                            ORDER BY score DESC LIMIT 6
                            """,
                            query_vector=query_vectors["mxbai-embed-large"],
                        )
                    )
                except Exception:
                    raw_hits = []

            if not chunk_hits and not raw_hits and query_vectors:
                try:
                    rows = _result_data(
                        session.run(
                            """
                            MATCH (p:PastRecord)
                            WHERE p.embedding IS NOT NULL AND size(p.embedding) > 0
                            RETURN elementId(p) AS node_id,
                                   labels(p) AS labels,
                                   coalesce(p.date, '') AS date,
                                   coalesce(p.role, '') AS role,
                                   coalesce(p.content, '') AS content,
                                   p.embedding AS embedding
                            ORDER BY coalesce(p.date, '') DESC
                            LIMIT 600
                            """
                        )
                    )
                    scored_rows = []
                    for row in rows:
                        embedding = row.get("embedding")
                        if not isinstance(embedding, list) or not embedding:
                            continue
                        best_score = max(
                            (
                                _cosine_similarity(query_vector, embedding)
                                for query_vector in query_vectors.values()
                                if len(query_vector) == len(embedding)
                            ),
                            default=0.0,
                        )
                        if best_score < 0.28:
                            continue
                        scored_rows.append(
                            {
                                "node_id": row.get("node_id"),
                                "labels": row.get("labels") or [],
                                "date": row.get("date") or "",
                                "role": row.get("role") or "",
                                "content": row.get("content") or "",
                                "score": best_score,
                            }
                        )
                    scored_rows.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
                    raw_hits = scored_rows[:6]
                except Exception:
                    raw_hits = []

            try:
                lexical_hits = _result_data(
                    session.run(
                        """
                        MATCH (p:PastRecord)
                        WHERE toLower(coalesce(p.content, '')) CONTAINS toLower($keyword)
                        RETURN elementId(p) AS node_id,
                               labels(p) AS labels,
                               coalesce(p.date, '') AS date,
                               coalesce(p.role, '') AS role,
                               coalesce(p.content, '') AS content,
                               0.999 AS score
                        ORDER BY coalesce(p.date, '') DESC
                        LIMIT 4
                        """,
                        keyword=keyword,
                    )
                )
            except Exception:
                lexical_hits = []
    except Exception as exc:
        return f"Root memory search failed: {exc}", []

    hits = _merge_search_hits(chunk_hits, raw_hits, lexical_hits)[:6]
    hits = [hit for hit in hits if _compact_text(hit.get("content") or "", limit=20)]
    if not hits:
        return f"No raw memory record was found for '{keyword}'.", []

    lines = [f"Root-first memory search results for '{keyword}':", ""]
    found_dates = []
    for row in hits:
        source_type = _source_type_from_labels(row.get("labels") or [], row.get("role") or "")
        source_date = str(row.get("date") or "").strip() or "unknown-date"
        score = float(row.get("score") or 0.0)
        summary = _compact_text(row.get("content") or "", limit=180)
        lines.append(f"[source: {source_type}|{source_date}] (score: {score:.3f})")
        lines.append(f"snippet: {summary}")
        lines.append("-" * 30)
        if source_date != "unknown-date":
            found_dates.append(source_date)

    return "\n".join(lines).strip(), list(dict.fromkeys(found_dates))


def scroll_chat_log(
    target_id: str,
    direction: str = "both",
    limit: int = 15,
    *,
    session_factory: Callable | None = None,
) -> tuple[str, list[str]]:
    """Read records around a Neo4j NEXT-chain anchor."""
    try:
        safe_limit = max(1, min(int(limit), 30))
    except Exception:
        safe_limit = 15

    normalized_direction = str(direction or "both").strip().lower()
    if normalized_direction not in {"past", "future", "both"}:
        normalized_direction = "both"

    raw_target = str(target_id or "").strip()
    if not raw_target:
        return "Scroll failed: target_id is empty.", []

    alt_id = _alternate_date_id(raw_target)
    query = f"""
    MATCH (target)
    WHERE trim(coalesce(target.id, '')) = $t_id OR trim(coalesce(target.id, '')) = $a_id
       OR trim(coalesce(target.date, '')) = $t_id OR trim(coalesce(target.date, '')) = $a_id
       OR elementId(target) = $t_id OR elementId(target) = $a_id
    CALL (target) {{
        MATCH (prev)-[:NEXT*1..{safe_limit}]->(target)
        WHERE $direction IN ['past', 'both']
        RETURN prev AS node, "context_before" AS tag
        UNION
        RETURN target AS node, "target_hit" AS tag
        UNION
        MATCH (target)-[:NEXT*1..{safe_limit}]->(next)
        WHERE $direction IN ['future', 'both']
        RETURN next AS node, "context_after" AS tag
    }}
    RETURN coalesce(node.id, node.date, elementId(node)) AS id,
           coalesce(node.role, 'unknown') AS speaker,
           coalesce(node.content, '') AS content,
           tag
    ORDER BY coalesce(node.date, node.id, elementId(node), "") ASC
    """

    session_factory = session_factory or neo4j_connection.get_db_session
    try:
        with session_factory() as session:
            rows = _result_data(
                session.run(
                    query,
                    t_id=raw_target,
                    a_id=alt_id,
                    direction=normalized_direction,
                )
            )
    except Exception as exc:
        return f"Scroll failed: {exc}", []

    if not rows:
        return f"Scroll failed: anchor '{target_id}' was not found.", []

    exact_ids = []
    before_rows = []
    anchor_rows = []
    after_rows = []
    for row in rows:
        node_id = str(row.get("id") or "").strip()
        if node_id and node_id not in exact_ids:
            exact_ids.append(node_id)
        bucket = str(row.get("tag") or "").strip()
        if bucket == "context_before":
            before_rows.append(row)
        elif bucket == "target_hit":
            anchor_rows.append(row)
        elif bucket == "context_after":
            after_rows.append(row)

    lines = [
        "[context scroll result]",
        f"anchor: {target_id}",
        f"direction: {normalized_direction} | limit: {safe_limit}",
        "",
    ]
    if anchor_rows:
        lines.append("[anchor]")
        for idx, row in enumerate(anchor_rows[:3], start=1):
            lines.append(
                f"{idx}. [{row.get('id')}] {row.get('speaker')}: {_compact_text(row.get('content'), 220)}"
            )
        lines.append("")
    if before_rows:
        lines.append(f"[before {len(before_rows)}]")
        for idx, row in enumerate(before_rows[-safe_limit:], start=1):
            lines.append(
                f"{idx}. [{row.get('id')}] {row.get('speaker')}: {_compact_text(row.get('content'), 180)}"
            )
        lines.append("")
    if after_rows:
        lines.append(f"[after {len(after_rows)}]")
        for idx, row in enumerate(after_rows[:safe_limit], start=1):
            lines.append(
                f"{idx}. [{row.get('id')}] {row.get('speaker')}: {_compact_text(row.get('content'), 180)}"
            )
        lines.append("")

    return "\n".join(lines).strip(), exact_ids


def scan_db_schema(*, session_factory: Callable | None = None) -> tuple[str, list[str]]:
    """Inspect current Neo4j schema labels, relationship types, and property keys."""
    query_labels = "CALL db.labels() YIELD label RETURN collect(label) AS labels"
    query_rels = "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS rels"
    query_props = "CALL db.propertyKeys() YIELD propertyKey RETURN collect(propertyKey) AS props"

    session_factory = session_factory or neo4j_connection.get_db_session
    try:
        with session_factory() as session:
            labels = session.run(query_labels).single()["labels"]
            rels = session.run(query_rels).single()["rels"]
            props = session.run(query_props).single()["props"]
    except Exception as exc:
        return f"DB schema scan failed: {exc}", []

    safe_props = (props or [])[:30]
    result = (
        "[live DB schema scan]\n"
        f"1. node labels: {labels or []}\n"
        f"2. relationship types: {rels or []}\n"
        f"3. property keys: {safe_props}..."
    )
    return result, []


__all__ = [
    "normalize_source_type",
    "read_full_source",
    "scan_db_schema",
    "scroll_chat_log",
    "search_memory",
]
