"""Graph persistence helpers for the V4 past department."""

from __future__ import annotations

import hashlib
import time
from datetime import date, datetime
from typing import Any, Iterable, Mapping

NIGHT_GOVERNMENT_KEY = "night_government_v1"
R4_CREATED_BY = "v4_r4_past_department"
SHARED_ACCORD_NAME = "허정후-송련 어코드"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _stable_key(prefix: str, *parts: Any) -> str:
    material = "\n".join(_norm(part) for part in parts).encode("utf-8")
    return f"{prefix}::" + hashlib.sha1(material).hexdigest()[:16]


def _coerce_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = _norm(value)
    if not text:
        raise ValueError("date value is required")
    return datetime.strptime(text[:10], "%Y-%m-%d").date()


def build_shared_accord_cleanup_cypher() -> str:
    return """
    MATCH (acc {kind: "shared_accord", name: $accord_name})
    DETACH DELETE acc
    """


def build_shared_accord_count_cypher() -> str:
    return """
    MATCH (acc {kind: "shared_accord", name: $accord_name})
    RETURN count(acc) AS count
    """


def cleanup_shared_accord(session: Any, graph_operations_log: list | None = None) -> None:
    session.run(build_shared_accord_cleanup_cypher(), accord_name=SHARED_ACCORD_NAME)
    if isinstance(graph_operations_log, list):
        graph_operations_log.append({"operation": "cleanup_shared_accord", "name": SHARED_ACCORD_NAME})


def verify_shared_accord_removed(session: Any) -> bool:
    rows = list(session.run(build_shared_accord_count_cypher(), accord_name=SHARED_ACCORD_NAME))
    if not rows:
        return True
    first = rows[0]
    if isinstance(first, Mapping):
        return int(first.get("count", 0) or 0) == 0
    try:
        return int(first["count"] or 0) == 0
    except Exception:
        return False


def build_time_branch_specs(values: Iterable[Any]) -> list[dict[str, Any]]:
    dates = sorted({_coerce_date(value) for value in values})
    specs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in dates:
        year_key = f"{item.year:04d}"
        month_key = f"{item.year:04d}/{item.month:02d}"
        day_key = f"{item.year:04d}/{item.month:02d}/{item.day:02d}"
        for branch_key, level, parent in [
            (year_key, "year", ""),
            (month_key, "month", year_key),
            (day_key, "day", month_key),
        ]:
            if branch_key in seen:
                continue
            seen.add(branch_key)
            specs.append(
                {
                    "branch_path": branch_key,
                    "time_level": level,
                    "parent_branch_path": parent,
                    "created_by": R4_CREATED_BY,
                }
            )
    return specs


def persist_time_branch_window(
    session: Any,
    values: Iterable[Any],
    *,
    coreego_name: str = "SongRyeon",
    graph_operations_log: list | None = None,
) -> list[dict[str, Any]]:
    specs = build_time_branch_specs(values)
    for spec in specs:
        session.run(
            """
            MERGE (ce:CoreEgo {name: $coreego_name})
            MERGE (tb:TimeBranch {governor_key: $governor_key, branch_path: $branch_path})
            SET tb.time_level = $time_level,
                tb.parent_branch_path = $parent_branch_path,
                tb.created_by = coalesce(tb.created_by, $created_by),
                tb.updated_at = timestamp()
            WITH ce, tb
            FOREACH (_ IN CASE WHEN $time_level = "year" THEN [1] ELSE [] END |
                MERGE (ce)-[:HAS_TIME_BRANCH]->(tb)
            )
            """,
            coreego_name=coreego_name,
            governor_key=NIGHT_GOVERNMENT_KEY,
            **spec,
        )
        if spec["parent_branch_path"]:
            session.run(
                """
                MATCH (parent:TimeBranch {governor_key: $governor_key, branch_path: $parent_branch_path})
                MATCH (child:TimeBranch {governor_key: $governor_key, branch_path: $branch_path})
                MERGE (parent)-[:HAS_CHILD_TIME_BRANCH]->(child)
                """,
                governor_key=NIGHT_GOVERNMENT_KEY,
                parent_branch_path=spec["parent_branch_path"],
                branch_path=spec["branch_path"],
            )
    by_level: dict[str, list[str]] = {}
    for spec in specs:
        by_level.setdefault(spec["time_level"], []).append(spec["branch_path"])
    for branch_paths in by_level.values():
        for left, right in zip(branch_paths, branch_paths[1:]):
            session.run(
                """
                MATCH (left:TimeBranch {governor_key: $governor_key, branch_path: $left_path})
                MATCH (right:TimeBranch {governor_key: $governor_key, branch_path: $right_path})
                MERGE (left)-[:NEXT_SIBLING]->(right)
                """,
                governor_key=NIGHT_GOVERNMENT_KEY,
                left_path=left,
                right_path=right,
            )
    if isinstance(graph_operations_log, list):
        graph_operations_log.append({"operation": "persist_time_branch_window", "count": len(specs)})
    return specs


def normalize_change_proposal(change_proposal: Mapping[str, Any]) -> dict[str, Any]:
    proposal = dict(change_proposal or {})
    target_node_id = _norm(proposal.get("target_node_id") or proposal.get("target") or "CoreEgo:SongRyeon")
    attr_name = _norm(proposal.get("attr_name") or "night_advisory")
    new_value = proposal.get("new_value")
    rationale = proposal.get("rationale") if isinstance(proposal.get("rationale"), Mapping) else {}
    importance = proposal.get("importance") if isinstance(proposal.get("importance"), Mapping) else {}
    try:
        score = max(0.0, min(float(importance.get("score", 0.5) or 0.5), 1.0))
    except (TypeError, ValueError):
        score = 0.5
    proposal_key = _norm(proposal.get("proposal_key")) or _stable_key("change_proposal", target_node_id, attr_name, new_value)
    axis = _norm(proposal.get("axis")) or "time"
    if axis not in {"time", "semantic"}:
        axis = "time"
    return {
        "proposal_key": proposal_key,
        "axis": axis,
        "target_node_id": target_node_id,
        "attr_name": attr_name,
        "old_value": proposal.get("old_value"),
        "new_value": new_value,
        "rationale": {
            "summary": _norm(rationale.get("summary")),
            "evidence_keys": [str(item) for item in list(rationale.get("evidence_keys", []) or []) if str(item)],
            "sources": [str(item) for item in list(rationale.get("sources", []) or []) if str(item)],
        },
        "importance": {
            "score": score,
            "sources": [str(item) for item in list(importance.get("sources", []) or []) if str(item)],
        },
    }


def persist_change_proposal(session: Any, change_proposal: Mapping[str, Any], graph_operations_log: list | None = None) -> dict[str, Any]:
    proposal = normalize_change_proposal(change_proposal)
    session.run(
        """
        MERGE (target:ProposedChangeTarget {node_id: $target_node_id})
        MERGE (cp:ChangeProposal {proposal_key: $proposal_key})
        SET cp.axis = $axis,
            cp.attr_name = $attr_name,
            cp.old_value = $old_value,
            cp.new_value = $new_value,
            cp.created_by = coalesce(cp.created_by, $created_by),
            cp.updated_at = timestamp()
        MERGE (cp)-[:TARGETS_CHANGE]->(target)
        MERGE (cr:ChangeRationale {proposal_key: $proposal_key})
        SET cr.axis = $axis,
            cr.summary = $rationale_summary,
            cr.evidence_keys = $rationale_evidence_keys,
            cr.sources = $rationale_sources,
            cr.created_by = coalesce(cr.created_by, $created_by)
        MERGE (cr)-[:JUSTIFIES]->(target)
        MERGE (ci:ChangeImportance {proposal_key: $proposal_key})
        SET ci.axis = $axis,
            ci.score = toFloat($importance_score),
            ci.sources = $importance_sources,
            ci.created_by = coalesce(ci.created_by, $created_by)
        MERGE (ci)-[:WEIGHS]->(target)
        """,
        proposal_key=proposal["proposal_key"],
        axis=proposal["axis"],
        target_node_id=proposal["target_node_id"],
        attr_name=proposal["attr_name"],
        old_value=proposal["old_value"],
        new_value=proposal["new_value"],
        rationale_summary=proposal["rationale"]["summary"],
        rationale_evidence_keys=proposal["rationale"]["evidence_keys"],
        rationale_sources=proposal["rationale"]["sources"],
        importance_score=proposal["importance"]["score"],
        importance_sources=proposal["importance"]["sources"],
        created_by=R4_CREATED_BY,
    )
    if isinstance(graph_operations_log, list):
        graph_operations_log.append({"operation": "persist_change_proposal", "proposal_key": proposal["proposal_key"]})
    return proposal


def build_election_payload(
    change_proposal: Mapping[str, Any],
    *,
    votes: list[dict[str, Any]],
    result: str,
    rounds: int,
    max_assembly_depth: int = 3,
) -> dict[str, Any]:
    proposal = normalize_change_proposal(change_proposal)
    score = float(proposal["importance"]["score"])
    start_depth = max(1, min(int(round(score * max_assembly_depth)) or 1, max_assembly_depth))
    election_id = _stable_key("election", proposal["proposal_key"], rounds, result)
    return {
        "election_id": election_id,
        "proposal_key": proposal["proposal_key"],
        "start_depth": start_depth,
        "votes": votes,
        "result": result,
        "rounds": int(rounds),
        "created_at": int(time.time() * 1000),
    }


def persist_election(session: Any, election: Mapping[str, Any], graph_operations_log: list | None = None) -> dict[str, Any]:
    payload = dict(election or {})
    session.run(
        """
        MERGE (el:Election {election_id: $election_id})
        SET el.proposal_key = $proposal_key,
            el.start_depth = toInteger($start_depth),
            el.votes = $votes,
            el.result = $result,
            el.rounds = toInteger($rounds),
            el.created_at = coalesce(el.created_at, toInteger($created_at)),
            el.created_by = coalesce(el.created_by, $created_by)
        WITH el
        MATCH (cp:ChangeProposal {proposal_key: $proposal_key})
        MERGE (el)-[:VOTES_ON]->(cp)
        """,
        **payload,
        created_by=R4_CREATED_BY,
    )
    if isinstance(graph_operations_log, list):
        graph_operations_log.append({"operation": "persist_election", "election_id": payload.get("election_id")})
    return payload
