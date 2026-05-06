import json

from Core.night_persistence_utils import link_both_roots, link_target_root


def persist_rem_governor_state(weaver, session, sd_id, rem_governor, rem_plan, graph_operations_log):
    if not isinstance(rem_governor, dict) or not rem_governor:
        return

    governor_key = str(rem_governor.get("governor_key") or "rem_governor_v1").strip() or "rem_governor_v1"
    session.run(
        """
        MATCH (sd:SecondDream {id: $sd_id})
        MERGE (rg:REMGovernorState {governor_key: $governor_key})
        SET rg.created_at = coalesce(rg.created_at, timestamp()),
            rg.updated_at = timestamp(),
            rg.name = 'REM 총괄',
            rg.batch_id = $sd_id,
            rg.root_entities = $root_entities,
            rg.root_descriptions = $root_descriptions,
            rg.root_profiles_json = $root_profiles_json,
            rg.root_profile_entities = $root_profile_entities,
            rg.root_inventory_json = $root_inventory_json,
            rg.root_inventory_count = toInteger($root_inventory_count),
            rg.policy_inventory_json = $policy_inventory_json,
            rg.policy_inventory_count = toInteger($policy_inventory_count),
            rg.known_branches = $known_branches,
            rg.required_branches = $required_branches,
            rg.branch_health = $branch_health,
            rg.open_unknowns = $open_unknowns,
            rg.priority_biases = $priority_biases,
            rg.branch_revision_rules = $branch_revision_rules,
            rg.policy_alignment_targets = $policy_alignment_targets,
            rg.evidence_roots = $evidence_roots,
            rg.last_growth_actions = $last_growth_actions,
            rg.governor_summary = $governor_summary,
            rg.preferred_report_target = $preferred_report_target,
            rg.status = $status
        MERGE (sd)-[:UPDATES_GOVERNOR]->(rg)
        """,
        sd_id=sd_id,
        governor_key=governor_key,
        root_entities=list(rem_governor.get("root_entities", []) or []),
        root_descriptions=list(rem_governor.get("root_descriptions", []) or []),
        root_profiles_json=json.dumps(list(rem_governor.get("root_profiles", []) or []), ensure_ascii=False),
        root_profile_entities=[
            str(profile.get("root_entity") or "").strip()
            for profile in (rem_governor.get("root_profiles", []) or [])
            if isinstance(profile, dict) and str(profile.get("root_entity") or "").strip()
        ],
        root_inventory_json=json.dumps(list(rem_governor.get("root_inventory", []) or []), ensure_ascii=False),
        root_inventory_count=len(list(rem_governor.get("root_inventory", []) or [])),
        policy_inventory_json=json.dumps(list(rem_governor.get("policy_inventory", []) or []), ensure_ascii=False),
        policy_inventory_count=len(list(rem_governor.get("policy_inventory", []) or [])),
        known_branches=list(rem_governor.get("known_branches", []) or []),
        required_branches=list(rem_governor.get("required_branches", []) or []),
        branch_health=list(rem_governor.get("branch_health", []) or []),
        open_unknowns=list(rem_governor.get("open_unknowns", []) or []),
        priority_biases=list(rem_governor.get("priority_biases", []) or []),
        branch_revision_rules=list(rem_governor.get("branch_revision_rules", []) or []),
        policy_alignment_targets=list(rem_governor.get("policy_alignment_targets", []) or []),
        evidence_roots=list(rem_governor.get("evidence_roots", []) or []),
        last_growth_actions=list(rem_governor.get("last_growth_actions", []) or []),
        governor_summary=str(rem_governor.get("governor_summary") or ""),
        preferred_report_target=str(rem_governor.get("preferred_report_target") or "phase_9"),
        status=str(rem_governor.get("status") or "active"),
    )

    link_both_roots(
        session,
        "MATCH (rg:REMGovernorState {governor_key: $governor_key})",
        "rg",
        {"governor_key": governor_key},
        rel_type="TRACKS_ROOT",
    )

    weaver._apply_governor_root_state_to_roots(session, rem_governor)

    branch_health_map = weaver._parse_branch_health_map(rem_governor)
    branch_paths = weaver._dedupe_keep_order(
        list(rem_governor.get("known_branches", []) or []) +
        list(rem_governor.get("required_branches", []) or []) +
        weaver._plan_branch_paths(rem_plan)
    )
    required_branches = set(str(item or "").strip() for item in rem_governor.get("required_branches", []) or [])
    for branch_path in branch_paths:
        normalized_branch = str(branch_path or "").strip()
        if not normalized_branch:
            continue
        branch_role = "required" if normalized_branch in required_branches else "known"
        health_hint = branch_health_map.get(normalized_branch, "unknown")
        root_entity, root_name_ko, root_rank = weaver._branch_root_info(normalized_branch)
        branch_title_ko = weaver._branch_title_ko(normalized_branch) or normalized_branch
        branch_depth = len([segment for segment in normalized_branch.split("/") if segment.strip()])
        session.run(
            """
            MATCH (rg:REMGovernorState {governor_key: $governor_key})
            MERGE (gb:GovernorBranch {governor_key: $governor_key, branch_path: $branch_path})
            SET gb.updated_at = timestamp(),
                gb.name = $branch_title_ko,
                gb.branch_title_ko = $branch_title_ko,
                gb.branch_role = $branch_role,
                gb.health_hint = $health_hint,
                gb.root_entity = $root_entity,
                gb.root_name_ko = $root_name_ko,
                gb.root_rank = toInteger($root_rank),
                gb.branch_depth = toInteger($branch_depth)
            MERGE (rg)-[:HAS_BRANCH]->(gb)
            """,
            governor_key=governor_key,
            branch_path=normalized_branch,
            branch_title_ko=branch_title_ko,
            branch_role=branch_role,
            health_hint=health_hint,
            root_entity=root_entity,
            root_name_ko=root_name_ko,
            root_rank=root_rank,
            branch_depth=branch_depth,
        )
        link_target_root(
            session,
            "MATCH (gb:GovernorBranch {governor_key: $governor_key, branch_path: $branch_path})",
            "gb",
            {"governor_key": governor_key, "branch_path": normalized_branch},
            root_entity,
        )

    graph_operations_log.append({"op": "REM_GOVERNOR", "key": governor_key})


def persist_branch_architect(weaver, session, sd_id, branch_architect, dreams, graph_operations_log):
    if not isinstance(branch_architect, dict) or not branch_architect:
        return

    architect_key = str(branch_architect.get("architect_key") or f"{sd_id}::branch_architect").strip()
    governor_key = str(branch_architect.get("governor_key") or "rem_governor_v1").strip() or "rem_governor_v1"
    session.run(
        """
        MATCH (sd:SecondDream {id: $sd_id})
        MERGE (ba:BranchArchitect {architect_key: $architect_key})
        SET ba.created_at = coalesce(ba.created_at, timestamp()),
            ba.updated_at = timestamp(),
            ba.name = '가지 설계자',
            ba.batch_id = $sd_id,
            ba.governor_key = $governor_key,
            ba.relay_notes = $relay_notes,
            ba.create_targets = $create_targets,
            ba.update_targets = $update_targets,
            ba.evidence_start_points = $evidence_start_points,
            ba.objective_summary = $objective_summary,
            ba.report_target_phase = $report_target_phase,
            ba.status = $status
        MERGE (sd)-[:USES_ARCHITECT]->(ba)
        """,
        sd_id=sd_id,
        architect_key=architect_key,
        governor_key=governor_key,
        relay_notes=list(branch_architect.get("relay_notes", []) or []),
        create_targets=list(branch_architect.get("create_targets", []) or []),
        update_targets=list(branch_architect.get("update_targets", []) or []),
        evidence_start_points=list(branch_architect.get("evidence_start_points", []) or []),
        objective_summary=str(branch_architect.get("objective_summary") or ""),
        report_target_phase=str(branch_architect.get("report_target_phase") or "phase_9"),
        status=str(branch_architect.get("status") or "active"),
    )

    session.run(
        """
        MATCH (ba:BranchArchitect {architect_key: $architect_key})
        MATCH (rg:REMGovernorState {governor_key: $governor_key})
        MERGE (ba)-[:FOLLOWS_GOVERNOR]->(rg)
        """,
        architect_key=architect_key,
        governor_key=governor_key,
    )

    handoff_report = branch_architect.get("architect_handoff_report", {}) if isinstance(branch_architect.get("architect_handoff_report"), dict) else {}
    if handoff_report:
        report_key = str(handoff_report.get("report_key") or f"{architect_key}::handoff").strip()
        session.run(
            """
            MATCH (ba:BranchArchitect {architect_key: $architect_key})
            MERGE (hr:ArchitectHandoffReport {report_key: $report_key})
            SET hr.created_at = coalesce(hr.created_at, timestamp()),
                hr.updated_at = timestamp(),
                hr.name = '가지 인수인계 감사',
                hr.batch_id = $sd_id,
                hr.governor_key = $governor_key,
                hr.architect_key = $architect_key,
                hr.target_roots = $target_roots,
                hr.selected_branch_paths = $selected_branch_paths,
                hr.create_targets = $create_targets,
                hr.update_targets = $update_targets,
                hr.evidence_start_points = $evidence_start_points,
                hr.preserved_constraints = $preserved_constraints,
                hr.translation_gaps = $translation_gaps,
                hr.intent_alignment = $intent_alignment,
                hr.reviewer_summary = $reviewer_summary,
                hr.status = $status
            MERGE (ba)-[:EMITS_HANDOFF]->(hr)
            """,
            sd_id=sd_id,
            architect_key=architect_key,
            report_key=report_key,
            governor_key=governor_key,
            target_roots=list(handoff_report.get("target_roots", []) or []),
            selected_branch_paths=list(handoff_report.get("selected_branch_paths", []) or []),
            create_targets=list(handoff_report.get("create_targets", []) or []),
            update_targets=list(handoff_report.get("update_targets", []) or []),
            evidence_start_points=list(handoff_report.get("evidence_start_points", []) or []),
            preserved_constraints=list(handoff_report.get("preserved_constraints", []) or []),
            translation_gaps=list(handoff_report.get("translation_gaps", []) or []),
            intent_alignment=str(handoff_report.get("intent_alignment") or "aligned"),
            reviewer_summary=str(handoff_report.get("reviewer_summary") or ""),
            status=str(handoff_report.get("status") or "ready"),
        )
        for root_entity in handoff_report.get("target_roots", []) or []:
            link_target_root(
                session,
                "MATCH (hr:ArchitectHandoffReport {report_key: $report_key})",
                "hr",
                {"report_key": report_key},
                root_entity,
            )
        graph_operations_log.append({"op": "ARCHITECT_HANDOFF", "key": report_key})

    for card in branch_architect.get("root_fact_cards", []) or []:
        if not isinstance(card, dict):
            continue
        root_entity = str(card.get("root_entity") or "").strip()
        link_target_root(
            session,
            "MATCH (ba:BranchArchitect {architect_key: $architect_key})",
            "ba",
            {"architect_key": architect_key},
            root_entity,
        )

    for idx, blueprint in enumerate(branch_architect.get("branch_blueprints", []) or []):
        if not isinstance(blueprint, dict):
            continue
        branch_path = str(blueprint.get("branch_path") or "").strip()
        if not branch_path:
            continue
        blueprint_key = f"{architect_key}::{idx}::{branch_path}"[:512]
        root_entity, root_name_ko, root_rank = weaver._branch_root_info(branch_path)
        branch_title_ko = weaver._branch_title_ko(branch_path) or str(blueprint.get("branch_title") or branch_path).strip()
        session.run(
            """
            MATCH (ba:BranchArchitect {architect_key: $architect_key})
            MERGE (bp:ArchitectBranchPlan {blueprint_key: $blueprint_key})
            SET bp.name = $branch_title_ko,
                bp.branch_path = $branch_path,
                bp.topic_slug = $topic_slug,
                bp.branch_title = $branch_title,
                bp.branch_title_ko = $branch_title_ko,
                bp.parent_root = $parent_root,
                bp.root_entity = $root_entity,
                bp.root_name_ko = $root_name_ko,
                bp.root_rank = toInteger($root_rank),
                bp.branch_kind = $branch_kind,
                bp.placement_reason = $placement_reason,
                bp.required_leaf_specs = $required_leaf_specs,
                bp.evidence_hints = $evidence_hints,
                bp.relay_target = $relay_target,
                bp.updated_at = timestamp()
            MERGE (ba)-[:HAS_BLUEPRINT]->(bp)
            """,
            architect_key=architect_key,
            blueprint_key=blueprint_key,
            branch_path=branch_path,
            topic_slug=str(blueprint.get("topic_slug") or "").strip(),
            branch_title=str(blueprint.get("branch_title") or "").strip(),
            branch_title_ko=branch_title_ko,
            parent_root=str(blueprint.get("parent_root") or "").strip(),
            root_entity=root_entity,
            root_name_ko=root_name_ko,
            root_rank=root_rank,
            branch_kind=str(blueprint.get("branch_kind") or "").strip(),
            placement_reason=str(blueprint.get("placement_reason") or "").strip(),
            required_leaf_specs=list(blueprint.get("required_leaf_specs", []) or []),
            evidence_hints=list(blueprint.get("evidence_hints", []) or []),
            relay_target=str(blueprint.get("relay_target") or "rem_plan"),
        )
        session.run(
            """
            MATCH (bp:ArchitectBranchPlan {blueprint_key: $blueprint_key})
            MATCH (gb:GovernorBranch {governor_key: $governor_key, branch_path: $branch_path})
            MERGE (bp)-[:FOLLOWS_BRANCH]->(gb)
            """,
            blueprint_key=blueprint_key,
            governor_key=governor_key,
            branch_path=branch_path,
        )
        link_target_root(
            session,
            "MATCH (bp:ArchitectBranchPlan {blueprint_key: $blueprint_key})",
            "bp",
            {"blueprint_key": blueprint_key},
            root_entity,
        )

    for dream in dreams or []:
        dream_id = str(dream.get("dream_id") or "").strip()
        if not dream_id:
            continue
        session.run(
            """
            MATCH (ba:BranchArchitect {architect_key: $architect_key})
            MATCH (d:Dream {id: $dream_id})
            MERGE (ba)-[:USES_DREAM]->(d)
            """,
            architect_key=architect_key,
            dream_id=dream_id,
        )

    graph_operations_log.append({"op": "BRANCH_ARCHITECT", "key": architect_key})


def persist_rem_plan(weaver, session, sd_id, rem_plan, dreams, graph_operations_log):
    if not isinstance(rem_plan, dict) or not rem_plan:
        return

    rem_plan_id = f"{sd_id}::rem_plan"
    session.run(
        """
        MATCH (sd:SecondDream {id: $sd_id})
        MERGE (rp:REMPlan {id: $rem_plan_id})
        SET rp.created_at = coalesce(rp.created_at, timestamp()),
            rp.name = 'REM 실행 계획',
            rp.batch_id = $sd_id,
            rp.strategy_key = $strategy_key,
            rp.governor_key = $governor_key,
            rp.architect_key = $architect_key,
            rp.handoff_report_key = $handoff_report_key,
            rp.target_roots = $target_roots,
            rp.selected_branch_paths = $selected_branch_paths,
            rp.create_targets = $create_targets,
            rp.update_targets = $update_targets,
            rp.evidence_start_points = $evidence_start_points,
            rp.scope_keys = $scope_keys,
            rp.next_night_handoff = $next_night_handoff,
            rp.phase11_feedback = $phase11_feedback,
            rp.blocked_branch_paths = $blocked_branch_paths,
            rp.verification_requirements = $verification_requirements,
            rp.report_target_phase = $report_target_phase,
            rp.objective_summary = $objective_summary,
            rp.status = $status
        MERGE (sd)-[:USES_PLAN]->(rp)
        """,
        sd_id=sd_id,
        rem_plan_id=rem_plan_id,
        strategy_key=str(rem_plan.get("strategy_key") or ""),
        governor_key=str(rem_plan.get("governor_key") or "rem_governor_v1"),
        architect_key=str(rem_plan.get("architect_key") or ""),
        handoff_report_key=str(rem_plan.get("handoff_report_key") or ""),
        target_roots=list(rem_plan.get("target_roots", []) or []),
        selected_branch_paths=list(rem_plan.get("selected_branch_paths", []) or []),
        create_targets=list(rem_plan.get("create_targets", []) or []),
        update_targets=list(rem_plan.get("update_targets", []) or []),
        evidence_start_points=list(rem_plan.get("evidence_start_points", []) or []),
        scope_keys=list(rem_plan.get("scope_keys", []) or []),
        next_night_handoff=list(rem_plan.get("next_night_handoff", []) or []),
        phase11_feedback=list(rem_plan.get("phase11_feedback", []) or []),
        blocked_branch_paths=list(rem_plan.get("blocked_branch_paths", []) or []),
        verification_requirements=list(rem_plan.get("verification_requirements", []) or []),
        report_target_phase=str(rem_plan.get("report_target_phase") or "phase_9"),
        objective_summary=str(rem_plan.get("objective_summary") or ""),
        status=str(rem_plan.get("status") or "planned"),
    )

    link_both_roots(
        session,
        "MATCH (rp:REMPlan {id: $rem_plan_id})",
        "rp",
        {"rem_plan_id": rem_plan_id},
    )

    session.run(
        """
        MATCH (rp:REMPlan {id: $rem_plan_id})
        MATCH (rg:REMGovernorState {governor_key: $governor_key})
        MERGE (rp)-[:FOLLOWS_GOVERNOR]->(rg)
        """,
        rem_plan_id=rem_plan_id,
        governor_key=str(rem_plan.get("governor_key") or "rem_governor_v1"),
    )

    session.run(
        """
        MATCH (rp:REMPlan {id: $rem_plan_id})
        MATCH (ba:BranchArchitect {architect_key: $architect_key})
        MERGE (rp)-[:FOLLOWS_ARCHITECT]->(ba)
        """,
        rem_plan_id=rem_plan_id,
        architect_key=str(rem_plan.get("architect_key") or f"{str(rem_plan.get('governor_key') or 'rem_governor_v1')}::branch_architect_v1"),
    )

    handoff_report_key = str(rem_plan.get("handoff_report_key") or "").strip()
    if handoff_report_key:
        session.run(
            """
            MATCH (rp:REMPlan {id: $rem_plan_id})
            MATCH (hr:ArchitectHandoffReport {report_key: $handoff_report_key})
            MERGE (rp)-[:FOLLOWS_HANDOFF]->(hr)
            """,
            rem_plan_id=rem_plan_id,
            handoff_report_key=handoff_report_key,
        )

    strategy_key = str(rem_plan.get("strategy_key") or "").strip()
    if strategy_key:
        session.run(
            """
            MATCH (rp:REMPlan {id: $rem_plan_id})
            MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})
            MERGE (rp)-[:FOLLOWS_STRATEGY]->(sc)
            """,
            rem_plan_id=rem_plan_id,
            strategy_key=strategy_key,
        )
    for scope_key in rem_plan.get("scope_keys", []) or []:
        normalized_scope_key = str(scope_key or "").strip()
        if not normalized_scope_key:
            continue
        session.run(
            """
            MATCH (rp:REMPlan {id: $rem_plan_id})
            MATCH (ns:NightlyScope {scope_key: $scope_key})
            MERGE (rp)-[:USES_SCOPE]->(ns)
            """,
            rem_plan_id=rem_plan_id,
            scope_key=normalized_scope_key,
        )

    for branch_path in weaver._plan_branch_paths(rem_plan):
        normalized_branch = str(branch_path or "").strip()
        if not normalized_branch:
            continue
        session.run(
            """
            MATCH (rp:REMPlan {id: $rem_plan_id})
            MATCH (gb:GovernorBranch {governor_key: $governor_key, branch_path: $branch_path})
            MERGE (rp)-[:FOLLOWS_BRANCH]->(gb)
            """,
            rem_plan_id=rem_plan_id,
            governor_key=str(rem_plan.get("governor_key") or "rem_governor_v1"),
            branch_path=normalized_branch,
        )

    for dream in dreams or []:
        dream_id = str(dream.get("dream_id") or "").strip()
        process_id = str(dream.get("process_id") or "").strip()
        if dream_id:
            session.run(
                """
                MATCH (rp:REMPlan {id: $rem_plan_id})
                MATCH (d:Dream {id: $dream_id})
                MERGE (rp)-[:USES_DREAM]->(d)
                """,
                rem_plan_id=rem_plan_id,
                dream_id=dream_id,
            )
        if process_id:
            session.run(
                """
                MATCH (rp:REMPlan {id: $rem_plan_id})
                MATCH (tp:TurnProcess {id: $process_id})
                MERGE (rp)-[:USES_PROCESS]->(tp)
                """,
                rem_plan_id=rem_plan_id,
                process_id=process_id,
            )
        for snapshot in dream.get("phase_snapshots") or []:
            if not isinstance(snapshot, dict) or not process_id:
                continue
            phase_name = str(snapshot.get("phase_name") or "").strip()
            phase_order = int(snapshot.get("phase_order", 0) or 0)
            if not phase_name:
                continue
            snapshot_id = f"{process_id}:{phase_order}:{phase_name}"
            session.run(
                """
                MATCH (rp:REMPlan {id: $rem_plan_id})
                MATCH (ps:PhaseSnapshot {id: $snapshot_id})
                MERGE (rp)-[:USES_PHASE]->(ps)
                """,
                rem_plan_id=rem_plan_id,
                snapshot_id=snapshot_id,
            )

    for topic_slug in weaver._plan_topics(rem_plan):
        normalized_topic_slug = str(topic_slug or "").strip()
        if not normalized_topic_slug:
            continue
        session.run(
            """
            MATCH (rp:REMPlan {id: $rem_plan_id})
            MERGE (tt:SupplyTopic {slug: $topic_slug})
            SET tt.batch_id = coalesce(tt.batch_id, $sd_id)
            MERGE (rp)-[:TRACKS_TOPIC]->(tt)
            """,
            rem_plan_id=rem_plan_id,
            topic_slug=normalized_topic_slug,
            sd_id=sd_id,
        )

    graph_operations_log.append({"op": "REM_PLAN", "id": rem_plan_id})
