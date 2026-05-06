"""Semantic CoreEgo designer.

This module revives the useful idea from the archived REMGovernor: keep a
root-level inventory and branch-health view. It does not revive old policy
routing or doctrine generation.
"""

from __future__ import annotations

from typing import Any, Mapping

ARCHIVE_REVIVAL_SOURCES = [
    "Core/_archive_v3_midnight/rem_governor.py::root_inventory",
    "Core/_archive_v3_midnight/branch_architect.py::branch_blueprints",
]


def _norm(value: Any) -> str:
    return str(value or "").strip()


def design_semantic_coreego(
    *,
    coreego_name: str = "SongRyeon",
    semantic_branches: list[Mapping[str, Any]] | None = None,
    concept_clusters: list[Mapping[str, Any]] | None = None,
    night_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = dict(night_context or {})
    branches = list(semantic_branches if semantic_branches is not None else context.get("semantic_branches", []) or [])
    clusters = list(concept_clusters if concept_clusters is not None else context.get("concept_clusters", []) or [])
    branch_paths = []
    for item in branches:
        if isinstance(item, Mapping) and _norm(item.get("branch_path")):
            branch_paths.append(_norm(item.get("branch_path")))
    cluster_keys = []
    for item in clusters:
        if isinstance(item, Mapping) and _norm(item.get("cluster_key")):
            cluster_keys.append(_norm(item.get("cluster_key")))
    return {
        "role": "semantic_coreego_designer",
        "axis": "semantic",
        "status": "read_only_inventory",
        "coreego_name": _norm(coreego_name) or "SongRyeon",
        "semantic_branch_count": len(branch_paths),
        "concept_cluster_count": len(cluster_keys),
        "branch_paths": list(dict.fromkeys(branch_paths))[:24],
        "cluster_keys": list(dict.fromkeys(cluster_keys))[:24],
        "archive_revival_sources": ARCHIVE_REVIVAL_SOURCES,
        "scope_note": "Revived archive inventory concept only; old routing policy remains retired.",
    }


__all__ = ["ARCHIVE_REVIVAL_SOURCES", "design_semantic_coreego"]
