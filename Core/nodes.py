import ast
import builtins
import json
import os
import re
import sys
import unicodedata
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from .request_intents_v4 import (
    extract_explicit_search_phrase as _shared_extract_explicit_search_phrase,
    is_assistant_investigation_request_turn as _shared_is_assistant_investigation_request_turn,
    is_assistant_question_request_turn as _shared_is_assistant_question_request_turn,
    is_directive_or_correction_turn as _shared_is_directive_or_correction_turn,
    is_initiative_request_turn as _shared_is_initiative_request_turn,
    is_recent_dialogue_review_turn as _shared_is_recent_dialogue_review_turn,
    topic_reset_confidence as _shared_topic_reset_confidence,
)
from .prompt_builders import (
    build_phase_2b_prompt,
    build_phase_minus_1a_prompt,
)
from .goal_contracts import (
    UserGoalContract,
    contract_satisfied_by_facts as _contract_satisfied_by_facts_impl,
    contract_identity_names_from_facts as _contract_identity_names_from_facts_impl,
    contract_status_packet as _contract_status_packet_impl,
    derive_user_goal_contract as _derive_user_goal_contract_impl,
    extract_canonical_name_candidates_from_identity_claim as _extract_canonical_name_candidates_from_identity_claim_impl,
    extract_user_name_candidates_from_text as _extract_user_name_candidates_from_text_impl,
    fact_supports_user_canonical_name_claim as _fact_supports_user_canonical_name_claim_impl,
    filled_slots_from_contract as _filled_slots_from_contract_impl,
)
from .state import AnimaState
from .evidence_ledger import (
    append_evidence_event,
    evidence_ledger_for_contract,
    evidence_ledger_for_prompt,
)
from .readiness import (
    normalize_readiness_decision,
    readiness_from_auditor_action,
    readiness_from_delivery_payload,
)
from .tools import available_tools
from .field_memo import (
    is_memory_state_disclosure_turn,
    looks_like_memo_recall_turn,
)
from .pipeline.contracts import (
    AdvocateReport,
    AnalysisReport,
    AnchoredReasoningPair,
    ArbitrationPair,
    AuditorOutput,
    CriticObjection,
    CriticReport,
    EvidenceItem,
    FactCell,
    FieldMemoJudgment,
    GoalLock,
    OperationContract,
    OperationPlan,
    OpsDecision,
    OpsNodeCard,
    OpsToolCard,
    RawReadItem,
    RawReadReport,
    ReasoningBoardV1,
    ReasoningBoardV2,
    ReasoningBudgetPlan,
    ResponseStrategy,
    SourceJudgment,
    StartGateAssessment,
    StartGateTurnContract,
    StepByStepPlan,
    StrategistReasoningOutput,
    StrategistToolRequest,
    StrategyArbitrationAudit,
    SubjectiveCell,
    VerdictBoard,
)
from .pipeline.packets import (
    analysis_packet_for_prompt as _analysis_packet_for_prompt,
    answer_mode_policy_packet_for_prompt as _answer_mode_policy_packet_for_prompt,
    build_source_relay_packet as _build_source_relay_packet,
    compact_analysis_for_prompt as _compact_analysis_for_prompt,
    judge_speaker_packet_for_prompt as _judge_speaker_packet_for_prompt,
    normalize_analysis_with_source_relay as _normalize_analysis_with_source_relay,
    raw_read_report_packet_for_prompt as _raw_read_report_packet_for_prompt,
    reasoning_board_packet_for_prompt as _reasoning_board_packet_for_prompt,
    source_relay_packet_for_prompt as _source_relay_packet_for_prompt,
    strategy_packet_for_prompt as _strategy_packet_for_prompt,
    strategist_output_packet_for_prompt as _strategist_output_packet_for_prompt,
    verdict_packet_for_prompt as _verdict_packet_for_prompt,
    working_memory_packet_for_prompt as _working_memory_packet_for_prompt,
)
from .pipeline.plans import (
    empty_action_plan as _empty_action_plan,
    empty_advocate_report as _empty_advocate_report,
    empty_critic_report as _empty_critic_report,
    empty_goal_lock as _empty_goal_lock,
    empty_operation_contract as _empty_operation_contract,
    empty_operation_plan as _empty_operation_plan,
    empty_verdict_board as _empty_verdict_board,
    normalize_action_plan as _normalize_action_plan,
    normalize_convergence_state as _normalize_convergence_state,
    normalize_delivery_readiness as _normalize_delivery_readiness,
    normalize_goal_lock as _normalize_goal_lock,
    normalize_operation_contract as _normalize_operation_contract,
    normalize_operation_plan as _normalize_operation_plan,
    normalize_short_string_list as _normalize_short_string_list,
    normalize_strategist_goal as _normalize_strategist_goal,
    strategist_answer_mode_target_from_policy as _strategist_answer_mode_target_from_policy,
    strategist_goal_from_goal_lock as _strategist_goal_from_goal_lock,
)
from .pipeline.delivery import run_phase_3_validator as _run_phase_3_validator
from .pipeline.delivery_contracts import (
    build_phase3_speaker_judge_contract as _build_phase3_speaker_judge_contract_impl,
    looks_like_internal_phase3_seed as _looks_like_internal_phase3_seed,
    verbalize_field_memo_delivery_seed as _verbalize_field_memo_delivery_seed_impl,
    verbalize_grounded_delivery_seed as _verbalize_grounded_delivery_seed_impl,
)
from .pipeline.delivery_failures import (
    build_clean_failure_packet as _build_clean_failure_packet_impl,
    clean_failure_missing_items as _clean_failure_missing_items_impl,
)
from .pipeline.delivery_gates import (
    field_memo_answer_ready_for_phase3 as _field_memo_answer_ready_for_phase3_impl,
    grounded_source_ready_for_phase3 as _grounded_source_ready_for_phase3_impl,
    guard_phase3_decision_for_grounded_turn as _guard_phase3_decision_for_grounded_turn_impl,
    phase3_delivery_payload_for_gate as _phase3_delivery_payload_for_gate_impl,
    phase3_delivery_payload_ready_for_gate as _phase3_delivery_payload_ready_for_gate_impl,
    recent_dialogue_ready_for_phase3 as _recent_dialogue_ready_for_phase3_impl,
    turn_requires_grounded_delivery as _turn_requires_grounded_delivery_impl,
)
from .pipeline.delivery_packets import build_judge_speaker_packet as _build_judge_speaker_packet
from .pipeline.delivery_payloads import (
    build_phase3_delivery_payload as _build_phase3_delivery_payload_impl,
    build_phase3_lane_delivery_packet as _build_phase3_lane_delivery_packet_impl,
    phase3_payload_accepted_facts_from_packet as _phase3_payload_accepted_facts_from_packet_impl,
)
from .pipeline.delivery_review import (
    build_speaker_review as _build_speaker_review,
    has_meaningful_delivery_seed as _has_meaningful_delivery_seed,
    is_generic_continue_seed as _is_generic_continue_seed,
    looks_like_generic_non_answer_text as _looks_like_generic_non_answer_text,
    looks_like_internal_delivery_leak as _looks_like_internal_delivery_leak,
    looks_like_user_parroting_report as _looks_like_user_parroting_report,
    normalize_user_facing_text as _normalize_user_facing_text,
    run_phase3_delivery_review as _run_phase3_delivery_review,
    sanitize_response_strategy_for_phase3 as _sanitize_response_strategy_for_phase3,
)
from .pipeline.delivery_sources import (
    build_field_memo_user_brief as _build_field_memo_user_brief_impl,
    build_findings_first_packet as _build_findings_first_packet_impl,
    build_grounded_source_findings_packet as _build_grounded_source_findings_packet_impl,
    build_recent_dialogue_brief as _build_recent_dialogue_brief_impl,
    extract_turns_from_recent_dialogue_report as _extract_turns_from_recent_dialogue_report_impl,
    field_memo_analysis_brief_for_delivery as _field_memo_analysis_brief_for_delivery_impl,
    format_findings_first_delivery as _format_findings_first_delivery_impl,
    parse_search_result_hits as _parse_search_result_hits_impl,
    recent_dialogue_brief_text as _recent_dialogue_brief_text_impl,
    split_field_memo_fact_blob as _split_field_memo_fact_blob_impl,
)
from .pipeline.answer_modes import (
    answer_mode_policy_allows_direct_phase3 as _answer_mode_policy_allows_direct_phase3_impl,
    answer_mode_policy_for_turn as _answer_mode_policy_for_turn_impl,
    answer_mode_policy_from_state as _answer_mode_policy_from_state_impl,
    extract_current_turn_grounding_facts as _extract_current_turn_grounding_facts_impl,
    response_strategy_from_answer_mode_policy as _response_strategy_from_answer_mode_policy_impl,
    turn_allows_parametric_knowledge_blend as _turn_allows_parametric_knowledge_blend_impl,
)
from .pipeline.continuation import (
    accepted_offer_execution_seed as _accepted_offer_execution_seed_impl,
    base_followup_context_expected as _base_followup_context_expected_impl,
    casual_social_user_facing_seed as _casual_social_user_facing_seed_impl,
    has_substantive_dialogue_anchor as _has_substantive_dialogue_anchor_impl,
    is_followup_offer_acceptance_turn as _is_followup_offer_acceptance_turn_impl,
    is_followup_ack_turn as _is_followup_ack_turn_impl,
    is_retry_previous_answer_turn as _is_retry_previous_answer_turn_impl,
    is_social_repair_turn as _is_social_repair_turn_impl,
    is_short_affirmation as _is_short_affirmation_impl,
    llm_short_term_context_material as _llm_short_term_context_material_impl,
    offer_acceptance_strategy as _offer_acceptance_strategy_impl,
    pending_dialogue_act_accepts_current_turn as _pending_dialogue_act_accepts_current_turn_impl,
    pending_dialogue_act_anchor as _pending_dialogue_act_anchor_impl,
    previous_delivery_anchor as _previous_delivery_anchor_impl,
    recent_context_last_assistant_turn as _recent_context_last_assistant_turn_impl,
    recent_context_invites_continuation as _recent_context_invites_continuation_impl,
    recent_hint_budget_from_working_memory as _recent_hint_budget_from_working_memory_impl,
    retry_previous_answer_strategy as _retry_previous_answer_strategy_impl,
    short_term_context_response_strategy as _short_term_context_response_strategy_impl,
    short_term_context_strategy_is_usable as _short_term_context_strategy_is_usable_impl,
    social_repair_strategy as _social_repair_strategy_impl,
    social_turn_strategy as _social_turn_strategy_impl,
    temporal_context_allows_carry_over as _temporal_context_allows_carry_over_impl,
    temporal_context_prefers_current_input as _temporal_context_prefers_current_input_impl,
    user_turn_targets_assistant_reply as _user_turn_targets_assistant_reply_impl,
    working_memory_active_offer as _working_memory_active_offer_impl,
    working_memory_active_task as _working_memory_active_task_impl,
    working_memory_direct_answer_seed as _working_memory_direct_answer_seed_impl,
    working_memory_expects_continuation as _working_memory_expects_continuation_impl,
    working_memory_last_assistant_answer as _working_memory_last_assistant_answer_impl,
    working_memory_pending_question as _working_memory_pending_question_impl,
    working_memory_pending_dialogue_act as _working_memory_pending_dialogue_act_impl,
    working_memory_temporal_context as _working_memory_temporal_context_impl,
    working_memory_writer_packet as _working_memory_writer_packet_impl,
)
from .pipeline.field_memo_review import (
    enforce_field_memo_judgments as _enforce_field_memo_judgments_impl,
    field_memo_evidence_kind as _field_memo_evidence_kind_impl,
    field_memo_evidence_text as _field_memo_evidence_text_impl,
    field_memo_facts_from_item as _field_memo_facts_from_item_impl,
    field_memo_judgments_from_source_judgments as _field_memo_judgments_from_source_judgments_impl,
    field_memo_metadata_text as _field_memo_metadata_text_impl,
    field_memo_packet_ready_for_delivery as _field_memo_packet_ready_for_delivery_impl,
    field_memo_review_has_concrete_memos as _field_memo_review_has_concrete_memos_impl,
    field_memo_text as _field_memo_text_impl,
    field_memo_tokens as _field_memo_tokens_impl,
    judge_field_memo_item_for_goal as _judge_field_memo_item_for_goal_impl,
    rejected_sources_from_field_memo_judgments as _rejected_sources_from_field_memo_judgments_impl,
)
from .pipeline.fact_judge import run_phase_2_analyzer as _run_phase_2_analyzer
from .pipeline.reader import run_phase_2a_reader as _run_phase_2a_reader
from .pipeline.rescue import run_phase_119_rescue as _run_phase_119_rescue
from .pipeline.start_gate import run_phase_minus_1s_start_gate as _run_phase_minus_1s_start_gate
from .pipeline.strategy import (
    run_base_phase_minus_1a_thinker as _run_base_phase_minus_1a_thinker,
    run_phase_minus_1a_thinker as _run_phase_minus_1a_thinker,
)
from .pipeline.strategy_repairs import (
    ensure_direct_delivery_response_strategy as _ensure_direct_delivery_response_strategy_impl,
    ensure_social_turn_strategist_delivery as _ensure_social_turn_strategist_delivery_impl,
)
from .pipeline.supervisor import run_phase_0_supervisor as _run_phase_0_supervisor
from .pipeline.tool_execution import run_phase_1_searcher as _run_phase_1_searcher
from .pipeline.runtime_context import (
    empty_tool_carryover_state as _empty_tool_carryover_state_impl,
    extract_source_ids_from_tool_result as _extract_source_ids_from_tool_result_impl,
    normalize_execution_trace as _normalize_execution_trace_impl,
    normalize_tool_carryover_state as _normalize_tool_carryover_state_impl,
    source_id_looks_scrollable as _source_id_looks_scrollable_impl,
    source_ids_from_working_memory as _source_ids_from_working_memory_impl,
    stable_action_signature as _stable_action_signature_impl,
    tool_carryover_anchor_id as _tool_carryover_anchor_id_impl,
    tool_carryover_from_state as _tool_carryover_from_state_impl,
    tool_carryover_from_working_memory as _tool_carryover_from_working_memory_impl,
    tool_query_from_args as _tool_query_from_args_impl,
    update_tool_carryover_after_tool as _update_tool_carryover_after_tool_impl,
)
from .pipeline.progress import (
    advance_progress_markers as _advance_progress_markers_impl,
    analysis_progress_signature as _analysis_progress_signature_impl,
    analysis_refresh_allowed as _analysis_refresh_allowed_impl,
    analysis_refresh_signature as _analysis_refresh_signature_impl,
    apply_progress_contract as _apply_progress_contract_impl,
    build_strategy_arbitration_audit as _build_strategy_arbitration_audit_impl,
    decision_from_strategy_arbitration_audit as _decision_from_strategy_arbitration_audit_impl,
    execution_trace_signature as _execution_trace_signature_impl,
    mark_analysis_refresh as _mark_analysis_refresh_impl,
    merge_strategy_audits as _merge_strategy_audits_impl,
    normalize_progress_markers as _normalize_progress_markers_impl,
    operation_contract_from_action_plan as _operation_contract_from_action_plan_impl,
    operation_contract_signature as _operation_contract_signature_impl,
    raw_progress_signature as _raw_progress_signature_impl,
    same_tool_call_as_execution as _same_tool_call_as_execution_impl,
    signature_digest as _signature_digest_impl,
    strategy_progress_signature as _strategy_progress_signature_impl,
    with_execution_trace_contract as _with_execution_trace_contract_impl,
)
from .pipeline.tool_planning import (
    compiled_memory_recall_queries as _compiled_memory_recall_queries_impl,
    decision_from_strategist_tool_contract as _decision_from_strategist_tool_contract_impl,
    deterministic_strategist_tool_request_from_context as _deterministic_strategist_tool_request_from_context_impl,
    ensure_tool_request_in_strategist_payload as _ensure_tool_request_in_strategist_payload_impl,
    recent_context_anchor_query as _recent_context_anchor_query_impl,
    strategist_tool_request_from_context as _strategist_tool_request_from_context_impl,
    tool_request_payload_from_instruction as _tool_request_payload_from_instruction_impl,
    valid_strategist_tool_request as _valid_strategist_tool_request_impl,
)
from .warroom.contracts import (
    WarRoomAgentNote,
    WarRoomDeliberationOutput,
    WarRoomDuty,
    WarRoomEpistemicDebt,
    WarRoomFreedom,
    WarRoomStateV1,
)
from .warroom.deliberator import run_phase_warroom_deliberator as _run_phase_warroom_deliberator
from .warroom.output import (
    _build_warroom_answer_seed_packet as _build_warroom_answer_seed_packet_impl,
    _fallback_war_room_output as _fallback_war_room_output_impl,
    _response_strategy_from_war_room_output,
    _war_room_output_is_usable,
    _war_room_seed_alignment_issue as _war_room_seed_alignment_issue_impl,
)
from .warroom.state import (
    _derive_war_room_operating_contract,
    _empty_war_room_operating_contract,
    _empty_war_room_state,
    _normalize_war_room_operating_contract,
    _normalize_war_room_state,
    _upsert_war_room_agent_note,
    _war_room_after_advocate,
    _war_room_after_judge,
    _war_room_from_critic,
    _war_room_missing_items_from_analysis,
    _war_room_packet_for_prompt,
)
from Core.adapters.neo4j_connection import get_db_session
from typing import Any

load_dotenv()


def _env_model_name(key: str, default: str) -> str:
    value = os.getenv(key, "").strip()
    return value or default


ANIMA_MAIN_MODEL = _env_model_name("ANIMA_MAIN_MODEL", "gemma4:e4b")
ANIMA_SUPERVISOR_MODEL = _env_model_name("ANIMA_SUPERVISOR_MODEL", "llama3.1")

llm = ChatOllama(model=ANIMA_MAIN_MODEL, temperature=0.0)
llm_supervisor = ChatOllama(model=ANIMA_SUPERVISOR_MODEL, temperature=0.0)

def _log(message: str):
    text = str(message)
    try:
        builtins.print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        builtins.print(safe_text)

print = _log
print(f"[ANIMA Models] main={ANIMA_MAIN_MODEL} | supervisor={ANIMA_SUPERVISOR_MODEL}")


def _is_clean_failure_action(action: Any) -> bool:
    return str(action or "").strip() in {"answer_not_ready", "clean_failure"}


def _ledger_with_event(state: dict, *, source_kind: str, producer_node: str, content: Any, source_ref: str = "", confidence: float = 1.0):
    return append_evidence_event(
        state.get("evidence_ledger", {}) if isinstance(state, dict) else {},
        source_kind=source_kind,
        producer_node=producer_node,
        source_ref=source_ref,
        timestamp=str(state.get("current_time") or "") if isinstance(state, dict) else "",
        content=content,
        confidence=confidence,
    )


def _attach_ledger_event(result: dict, state: dict, *, source_kind: str, producer_node: str, content: Any, source_ref: str = "", confidence: float = 1.0):
    if not isinstance(result, dict):
        return result
    result["evidence_ledger"] = _ledger_with_event(
        state,
        source_kind=source_kind,
        producer_node=producer_node,
        source_ref=source_ref,
        content=content,
        confidence=confidence,
    )
    return result

def _normalize_reasoning_preferred_path(value: Any) -> str:
    path = str(value or "").strip()
    if path == "direct_answer":
        return "delivery_contract"
    if path in {"delivery_contract", "internal_reasoning", "tool_first"}:
        return path
    return "internal_reasoning"


def extract_local_topology(node_ids: list):
    """
    Extract a 1-hop local topology summary for the given node ids.
    Returns strings like `Label -[REL]- Label` for nearby graph context.
    """
    if not node_ids:
        return "No local topology extracted because no source node ids were provided."

    query = """
    MATCH (n)-[r]-(m)
    WHERE n.date IN $node_ids OR n.id IN $node_ids
    WITH labels(n) AS source_labels, type(r) AS rel_type, labels(m) AS target_labels
    RETURN DISTINCT source_labels[0] + " -[" + rel_type + "]- " + target_labels[0] AS topology
    """
    try:
        with get_db_session() as session:
            result = session.run(query, node_ids=node_ids)
            topologies = [record["topology"] for record in result]

            if topologies:
                return "Local topology: " + ", ".join(topologies)
            return "No local topology was found around the referenced nodes."
    except Exception as e:
        print(f"[topology extraction error] {e}")
        return "Local topology extraction failed."


def get_tool_descriptions():
    desc = ""
    for t in available_tools:
        desc += f"- tool [{t.name}] | description: {t.description}\n"
    return desc


def _extract_tool_expression(text: str):
    if not text:
        return ""
    match = re.search(r"(tool_[A-Za-z0-9_]+\s*\(.*\))", text, re.DOTALL)
    return match.group(1).strip() if match else ""

def _has_structured_analysis(analysis_data: dict):
    if not isinstance(analysis_data, dict) or not analysis_data:
        return False
    if str(analysis_data.get("investigation_status") or "").strip():
        return True
    if analysis_data.get("evidences"):
        return True
    if str(analysis_data.get("situational_brief") or "").strip():
        return True
    return False


def _analysis_has_grounded_artifact_evidence(analysis_data: dict):
    if not isinstance(analysis_data, dict) or not analysis_data:
        return False

    evidences = analysis_data.get("evidences", [])
    if isinstance(evidences, list):
        for item in evidences:
            if not isinstance(item, dict):
                continue
            source_type = str(item.get("source_type") or "").strip().lower()
            extracted_fact = str(item.get("extracted_fact") or item.get("excerpt") or "").strip()
            if source_type == "artifact" and extracted_fact:
                return True

    source_judgments = analysis_data.get("source_judgments", [])
    if isinstance(source_judgments, list):
        for item in source_judgments:
            if not isinstance(item, dict):
                continue
            source_type = str(item.get("source_type") or "").strip().lower()
            accepted_facts = item.get("accepted_facts", [])
            if source_type == "artifact" and isinstance(accepted_facts, list) and any(str(fact).strip() for fact in accepted_facts):
                return True

    return False

def _tool_call_to_instruction(tool_name: str, tool_args: dict | None = None):
    tool_args = tool_args or {}
    if not tool_args:
        return f"{tool_name}()"
    pieces = []
    for key, value in tool_args.items():
        pieces.append(f"{key}={json.dumps(value, ensure_ascii=False)}")
    return f"{tool_name}({', '.join(pieces)})"

def _make_auditor_decision(action: str, memo: str = "", tool_name: str = "", tool_args: dict | None = None):
    normalized_tool_args = tool_args or {}
    instruction = ""
    if action == "phase_3":
        tool_name = "tool_pass_to_phase_3"
        normalized_tool_args = {}
        instruction = "tool_pass_to_phase_3()"
    elif action == "phase_119":
        tool_name = "tool_call_119_rescue"
        normalized_tool_args = {}
        instruction = "tool_call_119_rescue()"
    elif action == "call_tool" and tool_name:
        instruction = _tool_call_to_instruction(tool_name, normalized_tool_args)

    readiness_decision = readiness_from_auditor_action(
        action,
        memo=memo,
        tool_name=tool_name,
        tool_args=normalized_tool_args,
    )
    return {
        "action": action,
        "operational_state": action,
        "tool_name": tool_name,
        "tool_args": normalized_tool_args,
        "instruction": instruction,
        "memo": str(memo or "").strip(),
        "readiness_decision": readiness_decision,
    }


def _fallback_reasoning_budget_plan(user_input: str, working_memory: dict, artifact_hint: str = ""):
    text = str(user_input or "").strip()
    if artifact_hint:
        return {
            "reasoning_budget": 2,
            "preferred_path": "tool_first",
            "should_use_tools": True,
            "rationale": "This request is best resolved by reading the source material first.",
        }
    if _followup_context_expected(text, "", working_memory):
        return {
            "reasoning_budget": 1,
            "preferred_path": "internal_reasoning",
            "should_use_tools": False,
            "rationale": "This is a follow-up, but the strategist should still rebuild the concrete continuation contract before delivery.",
        }
    return {
        "reasoning_budget": 1,
        "preferred_path": "internal_reasoning",
        "should_use_tools": False,
        "rationale": "Fallback budget is intentionally thin; start-gate and planner contracts decide tools.",
    }

def _base_plan_reasoning_budget(user_input: str, recent_context: str, working_memory: dict):
    artifact_hint = _extract_artifact_hint(user_input)
    working_memory_packet = _working_memory_packet_for_prompt(working_memory, role="start_gate")
    sys_prompt = f"""You are ANIMA's thin reasoning-budget planner.

Read the current user input, recent context, and working memory. Decide only how much
thinking depth this turn needs. Do not choose concrete tools, rewrite the user's goal,
or produce final answer wording.

[user_input]
{user_input}

[recent_context]
{recent_context}

[working_memory]
{working_memory_packet}

[artifact_hint]
{artifact_hint if artifact_hint else '(none)'}

[reasoning_budget scale]
- 0: direct delivery is enough.
- 1: light reasoning or one short continuation step.
- 2: moderate reasoning or evidence review may be needed.
- 3~4: genuinely complex work needing extra planning.

[rules]
1. For simple continuation or social response, choose delivery_contract.
2. For ambiguous but answerable turns, choose internal_reasoning.
3. If a document, artifact, or explicit external source must be read, choose tool_first.
4. If artifact_hint exists, strongly prefer tool_first.
5. reasoning_budget is a budget, not an action plan.
6. preferred_path must be one of delivery_contract, internal_reasoning, tool_first.
"""

    try:
        structured_llm = llm.with_structured_output(ReasoningBudgetPlan)
        res = structured_llm.invoke([SystemMessage(content=sys_prompt)])
        plan = res.model_dump()
        plan["reasoning_budget"] = max(0, min(int(plan.get("reasoning_budget", 1)), 4))
        plan["preferred_path"] = _normalize_reasoning_preferred_path(plan.get("preferred_path"))
        if artifact_hint and plan["preferred_path"] != "tool_first":
            plan["preferred_path"] = "tool_first"
            plan["should_use_tools"] = True
        return plan
    except Exception as e:
        print(f"[Reasoning fallback] structured output failed; using fallback plan: {e}")
        return _fallback_reasoning_budget_plan(user_input, working_memory, artifact_hint=artifact_hint)

def _decision_from_instruction(instruction: str, is_satisfied: bool, memo: str):
    stripped = str(instruction or "").strip()
    if not stripped:
        return _make_auditor_decision("phase_3", memo=memo) if is_satisfied else None

    direct_message = _build_direct_tool_message(stripped)
    if direct_message is not None:
        tool_call = direct_message.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call.get("args", {})
        if tool_name == "tool_pass_to_phase_3":
            return _make_auditor_decision("phase_3", memo=memo)
        if tool_name == "tool_call_119_rescue":
            return _make_auditor_decision("phase_119", memo=memo)
        if tool_name in {"tool_search_memory", "tool_search_field_memos"}:
            repaired = _repair_search_tool_request(tool_name, tool_args, fallback_text=stripped)
            if not repaired:
                return None
            tool_name, tool_args = repaired
        return _make_auditor_decision("call_tool", memo=memo, tool_name=tool_name, tool_args=tool_args)

    if not is_satisfied:
        normalized_instruction = _normalize_suggested_instruction(stripped)
        direct_message = _build_direct_tool_message(normalized_instruction)
        if direct_message is not None:
            tool_call = direct_message.tool_calls[0]
            return _make_auditor_decision(
                "call_tool",
                memo=memo,
                tool_name=tool_call["name"],
                tool_args=tool_call.get("args", {}),
            )

    if is_satisfied:
        return _make_auditor_decision("phase_3", memo=memo)
    return None


def _extract_exact_tool_call(suggestion: str):
    stripped = str(suggestion or "").strip()
    if not stripped:
        return ""

    direct_message = _build_direct_tool_message(stripped)
    if direct_message is None:
        return ""

    tool_call = direct_message.tool_calls[0]
    tool_name = str(tool_call.get("name") or "").strip()
    tool_args = tool_call.get("args", {}) if isinstance(tool_call.get("args"), dict) else {}

    if tool_name == "tool_pass_to_phase_3":
        return "tool_pass_to_phase_3()"
    if tool_name == "tool_call_119_rescue":
        return "tool_call_119_rescue()"
    if tool_name.startswith("tool_"):
        return _tool_call_to_instruction(tool_name, tool_args)
    return ""


def _enforce_recent_dialogue_review_analysis(analysis_dict: dict, raw_read_report: dict):
    if not isinstance(analysis_dict, dict):
        analysis_dict = {}
    if not isinstance(raw_read_report, dict):
        return analysis_dict

    read_mode = str(raw_read_report.get("read_mode") or "").strip()
    if read_mode != "recent_dialogue_review":
        return analysis_dict

    normalized = json.loads(json.dumps(analysis_dict, ensure_ascii=False))
    raw_items = raw_read_report.get("items", [])
    if not isinstance(raw_items, list):
        raw_items = []
    if _recent_dialogue_review_failed(raw_read_report):
        existing_brief = str(normalized.get("situational_brief") or "").strip()
        existing_thought = str(normalized.get("analytical_thought") or "").strip()
        normalized["investigation_status"] = "INCOMPLETE"
        normalized["situational_brief"] = (
            "Recent dialogue review failed because concrete recent raw turns were not actually available. "
            "Do not pretend the recent conversation was inspected."
        )
        if existing_brief and existing_brief != normalized["situational_brief"]:
            normalized["situational_brief"] += f" Existing brief: {existing_brief}"
        fail_note = (
            "recent_dialogue_review requested concrete recent turns, but phase_2a did not recover enough "
            "recent raw dialogue items. The case must stay incomplete and should not loop as if review succeeded."
        )
        normalized["analytical_thought"] = (
            f"{existing_thought}\n{fail_note}".strip()
            if existing_thought
            else fail_note
        )
        return normalized

    evidences = normalized.get("evidences", [])
    if not isinstance(evidences, list):
        evidences = []

    concrete_evidence_count = 0
    existing_evidence_keys = set()
    for evidence in evidences:
        if not isinstance(evidence, dict):
            continue
        source_id = str(evidence.get("source_id") or "").strip()
        extracted_fact = str(evidence.get("extracted_fact") or "").strip()
        if source_id.startswith("recent_turn_") and extracted_fact:
            concrete_evidence_count += 1
        if source_id and extracted_fact:
            existing_evidence_keys.add((source_id, extracted_fact))

    model_concrete_evidence_count = concrete_evidence_count

    recent_turn_evidences = []
    for item in raw_items[:3]:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id") or "").strip()
        observed_fact = str(item.get("observed_fact") or "").strip()
        source_type = str(item.get("source_type") or "recent_chat_turn").strip() or "recent_chat_turn"
        if not source_id or not observed_fact:
            continue
        if (source_id, observed_fact) in existing_evidence_keys:
            continue
        recent_turn_evidences.append({
            "source_id": source_id,
            "source_type": source_type,
            "extracted_fact": observed_fact,
        })
        existing_evidence_keys.add((source_id, observed_fact))

    if concrete_evidence_count < 2 and recent_turn_evidences:
        evidences.extend(recent_turn_evidences)
        concrete_evidence_count += len(recent_turn_evidences)

    normalized["evidences"] = evidences

    if model_concrete_evidence_count >= 2:
        return normalized

    status = str(normalized.get("investigation_status") or "").strip()
    if status == "COMPLETED":
        normalized["investigation_status"] = "INCOMPLETE"

    existing_brief = str(normalized.get("situational_brief") or "").strip()
    normalized["situational_brief"] = (
        "Recent dialogue review requires concrete turn-level evidence. "
        "General dissatisfaction summaries are not enough to close the case."
    )
    if existing_brief and existing_brief != normalized["situational_brief"]:
        normalized["situational_brief"] += f" Existing brief: {existing_brief}"

    existing_thought = str(normalized.get("analytical_thought") or "").strip()
    added_note = (
        "In recent_dialogue_review mode, analysis must point to concrete recent turns. "
        "If the model cannot cite those turns, it should stay incomplete rather than pretend the review is finished."
    )
    normalized["analytical_thought"] = (
        f"{existing_thought}\n{added_note}".strip()
        if existing_thought
        else added_note
    )

    return normalized



def _phase_2_tool_guide():
    return (
        "Available exact tool calls when expansion is required:\n"
        "- tool_search_memory(keyword=\"...\")\n"
        "- tool_read_full_diary(target_date=\"YYYY-MM-DD\")\n"
        "- tool_scroll_chat_log(target_id=\"...\", direction=\"both\", limit=15)\n"
        "- tool_read_artifact(artifact_hint=\"...\")\n"
        "- tool_scan_db_schema(dummy_keyword=\"schema\")\n"
    )




def _raw_reference_excerpt(search_results: str, limit: int = 4000):
    raw_reference = str(search_results or "").strip()
    if not raw_reference:
        return ""
    if len(raw_reference) > limit:
        return raw_reference[:limit] + "\n...(truncated)"
    return raw_reference


def _phase3_followup_strength(loop_count: int):
    try:
        current_loop = int(loop_count or 0)
    except (TypeError, ValueError):
        current_loop = 0

    if current_loop <= 1:
        return {
            "level": "gentle",
            "instruction": "Ask for one small clarification if the answer boundary is still unclear.",
        }
    if current_loop == 2:
        return {
            "level": "direct",
            "instruction": "Ask the user to name the exact question, item, or source needed.",
        }
    return {
        "level": "firm",
        "instruction": "Stop guessing and ask for a concrete target before continuing.",
    }

def _phase3_reference_policy(search_results: str, loop_count: int, small_limit: int = 1200):
    raw_reference = str(search_results or "").strip()
    strength = _phase3_followup_strength(loop_count)

    if not raw_reference:
        return {
            "mode": "none",
            "char_count": 0,
            "raw_reference": "",
            "followup_strength": strength["level"],
            "followup_instruction": strength["instruction"],
            "note": "No raw reference is available for phase_3.",
        }

    if len(raw_reference) <= small_limit:
        return {
            "mode": "small_raw_allowed",
            "char_count": len(raw_reference),
            "raw_reference": raw_reference,
            "followup_strength": strength["level"],
            "followup_instruction": strength["instruction"],
            "note": "The raw reference is small enough to expose to phase_3.",
        }

    return {
        "mode": "hidden_large_raw",
        "char_count": len(raw_reference),
        "raw_reference": "",
        "followup_strength": strength["level"],
        "followup_instruction": strength["instruction"],
        "note": "The raw reference is too large, so phase_3 should rely on follow-up guidance instead.",
    }


def _compact_user_facing_summary(text: str, limit: int = 160):
    normalized = re.sub(r"\s+", " ", str(text or "").strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


def _parse_search_result_hits(raw_reference: str):
    return _parse_search_result_hits_impl(
        raw_reference,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _format_findings_first_delivery(user_input: str, judge_speaker_packet: dict):
    return _format_findings_first_delivery_impl(
        user_input,
        judge_speaker_packet,
        compact_user_facing_summary=_compact_user_facing_summary,
        extract_explicit_search_keyword=_extract_explicit_search_keyword,
    )


def _extract_turns_from_recent_dialogue_report(raw_read_report: dict, max_turns: int = 6):
    return _extract_turns_from_recent_dialogue_report_impl(raw_read_report, max_turns=max_turns)


def _recent_dialogue_brief_text(turns: list[dict], user_input: str = ""):
    return _recent_dialogue_brief_text_impl(
        turns,
        user_input=user_input,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _build_recent_dialogue_brief(raw_read_report: dict, analysis_data: dict | None = None, user_input: str = ""):
    return _build_recent_dialogue_brief_impl(
        raw_read_report,
        analysis_data,
        user_input=user_input,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _field_memo_analysis_brief_for_delivery(analysis_data: dict):
    return _field_memo_analysis_brief_for_delivery_impl(analysis_data)


def _split_field_memo_fact_blob(value: str) -> list[str]:
    return [
        _compact_user_facing_summary(item, limit=180)
        for item in _split_field_memo_fact_blob_impl(value)
    ]


def _compact_contract_key(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "").lower())
    return re.sub(r"\s+", "", normalized)


def _field_memo_evidence_text(item: dict):
    return _field_memo_evidence_text_impl(item)


def _field_memo_metadata_text(item: dict):
    return _field_memo_metadata_text_impl(item)


def _field_memo_text(item: dict):
    return _field_memo_text_impl(item)


def _derive_user_goal_contract(user_input: str, source_lane: str = "field_memo_review"):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    return UserGoalContract(
        user_goal=_normalized_goal_from_user_input(text),
        source_lane=source_lane,
        output_act="answer",
        slot_to_fill="",
        success_criteria=["Answer the normalized current user goal without broadening it."],
        forbidden_drift=[],
        evidence_required=False,
    ).model_dump()


def _extract_user_name_candidates_from_text(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "").strip())
    if not normalized:
        return []
    names = []
    patterns = [
        r"\bname\s*(?:is|:|=)\s*([A-Za-z][A-Za-z0-9_-]{1,30})",
        r"\ub0b4\s*\uc774\ub984\s*(?:\uc740|\ub294|:|=)?\s*([\uac00-\ud7a3]{2,4})",
        r"\ub098\uc758\s*\uc774\ub984\s*(?:\uc740|\ub294|:|=)?\s*([\uac00-\ud7a3]{2,4})",
        r"\uc0ac\uc6a9\uc790(?:\uc758)?\s*\uc774\ub984\s*(?:\uc740|\ub294|:|=)?\s*([\uac00-\ud7a3]{2,4})",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, normalized, flags=re.IGNORECASE):
            candidate = str(match or "").strip()
            if 2 <= len(candidate) <= 30:
                names.append(candidate)
    return _dedupe_keep_order(names)[:3]


def _contract_identity_names_from_facts(facts: list[str], answer_brief: str = ""):
    names = []
    for value in list(facts or []) + ([answer_brief] if answer_brief else []):
        value_text = str(value or "")
        if not _fact_supports_user_canonical_name_claim(value_text):
            continue
        names.extend(_extract_canonical_name_candidates_from_identity_claim(value_text))
        names.extend(_extract_user_name_candidates_from_text(value_text))
    return _dedupe_keep_order(names)[:3]


def _extract_canonical_name_candidates_from_identity_claim(value: str):
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    if not text:
        return []
    names: list[str] = []
    if "\ud5c8\uc815\ud6c4" in text:
        names.append("\ud5c8\uc815\ud6c4")
    direct_patterns = [
        r"\ub0b4\s*\uc774\ub984\s*(?:\uc740|\ub294|\uc774|\uac00|:|=)?\s*([\uac00-\ud7a3]{2,4})",
        r"\ub098\uc758\s*\uc774\ub984\s*(?:\uc740|\ub294|\uc774|\uac00|:|=)?\s*([\uac00-\ud7a3]{2,4})",
        r"\uc0ac\uc6a9\uc790(?:\uc758)?\s*\uc774\ub984\s*(?:\uc740|\ub294|\uc774|\uac00|:|=)?\s*([\uac00-\ud7a3]{2,4})",
        r"\uc0ac\uc6a9\uc790\ub294\s*([\uac00-\ud7a3]{2,4})",
        r"\uac1c\ubc1c\uc790(?:\ub294|\uac00|\(|\s)*([\uac00-\ud7a3]{2,4})",
    ]
    for pattern in direct_patterns:
        for match in re.findall(pattern, text):
            candidate = str(match or "").strip()
            if 2 <= len(candidate) <= 4:
                names.append(candidate)
    return _dedupe_keep_order(names)[:3]


def _fact_supports_user_canonical_name_claim(value: str):
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    if not text:
        return False
    lowered = text.lower()
    compact = re.sub(r"\s+", "", lowered)

    # A user-name slot must be backed by an identity claim, not by any list of
    # Korean names. This prevents friend lists or story character lists from
    # satisfying "say my name".
    list_context_markers = [
        "\uce5c\uad6c",          # friend
        "\ub4f1\uc7a5\uc778\ubb3c",  # character
        "\uce90\ub9ad\ud130",      # character
        "\uac8c\uc784",          # game
        "\uc624\ubaa8\ub9ac",      # omori
        "\uc18c\uc124",          # fiction/story
        "\uc774\uc57c\uae30",      # story
    ]
    identity_markers = [
        "\ub0b4\uc774\ub984",
        "\ub098\uc758\uc774\ub984",
        "\uc0ac\uc6a9\uc790\uc774\ub984",
        "\uc0ac\uc6a9\uc790",
        "\ubcf8\uba85",
        "\uac1c\ubc1c\uc790",
        "\ub9cc\ub4e0",
        "\ud5c8\uc815\ud6c4",
        "person profile",
        "canonical_name",
    ]

    has_identity_anchor = any(marker in compact for marker in identity_markers)
    if any(marker in compact for marker in list_context_markers) and not has_identity_anchor:
        return False

    direct_claim_patterns = [
        r"\ub0b4\s*\uc774\ub984\s*(?:\uc740|\ub294|\uc774|\uac00|:|=)?\s*[\uac00-\ud7a3]{2,4}",
        r"\ub098\uc758\s*\uc774\ub984\s*(?:\uc740|\ub294|\uc774|\uac00|:|=)?\s*[\uac00-\ud7a3]{2,4}",
        r"\uc0ac\uc6a9\uc790(?:\uc758)?\s*\uc774\ub984\s*(?:\uc740|\ub294|\uc774|\uac00|:|=)?\s*[\uac00-\ud7a3]{2,4}",
        r"\uc0ac\uc6a9\uc790\ub294\s*[\uac00-\ud7a3]{2,4}",
        r"\uac1c\ubc1c\uc790(?:\ub294|\uac00|\(|\s)*[\uac00-\ud7a3]{2,4}",
    ]
    if any(re.search(pattern, text) for pattern in direct_claim_patterns):
        return True

    # The current project repeatedly identifies the human developer/user as
    # Heo Jeonghu; still require an identity-ish anchor around the name.
    return "\ud5c8\uc815\ud6c4" in text and has_identity_anchor


def _contract_satisfied_by_facts(contract: dict, facts: list[str], answer_brief: str = ""):
    slot = str((contract or {}).get("slot_to_fill") or "").strip()
    if slot == "user.canonical_name":
        return bool(_contract_identity_names_from_facts(facts, answer_brief))
    return True


def _contract_status_packet(contract: dict, facts: list[str], answer_brief: str = ""):
    slot = str((contract or {}).get("slot_to_fill") or "").strip()
    if not slot:
        return "satisfied", [], ""
    if _contract_satisfied_by_facts(contract, facts, answer_brief):
        return "satisfied", [], ""
    directive = (
        f"The current evidence does not fill `{slot}` directly. "
        "Do not widen into a nearby analysis; look for evidence that fills the slot itself."
    )
    return "missing_slot", [slot], directive


def _filled_slots_from_contract(contract: dict, facts: list[str], answer_brief: str = ""):
    slot = str((contract or {}).get("slot_to_fill") or "").strip()
    if not slot:
        return {}
    facts = [str(fact).strip() for fact in facts or [] if str(fact).strip()]
    if not _contract_satisfied_by_facts(contract, facts, answer_brief):
        return {}
    if slot == "user.canonical_name":
        names = _contract_identity_names_from_facts(facts, answer_brief)
        return {slot: names[0]} if names else {}
    if answer_brief:
        return {slot: _compact_user_facing_summary(answer_brief, 240)}
    return {slot: facts[:4]} if facts else {}


# Canonical goal-contract bindings live in Core.goal_contracts.
_derive_user_goal_contract = _derive_user_goal_contract_impl
_extract_user_name_candidates_from_text = _extract_user_name_candidates_from_text_impl
_extract_canonical_name_candidates_from_identity_claim = _extract_canonical_name_candidates_from_identity_claim_impl
_fact_supports_user_canonical_name_claim = _fact_supports_user_canonical_name_claim_impl
_contract_identity_names_from_facts = _contract_identity_names_from_facts_impl
_contract_satisfied_by_facts = _contract_satisfied_by_facts_impl
_contract_status_packet = _contract_status_packet_impl
_filled_slots_from_contract = _filled_slots_from_contract_impl


def _rejected_sources_from_field_memo_judgments(judgments: list[dict]):
    return _rejected_sources_from_field_memo_judgments_impl(judgments)



def _field_memo_tokens(text: str):
    return _field_memo_tokens_impl(text)


def _field_memo_evidence_kind(item: dict):
    return _field_memo_evidence_kind_impl(
        item,
        split_field_memo_fact_blob=_split_field_memo_fact_blob,
        compact_user_facing_summary=_compact_user_facing_summary,
    )

def _field_memo_facts_from_item(item: dict):
    return _field_memo_facts_from_item_impl(
        item,
        split_field_memo_fact_blob=_split_field_memo_fact_blob,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _judge_field_memo_item_for_goal(item: dict, user_input: str):
    return _judge_field_memo_item_for_goal_impl(
        item,
        user_input,
        split_field_memo_fact_blob=_split_field_memo_fact_blob,
        compact_user_facing_summary=_compact_user_facing_summary,
        derive_user_goal_contract=_derive_user_goal_contract,
        contract_satisfied_by_facts=_contract_satisfied_by_facts,
    )

def _field_memo_judgments_from_source_judgments(source_judgments: list[dict], item_ids: set[str]):
    return _field_memo_judgments_from_source_judgments_impl(
        source_judgments,
        item_ids,
        normalize_short_string_list=_normalize_short_string_list,
    )

def _enforce_field_memo_judgments(analysis_dict: dict, raw_read_report: dict, user_input: str):
    return _enforce_field_memo_judgments_impl(
        analysis_dict,
        raw_read_report,
        user_input,
        split_field_memo_fact_blob=_split_field_memo_fact_blob,
        compact_user_facing_summary=_compact_user_facing_summary,
        derive_user_goal_contract=_derive_user_goal_contract,
        contract_satisfied_by_facts=_contract_satisfied_by_facts,
        contract_status_packet=_contract_status_packet,
        filled_slots_from_contract=_filled_slots_from_contract,
        normalize_short_string_list=_normalize_short_string_list,
    )


def _build_field_memo_user_brief(raw_read_report: dict, analysis_data: dict | None = None):
    return _build_field_memo_user_brief_impl(
        raw_read_report,
        analysis_data,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _field_memo_review_has_concrete_memos(raw_read_report: dict):
    return _field_memo_review_has_concrete_memos_impl(raw_read_report)


def _turn_requires_grounded_delivery(user_input: str, recent_context: str = ""):
    return _turn_requires_grounded_delivery_impl(
        user_input,
        recent_context,
        answer_mode_policy_for_turn=_answer_mode_policy_for_turn,
    )


def _answer_mode_policy_for_turn(
    user_input: str,
    recent_context: str = "",
    goal_contract: dict | None = None,
):
    return _answer_mode_policy_for_turn_impl(
        user_input,
        recent_context,
        goal_contract,
        is_memory_state_disclosure_turn=is_memory_state_disclosure_turn,
        looks_like_current_turn_memory_story_share=_looks_like_current_turn_memory_story_share,
        looks_like_memo_recall_turn=looks_like_memo_recall_turn,
        extract_explicit_search_keyword=_extract_explicit_search_keyword,
        extract_artifact_hint=_extract_artifact_hint,
        is_recent_dialogue_review_turn=_is_recent_dialogue_review_turn,
        is_assistant_investigation_request_turn=_is_assistant_investigation_request_turn,
    )


def _answer_mode_policy_from_state(state: dict | None, analysis_data: dict | None = None):
    return _answer_mode_policy_from_state_impl(
        state,
        analysis_data,
        answer_mode_policy_for_turn=_answer_mode_policy_for_turn,
    )




def _answer_mode_policy_allows_direct_phase3(policy: dict | None):
    return _answer_mode_policy_allows_direct_phase3_impl(policy)


def _response_strategy_from_answer_mode_policy(
    user_input: str,
    policy: dict | None,
    current_turn_facts: list[str] | None = None,
):
    return _response_strategy_from_answer_mode_policy_impl(
        user_input,
        policy,
        current_turn_facts,
    )


def _turn_allows_parametric_knowledge_blend(user_input: str, recent_context: str = ""):
    return _turn_allows_parametric_knowledge_blend_impl(
        user_input,
        recent_context,
        answer_mode_policy_for_turn=_answer_mode_policy_for_turn,
    )


def _extract_current_turn_grounding_facts(user_input: str, contract: dict | None = None):
    return _extract_current_turn_grounding_facts_impl(
        user_input,
        contract,
        is_memory_state_disclosure_turn=is_memory_state_disclosure_turn,
        looks_like_current_turn_memory_story_share=_looks_like_current_turn_memory_story_share,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _field_memo_answer_ready_for_phase3(raw_read_report: dict, analysis_data: dict, user_input: str):
    return _field_memo_answer_ready_for_phase3_impl(
        raw_read_report,
        analysis_data,
        user_input,
        build_field_memo_user_brief=_build_field_memo_user_brief,
        field_memo_packet_ready_for_delivery=_field_memo_packet_ready_for_delivery,
    )


def _field_memo_packet_ready_for_delivery(packet: dict, analysis_data: dict | None = None, user_input: str = ""):
    return _field_memo_packet_ready_for_delivery_impl(
        packet,
        analysis_data,
        user_input,
        derive_user_goal_contract=_derive_user_goal_contract,
        contract_satisfied_by_facts=_contract_satisfied_by_facts,
    )


def _recent_dialogue_ready_for_phase3(raw_read_report: dict, analysis_data: dict, user_input: str):
    return _recent_dialogue_ready_for_phase3_impl(
        raw_read_report,
        analysis_data,
        user_input,
        build_recent_dialogue_brief=_build_recent_dialogue_brief,
    )


def _grounded_source_ready_for_phase3(state: AnimaState, analysis_data: dict, user_input: str):
    return _grounded_source_ready_for_phase3_impl(
        state,
        analysis_data,
        user_input,
        field_memo_answer_ready_for_phase3=_field_memo_answer_ready_for_phase3,
        recent_dialogue_ready_for_phase3=_recent_dialogue_ready_for_phase3,
        analysis_has_answer_relevant_evidence=_analysis_has_answer_relevant_evidence,
        operation_plan_from_state=_operation_plan_from_state,
    )


def _guard_phase3_decision_for_grounded_turn(
    state: AnimaState,
    decision: dict,
    strategist_output: dict,
    analysis_data: dict,
    working_memory: dict,
    loop_count: int,
    reasoning_budget: int,
    response_strategy: dict | None = None,
):
    return _guard_phase3_decision_for_grounded_turn_impl(
        state,
        decision,
        strategist_output,
        analysis_data,
        working_memory,
        loop_count,
        reasoning_budget,
        response_strategy=response_strategy,
        answer_mode_policy_from_state=_answer_mode_policy_from_state,
        short_term_context_strategy_is_usable=_short_term_context_strategy_is_usable,
        phase3_delivery_payload_ready_for_gate=_phase3_delivery_payload_ready_for_gate,
        war_room_output_is_usable=_war_room_output_is_usable,
        war_room_seed_alignment_issue=_war_room_seed_alignment_issue,
        soft_reasoning_budget_limit=_soft_reasoning_budget_limit,
        decision_from_strategist_tool_contract=_decision_from_strategist_tool_contract,
        start_gate_requests_memory_recall=_start_gate_requests_memory_recall,
        compiled_memory_recall_queries=_compiled_memory_recall_queries,
        tool_carryover_from_state=_tool_carryover_from_state,
        make_auditor_decision=_make_auditor_decision,
        gemini_scroll_candidate_from_state=_gemini_scroll_candidate_from_state,
        logger=print,
    )


def _build_findings_first_packet(user_input: str, judge_speaker_packet: dict):
    return _build_findings_first_packet_impl(
        user_input,
        judge_speaker_packet,
        format_findings_first_delivery=_format_findings_first_delivery,
    )


def _build_warroom_answer_seed_packet(state: AnimaState):
    return _build_warroom_answer_seed_packet_impl(
        state,
        looks_like_generic_non_answer_text=_looks_like_generic_non_answer_text,
    )


def _build_grounded_source_findings_packet(raw_read_report: dict, analysis_data: dict, user_input: str):
    return _build_grounded_source_findings_packet_impl(
        raw_read_report,
        analysis_data,
        user_input,
        analysis_has_answer_relevant_evidence=_analysis_has_answer_relevant_evidence,
        grounded_findings_from_analysis=_grounded_findings_from_analysis,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _build_phase3_lane_delivery_packet(state: AnimaState, judge_speaker_packet: dict):
    return _build_phase3_lane_delivery_packet_impl(
        state,
        judge_speaker_packet,
        operation_plan_from_state=_operation_plan_from_state,
        build_recent_dialogue_brief=_build_recent_dialogue_brief,
        build_field_memo_user_brief=_build_field_memo_user_brief,
        build_warroom_answer_seed_packet=_build_warroom_answer_seed_packet,
        strategy_needs_post_read_synthesis=_strategy_needs_post_read_synthesis,
        build_findings_first_packet=_build_findings_first_packet,
        analysis_has_grounded_artifact_evidence=_analysis_has_grounded_artifact_evidence,
        build_grounded_source_findings_packet=_build_grounded_source_findings_packet,
    )


def _phase3_payload_accepted_facts_from_packet(packet: dict):
    return _phase3_payload_accepted_facts_from_packet_impl(
        packet,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _clean_failure_missing_items(raw_slots: list[str] | None):
    return _clean_failure_missing_items_impl(raw_slots)


def _build_clean_failure_packet(
    state: AnimaState,
    analysis_data: dict,
    raw_read_report: dict,
    operation_plan: dict,
    user_goal: str,
    missing_slots: list[str] | None = None,
    rejected_sources: list[dict] | None = None,
):
    return _build_clean_failure_packet_impl(
        state,
        analysis_data,
        raw_read_report,
        operation_plan,
        user_goal,
        missing_slots=missing_slots,
        rejected_sources=rejected_sources,
        analysis_has_answer_relevant_evidence=_analysis_has_answer_relevant_evidence,
        analysis_reports_relevance_gap=_analysis_reports_relevance_gap,
        compact_user_facing_summary=_compact_user_facing_summary,
        normalize_short_string_list=_normalize_short_string_list,
        grounded_findings_from_analysis=_grounded_findings_from_analysis,
    )


def _build_phase3_delivery_payload(
    state: AnimaState,
    judge_speaker_packet: dict,
    phase3_delivery_packet: dict,
):
    return _build_phase3_delivery_payload_impl(
        state,
        judge_speaker_packet,
        phase3_delivery_packet,
        operation_plan_from_state=_operation_plan_from_state,
        normalize_goal_lock=_normalize_goal_lock,
        compact_user_facing_summary=_compact_user_facing_summary,
        derive_user_goal_contract=_derive_user_goal_contract,
        answer_mode_policy_for_turn=_answer_mode_policy_for_turn,
        extract_current_turn_grounding_facts=_extract_current_turn_grounding_facts,
        contract_satisfied_by_facts=_contract_satisfied_by_facts,
        turn_allows_parametric_knowledge_blend=_turn_allows_parametric_knowledge_blend,
        field_memo_packet_ready_for_delivery=_field_memo_packet_ready_for_delivery,
        has_meaningful_delivery_seed=_has_meaningful_delivery_seed,
        build_clean_failure_packet=_build_clean_failure_packet,
    )


def _verbalize_field_memo_delivery_seed(delivery_payload: dict):
    return _verbalize_field_memo_delivery_seed_impl(
        delivery_payload,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _verbalize_grounded_delivery_seed(delivery_payload: dict):
    return _verbalize_grounded_delivery_seed_impl(
        delivery_payload,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _build_phase3_speaker_judge_contract(
    state: AnimaState,
    delivery_payload: dict,
    phase3_recent_context: str = "",
    delivery_freedom_mode: str = "",
    grounded_mode: bool = False,
    supervisor_memo: str = "",
):
    return _build_phase3_speaker_judge_contract_impl(
        state,
        delivery_payload,
        phase3_recent_context=phase3_recent_context,
        delivery_freedom_mode=delivery_freedom_mode,
        grounded_mode=grounded_mode,
        supervisor_memo=supervisor_memo,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _phase3_delivery_payload_for_gate(
    state: AnimaState,
    strategist_output: dict,
    analysis_data: dict,
):
    return _phase3_delivery_payload_for_gate_impl(
        state,
        strategist_output,
        analysis_data,
        phase3_reference_policy=_phase3_reference_policy,
        build_judge_speaker_packet=_build_judge_speaker_packet,
        build_phase3_lane_delivery_packet=_build_phase3_lane_delivery_packet,
        build_phase3_delivery_payload=_build_phase3_delivery_payload,
    )


def _phase3_delivery_payload_ready_for_gate(
    state: AnimaState,
    strategist_output: dict,
    analysis_data: dict,
):
    return _phase3_delivery_payload_ready_for_gate_impl(
        state,
        strategist_output,
        analysis_data,
        phase3_delivery_payload_for_gate=_phase3_delivery_payload_for_gate,
    )


def _format_recent_dialogue_self_critique(phase3_delivery_packet: dict):
    packet = phase3_delivery_packet if isinstance(phase3_delivery_packet, dict) else {}
    recent = packet.get("recent_dialogue_brief", {})
    if not isinstance(recent, dict):
        return ""
    turns = recent.get("recent_turns", [])
    if not isinstance(turns, list) or len(turns) < 2:
        return ""

    assistant_turns = [
        str(turn.get("content") or "").strip()
        for turn in turns
        if isinstance(turn, dict) and str(turn.get("role") or "").strip().lower() == "assistant" and str(turn.get("content") or "").strip()
    ]
    user_turns = [
        str(turn.get("content") or "").strip()
        for turn in turns
        if isinstance(turn, dict) and str(turn.get("role") or "").strip().lower() == "user" and str(turn.get("content") or "").strip()
    ]
    repeated_assistant = False
    if len(assistant_turns) >= 2:
        compact = [re.sub(r"\s+", "", item) for item in assistant_turns[-3:]]
        repeated_assistant = len(set(compact)) < len(compact)
    short_acceptance_seen = any(
        re.sub(r"[\s!~.]+", "", unicodedata.normalize("NFKC", item).lower())
        in {"ok", "yes", "y", "\u110b\u110b", "\u1100\u1100", "\uc88b\uc544", "\uadf8\ub798", "\ud574\uc918", "\uc9c4\ud589"}
        for item in user_turns[-4:]
    )

    lines = ["Recent dialogue suggests the assistant missed the intended continuation."]
    if repeated_assistant or short_acceptance_seen:
        lines.append(
            "The user likely accepted or requested execution of the previous offer, but the assistant treated it as a new clarification."
        )
    else:
        lines.append(
            "The assistant did not separate recent context from the required final action clearly enough."
        )
    if assistant_turns:
        lines.append(f"Last assistant reply was '{_compact_user_facing_summary(assistant_turns[-1], 140)}'; check for repetition before answering.")
    lines.append(
        "Structurally, recent-dialogue review was over-weighted while the actual output act was not preserved."
    )
    lines.append(
        "Repair instruction: do not copy the recent-dialogue brief; admit the miss, state why, and answer the current correction."
    )
    return "\n".join(lines).strip()


def _phase3_reference_policy_packet(policy: dict):
    if not isinstance(policy, dict) or not policy:
        return "No phase_3 reference policy is available."
    packet = {
        "mode": policy.get("mode", "none"),
        "char_count": policy.get("char_count", 0),
        "followup_strength": policy.get("followup_strength", "gentle"),
        "followup_instruction": policy.get("followup_instruction", ""),
        "note": policy.get("note", ""),
    }
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)



def _normalize_delivery_freedom_mode(mode: str, reply_mode: str = ""):
    normalized_mode = str(mode or "").strip()
    if normalized_mode == "answer_not_ready":
        return "clean_failure"
    if normalized_mode in {"grounded", "supportive_free", "proposal", "identity_direct", "clean_failure"}:
        return normalized_mode

    normalized_reply_mode = str(reply_mode or "").strip()
    if normalized_reply_mode in {"continue_previous_offer", "ask_user_question_now"}:
        return "proposal"
    if normalized_reply_mode == "casual_reaction":
        return "supportive_free"
    if normalized_reply_mode == "cautious_minimal":
        return "clean_failure"
    return "grounded"


def _grounded_findings_from_analysis(analysis_data: dict | None, limit: int = 3):
    if not isinstance(analysis_data, dict):
        return []
    facts = []
    evidences = analysis_data.get("evidences", [])
    if isinstance(evidences, list):
        for item in evidences:
            if not isinstance(item, dict):
                continue
            fact = str(item.get("extracted_fact") or "").strip()
            if fact:
                facts.append(fact)
    if not facts:
        source_judgments = analysis_data.get("source_judgments", [])
        if isinstance(source_judgments, list):
            for judgment in source_judgments:
                if not isinstance(judgment, dict):
                    continue
                for fact in judgment.get("accepted_facts", []):
                    normalized = str(fact or "").strip()
                    if normalized:
                        facts.append(normalized)
    return _normalize_short_string_list(facts, limit=limit)


def _analysis_reports_relevance_gap(analysis_data: dict | None):
    if not isinstance(analysis_data, dict):
        return False
    text_parts = [
        str(analysis_data.get("situational_brief") or ""),
        str(analysis_data.get("analytical_thought") or ""),
    ]
    for judgment in analysis_data.get("source_judgments", []) or []:
        if not isinstance(judgment, dict):
            continue
        text_parts.append(str(judgment.get("objection_reason") or ""))
        text_parts.extend(str(item or "") for item in judgment.get("missing_info", []) or [])
    normalized = unicodedata.normalize("NFKC", " ".join(text_parts)).lower()
    gap_markers = [
        "\uc9c1\uc811\uc801\uc778 \ub2f5\ubcc0\uc744 \uc81c\uacf5\ud558\uc9c0",
        "\uc9c1\uc811\uc801\uc778 \ub2f5\ubcc0\uc744 \uc8fc\uc9c0",
        "\uad00\ub828 \ub0b4\uc6a9\uc5d0 \ub300\ud55c \uc9c1\uc811\uc801\uc778",
        "\uad00\ub828 \ub0b4\uc6a9\uc774 \uc5c6",
        "\uad00\ub828\uc774 \uc5c6",
        "\ubb34\uad00",
        "\ucd94\uac00\uc801\uc778 \uc815\ubcf4\uac00 \ud544\uc694",
        "\ucd94\uac00 \uc815\ubcf4\uac00 \ud544\uc694",
        "\uad6c\uccb4\uc801\uc778 \uc815\ubcf4\ub294 \uc5c6",
        "\uad6c\uccb4\uc801\uc778 \ub2f5\ubcc0\uc740 \uc5c6",
        "\ucc3e\uc744 \uc218 \uc5c6",
        "\ud30c\uc545\ub418\uc9c0 \uc54a",
        "\ud655\uc778\ub418\uc9c0 \uc54a",
        "does not provide a direct answer",
        "not directly answer",
        "not relevant",
        "unrelated",
        "insufficient",
    ]
    return any(marker in normalized for marker in gap_markers)


def _analysis_has_answer_relevant_evidence(analysis_data: dict | None):
    if not isinstance(analysis_data, dict) or not analysis_data:
        return False
    usable_field_memo_facts = [
        str(fact).strip()
        for fact in analysis_data.get("usable_field_memo_facts", []) or []
        if str(fact).strip()
    ]
    if (
        bool(analysis_data.get("can_answer_user_goal"))
        and usable_field_memo_facts
        and str(analysis_data.get("contract_status") or "satisfied").strip() in {"", "satisfied"}
        and not analysis_data.get("missing_slots")
    ):
        return True
    status = str(analysis_data.get("investigation_status") or "").upper()
    if status != "COMPLETED":
        return False
    if _analysis_reports_relevance_gap(analysis_data):
        return False

    judgments = analysis_data.get("source_judgments", [])
    if isinstance(judgments, list) and judgments:
        for judgment in judgments:
            if not isinstance(judgment, dict):
                continue
            source_status = str(judgment.get("source_status") or "").strip().lower()
            accepted = [
                str(item or "").strip()
                for item in judgment.get("accepted_facts", []) or []
                if str(item or "").strip()
            ]
            if source_status == "pass" and accepted:
                return True
        if any(isinstance(judgment, dict) and str(judgment.get("search_needed") or "").lower() == "true" for judgment in judgments):
            return False

    return bool(_grounded_findings_from_analysis(analysis_data))


def _derive_goal_lock(user_input: str, start_gate_review: dict | None = None):
    return _derive_goal_lock_v2(user_input, start_gate_review)


def _derive_goal_lock_v2(user_input: str, start_gate_review: dict | None = None):
    text = str(user_input or "").strip()
    start_gate_review = start_gate_review if isinstance(start_gate_review, dict) else {}
    answer_shape = "direct_answer"
    must_not_expand_to = ["generic_nonanswer", "topic_drift"]
    goal_contract = _derive_user_goal_contract(text, source_lane="direct_dialogue")
    output_act = str(goal_contract.get("output_act") or "").strip()
    if output_act == "answer_identity_slot":
        answer_shape = "identity_short"
    elif output_act == "answer_memory_recall":
        answer_shape = "findings_first"
        must_not_expand_to = ["generic_nonanswer", "ask_user_to_search_again", "topic_drift"]
    elif str(start_gate_review.get("answerability") or "").strip() == "direct_now":
        answer_shape = "direct_answer"

    user_goal_core = _normalized_goal_from_contract(goal_contract, text)
    if is_memory_state_disclosure_turn(text):
        answer_shape = "memory_state_ack"
        must_not_expand_to = ["memory_retrieval", "tool_search", "clean_failure", "topic_drift"]

    return _normalize_goal_lock({
        "user_goal_core": user_goal_core,
        "answer_shape": answer_shape,
        "must_not_expand_to": must_not_expand_to,
    })


def _normalized_goal_from_contract(goal_contract: dict | None, user_input: str = ""):
    contract = goal_contract if isinstance(goal_contract, dict) else {}
    text = str(user_input or "").strip()
    slot = str(contract.get("slot_to_fill") or "").strip()
    output_act = str(contract.get("output_act") or "").strip()

    if is_memory_state_disclosure_turn(text):
        return "Acknowledge the user's memory reset disclosure and orient to the new start."
    if slot == "user.canonical_name":
        return "Answer the user's canonical name from grounded identity evidence."
    if slot == "memory.referent_fact":
        return "Recover the concrete remembered situation or event being referenced."
    if slot == "character.identity":
        return "Identify the requested character directly."
    if slot == "character.fictionality":
        return "State whether the requested character is fictional or real."
    if slot == "character.relationship":
        return "Explain the requested relationship between the named characters or concepts."
    if slot == "story.narrative_fact":
        return "Answer the requested story or character fact directly."
    if output_act == "answer_narrative_fact":
        return "Answer the public story or character question directly without forcing private-memory retrieval."
    if output_act == "self_analysis_snapshot":
        return "Give a bounded conversation-based self-analysis snapshot."
    if output_act == "diagnose_system":
        return "Diagnose the reported system behavior and state the concrete fix."
    return "Answer the current turn without broadening the goal."


def _goal_locked_delivery_step_goal(goal_lock: dict | None):
    normalized = _normalize_goal_lock(goal_lock if isinstance(goal_lock, dict) else {})
    shape = normalized.get("answer_shape", "direct_answer")
    if shape == "proposal_1_to_3":
        return "Turn the grounded findings into 1-3 concrete things we can do today."
    if shape == "fit_summary":
        return "Summarize which grounded ANIMA capabilities fit the current plan right now."
    if shape == "feature_summary":
        return "Summarize the grounded capabilities first without drifting into unrequested expansion."
    if shape == "identity_short":
        return "Answer the identity question directly and briefly."
    if shape == "capability_boundary":
        return "Explain clearly what kind of analysis is possible right now, what remains limited, and what we can analyze immediately."
    if shape == "self_analysis_snapshot":
        return "Give a bounded conversation-based snapshot of what kind of person the user seems to be right now."
    if shape == "findings_first":
        return "Deliver the grounded findings first before opening any new search frontier."
    if shape == "memory_state_ack":
        return "Acknowledge the memory reset disclosure and orient naturally to the new start."
    return "Prepare a direct answer from the current contract and available facts."


def _goal_locked_gathering_step_goal(goal_lock: dict | None):
    normalized = _normalize_goal_lock(goal_lock if isinstance(goal_lock, dict) else {})
    shape = normalized.get("answer_shape", "direct_answer")
    user_goal = str(normalized.get("user_goal_core") or "").strip()
    if shape == "proposal_1_to_3":
        return "Read one stronger grounded source so we can recommend 1-3 concrete things we can do today."
    if shape == "fit_summary":
        return "Read one stronger grounded source so we can summarize which capabilities fit the current goal."
    if shape == "feature_summary":
        return "Read one stronger grounded source so we can summarize the relevant capabilities directly."
    if shape == "capability_boundary":
        return "Read one stronger grounded source so we can explain the current analysis boundary and what kind of self-analysis is possible now."
    if shape == "self_analysis_snapshot":
        return "Review the recent dialogue and working memory so we can extract 2-4 grounded observations about the user's visible conversation patterns."
    if shape == "findings_first":
        return "Read one stronger grounded source so we can extract the findings that matter most to the current ask."
    if shape == "memory_state_ack":
        return "No source read is needed; acknowledge the memory reset disclosure and continue from the current turn."
    if user_goal:
        return "Decide whether one source read is needed for the strategist goal."
    return "Plan the next evidence step only if the current contract requires it."


def _tool_candidate_step_goal(goal_lock: dict | None, tool_candidate: dict | None):
    tool_candidate = tool_candidate if isinstance(tool_candidate, dict) else {}
    tool_name = str(tool_candidate.get("tool_name") or "").strip()
    if not tool_name:
        return _goal_locked_gathering_step_goal(goal_lock)
    return f"Execute the selected {tool_name} call once, then let phase 2b judge whether it satisfies the strategist goal."


def _goal_locked_delivery_strategy(
    response_strategy: dict,
    analysis_data: dict,
    user_input: str,
    goal_lock: dict | None = None,
    facts: list | None = None,
):
    normalized = json.loads(json.dumps(response_strategy if isinstance(response_strategy, dict) else {}, ensure_ascii=False))
    grounded_facts = _normalize_short_string_list(facts if isinstance(facts, list) else _grounded_findings_from_analysis(analysis_data), limit=3)
    if not grounded_facts:
        return normalized

    goal_lock = _normalize_goal_lock(goal_lock if isinstance(goal_lock, dict) else _derive_goal_lock_v2(user_input, {}))
    answer_shape = goal_lock.get("answer_shape", "direct_answer")
    normalized["reply_mode"] = "grounded_answer"
    normalized["evidence_brief"] = " / ".join(grounded_facts)
    normalized["reasoning_brief"] = "Keep the answer anchored to the grounded findings and stay inside the user goal."
    normalized["must_include_facts"] = grounded_facts

    if answer_shape == "proposal_1_to_3":
        normalized["delivery_freedom_mode"] = "proposal"
        normalized["answer_goal"] = "Use the grounded findings to propose 1-3 concrete things we can do today."
        normalized["direct_answer_seed"] = "Based on the grounded material, here are the concrete things we can do today."
        normalized["answer_outline"] = [
            "Summarize the grounded capability fit first.",
            "Propose 1-3 concrete next actions for today.",
            "Add only one narrow follow-up if it truly helps.",
        ]
    elif answer_shape == "capability_boundary":
        normalized["delivery_freedom_mode"] = "grounded"
        normalized["answer_goal"] = "Explain clearly what kind of self-analysis is possible now, what remains limited, and what we can do immediately."
        normalized["direct_answer_seed"] = "With the current evidence, I can give a bounded pattern read, not a deep diagnosis."
        normalized["answer_outline"] = [
            "State the possible analysis boundary first.",
            "Name the current limitations without exaggerating.",
            "Suggest one or two immediately useful next analysis steps.",
        ]
    elif answer_shape == "self_analysis_snapshot":
        normalized["delivery_freedom_mode"] = "grounded"
        normalized["answer_goal"] = "Give a bounded, conversation-based snapshot of the user's visible patterns right now."
        normalized["direct_answer_seed"] = "From this conversation alone, a few patterns are visible."
        normalized["answer_outline"] = [
            "Start by saying this is a conversation-based read, not a deep diagnosis.",
            "Name 2-4 grounded patterns visible in the dialogue.",
            "Close with one short note about what would make the read deeper or more reliable.",
        ]
    elif answer_shape in {"fit_summary", "feature_summary"}:
        normalized["delivery_freedom_mode"] = "grounded"
        normalized["answer_goal"] = "Summarize which grounded capabilities fit the current user goal."
        normalized["direct_answer_seed"] = "Based on the grounded material, the capabilities that fit this goal are:"
        normalized["answer_outline"] = [
            "Name the grounded capabilities first.",
            "Explain briefly why they fit the user's stated goal.",
            "Avoid drifting into unrelated ethics or research unless asked.",
        ]
    elif answer_shape == "identity_short":
        normalized["delivery_freedom_mode"] = "grounded"
        normalized["answer_goal"] = "Answer identity-related questions from approved context or grounded facts."
        normalized["direct_answer_seed"] = ""
    else:
        normalized["delivery_freedom_mode"] = "grounded"
        normalized["answer_goal"] = "Deliver the grounded findings directly."
        normalized["direct_answer_seed"] = ""
        normalized["answer_outline"] = [
            "State the grounded findings first.",
            "Keep the answer inside the user's actual ask.",
        ]

    must_avoid = normalized.get("must_avoid_claims", [])
    if not isinstance(must_avoid, list):
        must_avoid = []
    must_avoid.extend(goal_lock.get("must_not_expand_to", []))
    normalized["must_avoid_claims"] = _normalize_short_string_list(must_avoid, limit=8)
    return normalized


def _goal_lock_requires_converged_delivery(
    goal_lock: dict | None,
    analysis_data: dict,
    grounded_facts: list | None = None,
):
    normalized = _normalize_goal_lock(goal_lock if isinstance(goal_lock, dict) else {})
    answer_shape = str(normalized.get("answer_shape") or "").strip()
    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    facts = _normalize_short_string_list(
        grounded_facts if isinstance(grounded_facts, list) else _grounded_findings_from_analysis(analysis_data),
        limit=3,
    )
    if status != "COMPLETED" or not facts:
        return False
    return answer_shape in {"proposal_1_to_3", "fit_summary", "feature_summary", "findings_first", "capability_boundary", "self_analysis_snapshot"}


def _goal_lock_prefers_delivery_on_completed_findings(goal_lock: dict | None):
    normalized = _normalize_goal_lock(goal_lock if isinstance(goal_lock, dict) else {})
    answer_shape = str(normalized.get("answer_shape") or "").strip()
    return answer_shape in {"proposal_1_to_3", "fit_summary", "feature_summary", "findings_first", "capability_boundary", "self_analysis_snapshot"}


def _strategy_needs_post_read_synthesis(strategist_output: dict | None, analysis_data: dict | None):
    strategist_output = strategist_output if isinstance(strategist_output, dict) else {}
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    if str(analysis_data.get("investigation_status") or "").upper() != "COMPLETED":
        return False
    operation_plan = strategist_output.get("operation_plan", {})
    if not isinstance(operation_plan, dict):
        operation_plan = {}
    output_act = str(operation_plan.get("output_act") or "").strip()
    if output_act in {"deliver_findings", "summarize"}:
        return False
    goal_lock = _normalize_goal_lock(strategist_output.get("goal_lock", {}))
    shape = str(goal_lock.get("answer_shape") or "").strip()
    return shape in {"self_analysis_snapshot", "fit_summary", "feature_summary", "capability_boundary"}


def _strategy_synthesis_is_satisfied(strategist_output: dict | None, analysis_data: dict | None):
    if not _strategy_needs_post_read_synthesis(strategist_output, analysis_data):
        return True
    strategist_output = strategist_output if isinstance(strategist_output, dict) else {}
    goal_lock = _normalize_goal_lock(strategist_output.get("goal_lock", {}))
    response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    user_goal = str(goal_lock.get("user_goal_core") or "").strip()
    if not _has_usable_response_seed(response_strategy, user_goal):
        return False

    seed = " ".join([
        str(response_strategy.get("direct_answer_seed") or ""),
        str(response_strategy.get("reasoning_brief") or ""),
        str(response_strategy.get("evidence_brief") or ""),
    ])
    normalized_seed = unicodedata.normalize("NFKC", seed).lower()
    clean_satisfied_markers = [
        "\uadf8\ub798\uc11c",
        "\ubc14\ud0d5\uc73c\ub85c",
        "\uae30\ubc18\uc73c\ub85c",
        "\uc758\ubbf8",
        "\ud574\uc11d",
        "\uc0dd\uac01",
        "\uc774\ud574",
        "\uc815\uccb4\uc131",
        "\uc1a1\ub828",
        "\uc544\ub2c8\ub9c8",
        "\ud504\ub85c\ud1a0\ud0c0\uc785",
        "anima",
        "agent",
        "prototype",
    ]
    if any(marker in normalized_seed for marker in clean_satisfied_markers):
        return True
    synthesis_markers = ["based on", "meaning", "interpret", "think", "identity", "anima", "agent"]
    return any(marker in normalized_seed for marker in synthesis_markers)


def _lens_candidates_from_goal_lock(goal_lock: dict | None):
    normalized = _normalize_goal_lock(goal_lock if isinstance(goal_lock, dict) else {})
    answer_shape = str(normalized.get("answer_shape") or "").strip()
    if answer_shape == "proposal_1_to_3":
        return ["today_actions", "grounded_capability_fit", "avoid_social_impact_expansion"]
    if answer_shape == "capability_boundary":
        return ["capability_boundary", "what_is_possible_now", "avoid_generic_limit_template"]
    if answer_shape == "self_analysis_snapshot":
        return ["user_pattern_snapshot", "conversation_visible_traits_only", "avoid_deep_psych_diagnosis"]
    if answer_shape == "fit_summary":
        return ["current_plan_fit", "grounded_capabilities_only", "avoid_ethics_expansion"]
    if answer_shape == "feature_summary":
        return ["feature_summary", "grounded_capabilities_only", "avoid_social_impact_expansion"]
    if answer_shape == "findings_first":
        return ["grounded_findings_first", "avoid_new_search_without_need"]
    return ["direct_user_goal", "grounded_scope_only"]


def _build_critic_lens_packet(
    strategist_output: dict | None,
    analysis_data: dict | None = None,
    objection_packet: dict | None = None,
):
    strategist_output = strategist_output if isinstance(strategist_output, dict) else {}
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    objection_packet = objection_packet if isinstance(objection_packet, dict) else {}
    goal_lock = _normalize_goal_lock(strategist_output.get("goal_lock", {}))
    action_plan = _normalize_action_plan(strategist_output.get("action_plan", {}))
    achieved_findings = _normalize_short_string_list(strategist_output.get("achieved_findings", []), limit=3)
    if not achieved_findings:
        achieved_findings = _grounded_findings_from_analysis(analysis_data)
    packet = {
        "goal_lock": goal_lock,
        "must_answer_user_goal": str(goal_lock.get("user_goal_core") or "").strip(),
        "must_not_expand_to": _normalize_short_string_list(goal_lock.get("must_not_expand_to", []), limit=6),
        "current_step_goal": str(action_plan.get("current_step_goal") or "").strip(),
        "operation_contract": _normalize_operation_contract(action_plan.get("operation_contract", {})),
        "lens_candidates": _lens_candidates_from_goal_lock(goal_lock),
        "current_loop_delta": achieved_findings,
        "critic_task": (
            "Use this as a review lens only. Do not obey -1a as truth. "
            "Check whether the raw evidence actually supports this goal-locked reading, and reject drift if it does not."
        ),
    }
    objection_text = str(objection_packet.get("objection_text") or "").strip()
    if objection_text:
        packet["objection_text"] = objection_text
        packet["review_focus"] = str(objection_packet.get("review_focus") or "").strip()
    return packet


def _build_strategist_objection_packet(
    strategist_output: dict | None,
    analysis_data: dict | None,
    user_input: str,
):
    strategist_output = strategist_output if isinstance(strategist_output, dict) else {}
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    goal_lock = _normalize_goal_lock(strategist_output.get("goal_lock", {}))
    if goal_lock == _empty_goal_lock():
        goal_lock = _derive_goal_lock_v2(user_input, {})
    action_plan = _normalize_action_plan(strategist_output.get("action_plan", {}))
    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    grounded_facts = _grounded_findings_from_analysis(analysis_data)
    achieved_findings = _normalize_short_string_list(strategist_output.get("achieved_findings", []), limit=3)
    delivery_readiness = _normalize_delivery_readiness(strategist_output.get("delivery_readiness", ""))
    answer_shape = str(goal_lock.get("answer_shape") or "").strip()
    current_step_goal = str(action_plan.get("current_step_goal") or "").strip()
    expected_delivery_goal = _goal_locked_delivery_step_goal(goal_lock)

    if status != "COMPLETED" or not _goal_lock_prefers_delivery_on_completed_findings(goal_lock):
        return {}

    if _strategy_needs_post_read_synthesis(strategist_output, analysis_data) and not _strategy_synthesis_is_satisfied(strategist_output, analysis_data):
        return {}

    if grounded_facts and not achieved_findings:
        return {
            "has_objection": True,
            "suspected_owner": "phase_2b",
            "objection_text": "Grounded facts exist, but the current analysis did not surface deliverable findings cleanly enough for the strategist.",
            "review_focus": f"Re-check the evidence through the `{answer_shape}` lens and extract grounded findings that answer the user goal directly.",
        }

    if achieved_findings and (delivery_readiness != "deliver_now" or action_plan.get("required_tool")):
        return {
            "has_objection": True,
            "suspected_owner": "-1a",
            "objection_text": "The strategist kept planning even though grounded findings already support a goal-locked delivery.",
            "review_focus": f"Stop expansion and deliver using the `{answer_shape}` shape now.",
        }

    if achieved_findings and current_step_goal and current_step_goal != expected_delivery_goal:
        return {
            "has_objection": True,
            "suspected_owner": "-1a",
            "objection_text": "The current strategist step goal drifted away from the user goal after grounded findings were already available.",
            "review_focus": f"Replace the drifted step goal with a `{answer_shape}` delivery goal.",
        }

    return {}


def _ensure_strategist_continuity_fields(
    strategist_payload: dict,
    user_input: str,
    analysis_data: dict,
    start_gate_review: dict | None = None,
):
    if not isinstance(strategist_payload, dict):
        strategist_payload = {}
    normalized = json.loads(json.dumps(strategist_payload, ensure_ascii=False))
    action_plan = _normalize_action_plan(normalized.get("action_plan", {}))
    response_strategy = normalized.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}

    goal_lock = _normalize_goal_lock(normalized.get("goal_lock", {}))
    if goal_lock == _empty_goal_lock():
        goal_lock = _derive_goal_lock_v2(user_input, start_gate_review)

    grounded_facts = _grounded_findings_from_analysis(analysis_data)
    achieved_findings = _normalize_short_string_list(normalized.get("achieved_findings", []), limit=3)
    if not achieved_findings:
        achieved_findings = grounded_facts
    needs_post_read_synthesis = _strategy_needs_post_read_synthesis(normalized, analysis_data)
    synthesis_satisfied = _strategy_synthesis_is_satisfied(normalized, analysis_data)

    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    convergence_state = _normalize_convergence_state(normalized.get("convergence_state", ""))
    if normalized.get("convergence_state") in {None, ""}:
        if _has_meaningful_strategy(response_strategy) or (status == "COMPLETED" and achieved_findings and not needs_post_read_synthesis):
            convergence_state = "deliverable"
        elif achieved_findings:
            convergence_state = "synthesizing"
        elif status in {"INCOMPLETE", "EXPANSION_REQUIRED"}:
            convergence_state = "gathering"

    delivery_readiness = _normalize_delivery_readiness(normalized.get("delivery_readiness", ""))
    if normalized.get("delivery_readiness") in {None, ""}:
        if _has_meaningful_strategy(response_strategy) or (status == "COMPLETED" and achieved_findings and not needs_post_read_synthesis):
            delivery_readiness = "deliver_now"
        elif action_plan.get("required_tool"):
            delivery_readiness = "need_one_more_source"
        elif action_plan.get("operation_contract", {}).get("operation_kind") == "read_same_source_deeper":
            delivery_readiness = "need_targeted_deeper_read"
        else:
            delivery_readiness = "need_reframe"

    next_frontier = _normalize_short_string_list(normalized.get("next_frontier", []), limit=3)
    if not next_frontier:
        next_frontier = _normalize_short_string_list(action_plan.get("next_steps_forecast", []), limit=3)

    force_goal_locked_delivery = _goal_lock_requires_converged_delivery(
        goal_lock,
        analysis_data,
        grounded_facts,
    ) and not needs_post_read_synthesis
    if force_goal_locked_delivery:
        convergence_state = "deliverable"
        delivery_readiness = "deliver_now"
        achieved_findings = grounded_facts or achieved_findings
        action_plan["required_tool"] = ""
        action_plan["current_step_goal"] = _goal_locked_delivery_step_goal(goal_lock)
        action_plan["next_steps_forecast"] = []
        next_frontier = []
        response_strategy = _goal_locked_delivery_strategy(
            response_strategy if isinstance(response_strategy, dict) else {},
            analysis_data,
            user_input,
            goal_lock=goal_lock,
            facts=achieved_findings,
        )

    if needs_post_read_synthesis and not synthesis_satisfied:
        convergence_state = "synthesizing"
        delivery_readiness = "need_reframe"
        action_plan["required_tool"] = ""
        if (
            not action_plan.get("current_step_goal")
            or action_plan.get("current_step_goal") == _goal_locked_delivery_step_goal(goal_lock)
        ):
            action_plan["current_step_goal"] = "Use the completed source read as material for synthesis/reflection before final delivery."
        if not next_frontier:
            next_frontier = [
                "Run WarRoom or rebuild the delivery contract so the answer interprets the read source against the user's actual goal.",
                "Separate source-reading completion from strategy satisfaction before phase_3.",
            ]

    if delivery_readiness == "deliver_now":
        action_plan["required_tool"] = ""
        if force_goal_locked_delivery or not action_plan.get("current_step_goal") or action_plan.get("current_step_goal", "").strip().lower().startswith("deliver the final answer"):
            action_plan["current_step_goal"] = _goal_locked_delivery_step_goal(goal_lock)
        response_strategy = _goal_locked_delivery_strategy(
            response_strategy if _has_meaningful_strategy(response_strategy) else _fallback_response_strategy(analysis_data),
            analysis_data,
            user_input,
            goal_lock=goal_lock,
            facts=achieved_findings,
        )

    normalized["goal_lock"] = goal_lock
    normalized["convergence_state"] = convergence_state
    normalized["achieved_findings"] = achieved_findings
    normalized["delivery_readiness"] = delivery_readiness
    normalized["next_frontier"] = next_frontier
    normalized["action_plan"] = action_plan
    normalized["response_strategy"] = response_strategy
    return normalized


def _dedupe_keep_order(items):
    seen = set()
    result = []
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result

def _infer_fact_kind(source_type: str, fact_text: str):
    text = str(fact_text or "")
    source = str(source_type or "").lower()
    if '"' in text or "'" in text:
        return "quote"
    if any(token in text for token in ["year", "month", "day", "date", ":"]):
        return "timeline"
    if any(token in source for token in ["chat", "diary", "record", "episode"]):
        return "event"
    return "other"

def _analysis_status_to_recommended_action(status: str):
    normalized = str(status or "").upper()
    if normalized == "COMPLETED":
        return "answer_now"
    if normalized == "EXPANSION_REQUIRED":
        return "search_more"
    return "insufficient_evidence"

def _empty_reasoning_board(turn_id: str = "", user_input: str = ""):
    return {
        "turn_id": str(turn_id or ""),
        "user_input": str(user_input or ""),
        "fact_cells": [],
        "candidate_pairs": [],
        "open_questions": [],
        "search_requests": [],
        "final_fact_ids": [],
        "final_pair_ids": [],
        "must_avoid_claims": [],
        "direct_answer_seed": "",
        "strategist_plan": {
            "case_theory": "",
            "operation_plan": _empty_operation_plan(),
            "action_plan": _empty_action_plan(),
            "goal_lock": _empty_goal_lock(),
            "convergence_state": "gathering",
            "achieved_findings": [],
            "delivery_readiness": "need_reframe",
            "next_frontier": [],
            "war_room_contract": _empty_war_room_operating_contract(),
        },
        "critic_report": _empty_critic_report(),
        "advocate_report": _empty_advocate_report(),
        "verdict_board": _empty_verdict_board(),
    }


def _is_warroom_deliberation_turn(user_input: str, recent_context: str = ""):
    del recent_context
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    if _extract_artifact_hint(text) or _extract_explicit_search_keyword(text):
        return False
    explicit_markers = ["warroom", "deliberate", "think deeply", "\uc219\uace0", "\ud1a0\ub860"]
    return any(marker in text for marker in explicit_markers)


def _is_listening_note_turn(user_input: str, recent_context: str = "", working_memory: dict | None = None):
    """The listening_note lane is retired.

    Story/listening turns should now use normal direct delivery plus FieldMemo
    persistence. Keeping this as a tiny false gate prevents old routing branches
    from reactivating the brittle one-shot listening template.
    """
    return False


def _is_self_critique_output_request(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    markers = ["self critique", "self-critique", "criticize yourself", "\uc790\uae30\ube44\ud310", "\ube44\ud310", "\ubc18\uc131"]
    return any(marker in text for marker in markers)


def _derive_source_lane_from_plan(user_input: str, plan_type: str, requested_move: str = "", required_tool: str = ""):
    del user_input, requested_move
    tool_text = str(required_tool or "").strip()
    if plan_type == "recent_dialogue_review":
        return "recent_dialogue_review"
    if "tool_scroll_chat_log" in tool_text:
        return "scroll_source"
    if "tool_read_artifact" in tool_text:
        return "artifact_read"
    if "tool_search_field_memos" in tool_text:
        return "field_memo_review"
    if "tool_search_memory" in tool_text:
        return "memory_search"
    if plan_type == "warroom_deliberation":
        return "warroom"
    return "none"



def _derive_output_act_from_turn(
    user_input: str,
    plan_type: str,
    requested_move: str = "",
    response_strategy: dict | None = None,
):
    del user_input, requested_move
    response_strategy = response_strategy if isinstance(response_strategy, dict) else {}
    reply_mode = str(response_strategy.get("reply_mode") or "").strip()
    if reply_mode == "ask_user_question_now":
        return "ask_one_question"
    if plan_type == "tool_evidence":
        return "deliver_findings"
    if plan_type == "recent_dialogue_review":
        return "summarize"
    if reply_mode == "continue_previous_offer":
        return "answer"
    return "answer"



def _derive_operation_plan(
    user_input: str,
    analysis_data: dict | None,
    action_plan: dict | None,
    response_strategy: dict | None,
    working_memory: dict | None = None,
    recent_context: str = "",
    start_gate_review: dict | None = None,
):
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    action_plan = _normalize_action_plan(action_plan if isinstance(action_plan, dict) else {})
    response_strategy = response_strategy if isinstance(response_strategy, dict) else {}
    working_memory = working_memory if isinstance(working_memory, dict) else {}
    start_gate_review = start_gate_review if isinstance(start_gate_review, dict) else {}

    required_tool = str(action_plan.get("required_tool") or "").strip()
    operation_contract = _normalize_operation_contract(action_plan.get("operation_contract", {}))
    operation_kind = str(operation_contract.get("operation_kind") or "").strip()
    reply_mode = str(response_strategy.get("reply_mode") or "").strip()
    delivery_mode = _normalize_delivery_freedom_mode(
        str(response_strategy.get("delivery_freedom_mode") or "").strip(),
        reply_mode=reply_mode,
    )

    del recent_context

    if "tool_search_field_memos" in required_tool or "tool_search_memory" in required_tool or operation_kind == "search_new_source":
        plan_type = "tool_evidence"
    elif (
        "tool_read_artifact" in required_tool
        or "tool_scroll_chat_log" in required_tool
        or "tool_read_full_diary" in required_tool
        or operation_kind in {"read_same_source_deeper", "review_personal_history"}
    ):
        plan_type = "raw_source_analysis"
    elif operation_kind == "deliver_now":
        plan_type = "direct_delivery"
    elif delivery_mode in {"supportive_free", "identity_direct"} or reply_mode in {"casual_reaction", "continue_previous_offer"}:
        plan_type = "direct_delivery"
    else:
        plan_type = "direct_delivery"

    source_lane = _derive_source_lane_from_plan(user_input, plan_type, required_tool=required_tool)
    output_act = _derive_output_act_from_turn(user_input, plan_type, response_strategy=response_strategy)

    goal_lock = _derive_goal_lock_v2(user_input, start_gate_review)
    user_goal = str(goal_lock.get("user_goal_core") or user_input or "").strip()
    if plan_type == "tool_evidence":
        evidence_policy = "Tool results are needed; do not finalize before reading them."
        executor_instruction = required_tool or "Run the concrete retrieval tool that matches the current request."
        success = ["The tool result is relevant to the current user question.", "Retrieved findings can be delivered in findings-first form."]
        rejection = ["Using unrelated search results as the answer.", "Deflecting the user back to search again."]
    elif plan_type == "recent_dialogue_review":
        evidence_policy = "Read recent raw dialogue and keep user/assistant roles separate."
        executor_instruction = "Review recent dialogue as source text and identify the intended continuation or correction."
        success = ["Uses concrete recent turns as evidence.", "Does not distort user and assistant roles."]
        rejection = ["Answers generically without recent raw dialogue.", "Treats user speech as assistant speech."]
    elif plan_type == "raw_source_analysis":
        evidence_policy = "Read raw diary/file/chat text and separate fact from interpretation."
        executor_instruction = required_tool or "Read the raw source and extract evidence that matches the requested analysis axis."
        success = ["Separates source-derived facts first.", "Does not confuse source reading with tool planning."]
        rejection = ["Fills gaps by inference without source text.", "Conflates fact and interpretation."]
    elif plan_type == "warroom_deliberation":
        evidence_policy = "Reasoning, intent, and structure matter more than tool retrieval here; avoid generic limitation loops."
        executor_instruction = str(action_plan.get("current_step_goal") or response_strategy.get("answer_goal") or "Clarify the reasoning and answer boundary for the current turn.").strip()
        success = ["Understands what the user is really asking.", "Separates reasoning, obligation, gaps, and answer boundary.", "Produces an answer seed phase_3 can say directly."]
        rejection = ["Only repeats that evidence is missing.", "Wraps user input in report style.", "Sends a no-tool turn into 2a/2b unnecessarily."]
    else:
        evidence_policy = "Answer directly within the current user turn and approved response strategy."
        executor_instruction = str(response_strategy.get("answer_goal") or action_plan.get("current_step_goal") or "Answer the current request naturally and directly.").strip()
        success = ["Directly answers the user request.", "Does not use internal report tone."]
        rejection = ["Repeats the user input as an observation.", "Falls into an unnecessary evidence loop."]

    delivery_shape = str(goal_lock.get("answer_shape") or "").strip() or {
        "tool_evidence": "findings_first",
        "recent_dialogue_review": "conversation_review",
        "raw_source_analysis": "source_grounded_summary",
        "warroom_deliberation": "deliberative_answer",
        "direct_delivery": "direct_answer",
    }.get(plan_type, "direct_answer")
    if output_act == "self_critique":
        delivery_shape = "fault_admission + concrete_cause + fix_plan"
        success = _dedupe_keep_order(
            list(success)
            + [
                "Admit the concrete assistant failure based on recent dialogue evidence.",
                "Explain the structural cause of the failure.",
                "Name the next correction direction.",
            ]
        )[:6]
        rejection = _dedupe_keep_order(
            list(rejection)
            + [
                "Only summarizes recent dialogue and skips self-critique.",
                "Ends with a generic apology only.",
            ]
        )[:6]
    elif output_act == "deliver_findings":
        delivery_shape = "findings_first"
    elif output_act == "execute_game":
        delivery_shape = "execute_first_step"

    confidence = 0.76
    if plan_type in {"tool_evidence", "raw_source_analysis"} and not required_tool:
        confidence = 0.58
    if plan_type == "warroom_deliberation" and required_tool:
        confidence = 0.45

    return _normalize_operation_plan({
        "plan_type": plan_type,
        "source_lane": source_lane,
        "output_act": output_act,
        "user_goal": user_goal,
        "executor_instruction": executor_instruction,
        "evidence_policy": evidence_policy,
        "success_criteria": success,
        "rejection_criteria": rejection,
        "delivery_shape": delivery_shape,
        "confidence": confidence,
    })


def _build_reasoning_board_from_analysis(state: AnimaState, analysis_data: dict):
    board = _empty_reasoning_board(
        turn_id=str(state.get("current_time") or f"loop_{state.get('loop_count', 0)}"),
        user_input=str(state.get("user_input") or ""),
    )
    if not isinstance(analysis_data, dict):
        return board

    seen_facts = set()

    def add_fact(source_id: str, source_type: str, extracted_fact: str, excerpt: str = ""):
        normalized_fact = str(extracted_fact or "").strip()
        if not normalized_fact:
            return
        dedupe_key = (str(source_id or "").strip(), normalized_fact)
        if dedupe_key in seen_facts:
            return
        seen_facts.add(dedupe_key)
        fact_id = f"fact_{len(board['fact_cells']) + 1}"
        board["fact_cells"].append({
            "fact_id": fact_id,
            "source_id": str(source_id or "").strip() or "unknown_source",
            "source_type": str(source_type or "").strip() or "unknown",
            "excerpt": (str(excerpt or "").strip() or normalized_fact)[:180],
            "extracted_fact": normalized_fact,
            "fact_kind": _infer_fact_kind(source_type, normalized_fact),
            "confidence": 0.9,
        })

    evidences = analysis_data.get("evidences", [])
    if isinstance(evidences, list):
        for idx, item in enumerate(evidences, start=1):
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("source_id") or "").strip() or f"unknown_source_{idx}"
            source_type = str(item.get("source_type") or "").strip() or "unknown"
            extracted_fact = str(item.get("extracted_fact") or "").strip()
            add_fact(source_id, source_type, extracted_fact, extracted_fact)

    source_judgments = analysis_data.get("source_judgments", [])
    if isinstance(source_judgments, list):
        for judgment in source_judgments:
            if not isinstance(judgment, dict):
                continue
            source_id = str(judgment.get("source_id") or "").strip() or "unknown_source"
            source_type = str(judgment.get("source_type") or "").strip() or "unknown"
            for fact in judgment.get("accepted_facts", []):
                if not isinstance(fact, str):
                    continue
                add_fact(source_id, source_type, fact, fact)

    analytical_thought = str(analysis_data.get("analytical_thought") or "").strip()
    if analytical_thought:
        board["open_questions"].append(analytical_thought)

    board["final_fact_ids"] = []
    board["open_questions"] = _dedupe_keep_order(board["open_questions"])
    board["search_requests"] = _dedupe_keep_order(board["search_requests"])
    status = str(analysis_data.get("investigation_status") or "").upper()
    critic_report = _empty_critic_report()
    critic_report["situational_brief"] = str(analysis_data.get("situational_brief") or "").strip()
    critic_report["analytical_thought"] = analytical_thought
    critic_report["source_judgments"] = source_judgments if isinstance(source_judgments, list) else []
    critic_report["open_questions"] = list(board["open_questions"])
    critic_report["recommended_action"] = _analysis_status_to_recommended_action(status)

    objections = []
    if status in {"EXPANSION_REQUIRED", "INCOMPLETE"}:
        objections.append({
            "objection_id": "critic_primary_gap",
            "objection_text": analytical_thought or critic_report["situational_brief"] or "The critic found an unresolved gap that still blocks a confident answer.",
            "target_fact_ids": list(board["final_fact_ids"]),
            "target_pair_ids": [],
            "severity": "high" if status == "INCOMPLETE" else "medium",
            "needs_search": True,
        })
    elif analytical_thought:
        objections.append({
            "objection_id": "critic_caution_note",
            "objection_text": analytical_thought,
            "target_fact_ids": list(board["final_fact_ids"]),
            "target_pair_ids": [],
            "severity": "low",
            "needs_search": False,
        })

    critic_report["objections"] = objections
    board["critic_report"] = critic_report
    return board

_START_GATE_INTENTS = {
    "providing_current_memory",
    "requesting_memory_recall",
    "public_knowledge_question",
    "direct_social",
    "correction_or_feedback",
    "capability_boundary_question",
    "task_or_tool_request",
    "other",
}

_START_GATE_ANSWER_MODES = {
    "current_turn_grounding",
    "grounded_recall",
    "public_parametric_knowledge",
    "generic_dialogue",
}


def _safe_model_dump(value):
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            return {}
    if hasattr(value, "dict"):
        try:
            return value.dict()
        except Exception:
            return {}
    return {}


def _generic_normalized_goal_for_start_gate(intent: str, answer_mode: str):
    if answer_mode == "current_turn_grounding" or intent == "providing_current_memory":
        return "Respond directly to the user-provided current-turn fact or story."
    if answer_mode == "grounded_recall" or intent == "requesting_memory_recall":
        return "Answer the memory-recall request only after grounded stored evidence is available."
    if answer_mode == "public_parametric_knowledge" or intent == "public_knowledge_question":
        return "Answer the public-knowledge question directly without private-memory retrieval."
    if intent == "correction_or_feedback":
        return "Acknowledge the correction or feedback and answer the immediate turn."
    if intent == "capability_boundary_question":
        return "Explain the assistant's current memory/source access boundary directly."
    if intent == "direct_social":
        return "Respond naturally to the current social turn."
    if intent == "task_or_tool_request":
        return "Plan the requested task before any tool execution."
    return "Answer the current turn."


def _fallback_start_gate_turn_contract(
    user_input: str,
    recent_context: str = "",
    goal_contract: dict | None = None,
):
    text = str(user_input or "").strip()
    goal_contract = goal_contract if isinstance(goal_contract, dict) else _derive_user_goal_contract(text, source_lane="direct_dialogue")
    policy = _answer_mode_policy_for_turn(text, recent_context, goal_contract)
    preferred = str(policy.get("preferred_answer_mode") or "generic_dialogue").strip()
    if bool(policy.get("grounded_delivery_required")):
        if str(policy.get("question_class") or "").strip() == "grounded_memory_recall":
            answer_mode = "grounded_recall"
            intent = "requesting_memory_recall"
        else:
            answer_mode = "generic_dialogue"
            intent = "task_or_tool_request"
    elif preferred == "current_turn_grounding":
        answer_mode = "current_turn_grounding"
        intent = "providing_current_memory"
    elif preferred == "public_parametric_knowledge":
        answer_mode = "public_parametric_knowledge"
        intent = "public_knowledge_question"
    else:
        answer_mode = "generic_dialogue"
        intent = "other"

    facts = _extract_current_turn_grounding_facts(text, goal_contract)
    direct_delivery_allowed = answer_mode in {"current_turn_grounding", "public_parametric_knowledge"}
    requires_grounding = bool(policy.get("grounded_delivery_required"))
    return {
        "user_intent": intent,
        "normalized_goal": _generic_normalized_goal_for_start_gate(intent, answer_mode),
        "answer_mode_preference": answer_mode,
        "requires_grounding": requires_grounding,
        "direct_delivery_allowed": direct_delivery_allowed,
        "needs_planning": not direct_delivery_allowed,
        "current_turn_facts": facts,
        "rationale": "Fallback contract from legacy answer-mode policy; used only when the LLM start gate contract is unavailable.",
        "contract_source": "fallback_policy",
    }


def _normalize_start_gate_turn_contract(contract: dict | StartGateTurnContract | None, user_input: str, recent_context: str = ""):
    del recent_context
    payload = _safe_model_dump(contract)
    if not payload:
        payload = _fallback_start_gate_turn_contract(user_input)

    intent = str(payload.get("user_intent") or "other").strip()
    if intent not in _START_GATE_INTENTS:
        intent = "other"
    answer_mode = str(payload.get("answer_mode_preference") or "generic_dialogue").strip()
    if answer_mode not in _START_GATE_ANSWER_MODES:
        answer_mode = "generic_dialogue"

    if intent == "providing_current_memory":
        answer_mode = "current_turn_grounding"
    elif intent == "requesting_memory_recall":
        answer_mode = "grounded_recall"
    elif intent == "public_knowledge_question":
        answer_mode = "public_parametric_knowledge"
    elif intent == "capability_boundary_question":
        answer_mode = "generic_dialogue"
        payload["requires_grounding"] = False
        payload["direct_delivery_allowed"] = False
        payload["needs_planning"] = True
    elif answer_mode == "grounded_recall":
        intent = "requesting_memory_recall"

    requires_grounding = bool(payload.get("requires_grounding")) or answer_mode == "grounded_recall"
    if answer_mode in {"current_turn_grounding", "public_parametric_knowledge"}:
        requires_grounding = False

    direct_delivery_allowed = bool(payload.get("direct_delivery_allowed"))
    if answer_mode in {"current_turn_grounding", "public_parametric_knowledge"}:
        direct_delivery_allowed = True
    if requires_grounding or answer_mode == "grounded_recall":
        direct_delivery_allowed = False

    needs_planning = bool(payload.get("needs_planning")) or not direct_delivery_allowed
    if intent == "task_or_tool_request":
        direct_delivery_allowed = False
        needs_planning = True

    raw_goal = str(payload.get("normalized_goal") or "").strip()
    user_text = str(user_input or "").strip()
    normalized_user = unicodedata.normalize("NFKC", user_text)
    normalized_goal = raw_goal
    if not normalized_goal or unicodedata.normalize("NFKC", normalized_goal) == normalized_user:
        normalized_goal = _generic_normalized_goal_for_start_gate(intent, answer_mode)
    normalized_goal = _compact_user_facing_summary(normalized_goal, 180)

    facts = []
    for fact in payload.get("current_turn_facts", []) or []:
        fact_text = str(fact or "").strip()
        if fact_text:
            facts.append(_compact_user_facing_summary(fact_text, 260))
    if answer_mode == "current_turn_grounding" and not facts and user_text:
        facts = _extract_current_turn_grounding_facts(user_text)
        if not facts:
            facts = [_compact_user_facing_summary(user_text, 260)]

    return {
        "schema": "StartGateTurnContract.v1",
        "user_intent": intent,
        "normalized_goal": normalized_goal,
        "answer_mode_preference": answer_mode,
        "requires_grounding": requires_grounding,
        "direct_delivery_allowed": direct_delivery_allowed,
        "needs_planning": needs_planning,
        "current_turn_facts": _dedupe_keep_order(facts)[:4],
        "rationale": _compact_user_facing_summary(str(payload.get("rationale") or ""), 240),
        "contract_source": str(payload.get("contract_source") or "llm_start_gate").strip() or "llm_start_gate",
    }


def _answer_mode_policy_from_start_gate_turn_contract(contract: dict | None, fallback_policy: dict | None = None):
    fallback_policy = fallback_policy if isinstance(fallback_policy, dict) else {}
    contract = contract if isinstance(contract, dict) else {}
    answer_mode = str(contract.get("answer_mode_preference") or "").strip()
    intent = str(contract.get("user_intent") or fallback_policy.get("question_class") or "generic_dialogue").strip()
    preferred = "grounded_answer" if answer_mode == "grounded_recall" else answer_mode
    if preferred not in {"grounded_answer", "current_turn_grounding", "public_parametric_knowledge", "generic_dialogue"}:
        preferred = str(fallback_policy.get("preferred_answer_mode") or "generic_dialogue").strip() or "generic_dialogue"
    return {
        "question_class": intent,
        "preferred_answer_mode": preferred,
        "grounded_delivery_required": bool(contract.get("requires_grounding")) or answer_mode == "grounded_recall",
        "parametric_knowledge_allowed": answer_mode == "public_parametric_knowledge",
        "current_turn_grounding_ready": answer_mode == "current_turn_grounding",
        "direct_delivery_allowed": bool(contract.get("direct_delivery_allowed")),
        "start_gate_contract_source": str(contract.get("contract_source") or "").strip(),
    }


def _llm_start_gate_turn_contract(
    user_input: str,
    recent_context: str,
    working_memory: dict,
    reasoning_plan: dict,
    s_thinking_history: dict | None = None,
    analysis_report: dict | None = None,
    tactical_briefing: str = "",
    prior_thought_critique: dict | None = None,
):
    del working_memory
    text = str(user_input or "").strip()
    if not text:
        return _normalize_start_gate_turn_contract(
            {
                "user_intent": "other",
                "normalized_goal": "Answer the current turn.",
                "answer_mode_preference": "generic_dialogue",
                "requires_grounding": False,
                "direct_delivery_allowed": False,
                "needs_planning": True,
                "current_turn_facts": [],
                "rationale": "Empty turn.",
            },
            text,
            recent_context,
        )

    history_prompt = "{}"
    if isinstance(s_thinking_history, dict) and s_thinking_history:
        history_prompt = json.dumps(s_thinking_history, ensure_ascii=False, separators=(",", ":"))
    analysis_prompt = ""
    if isinstance(analysis_report, dict) and analysis_report:
        analysis_packet = _compact_analysis_for_prompt(analysis_report, role="-1s")
        if analysis_packet:
            analysis_prompt = (
                "\n\n[analysis_report_compact]\n"
                + json.dumps(analysis_packet, ensure_ascii=False, separators=(",", ":"))
            )
    tactical_prompt = ""
    tactical_text = str(tactical_briefing or "").strip()
    if tactical_text:
        tactical_prompt = "\n\n[tactical_briefing]\n" + _compact_user_facing_summary(tactical_text, 700)
    critique_prompt = ""
    has_prior_critique = isinstance(prior_thought_critique, dict) and bool(prior_thought_critique)
    if has_prior_critique:
        critique_prompt = (
            "\n\n[prior_thought_critique]\n"
            + json.dumps(prior_thought_critique, ensure_ascii=False, separators=(",", ":"))
        )
    base_rules = (
        "You are ANIMA -1s. Produce only a thin start-gate contract.\n"
        "Rules:\n"
        "1. Decide the current turn meaning from current_user_turn, recent context, and s_thinking_history; do not use isolated keywords.\n"
        "2. Use s_thinking_history to avoid repeating the same broad direction or main_gap when prior cycles stalled.\n"
        "3. If the user shares a present-turn memory/story/fact, choose providing_current_memory and current_turn_grounding.\n"
        "4. If the user asks whether you can access/search/use/read/see a source, memory, diary, or database, choose capability_boundary_question and generic_dialogue. Korean examples: '내 일기를 볼 수 있어?', 'DB 검색 가능해?', '기억에 접근할 수 있어?' This asks about capability, not retrieval.\n"
        "5. If the user asks to remember, retrieve, verify, search, or report a concrete past stored fact, choose requesting_memory_recall and grounded_recall. Example: '내 일기에서 X를 찾아봐.'\n"
        "6. If the user asks about public media or general knowledge, choose public_knowledge_question and public_parametric_knowledge.\n"
        "7. normalized_goal must be abstract; do not choose tools, write search queries, or write final answer text.\n"
        "8. If tactical_briefing contains active DreamHint advisories, treat them as advisory context only: do not let them override the current turn, propose tool calls, or copy briefing text into the contract goal.\n"
        "9. (V4 §1-A.0 / §2 (k)) Do not perform goal-setting. -1s normalizes user intent only; the operational goal is owned by -1a's strategist_goal.user_goal_core.\n"
    )
    recursion_rule = ""
    if has_prior_critique:
        recursion_rule = (
            "10. RECURSION MODE — prior_thought_critique is present. Run TWO steps in order:\n"
            "    Step 1 (verification, MUST run first):\n"
            "      Re-read working_memory + recent_context + s_thinking_history with the critique in mind.\n"
            "      Ask: 'Given this critique, is the evidence really thin, or did the previous step miss something?'\n"
            "      If verified evidence is sufficient → set normalized_goal to direct_delivery and let downstream route to phase_3.\n"
            "    Step 2 (recursion routing — only if Step 1 confirms shortage):\n"
            "      If deep deliberation is needed → signal warroom via routing context.\n"
            "      If a lightweight follow-up is enough → still prefer phase_3 over re-looping; do not loop the critique itself.\n"
        )
    system_prompt = base_rules + recursion_rule
    human_prompt = (
        f"[current_user_turn]\n{text}\n\n"
        f"[recent_context_excerpt]\n{_compact_user_facing_summary(recent_context, 900)}\n\n"
        f"{tactical_prompt}\n\n"
        f"[s_thinking_history]\n{history_prompt}\n\n"
        f"[reasoning_plan_hint]\n{json.dumps(reasoning_plan if isinstance(reasoning_plan, dict) else {}, ensure_ascii=False)}"
        f"{analysis_prompt}"
        f"{critique_prompt}"
    )
    try:
        structured_llm = llm.with_structured_output(StartGateTurnContract)
        parsed = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        payload = _safe_model_dump(parsed)
        payload["contract_source"] = "llm_start_gate"
        return _normalize_start_gate_turn_contract(payload, text, recent_context)
    except Exception as exc:
        fallback = _fallback_start_gate_turn_contract(text, recent_context)
        fallback["rationale"] = f"LLM start gate unavailable; using fallback contract. {type(exc).__name__}"
        return _normalize_start_gate_turn_contract(fallback, text, recent_context)


def _build_start_gate_switches(
    user_input: str,
    recent_context: str,
    working_memory: dict,
    start_gate_review: dict,
    reasoning_plan: dict,
    start_gate_turn_contract: dict | StartGateTurnContract | None = None,
):
    text = str(user_input or "").strip()
    artifact_hint = _extract_artifact_hint(text)
    explicit_search = _extract_explicit_search_keyword(text)
    working_memory = working_memory if isinstance(working_memory, dict) else {}
    temporal_context = working_memory.get("temporal_context", {})
    if not isinstance(temporal_context, dict):
        temporal_context = {}
    goal_contract = _derive_user_goal_contract(text, source_lane="direct_dialogue")
    fallback_policy = _answer_mode_policy_for_turn(text, recent_context, goal_contract)
    turn_contract = _normalize_start_gate_turn_contract(
        start_gate_turn_contract or _fallback_start_gate_turn_contract(text, recent_context, goal_contract),
        text,
        recent_context,
    )
    normalized_goal = str(turn_contract.get("normalized_goal") or "").strip() or _normalized_goal_from_contract(goal_contract, text)
    answer_mode_policy = _answer_mode_policy_from_start_gate_turn_contract(turn_contract, fallback_policy)
    direct_delivery_allowed = bool(turn_contract.get("direct_delivery_allowed"))
    requires_grounding = bool(turn_contract.get("requires_grounding"))
    needs_planning = bool(turn_contract.get("needs_planning")) or not direct_delivery_allowed
    ops_next_hop = "phase_3" if direct_delivery_allowed else "-1a_thinker"
    turn_family = "direct_delivery" if direct_delivery_allowed else "planning_contract"
    try:
        topic_reset_confidence = float(temporal_context.get("topic_reset_confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        topic_reset_confidence = 0.0
    allow_task_inheritance = (
        bool(temporal_context.get("carry_over_allowed"))
        and not artifact_hint
        and not explicit_search
        and topic_reset_confidence < 0.7
    )
    situation_frame = {
        "turn_family": turn_family,
        "direct_strategy": "",
        "root_target": "",
        "relevant_branch_paths": [],
        "evidence_need": "grounded_source" if requires_grounding else "llm_or_current_turn",
        "user_need_summary": normalized_goal,
        "avoid": [
            "Do not create tool names, search queries, or direct-delivery scripts in phase -1s.",
            "Do not copy raw user wording into planner goal fields.",
        ],
    }

    return {
        "contract_kind": "thin_start_gate_v1",
        "normalized_goal": normalized_goal,
        "start_gate_turn_contract": turn_contract,
        "goal_contract": goal_contract,
        "answer_mode_policy": answer_mode_policy,
        "requires_grounding": requires_grounding,
        "direct_delivery_allowed": direct_delivery_allowed,
        "needs_planning": needs_planning,
        "ops_next_hop": ops_next_hop,
        "direct_strategy": "",
        "requested_move": "",
        "artifact_hint": artifact_hint,
        "explicit_search": explicit_search,
        "turn_family": turn_family,
        "reflective_mode": "",
        "answer_shape_hint": "",
        "force_tool_first": False,
        "force_recent_dialogue_review": False,
        "allow_task_inheritance": allow_task_inheritance,
        "allow_recent_hints": topic_reset_confidence < 0.7,
        "memo": "thin start gate produced a normalized goal contract only.",
        "current_turn_facts": list(turn_contract.get("current_turn_facts", []) or []),
        "situation_frame": situation_frame,
    }


def _looks_like_dialogue_audit_turn(user_input: str, recent_context: str = ""):
    text = unicodedata.normalize("NFKC", str(user_input or "")).lower()
    if not text:
        return False
    context_words = ["conversation", "recent", "previous", "\ub300\ud654", "\ucd5c\uadfc", "\uc774\uc804"]
    audit_words = ["summarize", "review", "check", "audit", "\uc694\uc57d", "\uc815\ub9ac", "\uac80\ud1a0"]
    if any(word in text for word in context_words) and any(word in text for word in audit_words):
        return True
    return bool(recent_context) and any(word in text for word in audit_words)


def _fast_start_gate_assessment(user_input: str, recent_context: str, working_memory: dict, reasoning_plan: dict):
    text = str(user_input or "").strip()
    del recent_context, working_memory
    artifact_hint = _extract_artifact_hint(text)
    explicit_search = _extract_explicit_search_keyword(text)
    preferred_path = str((reasoning_plan or {}).get("preferred_path") or "").strip()
    rationale = str((reasoning_plan or {}).get("rationale") or "").strip()

    risk_flags = []
    if not text:
        return {
            "answerability": "needs_planning",
            "recommended_handler": "-1a_thinker",
            "confidence": 0.4,
            "why_short": "Empty turn; downstream planner should decide whether to speak.",
            "risk_flags": ["empty_turn"],
        }

    if artifact_hint:
        return {
            "answerability": "needs_planning",
            "recommended_handler": "-1a_thinker",
            "confidence": 0.92,
            "why_short": "An artifact/source review was requested, so the strategist should plan the read before anyone speaks.",
            "risk_flags": ["source_specific", "grounding_required"],
        }

    if explicit_search:
        risk_flags.extend(["grounding_required"])
        risk_flags.append("search_phrase_detected")
        return {
            "answerability": "needs_grounding",
            "recommended_handler": "-1a_thinker",
            "confidence": 0.8,
            "why_short": "An explicit search phrase exists; -1a should decide whether and how to use tools.",
            "risk_flags": risk_flags,
        }

    if _normalize_reasoning_preferred_path(preferred_path) == "delivery_contract":
        risk_flags.append("delivery_contract_needs_judgment")
        return {
            "answerability": "direct_but_risky",
            "recommended_handler": "-1a_thinker",
            "confidence": 0.7,
            "why_short": rationale or "The runtime hint says a delivery contract may be enough; -1a should confirm the framing before delivery.",
            "risk_flags": risk_flags,
        }

    return {
        "answerability": "needs_planning",
        "recommended_handler": "-1a_thinker",
        "confidence": 0.65,
        "why_short": rationale or "This is not a trivial direct-answer turn, so the strategist should take the first pass.",
        "risk_flags": risk_flags,
    }


def _phase3_recent_context_excerpt(recent_context: str, max_chars: int = 1400):
    text = str(recent_context or "").strip()
    if not text:
        return ""
    marker = "[Recent Raw Turns]"
    if marker in text:
        text = text.split(marker, 1)[1].strip()
    if len(text) <= max_chars:
        return text
    return text[-max_chars:].strip()


def _extract_recent_raw_turns_from_context(recent_context: str, max_turns: int = 6):
    text = str(recent_context or "").strip()
    if not text:
        return []

    marker = "[Recent Raw Turns]"
    if marker in text:
        text = text.split(marker, 1)[1].strip()

    turns = []
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = re.match(r"^\[?(user|assistant)\]?:\s*(.*)$", line, re.IGNORECASE)
        if matched:
            if current:
                turns.append(current)
            role = matched.group(1).lower()
            content = matched.group(2).strip()
            current = {"role": role, "content": content}
            continue
        if current:
            current["content"] = (current["content"] + " " + line).strip()
    if current:
        turns.append(current)

    return turns[-max_turns:]


def _is_recent_dialogue_review_turn(user_input: str, recent_context: str = ""):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    markers = [
        "review the conversation",
        "read the recent chat",
        "recent dialogue",
        "what was weird",
        "\ucd5c\uadfc \ub300\ud654",
        "\uc774\uc804 \ub300\ud654",
        "\ub300\ud654 \uac80\ud1a0",
    ]
    if any(marker in text for marker in markers):
        return True
    return bool(recent_context) and any(marker in text for marker in ["review", "summarize", "\uc694\uc57d", "\uac80\ud1a0"])

def _is_date_memory_recall_turn(user_input: str):
    text = str(user_input or "").strip()
    if not text:
        return False

    date_like = bool(
        re.search(r"\b\d{4}[-./]\d{1,2}[-./]\d{1,2}\b", text)
        or re.search(r"\d{4}\s*\ub144\s*\d{1,2}\s*\uc6d4\s*\d{1,2}\s*\uc77c", text)
    )
    if not date_like:
        return False

    recall_markers = [
        "\uadf8\ub54c",
        "\uadf8\ub0a0",
        "\ud558\ub8e8",
        "\ub9d0\ud574\ubd10",
        "\uc5b4\ub5a0",
        "\ubcf4\ub0b8",
        "\uae30\uc5b5",
        "\ube44\uc2b7",
    ]
    return any(marker in text for marker in recall_markers)


def _judge_delivery_gate_review(
    *,
    user_input: str,
    recent_context: str,
    working_memory: dict,
    reasoning_board: dict,
    analysis_data: dict,
    response_strategy: dict,
    search_results: str,
    loop_count: int,
):
    strategy, packet, review = _prepare_phase3_delivery(
        user_input=user_input,
        recent_context=recent_context,
        working_memory=working_memory,
        reasoning_board=reasoning_board,
        analysis_data=analysis_data,
        response_strategy=response_strategy,
        search_results=search_results,
        loop_count=loop_count,
    )

    normalized_review = json.loads(json.dumps(review, ensure_ascii=False)) if isinstance(review, dict) else {}
    issues = list(normalized_review.get("issues", [])) if isinstance(normalized_review.get("issues"), list) else []
    missing = (
        list(normalized_review.get("missing_for_delivery", []))
        if isinstance(normalized_review.get("missing_for_delivery"), list)
        else []
    )

    combined_delivery_text = " ".join(
        [
            str(strategy.get("direct_answer_seed") or "").strip(),
            str(packet.get("final_answer_brief") or "").strip(),
            str(packet.get("followup_instruction") or "").strip(),
        ]
    ).strip()
    explicit_search = _extract_explicit_search_keyword(user_input)
    date_recall_turn = _is_date_memory_recall_turn(user_input)
    packet_followup = str(packet.get("followup_instruction") or "").strip()
    packet_brief = str(packet.get("final_answer_brief") or "").strip()
    delivery_mode = str(packet.get("delivery_freedom_mode") or strategy.get("delivery_freedom_mode") or "").strip()
    direct_seed = str(strategy.get("direct_answer_seed") or "").strip()

    if (
        _looks_like_generic_non_answer_text(combined_delivery_text)
        and (explicit_search or date_recall_turn)
    ):
        issues.append("Retrieval or recall request still resolves to a generic non-answer.")

    if delivery_mode == "proposal" and packet_brief and packet_followup and _looks_like_generic_non_answer_text(packet_followup):
        issues.append("Proposal delivery still carries a generic narrowing follow-up.")

    if date_recall_turn and _looks_like_generic_non_answer_text(combined_delivery_text):
        missing.append("A dated memory recall request still lacks concrete recalled content.")

    if _looks_like_user_parroting_report(packet_brief, user_input):
        issues.append("The approved brief still parrots the user's own wording as a report instead of a reply.")

    if _looks_like_user_parroting_report(direct_seed, user_input):
        issues.append("The direct answer seed still parrots the user's own wording as a report instead of a reply.")

    approved_fact_cells = packet.get("approved_fact_cells", []) if isinstance(packet.get("approved_fact_cells"), list) else []
    approved_claims = packet.get("approved_claims", []) if isinstance(packet.get("approved_claims"), list) else []
    delivery_ok = not issues and not missing
    normalized_review["issues"] = _dedupe_keep_order([str(item).strip() for item in issues if str(item).strip()])
    normalized_review["missing_for_delivery"] = _dedupe_keep_order([str(item).strip() for item in missing if str(item).strip()])
    normalized_review["delivery_ok"] = delivery_ok
    normalized_review["should_remand"] = not delivery_ok

    if delivery_ok:
        normalized_review["suggested_action"] = "deliver_now"
    elif explicit_search or date_recall_turn:
        normalized_review["suggested_action"] = "remand_to_judge"
    elif normalized_review["missing_for_delivery"] and not approved_fact_cells and not approved_claims:
        normalized_review["suggested_action"] = "strengthen_response_strategy"
    else:
        normalized_review["suggested_action"] = str(normalized_review.get("suggested_action") or "remand_to_judge")

    return strategy, packet, normalized_review

def _base_minimal_direct_dialogue_strategy(user_input: str, working_memory: dict):
    current_user_text = str(user_input or "").strip()
    active_task = _working_memory_active_task(working_memory)
    must_include = [f"current user request: {current_user_text}"] if current_user_text else []
    if active_task and active_task != current_user_text:
        must_include.append(f"current task context: {active_task}")

    return {
        "reply_mode": "cautious_minimal",
        "delivery_freedom_mode": "grounded",
        "answer_goal": "Answer the current user request directly with minimal scripted shaping.",
        "tone_strategy": "Calm, direct, evidence-aware, and free of internal report tone.",
        "evidence_brief": f"current user request: {current_user_text}" if current_user_text else "Use the current user turn as the primary evidence focus.",
        "reasoning_brief": "Phase 3 should answer the current request directly and ask a follow-up only if truly needed.",
        "direct_answer_seed": "",
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "Do not mention internal roles, judge packets, or stage workflows.",
            "Do not pretend unsupported context exists.",
            "Do not replace a direct answer with vague filler.",
        ],
        "answer_outline": [
            "Answer the current user request directly.",
            "Briefly state limits only if important.",
            "Ask at most one precise follow-up if needed.",
        ],
        "uncertainty_policy": "If evidence is weak, state the limit clearly instead of guessing.",
    }

def _prepare_phase3_delivery(
    user_input: str,
    recent_context: str,
    working_memory: dict,
    reasoning_board: dict,
    analysis_data: dict,
    response_strategy: dict,
    search_results: str,
    loop_count: int,
):
    strategy = response_strategy if isinstance(response_strategy, dict) else {}
    if not strategy:
        if _has_structured_analysis(analysis_data):
            strategy = _fallback_response_strategy(analysis_data)
        else:
            strategy = _minimal_direct_dialogue_strategy(user_input, working_memory)

    phase3_reference_policy = _phase3_reference_policy(search_results, loop_count)
    packet = _build_judge_speaker_packet(reasoning_board, strategy, phase3_reference_policy)
    recent_excerpt = _phase3_recent_context_excerpt(recent_context)
    review = _build_speaker_review(packet, user_input=user_input, recent_context_excerpt=recent_excerpt)

    if review.get("should_remand") and not str(strategy.get("direct_answer_seed") or "").strip():
        strengthened_strategy = _minimal_direct_dialogue_strategy(user_input, working_memory)
        packet = _build_judge_speaker_packet(reasoning_board, strengthened_strategy, phase3_reference_policy)
        review = _build_speaker_review(packet, user_input=user_input, recent_context_excerpt=recent_excerpt)
        strategy = strengthened_strategy

    return strategy, packet, review


def _apply_strategist_output_to_reasoning_board(board: dict, strategist_payload: dict):
    if not isinstance(board, dict):
        board = _empty_reasoning_board()
    next_board = json.loads(json.dumps(board, ensure_ascii=False))
    fact_map = {
        str(fact.get("fact_id") or "").strip(): fact
        for fact in next_board.get("fact_cells", [])
        if isinstance(fact, dict)
    }

    candidate_pairs = []
    for idx, raw_pair in enumerate(strategist_payload.get("candidate_pairs", []), start=1):
        if not isinstance(raw_pair, dict):
            continue
        fact_ids = [fid for fid in _dedupe_keep_order(raw_pair.get("fact_ids", [])) if fid in fact_map]
        if not fact_ids:
            continue
        subjective = raw_pair.get("subjective", {}) if isinstance(raw_pair.get("subjective"), dict) else {}
        claim_text = str(subjective.get("claim_text") or "").strip()
        if not claim_text:
            continue
        answer_policy = str(subjective.get("answer_policy") or "cautious")
        if answer_policy not in {"allowed", "cautious", "forbidden"}:
            answer_policy = "cautious"
        claim_kind = str(subjective.get("claim_kind") or "interpretation")
        if claim_kind not in {"interpretation", "hypothesis", "causal_guess", "intent_inference", "user_model_update", "response_policy"}:
            claim_kind = "interpretation"
        confidence = float(subjective.get("confidence", 0.5) or 0.5)
        confidence = max(0.0, min(1.0, confidence))
        candidate_pairs.append({
            "pair_id": str(raw_pair.get("pair_id") or f"pair_{idx}"),
            "fact_ids": fact_ids,
            "paired_fact_digest": str(raw_pair.get("paired_fact_digest") or "").strip(),
            "subjective": {
                "claim_text": claim_text,
                "claim_kind": claim_kind,
                "confidence": confidence,
                "answer_policy": answer_policy,
                "uncertainty_note": str(subjective.get("uncertainty_note") or "").strip(),
            },
            "audit_status": "pending",
            "audit_note": "",
        })

    response_strategy = strategist_payload.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}

    operation_plan = _normalize_operation_plan(strategist_payload.get("operation_plan", {}))
    case_theory = str(strategist_payload.get("case_theory") or "").strip()
    action_plan = _normalize_action_plan(strategist_payload.get("action_plan", {}))
    goal_lock = _normalize_goal_lock(strategist_payload.get("goal_lock", {}))
    strategist_goal = _normalize_strategist_goal(strategist_payload.get("strategist_goal", {}))
    convergence_state = _normalize_convergence_state(strategist_payload.get("convergence_state", ""))
    achieved_findings = _normalize_short_string_list(strategist_payload.get("achieved_findings", []), limit=3)
    delivery_readiness = _normalize_delivery_readiness(strategist_payload.get("delivery_readiness", ""))
    next_frontier = _normalize_short_string_list(strategist_payload.get("next_frontier", []), limit=3)
    war_room_contract = _normalize_war_room_operating_contract(strategist_payload.get("war_room_contract", {}))
    requested_fact_ids = []
    for pair in candidate_pairs:
        requested_fact_ids.extend(pair.get("fact_ids", []))
    requested_fact_ids = _dedupe_keep_order(requested_fact_ids)

    next_board["candidate_pairs"] = candidate_pairs
    next_board["final_fact_ids"] = [fid for fid in requested_fact_ids if fid in fact_map]
    next_board["final_pair_ids"] = []
    next_board["must_avoid_claims"] = _dedupe_keep_order(response_strategy.get("must_avoid_claims", []))
    next_board["direct_answer_seed"] = str(response_strategy.get("direct_answer_seed") or "").strip()
    next_board["strategist_plan"] = {
        "case_theory": case_theory,
        "operation_plan": operation_plan,
        "action_plan": action_plan,
        "goal_lock": goal_lock,
        "strategist_goal": strategist_goal,
        "convergence_state": convergence_state,
        "achieved_findings": achieved_findings,
        "delivery_readiness": delivery_readiness,
        "next_frontier": next_frontier,
        "war_room_contract": war_room_contract,
    }
    next_board["advocate_report"] = {
        "defense_strategy": case_theory or str(response_strategy.get("reasoning_brief") or response_strategy.get("answer_goal") or "").strip(),
        "summary_of_position": (
            str(response_strategy.get("direct_answer_seed") or response_strategy.get("evidence_brief") or "").strip()
            or action_plan.get("current_step_goal", "")
        ),
        "supported_pair_ids": [str(pair.get("pair_id") or "").strip() for pair in candidate_pairs if str(pair.get("pair_id") or "").strip()],
        "response_contract": {
            "reply_mode": str(response_strategy.get("reply_mode") or "").strip(),
            "answer_goal": str(response_strategy.get("answer_goal") or "").strip(),
            "tone_strategy": str(response_strategy.get("tone_strategy") or "").strip(),
            "uncertainty_policy": str(response_strategy.get("uncertainty_policy") or "").strip(),
            "current_step_goal": str(action_plan.get("current_step_goal") or "").strip(),
            "required_tool": str(action_plan.get("required_tool") or "").strip(),
            "operation_plan": operation_plan,
            "goal_lock": goal_lock,
            "strategist_goal": strategist_goal,
            "convergence_state": convergence_state,
            "delivery_readiness": delivery_readiness,
            "operation_contract": _normalize_operation_contract(action_plan.get("operation_contract", {})),
            "war_room_contract": war_room_contract,
        },
    }
    return next_board

def _audit_reasoning_board(board: dict, analysis_data: dict):
    if not isinstance(board, dict):
        return _empty_reasoning_board()

    audited = json.loads(json.dumps(board, ensure_ascii=False))
    fact_ids = {
        str(fact.get("fact_id") or "").strip()
        for fact in audited.get("fact_cells", [])
        if isinstance(fact, dict)
    }
    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    approved_pair_ids = []
    approved_fact_ids = []
    rejected_pair_ids = []
    held_pair_ids = []
    judge_notes = []

    for pair in audited.get("candidate_pairs", []):
        if not isinstance(pair, dict):
            continue
        pair_id = str(pair.get("pair_id") or "").strip()
        valid_fact_ids = [fid for fid in _dedupe_keep_order(pair.get("fact_ids", [])) if fid in fact_ids]
        subjective = pair.get("subjective", {}) if isinstance(pair.get("subjective"), dict) else {}
        confidence = float(subjective.get("confidence", 0.0) or 0.0)
        answer_policy = str(subjective.get("answer_policy") or "cautious")

        if not valid_fact_ids:
            pair["audit_status"] = "rejected"
            pair["audit_note"] = "Rejected because the claim is not anchored to any approved fact."
            if pair_id:
                rejected_pair_ids.append(pair_id)
            continue
        if answer_policy == "forbidden":
            pair["audit_status"] = "rejected"
            pair["audit_note"] = "Rejected because the answer policy explicitly forbids delivery."
            if pair_id:
                rejected_pair_ids.append(pair_id)
            continue
        if status == "INCOMPLETE":
            pair["audit_status"] = "needs_more_evidence"
            pair["audit_note"] = "Held because the investigation is still incomplete."
            if pair_id:
                held_pair_ids.append(pair_id)
            continue
        if status == "EXPANSION_REQUIRED":
            if answer_policy == "allowed" and confidence >= 0.8:
                pair["audit_status"] = "approved"
                pair["audit_note"] = "Approved cautiously because the claim is strongly supported despite expansion still being useful."
            else:
                pair["audit_status"] = "needs_more_evidence"
                pair["audit_note"] = "Held because more evidence is still needed before this claim can be delivered."
                if pair_id:
                    held_pair_ids.append(pair_id)
                continue
        else:
            if confidence >= 0.55 and answer_policy in {"allowed", "cautious"}:
                pair["audit_status"] = "approved"
                pair["audit_note"] = "Approved because the claim has enough confidence and an allowed delivery policy."
            else:
                pair["audit_status"] = "needs_more_evidence"
                pair["audit_note"] = "Held because the confidence is still too weak for delivery."
                if pair_id:
                    held_pair_ids.append(pair_id)
                continue

        if pair_id:
            approved_pair_ids.append(pair_id)
        approved_fact_ids.extend(valid_fact_ids)

    audited["final_pair_ids"] = _dedupe_keep_order(approved_pair_ids)
    audited["final_fact_ids"] = _dedupe_keep_order(approved_fact_ids) or _dedupe_keep_order(
        audited.get("final_fact_ids", [])
    )

    if status == "COMPLETED":
        judge_notes.append("The critic marked the case as complete.")
    elif status == "EXPANSION_REQUIRED":
        judge_notes.append("The critic requested more exploration before final delivery.")
    elif status == "INCOMPLETE":
        judge_notes.append("The critic marked the case as incomplete.")

    if audited["final_pair_ids"]:
        judge_notes.append("At least one advocate claim passed the final review.")
    elif audited["final_fact_ids"]:
        judge_notes.append("No advocate claim was fully approved, but the fact layer remains available.")
    else:
        judge_notes.append("The board still lacks enough grounded material for confident delivery.")

    verdict_board = _empty_verdict_board()
    verdict_board["approved_fact_ids"] = list(audited["final_fact_ids"])
    verdict_board["approved_pair_ids"] = list(audited["final_pair_ids"])
    verdict_board["rejected_pair_ids"] = _dedupe_keep_order(rejected_pair_ids)
    verdict_board["held_pair_ids"] = _dedupe_keep_order(held_pair_ids)
    verdict_board["requires_search"] = status == "EXPANSION_REQUIRED"
    verdict_board["answer_now"] = status == "COMPLETED" or bool(audited["final_fact_ids"])
    verdict_board["judge_notes"] = _dedupe_keep_order(judge_notes)
    verdict_board["final_answer_brief"] = str(
        audited.get("direct_answer_seed")
        or ((audited.get("advocate_report") or {}).get("summary_of_position") if isinstance(audited.get("advocate_report"), dict) else "")
        or ""
    ).strip()
    audited["verdict_board"] = verdict_board
    return audited


def _extract_achieved_findings_blob_from_memo(memo: str):
    text = str(memo or "").strip()
    if not text:
        return ""
    match = re.search(
        r"Achieved findings:\s*(.+?)(?=(?:\s+(?:Goal lock|Convergence|Next steps|Next frontier|Answer brief):)|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""
    return re.sub(r"\s+", " ", str(match.group(1) or "").strip())


def _memo_findings_brief_from_auditor_memo(
    memo: str,
    strategist_output: dict | None,
    analysis_data: dict | None,
):
    strategist_output = strategist_output if isinstance(strategist_output, dict) else {}
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    goal_lock = _normalize_goal_lock(strategist_output.get("goal_lock", {}))
    answer_shape = str(goal_lock.get("answer_shape") or "").strip()
    findings_blob = _extract_achieved_findings_blob_from_memo(memo)
    if not findings_blob:
        grounded = _normalize_short_string_list(_grounded_findings_from_analysis(analysis_data), limit=3)
        if not grounded:
            return ""
        findings_blob = " / ".join(grounded)
    if answer_shape == "proposal_1_to_3":
        return f"Based on the currently confirmed evidence, we can do this today: {findings_blob}"
    if answer_shape == "self_analysis_snapshot":
        return f"Based on recent dialogue, the clearest first-pass read is: {findings_blob}"
    if answer_shape in {"fit_summary", "feature_summary"}:
        return f"The evidence-backed points that best fit the current goal are: {findings_blob}"
    if answer_shape == "findings_first":
        return f"The direct findings available now are: {findings_blob}"
    if _extract_achieved_findings_blob_from_memo(memo):
        return findings_blob
    return ""


def _promote_auditor_memo_findings_to_reasoning_board(
    reasoning_board: dict | None,
    *,
    auditor_decision: dict | None,
    strategist_output: dict | None,
    analysis_data: dict | None,
):
    board = json.loads(json.dumps(reasoning_board, ensure_ascii=False)) if isinstance(reasoning_board, dict) else {}
    decision = auditor_decision if isinstance(auditor_decision, dict) else {}
    if str(decision.get("action") or "").strip() != "phase_3":
        return board
    memo = str(decision.get("memo") or "").strip()
    brief = _memo_findings_brief_from_auditor_memo(memo, strategist_output, analysis_data)
    if not brief:
        return board
    verdict_board = board.get("verdict_board", {})
    if not isinstance(verdict_board, dict):
        verdict_board = _empty_verdict_board()
    verdict_board["final_answer_brief"] = brief
    judge_notes = verdict_board.get("judge_notes", []) if isinstance(verdict_board.get("judge_notes"), list) else []
    judge_notes.append("The judge promoted memo-grounded findings into the final answer brief for phase 3 delivery.")
    verdict_board["judge_notes"] = _dedupe_keep_order([str(note).strip() for note in judge_notes if str(note).strip()])
    board["verdict_board"] = verdict_board
    return board


def _fallback_response_strategy(analysis_data: dict):
    evidences = analysis_data.get("evidences", []) if isinstance(analysis_data, dict) else []
    must_include = []
    if isinstance(evidences, list):
        for item in evidences[:3]:
            if isinstance(item, dict):
                fact = str(item.get("extracted_fact") or item.get("observed_fact") or item.get("excerpt") or "").strip()
            else:
                fact = str(item or "").strip()
            if fact:
                must_include.append(fact)
    must_include = _dedupe_keep_order(must_include)[:3]

    if must_include:
        answer_goal = "Answer directly from the strongest available facts."
        evidence_brief = " / ".join(must_include[:3])
        reasoning_brief = "Use the facts that actually support the answer and stay inside that boundary."
        direct_answer_seed = "Said narrowly from the confirmed evidence:"
        reply_mode = "grounded_answer"
    else:
        answer_goal = "Answer gently while making the current limit clear."
        evidence_brief = "Only weak or incomplete evidence is available."
        reasoning_brief = "Do not over-apologize; state the limit and ask a precise follow-up only if needed."
        direct_answer_seed = "With the evidence currently available, I cannot settle that yet."
        reply_mode = "cautious_minimal"

    return {
        "reply_mode": reply_mode,
        "delivery_freedom_mode": "grounded" if must_include else "clean_failure",
        "answer_goal": answer_goal,
        "tone_strategy": "Calm, direct, evidence-aware, and free of internal role explanation.",
        "evidence_brief": evidence_brief,
        "reasoning_brief": reasoning_brief,
        "direct_answer_seed": direct_answer_seed,
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "Do not invent unsupported facts.",
            "Do not overstate recent_context as confirmed evidence.",
            "Do not mention internal roles, judge packets, or stage workflows.",
        ],
        "answer_outline": [
            "Answer the user request directly.",
            "State limits briefly only when important.",
            "Ask one precise follow-up only when necessary.",
        ],
        "uncertainty_policy": "If evidence is weak, state the boundary instead of guessing.",
    }


def _force_findings_first_delivery_strategy(
    response_strategy: dict,
    s_thinking_packet: dict | None,
    fact_cells_for_strategist: list[dict] | None,
    user_input: str,
):
    del s_thinking_packet, fact_cells_for_strategist, user_input
    strategy = response_strategy if isinstance(response_strategy, dict) else {}
    return strategy


def _has_substantive_dialogue_anchor(user_input: str):
    return _has_substantive_dialogue_anchor_impl(user_input)


def _is_casual_social_turn(user_input: str):
    text = str(user_input or "").strip()
    lowered = unicodedata.normalize("NFKC", text).lower()
    if not text:
        return False
    if _is_artifact_review_turn(text) or _is_internal_reasoning_turn(text):
        return False
    if _is_assistant_question_request_turn(text) or _is_directive_or_correction_turn(text):
        return False
    if _has_substantive_dialogue_anchor(text):
        return False
    social_markers = ["hi", "hello", "thanks", "thank you", "lol", "haha", "\uc548\ub155", "\uace0\ub9c8\uc6cc", "\uc88b\uc544"]
    return len(text) <= 40 and any(marker in lowered for marker in social_markers)


def _is_positive_memory_feedback_turn(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text or "?" in text or len(text) > 80:
        return False
    memory_markers = ["remember", "memory", "\uae30\uc5b5"]
    praise_markers = ["good", "right", "nice", "\ub9de\uc544", "\uc88b\uc544", "\uc815\ud655"]
    return any(marker in text for marker in memory_markers) and any(marker in text for marker in praise_markers)


def _is_personal_experience_recall_turn(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    personal_markers = ["i ", "my ", "me ", "\ub098", "\ub0b4"]
    recall_markers = ["remember", "recall", "search", "\uae30\uc5b5", "\ucc3e\uc544", "\uac80\uc0c9"]
    return any(marker in text for marker in personal_markers) and any(marker in text for marker in recall_markers)


def _is_social_reentry_turn(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text or len(text) > 70:
        return False
    markers = ["back", "again", "long time", "\ub2e4\uc2dc", "\uc624\ub79c\ub9cc", "\ubcf5\uadc0"]
    return any(marker in text for marker in markers)


def _is_internal_reasoning_turn(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    explicit_lookup_markers = ["read", "file", "document", "log", "pptx", "\ubb38\uc11c", "\ud30c\uc77c"]
    if any(marker in text for marker in explicit_lookup_markers):
        return False
    serious_goal_markers = ["goal", "plan", "career", "project", "architecture", "\ubaa9\ud45c", "\uacc4\ud68d", "\ud504\ub85c\uc81d\ud2b8", "\uad6c\uc870"]
    reflective_markers = ["think", "analyze", "why", "how", "\uc0dd\uac01", "\ubd84\uc11d", "\uc65c", "\uc5b4\ub5bb\uac8c"]
    return any(marker in text for marker in serious_goal_markers + reflective_markers)


def _is_short_affirmation(user_input: str):
    return _is_short_affirmation_impl(user_input)


def _working_memory_expects_continuation(working_memory: dict):
    return _working_memory_expects_continuation_impl(working_memory)


def _working_memory_active_task(working_memory: dict):
    return _working_memory_active_task_impl(working_memory)


def _working_memory_active_offer(working_memory: dict):
    return _working_memory_active_offer_impl(working_memory)


def _working_memory_pending_dialogue_act(working_memory: dict):
    return _working_memory_pending_dialogue_act_impl(working_memory)


def _pending_dialogue_act_anchor(working_memory: dict):
    return _pending_dialogue_act_anchor_impl(working_memory)


def _pending_dialogue_act_accepts_current_turn(user_input: str, working_memory: dict):
    return _pending_dialogue_act_accepts_current_turn_impl(user_input, working_memory)


def _working_memory_writer_packet(working_memory: dict):
    return _working_memory_writer_packet_impl(working_memory)


def _llm_short_term_context_material(working_memory: dict):
    return _llm_short_term_context_material_impl(
        working_memory,
        looks_like_internal_phase3_seed=_looks_like_internal_phase3_seed,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _short_term_context_response_strategy(user_input: str, working_memory: dict):
    return _short_term_context_response_strategy_impl(
        user_input,
        working_memory,
        looks_like_internal_phase3_seed=_looks_like_internal_phase3_seed,
        compact_user_facing_summary=_compact_user_facing_summary,
    )


def _short_term_context_strategy_is_usable(response_strategy: dict | None, user_input: str, working_memory: dict):
    return _short_term_context_strategy_is_usable_impl(
        response_strategy,
        user_input,
        working_memory,
        looks_like_internal_phase3_seed=_looks_like_internal_phase3_seed,
        compact_user_facing_summary=_compact_user_facing_summary,
        has_meaningful_delivery_seed=_has_meaningful_delivery_seed,
    )


def _working_memory_direct_answer_seed(working_memory: dict):
    return _working_memory_direct_answer_seed_impl(working_memory)


def _working_memory_pending_question(working_memory: dict):
    return _working_memory_pending_question_impl(working_memory)


def _working_memory_last_assistant_answer(working_memory: dict):
    return _working_memory_last_assistant_answer_impl(working_memory)


def _recent_context_last_assistant_turn(recent_context: str):
    return _recent_context_last_assistant_turn_impl(
        recent_context,
        extract_recent_raw_turns_from_context=_extract_recent_raw_turns_from_context,
    )


def _previous_delivery_anchor(user_input: str, recent_context: str, working_memory: dict):
    return _previous_delivery_anchor_impl(
        user_input,
        recent_context,
        working_memory,
        extract_recent_raw_turns_from_context=_extract_recent_raw_turns_from_context,
        is_generic_continue_seed=_is_generic_continue_seed,
    )


def _is_retry_previous_answer_turn(user_input: str, recent_context: str, working_memory: dict):
    return _is_retry_previous_answer_turn_impl(
        user_input,
        recent_context,
        working_memory,
        extract_artifact_hint=_extract_artifact_hint,
        extract_explicit_search_keyword=_extract_explicit_search_keyword,
        is_assistant_investigation_request_turn=_is_assistant_investigation_request_turn,
        is_recent_dialogue_review_turn=_is_recent_dialogue_review_turn,
        is_directive_or_correction_turn=_shared_is_directive_or_correction_turn,
        extract_recent_raw_turns_from_context=_extract_recent_raw_turns_from_context,
        is_generic_continue_seed=_is_generic_continue_seed,
    )


def _working_memory_temporal_context(working_memory: dict):
    return _working_memory_temporal_context_impl(working_memory)


def _temporal_context_prefers_current_input(working_memory: dict):
    return _temporal_context_prefers_current_input_impl(working_memory)


def _temporal_context_allows_carry_over(working_memory: dict):
    return _temporal_context_allows_carry_over_impl(working_memory)


def _recent_hint_budget_from_working_memory(working_memory: dict):
    return _recent_hint_budget_from_working_memory_impl(working_memory)


def _raw_grounding_strength(raw_read_report: dict):
    if not isinstance(raw_read_report, dict):
        return "thin"
    items = raw_read_report.get("items", [])
    if not isinstance(items, list):
        return "thin"
    grounded_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        observed_fact = str(item.get("observed_fact") or "").strip()
        excerpt = str(item.get("excerpt") or "").strip()
        if observed_fact or excerpt:
            grounded_count += 1
    if grounded_count >= 3:
        return "strong"
    if grounded_count >= 1:
        return "medium"
    return "thin"



def _extract_artifact_hint(text: str):
    raw = str(text or "").strip()
    if not raw:
        return ""
    path_match = re.search(r'([A-Za-z]:\\[^"\']+\.(?:pptx|txt|md|json|py|docx))', raw, re.IGNORECASE)
    if path_match:
        return path_match.group(1).strip()
    file_match = re.search(r'([^\n\r"\']+\.(?:pptx|txt|md|json|py|docx))', raw, re.IGNORECASE)
    if file_match:
        return file_match.group(1).strip()
    lowered = raw.lower()
    if "anima" in lowered and ("artifact" in lowered or "document" in lowered):
        return "ANIMA artifact"
    return ""


def _is_artifact_review_turn(user_input: str):
    text = str(user_input or "").strip()
    if not text:
        return False
    artifact_hint = _extract_artifact_hint(text)
    if not artifact_hint:
        return False
    lowered = text.lower()
    review_markers = ["read", "review", "check", "inspect", "analyze", "\uc77d\uc5b4", "\uac80\ud1a0", "\ubd84\uc11d"]
    return any(marker in lowered for marker in review_markers) or any(ext in lowered for ext in [".pptx", ".txt", ".md", ".docx", ".json", ".py"])



def _artifact_instruction_from_text(text: str):
    artifact_hint = _extract_artifact_hint(text)
    if not artifact_hint:
        return ""
    return f'tool_read_artifact(artifact_hint={json.dumps(artifact_hint, ensure_ascii=False)})'



def _recent_context_invites_continuation(recent_context: str):
    return _recent_context_invites_continuation_impl(recent_context)


def _is_followup_ack_turn(user_input: str, recent_context: str):
    return _is_followup_ack_turn_impl(user_input, recent_context)


def _base_followup_context_expected(user_input: str, recent_context: str, working_memory: dict):
    return _base_followup_context_expected_impl(
        user_input,
        recent_context,
        working_memory,
        is_followup_offer_acceptance_turn=_is_followup_offer_acceptance_turn,
    )


def _casual_social_user_facing_seed(user_input: str):
    return _casual_social_user_facing_seed_impl(user_input)


def _social_turn_strategy(user_input: str):
    return _social_turn_strategy_impl(user_input)


def _user_turn_targets_assistant_reply(text: str, recent_context: str = ""):
    return _user_turn_targets_assistant_reply_impl(
        text,
        recent_context,
        extract_recent_raw_turns_from_context=_extract_recent_raw_turns_from_context,
    )

def _is_social_repair_turn(user_input: str, recent_context: str = "", working_memory: dict | None = None):
    return _is_social_repair_turn_impl(
        user_input,
        recent_context,
        working_memory,
        extract_artifact_hint=_extract_artifact_hint,
        is_directive_or_correction_turn=_shared_is_directive_or_correction_turn,
        extract_recent_raw_turns_from_context=_extract_recent_raw_turns_from_context,
    )


def _social_repair_strategy(user_input: str, recent_context: str, working_memory: dict):
    return _social_repair_strategy_impl(
        user_input,
        recent_context,
        working_memory,
        extract_recent_raw_turns_from_context=_extract_recent_raw_turns_from_context,
    )

def _ensure_social_turn_strategist_delivery(
    strategist_payload: dict,
    user_input: str,
    recent_context: str,
    working_memory: dict,
    analysis_data: dict,
):
    return _ensure_social_turn_strategist_delivery_impl(
        strategist_payload,
        user_input,
        recent_context,
        working_memory,
        analysis_data,
        normalize_action_plan=_normalize_action_plan,
        normalize_short_string_list=_normalize_short_string_list,
        has_meaningful_strategy=_has_meaningful_strategy,
        has_meaningful_delivery_seed=_has_meaningful_delivery_seed,
        looks_like_generic_non_answer_text=_looks_like_generic_non_answer_text,
        looks_like_user_parroting_report=_looks_like_user_parroting_report,
        is_social_repair_turn=_is_social_repair_turn,
        is_casual_social_turn=_is_casual_social_turn,
        is_persona_preference_turn=_is_persona_preference_turn,
        is_retry_previous_answer_turn=_is_retry_previous_answer_turn,
        is_directive_or_correction_turn=_is_directive_or_correction_turn,
        recent_context_last_assistant_turn=_recent_context_last_assistant_turn,
        social_repair_strategy=_social_repair_strategy,
        persona_preference_strategy=_persona_preference_strategy,
        social_turn_strategy=_social_turn_strategy,
    )


def _ensure_direct_delivery_response_strategy(
    strategist_payload: dict,
    user_input: str,
    recent_context: str,
    working_memory: dict,
    analysis_data: dict,
    start_gate_review: dict | None = None,
):
    return _ensure_direct_delivery_response_strategy_impl(
        strategist_payload,
        user_input,
        recent_context,
        working_memory,
        analysis_data,
        start_gate_review,
        has_meaningful_strategy=_has_meaningful_strategy,
        has_usable_response_seed=_has_usable_response_seed,
        normalize_action_plan=_normalize_action_plan,
        normalize_operation_plan=_normalize_operation_plan,
        empty_operation_plan=_empty_operation_plan,
        derive_operation_plan=_derive_operation_plan,
        fallback_response_strategy=_fallback_response_strategy,
        minimal_direct_dialogue_strategy=_minimal_direct_dialogue_strategy,
        normalize_short_string_list=_normalize_short_string_list,
    )


def _is_creative_story_request_turn(user_input: str) -> bool:
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    if _extract_artifact_hint(text):
        return False
    if _extract_explicit_search_keyword(text):
        return False
    if _is_assistant_investigation_request_turn(text):
        return False

    markers = [
        "\uc7ac\ubc0c\ub294 \uc598\uae30",
        "\uc7ac\ubc0c\ub294 \uc774\uc57c\uae30",
        "\uc6c3\uae34 \uc598\uae30",
        "\uc6c3\uae34 \uc774\uc57c\uae30",
        "\ub18d\ub2f4 \ud574\uc918",
        "\ub18d\ub2f4 \ud574\ubd10",
        "\uc37c \ud480\uc5b4\uc918",
        "\uc37c \ud480\uc5b4\ubd10",
        "funny story",
        "tell me something funny",
        "tell me a joke",
    ]
    if any(marker in text for marker in markers):
        return True

    return bool(re.search(r"(joke|story|anecdote)", text)) and any(
        token in text for token in ["funny", "short", "tell", "make me laugh"]
    )


def _creative_story_strategy(user_input: str, working_memory: dict):
    strategy = _base_minimal_direct_dialogue_strategy(user_input, working_memory)
    strategy["reply_mode"] = "generic_dialogue"
    strategy["delivery_freedom_mode"] = "supportive_free"
    strategy["answer_goal"] = "Let phase 3 answer the current creative request directly."
    return strategy


def _is_self_analysis_request_turn(user_input: str) -> bool:
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    self_markers = ["me", "myself", "about me", "\ub098", "\ub0b4", "\ub098\ub294"]
    analysis_markers = ["analyze", "analysis", "personality", "tendency", "\ubd84\uc11d", "\uc131\ud5a5", "\uc131\uaca9"]
    capability_markers = ["can you", "possible", "\uac00\ub2a5", "\ud560 \uc218"]
    return any(marker in text for marker in self_markers) and any(marker in text for marker in analysis_markers) and not any(marker in text for marker in capability_markers)


def _working_memory_user_model_delta(working_memory: dict):
    if not isinstance(working_memory, dict):
        return {}
    user_model = working_memory.get("user_model_delta", {})
    return user_model if isinstance(user_model, dict) else {}


def _self_analysis_grounded_clues(user_input: str, recent_context: str, working_memory: dict, limit: int = 4):
    clues = []
    user_text = str(user_input or "").strip()
    recent_turns = _extract_recent_raw_turns_from_context(recent_context, max_turns=8)
    recent_user_turns = [
        str(turn.get("content") or "").strip()
        for turn in recent_turns
        if isinstance(turn, dict) and str(turn.get("role") or "").strip().lower() == "user" and str(turn.get("content") or "").strip()
    ]
    user_model = _working_memory_user_model_delta(working_memory)
    observed_preferences = [str(item).strip() for item in user_model.get("observed_preferences", []) if str(item).strip()]
    friction_points = [str(item).strip() for item in user_model.get("friction_points", []) if str(item).strip()]
    if observed_preferences:
        clues.append("Working memory includes visible user preferences: " + " / ".join(observed_preferences[:2]))
    if friction_points:
        clues.append("Recent friction points: " + " / ".join(friction_points[:2]))
    if recent_user_turns:
        clues.append("Recent user context: " + _compact_user_facing_summary(" / ".join(recent_user_turns[-3:]), 220))
    if user_text:
        clues.append("Current self-analysis request: " + _compact_user_facing_summary(user_text, 160))
    return _normalize_short_string_list(clues, limit=limit)


def _self_analysis_snapshot_strategy(user_input: str, recent_context: str, working_memory: dict):
    user_text = str(user_input or "").strip()
    clues = _self_analysis_grounded_clues(user_input, recent_context, working_memory, limit=4)
    must_include = [f"Current self-analysis request: {user_text}"] if user_text else []
    must_include.extend(clues)
    clue_seed = " / ".join(clues[:3])
    return {
        "reply_mode": "grounded_answer",
        "delivery_freedom_mode": "grounded",
        "answer_goal": "Give a bounded, conversation-based snapshot of the user visible patterns right now.",
        "tone_strategy": "Warm, direct, and specific without pretending to know hidden private facts.",
        "evidence_brief": " / ".join(clues),
        "reasoning_brief": "Use only patterns visible in the current conversation and working memory.",
        "direct_answer_seed": f"From the visible conversation, the useful clues are: {clue_seed}",
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "Do not claim access to hidden private data.",
            "Do not give a deep psychological diagnosis.",
            "Do not ask the user to narrow the scope before giving a first-pass snapshot.",
        ],
        "answer_outline": [
            "State that this is conversation-based.",
            "Name the grounded visible patterns.",
            "Keep uncertainty honest.",
        ],
        "uncertainty_policy": "This is a first-pass read from visible conversation only.",
    }


def _capability_boundary_strategy(user_input: str, recent_context: str, working_memory: dict):
    user_text = str(user_input or "").strip()
    recent_turns = _extract_recent_raw_turns_from_context(recent_context, max_turns=6)
    user_model = _working_memory_user_model_delta(working_memory)
    evidence_state = working_memory.get("evidence_state", {}) if isinstance(working_memory, dict) else {}
    if not isinstance(evidence_state, dict):
        evidence_state = {}
    active_sources = [str(item).strip() for item in evidence_state.get("active_source_ids", []) if str(item).strip()]

    facts = [
        "This ANIMA runtime can search configured grounded records, including migrated Neo4j memory and date-specific diary reads, when the planner selects those tools.",
        "A capability answer is not itself a search; actual diary content requires a concrete search/read request and returned source.",
        "The assistant cannot access hidden offline private files or accounts outside the configured records.",
    ]
    if recent_turns:
        facts.append(f"{len(recent_turns)} recent raw turns are available for visible dialogue-pattern reading.")
    if active_sources:
        facts.append(f"Active grounded sources are available this turn: {' / '.join(active_sources[:2])}.")
    if user_model.get("observed_preferences"):
        facts.append("Working memory contains visible preferences or friction points from prior turns.")

    facts = _normalize_short_string_list(facts, limit=4)
    must_include = list(facts)

    return {
        "reply_mode": "grounded_answer",
        "delivery_freedom_mode": "grounded",
        "answer_goal": "Explain clearly how the assistant knows user information, what sources it can use, and where the boundary is.",
        "tone_strategy": "Direct, transparent, and calm. Explain the actual boundary without sounding helpless.",
        "evidence_brief": " / ".join(facts),
        "reasoning_brief": "This is a capability-boundary question, so the answer should explain what comes from explicit dialogue, working memory, and grounded sources, while denying hidden access.",
        "direct_answer_seed": "",
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "Do not claim access to hidden private data.",
            "Do not say diary search is impossible when the configured grounded tools can search migrated diary records.",
            "Do not use a helpless generic limitation template.",
            "Do not pretend the boundary question requires a search loop before answering.",
        ],
        "answer_outline": [
            "Explain what information sources are actually available now.",
            "State the privacy boundary clearly.",
            "Briefly add what kind of first-pass analysis is possible from those sources.",
        ],
        "uncertainty_policy": "Be transparent about the boundary, but still say what is already possible instead of stopping at 'I can't.'",
    }


def _is_self_analysis_detail_followup_turn(user_input: str, recent_context: str, working_memory: dict) -> bool:
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text or _is_self_analysis_request_turn(text):
        return False
    active_offer = _working_memory_active_offer(working_memory)
    active_task = _working_memory_active_task(working_memory)
    recent_assistant = _recent_context_last_assistant_turn(recent_context)
    anchor_blob = " ".join(
        part for part in [active_offer, active_task, recent_assistant] if isinstance(part, str) and part.strip()
    ).lower()
    if not anchor_blob:
        return False
    self_analysis_anchor_markers = ["pattern", "self-analysis", "conversation-based snapshot", "visible patterns", "\ud328\ud134", "\uc790\uae30\ubd84\uc11d"]
    if not any(marker in anchor_blob for marker in self_analysis_anchor_markers):
        return False
    detail_markers = ["detail", "specific", "why", "where", "evidence", "\uad6c\uccb4", "\uc790\uc138", "\uc65c", "\uc5b4\ub514", "\uadfc\uac70"]
    return any(marker in text for marker in detail_markers)


def _followup_ack_strategy(user_input: str, recent_context: str):
    del recent_context
    strategy = _base_minimal_direct_dialogue_strategy(user_input, {})
    strategy["reply_mode"] = "continue_previous_offer"
    strategy["delivery_freedom_mode"] = "proposal"
    strategy["answer_goal"] = "Use short-term context to continue the current conversational thread."
    return strategy


def _accepted_offer_execution_seed(active_offer: str):
    return _accepted_offer_execution_seed_impl(active_offer)


def _offer_acceptance_strategy(user_input: str, working_memory: dict):
    return _offer_acceptance_strategy_impl(user_input, working_memory)


def _retry_previous_answer_strategy(user_input: str, recent_context: str, working_memory: dict):
    return _retry_previous_answer_strategy_impl(
        user_input,
        recent_context,
        working_memory,
        extract_recent_raw_turns_from_context=_extract_recent_raw_turns_from_context,
        is_generic_continue_seed=_is_generic_continue_seed,
    )


def _is_identity_question_turn(user_input: str) -> bool:
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    markers = [
        "\ub10c \ub204\uad6c",
        "\ub124 \uc774\ub984",
        "\uc774\ub984\uc740",
        "\uc790\uae30\uc18c\uac1c",
        "who are you",
        "what is your name",
        "your name",
    ]
    return any(marker in text for marker in markers)


def _identity_dialogue_strategy(user_input: str, working_memory: dict):
    strategy = _base_minimal_direct_dialogue_strategy(user_input, working_memory)
    strategy["delivery_freedom_mode"] = "grounded"
    strategy["answer_goal"] = "Answer assistant-identity questions from approved context without claiming memory retrieval."
    strategy["must_include_facts"] = []
    return strategy


def _is_persona_preference_turn(user_input: str) -> bool:
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    if _extract_artifact_hint(text) or _extract_explicit_search_keyword(text):
        return False

    assistant_markers = [
        "\ub108",
        "\ub124\uac00",
        "\ub2c8\uac00",
        "\uc1a1\ub828",
        "you",
        "assistant",
    ]
    hypothetical_markers = [
        "\uc0ac\ub78c\uc774 \ub41c\ub2e4\uba74",
        "\uc0ac\ub78c \ub41c\ub2e4\uba74",
        "\uc778\uac04\uc774 \ub41c\ub2e4\uba74",
        "\uc778\uac04 \ub41c\ub2e4\uba74",
        "\uc0ac\ub78c\uc774\ub77c\uba74",
        "\uc778\uac04\uc774\ub77c\uba74",
        "\ub41c\ub2e4\uba74",
        "\ub9cc\uc57d",
        "if you were human",
        "if you became human",
    ]
    preference_markers = [
        "\ub418\uace0 \uc2f6",
        "\ub418\uace0\uc2f6",
        "\ud574\ubcf4\uace0 \uc2f6",
        "\ud574\ubcf4\uace0\uc2f6",
        "\uace0\ub974",
        "\uc120\ud0dd",
        "\uc5b4\ub290 \ucabd",
        "prefer",
        "would you rather",
        "want to be",
    ]
    persona_markers = [
        "\ub0a8\uc790",
        "\uc5ec\uc790",
        "\uc131\ubcc4",
        "\ubab8",
        "\uc721\uccb4",
        "gender",
        "male",
        "female",
    ]
    has_assistant_target = any(marker in text for marker in assistant_markers)
    has_hypothetical = any(marker in text for marker in hypothetical_markers)
    has_preference = any(marker in text for marker in preference_markers)
    has_persona_topic = any(marker in text for marker in persona_markers)
    return has_assistant_target and has_hypothetical and has_preference and has_persona_topic


def _persona_preference_strategy(user_input: str, working_memory: dict):
    strategy = _base_minimal_direct_dialogue_strategy(user_input, working_memory)
    strategy["reply_mode"] = "generic_dialogue"
    strategy["delivery_freedom_mode"] = "supportive_free"
    strategy["answer_goal"] = "Let phase 3 answer the current persona or hypothetical question without scripted preference text."
    return strategy


def _is_emotional_vent_turn(user_input: str, recent_context: str = "", working_memory: dict | None = None):
    del recent_context, working_memory
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text or "?" in text or _is_assistant_question_request_turn(text):
        return False
    if _extract_artifact_hint(text) or any(token in text for token in ["search ", "tool_", "schema", "db", "chat log"]):
        return False
    vent_markers = ["tired", "angry", "frustrated", "upset", "hurt", "exhausted", "\ud798\ub4e4", "\uc9dc\uc99d", "\ud654\ub098", "\uc18d\uc0c1", "\uace0\ub9bd", "\ub2f5\ub2f5"]
    return any(marker in text for marker in vent_markers)


def _supportive_empathy_strategy(user_input: str, recent_context: str, working_memory: dict):
    del recent_context
    strategy = _base_minimal_direct_dialogue_strategy(user_input, working_memory)
    strategy["delivery_freedom_mode"] = "supportive_free"
    strategy["answer_goal"] = "Let phase 3 respond naturally to the current user turn without scripted empathy text."
    return strategy


def _base_initiative_request_strategy(user_input: str, working_memory: dict):
    strategy = _base_minimal_direct_dialogue_strategy(user_input, working_memory)
    strategy["reply_mode"] = "continue_previous_offer"
    strategy["delivery_freedom_mode"] = "proposal"
    strategy["answer_goal"] = "Let phase 3 propose the next useful move from the available context."
    return strategy


def _assistant_question_seed(user_input: str, working_memory: dict):
    del user_input, working_memory
    return ""


def _clean_failure_response_strategy(user_input: str, war_room: dict):
    debt = war_room.get("epistemic_debt", {}) if isinstance(war_room, dict) else {}
    missing_items = debt.get("missing_items", []) if isinstance(debt, dict) else []
    if isinstance(missing_items, list):
        missing_items = [
            str(item).strip()
            for item in missing_items
            if str(item).strip() and not _looks_like_generic_non_answer_text(str(item))
        ]
    else:
        missing_items = []
    raw_next_best_action = str(debt.get("next_best_action") or "").strip()
    next_best_action = "" if _looks_like_generic_non_answer_text(raw_next_best_action) else raw_next_best_action
    why_tool_not_used = str(debt.get("why_tool_not_used") or "").strip()
    if _looks_like_generic_non_answer_text(why_tool_not_used):
        why_tool_not_used = ""

    missing_brief = _compact_user_facing_summary(missing_items[0], 180).rstrip(" .??!?") if missing_items else ""
    next_action_brief = _compact_user_facing_summary(next_best_action, 120) if next_best_action else ""

    must_include = ["State what is confirmed and what remains unconfirmed in natural language."]
    if missing_items:
        must_include.append(f"Unconfirmed: {', '.join(_compact_user_facing_summary(item, 90) for item in missing_items[:2])}")
    if next_best_action:
        must_include.append(f"Next check direction: {next_action_brief}")

    direct_seed = "With the evidence currently available, I cannot settle the whole request yet. I can name the boundary and the next check."
    if missing_items and next_action_brief:
        direct_seed = f"With the evidence currently available, I cannot settle this yet. Unconfirmed: {missing_brief}. Next check: {next_action_brief}."
    elif missing_items:
        direct_seed = f"With the evidence currently available, I cannot settle this yet. Unconfirmed: {missing_brief}."
    elif next_action_brief:
        direct_seed = f"I cannot settle this yet. The next check should be: {next_action_brief}."

    return {
        "reply_mode": "cautious_minimal",
        "delivery_freedom_mode": "clean_failure",
        "answer_goal": "State what can and cannot be confirmed right now, naturally.",
        "tone_strategy": "Not defensive or report-like; say the practical limit plainly.",
        "evidence_brief": f"current user request: {str(user_input or '').strip()}",
        "reasoning_brief": why_tool_not_used or "The currently retrieved evidence cannot safely verify every requested detail.",
        "direct_answer_seed": direct_seed,
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "Do not expose garbled or internal fallback wording.",
            "Do not expose internal next_best_action or judge wording.",
            "Do not pretend missing evidence is confirmed.",
        ],
        "answer_outline": [
            "Name the answerable boundary first.",
            "Name the unconfirmed part in one sentence.",
            "Suggest one next check direction if possible.",
        ],
        "uncertainty_policy": "The weaker the evidence, the narrower and more concrete the answer should be.",
    }


def _ask_user_question_strategy(user_input: str, working_memory: dict):
    active_task = _working_memory_active_task(working_memory)
    must_include = ["Ask the user one concrete question right now."]
    if active_task:
        must_include.append(f"current task context: {active_task}")

    return {
        "reply_mode": "ask_user_question_now",
        "delivery_freedom_mode": "proposal",
        "answer_goal": "Ask one question that immediately moves the conversation forward.",
        "tone_strategy": "Natural, focused, and specific.",
        "evidence_brief": f"current user request: {str(user_input or '').strip()}",
        "reasoning_brief": "The user wants the assistant to lead with the next question, not defer vaguely.",
        "direct_answer_seed": "",
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "Do not bounce the choice of question back to the user.",
            "Do not ask more than one core question.",
            "Do not replace the question with role explanation.",
        ],
        "answer_outline": [
            "Ask one concrete question.",
            "Tie it to the current conversation flow.",
        ],
        "uncertainty_policy": "If context is thin, choose the smallest useful question.",
    }


def _normalize_search_keyword(text: str):
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if _extract_artifact_hint(cleaned):
        return ""
    cleaned = re.sub(
        r"(previous answer|previous conversation|recent conversation|read again|check again)",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"(look up|search|check|tell me)$", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    if len(cleaned) > 60:
        return ""
    return cleaned or "recent"


def _looks_like_fake_tool_or_meta_string(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "").strip())
    if not normalized:
        return False

    lowered = normalized.lower()
    if lowered.startswith("tool_") and "(" not in lowered:
        return True

    meta_markers = [
        "tool_call_for_",
        "clarification_prompt",
        "goal lock:",
        "achieved findings:",
        "next frontier:",
        "next steps:",
        "instruction=",
        "operation contract",
        "response_strategy",
        "current_step_goal",
        "query_variant",
    ]
    return any(marker in lowered for marker in meta_markers)


def _normalize_suggested_instruction(suggestion: str):
    if not suggestion:
        return ""

    suggestion = str(suggestion).strip()
    if _looks_like_fake_tool_or_meta_string(suggestion):
        return ""

    exact = _extract_exact_tool_call(suggestion)
    if exact:
        return exact

    artifact_hint = _extract_artifact_hint(suggestion)
    if artifact_hint:
        return f'tool_read_artifact(artifact_hint={json.dumps(artifact_hint, ensure_ascii=False)})'

    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", suggestion)
    lowered = suggestion.lower()
    if date_match and any(token in suggestion for token in ["\uc77c\uae30", "diary"]):
        return f'tool_read_full_diary(target_date="{date_match.group(1)}")'
    if date_match and any(token in lowered for token in ["\ub300\ud654", "\ucc44\ud305", "chat", "log"]):
        return f'tool_scroll_chat_log(target_id="{date_match.group(1)}", direction="both", limit=15)'
    if any(token in lowered for token in ["schema", "db"]) or any(token in suggestion for token in ["\uc2a4\ud0a4\ub9c8", "\ub370\uc774\ud130\ubca0\uc774\uc2a4"]):
        return 'tool_scan_db_schema(dummy_keyword="database schema")'

    # Thin-controller mode: do not turn arbitrary planner/auditor prose such as
    # "plan_more" into a memory search. Tool calls must be explicit.
    return ""

def _build_direct_tool_message(instruction: str):
    if not instruction:
        return None

    stripped = str(instruction).strip()

    direct_name = None
    if stripped in {"tool_pass_to_phase_3", "tool_pass_to_phase_3()"}:
        direct_name = "tool_pass_to_phase_3"
    elif stripped in {"tool_call_119_rescue", "tool_call_119_rescue()"}:
        direct_name = "tool_call_119_rescue"

    allowed_tools = {tool.name for tool in available_tools}
    if direct_name and stripped.endswith(")"):
        return AIMessage(
            content="",
            tool_calls=[{"name": direct_name, "args": {}, "id": f"direct_{direct_name}"}]
        )
    if direct_name and "(" not in stripped:
        return AIMessage(
            content="",
            tool_calls=[{"name": direct_name, "args": {}, "id": f"direct_{direct_name}"}]
        )

    match = re.fullmatch(r"\s*(tool_[A-Za-z0-9_]+\s*\(.*\))\s*", stripped, re.DOTALL)
    if not match:
        return None

    try:
        expr = ast.parse(match.group(1), mode="eval").body
    except SyntaxError:
        return None

    if not isinstance(expr, ast.Call) or not isinstance(expr.func, ast.Name):
        return None

    tool_name = expr.func.id
    if tool_name not in allowed_tools or expr.args:
        return None

    args = {}
    for keyword in expr.keywords:
        if keyword.arg is None or not isinstance(keyword.value, ast.Constant):
            return None
        args[keyword.arg] = keyword.value.value

    return AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": args, "id": f"direct_{tool_name}"}]
    )

def _stable_action_signature(tool_name: str, tool_args: dict):
    return _stable_action_signature_impl(tool_name, tool_args)

def _has_meaningful_strategy(strategy_data: dict):
    if not isinstance(strategy_data, dict) or not strategy_data:
        return False
    keys = [
        "reply_mode",
        "answer_goal",
        "evidence_brief",
        "reasoning_brief",
        "direct_answer_seed",
    ]
    if any(str(strategy_data.get(key) or "").strip() for key in keys):
        return True
    return bool(strategy_data.get("must_include_facts") or strategy_data.get("answer_outline"))

def _anchor_terms(*texts):
    terms = set()
    for text in texts:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[가-힣]{2,}", str(text or "")):
            terms.add(token.lower())
    return terms

def _decision_uses_unanchored_topic(decision: dict, user_input: str, analysis_data: dict):
    if not isinstance(decision, dict):
        return False
    instruction = str(decision.get("instruction") or "").strip()
    if instruction in {"tool_pass_to_phase_3", "tool_pass_to_phase_3()", "tool_call_119_rescue", "tool_call_119_rescue()"}:
        return False
    candidate_texts = [
        instruction,
        json.dumps(decision.get("tool_args", {}), ensure_ascii=False),
    ]
    candidate_terms = _anchor_terms(*candidate_texts)
    if not candidate_terms:
        return False

    analysis_terms = []
    if isinstance(analysis_data, dict):
        analysis_terms.append(analysis_data.get("situational_brief", ""))
        analysis_terms.append(analysis_data.get("analytical_thought", ""))
        for item in analysis_data.get("evidences", []) or []:
            if isinstance(item, dict):
                analysis_terms.append(item.get("source_id", ""))
                analysis_terms.append(item.get("extracted_fact", ""))

    anchored = _anchor_terms(user_input, *analysis_terms)
    generic = {
        "tool", "phase", "search", "memory", "diary", "chat", "schema",
        "keyword", "target", "date", "both", "limit", "recent", "full",
    }
    unexpected = {term for term in candidate_terms if term not in anchored and term not in generic}
    return bool(unexpected)

def _soft_reasoning_budget_limit(reasoning_budget: int):
    try:
        base_budget = max(int(reasoning_budget or 0), 0)
    except (TypeError, ValueError):
        base_budget = 1
    return base_budget, base_budget + 1


def _normalize_progress_markers(markers: dict | None):
    return _normalize_progress_markers_impl(markers)


def _signature_digest(payload):
    return _signature_digest_impl(payload)


def _raw_progress_signature(raw_read_report: dict):
    return _raw_progress_signature_impl(raw_read_report)


def _analysis_progress_signature(analysis_data: dict):
    return _analysis_progress_signature_impl(analysis_data)


def _strategy_progress_signature(strategist_output: dict):
    return _strategy_progress_signature_impl(strategist_output)


def _normalize_execution_trace(trace: dict | None):
    return _normalize_execution_trace_impl(trace)


def _empty_tool_carryover_state():
    return _empty_tool_carryover_state_impl()


def _normalize_tool_carryover_state(carryover: dict | None):
    return _normalize_tool_carryover_state_impl(carryover)


def _source_id_looks_scrollable(source_id: str):
    return _source_id_looks_scrollable_impl(source_id)

def _text_mentions_gemini_chat(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    markers = [
        "gemini",
        "geminichat",
        "\uc81c\ubbf8\ub098\uc774",
        "\uc81c\ubbf8\ub098\uc774\ub300\ud654",
        "\uc81c\ubbf8\ub098\uc774 \ucc44\ud305",
    ]
    return any(marker in normalized for marker in markers)


def _source_ids_from_working_memory(working_memory: dict | None):
    return _source_ids_from_working_memory_impl(working_memory)


def _tool_carryover_from_working_memory(working_memory: dict | None):
    return _tool_carryover_from_working_memory_impl(working_memory)


def _tool_carryover_from_state(state: dict | None):
    return _tool_carryover_from_state_impl(state)


def _extract_source_ids_from_tool_result(result_str: str, exact_dates: list | None = None):
    return _extract_source_ids_from_tool_result_impl(result_str, exact_dates)


def _tool_query_from_args(tool_name: str, tool_args: dict | None):
    return _tool_query_from_args_impl(tool_name, tool_args)


def _update_tool_carryover_after_tool(
    state: dict | None,
    current_carryover: dict | None,
    tool_name: str,
    tool_args: dict | None,
    result_str: str,
    exact_dates: list | None = None,
):
    return _update_tool_carryover_after_tool_impl(
        state,
        current_carryover,
        tool_name,
        tool_args,
        result_str,
        exact_dates,
    )


def _tool_carryover_anchor_id(state_or_working_memory: dict | None):
    return _tool_carryover_anchor_id_impl(state_or_working_memory)

def _looks_like_scroll_followup_turn(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    scroll_markers = ["scroll", "nearby", "around", "before", "after", "\uc2a4\ud06c\ub864", "\uc8fc\ubcc0", "\uadfc\ucc98"]
    anchor_markers = ["that result", "that record", "target_id", "\uadf8 \uacb0\uacfc", "\uadf8 \uae30\ub85d", "\ubc29\uae08"]
    return any(marker in text for marker in scroll_markers) and (
        any(marker in text for marker in anchor_markers)
        or bool(re.search(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}", text))
    )


def _scroll_direction_from_user_input(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if any(marker in text for marker in ["both", "around", "nearby", "\uc8fc\ubcc0", "\uadfc\ucc98"]):
        return "both"
    if any(marker in text for marker in ["past", "before", "previous", "\uc774\uc804", "\uacfc\uac70"]):
        return "past"
    if any(marker in text for marker in ["future", "after", "next", "\ub2e4\uc74c", "\uc774\ud6c4"]):
        return "future"
    return "both"


def _scroll_tool_candidate_from_state(user_input: str, state: dict | None):
    if not _looks_like_scroll_followup_turn(user_input):
        return None
    anchor_id = _tool_carryover_anchor_id(state)
    if not anchor_id:
        return None
    return {
        "tool_name": "tool_scroll_chat_log",
        "tool_args": {
            "target_id": anchor_id,
            "direction": _scroll_direction_from_user_input(user_input),
            "limit": 20,
        },
        "memo": "ToolCarryoverState found an anchored source id, so scroll the same time-axis neighborhood instead of starting a new keyword search.",
    }


def _gemini_scroll_candidate_from_state(state: dict | None, memo: str = ""):
    state = state if isinstance(state, dict) else {}
    carryover = _tool_carryover_from_state(state)
    if str(carryover.get("last_tool") or "").strip() == "tool_scroll_chat_log":
        return None

    text_parts = [
        str(state.get("search_results") or ""),
        str(carryover.get("last_result_summary") or ""),
        str(carryover.get("last_query") or ""),
    ]
    raw_read_report = state.get("raw_read_report", {})
    if isinstance(raw_read_report, dict):
        text_parts.append(str(raw_read_report.get("source_summary") or ""))
        for item in raw_read_report.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            text_parts.append(str(item.get("source_type") or ""))
            text_parts.append(str(item.get("source_id") or ""))
            text_parts.append(str(item.get("excerpt") or item.get("observed_fact") or ""))

    if not _text_mentions_gemini_chat("\n".join(text_parts)):
        return None

    anchor_id = (
        str(carryover.get("origin_source_id") or "").strip()
        or str(carryover.get("last_target_id") or "").strip()
        or next((src for src in carryover.get("source_ids", []) if _source_id_looks_scrollable(src)), "")
    )
    if not anchor_id:
        return None

    args = {"target_id": anchor_id, "direction": "both", "limit": 20}
    executed_actions = state.get("executed_actions", [])
    if not isinstance(executed_actions, list):
        executed_actions = []
    if _stable_action_signature("tool_scroll_chat_log", args) in executed_actions:
        return None

    return _make_auditor_decision(
        "call_tool",
        memo=memo or (
            "A Gemini chat search hit is often fragmented, so scroll around the hit before treating it as irrelevant."
        ),
        tool_name="tool_scroll_chat_log",
        tool_args=args,
    )


def _analysis_needs_context_scroll(analysis_data: dict | None):
    if not isinstance(analysis_data, dict) or not analysis_data:
        return False
    status = str(analysis_data.get("investigation_status") or "").upper()
    if status in {"INCOMPLETE", "EXPANSION_REQUIRED"}:
        return True
    if bool(analysis_data.get("can_answer_user_goal") is False):
        return True
    return _analysis_reports_relevance_gap(analysis_data)


def _autonomous_scroll_candidate_from_state(state: dict | None, analysis_data: dict | None, memo: str = ""):
    """Carryover scroll never outranks the current user goal."""
    return None

def _enforce_autonomous_scroll_replan_directive(analysis_dict: dict, state: dict | None, raw_read_report: dict):
    if not isinstance(analysis_dict, dict):
        return analysis_dict
    temp_state = dict(state or {})
    temp_state["raw_read_report"] = raw_read_report if isinstance(raw_read_report, dict) else {}
    temp_state["analysis_report"] = analysis_dict
    candidate = _autonomous_scroll_candidate_from_state(
        temp_state,
        analysis_dict,
        memo="2b judged the current hit insufficient; next strategy should inspect the carried source neighborhood.",
    )
    if not candidate:
        return analysis_dict

    args = candidate.get("tool_args", {}) if isinstance(candidate.get("tool_args"), dict) else {}
    target_id = str(args.get("target_id") or "").strip()
    direction = str(args.get("direction") or "both").strip()
    limit = str(args.get("limit") or 20).strip()
    directive = (
        "The current FieldMemo candidates did not directly fill the goal slot, but a scrollable source id is available. "
        f"Next, read the source neighborhood with tool_scroll_chat_log(target_id={target_id!r}, "
        f"direction={direction!r}, limit={limit}) rather than widening the keyword search."
    )
    previous = str(analysis_dict.get("replan_directive_for_strategist") or "").strip()
    analysis_dict["replan_directive_for_strategist"] = directive if not previous else f"{previous}\n{directive}"
    if str(analysis_dict.get("investigation_status") or "").upper() == "COMPLETED" and not _analysis_has_answer_relevant_evidence(analysis_dict):
        analysis_dict["investigation_status"] = "EXPANSION_REQUIRED"
    return analysis_dict


def _operation_contract_from_action_plan(action_plan: dict | None):
    return _operation_contract_from_action_plan_impl(action_plan)


def _derive_operation_contract(
    user_input: str,
    action_plan: dict | None,
    response_strategy: dict | None = None,
    analysis_data: dict | None = None,
):
    normalized_action_plan = _normalize_action_plan(action_plan if isinstance(action_plan, dict) else {})
    existing = _normalize_operation_contract(normalized_action_plan.get("operation_contract", {}))
    if existing.get("operation_kind") != "unspecified":
        return existing

    response_strategy = response_strategy if isinstance(response_strategy, dict) else {}
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    required_tool = str(normalized_action_plan.get("required_tool") or "").strip()
    query_variant = _tool_query_from_instruction(required_tool) if required_tool else ""
    target_scope = ""
    novelty_requirement = "If this pass repeats the same tool or source, change the focus or target scope."
    del user_input

    if "tool_read_artifact" in required_tool:
        operation_kind = "read_same_source_deeper"
        target_scope = "artifact_review"
    elif "tool_scroll_chat_log" in required_tool:
        operation_kind = "read_same_source_deeper"
        target_scope = "anchored_chat_log_scroll"
        novelty_requirement = "Use ToolCarryoverState's source id as the time-axis origin and read a different neighborhood than the previous pass."
    elif "tool_read_full_diary" in required_tool:
        operation_kind = "review_personal_history"
        target_scope = "past_self_history"
    elif "tool_search_memory" in required_tool or "tool_search_field_memos" in required_tool:
        operation_kind = "search_new_source"
        target_scope = "memory_search"
    elif "tool_scan_db_schema" in required_tool:
        operation_kind = "search_new_source"
        target_scope = "database_schema"
    elif _has_meaningful_strategy(response_strategy):
        operation_kind = "deliver_now"
        target_scope = "direct_answer"
        novelty_requirement = "Do not bounce the user back with the same generic safety line."
    elif str((analysis_data or {}).get("investigation_status") or "").upper() == "COMPLETED":
        operation_kind = "deliver_now"
        target_scope = "grounded_delivery"
    else:
        operation_kind = "unspecified"

    return _normalize_operation_contract({
        "operation_kind": operation_kind,
        "target_scope": target_scope,
        "query_variant": query_variant,
        "novelty_requirement": novelty_requirement if operation_kind != "unspecified" else "",
    })


def _operation_contract_signature(operation_contract: dict | None):
    return _operation_contract_signature_impl(operation_contract)


def _execution_trace_signature(execution_trace: dict | None):
    return _execution_trace_signature_impl(execution_trace)


def _with_execution_trace_contract(execution_trace: dict | None, operation_contract: dict | None):
    return _with_execution_trace_contract_impl(execution_trace, operation_contract)


def _same_tool_call_as_execution(decision: dict | None, execution_trace: dict | None):
    return _same_tool_call_as_execution_impl(decision, execution_trace)

def _advance_progress_markers(
    markers: dict | None,
    state: AnimaState,
    analysis_data: dict,
    strategist_output: dict,
    stage: str,
):
    return _advance_progress_markers_impl(
        markers,
        state,
        analysis_data,
        strategist_output,
        stage,
    )


def _analysis_refresh_signature(analysis_data: dict):
    return _analysis_refresh_signature_impl(analysis_data)


def _analysis_refresh_allowed(progress_markers: dict | None, analysis_data: dict):
    return _analysis_refresh_allowed_impl(progress_markers, analysis_data)


def _mark_analysis_refresh(progress_markers: dict | None, analysis_data: dict):
    return _mark_analysis_refresh_impl(progress_markers, analysis_data)


def _apply_progress_contract(
    decision: dict | None,
    *,
    stalled_repeats: int,
    same_operation_repeats: int,
    user_input: str,
    analysis_data: dict,
    strategist_output: dict,
    working_memory: dict,
    execution_trace: dict | None = None,
):
    return _apply_progress_contract_impl(
        decision,
        stalled_repeats=stalled_repeats,
        same_operation_repeats=same_operation_repeats,
        user_input=user_input,
        analysis_data=analysis_data,
        strategist_output=strategist_output,
        working_memory=working_memory,
        execution_trace=execution_trace,
    )


def _merge_strategy_audits(*audits: dict):
    return _merge_strategy_audits_impl(*audits)


def _build_strategy_arbitration_audit(
    state: AnimaState,
    strategist_output: dict,
    analysis_data: dict,
):
    return _build_strategy_arbitration_audit_impl(state, strategist_output, analysis_data)

def _decision_from_strategy_arbitration_audit(
    audit: dict,
    *,
    loop_count: int,
    reasoning_budget: int,
):
    return _decision_from_strategy_arbitration_audit_impl(
        audit,
        loop_count=loop_count,
        reasoning_budget=reasoning_budget,
    )

def _strategist_needs_refresh_from_analysis(strategist_output: dict, analysis_data: dict):
    if not isinstance(analysis_data, dict) or not analysis_data:
        return False
    if not isinstance(strategist_output, dict) or not strategist_output:
        return True

    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    if status != "COMPLETED":
        return False

    grounded_facts = _grounded_findings_from_analysis(analysis_data)
    if not grounded_facts:
        return False

    action_plan = _normalize_action_plan(strategist_output.get("action_plan", {}))
    response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    goal_lock = _normalize_goal_lock(strategist_output.get("goal_lock", {}))
    achieved_findings = _normalize_short_string_list(strategist_output.get("achieved_findings", []), limit=3)
    delivery_readiness = _normalize_delivery_readiness(strategist_output.get("delivery_readiness", ""))

    if _goal_lock_prefers_delivery_on_completed_findings(goal_lock) and not action_plan.get("required_tool"):
        return False

    if not achieved_findings:
        return True
    if delivery_readiness != "deliver_now" and not action_plan.get("required_tool"):
        return True
    if not _has_meaningful_strategy(response_strategy) and action_plan.get("operation_contract", {}).get("operation_kind") != "deliver_now":
        return True
    return False


def _valid_strategist_tool_request(tool_request: dict | None):
    return _valid_strategist_tool_request_impl(
        tool_request,
        allowed_tool_names={tool.name for tool in available_tools},
        repair_search_tool_request=_repair_search_tool_request,
    )


def _tool_request_payload_from_instruction(required_tool: str, rationale: str = ""):
    return _tool_request_payload_from_instruction_impl(
        required_tool,
        rationale=rationale,
        build_direct_tool_message=_build_direct_tool_message,
        valid_strategist_tool_request=_valid_strategist_tool_request,
    )


def _ensure_tool_request_in_strategist_payload(strategist_payload: dict):
    """DEPRECATED: F4 removed -1a tool_request authorship.

    This wrapper now delegates to the one-season compatibility no-op, which
    preserves legacy packets but never authors a new tool call.
    """
    return _ensure_tool_request_in_strategist_payload_impl(
        strategist_payload,
        valid_strategist_tool_request=_valid_strategist_tool_request,
        normalize_action_plan=_normalize_action_plan,
        tool_request_payload_from_instruction=_tool_request_payload_from_instruction,
    )


def _decision_from_strategist_tool_contract(strategist_output: dict, analysis_data: dict | None = None):
    return _decision_from_strategist_tool_contract_impl(
        strategist_output,
        analysis_data,
        ensure_tool_request_in_strategist_payload=_ensure_tool_request_in_strategist_payload,
        valid_strategist_tool_request=_valid_strategist_tool_request,
        analysis_has_answer_relevant_evidence=_analysis_has_answer_relevant_evidence,
        make_auditor_decision=_make_auditor_decision,
    )


def _clean_strategist_search_fragment(fragment: str):
    text = unicodedata.normalize("NFKC", str(fragment or "").strip())
    if not text:
        return ""
    text = text.strip(" \t\r\n\"'`.,!?()[]{}<>")
    text = re.sub(r"^\s*(?:please|just|once|search|find|look up)\s+", "", text, flags=re.IGNORECASE).strip()
    text = re.split(r"\s*(?:then|and then|result|results|tell me|explain|\uacb0\uacfc|\ub9d0\ud574|\uc54c\ub824)\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    text = re.sub(r"\s+", " ", text).strip(" \"'`.,!?()[]{}<>")
    if not text or len(text) > 90:
        return ""
    if _looks_like_fake_tool_or_meta_string(text):
        return ""
    return text

def _search_query_is_overbroad_or_instruction(query: str):
    text = unicodedata.normalize("NFKC", str(query or "").strip()).lower()
    if not text:
        return True
    if is_memory_state_disclosure_turn(text):
        return True
    if len(text) > 80:
        return True
    bad_markers = [
        "analyze", "explain", "tell me", "search for", "tool_",
        "current user turn", "respond to", "phase_", "answer_not_ready",
    ]
    return any(marker in text for marker in bad_markers)


def _repair_search_tool_request(tool_name: str, tool_args: dict | None, fallback_text: str = ""):
    normalized_tool_name = str(tool_name or "").strip()
    if normalized_tool_name not in {"tool_search_memory", "tool_search_field_memos"}:
        return None

    args = tool_args if isinstance(tool_args, dict) else {}
    arg_name = "query" if normalized_tool_name == "tool_search_field_memos" else "keyword"
    other_arg_name = "keyword" if arg_name == "query" else "query"
    raw_query = str(args.get(arg_name) or args.get(other_arg_name) or "").strip()
    cleaned = _clean_strategist_search_fragment(raw_query)
    if not cleaned or _search_query_is_overbroad_or_instruction(cleaned):
        return None

    repaired_args = dict(args)
    repaired_args[arg_name] = cleaned
    if normalized_tool_name == "tool_search_field_memos":
        try:
            repaired_args["limit"] = int(repaired_args.get("limit", 6) or 6)
        except (TypeError, ValueError):
            repaired_args["limit"] = 6
    return normalized_tool_name, repaired_args


def _deterministic_search_keyword_from_user_input(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    if not text:
        return ""

    quote_chars = "\"'`\u201c\u201d\u2018\u2019\u300c\u300d"
    quoted_candidates = re.findall(rf"[{re.escape(quote_chars)}](.{{1,80}}?)[{re.escape(quote_chars)}]", text)
    for quoted in reversed(quoted_candidates):
        cleaned = _clean_strategist_search_fragment(quoted)
        if cleaned:
            return cleaned

    search_match = re.search(r"\bSEARCH\s+(.+)", text, flags=re.IGNORECASE)
    if search_match:
        cleaned = _clean_strategist_search_fragment(search_match.group(1))
        if cleaned:
            return cleaned

    legacy_keyword = _extract_explicit_search_keyword(text)
    if legacy_keyword:
        cleaned = _clean_strategist_search_fragment(legacy_keyword)
        if cleaned:
            return cleaned

    return ""


def _deterministic_search_keywords_from_user_input(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    if not text:
        return []

    candidates = []
    quoted_candidates = re.findall(r"[\"'`“”‘’「」『』](.{1,80}?)[\"'`“”‘’「」『』]", text)
    candidates.extend(_clean_strategist_search_fragment(item) for item in quoted_candidates)

    split_parts = re.split(r"\s*(?:or|또는|혹은)\s+", text, flags=re.IGNORECASE)
    for part in split_parts:
        keyword = _deterministic_search_keyword_from_user_input(part)
        if keyword:
            candidates.append(keyword)

    primary = _deterministic_search_keyword_from_user_input(text)
    if primary:
        candidates.insert(0, primary)

    return _dedupe_keep_order(
        [
            candidate
            for candidate in candidates
            if candidate and not _search_query_is_overbroad_or_instruction(candidate)
        ]
    )[:4]


def _tool_query_from_instruction(instruction: str):
    text = str(instruction or "").strip()
    if not text:
        return ""

    exact = _extract_exact_tool_call(text) or text
    for key in ("query", "keyword", "artifact_hint", "target_id"):
        patterns = [
            rf"{key}\s*=\s*['\"]([^'\"]{{1,120}})['\"]",
            rf"['\"]{key}['\"]\s*:\s*['\"]([^'\"]{{1,120}})['\"]",
        ]
        for pattern in patterns:
            matched = re.search(pattern, exact)
            if matched:
                cleaned = _clean_strategist_search_fragment(matched.group(1))
                if cleaned:
                    return cleaned
    return ""


def _memory_query_stopwords():
    return {
        "the", "and", "or", "to", "for", "with", "about", "this", "that",
        "please", "search", "remember", "recall", "directly", "question",
        "answer", "user", "assistant", "query", "keyword", "profile",
        "\ub124\uac00", "\ub0b4\uac00", "\ub098\ub294", "\ub09c", "\ub0b4",
        "\uadf8\ub54c", "\uadf8\uac8c", "\uadf8\uac83", "\uadf8\uac70",
        "\uadf8", "\uadf8\ub7f0", "\uadf8\ub7fc", "\uc544\uae4c",
        "\ubc29\uae08", "\uc774\uc804", "\uc704", "\uc9c1\uc811",
        "\uc0c1\ud669", "\uc0ac\uac74", "\uc7a5\uba74", "\uae30\uc5b5",
        "\ud68c\uc0c1", "\ub5a0\uc62c\ub824", "\ub5a0\uc62c\ub824\ubd10",
        "\ub9d0\ud574", "\ub9d0\ud574\ubd10", "\uc54c\ub824", "\ucc3e\uc544",
        "\ucc3e\uc544\ubd10", "\uac80\uc0c9", "\uac80\uc0c9\ud574",
        "\uc9c8\ubb38", "\ub2f5\ubcc0", "\ud574\ubd10", "\ud574",
        "\ub2f5\ud574", "\ud55c\ub2e4",
        "\ub2e4\uc2dc", "\uc81c\ub300\ub85c", "\uc544\ub294\ub9cc\ud07c",
        "\uc5b4\ub5bb\uac8c", "\ud588\uc744\uac70", "\ud588\uc744\uac70\uc57c",
        "\ud588\uc744", "\uac70\uc57c", "\uacbd\uc6b0", "\ubc14\ud0d5",
        "\uc804\ubd80", "\uc9c0\uae08", "\ud604\uc7ac", "\ub4f1\uc7a5\uc778\ubb3c",
        "\uadf8\ub54c\uc758", "\uc0c1\ud669\uc744", "\uc9c1\uc811",
    }


def _strip_korean_search_suffix(token: str):
    text = str(token or "").strip()
    suffixes = [
        "\uc774\uc5c8\ub2e4\uba74", "\uc774\uc5c8\ub2e4", "\uc774\ub77c\uba74",
        "\uc774\ub77c\uace0", "\uc774\ub77c\ub294", "\uc600\ub2e4\uba74",
        "\uc600\ub2e4", "\ub77c\uba74", "\ub77c\uace0", "\ub77c\ub294",
        "\uc5d0\uc11c", "\uc5d0\uac8c", "\uc73c\ub85c", "\ub85c",
        "\uc640", "\uacfc", "\uc740", "\ub294", "\uc774", "\uac00",
        "\uc744", "\ub97c", "\uc5d0", "\ub3c4", "\ub9cc", "\uc57c", "\uc544",
    ]
    changed = True
    while changed:
        changed = False
        for suffix in suffixes:
            if len(text) - len(suffix) >= 2 and text.endswith(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
                break
    return text


def _extract_search_anchor_terms_from_text(text: str, max_terms: int = 8):
    normalized = unicodedata.normalize("NFKC", str(text or "").strip())
    if not normalized:
        return []

    stopwords = _memory_query_stopwords()
    raw_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_\-]{1,24}|[0-9]{2,}|[\uac00-\ud7a3]{2,24}", normalized)
    terms = []
    for raw in raw_tokens:
        token = raw.strip()
        lowered = token.lower()
        if lowered in stopwords:
            continue
        if re.search(r"[\uac00-\ud7a3]", token):
            token = _strip_korean_search_suffix(token)
            lowered = token.lower()
        if not token or len(token) < 2 or lowered in stopwords:
            continue
        if _looks_like_fake_tool_or_meta_string(token):
            continue
        terms.append(token)
    return _dedupe_keep_order(terms)[:max_terms]


def _query_from_anchor_terms(terms, max_chars: int = 60):
    selected = []
    for term in terms or []:
        candidate = " ".join(selected + [str(term).strip()])
        if len(candidate) > max_chars:
            break
        selected.append(str(term).strip())
    query = " ".join(term for term in selected if term).strip()
    if not query or _search_query_is_overbroad_or_instruction(query):
        return ""
    return query


def _looks_like_deictic_memory_query(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "").strip()).lower()
    if not normalized:
        return False
    compact = re.sub(r"\s+", "", normalized)
    deictic_markers = [
        "\uadf8\ub54c", "\uadf8\uc0ac\uac74", "\uadf8\uc0c1\ud669",
        "\uadf8\uc7a5\uba74", "\uadf8\uac8c", "\uc544\uae4c", "\ubc29\uae08",
        "\uc774\uc804", "\uc704\uc5d0\uc11c", "that", "previous",
    ]
    recall_markers = [
        "\uae30\uc5b5", "\ud68c\uc0c1", "\ub5a0\uc62c", "\uc0dd\uac01",
        "\ub9d0\ud574", "\uc54c\ub824", "remember", "recall",
    ]
    if not any(marker in compact or marker in normalized for marker in deictic_markers):
        return False
    if not any(marker in compact or marker in normalized for marker in recall_markers):
        return False
    anchor_terms = _extract_search_anchor_terms_from_text(normalized, max_terms=4)
    return len(anchor_terms) <= 2


def _tool_call_already_executed(decision: dict | None, state: dict | None):
    if not isinstance(decision, dict):
        return False
    tool_name = str(decision.get("tool_name") or "").strip()
    tool_args = decision.get("tool_args", {}) if isinstance(decision.get("tool_args"), dict) else {}
    if not tool_name:
        return False
    executed_actions = state.get("executed_actions", []) if isinstance(state, dict) else []
    if not isinstance(executed_actions, list):
        executed_actions = []
    signature = _stable_action_signature(tool_name, tool_args)
    if signature in executed_actions:
        return True
    return _same_tool_call_as_execution(decision, state.get("execution_trace", {}) if isinstance(state, dict) else {})


def _next_alternative_search_decision(user_input: str, state: dict | None, current_decision: dict | None, memo: str = ""):
    if not isinstance(current_decision, dict):
        return None
    current_tool = str(current_decision.get("tool_name") or "").strip()
    current_args = current_decision.get("tool_args", {}) if isinstance(current_decision.get("tool_args"), dict) else {}
    if current_tool != "tool_search_memory":
        return None

    current_keyword = str(current_args.get("keyword") or current_args.get("query") or "").strip()
    executed_actions = state.get("executed_actions", []) if isinstance(state, dict) else []
    if not isinstance(executed_actions, list):
        executed_actions = []

    for keyword in _deterministic_search_keywords_from_user_input(user_input):
        if not keyword or keyword == current_keyword:
            continue
        args = {"keyword": keyword}
        if _stable_action_signature("tool_search_memory", args) in executed_actions:
            continue
        return _make_auditor_decision(
            "call_tool",
            memo=memo or f"The first search candidate '{current_keyword}' was checked; continue with the user-provided alternative keyword '{keyword}'.",
            tool_name="tool_search_memory",
            tool_args=args,
        )
    return None


def _turn_requests_relation_or_synthesis(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    markers = [
        "\uad00\uacc4", "\uc720\ucd94", "\ucd94\ub860", "\ud574\uc11d", "\ud310\ub2e8",
        "\uc815\uccb4\uc131", "\uc885\ud569", "infer", "relationship", "synthesize", "interpret",
    ]
    return any(marker in text for marker in markers)


def _looks_like_current_turn_personal_fact_share(user_input: str) -> bool:
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    if not text:
        return False
    lowered = text.lower()
    compact = re.sub(r"\s+", "", lowered)

    first_person_markers = [
        "\ub0b4\uac00",
        "\ub098\ub294",
        "\ub09c",
        "\ub0b4\uac8c",
        "\ub098\uc5d0\uac8c",
        "i ",
        "i'",
        "my ",
    ]
    if not any(marker in compact or marker in lowered for marker in first_person_markers):
        return False

    retrieval_markers = [
        "\uae30\uc5b5",
        "\uac80\uc0c9",
        "\ucc3e\uc544",
        "\ub9d0\ud574\ubd10",
        "\uc54c\ub824",
        "\ubd84\uc11d",
        "\uc720\ucd94",
        "search",
        "remember",
        "recall",
    ]
    if any(marker in compact or marker in lowered for marker in retrieval_markers):
        return False

    disclosure_markers = [
        "\ud588\uac70\ub4e0",
        "\ud588\uc5b4",
        "\ud588\ub2e4",
        "\ud574\ubd24",
        "\ub118\uac8c",
        "\uc2dc\uac04",
        "\uc88b\uc544",
        "\uc2eb\uc5b4",
        "\ubcf4\uace0",
        "\ubcf4\uba74",
        "played",
        "hours",
        "like",
        "love",
        "hate",
    ]
    return bool(re.search(r"\d", text) or any(marker in compact or marker in lowered for marker in disclosure_markers))


def _looks_like_current_turn_memory_story_share(user_input: str) -> bool:
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    if not text or "?" in text:
        return False
    lowered = text.lower()
    request_markers = ["remember", "recall", "search", "find", "\uae30\uc5b5\ud574", "\ucc3e\uc544", "\uac80\uc0c9"]
    if any(marker in lowered for marker in request_markers):
        return False
    story_markers = ["when i", "back then", "as a kid", "\uc5b4\ub9b4", "\uadf8\ub54c", "\uc608\uc804", "\uc720\uce58\uc6d0", "\ud559\uad50"]
    first_person_markers = [" i ", " my ", "\ub098", "\ub0b4", "\ub0b4\uac00"]
    has_story_signal = any(marker in lowered for marker in story_markers)
    has_personal_signal = any(marker in lowered for marker in first_person_markers)
    return bool((has_story_signal and has_personal_signal) or (len(text) >= 45 and has_personal_signal))


def _base_fallback_strategist_output(
    user_input: str,
    s_thinking_packet: dict | None,
    working_memory: dict,
    reasoning_board: dict,
    fact_cells_for_strategist: list[dict] | None = None,
    recent_context: str = "",
    start_gate_switches: dict | None = None,
    tool_carryover: dict | None = None,
):
    handoff = s_thinking_packet if isinstance(s_thinking_packet, dict) else {}
    facts = []
    for cell in fact_cells_for_strategist or []:
        if not isinstance(cell, dict):
            continue
        fact = str(cell.get("extracted_fact") or "").strip()
        if fact:
            facts.append(fact)
    if not facts:
        facts = [
            str(item or "").strip()
            for item in handoff.get("what_we_know", []) or []
            if str(item or "").strip()
        ][:8]
    missing = [
        str(item or "").strip()
        for item in handoff.get("what_is_missing", []) or []
        if str(item or "").strip()
    ][:8]
    synthetic_case = {
        "investigation_status": "COMPLETED" if facts else ("INCOMPLETE" if missing else ""),
        "situational_brief": str(handoff.get("goal_state") or "").strip(),
        "analytical_thought": str(handoff.get("next_node_reason") or handoff.get("evidence_state") or "").strip(),
        "evidences": [
            {
                "source_id": str((cell or {}).get("source_id") or (cell or {}).get("fact_id") or f"fact_{idx + 1}").strip(),
                "source_type": str((cell or {}).get("source_type") or "thinking_handoff").strip(),
                "extracted_fact": fact,
            }
            for idx, (fact, cell) in enumerate(zip(facts, (fact_cells_for_strategist or []) + [{}] * len(facts)))
        ],
        "usable_field_memo_facts": facts,
        "missing_slots": missing,
        "can_answer_user_goal": bool(facts),
        "contract_status": "satisfied" if facts else "missing_evidence",
    }
    status = str(synthetic_case.get("investigation_status") or "").upper()
    case_theory = (
        str(synthetic_case.get("situational_brief") or "").strip()
        or str(synthetic_case.get("analytical_thought") or "").strip()
        or "The case still needs a clearer operating theory before delivery."
    )
    start_gate_switches = start_gate_switches if isinstance(start_gate_switches, dict) else {}
    start_gate_goal_contract = start_gate_switches.get("goal_contract", {})
    goal_lock = start_gate_goal_contract if isinstance(start_gate_goal_contract, dict) and start_gate_goal_contract else _derive_goal_lock_v2(user_input, {})
    answer_mode_policy = start_gate_switches.get("answer_mode_policy", {})
    if not isinstance(answer_mode_policy, dict) or not answer_mode_policy:
        answer_mode_policy = _answer_mode_policy_for_turn(user_input, recent_context, goal_lock)
    current_turn_facts = list(start_gate_switches.get("current_turn_facts", []) or [])
    if not current_turn_facts:
        current_turn_facts = _extract_current_turn_grounding_facts(user_input, goal_lock)
    policy_allows_direct = _answer_mode_policy_allows_direct_phase3(answer_mode_policy)
    question_class = str(answer_mode_policy.get("question_class") or "").strip()
    capability_boundary_strategy = (
        _capability_boundary_strategy(user_input, recent_context, working_memory)
        if question_class == "capability_boundary_question"
        else None
    )
    response_strategy = None
    short_context_strategy = _short_term_context_response_strategy(user_input, working_memory)
    needs_tool_operation = bool(
        status in {"", "EXPANSION_REQUIRED", "INCOMPLETE"}
        and not policy_allows_direct
        and not capability_boundary_strategy
        and not short_context_strategy
    )

    if needs_tool_operation:
        action_plan = {
            "current_step_goal": "Ask phase 0 to convert the operation contract into one safe tool call.",
            "required_tool": "",
            "next_steps_forecast": [
                "Re-run phase 2 on the newly gathered source.",
                "Update the goal lock and achieved findings after the gap is reduced.",
                "Deliver the final answer only when the grounded findings clearly answer the current ask.",
            ],
            "operation_contract": {
                "operation_kind": "search_new_source",
                "target_scope": "memory_or_source_search",
                "query_variant": "",
                "novelty_requirement": "Phase 0 must choose an exact query from the current operation contract, not from raw user wording.",
            },
        }
    else:
        if capability_boundary_strategy:
            response_strategy = capability_boundary_strategy
        elif policy_allows_direct:
            response_strategy = _response_strategy_from_answer_mode_policy(user_input, answer_mode_policy, current_turn_facts)
        else:
            response_strategy = short_context_strategy or _fallback_response_strategy(synthetic_case)
        if capability_boundary_strategy:
            current_step_goal = "Explain the assistant's current memory/source access boundary without opening a search loop."
            next_steps = [
                "Describe what sources can be used when the system actually executes tools.",
                "State that no search has been performed yet on this turn.",
                "Invite a concrete query only if the user wants an actual search next.",
            ]
        elif short_context_strategy and not policy_allows_direct:
            current_step_goal = "Answer from LLM-authored short-term context and fulfill any pending conversational obligation."
            next_steps = [
                "Use the short-term context as conversational context only.",
                "Do not reopen a search loop unless the user explicitly asks for retrieval.",
                "If context is insufficient, ask one concrete clarifying question.",
            ]
        else:
            current_step_goal = _goal_locked_delivery_step_goal(goal_lock)
            next_steps = [
                "If the user pushes back, inspect the exact weak point instead of bluffing.",
                "If a new gap appears, hand the case back to phase 2 for another read.",
            ]
        action_plan = {
            "current_step_goal": current_step_goal,
            "required_tool": "",
            "next_steps_forecast": next_steps,
        }

    has_grounded_findings = bool(status == "COMPLETED" and _grounded_findings_from_analysis(synthetic_case))
    short_context_deliverable = bool(short_context_strategy and not needs_tool_operation)
    deliverable_now = bool(
        policy_allows_direct
        or has_grounded_findings
        or short_context_deliverable
        or capability_boundary_strategy
    )

    strategist_output = {
        "case_theory": case_theory,
        "answer_mode_policy": answer_mode_policy,
        "operation_plan": _derive_operation_plan(
            user_input,
            synthetic_case,
            action_plan,
            response_strategy if isinstance(response_strategy, dict) else {},
            working_memory,
        ),
        "goal_lock": goal_lock,
        "convergence_state": "deliverable" if deliverable_now else "gathering",
        "achieved_findings": _grounded_findings_from_analysis(synthetic_case),
        "delivery_readiness": "deliver_now" if deliverable_now else ("need_one_more_source" if needs_tool_operation else "need_reframe"),
        "next_frontier": list(action_plan.get("next_steps_forecast", [])),
        "action_plan": action_plan,
        "response_strategy": response_strategy,
        "war_room_contract": _derive_war_room_operating_contract(
            user_input,
            synthetic_case,
            action_plan,
            response_strategy if isinstance(response_strategy, dict) else {},
        ),
        "candidate_pairs": [],
    }
    strategist_output = _sanitize_strategist_goal_fields(
        strategist_output,
        user_input,
        start_gate_switches,
    )
    reasoning_board = _apply_strategist_output_to_reasoning_board(reasoning_board, strategist_output)
    return strategist_output, reasoning_board


def _base_phase_minus_1a_thinker(state: AnimaState):
    return _run_base_phase_minus_1a_thinker(
        state,
        llm=llm,
        strategist_reasoning_output_schema=StrategistReasoningOutput,
        build_phase_minus_1a_prompt=build_phase_minus_1a_prompt,
        normalize_war_room_state=_normalize_war_room_state,
        working_memory_packet_for_prompt=_working_memory_packet_for_prompt,
        war_room_packet_for_prompt=_war_room_packet_for_prompt,
        answer_mode_policy_from_state=_answer_mode_policy_from_state,
        answer_mode_policy_packet_for_prompt=_answer_mode_policy_packet_for_prompt,
        evidence_ledger_for_prompt=evidence_ledger_for_prompt,
        fallback_strategist_output=_base_fallback_strategist_output,
        force_findings_first_delivery_strategy=_force_findings_first_delivery_strategy,
        war_room_after_advocate=_war_room_after_advocate,
        sanitize_strategist_goal_fields=_sanitize_strategist_goal_fields,
        apply_strategist_output_to_reasoning_board=_apply_strategist_output_to_reasoning_board,
        print_fn=print,
    )

def _planned_operation_contract_from_state(state: AnimaState):
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    action_plan = _normalize_action_plan(strategist_output.get("action_plan", {}))
    response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    analysis_data = state.get("analysis_report", {})
    if not isinstance(analysis_data, dict):
        analysis_data = {}
    return _derive_operation_contract(
        str(state.get("user_input") or ""),
        action_plan,
        response_strategy=response_strategy,
        analysis_data=analysis_data,
    )


def _execution_trace_after_supervisor(state: AnimaState, tool_name: str = "", tool_args: dict | None = None):
    trace = _with_execution_trace_contract(state.get("execution_trace", {}), _planned_operation_contract_from_state(state))
    trace["executed_tool"] = str(tool_name or "").strip()
    trace["tool_args_signature"] = _signature_digest(tool_args if isinstance(tool_args, dict) else {})
    return trace


def _execution_trace_after_phase2a(state: AnimaState, raw_read_report: dict):
    trace = _with_execution_trace_contract(state.get("execution_trace", {}), _planned_operation_contract_from_state(state))
    raw_read_report = raw_read_report if isinstance(raw_read_report, dict) else {}
    trace["read_mode"] = str(raw_read_report.get("read_mode") or "").strip()
    trace["read_focus"] = trace.get("target_scope") or trace.get("operation_kind") or trace.get("read_mode")
    items = raw_read_report.get("items", [])
    if not isinstance(items, list):
        items = []
    source_ids = []
    for item in items:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id") or "").strip()
        if source_id:
            source_ids.append(source_id)
    trace["source_ids"] = _dedupe_keep_order(source_ids)[:8]
    return trace


def _execution_trace_after_phase2b(state: AnimaState, analysis_data: dict):
    trace = _with_execution_trace_contract(state.get("execution_trace", {}), _planned_operation_contract_from_state(state))
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    evidences = analysis_data.get("evidences", [])
    if not isinstance(evidences, list):
        evidences = []
    trace["analysis_focus"] = trace.get("target_scope") or trace.get("operation_kind") or str(analysis_data.get("investigation_status") or "").strip()
    trace["evidence_count"] = len([
        item for item in evidences
        if isinstance(item, dict) and str(item.get("extracted_fact") or "").strip()
    ])
    evidence_sources = [
        str(item.get("source_id") or "").strip()
        for item in evidences
        if isinstance(item, dict) and str(item.get("source_id") or "").strip()
    ]
    if evidence_sources:
        trace["source_ids"] = _dedupe_keep_order(list(trace.get("source_ids", [])) + evidence_sources)[:8]
    return trace


def phase_0_supervisor(state: AnimaState):
    return _run_phase_0_supervisor(
        state,
        llm_supervisor=llm_supervisor,
        available_tools=available_tools,
        planned_operation_contract_from_state=_planned_operation_contract_from_state,
        execution_trace_after_supervisor=_execution_trace_after_supervisor,
        build_direct_tool_message=_build_direct_tool_message,
        build_supervisor_tool_message=_build_supervisor_tool_message,
        ops_tool_cards=_ops_tool_cards,
        ops_node_cards=_ops_node_cards,
        print_fn=print,
    )

def phase_1_searcher(state: AnimaState):
    return _run_phase_1_searcher(
        state,
        stable_action_signature=_stable_action_signature,
        tool_carryover_from_state=_tool_carryover_from_state,
        update_tool_carryover_after_tool=_update_tool_carryover_after_tool,
        extract_local_topology=extract_local_topology,
        print_fn=print,
    )

def _fallback_current_turn_raw_read_report(user_input: str):
    user_text = str(user_input or "").strip()
    observed = user_text if user_text else "The current raw input is empty."
    return {
        "read_mode": "current_turn_only",
        "reviewed_all_input": True,
        "source_summary": "No external source exists; the current user turn was reviewed as source text.",
        "items": [
            {
                "source_id": "current_user_turn",
                "source_type": "current_turn",
                "excerpt": observed[:240],
                "observed_fact": observed,
            }
        ] if user_text else [],
        "coverage_notes": "Fallback path reviewed only the current turn.",
    }


def _fallback_current_turn_with_recent_context_report(user_input: str, recent_context: str, max_recent_turns: int = 2):
    base = _fallback_current_turn_raw_read_report(user_input)
    turns = _extract_recent_raw_turns_from_context(recent_context, max_turns=max_recent_turns)
    if not turns:
        return base

    items = base.get("items", []) if isinstance(base.get("items"), list) else []
    recent_subset = turns[-max_recent_turns:]
    for idx, turn in enumerate(recent_subset, start=1):
        role = str(turn.get("role") or "unknown").strip()
        content = str(turn.get("content") or "").strip()
        if not content:
            continue
        items.append({
            "source_id": f"recent_hint_{idx}",
            "source_type": "recent_chat_hint",
            "excerpt": f"{role}: {content}"[:240],
            "observed_fact": f"{role}: {content}",
        })

    base["items"] = items
    base["source_summary"] = "Reviewed the current turn and attached a small recent-context hint."
    base["coverage_notes"] = f"Attached {len(recent_subset)} recent-context hints for downstream review."
    return base


def _fallback_recent_dialogue_raw_read_report(recent_context: str):
    turns = _extract_recent_raw_turns_from_context(recent_context)
    items = []
    for idx, turn in enumerate(turns, start=1):
        role = str(turn.get("role") or "unknown").strip()
        content = str(turn.get("content") or "").strip()
        if not content:
            continue
        items.append({
            "source_id": f"recent_turn_{idx}",
            "source_type": "recent_chat_turn",
            "excerpt": f"{role}: {content}"[:240],
            "observed_fact": f"{role}: {content}",
        })

    if not items:
        return {
            "read_mode": "recent_dialogue_review",
            "reviewed_all_input": False,
            "source_summary": "recent_context did not yield any parseable recent raw turns.",
            "items": [],
            "coverage_notes": (
                "recent_dialogue_parse_failed: no parseable recent raw turns were recovered from "
                "[Recent Raw Turns]. Expected user:/assistant: or [user]:/[assistant]: lines."
            ),
        }

    return {
        "read_mode": "recent_dialogue_review",
        "reviewed_all_input": True,
        "source_summary": "Recent raw turns from recent_context were reviewed as source text.",
        "items": items,
        "coverage_notes": f"Reviewed {len(items)} recent raw turns; use role-grounded turn evidence before broad interpretation.",
    }


def _recent_dialogue_review_failed(raw_read_report: dict):
    if not isinstance(raw_read_report, dict):
        return False
    if str(raw_read_report.get("read_mode") or "").strip() != "recent_dialogue_review":
        return False
    if not bool(raw_read_report.get("reviewed_all_input")):
        return True
    items = raw_read_report.get("items", [])
    if not isinstance(items, list) or len(items) < 2:
        return True
    coverage_notes = str(raw_read_report.get("coverage_notes") or "").strip().lower()
    return "recent_dialogue_parse_failed" in coverage_notes


def _recent_dialogue_review_has_concrete_turns(analysis_data: dict):
    if not isinstance(analysis_data, dict):
        return False
    evidences = analysis_data.get("evidences", [])
    if not isinstance(evidences, list):
        evidences = []
    for item in evidences:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id") or "").strip()
        extracted_fact = str(item.get("extracted_fact") or "").strip()
        if source_id.startswith("recent_turn_") and extracted_fact:
            return True
    return False


def _field_memo_raw_read_report(search_data: str):
    text = str(search_data or "").strip()
    if "[tool_search_field_memos result]" not in text and "[FieldMemo search result]" not in text:
        return {}
    items = []
    pattern = re.compile(
        r"\[FieldMemo\s+\d+\]\s*"
        r"memo_id:\s*(?P<memo_id>[^\n]+)\n"
        r"(?:memo_level:\s*(?P<memo_level>[^\n]*)\n)?"
        r"(?:summary_scope:\s*(?P<summary_scope>[^\n]*)\n)?"
        r"branch_path:\s*(?P<branch_path>[^\n]*)\n"
        r"root_entity:\s*(?P<root_entity>[^\n]*)\n"
        r"memo_kind:\s*(?P<memo_kind>[^\n]*)\n"
        r"(?:status:\s*(?P<status>[^\n]*)\n)?"
        r"summary:\s*(?P<summary>[^\n]*)\n"
        r"known_facts:\s*(?P<known_facts>[^\n]*)\n"
        r"unknown_slots:\s*(?P<unknown_slots>[^\n]*)",
        flags=re.DOTALL,
    )
    for match in pattern.finditer(text):
        memo_id = str(match.group("memo_id") or "").strip()
        branch_path = str(match.group("branch_path") or "").strip()
        root_entity = str(match.group("root_entity") or "").strip()
        memo_level = str(match.group("memo_level") or "1").strip()
        summary_scope = str(match.group("summary_scope") or "").strip()
        memo_kind = str(match.group("memo_kind") or "").strip()
        status = str(match.group("status") or "active").strip()
        summary = str(match.group("summary") or "").strip()
        known_facts = str(match.group("known_facts") or "").strip()
        unknown_slots = str(match.group("unknown_slots") or "").strip()
        observed = " / ".join(part for part in [summary, f"memo_level={memo_level}", f"summary_scope={summary_scope}", f"status={status}", f"known_facts={known_facts}", f"unknown_slots={unknown_slots}"] if part)
        if not memo_id or not observed:
            continue
        items.append({
            "source_id": memo_id,
            "source_type": "field_memo",
            "excerpt": observed[:360],
            "observed_fact": observed[:360],
            "branch_path": branch_path,
            "root_entity": root_entity,
            "memo_kind": memo_kind,
            "status": status,
            "memo_level": memo_level,
            "summary_scope": summary_scope,
            "summary": summary,
            "known_facts": known_facts,
            "unknown_slots": unknown_slots,
        })
    if not items and "FieldMemo entries exist" in text:
        items.append({
            "source_id": "field_memo_empty",
            "source_type": "field_memo",
            "excerpt": "FieldMemo search returned no entries.",
            "observed_fact": "FieldMemo search returned no matching memo for the current query.",
        })
    if not items:
        return {}
    return {
        "read_mode": "field_memo_review",
        "reviewed_all_input": True,
        "source_summary": f"Read {len(items)} FieldMemo candidates as recall candidates.",
        "items": items,
        "coverage_notes": "FieldMemo entries are recall candidates; phase_2b must separate verified facts from uncertain or missing slots.",
    }


def _fallback_tool_grounded_raw_read_report(search_data: str):
    text = str(search_data or "").strip()
    if not text:
        return {
            "read_mode": "empty",
            "reviewed_all_input": False,
            "source_summary": "Search result text was empty, so no raw-read packet could be built.",
            "items": [],
            "coverage_notes": "tool-grounded fallback parser did not receive any search result text.",
        }

    source_pattern = re.compile(
        r"\[Source\s+\d+\s*\|\s*track=(?P<track>[^\|\]]+)\s*\|\s*source_id=(?P<source_id>[^\]]+)\]\s*(?P<body>.*?)(?=\n\[Source\s+\d+\s*\||\Z)",
        flags=re.DOTALL,
    )
    items = []
    for match in source_pattern.finditer(text):
        source_type = str(match.group("track") or "").strip() or "memory"
        source_id = str(match.group("source_id") or "").strip() or "unknown_source"
        body = str(match.group("body") or "").strip()
        body = re.sub(r"^\[local_topology\].*?\[source_data\]\s*", "", body, flags=re.DOTALL).strip()
        observed = body[:240].strip()
        if not observed:
            continue
        items.append({
            "source_id": source_id,
            "source_type": source_type,
            "excerpt": observed,
            "observed_fact": observed,
        })

    if not items:
        tool_chunks = re.findall(r"\[(.*?) result\]\s*(.*?)(?=\n\[[^\n]+ result\]|\Z)", text, flags=re.DOTALL)
        for idx, (tool_name, body) in enumerate(tool_chunks[:4], start=1):
            cleaned = re.sub(r"^\[local_topology\].*?\[source_data\]\s*", "", str(body).strip(), flags=re.DOTALL).strip()
            if not cleaned:
                continue
            items.append({
                "source_id": f"tool_result_{idx}",
                "source_type": str(tool_name).strip() or "tool_result",
                "excerpt": cleaned[:240],
                "observed_fact": cleaned[:240],
            })

    return {
        "read_mode": "full_raw_review",
        "reviewed_all_input": bool(items),
        "source_summary": (
            f"Extracted {len(items)} grounded items from tool results using deterministic fallback parsing."
            if items else
            "Could not extract grounded items from tool results."
        ),
        "items": items,
        "coverage_notes": (
            "Structured raw-read report was too thin, so deterministic fallback parsing was used."
            if items else
            "Deterministic fallback parser found no usable grounded text."
        ),
    }


def _artifact_grounded_raw_read_report(search_data: str):
    text = str(search_data or "").strip()
    artifact_start = text.find("[artifact]")
    if artifact_start < 0:
        return {}
    if artifact_start > 0:
        text = text[artifact_start:].lstrip()

    header_match = re.search(
        r"\[artifact\]\s*"
        r"path:\s*(?P<path>[^\n]+)\n"
        r"type:\s*(?P<type>[^\n]+)\n"
        r"name:\s*(?P<name>[^\n]+)\n\n",
        text,
        flags=re.DOTALL,
    )
    if not header_match:
        return {}

    artifact_path = str(header_match.group("path") or "").strip()
    artifact_type = str(header_match.group("type") or "").strip().lower()
    artifact_name = str(header_match.group("name") or "").strip() or os.path.basename(artifact_path) or "artifact"
    body = text[header_match.end():].strip()
    if not body:
        return {
            "read_mode": "full_raw_review",
            "reviewed_all_input": False,
            "source_summary": f"No readable body text was found in {artifact_name}.",
            "items": [],
            "coverage_notes": "Artifact fast path found an empty body and could not build usable grounded items.",
        }

    items = []
    source_id = artifact_name
    source_type = "artifact"

    if artifact_type == ".pptx":
        slide_lines = [
            line.strip()
            for line in body.splitlines()
            if line.strip()
        ]
        for idx, line in enumerate(slide_lines[:12], start=1):
            cleaned = re.sub(r"^\[slide\s+\d+\]\s*", "", line, flags=re.IGNORECASE).strip()
            if not cleaned:
                continue
            slide_match = re.match(r"^\[slide\s+(\d+)\]\s*", line, flags=re.IGNORECASE)
            slide_no = slide_match.group(1) if slide_match else str(idx)
            items.append({
                "source_id": f"{source_id}#slide_{slide_no}",
                "source_type": source_type,
                "excerpt": line[:240],
                "observed_fact": cleaned[:240],
            })
    else:
        paragraphs = [
            chunk.strip()
            for chunk in re.split(r"\n\s*\n+", body)
            if chunk.strip()
        ]
        if len(paragraphs) <= 1:
            paragraphs = [
                line.strip()
                for line in body.splitlines()
                if line.strip()
            ]
        for idx, paragraph in enumerate(paragraphs[:10], start=1):
            collapsed = re.sub(r"\s+", " ", paragraph).strip()
            if not collapsed:
                continue
            items.append({
                "source_id": f"{source_id}#part_{idx}",
                "source_type": source_type,
                "excerpt": collapsed[:240],
                "observed_fact": collapsed[:240],
            })

    if not items:
        collapsed = re.sub(r"\s+", " ", body).strip()
        if collapsed:
            items.append({
                "source_id": source_id,
                "source_type": source_type,
                "excerpt": collapsed[:240],
                "observed_fact": collapsed[:240],
            })

    if not items:
        return {}

    source_summary = (
        f"{artifact_name} was reviewed by deterministic artifact parsing and "
        f"{len(items)} grounded items were extracted."
    )
    coverage_notes = (
        "Artifact fast path bypassed structured LLM reading and packed source text into slide/section grounded items."
    )
    return {
        "read_mode": "full_raw_review",
        "reviewed_all_input": True,
        "source_summary": source_summary,
        "items": items,
        "coverage_notes": coverage_notes,
    }


def phase_2a_reader(state: AnimaState):
    return _run_phase_2a_reader(
        state,
        llm_supervisor=llm_supervisor,
        raw_read_report_schema=RawReadReport,
        is_recent_dialogue_review_turn=_is_recent_dialogue_review_turn,
        fallback_recent_dialogue_raw_read_report=_fallback_recent_dialogue_raw_read_report,
        recent_dialogue_review_failed=_recent_dialogue_review_failed,
        fallback_current_turn_with_recent_context_report=_fallback_current_turn_with_recent_context_report,
        execution_trace_after_phase2a=_execution_trace_after_phase2a,
        field_memo_raw_read_report=_field_memo_raw_read_report,
        artifact_grounded_raw_read_report=_artifact_grounded_raw_read_report,
        phase3_recent_context_excerpt=_phase3_recent_context_excerpt,
        fallback_tool_grounded_raw_read_report=_fallback_tool_grounded_raw_read_report,
        print_fn=print,
    )


def _is_initiative_request_turn(user_input: str):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if not text:
        return False
    if _is_assistant_question_request_turn(text):
        return True
    markers = ["you decide", "you think", "do not ask", "just propose", "figure it out", "\ub124\uac00 \ud310\ub2e8", "\ub124\uac00 \uc0dd\uac01", "\uc9c1\uc811 \ud574", "\uc81c\uc548\ud574"]
    return any(marker in text for marker in markers)


def _enforce_thin_raw_strategist_escalation(
    strategist_payload: dict,
    analysis_data: dict,
    raw_read_report: dict,
    user_input: str,
    working_memory: dict,
):
    if not isinstance(strategist_payload, dict):
        strategist_payload = {}

    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    raw_strength = _raw_grounding_strength(raw_read_report)
    evidences = (analysis_data or {}).get("evidences", []) if isinstance(analysis_data, dict) else []
    grounded_facts = [
        str(item.get("extracted_fact") or "").strip()
        for item in evidences
        if isinstance(item, dict) and str(item.get("extracted_fact") or "").strip()
    ]
    grounded_facts = _dedupe_keep_order(grounded_facts)[:3]
    should_escalate = (
        raw_strength == "thin"
        and (status in {"", "INCOMPLETE", "EXPANSION_REQUIRED"} or not grounded_facts)
    )
    if not should_escalate:
        return strategist_payload

    normalized = json.loads(json.dumps(strategist_payload, ensure_ascii=False))
    action_plan = _normalize_action_plan(normalized.get("action_plan", {}))
    if action_plan.get("required_tool"):
        return normalized

    tool_candidate = _strategist_tool_request_from_context(user_input, analysis_data, working_memory)
    case_theory = str(normalized.get("case_theory") or "").strip()
    escalation_note = "Raw grounding is still thin, so the strategist should ask for stronger evidence before trusting contextual interpretation."
    normalized["case_theory"] = f"{case_theory} {escalation_note}".strip() if case_theory else escalation_note

    if tool_candidate:
        normalized["action_plan"] = {
            "current_step_goal": "Thin raw grounding means the next step should gather one stronger source before any final delivery.",
            "required_tool": _tool_call_to_instruction(
                str(tool_candidate.get("tool_name") or ""),
                tool_candidate.get("tool_args", {}),
            ),
            "next_steps_forecast": [
                "Re-run phase 2 on the stronger grounded source.",
                "Let 2b diagnose the new fact layer before composing delivery.",
                "Only deliver a final answer after grounded evidence becomes stable.",
            ],
        }
        normalized["response_strategy"] = None
        return normalized

    normalized["action_plan"] = {
        "current_step_goal": "The current raw evidence is too thin, so the next step must stay in clarification or evidence-gathering mode.",
        "required_tool": "",
        "next_steps_forecast": [
            "Reduce contextual speculation instead of completing the answer from weak signals.",
            "Ask for one stronger anchor only if retrieval cannot be chosen safely.",
        ],
    }
    normalized["response_strategy"] = None
    return normalized


_previous_followup_context_expected = _base_followup_context_expected


def _followup_context_expected(user_input: str, recent_context: str, working_memory: dict):
    if _pending_dialogue_act_accepts_current_turn(user_input, working_memory):
        return True
    if _temporal_context_prefers_current_input(working_memory):
        return False
    if looks_like_memo_recall_turn(user_input):
        return False
    return _previous_followup_context_expected(user_input, recent_context, working_memory)


def _phase2a_should_inherit_task_context(state: AnimaState):
    user_input = str(state.get("user_input") or "").strip()
    recent_context = str(state.get("recent_context") or "")
    working_memory = state.get("working_memory", {})
    execution_trace = _normalize_execution_trace(state.get("execution_trace", {}))
    tool_carryover = _tool_carryover_from_state(state)
    if not user_input:
        return False
    normalized = unicodedata.normalize("NFKC", user_input)
    retry_markers = [
        "again",
        "previous",
        "that",
        "not that",
        "read again",
        "search again",
        "\ub2e4\uc2dc",
        "\uc774\uc804",
        "\uadf8\uac70",
        "\ubc18\ubcf5",
        "\uc9c1\uc811",
    ]
    refers_back = any(marker in normalized for marker in retry_markers)

    if _followup_context_expected(user_input, recent_context, working_memory):
        return True
    if _working_memory_expects_continuation(working_memory):
        return True
    if refers_back and (
        _working_memory_active_task(working_memory)
        or execution_trace.get("source_ids")
        or execution_trace.get("executed_tool")
        or tool_carryover.get("source_ids")
    ):
        return True
    if _looks_like_scroll_followup_turn(user_input) and _tool_carryover_anchor_id(state):
        return True
    return False


def _phase2a_task_inheritance_packet(state: AnimaState):
    if not _phase2a_should_inherit_task_context(state):
        return {}

    working_memory = state.get("working_memory", {})
    if not isinstance(working_memory, dict):
        working_memory = {}
    execution_trace = _normalize_execution_trace(state.get("execution_trace", {}))
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    tool_carryover = _tool_carryover_from_state(state)
    dialogue_state = working_memory.get("dialogue_state", {})
    if not isinstance(dialogue_state, dict):
        dialogue_state = {}
    evidence_state = working_memory.get("evidence_state", {})
    if not isinstance(evidence_state, dict):
        evidence_state = {}

    active_task = str(dialogue_state.get("active_task") or "").strip()
    active_task_source = str(dialogue_state.get("active_task_source") or "").strip()
    active_offer = str(dialogue_state.get("active_offer") or "").strip()
    active_offer_source = str(dialogue_state.get("active_offer_source") or "").strip()
    goal_lock = _normalize_goal_lock(strategist_output.get("goal_lock", {}))
    carried_source_ids = _dedupe_keep_order(
        list(evidence_state.get("active_source_ids", [])) + list(execution_trace.get("source_ids", []))
    )[:5]

    return {
        "active_task": active_task,
        "active_task_source": active_task_source,
        "active_offer": active_offer,
        "active_offer_source": active_offer_source,
        "goal_lock": goal_lock,
        "source_ids": carried_source_ids,
        "executed_tool": str(execution_trace.get("executed_tool") or "").strip(),
        "operation_kind": str(execution_trace.get("operation_kind") or "").strip(),
        "read_focus": str(execution_trace.get("read_focus") or "").strip(),
        "analysis_focus": str(execution_trace.get("analysis_focus") or "").strip(),
        "tool_carryover": tool_carryover,
        "self_correction_memo": str(state.get("self_correction_memo") or "").strip(),
    }


def _apply_phase2a_task_inheritance(raw_read_report: dict, inheritance_packet: dict | None = None):
    if not isinstance(raw_read_report, dict):
        raw_read_report = {}
    inheritance_packet = inheritance_packet if isinstance(inheritance_packet, dict) else {}
    if not inheritance_packet:
        return raw_read_report

    normalized = json.loads(json.dumps(raw_read_report, ensure_ascii=False))
    items = normalized.get("items", [])
    if not isinstance(items, list):
        items = []

    def _append_item(source_id: str, observed_fact: str):
        text = str(observed_fact or "").strip()
        if not text:
            return
        items.append({
            "source_id": source_id,
            "source_type": "task_inheritance",
            "excerpt": text[:240],
            "observed_fact": text[:240],
        })

    active_task = str(inheritance_packet.get("active_task") or "").strip()
    if active_task:
        source_label = str(inheritance_packet.get("active_task_source") or "").strip() or "working_memory"
        _append_item("inherited_active_task", f"Previous active task from {source_label}: {active_task}")

    active_offer = str(inheritance_packet.get("active_offer") or "").strip()
    if active_offer:
        offer_source = str(inheritance_packet.get("active_offer_source") or "").strip() or "assistant_offer"
        _append_item("inherited_active_offer", f"Previous assistant offer from {offer_source}: {active_offer}")

    goal_lock = inheritance_packet.get("goal_lock", {})
    if isinstance(goal_lock, dict):
        user_goal_core = str(goal_lock.get("user_goal_core") or "").strip()
        answer_shape = str(goal_lock.get("answer_shape") or "").strip()
        if user_goal_core:
            _append_item(
                "inherited_goal_lock",
                f"Previous goal lock: {user_goal_core}" + (f" | answer_shape={answer_shape}" if answer_shape else ""),
            )

    source_ids = inheritance_packet.get("source_ids", [])
    if isinstance(source_ids, list) and source_ids:
        joined = ", ".join(str(item).strip() for item in source_ids[:3] if str(item).strip())
        if joined:
            _append_item("inherited_source_ids", f"Previously active sources: {joined}")

    executed_tool = str(inheritance_packet.get("executed_tool") or "").strip()
    operation_kind = str(inheritance_packet.get("operation_kind") or "").strip()
    if executed_tool:
        _append_item(
            "inherited_last_tool",
            f"Last executed tool: {executed_tool}" + (f" | operation_kind={operation_kind}" if operation_kind else ""),
        )

    tool_carryover = _normalize_tool_carryover_state(inheritance_packet.get("tool_carryover", {}))
    anchor_id = tool_carryover.get("origin_source_id") or tool_carryover.get("last_target_id")
    if anchor_id or tool_carryover.get("source_ids"):
        source_hint = ", ".join(tool_carryover.get("source_ids", [])[:4])
        _append_item(
            "inherited_tool_carryover",
            (
                f"ToolCarryoverState: origin={anchor_id or 'n/a'} | "
                f"last_tool={tool_carryover.get('last_tool') or 'n/a'} | "
                f"last_query={tool_carryover.get('last_query') or 'n/a'} | "
                f"source_ids={source_hint or 'n/a'}"
            ),
        )

    read_focus = str(inheritance_packet.get("read_focus") or "").strip()
    analysis_focus = str(inheritance_packet.get("analysis_focus") or "").strip()
    if read_focus or analysis_focus:
        _append_item(
            "inherited_focus",
            f"Previous focus: read_focus={read_focus or 'n/a'} | analysis_focus={analysis_focus or 'n/a'}",
        )

    correction_memo = str(inheritance_packet.get("self_correction_memo") or "").strip()
    if correction_memo:
        _append_item("inherited_correction_memo", f"Judge self-correction memo: {correction_memo}")

    normalized["items"] = items
    summary = str(normalized.get("source_summary") or "").strip()
    coverage = str(normalized.get("coverage_notes") or "").strip()
    inherit_note = "Task inheritance context from the previous active task was attached for this read."
    normalized["source_summary"] = (summary + " " + inherit_note).strip()
    normalized["coverage_notes"] = (coverage + " " + inherit_note).strip()
    return normalized


_previous_minimal_direct_dialogue_strategy = _base_minimal_direct_dialogue_strategy


def _minimal_direct_dialogue_strategy(user_input: str, working_memory: dict):
    context_strategy = _short_term_context_response_strategy(user_input, working_memory)
    if context_strategy and (_working_memory_expects_continuation(working_memory) or not _has_substantive_dialogue_anchor(user_input)):
        return context_strategy

    strategy = _previous_minimal_direct_dialogue_strategy(user_input, working_memory)
    if not isinstance(strategy, dict):
        return strategy
    if not str(strategy.get("delivery_freedom_mode") or "").strip():
        strategy["delivery_freedom_mode"] = "grounded"
    if _temporal_context_allows_carry_over(working_memory):
        return strategy

    must_include = strategy.get("must_include_facts", [])
    if isinstance(must_include, list):
        filtered = []
        for item in must_include:
            text = str(item or "").strip()
            if "Active task context" in text or "active_task" in text:
                continue
            filtered.append(text)
        strategy["must_include_facts"] = filtered
    return strategy


_previous_initiative_request_strategy = _base_initiative_request_strategy


def _initiative_request_strategy(user_input: str, working_memory: dict):
    strategy = _previous_initiative_request_strategy(user_input, working_memory)
    if not isinstance(strategy, dict):
        return strategy
    strategy["delivery_freedom_mode"] = "proposal"
    if _temporal_context_allows_carry_over(working_memory):
        return strategy

    must_include = strategy.get("must_include_facts", [])
    if isinstance(must_include, list):
        filtered = []
        for item in must_include:
            text = str(item or "").strip()
            if "Active task context" in text or "active_task" in text:
                continue
            filtered.append(text)
        strategy["must_include_facts"] = filtered
    return strategy


_previous_phase_2a_reader = phase_2a_reader


def _base_phase_2a_reader(state: AnimaState):
    search_data = str(state.get("search_results", "") or "")
    if search_data.strip() or _is_recent_dialogue_review_turn(state.get("user_input", ""), state.get("recent_context", "")):
        result = _previous_phase_2a_reader(state)
        if isinstance(result, dict) and isinstance(result.get("raw_read_report"), dict):
            result = _attach_ledger_event(
                result,
                state,
                source_kind="raw_read_report",
                producer_node="phase_2a_reader",
                source_ref=str(result.get("raw_read_report", {}).get("read_mode") or "source_review"),
                content=result.get("raw_read_report", {}),
                confidence=0.9,
            )
        return result

    print("[Phase 2a] Reading raw sources end-to-end...")
    recent_hint_budget = _recent_hint_budget_from_working_memory(state.get("working_memory", {}))
    inheritance_packet = _phase2a_task_inheritance_packet(state)
    if recent_hint_budget <= 0:
        raw_read_report = _fallback_current_turn_raw_read_report(state.get("user_input", ""))
        raw_read_report = _apply_phase2a_task_inheritance(raw_read_report, inheritance_packet)
        print("  [Phase 2a] current_turn_only | temporal topic-shift signal blocks stale recent hints")
        if inheritance_packet:
            print("  [Phase 2a] task_inheritance | previous task context attached")
        return _attach_ledger_event({
            "raw_read_report": raw_read_report,
            "execution_trace": _execution_trace_after_phase2a(state, raw_read_report),
        }, state, source_kind="raw_read_report", producer_node="phase_2a_reader", source_ref="current_turn_only", content=raw_read_report, confidence=0.85)

    raw_read_report = _fallback_current_turn_with_recent_context_report(
        state.get("user_input", ""),
        state.get("recent_context", ""),
        max_recent_turns=recent_hint_budget,
    )
    raw_read_report = _apply_phase2a_task_inheritance(raw_read_report, inheritance_packet)
    recent_hint_count = max(len(raw_read_report.get("items", [])) - 1, 0)
    print(f"  [Phase 2a] current_turn_only | recent hints={recent_hint_count}")
    if inheritance_packet:
        print("  [Phase 2a] task_inheritance | previous task context attached")
    return _attach_ledger_event({
        "raw_read_report": raw_read_report,
        "execution_trace": _execution_trace_after_phase2a(state, raw_read_report),
    }, state, source_kind="raw_read_report", producer_node="phase_2a_reader", source_ref="current_turn_with_recent_context", content=raw_read_report, confidence=0.85)


_previous_phase_minus_1a_thinker = _base_phase_minus_1a_thinker


def _ensure_operation_contract_in_strategist_payload(
    strategist_payload: dict,
    user_input: str,
    analysis_data: dict,
):
    if not isinstance(strategist_payload, dict):
        strategist_payload = {}
    normalized = json.loads(json.dumps(strategist_payload, ensure_ascii=False))
    action_plan = _normalize_action_plan(normalized.get("action_plan", {}))
    response_strategy = normalized.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    action_plan["operation_contract"] = _derive_operation_contract(
        user_input,
        action_plan,
        response_strategy=response_strategy,
        analysis_data=analysis_data,
    )
    normalized["action_plan"] = action_plan
    return normalized


def _ensure_operation_plan_in_strategist_payload(
    strategist_payload: dict,
    user_input: str,
    analysis_data: dict,
    working_memory: dict | None = None,
    recent_context: str = "",
    start_gate_review: dict | None = None,
):
    if not isinstance(strategist_payload, dict):
        strategist_payload = {}
    normalized = json.loads(json.dumps(strategist_payload, ensure_ascii=False))
    action_plan = _normalize_action_plan(normalized.get("action_plan", {}))
    response_strategy = normalized.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    derived_plan = _derive_operation_plan(
        user_input,
        analysis_data,
        action_plan,
        response_strategy,
        working_memory if isinstance(working_memory, dict) else {},
        recent_context,
        start_gate_review if isinstance(start_gate_review, dict) else {},
    )
    existing_plan = normalized.get("operation_plan", {})
    existing_plan = _normalize_operation_plan(existing_plan if isinstance(existing_plan, dict) else {})
    existing_has_signal = bool(
        str(existing_plan.get("user_goal") or "").strip()
        or str(existing_plan.get("executor_instruction") or "").strip()
        or existing_plan.get("success_criteria")
    )
    if existing_has_signal and existing_plan.get("plan_type") in {
        "direct_delivery",
        "warroom_deliberation",
        "tool_evidence",
        "recent_dialogue_review",
        "raw_source_analysis",
    }:
        if existing_plan.get("plan_type") == "direct_delivery" and derived_plan.get("plan_type") != "direct_delivery":
            normalized["operation_plan"] = derived_plan
            return _sanitize_strategist_goal_fields(normalized, user_input, start_gate_review)
        if derived_plan.get("plan_type") in {"tool_evidence", "recent_dialogue_review", "raw_source_analysis"} and existing_plan.get("plan_type") != derived_plan.get("plan_type"):
            normalized["operation_plan"] = derived_plan
            return _sanitize_strategist_goal_fields(normalized, user_input, start_gate_review)
        semantic_contract_changed = False
        if derived_plan.get("output_act") not in {"", "answer"} and existing_plan.get("output_act") != derived_plan.get("output_act"):
            existing_plan["output_act"] = derived_plan.get("output_act")
            existing_plan["delivery_shape"] = derived_plan.get("delivery_shape", existing_plan.get("delivery_shape", ""))
            semantic_contract_changed = True
        if derived_plan.get("source_lane") not in {"", "none"} and existing_plan.get("source_lane") in {"", "none"}:
            existing_plan["source_lane"] = derived_plan.get("source_lane")
            semantic_contract_changed = True
        if semantic_contract_changed and str(derived_plan.get("evidence_policy") or "").strip():
            existing_plan["evidence_policy"] = derived_plan.get("evidence_policy", existing_plan.get("evidence_policy", ""))
        for key in ("executor_instruction", "evidence_policy", "delivery_shape"):
            if not str(existing_plan.get(key) or "").strip():
                existing_plan[key] = derived_plan.get(key, "")
        for key in ("success_criteria", "rejection_criteria"):
            if not existing_plan.get(key):
                existing_plan[key] = derived_plan.get(key, [])
        normalized["operation_plan"] = existing_plan
        return _sanitize_strategist_goal_fields(normalized, user_input, start_gate_review)

    normalized["operation_plan"] = derived_plan
    return _sanitize_strategist_goal_fields(normalized, user_input, start_gate_review)


def _raw_user_wording_leaked(value: str, user_input: str):
    value_norm = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    user_norm = unicodedata.normalize("NFKC", str(user_input or "")).strip().lower()
    if not value_norm or not user_norm or len(user_norm) < 12:
        return False
    compact_value = re.sub(r"\s+", "", value_norm)
    compact_user = re.sub(r"\s+", "", user_norm)
    if compact_user and compact_user in compact_value:
        return True
    return len(compact_user) >= 24 and compact_user[:24] in compact_value


def _strategist_goal_from_payload_or_contract(
    strategist_payload: dict,
    goal_lock: dict,
    user_input: str,
    start_gate_review: dict | None = None,
):
    start_gate_review = start_gate_review if isinstance(start_gate_review, dict) else {}
    answer_mode_policy = start_gate_review.get("answer_mode_policy", {})
    if not isinstance(answer_mode_policy, dict):
        answer_mode_policy = {}
    policy_target = _strategist_answer_mode_target_from_policy(answer_mode_policy)

    existing_goal = strategist_payload.get("strategist_goal", {})
    if not isinstance(existing_goal, dict) or not existing_goal:
        normalized_goal_alias = strategist_payload.get("normalized_goal", {})
        existing_goal = normalized_goal_alias if isinstance(normalized_goal_alias, dict) else {}
    strategist_goal = _normalize_strategist_goal(existing_goal)
    fallback_goal = _strategist_goal_from_goal_lock(
        goal_lock,
        answer_mode_target=policy_target,
    )

    if (
        not str(strategist_goal.get("user_goal_core") or "").strip()
        or _raw_user_wording_leaked(strategist_goal.get("user_goal_core", ""), user_input)
    ):
        strategist_goal["user_goal_core"] = fallback_goal.get("user_goal_core", "")
    if strategist_goal.get("answer_mode_target") == "ambiguous" and policy_target != "ambiguous":
        strategist_goal["answer_mode_target"] = policy_target
    if not strategist_goal.get("success_criteria"):
        strategist_goal["success_criteria"] = fallback_goal.get("success_criteria", [])
    return _normalize_strategist_goal(strategist_goal)


def _sanitize_strategist_goal_fields(
    strategist_payload: dict,
    user_input: str,
    start_gate_review: dict | None = None,
):
    normalized = json.loads(json.dumps(strategist_payload if isinstance(strategist_payload, dict) else {}, ensure_ascii=False))
    derived_goal_lock = _derive_goal_lock_v2(user_input, start_gate_review if isinstance(start_gate_review, dict) else {})

    goal_lock = _normalize_goal_lock(normalized.get("goal_lock", {}))
    strategist_goal = _strategist_goal_from_payload_or_contract(
        normalized,
        derived_goal_lock,
        user_input,
        start_gate_review,
    )
    strategist_goal_core = str(strategist_goal.get("user_goal_core") or "").strip()
    goal_lock["user_goal_core"] = strategist_goal_core
    if (
        not str(goal_lock.get("answer_shape") or "").strip()
        or str(derived_goal_lock.get("answer_shape") or "").strip() != "direct_answer"
    ):
        goal_lock["answer_shape"] = derived_goal_lock.get("answer_shape", goal_lock.get("answer_shape", "direct_answer"))
    if derived_goal_lock.get("must_not_expand_to"):
        goal_lock["must_not_expand_to"] = derived_goal_lock.get("must_not_expand_to", [])
    normalized["goal_lock"] = goal_lock
    normalized["strategist_goal"] = strategist_goal
    normalized["normalized_goal"] = strategist_goal

    action_plan = _normalize_action_plan(normalized.get("action_plan", {}))
    operation_plan = _normalize_operation_plan(normalized.get("operation_plan", {}))
    if strategist_goal_core:
        operation_plan["user_goal"] = strategist_goal_core

    plan_type = str(operation_plan.get("plan_type") or "").strip()
    step_goal = str(action_plan.get("current_step_goal") or "").strip()
    if (
        not step_goal
        or _raw_user_wording_leaked(step_goal, user_input)
        or _raw_user_wording_leaked(operation_plan.get("user_goal", ""), user_input)
    ):
        if plan_type in {"tool_evidence", "recent_dialogue_review", "raw_source_analysis"}:
            action_plan["current_step_goal"] = _goal_locked_gathering_step_goal(goal_lock)
        else:
            action_plan["current_step_goal"] = _goal_locked_delivery_step_goal(goal_lock)

    normalized["action_plan"] = action_plan
    normalized["operation_plan"] = operation_plan
    return normalized


def _ensure_war_room_contract_in_strategist_payload(
    strategist_payload: dict,
    user_input: str,
    analysis_data: dict,
    start_gate_review: dict | None = None,
):
    if not isinstance(strategist_payload, dict):
        strategist_payload = {}
    normalized = json.loads(json.dumps(strategist_payload, ensure_ascii=False))
    action_plan = _normalize_action_plan(normalized.get("action_plan", {}))
    response_strategy = normalized.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    existing_contract = normalized.get("war_room_contract", {})
    existing_contract = _normalize_war_room_operating_contract(existing_contract if isinstance(existing_contract, dict) else {})
    existing_has_signal = bool(
        existing_contract.get("freedom", {}).get("granted")
        or existing_contract.get("reason", {}).get("why_tool_is_not_primary")
        or existing_contract.get("deficiency", {}).get("missing_items")
    )
    if existing_has_signal:
        normalized["war_room_contract"] = existing_contract
        return normalized

    normalized["war_room_contract"] = _derive_war_room_operating_contract(
        user_input,
        analysis_data,
        action_plan,
        response_strategy,
        start_gate_review=start_gate_review if isinstance(start_gate_review, dict) else {},
    )
    return normalized


def phase_minus_1a_thinker(state: AnimaState):
    return _run_phase_minus_1a_thinker(
        state,
        previous_phase_minus_1a_thinker=_previous_phase_minus_1a_thinker,
        build_strategist_objection_packet=_build_strategist_objection_packet,
        normalize_operation_plan=_normalize_operation_plan,
        attach_ledger_event=_attach_ledger_event,
    )


def _extract_explicit_search_keyword(user_input: str):
    candidate = _shared_extract_explicit_search_phrase(user_input)
    if candidate:
        return _clean_explicit_search_fragment(candidate)
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    if not text:
        return ""
    match = re.search(r"(?:search|find|look up|\uac80\uc0c9|\ucc3e\uc544)\s+(.+)$", text, flags=re.IGNORECASE)
    if match:
        return _clean_explicit_search_fragment(match.group(1))
    return ""


def _clean_explicit_search_fragment(fragment: str):
    text = unicodedata.normalize("NFKC", str(fragment or "").strip())
    if not text:
        return ""
    text = re.sub(r"^\s*(?:please|just|once|search|find|look up|\uac80\uc0c9|\ucc3e\uc544)\s+", "", text, flags=re.IGNORECASE).strip()
    text = re.split(r"\s*(?:then|and|result|results|tell me|explain|\uacb0\uacfc|\ub9d0\ud574|\uc54c\ub824)\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    text = re.sub(r"\s+", " ", text).strip(" \"'.,!?()[]{}<>")
    if not text or len(text) > 80:
        return ""
    return text


def _extract_explicit_search_keywords(user_input: str):
    primary = _extract_explicit_search_keyword(user_input)
    return [primary] if primary else []


def _supervisor_search_queries(user_input: str, tool_name: str, tool_args: dict, operation_contract: dict | None = None):
    normalized_tool = str(tool_name or "").strip()
    if normalized_tool not in {"tool_search_memory", "tool_search_field_memos"}:
        return []
    queries = []
    normalized_contract = _normalize_operation_contract(operation_contract if isinstance(operation_contract, dict) else {})
    explicit_queries = _extract_explicit_search_keywords(user_input)
    queries.extend(explicit_queries)
    keyword = ""
    if isinstance(tool_args, dict):
        raw_keyword = str(tool_args.get("keyword") or tool_args.get("query") or "")
        keyword = _clean_explicit_search_fragment(raw_keyword) or _normalize_search_keyword(raw_keyword)
    if keyword and not _looks_like_fake_tool_or_meta_string(keyword):
        queries.insert(0, keyword)
    query_variant = str(normalized_contract.get("query_variant") or "").strip()
    if query_variant and not _looks_like_fake_tool_or_meta_string(query_variant):
        queries.insert(0, query_variant)
    return _dedupe_keep_order([query for query in queries if query])[:2]


def _build_supervisor_tool_message(tool_name: str, tool_args: dict, user_input: str, operation_contract: dict | None = None):
    normalized_tool_name = str(tool_name or "").strip()
    normalized_tool_args = tool_args if isinstance(tool_args, dict) else {}

    if normalized_tool_name in {"tool_search_memory", "tool_search_field_memos"}:
        arg_name = "query" if normalized_tool_name == "tool_search_field_memos" else "keyword"
        exact_query = str(normalized_tool_args.get(arg_name) or "").strip()
        if not exact_query:
            other_arg_name = "keyword" if arg_name == "query" else "query"
            exact_query = str(normalized_tool_args.get(other_arg_name) or "").strip()

        if exact_query:
            exact_args = dict(normalized_tool_args)
            exact_args[arg_name] = exact_query
            if normalized_tool_name == "tool_search_field_memos":
                try:
                    exact_args["limit"] = int(exact_args.get("limit", 6) or 6)
                except (TypeError, ValueError):
                    exact_args["limit"] = 6
            return AIMessage(
                content="",
                tool_calls=[{"name": normalized_tool_name, "args": exact_args, "id": f"auditor_{normalized_tool_name}_exact"}],
            )

        # Only fall back to the older query expander when -1a/-1b failed to
        # provide any usable query at all. Exact strategist args must not be
        # rewritten by phase 0.
        queries = _supervisor_search_queries(user_input, normalized_tool_name, normalized_tool_args, operation_contract=operation_contract)
        if queries:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": normalized_tool_name,
                        "args": {arg_name: query},
                        "id": f"auditor_{normalized_tool_name}_{idx}",
                    }
                    for idx, query in enumerate(queries, start=1)
                ],
            )

    return AIMessage(
        content="",
        tool_calls=[{"name": normalized_tool_name, "args": normalized_tool_args, "id": f"auditor_{normalized_tool_name}"}],
    )


def _is_assistant_investigation_request_turn(user_input: str):
    return _shared_is_assistant_investigation_request_turn(user_input)


def _ops_tool_cards():
    return [
        {
            "tool_name": "tool_search_field_memos",
            "purpose": "Retrieve curated FieldMemo candidates from prior turns.",
            "use_when": "Use when the user asks about remembered, previous, or recently taught personal facts.",
            "avoid_when": "Avoid for pure emotional acknowledgement, public knowledge, or explicit raw-source/date searches.",
        },
        {
            "tool_name": "tool_read_artifact",
            "purpose": "Read a local document or artifact directly.",
            "use_when": "Use when artifact_hint or document/PPTX/source reading is required.",
            "avoid_when": "Avoid for lightweight conversation or direct-answer turns.",
        },
        {
            "tool_name": "tool_search_memory",
            "purpose": "Run a broad memory/raw-record search when needed.",
            "use_when": "Use for explicit search keywords, past recall, or record exploration.",
            "avoid_when": "Avoid when the current turn itself is enough to answer.",
        },
        {
            "tool_name": "tool_scroll_chat_log",
            "purpose": "Read around a specific recovered chat-log source id.",
            "use_when": "Use when a concrete target_id exists and surrounding context is needed.",
            "avoid_when": "Avoid vague recent-conversation summaries without a target id.",
        },
        {
            "tool_name": "tool_read_full_diary",
            "purpose": "Read the diary entry for a specific date.",
            "use_when": "Use when a date-specific diary recall is requested.",
            "avoid_when": "Avoid for undated general conversation or document search.",
        },
    ]


def _ops_node_cards():
    return [
        {
            "node_name": "phase_3",
            "responsibility": "Direct answer, continuation, suggestion, creative/social delivery.",
            "route_when": "Use when the turn can be answered now or already has an approved payload.",
        },
        {
            "node_name": "-1a_thinker",
            "responsibility": "Plan shaping, question narrowing, tool planning.",
            "route_when": "Use when question structure or planning must be clarified first.",
        },
        {
            "node_name": "phase_2a",
            "responsibility": "Read raw source or recent dialogue input.",
            "route_when": "Use when raw-read evidence is primary.",
        },
    ]


def _plan_reasoning_budget(user_input: str, recent_context: str, working_memory: dict):
    text = str(user_input or "").strip()
    artifact_hint = _extract_artifact_hint(text)


    if _is_assistant_investigation_request_turn(text):
        if artifact_hint:
            return {
                "reasoning_budget": 2,
                "preferred_path": "tool_first",
                "should_use_tools": True,
                "rationale": "The user explicitly asked the assistant to investigate, so source/tool checking may be needed before final delivery.",
            }
        if _is_recent_dialogue_review_turn(text, recent_context):
            return {
                "reasoning_budget": 2,
                "preferred_path": "internal_reasoning",
                "should_use_tools": False,
                "rationale": "The user asked for recent-dialogue review, so inspect the recent flow before final delivery.",
            }
        return {
            "reasoning_budget": 2,
            "preferred_path": "internal_reasoning",
            "should_use_tools": False,
            "rationale": "The user asked the assistant to think/investigate; plan the answer boundary before final delivery.",
        }

    return _base_plan_reasoning_budget(user_input, recent_context, working_memory)


def _parse_reasoning_budget_value(value):
    if value is None:
        return None
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return None


def _resolve_reasoning_budget(state: AnimaState, reasoning_plan: dict | None = None, default: int = 1):
    plan = reasoning_plan if isinstance(reasoning_plan, dict) else {}
    state_plan = state.get("reasoning_plan", {})
    state_plan_ready = isinstance(state_plan, dict) and bool(state_plan)

    state_budget = _parse_reasoning_budget_value(state.get("reasoning_budget", None))
    if state_plan_ready and state_budget is not None:
        return state_budget

    plan_budget = _parse_reasoning_budget_value(plan.get("reasoning_budget", None))
    if plan_budget is not None:
        return plan_budget

    legacy_budget = _parse_reasoning_budget_value(plan.get("budget", None))
    if legacy_budget is not None:
        return legacy_budget

    if state_budget is not None:
        return state_budget

    return max(int(default), 0)


def _operation_plan_from_state(state: AnimaState, strategist_output: dict | None = None):
    strategist_output = strategist_output if isinstance(strategist_output, dict) else state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}

    state_plan = state.get("operation_plan", {})
    if isinstance(state_plan, dict) and state_plan:
        return _normalize_operation_plan(state_plan)

    strategist_plan = strategist_output.get("operation_plan", {})
    if isinstance(strategist_plan, dict) and strategist_plan:
        return _normalize_operation_plan(strategist_plan)

    reasoning_board = state.get("reasoning_board", {})
    if isinstance(reasoning_board, dict):
        board_plan = reasoning_board.get("strategist_plan", {})
        if isinstance(board_plan, dict):
            nested_plan = board_plan.get("operation_plan", {})
            if isinstance(nested_plan, dict) and nested_plan:
                return _normalize_operation_plan(nested_plan)

    action_plan = _normalize_action_plan(strategist_output.get("action_plan", {}))
    response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = state.get("response_strategy", {}) if isinstance(state.get("response_strategy", {}), dict) else {}
    return _derive_operation_plan(
        str(state.get("user_input") or ""),
        state.get("analysis_report", {}) if isinstance(state.get("analysis_report", {}), dict) else {},
        action_plan,
        response_strategy,
        state.get("working_memory", {}) if isinstance(state.get("working_memory", {}), dict) else {},
        str(state.get("recent_context") or ""),
        state.get("start_gate_review", {}) if isinstance(state.get("start_gate_review", {}), dict) else {},
    )


def _war_room_seed_alignment_issue(user_input: str, war_room_output: dict, recent_context: str = ""):
    return _war_room_seed_alignment_issue_impl(
        user_input,
        war_room_output,
        recent_context,
        user_turn_targets_assistant_reply=_user_turn_targets_assistant_reply,
    )


def _has_usable_response_seed(response_strategy: dict, user_input: str = ""):
    if not isinstance(response_strategy, dict) or not response_strategy:
        return False
    delivery_mode = _normalize_delivery_freedom_mode(
        str(response_strategy.get("delivery_freedom_mode") or "").strip(),
        str(response_strategy.get("reply_mode") or "").strip(),
    )
    if delivery_mode == "clean_failure":
        return False
    direct_seed = str(response_strategy.get("direct_answer_seed") or "").strip()
    return _has_meaningful_delivery_seed(direct_seed, user_input)


def _strategy_supports_direct_phase3(
    response_strategy: dict,
    user_input: str = "",
    recent_context: str = "",
):
    if _has_usable_response_seed(response_strategy, user_input):
        return True

    policy = _answer_mode_policy_for_turn(user_input, recent_context)
    if bool(policy.get("current_turn_grounding_ready")):
        return True

    return bool(policy.get("parametric_knowledge_allowed"))


def _fallback_war_room_output(user_input: str, operation_plan: dict, response_strategy: dict, war_room_contract: dict, recent_context: str = ""):
    return _fallback_war_room_output_impl(
        user_input,
        operation_plan,
        response_strategy,
        war_room_contract,
        recent_context,
        looks_like_generic_non_answer_text=_looks_like_generic_non_answer_text,
        looks_like_user_parroting_report=_looks_like_user_parroting_report,
        war_room_seed_alignment_issue=_war_room_seed_alignment_issue,
        is_emotional_vent_turn=_is_emotional_vent_turn,
    )


def phase_warroom_deliberator(state: AnimaState):
    return _run_phase_warroom_deliberator(
        state,
        llm=llm,
        operation_plan_from_state=_operation_plan_from_state,
        normalize_action_plan=_normalize_action_plan,
        working_memory_packet_for_prompt=_working_memory_packet_for_prompt,
        attach_ledger_event=_attach_ledger_event,
        war_room_output_is_usable=_war_room_output_is_usable,
        war_room_seed_alignment_issue=_war_room_seed_alignment_issue,
        response_strategy_from_war_room_output=_response_strategy_from_war_room_output,
        fallback_war_room_output=_fallback_war_room_output,
    )


def phase_119_rescue(state: AnimaState):
    return _run_phase_119_rescue(
        state,
        operation_plan_from_state=_operation_plan_from_state,
        normalize_goal_lock=_normalize_goal_lock,
        compact_user_facing_summary=_compact_user_facing_summary,
        dedupe_keep_order=_dedupe_keep_order,
        clean_failure_missing_items=_clean_failure_missing_items,
        build_clean_failure_packet=_build_clean_failure_packet,
        empty_reasoning_board=_empty_reasoning_board,
        empty_verdict_board=_empty_verdict_board,
        make_auditor_decision=_make_auditor_decision,
        normalize_readiness_decision=normalize_readiness_decision,
        attach_ledger_event=_attach_ledger_event,
        print_fn=print,
    )


def phase_3_validator(state: AnimaState):
    return _run_phase_3_validator(
        state,
        llm=llm,
        sanitize_response_strategy_for_phase3=_sanitize_response_strategy_for_phase3,
        phase3_recent_context_excerpt=_phase3_recent_context_excerpt,
        phase3_reference_policy=_phase3_reference_policy,
        build_judge_speaker_packet=_build_judge_speaker_packet,
        build_phase3_lane_delivery_packet=_build_phase3_lane_delivery_packet,
        build_phase3_delivery_payload=_build_phase3_delivery_payload,
        build_phase3_speaker_judge_contract=_build_phase3_speaker_judge_contract,
        normalize_readiness_decision=normalize_readiness_decision,
        normalize_user_facing_text=_normalize_user_facing_text,
        attach_ledger_event=_attach_ledger_event,
        print_fn=print,
    )


def phase_delivery_review(state: AnimaState):
    return _run_phase3_delivery_review(
        state,
        llm=llm,
        attach_ledger_event=_attach_ledger_event,
        print_fn=print,
    )


def phase_minus_1s_start_gate(state: AnimaState):
    return _run_phase_minus_1s_start_gate(
        state,
        plan_reasoning_budget=_plan_reasoning_budget,
        resolve_reasoning_budget=_resolve_reasoning_budget,
        fast_start_gate_assessment=_fast_start_gate_assessment,
        llm_start_gate_turn_contract=_llm_start_gate_turn_contract,
        build_start_gate_switches=_build_start_gate_switches,
        make_auditor_decision=_make_auditor_decision,
        extract_current_turn_grounding_facts=_extract_current_turn_grounding_facts,
        response_strategy_from_answer_mode_policy=_response_strategy_from_answer_mode_policy,
        attach_ledger_event=_attach_ledger_event,
        print_fn=print,
    )


def _start_gate_requests_memory_recall(state: dict | None, user_input: str = ""):
    state = state if isinstance(state, dict) else {}
    contract = state.get("start_gate_contract", {})
    if not isinstance(contract, dict):
        contract = {}
    turn_contract = contract.get("turn_contract", {})
    if not isinstance(turn_contract, dict):
        switches = state.get("start_gate_switches", {})
        if isinstance(switches, dict):
            turn_contract = switches.get("start_gate_turn_contract", {})
    if isinstance(turn_contract, dict) and turn_contract:
        intent = str(turn_contract.get("user_intent") or "").strip()
        answer_mode = str(turn_contract.get("answer_mode_preference") or "").strip()
        return intent == "requesting_memory_recall" or answer_mode == "grounded_recall"

    answer_mode_policy = contract.get("answer_mode_policy", {})
    if not isinstance(answer_mode_policy, dict):
        switches = state.get("start_gate_switches", {})
        answer_mode_policy = switches.get("answer_mode_policy", {}) if isinstance(switches, dict) else {}
    if isinstance(answer_mode_policy, dict) and answer_mode_policy:
        question_class = str(answer_mode_policy.get("question_class") or "").strip()
        preferred_mode = str(answer_mode_policy.get("preferred_answer_mode") or "").strip()
        if question_class in {"requesting_memory_recall", "grounded_memory_recall"}:
            return True
        if preferred_mode == "grounded_recall":
            return True
        if bool(answer_mode_policy.get("direct_delivery_allowed")):
            return False

    return False


def phase_2_analyzer(state: AnimaState):
    return _run_phase_2_analyzer(
        state,
        llm=llm,
        analysis_report_schema=AnalysisReport,
        build_phase_2b_prompt=build_phase_2b_prompt,
        working_memory_packet_for_prompt=_working_memory_packet_for_prompt,
        raw_read_report_packet_for_prompt=_raw_read_report_packet_for_prompt,
        build_source_relay_packet=_build_source_relay_packet,
        source_relay_packet_for_prompt=_source_relay_packet_for_prompt,
        planned_operation_contract_from_state=_planned_operation_contract_from_state,
        normalize_execution_trace=_normalize_execution_trace,
        tool_carryover_from_state=_tool_carryover_from_state,
        evidence_ledger_for_prompt=evidence_ledger_for_prompt,
        normalize_analysis_with_source_relay=_normalize_analysis_with_source_relay,
        enforce_field_memo_judgments=_enforce_field_memo_judgments,
        build_reasoning_board_from_analysis=_build_reasoning_board_from_analysis,
        war_room_from_critic=_war_room_from_critic,
        execution_trace_after_phase2b=_execution_trace_after_phase2b,
        attach_ledger_event=_attach_ledger_event,
        print_fn=print,
    )


# ==========================================================
# Canonical active bindings
# ==========================================================
_is_recent_dialogue_review_turn = _shared_is_recent_dialogue_review_turn
_is_assistant_question_request_turn = _shared_is_assistant_question_request_turn
_is_directive_or_correction_turn = _shared_is_directive_or_correction_turn
_is_initiative_request_turn = _shared_is_initiative_request_turn
def _classify_requested_assistant_move(user_input: str, recent_context: str = ""):
    del user_input, recent_context
    return ""
phase_2a_reader = _base_phase_2a_reader



# ==========================================================
# Simplified active overrides
# ==========================================================
def _is_followup_offer_acceptance_turn(user_input: str, working_memory: dict):
    return _is_followup_offer_acceptance_turn_impl(
        user_input,
        working_memory,
        extract_artifact_hint=_extract_artifact_hint,
        extract_explicit_search_keyword=_extract_explicit_search_keyword,
        is_assistant_investigation_request_turn=_is_assistant_investigation_request_turn,
        is_creative_story_request_turn=_is_creative_story_request_turn,
        is_directive_or_correction_turn=_shared_is_directive_or_correction_turn,
    )


def _recent_context_anchor_query(recent_context: str, working_memory: dict | None = None):
    return _recent_context_anchor_query_impl(
        recent_context,
        working_memory,
        extract_recent_raw_turns_from_context=_extract_recent_raw_turns_from_context,
        extract_search_anchor_terms_from_text=_extract_search_anchor_terms_from_text,
        temporal_context_allows_carry_over=_temporal_context_allows_carry_over,
        query_from_anchor_terms=_query_from_anchor_terms,
    )


def _compiled_memory_recall_queries(
    user_input: str,
    recent_context: str = "",
    working_memory: dict | None = None,
    strategist_output: dict | None = None,
    analysis_data: dict | None = None,
    tool_carryover: dict | None = None,
):
    return _compiled_memory_recall_queries_impl(
        user_input,
        recent_context=recent_context,
        working_memory=working_memory,
        strategist_output=strategist_output,
        analysis_data=analysis_data,
        tool_carryover=tool_carryover,
        is_memory_state_disclosure_turn=is_memory_state_disclosure_turn,
        looks_like_current_turn_memory_story_share=_looks_like_current_turn_memory_story_share,
        looks_like_memo_recall_turn=looks_like_memo_recall_turn,
        extract_explicit_search_keyword=_extract_explicit_search_keyword,
        looks_like_deictic_memory_query=_looks_like_deictic_memory_query,
        deterministic_search_keyword_from_user_input=_deterministic_search_keyword_from_user_input,
        extract_search_anchor_terms_from_text=_extract_search_anchor_terms_from_text,
        query_from_anchor_terms=_query_from_anchor_terms,
        recent_context_anchor_query=_recent_context_anchor_query,
        temporal_context_allows_carry_over=_temporal_context_allows_carry_over,
        clean_strategist_search_fragment=_clean_strategist_search_fragment,
        normalize_search_keyword=_normalize_search_keyword,
        search_query_is_overbroad_or_instruction=_search_query_is_overbroad_or_instruction,
        is_generic_continue_seed=_is_generic_continue_seed,
        looks_like_generic_non_answer_text=_looks_like_generic_non_answer_text,
        looks_like_fake_tool_or_meta_string=_looks_like_fake_tool_or_meta_string,
    )


def _deterministic_strategist_tool_request_from_context(
    user_input: str,
    working_memory: dict | None = None,
    *,
    tool_carryover: dict | None = None,
):
    return _deterministic_strategist_tool_request_from_context_impl(
        user_input,
        working_memory,
        tool_carryover=tool_carryover,
        is_memory_state_disclosure_turn=is_memory_state_disclosure_turn,
        looks_like_scroll_followup_turn=_looks_like_scroll_followup_turn,
        tool_carryover_anchor_id=_tool_carryover_anchor_id,
        scroll_direction_from_user_input=_scroll_direction_from_user_input,
        deterministic_search_keyword_from_user_input=_deterministic_search_keyword_from_user_input,
    )


def _strategist_tool_request_from_context(
    user_input: str,
    analysis_data: dict,
    working_memory: dict,
    *,
    recent_context: str = "",
    start_gate_switches: dict | None = None,
    tool_carryover: dict | None = None,
):
    return _strategist_tool_request_from_context_impl(
        user_input,
        analysis_data,
        working_memory,
        recent_context=recent_context,
        start_gate_switches=start_gate_switches,
        tool_carryover=tool_carryover,
        llm=llm,
        valid_strategist_tool_request=_valid_strategist_tool_request,
        is_memory_state_disclosure_turn=is_memory_state_disclosure_turn,
        looks_like_scroll_followup_turn=_looks_like_scroll_followup_turn,
        tool_carryover_anchor_id=_tool_carryover_anchor_id,
        scroll_direction_from_user_input=_scroll_direction_from_user_input,
        compiled_memory_recall_queries=_compiled_memory_recall_queries,
        logger=print,
    )

