"""StrategyCouncil department for the midnight reflection graph.

This module is a mechanical extraction from Core.midnight_reflection.DreamWeaver.
It keeps the original behavior while moving the department body out of the god-file.
"""

import json
import math
import re
import unicodedata
from datetime import datetime

import ollama

from Core.midnight_reflection_contracts import MidnightState
from Core.rem_governor import (
    AttentionDigestItem,
    ChildBranchProposalItem,
    GoalGapItem,
    GoalTreeItem,
    NightlyScopeItem,
    StrategyCouncilStateSchema,
    dedupe_keep_order,
)


def _default_strategy_council_state(self, rem_governor=None):
    governor = rem_governor if isinstance(rem_governor, dict) and rem_governor else self._default_rem_governor_state()
    root_entities = self._dedupe_keep_order(list(governor.get("root_entities", []) or []))
    person_root = next((root for root in root_entities if str(root).startswith("Person:")), "Person:root")
    coreego_root = next((root for root in root_entities if str(root).startswith("CoreEgo:")), "CoreEgo:root")
    if not root_entities:
        root_entities = [person_root, coreego_root]
    default_goals = []
    if any(str(root or "").startswith("Person:") for root in root_entities):
        default_goals.append(
            GoalTreeItem(
                goal_key="goal::person_root_understanding",
                root_entity=person_root,
                title="Person root understanding",
                summary="Deepen the person-root understanding using history and self-model branches.",
                goal_type="expand",
                branch_paths=[
                    self._branch_path_for_topic("person_definition"),
                    self._branch_path_for_topic("person_life_history"),
                    self._branch_path_for_topic("person_current_state"),
                    self._branch_path_for_topic("person_development_pattern"),
                    self._branch_path_for_topic("personal_history_review"),
                    self._branch_path_for_topic("self_analysis_snapshot"),
                ],
                priority_weight=0.72,
            ).model_dump()
        )
    if any(str(root or "").startswith("CoreEgo:") for root in root_entities):
        default_goals.append(
            GoalTreeItem(
                goal_key="goal::coreego_field_stability",
                root_entity=coreego_root,
                title="CoreEgo field stability",
                summary="Stabilize field response, tool use, and social repair branches under the CoreEgo root.",
                goal_type="stabilize",
                branch_paths=[
                    self._branch_path_for_topic("coreego_definition"),
                    self._branch_path_for_topic("coreego_history"),
                    self._branch_path_for_topic("coreego_current_state"),
                    self._branch_path_for_topic("coreego_field_response"),
                    self._branch_path_for_topic("coreego_self_model"),
                    self._branch_path_for_topic("recent_dialogue_review"),
                    self._branch_path_for_topic("tool_routing"),
                    self._branch_path_for_topic("field_repair"),
                ],
                priority_weight=0.84,
            ).model_dump()
        )
    default_scope = []
    for index, branch_path in enumerate(self._dedupe_keep_order(list(governor.get("required_branches", []) or []))[:4], start=1):
        root_entity = self._root_entity_from_asset_scope(branch_path)
        default_scope.append(
            NightlyScopeItem(
                scope_key=f"scope::{self._safe_slug_fragment(branch_path)}",
                root_entity=root_entity,
                branch_path=branch_path,
                scope_reason=f"Seed scope for {branch_path} branch upkeep.",
                target_action="repair" if "field_repair" in branch_path else "refresh",
                evidence_start_points=self._dedupe_keep_order(list(governor.get("evidence_roots", []) or []))[:4],
                priority_weight=max(0.4, 0.8 - (index * 0.08)),
            ).model_dump()
        )
    payload = {
        "strategy_key": "strategy_council_v1",
        "governor_key": str(governor.get("governor_key") or "rem_governor_v1"),
        "target_roots": root_entities,
        "goal_tree": default_goals,
        "goal_gaps": [],
        "tonight_scope": default_scope,
        "child_branch_proposals": [],
        "proposal_decisions": [],
        "attention_shortlist": [],
        "remembered_self_summary": str(governor.get("governor_summary") or "Governor keeps the remembered self in a root-level compressed summary."),
        "planning_self_summary": "StrategyCouncil critiques the remembered self and turns it into a narrow nightly plan.",
        "editorial_mandates": [
            "Keep the remembered self grounded in root facts and branch evidence.",
            "Prefer repairs before speculative growth when the field is unstable.",
        ],
        "scope_budget": {
            "max_scope_count": 6,
            "max_new_growth": 2,
            "max_refresh": 3,
            "max_repair": 2,
        },
        "planning_horizon": "rolling_3_nights",
        "strategy_summary": "StrategyCouncil keeps a rolling root-level goal tree and a narrow nightly scope.",
        "next_night_handoff": [
            "Continue deepening the person-root understanding branches.",
            "Keep tracking field stability under the CoreEgo root.",
        ],
        "status": "active",
    }
    return StrategyCouncilStateSchema(**payload).model_dump()

def _load_existing_strategy_council_state(self, strategy_key="strategy_council_v1"):
    if not self.neo4j_driver:
        return {}
    if not self._neo4j_label_exists("StrategyCouncil"):
        return {}
    try:
        with self.neo4j_driver.session() as session:
            rows = session.run(
                """
                MATCH (sc:StrategyCouncil)
                RETURN sc{.*} AS props
                """,
            )
            record = None
            for candidate in rows:
                props = dict(candidate.get("props") or {})
                if str(props.get("strategy_key") or "").strip() == str(strategy_key or "").strip():
                    record = candidate
                    break
            if not record:
                return {}
            props = dict(record.get("props") or {})

            def _parse_json_list(field_name):
                raw = str(props.get(field_name) or "").strip()
                if not raw:
                    return []
                try:
                    parsed = json.loads(raw)
                except Exception:
                    return []
                return [dict(item) for item in parsed if isinstance(item, dict)]

            def _parse_json_dict(field_name, default=None):
                raw = str(props.get(field_name) or "").strip()
                if not raw:
                    return dict(default or {})
                try:
                    parsed = json.loads(raw)
                except Exception:
                    return dict(default or {})
                return dict(parsed) if isinstance(parsed, dict) else dict(default or {})

            payload = {
                "strategy_key": str(props.get("strategy_key") or strategy_key),
                "governor_key": str(props.get("governor_key") or "rem_governor_v1"),
                "target_roots": self._dedupe_keep_order(list(props.get("target_roots", []) or [])),
                "goal_tree": _parse_json_list("goal_tree_json"),
                "goal_gaps": _parse_json_list("goal_gaps_json"),
                "tonight_scope": _parse_json_list("tonight_scope_json"),
                "child_branch_proposals": _parse_json_list("child_branch_proposals_json"),
                "proposal_decisions": _parse_json_list("proposal_decisions_json"),
                "attention_shortlist": _parse_json_list("attention_shortlist_json"),
                "remembered_self_summary": str(props.get("remembered_self_summary") or ""),
                "planning_self_summary": str(props.get("planning_self_summary") or ""),
                "editorial_mandates": self._dedupe_keep_order(list(props.get("editorial_mandates", []) or [])),
                "scope_budget": _parse_json_dict(
                    "scope_budget_json",
                    {"max_scope_count": 6, "max_new_growth": 2, "max_refresh": 3, "max_repair": 2},
                ),
                "planning_horizon": str(props.get("planning_horizon") or "rolling_3_nights"),
                "strategy_summary": str(props.get("strategy_summary") or ""),
                "next_night_handoff": self._dedupe_keep_order(list(props.get("next_night_handoff", []) or [])),
                "status": str(props.get("status") or "active"),
            }
            return StrategyCouncilStateSchema(**payload).model_dump()
    except Exception:
        return {}

def _collect_strategy_evidence_points(self, dream_rows):
    evidence_points = []
    normalized_fragments = []
    for row in dream_rows if isinstance(dream_rows, list) else []:
        if not isinstance(row, dict):
            try:
                row = dict(row)
            except Exception:
                row = {}
        if not isinstance(row, dict):
            continue
        for key in ("input", "answer", "turn_summary"):
            value = str(row.get(key) or "").strip()
            if value:
                normalized_fragments.append(value)
        dream_id = str(row.get("dream_id") or "").strip()
        process_id = str(row.get("process_id") or "").strip()
        if dream_id:
            evidence_points.append(f"Dream:{dream_id}")
        if process_id:
            evidence_points.append(f"TurnProcess:{process_id}")
        process_summary = self._normalize_phase_payload(row.get("process_summary"))
        if isinstance(process_summary, dict):
            for source_id in process_summary.get("used_sources", []) or []:
                normalized_source = str(source_id or "").strip()
                if normalized_source:
                    evidence_points.append(normalized_source)
    normalized_text = unicodedata.normalize("NFKC", " ".join(normalized_fragments))
    return normalized_text, self._dedupe_keep_order(evidence_points)

def _strategy_attention_tokens(text):
    normalized = unicodedata.normalize("NFKC", str(text or "").lower())
    return dedupe_keep_order(re.findall(r"[0-9a-zA-Z가-힣/_-]{2,}", normalized))

def _strategy_lexical_overlap_score(cls, query_text, candidate_text):
    query_tokens = set(cls._strategy_attention_tokens(query_text))
    candidate_tokens = set(cls._strategy_attention_tokens(candidate_text))
    if not query_tokens or not candidate_tokens:
        return 0.0
    overlap = len(query_tokens & candidate_tokens)
    return min(1.0, overlap / max(1, min(len(query_tokens), 12)))

def _strategy_cosine_similarity(vec1, vec2):
    if not isinstance(vec1, list) or not isinstance(vec2, list) or not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    try:
        dot_product = sum(float(a) * float(b) for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(float(a) * float(a) for a in vec1))
        norm_b = math.sqrt(sum(float(b) * float(b) for b in vec2))
    except Exception:
        return 0.0
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def _strategy_embed_text(text):
    normalized = unicodedata.normalize("NFKC", str(text or "").strip())
    if not normalized:
        return []
    for model_name in ("nomic-embed-text", "mxbai-embed-large"):
        try:
            response = ollama.embeddings(model=model_name, prompt=normalized)
            embedding = response.get("embedding")
            if isinstance(embedding, list) and embedding:
                return embedding
        except Exception:
            continue
    return []

def _strategy_digest_attention_text(self, digest):
    if not isinstance(digest, dict):
        return ""
    parts = [
        str(digest.get("title") or "").strip(),
        str(digest.get("summary") or "").strip(),
        str(digest.get("branch_path") or "").strip(),
        " ".join(str(item or "").strip() for item in (digest.get("related_topics", []) or []) if str(item or "").strip()),
        " ".join(str(item or "").strip() for item in (digest.get("evidence_addresses", []) or [])[:3] if str(item or "").strip()),
    ]
    return unicodedata.normalize("NFKC", " ".join(part for part in parts if part)).strip()

def _strategy_cluster_attention_text(self, cluster):
    if not isinstance(cluster, dict):
        return ""
    parts = [
        str(cluster.get("title") or cluster.get("name") or "").strip(),
        str(cluster.get("summary") or "").strip(),
        str(cluster.get("synthesis_statement") or "").strip(),
        str(cluster.get("branch_path") or "").strip(),
        str(cluster.get("topic_slug") or "").strip(),
        f"u_cluster_purity={cluster.get('u_cluster_purity', '')}",
        f"u_synthesis_score={cluster.get('u_synthesis_score', '')}",
        " ".join(str(item or "").strip() for item in (cluster.get("inverse_relation_updates", []) or [])[:3] if str(item or "").strip()),
        " ".join(str(item or "").strip() for item in (cluster.get("tags", []) or []) if str(item or "").strip()),
    ]
    return unicodedata.normalize("NFKC", " ".join(part for part in parts if part)).strip()

def _dedupe_attention_shortlist(items):
    seen_assets = set()
    seen_branches = set()
    result = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        asset_key = str(item.get("asset_key") or item.get("digest_key") or item.get("cluster_key") or "").strip()
        branch_path = str(item.get("branch_path") or "").strip()
        if not asset_key or asset_key in seen_assets or (branch_path and branch_path in seen_branches):
            continue
        seen_assets.add(asset_key)
        if branch_path:
            seen_branches.add(branch_path)
        result.append(item)
    return result

def _build_strategy_attention_shortlist(
    self,
    *,
    existing_branch_digests,
    existing_concept_clusters,
    normalized_text,
    remembered_self_summary,
    goal_tree,
    goal_gaps,
    branch_health_map,
    required_branches,
):
    digests = [dict(item) for item in (existing_branch_digests or []) if isinstance(item, dict)]
    concept_clusters = [dict(item) for item in (existing_concept_clusters or []) if isinstance(item, dict)]
    if not digests and not concept_clusters:
        return []

    goal_titles = [str(item.get("title") or "").strip() for item in goal_tree if isinstance(item, dict)]
    goal_summaries = [str(item.get("summary") or "").strip() for item in goal_tree if isinstance(item, dict)]
    gap_titles = [str(item.get("title") or "").strip() for item in goal_gaps if isinstance(item, dict)]
    gap_summaries = [str(item.get("summary") or "").strip() for item in goal_gaps if isinstance(item, dict)]
    query_text = unicodedata.normalize(
        "NFKC",
        " ".join(
            part for part in [
                normalized_text,
                remembered_self_summary,
                " ".join(goal_titles[:4]),
                " ".join(goal_summaries[:3]),
                " ".join(gap_titles[:4]),
                " ".join(gap_summaries[:2]),
            ] if part
        ),
    ).strip()
    query_vector = self._strategy_embed_text(query_text)
    current_time_ms = int(datetime.now().timestamp() * 1000)
    required_branch_set = set(required_branches or [])
    results = []

    for digest in digests:
        digest_key = str(digest.get("digest_key") or "").strip()
        branch_path = str(digest.get("branch_path") or "").strip()
        if not digest_key or not branch_path:
            continue
        digest_text = self._strategy_digest_attention_text(digest)
        if not digest_text:
            continue
        candidate_vector = digest.get("attention_embedding")
        if not isinstance(candidate_vector, list) or not candidate_vector:
            candidate_vector = self._strategy_embed_text(digest_text) if query_vector else []
        semantic_score = self._strategy_cosine_similarity(query_vector, candidate_vector) if query_vector and candidate_vector else 0.0
        lexical_score = self._strategy_lexical_overlap_score(query_text, digest_text)
        support_score = min(
            1.0,
            (len(digest.get("supporting_dream_ids", []) or []) * 0.12)
            + (min(len(digest.get("evidence_addresses", []) or []), 5) * 0.06)
            + (len(digest.get("attached_tactic_ids", []) or []) * 0.09)
            + (len(digest.get("attached_policy_keys", []) or []) * 0.07)
            + (len(digest.get("attached_doctrine_keys", []) or []) * 0.07),
        )
        pressure_score = 0.35
        if branch_path in required_branch_set:
            pressure_score += 0.15
        health_hint = str(branch_health_map.get(branch_path) or "").strip()
        if health_hint in {"needs_growth", "planned", "seed"}:
            pressure_score += 0.22
        if any(str(item.get("branch_path") or "").strip() == branch_path for item in goal_gaps if isinstance(item, dict)):
            pressure_score += 0.12
        related_topics = [str(item or "").strip() for item in (digest.get("related_topics", []) or []) if str(item or "").strip()]
        if any(topic in query_text for topic in related_topics):
            pressure_score += 0.08
        pressure_score = min(1.0, pressure_score)

        created_at = digest.get("created_at") or digest.get("updated_at") or 0
        try:
            created_at = int(created_at)
        except Exception:
            created_at = 0
        if created_at > 0:
            age_days = max(0.0, (current_time_ms - created_at) / 86400000.0)
            recency_score = max(0.0, 1.0 - min(age_days, 21.0) / 21.0)
        else:
            recency_score = 0.35

        final_score = min(
            0.999,
            (semantic_score * 0.50)
            + (lexical_score * 0.20)
            + (support_score * 0.15)
            + (pressure_score * 0.10)
            + (recency_score * 0.05),
        )
        if final_score < 0.22 and not (pressure_score >= 0.68 and support_score >= 0.24):
            continue

        why_now_parts = []
        if semantic_score >= 0.48:
            why_now_parts.append("current nightly context semantically aligns with this branch digest")
        if lexical_score >= 0.18:
            why_now_parts.append("surface terms overlap with tonight's evidence")
        if pressure_score >= 0.62:
            why_now_parts.append("branch pressure is still elevated")
        if support_score >= 0.28:
            why_now_parts.append("the digest already has enough tactics/policies/evidence attached")
        if not why_now_parts:
            why_now_parts.append("this digest is still relevant enough to keep near the planning surface")

        results.append(
            AttentionDigestItem(
                asset_type="branch_digest",
                asset_key=digest_key,
                digest_key=digest_key,
                branch_path=branch_path,
                title=str(digest.get("title") or branch_path),
                summary=str(digest.get("summary") or "")[:400],
                related_topics=related_topics[:6],
                final_score=round(final_score, 4),
                semantic_score=round(semantic_score, 4),
                lexical_score=round(lexical_score, 4),
                support_score=round(support_score, 4),
                pressure_score=round(pressure_score, 4),
                why_now="; ".join(why_now_parts),
            ).model_dump()
        )

    for cluster in concept_clusters:
        cluster_key = str(cluster.get("cluster_key") or "").strip()
        branch_path = str(cluster.get("branch_path") or "").strip()
        if not cluster_key or not branch_path:
            continue
        cluster_text = self._strategy_cluster_attention_text(cluster)
        if not cluster_text:
            continue
        candidate_vector = cluster.get("attention_embedding")
        if not isinstance(candidate_vector, list) or not candidate_vector:
            candidate_vector = self._strategy_embed_text(cluster_text) if query_vector else []
        semantic_score = self._strategy_cosine_similarity(query_vector, candidate_vector) if query_vector and candidate_vector else 0.0
        lexical_score = self._strategy_lexical_overlap_score(query_text, cluster_text)
        fact_count = len(cluster.get("fact_keys", []) or [])
        bucket_count = len(cluster.get("time_bucket_keys", []) or [])
        support_score = min(
            1.0,
            float(cluster.get("support_weight", 0.5) or 0.5)
            + min(fact_count, 5) * 0.07
            + min(bucket_count, 3) * 0.05,
        )
        pressure_score = 0.28
        if branch_path in required_branch_set:
            pressure_score += 0.12
        health_hint = str(branch_health_map.get(branch_path) or "").strip()
        if health_hint in {"needs_growth", "planned", "seed"}:
            pressure_score += 0.18
        if any(str(item.get("branch_path") or "").strip() == branch_path for item in goal_gaps if isinstance(item, dict)):
            pressure_score += 0.10
        topic_slug = str(cluster.get("topic_slug") or "").strip()
        tags = [str(item or "").strip() for item in (cluster.get("tags", []) or []) if str(item or "").strip()]
        if topic_slug and topic_slug in query_text:
            pressure_score += 0.08
        if any(tag and tag in query_text for tag in tags[:4]):
            pressure_score += 0.06
        pressure_score = min(1.0, pressure_score)

        created_at = cluster.get("created_at") or 0
        try:
            created_at = int(created_at)
        except Exception:
            created_at = 0
        if created_at > 0:
            age_days = max(0.0, (current_time_ms - created_at) / 86400000.0)
            recency_score = max(0.0, 1.0 - min(age_days, 30.0) / 30.0)
        else:
            recency_score = 0.3

        final_score = min(
            0.999,
            (semantic_score * 0.48)
            + (lexical_score * 0.18)
            + (support_score * 0.20)
            + (pressure_score * 0.09)
            + (recency_score * 0.05),
        )
        if final_score < 0.24 and not (support_score >= 0.58 and pressure_score >= 0.42):
            continue

        why_now_parts = []
        if semantic_score >= 0.46:
            why_now_parts.append("current nightly context semantically aligns with this concept cluster")
        if lexical_score >= 0.16:
            why_now_parts.append("surface terms overlap with cluster language")
        if support_score >= 0.62:
            why_now_parts.append("the cluster is already grounded in enough facts and time buckets")
        if pressure_score >= 0.46:
            why_now_parts.append("its parent branch is still strategically relevant")
        if not why_now_parts:
            why_now_parts.append("this concept cluster is close enough to the planning surface to stay active")

        results.append(
            AttentionDigestItem(
                asset_type="concept_cluster",
                asset_key=cluster_key,
                cluster_key=cluster_key,
                branch_path=branch_path,
                title=str(cluster.get("title") or cluster_key),
                summary=str(cluster.get("summary") or "")[:400],
                related_topics=[topic_slug] if topic_slug else tags[:6],
                final_score=round(final_score, 4),
                semantic_score=round(semantic_score, 4),
                lexical_score=round(lexical_score, 4),
                support_score=round(support_score, 4),
                pressure_score=round(pressure_score, 4),
                why_now="; ".join(why_now_parts),
            ).model_dump()
        )

    results.sort(key=lambda item: float(item.get("final_score", 0.0) or 0.0), reverse=True)
    return self._dedupe_attention_shortlist(results)[:7]

def _build_strategy_council_state(self, state: MidnightState):
    governor = state.get("rem_governor", {}) if isinstance(state.get("rem_governor"), dict) else {}
    if not governor:
        governor = self._default_rem_governor_state()
    existing = self._load_existing_strategy_council_state() or self._default_strategy_council_state(governor)
    branch_health_map = self._parse_branch_health_map(governor)
    required_branches = self._dedupe_keep_order(list(governor.get("required_branches", []) or []))
    known_branches = self._dedupe_keep_order(list(governor.get("known_branches", []) or []))
    root_entities = self._dedupe_keep_order(list(governor.get("root_entities", []) or [])) or list(existing.get("target_roots", []) or [])
    open_unknowns = self._dedupe_keep_order(list(governor.get("open_unknowns", []) or []))
    policy_inventory = [
        dict(item)
        for item in (governor.get("policy_inventory", []) or [])
        if isinstance(item, dict)
    ]
    existing_branch_digest_rows = [
        dict(item)
        for item in (state.get("existing_branch_digests", []) or [])
        if isinstance(item, dict) and str(item.get("branch_path") or "").strip()
    ]
    existing_branch_digests = {
        str(item.get("branch_path") or "").strip()
        for item in existing_branch_digest_rows
    }
    latest_child_branch_proposals = [
        dict(item)
        for item in (state.get("child_branch_proposals", []) or [])
        if isinstance(item, dict) and str(item.get("proposal_key") or "").strip()
    ]
    existing_child_branch_proposals = [
        dict(item)
        for item in (existing.get("child_branch_proposals", []) or [])
        if isinstance(item, dict) and str(item.get("proposal_key") or "").strip()
    ]
    child_branch_proposals = self._dedupe_child_branch_proposals(
        latest_child_branch_proposals + existing_child_branch_proposals
    )[:12]
    remembered_self_summary = str(governor.get("governor_summary") or existing.get("remembered_self_summary") or "").strip()
    normalized_text, evidence_points = self._collect_strategy_evidence_points(state.get("dream_rows", []))
    evidence_points = self._dedupe_keep_order(evidence_points + list(governor.get("evidence_roots", []) or []))
    person_root = next((root for root in root_entities if str(root).startswith("Person:")), "Person:root")
    coreego_root = next((root for root in root_entities if str(root).startswith("CoreEgo:")), "CoreEgo:root")

    goal_tree = []
    for root_entity in root_entities:
        root_branch_paths = [
            branch_path for branch_path in self._dedupe_keep_order(required_branches + known_branches)
            if str(branch_path or "").startswith(root_entity.split(":", 1)[0] + "/")
        ][:4]
        if str(root_entity).startswith("Person:"):
            goal_tree.append(
                GoalTreeItem(
                    goal_key="goal::person_root_understanding",
                    root_entity=root_entity,
                    title="Person root understanding",
                    summary="Deepen the person-root understanding using history and self-model branches.",
                    goal_type="expand",
                    branch_paths=root_branch_paths or [
                        self._branch_path_for_topic("personal_history_review"),
                        self._branch_path_for_topic("self_analysis_snapshot"),
                    ],
                    priority_weight=0.74,
                ).model_dump()
            )
        elif str(root_entity).startswith("CoreEgo:"):
            goal_tree.append(
                GoalTreeItem(
                    goal_key="goal::coreego_field_stability",
                    root_entity=root_entity,
                    title="CoreEgo field stability",
                    summary="Stabilize field response, tool use, and social repair under the CoreEgo root.",
                    goal_type="stabilize",
                    branch_paths=root_branch_paths or [
                        self._branch_path_for_topic("recent_dialogue_review"),
                        self._branch_path_for_topic("tool_routing"),
                        self._branch_path_for_topic("field_repair"),
                    ],
                    priority_weight=0.86,
                ).model_dump()
            )
    for branch_path, health_hint in list(branch_health_map.items())[:8]:
        if health_hint not in {"needs_growth", "planned", "seed"}:
            continue
        root_entity = self._root_entity_from_asset_scope(branch_path)
        goal_tree.append(
            GoalTreeItem(
                goal_key=f"goal::{self._safe_slug_fragment(branch_path)}",
                root_entity=root_entity,
                title=f"{branch_path} repair goal",
                summary=f"{branch_path} is still in {health_hint} state and needs branch-level follow-up.",
                goal_type="repair" if "repair" in branch_path else "refine",
                branch_paths=[branch_path],
                priority_weight=0.9 if "repair" in branch_path else 0.68,
            ).model_dump()
        )
    goal_tree = self._dedupe_goal_tree(goal_tree)

    goal_gaps = []
    for branch_path, health_hint in branch_health_map.items():
        if health_hint not in {"needs_growth", "planned", "seed"} and branch_path in existing_branch_digests:
            continue
        root_entity = self._root_entity_from_asset_scope(branch_path)
        severity = "high" if ("repair" in branch_path or "tool_doctrine" in branch_path) else "medium"
        summary = f"{branch_path} still needs attention; health={health_hint or 'unknown'}."
        if branch_path not in existing_branch_digests:
            summary += " No active branch digest was found for this branch."
        goal_gaps.append(
            GoalGapItem(
                gap_key=f"gap::{self._safe_slug_fragment(branch_path)}::{health_hint or 'unknown'}",
                root_entity=root_entity,
                branch_path=branch_path,
                title=f"{branch_path} gap",
                summary=summary,
                severity=severity,
                evidence_roots=evidence_points[:6],
            ).model_dump()
        )
    for index, text in enumerate(open_unknowns[:6], start=1):
        lowered = str(text or "").lower()
        root_entity = coreego_root if any(token in lowered for token in ["tool", "repair", "field", "ego", "response"]) else person_root
        goal_gaps.append(
            GoalGapItem(
                gap_key=f"gap::open_unknown::{index}",
                root_entity=root_entity,
                branch_path="",
                title=f"open_unknown_{index}",
                summary=text,
                severity="medium",
                evidence_roots=evidence_points[:4],
            ).model_dump()
        )
    for proposal in child_branch_proposals:
        proposed_branch_path = str(proposal.get("proposed_branch_path") or "").strip()
        parent_branch_path = str(proposal.get("parent_branch_path") or "").strip()
        root_entity = str(proposal.get("root_entity") or self._root_entity_from_asset_scope(parent_branch_path)).strip()
        topic_slug = str(proposal.get("topic_slug") or self._topic_slug_from_branch_path(proposed_branch_path)).strip()
        if not proposed_branch_path:
            continue
        goal_gaps.append(
            GoalGapItem(
                gap_key=f"gap::child_branch::{self._safe_slug_fragment(proposed_branch_path)}",
                root_entity=root_entity,
                branch_path=proposed_branch_path,
                title=f"{proposed_branch_path} child branch gap",
                summary=str(proposal.get("proposal_reason") or f"{parent_branch_path} is asking for a child branch around {topic_slug}."),
                severity="high" if float(proposal.get("pressure_score", 0.5) or 0.5) >= 0.82 else "medium",
                evidence_roots=self._dedupe_keep_order(
                    list(proposal.get("evidence_start_points", []) or []) + evidence_points[:4]
                )[:8],
            ).model_dump()
        )
    goal_gaps = self._dedupe_goal_gaps(goal_gaps)[:12]

    attention_shortlist = self._build_strategy_attention_shortlist(
        existing_branch_digests=existing_branch_digest_rows,
        existing_concept_clusters=state.get("existing_concept_clusters", []),
        normalized_text=normalized_text,
        remembered_self_summary=remembered_self_summary,
        goal_tree=goal_tree,
        goal_gaps=goal_gaps,
        branch_health_map=branch_health_map,
        required_branches=required_branches,
    )
    attention_score_map = {
        str(item.get("branch_path") or "").strip(): float(item.get("final_score", 0.0) or 0.0)
        for item in attention_shortlist
        if isinstance(item, dict) and str(item.get("branch_path") or "").strip()
    }
    attention_titles = [
        str(item.get("title") or item.get("branch_path") or "").strip()
        for item in attention_shortlist
        if isinstance(item, dict) and str(item.get("title") or item.get("branch_path") or "").strip()
    ]

    proposal_decisions = []
    accepted_child_branch_proposals = []
    deferred_child_branch_proposals = []
    for proposal in child_branch_proposals:
        pressure_score = float(proposal.get("pressure_score", 0.5) or 0.5)
        trigger_notes = [str(item or "").strip() for item in (proposal.get("trigger_notes", []) or []) if str(item or "").strip()]
        proposed_branch_path = str(proposal.get("proposed_branch_path") or "").strip()
        parent_branch_path = str(proposal.get("parent_branch_path") or "").strip()
        attention_bonus = max(
            attention_score_map.get(proposed_branch_path, 0.0),
            attention_score_map.get(parent_branch_path, 0.0),
        )
        weighted_pressure = min(0.999, pressure_score + (attention_bonus * 0.08))
        if weighted_pressure >= 0.8 and len(trigger_notes) >= 2:
            decision = "accept"
            rationale = "High pressure and repeated triggers justify branch growth in this nightly window."
            if attention_bonus >= 0.4:
                rationale += " Strategy attention is already surfacing this branch family."
            accepted_child_branch_proposals.append(proposal)
            priority_weight = min(0.98, weighted_pressure + 0.08)
        elif weighted_pressure >= 0.68:
            decision = "defer"
            rationale = "Signal is real, but the branch should be watched one more nightly pass before growth."
            deferred_child_branch_proposals.append(proposal)
            priority_weight = weighted_pressure
        else:
            decision = "reject"
            rationale = "Pressure is still too weak for a child branch."
            priority_weight = max(0.3, weighted_pressure - 0.1)
        proposal_decisions.append(
            {
                "proposal_key": str(proposal.get("proposal_key") or "").strip(),
                "proposed_branch_path": proposed_branch_path,
                "decision": decision,
                "rationale": rationale,
                "priority_weight": round(priority_weight, 3),
            }
        )
    accepted_child_branch_proposals = self._dedupe_child_branch_proposals(accepted_child_branch_proposals)[:6]
    deferred_child_branch_proposals = self._dedupe_child_branch_proposals(deferred_child_branch_proposals)[:6]

    repair_gap_count = sum(1 for gap in goal_gaps if str(gap.get("severity") or "").strip() == "high")
    scope_budget = {
        "max_scope_count": 6,
        "max_new_growth": 1 if repair_gap_count >= 3 else 2,
        "max_refresh": 2 if repair_gap_count >= 4 else 3,
        "max_repair": 3 if repair_gap_count >= 2 else 2,
    }

    editorial_mandates = [
        "Use the remembered self as a compression layer, not as a source of free invention.",
        "Prefer branch repair before speculative growth when field stability is weak.",
    ]
    if accepted_child_branch_proposals:
        editorial_mandates.append("Accepted child branch proposals should be translated into concrete blueprints tonight.")
    if deferred_child_branch_proposals:
        editorial_mandates.append("Deferred child branch proposals must leave a carry-forward note for the next nightly pass.")
    if open_unknowns:
        editorial_mandates.append("Keep one slot open for unresolved unknowns so the plan does not overfit only known branches.")
    if attention_shortlist:
        editorial_mandates.append("Pull the top branch digests into tonight's planning surface before cold-start growth.")
    editorial_mandates = self._dedupe_keep_order(editorial_mandates)[:6]

    planning_self_summary = " ".join(
        part for part in [
            "StrategyCouncil critiques the remembered self instead of replacing it.",
            f"Accepted child growth: {len(accepted_child_branch_proposals)}." if accepted_child_branch_proposals else "",
            f"Deferred child growth: {len(deferred_child_branch_proposals)}." if deferred_child_branch_proposals else "",
            f"Attention shortlist: {', '.join(attention_titles[:3])}." if attention_titles else "",
            f"Tonight focuses on {min(scope_budget['max_scope_count'], max(1, len(goal_gaps)))} scope slots.",
        ] if part
    ).strip()

    policy_branch_counts = {}
    for item in policy_inventory:
        branch_path = str(item.get("branch_path") or "").strip()
        if not branch_path:
            continue
        policy_branch_counts[branch_path] = policy_branch_counts.get(branch_path, 0) + 1

    scope_candidates = []
    for branch_path in self._dedupe_keep_order(required_branches + known_branches):
        if not branch_path:
            continue
        health_hint = str(branch_health_map.get(branch_path) or "known").strip()
        root_entity = self._root_entity_from_asset_scope(branch_path)
        score = 0.45
        if branch_path in required_branches:
            score += 0.14
        if health_hint in {"needs_growth", "planned", "seed"}:
            score += 0.26
        if branch_path not in existing_branch_digests:
            score += 0.12
        if policy_branch_counts.get(branch_path, 0) == 0:
            score += 0.08
        topic_slug = self._topic_slug_from_branch_path(branch_path)
        if topic_slug and topic_slug in normalized_text:
            score += 0.12
        if branch_path in attention_score_map:
            score += min(0.24, attention_score_map[branch_path] * 0.24)
        target_action = "repair" if ("repair" in branch_path or topic_slug == "field_repair") else (
            "grow" if health_hint in {"needs_growth", "planned", "seed"} or branch_path not in existing_branch_digests else "refresh"
        )
        scope_candidates.append(
            (
                score,
                NightlyScopeItem(
                    scope_key=f"scope::{self._safe_slug_fragment(branch_path)}",
                    root_entity=root_entity,
                    branch_path=branch_path,
                    scope_reason=f"{branch_path} selected for {target_action}; health={health_hint}, policy_assets={policy_branch_counts.get(branch_path, 0)}.",
                    target_action=target_action,
                    evidence_start_points=evidence_points[:8],
                    priority_weight=min(score, 0.98),
                ).model_dump(),
            )
        )
    for proposal in child_branch_proposals:
        proposed_branch_path = str(proposal.get("proposed_branch_path") or "").strip()
        parent_branch_path = str(proposal.get("parent_branch_path") or "").strip()
        root_entity = str(proposal.get("root_entity") or self._root_entity_from_asset_scope(parent_branch_path)).strip()
        pressure_score = float(proposal.get("pressure_score", 0.5) or 0.5)
        if not proposed_branch_path:
            continue
        scope_candidates.append(
            (
                min(max(pressure_score + 0.12 + (attention_score_map.get(parent_branch_path, 0.0) * 0.10), 0.62), 0.99),
                NightlyScopeItem(
                    scope_key=f"scope::{self._safe_slug_fragment(proposed_branch_path)}",
                    root_entity=root_entity,
                    branch_path=proposed_branch_path,
                    scope_reason=str(proposal.get("proposal_reason") or f"Child branch growth proposed under {parent_branch_path}."),
                    target_action="grow",
                    evidence_start_points=self._dedupe_keep_order(
                        list(proposal.get("evidence_start_points", []) or []) + evidence_points[:6]
                    )[:8],
                    priority_weight=min(max(pressure_score + 0.12, 0.62), 0.99),
                    status="planned",
                ).model_dump(),
            )
        )
    scope_candidates.sort(key=lambda item: item[0], reverse=True)
    filtered_scope = []
    new_growth_count = 0
    repair_count = 0
    refresh_count = 0
    for _, item in scope_candidates:
        if not isinstance(item, dict):
            continue
        target_action = str(item.get("target_action") or "refresh").strip()
        if target_action == "grow" and new_growth_count >= int(scope_budget["max_new_growth"]):
            continue
        if target_action == "repair" and repair_count >= int(scope_budget["max_repair"]):
            continue
        if target_action == "refresh" and refresh_count >= int(scope_budget["max_refresh"]):
            continue
        filtered_scope.append(item)
        if target_action == "grow":
            new_growth_count += 1
        elif target_action == "repair":
            repair_count += 1
        else:
            refresh_count += 1
    tonight_scope = self._dedupe_scope_items(filtered_scope)[: int(scope_budget["max_scope_count"])]

    next_night_handoff = []
    for scope in tonight_scope[:4]:
        branch_path = str(scope.get("branch_path") or "").strip()
        target_action = str(scope.get("target_action") or "refresh").strip()
        if branch_path:
            next_night_handoff.append(f"Carry {branch_path} forward after tonight's {target_action} pass.")
    for proposal in deferred_child_branch_proposals[:3]:
        proposed_branch_path = str(proposal.get("proposed_branch_path") or "").strip()
        parent_branch_path = str(proposal.get("parent_branch_path") or "").strip()
        if proposed_branch_path:
            next_night_handoff.append(
                f"Re-evaluate deferred child branch proposal {proposed_branch_path} under {parent_branch_path or 'its parent branch'}."
            )
    next_night_handoff.extend(open_unknowns[:3])
    next_night_handoff = self._dedupe_keep_order(next_night_handoff)[:8]

    goal_titles = [str(item.get("title") or "").strip() for item in goal_tree[:3] if isinstance(item, dict)]
    scope_titles = [str(item.get("branch_path") or "").strip() for item in tonight_scope[:3] if isinstance(item, dict)]
    strategy_summary = " / ".join(
        part for part in [
            f"Goals: {', '.join(goal_titles)}" if goal_titles else "",
            f"Tonight: {', '.join(scope_titles)}" if scope_titles else "",
            f"Attention: {', '.join(attention_titles[:3])}" if attention_titles else "",
            f"Open gaps: {len(goal_gaps)}" if goal_gaps else "",
            f"Accepted child proposals: {len(accepted_child_branch_proposals)}" if accepted_child_branch_proposals else "",
            f"Deferred child proposals: {len(deferred_child_branch_proposals)}" if deferred_child_branch_proposals else "",
        ]
        if part
    )
    if not strategy_summary:
        strategy_summary = str(existing.get("strategy_summary") or "StrategyCouncil keeps a rolling goal tree and a narrow nightly scope.")

    payload = {
        "strategy_key": str(existing.get("strategy_key") or "strategy_council_v1"),
        "governor_key": str(governor.get("governor_key") or existing.get("governor_key") or "rem_governor_v1"),
        "target_roots": root_entities,
        "goal_tree": goal_tree,
        "goal_gaps": goal_gaps,
        "tonight_scope": tonight_scope,
        "child_branch_proposals": accepted_child_branch_proposals,
        "proposal_decisions": proposal_decisions,
        "attention_shortlist": attention_shortlist,
        "remembered_self_summary": remembered_self_summary,
        "planning_self_summary": planning_self_summary,
        "editorial_mandates": editorial_mandates,
        "scope_budget": scope_budget,
        "planning_horizon": str(existing.get("planning_horizon") or "rolling_3_nights"),
        "strategy_summary": strategy_summary,
        "next_night_handoff": next_night_handoff,
        "status": "active",
    }
    return StrategyCouncilStateSchema(**payload).model_dump()


def _dedupe_goal_tree(items):
    seen = set()
    result = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        goal_key = str(item.get("goal_key") or "").strip()
        if not goal_key or goal_key in seen:
            continue
        seen.add(goal_key)
        result.append(item)
    return result

def _dedupe_goal_gaps(items):
    seen = set()
    result = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        gap_key = str(item.get("gap_key") or "").strip()
        if not gap_key or gap_key in seen:
            continue
        seen.add(gap_key)
        result.append(item)
    return result

def _dedupe_scope_items(items):
    seen = set()
    result = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        scope_key = str(item.get("scope_key") or "").strip()
        if not scope_key or scope_key in seen:
            continue
        seen.add(scope_key)
        result.append(item)
    return result

def _dedupe_child_branch_proposals(items):
    seen = set()
    result = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        proposal_key = str(item.get("proposal_key") or "").strip()
        if not proposal_key or proposal_key in seen:
            continue
        seen.add(proposal_key)
        result.append(item)
    return result
