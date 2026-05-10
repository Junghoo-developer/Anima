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
from .pipeline.thought_critic import phase_2b_thought_critic
from .speaker_guards import phase_3_validator_with_speaker_guard
from .state import AnimaState


def _log(message: str, fallback: str | None = None):
    try:
        print(message)
    except UnicodeEncodeError:
        print(fallback or message)


def route_audit_result(state: AnimaState):
    del state
    _log("[System] Legacy audit route is retired; routing to phase_119.")
    return "phase_119"


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


def _operation_contract_needs_supervisor(action_plan: dict) -> bool:
    """Return True when F4/F4.5 operation intent still needs phase 0 execution."""
    if not isinstance(action_plan, dict):
        return False
    operation_contract = action_plan.get("operation_contract", {})
    if not isinstance(operation_contract, dict):
        return False

    operation_kind = str(operation_contract.get("operation_kind") or "").strip()
    source_lane = str(operation_contract.get("source_lane") or "").strip()
    if operation_kind in {"", "unspecified", "deliver_now"}:
        return False
    if source_lane == "capability_boundary":
        return False
    return operation_kind in {
        "search_new_source",
        "read_same_source_deeper",
        "review_personal_history",
        "extract_feature_summary",
        "compare_with_user_goal",
        "review_recent_dialogue",
    }


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


def _strategist_needs_thought_recursion(state: AnimaState) -> bool:
    """Detect deterministic gate for 2b_thought_critic recursion.

    V4 §1-A.3 (CR1) gate conditions, all AND:
      - has_goal: ``strategist_goal.user_goal_core`` is set (-1a fallback also sets it)
      - no_facts: ``reasoning_board.fact_cells`` is empty (B-2.2 (가) — truly empty case only)
      - no_tool_needed: ``action_plan.required_tool`` empty AND no executable tool_request
        AND no F4/F4.5 operation_contract evidence/read operation

    The gate intentionally **does not** depend on ``delivery_readiness`` because
    that field is an LLM-emitted label (see V4 §1-A.0 — gemma4 false-negative
    concern). Only deterministic data carries the gate; LLM judgment runs in
    the second -1s call after the critique result becomes its input
    differentiator.
    """
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        return False

    strategist_goal = strategist_output.get("strategist_goal", {})
    if not isinstance(strategist_goal, dict):
        strategist_goal = {}
    has_goal = bool(str(strategist_goal.get("user_goal_core") or "").strip())

    reasoning_board = state.get("reasoning_board", {})
    if not isinstance(reasoning_board, dict):
        reasoning_board = {}
    fact_cells = reasoning_board.get("fact_cells", [])
    no_facts = isinstance(fact_cells, list) and len(fact_cells) == 0

    action_plan = strategist_output.get("action_plan", {})
    if not isinstance(action_plan, dict):
        action_plan = {}
    required_tool = str(action_plan.get("required_tool") or "").strip()
    no_tool_needed = (
        not required_tool
        and not _executable_tool_request(strategist_output)
        and not _operation_contract_needs_supervisor(action_plan)
    )

    return has_goal and no_facts and no_tool_needed


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
    if next_node in {"warroom_deliberator", "warroom"}:
        if _graph_hard_stop_exceeded(state):
            _log("[System] -1s planning budget exhausted; routing to phase_119.")
            return "phase_119"
        _log("[System] -1s requests warroom deliberation.")
        return "warroom_deliberator"
    if next_node in {"2b_thought_critic", "thought_critic"}:
        if _graph_hard_stop_exceeded(state):
            _log("[System] -1s planning budget exhausted; routing to phase_119.")
            return "phase_119"
        _log("[System] -1s requests another thought critique.")
        return "2b_thought_critic"

    _log("[System] -1s produced no valid V4 next_node; routing to phase_119.")
    return "phase_119"


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
    if _strategist_needs_thought_recursion(state):
        _log("[System] -1a fallback with no facts; routing to 2b_thought_critic.")
        return "2b_thought_critic"
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
workflow.add_node("2b_thought_critic", phase_2b_thought_critic)

workflow.add_edge(START, "-1s_start_gate")
workflow.add_conditional_edges(
    "-1s_start_gate",
    route_after_s_thinking,
    {
        "phase_3": "phase_3",
        "phase_119": "phase_119",
        "-1a_thinker": "-1a_thinker",
        "warroom_deliberator": "warroom_deliberator",
        "2b_thought_critic": "2b_thought_critic",
    },
)
workflow.add_conditional_edges(
    "-1a_thinker",
    route_after_strategist,
    {
        "0_supervisor": "0_supervisor",
        "phase_3": "phase_3",
        "phase_119": "phase_119",
        "2b_thought_critic": "2b_thought_critic",
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
workflow.add_edge("2b_thought_critic", "-1s_start_gate")
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
