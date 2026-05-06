"""Contracts for the V4 past department."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PastAssemblyOutput:
    """Output consumed by the future department after R4."""

    past_assembly_thought: str
    election_result: bool
    change_proposal: dict[str, Any] = field(default_factory=dict)
    election_rounds: int = 0


def empty_change_proposal() -> dict[str, Any]:
    return {
        "proposal_key": "",
        "target_node_id": "",
        "attr_name": "",
        "old_value": None,
        "new_value": None,
        "rationale": {
            "summary": "",
            "evidence_keys": [],
            "sources": [],
        },
        "importance": {
            "score": 0.0,
            "sources": [],
        },
    }
