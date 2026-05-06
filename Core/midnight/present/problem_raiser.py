"""Present department problem raiser."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Mapping

from .contracts import SecondDreamProblems


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _problem_text(item: Any) -> str:
    if isinstance(item, Mapping):
        return str(item.get("topic") or item.get("problem") or item.get("summary") or item.get("gap") or item)
    return str(item or "")


def raise_present_problems(
    *,
    empty_seconddream: Mapping[str, Any] | Any | None = None,
    recall_auditor_output: Mapping[str, Any] | Any | None = None,
    problem_writer: Callable[[dict[str, Any], dict[str, Any]], Mapping[str, Any]] | None = None,
    night_context: Mapping[str, Any] | None = None,
) -> SecondDreamProblems:
    """Extract supply topics and field-loop problems from recall audit output."""
    context = dict(night_context or {})
    empty = _as_dict(empty_seconddream) or _as_dict(context.get("empty_seconddream"))
    auditor = _as_dict(recall_auditor_output) or _as_dict(context.get("recall_auditor_output"))
    source_persona = str(auditor.get("source_persona") or context.get("source_persona") or "present_problem_raiser").strip()
    if problem_writer:
        payload = dict(problem_writer(empty, auditor) or {})
        supply_topics = [str(item) for item in list(payload.get("supply_topics", []) or []) if str(item)]
        field_loop_problems = [str(item) for item in list(payload.get("field_loop_problems", []) or []) if str(item)]
    else:
        criticized = list(auditor.get("criticized_items", []) or auditor.get("items", []) or [])
        supply_topics = []
        field_loop_problems = []
        for item in criticized:
            text = _problem_text(item)
            if not text:
                continue
            if isinstance(item, Mapping) and str(item.get("kind") or item.get("type") or "").lower() in {"supply", "supply_topic", "gap"}:
                supply_topics.append(text)
            else:
                field_loop_problems.append(text)
        if not supply_topics and field_loop_problems:
            supply_topics = field_loop_problems[:2]
    return SecondDreamProblems(
        seconddream_key=str(empty.get("seconddream_key") or context.get("seconddream_key") or "seconddream::pending"),
        supply_topics=list(dict.fromkeys(supply_topics))[:12],
        field_loop_problems=list(dict.fromkeys(field_loop_problems))[:12],
        source_persona=source_persona,
    )
