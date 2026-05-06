"""Present department day-memory summarizer."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Mapping

from .contracts import SecondDreamSummary


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _item_text(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("summary") or item.get("content") or item.get("text") or item.get("observed_fact") or "")
    return str(item or "")


def summarize_day_memory(
    *,
    empty_seconddream: Mapping[str, Any] | Any | None = None,
    recall_formatter_output: Mapping[str, Any] | Any | None = None,
    summary_writer: Callable[[dict[str, Any], dict[str, Any]], str] | None = None,
    night_context: Mapping[str, Any] | None = None,
) -> SecondDreamSummary:
    """Fill the SecondDream summary from recent-recall formatter output."""
    context = dict(night_context or {})
    empty = _as_dict(empty_seconddream) or _as_dict(context.get("empty_seconddream"))
    formatter = _as_dict(recall_formatter_output) or _as_dict(context.get("recall_formatter_output"))
    items = list(formatter.get("formatted_items", []) or formatter.get("items", []) or [])
    source_persona = str(formatter.get("source_persona") or context.get("source_persona") or "").strip()
    source_dream_keys = [str(item) for item in list(formatter.get("source_dream_keys", []) or []) if str(item)]
    if not source_persona:
        source_persona = "present_summarizer"
    if summary_writer:
        summary = str(summary_writer(empty, formatter) or "").strip()
    else:
        item_summaries = [_item_text(item) for item in items]
        item_summaries = [summary for summary in item_summaries if summary]
        summary = " / ".join(item_summaries[:5]) or "No unprocessed day-memory items were supplied by recent recall."
    return SecondDreamSummary(
        seconddream_key=str(empty.get("seconddream_key") or context.get("seconddream_key") or "seconddream::pending"),
        branch_path=str(empty.get("branch_path") or context.get("branch_path") or "TimeBranch/present"),
        summary=summary,
        source_persona=source_persona,
        source_dream_keys=source_dream_keys,
    )
