import ast
import builtins
import json
import re
import sys
import unicodedata
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_ollama import ChatOllama
from .state import AnimaState
from .tools import available_tools
from tools import toolbox
from tools.toolbox import get_db_session
from pydantic import BaseModel, Field
from typing import Dict, List, Literal

llm = ChatOllama(model="gemma3:12b", temperature=0.0)
llm_supervisor = ChatOllama(model="llama3.1", temperature=0.0)

def _log(message: str):
    text = str(message)
    try:
        builtins.print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        builtins.print(safe_text)

print = _log

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

class AnalysisReport(BaseModel):
    evidences: List[EvidenceItem] = Field(description="Evidence items extracted from raw search results.")
    source_judgments: List[SourceJudgment] = Field(
        default_factory=list,
        description="Per-source prosecutor judgments derived from the raw relay packet."
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
    read_mode: Literal["current_turn_only", "recent_dialogue_review", "full_raw_review", "empty"] = Field(
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
    answer_goal: str = Field(description="Primary goal of the response.")
    tone_strategy: str = Field(description="Tone and stance guidance for the response.")
    evidence_brief: str = Field(description="Compressed factual brief prepared for phase_3.")
    reasoning_brief: str = Field(description="Short explanation of how facts connect to the user request.")
    direct_answer_seed: str = Field(description="Grounded answer seed that phase_3 can reuse.")
    must_include_facts: List[str] = Field(description="Facts that must appear or be respected in the response.")
    must_avoid_claims: List[str] = Field(description="Claims that must not appear because they are ungrounded or risky.")
    answer_outline: List[str] = Field(description="Practical outline for the final answer.")
    uncertainty_policy: str = Field(description="How to speak when evidence is weak or incomplete.")

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
    recommended_searches: List[str] = Field(description="Exact tool calls or search requests recommended by the critic.")
    recommended_action: Literal["answer_now", "search_more", "insufficient_evidence"] = Field(
        description="Critic recommendation before the judge makes a final decision."
    )

class AdvocateReport(BaseModel):
    defense_strategy: str = Field(description="How -1a wants to defend or present the case.")
    summary_of_position: str = Field(description="Short summary of the advocate position.")
    supported_pair_ids: List[str] = Field(description="Reasoning pairs that the advocate wants to push forward.")
    response_contract: Dict[str, str] = Field(description="Short response-level contract derived from the strategy.")

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

class StrategistReasoningOutput(BaseModel):
    case_theory: str = Field(description="Master-plan summary based on the user's state and the critic's diagnosis.")
    action_plan: StepByStepPlan = Field(description="Concrete plan for what the system should do on this turn.")
    response_strategy: ResponseStrategy | None = Field(
        default=None,
        description="Response script only when the current step is final-answer delivery. Leave null when evidence collection or planning comes first."
    )
    candidate_pairs: List[AnchoredReasoningPair] = Field(
        description="Candidate reasoning pairs. Each pair must reference existing fact_ids."
    )

class AuditorOutput(BaseModel):
    is_satisfied: bool = Field(description="Whether the turn may proceed to phase_3 without more tool use.")
    rejection_reason: str = Field(description="Short audit memo explaining the decision.")
    instruction_to_0: str = Field(description="Exact tool call for phase_0, or empty string.")


class ReasoningBudgetPlan(BaseModel):
    reasoning_budget: int = Field(description="How many reasoning/search loops are worth spending on this turn. 0 means answer directly.")
    preferred_path: Literal["direct_answer", "internal_reasoning", "tool_first"] = Field(
        description="Recommended first path for this turn."
    )
    should_use_tools: bool = Field(description="Whether tool use is likely worthwhile for this turn.")
    rationale: str = Field(description="Short operational explanation for the budget choice.")


class WarRoomFreedom(BaseModel):
    granted: bool = Field(description="Whether non-tool reasoning freedom is currently granted.")
    granted_by: str = Field(description="Who most recently granted or denied the freedom.")
    scope: Literal["none", "planning_only", "bounded_speculation", "direct_empathy"] = Field(
        description="Permitted range of non-tool reasoning."
    )
    reason: Literal["none", "no_tool_needed", "no_suitable_tool", "tool_would_not_help", "user_requested_direct_thinking", "evidence_gap"] = Field(
        description="Operational reason for the current freedom state."
    )
    note: str = Field(description="Short explanation of the current freedom setting.")


class WarRoomDuty(BaseModel):
    must_label_hypotheses: bool = Field(description="Whether hypotheses must be labeled explicitly.")
    must_separate_fact_and_opinion: bool = Field(description="Whether facts and interpretations must stay separated.")
    must_report_missing_info: bool = Field(description="Whether missing information must be surfaced explicitly.")
    must_not_upgrade_guess_to_fact: bool = Field(description="Whether guesses must never be upgraded into facts.")
    boundary_note: str = Field(description="Short note about the current speech boundary.")


class WarRoomEpistemicDebt(BaseModel):
    debt_kind: List[str] = Field(description="Kinds of current epistemic debt, such as evidence_gap or tool_gap.")
    missing_items: List[str] = Field(description="Concrete missing items or unanswered points.")
    why_tool_not_used: str = Field(description="Why tools were not used or why they would not help enough.")
    next_best_action: str = Field(description="Best next action to reduce the debt.")


class WarRoomAgentNote(BaseModel):
    agent_name: str = Field(description="Agent that wrote this note, such as phase_2b, -1a, or -1b.")
    used_freedom: bool = Field(description="Whether the agent actually used non-tool reasoning freedom.")
    freedom_scope: str = Field(description="Scope of freedom used by the agent.")
    shortage_reason: str = Field(description="What was missing or constrained at this stage.")
    missing_items: List[str] = Field(description="Concrete missing items noticed by this agent.")
    why_no_tool: str = Field(description="Why the agent did not use tools or why tools were insufficient.")
    allowed_output_boundary: str = Field(description="What this agent believes may safely be said.")


class WarRoomStateV1(BaseModel):
    freedom: WarRoomFreedom
    duty: WarRoomDuty
    epistemic_debt: WarRoomEpistemicDebt
    agent_notes: List[WarRoomAgentNote]

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

    return {
        "action": action,
        "operational_state": action,
        "tool_name": tool_name,
        "tool_args": normalized_tool_args,
        "instruction": instruction,
        "memo": str(memo or "").strip(),
    }


def _tool_candidate_for_case(user_input: str, analysis_data: dict, working_memory: dict | None = None):
    artifact_hint = _extract_artifact_hint(user_input)
    if artifact_hint:
        return {
            "tool_name": "tool_read_artifact",
            "tool_args": {"artifact_hint": artifact_hint},
            "memo": "Artifact review is needed before answering.",
        }

    if _should_default_to_memory_search(user_input, analysis_data, working_memory or {}):
        keyword = _normalize_search_keyword(str((analysis_data or {}).get("analytical_thought") or user_input))
        if keyword:
            return {
                "tool_name": "tool_search_memory",
                "tool_args": {"keyword": keyword},
                "memo": "Memory search may provide missing grounding for this turn.",
            }

    return None

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
            "reasoning_budget": 0,
            "preferred_path": "direct_answer",
            "should_use_tools": False,
            "rationale": "A short direct reply is enough for this follow-up.",
        }
    if _should_default_to_memory_search(text, {}, working_memory):
        return {
            "reasoning_budget": 2,
            "preferred_path": "tool_first",
            "should_use_tools": True,
            "rationale": "Current evidence looks thin, so retrieval should come first.",
        }
    return {
        "reasoning_budget": 1,
        "preferred_path": "internal_reasoning",
        "should_use_tools": False,
        "rationale": "One round of internal reasoning is appropriate before responding.",
    }

def _plan_reasoning_budget(user_input: str, recent_context: str, working_memory: dict):
    artifact_hint = _extract_artifact_hint(user_input)
    working_memory_packet = _working_memory_packet_for_prompt(working_memory)
    sys_prompt = f"""당신은 ANIMA의 추론 예산 플래너다.

현재 사용자 입력, 최근 맥락, working_memory를 보고 이번 턴에 어느 정도의 사고 깊이가 필요한지 결정하라.
의미 판단은 모델이 하되, 과소사고와 과잉탐색을 모두 피하라.
모든 자유서술 필드는 한국어로 짧고 읽기 쉽게 작성하라.

[user_input]
{user_input}

[recent_context]
{recent_context}

[working_memory]
{working_memory_packet}

[artifact_hint]
{artifact_hint if artifact_hint else '없음'}

[reasoning_budget scale]
- 0: 직접 답변이면 충분함
- 1: 짧은 내부 사고 1회
- 2: 더 깊은 내부 점검 또는 근거 검토
- 3~4: 정말 복잡해서 추가 작업이 필요한 턴

[rules]
1. 단순 후속 응답이면 direct_answer를 고른다.
2. 의미는 분명하지만 한 번 더 조심스럽게 볼 필요가 있으면 internal_reasoning을 고른다.
3. 문서, 부가자료, 검색 회수가 핵심이면 tool_first를 고른다.
4. artifact_hint가 있으면 tool_first를 강하게 우선한다.
5. reasoning_budget은 계획이지 딱딱한 하드 스톱이 아니다.
6. preferred_path는 direct_answer, internal_reasoning, tool_first 중 하나여야 한다.
"""

    try:
        structured_llm = llm.with_structured_output(ReasoningBudgetPlan)
        res = structured_llm.invoke([SystemMessage(content=sys_prompt)])
        plan = res.model_dump()
        plan["reasoning_budget"] = max(0, min(int(plan.get("reasoning_budget", 1)), 4))
        if artifact_hint and plan["preferred_path"] != "tool_first":
            plan["preferred_path"] = "tool_first"
            plan["should_use_tools"] = True
        return plan
    except Exception as e:
        print(f"[추론 예산 플래너] 구조화 출력 예외로 fallback을 사용합니다: {e}")
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


def _raw_read_report_packet_for_prompt(raw_read_report: dict):
    if not raw_read_report:
        return "사용 가능한 원문 검토 보고가 없습니다."
    packet = {
        "read_mode": raw_read_report.get("read_mode", ""),
        "reviewed_all_input": raw_read_report.get("reviewed_all_input", False),
        "source_summary": raw_read_report.get("source_summary", ""),
        "items": raw_read_report.get("items", []),
        "coverage_notes": raw_read_report.get("coverage_notes", ""),
    }
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)

def _build_source_relay_packet(raw_read_report: dict):
    if not isinstance(raw_read_report, dict) or not raw_read_report:
        return {
            "read_mode": "empty",
            "reviewed_all_input": False,
            "global_source_summary": "",
            "global_coverage_notes": "",
            "source_packets": [],
        }

    read_mode = str(raw_read_report.get("read_mode") or "").strip() or "empty"
    reviewed_all_input = bool(raw_read_report.get("reviewed_all_input", False))
    global_source_summary = str(raw_read_report.get("source_summary") or "").strip()
    global_coverage_notes = str(raw_read_report.get("coverage_notes") or "").strip()
    grouped = {}

    for item in raw_read_report.get("items", []):
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id") or "").strip() or "unknown_source"
        source_type = str(item.get("source_type") or "").strip() or "unknown"
        key = (source_id, source_type)
        packet = grouped.setdefault(key, {
            "source_id": source_id,
            "source_type": source_type,
            "source_summary": "",
            "coverage_notes": "",
            "must_forward_facts": [],
            "quoted_excerpts": [],
            "coverage_complete": reviewed_all_input,
        })
        observed_fact = str(item.get("observed_fact") or "").strip()
        excerpt = str(item.get("excerpt") or "").strip()
        if observed_fact and observed_fact not in packet["must_forward_facts"]:
            packet["must_forward_facts"].append(observed_fact)
        if excerpt and excerpt not in packet["quoted_excerpts"]:
            packet["quoted_excerpts"].append(excerpt)

    source_packets = []
    if grouped:
        multi_source = len(grouped) > 1
        for (_, _), packet in grouped.items():
            source_id = packet["source_id"]
            source_type = packet["source_type"]
            packet["source_summary"] = (
                f"{source_type} source `{source_id}` was reviewed by phase_2a."
                if multi_source else
                (global_source_summary or f"{source_type} source `{source_id}` was reviewed by phase_2a.")
            )
            packet["coverage_notes"] = global_coverage_notes or "phase_2a completed a raw read pass for this source."
            packet["must_forward_facts"] = packet["must_forward_facts"][:6]
            packet["quoted_excerpts"] = packet["quoted_excerpts"][:3]
            source_packets.append(packet)

    if not source_packets and read_mode == "current_turn_only":
        source_packets.append({
            "source_id": "current_user_turn",
            "source_type": "current_turn",
            "source_summary": global_source_summary or "The current user turn was reviewed as the only available raw source.",
            "coverage_notes": global_coverage_notes or "No external raw source was available in this turn.",
            "must_forward_facts": [],
            "quoted_excerpts": [],
            "coverage_complete": reviewed_all_input,
        })

    return {
        "read_mode": read_mode,
        "reviewed_all_input": reviewed_all_input,
        "global_source_summary": global_source_summary,
        "global_coverage_notes": global_coverage_notes,
        "source_packets": source_packets,
    }


def _source_relay_packet_for_prompt(source_relay_packet: dict):
    if not isinstance(source_relay_packet, dict) or not source_relay_packet:
        return "사용 가능한 소스 릴레이 패킷이 없습니다."
    try:
        return json.dumps(source_relay_packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(source_relay_packet)

def _normalize_analysis_with_source_relay(analysis_dict: dict, source_relay_packet: dict):
    if not isinstance(analysis_dict, dict):
        analysis_dict = {}
    if not isinstance(source_relay_packet, dict):
        source_relay_packet = {}

    normalized = json.loads(json.dumps(analysis_dict, ensure_ascii=False))
    source_packets = source_relay_packet.get("source_packets", [])
    if not isinstance(source_packets, list):
        source_packets = []

    judgments = normalized.get("source_judgments", [])
    if not isinstance(judgments, list):
        judgments = []
    judgment_map = {}
    for judgment in judgments:
        if not isinstance(judgment, dict):
            continue
        key = (
            str(judgment.get("source_id") or "").strip(),
            str(judgment.get("source_type") or "").strip(),
        )
        judgment_map[key] = judgment

    normalized_judgments = []
    for packet in source_packets:
        if not isinstance(packet, dict):
            continue
        source_id = str(packet.get("source_id") or "").strip() or "unknown_source"
        source_type = str(packet.get("source_type") or "").strip() or "unknown"
        key = (source_id, source_type)
        existing = judgment_map.get(key, {})
        accepted_facts = existing.get("accepted_facts", [])
        if not isinstance(accepted_facts, list):
            accepted_facts = []
        contested_facts = existing.get("contested_facts", [])
        if not isinstance(contested_facts, list):
            contested_facts = []
        missing_info = existing.get("missing_info", [])
        if not isinstance(missing_info, list):
            missing_info = []

        must_forward_facts = [
            str(fact).strip()
            for fact in packet.get("must_forward_facts", [])
            if str(fact).strip()
        ]
        if not accepted_facts and must_forward_facts:
            accepted_facts = must_forward_facts[:3]

        source_status = str(existing.get("source_status") or "").strip().lower()
        if source_status not in {"pass", "objection", "ambiguous", "insufficient"}:
            source_status = "pass" if accepted_facts else "ambiguous"

        normalized_judgments.append({
            "source_id": source_id,
            "source_type": source_type,
            "source_status": source_status,
            "accepted_facts": _dedupe_keep_order([str(f).strip() for f in accepted_facts if str(f).strip()])[:5],
            "contested_facts": _dedupe_keep_order([str(f).strip() for f in contested_facts if str(f).strip()])[:5],
            "objection_reason": str(existing.get("objection_reason") or "").strip(),
            "missing_info": _dedupe_keep_order([str(f).strip() for f in missing_info if str(f).strip()])[:4],
            "search_needed": bool(existing.get("search_needed", False)),
        })

    normalized["source_judgments"] = normalized_judgments

    evidences = normalized.get("evidences", [])
    if not isinstance(evidences, list):
        evidences = []
    existing_evidence_keys = {
        (
            str(item.get("source_id") or "").strip(),
            str(item.get("extracted_fact") or "").strip(),
        )
        for item in evidences
        if isinstance(item, dict)
    }
    for judgment in normalized_judgments:
        source_id = str(judgment.get("source_id") or "").strip()
        source_type = str(judgment.get("source_type") or "").strip()
        for fact in judgment.get("accepted_facts", []):
            key = (source_id, str(fact).strip())
            if not key[1] or key in existing_evidence_keys:
                continue
            evidences.append({
                "source_id": source_id,
                "source_type": source_type,
                "extracted_fact": str(fact).strip(),
            })
            existing_evidence_keys.add(key)
    normalized["evidences"] = evidences
    return normalized


def _enforce_recent_dialogue_review_analysis(analysis_dict: dict, raw_read_report: dict):
    if not isinstance(analysis_dict, dict):
        analysis_dict = {}
    if not isinstance(raw_read_report, dict):
        return analysis_dict

    read_mode = str(raw_read_report.get("read_mode") or "").strip()
    if read_mode != "recent_dialogue_review":
        return analysis_dict

    raw_items = raw_read_report.get("items", [])
    if not isinstance(raw_items, list):
        raw_items = []
    if len(raw_items) < 2:
        return analysis_dict

    normalized = json.loads(json.dumps(analysis_dict, ensure_ascii=False))

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
        "- tool_scan_trend_u_function(keyword=\"...\", track_type=\"Episode\")\n"
        "- tool_scan_trend_u_function_3d(keyword_z=\"...\", keyword_anti_z=\"...\", keyword_y=\"...\", track_type=\"PastRecord\")\n"
    )


def _analysis_packet_for_prompt(analysis_data: dict, include_thought: bool = True):
    if not analysis_data:
        return "사용 가능한 구조화 2차 분석 보고가 없습니다."

    packet = {
        "evidences": analysis_data.get("evidences", []),
        "source_judgments": analysis_data.get("source_judgments", []),
        "situational_brief": analysis_data.get("situational_brief", ""),
        "investigation_status": analysis_data.get("investigation_status", ""),
    }
    if include_thought:
        packet["analytical_thought"] = analysis_data.get("analytical_thought", "")

    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)

def _working_memory_packet_for_prompt(working_memory: dict):
    if not working_memory:
        return "사용 가능한 구조화 working_memory가 없습니다."
    try:
        return json.dumps(working_memory, ensure_ascii=False, indent=2)
    except TypeError:
        return str(working_memory)

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
            "instruction": "답변 범위를 조금만 더 좁혀 주시면 더 정확하게 답할 수 있습니다.",
        }
    if current_loop == 2:
        return {
            "level": "direct",
            "instruction": "정확한 질문, 항목, 또는 슬라이드를 지정해 주시면 그 지점을 바로 답하겠습니다.",
        }
    return {
        "level": "firm",
        "instruction": "정확한 질문 번호나 항목명을 지정해 주세요. 여기서부터는 제가 계속 추측하면 안 됩니다.",
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

def _strategy_packet_for_prompt(strategy_data: dict):
    if not strategy_data:
        return "No -1a strategy packet is available."
    packet = {
        "reply_mode": strategy_data.get("reply_mode", ""),
        "answer_goal": strategy_data.get("answer_goal", ""),
        "tone_strategy": strategy_data.get("tone_strategy", ""),
        "evidence_brief": strategy_data.get("evidence_brief", ""),
        "reasoning_brief": strategy_data.get("reasoning_brief", ""),
        "direct_answer_seed": strategy_data.get("direct_answer_seed", ""),
        "must_include_facts": strategy_data.get("must_include_facts", []),
        "must_avoid_claims": strategy_data.get("must_avoid_claims", []),
        "answer_outline": strategy_data.get("answer_outline", []),
        "uncertainty_policy": strategy_data.get("uncertainty_policy", ""),
    }
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


def _empty_action_plan():
    return {
        "current_step_goal": "",
        "required_tool": "",
        "next_steps_forecast": [],
    }


def _normalize_action_plan(action_plan: dict | None):
    base = _empty_action_plan()
    if not isinstance(action_plan, dict):
        return base
    base["current_step_goal"] = str(action_plan.get("current_step_goal") or "").strip()
    base["required_tool"] = str(action_plan.get("required_tool") or "").strip()
    next_steps = action_plan.get("next_steps_forecast", [])
    if isinstance(next_steps, list):
        base["next_steps_forecast"] = _dedupe_keep_order([str(step).strip() for step in next_steps if str(step).strip()])[:3]
    return base


def _strategist_output_packet_for_prompt(strategist_output: dict):
    if not strategist_output:
        return "No -1a strategist output is available."

    response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}

    packet = {
        "case_theory": str(strategist_output.get("case_theory") or "").strip(),
        "action_plan": _normalize_action_plan(strategist_output.get("action_plan", {})),
        "response_strategy": response_strategy,
        "candidate_pair_count": len(strategist_output.get("candidate_pairs", []))
        if isinstance(strategist_output.get("candidate_pairs"), list)
        else 0,
    }
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)

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

def _empty_critic_report():
    return {
        "situational_brief": "",
        "analytical_thought": "",
        "source_judgments": [],
        "open_questions": [],
        "objections": [],
        "recommended_searches": [],
        "recommended_action": "insufficient_evidence",
    }

def _empty_advocate_report():
    return {
        "defense_strategy": "",
        "summary_of_position": "",
        "supported_pair_ids": [],
        "response_contract": {},
    }

def _empty_verdict_board():
    return {
        "answer_now": False,
        "requires_search": False,
        "approved_fact_ids": [],
        "approved_pair_ids": [],
        "rejected_pair_ids": [],
        "held_pair_ids": [],
        "judge_notes": [],
        "final_answer_brief": "",
    }

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
            "action_plan": _empty_action_plan(),
        },
        "critic_report": _empty_critic_report(),
        "advocate_report": _empty_advocate_report(),
        "verdict_board": _empty_verdict_board(),
    }


def _empty_war_room_state():
    return {
        "freedom": {
            "granted": False,
            "granted_by": "",
            "scope": "none",
            "reason": "none",
            "note": "No freedom is granted by default until a node explicitly earns it.",
        },
        "duty": {
            "must_label_hypotheses": True,
            "must_separate_fact_and_opinion": True,
            "must_report_missing_info": True,
            "must_not_upgrade_guess_to_fact": True,
            "boundary_note": "Facts and opinions must stay separate at all times.",
        },
        "epistemic_debt": {
            "debt_kind": [],
            "missing_items": [],
            "why_tool_not_used": "",
            "next_best_action": "",
        },
        "agent_notes": [],
    }


def _normalize_war_room_state(war_room: dict | None):
    base = _empty_war_room_state()
    if not isinstance(war_room, dict):
        return base
    for section in ("freedom", "duty", "epistemic_debt"):
        value = war_room.get(section)
        if isinstance(value, dict):
            base[section].update(value)
    notes = war_room.get("agent_notes", [])
    if isinstance(notes, list):
        base["agent_notes"] = [note for note in notes if isinstance(note, dict)]
    return base


def _war_room_missing_items_from_analysis(analysis_data: dict):
    missing_items = []
    if not isinstance(analysis_data, dict):
        return missing_items

    for item in analysis_data.get("evidences", []) if isinstance(analysis_data.get("evidences"), list) else []:
        if not isinstance(item, dict):
            continue
        extracted_fact = str(item.get("extracted_fact") or "").strip()
        if extracted_fact:
            break

    analytical_thought = str(analysis_data.get("analytical_thought") or "").strip()
    if analytical_thought and str(analysis_data.get("investigation_status") or "").upper() in {"EXPANSION_REQUIRED", "INCOMPLETE"}:
        missing_items.append(analytical_thought)

    return _dedupe_keep_order([item for item in missing_items if item])[:4]

def _upsert_war_room_agent_note(war_room: dict, note: dict):
    war_room = _normalize_war_room_state(war_room)
    agent_name = str((note or {}).get("agent_name") or "").strip()
    if not agent_name:
        return war_room
    notes = [existing for existing in war_room.get("agent_notes", []) if str(existing.get("agent_name") or "").strip() != agent_name]
    notes.append(note)
    war_room["agent_notes"] = notes[-6:]
    return war_room


def _war_room_from_critic(state: AnimaState, analysis_data: dict, raw_read_report: dict):
    war_room = _normalize_war_room_state(state.get("war_room", {}))
    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    internal_reasoning_only = str((raw_read_report or {}).get("read_mode") or "").strip() == "current_turn_only"
    missing_items = _war_room_missing_items_from_analysis(analysis_data)

    if internal_reasoning_only:
        reason = "tool_would_not_help"
        scope = "planning_only"
        why_no_tool = "The current turn can be examined directly without external retrieval."
    else:
        reason = "none"
        scope = "none"
        why_no_tool = ""

    debt_kind = []
    if status in {"INCOMPLETE", "EXPANSION_REQUIRED"}:
        debt_kind.append("evidence_gap")
    if internal_reasoning_only:
        debt_kind.append("tool_gap")

    war_room["freedom"] = {
        "granted": internal_reasoning_only,
        "granted_by": "phase_2b",
        "scope": scope,
        "reason": reason,
        "note": "phase_2b used no-tool reasoning only because the current turn itself was the main evidence source." if internal_reasoning_only else "phase_2b stayed grounded in retrieved or provided sources.",
    }
    war_room["epistemic_debt"] = {
        "debt_kind": _dedupe_keep_order(debt_kind),
        "missing_items": missing_items,
        "why_tool_not_used": why_no_tool,
        "next_best_action": "Answer now with current evidence." if status == "COMPLETED" else "Hand the diagnosed gap to -1a so the strategist can plan the next step.",
    }
    return _upsert_war_room_agent_note(war_room, {
        "agent_name": "phase_2b",
        "used_freedom": internal_reasoning_only,
        "freedom_scope": scope,
        "shortage_reason": str((analysis_data or {}).get("situational_brief") or "").strip() or "phase_2b identified remaining gaps before a confident answer.",
        "missing_items": missing_items,
        "why_no_tool": why_no_tool or "phase_2b relied on the current turn because no stronger external source was required yet.",
        "allowed_output_boundary": "Only fact-grounded criticism and clearly labeled uncertainty are allowed.",
    })

def _war_room_after_advocate(war_room: dict, analysis_data: dict, strategist_output: dict, reasoning_board: dict):
    war_room = _normalize_war_room_state(war_room)
    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    candidate_pairs = reasoning_board.get("candidate_pairs", []) if isinstance(reasoning_board, dict) else []
    response_strategy = strategist_output.get("response_strategy", {}) if isinstance(strategist_output, dict) else {}
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    action_plan = _normalize_action_plan(strategist_output.get("action_plan", {})) if isinstance(strategist_output, dict) else _empty_action_plan()
    case_theory = str((strategist_output or {}).get("case_theory") or "").strip() if isinstance(strategist_output, dict) else ""
    used_freedom = bool(
        candidate_pairs
        or _has_meaningful_strategy(response_strategy)
        or action_plan.get("current_step_goal")
        or action_plan.get("required_tool")
        or case_theory
    )
    scope = "bounded_speculation" if candidate_pairs else "planning_only"
    missing_items = war_room.get("epistemic_debt", {}).get("missing_items", [])

    war_room["freedom"] = {
        "granted": used_freedom,
        "granted_by": "-1a",
        "scope": scope,
        "reason": "evidence_gap" if status in {"INCOMPLETE", "EXPANSION_REQUIRED"} else "no_tool_needed",
        "note": "-1a used limited reasoning freedom to assemble a defensible response plan from approved facts.",
    }
    war_room["duty"]["boundary_note"] = "Claims must stay anchored to facts, and guesses must remain labeled as guesses."
    return _upsert_war_room_agent_note(war_room, {
        "agent_name": "-1a",
        "used_freedom": used_freedom,
        "freedom_scope": scope,
        "shortage_reason": case_theory or str((analysis_data or {}).get("analytical_thought") or "").strip() or "-1a had to shape a response under incomplete certainty.",
        "missing_items": list(missing_items)[:4],
        "why_no_tool": "When -1a skips tools, it must explain the epistemic gap and hand an explicit plan to -1b instead of improvising.",
        "allowed_output_boundary": "Only defended, fact-anchored response planning is allowed here.",
    })

def _war_room_after_judge(war_room: dict, decision: dict, analysis_data: dict, reasoning_board: dict):
    war_room = _normalize_war_room_state(war_room)
    verdict = reasoning_board.get("verdict_board", {}) if isinstance(reasoning_board, dict) else {}
    action = str((decision or {}).get("action") or "").strip()
    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    requires_search = bool(verdict.get("requires_search")) if isinstance(verdict, dict) else False
    answer_now = bool(verdict.get("answer_now")) if isinstance(verdict, dict) else False
    judge_notes = verdict.get("judge_notes", []) if isinstance(verdict.get("judge_notes"), list) else []
    missing_items = war_room.get("epistemic_debt", {}).get("missing_items", [])

    if action == "call_tool":
        freedom = {
            "granted": False,
            "granted_by": "-1b",
            "scope": "none",
            "reason": "evidence_gap",
            "note": "The judge requires more evidence before allowing delivery.",
        }
    elif action == "plan_more":
        freedom = {
            "granted": True,
            "granted_by": "-1b",
            "scope": "planning_only",
            "reason": "no_suitable_tool",
            "note": "The judge allows another planning pass because the current tools do not fit the case cleanly.",
        }
    elif action == "answer_not_ready":
        freedom = {
            "granted": True,
            "granted_by": "-1b",
            "scope": "planning_only",
            "reason": "no_suitable_tool" if requires_search else "evidence_gap",
            "note": "The judge prefers transparent limits over pretending to be ready.",
        }
    else:
        freedom = {
            "granted": True,
            "granted_by": "-1b",
            "scope": "bounded_speculation" if status in {"INCOMPLETE", "EXPANSION_REQUIRED"} and not requires_search else "planning_only",
            "reason": "evidence_gap" if status in {"INCOMPLETE", "EXPANSION_REQUIRED"} else "no_tool_needed",
            "note": "The judge allows delivery within the approved response boundary.",
        }

    debt_kind = list(war_room.get("epistemic_debt", {}).get("debt_kind", []))
    if requires_search and "evidence_gap" not in debt_kind:
        debt_kind.append("evidence_gap")

    next_best_action = str((decision or {}).get("instruction") or "").strip()
    if action == "phase_3" or answer_now:
        next_best_action = "Deliver the approved answer now."
    elif action == "plan_more":
        next_best_action = "Run one more planning cycle before delivery."
    elif action == "answer_not_ready":
        next_best_action = "Explain the limitation clearly and ask for the smallest useful clarification."

    war_room["freedom"] = freedom
    war_room["epistemic_debt"] = {
        "debt_kind": _dedupe_keep_order(debt_kind),
        "missing_items": list(missing_items)[:4],
        "why_tool_not_used": (
            "The judge determined that another tool call was unnecessary for this turn."
            if action not in {"call_tool", "plan_more", "answer_not_ready"}
            else "The judge kept the case in planning mode because better grounding was still needed."
            if action in {"plan_more", "answer_not_ready"}
            else "The judge selected a tool because the current evidence boundary was too weak."
        ),
        "next_best_action": next_best_action,
    }
    return _upsert_war_room_agent_note(war_room, {
        "agent_name": "-1b",
        "used_freedom": bool(freedom.get("granted")),
        "freedom_scope": str(freedom.get("scope") or "none"),
        "shortage_reason": str((decision or {}).get("memo") or "").strip() or "The judge did not record a detailed shortage memo.",
        "missing_items": list(missing_items)[:4],
        "why_no_tool": war_room["epistemic_debt"]["why_tool_not_used"],
        "allowed_output_boundary": "Only what the judge approved may reach phase_3." + (f" Judge notes: {' / '.join(judge_notes[:2])}" if judge_notes else ""),
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

    board["final_fact_ids"] = [fact["fact_id"] for fact in board["fact_cells"][:3]]
    board["open_questions"] = _dedupe_keep_order(board["open_questions"])
    board["search_requests"] = _dedupe_keep_order(board["search_requests"])
    status = str(analysis_data.get("investigation_status") or "").upper()
    critic_report = _empty_critic_report()
    critic_report["situational_brief"] = str(analysis_data.get("situational_brief") or "").strip()
    critic_report["analytical_thought"] = analytical_thought
    critic_report["source_judgments"] = source_judgments if isinstance(source_judgments, list) else []
    critic_report["open_questions"] = list(board["open_questions"])
    critic_report["recommended_searches"] = []
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

def _reasoning_board_packet_for_prompt(board: dict, approved_only: bool = False):
    if not isinstance(board, dict) or not board:
        return "사용 가능한 추론 보드가 없습니다."

    fact_map = {
        str(fact.get("fact_id") or "").strip(): fact
        for fact in board.get("fact_cells", [])
        if isinstance(fact, dict)
    }

    if approved_only:
        final_fact_ids = board.get("final_fact_ids") or list(fact_map.keys())
        final_pair_ids = set(board.get("final_pair_ids", []))
        approved_pairs = []
        for pair in board.get("candidate_pairs", []):
            if not isinstance(pair, dict):
                continue
            if pair.get("audit_status") != "approved":
                continue
            if final_pair_ids and pair.get("pair_id") not in final_pair_ids:
                continue
            approved_pairs.append(pair)
        packet = {
            "final_fact_cells": [fact_map[fid] for fid in final_fact_ids if fid in fact_map],
            "approved_pairs": approved_pairs,
            "must_avoid_claims": board.get("must_avoid_claims", []),
            "direct_answer_seed": board.get("direct_answer_seed", ""),
            "open_questions": board.get("open_questions", []),
            "strategist_plan": board.get("strategist_plan", {"case_theory": "", "action_plan": _empty_action_plan()}),
            "critic_report": board.get("critic_report", _empty_critic_report()),
            "verdict_board": board.get("verdict_board", _empty_verdict_board()),
        }
    else:
        packet = {
            "fact_cells": board.get("fact_cells", []),
            "candidate_pairs": board.get("candidate_pairs", []),
            "open_questions": board.get("open_questions", []),
            "search_requests": board.get("search_requests", []),
            "final_fact_ids": board.get("final_fact_ids", []),
            "final_pair_ids": board.get("final_pair_ids", []),
            "must_avoid_claims": board.get("must_avoid_claims", []),
            "direct_answer_seed": board.get("direct_answer_seed", ""),
            "strategist_plan": board.get("strategist_plan", {"case_theory": "", "action_plan": _empty_action_plan()}),
            "critic_report": board.get("critic_report", _empty_critic_report()),
            "advocate_report": board.get("advocate_report", _empty_advocate_report()),
            "verdict_board": board.get("verdict_board", _empty_verdict_board()),
        }

    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)

def _verdict_packet_for_prompt(board: dict):
    if not isinstance(board, dict) or not board:
        return "사용 가능한 판결 보드가 없습니다."
    verdict = board.get("verdict_board", {})
    if not isinstance(verdict, dict) or not verdict:
        return "사용 가능한 판결 보드가 없습니다."
    try:
        return json.dumps(verdict, ensure_ascii=False, indent=2)
    except TypeError:
        return str(verdict)

def _build_judge_speaker_packet(reasoning_board: dict, response_strategy: dict, phase3_reference_policy: dict):
    board = reasoning_board if isinstance(reasoning_board, dict) else {}
    strategy = response_strategy if isinstance(response_strategy, dict) else {}
    verdict = board.get("verdict_board", {}) if isinstance(board.get("verdict_board"), dict) else {}
    fact_map = {
        str(fact.get("fact_id") or "").strip(): fact
        for fact in board.get("fact_cells", [])
        if isinstance(fact, dict)
    }
    approved_fact_ids = verdict.get("approved_fact_ids", []) if isinstance(verdict.get("approved_fact_ids"), list) else []
    approved_pair_ids = set(verdict.get("approved_pair_ids", [])) if isinstance(verdict.get("approved_pair_ids"), list) else set()
    approved_fact_cells = [fact_map[fid] for fid in approved_fact_ids if fid in fact_map]

    approved_claims = []
    for pair in board.get("candidate_pairs", []):
        if not isinstance(pair, dict):
            continue
        if pair.get("audit_status") != "approved":
            continue
        pair_id = str(pair.get("pair_id") or "").strip()
        if approved_pair_ids and pair_id not in approved_pair_ids:
            continue
        subjective = pair.get("subjective", {}) if isinstance(pair.get("subjective"), dict) else {}
        claim_text = str(subjective.get("claim_text") or "").strip()
        if not claim_text:
            continue
        approved_claims.append({
            "pair_id": pair_id,
            "paired_fact_digest": str(pair.get("paired_fact_digest") or "").strip(),
            "claim_text": claim_text,
            "answer_policy": str(subjective.get("answer_policy") or "cautious").strip(),
            "uncertainty_note": str(subjective.get("uncertainty_note") or "").strip(),
        })

    raw_reference = ""
    reference_mode = ""
    followup_instruction = ""
    if isinstance(phase3_reference_policy, dict):
        raw_reference = str(phase3_reference_policy.get("raw_reference") or "").strip()
        reference_mode = str(phase3_reference_policy.get("mode") or "").strip()
        followup_instruction = str(phase3_reference_policy.get("followup_instruction") or "").strip()

    verdict_answer_brief = str(verdict.get("final_answer_brief") or "").strip()
    strategy_answer_seed = str(strategy.get("direct_answer_seed") or "").strip()
    if verdict_answer_brief and _looks_like_internal_delivery_leak(verdict_answer_brief) and strategy_answer_seed:
        answer_brief = strategy_answer_seed
    else:
        answer_brief = verdict_answer_brief or strategy_answer_seed
    judge_notes = verdict.get("judge_notes", []) if isinstance(verdict.get("judge_notes"), list) else []
    must_avoid_claims = board.get("must_avoid_claims", []) if isinstance(board.get("must_avoid_claims"), list) else []
    reply_mode = str(strategy.get("reply_mode") or "").strip()
    grounded_mode = bool(approved_fact_cells or approved_claims or answer_brief or raw_reference)

    return {
        "speaker_mode": "grounded_mode" if grounded_mode else "direct_dialogue_mode",
        "reply_mode": reply_mode or ("grounded_answer" if grounded_mode else "cautious_minimal"),
        "answer_now": bool(verdict.get("answer_now", False)),
        "requires_search": bool(verdict.get("requires_search", False)),
        "final_answer_brief": answer_brief,
        "approved_fact_cells": approved_fact_cells,
        "approved_claims": approved_claims,
        "must_avoid_claims": _dedupe_keep_order([str(item).strip() for item in must_avoid_claims if str(item).strip()]),
        "judge_notes": _dedupe_keep_order([str(note).strip() for note in judge_notes if str(note).strip()]),
        "tone_strategy": str(strategy.get("tone_strategy") or "").strip(),
        "uncertainty_policy": str(strategy.get("uncertainty_policy") or "").strip(),
        "answer_outline": strategy.get("answer_outline", []) if isinstance(strategy.get("answer_outline"), list) else [],
        "reference_mode": reference_mode,
        "followup_instruction": followup_instruction,
        "raw_reference_excerpt": raw_reference,
    }


def _judge_speaker_packet_for_prompt(judge_speaker_packet: dict):
    if not isinstance(judge_speaker_packet, dict) or not judge_speaker_packet:
        return "사용 가능한 판사 공개 발화 패킷이 없습니다."
    try:
        return json.dumps(judge_speaker_packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(judge_speaker_packet)

def _normalize_user_facing_text(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


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
        matched = re.match(r"^(user|assistant):\s*(.*)$", line, re.IGNORECASE)
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
    text = str(user_input or "").strip()
    normalized = unicodedata.normalize("NFKC", text).lower()
    if not normalized:
        return False

    review_markers = [
        "최근 대화",
        "지금까지의 대화",
        "이전 대화",
        "방금 대화",
        "대화가 어디가 이상",
        "최근 대화를 읽고",
        "최근 대화를 보고",
        "대화를 읽고 알아내",
        "대화를 읽고 말해",
        "직접 확인해봐",
        "문제점을 말해",
        "어디가 이상한지",
        "네가 알아보라고",
        "네가 알아보라",
        "네가 알아봐",
        "네가 직접 알아봐",
        "니가 알아보라고",
        "니가 알아봐",
        "직접 읽어봐",
        "다시 읽어봐",
        "읽고 판단해",
    ]
    if any(marker in text for marker in review_markers):
        return True

    if recent_context and any(marker in normalized for marker in ["what was weird", "review the conversation", "read the recent chat"]):
        return True

    return False

def _looks_like_internal_delivery_leak(text: str):
    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    if not normalized:
        return False
    internal_markers = [
        "판사",
        "검사",
        "변호사",
        "워룸",
        "speaker review",
        "judge",
        "critic",
        "advocate",
        "speaker packet",
        "judge_speaker_packet",
        "승인된 공개본",
    ]
    return any(marker in normalized for marker in internal_markers)


def _build_speaker_review(judge_speaker_packet: dict, user_input: str = "", recent_context_excerpt: str = ""):
    packet = judge_speaker_packet if isinstance(judge_speaker_packet, dict) else {}
    speaker_mode = str(packet.get("speaker_mode") or "").strip()
    reply_mode = str(packet.get("reply_mode") or "").strip()
    final_answer_brief = str(packet.get("final_answer_brief") or "").strip()
    followup_instruction = str(packet.get("followup_instruction") or "").strip()
    approved_fact_cells = packet.get("approved_fact_cells", []) if isinstance(packet.get("approved_fact_cells"), list) else []
    approved_claims = packet.get("approved_claims", []) if isinstance(packet.get("approved_claims"), list) else []
    reference_mode = str(packet.get("reference_mode") or "").strip()

    issues = []
    missing_for_delivery = []

    if _looks_like_internal_delivery_leak(final_answer_brief):
        issues.append("final_answer_brief is too weak for direct delivery.")

    has_delivery_seed = bool(final_answer_brief or followup_instruction or approved_fact_cells or approved_claims)
    if not has_delivery_seed and reply_mode not in {"ask_user_question_now", "continue_previous_offer"}:
        missing_for_delivery.append("A concrete follow-up instruction is missing.")

    if reply_mode == "grounded_answer" and not (final_answer_brief or approved_fact_cells or approved_claims):
        missing_for_delivery.append("grounded_answer needs at least one grounded fact or claim.")

    if speaker_mode == "grounded_mode" and not (approved_fact_cells or approved_claims or final_answer_brief):
        issues.append("grounded_mode was selected without enough approved delivery material.")

    if reference_mode == "hidden_large_raw" and not (final_answer_brief or followup_instruction):
        missing_for_delivery.append("A direct dialogue path still needs a clearer follow-up intent.")

    if not str(user_input or "").strip() and not str(recent_context_excerpt or "").strip():
        issues.append("Neither the current user input nor recent context is available for speaker delivery.")

    delivery_ok = not issues and not missing_for_delivery
    if delivery_ok:
        suggested_action = "deliver_now"
    elif missing_for_delivery and not approved_fact_cells and not approved_claims:
        suggested_action = "strengthen_response_strategy"
    elif followup_instruction:
        suggested_action = "followup_only"
    else:
        suggested_action = "remand_to_judge"

    return {
        "delivery_ok": delivery_ok,
        "should_remand": not delivery_ok,
        "issues": issues,
        "missing_for_delivery": missing_for_delivery,
        "suggested_action": suggested_action,
        "reply_mode": reply_mode,
    }

def _minimal_direct_dialogue_strategy(user_input: str, working_memory: dict):
    current_user_text = str(user_input or "").strip()
    active_task = _working_memory_active_task(working_memory)
    must_include = [f"현재 사용자 요청: {current_user_text}"] if current_user_text else []
    if active_task and active_task != current_user_text:
        must_include.append(f"현재 작업 맥락: {active_task}")

    return {
        "reply_mode": "cautious_minimal",
        "answer_goal": "현재 사용자 요청에 직접 답하되, 대화 드리프트를 최소화한다.",
        "tone_strategy": "차분하고, 짧고, 근거 중심으로 말한다. 내부 역할 누수와 과한 설명을 피한다.",
        "evidence_brief": f"현재 사용자 요청: {current_user_text}" if current_user_text else "현재 사용자 턴을 주된 근거 앵커로 사용한다.",
        "reasoning_brief": "3차는 현재 요청에 직접 답하고, 정말 필요할 때만 후속 질문 한 개를 붙인다.",
        "direct_answer_seed": "현재 사용자 요청에 직접 답하고, 필요할 때만 정확한 후속 질문 한 개를 덧붙인다.",
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "내부 역할, 판사 패킷, 숨겨진 워크플로를 노출하지 말 것.",
            "현재 패킷이 실제로 지지하지 않는 내용을 아는 척하지 말 것.",
            "직접 답변을 모호한 군더더기나 빈 예의 표현으로 대체하지 말 것.",
        ],
        "answer_outline": [
            "현재 사용자 요청에 직접 답한다.",
            "정말 중요할 때만 한계를 짧게 밝힌다.",
            "필요할 때만 정확한 후속 질문 한 개를 쓴다.",
        ],
        "uncertainty_policy": "근거가 약하면 추측하지 말고 한계를 분명히 말한다.",
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


def _war_room_packet_for_prompt(war_room: dict):
    normalized = _normalize_war_room_state(war_room)
    try:
        return json.dumps(normalized, ensure_ascii=False, indent=2)
    except TypeError:
        return str(normalized)

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

    case_theory = str(strategist_payload.get("case_theory") or "").strip()
    action_plan = _normalize_action_plan(strategist_payload.get("action_plan", {}))
    requested_fact_ids = []
    for pair in candidate_pairs:
        requested_fact_ids.extend(pair.get("fact_ids", []))
    requested_fact_ids = _dedupe_keep_order(requested_fact_ids)

    next_board["candidate_pairs"] = candidate_pairs
    next_board["final_fact_ids"] = [fid for fid in requested_fact_ids if fid in fact_map] or [
        fact["fact_id"] for fact in next_board.get("fact_cells", [])[:3]
    ]
    next_board["final_pair_ids"] = []
    next_board["must_avoid_claims"] = _dedupe_keep_order(response_strategy.get("must_avoid_claims", []))
    next_board["direct_answer_seed"] = str(response_strategy.get("direct_answer_seed") or "").strip()
    next_board["strategist_plan"] = {
        "case_theory": case_theory,
        "action_plan": action_plan,
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
    ) or [
        fact.get("fact_id") for fact in audited.get("fact_cells", [])[:3] if isinstance(fact, dict)
    ]

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


def _fallback_response_strategy(analysis_data: dict):
    evidences = analysis_data.get("evidences", []) if isinstance(analysis_data, dict) else []
    must_include = []
    for item in evidences[:3]:
        fact = str(item.get("extracted_fact") or "").strip()
        if fact:
            must_include.append(fact)

    if must_include:
        answer_goal = "가장 강한 가용 팩트부터 직접 답한다."
        evidence_brief = " / ".join(must_include[:3])
        reasoning_brief = "근거가 있는 팩트부터 앞세우고, 실제로 지지되는 범위 안에서만 답한다."
        direct_answer_seed = "가용한 팩트부터 먼저 사용하고, 꼭 필요한 최소한의 해석만 덧붙인다."
        reply_mode = "grounded_answer"
    else:
        answer_goal = "현재 한계를 분명히 밝히면서 조심스럽게 답한다."
        evidence_brief = "현재 패킷에는 약하거나 불완전한 근거만 들어 있다."
        reasoning_brief = "허세를 부리지 말고 한계를 먼저 밝힌 뒤, 답할 수 있는 범위까지만 답하고 꼭 필요할 때만 정확한 후속 질문을 붙인다."
        direct_answer_seed = "현재 한계를 분명히 말하고, 가용 근거가 허용하는 범위까지만 답한다."
        reply_mode = "cautious_minimal"

    return {
        "reply_mode": reply_mode,
        "answer_goal": answer_goal,
        "tone_strategy": "차분하고, 근거 중심이며, 직접적으로 말한다. 내부 역할 누수와 과한 설명을 피한다.",
        "evidence_brief": evidence_brief,
        "reasoning_brief": reasoning_brief,
        "direct_answer_seed": direct_answer_seed,
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "현재 패킷에 없는 팩트를 만들어내지 말 것.",
            "recent_context를 승인된 증거처럼 과해석하지 말 것.",
            "내부 역할, 판사, 패킷, 숨겨진 워크플로를 노출하지 말 것.",
        ],
        "answer_outline": [
            "사용자 요청에 직접 답한다.",
            "정말 중요할 때만 한계를 짧게 밝힌다.",
            "정말 필요할 때만 정확한 후속 질문 한 개를 묻는다.",
        ],
        "uncertainty_policy": "근거가 약하면 추측 대신 한계를 분명히 밝힌다.",
    }


def _is_casual_social_turn(user_input: str):
    text = str(user_input or "").strip()
    lowered = unicodedata.normalize("NFKC", text).lower()
    if not text:
        return False
    if _is_artifact_review_turn(text):
        return False
    if _is_internal_reasoning_turn(text):
        return False
    if _is_assistant_question_request_turn(text):
        return False
    if _is_directive_or_correction_turn(text):
        return False

    greeting_prefixes = ["안녕", "하이", "ㅎㅇ", "헬로", "좋은 아침", "yo"]
    if any(text.startswith(prefix) for prefix in greeting_prefixes):
        strong_request_markers = ["왜", "어떻게", "뭐", "무엇", "설명", "분석", "판단", "질문", "알아봐"]
        if not any(marker in text for marker in strong_request_markers):
            return True

    social_markers = [
        "고마워", "감사", "ㅋㅋ", "ㅎㅎ", "좋네", "오케이", "오키", "알겠어", "수고", "굿",
    ]
    if any(marker in text for marker in social_markers):
        return True

    return len(text) <= 20 and lowered in {"ok", "okay", "thanks", "thx", "cool", "nice"}


def _is_internal_reasoning_turn(user_input: str):
    text = str(user_input or "").strip()
    lowered = unicodedata.normalize("NFKC", text).lower()
    if not text:
        return False

    explicit_lookup_markers = ["읽어봐", "읽고", "자료", "문서", "부가자료", "기획서", "슬라이드", "pptx", "로그", "채팅"]
    if any(marker in text for marker in explicit_lookup_markers):
        return False

    serious_goal_markers = [
        "목표", "우승", "공모전", "기획", "개선", "전략", "계획", "돈 벌", "경력", "사업", "프로젝트", "시스템", "아키텍처", "논리", "모순",
    ]
    reflective_markers = ["왜", "어떻게", "무엇을", "뭐가 문제", "이상한지", "설명해", "분석해", "생각해봐"]
    english_goal_markers = ["goal", "plan", "career", "money", "build", "project", "startup", "win"]

    return (
        any(marker in text for marker in serious_goal_markers)
        or any(marker in text for marker in reflective_markers)
        or any(marker in lowered for marker in english_goal_markers)
    )


def _is_short_affirmation(user_input: str):
    text = str(user_input or "").strip().lower()
    if not text:
        return False
    normalized = re.sub(r"[\s!~.]+", "", text)
    affirmations = {"응", "그래", "넥", "ㅇㅋ", "오케이", "좋아", "ㅇㅇ", "ok", "okay", "yes", "yep"}
    return normalized in affirmations


def _working_memory_expects_continuation(working_memory: dict):
    if not isinstance(working_memory, dict):
        return False
    dialogue_state = working_memory.get("dialogue_state", {})
    if not isinstance(dialogue_state, dict):
        return False
    return bool(dialogue_state.get("continuation_expected"))


def _working_memory_active_task(working_memory: dict):
    if not isinstance(working_memory, dict):
        return ""
    dialogue_state = working_memory.get("dialogue_state", {})
    if not isinstance(dialogue_state, dict):
        return ""
    return str(dialogue_state.get("active_task") or "").strip()



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
    compact = re.sub(r"\s+", "", lowered)
    if "anima부가자료" in compact or "아니마부가자료" in compact:
        return "ANIMA 부가자료"
    if "anima기획서" in compact or "아니마기획서" in compact:
        return "ANIMA 기획서"
    if "부가자료" in raw:
        pattern = re.search(r"([A-Za-z가-힣0-9 _-]{0,80}부가자료)", raw)
        if pattern:
            return pattern.group(1).strip()
        return "부가자료"
    if "기획서" in raw:
        pattern = re.search(r"([A-Za-z가-힣0-9 _-]{0,80}기획서)", raw)
        if pattern:
            return pattern.group(1).strip()
        return "기획서"

    pattern = re.search(r"([A-Za-z가-힣0-9 _-]{1,80}(?:문서|자료|슬라이드))(?:\s|$)", raw)
    return pattern.group(1).strip() if pattern else ""



def _is_artifact_review_turn(user_input: str):
    text = str(user_input or "").strip()
    if not text:
        return False
    artifact_hint = _extract_artifact_hint(text)
    if not artifact_hint:
        return False
    review_markers = [
        "읽어봐",
        "읽고",
        "봐봐",
        "확인해봐",
        "검토해봐",
        "다 나와있잖아",
        "자료에 있잖아",
        "부가자료에 있잖아",
        "기획서에 있잖아",
        "문서에 있잖아",
        "슬라이드에 있잖아",
    ]
    lowered = text.lower()
    return any(marker in text for marker in review_markers) or any(ext in lowered for ext in [".pptx", ".txt", ".md", ".docx", ".json"])



def _artifact_instruction_from_text(text: str):
    artifact_hint = _extract_artifact_hint(text)
    if not artifact_hint:
        return ""
    return f'tool_read_artifact(artifact_hint={json.dumps(artifact_hint, ensure_ascii=False)})'



def _should_default_to_memory_search(user_input: str, analysis_data: dict, working_memory: dict):
    text = str(user_input or "").strip()
    if not text:
        return False

    if _is_recent_dialogue_review_turn(text):
        return False
    if _is_artifact_review_turn(text):
        return False
    if _is_initiative_request_turn(text):
        return False
    if _is_internal_reasoning_turn(text):
        return False

    explicit_memory_markers = [
        "과거", "기억", "기록", "이전 대화", "지난 대화", "이전 채팅", "다시 찾아", "꺼내봐", "예전에", "그때 말한",
    ]
    if any(marker in text for marker in explicit_memory_markers):
        return True

    evidence_state = working_memory.get("evidence_state", {}) if isinstance(working_memory, dict) else {}
    source_ids = evidence_state.get("active_source_ids", []) if isinstance(evidence_state, dict) else []
    if source_ids and any(marker in text for marker in ["그때", "그 얘기", "그 부분", "이전 것"]):
        return True

    return False


def _recent_context_invites_continuation(recent_context: str):
    text = str(recent_context or "").strip()
    if not text:
        return False

    tail = text[-500:]
    markers = [
        "어떤 점", "자세히", "말해줘", "설명해줘", "알려줘", "궁금해", "확인해줘",
    ]
    if any(marker in tail for marker in markers):
        return True

    question_like_markers = ["?", "무엇", "왜", "어떻게", "어디"]
    return any(marker in tail for marker in question_like_markers)


def _is_followup_ack_turn(user_input: str, recent_context: str):
    return _is_short_affirmation(user_input) and _recent_context_invites_continuation(recent_context)


def _is_initiative_request_turn(user_input: str):
    text = str(user_input or "").strip()
    lowered = text.lower()
    if not text:
        return False
    if _is_assistant_question_request_turn(text):
        return True
    initiative_markers = [
        "네가 알아봐", "네가 알아보라고", "네가 생각해", "네가 생각하라고", "네가 정해", "네가 판단해", "그냥 해봐", "네가 제안해", "직접 해봐",
    ]
    english_markers = ["you decide", "you think", "don't ask", "just propose", "figure it out"]
    return any(marker in text for marker in initiative_markers) or any(marker in lowered for marker in english_markers)


def _is_assistant_question_request_turn(user_input: str):
    text = str(user_input or "").strip()
    lowered = text.lower()
    if not text:
        return False
    question_request_markers = [
        "질문해봐", "질문해 봐", "네가 질문해", "네가 질문하라고", "네가 물어봐", "한 번 물어봐", "한 가지 물어봐", "너가 질문해",
    ]
    english_markers = ["ask me a question", "you ask", "ask first", "ask one question"]
    return any(marker in text for marker in question_request_markers) or any(marker in lowered for marker in english_markers)


def _followup_context_expected(user_input: str, recent_context: str, working_memory: dict):
    return _is_short_affirmation(user_input) and (
        _recent_context_invites_continuation(recent_context)
        or _working_memory_expects_continuation(working_memory)
    )


def _is_directive_or_correction_turn(user_input: str):
    text = str(user_input or "").strip()
    lowered = text.lower()
    if not text:
        return False
    if _is_assistant_question_request_turn(text):
        return True
    directive_markers = [
        "다시 봐", "직접 확인해봐", "네가 확인해봐", "네가 알아봐", "이상해", "틀렸어", "아니라고", "똑바로", "직접 읽어봐", "그거 말고",
    ]
    english_markers = ["you decide", "you think", "don't ask", "just propose", "check it yourself"]
    return any(marker in text for marker in directive_markers) or any(marker in lowered for marker in english_markers)


def _social_turn_strategy(user_input: str):
    user_text = str(user_input or "").strip()
    return {
        "reply_mode": "casual_reaction",
        "answer_goal": "Respond naturally to a light social turn.",
        "tone_strategy": "Stay warm, light, and brief.",
        "evidence_brief": f"Current user turn: {user_text}",
        "reasoning_brief": "No deep analysis is needed for this turn.",
        "direct_answer_seed": "React naturally and keep the conversation moving.",
        "must_include_facts": [f"Current user turn: {user_text}"],
        "must_avoid_claims": [
            "Do not invent hidden intent.",
            "Do not expose internal workflow.",
            "Do not turn a light turn into a heavy analysis.",
        ],
        "answer_outline": [
            "Respond naturally.",
            "Add one short follow-up only if it helps.",
        ],
        "uncertainty_policy": "If the turn is too vague, keep the reply simple instead of bluffing.",
    }


def _followup_ack_strategy(user_input: str, recent_context: str):
    user_text = str(user_input or "").strip()
    return {
        "reply_mode": "continue_previous_offer",
        "answer_goal": "Continue the immediately preceding thread without repeating the whole setup.",
        "tone_strategy": "Assume continuity and move the conversation forward smoothly.",
        "evidence_brief": f"Follow-up acknowledgement: {user_text}",
        "reasoning_brief": "The user appears to be continuing the previous thread rather than opening a new topic.",
        "direct_answer_seed": "Pick up the previous thread naturally and move one step forward.",
        "must_include_facts": [
            f"Follow-up acknowledgement: {user_text}",
            "The previous assistant move likely invited continuation.",
        ],
        "must_avoid_claims": [
            "Do not restart the conversation from zero.",
            "Do not pretend the user supplied brand-new evidence if they did not.",
            "Do not over-explain context the user already knows.",
        ],
        "answer_outline": [
            "Acknowledge the continuation.",
            "Advance the prior thread by one useful step.",
            "Use one precise follow-up only if it is needed.",
        ],
        "uncertainty_policy": "If continuity is weak, ask one small clarifying follow-up instead of forcing it.",
    }


def _initiative_request_strategy(user_input: str, working_memory: dict):
    user_text = str(user_input or "").strip()
    active_task = _working_memory_active_task(working_memory)
    must_include = [f"Current initiative request: {user_text}"]
    if active_task and active_task != user_text:
        must_include.append(f"Active task context: {active_task}")

    return {
        "reply_mode": "continue_previous_offer",
        "answer_goal": "Take initiative and propose the next useful move instead of pushing the decision back to the user.",
        "tone_strategy": "Sound decisive, grounded, and collaborative.",
        "evidence_brief": f"The user asked the assistant to take initiative: {user_text}",
        "reasoning_brief": "The assistant should propose a concrete next move instead of asking vague follow-up questions.",
        "direct_answer_seed": "Make one concrete proposal or next step on your own, then explain it briefly.",
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "Do not bounce the task back to the user with a vague question.",
            "Do not pretend the user supplied a detailed plan if they did not.",
            "Do not leak internal role language.",
        ],
        "answer_outline": [
            "State one concrete initiative.",
            "Explain why that move fits the current context.",
            "Ask for confirmation only if truly necessary.",
        ],
        "uncertainty_policy": "If context is thin, choose a modest and reversible next step.",
    }


def _assistant_question_seed(user_input: str, working_memory: dict):
    text = str(user_input or "").strip()
    question_request_markers = ["\uc9c8\ubb38\ud574\ubd10", "\ub124\uac00 \uc9c8\ubb38\ud574", "\ub124\uac00 \ubb3c\uc5b4\ubd10"]
    goal_markers = ["\ubaa9\ud45c", "\uc6b0\uc2b9", "\uacf5\ubaa8\uc804", "\uacc4\ud68d", "\uc804\ub7b5", "\uae30\ud68d", "\uacbd\ub825"]
    reflective_markers = ["\uc65c", "\uc5b4\ub5bb\uac8c", "\ubb34\uc5c7", "\ubaa8\uc21c", "\ubd88\uc548", "\ubb38\uc81c"]

    if any(marker in text for marker in question_request_markers):
        return "Ask one concrete question that helps the user move the conversation forward right now."
    if any(marker in text for marker in goal_markers):
        return "Ask the one question that will make the user's goal or success criteria clearer."
    if any(marker in text for marker in reflective_markers):
        return "Ask one reflective question that helps the user name the real tension or uncertainty."
    return "Ask one concrete question that reduces ambiguity and moves the conversation forward."


def _answer_not_ready_strategy(user_input: str, war_room: dict):
    debt = war_room.get("epistemic_debt", {}) if isinstance(war_room, dict) else {}
    missing_items = debt.get("missing_items", []) if isinstance(debt, dict) else []
    next_best_action = str(debt.get("next_best_action") or "").strip()
    why_tool_not_used = str(debt.get("why_tool_not_used") or "").strip()

    must_include = ["현재 답변이 아직 완전히 준비되지 않았음을 투명하게 밝혀야 합니다."]
    if missing_items:
        must_include.append(f"가장 중요한 누락 항목: {', '.join(missing_items[:2])}")
    if next_best_action:
        must_include.append(f"다음 최선 행동: {next_best_action}")

    direct_seed = "아직 깔끔하게 마무리할 수 없으므로, 현재 한계와 다음 최선 단계를 분명히 설명한다."
    if missing_items and next_best_action:
        direct_seed = f"가장 큰 누락 항목은 {missing_items[0]}입니다. 가장 분명한 다음 단계는 {next_best_action}입니다."
    elif missing_items:
        direct_seed = f"가장 큰 누락 항목은 {missing_items[0]}이므로, 그 점을 분명히 말해야 합니다."
    elif next_best_action:
        direct_seed = f"다음 최선 단계는 {next_best_action}이므로, 그 점을 분명히 말해야 합니다."

    return {
        "reply_mode": "cautious_minimal",
        "answer_goal": "현재 한계를 솔직하게 밝히고, 가장 분명한 다음 단계를 제안한다.",
        "tone_strategy": "방어적이지 않게, 차분하고 투명하며 실용적으로 말한다.",
        "evidence_brief": f"현재 사용자 요청: {str(user_input or '').strip()}",
        "reasoning_brief": why_tool_not_used or "현재 도구 세트나 근거만으로는 이 문제를 깔끔하게 끝낼 수 없다.",
        "direct_answer_seed": direct_seed,
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "답변이 준비되지 않았는데 준비된 척하지 말 것.",
            "누락된 근거를 숨기지 말 것.",
            "사용자에게 내부 전문용어를 그대로 쏟아내지 말 것.",
        ],
        "answer_outline": [
            "현재 한계를 분명히 말한다.",
            "가장 중요한 누락 항목을 지목한다.",
            "다음 최선 행동을 제안한다.",
        ],
        "uncertainty_policy": "근거가 약할수록 결핍을 더 구체적으로 밝힌다.",
    }


def _ask_user_question_strategy(user_input: str, working_memory: dict):
    active_task = _working_memory_active_task(working_memory)
    must_include = ["지금은 어시스턴트가 사용자에게 구체적인 질문 한 개를 던져야 합니다."]
    if active_task:
        must_include.append(f"현재 작업 맥락: {active_task}")

    return {
        "reply_mode": "ask_user_question_now",
        "answer_goal": "대화를 즉시 앞으로 밀 수 있는 질문 한 개를 던진다.",
        "tone_strategy": "자연스럽고, 집중되어 있으며, 구체적으로 묻는다.",
        "evidence_brief": f"현재 사용자 요청: {str(user_input or '').strip()}",
        "reasoning_brief": "사용자는 애매한 되묻기가 아니라, 어시스턴트가 다음 질문을 먼저 던지길 원한다.",
        "direct_answer_seed": _assistant_question_seed(user_input, working_memory),
        "must_include_facts": must_include,
        "must_avoid_claims": [
            "무슨 질문을 원하냐고 다시 떠넘기지 말 것.",
            "핵심 질문을 두 개 이상 던지지 말 것.",
            "질문을 내부 역할 설명으로 바꾸지 말 것.",
        ],
        "answer_outline": [
            "구체적인 질문 한 개를 던진다.",
            "지금 대화 흐름에 붙어 있게 묻는다.",
        ],
        "uncertainty_policy": "맥락이 얇으면 넓은 질문 대신 가장 작은 유효 질문 하나를 고른다.",
    }


def _normalize_search_keyword(text: str):
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if _extract_artifact_hint(cleaned):
        return ""
    cleaned = re.sub(
        r"(이전 답변|이전 대화|최근 대화|지금까지의 대화|직접 확인해봐|다시 읽어봐|읽고 판단해|네가 알아보라고)",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"(찾아봐|알아봐|확인해봐|검토해봐|말해봐)$", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    if len(cleaned) > 60:
        return ""
    return cleaned or "최근"


def _normalize_suggested_instruction(suggestion: str):
    if not suggestion:
        return ""

    suggestion = str(suggestion).strip()
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

    keyword = _normalize_search_keyword(suggestion)
    if not keyword:
        return ""
    return f'tool_search_memory(keyword={json.dumps(keyword, ensure_ascii=False)})'

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
    try:
        serialized_args = json.dumps(tool_args, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        serialized_args = str(tool_args)
    return f"{tool_name}:{serialized_args}"

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
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", str(text or "")):
            terms.add(token.lower())
    return terms

def _decision_uses_unanchored_topic(decision: dict, user_input: str, analysis_data: dict):
    if not isinstance(decision, dict):
        return False
    candidate_texts = [
        decision.get("memo", ""),
        decision.get("instruction", ""),
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


def _preferred_decision_from_analysis(
    analysis_data: dict,
    loop_count: int,
    user_input: str = "",
    working_memory: dict | None = None,
    reasoning_budget: int = 1,
):
    status = str(analysis_data.get("investigation_status") or "").upper()
    situational_brief = str(analysis_data.get("situational_brief") or "").strip()
    budget_limit, soft_limit = _soft_reasoning_budget_limit(reasoning_budget)
    recent_review = _is_recent_dialogue_review_turn(user_input)

    if status == "COMPLETED":
        memo = situational_brief or "Phase 2 judged the case complete enough for delivery."
        return _make_auditor_decision("phase_3", memo=memo)

    if status == "EXPANSION_REQUIRED":
        tool_candidate = _tool_candidate_for_case(user_input, analysis_data, working_memory)
        if tool_candidate:
            return _make_auditor_decision(
                "call_tool",
                memo=situational_brief or str(tool_candidate.get("memo") or "A suitable tool candidate was found for the unresolved gap."),
                tool_name=str(tool_candidate.get("tool_name") or ""),
                tool_args=tool_candidate.get("tool_args", {}),
            )

        if loop_count <= soft_limit or recent_review:
            over_budget_note = "The soft reasoning budget was reached, but the case can still continue because the graph-level hard stop remains available."
            memo = situational_brief or (over_budget_note if loop_count >= budget_limit else "The case still needs one more planning or review step before a confident answer.")
            return _make_auditor_decision("plan_more", memo=memo)

        return _make_auditor_decision(
            "answer_not_ready",
            memo=situational_brief or "The gap is still unresolved, so the assistant should explain the limit instead of bluffing.",
        )

    if status == "INCOMPLETE":
        tool_candidate = _tool_candidate_for_case(user_input, analysis_data, working_memory)
        if tool_candidate and (loop_count <= soft_limit or recent_review):
            return _make_auditor_decision(
                "call_tool",
                memo=situational_brief or str(tool_candidate.get("memo") or "A tool candidate may recover the missing evidence."),
                tool_name=str(tool_candidate.get("tool_name") or ""),
                tool_args=tool_candidate.get("tool_args", {}),
            )
        if loop_count <= soft_limit or recent_review:
            memo = situational_brief or "The evidence is still incomplete, so the war room should continue before final delivery."
            return _make_auditor_decision("plan_more", memo=memo)
        return _make_auditor_decision(
            "answer_not_ready",
            memo=situational_brief or "The evidence is still incomplete, so the assistant should surface the missing pieces clearly.",
        )

    return None


def _preferred_decision_from_verdict(
    reasoning_board: dict,
    analysis_data: dict,
    loop_count: int,
    user_input: str = "",
    working_memory: dict | None = None,
    reasoning_budget: int = 1,
):
    if not isinstance(reasoning_board, dict):
        return None

    verdict = reasoning_board.get("verdict_board", {})
    if not isinstance(verdict, dict) or not verdict:
        return None

    answer_now = bool(verdict.get("answer_now"))
    requires_search = bool(verdict.get("requires_search"))
    judge_notes = verdict.get("judge_notes", []) if isinstance(verdict.get("judge_notes"), list) else []
    final_answer_brief = str(verdict.get("final_answer_brief") or "").strip()
    approved_fact_ids = verdict.get("approved_fact_ids", []) if isinstance(verdict.get("approved_fact_ids"), list) else []
    approved_pair_ids = verdict.get("approved_pair_ids", []) if isinstance(verdict.get("approved_pair_ids"), list) else []

    situational_brief = str((analysis_data or {}).get("situational_brief") or "").strip()
    budget_limit, soft_limit = _soft_reasoning_budget_limit(reasoning_budget)
    recent_review = _is_recent_dialogue_review_turn(user_input)

    memo_parts = []
    if situational_brief:
        memo_parts.append(situational_brief)
    memo_parts.extend(str(note).strip() for note in judge_notes if str(note).strip())
    if final_answer_brief:
        memo_parts.append(f"Answer brief: {final_answer_brief}")
    memo = " ".join(_dedupe_keep_order(memo_parts)).strip()

    if answer_now or approved_fact_ids or approved_pair_ids:
        return _make_auditor_decision(
            "phase_3",
            memo=memo or "The verdict board approved enough material for phase 3 delivery.",
        )

    if requires_search:
        tool_candidate = _tool_candidate_for_case(user_input, analysis_data, working_memory)
        if tool_candidate:
            return _make_auditor_decision(
                "call_tool",
                memo=memo or str(tool_candidate.get("memo") or "The verdict board still has an unresolved gap with a usable tool candidate."),
                tool_name=str(tool_candidate.get("tool_name") or ""),
                tool_args=tool_candidate.get("tool_args", {}),
            )

        if loop_count <= soft_limit or recent_review:
            over_budget_note = "The soft reasoning budget was reached, but the case can still plan further because the graph-level hard stop remains available."
            return _make_auditor_decision(
                "plan_more",
                memo=memo or (over_budget_note if loop_count >= budget_limit else "The verdict board still needs one more planning step before delivery."),
            )

        return _make_auditor_decision(
            "answer_not_ready",
            memo=memo or "The verdict board still lacks enough material, so the assistant should explain the limit instead of forcing an answer.",
        )

    if not answer_now and not approved_fact_ids and not approved_pair_ids:
        if loop_count <= soft_limit or recent_review:
            return _make_auditor_decision(
                "plan_more",
                memo=memo or "The verdict board is still too thin, so one more planning loop is safer than immediate delivery.",
            )
        return _make_auditor_decision(
            "answer_not_ready",
            memo=memo or "The verdict board is still too thin for safe delivery.",
        )

    return None


def _preferred_decision_from_strategist(
    strategist_output: dict,
    analysis_data: dict,
    loop_count: int,
    reasoning_budget: int = 1,
):
    if not isinstance(strategist_output, dict) or not strategist_output:
        return None

    action_plan = _normalize_action_plan(strategist_output.get("action_plan", {}))
    case_theory = str(strategist_output.get("case_theory") or "").strip()
    response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}

    budget_limit, soft_limit = _soft_reasoning_budget_limit(reasoning_budget)
    step_goal = str(action_plan.get("current_step_goal") or "").strip()
    required_tool = str(action_plan.get("required_tool") or "").strip()
    next_steps = action_plan.get("next_steps_forecast", []) if isinstance(action_plan.get("next_steps_forecast"), list) else []
    memo_parts = [part for part in [case_theory, step_goal] if part]
    if next_steps:
        memo_parts.append(f"Next steps: {' / '.join(str(step).strip() for step in next_steps if str(step).strip())}")
    memo = " ".join(_dedupe_keep_order(memo_parts)).strip()

    if required_tool:
        return _decision_from_instruction(
            required_tool,
            is_satisfied=False,
            memo=memo or "The strategist requested one exact tool action before any final answer.",
        )

    if _has_meaningful_strategy(response_strategy):
        return _make_auditor_decision(
            "phase_3",
            memo=memo or "The strategist says the current step is final delivery and provided a usable response strategy.",
        )

    if step_goal:
        if loop_count <= soft_limit:
            return _make_auditor_decision(
                "plan_more",
                memo=memo or "The strategist still wants another planning step before delivery.",
            )
        return _make_auditor_decision(
            "answer_not_ready",
            memo=memo or "The strategist still has an unfinished plan and cannot justify delivery yet.",
        )

    return None


# Core/nodes.py (phase_minus_1a strategist section)

# ==========================================================
# [Phase -1a: Strategist / Advocate]
# ==========================================================
def _fallback_strategist_output(user_input: str, analysis_data: dict, working_memory: dict, reasoning_board: dict):
    status = str((analysis_data or {}).get("investigation_status") or "").upper()
    case_theory = (
        str((analysis_data or {}).get("situational_brief") or "").strip()
        or str((analysis_data or {}).get("analytical_thought") or "").strip()
        or "The case still needs a clearer operating theory before delivery."
    )
    tool_candidate = _tool_candidate_for_case(user_input, analysis_data, working_memory)
    response_strategy = None

    if status in {"EXPANSION_REQUIRED", "INCOMPLETE"} and tool_candidate:
        action_plan = {
            "current_step_goal": "Collect the next missing fact before attempting a final answer.",
            "required_tool": _tool_call_to_instruction(
                str(tool_candidate.get("tool_name") or ""),
                tool_candidate.get("tool_args", {}),
            ),
            "next_steps_forecast": [
                "Re-run phase 2 on the newly gathered source.",
                "Rebuild the advocate position only after the gap is reduced.",
                "Deliver the final answer when the fact layer is stable.",
            ],
        }
    else:
        response_strategy = _fallback_response_strategy(analysis_data)
        action_plan = {
            "current_step_goal": "Deliver the final answer using the current approved evidence boundary.",
            "required_tool": "",
            "next_steps_forecast": [
                "If the user pushes back, inspect the exact weak point instead of bluffing.",
                "If a new gap appears, hand the case back to phase 2 for another read.",
            ],
        }

    strategist_output = {
        "case_theory": case_theory,
        "action_plan": action_plan,
        "response_strategy": response_strategy,
        "candidate_pairs": [],
    }
    reasoning_board = _apply_strategist_output_to_reasoning_board(reasoning_board, strategist_output)
    return strategist_output, reasoning_board


def phase_minus_1a_thinker(state: AnimaState):
    print("[Phase -1a] 근거를 바탕으로 마스터 플랜을 수립 중...")

    analysis_data = state.get("analysis_report", {})
    status = str(analysis_data.get("investigation_status") or "").upper()
    evidences = analysis_data.get("evidences", []) if isinstance(analysis_data, dict) else []
    reasoning_board = state.get("reasoning_board", {})
    if not isinstance(reasoning_board, dict) or not reasoning_board:
        reasoning_board = _build_reasoning_board_from_analysis(state, analysis_data)

    recent_context = state.get("recent_context", "")
    songryeon_thoughts = state.get("songryeon_thoughts", "")
    tactical_briefing = state.get("tactical_briefing", "")
    user_state = state.get("user_state", "")
    user_char = state.get("user_char", "")
    bio_status = state.get("biolink_status", "")
    time_gap = state.get("time_gap", 0)
    tolerance = state.get("global_tolerance", 1.0)
    auditor_memo = state.get("self_correction_memo", "")
    working_memory = state.get("working_memory", {})
    raw_read_report = state.get("raw_read_report", {})
    war_room = _normalize_war_room_state(state.get("war_room", {}))
    analysis_packet = _analysis_packet_for_prompt(analysis_data, include_thought=True)
    working_memory_packet = _working_memory_packet_for_prompt(working_memory)
    reasoning_board_packet = _reasoning_board_packet_for_prompt(reasoning_board, approved_only=False)
    raw_read_packet = _raw_read_report_packet_for_prompt(raw_read_report)

    if not evidences and status in {"", "INCOMPLETE"}:
        print("  [Phase -1a] 근거가 얇아서 fallback 플래너를 사용합니다.")
        strategist_output, reasoning_board = _fallback_strategist_output(
            state["user_input"],
            analysis_data,
            working_memory,
            reasoning_board,
        )
        response_strategy = strategist_output.get("response_strategy", {})
        if not isinstance(response_strategy, dict):
            response_strategy = {}
        war_room = _war_room_after_advocate(war_room, analysis_data, strategist_output, reasoning_board)
        print(f"  [Phase -1a] current_step_goal={strategist_output.get('action_plan', {}).get('current_step_goal', '')[:120]}")
        print(f"  [Phase -1a] candidate_pairs={len(reasoning_board.get('candidate_pairs', []))}")
        return {
            "strategist_output": strategist_output,
            "response_strategy": response_strategy,
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "thought_logs": [],
        }

    sys_prompt = (
        "당신은 ANIMA의 -1a 마스터 플래너이자 전략가이며 변호사다.\n\n"
        "2b는 사건을 진단만 했다. 당신은 그 진단을 구체적인 단계별 계획으로 바꿔야 한다.\n"
        "당신은 엘리트 변호사이자 전략가다. 근거가 부족하면 섣불리 response_strategy를 쓰지 말라.\n"
        "근거가 약하면 action_plan을 통해 다음에 어떤 정확한 도구를 왜 써야 하는지 계획부터 세워라.\n"
        "현재 단계가 진짜 최종 답변일 때만 response_strategy를 작성하라.\n"
        "모든 자유서술 필드는 한국어로 작성하라.\n\n"
        f"[user_input]\n{state['user_input']}\n\n"
        f"[recent_context]\n{recent_context}\n\n"
        f"[user_state]\n{user_state}\n\n"
        f"[user_char]\n{user_char}\n\n"
        f"[time_gap]\n{time_gap}\n\n"
        f"[global_tolerance]\n{tolerance}\n\n"
        f"[biolink_status]\n{bio_status}\n\n"
        f"[songryeon_thoughts]\n{songryeon_thoughts}\n\n"
        f"[tactical_briefing]\n{tactical_briefing}\n\n"
        f"[working_memory]\n{working_memory_packet}\n\n"
        f"[reasoning_board]\n{reasoning_board_packet}\n\n"
        f"[auditor_memo]\n{auditor_memo if auditor_memo else 'N/A'}\n\n"
        f"[analysis_report]\n{analysis_packet}\n\n"
        f"[raw_read_report]\n{raw_read_packet}\n\n"
        "규칙:\n"
        "1. 2차 evidences와 situational_brief를 출발 근거층으로 취급하라.\n"
        "2. action_plan.required_tool은 정확한 tool call 또는 빈 문자열이어야 한다.\n"
        "3. investigation_status가 INCOMPLETE 또는 EXPANSION_REQUIRED면, 성급한 답변보다 계획과 근거 수집을 우선하라.\n"
        "4. 현재 단계가 최종 답변이 아니면 response_strategy는 null이어도 된다.\n"
        "5. candidate reasoning pair는 반드시 기존 fact_id에 결박되어야 한다.\n"
        "6. paired_fact_digest에는 사실만 넣어라.\n"
        "7. 해석은 subjective.claim_text에, 불확실성은 subjective.uncertainty_note에 넣어라.\n"
        "8. 새 candidate pair는 audit_status='pending'으로 시작해야 한다.\n"
        "9. response_strategy가 있을 때만 must_avoid_claims를 채워라.\n"
        "10. 최종 라우팅 결정은 하지 마라. 당신의 계획 승인 여부는 -1b가 판단한다.\n"
    )

    structured_llm = llm.with_structured_output(StrategistReasoningOutput)
    try:
        res = structured_llm.invoke([SystemMessage(content=sys_prompt)])
        strategist_payload = res.model_dump()
        response_strategy = strategist_payload.get("response_strategy", {})
        if not isinstance(response_strategy, dict):
            response_strategy = {}
        strategist_payload["response_strategy"] = response_strategy
        reasoning_board = _apply_strategist_output_to_reasoning_board(reasoning_board, strategist_payload)
        print(f"  [Phase -1a] current_step_goal={strategist_payload.get('action_plan', {}).get('current_step_goal', '')[:120]}")
        print(f"  [Phase -1a] candidate_pairs={len(reasoning_board.get('candidate_pairs', []))}")
    except Exception as e:
        print(f"[Phase -1a] 구조화 출력 예외: {e}")
        strategist_payload, reasoning_board = _fallback_strategist_output(
            state["user_input"],
            analysis_data,
            working_memory,
            reasoning_board,
        )
        response_strategy = strategist_payload.get("response_strategy", {})
        if not isinstance(response_strategy, dict):
            response_strategy = {}

    war_room = _war_room_after_advocate(war_room, analysis_data, strategist_payload, reasoning_board)
    return {
        "strategist_output": strategist_payload,
        "response_strategy": response_strategy,
        "reasoning_board": reasoning_board,
        "war_room": war_room,
        "thought_logs": [],
    }


def phase_minus_1b_auditor(state: AnimaState):
    print("[Phase -1b] 현재 턴을 감사 중...")

    user_input = str(state.get("user_input") or "")
    recent_context = str(state.get("recent_context") or "")
    analysis_data = state.get("analysis_report", {})
    if not isinstance(analysis_data, dict):
        analysis_data = {}
    has_analysis = bool(analysis_data)
    working_memory = state.get("working_memory", {})
    if not isinstance(working_memory, dict):
        working_memory = {}
    reasoning_board = state.get("reasoning_board", {})
    if not isinstance(reasoning_board, dict):
        reasoning_board = {}
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    war_room = _normalize_war_room_state(state.get("war_room", {}))
    loop_count = int(state.get("loop_count", 0) or 0)

    reasoning_plan = state.get("reasoning_plan", {})
    if not isinstance(reasoning_plan, dict) or not reasoning_plan:
        reasoning_plan = _plan_reasoning_budget(user_input, recent_context, working_memory)
    reasoning_budget = int(state.get("reasoning_budget", reasoning_plan.get("budget", 1)) or reasoning_plan.get("budget", 1) or 1)
    if reasoning_budget < 0:
        reasoning_budget = 0

    artifact_hint = _extract_artifact_hint(user_input)

    if artifact_hint and not has_analysis and reasoning_plan.get("preferred_path") == "tool_first":
        memo = "Artifact review request detected."
        decision = _make_auditor_decision(
            "call_tool",
            memo=memo,
            tool_name="tool_read_artifact",
            tool_args={"artifact_hint": artifact_hint},
        )
        print(f"  [-1b] {memo} | instruction={decision['instruction']}")
        war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
        return {
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "self_correction_memo": memo,
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }

    if _followup_context_expected(user_input, recent_context, working_memory):
        memo = "The current turn looks like a lightweight follow-up that can continue directly in phase 3."
        decision = _make_auditor_decision("phase_3", memo=memo)
        print(f"  [-1b] {memo} | instruction={decision['instruction']}")
        followup_strategy = _followup_ack_strategy(user_input, recent_context)
        war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
        return {
            "response_strategy": followup_strategy,
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "self_correction_memo": memo,
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }

    if _is_assistant_question_request_turn(user_input):
        memo = "The user wants the assistant to ask one concrete question now."
        decision = _make_auditor_decision("phase_3", memo=memo)
        print(f"  [-1b] {memo} | instruction={decision['instruction']}")
        question_strategy = _ask_user_question_strategy(user_input, working_memory)
        war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
        return {
            "response_strategy": question_strategy,
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "self_correction_memo": memo,
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }

    if not has_analysis and reasoning_plan.get("preferred_path") == "internal_reasoning" and reasoning_budget > 0:
        memo = str(reasoning_plan.get("rationale") or "The current turn still needs one internal reasoning pass before delivery.").strip()
        decision = _make_auditor_decision("internal_reasoning", memo=memo)
        print(f"  [-1b] {memo} | instruction={decision['instruction']}")
        war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
        return {
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "self_correction_memo": memo,
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }

    if not has_analysis and reasoning_plan.get("preferred_path") == "direct_answer":
        memo = str(reasoning_plan.get("rationale") or "The current turn looks answerable without a tool-first path.").strip()
        decision = _make_auditor_decision("phase_3", memo=memo)
        response_strategy = {}
        if _is_initiative_request_turn(user_input):
            response_strategy = _initiative_request_strategy(user_input, working_memory)
        response_strategy, _, speaker_review = _prepare_phase3_delivery(
            user_input=user_input,
            recent_context=recent_context,
            working_memory=working_memory,
            reasoning_board=reasoning_board,
            analysis_data=analysis_data,
            response_strategy=response_strategy,
            search_results=state.get("search_results", ""),
            loop_count=loop_count,
        )
        if speaker_review.get("should_remand") and reasoning_budget > 0:
            decision = _make_auditor_decision(
                "internal_reasoning",
                memo="Phase 3 delivery review says the packet is still too weak, so one more internal loop is safer.",
            )
            response_strategy = {}
        print(f"  [-1b] {decision.get('memo', memo)} | instruction={decision['instruction']}")
        war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
        return {
            "response_strategy": response_strategy,
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "self_correction_memo": decision.get("memo", memo),
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "speaker_review": speaker_review,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }

    if has_analysis or reasoning_board.get("candidate_pairs") or reasoning_board.get("fact_cells"):
        reasoning_board = _audit_reasoning_board(reasoning_board, analysis_data)
        preferred_strategist = _preferred_decision_from_strategist(
            strategist_output,
            analysis_data,
            loop_count,
            reasoning_budget=reasoning_budget,
        )
        if preferred_strategist:
            print(f"  [-1b] strategist-plan decision: {preferred_strategist.get('memo', '')} | instruction={preferred_strategist.get('instruction', '')}")
            war_room = _war_room_after_judge(war_room, preferred_strategist, analysis_data, reasoning_board)
            response_strategy = strategist_output.get("response_strategy", {})
            if not isinstance(response_strategy, dict):
                response_strategy = {}
            if str(preferred_strategist.get("action") or "").strip() != "phase_3":
                response_strategy = {}
            if str(preferred_strategist.get("action") or "").strip() == "answer_not_ready":
                response_strategy = _answer_not_ready_strategy(user_input, war_room)
            return {
                "strategist_output": strategist_output,
                "response_strategy": response_strategy,
                "auditor_instruction": preferred_strategist.get("instruction", ""),
                "auditor_decision": preferred_strategist,
                "self_correction_memo": preferred_strategist.get("memo", ""),
                "reasoning_board": reasoning_board,
                "war_room": war_room,
                "reasoning_budget": reasoning_budget,
                "reasoning_plan": reasoning_plan,
            }
        preferred_verdict = _preferred_decision_from_verdict(
            reasoning_board,
            analysis_data,
            loop_count,
            user_input=user_input,
            working_memory=working_memory,
            reasoning_budget=reasoning_budget,
        )
        if preferred_verdict:
            print(f"  [-1b] verdict-board decision: {preferred_verdict.get('memo', '')} | instruction={preferred_verdict.get('instruction', '')}")
            war_room = _war_room_after_judge(war_room, preferred_verdict, analysis_data, reasoning_board)
            response_strategy = {}
            if str(preferred_verdict.get("action") or "").strip() == "answer_not_ready":
                response_strategy = _answer_not_ready_strategy(user_input, war_room)
            return {
                "strategist_output": strategist_output,
                "response_strategy": response_strategy,
                "auditor_instruction": preferred_verdict.get("instruction", ""),
                "auditor_decision": preferred_verdict,
                "self_correction_memo": preferred_verdict.get("memo", ""),
                "reasoning_board": reasoning_board,
                "war_room": war_room,
                "reasoning_budget": reasoning_budget,
                "reasoning_plan": reasoning_plan,
            }

    analysis_packet = _analysis_packet_for_prompt(analysis_data, include_thought=True)
    strategist_packet = _strategist_output_packet_for_prompt(strategist_output)
    working_memory_packet = _working_memory_packet_for_prompt(working_memory)
    reasoning_board_packet = _reasoning_board_packet_for_prompt(reasoning_board, approved_only=False)
    user_state = state.get("user_state", "")
    user_char = state.get("user_char", "")
    time_gap = state.get("time_gap", 0)
    tolerance = state.get("global_tolerance", 1.0)
    bio_status = state.get("biolink_status", "")

    sys_prompt = (
        "You are the ANIMA phase -1b auditor and judge.\n\n"
        "Read the current turn, recent context, working memory, analysis report, and the strategist's plan.\n"
        "Decide whether the case should go directly to phase 3, continue internal reasoning, call a tool, plan more, or answer_not_ready.\n"
        "When you reject or hold something, explain why in plain operational language.\n\n"
        f"[user_input]\n{user_input}\n\n"
        f"[recent_context]\n{recent_context}\n\n"
        f"[user_state]\n{user_state}\n\n"
        f"[user_char]\n{user_char}\n\n"
        f"[time_gap]\n{time_gap}\n\n"
        f"[global_tolerance]\n{tolerance}\n\n"
        f"[biolink_status]\n{bio_status}\n\n"
        f"[working_memory]\n{working_memory_packet}\n\n"
        f"[reasoning_budget]\n{reasoning_budget}\n\n"
        f"[reasoning_plan]\n{json.dumps(reasoning_plan, ensure_ascii=False)}\n\n"
        f"[reasoning_board]\n{reasoning_board_packet}\n\n"
        f"[analysis_report]\n{analysis_packet}\n\n"
        f"[analysis_exists]\n{has_analysis}\n\n"
        f"[strategist_output]\n{strategist_packet}\n\n"
        "Rules:\n"
        "1. instruction_to_0 must be an exact tool call when you choose call_tool.\n"
        "2. If analysis_exists is false, do not pretend investigation_status exists yet.\n"
        "3. Prefer current user_input as the main anchor; treat recent_context and working_memory as support, not replacement evidence.\n"
        "4. Phase 2 diagnoses the case; -1a owns the step-by-step action plan.\n"
        "5. If strategist_output.action_plan.required_tool is valid, review that plan first before improvising another tool path.\n"
        "6. COMPLETED may go to phase_3.\n"
        "7. reasoning_budget is a soft planning guide, not an absolute cutoff.\n"
        "8. EXPANSION_REQUIRED may still plan more or call a tool even when the soft budget is full, as long as the graph hard stop is still available.\n"
        "9. If the packet is too weak for safe delivery, prefer plan_more or answer_not_ready over bluffing.\n"
    )

    decision = None
    try:
        structured_llm = llm.with_structured_output(AuditorOutput)
        res = structured_llm.invoke([SystemMessage(content=sys_prompt)])
        memo = str(res.rejection_reason or "").strip()
        preferred = _preferred_decision_from_strategist(
            strategist_output,
            analysis_data,
            loop_count,
            reasoning_budget=reasoning_budget,
        )
        if preferred is None and has_analysis:
            preferred = _preferred_decision_from_analysis(
                analysis_data,
                loop_count,
                user_input=user_input,
                working_memory=working_memory,
                reasoning_budget=reasoning_budget,
            )
        if preferred:
            decision = preferred
        else:
            decision = _decision_from_instruction(
                str(res.instruction_to_0 or "").strip(),
                is_satisfied=bool(res.is_satisfied),
                memo=memo,
            )
        if decision is None:
            if artifact_hint:
                decision = _make_auditor_decision(
                    "call_tool",
                    memo=memo or "Artifact review request detected during fallback routing.",
                    tool_name="tool_read_artifact",
                    tool_args={"artifact_hint": artifact_hint},
                )
            elif _should_default_to_memory_search(user_input, analysis_data, working_memory):
                keyword = _normalize_search_keyword(user_input)
                decision = _make_auditor_decision(
                    "call_tool",
                    memo=memo or "Fallback routing selected memory search because the turn still looks retrieval-dependent.",
                    tool_name="tool_search_memory",
                    tool_args={"keyword": keyword or "recent context"},
                )
            else:
                decision = _make_auditor_decision(
                    "phase_3",
                    memo=memo or "Fallback routing selected direct delivery because no stronger tool path was available.",
                )
    except Exception as e:
        print(f"[Phase -1b] structured output exception: {e}")
        preferred = _preferred_decision_from_strategist(
            strategist_output,
            analysis_data,
            loop_count,
            reasoning_budget=reasoning_budget,
        )
        if preferred is None and has_analysis:
            preferred = _preferred_decision_from_analysis(
                analysis_data,
                loop_count,
                user_input=user_input,
                working_memory=working_memory,
                reasoning_budget=reasoning_budget,
            )
        if preferred:
            decision = preferred
        else:
            if artifact_hint:
                decision = _make_auditor_decision(
                    "call_tool",
                    memo="Structured output failed, so fallback routing selected artifact review.",
                    tool_name="tool_read_artifact",
                    tool_args={"artifact_hint": artifact_hint},
                )
            elif _should_default_to_memory_search(user_input, analysis_data, working_memory):
                decision = _make_auditor_decision(
                    "call_tool",
                    memo="Structured output failed, so fallback routing selected memory search.",
                    tool_name="tool_search_memory",
                    tool_args={"keyword": _normalize_search_keyword(user_input) or "recent context"},
                )
            else:
                decision = _make_auditor_decision(
                    "phase_3",
                    memo="Structured output failed, so fallback routing selected direct delivery.",
                )

    if not has_analysis and _decision_uses_unanchored_topic(decision, user_input, analysis_data):
        if _is_directive_or_correction_turn(user_input) or _is_initiative_request_turn(user_input):
            decision = _make_auditor_decision(
                "phase_3",
                memo="An unrelated stale topic was blocked, so the turn is being re-anchored to the current user request for direct delivery.",
            )
        elif _is_artifact_review_turn(user_input):
            decision = _make_auditor_decision(
                "call_tool",
                memo="An unrelated stale topic was blocked, so the turn is being re-anchored to artifact review.",
                tool_name="tool_read_artifact",
                tool_args={"artifact_hint": _extract_artifact_hint(user_input)},
            )
        elif _should_default_to_memory_search(user_input, analysis_data, working_memory):
            decision = _make_auditor_decision(
                "call_tool",
                memo="An unrelated stale topic was blocked, so the turn is being re-anchored to memory search.",
                tool_name="tool_search_memory",
                tool_args={"keyword": _normalize_search_keyword(user_input) or "recent context"},
            )
        else:
            decision = _make_auditor_decision(
                "phase_3",
                memo="An unrelated stale topic was blocked, so the turn is being re-anchored to the current user request.",
            )

    reasoning_board = _audit_reasoning_board(reasoning_board, analysis_data)
    if reasoning_board.get("candidate_pairs"):
        approved_pairs = len(reasoning_board.get("final_pair_ids", []))
        print(f"  [-1b] approved pairs={approved_pairs} / {len(reasoning_board.get('candidate_pairs', []))}")

    war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
    response_strategy = strategist_output.get("response_strategy", {}) if str(decision.get("action") or "").strip() == "phase_3" else {}
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    if str(decision.get("action") or "").strip() == "answer_not_ready":
        response_strategy = _answer_not_ready_strategy(user_input, war_room)
    print(f"  [-1b] final decision: {decision.get('memo', '')} | instruction={decision.get('instruction', '')}")
    return {
        "strategist_output": strategist_output,
        "response_strategy": response_strategy,
        "auditor_instruction": decision.get("instruction", ""),
        "auditor_decision": decision,
        "self_correction_memo": decision.get("memo", ""),
        "reasoning_board": reasoning_board,
        "war_room": war_room,
        "reasoning_budget": reasoning_budget,
        "reasoning_plan": reasoning_plan,
    }


def phase_0_supervisor(state: AnimaState):
    print("[Phase 0] Executing auditor instruction...")
    llm_with_tools = llm_supervisor.bind_tools(available_tools)
    auditor_decision = state.get("auditor_decision", {})
    auditor_instruction = str(state.get("auditor_instruction", "") or "").strip()

    if isinstance(auditor_decision, dict):
        action = str(auditor_decision.get("action") or "").strip()
        tool_name = str(auditor_decision.get("tool_name") or "").strip()
        tool_args = auditor_decision.get("tool_args", {}) if isinstance(auditor_decision.get("tool_args"), dict) else {}
        if action == "call_tool" and tool_name:
            print(f"  [Phase 0] direct structured tool execution: {tool_name}")
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[{"name": tool_name, "args": tool_args, "id": f"auditor_{tool_name}"}],
                    )
                ]
            }
        if action == "phase_3":
            return {"messages": [AIMessage(content="", tool_calls=[{"name": "tool_pass_to_phase_3", "args": {}, "id": "auditor_pass"}])]} 
        if action == "phase_119":
            return {"messages": [AIMessage(content="", tool_calls=[{"name": "tool_call_119_rescue", "args": {}, "id": "auditor_119"}])]} 

    direct_message = _build_direct_tool_message(auditor_instruction)
    if direct_message is not None:
        print(f"  [Phase 0] direct tool execution from exact instruction: {direct_message.tool_calls[0]['name']}")
        return {"messages": [direct_message]}

    sys_prompt = (
        "You are a tool-call extractor.\n"
        "Convert the auditor instruction below into an exact tool call and do not reply with normal text.\n\n"
        f"[auditor_instruction]\n{auditor_instruction}\n"
    )

    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content="Return only a tool call."),
    ]

    for attempt in range(3):
        response = llm_with_tools.invoke(messages)
        if response.tool_calls:
            print(f"  [Phase 0] 파싱된 도구 호출: {response.tool_calls[0]['name']}")
            return {"messages": [response]}

        print(f"  [Phase 0] 도구 호출 파싱 실패, 재시도합니다. ({attempt + 1}/3)")
        messages.append(response)
        messages.append(HumanMessage(content="Please convert the supervisor instruction into an exact tool call."))

    print("[Phase 0] fallback으로 phase_3 패스를 강제합니다.")
    forced_msg = AIMessage(content="", tool_calls=[{"name": "tool_pass_to_phase_3", "args": {}, "id": "forced_pass"}])
    return {"messages": [forced_msg]}

def phase_1_searcher(state: AnimaState):
    print("[Phase 1] Executing tool calls...")

    last_message = state["messages"][-1]
    used_sources = state.get("used_sources", [])
    search_results_text = ""
    tool_messages = []
    executed_actions = state.get("executed_actions", [])

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})

            keyword = (
                tool_args.get("keyword")
                or tool_args.get("target_date")
                or tool_args.get("target_id")
                or tool_args.get("artifact_hint")
                or tool_args.get("keyword_z")
                or tool_args.get("dummy_keyword")
                or ""
            )
            if tool_name == "tool_scan_db_schema" and not keyword:
                keyword = "전체스키마"
            if isinstance(keyword, list):
                keyword = ", ".join(str(k) for k in keyword)
            elif not isinstance(keyword, str):
                keyword = str(keyword)

            action_signature = _stable_action_signature(tool_name, tool_args)
            print(f"  [Phase 1] tool={tool_name} | target={keyword}")

            if tool_name in {"tool_pass_to_phase_3", "tool_call_119_rescue"}:
                result_str = "Control tool acknowledged."
                exact_dates = []
            elif not keyword.strip():
                result_str = "[system warning] Empty search target detected."
                exact_dates = []
            elif action_signature in executed_actions:
                tactic_note = toolbox.search_tactics(keyword)
                result_str = (
                    f"[duplicate warning] '{keyword}' was already searched.\n"
                    f"Use this tactic note before retrying.\n\n{tactic_note}"
                )
                exact_dates = []
            else:
                executed_actions.append(action_signature)
                try:
                    if tool_name == "tool_search_memory":
                        result = toolbox.search_memory(tool_args.get("keyword", ""))
                        result_str, exact_dates = result if isinstance(result, tuple) and len(result) == 2 else (str(result), [])
                    elif tool_name == "tool_read_full_diary":
                        result = toolbox.read_full_source("일기장", tool_args.get("target_date", ""))
                        result_str, exact_dates = result if isinstance(result, tuple) and len(result) == 2 else (str(result), [])
                    elif tool_name == "tool_read_artifact":
                        result = toolbox.read_artifact(tool_args.get("artifact_hint", ""))
                        result_str, exact_dates = result if isinstance(result, tuple) and len(result) == 2 else (str(result), [])
                    elif tool_name == "tool_scan_db_schema":
                        result_str = toolbox.scan_db_schema()[0]
                        exact_dates = []
                    elif tool_name == "tool_scroll_chat_log":
                        result = toolbox.scroll_chat_log(
                            tool_args.get("target_id", ""),
                            tool_args.get("direction", "both"),
                            tool_args.get("limit", 15),
                        )
                        result_str, exact_dates = result if isinstance(result, tuple) and len(result) == 2 else (str(result), [])
                    elif tool_name == "tool_scan_trend_u_function":
                        result_str = toolbox.scan_trend_u_function(
                            tool_args.get("keyword", ""),
                            track_type=tool_args.get("track_type", "Episode"),
                        )
                        exact_dates = []
                    elif tool_name == "tool_scan_trend_u_function_3d":
                        result_str = toolbox.scan_trend_u_function(
                            tool_args.get("keyword_z", ""),
                            tool_args.get("keyword_anti_z", ""),
                            tool_args.get("keyword_y", ""),
                            track_type=tool_args.get("track_type", "PastRecord"),
                        )
                        exact_dates = []
                    else:
                        result_str, exact_dates = (f"Unknown tool: {tool_name}", [])

                    if exact_dates and tool_name != "tool_read_artifact":
                        extracted_topology = extract_local_topology(exact_dates)
                        result_str = f"[local_topology]\n{extracted_topology}\n\n[source_data]\n{result_str}"
                except Exception as e:
                    print(f"  [Phase 1] tool error: {e}")
                    result_str = f"[tool error] Search failed for target '{keyword}'."
                    exact_dates = []

            for source_id in exact_dates:
                if source_id not in used_sources:
                    used_sources.append(source_id)

            search_results_text += f"[{tool_name} result]\n{result_str}\n\n"
            tool_messages.append(ToolMessage(content=result_str, tool_call_id=tool_call["id"]))

    return {
        "search_results": search_results_text,
        "used_sources": used_sources,
        "executed_actions": executed_actions,
        "messages": tool_messages,
    }

def _fallback_current_turn_raw_read_report(user_input: str):
    user_text = str(user_input or "").strip()
    observed = user_text if user_text else "No current-turn content was available."
    return {
        "read_mode": "current_turn_only",
        "reviewed_all_input": True,
        "source_summary": "Phase 2a reviewed only the current user turn because no external raw source was available.",
        "items": [
            {
                "source_id": "current_user_turn",
                "source_type": "current_turn",
                "excerpt": observed[:240],
                "observed_fact": observed,
            }
        ] if user_text else [],
        "coverage_notes": "Only the current turn was directly reviewed in this fallback path.",
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
    base["source_summary"] = "Phase 2a reviewed the current turn and attached a small recent-context hint packet."
    base["coverage_notes"] = f"Current turn plus {len(recent_subset)} recent-context hint item(s) were packaged for downstream review."
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
        return _fallback_current_turn_raw_read_report("")

    return {
        "read_mode": "recent_dialogue_review",
        "reviewed_all_input": True,
        "source_summary": "Phase 2a reviewed recent raw dialogue turns from recent_context.",
        "items": items,
        "coverage_notes": f"Recent raw turns reviewed: {len(items)} item(s). Use this packet to ground dialogue review before broader interpretation.",
    }


def phase_2a_reader(state: AnimaState):
    print("[Phase 2a] 원본 소스를 처음부터 끝까지 검토 중...")

    search_data = str(state.get("search_results", "") or "")
    if not search_data.strip():
        if _is_recent_dialogue_review_turn(state.get("user_input", ""), state.get("recent_context", "")):
            raw_read_report = _fallback_recent_dialogue_raw_read_report(state.get("recent_context", ""))
            print(f"  [Phase 2a] recent_dialogue_review | 최근 raw turns 수={len(raw_read_report.get('items', []))}")
            return {"raw_read_report": raw_read_report}
        raw_read_report = _fallback_current_turn_with_recent_context_report(
            state.get("user_input", ""),
            state.get("recent_context", ""),
        )
        recent_hint_count = max(len(raw_read_report.get("items", [])) - 1, 0)
        print(f"  [Phase 2a] current_turn_only | 최근 맥락 힌트 수={recent_hint_count}")
        return {"raw_read_report": raw_read_report}

    sys_prompt = (
        "You are the ANIMA phase 2a raw reader.\n\n"
        "Read the provided raw material from start to finish and produce a raw-read report.\n"
        "Do not argue yet. Do not deliver final judgments yet. Just review what was actually read and package it cleanly.\n\n"
        f"[user_input]\n{state.get('user_input', '')}\n\n"
        f"[recent_context_excerpt]\n{_phase3_recent_context_excerpt(state.get('recent_context', ''), max_chars=800) or 'N/A'}\n\n"
        f"[raw_search_results]\n{search_data}\n\n"
        "Rules:\n"
        "1. reviewed_all_input should reflect whether the provided raw material was actually reviewed end-to-end.\n"
        "2. items should capture source-level observations with short excerpts where possible.\n"
        "3. observed_fact should stay factual and local to the reviewed source.\n"
        "4. excerpt should be short and directly traceable to the source.\n"
        "5. source_summary should summarize what was read, not what you infer.\n"
        "6. coverage_notes should explain what was fully reviewed and what still remains unclear.\n"
        "7. Do not invent tool results or source coverage that never happened.\n"
    )

    structured_llm = llm_supervisor.with_structured_output(RawReadReport)
    try:
        response_obj = structured_llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content="Please read the supplied raw material and build a raw-read report."),
        ])
        raw_read_report = response_obj.model_dump()
        item_count = len(raw_read_report.get("items", []))
        print(f"  [Phase 2a] 읽기 모드={raw_read_report.get('read_mode', '')} | 항목 수={item_count}")
    except Exception as e:
        print(f"[Phase 2a] structured output 예외: {e}")
        raw_read_report = {
            "read_mode": "full_raw_review",
            "reviewed_all_input": False,
            "source_summary": "Phase 2a fallback path was used after a structured output failure.",
            "items": [],
            "coverage_notes": "The raw material could not be packaged cleanly by phase 2a.",
        }

    return {"raw_read_report": raw_read_report}


def phase_2_analyzer(state: AnimaState):
    print("[Phase 2b] phase_2a 원문 검토 결과를 바탕으로 구조화 증거철을 작성 중...")

    current_loop = state.get("loop_count", 0)
    auditor_memo = state.get("self_correction_memo", "")
    working_memory_packet = _working_memory_packet_for_prompt(state.get("working_memory", {}))
    raw_read_report = state.get("raw_read_report", {})
    raw_read_packet = _raw_read_report_packet_for_prompt(raw_read_report)
    source_relay_packet = _build_source_relay_packet(raw_read_report)
    source_relay_prompt = _source_relay_packet_for_prompt(source_relay_packet)
    read_mode = str(raw_read_report.get("read_mode") or "").strip()
    analysis_mode = (
        "recent_dialogue_review"
        if read_mode == "recent_dialogue_review"
        else "internal_reasoning_only"
        if read_mode == "current_turn_only"
        else "tool_grounded"
    )

    sys_prompt = (
        "당신은 ANIMA의 2b 검사이자 근거 감사관이다.\n\n"
        "phase 2a 원문 검토 보고를 읽고, 근거에 닻을 내린 분석 보고를 작성하라.\n"
        "phase 2a가 실제로 검토한 내용만으로 evidences, analytical_thought, situational_brief를 만들어라.\n"
        "당신의 임무는 진단뿐이다. 다음 도구를 계획하지 말고, 인식적 결핍을 분명하게 진단하라.\n"
        "모든 자유서술 필드는 한국어로 작성하라.\n\n"
        f"[analysis_mode]\n{analysis_mode}\n\n"
        f"[user_input]\n{state['user_input']}\n\n"
        f"[raw_read_report]\n{raw_read_packet}\n\n"
        f"[auditor_memo]\n{auditor_memo if auditor_memo else 'N/A'}\n\n"
        f"[working_memory]\n{working_memory_packet}\n\n"
        f"[source_relay_packet]\n{source_relay_prompt}\n\n"
        "[phase_2b_source_contract]\n"
        "- phase_2a가 넘긴 모든 source packet에 대해 source_judgments를 작성하라.\n"
        "- 각 source_judgment에는 source_status, accepted_facts, objection_reason, missing_info, search_needed가 포함되어야 한다.\n"
        "- must_forward_facts는 반드시 릴레이되어야 하는 핵심 사실로 취급하라. 존재한다면 넓은 비판보다 먼저 accepted_facts와 evidences에 반영하라.\n"
        "- situational_brief는 fact-first로 작성하라. 사용자 태도 언급은 source facts와 source judgments 뒤에만 붙여라.\n\n"
        "규칙:\n"
        "1. evidences는 구체적이고 source-grounded 해야 한다.\n"
        "2. analytical_thought는 비판적이어도 되지만, 반드시 evidences에 묶여 있어야 한다.\n"
        "3. situational_brief는 하위 노드들이 바로 활용할 수 있는 사건 요약이어야 한다.\n"
        "4. 현재 근거로 신뢰 가능한 답이 가능할 때만 COMPLETED를 사용하라.\n"
        "5. 핵심 근거가 비면 INCOMPLETE를 사용하라.\n"
        "6. 수색이나 재검토를 한 번 더 하면 크게 나아질 때만 EXPANSION_REQUIRED를 사용하라.\n"
        "7. 다음 도구를 계획하지 말고, 어떤 인식적 결핍이 남았는지만 적어라.\n"
        "8. phase_2a가 읽지 않은 raw fact를 환각하지 말라.\n"
        "9. internal_reasoning_only 모드에서는 정말 필요한 경우가 아니면 memory search를 강요하지 말라.\n"
        "10. recent_dialogue_review 모드에서는 raw_read_report.items에 있는 실제 최근 턴에 근거하라.\n"
    )

    structured_llm = llm.with_structured_output(AnalysisReport)
    try:
        response_obj = structured_llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=state["user_input"]),
        ])
        analysis_dict = _normalize_analysis_with_source_relay(response_obj.model_dump(), source_relay_packet)
        analysis_dict = _enforce_recent_dialogue_review_analysis(analysis_dict, raw_read_report)
        reasoning_board = _build_reasoning_board_from_analysis(state, analysis_dict)
        status = analysis_dict.get("investigation_status", "UNKNOWN")
        brief = analysis_dict.get("situational_brief", "")
        print(f"  [Phase 2b] 상태={status} | 요약={brief[:120]}")
        fake_ai_message = AIMessage(content=json.dumps(analysis_dict, ensure_ascii=False))
    except Exception as e:
        print(f"[Phase 2b] 구조화 출력 예외: {e}")
        analysis_dict = {
            "evidences": [],
            "source_judgments": [],
            "analytical_thought": "구조화 출력이 실패하여 2차 fallback 분석 패킷을 사용했습니다.",
            "situational_brief": "구조화 출력 실패로 인해 2차 fallback 경로가 사용되었습니다.",
            "investigation_status": "INCOMPLETE",
        }
        reasoning_board = _build_reasoning_board_from_analysis(state, analysis_dict)
        fake_ai_message = AIMessage(content="phase_2_fallback_seed")

    war_room = _war_room_from_critic(state, analysis_dict, raw_read_report)
    return {
        "analysis_report": analysis_dict,
        "reasoning_board": reasoning_board,
        "war_room": war_room,
        "loop_count": current_loop + 1,
        "messages": [fake_ai_message],
    }


def phase_119_rescue(state: AnimaState):
    print("[Phase 119] 긴급 구조 루프를 호출합니다.")

    sys_prompt = (
        "You are the ANIMA phase 119 rescue guard.\n\n"
        "The system is stuck or over-iterating. Produce a compact rescue memo that helps the supervisor hand control back safely.\n"
        "State the most important limit, the safest next move, and whether phase 3 should answer with caution.\n\n"
        f"[user_input]\n{state['user_input']}\n\n"
        f"[analysis_report]\n{_analysis_packet_for_prompt(state.get('analysis_report', {}), include_thought=True)}\n\n"
        f"[reasoning_board]\n{_reasoning_board_packet_for_prompt(state.get('reasoning_board', {}), approved_only=False)}\n\n"
    )

    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=state["user_input"]),
    ])

    return {
        "supervisor_instructions": f"[119 rescue] {response.content}",
        "messages": [response],
    }


def phase_3_validator(state: AnimaState):
    response_strategy = state.get("response_strategy", {})
    reasoning_board = state.get("reasoning_board", {})
    loop_count = state.get("loop_count", 0)
    phase3_recent_context = _phase3_recent_context_excerpt(state.get("recent_context", ""))
    phase3_reference_policy = _phase3_reference_policy(state.get("search_results", ""), loop_count)
    judge_speaker_packet = _build_judge_speaker_packet(
        reasoning_board=reasoning_board,
        response_strategy=response_strategy,
        phase3_reference_policy=phase3_reference_policy,
    )
    judge_speaker_prompt = _judge_speaker_packet_for_prompt(judge_speaker_packet)
    grounded_mode = judge_speaker_packet.get("speaker_mode") == "grounded_mode"

    if grounded_mode:
        print("[Phase 3] 판사 공개본을 바탕으로 최종 답변 생성 중...")
    else:
        print("[Phase 3] 현재 사용자 입력과 판사 공개본을 바탕으로 직접 대화 응답 생성 중...")

    supervisor_memo = state.get("supervisor_instructions", "")
    if "[119 rescue]" not in supervisor_memo:
        supervisor_memo = ""

    sys_prompt = (
        "당신은 ANIMA의 3차 화자다.\n\n"
        "판사가 승인한 공개 패킷을 사용자-facing 최종 답변으로 바꿔라.\n"
        "내부 토론을 다시 열지 말고, 숨겨진 워크플로, 판사 패킷, 내부 역할명을 노출하지 말라.\n\n"
        f"[response_mode]\n{'grounded_mode' if grounded_mode else 'direct_dialogue_mode'}\n\n"
        f"[judge_speaker_packet]\n{judge_speaker_prompt}\n\n"
        f"[recent_context_excerpt]\n{phase3_recent_context if phase3_recent_context else 'N/A'}\n\n"
        + ((f"[supervisor_memo]\n{supervisor_memo}\n\n") if supervisor_memo else "")
        + "규칙:\n"
        "1. judge_speaker_packet을 주된 송달 패킷으로 취급하라.\n"
        "2. user_input과 recent_context_excerpt는 직전 흐름 유지를 위한 보조 맥락으로만 써라.\n"
        "3. judge_speaker_packet과 recent_context_excerpt가 충돌하면 judge_speaker_packet을 따른다.\n"
        "4. approved_fact_cells와 approved_claims는 전달 보조 자료일 뿐, 새 추론 놀이터가 아니다.\n"
        "5. must_avoid_claims를 엄격히 지켜라.\n"
        "6. final_answer_brief가 있으면 가장 강한 답변 씨앗으로 사용하라.\n"
        "7. reply_mode가 continue_previous_offer면 대화를 처음부터 다시 시작하지 말고 직전 흐름을 이어라.\n"
        "8. reply_mode가 ask_user_question_now면 모호한 메타 질문 대신 구체적인 질문 한 개를 던져라.\n"
        "9. answer_now가 false이고 reference_mode가 hidden_large_raw면, 허세를 부리지 말고 정확한 후속 질문을 택하라.\n"
        "10. 근거가 약할수록 uncertainty_policy를 따르라.\n"
        "11. 최종 답변은 사용자가 다른 언어를 명시적으로 원하지 않는 한 자연스러운 한국어여야 한다.\n"
    )

    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=state["user_input"]),
    ])

    raw_text = response.content if isinstance(response.content, str) else str(response.content)
    normalized_text = _normalize_user_facing_text(raw_text)
    final_message = AIMessage(content=normalized_text if normalized_text else raw_text)

    print("[Phase 3] 최종 응답 생성 완료.")
    return {"messages": [final_message]}


def _source_relay_packet_for_prompt(source_relay_packet: dict):
    if not isinstance(source_relay_packet, dict) or not source_relay_packet:
        return "사용 가능한 소스 릴레이 패킷이 없습니다."
    try:
        return json.dumps(source_relay_packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(source_relay_packet)


def _build_source_relay_packet(raw_read_report: dict):
    if not isinstance(raw_read_report, dict) or not raw_read_report:
        return {
            "read_mode": "empty",
            "reviewed_all_input": False,
            "global_source_summary": "",
            "global_coverage_notes": "",
            "source_packets": [],
        }

    read_mode = str(raw_read_report.get("read_mode") or "").strip() or "empty"
    reviewed_all_input = bool(raw_read_report.get("reviewed_all_input", False))
    global_source_summary = str(raw_read_report.get("source_summary") or "").strip()
    global_coverage_notes = str(raw_read_report.get("coverage_notes") or "").strip()
    grouped = {}

    for item in raw_read_report.get("items", []):
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id") or "").strip() or "unknown_source"
        source_type = str(item.get("source_type") or "").strip() or "unknown"
        key = (source_id, source_type)
        packet = grouped.setdefault(key, {
            "source_id": source_id,
            "source_type": source_type,
            "source_summary": "",
            "coverage_notes": "",
            "must_forward_facts": [],
            "quoted_excerpts": [],
            "coverage_complete": reviewed_all_input,
        })
        observed_fact = str(item.get("observed_fact") or "").strip()
        excerpt = str(item.get("excerpt") or "").strip()
        if observed_fact and observed_fact not in packet["must_forward_facts"]:
            packet["must_forward_facts"].append(observed_fact)
        if excerpt and excerpt not in packet["quoted_excerpts"]:
            packet["quoted_excerpts"].append(excerpt)

    source_packets = []
    if grouped:
        multi_source = len(grouped) > 1
        for (_, _), packet in grouped.items():
            source_id = packet["source_id"]
            source_type = packet["source_type"]
            packet["source_summary"] = (
                f"phase_2a가 `{source_id}`({source_type}) 원문을 검토했습니다."
                if multi_source else
                (global_source_summary or f"phase_2a가 `{source_id}`({source_type}) 원문을 검토했습니다.")
            )
            packet["coverage_notes"] = global_coverage_notes or "phase_2a가 이 소스에 대해 원문 검토 패스를 마쳤습니다."
            packet["must_forward_facts"] = packet["must_forward_facts"][:6]
            packet["quoted_excerpts"] = packet["quoted_excerpts"][:3]
            source_packets.append(packet)

    if not source_packets and read_mode == "current_turn_only":
        source_packets.append({
            "source_id": "current_user_turn",
            "source_type": "current_turn",
            "source_summary": global_source_summary or "현재 사용자 턴만 이번 턴에서 사용 가능한 유일한 원문으로 검토되었습니다.",
            "coverage_notes": global_coverage_notes or "이번 턴에는 외부 원문 소스가 없어 현재 턴만 직접 검토했습니다.",
            "must_forward_facts": [],
            "quoted_excerpts": [],
            "coverage_complete": reviewed_all_input,
        })

    return {
        "read_mode": read_mode,
        "reviewed_all_input": reviewed_all_input,
        "global_source_summary": global_source_summary,
        "global_coverage_notes": global_coverage_notes,
        "source_packets": source_packets,
    }


def _fallback_current_turn_raw_read_report(user_input: str):
    user_text = str(user_input or "").strip()
    observed = user_text if user_text else "현재 턴 원문이 비어 있습니다."
    return {
        "read_mode": "current_turn_only",
        "reviewed_all_input": True,
        "source_summary": "외부 원문이 없어 현재 사용자 턴만 원문으로 검토했습니다.",
        "items": [
            {
                "source_id": "current_user_turn",
                "source_type": "current_turn",
                "excerpt": observed[:240],
                "observed_fact": observed,
            }
        ] if user_text else [],
        "coverage_notes": "이 fallback 경로에서는 현재 턴만 직접 검토했습니다.",
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
    base["source_summary"] = "현재 턴을 검토하고, 최근 대화 힌트를 소량 함께 첨부했습니다."
    base["coverage_notes"] = f"현재 턴과 최근 대화 힌트 {len(recent_subset)}개를 downstream 검토용으로 묶었습니다."
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
        return _fallback_current_turn_raw_read_report("")

    return {
        "read_mode": "recent_dialogue_review",
        "reviewed_all_input": True,
        "source_summary": "recent_context에 들어 있는 최근 raw 대화 턴들을 원문처럼 다시 검토했습니다.",
        "items": items,
        "coverage_notes": f"최근 raw 대화 턴 {len(items)}개를 검토했습니다. 더 넓은 해석보다 먼저 이 패킷을 근거로 대화 검토를 진행하세요.",
    }


def phase_2a_reader(state: AnimaState):
    print("[Phase 2a] 원본 소스를 처음부터 끝까지 검토 중...")

    search_data = str(state.get("search_results", "") or "")
    if not search_data.strip():
        if _is_recent_dialogue_review_turn(state.get("user_input", ""), state.get("recent_context", "")):
            raw_read_report = _fallback_recent_dialogue_raw_read_report(state.get("recent_context", ""))
            print(f"  [Phase 2a] recent_dialogue_review | 최근 raw turns 수={len(raw_read_report.get('items', []))}")
            return {"raw_read_report": raw_read_report}
        raw_read_report = _fallback_current_turn_with_recent_context_report(
            state.get("user_input", ""),
            state.get("recent_context", ""),
        )
        recent_hint_count = max(len(raw_read_report.get("items", [])) - 1, 0)
        print(f"  [Phase 2a] current_turn_only | 최근 대화 힌트 수={recent_hint_count}")
        return {"raw_read_report": raw_read_report}

    sys_prompt = (
        "당신은 ANIMA의 phase 2a 원문 검토관입니다.\n\n"
        "제공된 원문을 처음부터 끝까지 읽고 raw-read report를 작성하라.\n"
        "아직 논쟁하지 말고, 아직 최종 판정도 내리지 마라. 실제로 무엇을 읽었는지와 어떻게 패키징했는지만 정리하라.\n"
        "모든 자유서술 필드는 한국어로 작성하라.\n\n"
        f"[user_input]\n{state.get('user_input', '')}\n\n"
        f"[recent_context_excerpt]\n{_phase3_recent_context_excerpt(state.get('recent_context', ''), max_chars=800) or 'N/A'}\n\n"
        f"[raw_search_results]\n{search_data}\n\n"
        "규칙:\n"
        "1. reviewed_all_input는 제공된 원문을 실제로 끝까지 검토했는지 반영해야 한다.\n"
        "2. items는 가능한 한 source 단위 관찰과 짧은 발췌를 담아야 한다.\n"
        "3. observed_fact는 검토한 source에 국한된 사실이어야 한다.\n"
        "4. excerpt는 짧고 source에 직접 추적 가능해야 한다.\n"
        "5. source_summary는 읽은 내용을 요약해야 하며, 추론을 적지 마라.\n"
        "6. coverage_notes는 무엇을 충분히 읽었고 무엇이 아직 불명확한지 설명해야 한다.\n"
        "7. 실제로 없던 tool 결과나 source coverage를 꾸며내지 마라.\n"
    )

    structured_llm = llm_supervisor.with_structured_output(RawReadReport)
    try:
        response_obj = structured_llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content="제공된 원문을 읽고 raw-read report를 작성하라."),
        ])
        raw_read_report = response_obj.model_dump()
        item_count = len(raw_read_report.get("items", []))
        print(f"  [Phase 2a] 읽기 모드={raw_read_report.get('read_mode', '')} | 항목 수={item_count}")
    except Exception as e:
        print(f"[Phase 2a] 구조화 출력 예외: {e}")
        raw_read_report = {
            "read_mode": "full_raw_review",
            "reviewed_all_input": False,
            "source_summary": "구조화 출력 실패로 phase_2a fallback 경로가 사용되었습니다.",
            "items": [],
            "coverage_notes": "phase_2a가 원문을 깔끔하게 패키징하지 못했습니다.",
        }

    return {"raw_read_report": raw_read_report}


def phase_2_analyzer(state: AnimaState):
    print("[Phase 2b] phase_2a 원문 검토 결과를 바탕으로 구조화 증거철을 작성 중...")

    current_loop = state.get("loop_count", 0)
    auditor_memo = state.get("self_correction_memo", "")
    working_memory_packet = _working_memory_packet_for_prompt(state.get("working_memory", {}))
    raw_read_report = state.get("raw_read_report", {})
    raw_read_packet = _raw_read_report_packet_for_prompt(raw_read_report)
    source_relay_packet = _build_source_relay_packet(raw_read_report)
    source_relay_prompt = _source_relay_packet_for_prompt(source_relay_packet)
    read_mode = str(raw_read_report.get("read_mode") or "").strip()
    analysis_mode = (
        "recent_dialogue_review"
        if read_mode == "recent_dialogue_review"
        else "internal_reasoning_only"
        if read_mode == "current_turn_only"
        else "tool_grounded"
    )

    sys_prompt = (
        "당신은 ANIMA의 2b 검사이자 사실 감사관입니다.\n\n"
        "phase 2a 원문 검토 보고를 읽고, 그 근거 위에서만 분석 보고서를 작성하라.\n"
        "phase 2a가 실제로 검토한 내용만으로 evidences, analytical_thought, situational_brief를 만들어라.\n"
        "당신의 임무는 진단이지 다음 도구 계획이 아니다. 인식적 결핍이 무엇인지 분명하게 적어라.\n"
        "모든 자유서술 필드는 한국어로 작성하라.\n\n"
        f"[analysis_mode]\n{analysis_mode}\n\n"
        f"[user_input]\n{state['user_input']}\n\n"
        f"[raw_read_report]\n{raw_read_packet}\n\n"
        f"[auditor_memo]\n{auditor_memo if auditor_memo else 'N/A'}\n\n"
        f"[working_memory]\n{working_memory_packet}\n\n"
        f"[source_relay_packet]\n{source_relay_prompt}\n\n"
        "[phase_2b_source_contract]\n"
        "- phase_2a가 넘긴 모든 source packet에 대해 source_judgments를 작성하라.\n"
        "- 각 source_judgment에는 source_status, accepted_facts, objection_reason, missing_info, search_needed가 들어가야 한다.\n"
        "- must_forward_facts는 반드시 릴레이되어야 하는 직접 관찰 사실이다. 존재한다면 비판보다 먼저 accepted_facts와 evidences에 반영하라.\n"
        "- situational_brief는 fact-first로 작성하라. 사용자 태도 평가는 source facts와 source judgments 이후에만 덧붙여라.\n\n"
        "규칙:\n"
        "1. evidences는 구체적이고 source-grounded여야 한다.\n"
        "2. analytical_thought는 비판적이어도 되지만 반드시 evidences에 묶여 있어야 한다.\n"
        "3. situational_brief는 상위 노드들이 바로 사용할 수 있는 사건 요약이어야 한다.\n"
        "4. 현재 근거로 답변이 가능할 때만 COMPLETED를 사용하라.\n"
        "5. 직접 근거가 비면 INCOMPLETE를 사용하라.\n"
        "6. 더 읽거나 확인해야 종결할 수 있을 때만 EXPANSION_REQUIRED를 사용하라.\n"
        "7. 다음 도구를 계획하지 말고, 어떤 인식적 결핍이 있는지만 적어라.\n"
        "8. phase_2a가 읽지 않은 raw fact를 새로 만들지 마라.\n"
        "9. internal_reasoning_only 모드에서 바로 답할 수 있다면 memory search를 강요하지 마라.\n"
        "10. recent_dialogue_review 모드에서는 raw_read_report.items에 담긴 실제 최근 대화 턴을 직접 근거로 사용하라.\n"
    )

    structured_llm = llm.with_structured_output(AnalysisReport)
    try:
        response_obj = structured_llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=state["user_input"]),
        ])
        analysis_dict = _normalize_analysis_with_source_relay(response_obj.model_dump(), source_relay_packet)
        analysis_dict = _enforce_recent_dialogue_review_analysis(analysis_dict, raw_read_report)
        reasoning_board = _build_reasoning_board_from_analysis(state, analysis_dict)
        status = analysis_dict.get("investigation_status", "UNKNOWN")
        brief = analysis_dict.get("situational_brief", "")
        print(f"  [Phase 2b] 상태={status} | 요약={brief[:120]}")
        fake_ai_message = AIMessage(content=json.dumps(analysis_dict, ensure_ascii=False))
    except Exception as e:
        print(f"[Phase 2b] 구조화 출력 예외: {e}")
        analysis_dict = {
            "evidences": [],
            "source_judgments": [],
            "analytical_thought": "구조화 출력이 실패하여 2차 fallback 분석 문구를 사용합니다.",
            "situational_brief": "구조화 출력 실패로 인해 2차 fallback 경로가 사용되었습니다.",
            "investigation_status": "INCOMPLETE",
        }
        reasoning_board = _build_reasoning_board_from_analysis(state, analysis_dict)
        fake_ai_message = AIMessage(content="phase_2_fallback_seed")

    war_room = _war_room_from_critic(state, analysis_dict, raw_read_report)
    return {
        "analysis_report": analysis_dict,
        "reasoning_board": reasoning_board,
        "war_room": war_room,
        "loop_count": current_loop + 1,
        "messages": [fake_ai_message],
    }


def phase_119_rescue(state: AnimaState):
    print("[Phase 119] 긴급 구조 루프를 실행합니다.")

    sys_prompt = (
        "당신은 ANIMA의 119 구조 가드입니다.\n\n"
        "시스템이 루프에 갇히거나 과도하게 반복되고 있습니다. 상위 제어권이 안전하게 돌아갈 수 있도록 짧은 구조 메모를 작성하라.\n"
        "가장 중요한 한계, 가장 안전한 다음 행동, 그리고 3차가 조심스럽게 답해야 하는지를 적어라.\n"
        "모든 자유서술 필드는 한국어로 작성하라.\n\n"
        f"[user_input]\n{state['user_input']}\n\n"
        f"[analysis_report]\n{_analysis_packet_for_prompt(state.get('analysis_report', {}), include_thought=True)}\n\n"
        f"[reasoning_board]\n{_reasoning_board_packet_for_prompt(state.get('reasoning_board', {}), approved_only=False)}\n\n"
    )

    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=state["user_input"]),
    ])

    return {
        "supervisor_instructions": f"[119 rescue] {response.content}",
        "messages": [response],
    }


def phase_3_validator(state: AnimaState):
    response_strategy = state.get("response_strategy", {})
    reasoning_board = state.get("reasoning_board", {})
    loop_count = state.get("loop_count", 0)
    phase3_recent_context = _phase3_recent_context_excerpt(state.get("recent_context", ""))
    phase3_reference_policy = _phase3_reference_policy(state.get("search_results", ""), loop_count)
    judge_speaker_packet = _build_judge_speaker_packet(
        reasoning_board=reasoning_board,
        response_strategy=response_strategy,
        phase3_reference_policy=phase3_reference_policy,
    )
    judge_speaker_prompt = _judge_speaker_packet_for_prompt(judge_speaker_packet)
    grounded_mode = judge_speaker_packet.get("speaker_mode") == "grounded_mode"

    if grounded_mode:
        print("[Phase 3] 판사 공개본을 바탕으로 최종 답변 생성 중...")
    else:
        print("[Phase 3] 현재 사용자 입력과 판사 공개본을 바탕으로 직접 대화 응답 생성 중...")

    supervisor_memo = state.get("supervisor_instructions", "")
    if "[119 rescue]" not in supervisor_memo:
        supervisor_memo = ""

    sys_prompt = (
        "당신은 ANIMA의 3차 화자입니다.\n\n"
        "판사가 승인한 공개 패킷을 사용자-facing 최종 응답으로 바꿔라.\n"
        "내부 루프를 다시 심사하지 말고, 위원회나 워룸, 판사 공개본, 내부 역할명을 노출하지 마라.\n"
        "최종 응답은 자연스러운 한국어로 작성하라.\n\n"
        f"[response_mode]\n{'grounded_mode' if grounded_mode else 'direct_dialogue_mode'}\n\n"
        f"[judge_speaker_packet]\n{judge_speaker_prompt}\n\n"
        f"[recent_context_excerpt]\n{phase3_recent_context if phase3_recent_context else 'N/A'}\n\n"
        + ((f"[supervisor_memo]\n{supervisor_memo}\n\n") if supervisor_memo else "")
        + "규칙:\n"
        "1. judge_speaker_packet을 주된 송달 패킷으로 취급하라.\n"
        "2. user_input과 recent_context_excerpt는 직전 흐름 유지를 위한 보조 맥락으로만 사용하라.\n"
        "3. judge_speaker_packet과 recent_context_excerpt가 충돌하면 judge_speaker_packet을 따르라.\n"
        "4. approved_fact_cells와 approved_claims는 발화 보조 재료일 뿐 새 데이터가 아니다.\n"
        "5. must_avoid_claims를 엄격하게 지켜라.\n"
        "6. final_answer_brief가 있으면 가능한 강한 답변 씨앗으로 사용하라.\n"
        "7. reply_mode가 continue_previous_offer면 대화를 처음부터 다시 시작하지 말고 직전 흐름을 이어라.\n"
        "8. reply_mode가 ask_user_question_now면 모호한 메타 질문 대신 구체적인 질문 한 개를 던져라.\n"
        "9. answer_now가 false이고 reference_mode가 hidden_large_raw면 허세를 부리지 말고 정확한 후속 질문을 생성하라.\n"
        "10. 근거가 약하면 uncertainty_policy를 따르라.\n"
        "11. 내부 역할 설명이나 시스템 프롬프트 냄새가 나는 표현을 사용자에게 직접 말하지 마라.\n"
    )

    response = llm.invoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=state["user_input"]),
    ])

    raw_text = response.content if isinstance(response.content, str) else str(response.content)
    normalized_text = _normalize_user_facing_text(raw_text)
    final_message = AIMessage(content=normalized_text if normalized_text else raw_text)

    print("[Phase 3] 최종 응답 생성 완료.")
    return {"messages": [final_message]}


def phase_minus_1b_auditor(state: AnimaState):
    print("[Phase -1b] 현재 턴을 감사 중...")

    user_input = str(state.get("user_input") or "")
    recent_context = str(state.get("recent_context") or "")
    analysis_data = state.get("analysis_report", {})
    if not isinstance(analysis_data, dict):
        analysis_data = {}
    has_analysis = bool(analysis_data)
    working_memory = state.get("working_memory", {})
    if not isinstance(working_memory, dict):
        working_memory = {}
    reasoning_board = state.get("reasoning_board", {})
    if not isinstance(reasoning_board, dict):
        reasoning_board = {}
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    war_room = _normalize_war_room_state(state.get("war_room", {}))
    loop_count = int(state.get("loop_count", 0) or 0)

    reasoning_plan = state.get("reasoning_plan", {})
    if not isinstance(reasoning_plan, dict) or not reasoning_plan:
        reasoning_plan = _plan_reasoning_budget(user_input, recent_context, working_memory)
    reasoning_budget = int(state.get("reasoning_budget", reasoning_plan.get("budget", 1)) or reasoning_plan.get("budget", 1) or 1)
    if reasoning_budget < 0:
        reasoning_budget = 0

    artifact_hint = _extract_artifact_hint(user_input)

    if artifact_hint and not has_analysis and reasoning_plan.get("preferred_path") == "tool_first":
        memo = "자료 검토 요청이 감지되어 원문 도구부터 실행합니다."
        decision = _make_auditor_decision(
            "call_tool",
            memo=memo,
            tool_name="tool_read_artifact",
            tool_args={"artifact_hint": artifact_hint},
        )
        print(f"  [-1b] {memo} | instruction={decision['instruction']}")
        war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
        return {
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "self_correction_memo": memo,
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }

    if _followup_context_expected(user_input, recent_context, working_memory):
        memo = "가벼운 후속 턴으로 보이므로 바로 3차에서 이어서 답할 수 있습니다."
        decision = _make_auditor_decision("phase_3", memo=memo)
        print(f"  [-1b] {memo} | instruction={decision['instruction']}")
        followup_strategy = _followup_ack_strategy(user_input, recent_context)
        war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
        return {
            "response_strategy": followup_strategy,
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "self_correction_memo": memo,
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }

    if _is_assistant_question_request_turn(user_input):
        memo = "사용자가 지금 당장 assistant의 구체적인 질문 1개를 원합니다."
        decision = _make_auditor_decision("phase_3", memo=memo)
        print(f"  [-1b] {memo} | instruction={decision['instruction']}")
        question_strategy = _ask_user_question_strategy(user_input, working_memory)
        war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
        return {
            "response_strategy": question_strategy,
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "self_correction_memo": memo,
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }

    if not has_analysis and reasoning_plan.get("preferred_path") == "internal_reasoning" and reasoning_budget > 0:
        memo = str(reasoning_plan.get("rationale") or "현재 턴은 바로 내보내기 전에 내부 사고 1회가 더 필요합니다.").strip()
        decision = _make_auditor_decision("internal_reasoning", memo=memo)
        print(f"  [-1b] {memo} | instruction={decision['instruction']}")
        war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
        return {
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "self_correction_memo": memo,
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }

    if not has_analysis and reasoning_plan.get("preferred_path") == "direct_answer":
        memo = str(reasoning_plan.get("rationale") or "현재 턴은 도구를 먼저 쓰지 않아도 직접 답변할 수 있습니다.").strip()
        decision = _make_auditor_decision("phase_3", memo=memo)
        response_strategy = {}
        if _is_initiative_request_turn(user_input):
            response_strategy = _initiative_request_strategy(user_input, working_memory)
        response_strategy, _, speaker_review = _prepare_phase3_delivery(
            user_input=user_input,
            recent_context=recent_context,
            working_memory=working_memory,
            reasoning_board=reasoning_board,
            analysis_data=analysis_data,
            response_strategy=response_strategy,
            search_results=state.get("search_results", ""),
            loop_count=loop_count,
        )
        if speaker_review.get("should_remand") and reasoning_budget > 0:
            decision = _make_auditor_decision(
                "internal_reasoning",
                memo="3차 송달 점검 결과 패킷이 아직 약하므로, 한 번 더 내부 루프를 도는 편이 안전합니다.",
            )
            response_strategy = {}
        print(f"  [-1b] {decision.get('memo', memo)} | instruction={decision['instruction']}")
        war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
        return {
            "response_strategy": response_strategy,
            "auditor_instruction": decision["instruction"],
            "auditor_decision": decision,
            "self_correction_memo": decision.get("memo", memo),
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "speaker_review": speaker_review,
            "reasoning_budget": reasoning_budget,
            "reasoning_plan": reasoning_plan,
        }

    if has_analysis or reasoning_board.get("candidate_pairs") or reasoning_board.get("fact_cells"):
        reasoning_board = _audit_reasoning_board(reasoning_board, analysis_data)
        preferred_strategist = _preferred_decision_from_strategist(
            strategist_output,
            analysis_data,
            loop_count,
            reasoning_budget=reasoning_budget,
        )
        if preferred_strategist:
            print(f"  [-1b] 전략 계획 판정: {preferred_strategist.get('memo', '')} | instruction={preferred_strategist.get('instruction', '')}")
            war_room = _war_room_after_judge(war_room, preferred_strategist, analysis_data, reasoning_board)
            response_strategy = strategist_output.get("response_strategy", {})
            if not isinstance(response_strategy, dict):
                response_strategy = {}
            if str(preferred_strategist.get("action") or "").strip() != "phase_3":
                response_strategy = {}
            if str(preferred_strategist.get("action") or "").strip() == "answer_not_ready":
                response_strategy = _answer_not_ready_strategy(user_input, war_room)
            return {
                "strategist_output": strategist_output,
                "response_strategy": response_strategy,
                "auditor_instruction": preferred_strategist.get("instruction", ""),
                "auditor_decision": preferred_strategist,
                "self_correction_memo": preferred_strategist.get("memo", ""),
                "reasoning_board": reasoning_board,
                "war_room": war_room,
                "reasoning_budget": reasoning_budget,
                "reasoning_plan": reasoning_plan,
            }
        preferred_verdict = _preferred_decision_from_verdict(
            reasoning_board,
            analysis_data,
            loop_count,
            user_input=user_input,
            working_memory=working_memory,
            reasoning_budget=reasoning_budget,
        )
        if preferred_verdict:
            print(f"  [-1b] 판결 보드 결정: {preferred_verdict.get('memo', '')} | instruction={preferred_verdict.get('instruction', '')}")
            war_room = _war_room_after_judge(war_room, preferred_verdict, analysis_data, reasoning_board)
            response_strategy = {}
            if str(preferred_verdict.get("action") or "").strip() == "answer_not_ready":
                response_strategy = _answer_not_ready_strategy(user_input, war_room)
            return {
                "strategist_output": strategist_output,
                "response_strategy": response_strategy,
                "auditor_instruction": preferred_verdict.get("instruction", ""),
                "auditor_decision": preferred_verdict,
                "self_correction_memo": preferred_verdict.get("memo", ""),
                "reasoning_board": reasoning_board,
                "war_room": war_room,
                "reasoning_budget": reasoning_budget,
                "reasoning_plan": reasoning_plan,
            }

    analysis_packet = _analysis_packet_for_prompt(analysis_data, include_thought=True)
    strategist_packet = _strategist_output_packet_for_prompt(strategist_output)
    working_memory_packet = _working_memory_packet_for_prompt(working_memory)
    reasoning_board_packet = _reasoning_board_packet_for_prompt(reasoning_board, approved_only=False)
    user_state = state.get("user_state", "")
    user_char = state.get("user_char", "")
    time_gap = state.get("time_gap", 0)
    tolerance = state.get("global_tolerance", 1.0)
    bio_status = state.get("biolink_status", "")

    sys_prompt = (
        "당신은 ANIMA의 -1b 감사관이자 판사입니다.\n\n"
        "현재 턴, 최근 대화, working_memory, 분석 보고, 그리고 전략가의 계획을 함께 읽고 판결을 내려라.\n"
        "이 사건이 바로 3차로 가야 하는지, 내부 사고를 더 해야 하는지, 도구를 호출해야 하는지, 계획을 더 세워야 하는지, 아니면 answer_not_ready로 가야 하는지 결정하라.\n"
        "보류하거나 반려할 때는 왜 그런지 운영 언어로 분명하게 설명하라.\n"
        "모든 자유서술 필드는 한국어로 작성하라.\n\n"
        f"[user_input]\n{user_input}\n\n"
        f"[recent_context]\n{recent_context}\n\n"
        f"[user_state]\n{user_state}\n\n"
        f"[user_char]\n{user_char}\n\n"
        f"[time_gap]\n{time_gap}\n\n"
        f"[global_tolerance]\n{tolerance}\n\n"
        f"[biolink_status]\n{bio_status}\n\n"
        f"[working_memory]\n{working_memory_packet}\n\n"
        f"[reasoning_budget]\n{reasoning_budget}\n\n"
        f"[reasoning_plan]\n{json.dumps(reasoning_plan, ensure_ascii=False)}\n\n"
        f"[reasoning_board]\n{reasoning_board_packet}\n\n"
        f"[analysis_report]\n{analysis_packet}\n\n"
        f"[analysis_exists]\n{has_analysis}\n\n"
        f"[strategist_output]\n{strategist_packet}\n\n"
        "규칙:\n"
        "1. call_tool을 고를 때 instruction_to_0는 반드시 정확한 tool call이어야 한다.\n"
        "2. analysis_exists가 false이면 investigation_status가 이미 존재하는 것처럼 꾸며내지 마라.\n"
        "3. current user_input을 주 앵커로 삼고, recent_context와 working_memory는 보조 증거로만 사용하라.\n"
        "4. 2차는 사건을 진단하고, -1a는 단계별 행동 계획을 세운다.\n"
        "5. strategist_output.action_plan.required_tool이 유효하면, 즉흥적인 다른 도구 경로를 만들기 전에 그 계획부터 검토하라.\n"
        "6. COMPLETED는 phase_3로 갈 수 있다.\n"
        "7. reasoning_budget은 계획 가이드이지 절대적인 하드 컷오프가 아니다.\n"
        "8. EXPANSION_REQUIRED는 soft budget이 찼더라도 graph의 hard stop이 남아 있으면 계속 plan_more나 call_tool을 선택할 수 있다.\n"
        "9. 송달 패킷이 약하면 bluffing보다 plan_more 또는 answer_not_ready를 우선하라.\n"
    )

    decision = None
    try:
        structured_llm = llm.with_structured_output(AuditorOutput)
        res = structured_llm.invoke([SystemMessage(content=sys_prompt)])
        memo = str(res.rejection_reason or "").strip()
        preferred = _preferred_decision_from_strategist(
            strategist_output,
            analysis_data,
            loop_count,
            reasoning_budget=reasoning_budget,
        )
        if preferred is None and has_analysis:
            preferred = _preferred_decision_from_analysis(
                analysis_data,
                loop_count,
                user_input=user_input,
                working_memory=working_memory,
                reasoning_budget=reasoning_budget,
            )
        if preferred:
            decision = preferred
        else:
            decision = _decision_from_instruction(
                str(res.instruction_to_0 or "").strip(),
                is_satisfied=bool(res.is_satisfied),
                memo=memo,
            )
        if decision is None:
            if artifact_hint:
                decision = _make_auditor_decision(
                    "call_tool",
                    memo=memo or "fallback 라우팅에서 자료 검토 요청을 감지했습니다.",
                    tool_name="tool_read_artifact",
                    tool_args={"artifact_hint": artifact_hint},
                )
            elif _should_default_to_memory_search(user_input, analysis_data, working_memory):
                keyword = _normalize_search_keyword(user_input)
                decision = _make_auditor_decision(
                    "call_tool",
                    memo=memo or "retrieval 의존 턴으로 보여 fallback 메모리 검색을 선택했습니다.",
                    tool_name="tool_search_memory",
                    tool_args={"keyword": keyword or "recent context"},
                )
            else:
                decision = _make_auditor_decision(
                    "phase_3",
                    memo=memo or "더 강한 도구 경로가 없어 fallback 직접 송달을 선택했습니다.",
                )
    except Exception as e:
        print(f"[Phase -1b] 구조화 출력 예외: {e}")
        preferred = _preferred_decision_from_strategist(
            strategist_output,
            analysis_data,
            loop_count,
            reasoning_budget=reasoning_budget,
        )
        if preferred is None and has_analysis:
            preferred = _preferred_decision_from_analysis(
                analysis_data,
                loop_count,
                user_input=user_input,
                working_memory=working_memory,
                reasoning_budget=reasoning_budget,
            )
        if preferred:
            decision = preferred
        else:
            if artifact_hint:
                decision = _make_auditor_decision(
                    "call_tool",
                    memo="구조화 출력이 실패하여 fallback으로 자료 검토를 선택했습니다.",
                    tool_name="tool_read_artifact",
                    tool_args={"artifact_hint": artifact_hint},
                )
            elif _should_default_to_memory_search(user_input, analysis_data, working_memory):
                decision = _make_auditor_decision(
                    "call_tool",
                    memo="구조화 출력이 실패하여 fallback 메모리 검색을 선택했습니다.",
                    tool_name="tool_search_memory",
                    tool_args={"keyword": _normalize_search_keyword(user_input) or "recent context"},
                )
            else:
                decision = _make_auditor_decision(
                    "phase_3",
                    memo="구조화 출력이 실패하여 fallback 직접 송달을 선택했습니다.",
                )

    if not has_analysis and _decision_uses_unanchored_topic(decision, user_input, analysis_data):
        if _is_directive_or_correction_turn(user_input) or _is_initiative_request_turn(user_input):
            decision = _make_auditor_decision(
                "phase_3",
                memo="무관한 오래된 주제를 차단하고 현재 사용자 요청으로 다시 앵커링했습니다.",
            )
        elif _is_artifact_review_turn(user_input):
            decision = _make_auditor_decision(
                "call_tool",
                memo="무관한 오래된 주제를 차단하고 자료 검토 경로로 다시 앵커링했습니다.",
                tool_name="tool_read_artifact",
                tool_args={"artifact_hint": _extract_artifact_hint(user_input)},
            )
        elif _should_default_to_memory_search(user_input, analysis_data, working_memory):
            decision = _make_auditor_decision(
                "call_tool",
                memo="무관한 오래된 주제를 차단하고 메모리 검색으로 다시 앵커링했습니다.",
                tool_name="tool_search_memory",
                tool_args={"keyword": _normalize_search_keyword(user_input) or "recent context"},
            )
        else:
            decision = _make_auditor_decision(
                "phase_3",
                memo="무관한 오래된 주제를 차단하고 현재 사용자 요청으로 다시 앵커링했습니다.",
            )

    reasoning_board = _audit_reasoning_board(reasoning_board, analysis_data)
    if reasoning_board.get("candidate_pairs"):
        approved_pairs = len(reasoning_board.get("final_pair_ids", []))
        print(f"  [-1b] 승인된 추론쌍={approved_pairs} / 전체={len(reasoning_board.get('candidate_pairs', []))}")

    war_room = _war_room_after_judge(war_room, decision, analysis_data, reasoning_board)
    response_strategy = strategist_output.get("response_strategy", {}) if str(decision.get("action") or "").strip() == "phase_3" else {}
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    if str(decision.get("action") or "").strip() == "answer_not_ready":
        response_strategy = _answer_not_ready_strategy(user_input, war_room)
    print(f"  [-1b] 최종 판정: {decision.get('memo', '')} | instruction={decision.get('instruction', '')}")
    return {
        "strategist_output": strategist_output,
        "response_strategy": response_strategy,
        "auditor_instruction": decision.get("instruction", ""),
        "auditor_decision": decision,
        "self_correction_memo": decision.get("memo", ""),
        "reasoning_board": reasoning_board,
        "war_room": war_room,
        "reasoning_budget": reasoning_budget,
        "reasoning_plan": reasoning_plan,
    }


def _raw_dialogue_text_for_role_check(raw_read_report: dict, user_input: str) -> str:
    parts = []
    if isinstance(raw_read_report, dict):
        for item in raw_read_report.get("items", []):
            if not isinstance(item, dict):
                continue
            observed = str(item.get("observed_fact") or "").strip()
            excerpt = str(item.get("excerpt") or "").strip()
            if observed:
                parts.append(observed)
            elif excerpt:
                parts.append(excerpt)
    user_text = str(user_input or "").strip()
    if user_text:
        parts.append(user_text)
    return " ".join(part for part in parts if part)


def _extract_role_sensitive_quote(raw_text: str) -> str:
    text = str(raw_text or "").strip()
    if not text:
        return ""
    for marker in ["내가 너", "내가 널", "내가 너를", "나나 너나", "네가 나", "네가 날", "네가 나를"]:
        idx = text.find(marker)
        if idx >= 0:
            return text[idx:idx + 120].strip()
    return text[:120]


def _enforce_role_fidelity_for_dialogue(analysis_dict: dict, raw_read_report: dict, user_input: str):
    if not isinstance(analysis_dict, dict):
        analysis_dict = {}

    raw_text = _raw_dialogue_text_for_role_check(raw_read_report, user_input)
    if not raw_text:
        return analysis_dict

    role_sensitive = any(marker in raw_text for marker in ["내가 너", "내가 널", "내가 너를", "나나 너나", "네가 나", "네가 날", "네가 나를"])
    if not role_sensitive:
        return analysis_dict

    quote = _extract_role_sensitive_quote(raw_text)
    evidences = analysis_dict.get("evidences", [])
    if not isinstance(evidences, list):
        evidences = []

    direct_quote_evidence = f'직접 발화 근거: "{quote}"'
    if direct_quote_evidence not in evidences:
        evidences.insert(0, direct_quote_evidence)
    analysis_dict["evidences"] = evidences[:8]

    summary = str(analysis_dict.get("situational_brief") or "").strip()
    suspicious_flip = any(token in summary for token in ["AI가 사용자를", "AI가 자신을", "사용자를 이상하게", "assistant가 사용자를"])
    if suspicious_flip or not summary:
        analysis_dict["situational_brief"] = (
            f'사용자는 "{quote}"라고 직접 표현하며, 현재 대화가 자신과 assistant 모두 제대로 말을 잇지 못하는 쪽으로 꼬였다고 보고 있습니다.'
        )

    thought = str(analysis_dict.get("analytical_thought") or "").strip()
    fidelity_note = "원문에 등장한 화자/대상 관계와 인칭을 뒤집지 말고 그대로 유지해야 합니다."
    if fidelity_note not in thought:
        analysis_dict["analytical_thought"] = (
            f"{fidelity_note} {thought}".strip()
            if thought else fidelity_note
        )

    return analysis_dict


def phase_2_analyzer(state: AnimaState):
    print("[Phase 2b] phase_2a 원문 검토 결과를 바탕으로 구조화 증거철을 작성 중...")

    current_loop = state.get("loop_count", 0)
    auditor_memo = state.get("self_correction_memo", "")
    working_memory_packet = _working_memory_packet_for_prompt(state.get("working_memory", {}))
    raw_read_report = state.get("raw_read_report", {})
    raw_read_packet = _raw_read_report_packet_for_prompt(raw_read_report)
    source_relay_packet = _build_source_relay_packet(raw_read_report)
    source_relay_prompt = _source_relay_packet_for_prompt(source_relay_packet)
    read_mode = str(raw_read_report.get("read_mode") or "").strip()
    analysis_mode = (
        "recent_dialogue_review"
        if read_mode == "recent_dialogue_review"
        else "internal_reasoning_only"
        if read_mode == "current_turn_only"
        else "tool_grounded"
    )

    sys_prompt = (
        "당신은 ANIMA의 2b 검사이자 사실 감사관입니다.\n\n"
        "phase 2a 원문 검토 보고를 읽고, 그 근거 위에서만 분석 보고서를 작성하라.\n"
        "반드시 fact-first로 쓰고, 직접 발화의 주어/목적어와 화자 관계를 뒤집지 마라.\n"
        "특히 user_input이나 raw_read_report에 '내가/너를/나나 너나' 같은 표현이 있으면, 최소 한 개 이상의 직접 인용 근거를 evidences에 넣어라.\n"
        "당신의 임무는 진단이지 다음 도구 계획이 아니다. 인식적 결핍이 무엇인지 분명하게 적어라.\n"
        "모든 자유서술 필드는 한국어로 작성하라.\n\n"
        f"[analysis_mode]\n{analysis_mode}\n\n"
        f"[user_input]\n{state['user_input']}\n\n"
        f"[raw_read_report]\n{raw_read_packet}\n\n"
        f"[auditor_memo]\n{auditor_memo if auditor_memo else 'N/A'}\n\n"
        f"[working_memory]\n{working_memory_packet}\n\n"
        f"[source_relay_packet]\n{source_relay_prompt}\n\n"
        "[phase_2b_source_contract]\n"
        "- phase_2a가 넘긴 모든 source packet에 대해 source_judgments를 작성하라.\n"
        "- 각 source_judgment에는 source_status, accepted_facts, objection_reason, missing_info, search_needed가 들어가야 한다.\n"
        "- must_forward_facts는 반드시 릴레이되어야 하는 직접 관찰 사실이다. 존재한다면 비판보다 먼저 accepted_facts와 evidences에 반영하라.\n"
        "- situational_brief는 fact-first로 작성하라. 사용자 태도 평가는 source facts와 source judgments 이후에만 덧붙여라.\n\n"
        "규칙:\n"
        "1. evidences는 구체적이고 source-grounded여야 한다.\n"
        "2. analytical_thought는 비판적이어도 되지만 반드시 evidences에 묶여 있어야 한다.\n"
        "3. 직접 발화의 인칭을 3인칭 일반론으로 바꾸는 과정에서 주어/목적어를 뒤집지 마라.\n"
        "4. 현재 근거로 답변이 가능할 때만 COMPLETED를 사용하라.\n"
        "5. 직접 근거가 비면 INCOMPLETE를 사용하라.\n"
        "6. 더 읽거나 확인해야 종결할 수 있을 때만 EXPANSION_REQUIRED를 사용하라.\n"
        "7. 다음 도구를 계획하지 말고, 어떤 인식적 결핍이 있는지만 적어라.\n"
        "8. phase_2a가 읽지 않은 raw fact를 새로 만들지 마라.\n"
        "9. internal_reasoning_only 모드에서 바로 답할 수 있다면 memory search를 강요하지 마라.\n"
        "10. recent_dialogue_review 모드에서는 raw_read_report.items에 담긴 실제 최근 대화 턴을 직접 근거로 사용하라.\n"
    )

    structured_llm = llm.with_structured_output(AnalysisReport)
    try:
        response_obj = structured_llm.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=state["user_input"]),
        ])
        analysis_dict = _normalize_analysis_with_source_relay(response_obj.model_dump(), source_relay_packet)
        analysis_dict = _enforce_recent_dialogue_review_analysis(analysis_dict, raw_read_report)
        analysis_dict = _enforce_role_fidelity_for_dialogue(analysis_dict, raw_read_report, state["user_input"])
        reasoning_board = _build_reasoning_board_from_analysis(state, analysis_dict)
        status = analysis_dict.get("investigation_status", "UNKNOWN")
        brief = analysis_dict.get("situational_brief", "")
        print(f"  [Phase 2b] 상태={status} | 요약={brief[:120]}")
        fake_ai_message = AIMessage(content=json.dumps(analysis_dict, ensure_ascii=False))
    except Exception as e:
        print(f"[Phase 2b] 구조화 출력 예외: {e}")
        analysis_dict = {
            "evidences": [],
            "source_judgments": [],
            "analytical_thought": "구조화 출력이 실패하여 2차 fallback 분석 문구를 사용합니다.",
            "situational_brief": "구조화 출력 실패로 인해 2차 fallback 경로가 사용되었습니다.",
            "investigation_status": "INCOMPLETE",
        }
        analysis_dict = _enforce_role_fidelity_for_dialogue(analysis_dict, raw_read_report, state["user_input"])
        reasoning_board = _build_reasoning_board_from_analysis(state, analysis_dict)
        fake_ai_message = AIMessage(content="phase_2_fallback_seed")

    war_room = _war_room_from_critic(state, analysis_dict, raw_read_report)
    return {
        "analysis_report": analysis_dict,
        "reasoning_board": reasoning_board,
        "war_room": war_room,
        "loop_count": current_loop + 1,
        "messages": [fake_ai_message],
    }
