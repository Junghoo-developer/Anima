# Core/state.py
from typing import Annotated, Any, Dict, List, TypedDict
import operator


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
    reasoning_board: Dict[str, Any]
    war_room: Dict[str, Any]
    speaker_review: Dict[str, Any]
    reasoning_budget: int
    reasoning_plan: Dict[str, Any]

    thought_logs: List[Dict[str, str]]
    strategist_output: Dict[str, Any]
    response_strategy: Dict[str, Any]
    auditor_instruction: str
    auditor_decision: Dict[str, Any]
    self_correction_memo: str

    supervisor_instructions: str
    search_results: str
    raw_read_report: Dict[str, Any]
    analysis_report: Dict[str, Any]

    loop_count: int
    executed_actions: List[str]
    used_sources: List[str]

    messages: Annotated[list, operator.add]
