"""Phase10 policy/doctrine department for the midnight reflection graph.

This module is a mechanical extraction from Core.midnight_reflection.DreamWeaver.
It keeps advisory RoutePolicy/ToolDoctrine compilation behavior unchanged while
moving the Phase10 policy compiler out of the night-loop god-file.
"""

import unicodedata

from Core.midnight_reflection_contracts import MidnightState, TacticalThoughtItem
from Core.rem_governor import (
    RoutePolicyItem,
    ToolDoctrineItem,
    normalize_branch_path_to_existing_roots,
    topic_label_ko,
    topic_slug_from_branch_path,
)


def _tactic_family_blueprints(self):
    return {
        "personal_history_review": {
            "branch_scope": "Person/personal_history/history_review",
            "preferred_next_hop": "",
            "preferred_direct_strategy": "",
            "preferred_tools": [],
            "disallowed_tools": [],
            "tone_recipe": "Use grounded past-record evidence only.",
            "must_include": ["source address and provenance"],
            "must_avoid": ["routing from this blueprint"],
            "repair_recipe": "Ask the field loop to gather grounded evidence if needed.",
            "evidence_priority": ["Diary", "PastRecord", "Dream"],
            "semantic_signals": ["history", "past", "diary", "record"],
            "confidence_gate": 0.62,
            "default_rule": "Advisory only.",
        },
        "recent_dialogue_review": {
            "branch_scope": "CoreEgo/conversation/dialogue_review",
            "preferred_next_hop": "",
            "preferred_direct_strategy": "",
            "preferred_tools": [],
            "disallowed_tools": ["tool_search_memory"],
            "tone_recipe": "Separate current turn from recent dialogue.",
            "must_include": ["recent turn provenance"],
            "must_avoid": ["treating hints as facts"],
            "repair_recipe": "Review the exact recent turn before summarizing.",
            "evidence_priority": ["TurnProcess", "PhaseSnapshot", "Dream"],
            "semantic_signals": ["dialogue", "conversation", "recap"],
            "confidence_gate": 0.58,
            "default_rule": "Advisory only.",
        },
        "self_analysis_snapshot": {
            "branch_scope": "Person/self_model/visible_patterns",
            "preferred_next_hop": "",
            "preferred_direct_strategy": "",
            "preferred_tools": [],
            "disallowed_tools": ["tool_search_memory", "tool_read_artifact"],
            "tone_recipe": "Name visible patterns only.",
            "must_include": ["evidence-backed pattern"],
            "must_avoid": ["diagnosis without evidence"],
            "repair_recipe": "Keep the claim narrow and provenance-backed.",
            "evidence_priority": ["WorkingMemory", "Dream", "RecentContext"],
            "semantic_signals": ["self", "pattern", "snapshot"],
            "confidence_gate": 0.6,
            "default_rule": "Advisory only.",
        },
        "tool_routing": {
            "branch_scope": "CoreEgo/ops/tool_doctrine",
            "preferred_next_hop": "",
            "preferred_direct_strategy": "",
            "preferred_tools": [],
            "disallowed_tools": [],
            "tone_recipe": "Treat tool doctrine as advisory.",
            "must_include": ["source anchor if a tool is used"],
            "must_avoid": ["planner memo as search query"],
            "repair_recipe": "Let -1a/-1b decide tool use from the current contract.",
            "evidence_priority": ["Artifact", "Diary", "PastRecord", "Dream"],
            "semantic_signals": ["artifact", "tool", "search", "read"],
            "confidence_gate": 0.63,
            "default_rule": "Advisory only.",
        },
        "field_repair": {
            "branch_scope": "CoreEgo/ops/field_repair",
            "preferred_next_hop": "",
            "preferred_direct_strategy": "",
            "preferred_tools": [],
            "disallowed_tools": [],
            "tone_recipe": "Identify the field failure narrowly.",
            "must_include": ["failure evidence"],
            "must_avoid": ["generic clarification loops"],
            "repair_recipe": "Use exact prior response and current correction as evidence.",
            "evidence_priority": ["TurnProcess", "PhaseSnapshot", "Dream"],
            "semantic_signals": ["repair", "failure", "wrong", "bug"],
            "confidence_gate": 0.57,
            "default_rule": "Advisory only.",
        },
        "social_praise_ack": {
            "branch_scope": "CoreEgo/social/praise_ack",
            "preferred_next_hop": "",
            "preferred_direct_strategy": "",
            "preferred_tools": [],
            "disallowed_tools": ["tool_search_memory", "tool_read_artifact"],
            "tone_recipe": "Accept praise lightly.",
            "must_include": ["current-turn response"],
            "must_avoid": ["turning praise into a report"],
            "repair_recipe": "Respond naturally to the current turn.",
            "evidence_priority": ["CurrentTurn", "RecentContext"],
            "semantic_signals": ["nice", "smarter", "thanks", "good"],
            "confidence_gate": 0.56,
            "default_rule": "Advisory only.",
        },
        "social_repair": {
            "branch_scope": "CoreEgo/social/repair_response",
            "preferred_next_hop": "",
            "preferred_direct_strategy": "",
            "preferred_tools": [],
            "disallowed_tools": ["tool_search_memory", "tool_read_artifact"],
            "tone_recipe": "Acknowledge the bad response and correct course.",
            "must_include": ["what went wrong"],
            "must_avoid": ["blaming the user"],
            "repair_recipe": "Use the current complaint and prior answer directly.",
            "evidence_priority": ["CurrentTurn", "RecentContext", "TurnProcess"],
            "semantic_signals": ["repair", "sorry", "wrong", "weird"],
            "confidence_gate": 0.6,
            "default_rule": "Advisory only.",
        },
        "playful_positive_reaction": {
            "branch_scope": "CoreEgo/social/light_reaction",
            "preferred_next_hop": "",
            "preferred_direct_strategy": "",
            "preferred_tools": [],
            "disallowed_tools": ["tool_search_memory", "tool_read_artifact"],
            "tone_recipe": "Respond lightly.",
            "must_include": ["current-turn context"],
            "must_avoid": ["heavy analysis"],
            "repair_recipe": "Keep it short and natural.",
            "evidence_priority": ["CurrentTurn", "RecentContext"],
            "semantic_signals": ["cute", "fun", "lol"],
            "confidence_gate": 0.52,
            "default_rule": "Advisory only.",
        },
    }

def _infer_tactical_family(self, tactic: dict, rem_plan: dict, phase_7: dict):
    if not isinstance(tactic, dict):
        tactic = {}
    explicit_family = str(tactic.get("target_family") or "").strip()
    if explicit_family:
        return explicit_family

    branch_scope = normalize_branch_path_to_existing_roots(str(tactic.get("branch_scope") or "").strip())
    if branch_scope:
        branch_family = topic_slug_from_branch_path(branch_scope)
        if branch_family:
            return branch_family

    text_blob = unicodedata.normalize(
        "NFKC",
        " ".join(
            part
            for part in [
                str(tactic.get("situation_trigger") or "").strip(),
                str(tactic.get("actionable_rule") or "").strip(),
                str(tactic.get("repair_recipe") or "").strip(),
            ]
            if part
        ),
    ).lower()

    marker_map = {
        "social_repair": ["repair", "sorry", "wrong", "weird"],
        "social_praise_ack": ["smarter", "nice", "thanks", "good"],
        "playful_positive_reaction": ["cute", "fun", "lol"],
        "personal_history_review": ["history", "past", "diary", "record"],
        "recent_dialogue_review": ["dialogue", "conversation", "recap"],
        "self_analysis_snapshot": ["self", "pattern", "snapshot"],
        "tool_routing": ["artifact", "tool", "search", "read"],
        "field_repair": ["failure", "wrong", "bug"],
    }
    for family, markers in marker_map.items():
        if any(marker in text_blob for marker in markers):
            return family

    selected_branch_paths = list(rem_plan.get("selected_branch_paths", []) or []) if isinstance(rem_plan, dict) else []
    if selected_branch_paths:
        return topic_slug_from_branch_path(str(selected_branch_paths[0] or "").strip()) or "field_repair"

    classified_topics = list(phase_7.get("classified_topics", []) or []) if isinstance(phase_7, dict) else []
    for topic in classified_topics:
        if not isinstance(topic, dict):
            continue
        topic_slug = str(topic.get("topic_slug") or "").strip()
        if topic_slug:
            return topic_slug
    return "field_repair"

def _normalize_tactical_cards(self, tactical: dict, rem_plan: dict, phase_7: dict):
    blueprints = self._tactic_family_blueprints()
    raw_items = list(tactical.get("tactical_thoughts", []) or []) if isinstance(tactical, dict) else []
    normalized_cards = []

    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        family = self._infer_tactical_family(item, rem_plan, phase_7)
        blueprint = dict(blueprints.get(family, blueprints["field_repair"]))
        branch_scope = normalize_branch_path_to_existing_roots(
            str(item.get("branch_scope") or blueprint.get("branch_scope") or "").strip()
        )
        root_scope = str(item.get("root_scope") or "").strip() or (branch_scope.split("/", 1)[0] if branch_scope else "CoreEgo")
        tactic_key = str(item.get("tactic_key") or f"tactic::{family}::{index}").strip()
        actionable_rule = str(item.get("actionable_rule") or blueprint.get("default_rule") or "").strip()
        situation_trigger = str(item.get("situation_trigger") or topic_label_ko(family) or family).strip()
        semantic_signals = self._dedupe_keep_order(list(item.get("semantic_signals", []) or []) + list(blueprint.get("semantic_signals", []) or []))
        preferred_tools = self._dedupe_keep_order(list(item.get("preferred_tools", []) or []) + list(blueprint.get("preferred_tools", []) or []))
        disallowed_tools = self._dedupe_keep_order(list(item.get("disallowed_tools", []) or []) + list(blueprint.get("disallowed_tools", []) or []))
        must_include = self._dedupe_keep_order(list(item.get("must_include", []) or []) + list(blueprint.get("must_include", []) or []))
        must_avoid = self._dedupe_keep_order(list(item.get("must_avoid", []) or []) + list(blueprint.get("must_avoid", []) or []))
        evidence_priority = self._dedupe_keep_order(list(item.get("evidence_priority", []) or []) + list(blueprint.get("evidence_priority", []) or []))
        try:
            priority_weight = float(item.get("priority_weight", 5.0) or 5.0)
        except (TypeError, ValueError):
            priority_weight = 5.0
        try:
            confidence_gate = float(item.get("confidence_gate", blueprint.get("confidence_gate", 0.55)) or blueprint.get("confidence_gate", 0.55))
        except (TypeError, ValueError):
            confidence_gate = float(blueprint.get("confidence_gate", 0.55) or 0.55)

        normalized_cards.append(
            TacticalThoughtItem(
                situation_trigger=situation_trigger,
                actionable_rule=actionable_rule,
                priority_weight=priority_weight,
                applies_to_phase=str(item.get("applies_to_phase") or "0").strip() or "0",
                tactic_key=tactic_key,
                target_family=family,
                root_scope=root_scope,
                branch_scope=branch_scope,
                semantic_signals=semantic_signals,
                preferred_next_hop=str(item.get("preferred_next_hop") or blueprint.get("preferred_next_hop") or "").strip(),
                preferred_direct_strategy=str(item.get("preferred_direct_strategy") or blueprint.get("preferred_direct_strategy") or "").strip(),
                preferred_tools=preferred_tools,
                disallowed_tools=disallowed_tools,
                tone_recipe=str(item.get("tone_recipe") or blueprint.get("tone_recipe") or "").strip(),
                must_include=must_include,
                must_avoid=must_avoid,
                repair_recipe=str(item.get("repair_recipe") or blueprint.get("repair_recipe") or "").strip(),
                evidence_priority=evidence_priority,
                confidence_gate=confidence_gate,
                status=str(item.get("status") or "active").strip() or "active",
            ).model_dump()
        )

    if normalized_cards:
        return normalized_cards

    for index, family in enumerate(self._plan_topics(rem_plan)):
        blueprint = dict(blueprints.get(family, blueprints["field_repair"]))
        branch_scope = normalize_branch_path_to_existing_roots(str(blueprint.get("branch_scope") or "").strip())
        root_scope = branch_scope.split("/", 1)[0] if branch_scope else "CoreEgo"
        normalized_cards.append(
            TacticalThoughtItem(
                situation_trigger=topic_label_ko(family) or family,
                actionable_rule=str(blueprint.get("default_rule") or "").strip(),
                priority_weight=5.0,
                applies_to_phase="0",
                tactic_key=f"tactic::{family}::fallback::{index}",
                target_family=family,
                root_scope=root_scope,
                branch_scope=branch_scope,
                semantic_signals=list(blueprint.get("semantic_signals", []) or []),
                preferred_next_hop=str(blueprint.get("preferred_next_hop") or "").strip(),
                preferred_direct_strategy=str(blueprint.get("preferred_direct_strategy") or "").strip(),
                preferred_tools=list(blueprint.get("preferred_tools", []) or []),
                disallowed_tools=list(blueprint.get("disallowed_tools", []) or []),
                tone_recipe=str(blueprint.get("tone_recipe") or "").strip(),
                must_include=list(blueprint.get("must_include", []) or []),
                must_avoid=list(blueprint.get("must_avoid", []) or []),
                repair_recipe=str(blueprint.get("repair_recipe") or "").strip(),
                evidence_priority=list(blueprint.get("evidence_priority", []) or []),
                confidence_gate=float(blueprint.get("confidence_gate", 0.55) or 0.55),
                status="active",
            ).model_dump()
        )
    return normalized_cards

def _route_policy_from_tactic(self, tactic: dict, policy_source: str):
    if not isinstance(tactic, dict):
        return {}
    preferred_next_hop = str(tactic.get("preferred_next_hop") or "").strip()
    preferred_direct_strategy = str(tactic.get("preferred_direct_strategy") or "").strip()
    preferred_tools = [str(tool or "").strip() for tool in tactic.get("preferred_tools", []) or [] if str(tool or "").strip()]
    branch_scope = str(tactic.get("branch_scope") or "").strip()
    target_family = str(tactic.get("target_family") or "fallback").strip() or "fallback"
    if not preferred_next_hop:
        if preferred_tools:
            preferred_next_hop = "phase_1"
        elif preferred_direct_strategy:
            preferred_next_hop = "phase_3"
        else:
            preferred_next_hop = "phase_2a"
    fallback_next_hop = "phase_2a" if preferred_next_hop in {"phase_3", "phase_1", "tool_first"} else "-1a_thinker"
    return RoutePolicyItem(
        policy_key=f"policy::{str(tactic.get('tactic_key') or target_family).strip()}",
        turn_family=target_family,
        answer_shape_hint=preferred_direct_strategy or target_family,
        trigger_signals=list(tactic.get("semantic_signals", []) or []),
        preferred_next_hop="phase_1" if preferred_next_hop == "tool_first" else preferred_next_hop,
        fallback_next_hop=fallback_next_hop,
        preferred_direct_strategy=preferred_direct_strategy,
        requires_grounding=preferred_next_hop != "phase_3" or bool(preferred_tools),
        requires_recent_context=True,
        requires_active_offer=False,
        requires_history_scope="/history_review" in branch_scope or "/dialogue_review" in branch_scope,
        router_mode="policy_first",
        match_priority=max(float(tactic.get("priority_weight", 5.0) or 5.0) / 10.0, 0.45),
        confidence_gate=float(tactic.get("confidence_gate", 0.55) or 0.55),
        rationale=str(tactic.get("actionable_rule") or "").strip(),
        compiled_from_tactic_key=str(tactic.get("tactic_key") or "").strip(),
        policy_source=policy_source,
        status=str(tactic.get("status") or "active"),
    ).model_dump()

def _tool_doctrine_from_tactic(self, tactic: dict, policy_source: str):
    if not isinstance(tactic, dict):
        return {}
    preferred_tools = [str(tool or "").strip() for tool in tactic.get("preferred_tools", []) or [] if str(tool or "").strip()]
    disallowed_tools = [str(tool or "").strip() for tool in tactic.get("disallowed_tools", []) or [] if str(tool or "").strip()]
    if not preferred_tools and not disallowed_tools:
        return {}
    target_family = str(tactic.get("target_family") or "fallback").strip() or "fallback"
    return ToolDoctrineItem(
        doctrine_key=f"doctrine::{str(tactic.get('tactic_key') or target_family).strip()}",
        target_family=target_family,
        recommended_tools=preferred_tools,
        tool_order=preferred_tools,
        query_rewrite_rules=["keep root-first retrieval"],
        source_priority=["Dream", "TurnProcess", "PastRecord"],
        avoid_patterns=["generic clarification loop"],
        success_signals=["grounded source anchor found"],
        failure_signals=["no grounded source found"],
        execution_mode="policy_guided",
        rationale=str(tactic.get("actionable_rule") or "").strip(),
        compiled_from_tactic_key=str(tactic.get("tactic_key") or "").strip(),
        policy_source=policy_source,
        status=str(tactic.get("status") or "active"),
    ).model_dump()

def _build_policy_doctrine_bundle(self, state: MidnightState):
    rem_plan = state.get("rem_plan", {}) if isinstance(state.get("rem_plan"), dict) else {}
    phase_7 = state.get("phase_7_audit", {}) if isinstance(state.get("phase_7_audit"), dict) else {}
    tool_runs = state.get("tool_runs", []) if isinstance(state.get("tool_runs"), list) else []
    tactical = state.get("tactical_doctrine", {}) if isinstance(state.get("tactical_doctrine"), dict) else {}

    priority_topics = self._plan_topics(rem_plan)
    policy_source = str(rem_plan.get("governor_key") or "nightly_reflection").strip() or "nightly_reflection"
    route_policies = []
    tool_doctrines = []
    normalized_tactics = self._normalize_tactical_cards(tactical, rem_plan, phase_7)
    covered_families = set()

    for tactic_item in normalized_tactics:
        if not isinstance(tactic_item, dict):
            continue
        family = str(tactic_item.get("target_family") or "").strip()
        if family:
            covered_families.add(family)
        compiled_policy = self._route_policy_from_tactic(
            tactic_item,
            policy_source=f"tactical::{str(tactic_item.get('tactic_key') or family).strip()}",
        )
        if compiled_policy:
            route_policies.append(compiled_policy)
        compiled_doctrine = self._tool_doctrine_from_tactic(
            tactic_item,
            policy_source=f"tactical::{str(tactic_item.get('tactic_key') or family).strip()}",
        )
        if compiled_doctrine:
            tool_doctrines.append(compiled_doctrine)

    policy_templates = {
        "personal_history_review": {
            "turn_family": "personal_history_review",
            "answer_shape_hint": "history_review",
            "preferred_next_hop": "phase_2a",
            "fallback_next_hop": "-1a_thinker",
            "preferred_direct_strategy": "",
            "requires_grounding": True,
            "requires_recent_context": True,
            "requires_active_offer": False,
            "requires_history_scope": True,
            "trigger_signals": ["history", "past", "diary", "record"],
            "router_mode": "policy_first",
            "match_priority": 0.88,
            "rationale": "Advisory policy for grounded personal-history review.",
        },
        "recent_dialogue_review": {
            "turn_family": "dialogue_review",
            "answer_shape_hint": "review_recent_dialogue",
            "preferred_next_hop": "phase_2a",
            "fallback_next_hop": "-1a_thinker",
            "preferred_direct_strategy": "",
            "requires_grounding": True,
            "requires_recent_context": True,
            "requires_active_offer": False,
            "requires_history_scope": False,
            "trigger_signals": ["dialogue", "conversation", "summary", "recap"],
            "router_mode": "policy_first",
            "match_priority": 0.84,
            "rationale": "Advisory policy for recent-dialogue review.",
        },
        "self_analysis_snapshot": {
            "turn_family": "reflective_direct",
            "answer_shape_hint": "self_analysis_snapshot",
            "preferred_next_hop": "phase_3",
            "fallback_next_hop": "-1a_thinker",
            "preferred_direct_strategy": "self_analysis_snapshot",
            "requires_grounding": False,
            "requires_recent_context": True,
            "requires_active_offer": False,
            "requires_history_scope": False,
            "trigger_signals": ["self", "pattern", "snapshot"],
            "router_mode": "policy_first",
            "match_priority": 0.93,
            "rationale": "Advisory policy for self-analysis snapshots.",
        },
        "tool_routing": {
            "turn_family": "tool_heavy",
            "answer_shape_hint": "investigate_now",
            "preferred_next_hop": "phase_1",
            "fallback_next_hop": "phase_2a",
            "preferred_direct_strategy": "",
            "requires_grounding": True,
            "requires_recent_context": False,
            "requires_active_offer": False,
            "requires_history_scope": False,
            "trigger_signals": ["tool", "search", "artifact", "read"],
            "router_mode": "policy_first",
            "match_priority": 0.9,
            "rationale": "Advisory policy for tool-heavy turns.",
        },
    }

    doctrine_templates = {
        "personal_history_review": {
            "target_family": "personal_history_review",
            "recommended_tools": ["tool_read_full_diary", "tool_scroll_chat_log"],
            "tool_order": ["tool_read_full_diary", "tool_scroll_chat_log", "tool_search_memory"],
            "query_rewrite_rules": ["keep root-first retrieval"],
            "source_priority": ["Dream", "TurnProcess", "PastRecord"],
            "avoid_patterns": ["generic clarification loop"],
            "success_signals": ["grounded source anchor found"],
            "failure_signals": ["no grounded source found"],
            "rationale": "Personal-history review should start from date/source-grounded evidence instead of broad memory search.",
        },
        "recent_dialogue_review": {
            "target_family": "dialogue_review",
            "recommended_tools": ["phase_2a_recent_dialogue_review"],
            "tool_order": ["phase_2a_recent_dialogue_review", "tool_scroll_chat_log"],
            "query_rewrite_rules": ["keep root-first retrieval"],
            "source_priority": ["Dream", "TurnProcess", "PastRecord"],
            "avoid_patterns": ["generic clarification loop"],
            "success_signals": ["grounded source anchor found"],
            "failure_signals": ["no grounded source found"],
            "rationale": "Recent-dialogue review should inspect the latest raw turns before broad synthesis.",
        },
        "self_analysis_snapshot": {
            "target_family": "reflective_direct",
            "recommended_tools": ["phase_3_direct_delivery"],
            "tool_order": ["phase_3_direct_delivery"],
            "query_rewrite_rules": ["keep root-first retrieval"],
            "source_priority": ["Dream", "TurnProcess", "PastRecord"],
            "avoid_patterns": ["generic clarification loop"],
            "success_signals": ["grounded source anchor found"],
            "failure_signals": ["no grounded source found"],
            "rationale": "When self-analysis is answerable from visible context, answer directly from that context.",
        },
        "tool_routing": {
            "target_family": "tool_heavy",
            "recommended_tools": self._dedupe_keep_order([
                str(run.get("tool") or "").strip() for run in tool_runs if isinstance(run, dict) and str(run.get("tool") or "").strip()
            ]) or ["tool_read_artifact", "tool_search_memory"],
            "tool_order": self._dedupe_keep_order([
                str(run.get("tool") or "").strip() for run in tool_runs if isinstance(run, dict) and str(run.get("tool") or "").strip()
            ]) or ["tool_read_artifact", "tool_search_memory"],
            "query_rewrite_rules": ["keep root-first retrieval"],
            "source_priority": ["Dream", "TurnProcess", "PastRecord"],
            "avoid_patterns": ["generic clarification loop"],
            "success_signals": ["grounded source anchor found"],
            "failure_signals": ["no grounded source found"],
            "rationale": "Tool-centered flows should follow evidence-backed tool order instead of ad hoc routing.",
        },
        "field_repair": {
            "target_family": "field_repair",
            "recommended_tools": ["phase_2a_recent_dialogue_review", "tool_search_memory"],
            "tool_order": ["phase_2a_recent_dialogue_review", "tool_search_memory"],
            "query_rewrite_rules": ["keep root-first retrieval"],
            "source_priority": ["Dream", "TurnProcess", "PastRecord"],
            "avoid_patterns": ["generic clarification loop"],
            "success_signals": ["grounded source anchor found"],
            "failure_signals": ["no grounded source found"],
            "rationale": "Field repair should diagnose failure type and recent handoff before broad retrieval.",
        },
    }

    for topic in priority_topics:
        if topic in covered_families:
            continue
        template = policy_templates.get(topic)
        if template:
            route_policies.append(
                RoutePolicyItem(
                    policy_key=f"policy::{template['turn_family']}::{template['answer_shape_hint']}",
                    turn_family=template["turn_family"],
                    answer_shape_hint=template["answer_shape_hint"],
                    trigger_signals=template["trigger_signals"],
                    preferred_next_hop=template["preferred_next_hop"],
                    fallback_next_hop=template["fallback_next_hop"],
                    preferred_direct_strategy=template["preferred_direct_strategy"],
                    requires_grounding=template["requires_grounding"],
                    requires_recent_context=template["requires_recent_context"],
                    requires_active_offer=template["requires_active_offer"],
                    requires_history_scope=template["requires_history_scope"],
                    router_mode=template["router_mode"],
                    match_priority=float(template["match_priority"]),
                    confidence_gate=0.55,
                    rationale=template["rationale"],
                    policy_source=policy_source,
                    status="active",
                ).model_dump()
            )
        doctrine = doctrine_templates.get(topic)
        if doctrine:
            tool_doctrines.append(
                ToolDoctrineItem(
                    doctrine_key=f"doctrine::{doctrine['target_family']}",
                    target_family=doctrine["target_family"],
                    recommended_tools=doctrine["recommended_tools"],
                    tool_order=doctrine["tool_order"],
                    query_rewrite_rules=["keep root-first retrieval"],
                    source_priority=["Dream", "TurnProcess", "PastRecord"],
                    avoid_patterns=["generic clarification loop"],
                    success_signals=["grounded source anchor found"],
                    failure_signals=["no grounded source found"],
                    execution_mode="policy_guided",
                    rationale=doctrine["rationale"],
                    policy_source=policy_source,
                    status="active",
                ).model_dump()
            )

    if not route_policies:
        route_policies.append(
            RoutePolicyItem(
                policy_key="policy::fallback::planner",
                turn_family="fallback",
                answer_shape_hint="",
                trigger_signals=[],
                preferred_next_hop="-1a_thinker",
                fallback_next_hop="phase_2a",
                preferred_direct_strategy="",
                requires_grounding=False,
                requires_recent_context=False,
                requires_active_offer=False,
                requires_history_scope=False,
                router_mode="fallback",
                match_priority=0.1,
                confidence_gate=0.35,
                rationale="Use the fallback planner path only when no better contract exists.",
                policy_source=policy_source,
                status="active",
            ).model_dump()
        )

    if not tool_doctrines:
        tool_doctrines.append(
            ToolDoctrineItem(
                doctrine_key="doctrine::field_repair::fallback",
                target_family="field_repair",
                recommended_tools=["phase_2a_recent_dialogue_review", "tool_search_memory"],
                tool_order=["phase_2a_recent_dialogue_review", "tool_search_memory"],
                query_rewrite_rules=["keep root-first retrieval"],
                source_priority=["Dream", "TurnProcess", "PastRecord"],
                avoid_patterns=["generic clarification loop"],
                success_signals=["grounded source anchor found"],
                failure_signals=["no grounded source found"],
                execution_mode="fallback",
                rationale="If no tool doctrine exists, keep one minimal field-repair doctrine for advisory context.",
                policy_source=policy_source,
                status="active",
            ).model_dump()
        )

    deduped_route_policies = []
    seen_policy_keys = set()
    for policy in route_policies:
        if not isinstance(policy, dict):
            continue
        policy_key = str(policy.get("policy_key") or "").strip()
        if not policy_key or policy_key in seen_policy_keys:
            continue
        seen_policy_keys.add(policy_key)
        deduped_route_policies.append(policy)

    deduped_tool_doctrines = []
    seen_doctrine_keys = set()
    for doctrine in tool_doctrines:
        if not isinstance(doctrine, dict):
            continue
        doctrine_key = str(doctrine.get("doctrine_key") or "").strip()
        if not doctrine_key or doctrine_key in seen_doctrine_keys:
            continue
        seen_doctrine_keys.add(doctrine_key)
        deduped_tool_doctrines.append(doctrine)

    return {
        "route_policies": deduped_route_policies,
        "tool_doctrines": deduped_tool_doctrines,
        "policy_summary": {
            "route_policy_count": len(deduped_route_policies),
            "tool_doctrine_count": len(deduped_tool_doctrines),
            "priority_topics": priority_topics,
            "valuable_tactics": bool(tactical.get("is_valuable_tactics")),
            "compiled_tactic_count": len(normalized_tactics),
            "active_supply_topics": [
                str(topic.get("topic_slug") or "").strip()
                for topic in phase_7.get("classified_topics", [])
                if isinstance(topic, dict) and str(topic.get("topic_slug") or "").strip()
            ],
        },
    }
