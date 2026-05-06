"""Semantic CoreEgo self seat."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from Core.midnight.past.contracts import empty_change_proposal

from ..contracts import ConceptClusterSpec, SemanticBranchSpec
from ..persistence import build_concept_cluster_spec, build_semantic_branch_spec, semantic_branch_path_for_text


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _candidate_text(item: Any) -> str:
    if isinstance(item, Mapping):
        return _norm(item.get("summary") or item.get("text") or item.get("title") or item.get("hint_text") or item)
    return _norm(item)


def propose_semantic_branches(
    *,
    recall_results: list[Mapping[str, Any]] | None = None,
    design_packet: Mapping[str, Any] | None = None,
    source_persona: str = "semantic_coreego_self",
    max_branches: int = 6,
) -> dict[str, Any]:
    """Create free SemanticBranch candidates from recall material."""
    design = dict(design_packet or {})
    branch_specs: list[SemanticBranchSpec] = []
    cluster_specs: list[ConceptClusterSpec] = []
    for idx, item in enumerate(list(recall_results or []), start=1):
        text = _candidate_text(item)
        if not text:
            continue
        branch_path = _norm(item.get("branch_path")) if isinstance(item, Mapping) else ""
        if not branch_path:
            branch_path = semantic_branch_path_for_text(text)
        branch_specs.append(
            build_semantic_branch_spec(
                branch_path=branch_path,
                title=_norm(item.get("title") if isinstance(item, Mapping) else "") or branch_path.rsplit("/", 1)[-1],
                summary=text[:500],
                parent_branch_path=_norm(item.get("parent_branch_path") if isinstance(item, Mapping) else ""),
            )
        )
        source_id = _norm(item.get("source_id") if isinstance(item, Mapping) else "") or f"semantic_source::{idx}"
        cluster_specs.append(
            build_concept_cluster_spec(
                branch_path=branch_path,
                title=_norm(item.get("title") if isinstance(item, Mapping) else "") or f"Concept cluster {idx}",
                summary=text[:500],
                facts=[text],
                source_refs=[source_id],
                source_persona=_norm(item.get("source_persona") if isinstance(item, Mapping) else "") or source_persona,
            )
        )
        if len(branch_specs) >= max_branches:
            break
    proposal = empty_change_proposal()
    proposal.update(
        {
            "axis": "semantic",
            "target_node_id": f"CoreEgo:{design.get('coreego_name', 'SongRyeon')}",
            "attr_name": "semantic_branch_candidates",
            "new_value": [asdict(item) for item in branch_specs],
            "rationale": {
                "summary": "Semantic CoreEgo proposed free SemanticBranch candidates from recall material.",
                "evidence_keys": [ref for cluster in cluster_specs for ref in cluster.source_refs],
                "sources": [cluster.cluster_key for cluster in cluster_specs],
            },
            "importance": {
                "score": 0.6 if branch_specs else 0.2,
                "sources": [cluster.cluster_key for cluster in cluster_specs],
            },
        }
    )
    return {
        "role": "semantic_coreego_self",
        "axis": "semantic",
        "branch_specs": branch_specs,
        "concept_clusters": cluster_specs,
        "change_proposal": proposal,
        "semantic_thought": f"Semantic self proposed {len(branch_specs)} branch candidate(s).",
    }


__all__ = ["propose_semantic_branches"]
