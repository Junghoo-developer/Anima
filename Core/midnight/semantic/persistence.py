"""Graph persistence for the V4 semantic-axis government."""

from __future__ import annotations

import hashlib
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from .contracts import ConceptClusterSpec, SemanticBranchSpec

NIGHT_GOVERNMENT_KEY = "night_government_v1"
R8_CREATED_BY = "v4_r8_semantic_government"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _safe_slug(value: Any) -> str:
    text = _norm(value).lower()
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-", "/"} else "_" for ch in text).strip("_")
    if cleaned:
        return cleaned[:120]
    return hashlib.sha1(_norm(value).encode("utf-8")).hexdigest()[:16]


def _stable_key(prefix: str, *parts: Any) -> str:
    material = "\n".join(_norm(part) for part in parts).encode("utf-8")
    return f"{prefix}::" + hashlib.sha1(material).hexdigest()[:16]


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def build_semantic_branch_spec(
    *,
    branch_path: str,
    title: str = "",
    summary: str = "",
    parent_branch_path: str = "",
    embedding: list[float] | None = None,
    created_by: str = R8_CREATED_BY,
) -> SemanticBranchSpec:
    path = _norm(branch_path)
    if not path:
        raise ValueError("SemanticBranch.branch_path is required")
    return SemanticBranchSpec(
        branch_path=path,
        title=_norm(title) or path.rsplit("/", 1)[-1],
        summary=_norm(summary),
        parent_branch_path=_norm(parent_branch_path),
        embedding=list(embedding or []),
        created_by=_norm(created_by) or R8_CREATED_BY,
    )


def build_concept_cluster_spec(
    *,
    branch_path: str,
    title: str,
    summary: str = "",
    facts: list[str] | None = None,
    source_refs: list[str] | None = None,
    source_persona: str = "system",
    cluster_key: str | None = None,
) -> ConceptClusterSpec:
    path = _norm(branch_path)
    clean_title = _norm(title)
    persona = _norm(source_persona)
    if not path:
        raise ValueError("ConceptCluster.branch_path is required")
    if not clean_title:
        raise ValueError("ConceptCluster.title is required")
    if not persona:
        raise ValueError("ConceptCluster.source_persona is required")
    return ConceptClusterSpec(
        cluster_key=_norm(cluster_key) or _stable_key("concept_cluster", path, clean_title),
        branch_path=path,
        title=clean_title,
        summary=_norm(summary),
        facts=[_norm(item) for item in list(facts or []) if _norm(item)],
        source_refs=[_norm(item) for item in list(source_refs or []) if _norm(item)],
        source_persona=persona,
    )


def persist_semantic_branch(
    session: Any,
    branch: SemanticBranchSpec | Mapping[str, Any],
    *,
    coreego_name: str = "SongRyeon",
    graph_operations_log: list | None = None,
) -> dict[str, Any]:
    payload = _as_dict(branch)
    spec = build_semantic_branch_spec(**payload)
    session.run(
        """
        MERGE (ce:CoreEgo {name: $coreego_name})
        MERGE (sb:SemanticBranch {governor_key: $governor_key, branch_path: $branch_path})
        SET sb.title = $title,
            sb.summary = $summary,
            sb.parent_branch_path = $parent_branch_path,
            sb.embedding = coalesce(sb.embedding, $embedding),
            sb.created_at = coalesce(sb.created_at, toInteger($created_at)),
            sb.updated_at = timestamp(),
            sb.created_by = coalesce(sb.created_by, $created_by)
        MERGE (ce)-[:HAS_SEMANTIC_BRANCH]->(sb)
        """,
        coreego_name=coreego_name,
        governor_key=NIGHT_GOVERNMENT_KEY,
        branch_path=spec.branch_path,
        title=spec.title,
        summary=spec.summary,
        parent_branch_path=spec.parent_branch_path,
        embedding=spec.embedding,
        created_at=int(time.time() * 1000),
        created_by=R8_CREATED_BY,
    )
    if spec.parent_branch_path:
        session.run(
            """
            MATCH (parent:SemanticBranch {governor_key: $governor_key, branch_path: $parent_branch_path})
            MATCH (child:SemanticBranch {governor_key: $governor_key, branch_path: $branch_path})
            MERGE (parent)-[:HAS_CHILD_SEMANTIC_BRANCH]->(child)
            """,
            governor_key=NIGHT_GOVERNMENT_KEY,
            parent_branch_path=spec.parent_branch_path,
            branch_path=spec.branch_path,
        )
    if isinstance(graph_operations_log, list):
        graph_operations_log.append({"operation": "persist_semantic_branch", "branch_path": spec.branch_path})
    return asdict(spec)


def persist_concept_cluster(
    session: Any,
    cluster: ConceptClusterSpec | Mapping[str, Any],
    *,
    graph_operations_log: list | None = None,
) -> dict[str, Any]:
    payload = _as_dict(cluster)
    spec = build_concept_cluster_spec(**payload)
    session.run(
        """
        MERGE (cc:ConceptCluster {cluster_key: $cluster_key})
        SET cc.title = $title,
            cc.summary = $summary,
            cc.facts = $facts,
            cc.source_refs = $source_refs,
            cc.source_persona = $source_persona,
            cc.updated_at = timestamp(),
            cc.created_at = coalesce(cc.created_at, toInteger($created_at)),
            cc.created_by = coalesce(cc.created_by, $created_by)
        MERGE (sb:SemanticBranch {governor_key: $governor_key, branch_path: $branch_path})
        MERGE (sb)-[:CURATES]->(cc)
        """,
        cluster_key=spec.cluster_key,
        title=spec.title,
        summary=spec.summary,
        facts=spec.facts,
        source_refs=spec.source_refs,
        source_persona=spec.source_persona,
        governor_key=NIGHT_GOVERNMENT_KEY,
        branch_path=spec.branch_path,
        created_at=int(time.time() * 1000),
        created_by=R8_CREATED_BY,
    )
    for source_ref in spec.source_refs:
        session.run(
            """
            MATCH (cc:ConceptCluster {cluster_key: $cluster_key})
            MERGE (src:SemanticSourceRef {source_id: $source_id})
            MERGE (cc)-[:CITES_SEMANTIC_SOURCE]->(src)
            """,
            cluster_key=spec.cluster_key,
            source_id=source_ref,
        )
    if isinstance(graph_operations_log, list):
        graph_operations_log.append({"operation": "persist_concept_cluster", "cluster_key": spec.cluster_key})
    return asdict(spec)


def persist_timebucket_bridge(
    session: Any,
    *,
    semantic_branch_path: str,
    time_bucket_key: str,
    graph_operations_log: list | None = None,
) -> dict[str, str]:
    branch = _norm(semantic_branch_path)
    bucket = _norm(time_bucket_key)
    if not branch or not bucket:
        raise ValueError("semantic_branch_path and time_bucket_key are required")
    session.run(
        """
        MERGE (sb:SemanticBranch {governor_key: $governor_key, branch_path: $semantic_branch_path})
        MERGE (tb:TimeBucket {bucket_key: $time_bucket_key})
        SET tb.updated_at = timestamp()
        MERGE (sb)-[:OBSERVES_TIME_BUCKET]->(tb)
        """,
        governor_key=NIGHT_GOVERNMENT_KEY,
        semantic_branch_path=branch,
        time_bucket_key=bucket,
    )
    if isinstance(graph_operations_log, list):
        graph_operations_log.append({"operation": "persist_timebucket_bridge", "branch_path": branch, "time_bucket": bucket})
    return {"semantic_branch_path": branch, "time_bucket_key": bucket}


def semantic_branch_path_for_text(text: Any, *, root: str = "CoreEgo/Semantic") -> str:
    tokens = [token for token in re_split_tokens(_norm(text)) if token]
    head = tokens[0] if tokens else _safe_slug(text)
    return f"{root}/{_safe_slug(head)}"


def re_split_tokens(text: str) -> list[str]:
    import re

    return re.findall(r"[0-9A-Za-z가-힣_]+", text.lower())
