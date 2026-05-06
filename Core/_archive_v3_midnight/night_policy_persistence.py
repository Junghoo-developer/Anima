from Core.night_persistence_utils import link_target_root


def persist_route_policies(weaver, session, sd_id, route_policies, graph_operations_log):
    for policy in route_policies or []:
        if not isinstance(policy, dict):
            continue
        policy_key = str(policy.get("policy_key") or "").strip()
        if not policy_key:
            continue

        target_family = str(policy.get("turn_family") or "").strip()
        branch_path = weaver._normalize_branch_path_to_existing_roots(
            weaver._branch_path_for_topic(target_family) if target_family else ""
        )
        root_entity = weaver._root_entity_from_asset_scope(branch_path)
        compiled_from_tactic_key = str(policy.get("compiled_from_tactic_key") or "").strip()

        session.run(
            """
            MATCH (sd:SecondDream {id: $sd_id})
            MERGE (rp:RoutePolicy {policy_key: $policy_key})
            SET rp.created_at = coalesce(rp.created_at, timestamp()),
                rp.name = $policy_name_ko,
                rp.batch_id = $sd_id,
                rp.turn_family = $turn_family,
                rp.answer_shape_hint = $answer_shape_hint,
                rp.trigger_signals = $trigger_signals,
                rp.preferred_next_hop = $preferred_next_hop,
                rp.fallback_next_hop = $fallback_next_hop,
                rp.preferred_direct_strategy = $preferred_direct_strategy,
                rp.requires_grounding = $requires_grounding,
                rp.requires_recent_context = $requires_recent_context,
                rp.requires_active_offer = $requires_active_offer,
                rp.requires_history_scope = $requires_history_scope,
                rp.router_mode = $router_mode,
                rp.match_priority = toFloat($match_priority),
                rp.confidence_gate = toFloat($confidence_gate),
                rp.rationale = $rationale,
                rp.compiled_from_tactic_key = $compiled_from_tactic_key,
                rp.policy_source = $policy_source,
                rp.status = $status
            MERGE (sd)-[:UPDATES_POLICY]->(rp)
            """,
            sd_id=sd_id,
            policy_key=policy_key,
            policy_name_ko=f"라우트 정책::{str(policy.get('turn_family') or 'unknown').strip() or 'unknown'}",
            turn_family=target_family,
            answer_shape_hint=str(policy.get("answer_shape_hint") or ""),
            trigger_signals=list(policy.get("trigger_signals", []) or []),
            preferred_next_hop=str(policy.get("preferred_next_hop") or ""),
            fallback_next_hop=str(policy.get("fallback_next_hop") or ""),
            preferred_direct_strategy=str(policy.get("preferred_direct_strategy") or ""),
            requires_grounding=bool(policy.get("requires_grounding")),
            requires_recent_context=bool(policy.get("requires_recent_context")),
            requires_active_offer=bool(policy.get("requires_active_offer")),
            requires_history_scope=bool(policy.get("requires_history_scope")),
            router_mode=str(policy.get("router_mode") or "policy_first"),
            match_priority=float(policy.get("match_priority", 0.5) or 0.5),
            confidence_gate=float(policy.get("confidence_gate", 0.0) or 0.0),
            rationale=str(policy.get("rationale") or ""),
            compiled_from_tactic_key=compiled_from_tactic_key,
            policy_source=str(policy.get("policy_source") or "nightly_reflection"),
            status=str(policy.get("status") or "active"),
        )

        if branch_path:
            session.run(
                """
                MATCH (rp:RoutePolicy {policy_key: $policy_key})
                MATCH (gb:GovernorBranch {governor_key: 'rem_governor_v1', branch_path: $branch_path})
                MERGE (rp)-[:FOLLOWS_BRANCH]->(gb)
                MERGE (gb)-[:HAS_POLICY]->(rp)
                """,
                policy_key=policy_key,
                branch_path=branch_path,
            )

        link_target_root(
            session,
            "MATCH (rp:RoutePolicy {policy_key: $policy_key})",
            "rp",
            {"policy_key": policy_key},
            root_entity,
        )

        if compiled_from_tactic_key:
            session.run(
                """
                MATCH (t:TacticalThought {id: $tactic_key})
                MATCH (rp:RoutePolicy {policy_key: $policy_key})
                MERGE (t)-[:UPDATES_POLICY]->(rp)
                """,
                tactic_key=compiled_from_tactic_key,
                policy_key=policy_key,
            )

        graph_operations_log.append({"op": "ROUTE_POLICY", "key": policy_key})


def persist_tool_doctrines(weaver, session, sd_id, tool_doctrines, graph_operations_log):
    for doctrine in tool_doctrines or []:
        if not isinstance(doctrine, dict):
            continue
        doctrine_key = str(doctrine.get("doctrine_key") or "").strip()
        if not doctrine_key:
            continue

        target_family = str(doctrine.get("target_family") or "").strip()
        branch_path = weaver._normalize_branch_path_to_existing_roots(
            weaver._branch_path_for_topic(target_family) if target_family else ""
        )
        root_entity = weaver._root_entity_from_asset_scope(branch_path)
        compiled_from_tactic_key = str(doctrine.get("compiled_from_tactic_key") or "").strip()

        session.run(
            """
            MATCH (sd:SecondDream {id: $sd_id})
            MERGE (td:ToolDoctrine {doctrine_key: $doctrine_key})
            SET td.created_at = coalesce(td.created_at, timestamp()),
                td.name = $doctrine_name_ko,
                td.batch_id = $sd_id,
                td.target_family = $target_family,
                td.recommended_tools = $recommended_tools,
                td.tool_order = $tool_order,
                td.query_rewrite_rules = $query_rewrite_rules,
                td.source_priority = $source_priority,
                td.avoid_patterns = $avoid_patterns,
                td.success_signals = $success_signals,
                td.failure_signals = $failure_signals,
                td.execution_mode = $execution_mode,
                td.rationale = $rationale,
                td.compiled_from_tactic_key = $compiled_from_tactic_key,
                td.policy_source = $policy_source,
                td.status = $status
            MERGE (sd)-[:UPDATES_DOCTRINE]->(td)
            """,
            sd_id=sd_id,
            doctrine_key=doctrine_key,
            doctrine_name_ko=f"도구 교리::{str(doctrine.get('target_family') or 'unknown').strip() or 'unknown'}",
            target_family=target_family,
            recommended_tools=list(doctrine.get("recommended_tools", []) or []),
            tool_order=list(doctrine.get("tool_order", []) or []),
            query_rewrite_rules=["keep root-first retrieval"],
            source_priority=["Dream", "TurnProcess", "PastRecord"],
            avoid_patterns=["generic clarification loop"],
            success_signals=["grounded source anchor found"],
            failure_signals=["no grounded source found"],
            execution_mode=str(doctrine.get("execution_mode") or "policy_guided"),
            rationale=str(doctrine.get("rationale") or ""),
            compiled_from_tactic_key=compiled_from_tactic_key,
            policy_source=str(doctrine.get("policy_source") or "nightly_reflection"),
            status=str(doctrine.get("status") or "active"),
        )

        if branch_path:
            session.run(
                """
                MATCH (td:ToolDoctrine {doctrine_key: $doctrine_key})
                MATCH (gb:GovernorBranch {governor_key: 'rem_governor_v1', branch_path: $branch_path})
                MERGE (td)-[:FOLLOWS_BRANCH]->(gb)
                MERGE (gb)-[:HAS_DOCTRINE]->(td)
                """,
                doctrine_key=doctrine_key,
                branch_path=branch_path,
            )

        link_target_root(
            session,
            "MATCH (td:ToolDoctrine {doctrine_key: $doctrine_key})",
            "td",
            {"doctrine_key": doctrine_key},
            root_entity,
        )

        if compiled_from_tactic_key:
            session.run(
                """
                MATCH (t:TacticalThought {id: $tactic_key})
                MATCH (td:ToolDoctrine {doctrine_key: $doctrine_key})
                MERGE (t)-[:UPDATES_DOCTRINE]->(td)
                """,
                tactic_key=compiled_from_tactic_key,
                doctrine_key=doctrine_key,
            )

        graph_operations_log.append({"op": "TOOL_DOCTRINE", "key": doctrine_key})
