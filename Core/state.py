# Core/state.py
import copy
from typing import Annotated, Any, Dict, List, TypedDict, cast
import operator

from .evidence_ledger import build_initial_evidence_ledger


class AnimaState(TypedDict):
    user_input: str
    current_time: str
    time_gap: float
    recent_context: str
    global_tolerance: float

    user_state: str
    user_char: str
    songryeon_thoughts: str
    tactical_briefing: str
    biolink_status: str
    working_memory: Dict[str, Any]
    operation_plan: Dict[str, Any]
    reasoning_board: Dict[str, Any]
    war_room: Dict[str, Any]
    war_room_output: Dict[str, Any]
    speaker_review: Dict[str, Any]
    start_gate_review: Dict[str, Any]
    start_gate_switches: Dict[str, Any]
    s_thinking_packet: Dict[str, Any]
    s_thinking_history: Dict[str, Any]
    ops_decision: Dict[str, Any]
    critic_lens_packet: Dict[str, Any]
    strategist_objection_packet: Dict[str, Any]
    delivery_status: str
    reasoning_budget: int
    reasoning_plan: Dict[str, Any]
    progress_markers: Dict[str, Any]
    evidence_ledger: Dict[str, Any]
    readiness_decision: Dict[str, Any]

    thought_logs: List[Dict[str, str]]
    strategist_output: Dict[str, Any]
    strategist_goal: Dict[str, Any]
    normalized_goal: Dict[str, Any]
    response_strategy: Dict[str, Any]
    auditor_instruction: str
    auditor_decision: Dict[str, Any]
    strategy_audit: Dict[str, Any]
    self_correction_memo: str

    supervisor_instructions: str
    execution_status: str
    execution_block_reason: str
    execution_trace: Dict[str, Any]
    tool_carryover: Dict[str, Any]
    search_results: str
    raw_read_report: Dict[str, Any]
    analysis_report: Dict[str, Any]
    rescue_handoff_packet: Dict[str, Any]
    phase3_delivery_packet: Dict[str, Any]
    delivery_review: Dict[str, Any]
    delivery_review_context: Dict[str, Any]
    delivery_review_rejections: int

    loop_count: int
    executed_actions: List[str]
    tool_result_cache: Dict[str, Any]
    used_sources: List[str]

    messages: Annotated[list, operator.add]


ANIMA_STATE_DEFAULTS: Dict[str, Any] = {
    "user_input": "",
    "current_time": "",
    "time_gap": 0.0,
    "recent_context": "",
    "global_tolerance": 1.0,
    "user_state": "",
    "user_char": "",
    "songryeon_thoughts": "",
    "tactical_briefing": "",
    "biolink_status": "",
    "working_memory": {},
    "operation_plan": {},
    "reasoning_board": {},
    "war_room": {},
    "war_room_output": {},
    "speaker_review": {},
    "start_gate_review": {},
    "start_gate_switches": {},
    "s_thinking_packet": {},
    "s_thinking_history": {},
    "ops_decision": {},
    "critic_lens_packet": {},
    "strategist_objection_packet": {},
    "delivery_status": "",
    "reasoning_budget": 0,
    "reasoning_plan": {},
    "progress_markers": {},
    "evidence_ledger": {},
    "readiness_decision": {},
    "thought_logs": [],
    "strategist_output": {},
    "strategist_goal": {},
    "normalized_goal": {},
    "response_strategy": {},
    "auditor_instruction": "",
    "auditor_decision": {},
    "strategy_audit": {},
    "self_correction_memo": "",
    "supervisor_instructions": "",
    "execution_status": "",
    "execution_block_reason": "",
    "execution_trace": {},
    "tool_carryover": {},
    "search_results": "",
    "raw_read_report": {},
    "analysis_report": {},
    "rescue_handoff_packet": {},
    "phase3_delivery_packet": {},
    "delivery_review": {},
    "delivery_review_context": {},
    "delivery_review_rejections": 0,
    "loop_count": 0,
    "executed_actions": [],
    "tool_result_cache": {},
    "used_sources": [],
    "messages": [],
}

LONG_LIVED_FIELDS = {
    "user_input",
    "current_time",
    "time_gap",
    "recent_context",
    "global_tolerance",
    "user_state",
    "user_char",
    "songryeon_thoughts",
    "tactical_briefing",
    "biolink_status",
    "working_memory",
    "progress_markers",
    "evidence_ledger",
}

TURN_LIVED_FIELDS = {
    "operation_plan",
    "reasoning_board",
    "war_room",
    "war_room_output",
    "speaker_review",
    "start_gate_review",
    "start_gate_switches",
    "s_thinking_packet",
    "s_thinking_history",
    "ops_decision",
    "critic_lens_packet",
    "strategist_objection_packet",
    "delivery_status",
    "reasoning_budget",
    "reasoning_plan",
    "readiness_decision",
    "thought_logs",
    "strategist_output",
    "strategist_goal",
    "normalized_goal",
    "response_strategy",
    "auditor_instruction",
    "auditor_decision",
    "strategy_audit",
    "self_correction_memo",
    "supervisor_instructions",
    "execution_status",
    "execution_block_reason",
    "execution_trace",
    "tool_carryover",
    "search_results",
    "raw_read_report",
    "analysis_report",
    "rescue_handoff_packet",
    "phase3_delivery_packet",
    "delivery_review",
    "delivery_review_context",
    "delivery_review_rejections",
    "loop_count",
    "executed_actions",
    "tool_result_cache",
    "used_sources",
    "messages",
}


def anima_state_keys() -> List[str]:
    return list(AnimaState.__annotations__.keys())


def empty_anima_state() -> AnimaState:
    return cast(AnimaState, copy.deepcopy(ANIMA_STATE_DEFAULTS))


def build_initial_anima_state(
    *,
    user_input: str,
    current_time: str,
    time_gap: float,
    recent_context: str,
    global_tolerance: float,
    user_state: str,
    user_char: str,
    songryeon_thoughts: str,
    tactical_briefing: str,
    biolink_status: str,
    working_memory: Dict[str, Any] | None = None,
) -> AnimaState:
    state = empty_anima_state()
    state.update(
        {
            "user_input": user_input,
            "current_time": current_time,
            "time_gap": time_gap,
            "recent_context": recent_context,
            "global_tolerance": global_tolerance,
            "user_state": user_state,
            "user_char": user_char,
            "songryeon_thoughts": songryeon_thoughts,
            "tactical_briefing": tactical_briefing,
            "biolink_status": biolink_status,
            "working_memory": copy.deepcopy(working_memory or {}),
            "evidence_ledger": build_initial_evidence_ledger(
                user_input=user_input,
                current_time=current_time,
                recent_context=recent_context,
                user_state=user_state,
                user_char=user_char,
                songryeon_thoughts=songryeon_thoughts,
                biolink_status=biolink_status,
                working_memory=working_memory or {},
            ),
        }
    )
    return state


def normalize_anima_state(state: Dict[str, Any] | None) -> AnimaState:
    normalized = empty_anima_state()
    if isinstance(state, dict):
        for key, value in state.items():
            if key in normalized:
                normalized[key] = value
    return normalized


def get_strategist_goal(state: Dict[str, Any] | None) -> Dict[str, Any]:
    """Return the V3 strategist goal through the one-season normalized_goal alias."""
    if not isinstance(state, dict):
        return {}
    strategist_goal = state.get("strategist_goal", {})
    if isinstance(strategist_goal, dict) and strategist_goal:
        return copy.deepcopy(strategist_goal)
    normalized_goal = state.get("normalized_goal", {})
    if isinstance(normalized_goal, dict) and normalized_goal:
        return copy.deepcopy(normalized_goal)
    return {}


def cleanup_turn_lived_fields(state: Dict[str, Any] | None) -> AnimaState:
    """Return a state copy with per-turn runtime artifacts reset.

    This is a contract helper, not an automatic graph hook. Call it only after
    the canonical turn record, Dream/TurnProcess snapshots, and FieldMemo
    candidate have already consumed the final state.
    """
    cleaned = normalize_anima_state(state)
    for key in TURN_LIVED_FIELDS:
        cleaned[key] = copy.deepcopy(ANIMA_STATE_DEFAULTS[key])
    return cleaned
