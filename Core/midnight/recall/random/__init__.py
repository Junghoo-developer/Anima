"""Random-recall department for the V4 midnight government.

This is the first executable recall algorithm: it gathers candidate memory
records from injected sources or a Neo4j-like session, ranks them with cosine
similarity, and preserves persona/provenance for later LLM seats.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class RandomRecallResult:
    results: list[dict[str, Any]] = field(default_factory=list)
    source_persona_map: dict[str, str] = field(default_factory=dict)
    query: str = ""
    persona_filter: str | None = None
    axis: str = "time"


@dataclass(frozen=True)
class RandomFormatterOutput:
    formatted_items: list[dict[str, Any]] = field(default_factory=list)
    source_persona_map: dict[str, str] = field(default_factory=dict)
    source_persona: str = "system"
    query: str = ""


@dataclass(frozen=True)
class RandomAuditorOutput:
    audited_items: list[dict[str, Any]] = field(default_factory=list)
    source_persona: str = "system"
    citations: list[str] = field(default_factory=list)
    rejected_items: list[dict[str, Any]] = field(default_factory=list)


def _require_persona(source_persona: str | None) -> str:
    persona = str(source_persona or "").strip()
    if not persona:
        raise ValueError("source_persona required")
    return persona


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "data") and callable(value.data):
        return dict(value.data())
    return {}


def _rows_to_dicts(rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [_as_dict(row) for row in rows if _as_dict(row)]


def _call_fetcher(fetcher: Callable[..., Iterable[Any]], *, limit: int) -> list[dict[str, Any]]:
    try:
        rows = fetcher(limit=limit)
    except TypeError:
        rows = fetcher()
    return _rows_to_dicts(list(rows or []))


def fetch_random_sources(
    *,
    session: Any = None,
    fetcher: Callable[..., Iterable[Any]] | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Fetch Diary, SecondDream, and generic graph-memory candidates."""
    if fetcher is not None:
        return _call_fetcher(fetcher, limit=limit)
    if session is None:
        return []
    queries = [
        """
    MATCH (d:Diary)
    RETURN coalesce(d.diary_id, d.id, elementId(d)) AS source_id,
           'Diary' AS source_type,
           d.content AS text,
           d.summary AS summary,
           d.embedding AS embedding,
           d.created_at AS created_at,
           d.source_persona AS source_persona
    LIMIT $limit
    """,
        """
    MATCH (sd:SecondDream)
    RETURN coalesce(sd.seconddream_key, sd.id, elementId(sd)) AS source_id,
           'SecondDream' AS source_type,
           sd.summary AS text,
           sd.summary AS summary,
           sd.embedding AS embedding,
           sd.created_at AS created_at,
           sd.source_persona AS source_persona
    LIMIT $limit
    """,
        """
    MATCH (n)
    WHERE NOT n:Diary AND NOT n:SecondDream
    RETURN coalesce(n.key, n.id, elementId(n)) AS source_id,
           head(labels(n)) AS source_type,
           coalesce(n.summary, n.content, n.name, n.text) AS text,
           coalesce(n.summary, n.name) AS summary,
           n.embedding AS embedding,
           n.created_at AS created_at,
           n.source_persona AS source_persona
    LIMIT $limit
    """,
    ]
    rows: list[dict[str, Any]] = []
    per_query_limit = max(1, int(limit))
    for query in queries:
        rows.extend(_rows_to_dicts(session.run(query, limit=per_query_limit)))
    return rows[:per_query_limit]


def fetch_semantic_sources(
    *,
    session: Any = None,
    fetcher: Callable[..., Iterable[Any]] | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Fetch SemanticBranch and ConceptCluster candidates."""
    if fetcher is not None:
        return _call_fetcher(fetcher, limit=limit)
    if session is None:
        return []
    queries = [
        """
    MATCH (sb:SemanticBranch)
    RETURN sb.branch_path AS source_id,
           'SemanticBranch' AS source_type,
           coalesce(sb.summary, sb.title, sb.branch_path) AS text,
           coalesce(sb.title, sb.branch_path) AS summary,
           sb.embedding AS embedding,
           sb.updated_at AS created_at,
           '송련' AS source_persona,
           sb.branch_path AS branch_path
    LIMIT $limit
    """,
        """
    MATCH (cc:ConceptCluster)
    RETURN cc.cluster_key AS source_id,
           'ConceptCluster' AS source_type,
           coalesce(cc.summary, cc.title) AS text,
           cc.title AS summary,
           cc.embedding AS embedding,
           cc.updated_at AS created_at,
           cc.source_persona AS source_persona,
           cc.branch_path AS branch_path
    LIMIT $limit
    """,
    ]
    rows: list[dict[str, Any]] = []
    per_query_limit = max(1, int(limit))
    for query in queries:
        rows.extend(_rows_to_dicts(session.run(query, limit=per_query_limit)))
    return rows[:per_query_limit]


def _text_for_item(item: Mapping[str, Any]) -> str:
    return str(item.get("text") or item.get("content") or item.get("summary") or item.get("body") or item.get("name") or "")


def _source_id(item: Mapping[str, Any], fallback_index: int) -> str:
    return str(
        item.get("source_id")
        or item.get("diary_id")
        or item.get("seconddream_key")
        or item.get("node_id")
        or item.get("id")
        or item.get("key")
        or f"random_source::{fallback_index}"
    )


def _source_type(item: Mapping[str, Any]) -> str:
    raw = item.get("source_type") or item.get("label") or item.get("labels") or item.get("kind") or ""
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    return str(raw or "GraphNode")


def _persona_for_item(item: Mapping[str, Any]) -> str:
    persona = str(item.get("source_persona") or "").strip()
    if persona:
        return persona
    source_type = _source_type(item).lower()
    if "diary" in source_type:
        return "정후"
    if "seconddream" in source_type or "dream" in source_type:
        return "송련"
    if "semanticbranch" in source_type or "conceptcluster" in source_type:
        return "송련"
    return "system"


def _matches_persona_filter(item: Mapping[str, Any], persona: str, persona_filter: str | None) -> bool:
    if not persona_filter:
        return True
    needle = str(persona_filter).strip().lower()
    if not needle:
        return True
    haystack = " ".join(
        [
            persona,
            _source_type(item),
            str(item.get("source_id") or ""),
            str(item.get("kind") or ""),
        ]
    ).lower()
    return needle in haystack


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[0-9A-Za-z가-힣_]+", str(text).lower())


def _simple_embedding(text: str, *, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    tokens = _tokenize(text)
    if not tokens:
        tokens = list(str(text))
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0
    return vector


def _coerce_embedding(value: Any) -> list[float]:
    if isinstance(value, str):
        parts = [part.strip() for part in value.replace("[", "").replace("]", "").split(",")]
        values = []
        for part in parts:
            if not part:
                continue
            try:
                values.append(float(part))
            except ValueError:
                return []
        return values
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return []
    return []


def _embedding_for_text(
    text: str,
    *,
    embedding_provider: Callable[[str], Sequence[float]] | None = None,
) -> list[float]:
    if embedding_provider is not None:
        return [float(item) for item in embedding_provider(text)]
    return _simple_embedding(text)


def _embedding_for_item(
    item: Mapping[str, Any],
    *,
    embedding_provider: Callable[[str], Sequence[float]] | None = None,
) -> list[float]:
    existing = _coerce_embedding(item.get("embedding"))
    if existing:
        return existing
    return _embedding_for_text(_text_for_item(item), embedding_provider=embedding_provider)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    left_values = [float(item) for item in left]
    right_values = [float(item) for item in right]
    if not left_values or not right_values:
        return 0.0
    length = min(len(left_values), len(right_values))
    left_values = left_values[:length]
    right_values = right_values[:length]
    dot = sum(a * b for a, b in zip(left_values, right_values))
    left_norm = math.sqrt(sum(a * a for a in left_values))
    right_norm = math.sqrt(sum(b * b for b in right_values))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def invoke(
    query: str,
    persona_filter: str | None = None,
    *,
    axis: str = "time",
    top_k: int = 10,
    sources: list[Mapping[str, Any]] | None = None,
    session: Any = None,
    fetcher: Callable[..., Iterable[Any]] | None = None,
    embedding_provider: Callable[[str], Sequence[float]] | None = None,
) -> RandomRecallResult:
    """Retrieve random recall candidates with cosine similarity."""
    axis_value = str(axis or "time")
    if axis_value not in {"time", "semantic"}:
        raise NotImplementedError(f"{axis_value} axis is not implemented")
    query_text = str(query or "").strip()
    candidate_sources = (
        [dict(item) for item in sources]
        if sources is not None
        else (
            fetch_semantic_sources(session=session, fetcher=fetcher)
            if axis_value == "semantic"
            else fetch_random_sources(session=session, fetcher=fetcher)
        )
    )
    query_embedding = _embedding_for_text(query_text, embedding_provider=embedding_provider)
    scored: list[dict[str, Any]] = []
    persona_map: dict[str, str] = {}
    for idx, item in enumerate(candidate_sources, start=1):
        text = _text_for_item(item)
        if not text:
            continue
        source_id = _source_id(item, idx)
        persona = _persona_for_item(item)
        if not _matches_persona_filter(item, persona, persona_filter):
            continue
        score = cosine_similarity(query_embedding, _embedding_for_item(item, embedding_provider=embedding_provider))
        result = dict(item)
        result.update(
            {
                "source_id": source_id,
                "source_type": _source_type(item),
                "text": text,
                "source_persona": persona,
                "score": score,
            }
        )
        scored.append(result)
        persona_map[source_id] = persona
    scored.sort(key=lambda item: (float(item.get("score") or 0.0), str(item.get("created_at") or "")), reverse=True)
    trimmed = scored[: max(0, int(top_k or 0))]
    return RandomRecallResult(
        results=trimmed,
        source_persona_map={str(item["source_id"]): persona_map[str(item["source_id"])] for item in trimmed},
        query=query_text,
        persona_filter=persona_filter,
        axis=str(axis or "time"),
    )


class _Formatter:
    def format(
        self,
        raw_results: RandomRecallResult | Mapping[str, Any] | None = None,
        *,
        source_persona: str | None = "random_recall_formatter",
    ) -> RandomFormatterOutput:
        persona = _require_persona(source_persona)
        payload = _as_dict(raw_results)
        results = list(payload.get("results", []) or [])
        persona_map = dict(payload.get("source_persona_map", {}) or {})
        formatted_items: list[dict[str, Any]] = []
        for item in results:
            if not isinstance(item, Mapping):
                continue
            source_id = str(item.get("source_id") or item.get("id") or item.get("key") or "")
            formatted_items.append(
                {
                    "source_id": source_id,
                    "source_type": _source_type(item),
                    "summary": str(item.get("summary") or _text_for_item(item))[:500],
                    "score": float(item.get("score") or 0.0),
                    "source_persona": str(item.get("source_persona") or persona_map.get(source_id) or persona),
                }
            )
        return RandomFormatterOutput(
            formatted_items=formatted_items,
            source_persona_map={str(k): str(v) for k, v in persona_map.items()},
            source_persona=persona,
            query=str(payload.get("query") or ""),
        )


class _Auditor:
    def audit(
        self,
        formatter_output: RandomFormatterOutput | Mapping[str, Any] | None = None,
        *,
        source_persona: str | None = None,
    ) -> RandomAuditorOutput:
        payload = _as_dict(formatter_output)
        persona = (
            _require_persona(source_persona)
            if source_persona is not None
            else _require_persona(payload.get("source_persona") or "random_recall_auditor")
        )
        items = list(payload.get("formatted_items", []) or [])
        audited: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        citations: list[str] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            source_id = str(item.get("source_id") or "")
            if source_id:
                citations.append(source_id)
            if float(item.get("score") or 0.0) <= 0.0:
                rejected.append(dict(item))
                continue
            audited.append(
                {
                    **dict(item),
                    "audit_status": "candidate",
                    "source_persona": str(item.get("source_persona") or persona),
                }
            )
        return RandomAuditorOutput(
            audited_items=audited,
            source_persona=persona,
            citations=list(dict.fromkeys(citations)),
            rejected_items=rejected,
        )


formatter = _Formatter()
auditor = _Auditor()


def build_random_recall(
    *,
    night_context: Mapping[str, Any] | None = None,
    query: str = "",
    persona_filter: str | None = None,
    sources: list[Mapping[str, Any]] | None = None,
    session: Any = None,
    fetcher: Callable[..., Iterable[Any]] | None = None,
    top_k: int = 10,
    axis: str = "time",
) -> dict[str, Any]:
    context = dict(night_context or {})
    result = invoke(
        query or str(context.get("query") or ""),
        persona_filter=persona_filter or context.get("persona_filter"),
        axis=axis,
        top_k=top_k,
        sources=sources,
        session=session or context.get("session"),
        fetcher=fetcher,
    )
    formatted = formatter.format(result)
    audited = auditor.audit(formatted)
    return {
        "role": "random_recall",
        "status": "completed",
        "result": asdict(result),
        "formatter_output": asdict(formatted),
        "auditor_output": asdict(audited),
    }


__all__ = [
    "RandomRecallResult",
    "RandomFormatterOutput",
    "RandomAuditorOutput",
    "fetch_random_sources",
    "fetch_semantic_sources",
    "cosine_similarity",
    "formatter",
    "auditor",
    "invoke",
    "build_random_recall",
]
