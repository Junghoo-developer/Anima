from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class REMPlanSchema(BaseModel):
    strategy_key: str = ""
    governor_key: str
    architect_key: str
    handoff_report_key: str
    target_roots: List[str]
    selected_branch_paths: List[str]
    create_targets: List[str]
    update_targets: List[str]
    evidence_start_points: List[str]
    scope_keys: List[str] = Field(default_factory=list)
    next_night_handoff: List[str] = Field(default_factory=list)
    phase11_feedback: List[str] = Field(default_factory=list)
    blocked_branch_paths: List[str] = Field(default_factory=list)
    verification_requirements: List[str] = Field(default_factory=list)
    report_target_phase: str
    objective_summary: str
    status: str


class GoalTreeItem(BaseModel):
    goal_key: str
    root_entity: str
    title: str
    summary: str
    goal_type: Literal["stabilize", "expand", "refine", "repair"] = "refine"
    branch_paths: List[str] = Field(default_factory=list)
    priority_weight: float = 0.5
    status: str = "active"


class GoalGapItem(BaseModel):
    gap_key: str
    root_entity: str
    branch_path: str = ""
    title: str
    summary: str
    severity: Literal["low", "medium", "high"] = "medium"
    evidence_roots: List[str] = Field(default_factory=list)
    status: str = "open"


class NightlyScopeItem(BaseModel):
    scope_key: str
    root_entity: str
    branch_path: str
    scope_reason: str
    target_action: Literal["stabilize", "grow", "refresh", "repair"] = "refresh"
    evidence_start_points: List[str] = Field(default_factory=list)
    priority_weight: float = 0.5
    status: str = "planned"


class ChildBranchProposalItem(BaseModel):
    proposal_key: str
    parent_branch_path: str
    proposed_branch_path: str
    root_entity: str
    topic_slug: str
    proposal_reason: str
    pressure_score: float = 0.5
    evidence_start_points: List[str] = Field(default_factory=list)
    trigger_notes: List[str] = Field(default_factory=list)
    status: Literal["proposed", "accepted", "rejected", "carried_forward"] = "proposed"


class ProposalDecisionItem(BaseModel):
    proposal_key: str
    proposed_branch_path: str
    decision: Literal["accept", "defer", "reject"] = "defer"
    rationale: str
    priority_weight: float = 0.5


class ScopeBudgetItem(BaseModel):
    max_scope_count: int = 6
    max_new_growth: int = 2
    max_refresh: int = 3
    max_repair: int = 2


class AttentionDigestItem(BaseModel):
    asset_type: Literal["branch_digest", "concept_cluster"] = "branch_digest"
    asset_key: str = ""
    digest_key: str = ""
    cluster_key: str = ""
    branch_path: str
    title: str
    summary: str
    related_topics: List[str] = Field(default_factory=list)
    final_score: float = 0.0
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    support_score: float = 0.0
    pressure_score: float = 0.0
    why_now: str = ""


class StrategyCouncilStateSchema(BaseModel):
    strategy_key: str
    governor_key: str
    target_roots: List[str]
    goal_tree: List[GoalTreeItem] = Field(default_factory=list)
    goal_gaps: List[GoalGapItem] = Field(default_factory=list)
    tonight_scope: List[NightlyScopeItem] = Field(default_factory=list)
    child_branch_proposals: List[ChildBranchProposalItem] = Field(default_factory=list)
    proposal_decisions: List[ProposalDecisionItem] = Field(default_factory=list)
    attention_shortlist: List[AttentionDigestItem] = Field(default_factory=list)
    remembered_self_summary: str = ""
    planning_self_summary: str = ""
    editorial_mandates: List[str] = Field(default_factory=list)
    scope_budget: ScopeBudgetItem = Field(default_factory=ScopeBudgetItem)
    planning_horizon: str = "rolling_3_nights"
    strategy_summary: str
    next_night_handoff: List[str] = Field(default_factory=list)
    status: str = "active"


class GovernorRootProfile(BaseModel):
    root_entity: str
    inferred_role: str
    factual_summary: str
    connected_node_types: List[str]
    connected_relation_types: List[str]
    evidence_roots: List[str]
    open_unknowns: List[str]


class GovernorInventoryItem(BaseModel):
    root_entity: str
    relation_type: str
    node_type: str
    node_name: str
    summary: str = ""


class GovernorPolicyAssetItem(BaseModel):
    asset_type: str
    asset_key: str
    root_entity: str
    branch_path: str = ""
    target_family: str = ""
    summary: str = ""
    status: str = "active"


class REMGovernorStateSchema(BaseModel):
    governor_key: str
    root_entities: List[str]
    root_descriptions: List[str]
    root_profiles: List[GovernorRootProfile] = Field(default_factory=list)
    root_inventory: List[GovernorInventoryItem] = Field(default_factory=list)
    policy_inventory: List[GovernorPolicyAssetItem] = Field(default_factory=list)
    known_branches: List[str]
    required_branches: List[str]
    branch_health: List[str]
    open_unknowns: List[str]
    priority_biases: List[str]
    branch_revision_rules: List[str]
    policy_alignment_targets: List[str]
    evidence_roots: List[str]
    last_growth_actions: List[str]
    governor_summary: str
    preferred_report_target: str
    status: str


class RoutePolicyItem(BaseModel):
    policy_key: str
    turn_family: str
    answer_shape_hint: str
    trigger_signals: List[str]
    preferred_next_hop: str
    fallback_next_hop: str
    preferred_direct_strategy: str = ""
    requires_grounding: bool
    requires_recent_context: bool
    requires_active_offer: bool
    requires_history_scope: bool
    router_mode: Literal["policy_first", "hybrid", "fallback"] = "policy_first"
    match_priority: float = 0.5
    confidence_gate: float
    rationale: str
    compiled_from_tactic_key: str = ""
    policy_source: str = "nightly_reflection"
    status: str


class ToolDoctrineItem(BaseModel):
    doctrine_key: str
    target_family: str
    recommended_tools: List[str]
    tool_order: List[str]
    query_rewrite_rules: List[str]
    source_priority: List[str]
    avoid_patterns: List[str]
    success_signals: List[str]
    failure_signals: List[str]
    execution_mode: Literal["policy_guided", "hybrid", "fallback"] = "policy_guided"
    rationale: str
    compiled_from_tactic_key: str = ""
    policy_source: str = "nightly_reflection"
    status: str


class Phase8ReviewPacket(BaseModel):
    review_target: Literal["phase_7", "phase_8a", "phase_9"]
    objection_kind: Literal["coverage_gap", "plan_revision", "resolved", "insufficient_evidence"]
    reviewer_summary: str
    target_topics: List[str]
    rejected_actions: List[str]
    revision_requests: List[str]
    carry_forward_addresses: List[str]


class ArchitectHandoffReportSchema(BaseModel):
    report_key: str
    governor_key: str
    architect_key: str
    target_roots: List[str]
    selected_branch_paths: List[str]
    create_targets: List[str]
    update_targets: List[str]
    evidence_start_points: List[str]
    preserved_constraints: List[str]
    translation_gaps: List[str]
    intent_alignment: Literal["aligned", "partial", "blocked"] = "aligned"
    reviewer_summary: str
    status: Literal["ready", "blocked"] = "ready"


class TimeBucketItem(BaseModel):
    bucket_key: str
    label: str
    time_scope: Literal["day", "month", "year", "unknown"] = "unknown"


class FactLeafItem(BaseModel):
    fact_key: str
    branch_path: str
    root_entity: str
    topic_slug: str
    time_bucket_key: str
    source_address: str
    source_type: str
    source_id: str
    fact_text: str
    source_excerpt: str = ""
    verification_status: Literal["pending", "approved", "rejected"] = "pending"
    verification_reason: str = ""
    confidence: float = 0.5
    support_weight: float = 0.5
    u_purity_score: float = 0.0
    u_support_score: float = 0.0
    u_evidence_alignment: float = 0.0
    u_source_prior: float = 0.0
    u_redundancy_support: float = 0.0
    u_contradiction_pressure: float = 0.0
    u_hallucination_risk: float = 0.0
    inverse_relation_hints: List[str] = Field(default_factory=list)
    supporting_dream_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class FactLeafAuditItem(BaseModel):
    audit_key: str
    fact_key: str
    branch_path: str
    source_address: str
    source_type: str
    source_id: str
    fact_text: str
    verdict: Literal["approved", "rejected"] = "approved"
    rejection_reason: str = ""
    source_pair_key: str = ""


class SourceFactPairItem(BaseModel):
    pair_key: str
    fact_key: str
    branch_path: str
    source_address: str
    source_type: str
    source_id: str
    fact_text: str
    source_excerpt: str = ""
    pair_status: Literal["approved", "rejected"] = "approved"
    verifier_name: str = "phase11_fact_pair_guard"
    verifier_confidence: float = 0.0
    mismatch_reason: str = ""


class FactLeafVerificationItem(BaseModel):
    fact_key: str
    verdict: Literal["supported", "too_weak", "unsupported"] = "too_weak"
    reason: str = ""
    confidence: float = 0.0


class FactLeafVerificationBatchSchema(BaseModel):
    verifier_summary: str = ""
    verifications: List[FactLeafVerificationItem] = Field(default_factory=list)


class ConceptClusterItem(BaseModel):
    cluster_key: str
    branch_path: str
    root_entity: str
    topic_slug: str
    title: str
    summary: str
    fact_keys: List[str]
    time_bucket_keys: List[str]
    support_weight: float = 0.5
    u_cluster_purity: float = 0.0
    u_coherence_score: float = 0.0
    u_tension_score: float = 0.0
    u_synthesis_score: float = 0.0
    thesis_fact_keys: List[str] = Field(default_factory=list)
    antithesis_fact_keys: List[str] = Field(default_factory=list)
    synthesis_statement: str = ""
    inverse_relation_updates: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class SynthesisBridgeThoughtItem(BaseModel):
    bridge_key: str
    branch_path: str
    root_entity: str
    topic_slug: str
    cluster_key: str
    title: str
    bridge_thought: str
    supporting_fact_keys: List[str]
    support_weight: float = 0.5
    u_synthesis_score: float = 0.0


class DifferenceNoteItem(BaseModel):
    note_key: str
    branch_path: str
    root_entity: str
    topic_slug: str
    title: str
    summary: str
    compared_fact_keys: List[str]
    compared_time_bucket_keys: List[str]
    contrast_axis: str = ""
    support_weight: float = 0.5
    u_tension_score: float = 0.0


class BranchDigestItem(BaseModel):
    digest_key: str
    branch_path: str
    title: str
    summary: str
    related_topics: List[str]
    evidence_addresses: List[str]
    supporting_dream_ids: List[str]
    attached_tactic_ids: List[str] = Field(default_factory=list)
    attached_policy_keys: List[str]
    attached_doctrine_keys: List[str]
    status: str = "active"


class BranchGrowthReportSchema(BaseModel):
    growth_scope: str
    growth_status: Literal["ready", "partial", "blocked"] = "ready"
    curated_branches: List[str]
    rejected_branch_paths: List[str] = Field(default_factory=list)
    consistency_findings: List[str]
    rejection_reasons: List[str] = Field(default_factory=list)
    rem_plan_feedback: List[str] = Field(default_factory=list)
    governor_feedback: List[str] = Field(default_factory=list)
    architect_feedback: List[str] = Field(default_factory=list)
    digest_count: int
    branch_pressure_hints: List[str] = Field(default_factory=list)
    child_branch_proposal_count: int = 0
    fact_leaf_count: int = 0
    fact_audit_count: int = 0
    source_fact_pair_count: int = 0
    approved_fact_leaf_count: int = 0
    rejected_fact_leaf_count: int = 0
    time_bucket_count: int = 0
    concept_cluster_count: int = 0
    synthesis_bridge_count: int = 0
    difference_note_count: int = 0


def dedupe_keep_order(items):
    seen = set()
    result = []
    for item in items or []:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def topic_label_ko(topic_slug: str):
    mapping = {
        "person_definition": "허정후 정의",
        "person_life_history": "허정후 역사",
        "person_current_state": "허정후 현재 상태",
        "person_development_pattern": "허정후 개발 패턴",
        "coreego_definition": "송련 정의",
        "coreego_history": "송련 역사",
        "coreego_current_state": "송련 현재 상태",
        "coreego_field_response": "송련 현장 응답",
        "coreego_self_model": "송련 자기 모델",
        "personal_history_review": "개인 과거 검토",
        "recent_dialogue_review": "최근 대화 검토",
        "self_analysis_snapshot": "자기 분석 스냅샷",
        "tool_routing": "도구 라우팅",
        "field_repair": "현장 보수",
        "social_praise_ack": "칭찬 반응",
        "social_repair": "사회적 수습",
        "playful_positive_reaction": "가벼운 호의 반응",
    }
    topic = str(topic_slug or "").strip()
    return mapping.get(topic, topic or "미지의 주제")


def branch_title_ko(branch_path: str):
    path = str(branch_path or "").strip()
    if not path:
        return ""
    leaf = path.split("/")[-1].strip()
    mapping = {
        "identity": "정의 가지",
        "history": "역사 가지",
        "current_state": "현재 상태 가지",
        "development_pattern": "개발 패턴 가지",
        "field_response": "현장 응답 가지",
        "self_model": "자기 모델 가지",
        "history_review": "과거 검토 가지",
        "dialogue_review": "대화 검토 가지",
        "visible_patterns": "가시 패턴 가지",
        "tool_doctrine": "도구 교리 가지",
        "field_repair": "현장 보수 가지",
        "praise_ack": "칭찬 반응 가지",
        "repair_response": "사회적 수습 가지",
        "light_reaction": "가벼운 호의 가지",
    }
    return mapping.get(leaf, topic_label_ko(leaf))


def normalize_branch_path_to_existing_roots(branch_path: str):
    path = str(branch_path or "").strip()
    if not path:
        return ""
    if path.startswith("UserRoot/"):
        return "Person/" + path.split("/", 1)[1]
    if path.startswith("SongryeonRoot/"):
        return "CoreEgo/" + path.split("/", 1)[1]
    return path


def topic_branch_templates():
    return {
        "person_definition": "Person/definition/identity",
        "person_life_history": "Person/definition/history",
        "person_current_state": "Person/definition/current_state",
        "person_development_pattern": "Person/definition/development_pattern",
        "coreego_definition": "CoreEgo/definition/identity",
        "coreego_history": "CoreEgo/definition/history",
        "coreego_current_state": "CoreEgo/definition/current_state",
        "coreego_field_response": "CoreEgo/definition/field_response",
        "coreego_self_model": "CoreEgo/definition/self_model",
        "personal_history_review": "Person/personal_history/history_review",
        "recent_dialogue_review": "CoreEgo/conversation/dialogue_review",
        "self_analysis_snapshot": "Person/self_model/visible_patterns",
        "tool_routing": "CoreEgo/ops/tool_doctrine",
        "field_repair": "CoreEgo/ops/field_repair",
        "social_praise_ack": "CoreEgo/social/praise_ack",
        "social_repair": "CoreEgo/social/repair_response",
        "playful_positive_reaction": "CoreEgo/social/light_reaction",
    }


def branch_path_for_topic(topic_slug):
    topic = str(topic_slug or "").strip()
    templates = topic_branch_templates()
    return normalize_branch_path_to_existing_roots(
        templates.get(topic, f"CoreEgo/misc/{topic or 'field_repair'}")
    )


def topic_slug_from_branch_path(branch_path: str):
    normalized = normalize_branch_path_to_existing_roots(branch_path)
    for topic_slug, template in topic_branch_templates().items():
        if normalized == template:
            return topic_slug
    leaf = normalized.split("/")[-1].strip()
    leaf_map = {
        "identity": "coreego_definition" if normalized.startswith("CoreEgo/") else "person_definition",
        "history": "coreego_history" if normalized.startswith("CoreEgo/") else "person_life_history",
        "current_state": "coreego_current_state" if normalized.startswith("CoreEgo/") else "person_current_state",
        "development_pattern": "person_development_pattern",
        "field_response": "coreego_field_response",
        "self_model": "coreego_self_model",
        "history_review": "personal_history_review",
        "dialogue_review": "recent_dialogue_review",
        "visible_patterns": "self_analysis_snapshot",
        "tool_doctrine": "tool_routing",
        "field_repair": "field_repair",
        "praise_ack": "social_praise_ack",
        "repair_response": "social_repair",
        "light_reaction": "playful_positive_reaction",
    }
    return leaf_map.get(leaf, leaf or "field_repair")


def parse_branch_health_map(rem_governor):
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
