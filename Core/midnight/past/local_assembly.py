"""Local council assembly for the V4 past department."""

from __future__ import annotations

from typing import Any, Mapping


def _summary(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("summary") or item.get("content") or item.get("second_dream_summary") or "")
    return str(item or "")


def assemble_local_council(
    *,
    council_key: str = "TimeBranch/local",
    branch_path: str = "TimeBranch/local",
    subordinate_second_dreams: list[Any] | None = None,
    change_proposal: Mapping[str, Any] | None = None,
    election_depth: int = 1,
    night_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = dict(night_context or {})
    dreams = list(subordinate_second_dreams if subordinate_second_dreams is not None else context.get("subordinate_second_dreams", []) or [])
    proposal = dict(change_proposal or context.get("change_proposal") or {})
    summaries = [_summary(item) for item in dreams]
    summaries = [summary for summary in summaries if summary]
    target = str(proposal.get("target_node_id") or proposal.get("target") or "")
    branch = str(branch_path or context.get("branch_path") or "TimeBranch/local")
    vote = bool(not target or target in branch or summaries)
    return {
        "role": "local_council",
        "council_key": str(council_key or context.get("council_key") or branch),
        "branch_path": branch,
        "designer_status": "read_only_foundation",
        "submission_summary": " / ".join(summaries[:4]) or "No subordinate SecondDream material was supplied.",
        "vote": "yes" if vote else "no",
        "supports_change": vote,
        "election_depth": int(election_depth),
        "handoff_target": "coreego_council",
    }
