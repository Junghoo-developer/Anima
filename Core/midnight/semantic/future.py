"""Semantic future seat."""

from __future__ import annotations

from typing import Any, Mapping


def build_semantic_future(
    *,
    approval_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    approval = dict(approval_packet or {})
    return {
        "role": "semantic_future",
        "axis": "semantic",
        "status": "advisory_ready" if approval.get("election_result") else "needs_revision",
        "hint_text": "Semantic branches are ready for future advisory use."
        if approval.get("election_result")
        else "Semantic branch proposal needs another pass.",
        "change_proposal": approval.get("change_proposal", {}),
    }


__all__ = ["build_semantic_future"]
