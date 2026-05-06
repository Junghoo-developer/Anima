"""Recent-recall department for the V4 midnight government.

Recent recall turns unprocessed daytime Dream rows into a small packet that the
present department can summarize, criticize, and verify. It deliberately keeps
meaning work shallow: code normalizes records, preserves provenance, and
requires source_persona; later LLM seats decide what the material means.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping


@dataclass(frozen=True)
class EmptySecondDream:
    seconddream_key: str
    branch_path: str
    created_at: int | str | None = None
    source_dream_keys: list[str] = field(default_factory=list)
    classification: str = "recent_day_memory"


@dataclass(frozen=True)
class RecallFormatterOutput:
    formatted_items: list[dict[str, Any]] = field(default_factory=list)
    source_dream_keys: list[str] = field(default_factory=list)
    source_persona: str = "system"


@dataclass(frozen=True)
class RecallAuditorOutput:
    criticized_items: list[dict[str, Any]] = field(default_factory=list)
    source_persona: str = "system"
    citations: list[str] = field(default_factory=list)


def _require_persona(source_persona: str | None) -> str:
    persona = str(source_persona or "").strip()
    if not persona:
        raise ValueError("source_persona required")
    return persona


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "data") and callable(value.data):
        return dict(value.data())
    return {}


def _rows_to_dicts(rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [_as_dict(row) for row in rows if _as_dict(row)]


def _call_fetcher(fetcher: Callable[..., Iterable[Any]], *, limit: int) -> list[dict[str, Any]]:
    try:
        rows = fetcher(limit=limit)
    except TypeError:
        rows = fetcher()
    return _rows_to_dicts(list(rows or []))


def fetch_unaudited_dreams(
    *,
    session: Any = None,
    fetcher: Callable[..., Iterable[Any]] | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Fetch daytime Dream rows that do not yet have a SecondDream audit.

    Tests can inject ``fetcher``. In production the optional Neo4j-like session
    path keeps this module an execution boundary instead of importing DB code.
    """
    if fetcher is not None:
        return _call_fetcher(fetcher, limit=limit)
    if session is None:
        return []
    query = """
    MATCH (d:Dream)
    WHERE NOT (d)<-[:AUDITED_FROM]-(:SecondDream)
    RETURN
      coalesce(d.dream_id, d.id, elementId(d)) AS dream_key,
      d.summary AS summary,
      d.content AS content,
      d.text AS text,
      d.created_at AS created_at,
      d.source_persona AS source_persona,
      d.branch_path AS branch_path
    ORDER BY coalesce(d.created_at, 0) ASC
    LIMIT $limit
    """
    return _rows_to_dicts(session.run(query, limit=int(limit)))


def _source_key(row: Mapping[str, Any], fallback_index: int) -> str:
    return str(
        row.get("dream_key")
        or row.get("dream_id")
        or row.get("source_id")
        or row.get("id")
        or f"dream::{fallback_index}"
    )


def _created_at(row: Mapping[str, Any]) -> int | str | None:
    return row.get("created_at") or row.get("timestamp") or row.get("date")


def _branch_from_created_at(value: Any) -> str:
    if isinstance(value, str):
        if len(value) >= 10 and value[4] == "-" and value[7] == "-":
            return value[:10].replace("-", "/")
        if "/" in value:
            parts = [part for part in value.split("/") if part]
            if len(parts) >= 3 and all(part.isdigit() for part in parts[:3]):
                return "/".join(parts[:3])
    if isinstance(value, (int, float)) and value:
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000.0
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y/%m/%d")
    return datetime.now(tz=timezone.utc).strftime("%Y/%m/%d")


def prepare_empty_seconddreams(
    unprocessed_dreams: list[Mapping[str, Any]] | None = None,
    *,
    session: Any = None,
    fetcher: Callable[..., Iterable[Any]] | None = None,
    limit: int = 50,
) -> list[EmptySecondDream]:
    """Prepare one empty SecondDream shell per day-level TimeBranch."""
    dreams = (
        [dict(item) for item in unprocessed_dreams]
        if unprocessed_dreams is not None
        else fetch_unaudited_dreams(session=session, fetcher=fetcher, limit=limit)
    )
    grouped: dict[str, dict[str, Any]] = {}
    for idx, dream in enumerate(dreams, start=1):
        branch_path = str(dream.get("branch_path") or _branch_from_created_at(_created_at(dream)))
        group = grouped.setdefault(branch_path, {"created_at": _created_at(dream), "source_dream_keys": []})
        key = _source_key(dream, idx)
        if key not in group["source_dream_keys"]:
            group["source_dream_keys"].append(key)
    shells: list[EmptySecondDream] = []
    for branch_path in sorted(grouped):
        group = grouped[branch_path]
        branch_key = branch_path.replace("/", "-")
        shells.append(
            EmptySecondDream(
                seconddream_key=f"seconddream::{branch_key}",
                branch_path=branch_path,
                created_at=group["created_at"],
                source_dream_keys=list(group["source_dream_keys"]),
            )
        )
    return shells


def _item_text(item: Mapping[str, Any]) -> str:
    return str(item.get("summary") or item.get("content") or item.get("text") or item.get("observed_fact") or "")


class _Formatter:
    def format(
        self,
        unprocessed_dreams: list[Mapping[str, Any]] | None = None,
        *,
        source_persona: str | None = "system",
    ) -> RecallFormatterOutput:
        persona = _require_persona(source_persona)
        formatted_items: list[dict[str, Any]] = []
        source_dream_keys: list[str] = []
        for idx, dream in enumerate(list(unprocessed_dreams or []), start=1):
            row = dict(dream)
            key = _source_key(row, idx)
            text = _item_text(row)
            source_dream_keys.append(key)
            formatted_items.append(
                {
                    "dream_key": key,
                    "summary": text,
                    "content": str(row.get("content") or row.get("text") or ""),
                    "created_at": _created_at(row),
                    "branch_path": str(row.get("branch_path") or _branch_from_created_at(_created_at(row))),
                    "source_persona": str(row.get("source_persona") or persona),
                }
            )
        return RecallFormatterOutput(
            formatted_items=formatted_items,
            source_dream_keys=list(dict.fromkeys(source_dream_keys)),
            source_persona=persona,
        )


class _Auditor:
    def audit(
        self,
        formatter_output: RecallFormatterOutput | Mapping[str, Any] | None = None,
        *,
        source_persona: str | None = None,
    ) -> RecallAuditorOutput:
        payload = _as_dict(formatter_output)
        persona = (
            _require_persona(source_persona)
            if source_persona is not None
            else _require_persona(payload.get("source_persona") or "system")
        )
        formatted_items = list(payload.get("formatted_items", []) or [])
        criticized_items = []
        for item in formatted_items:
            if not isinstance(item, Mapping):
                continue
            text = _item_text(item)
            criticized_items.append(
                {
                    "kind": "recent_recall_item",
                    "dream_key": str(item.get("dream_key") or ""),
                    "summary": text,
                    "source_persona": str(item.get("source_persona") or persona),
                    "needs_present_review": True,
                }
            )
        citations = [str(key) for key in list(payload.get("source_dream_keys", []) or []) if str(key)]
        if not citations:
            citations = [str(item.get("dream_key")) for item in criticized_items if item.get("dream_key")]
        return RecallAuditorOutput(
            criticized_items=criticized_items,
            source_persona=persona,
            citations=list(dict.fromkeys(citations)),
        )


formatter = _Formatter()
auditor = _Auditor()


def build_recent_recall(
    *,
    night_context: Mapping[str, Any] | None = None,
    unprocessed_dreams: list[Mapping[str, Any]] | None = None,
    session: Any = None,
    fetcher: Callable[..., Iterable[Any]] | None = None,
    source_persona: str | None = "system",
    limit: int = 50,
) -> dict[str, Any]:
    context = dict(night_context or {})
    dreams = (
        list(unprocessed_dreams)
        if unprocessed_dreams is not None
        else fetch_unaudited_dreams(session=session or context.get("session"), fetcher=fetcher, limit=limit)
    )
    persona = _require_persona(source_persona or context.get("source_persona") or "system")
    empty = prepare_empty_seconddreams(dreams)
    formatted = formatter.format(dreams, source_persona=persona)
    audited = auditor.audit(formatted, source_persona=persona)
    return {
        "role": "recent_recall",
        "status": "completed",
        "unprocessed_count": len(dreams),
        "empty_seconddreams": [asdict(item) for item in empty],
        "formatter_output": asdict(formatted),
        "auditor_output": asdict(audited),
    }


__all__ = [
    "EmptySecondDream",
    "RecallFormatterOutput",
    "RecallAuditorOutput",
    "fetch_unaudited_dreams",
    "prepare_empty_seconddreams",
    "formatter",
    "auditor",
    "build_recent_recall",
]
