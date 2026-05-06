"""CoreEgo assembly for the V4 past department."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from .contracts import PastAssemblyOutput
from .persistence import build_election_payload, normalize_change_proposal


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _dream_summary(dream: Any) -> str:
    if isinstance(dream, Mapping):
        return str(dream.get("summary") or dream.get("second_dream_summary") or dream.get("content") or "")
    return str(dream or "")


def _dream_sources(dreams: list[Any]) -> list[str]:
    sources: list[str] = []
    for dream in dreams:
        if isinstance(dream, Mapping):
            source = str(dream.get("dream_id") or dream.get("id") or dream.get("source_id") or "")
        else:
            source = ""
        if source and source not in sources:
            sources.append(source)
    return sources


def _change_proposal_from_dreams(unresolved_second_dreams: list[Any], local_submissions: list[dict[str, Any]]) -> dict[str, Any]:
    first = unresolved_second_dreams[0] if unresolved_second_dreams else {}
    first_dict = _as_dict(first)
    topic = str(first_dict.get("topic") or first_dict.get("branch_path") or first_dict.get("target") or "CoreEgo:SongRyeon").strip()
    summaries = [_dream_summary(dream) for dream in unresolved_second_dreams]
    summaries = [summary for summary in summaries if summary]
    local_notes = [
        str(item.get("submission_summary") or item.get("summary") or "")
        for item in local_submissions
        if isinstance(item, Mapping)
    ]
    local_notes = [note for note in local_notes if note]
    evidence_keys = _dream_sources(unresolved_second_dreams)
    importance_score = 0.5
    if len(unresolved_second_dreams) >= 3:
        importance_score = 0.8
    elif len(unresolved_second_dreams) == 2:
        importance_score = 0.65
    return normalize_change_proposal(
        {
            "target_node_id": topic,
            "attr_name": str(first_dict.get("attr_name") or "night_learning_note"),
            "old_value": first_dict.get("old_value"),
            "new_value": " / ".join([*summaries[:3], *local_notes[:2]]) or "Past assembly found no concrete unresolved dream.",
            "rationale": {
                "summary": "CoreEgo assembly synthesized unresolved SecondDream material and local council submissions.",
                "evidence_keys": evidence_keys,
                "sources": evidence_keys + [str(item.get("council_key")) for item in local_submissions if isinstance(item, Mapping) and item.get("council_key")],
            },
            "importance": {
                "score": importance_score,
                "sources": evidence_keys,
            },
        }
    )


def design_coreego(
    *,
    night_context: Mapping[str, Any] | None = None,
    coreego_name: str = "SongRyeon",
) -> dict[str, Any]:
    """Return a read-only CoreEgo structure snapshot.

    R4 only lays the foundation. Meaning-axis exploration is intentionally
    deferred to the later government fork.
    """
    context = dict(night_context or {})
    observed = context.get("observed_graph") if isinstance(context.get("observed_graph"), Mapping) else {}
    return {
        "role": "coreego_designer",
        "status": "read_only_foundation",
        "coreego_name": str(coreego_name or "SongRyeon"),
        "observed_labels": list(observed.get("labels", []) or []),
        "observed_relationships": list(observed.get("relationships", []) or []),
        "scope_note": "Phase 0-1 foundation only; full meaning-axis survey is deferred.",
    }


def assemble_coreego(
    *,
    unresolved_second_dreams: list[Any] | None = None,
    local_submissions: list[dict[str, Any]] | None = None,
    design_packet: Mapping[str, Any] | None = None,
    night_context: Mapping[str, Any] | None = None,
) -> PastAssemblyOutput:
    context = dict(night_context or {})
    dreams = list(unresolved_second_dreams if unresolved_second_dreams is not None else context.get("unresolved_second_dreams", []) or [])
    submissions = list(local_submissions if local_submissions is not None else context.get("local_submissions", []) or [])
    design = dict(design_packet or context.get("design_packet") or {})
    proposal = _change_proposal_from_dreams(dreams, submissions)
    thought = (
        f"CoreEgo assembly reviewed {len(dreams)} unresolved SecondDream item(s) "
        f"and {len(submissions)} local submission(s). "
        f"Designer status: {design.get('status', 'read_only_foundation')}."
    )
    return PastAssemblyOutput(
        past_assembly_thought=thought,
        election_result=False,
        change_proposal=proposal,
        election_rounds=int(context.get("election_rounds", 0) or 0),
    )


def _votes_from_local_reports(local_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    votes: list[dict[str, Any]] = []
    for idx, report in enumerate(local_reports, start=1):
        if not isinstance(report, Mapping):
            continue
        council_key = str(report.get("council_key") or report.get("office_key") or f"local_council_{idx}")
        raw_vote = report.get("vote")
        if raw_vote is None:
            raw_vote = report.get("supports_change")
        approve = bool(raw_vote)
        votes.append({"voter": council_key, "vote": "yes" if approve else "no"})
    return votes


def approve_coreego(
    *,
    assembly_output: PastAssemblyOutput | Mapping[str, Any] | None = None,
    change_proposal: Mapping[str, Any] | None = None,
    local_reports: list[dict[str, Any]] | None = None,
    election_rounds: int = 0,
    max_assembly_depth: int = 3,
    night_context: Mapping[str, Any] | None = None,
) -> PastAssemblyOutput:
    context = dict(night_context or {})
    output = assembly_output if isinstance(assembly_output, PastAssemblyOutput) else None
    assembly_dict = _as_dict(assembly_output)
    proposal = normalize_change_proposal(change_proposal or assembly_dict.get("change_proposal") or context.get("change_proposal") or {})
    rounds = int(election_rounds or assembly_dict.get("election_rounds") or context.get("election_rounds") or 0)
    if rounds >= 3:
        # TODO(v1.7): implement the emergency-government path instead of raising.
        raise NotImplementedError("비상계엄령 v1.7 빵구")
    reports = list(local_reports if local_reports is not None else context.get("local_reports", []) or [])
    votes = _votes_from_local_reports(reports)
    if votes:
        yes_count = sum(1 for vote in votes if vote.get("vote") == "yes")
        result = "pass" if yes_count / len(votes) > 0.5 else "fail"
    else:
        result = "pass"
        votes = [{"voter": "coreego_default", "vote": "yes"}]
    election = build_election_payload(
        proposal,
        votes=votes,
        result=result,
        rounds=rounds,
        max_assembly_depth=max_assembly_depth,
    )
    proposal["election"] = election
    thought = (
        (output.past_assembly_thought if output else str(assembly_dict.get("past_assembly_thought") or "CoreEgo assembly reviewed a proposal."))
        + f" Election result: {result}."
    )
    return PastAssemblyOutput(
        past_assembly_thought=thought,
        election_result=result == "pass",
        change_proposal=proposal,
        election_rounds=rounds,
    )
