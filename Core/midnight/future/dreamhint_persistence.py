"""DreamHint persistence for the V4 future department."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Mapping

NIGHT_GOVERNMENT_KEY = "night_government_v1"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _stable_hint_key(hint_text: str, source_persona: str, branch_path: str) -> str:
    material = f"{source_persona}\n{branch_path}\n{hint_text}".encode("utf-8")
    return "dreamhint::" + hashlib.sha1(material).hexdigest()[:16]


def build_dreamhint_payload(
    *,
    hint_text: str,
    source_persona: str,
    branch_path: str,
    dreamhint_key: str | None = None,
    cites_past_thought: list[str] | None = None,
    recall_result_refs: list[str] | None = None,
    created_at: int | None = None,
    expires_at: int | None = None,
    archive_at: int | None = None,
) -> dict[str, Any]:
    hint = _norm(hint_text)
    persona = _norm(source_persona)
    branch = _norm(branch_path)
    if not hint:
        raise ValueError("DreamHint.hint_text is required")
    if not persona:
        raise ValueError("DreamHint.source_persona is required")
    if not branch:
        raise ValueError("DreamHint.branch_path is required")
    key = _norm(dreamhint_key) or _stable_hint_key(hint, persona, branch)
    return {
        "dreamhint_key": key,
        "hint_text": hint,
        "source_persona": persona,
        "branch_path": branch,
        "created_at": int(created_at if created_at is not None else time.time() * 1000),
        "expires_at": expires_at,
        "archive_at": archive_at,
        "cites_past_thought": [str(item) for item in list(cites_past_thought or []) if str(item)],
        "recall_result_refs": [str(item) for item in list(recall_result_refs or []) if str(item)],
    }


ACTIVE_DREAMHINT_WHERE = (
    "coalesce(dh.archive_at, 9999999999999) > timestamp() "
    "AND coalesce(dh.expires_at, 9999999999999) > timestamp()"
)


def build_active_dreamhint_query(*, branch_path: str | None = None, limit: int = 12) -> tuple[str, dict[str, Any]]:
    """Build the field-loop query for active DreamHint advisory records."""
    where_parts = [ACTIVE_DREAMHINT_WHERE]
    params: dict[str, Any] = {"limit": max(1, min(int(limit or 12), 50))}
    if _norm(branch_path):
        where_parts.append("dh.branch_path = $branch_path")
        params["branch_path"] = _norm(branch_path)
    query = f"""
    MATCH (dh:DreamHint)
    WHERE {' AND '.join(where_parts)}
    RETURN dh.dreamhint_key AS dreamhint_key,
           dh.hint_text AS hint_text,
           dh.source_persona AS source_persona,
           dh.branch_path AS branch_path,
           dh.created_at AS created_at,
           dh.expires_at AS expires_at,
           dh.archive_at AS archive_at
    ORDER BY coalesce(dh.created_at, 0) DESC
    LIMIT $limit
    """
    return query, params


def fetch_active_dreamhints(session: Any, *, branch_path: str | None = None, limit: int = 12) -> list[dict[str, Any]]:
    query, params = build_active_dreamhint_query(branch_path=branch_path, limit=limit)
    rows = session.run(query, **params)
    if hasattr(rows, "data"):
        return list(rows.data())
    return [dict(row) if isinstance(row, Mapping) else row for row in list(rows or [])]


def persist_dreamhint(session: Any, dreamhint: Mapping[str, Any], graph_operations_log: list | None = None) -> dict[str, Any]:
    payload = build_dreamhint_payload(
        dreamhint_key=dreamhint.get("dreamhint_key"),
        hint_text=str(dreamhint.get("hint_text") or ""),
        source_persona=str(dreamhint.get("source_persona") or ""),
        branch_path=str(dreamhint.get("branch_path") or ""),
        created_at=dreamhint.get("created_at"),
        expires_at=dreamhint.get("expires_at"),
        archive_at=dreamhint.get("archive_at"),
        cites_past_thought=list(dreamhint.get("cites_past_thought", []) or []),
        recall_result_refs=list(dreamhint.get("recall_result_refs", []) or []),
    )
    session.run(
        """
        MERGE (dh:DreamHint {dreamhint_key: $dreamhint_key})
        SET dh.hint_text = $hint_text,
            dh.source_persona = $source_persona,
            dh.branch_path = $branch_path,
            dh.created_at = coalesce(dh.created_at, toInteger($created_at)),
            dh.expires_at = $expires_at,
            dh.archive_at = $archive_at
        MERGE (tb:TimeBranch {governor_key: $governor_key, branch_path: $branch_path})
        MERGE (dh)-[:GUIDES_BRANCH]->(tb)
        """,
        **payload,
        governor_key=NIGHT_GOVERNMENT_KEY,
    )
    for thought_ref in payload["cites_past_thought"]:
        session.run(
            """
            MATCH (dh:DreamHint {dreamhint_key: $dreamhint_key})
            MERGE (pt:PastThoughtRef {source_id: $source_id})
            MERGE (dh)-[:CITES_PAST_THOUGHT]->(pt)
            """,
            dreamhint_key=payload["dreamhint_key"],
            source_id=thought_ref,
        )
    for recall_ref in payload["recall_result_refs"]:
        session.run(
            """
            MATCH (dh:DreamHint {dreamhint_key: $dreamhint_key})
            MERGE (rr:RecallResultRef {source_id: $source_id})
            MERGE (dh)-[:LINKS_RECALL_RESULT]->(rr)
            """,
            dreamhint_key=payload["dreamhint_key"],
            source_id=recall_ref,
        )
    if isinstance(graph_operations_log, list):
        graph_operations_log.append(
            {
                "operation": "persist_dreamhint",
                "dreamhint_key": payload["dreamhint_key"],
                "branch_path": payload["branch_path"],
            }
        )
    return payload


__all__ = [
    "ACTIVE_DREAMHINT_WHERE",
    "build_active_dreamhint_query",
    "build_dreamhint_payload",
    "fetch_active_dreamhints",
    "persist_dreamhint",
]
