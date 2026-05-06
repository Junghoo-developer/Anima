"""Contracts for the V4 semantic-axis night government."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SemanticBranchSpec:
    branch_path: str
    title: str
    summary: str = ""
    parent_branch_path: str = ""
    embedding: list[float] = field(default_factory=list)
    created_by: str = "v4_r8_semantic_government"


@dataclass(frozen=True)
class ConceptClusterSpec:
    cluster_key: str
    branch_path: str
    title: str
    summary: str = ""
    facts: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    source_persona: str = "system"


@dataclass(frozen=True)
class SemanticAssemblyOutput:
    axis: str = "semantic"
    coreego_name: str = "SongRyeon"
    semantic_thought: str = ""
    branch_specs: list[SemanticBranchSpec] = field(default_factory=list)
    concept_clusters: list[ConceptClusterSpec] = field(default_factory=list)
    change_proposal: dict[str, Any] = field(default_factory=dict)
    election_result: bool = True
    election_rounds: int = 0

