"""Future decision-maker node for the V4 midnight government."""

from __future__ import annotations

from typing import Any, Mapping


def _recall_refs(critic_packet: Mapping[str, Any]) -> list[str]:
    recall = critic_packet.get("random_recall") if isinstance(critic_packet.get("random_recall"), Mapping) else {}
    refs: list[str] = []
    for item in list(recall.get("results", []) or []):
        if not isinstance(item, Mapping):
            continue
        source_id = str(item.get("source_id") or item.get("id") or item.get("key") or "")
        if source_id and source_id not in refs:
            refs.append(source_id)
    return refs


def make_future_decision(
    *,
    witness_packet: Mapping[str, Any] | None = None,
    critic_packet: Mapping[str, Any] | None = None,
    source_persona: str | None = None,
    branch_path: str = "TimeBranch/future",
    night_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Approve a DreamHint or remand the future cycle for more critique."""
    context = dict(night_context or {})
    witness = dict(witness_packet or context.get("witness_packet") or {})
    critic = dict(critic_packet or context.get("critic_packet") or {})
    blocking_gaps = list(critic.get("blocking_gaps", []) or [])
    persona = str(source_persona or context.get("source_persona") or "").strip()
    if blocking_gaps:
        return {
            "role": "future_decision_maker",
            "status": "rejected",
            "decision": "remand",
            "remand_target": "field_critic",
            "feedback": "Resolve blocking gaps before issuing a DreamHint.",
            "blocking_gaps": blocking_gaps,
            "next_node": "field_critic",
        }
    if not persona:
        return {
            "role": "future_decision_maker",
            "status": "rejected",
            "decision": "remand",
            "remand_target": "field_critic",
            "feedback": "DreamHint requires non-empty source_persona.",
            "blocking_gaps": ["source_persona_missing"],
            "next_node": "field_critic",
        }
    hint_text = " / ".join(
        part
        for part in [
            str(witness.get("witness_summary") or ""),
            str(critic.get("critique_summary") or ""),
        ]
        if part
    ) or "Future department approved an advisory DreamHint."
    past_ref = str(witness.get("past_assembly_thought") or "")
    dreamhint = {
        "hint_text": hint_text,
        "source_persona": persona,
        "branch_path": str(branch_path or "TimeBranch/future"),
        "cites_past_thought": [past_ref] if past_ref else [],
        "recall_result_refs": _recall_refs(critic),
        "expires_at": None,
    }
    return {
        "role": "future_decision_maker",
        "status": "approved",
        "decision": "approve",
        "dreamhint": dreamhint,
        "next_node": "dreamhint_persistence",
    }
