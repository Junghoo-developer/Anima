"""Future department skeleton."""

from .contracts import PastAssemblyInput, PastAssemblyMockInput, PresentSecondDreamInput
from .decision_maker import make_future_decision
from .dreamhint_persistence import build_dreamhint_payload, persist_dreamhint
from .field_critic import build_future_field_critique
from .witness import build_future_witness


def run_future_assembly(
    *,
    past_input=None,
    present_input=None,
    previous_decision_thought: str = "",
    source_persona: str | None = None,
    branch_path: str = "TimeBranch/future",
    session=None,
    recall_invoke=None,
    graph_operations_log: list | None = None,
) -> dict:
    witness = build_future_witness(
        past_input=past_input,
        previous_decision_thought=previous_decision_thought,
    )
    critic = build_future_field_critique(
        witness_packet=witness,
        present_input=present_input,
        recall_invoke=recall_invoke,
    )
    decision = make_future_decision(
        witness_packet=witness,
        critic_packet=critic,
        source_persona=source_persona,
        branch_path=branch_path,
    )
    persisted = None
    if session is not None and decision.get("status") == "approved":
        persisted = persist_dreamhint(session, decision["dreamhint"], graph_operations_log=graph_operations_log)
    return {
        "witness": witness,
        "critic": critic,
        "decision": decision,
        "persisted_dreamhint": persisted,
    }


__all__ = [
    "PastAssemblyMockInput",
    "PastAssemblyInput",
    "PresentSecondDreamInput",
    "build_future_witness",
    "build_future_field_critique",
    "make_future_decision",
    "run_future_assembly",
    "build_dreamhint_payload",
    "persist_dreamhint",
]
