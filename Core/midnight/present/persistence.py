"""SecondDream persistence for the V4 present department."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Mapping

NIGHT_GOVERNMENT_KEY = "night_government_v1"
R5_CREATED_BY = "v4_r5_present_department"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _stable_key(prefix: str, *parts: Any) -> str:
    material = "\n".join(_norm(part) for part in parts).encode("utf-8")
    return f"{prefix}::" + hashlib.sha1(material).hexdigest()[:16]


def _jsonable(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _created_at_ms(value: Any) -> int:
    if value is None:
        return int(time.time() * 1000)
    if isinstance(value, (int, float)):
        raw = float(value)
        return int(raw if raw > 10_000_000_000 else raw * 1000)
    text = _norm(value)
    if not text:
        return int(time.time() * 1000)
    try:
        return int(float(text))
    except ValueError:
        pass
    try:
        normalized = text.replace("Z", "+00:00")
        return int(datetime.fromisoformat(normalized).timestamp() * 1000)
    except ValueError:
        return int(time.time() * 1000)


def build_seconddream_payload(
    *,
    seconddream_key: str,
    summary: str,
    problems: list[Any],
    audit: Mapping[str, Any],
    source_persona: str,
    branch_path: str,
    source_dream_keys: list[str] | None = None,
    created_at: int | None = None,
) -> dict[str, Any]:
    key = _norm(seconddream_key) or _stable_key("seconddream", branch_path, summary)
    persona = _norm(source_persona)
    branch = _norm(branch_path)
    clean_summary = _norm(summary)
    if not key:
        raise ValueError("SecondDream.seconddream_key is required")
    if not clean_summary:
        raise ValueError("SecondDream.summary is required")
    if not persona:
        raise ValueError("SecondDream.source_persona is required")
    if not branch:
        raise ValueError("SecondDream.branch_path is required")
    audit_payload = _as_dict(audit)
    audit_payload["source_persona"] = _norm(audit_payload.get("source_persona") or persona)
    return {
        "seconddream_key": key,
        "summary": clean_summary,
        "problems": [str(problem) for problem in list(problems or []) if str(problem)],
        "audit": audit_payload,
        "audit_json": _jsonable(audit_payload),
        "source_persona": persona,
        "branch_path": branch,
        "source_dream_keys": [str(item) for item in list(source_dream_keys or []) if str(item)],
        "created_at": _created_at_ms(created_at),
    }


def persist_seconddream(session: Any, seconddream: Mapping[str, Any], graph_operations_log: list | None = None) -> dict[str, Any]:
    payload = build_seconddream_payload(
        seconddream_key=str(seconddream.get("seconddream_key") or ""),
        summary=str(seconddream.get("summary") or ""),
        problems=list(seconddream.get("problems", []) or []),
        audit=seconddream.get("audit", {}) if isinstance(seconddream.get("audit"), Mapping) else {},
        source_persona=str(seconddream.get("source_persona") or ""),
        branch_path=str(seconddream.get("branch_path") or ""),
        source_dream_keys=list(seconddream.get("source_dream_keys", []) or []),
        created_at=seconddream.get("created_at"),
    )
    session.run(
        """
        MERGE (sd:SecondDream {seconddream_key: $seconddream_key})
        SET sd.summary = $summary,
            sd.problems = $problems,
            sd.audit = $audit_json,
            sd.source_persona = $source_persona,
            sd.branch_path = $branch_path,
            sd.created_at = coalesce(sd.created_at, toInteger($created_at)),
            sd.created_by = coalesce(sd.created_by, $created_by)
        MERGE (tb:TimeBranch {governor_key: $governor_key, branch_path: $branch_path})
        MERGE (sd)-[:GUIDES_BRANCH]->(tb)
        """,
        **payload,
        created_by=R5_CREATED_BY,
        governor_key=NIGHT_GOVERNMENT_KEY,
    )
    for dream_key in payload["source_dream_keys"]:
        session.run(
            """
            MATCH (sd:SecondDream {seconddream_key: $seconddream_key})
            MERGE (dream:Dream {dream_key: $dream_key})
            MERGE (sd)-[:AUDITED_FROM]->(dream)
            """,
            seconddream_key=payload["seconddream_key"],
            dream_key=dream_key,
        )
    for topic in payload["problems"]:
        session.run(
            """
            MATCH (sd:SecondDream {seconddream_key: $seconddream_key})
            MERGE (topic:SupplyTopic {name: $topic})
            SET topic.embedding = coalesce(topic.embedding, []),
                topic.embedding_model = coalesce(topic.embedding_model, ''),
                topic.updated_at = timestamp()
            MERGE (sd)-[:CONTAINS_TOPIC]->(topic)
            """,
            seconddream_key=payload["seconddream_key"],
            topic=topic,
        )
    if isinstance(graph_operations_log, list):
        graph_operations_log.append(
            {
                "operation": "persist_seconddream",
                "seconddream_key": payload["seconddream_key"],
                "branch_path": payload["branch_path"],
            }
        )
    return payload
