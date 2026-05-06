"""Future field critic node for the V4 midnight government."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Mapping

from Core.midnight.recall.random import RandomRecallResult, invoke as default_random_recall
from Core.midnight.present.contracts import PresentSecondDreamOutput


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _compact_problem(problem: Any) -> str:
    if isinstance(problem, Mapping):
        return str(problem.get("topic") or problem.get("summary") or problem.get("problem") or problem)
    return str(problem or "")


def _recall_result_to_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, RandomRecallResult):
        return asdict(result)
    if is_dataclass(result):
        return asdict(result)
    if isinstance(result, Mapping):
        return dict(result)
    return {"results": [], "source_persona_map": {}}


def build_future_field_critique(
    *,
    witness_packet: Mapping[str, Any] | None = None,
    present_input: PresentSecondDreamOutput | Mapping[str, Any] | None = None,
    recall_invoke: Callable[[str, str | None], Any] | None = None,
    persona_filter: str | None = None,
    night_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Raise field problems, call random recall once, and choose the next seat."""
    context = dict(night_context or {})
    witness = dict(witness_packet or context.get("witness_packet") or {})
    present = _as_dict(present_input) or _as_dict(context.get("present_input"))
    problems = [_compact_problem(problem) for problem in list(present.get("problems", []) or [])]
    problems = [problem for problem in problems if problem]
    audit = present.get("audit") if isinstance(present.get("audit"), dict) else {}
    audit_gaps = [str(gap) for gap in list(audit.get("gaps", []) or audit.get("missing", []) or []) if str(gap)]
    missing_topics = []
    for item in [*problems, *audit_gaps]:
        if item not in missing_topics:
            missing_topics.append(item)
    query = "; ".join(missing_topics[:3]) or witness.get("witness_summary") or "future department random recall"
    recall_fn = recall_invoke or default_random_recall
    recall_result = _recall_result_to_dict(recall_fn(str(query), persona_filter))
    recall_items = list(recall_result.get("results", []) or [])
    blocking_gaps = [] if recall_items else missing_topics
    next_node = "decision_maker" if recall_items or not blocking_gaps else "future_witness"
    critique_summary = (
        "Random recall supplied material for the future decision."
        if recall_items
        else "Future critique still lacks supporting recall material."
    )
    return {
        "role": "future_field_critic",
        "status": "ready" if next_node == "decision_maker" else "needs_more_witnessing",
        "witness_summary": witness.get("witness_summary", ""),
        "present_summary": str(present.get("summary") or present.get("second_dream_summary") or ""),
        "missing_topics": missing_topics,
        "recall_query": str(query),
        "random_recall": recall_result,
        "blocking_gaps": blocking_gaps,
        "critique_summary": critique_summary,
        "next_node": next_node,
    }
