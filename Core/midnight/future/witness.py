"""Future witness node for the V4 midnight government."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from Core.midnight.past.contracts import PastAssemblyOutput

from .contracts import PastAssemblyMockInput


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def build_future_witness(
    *,
    past_input: PastAssemblyOutput | PastAssemblyMockInput | Mapping[str, Any] | None = None,
    previous_decision_thought: str = "",
    night_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize past thought and hand the future cycle to the field critic."""
    context = dict(night_context or {})
    past = _as_dict(past_input) or _as_dict(context.get("past_input"))
    prior = str(
        previous_decision_thought
        or context.get("previous_decision_thought")
        or context.get("previous_future_decision")
        or ""
    )
    past_thought = str(past.get("past_assembly_thought") or "")
    change_proposal = past.get("change_proposal") if isinstance(past.get("change_proposal"), dict) else {}
    election_result = bool(past.get("election_result", False))
    summary_parts = [
        part
        for part in [
            f"past: {past_thought}" if past_thought else "",
            f"prior_future_decision: {prior}" if prior else "",
            f"change_proposal_keys: {', '.join(sorted(change_proposal))}" if change_proposal else "",
        ]
        if part
    ]
    return {
        "role": "future_witness",
        "status": "ready",
        "past_assembly_thought": past_thought,
        "previous_decision_thought": prior,
        "election_result": election_result,
        "change_proposal": change_proposal,
        "witness_summary": " | ".join(summary_parts) if summary_parts else "No past/future thought supplied yet.",
        "next_node": "field_critic",
    }
