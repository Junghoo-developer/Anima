"""Present department fact checker."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Mapping

from .contracts import PresentSecondDreamOutput, SecondDreamAudit, SecondDreamProblems, SecondDreamSummary


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _source_texts(source_data: Any) -> list[str]:
    if isinstance(source_data, Mapping):
        source_data = list(source_data.get("items", []) or source_data.get("sources", []) or source_data.values())
    if not isinstance(source_data, list):
        source_data = [source_data] if source_data else []
    texts = []
    for item in source_data:
        if isinstance(item, Mapping):
            text = str(item.get("text") or item.get("content") or item.get("summary") or item.get("observed_fact") or "")
        else:
            text = str(item or "")
        if text:
            texts.append(text)
    return texts


def _problem_list(problems: Mapping[str, Any]) -> list[str]:
    return [
        str(item)
        for item in [
            *list(problems.get("supply_topics", []) or []),
            *list(problems.get("field_loop_problems", []) or []),
        ]
        if str(item)
    ]


def check_present_facts(
    *,
    summary: SecondDreamSummary | Mapping[str, Any] | None = None,
    problems: SecondDreamProblems | Mapping[str, Any] | None = None,
    source_data: Any = None,
    fact_checker: Callable[[dict[str, Any], dict[str, Any], Any], Mapping[str, Any]] | None = None,
    night_context: Mapping[str, Any] | None = None,
) -> PresentSecondDreamOutput:
    """Verify present-department outputs and produce a filled SecondDream packet."""
    context = dict(night_context or {})
    summary_payload = _as_dict(summary) or _as_dict(context.get("summary"))
    problems_payload = _as_dict(problems) or _as_dict(context.get("problems"))
    persona = str(
        summary_payload.get("source_persona")
        or problems_payload.get("source_persona")
        or context.get("source_persona")
        or ""
    ).strip()
    if not persona:
        raise ValueError("SecondDream.source_persona is required")
    if fact_checker:
        audit_payload = dict(fact_checker(summary_payload, problems_payload, source_data) or {})
    else:
        source_texts = _source_texts(source_data)
        summary_text = str(summary_payload.get("summary") or "")
        problem_items = _problem_list(problems_payload)
        citations = []
        rejected = []
        for idx, text in enumerate(source_texts, start=1):
            if summary_text and summary_text[:40] in text:
                citations.append(f"source::{idx}")
        for problem in problem_items:
            if source_texts and not any(problem[:40] in text for text in source_texts):
                rejected.append(problem)
        audit_payload = {
            "verified": bool(summary_text and not rejected),
            "source_persona": persona,
            "citations": citations or [f"source::{idx}" for idx, _ in enumerate(source_texts[:3], start=1)],
            "rejected_claims": rejected,
            "notes": ["Present fact checker compared summary/problems against source_data."],
        }
    audit_payload["source_persona"] = str(audit_payload.get("source_persona") or persona).strip()
    if not audit_payload["source_persona"]:
        raise ValueError("SecondDream.source_persona is required")
    audit = SecondDreamAudit(
        seconddream_key=str(summary_payload.get("seconddream_key") or problems_payload.get("seconddream_key") or "seconddream::pending"),
        verified=bool(audit_payload.get("verified")),
        source_persona=audit_payload["source_persona"],
        citations=[str(item) for item in list(audit_payload.get("citations", []) or []) if str(item)],
        rejected_claims=[str(item) for item in list(audit_payload.get("rejected_claims", []) or []) if str(item)],
        notes=[str(item) for item in list(audit_payload.get("notes", []) or []) if str(item)],
    )
    return PresentSecondDreamOutput(
        seconddream_key=audit.seconddream_key,
        summary=str(summary_payload.get("summary") or ""),
        problems=_problem_list(problems_payload),
        audit=asdict(audit),
    )
