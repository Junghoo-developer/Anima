import json

from Core.night_persistence_utils import link_target_root


def persist_strategy_council(weaver, session, sd_id, strategy_council, graph_operations_log):
    if not isinstance(strategy_council, dict) or not strategy_council:
        return

    strategy_key = str(strategy_council.get("strategy_key") or "strategy_council_v1").strip() or "strategy_council_v1"
    governor_key = str(strategy_council.get("governor_key") or "rem_governor_v1").strip() or "rem_governor_v1"
    session.run(
        """
        MATCH (sd:SecondDream {id: $sd_id})
        MERGE (sc:StrategyCouncil {strategy_key: $strategy_key})
        SET sc.created_at = coalesce(sc.created_at, timestamp()),
            sc.updated_at = timestamp(),
            sc.name = '전략 의회',
            sc.batch_id = $sd_id,
            sc.governor_key = $governor_key,
            sc.target_roots = $target_roots,
            sc.goal_tree_json = $goal_tree_json,
            sc.goal_gaps_json = $goal_gaps_json,
            sc.tonight_scope_json = $tonight_scope_json,
            sc.child_branch_proposals_json = $child_branch_proposals_json,
            sc.proposal_decisions_json = $proposal_decisions_json,
            sc.attention_shortlist_json = $attention_shortlist_json,
            sc.remembered_self_summary = $remembered_self_summary,
            sc.planning_self_summary = $planning_self_summary,
            sc.editorial_mandates = $editorial_mandates,
            sc.scope_budget_json = $scope_budget_json,
            sc.planning_horizon = $planning_horizon,
            sc.strategy_summary = $strategy_summary,
            sc.next_night_handoff = $next_night_handoff,
            sc.status = $status
        MERGE (sd)-[:UPDATES_STRATEGY]->(sc)
        """,
        sd_id=sd_id,
        strategy_key=strategy_key,
        governor_key=governor_key,
        target_roots=list(strategy_council.get("target_roots", []) or []),
        goal_tree_json=json.dumps(list(strategy_council.get("goal_tree", []) or []), ensure_ascii=False),
        goal_gaps_json=json.dumps(list(strategy_council.get("goal_gaps", []) or []), ensure_ascii=False),
        tonight_scope_json=json.dumps(list(strategy_council.get("tonight_scope", []) or []), ensure_ascii=False),
        child_branch_proposals_json=json.dumps(list(strategy_council.get("child_branch_proposals", []) or []), ensure_ascii=False),
        proposal_decisions_json=json.dumps(list(strategy_council.get("proposal_decisions", []) or []), ensure_ascii=False),
        attention_shortlist_json=json.dumps(list(strategy_council.get("attention_shortlist", []) or []), ensure_ascii=False),
        remembered_self_summary=str(strategy_council.get("remembered_self_summary") or ""),
        planning_self_summary=str(strategy_council.get("planning_self_summary") or ""),
        editorial_mandates=list(strategy_council.get("editorial_mandates", []) or []),
        scope_budget_json=json.dumps(dict(strategy_council.get("scope_budget", {}) or {}), ensure_ascii=False),
        planning_horizon=str(strategy_council.get("planning_horizon") or "rolling_3_nights"),
        strategy_summary=str(strategy_council.get("strategy_summary") or ""),
        next_night_handoff=list(strategy_council.get("next_night_handoff", []) or []),
        status=str(strategy_council.get("status") or "active"),
    )
    session.run(
        """
        MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})-[r:ATTENDS_TO_DIGEST]->(:BranchDigest)
        DELETE r
        """,
        strategy_key=strategy_key,
    )
    session.run(
        """
        MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})-[r:ATTENDS_TO_CLUSTER]->(:ConceptCluster)
        DELETE r
        """,
        strategy_key=strategy_key,
    )
    session.run(
        """
        MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})
        MATCH (rg:REMGovernorState {governor_key: $governor_key})
        MERGE (sc)-[:GUIDES_GOVERNOR]->(rg)
        """,
        strategy_key=strategy_key,
        governor_key=governor_key,
    )

    for root_entity in strategy_council.get("target_roots", []) or []:
        link_target_root(
            session,
            "MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})",
            "sc",
            {"strategy_key": strategy_key},
            root_entity,
        )

    for goal in strategy_council.get("goal_tree", []) or []:
        if not isinstance(goal, dict):
            continue
        goal_key = str(goal.get("goal_key") or "").strip()
        if not goal_key:
            continue
        root_entity = str(goal.get("root_entity") or "").strip()
        session.run(
            """
            MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})
            MERGE (gt:GoalTree {goal_key: $goal_key})
            SET gt.updated_at = timestamp(),
                gt.name = $title,
                gt.root_entity = $root_entity,
                gt.summary = $summary,
                gt.goal_type = $goal_type,
                gt.branch_paths = $branch_paths,
                gt.priority_weight = toFloat($priority_weight),
                gt.status = $status
            MERGE (sc)-[:HAS_GOAL]->(gt)
            """,
            strategy_key=strategy_key,
            goal_key=goal_key,
            title=str(goal.get("title") or goal_key),
            root_entity=root_entity,
            summary=str(goal.get("summary") or ""),
            goal_type=str(goal.get("goal_type") or "refine"),
            branch_paths=list(goal.get("branch_paths", []) or []),
            priority_weight=float(goal.get("priority_weight", 0.5) or 0.5),
            status=str(goal.get("status") or "active"),
        )
        link_target_root(
            session,
            "MATCH (gt:GoalTree {goal_key: $goal_key})",
            "gt",
            {"goal_key": goal_key},
            root_entity,
        )
        for branch_path in goal.get("branch_paths", []) or []:
            normalized_branch = str(branch_path or "").strip()
            if not normalized_branch:
                continue
            session.run(
                """
                MATCH (gt:GoalTree {goal_key: $goal_key})
                MATCH (gb:GovernorBranch {governor_key: $governor_key, branch_path: $branch_path})
                MERGE (gt)-[:FOLLOWS_BRANCH]->(gb)
                """,
                goal_key=goal_key,
                governor_key=governor_key,
                branch_path=normalized_branch,
            )

    for gap in strategy_council.get("goal_gaps", []) or []:
        if not isinstance(gap, dict):
            continue
        gap_key = str(gap.get("gap_key") or "").strip()
        if not gap_key:
            continue
        root_entity = str(gap.get("root_entity") or "").strip()
        branch_path = str(gap.get("branch_path") or "").strip()
        session.run(
            """
            MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})
            MERGE (gg:GoalGap {gap_key: $gap_key})
            SET gg.updated_at = timestamp(),
                gg.name = $title,
                gg.root_entity = $root_entity,
                gg.branch_path = $branch_path,
                gg.summary = $summary,
                gg.severity = $severity,
                gg.evidence_roots = $evidence_roots,
                gg.status = $status
            MERGE (sc)-[:DETECTS_GAP]->(gg)
            """,
            strategy_key=strategy_key,
            gap_key=gap_key,
            title=str(gap.get("title") or gap_key),
            root_entity=root_entity,
            branch_path=branch_path,
            summary=str(gap.get("summary") or ""),
            severity=str(gap.get("severity") or "medium"),
            evidence_roots=list(gap.get("evidence_roots", []) or []),
            status=str(gap.get("status") or "open"),
        )
        if branch_path:
            session.run(
                """
                MATCH (gg:GoalGap {gap_key: $gap_key})
                MATCH (gb:GovernorBranch {governor_key: $governor_key, branch_path: $branch_path})
                MERGE (gg)-[:FOLLOWS_BRANCH]->(gb)
                """,
                gap_key=gap_key,
                governor_key=governor_key,
                branch_path=branch_path,
            )

    for scope in strategy_council.get("tonight_scope", []) or []:
        if not isinstance(scope, dict):
            continue
        scope_key = str(scope.get("scope_key") or "").strip()
        branch_path = str(scope.get("branch_path") or "").strip()
        root_entity = str(scope.get("root_entity") or "").strip()
        if not scope_key:
            continue
        session.run(
            """
            MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})
            MERGE (ns:NightlyScope {scope_key: $scope_key})
            SET ns.updated_at = timestamp(),
                ns.name = $scope_name,
                ns.root_entity = $root_entity,
                ns.branch_path = $branch_path,
                ns.scope_reason = $scope_reason,
                ns.target_action = $target_action,
                ns.evidence_start_points = $evidence_start_points,
                ns.priority_weight = toFloat($priority_weight),
                ns.status = $status
            MERGE (sc)-[:SETS_SCOPE]->(ns)
            """,
            strategy_key=strategy_key,
            scope_key=scope_key,
            scope_name=weaver._branch_title_ko(branch_path) or scope_key,
            root_entity=root_entity,
            branch_path=branch_path,
            scope_reason=str(scope.get("scope_reason") or ""),
            target_action=str(scope.get("target_action") or "refresh"),
            evidence_start_points=list(scope.get("evidence_start_points", []) or []),
            priority_weight=float(scope.get("priority_weight", 0.5) or 0.5),
            status=str(scope.get("status") or "planned"),
        )
        if branch_path:
            session.run(
                """
                MATCH (ns:NightlyScope {scope_key: $scope_key})
                MATCH (gb:GovernorBranch {governor_key: $governor_key, branch_path: $branch_path})
                MERGE (ns)-[:FOLLOWS_BRANCH]->(gb)
                """,
                scope_key=scope_key,
                governor_key=governor_key,
                branch_path=branch_path,
            )
        link_target_root(
            session,
            "MATCH (ns:NightlyScope {scope_key: $scope_key})",
            "ns",
            {"scope_key": scope_key},
            root_entity,
        )

    for proposal in strategy_council.get("child_branch_proposals", []) or []:
        if not isinstance(proposal, dict):
            continue
        proposal_key = str(proposal.get("proposal_key") or "").strip()
        proposed_branch_path = str(proposal.get("proposed_branch_path") or "").strip()
        parent_branch_path = str(proposal.get("parent_branch_path") or "").strip()
        root_entity = str(proposal.get("root_entity") or weaver._root_entity_from_asset_scope(parent_branch_path)).strip()
        if not proposal_key or not proposed_branch_path:
            continue
        session.run(
            """
            MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})
            MERGE (cbp:ChildBranchProposal {proposal_key: $proposal_key})
            SET cbp.updated_at = timestamp(),
                cbp.name = $proposal_name,
                cbp.parent_branch_path = $parent_branch_path,
                cbp.proposed_branch_path = $proposed_branch_path,
                cbp.root_entity = $root_entity,
                cbp.topic_slug = $topic_slug,
                cbp.proposal_reason = $proposal_reason,
                cbp.pressure_score = toFloat($pressure_score),
                cbp.evidence_start_points = $evidence_start_points,
                cbp.trigger_notes = $trigger_notes,
                cbp.status = $status
            MERGE (sc)-[:PROPOSES_CHILD_BRANCH]->(cbp)
            """,
            strategy_key=strategy_key,
            proposal_key=proposal_key,
            proposal_name=weaver._branch_title_ko(proposed_branch_path) or proposed_branch_path,
            parent_branch_path=parent_branch_path,
            proposed_branch_path=proposed_branch_path,
            root_entity=root_entity,
            topic_slug=str(proposal.get("topic_slug") or "").strip(),
            proposal_reason=str(proposal.get("proposal_reason") or ""),
            pressure_score=float(proposal.get("pressure_score", 0.5) or 0.5),
            evidence_start_points=list(proposal.get("evidence_start_points", []) or []),
            trigger_notes=list(proposal.get("trigger_notes", []) or []),
            status=str(proposal.get("status") or "proposed"),
        )
        if parent_branch_path:
            session.run(
                """
                MATCH (cbp:ChildBranchProposal {proposal_key: $proposal_key})
                MATCH (gb:GovernorBranch {governor_key: $governor_key, branch_path: $parent_branch_path})
                MERGE (cbp)-[:EXTENDS_BRANCH]->(gb)
                """,
                proposal_key=proposal_key,
                governor_key=governor_key,
                parent_branch_path=parent_branch_path,
            )
        link_target_root(
            session,
            "MATCH (cbp:ChildBranchProposal {proposal_key: $proposal_key})",
            "cbp",
            {"proposal_key": proposal_key},
            root_entity,
        )

    graph_operations_log.append({"op": "STRATEGY_COUNCIL", "key": strategy_key})
