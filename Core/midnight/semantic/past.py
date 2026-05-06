"""Semantic past seat."""

from __future__ import annotations

from typing import Any, Mapping


def build_semantic_past(
    *,
    branch_specs: list[Mapping[str, Any]] | None = None,
    concept_clusters: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    branches = list(branch_specs or [])
    clusters = list(concept_clusters or [])
    return {
        "role": "semantic_past",
        "axis": "semantic",
        "summary": f"Semantic past reviewed {len(branches)} branch candidate(s) and {len(clusters)} concept cluster(s).",
        "branch_count": len(branches),
        "cluster_count": len(clusters),
    }


__all__ = ["build_semantic_past"]
