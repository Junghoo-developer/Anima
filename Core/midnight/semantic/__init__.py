"""Semantic-axis night government."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from Core.midnight.past.persistence import persist_change_proposal, persist_election
from Core.midnight.recall.random import build_random_recall

from .contracts import ConceptClusterSpec, SemanticAssemblyOutput, SemanticBranchSpec
from .coreego import ARCHIVE_REVIVAL_SOURCES, approve_semantic_coreego, design_semantic_coreego, propose_semantic_branches
from .future import build_semantic_future
from .local_assembly import assemble_semantic_local_council
from .past import build_semantic_past
from .persistence import persist_concept_cluster, persist_semantic_branch, persist_timebucket_bridge
from .present import build_semantic_present


def run_semantic_assembly(
    *,
    query: str = "semantic branch candidates",
    sources: list[Mapping[str, Any]] | None = None,
    graph_session: Any = None,
    persist: bool = False,
    coreego_name: str = "SongRyeon",
    source_persona: str = "semantic_coreego_self",
) -> dict[str, Any]:
    recall_packet = build_random_recall(query=query, sources=sources, session=graph_session, axis="semantic")
    present = build_semantic_present(recall_packet=recall_packet)
    design = design_semantic_coreego(coreego_name=coreego_name)
    result_payload = recall_packet.get("result") if isinstance(recall_packet.get("result"), dict) else {}
    self_packet = propose_semantic_branches(
        recall_results=list(result_payload.get("results", []) or []),
        design_packet=design,
        source_persona=source_persona,
    )
    local_reports = [
        assemble_semantic_local_council(
            branch_path=branch.branch_path,
            concept_clusters=[asdict(cluster) for cluster in self_packet["concept_clusters"] if cluster.branch_path == branch.branch_path],
            vote=True,
        )
        for branch in self_packet["branch_specs"]
    ]
    approval = approve_semantic_coreego(self_packet=self_packet, local_reports=local_reports)
    past = build_semantic_past(
        branch_specs=[asdict(item) for item in self_packet["branch_specs"]],
        concept_clusters=[asdict(item) for item in self_packet["concept_clusters"]],
    )
    future = build_semantic_future(approval_packet=approval)
    graph_operations_log: list[dict[str, Any]] = []
    if persist and graph_session is not None:
        for branch in self_packet["branch_specs"]:
            persist_semantic_branch(graph_session, branch, coreego_name=coreego_name, graph_operations_log=graph_operations_log)
        for cluster in self_packet["concept_clusters"]:
            persist_concept_cluster(graph_session, cluster, graph_operations_log=graph_operations_log)
        for branch in self_packet["branch_specs"]:
            persist_timebucket_bridge(
                graph_session,
                semantic_branch_path=branch.branch_path,
                time_bucket_key="semantic::bootstrap",
                graph_operations_log=graph_operations_log,
            )
        persisted_change = persist_change_proposal(
            graph_session,
            approval["change_proposal"],
            graph_operations_log=graph_operations_log,
        )
        if isinstance(persisted_change.get("election"), Mapping):
            persist_election(graph_session, persisted_change["election"], graph_operations_log=graph_operations_log)
    output = SemanticAssemblyOutput(
        coreego_name=coreego_name,
        semantic_thought=self_packet["semantic_thought"],
        branch_specs=list(self_packet["branch_specs"]),
        concept_clusters=list(self_packet["concept_clusters"]),
        change_proposal=dict(approval.get("change_proposal", {})),
        election_result=bool(approval.get("election_result")),
        election_rounds=int(approval.get("election_rounds", 0) or 0),
    )
    return {
        "status": "completed",
        "axis": "semantic",
        "recall": recall_packet,
        "present": present,
        "design": design,
        "self": {
            **self_packet,
            "branch_specs": [asdict(item) for item in self_packet["branch_specs"]],
            "concept_clusters": [asdict(item) for item in self_packet["concept_clusters"]],
        },
        "local_reports": local_reports,
        "approval": approval,
        "past": past,
        "future": future,
        "output": asdict(output),
        "graph_operations_log": graph_operations_log,
    }


__all__ = [
    "ARCHIVE_REVIVAL_SOURCES",
    "SemanticAssemblyOutput",
    "SemanticBranchSpec",
    "ConceptClusterSpec",
    "run_semantic_assembly",
    "design_semantic_coreego",
    "propose_semantic_branches",
    "approve_semantic_coreego",
    "assemble_semantic_local_council",
    "persist_semantic_branch",
    "persist_concept_cluster",
    "persist_timebucket_bridge",
]
