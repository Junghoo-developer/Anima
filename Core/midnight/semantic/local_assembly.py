"""SemanticBranch local council."""

from __future__ import annotations

from typing import Any, Mapping


def assemble_semantic_local_council(
    *,
    branch_path: str,
    concept_clusters: list[Mapping[str, Any]] | None = None,
    vote: bool = True,
) -> dict[str, Any]:
    clusters = list(concept_clusters or [])
    return {
        "role": "semantic_local_council",
        "axis": "semantic",
        "council_key": f"semantic_council::{branch_path}",
        "branch_path": str(branch_path or "CoreEgo/Semantic"),
        "submission_summary": f"Semantic local council reviewed {len(clusters)} ConceptCluster item(s).",
        "vote": bool(vote),
        "cluster_keys": [
            str(item.get("cluster_key"))
            for item in clusters
            if isinstance(item, Mapping) and item.get("cluster_key")
        ],
    }


__all__ = ["assemble_semantic_local_council"]
