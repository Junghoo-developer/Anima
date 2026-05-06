from Core.night_persistence_utils import link_target_root


def merge_topic_hierarchy(session, sd_id, topics):
    graph_ops = []
    for topic in topics:
        if topic.get("supply_sufficient"):
            continue
        slug = (topic.get("topic_slug") or "").strip()
        title = (topic.get("title") or slug).strip()
        anti_z = (topic.get("dynamic_anti_z") or "미상").strip()
        y_axis = (topic.get("dynamic_y_axis") or "미상").strip()

        parent_slug = topic.get("parent_topic_slug")
        if isinstance(parent_slug, str):
            parent_slug = parent_slug.strip() or None
        else:
            parent_slug = None

        session.run(
            """
            MATCH (sd:SecondDream {id: $sd_id})
            MERGE (tt:SupplyTopic {slug: $slug})
            SET tt.title = coalesce(tt.title, $title),
                tt.status = coalesce(tt.status, 'unfulfilled'),
                tt.anti_z = coalesce(tt.anti_z, $anti_z),
                tt.y_axis = coalesce(tt.y_axis, $y_axis),
                tt.batch_id = $sd_id
            MERGE (sd)-[:TRACKS_TOPIC]->(tt)
            """,
            slug=slug,
            title=title,
            anti_z=anti_z,
            y_axis=y_axis,
            sd_id=sd_id,
        )
        graph_ops.append({"op": "MERGE_SUPPL_TOPIC", "slug": slug, "parent": parent_slug})

        if parent_slug:
            session.run(
                """
                MATCH (sd:SecondDream {id: $sd_id})
                MERGE (pt:SupplyTopic {slug: $ps})
                SET pt.batch_id = $sd_id
                MERGE (ch:SupplyTopic {slug: $cs})
                MERGE (ch)-[:SUBTOPIC_OF]->(pt)
                MERGE (sd)-[:TRACKS_TOPIC]->(pt)
                """,
                ps=parent_slug,
                cs=slug,
                sd_id=sd_id,
            )
            graph_ops.append({"op": "SUBTOPIC_OF", "child": slug, "parent": parent_slug})
    return graph_ops


def forge_tactical_thoughts_neo4j(weaver, session, sd_id, p9, dream_ids, graph_operations_log, rem_plan=None, phase_7=None):
    if not p9 or not p9.get("is_valuable_tactics"):
        graph_operations_log.append({"op": "PHASE9_SKIP", "reason": "is_valuable_tactics false or empty"})
        return
    items = weaver._normalize_tactical_cards(
        p9 if isinstance(p9, dict) else {},
        rem_plan if isinstance(rem_plan, dict) else {},
        phase_7 if isinstance(phase_7, dict) else {},
    )
    if not items:
        graph_operations_log.append({"op": "PHASE9_SKIP", "reason": "no tactical_thoughts"})
        return

    for idx, tac in enumerate(items):
        tid = str(tac.get("tactic_key") or f"{sd_id}_tac_{idx}")[:500]
        trig = (tac.get("situation_trigger") or "").strip()
        rule = (tac.get("actionable_rule") or "").strip()
        if not rule:
            continue
        try:
            priority_weight = float(tac.get("priority_weight", 5.0))
        except (TypeError, ValueError):
            priority_weight = 5.0
        phase = str(tac.get("applies_to_phase") or "0")
        target_family = str(tac.get("target_family") or "").strip()
        root_scope = str(tac.get("root_scope") or "").strip()
        branch_scope = str(tac.get("branch_scope") or "").strip()
        preferred_next_hop = str(tac.get("preferred_next_hop") or "").strip()
        preferred_direct_strategy = str(tac.get("preferred_direct_strategy") or "").strip()
        tone_recipe = str(tac.get("tone_recipe") or "").strip()
        repair_recipe = str(tac.get("repair_recipe") or "").strip()
        try:
            confidence_gate = float(tac.get("confidence_gate", 0.55))
        except (TypeError, ValueError):
            confidence_gate = 0.55

        session.run(
            """
            MATCH (ego:CoreEgo {name: '송련'})
            MERGE (t:TacticalThought {id: $tid})
            SET t.situation_trigger = $trig,
                t.name = $name,
                t.actionable_rule = $rule,
                t.priority_weight = toFloat($priority_weight),
                t.applies_to_phase = $phase,
                t.target_family = $target_family,
                t.root_scope = $root_scope,
                t.branch_scope = $branch_scope,
                t.semantic_signals = $semantic_signals,
                t.preferred_next_hop = $preferred_next_hop,
                t.preferred_direct_strategy = $preferred_direct_strategy,
                t.preferred_tools = $preferred_tools,
                t.disallowed_tools = $disallowed_tools,
                t.tone_recipe = $tone_recipe,
                t.must_include = $must_include,
                t.must_avoid = $must_avoid,
                t.repair_recipe = $repair_recipe,
                t.evidence_priority = $evidence_priority,
                t.confidence_gate = toFloat($confidence_gate),
                t.status = $status,
                t.created_at = timestamp(),
                t.batch_id = $sd_id
            MERGE (ego)-[:ORDERS_TACTIC]->(t)
            """,
            tid=tid,
            trig=trig,
            name=weaver._topic_label_ko(target_family) or "전술 카드",
            rule=rule,
            priority_weight=priority_weight,
            phase=phase,
            target_family=target_family,
            root_scope=root_scope,
            branch_scope=branch_scope,
            semantic_signals=list(tac.get("semantic_signals", []) or []),
            preferred_next_hop=preferred_next_hop,
            preferred_direct_strategy=preferred_direct_strategy,
            preferred_tools=list(tac.get("preferred_tools", []) or []),
            disallowed_tools=list(tac.get("disallowed_tools", []) or []),
            tone_recipe=tone_recipe,
            must_include=list(tac.get("must_include", []) or []),
            must_avoid=list(tac.get("must_avoid", []) or []),
            repair_recipe=repair_recipe,
            evidence_priority=list(tac.get("evidence_priority", []) or []),
            confidence_gate=confidence_gate,
            status=str(tac.get("status") or "active"),
            sd_id=sd_id,
        )
        session.run(
            """
            MATCH (t:TacticalThought {id: $tid})
            MATCH (sd:SecondDream {id: $sd_id})
            MERGE (t)-[:FORGED_IN]->(sd)
            """,
            tid=tid,
            sd_id=sd_id,
        )
        for dream_id in dream_ids:
            if not dream_id:
                continue
            session.run(
                """
                MATCH (t:TacticalThought {id: $tid})
                MATCH (d:Dream {id: $dream_id})
                MERGE (t)-[:GROUNDED_IN]->(d)
                """,
                tid=tid,
                dream_id=dream_id,
            )
        normalized_branch_scope = weaver._normalize_branch_path_to_existing_roots(branch_scope)
        if normalized_branch_scope:
            session.run(
                """
                MATCH (t:TacticalThought {id: $tid})
                MATCH (gb:GovernorBranch {governor_key: 'rem_governor_v1', branch_path: $branch_path})
                MERGE (t)-[:FOLLOWS_BRANCH]->(gb)
                MERGE (gb)-[:HAS_TACTIC]->(t)
                """,
                tid=tid,
                branch_path=normalized_branch_scope,
            )
        root_entity = weaver._root_entity_from_asset_scope(normalized_branch_scope, root_scope)
        link_target_root(
            session,
            "MATCH (t:TacticalThought {id: $tid})",
            "t",
            {"tid": tid},
            root_entity,
        )
        if normalized_branch_scope or target_family:
            session.run(
                """
                MATCH (t:TacticalThought {id: $tid})
                CALL (t) {
                  MATCH (prior:TacticalThought)
                  WHERE prior.id <> $tid
                    AND coalesce(prior.status, 'active') = 'active'
                    AND (
                      ($branch_scope <> '' AND prior.branch_scope = $branch_scope)
                      OR ($target_family <> '' AND prior.target_family = $target_family)
                    )
                  RETURN prior
                  ORDER BY coalesce(prior.created_at, 0) DESC
                  LIMIT 3
                }
                MERGE (t)-[:REFINES_TACTIC]->(prior)
                """,
                tid=tid,
                branch_scope=normalized_branch_scope,
                target_family=target_family,
            )
        graph_operations_log.append({"op": "TACTICAL_THOUGHT", "id": tid})
