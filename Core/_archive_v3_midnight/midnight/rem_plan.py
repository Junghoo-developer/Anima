"""REMPlan department for the midnight reflection graph.

This module is a mechanical extraction from Core.midnight_reflection.DreamWeaver.
It keeps REMPlan planning behavior unchanged while moving the department body out
of the night-loop god-file.
"""

from Core.rem_governor import REMPlanSchema


def _plan_branch_paths(cls, rem_plan):
    if not isinstance(rem_plan, dict):
        return []
    selected = rem_plan.get("selected_branch_paths", [])
    if isinstance(selected, list):
        normalized = [str(item or "").strip() for item in selected if str(item or "").strip()]
        if normalized:
            return cls._dedupe_keep_order(normalized)
    legacy = rem_plan.get("branch_paths", [])
    if isinstance(legacy, list):
        return cls._dedupe_keep_order([str(item or "").strip() for item in legacy if str(item or "").strip()])
    return []

def _plan_topics(cls, rem_plan):
    topics = []
    for branch_path in cls._plan_branch_paths(rem_plan):
        topic_slug = cls._topic_slug_from_branch_path(branch_path)
        if topic_slug:
            topics.append(topic_slug)
    if not topics and isinstance(rem_plan, dict):
        legacy = rem_plan.get("priority_topics", [])
        if isinstance(legacy, list):
            topics.extend(str(item or "").strip() for item in legacy if str(item or "").strip())
    return cls._dedupe_keep_order(topics)

def _plan_evidence_points(cls, rem_plan):
    if not isinstance(rem_plan, dict):
        return []
    evidence = rem_plan.get("evidence_start_points", [])
    if isinstance(evidence, list):
        normalized = [str(item or "").strip() for item in evidence if str(item or "").strip()]
        if normalized:
            return cls._dedupe_keep_order(normalized)
    legacy = rem_plan.get("required_evidence_addresses", [])
    if isinstance(legacy, list):
        return cls._dedupe_keep_order([str(item or "").strip() for item in legacy if str(item or "").strip()])
    return []


def _build_rem_plan_from_rows(self, dream_rows, rem_governor=None, branch_architect=None, architect_handoff_report=None, strategy_council=None):
    rows = dream_rows if isinstance(dream_rows, list) else []
    governor = rem_governor if isinstance(rem_governor, dict) and rem_governor else self._default_rem_governor_state()
    architect = branch_architect if isinstance(branch_architect, dict) and branch_architect else {}
    handoff_report = architect_handoff_report if isinstance(architect_handoff_report, dict) and architect_handoff_report else {}
    strategy = strategy_council if isinstance(strategy_council, dict) and strategy_council else {}

    if not architect:
        raise ValueError("REMPlan cannot compute safely without BranchArchitect.")
    if not handoff_report:
        raise ValueError("REMPlan requires architect_handoff_report.")
    if str(handoff_report.get("status") or "").strip() != "ready":
        raise ValueError(f"REMPlan handoff blocked: {str(handoff_report.get('reviewer_summary') or 'architect handoff is not ready').strip()}")

    evidence_start_points = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        dream_id = str(row.get("dream_id") or "").strip()
        process_id = str(row.get("process_id") or "").strip()
        if dream_id:
            evidence_start_points.append(f"Dream:{dream_id}")
        if process_id:
            evidence_start_points.append(f"TurnProcess:{process_id}")
        process_summary = self._normalize_phase_payload(row.get("process_summary"))
        if isinstance(process_summary, dict):
            for source_id in process_summary.get("used_sources", []) or []:
                normalized_source = str(source_id or "").strip()
                if normalized_source:
                    evidence_start_points.append(normalized_source)
        for snapshot in row.get("phase_snapshots") or []:
            if not isinstance(snapshot, dict):
                continue
            phase_name = str(snapshot.get("phase_name") or "").strip()
            if phase_name and process_id:
                evidence_start_points.append(f"Phase:{process_id}:{phase_name}")

    selected_branch_paths = self._dedupe_keep_order(
        list(handoff_report.get("selected_branch_paths", []) or [])
        or [
            str(item.get("branch_path") or "").strip()
            for item in (architect.get("branch_blueprints") or [])
            if isinstance(item, dict) and str(item.get("branch_path") or "").strip()
        ]
    )
    if not selected_branch_paths:
        raise ValueError("REMPlan execution requires selected_branch_paths.")

    strategy_scope = [
        dict(item)
        for item in (strategy.get("tonight_scope", []) or [])
        if isinstance(item, dict)
    ]
    selected_branch_paths = self._dedupe_keep_order(
        selected_branch_paths
        + [
            str(item.get("branch_path") or "").strip()
            for item in strategy_scope
            if str(item.get("branch_path") or "").strip()
        ]
    )

    target_roots = self._dedupe_keep_order(
        list(strategy.get("target_roots", []) or [])
        + list(handoff_report.get("target_roots", []) or [])
        or list(governor.get("root_entities", []) or [])
        or ["Person:stable", "CoreEgo:songryeon"]
    )
    create_targets = self._dedupe_keep_order(
        list(handoff_report.get("create_targets", []) or [])
        or list(architect.get("create_targets", []) or [])
    )
    update_targets = self._dedupe_keep_order(
        list(handoff_report.get("update_targets", []) or [])
        or list(architect.get("update_targets", []) or [])
    )
    evidence_start_points = self._dedupe_keep_order(
        evidence_start_points
        + [
            str(point or "").strip()
            for item in strategy_scope
            if isinstance(item, dict)
            for point in (item.get("evidence_start_points", []) or [])
            if str(point or "").strip()
        ]
        + list(architect.get("evidence_start_points", []) or [])
        + list(handoff_report.get("evidence_start_points", []) or [])
        + list(governor.get("evidence_roots", []) or [])
    )[:32]

    objective_parts = [
        str(strategy.get("remembered_self_summary") or "").strip(),
        str(strategy.get("planning_self_summary") or "").strip(),
        str(strategy.get("strategy_summary") or "").strip(),
        str(governor.get("governor_summary") or "").strip(),
        str(architect.get("objective_summary") or "").strip(),
        str(handoff_report.get("reviewer_summary") or "").strip(),
    ]
    objective_summary = " / ".join(part for part in objective_parts if part)
    if not objective_summary:
        objective_summary = "Run tonight's work from REMGovernor and BranchArchitect roots, branches, and evidence anchors."
    attention_titles = [
        str(item.get("title") or item.get("branch_path") or "").strip()
        for item in (strategy.get("attention_shortlist", []) or [])
        if isinstance(item, dict) and str(item.get("title") or item.get("branch_path") or "").strip()
    ]
    if attention_titles:
        objective_summary += " / Attention: " + ", ".join(attention_titles[:3])
    editorial_mandates = [
        str(item or "").strip()
        for item in (strategy.get("editorial_mandates", []) or [])
        if str(item or "").strip()
    ]
    if editorial_mandates:
        objective_summary += " / Mandates: " + " | ".join(editorial_mandates[:3])

    return REMPlanSchema(
        strategy_key=str(strategy.get("strategy_key") or ""),
        governor_key=str(governor.get("governor_key") or "rem_governor_v1"),
        architect_key=str(architect.get("architect_key") or f"{str(governor.get('governor_key') or 'rem_governor_v1')}::branch_architect_v1"),
        handoff_report_key=str(handoff_report.get("report_key") or ""),
        target_roots=target_roots,
        selected_branch_paths=selected_branch_paths,
        create_targets=create_targets,
        update_targets=update_targets,
        evidence_start_points=evidence_start_points,
        scope_keys=self._dedupe_keep_order([
            str(item.get("scope_key") or "").strip()
            for item in strategy_scope
            if str(item.get("scope_key") or "").strip()
        ]),
        next_night_handoff=self._dedupe_keep_order(list(strategy.get("next_night_handoff", []) or []))[:8],
        phase11_feedback=[],
        blocked_branch_paths=[],
        verification_requirements=[
            "Phase11 must emit SourceFactPair and FactLeafAudit records before BranchDigest/ConceptCluster growth.",
            "If no approved FactLeaf exists for a branch, return feedback instead of growing the branch.",
        ],
        report_target_phase=str(architect.get("report_target_phase") or governor.get("preferred_report_target") or "phase_9"),
        objective_summary=objective_summary,
        status="planned",
    ).model_dump()


def _attach_branch_growth_feedback_to_rem_plan(cls, rem_plan, branch_growth_report):
    if not isinstance(rem_plan, dict):
        rem_plan = {}
    if not isinstance(branch_growth_report, dict):
        branch_growth_report = {}
    enriched = dict(rem_plan)
    feedback = cls._dedupe_keep_order(
        list(enriched.get("phase11_feedback", []) or [])
        + list(branch_growth_report.get("rem_plan_feedback", []) or [])
        + list(branch_growth_report.get("rejection_reasons", []) or [])
    )
    blocked_branch_paths = cls._dedupe_keep_order(
        list(enriched.get("blocked_branch_paths", []) or [])
        + list(branch_growth_report.get("rejected_branch_paths", []) or [])
    )
    verification_requirements = cls._dedupe_keep_order(
        list(enriched.get("verification_requirements", []) or [])
        + [
            "Pair every emitted FactLeaf with a SourceFactPair before allowing branch growth.",
            "Treat branches with no approved FactLeaf as rejected, not merely empty.",
        ]
    )
    growth_status = str(branch_growth_report.get("growth_status") or "").strip()
    status = str(enriched.get("status") or "planned").strip() or "planned"
    if growth_status == "blocked":
        status = "blocked_by_phase11"
    elif growth_status == "partial" and status == "planned":
        status = "partial_with_phase11_feedback"
    enriched["phase11_feedback"] = feedback[:12]
    enriched["blocked_branch_paths"] = blocked_branch_paths[:12]
    enriched["verification_requirements"] = verification_requirements[:8]
    enriched["status"] = status
    return enriched
