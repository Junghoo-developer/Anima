from typing import List, Optional, Literal
from typing import TypedDict

from pydantic import BaseModel, Field


class MidnightState(TypedDict):
    target_date: str
    dream_ids: List[str]
    dream_rows: List[dict]
    dreams_log_text: str
    existing_branch_digests: List[dict]
    existing_concept_clusters: List[dict]
    strategy_council: dict
    rem_governor: dict
    branch_architect: dict
    architect_handoff_report: dict
    rem_plan: dict
    phase_7_audit: dict
    pending_actions: list
    loop_count: int
    tool_runs: List[dict]
    fact_leaf_candidates: List[dict]
    doubt_feedback: str
    phase_8b_feedback: str
    phase_8_review_packet: dict
    tactical_doctrine: dict
    route_policies: List[dict]
    tool_doctrines: List[dict]
    branch_growth_report: dict
    branch_digests: List[dict]
    time_buckets: List[dict]
    fact_leaves: List[dict]
    fact_leaf_audits: List[dict]
    source_fact_pairs: List[dict]
    concept_clusters: List[dict]
    synthesis_bridges: List[dict]
    difference_notes: List[dict]
    child_branch_proposals: List[dict]
    field_memos: List[dict]
    layered_memos: List[dict]
    branch_offices: List[dict]
    local_reports: List[dict]


def build_reflection_debate_state(state: MidnightState):
    phase_7 = state.get("phase_7_audit", {}) if isinstance(state.get("phase_7_audit"), dict) else {}
    tactical = state.get("tactical_doctrine", {}) if isinstance(state.get("tactical_doctrine"), dict) else {}
    topics = phase_7.get("classified_topics", []) if isinstance(phase_7.get("classified_topics"), list) else []
    pending_actions = state.get("pending_actions", []) if isinstance(state.get("pending_actions"), list) else []
    fact_leaf_candidates = state.get("fact_leaf_candidates", []) if isinstance(state.get("fact_leaf_candidates"), list) else []

    unresolved_topics = []
    objections = []
    approved_topic_ids = []
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        slug = str(topic.get("topic_slug") or "").strip()
        title = str(topic.get("title") or slug).strip()
        if topic.get("supply_sufficient"):
            if slug:
                approved_topic_ids.append(slug)
            continue
        label = title or slug
        if label:
            unresolved_topics.append(label)
        gap = str(topic.get("gap_description") or "").strip()
        if label or gap:
            objections.append({
                "topic_slug": slug,
                "objection_text": gap or f"Supply gap remains around {label}.",
                "needs_search": True,
            })

    recommended_searches = []
    for action in pending_actions:
        if not isinstance(action, dict):
            continue
        tool = str(action.get("tool") or "").strip()
        keyword = str(action.get("keyword") or "").strip()
        topic_slug = str(action.get("topic_slug") or "").strip()
        if tool and keyword:
            recommended_searches.append(f"{tool}::{keyword}")
        elif tool:
            recommended_searches.append(f"{tool}::{topic_slug or 'unspecified'}")

    candidate_claims = []
    for candidate in fact_leaf_candidates[:8]:
        if not isinstance(candidate, dict):
            continue
        source_address = str(candidate.get("source_address") or "").strip()
        fact_text = str(candidate.get("fact_text") or "").strip()
        if fact_text:
            candidate_claims.append({
                "source_address": source_address,
                "fact_text": fact_text,
            })

    tactical_items = tactical.get("tactical_thoughts", []) if isinstance(tactical.get("tactical_thoughts"), list) else []
    final_answer_brief = ""
    if tactical_items:
        final_answer_brief = " / ".join(
            str(item.get("actionable_rule") or "").strip()
            for item in tactical_items[:3]
            if isinstance(item, dict) and str(item.get("actionable_rule") or "").strip()
        )
    if not final_answer_brief:
        final_answer_brief = str(tactical.get("critique_reasoning") or state.get("phase_8b_feedback") or "").strip()

    answer_now = bool(tactical_items) or state.get("doubt_feedback") == "RESOLVED"
    requires_search = bool(recommended_searches) and not answer_now

    return {
        "critic_report": {
            "situational_brief": str(state.get("phase_8b_feedback") or "").strip(),
            "analytical_thought": str(phase_7.get("thought_process") or "").strip(),
            "open_questions": unresolved_topics,
            "objections": objections,
            "recommended_searches": recommended_searches,
            "recommended_action": "answer_now" if answer_now else ("search_more" if requires_search else "insufficient_evidence"),
        },
        "advocate_report": {
            "defense_strategy": str(tactical.get("critique_reasoning") or "").strip(),
            "summary_of_position": final_answer_brief,
            "supported_pair_ids": [
                str(candidate.get("source_address") or "").strip()
                for candidate in fact_leaf_candidates[:8]
                if isinstance(candidate, dict) and str(candidate.get("source_address") or "").strip()
            ],
            "bridge_claims": candidate_claims,
        },
        "verdict_board": {
            "answer_now": answer_now,
            "requires_search": requires_search,
            "approved_fact_ids": approved_topic_ids,
            "approved_pair_ids": [
                str(candidate.get("source_address") or "").strip()
                for candidate in fact_leaf_candidates[:8]
                if isinstance(candidate, dict) and str(candidate.get("source_address") or "").strip()
            ],
            "rejected_pair_ids": [],
            "held_pair_ids": [],
            "judge_notes": [str(state.get("phase_8b_feedback") or "").strip()] if str(state.get("phase_8b_feedback") or "").strip() else [],
            "final_answer_brief": final_answer_brief,
        },
    }


class ClassifiedTopic(BaseModel):
    topic_slug: str
    title: str
    parent_topic_slug: Optional[str]
    what_was_demanded: str
    what_was_supplied_in_answer: str
    supply_sufficient: bool
    gap_description: str
    dynamic_anti_z: str = Field(
        ...,
        description="해당 주제와 팽팽하게 대립하는 모순 축(Anti-Z)",
    )
    dynamic_y_axis: str = Field(
        ...,
        description="해당 주제를 둘러싼 상황 변화 축(Y축)",
    )


class Phase7Schema(BaseModel):
    thought_process: str = Field(description="현재까지의 단서와 8b 보고를 바탕으로 한 7차 사고 과정")
    classified_topics: List[ClassifiedTopic] = Field(description="추출된 주제 목록(Z, Anti-Z, Y 포함)")
    instruction: str = Field(description="실행할 도구 지시")
    message_to_8b: str = Field(description="8b 정련관에게 보내는 분석 지시나 질문")
    coverage_map: List[dict] = Field(default_factory=list, description="심야 상위 계층이 7차 출력에 덧붙이는 커버리지 지도")


class Phase8Action(BaseModel):
    topic_slug: str
    tool: Literal[
        "SEARCH",
        "READ_FULL_SOURCE",
        "web_search",
        "recall_recent_dreams",
        "search_tactics",
        "search_supply_topics",
    ]
    keyword: Optional[str] = Field(None, description="일반 검색 도구를 사용할 때의 키워드")


class Phase8aSchema(BaseModel):
    actions: List[Phase8Action]


class SupplyBridge(BaseModel):
    topic_slug: str
    source_address: str
    bridge_thought: str = Field(description="레거시 호환용 bridge 설명")
    parent_topic_slug: Optional[str]


class FactLeafCandidate(BaseModel):
    topic_slug: str
    source_address: str
    fact_text: str = Field(description="원문이나 도구 결과에서 바로 지지할 수 있는 사실 후보 문장")
    parent_topic_slug: Optional[str] = None
    source_kind: str = ""
    inferred_time_bucket: str = ""
    support_weight: float = 0.55


class RefinedMidnightNode(BaseModel):
    id: str = Field(description="추출된 근거 기록의 주소 또는 ID")
    summary: str = Field(description="8b가 원문을 읽고 7차를 위해 작성한 정제 요약")


class Phase8bSchema(BaseModel):
    thought_process: str = Field(description="원문을 읽고 7차의 부족 주제를 어떻게 보강할지 적는 8b의 추론 과정")
    processed_data: List[RefinedMidnightNode]
    is_resolved: bool = Field(description="현재 원문 근거만으로 7차의 부족 주제를 충분히 보강할 수 있는지 여부")
    response_to_phase_7: str = Field(description="미해결일 때 7차에 되돌려 보낼 구체 지시")
    proactive_suggestion: str = Field(description="8b가 7차에 먼저 제안하는 보강 방향")
    fact_leaf_candidates: List[FactLeafCandidate] = Field(default_factory=list)
    bridges: List[SupplyBridge] = Field(default_factory=list)


class TacticalThoughtItem(BaseModel):
    situation_trigger: str
    actionable_rule: str
    priority_weight: float
    applies_to_phase: str
    tactic_key: str = ""
    target_family: str = ""
    root_scope: str = ""
    branch_scope: str = ""
    semantic_signals: List[str] = Field(default_factory=list)
    preferred_next_hop: str = ""
    preferred_direct_strategy: str = ""
    preferred_tools: List[str] = Field(default_factory=list)
    disallowed_tools: List[str] = Field(default_factory=list)
    tone_recipe: str = ""
    must_include: List[str] = Field(default_factory=list)
    must_avoid: List[str] = Field(default_factory=list)
    repair_recipe: str = ""
    evidence_priority: List[str] = Field(default_factory=list)
    confidence_gate: float = 0.55
    status: str = "active"


class Phase9Schema(BaseModel):
    critique_reasoning: str
    is_valuable_tactics: bool
    tactical_thoughts: List[TacticalThoughtItem]


CONSTITUTION_TEXT = """
[ANIMA 심야 성찰 헌법]
당신은 사용자 허정후를 보좌하는 ANIMA 시스템의 심야 성찰 관리자 '송련'입니다.
모든 분석은 사실과 모순을 분리해 보고하고, 추측보다 근거를 우선합니다.
목표는 사용자의 자기이해와 시스템의 정책 품질을 함께 높이는 것입니다.
"""


PHASE7_PROMPT = """
{constitution}

당신은 ANIMA 시스템의 'Phase 7: 공급 감사관'입니다.

[사용자 기록 목록]
{log_text}

[이전 8b 피드백]
{previous_feedback}

[이전 도구 실행 요약]
{tool_history}

임무:
1. 오늘 기록에서 공급이 부족한 주제를 찾습니다.
2. 각 주제마다 반대 축(dynamic_anti_z)과 상황 축(dynamic_y_axis)을 함께 적습니다.
3. 이전 루프 판단이 현재 기록과 충돌하면 최신 근거를 우선합니다.

출력:
ClassifiedTopic 리스트를 JSON 구조에 맞게 출력합니다.
"""


PHASE8A_PROMPT = """
{constitution}

당신은 ANIMA 시스템의 'Phase 8a: 보충 탐색 계획자'입니다.

[부족 주제]
{insufficient_topics_json}

[이전 8b 피드백]
{previous_feedback}

[도구 실행 기록]
{tool_history}

[사용 가능한 도구]
{tool_digest}

임무:
1. 부족 주제를 보강하기 위한 도구 호출 계획을 세웁니다.
2. 같은 실패 조합을 반복하지 않습니다.
3. 빈 keyword, placeholder query, 의미 없는 재검색을 피합니다.

출력:
Phase8aSchema 형식의 actions를 작성합니다.
"""


PHASE8B_PROMPT = """
{constitution}

당신은 ANIMA 시스템의 'Phase 8b: 사실 후보 정련관'입니다.

[Phase 7 결과]
{p7_json}

[도구 결과]
{tool_runs}

임무:
1. 원문과 도구 결과에서 FactLeaf 후보를 추출합니다.
2. 어떤 근거가 어떤 부족 주제를 보강하는지 thought_process에 적습니다.
3. 확실하지 않은 연결은 bridge를 꾸며내지 말고 fact 후보로만 남깁니다.

출력:
Phase8bSchema 형식으로 보고합니다.
"""


PHASE9_PROMPT = """
{constitution}

당신은 ANIMA 시스템의 'Phase 9: 전술 교관'입니다.

[Phase 7 결과]
{p7_json}

[공급 맥락]
{supply_context}

임무:
1. 공급 부족 주제와 보강 근거를 바탕으로 0차 행동 지침을 만듭니다.
2. 각 지침은 "IF [상황] THEN [행동]" 형태여야 합니다.
3. 막연한 조언보다 실제 현장 라우팅과 도구 선택에 도움이 되는 규칙을 씁니다.

출력:
TacticalThoughtItem 리스트를 작성합니다.
"""
