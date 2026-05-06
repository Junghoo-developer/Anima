"""Pydantic contracts for the ANIMA field-loop pipeline.

These schemas define structured LLM outputs and internal pipeline packets. Keep
field names, Literal values, and descriptions stable unless a behavior change is
intended and tested.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

class EvidenceItem(BaseModel):
    source_id: str = Field(description="Source identifier such as a date, node id, or document address.")
    source_type: str = Field(description="Source category such as diary, chat, db_schema, or memory.")
    extracted_fact: str = Field(description="Objective fact only. No speculation or interpretation.")

class SourceJudgment(BaseModel):
    source_id: str = Field(description="Source identifier judged by phase_2b.")
    source_type: str = Field(description="Source type judged by phase_2b.")
    source_status: Literal["pass", "objection", "ambiguous", "insufficient"] = Field(
        description="Per-source judgment made by the phase_2b critic."
    )
    accepted_facts: List[str] = Field(description="Facts from this source that remain usable after criticism.")
    contested_facts: List[str] = Field(description="Facts from this source that remain disputed or weak.")
    objection_reason: str = Field(description="Why this source is limited, objected to, or still ambiguous.")
    missing_info: List[str] = Field(description="What is still missing for this source.")
    search_needed: bool = Field(description="Whether this source still points to more search work.")

class FieldMemoJudgment(BaseModel):
    memo_id: str = Field(description="FieldMemo id judged by phase_2b.")
    relevance: Literal["direct", "indirect", "irrelevant"] = Field(
        default="irrelevant",
        description="Whether this memo directly answers the current user goal."
    )
    evidence_kind: Literal[
        "self_report",
        "identity_note",
        "narrative",
        "creative_worldbuilding",
        "tool_event",
        "search_result",
        "conversation_context",
        "fact_packet",
        "non_fact_trace",
        "phase_2b_fact_packet",
        "unknown",
    ] = Field(default="unknown", description="What kind of evidence this memo appears to be.")
    usable_for_current_goal: bool = Field(
        default=False,
        description="Whether this memo may be forwarded as evidence for the current goal."
    )
    accepted_facts: List[str] = Field(default_factory=list, description="Facts allowed through.")
    rejected_facts: List[str] = Field(default_factory=list, description="Facts rejected for this goal.")
    rejection_reason: str = Field(default="", description="Why this memo was rejected or downgraded.")
    recommended_followup_query: List[str] = Field(default_factory=list, description="Follow-up queries if this memo is insufficient.")

class AnalysisReport(BaseModel):
    evidences: List[EvidenceItem] = Field(description="Evidence items extracted from raw search results.")
    source_judgments: List[SourceJudgment] = Field(
        default_factory=list,
        description="Per-source prosecutor judgments derived from the raw relay packet."
    )
    field_memo_judgments: List[FieldMemoJudgment] = Field(
        default_factory=list,
        description="FieldMemo-specific relevance and evidence-kind judgments."
    )
    usable_field_memo_facts: List[str] = Field(
        default_factory=list,
        description="FieldMemo facts that survived the current-goal filter."
    )
    rejected_field_memo_ids: List[str] = Field(
        default_factory=list,
        description="FieldMemo ids rejected for the current goal."
    )
    can_answer_user_goal: bool = Field(
        default=False,
        description="Whether the filtered FieldMemo evidence can answer the user goal."
    )
    goal_contract: Dict[str, Any] = Field(
        default_factory=dict,
        description="Turn-level answer contract: user goal, slot to fill, success criteria, and forbidden drift."
    )
    contract_status: Literal[
        "unknown",
        "satisfied",
        "missing_slot",
        "wrong_source",
        "wrong_goal",
        "needs_replan",
    ] = Field(
        default="unknown",
        description="Whether the analysis actually satisfies the user's goal contract."
    )
    missing_slots: List[str] = Field(
        default_factory=list,
        description="Goal-contract slots that remain unfilled after the current read."
    )
    filled_slots: Dict[str, Any] = Field(
        default_factory=dict,
        description="Goal-contract slots filled by this analysis, keyed by slot name."
    )
    unfilled_slots: List[str] = Field(
        default_factory=list,
        description="Goal-contract slots still unfilled after filtering."
    )
    rejected_sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sources rejected for the current user goal, with reasons."
    )
    replan_directive_for_strategist: str = Field(
        default="",
        description="Concrete instruction back to -1a when the current lane failed the user goal contract."
    )
    analytical_thought: str = Field(description="Investigator reasoning about links, gaps, contradictions, and next steps.")
    situational_brief: str = Field(description="Short operational summary for -1b.")
    investigation_status: Literal["COMPLETED", "INCOMPLETE", "EXPANSION_REQUIRED"] = Field(
        description="Investigation state: completed, incomplete, or expansion required."
    )


class RawReadItem(BaseModel):
    source_id: str = Field(description="Source identifier such as a date, node id, or current_turn.")
    source_type: str = Field(description="Source type such as diary, chat, artifact, memory, or current_turn.")
    excerpt: str = Field(description="Short literal excerpt from the raw source.")
    observed_fact: str = Field(description="What was directly observed in the raw source, without interpretation.")


class RawReadReport(BaseModel):
    read_mode: Literal["current_turn_only", "recent_dialogue_review", "full_raw_review", "field_memo_review", "empty"] = Field(
        description="Whether phase_2a reviewed only the current turn, a full raw source payload, or nothing."
    )
    reviewed_all_input: bool = Field(description="Whether phase_2a completed a full read of the available raw input.")
    source_summary: str = Field(description="Short summary of what sources were reviewed.")
    items: List[RawReadItem] = Field(description="Important raw observations extracted from the reviewed input.")
    coverage_notes: str = Field(description="Notes about coverage, omissions, and confidence in the read pass.")

class ResponseStrategy(BaseModel):
    reply_mode: Literal["grounded_answer", "continue_previous_offer", "casual_reaction", "cautious_minimal", "ask_user_question_now"] = Field(
        description="Response mode for the current turn."
    )
    delivery_freedom_mode: Literal[
        "grounded",
        "supportive_free",
        "proposal",
        "identity_direct",
        "clean_failure",
        "answer_not_ready",
    ] = Field(
        default="grounded",
        description=(
            "How much freedom phase_3 may use when turning the approved packet into user-facing language. "
            "answer_not_ready is a legacy alias normalized to clean_failure."
        )
    )
    answer_goal: str = Field(description="Primary goal of the response.")
    tone_strategy: str = Field(description="Tone and stance guidance for the response.")
    evidence_brief: str = Field(description="Compressed factual brief prepared for phase_3.")
    reasoning_brief: str = Field(description="Short explanation of how facts connect to the user request.")
    direct_answer_seed: str = Field(description="Grounded answer seed that phase_3 can reuse.")
    must_include_facts: List[str] = Field(description="Facts that must appear or be respected in the response.")
    must_avoid_claims: List[str] = Field(description="Claims that must not appear because they are ungrounded or risky.")
    answer_outline: List[str] = Field(description="Practical outline for the final answer.")
    uncertainty_policy: str = Field(description="How to speak when evidence is weak or incomplete.")


class RecentDialogueBrief(BaseModel):
    lane: Literal["recent_dialogue_review"] = Field(default="recent_dialogue_review")
    user_facing_recent_dialogue_brief: str = Field(
        description="Recent dialogue recap that phase_3 may say directly to the user."
    )
    recent_turns: List[Dict[str, str]] = Field(description="Chronological recent user/assistant turns.")
    confirmed_turns: List[str] = Field(description="Concrete turns confirmed from raw recent dialogue.")
    continuation_anchor: str = Field(description="Where the conversation should resume from.")
    unknown_slots: List[str] = Field(description="What the recent dialogue did not actually establish.")
    answer_boundary: str = Field(description="Boundary that prevents phase_3 from speaking internal reports.")


class StartGateAssessment(BaseModel):
    answerability: Literal["direct_now", "direct_but_risky", "needs_grounding", "needs_planning", "special_case"] = Field(
        description="Fast answerability judgment made by -1s."
    )
    recommended_handler: Literal["phase_3", "-1a_thinker", "0_supervisor", "phase_119"] = Field(
        description="Which downstream handler should take over after the tiny gate."
    )
    confidence: float = Field(description="Confidence score between 0.0 and 1.0 for the fast routing judgment.")
    why_short: str = Field(description="Short explanation for why -1s chose this route.")
    risk_flags: List[str] = Field(description="Compact list of routing risks noticed by -1s.")


class StartGateTurnContract(BaseModel):
    user_intent: Literal[
        "providing_current_memory",
        "requesting_memory_recall",
        "public_knowledge_question",
        "direct_social",
        "correction_or_feedback",
        "capability_boundary_question",
        "task_or_tool_request",
        "other",
    ] = Field(description="The current turn intent, judged from meaning rather than keywords.")
    normalized_goal: str = Field(description="A short normalized goal. Do not copy the raw user wording.")
    answer_mode_preference: Literal[
        "current_turn_grounding",
        "grounded_recall",
        "public_parametric_knowledge",
        "generic_dialogue",
    ] = Field(description="Which evidence mode should govern this turn.")
    requires_grounding: bool = Field(description="Whether stored/private evidence must be retrieved before delivery.")
    direct_delivery_allowed: bool = Field(description="Whether phase 3 may answer now without a tool call.")
    needs_planning: bool = Field(description="Whether -1a should plan before delivery or tool execution.")
    current_turn_facts: List[str] = Field(
        default_factory=list,
        description="Facts supplied by the current user turn that may ground the immediate answer.",
    )
    rationale: str = Field(default="", description="Short reason for the contract.")


class SThinkingSituation(BaseModel):
    user_intent: str = Field(default="", description="Compact intent label from -1s contract reasoning.")
    domain: Literal[
        "memory_recall",
        "public_parametric",
        "self_kernel",
        "continuation",
        "feedback",
        "artifact_hint",
        "ambiguous",
    ] = Field(default="ambiguous", description="Broad answer/evidence domain for the current turn.")
    key_facts_needed: List[str] = Field(default_factory=list, description="Facts the loop still needs, stated abstractly.")


class SThinkingLoopSummary(BaseModel):
    attempted_so_far: List[str] = Field(default_factory=list, description="Loop actions already attempted this turn.")
    current_evidence_state: str = Field(default="", description="Short description of available evidence.")
    gaps: List[str] = Field(default_factory=list, description="Known gaps before delivery.")


class SThinkingNextDirection(BaseModel):
    suggested_focus: str = Field(default="", description="Abstract next focus. No tool names or queries.")
    avoid: List[str] = Field(default_factory=list, description="Things downstream should avoid.")


class SThinkingRoutingDecision(BaseModel):
    next_node: Literal["-1a", "phase_3", "119"] = Field(default="-1a", description="Abstract next node chosen by -1s.")
    reason: str = Field(default="", description="Short reason for the routing decision.")


class SThinkingPacket(BaseModel):
    schema_version: Literal["SThinkingPacket.v1"] = Field(default="SThinkingPacket.v1", alias="schema")
    situation_thinking: SThinkingSituation = Field(default_factory=SThinkingSituation)
    loop_summary: SThinkingLoopSummary = Field(default_factory=SThinkingLoopSummary)
    next_direction: SThinkingNextDirection = Field(default_factory=SThinkingNextDirection)
    routing_decision: SThinkingRoutingDecision = Field(default_factory=SThinkingRoutingDecision)


class OpsToolCard(BaseModel):
    tool_name: str = Field(description="Registered tool name that 0-supervisor may execute.")
    purpose: str = Field(description="What this tool is for.")
    use_when: str = Field(description="When this tool is appropriate.")
    avoid_when: str = Field(description="When this tool should not be the first choice.")


class OpsNodeCard(BaseModel):
    node_name: str = Field(description="Downstream node name.")
    responsibility: str = Field(description="What this node is best at.")
    route_when: str = Field(description="When 0-supervisor should hand the case to this node.")


class OpsDecision(BaseModel):
    decision_mode: Literal["direct_response", "tool_call", "handoff_planner", "handoff_phase2a", "handoff_phase3", "blocked"] = Field(
        description="How 0-supervisor decided to handle this turn."
    )
    next_hop: str = Field(description="Operational next hop chosen by 0-supervisor.")
    rationale: str = Field(description="Short explanation for the choice.")
    direct_strategy: str = Field(default="", description="Direct response strategy id when 0-supervisor chooses phase_3.")
    tool_name: str = Field(default="", description="Tool selected by 0-supervisor, when applicable.")
    tool_args: Dict[str, Any] = Field(default_factory=dict, description="Structured tool arguments when a tool call is selected.")
    allow_task_inheritance: bool = Field(default=False, description="Whether current-turn inheritance is allowed downstream.")
    allow_recent_hints: bool = Field(default=True, description="Whether recent raw hints may be mixed into fallback reading.")
    retry_anchor_kind: str = Field(default="", description="What kind of previous anchor the retry/follow-up relies on.")

class StrategistToolRequest(BaseModel):
    should_call_tool: bool = Field(
        default=False,
        description="Whether -1a believes one exact tool call should be sent to phase 0."
    )
    tool_name: Literal[
        "",
        "tool_search_field_memos",
        "tool_search_memory",
        "tool_scroll_chat_log",
        "tool_read_full_diary",
        "tool_read_artifact",
    ] = Field(default="", description="Exact tool phase 0 should execute.")
    tool_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Exact tool arguments. Phase 0 must execute these as-is."
    )
    rationale: str = Field(default="", description="Why this is the right tool/query.")

class FactCell(BaseModel):
    fact_id: str = Field(description="Stable fact identifier inside the reasoning board.")
    source_id: str = Field(description="Source address such as a date or node id.")
    source_type: str = Field(description="Source type such as diary, chat, or schema.")
    excerpt: str = Field(description="Short literal excerpt from the source.")
    extracted_fact: str = Field(description="Objective extracted fact.")
    fact_kind: Literal["event", "quote", "timeline", "preference", "relationship", "explicit_emotion", "other"] = Field(
        description="Type of fact."
    )
    confidence: float = Field(description="Fact confidence score between 0.0 and 1.0.")

class SubjectiveCell(BaseModel):
    claim_text: str = Field(description="Interpretation, hypothesis, or policy claim produced by -1a.")
    claim_kind: Literal[
        "interpretation",
        "hypothesis",
        "causal_guess",
        "intent_inference",
        "user_model_update",
        "response_policy",
    ] = Field(description="Kind of subjective claim.")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0.")
    answer_policy: Literal["allowed", "cautious", "forbidden"] = Field(
        description="Whether phase_3 may use this claim directly."
    )
    uncertainty_note: str = Field(default="", description="Short note about uncertainty.")

class AnchoredReasoningPair(BaseModel):
    pair_id: str = Field(description="Stable identifier for the fact-subjective pair.")
    fact_ids: List[str] = Field(description="Fact ids that anchor this subjective claim.")
    paired_fact_digest: str = Field(description="Fact-only digest corresponding to fact_ids.")
    subjective: SubjectiveCell = Field(description="Subjective claim anchored to facts.")
    audit_status: Literal["pending", "approved", "rejected", "needs_more_evidence"] = Field(
        description="Audit result assigned by -1b."
    )
    audit_note: str = Field(default="", description="Audit memo written by -1b.")

class ReasoningBoardV1(BaseModel):
    turn_id: str
    user_input: str
    fact_cells: List[FactCell]
    candidate_pairs: List[AnchoredReasoningPair]
    open_questions: List[str]
    search_requests: List[str]
    final_fact_ids: List[str]
    final_pair_ids: List[str]
    must_avoid_claims: List[str]
    direct_answer_seed: str

class CriticObjection(BaseModel):
    objection_id: str = Field(description="Stable objection identifier written by the phase_2 critic.")
    objection_text: str = Field(description="Why the current evidence or claim is still weak, risky, or incomplete.")
    target_fact_ids: List[str] = Field(description="Fact ids related to the objection.")
    target_pair_ids: List[str] = Field(description="Reasoning pair ids related to the objection.")
    severity: Literal["low", "medium", "high"] = Field(description="Operational severity of the objection.")
    needs_search: bool = Field(description="Whether the objection likely requires another tool call.")

class CriticReport(BaseModel):
    situational_brief: str = Field(description="Short prosecutor-style summary of the current case.")
    analytical_thought: str = Field(description="Critical reasoning about gaps, contradictions, and risks.")
    source_judgments: List[SourceJudgment] = Field(description="Per-source judgments made by the critic.")
    open_questions: List[str] = Field(description="Questions that remain unresolved.")
    objections: List[CriticObjection] = Field(description="Structured objections raised by the critic.")
    recommended_action: Literal["answer_now", "search_more", "insufficient_evidence"] = Field(
        description="Critic recommendation before the judge makes a final decision."
    )

class AdvocateReport(BaseModel):
    defense_strategy: str = Field(description="How -1a wants to defend or present the case.")
    summary_of_position: str = Field(description="Short summary of the advocate position.")
    supported_pair_ids: List[str] = Field(description="Reasoning pairs that the advocate wants to push forward.")
    response_contract: Dict[str, Any] = Field(description="Short response-level contract derived from the strategy.")

class VerdictBoard(BaseModel):
    answer_now: bool = Field(description="Whether phase_3 may answer now.")
    requires_search: bool = Field(description="Whether another search/tool step is still required.")
    approved_fact_ids: List[str] = Field(description="Fact ids approved by -1b.")
    approved_pair_ids: List[str] = Field(description="Reasoning pair ids approved by -1b.")
    rejected_pair_ids: List[str] = Field(description="Reasoning pair ids explicitly rejected by -1b.")
    held_pair_ids: List[str] = Field(description="Reasoning pair ids kept pending due to insufficient evidence.")
    judge_notes: List[str] = Field(description="Judge notes for phase_3 and future loops.")
    final_answer_brief: str = Field(description="Short answer brief allowed to reach phase_3.")

class ReasoningBoardV2(BaseModel):
    turn_id: str
    user_input: str
    fact_cells: List[FactCell]
    candidate_pairs: List[AnchoredReasoningPair]
    open_questions: List[str]
    search_requests: List[str]
    final_fact_ids: List[str]
    final_pair_ids: List[str]
    must_avoid_claims: List[str]
    direct_answer_seed: str
    critic_report: CriticReport
    advocate_report: AdvocateReport
    verdict_board: VerdictBoard

class OperationContract(BaseModel):
    operation_kind: Literal[
        "unspecified",
        "search_new_source",
        "read_same_source_deeper",
        "extract_feature_summary",
        "compare_with_user_goal",
        "review_recent_dialogue",
        "deliver_now",
    ] = Field(
        default="unspecified",
        description="What downstream operation should actually happen on this turn."
    )
    target_scope: str = Field(
        default="",
        description="What slice of the case/source this operation should focus on."
    )
    query_variant: str = Field(
        default="",
        description="If the same source/tool is reused, what query or focus variant makes this pass novel."
    )
    novelty_requirement: str = Field(
        default="",
        description="Short rule explaining what must differ from the previous pass."
    )

class OperationPlan(BaseModel):
    plan_type: Literal[
        "direct_delivery",
        "warroom_deliberation",
        "tool_evidence",
        "recent_dialogue_review",
        "raw_source_analysis",
    ] = Field(
        default="direct_delivery",
        description="Top-level execution lane selected for this turn."
    )
    source_lane: Literal[
        "none",
        "recent_dialogue_review",
        "field_memo_review",
        "memory_search",
        "scroll_source",
        "artifact_read",
        "warroom",
    ] = Field(
        default="none",
        description="What source or evidence lane should be read before delivery."
    )
    output_act: Literal[
        "answer",
        "summarize",
        "self_critique",
        "diagnose_bug",
        "apologize_and_repair",
        "deliver_findings",
        "answer_identity_slot",
        "answer_memory_recall",
        "answer_narrative_fact",
        "self_analysis_snapshot",
        "execute_game",
        "ask_one_question",
        "propose_next_step",
    ] = Field(
        default="answer",
        description="What kind of user-facing act phase_3 must produce after the source lane is handled."
    )
    user_goal: str = Field(default="", description="The user's current goal, stated compactly.")
    executor_instruction: str = Field(default="", description="Instruction for the lane executor.")
    evidence_policy: str = Field(default="", description="Whether evidence is required and why.")
    success_criteria: List[str] = Field(default_factory=list, description="Criteria for approving this plan's result.")
    rejection_criteria: List[str] = Field(default_factory=list, description="Criteria for rejecting or remanding this plan.")
    delivery_shape: str = Field(default="direct_answer", description="Expected phase_3 answer shape.")
    confidence: float = Field(default=0.5, description="Planner confidence from 0.0 to 1.0.")

class GoalLock(BaseModel):
    user_goal_core: str = Field(
        default="",
        description="Short restatement of the user's actual ask that -1a must keep anchored."
    )
    answer_shape: str = Field(
        default="direct_answer",
        description="Expected answer shape such as proposal_1_to_3, fit_summary, or feature_summary."
    )
    must_not_expand_to: List[str] = Field(
        default_factory=list,
        description="Areas -1a must not drift into unless the user explicitly asks for them."
    )


class StrategistGoal(BaseModel):
    user_goal_core: str = Field(
        default="",
        description="Compact -1a-owned goal for this turn. Do not copy the raw user wording."
    )
    answer_mode_target: Literal[
        "memory_recall",
        "public_parametric",
        "self_kernel",
        "continuation",
        "feedback",
        "artifact_hint",
        "ambiguous",
    ] = Field(
        default="ambiguous",
        description="Broad answer/evidence target chosen by the strategist from the current contract."
    )
    success_criteria: List[str] = Field(
        default_factory=list,
        description="Short criteria that tell downstream nodes when this goal is satisfied."
    )
    scope: Literal["narrow", "broad"] = Field(
        default="narrow",
        description="Whether the strategist goal should stay narrow or may deliberately cover a broader ask."
    )


class StepByStepPlan(BaseModel):
    current_step_goal: str = Field(description="Immediate goal for this turn, such as gather one missing fact or deliver the final answer.")
    required_tool: str = Field(
        default="",
        description="Exact tool instruction that phase_0 should execute for the current step. Use an empty string when no tool is needed."
    )
    next_steps_forecast: List[str] = Field(
        default_factory=list,
        description="Short forecast of the next 2-3 planned steps after the current step."
    )
    operation_contract: OperationContract = Field(
        default_factory=OperationContract,
        description="Structured contract that downstream departments must follow on this turn."
    )

class StrategistReasoningOutput(BaseModel):
    case_theory: str = Field(description="Master-plan summary based on the user's state and the critic's diagnosis.")
    operation_plan: OperationPlan = Field(
        default_factory=OperationPlan,
        description="Plan-first lane contract that decides whether this turn uses direct delivery, WarRoom deliberation, tools, recent dialogue review, or raw source analysis."
    )
    goal_lock: GoalLock = Field(
        default_factory=GoalLock,
        description="Anchor describing what the user is actually asking and what the answer should look like."
    )
    strategist_goal: StrategistGoal = Field(
        default_factory=StrategistGoal,
        description="V3 -1a goal contract. normalized_goal is only a legacy alias for this packet."
    )
    convergence_state: Literal["gathering", "synthesizing", "deliverable", "deepen_one_axis"] = Field(
        default="gathering",
        description="Where the strategist believes the case currently sits in the continuous reasoning pipeline."
    )
    achieved_findings: List[str] = Field(
        default_factory=list,
        description="Grounded findings that have already been secured and can support a partial or full answer."
    )
    delivery_readiness: Literal["deliver_now", "need_one_more_source", "need_reframe", "need_targeted_deeper_read"] = Field(
        default="need_reframe",
        description="Whether the current state is already answerable or what kind of next move is still required."
    )
    next_frontier: List[str] = Field(
        default_factory=list,
        description="Short list of the next best directions if the case should not be delivered yet."
    )
    action_plan: StepByStepPlan = Field(description="Concrete plan for what the system should do on this turn.")
    tool_request: StrategistToolRequest = Field(
        default_factory=StrategistToolRequest,
        description="Exact executable tool request for phase 0. Leave empty unless action_plan.required_tool is executable.",
    )
    response_strategy: ResponseStrategy | None = Field(
        default=None,
        description="Response script only when the current step is final-answer delivery. Leave null when evidence collection or planning comes first."
    )
    war_room_contract: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Operational contract for no-tool WarRoom reasoning. It must spell out freedom, duty, reason, "
            "deficiency, and the phase_3 speech boundary so downstream agents know what kind of thinking and speech is permitted."
        ),
    )
    candidate_pairs: List[AnchoredReasoningPair] = Field(
        description="Candidate reasoning pairs. Each pair must reference existing fact_ids."
    )

class AuditorOutput(BaseModel):
    is_satisfied: bool = Field(description="Whether the turn may proceed to phase_3 without more tool use.")
    rejection_reason: str = Field(description="Short audit memo explaining the decision.")
    instruction_to_0: str = Field(description="Exact tool call for phase_0, or empty string.")


class DeliveryReview(BaseModel):
    schema_version: Literal["DeliveryReview.v1"] = Field(default="DeliveryReview.v1", alias="schema")
    verdict: Literal["approve", "remand", "sos_119"] = Field(
        default="approve",
        description="Post-phase3 answer review decision.",
    )
    reason: str = Field(default="", description="Short review reason. Not user-facing.")
    issues_found: List[str] = Field(default_factory=list, description="Answer issues found by the reviewer.")
    remand_target: Literal["", "-1a", "-1s"] = Field(
        default="",
        description="Where to send the turn if the answer is rejected.",
    )
    remand_guidance: str = Field(default="", description="Guidance for the remand target. Not user-facing.")


class RescueHandoffPacket(BaseModel):
    schema_version: Literal["RescueHandoffPacket.v1"] = Field(default="RescueHandoffPacket.v1", alias="schema")
    trigger: Literal["budget_exceeded", "s_sos", "delivery_loop"] = Field(
        default="budget_exceeded",
        description="Why the rescue boundary was entered.",
    )
    attempted_path: List[str] = Field(default_factory=list, description="Compact runtime path already attempted.")
    preserved_evidences: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Validated partial evidences that survived rescue filtering.",
    )
    preserved_field_memo_facts: List[str] = Field(
        default_factory=list,
        description="FieldMemo facts already accepted for the current goal.",
    )
    rejected_only: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Rejected sources/candidates that must not be cited as answer evidence.",
    )
    what_we_know: List[str] = Field(default_factory=list, description="User-facing partial facts phase_3 may cite.")
    what_we_failed: List[str] = Field(default_factory=list, description="User-facing unresolved gaps.")
    speaker_tone_hint: Literal["사과 + 부분정보", "단순 모르겠다", "재질문", "다음 턴 약속"] = Field(
        default="단순 모르겠다",
        description="Natural tone hint for phase_3.",
    )
    user_facing_label: Literal["검색 결과 부족", "기억 못 찾음", "질문이 모호함", "재시도 필요"] = Field(
        default="검색 결과 부족",
        description="Code-owned coarse enum label; phase_3 naturalizes it instead of quoting it.",
    )


class ArbitrationPair(BaseModel):
    topic: Literal[
        "goal_slots",
        "source_validity",
        "answer_seed",
        "plan_status",
        "scroll_origin",
    ] = Field(description="Conflict topic compared by -1b between critic and strategist.")
    critic_claim: str = Field(default="", description="What 2b is effectively claiming on this topic.")
    strategist_claim: str = Field(default="", description="What -1a is effectively claiming on this topic.")
    conflict: bool = Field(default=False, description="Whether the critic and strategist materially disagree.")
    severity: Literal["low", "medium", "high"] = Field(default="low", description="Operational severity of the conflict.")
    preferred_side: Literal["critic", "strategist", "tie", "none"] = Field(
        default="none",
        description="Which side -1b should prefer on this topic."
    )
    blocking: bool = Field(default=False, description="Whether this conflict should block direct delivery.")
    recommended_action: Literal[
        "none",
        "phase_3",
        "plan_with_strategist",
        "call_tool",
        "warroom_deliberation",
        "internal_reasoning",
        "clean_failure",
        "answer_not_ready",
    ] = Field(
        default="none",
        description="Preferred next action if this pair is the controlling conflict."
    )
    resolution_rule: str = Field(default="", description="Short judge rule explaining how to resolve this conflict.")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Minimal structured evidence for this pair.")


class StrategyArbitrationAudit(BaseModel):
    audit_kind: Literal["critic_strategist_arbitration"] = Field(
        default="critic_strategist_arbitration",
        description="Audit packet that forces 2b and -1a onto the same comparison table."
    )
    user_goal: str = Field(default="", description="Compact restatement of the current user goal.")
    has_blocking_conflict: bool = Field(default=False, description="Whether any pair blocks immediate delivery.")
    recommended_action: Literal[
        "none",
        "phase_3",
        "plan_with_strategist",
        "call_tool",
        "warroom_deliberation",
        "internal_reasoning",
        "clean_failure",
        "answer_not_ready",
    ] = Field(default="none", description="Top-level next action recommended by the arbitration table.")
    blocking_topics: List[str] = Field(default_factory=list, description="Topics that currently block direct delivery.")
    audit_memo: str = Field(default="", description="Short memo summarizing the arbitration result.")
    pairs: List[ArbitrationPair] = Field(default_factory=list, description="Critic vs strategist comparison pairs.")


class ReasoningBudgetPlan(BaseModel):
    reasoning_budget: int = Field(description="How many reasoning/search loops are worth spending on this turn. 0 means answer directly.")
    preferred_path: Literal["delivery_contract", "internal_reasoning", "tool_first"] = Field(
        description="Recommended first path for this turn."
    )
    should_use_tools: bool = Field(description="Whether tool use is likely worthwhile for this turn.")
    rationale: str = Field(description="Short operational explanation for the budget choice.")


__all__ = [
    'EvidenceItem',
    'SourceJudgment',
    'FieldMemoJudgment',
    'AnalysisReport',
    'RawReadItem',
    'RawReadReport',
    'ResponseStrategy',
    'RecentDialogueBrief',
    'StartGateAssessment',
    'StartGateTurnContract',
    'SThinkingSituation',
    'SThinkingLoopSummary',
    'SThinkingNextDirection',
    'SThinkingRoutingDecision',
    'SThinkingPacket',
    'OpsToolCard',
    'OpsNodeCard',
    'OpsDecision',
    'StrategistToolRequest',
    'FactCell',
    'SubjectiveCell',
    'AnchoredReasoningPair',
    'ReasoningBoardV1',
    'CriticObjection',
    'CriticReport',
    'AdvocateReport',
    'VerdictBoard',
    'ReasoningBoardV2',
    'OperationContract',
    'OperationPlan',
    'GoalLock',
    'StrategistGoal',
    'StepByStepPlan',
    'StrategistReasoningOutput',
    'AuditorOutput',
    'DeliveryReview',
    'RescueHandoffPacket',
    'ArbitrationPair',
    'StrategyArbitrationAudit',
    'ReasoningBudgetPlan',
]
