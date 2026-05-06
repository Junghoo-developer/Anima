"""REMGovernor department for the midnight reflection graph.

This module is a mechanical extraction from Core.midnight_reflection.DreamWeaver.
It keeps REMGovernor behavior unchanged while moving root/governor state logic
out of the night-loop god-file.
"""

import json
import unicodedata

from Core.midnight_reflection_contracts import MidnightState
from Core.rem_governor import (
    GovernorInventoryItem,
    GovernorPolicyAssetItem,
    REMGovernorStateSchema,
    parse_branch_health_map,
)


def _parse_branch_health_map(rem_governor):
    return parse_branch_health_map(rem_governor)
    mapping = {}
    if not isinstance(rem_governor, dict):
        return mapping
    for item in rem_governor.get("branch_health", []) or []:
        text = str(item or "").strip()
        if not text:
            continue
        branch_path, _, health_hint = text.partition("::")
        branch_path = branch_path.strip()
        health_hint = (health_hint or "unknown").strip()
        if branch_path:
            mapping[branch_path] = health_hint
    return mapping


def _scan_root_graph_context(self):
    fallback = {
        "person_labels": [],
        "person_rel_types": [],
        "ego_labels": [],
        "ego_rel_types": [],
        "person_inventory": [],
        "ego_inventory": [],
    }
    if not self.neo4j_driver:
        return fallback
    try:
        with self.neo4j_driver.session() as session:
            record = session.run(
                """
                MATCH (p:Person {name: '허정후'})
                OPTIONAL MATCH (p)-[pr]-(pn)
                WITH
                  collect(DISTINCT head(labels(pn))) AS person_labels,
                  collect(DISTINCT type(pr)) AS person_rel_types,
                  collect(DISTINCT CASE
                    WHEN pn IS NULL THEN NULL
                    ELSE {
                      root_entity: 'Person:허정후',
                      relation_type: type(pr),
                      node_type: head(labels(pn)),
                      node_name: coalesce(pn.name, pn.title, pn.id, ''),
                      summary: coalesce(pn.description, pn.summary, '')
                    }
                  END) AS person_inventory
                MATCH (e:CoreEgo {name: '송련'})
                OPTIONAL MATCH (e)-[er]-(en)
                RETURN
                  [label IN person_labels WHERE label IS NOT NULL] AS person_labels,
                  [rel IN person_rel_types WHERE rel IS NOT NULL] AS person_rel_types,
                  collect(DISTINCT head(labels(en))) AS ego_labels,
                  collect(DISTINCT type(er)) AS ego_rel_types,
                  [item IN person_inventory WHERE item IS NOT NULL] AS person_inventory,
                  collect(DISTINCT CASE
                    WHEN en IS NULL THEN NULL
                    ELSE {
                      root_entity: 'CoreEgo:송련',
                      relation_type: type(er),
                      node_type: head(labels(en)),
                      node_name: coalesce(en.name, en.title, en.id, ''),
                      summary: coalesce(en.description, en.summary, '')
                    }
                  END) AS ego_inventory
                """
            ).single()
            if not record:
                return fallback
            return {
                "person_labels": [str(label or "").strip() for label in (record.get("person_labels") or []) if str(label or "").strip()],
                "person_rel_types": [str(rel or "").strip() for rel in (record.get("person_rel_types") or []) if str(rel or "").strip()],
                "ego_labels": [str(label or "").strip() for label in (record.get("ego_labels") or []) if str(label or "").strip()],
                "ego_rel_types": [str(rel or "").strip() for rel in (record.get("ego_rel_types") or []) if str(rel or "").strip()],
                "person_inventory": [
                    dict(item)
                    for item in (record.get("person_inventory") or [])
                    if isinstance(item, dict)
                ],
                "ego_inventory": [
                    dict(item)
                    for item in (record.get("ego_inventory") or [])
                    if isinstance(item, dict)
                ],
            }
    except Exception:
        return fallback

def _build_governor_root_profiles(self, governor, root_context):
    governor = governor if isinstance(governor, dict) else {}
    root_entities = list(governor.get("root_entities", []) or [])
    evidence_roots = list(governor.get("evidence_roots", []) or [])
    previous_profiles = {
        str(profile.get("root_entity") or "").strip(): dict(profile)
        for profile in (governor.get("root_profiles", []) or [])
        if isinstance(profile, dict) and str(profile.get("root_entity") or "").strip()
    }

    profiles = []
    for root_entity in root_entities:
        root_key = str(root_entity or "").strip()
        if not root_key:
            continue
        previous = previous_profiles.get(root_key, {})
        if root_key.startswith("Person:"):
            profile = {
                "root_entity": root_key,
                "inferred_role": "developer_user",
                "factual_summary": "This Person root appears to represent the user/developer axis and should connect diary, past records, and dialogue evidence.",
                "connected_node_types": self._dedupe_keep_order(root_context.get("person_labels", []) or list(previous.get("connected_node_types", []) or [])),
                "connected_relation_types": self._dedupe_keep_order(root_context.get("person_rel_types", []) or list(previous.get("connected_relation_types", []) or [])),
                "evidence_roots": self._dedupe_keep_order(
                    [item for item in evidence_roots if str(item or "").startswith("Person") or str(item or "").startswith("Dream:")]
                    or list(previous.get("evidence_roots", []) or [])
                )[:16],
                "open_unknowns": self._dedupe_keep_order(
                    [
                        "Branches not yet structured under the user root",
                        "Higher-level categories needed to describe the user root clearly",
                    ] + list(previous.get("open_unknowns", []) or [])
                )[:8],
            }
        elif root_key.startswith("CoreEgo:"):
            profile = {
                "root_entity": root_key,
                "inferred_role": "system_prototype",
                "factual_summary": "This CoreEgo root represents SongRyeon as the active response, memory, and policy subject inside ANIMA.",
                "connected_node_types": self._dedupe_keep_order(root_context.get("ego_labels", []) or list(previous.get("connected_node_types", []) or [])),
                "connected_relation_types": self._dedupe_keep_order(root_context.get("ego_rel_types", []) or list(previous.get("connected_relation_types", []) or [])),
                "evidence_roots": self._dedupe_keep_order(
                    [item for item in evidence_roots if str(item or "").startswith("CoreEgo") or str(item or "").startswith("Dream:")]
                    or list(previous.get("evidence_roots", []) or [])
                )[:16],
                "open_unknowns": self._dedupe_keep_order(
                    [
                        "Insufficient policy, tool, and field-repair branches under SongRyeon",
                        "Higher-level structure needed to describe SongRyeon's roles and boundaries",
                    ] + list(previous.get("open_unknowns", []) or [])
                )[:8],
            }
        else:
            profile = previous or {
                "root_entity": root_key,
                "inferred_role": "observed_root",
                "factual_summary": f"{root_key} is an observed root currently tracked by the Governor.",
                "connected_node_types": [],
                "connected_relation_types": [],
                "evidence_roots": [],
                "open_unknowns": [],
            }
        profiles.append(profile)
    return profiles

def _build_governor_root_inventory(self, root_context):
    inventory_items = []
    for item in (root_context.get("person_inventory") or []) + (root_context.get("ego_inventory") or []):
        if not isinstance(item, dict):
            continue
        try:
            inventory_items.append(
                GovernorInventoryItem(
                    root_entity=str(item.get("root_entity") or "").strip(),
                    relation_type=str(item.get("relation_type") or "").strip(),
                    node_type=str(item.get("node_type") or "").strip(),
                    node_name=str(item.get("node_name") or "").strip(),
                    summary=self._trim_text(item.get("summary"), 180),
                ).model_dump()
            )
        except Exception:
            continue
    return inventory_items[:48]

def _root_entity_from_asset_scope(self, branch_path="", root_scope=""):
    normalized_branch = self._normalize_branch_path_to_existing_roots(branch_path)
    if normalized_branch:
        root_entity, _, _ = self._branch_root_info(normalized_branch)
        if root_entity:
            return root_entity
    normalized_scope = str(root_scope or "").strip()
    if normalized_scope.startswith("Person"):
        return "Person:stable"
    if normalized_scope.startswith("CoreEgo"):
        return "CoreEgo:songryeon"
    return ""

def _build_governor_policy_inventory(self, state: MidnightState, rem_governor=None):
    existing_items = []
    if isinstance(rem_governor, dict):
        existing_items = [
            dict(item)
            for item in (rem_governor.get("policy_inventory", []) or [])
            if isinstance(item, dict)
        ]

    rem_plan = state.get("rem_plan", {}) if isinstance(state.get("rem_plan"), dict) else {}
    phase_7 = state.get("phase_7_audit", {}) if isinstance(state.get("phase_7_audit"), dict) else {}
    tactical = state.get("tactical_doctrine", {}) if isinstance(state.get("tactical_doctrine"), dict) else {}
    route_policies = state.get("route_policies", []) if isinstance(state.get("route_policies"), list) else []
    tool_doctrines = state.get("tool_doctrines", []) if isinstance(state.get("tool_doctrines"), list) else []
    branch_digests = state.get("branch_digests", []) if isinstance(state.get("branch_digests"), list) else []

    inventory_map = {}

    def upsert(item):
        if not isinstance(item, dict):
            return
        asset_type = str(item.get("asset_type") or "").strip()
        asset_key = str(item.get("asset_key") or "").strip()
        if not asset_type or not asset_key:
            return
        try:
            normalized = GovernorPolicyAssetItem(**item).model_dump()
        except Exception:
            return
        inventory_map[(asset_type, asset_key)] = normalized

    for item in existing_items:
        upsert(item)

    normalized_tactics = self._normalize_tactical_cards(tactical, rem_plan, phase_7)
    for tactic in normalized_tactics:
        if not isinstance(tactic, dict):
            continue
        branch_path = self._normalize_branch_path_to_existing_roots(str(tactic.get("branch_scope") or "").strip())
        target_family = str(tactic.get("target_family") or "").strip()
        asset_key = str(tactic.get("tactic_key") or "").strip()
        if not asset_key:
            continue
        root_entity = self._root_entity_from_asset_scope(branch_path, tactic.get("root_scope"))
        branch_title = self._branch_title_ko(branch_path) or branch_path or target_family
        upsert({
            "asset_type": "tactic",
            "asset_key": asset_key,
            "root_entity": root_entity,
            "branch_path": branch_path,
            "target_family": target_family,
            "summary": f"Tactic card {branch_title}",
            "status": str(tactic.get("status") or "active"),
        })

    for policy in route_policies:
        if not isinstance(policy, dict):
            continue
        asset_key = str(policy.get("policy_key") or "").strip()
        target_family = str(policy.get("turn_family") or "").strip()
        if not asset_key:
            continue
        branch_path = self._branch_path_for_topic(target_family) if target_family else ""
        branch_path = self._normalize_branch_path_to_existing_roots(branch_path)
        root_entity = self._root_entity_from_asset_scope(branch_path)
        upsert({
            "asset_type": "route_policy",
            "asset_key": asset_key,
            "root_entity": root_entity,
            "branch_path": branch_path,
            "target_family": target_family,
            "summary": f"Route policy {self._branch_title_ko(branch_path) or self._topic_label_ko(target_family) or asset_key}",
            "status": str(policy.get("status") or "active"),
        })

    for doctrine in tool_doctrines:
        if not isinstance(doctrine, dict):
            continue
        asset_key = str(doctrine.get("doctrine_key") or "").strip()
        target_family = str(doctrine.get("target_family") or "").strip()
        if not asset_key:
            continue
        branch_path = self._branch_path_for_topic(target_family) if target_family else ""
        branch_path = self._normalize_branch_path_to_existing_roots(branch_path)
        root_entity = self._root_entity_from_asset_scope(branch_path)
        upsert({
            "asset_type": "tool_doctrine",
            "asset_key": asset_key,
            "root_entity": root_entity,
            "branch_path": branch_path,
            "target_family": target_family,
            "summary": f"Tool doctrine {self._branch_title_ko(branch_path) or self._topic_label_ko(target_family) or asset_key}",
            "status": str(doctrine.get("status") or "active"),
        })

    for digest in branch_digests:
        if not isinstance(digest, dict):
            continue
        asset_key = str(digest.get("digest_key") or "").strip()
        branch_path = self._normalize_branch_path_to_existing_roots(str(digest.get("branch_path") or "").strip())
        if not asset_key or not branch_path:
            continue
        target_family = self._topic_slug_from_branch_path(branch_path)
        root_entity = self._root_entity_from_asset_scope(branch_path)
        upsert({
            "asset_type": "branch_digest",
            "asset_key": asset_key,
            "root_entity": root_entity,
            "branch_path": branch_path,
            "target_family": target_family,
            "summary": f"Branch digest asset {str(digest.get('title') or self._branch_title_ko(branch_path) or branch_path).strip()}",
            "status": str(digest.get("status") or "active"),
        })

    return list(inventory_map.values())[:128]


def _apply_governor_root_profiles_to_roots(self, session, rem_governor):
    root_profiles = {
        str(profile.get("root_entity") or "").strip(): dict(profile)
        for profile in (rem_governor.get("root_profiles", []) or [])
        if isinstance(profile, dict) and str(profile.get("root_entity") or "").strip()
    }
    root_inventory = [
        dict(item)
        for item in (rem_governor.get("root_inventory", []) or [])
        if isinstance(item, dict)
    ]
    person_inventory = [item for item in root_inventory if str(item.get("root_entity") or "").strip() == "Person:stable"]
    ego_inventory = [item for item in root_inventory if str(item.get("root_entity") or "").strip() == "CoreEgo:songryeon"]

    person_profile = root_profiles.get("Person:stable", {})
    if person_profile:
        session.run(
            """
            MATCH (u:Person {name: 'stable'})
            SET u.governor_role = $governor_role,
                u.governor_summary = $governor_summary,
                u.governor_known_node_types = $governor_known_node_types,
                u.governor_known_relation_types = $governor_known_relation_types,
                u.governor_evidence_roots = $governor_evidence_roots,
                u.governor_open_unknowns = $governor_open_unknowns,
                u.governor_root_inventory_json = $governor_root_inventory_json,
                u.governor_updated_at = timestamp(),
                u.description = coalesce(u.description, $governor_summary)
            """,
            governor_role=str(person_profile.get("inferred_role") or "developer_user"),
            governor_summary=str(person_profile.get("factual_summary") or ""),
            governor_known_node_types=list(person_profile.get("connected_node_types", []) or []),
            governor_known_relation_types=list(person_profile.get("connected_relation_types", []) or []),
            governor_evidence_roots=list(person_profile.get("evidence_roots", []) or []),
            governor_open_unknowns=list(person_profile.get("open_unknowns", []) or []),
            governor_root_inventory_json=json.dumps(person_inventory, ensure_ascii=False),
        )

    ego_profile = root_profiles.get("CoreEgo:songryeon", {})
    if ego_profile:
        session.run(
            """
            MATCH (e:CoreEgo {name: 'songryeon'})
            SET e.governor_role = $governor_role,
                e.governor_summary = $governor_summary,
                e.governor_known_node_types = $governor_known_node_types,
                e.governor_known_relation_types = $governor_known_relation_types,
                e.governor_evidence_roots = $governor_evidence_roots,
                e.governor_open_unknowns = $governor_open_unknowns,
                e.governor_root_inventory_json = $governor_root_inventory_json,
                e.governor_updated_at = timestamp(),
                e.description = coalesce(e.description, $governor_summary)
            """,
            governor_role=str(ego_profile.get("inferred_role") or "system_prototype"),
            governor_summary=str(ego_profile.get("factual_summary") or ""),
            governor_known_node_types=list(ego_profile.get("connected_node_types", []) or []),
            governor_known_relation_types=list(ego_profile.get("connected_relation_types", []) or []),
            governor_evidence_roots=list(ego_profile.get("evidence_roots", []) or []),
            governor_open_unknowns=list(ego_profile.get("open_unknowns", []) or []),
            governor_root_inventory_json=json.dumps(ego_inventory, ensure_ascii=False),
        )

def _apply_governor_root_state_to_roots(self, session, rem_governor):
    root_profiles = {
        str(profile.get("root_entity") or "").strip(): dict(profile)
        for profile in (rem_governor.get("root_profiles", []) or [])
        if isinstance(profile, dict) and str(profile.get("root_entity") or "").strip()
    }
    root_inventory = [
        dict(item)
        for item in (rem_governor.get("root_inventory", []) or [])
        if isinstance(item, dict)
    ]
    policy_inventory = [
        dict(item)
        for item in (rem_governor.get("policy_inventory", []) or [])
        if isinstance(item, dict)
    ]

    person_inventory = [item for item in root_inventory if str(item.get("root_entity") or "").strip() == "Person:stable"]
    ego_inventory = [item for item in root_inventory if str(item.get("root_entity") or "").strip() == "CoreEgo:songryeon"]
    person_policy_inventory = [item for item in policy_inventory if str(item.get("root_entity") or "").strip() == "Person:stable"]
    ego_policy_inventory = [item for item in policy_inventory if str(item.get("root_entity") or "").strip() == "CoreEgo:songryeon"]

    person_profile = root_profiles.get("Person:stable", {})
    if person_profile:
        session.run(
            """
            MATCH (u:Person {name: 'stable'})
            SET u.governor_role = $governor_role,
                u.governor_summary = $governor_summary,
                u.governor_known_node_types = $governor_known_node_types,
                u.governor_known_relation_types = $governor_known_relation_types,
                u.governor_evidence_roots = $governor_evidence_roots,
                u.governor_open_unknowns = $governor_open_unknowns,
                u.governor_root_inventory_json = $governor_root_inventory_json,
                u.governor_policy_inventory_json = $governor_policy_inventory_json,
                u.governor_policy_inventory_count = toInteger($governor_policy_inventory_count),
                u.governor_updated_at = timestamp(),
                u.description = coalesce(u.description, $governor_summary)
            """,
            governor_role=str(person_profile.get("inferred_role") or "developer_user"),
            governor_summary=str(person_profile.get("factual_summary") or ""),
            governor_known_node_types=list(person_profile.get("connected_node_types", []) or []),
            governor_known_relation_types=list(person_profile.get("connected_relation_types", []) or []),
            governor_evidence_roots=list(person_profile.get("evidence_roots", []) or []),
            governor_open_unknowns=list(person_profile.get("open_unknowns", []) or []),
            governor_root_inventory_json=json.dumps(person_inventory, ensure_ascii=False),
            governor_policy_inventory_json=json.dumps(person_policy_inventory, ensure_ascii=False),
            governor_policy_inventory_count=len(person_policy_inventory),
        )

    ego_profile = root_profiles.get("CoreEgo:songryeon", {})
    if ego_profile:
        session.run(
            """
            MATCH (e:CoreEgo {name: 'songryeon'})
            SET e.governor_role = $governor_role,
                e.governor_summary = $governor_summary,
                e.governor_known_node_types = $governor_known_node_types,
                e.governor_known_relation_types = $governor_known_relation_types,
                e.governor_evidence_roots = $governor_evidence_roots,
                e.governor_open_unknowns = $governor_open_unknowns,
                e.governor_root_inventory_json = $governor_root_inventory_json,
                e.governor_policy_inventory_json = $governor_policy_inventory_json,
                e.governor_policy_inventory_count = toInteger($governor_policy_inventory_count),
                e.governor_updated_at = timestamp(),
                e.description = coalesce(e.description, $governor_summary)
            """,
            governor_role=str(ego_profile.get("inferred_role") or "system_prototype"),
            governor_summary=str(ego_profile.get("factual_summary") or ""),
            governor_known_node_types=list(ego_profile.get("connected_node_types", []) or []),
            governor_known_relation_types=list(ego_profile.get("connected_relation_types", []) or []),
            governor_evidence_roots=list(ego_profile.get("evidence_roots", []) or []),
            governor_open_unknowns=list(ego_profile.get("open_unknowns", []) or []),
            governor_root_inventory_json=json.dumps(ego_inventory, ensure_ascii=False),
            governor_policy_inventory_json=json.dumps(ego_policy_inventory, ensure_ascii=False),
            governor_policy_inventory_count=len(ego_policy_inventory),
        )

def _default_rem_governor_state(self):
    base_branches = self._dedupe_keep_order([
        self._branch_path_for_topic("person_definition"),
        self._branch_path_for_topic("person_life_history"),
        self._branch_path_for_topic("person_current_state"),
        self._branch_path_for_topic("person_development_pattern"),
        self._branch_path_for_topic("coreego_definition"),
        self._branch_path_for_topic("coreego_history"),
        self._branch_path_for_topic("coreego_current_state"),
        self._branch_path_for_topic("coreego_field_response"),
        self._branch_path_for_topic("coreego_self_model"),
        self._branch_path_for_topic("personal_history_review"),
        self._branch_path_for_topic("self_analysis_snapshot"),
        self._branch_path_for_topic("recent_dialogue_review"),
        self._branch_path_for_topic("tool_routing"),
        self._branch_path_for_topic("field_repair"),
    ])
    payload = {
        "governor_key": "rem_governor_v1",
        "root_entities": ["Person:stable", "CoreEgo:songryeon"],
        "root_descriptions": [
            "Primary person root for user-facing autobiographical and development context.",
            "CoreEgo root for SongRyeon field behavior, memory behavior, and response stability.",
        ],
        "root_profiles": [
            {
                "root_entity": "Person:stable",
                "inferred_role": "developer_user",
                "factual_summary": "Primary user/developer root. Keep only grounded facts and provenance-backed summaries here.",
                "connected_node_types": [],
                "connected_relation_types": [],
                "evidence_roots": ["Person:stable"],
                "open_unknowns": ["Person root structure should be refined only from grounded memory."],
            },
            {
                "root_entity": "CoreEgo:songryeon",
                "inferred_role": "system_prototype",
                "factual_summary": "SongRyeon CoreEgo root. Track field response, memory behavior, and tool-use stability.",
                "connected_node_types": [],
                "connected_relation_types": [],
                "evidence_roots": ["CoreEgo:songryeon"],
                "open_unknowns": ["CoreEgo root structure should be refined only from grounded runtime evidence."],
            },
        ],
        "root_inventory": [],
        "policy_inventory": [],
        "known_branches": base_branches,
        "required_branches": base_branches,
        "branch_health": [f"{branch_path}::seed" for branch_path in base_branches],
        "open_unknowns": [
            "Person root facts need grounded consolidation.",
            "CoreEgo runtime failures need grounded consolidation.",
        ],
        "priority_biases": [
            "Prefer existing roots and branches before creating new ones.",
            "Expand only when grounded evidence supports the branch.",
            "Do not generate nodes from speculation alone.",
        ],
        "branch_revision_rules": [
            "Place a new topic under an existing branch when possible.",
            "Use only Person:stable and CoreEgo:songryeon as default roots.",
            "Every policy or memory asset must cite Dream, TurnProcess, or Phase evidence.",
        ],
        "policy_alignment_targets": ["TacticalThought", "RoutePolicy", "ToolDoctrine", "BranchDigest"],
        "evidence_roots": ["Person:stable", "CoreEgo:songryeon"],
        "last_growth_actions": [],
        "governor_summary": "REMGovernor maintains advisory roots and branch structure for nightly consolidation only.",
        "preferred_report_target": "phase_9",
        "status": "active",
    }
    return REMGovernorStateSchema(**payload).model_dump()


def _load_existing_rem_governor_state(self, governor_key="rem_governor_v1"):
    if not self.neo4j_driver:
        return {}
    try:
        with self.neo4j_driver.session() as session:
            record = session.run(
                """
                OPTIONAL MATCH (rg)
                WHERE rg.governor_key = $governor_key
                  AND 'REMGovernorState' IN labels(rg)
                OPTIONAL MATCH (rg)-[track_rel]->(root)
                WHERE type(track_rel) = 'TRACKS_ROOT'
                OPTIONAL MATCH (rg)-[branch_rel]->(gb)
                WHERE type(branch_rel) = 'HAS_BRANCH'
                RETURN
                  rg{.*} AS props,
                  collect(
                    DISTINCT CASE
                      WHEN 'Person' IN labels(root) THEN 'Person:' + coalesce(root.name, '')
                      WHEN 'CoreEgo' IN labels(root) THEN 'CoreEgo:' + coalesce(root.name, '')
                      ELSE ''
                    END
                  ) AS roots,
                  collect(
                    DISTINCT CASE
                      WHEN gb IS NULL THEN NULL
                      ELSE properties(gb)
                    END
                  ) AS branches
                """,
                governor_key=governor_key,
            ).single()
            if not record:
                return {}
            props = dict(record.get("props") or {})
            roots = [
                str(root or "").strip()
                for root in (record.get("roots") or [])
                if str(root or "").strip()
            ]
            branches = [
                dict(branch)
                for branch in (record.get("branches") or [])
                if isinstance(branch, dict) and str(branch.get("branch_path") or "").strip()
            ]
            known_branches = list(props.get("known_branches", []) or [])
            required_branches = list(props.get("required_branches", []) or [])
            branch_health = list(props.get("branch_health", []) or [])
            root_profiles = []
            root_inventory = []
            policy_inventory = []
            raw_root_profiles_json = str(props.get("root_profiles_json") or "").strip()
            if raw_root_profiles_json:
                try:
                    parsed_root_profiles = json.loads(raw_root_profiles_json)
                    if isinstance(parsed_root_profiles, list):
                        root_profiles = [
                            dict(profile)
                            for profile in parsed_root_profiles
                            if isinstance(profile, dict)
                        ]
                except Exception:
                    root_profiles = []
            raw_root_inventory_json = str(props.get("root_inventory_json") or "").strip()
            if raw_root_inventory_json:
                try:
                    parsed_root_inventory = json.loads(raw_root_inventory_json)
                    if isinstance(parsed_root_inventory, list):
                        root_inventory = [
                            dict(item)
                            for item in parsed_root_inventory
                            if isinstance(item, dict)
                        ]
                except Exception:
                    root_inventory = []
            raw_policy_inventory_json = str(props.get("policy_inventory_json") or "").strip()
            if raw_policy_inventory_json:
                try:
                    parsed_policy_inventory = json.loads(raw_policy_inventory_json)
                    if isinstance(parsed_policy_inventory, list):
                        policy_inventory = [
                            dict(item)
                            for item in parsed_policy_inventory
                            if isinstance(item, dict)
                        ]
                except Exception:
                    policy_inventory = []
            for branch in branches:
                branch_path = str(branch.get("branch_path") or "").strip()
                branch_role = str(branch.get("branch_role") or "known").strip() or "known"
                health_hint = str(branch.get("health_hint") or "unknown").strip() or "unknown"
                if branch_path:
                    known_branches.append(branch_path)
                    if branch_role == "required":
                        required_branches.append(branch_path)
                    branch_health.append(f"{branch_path}::{health_hint}")
            payload = {
                "governor_key": str(props.get("governor_key") or governor_key),
                "root_entities": self._dedupe_keep_order(roots or list(props.get("root_entities", []) or [])) or ["Person:stable", "CoreEgo:songryeon"],
                "root_descriptions": list(props.get("root_descriptions", []) or []),
                "root_profiles": root_profiles,
                "root_inventory": root_inventory,
                "policy_inventory": policy_inventory,
                "known_branches": self._dedupe_keep_order(known_branches),
                "required_branches": self._dedupe_keep_order(required_branches),
                "branch_health": self._dedupe_keep_order(branch_health),
                "open_unknowns": self._dedupe_keep_order(list(props.get("open_unknowns", []) or [])),
                "priority_biases": self._dedupe_keep_order(list(props.get("priority_biases", []) or [])),
                "branch_revision_rules": self._dedupe_keep_order(list(props.get("branch_revision_rules", []) or [])),
                "policy_alignment_targets": self._dedupe_keep_order(list(props.get("policy_alignment_targets", []) or [])),
                "evidence_roots": self._dedupe_keep_order(list(props.get("evidence_roots", []) or [])),
                "last_growth_actions": self._dedupe_keep_order(list(props.get("last_growth_actions", []) or [])),
                "governor_summary": str(props.get("governor_summary") or ""),
                "preferred_report_target": str(props.get("preferred_report_target") or "phase_9"),
                "status": str(props.get("status") or "active"),
            }
            return REMGovernorStateSchema(**payload).model_dump()
    except Exception:
        return {}


def _build_rem_governor_state(self, dream_rows):
    governor = self._load_existing_rem_governor_state() or self._default_rem_governor_state()
    root_context = self._scan_root_graph_context()
    person_labels = root_context.get("person_labels", [])
    person_rel_types = root_context.get("person_rel_types", [])
    ego_labels = root_context.get("ego_labels", [])
    ego_rel_types = root_context.get("ego_rel_types", [])
    normalized_text = unicodedata.normalize(
        "NFKC",
        " ".join(
            str(fragment or "").strip()
            for row in (dream_rows if isinstance(dream_rows, list) else [])
            if isinstance(row, dict)
            for fragment in (row.get("input"), row.get("answer"), row.get("turn_summary"))
        ),
    )

    known_branches = list(governor.get("known_branches", []) or [])
    required_branches = list(governor.get("required_branches", []) or [])
    open_unknowns = list(governor.get("open_unknowns", []) or [])
    evidence_roots = list(governor.get("evidence_roots", []) or [])
    root_inventory = list(governor.get("root_inventory", []) or [])
    branch_health_map = self._parse_branch_health_map(governor)

    self_definition_branches = [
        self._branch_path_for_topic("person_definition"),
        self._branch_path_for_topic("person_life_history"),
        self._branch_path_for_topic("person_current_state"),
        self._branch_path_for_topic("person_development_pattern"),
        self._branch_path_for_topic("coreego_definition"),
        self._branch_path_for_topic("coreego_history"),
        self._branch_path_for_topic("coreego_current_state"),
        self._branch_path_for_topic("coreego_field_response"),
        self._branch_path_for_topic("coreego_self_model"),
    ]
    required_branches.extend(self_definition_branches)
    known_branches.extend(self_definition_branches)

    if any(label in {"Diary", "PastRecord", "Dream"} for label in person_labels):
        required_branches.append(self._branch_path_for_topic("personal_history_review"))
        evidence_roots.extend([f"PersonContext:{label}" for label in person_labels if label])
    if any(label in {"Dream", "RoutePolicy", "ToolDoctrine", "TacticalThought", "BranchDigest"} for label in ego_labels):
        required_branches.extend([
            self._branch_path_for_topic("recent_dialogue_review"),
            self._branch_path_for_topic("tool_routing"),
            self._branch_path_for_topic("field_repair"),
        ])
        evidence_roots.extend([f"CoreEgoContext:{label}" for label in ego_labels if label])

    lowered_text = normalized_text.lower()
    if any(token in lowered_text for token in ["history", "past", "diary", "record"]):
        required_branches.append(self._branch_path_for_topic("personal_history_review"))
    if any(token in lowered_text for token in ["dialogue", "conversation", "summary", "recap"]):
        required_branches.append(self._branch_path_for_topic("recent_dialogue_review"))
    if any(token in lowered_text for token in ["pattern", "self", "snapshot"]):
        required_branches.append(self._branch_path_for_topic("self_analysis_snapshot"))
    if any(token in lowered_text for token in ["tool", "search", "artifact", "read"]):
        required_branches.append(self._branch_path_for_topic("tool_routing"))

    for branch_path in self._dedupe_keep_order(required_branches):
        known_branches.append(branch_path)
        branch_health_map.setdefault(branch_path, "observed")

    open_unknowns.extend([
        "Person root needs grounded fact leaves for history and current state.",
        "CoreEgo root needs grounded fact leaves for field response and self-model behavior.",
        "Identify which branches are missing provenance-backed facts.",
    ])

    payload = {
        "governor_key": str(governor.get("governor_key") or "rem_governor_v1"),
        "root_entities": self._dedupe_keep_order(list(governor.get("root_entities", []) or []) or ["Person:stable", "CoreEgo:songryeon"]),
        "root_descriptions": self._dedupe_keep_order(
            list(governor.get("root_descriptions", []) or []) + [
                f"Person root labels: {', '.join(person_labels) if person_labels else 'none'}",
                f"Person root relation types: {', '.join(person_rel_types) if person_rel_types else 'none'}",
                f"CoreEgo root labels: {', '.join(ego_labels) if ego_labels else 'none'}",
                f"CoreEgo root relation types: {', '.join(ego_rel_types) if ego_rel_types else 'none'}",
            ]
        ),
        "root_profiles": self._build_governor_root_profiles(governor, root_context),
        "root_inventory": self._build_governor_root_inventory(root_context) or root_inventory,
        "policy_inventory": list(governor.get("policy_inventory", []) or []),
        "known_branches": self._dedupe_keep_order(known_branches),
        "required_branches": self._dedupe_keep_order(required_branches),
        "branch_health": self._dedupe_keep_order([f"{branch_path}::{health_hint}" for branch_path, health_hint in branch_health_map.items()]),
        "open_unknowns": self._dedupe_keep_order(open_unknowns),
        "priority_biases": self._dedupe_keep_order(list(governor.get("priority_biases", []) or [])),
        "branch_revision_rules": self._dedupe_keep_order(list(governor.get("branch_revision_rules", []) or [])),
        "policy_alignment_targets": self._dedupe_keep_order(list(governor.get("policy_alignment_targets", []) or [])),
        "evidence_roots": self._dedupe_keep_order(evidence_roots),
        "last_growth_actions": self._dedupe_keep_order(list(governor.get("last_growth_actions", []) or [])),
        "governor_summary": str(governor.get("governor_summary") or "REMGovernor keeps advisory roots and branch structure for nightly consolidation only."),
        "preferred_report_target": str(governor.get("preferred_report_target") or "phase_9"),
        "status": str(governor.get("status") or "active"),
    }
    return REMGovernorStateSchema(**payload).model_dump()

def _refresh_rem_governor_state(self, state: MidnightState):
    governor = dict(state.get("rem_governor") or self._default_rem_governor_state())
    rem_plan = state.get("rem_plan", {}) if isinstance(state.get("rem_plan"), dict) else {}
    phase_7 = state.get("phase_7_audit", {}) if isinstance(state.get("phase_7_audit"), dict) else {}
    branch_digests = state.get("branch_digests", []) if isinstance(state.get("branch_digests"), list) else []
    review_packet = state.get("phase_8_review_packet", {}) if isinstance(state.get("phase_8_review_packet"), dict) else {}
    branch_growth_report = state.get("branch_growth_report", {}) if isinstance(state.get("branch_growth_report"), dict) else {}

    known_branches = list(governor.get("known_branches", []) or [])
    required_branches = list(governor.get("required_branches", []) or [])
    open_unknowns = list(governor.get("open_unknowns", []) or [])
    last_growth_actions = list(governor.get("last_growth_actions", []) or [])
    evidence_roots = list(governor.get("evidence_roots", []) or [])
    root_profiles = list(governor.get("root_profiles", []) or [])
    root_inventory = list(governor.get("root_inventory", []) or [])
    policy_inventory = self._build_governor_policy_inventory(state, governor)
    branch_health_map = self._parse_branch_health_map(governor)

    growth_status = str(branch_growth_report.get("growth_status") or "").strip()
    rejected_growth_branches = self._dedupe_keep_order(branch_growth_report.get("rejected_branch_paths", []) or [])
    if growth_status:
        last_growth_actions.append(f"branch_growth::{growth_status}")
    for rejected_branch in rejected_growth_branches:
        branch_health_map[str(rejected_branch)] = "blocked_no_fact_leaf"
    open_unknowns.extend(str(item or "").strip() for item in branch_growth_report.get("governor_feedback", []) or [] if str(item or "").strip())
    open_unknowns.extend(str(item or "").strip() for item in branch_growth_report.get("rejection_reasons", []) or [] if str(item or "").strip())

    for branch_path in self._plan_branch_paths(rem_plan):
        normalized = str(branch_path or "").strip()
        if not normalized:
            continue
        known_branches.append(normalized)
        required_branches.append(normalized)
        branch_health_map.setdefault(normalized, "planned")

    for digest in branch_digests:
        if not isinstance(digest, dict):
            continue
        branch_path = str(digest.get("branch_path") or "").strip()
        if not branch_path:
            continue
        known_branches.append(branch_path)
        branch_health_map[branch_path] = "grown"
        title = str(digest.get("title") or branch_path).strip()
        if title:
            last_growth_actions.append(f"branch_digest::{title}")

    for topic in phase_7.get("classified_topics", []) or []:
        if not isinstance(topic, dict):
            continue
        topic_slug = str(topic.get("topic_slug") or "").strip()
        if not topic_slug:
            continue
        branch_path = self._branch_path_for_topic(topic_slug)
        supply_sufficient = bool(topic.get("supply_sufficient"))
        branch_health_map[branch_path] = "covered" if supply_sufficient else "needs_growth"
        if not supply_sufficient:
            gap = str(topic.get("gap_description") or topic.get("title") or topic_slug).strip()
            if gap:
                open_unknowns.append(gap)

    for rejected_branch in rejected_growth_branches:
        branch_health_map[str(rejected_branch)] = "blocked_no_fact_leaf"

    if review_packet:
        target = str(review_packet.get("review_target") or "").strip()
        objection = str(review_packet.get("objection_kind") or "").strip()
        if target or objection:
            last_growth_actions.append(f"review::{target or 'unknown'}::{objection or 'unspecified'}")

    evidence_roots.extend(self._plan_evidence_points(rem_plan))

    payload = {
        "governor_key": str(governor.get("governor_key") or "rem_governor_v1"),
        "root_entities": self._dedupe_keep_order(list(governor.get("root_entities", []) or []) or ["Person:stable", "CoreEgo:songryeon"]),
        "root_descriptions": self._dedupe_keep_order(list(governor.get("root_descriptions", []) or [])),
        "root_profiles": root_profiles,
        "root_inventory": root_inventory,
        "policy_inventory": policy_inventory,
        "known_branches": self._dedupe_keep_order(known_branches),
        "required_branches": self._dedupe_keep_order(required_branches),
        "branch_health": self._dedupe_keep_order([f"{branch_path}::{health_hint}" for branch_path, health_hint in branch_health_map.items()]),
        "open_unknowns": self._dedupe_keep_order(open_unknowns),
        "priority_biases": self._dedupe_keep_order(list(governor.get("priority_biases", []) or [])),
        "branch_revision_rules": self._dedupe_keep_order(list(governor.get("branch_revision_rules", []) or [])),
        "policy_alignment_targets": self._dedupe_keep_order(list(governor.get("policy_alignment_targets", []) or [])),
        "evidence_roots": self._dedupe_keep_order(evidence_roots),
        "last_growth_actions": self._dedupe_keep_order(last_growth_actions)[-24:],
        "governor_summary": str(governor.get("governor_summary") or ""),
        "preferred_report_target": str(governor.get("preferred_report_target") or rem_plan.get("report_target_phase") or "phase_9"),
        "status": str(governor.get("status") or "active"),
    }
    return REMGovernorStateSchema(**payload).model_dump()
