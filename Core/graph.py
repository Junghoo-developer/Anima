# Core/graph.py
from langgraph.graph import END, START, StateGraph
from .state import AnimaState
from .nodes import (
    phase_minus_1a_thinker,
    phase_minus_1b_auditor,
    phase_0_supervisor,
    phase_1_searcher,
    phase_2a_reader,
    phase_2_analyzer,
    phase_3_validator,
    phase_119_rescue,
)
from .speaker_guards import (
    phase_minus_1b_auditor_with_speaker_guard,
    phase_3_validator_with_speaker_guard,
)


def _log(message: str, fallback: str | None = None):
    try:
        print(message)
    except UnicodeEncodeError:
        print(fallback or message)


def route_audit_result(state: AnimaState):
    decision = state.get("auditor_decision", {})
    action = str(decision.get("action") or "").strip()
    instruction = str(state.get("auditor_instruction", "") or "").strip()
    reasoning_board = state.get("reasoning_board", {})
    verdict = reasoning_board.get("verdict_board", {}) if isinstance(reasoning_board, dict) else {}
    verdict_answer_now = bool(verdict.get("answer_now")) if isinstance(verdict, dict) else False
    try:
        reasoning_budget = max(int(state.get("reasoning_budget", 1)), 0)
    except (TypeError, ValueError):
        reasoning_budget = 1
    hard_stop = max(reasoning_budget, 1) + 2

    if action == "phase_3":
        _log("[System] -1b passed the turn to phase_3.")
        return "phase_3"
    if action == "answer_not_ready":
        _log("[System] -1b가 아직 답변 준비가 끝나지 않았다고 판정하여, 한계를 투명하게 설명하는 응답으로 보냅니다.")
        return "phase_3"
    if action == "phase_119":
        _log("[System] -1b requested phase_119.")
        return "phase_119"
    if action in {"internal_reasoning", "plan_more"}:
        if state.get("loop_count", 0) >= hard_stop:
            _log("[System] 워룸 계획 한도를 넘겨 phase_119로 보냅니다.")
            return "phase_119"
    if action == "internal_reasoning":
        _log("[System] -1b requested internal critic-advocate reasoning.")
        return "phase_2a"
    if action == "plan_more":
        _log("[System] -1b가 워룸 추가 계획 토론을 요청했습니다.")
        return "phase_2a"
    if action == "call_tool":
        _log("[System] -1b rejected and routed to 0_supervisor.")
        return "0_supervisor"

    if instruction in {"tool_pass_to_phase_3", "tool_pass_to_phase_3()"}:
        return "phase_3"
    if instruction in {"tool_call_119_rescue", "tool_call_119_rescue()"}:
        return "phase_119"
    if verdict_answer_now:
        _log("[System] Verdict board allows phase_3.")
        return "phase_3"

    if state.get("loop_count", 0) >= hard_stop:
        _log("[System] Auditor retries exceeded; routing to phase_119.")
        return "phase_119"

    _log("[System] -1b rejected and routed to 0_supervisor.")
    return "0_supervisor"


def route_after_supervisor(state: AnimaState):
    loop_count = state.get("loop_count", 0)
    try:
        reasoning_budget = max(int(state.get("reasoning_budget", 1)), 0)
    except (TypeError, ValueError):
        reasoning_budget = 1
    hard_stop = max(reasoning_budget, 1) + 2
    if loop_count >= hard_stop:
        return "phase_119"

    messages = state.get("messages", [])
    if not messages:
        return "phase_3"

    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_names = [tool_call.get("name") for tool_call in last_message.tool_calls]
        if "tool_call_119_rescue" in tool_names:
            return "phase_119"
        if "tool_pass_to_phase_3" in tool_names:
            return "phase_3"
        return "phase_1"
    return "phase_3"


_log("ANIMA graph assembly starting...")

workflow = StateGraph(AnimaState)
workflow.add_node("-1a_thinker", phase_minus_1a_thinker)
workflow.add_node("-1b_auditor", phase_minus_1b_auditor_with_speaker_guard)
workflow.add_node("0_supervisor", phase_0_supervisor)
workflow.add_node("phase_1", phase_1_searcher)
workflow.add_node("phase_2a", phase_2a_reader)
workflow.add_node("phase_2", phase_2_analyzer)
workflow.add_node("phase_3", phase_3_validator_with_speaker_guard)
workflow.add_node("phase_119", phase_119_rescue)

workflow.add_edge(START, "-1b_auditor")
workflow.add_edge("-1a_thinker", "-1b_auditor")
workflow.add_conditional_edges(
    "-1b_auditor",
    route_audit_result,
    {"phase_3": "phase_3", "0_supervisor": "0_supervisor", "phase_119": "phase_119", "phase_2a": "phase_2a"},
)
workflow.add_conditional_edges("0_supervisor", route_after_supervisor)
workflow.add_edge("phase_1", "phase_2a")
workflow.add_edge("phase_2a", "phase_2")
workflow.add_edge("phase_2", "-1a_thinker")
workflow.add_edge("phase_119", "phase_3")
workflow.add_edge("phase_3", END)

anima_app = workflow.compile()
_log("ANIMA graph compile complete.")
