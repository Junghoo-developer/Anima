"""V4 midnight-government entrypoint."""

from dataclasses import asdict
from typing import Any, Mapping

from .future.decision_maker import make_future_decision
from .future.field_critic import build_future_field_critique
from .future import run_future_assembly
from .future.witness import build_future_witness
from .past import PastAssemblyOutput
from .past.persistence import cleanup_shared_accord, persist_change_proposal, persist_election
from .past.coreego_assembly import approve_coreego, assemble_coreego, design_coreego
from .present import PresentSecondDreamOutput
from .past.local_assembly import assemble_local_council
from .present.persistence import persist_seconddream
from .present.fact_checker import check_present_facts
from .present.problem_raiser import raise_present_problems
from .present.summarizer import summarize_day_memory
from .recall.random import build_random_recall, invoke as invoke_random_recall
from .recall.recent import EmptySecondDream, build_recent_recall
from .semantic import run_semantic_assembly

NIGHT_GOVERNMENT_KEY = "night_government_v1"
TIME_BRANCH_LABEL = "TimeBranch"
NIGHT_GOVERNMENT_STATE_LABEL = "NightGovernmentState"


def _fallback_empty_seconddream() -> dict[str, Any]:
    return asdict(
        EmptySecondDream(
            seconddream_key="seconddream::dry-run",
            branch_path="TimeBranch/present",
            created_at=None,
            source_dream_keys=[],
            classification="no_unprocessed_day_memory",
        )
    )


def _idle_future_packet(*, source_persona: str, branch_path: str = "TimeBranch/future") -> dict[str, Any]:
    return {
        "witness": {},
        "critic": {},
        "decision": {
            "role": "future_decision_maker",
            "status": "idle",
            "decision": "no_op",
            "reason": "no_unprocessed_day_memory",
            "source_persona": str(source_persona or "").strip(),
            "branch_path": str(branch_path or "TimeBranch/future"),
            "next_node": "",
        },
        "persisted_dreamhint": None,
    }


def run_night(
    *,
    unprocessed_dreams: list[Mapping[str, Any]] | None = None,
    random_sources: list[Mapping[str, Any]] | None = None,
    source_persona: str = "night_government_v1",
    recent_fetcher=None,
    random_fetcher=None,
    graph_session=None,
    recent_session=None,
    random_session=None,
    present_session=None,
    future_session=None,
    persist: bool = False,
    cleanup_shared_accord_now: bool = False,
    include_semantic: bool = False,
    semantic_sources: list[Mapping[str, Any]] | None = None,
    semantic_session=None,
) -> dict[str, Any]:
    """Run a first-pass V4 midnight cycle.

    R6 intentionally keeps this orchestration dry-run friendly: callers may
    inject daytime Dream rows and random-recall sources, while production DB
    sessions can be connected later without changing the department contracts.
    """
    recent_packet = build_recent_recall(
        unprocessed_dreams=unprocessed_dreams,
        session=recent_session or graph_session,
        fetcher=recent_fetcher,
        source_persona=source_persona,
    )
    empty_candidates = list(recent_packet.get("empty_seconddreams", []) or [])
    recent_unprocessed_count = int(recent_packet.get("unprocessed_count", 0) or 0)
    is_idle_no_input = recent_unprocessed_count == 0 and not empty_candidates
    if is_idle_no_input:
        return {
            "status": "completed",
            "mode": "production" if persist else "dry_run",
            "night_action": "idle_no_unprocessed_dreams",
            "persisted": False,
            "semantic_enabled": bool(include_semantic),
            "recent": recent_packet,
            "present": None,
            "persisted_seconddream": None,
            "past": None,
            "persisted_change_proposal": None,
            "persisted_election": None,
            "future": _idle_future_packet(source_persona=source_persona),
            "semantic": None,
            "graph_operations_log": [],
        }
    empty_seconddream = empty_candidates[0] if empty_candidates else _fallback_empty_seconddream()
    formatter_output = dict(recent_packet.get("formatter_output") or {})
    auditor_output = dict(recent_packet.get("auditor_output") or {})

    summary = summarize_day_memory(
        empty_seconddream=empty_seconddream,
        recall_formatter_output=formatter_output,
    )
    problems = raise_present_problems(
        empty_seconddream=empty_seconddream,
        recall_auditor_output=auditor_output,
    )
    source_data = formatter_output.get("formatted_items") or [{"text": summary.summary}]
    present_output = check_present_facts(
        summary=summary,
        problems=problems,
        source_data=source_data,
    )
    graph_operations_log: list[dict[str, Any]] = []
    persisted_seconddream = None
    if persist and (present_session or graph_session) is not None:
        persisted_seconddream = persist_seconddream(
            present_session or graph_session,
            {
                "seconddream_key": present_output.seconddream_key,
                "summary": present_output.summary,
                "problems": present_output.problems,
                "audit": present_output.audit,
                "source_persona": present_output.audit.get("source_persona") or source_persona,
                "branch_path": str(empty_seconddream.get("branch_path") or "TimeBranch/present"),
                "source_dream_keys": list(empty_seconddream.get("source_dream_keys", []) or []),
                "created_at": empty_seconddream.get("created_at"),
            },
            graph_operations_log=graph_operations_log,
        )

    design = design_coreego(
        night_context={"observed_graph": {"labels": ["SecondDream", "TimeBranch"], "relationships": ["AUDITED_FROM"]}}
    )
    assembled = assemble_coreego(
        unresolved_second_dreams=[
            {
                "dream_id": present_output.seconddream_key,
                "topic": empty_seconddream.get("branch_path", "TimeBranch/present"),
                "summary": present_output.summary,
            }
        ],
        design_packet=design,
    )
    approved = approve_coreego(assembly_output=assembled)
    persisted_change_proposal = None
    persisted_election = None
    if persist and (graph_session is not None) and isinstance(approved.change_proposal, Mapping):
        persisted_change_proposal = persist_change_proposal(
            graph_session,
            approved.change_proposal,
            graph_operations_log=graph_operations_log,
        )
        if isinstance(approved.change_proposal.get("election"), Mapping):
            persisted_election = persist_election(
                graph_session,
                approved.change_proposal["election"],
                graph_operations_log=graph_operations_log,
            )
    if persist and cleanup_shared_accord_now and graph_session is not None:
        cleanup_shared_accord(graph_session, graph_operations_log=graph_operations_log)

    def _recall_invoke(query: str, persona_filter: str | None = None):
        return invoke_random_recall(
            query,
            persona_filter=persona_filter,
            sources=random_sources,
            session=random_session or graph_session,
            fetcher=random_fetcher,
        )

    future = run_future_assembly(
        past_input=approved,
        present_input=present_output,
        source_persona=source_persona,
        branch_path=str(empty_seconddream.get("branch_path") or "TimeBranch/future"),
        session=(future_session or graph_session) if persist else None,
        recall_invoke=_recall_invoke,
        graph_operations_log=graph_operations_log,
    )
    semantic = None
    if include_semantic:
        semantic = run_semantic_assembly(
            sources=semantic_sources,
            graph_session=semantic_session or graph_session,
            persist=persist,
            coreego_name="SongRyeon",
            source_persona="semantic_coreego_self",
        )
    return {
        "status": "completed",
        "mode": "production" if persist else "dry_run",
        "night_action": "processed_day_memory",
        "persisted": bool(
            persisted_seconddream
            or persisted_change_proposal
            or persisted_election
            or (future or {}).get("persisted_dreamhint")
            or (semantic or {}).get("graph_operations_log")
        ),
        "semantic_enabled": bool(include_semantic),
        "recent": recent_packet,
        "present": asdict(present_output),
        "persisted_seconddream": persisted_seconddream,
        "past": asdict(approved),
        "persisted_change_proposal": persisted_change_proposal,
        "persisted_election": persisted_election,
        "future": future,
        "semantic": semantic,
        "graph_operations_log": graph_operations_log,
    }


__all__ = [
    "NIGHT_GOVERNMENT_KEY",
    "TIME_BRANCH_LABEL",
    "NIGHT_GOVERNMENT_STATE_LABEL",
    "run_night",
    "PastAssemblyOutput",
    "PresentSecondDreamOutput",
    "build_recent_recall",
    "build_random_recall",
    "invoke_random_recall",
    "run_semantic_assembly",
    "summarize_day_memory",
    "raise_present_problems",
    "check_present_facts",
    "design_coreego",
    "assemble_coreego",
    "approve_coreego",
    "assemble_local_council",
    "build_future_witness",
    "build_future_field_critique",
    "make_future_decision",
    "run_future_assembly",
]
