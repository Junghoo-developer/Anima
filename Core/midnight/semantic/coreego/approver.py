"""Semantic CoreEgo approval seat."""

from __future__ import annotations

from typing import Any, Mapping

from Core.midnight.past.coreego_assembly import approve_coreego


def approve_semantic_coreego(
    *,
    self_packet: Mapping[str, Any] | None = None,
    local_reports: list[dict[str, Any]] | None = None,
    election_rounds: int = 0,
) -> dict[str, Any]:
    packet = dict(self_packet or {})
    proposal = packet.get("change_proposal") if isinstance(packet.get("change_proposal"), Mapping) else {}
    proposal = dict(proposal or {})
    proposal["axis"] = "semantic"
    approved = approve_coreego(
        change_proposal=proposal,
        local_reports=local_reports,
        election_rounds=election_rounds,
    )
    return {
        "role": "semantic_coreego_approver",
        "axis": "semantic",
        "status": "approved" if approved.election_result else "rejected",
        "election_result": approved.election_result,
        "election_rounds": approved.election_rounds,
        "change_proposal": approved.change_proposal,
        "semantic_thought": approved.past_assembly_thought,
    }


__all__ = ["approve_semantic_coreego"]
