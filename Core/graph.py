# Core/graph.py
import os

from langgraph.graph import END, START, StateGraph
try:
    from langgraph.checkpoint.memory import MemorySaver
except Exception:  # pragma: no cover - optional runtime feature
    MemorySaver = None

from .nodes import (
    phase_0_supervisor,
    phase_1_searcher,
    phase_119_rescue,
    phase_2_analyzer,
    phase_2a_reader,
    phase_delivery_review,
    phase_minus_1a_thinker,
    phase_minus_1s_start_gate,
    phase_warroom_deliberator,
)
from .speaker_guards import phase_3_validator_with_speaker_guard
from .readiness import normalize_readiness_decision
from .state import AnimaState


def _log(message: str, fallback: str | None = None):
    try:
        print(message)
    except UnicodeEncodeError:
        print(fallback or message)


def route_audit_result(state: AnimaState):
    return route_audit_result_v2(state)


def route_after_supervisor(state: AnimaState):
    loop_count = state.get("loop_count", 0)
    try:
        reasoning_budget = max(int(state.get("reasoning_budget", 1)), 0)
    except (TypeError, ValueError):
        reasoning_budget = 1
    hard_stop = max(reasoning_budget, 1) + 2
    if loop_count >= hard_stop:
        return "phase_119"

    execution_status = str(state.get("execution_status") or "").strip().lower()
    if execution_status == "handoff_planner":
        return "-1a_thinker"
    if execution_status == "handoff_phase2a":
        return "phase_2a"
    if execution_status == "blocked":
        return "-1s_start_gate"

    messages = state.get("messages", [])
    if not messages:
        return "-1s_start_gate"

    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_names = [tool_call.get("name") for tool_call in last_message.tool_calls]
        if "tool_call_119_rescue" in tool_names:
            return "phase_119"
        if "tool_pass_to_phase_3" in tool_names:
            return "phase_3"
        return "phase_1"
    return "-1s_start_gate"


def _graph_hard_stop_exceeded(state: AnimaState) -> bool:
    try:
        loop_count = int(state.get("loop_count", 0) or 0)
    except (TypeError, ValueError):
        loop_count = 0
    try:
        reasoning_budget = max(int(state.get("reasoning_budget", 1) or 1), 0)
    except (TypeError, ValueError):
        reasoning_budget = 1
    return loop_count >= max(reasoning_budget, 1) + 2


def _executable_tool_request(strategist_output: dict) -> dict:
    tool_request = strategist_output.get("tool_request", {}) if isinstance(strategist_output, dict) else {}
    if not isinstance(tool_request, dict):
        return {}
    tool_name = str(tool_request.get("tool_name") or "").strip()
    if bool(tool_request.get("should_call_tool")) and tool_name:
        return tool_request
    return {}


def _has_delivery_strategy_material(response_strategy: dict) -> bool:
    if not isinstance(response_strategy, dict) or not response_strategy:
        return False
    for key in (
        "reply_mode",
        "answer_goal",
        "direct_answer_seed",
        "evidence_brief",
        "reasoning_brief",
        "tone_strategy",
        "answer_outline",
        "must_include_facts",
        "must_avoid_claims",
    ):
        value = response_strategy.get(key)
        if isinstance(value, list) and any(str(item or "").strip() for item in value):
            return True
        if str(value or "").strip():
            return True
    return False


def _strategist_no_tool_delivery_ready(state: AnimaState) -> bool:
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    if _executable_tool_request(strategist_output):
        return False

    operation_plan = state.get("operation_plan", {})
    if not isinstance(operation_plan, dict) or not operation_plan:
        operation_plan = strategist_output.get("operation_plan", {})
    if not isinstance(operation_plan, dict):
        operation_plan = {}

    action_plan = strategist_output.get("action_plan", {})
    if not isinstance(action_plan, dict):
        action_plan = {}
    if str(action_plan.get("required_tool") or "").strip():
        return False

    plan_type = str(operation_plan.get("plan_type") or "").strip()
    if plan_type in {"tool_evidence", "raw_source_analysis", "recent_dialogue_review", "warroom_deliberation"}:
        return False

    response_strategy = state.get("response_strategy", {})
    if not isinstance(response_strategy, dict) or not response_strategy:
        response_strategy = strategist_output.get("response_strategy", {})
    if not _has_delivery_strategy_material(response_strategy):
        return False

    delivery_readiness = str(strategist_output.get("delivery_readiness") or "").strip()
    convergence_state = str(strategist_output.get("convergence_state") or "").strip()
    if delivery_readiness == "deliver_now" or convergence_state == "deliverable":
        return True

    source_lane = str(operation_plan.get("source_lane") or "").strip()
    if plan_type in {"", "direct_delivery"} and source_lane in {"", "none", "direct_dialogue"}:
        facts = response_strategy.get("must_include_facts", [])
        if isinstance(facts, list) and any(str(fact or "").strip() for fact in facts):
            return True
    return False


def route_after_s_thinking(state: AnimaState):
    packet = state.get("s_thinking_packet", {})
    if not isinstance(packet, dict):
        packet = {}
    next_node = str(packet.get("next_node") or "").strip()
    if not next_node:
        routing = packet.get("routing_decision", {})
        if not isinstance(routing, dict):
            routing = {}
        next_node = str(routing.get("next_node") or "").strip()
    if next_node in {"119", "phase_119"}:
        _log("[System] -1s requested phase_119.")
        return "phase_119"
    if next_node == "phase_3":
        _log("[System] -1s allows phase_3 delivery.")
        return "phase_3"
    if next_node in {"-1a", "-1a_thinker", "plan_with_strategist"}:
        if _graph_hard_stop_exceeded(state):
            _log("[System] -1s planning budget exhausted; routing to phase_119.")
            return "phase_119"
        _log("[System] -1s requests -1a planning.")
        return "-1a_thinker"

    # Compatibility fallback for malformed or older start-gate packets while
    # the live path uses ThinkingHandoff.v1 top-level next_node.
    return route_audit_result_v2(state)


def route_after_strategist(state: AnimaState):
    if _graph_hard_stop_exceeded(state):
        _log("[System] Strategist loop budget exhausted; routing to phase_119.")
        return "phase_119"
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    if _executable_tool_request(strategist_output):
        _log("[System] Deprecated -1a tool_request detected; routing to 0_supervisor.")
        return "0_supervisor"
    if _strategist_no_tool_delivery_ready(state):
        _log("[System] -1a supplied a no-tool delivery contract; routing to phase_3.")
        return "phase_3"
    _log("[System] -1a asks phase 0 to select the concrete tool operation.")
    return "0_supervisor"


def route_after_phase3(state: AnimaState):
    return "delivery_review"


def route_after_delivery_review(state: AnimaState):
    review = state.get("delivery_review", {})
    if not isinstance(review, dict):
        review = {}
    verdict = str(review.get("verdict") or "").strip()
    target = str(review.get("remand_target") or "").strip()
    if verdict == "approve":
        return END
    if verdict == "sos_119" or target == "119":
        _log("[System] Delivery review requested phase_119.")
        return "phase_119"
    if verdict == "remand":
        if target == "-1s":
            _log("[System] Delivery review remanded to -1s.")
            return "-1s_start_gate"
        _log("[System] Delivery review remanded to -1a.")
        return "-1a_thinker"

    # Compatibility fallback for callers that still use route_after_phase3
    # before the delivery_review node has run.
    speaker_review = state.get("speaker_review", {})
    if not isinstance(speaker_review, dict):
        speaker_review = {}
    delivery_status = str(state.get("delivery_status") or "").strip().lower()
    if delivery_status == "delivered":
        return END

    should_remand = bool(speaker_review.get("should_remand"))
    loop_count = state.get("loop_count", 0)
    try:
        reasoning_budget = max(int(state.get("reasoning_budget", 1)), 0)
    except (TypeError, ValueError):
        reasoning_budget = 1
    hard_stop = max(reasoning_budget, 1) + 2

    if should_remand and loop_count < hard_stop:
        return "-1a_thinker"
    if should_remand:
        return "phase_119"
    return END


def route_audit_result_v2(state: AnimaState):
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
    readiness = normalize_readiness_decision(
        decision.get("readiness_decision", {}) if isinstance(decision, dict) else state.get("readiness_decision", {})
    )
    readiness_status = str(readiness.get("status") or "").strip()
    readiness_next_hop = str(readiness.get("allowed_next_hop") or "").strip()

    if readiness_status in {"ready_for_direct_answer", "ready_with_current_turn_facts", "ready_with_identity_context"}:
        _log("[System] Readiness allows phase_3 delivery.")
        return "phase_3"
    if readiness_status == "clean_failure":
        if readiness_next_hop == "phase_119":
            _log("[System] Readiness requests phase_119 clean failure preparation.")
            return "phase_119"
        _log("[System] Readiness requests a clean phase_3 failure boundary.")
        return "phase_3"
    if readiness_status == "needs_warroom":
        _log("[System] Readiness requests WarRoom deliberation.")
        return "warroom_deliberator"
    if readiness_status in {"needs_memory_recall", "needs_tool_evidence"}:
        _log("[System] Readiness requests supervised tool evidence.")
        return "0_supervisor"
    if readiness_status == "needs_context_repair":
        _log("[System] Readiness requests direct context repair in phase_3.")
        return "phase_3"
    if readiness_status == "needs_planning":
        if state.get("loop_count", 0) >= hard_stop:
            _log("[System] Readiness planning attempts exceeded the limit; routing to phase_119.")
            return "phase_119"
        if readiness_next_hop == "phase_2a":
            _log("[System] Readiness requests another read/planning pass.")
            return "phase_2a"
        _log("[System] Readiness requests a revised -1a strategy plan.")
        return "-1a_thinker"

    if action == "phase_3":
        _log("[System] -1b passed the turn to phase_3.")
        return "phase_3"
    if action in {"answer_not_ready", "clean_failure"}:
        _log("[System] -1b requested a clean failure boundary in phase_3.")
        return "phase_3"
    if action == "phase_119":
        _log("[System] -1b requested phase_119.")
        return "phase_119"
    if action == "warroom_deliberation":
        _log("[System] -1b requested WarRoom deliberation.")
        return "warroom_deliberator"
    if action in {"internal_reasoning", "plan_more", "plan_with_strategist"} and state.get("loop_count", 0) >= hard_stop:
        _log("[System] Planning retries exceeded the limit; routing to phase_119.")
        return "phase_119"
    if action == "internal_reasoning":
        _log("[System] -1b requested internal critic-advocate reasoning.")
        return "phase_2a"
    if action == "plan_more":
        _log("[System] -1b requested another read/planning pass.")
        return "phase_2a"
    if action == "plan_with_strategist":
        _log("[System] -1b requested a revised -1a strategy plan.")
        return "-1a_thinker"
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


_log("ANIMA graph assembly starting...")

workflow = StateGraph(AnimaState)
workflow.add_node("-1a_thinker", phase_minus_1a_thinker)
workflow.add_node("-1s_start_gate", phase_minus_1s_start_gate)
workflow.add_node("0_supervisor", phase_0_supervisor)
workflow.add_node("phase_1", phase_1_searcher)
workflow.add_node("phase_2a", phase_2a_reader)
workflow.add_node("phase_2", phase_2_analyzer)
workflow.add_node("phase_3", phase_3_validator_with_speaker_guard)
workflow.add_node("delivery_review", phase_delivery_review)
workflow.add_node("phase_119", phase_119_rescue)
workflow.add_node("warroom_deliberator", phase_warroom_deliberator)

workflow.add_edge(START, "-1s_start_gate")
workflow.add_conditional_edges(
    "-1s_start_gate",
    route_after_s_thinking,
    {
        "phase_3": "phase_3",
        "phase_119": "phase_119",
        "-1a_thinker": "-1a_thinker",
    },
)
workflow.add_conditional_edges(
    "-1a_thinker",
    route_after_strategist,
    {
        "0_supervisor": "0_supervisor",
        "phase_3": "phase_3",
        "phase_119": "phase_119",
    },
)
workflow.add_conditional_edges(
    "0_supervisor",
    route_after_supervisor,
    {
        "phase_1": "phase_1",
        "phase_3": "phase_3",
        "phase_119": "phase_119",
        "phase_2a": "phase_2a",
        "-1a_thinker": "-1a_thinker",
        "-1s_start_gate": "-1s_start_gate",
    },
)
workflow.add_edge("phase_1", "phase_2a")
workflow.add_edge("phase_2a", "phase_2")
workflow.add_edge("phase_2", "-1s_start_gate")
workflow.add_edge("warroom_deliberator", "-1s_start_gate")
workflow.add_edge("phase_119", "phase_3")
workflow.add_edge("phase_3", "delivery_review")
workflow.add_conditional_edges(
    "delivery_review",
    route_after_delivery_review,
    {
        "-1a_thinker": "-1a_thinker",
        "-1s_start_gate": "-1s_start_gate",
        "phase_119": "phase_119",
        END: END,
    },
)

compile_kwargs = {}
if os.getenv("ANIMA_ENABLE_CHECKPOINTER", "").strip() == "1" and MemorySaver is not None:
    compile_kwargs["checkpointer"] = MemorySaver()
    _log("ANIMA graph compile using MemorySaver checkpointer.")
elif os.getenv("ANIMA_ENABLE_CHECKPOINTER", "").strip() == "1":
    _log("ANIMA graph checkpointer requested but MemorySaver is unavailable.")

anima_app = workflow.compile(**compile_kwargs)
_log("ANIMA graph compile complete.")
