"""Contracts for the V4 present department."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PresentSecondDreamOutput:
    """Filled SecondDream packet consumed by the past/future departments."""

    seconddream_key: str
    summary: str
    problems: list[Any] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SecondDreamSummary:
    seconddream_key: str
    branch_path: str
    summary: str
    source_persona: str
    source_dream_keys: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SecondDreamProblems:
    seconddream_key: str
    supply_topics: list[str] = field(default_factory=list)
    field_loop_problems: list[str] = field(default_factory=list)
    source_persona: str = ""


@dataclass(frozen=True)
class SecondDreamAudit:
    seconddream_key: str
    verified: bool
    source_persona: str
    citations: list[str] = field(default_factory=list)
    rejected_claims: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
