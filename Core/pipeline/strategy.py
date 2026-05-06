"""Phase -1a strategist for the ANIMA field loop.

The strategist converts the current evidence state into an action plan. It may
propose tool use, WarRoom deliberation, or delivery readiness, but it should not
execute tools or make the final readiness decision.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.messages import AIMessage, SystemMessage

from .packets import (
    compact_analysis_for_prompt,
    compact_reasoning_board_for_prompt,
    compact_raw_read_report_for_prompt,
    compact_s_thinking_packet_for_prompt,
    compact_working_memory_for_prompt,
)
from .plans import normalize_strategist_goal, strategist_goal_from_goal_lock


def _json_clone(value: Any):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return value


def _clip_text(value: Any, limit: int = 1200) -> str:
    text = str(value or "").strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _clip_list(values: Any, limit: int = 8) -> list[Any]:
    if not isinstance(values, list):
        return []
    return values[: max(limit, 0)]


def _clip_string_list(values: Any, limit: int = 8, text_limit: int = 240) -> list[str]:
    return [
        item
        for item in (_clip_text(value, text_limit) for value in _clip_list(values, limit))
        if item
    ]


def _project_analysis_report(analysis_data: Any) -> dict[str, Any]:
    if not isinstance(analysis_data, dict):
        return {}
    return compact_analysis_for_prompt(analysis_data, role="strategist")


def _project_working_memory(working_memory: Any) -> dict[str, Any]:
    if not isinstance(working_memory, dict):
        return {}
    return compact_working_memory_for_prompt(working_memory, role="strategist")


def _project_reasoning_board(board: Any) -> dict[str, Any]:
    if not isinstance(board, dict):
        return {}
    return compact_reasoning_board_for_prompt(board, role="strategist")


def _project_raw_read_report(raw_read_report: Any) -> dict[str, Any]:
    if not isinstance(raw_read_report, dict):
        return {}
    return compact_raw_read_report_for_prompt(
        raw_read_report,
        item_limit=8,
        excerpt_limit=360,
        observed_fact_limit=320,
        known_facts_limit=360,
        item_summary_limit=260,
        source_summary_limit=500,
        coverage_notes_limit=500,
    )


def _project_strategist_goal(source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(source, dict):
        return normalize_strategist_goal({})
    strategist_goal = source.get("strategist_goal", {})
    if isinstance(strategist_goal, dict) and strategist_goal:
        return normalize_strategist_goal(strategist_goal)
    normalized_goal = source.get("normalized_goal", {})
    if isinstance(normalized_goal, dict) and normalized_goal:
        return normalize_strategist_goal(normalized_goal)
    strategist_output = source.get("strategist_output", {})
    if isinstance(strategist_output, dict):
        output_goal = strategist_output.get("strategist_goal", {})
        if isinstance(output_goal, dict) and output_goal:
            return normalize_strategist_goal(output_goal)
        normalized_goal_alias = strategist_output.get("normalized_goal", {})
        if isinstance(normalized_goal_alias, dict) and normalized_goal_alias:
            return normalize_strategist_goal(normalized_goal_alias)
        goal_lock = strategist_output.get("goal_lock", {})
        if isinstance(goal_lock, dict) and goal_lock:
            return strategist_goal_from_goal_lock(goal_lock)
    return normalize_strategist_goal({})


def project_state_for_strategist(state: dict[str, Any]) -> dict[str, Any]:
    """Return the bounded prompt surface that -1a is allowed to inspect."""
    source = state if isinstance(state, dict) else {}
    return {
        "user_input": _clip_text(source.get("user_input"), 1600),
        "recent_context": _clip_text(source.get("recent_context"), 3200),
        "user_state": _clip_text(source.get("user_state"), 700),
        "user_char": _clip_text(source.get("user_char"), 700),
        "songryeon_thoughts": _clip_text(source.get("songryeon_thoughts"), 900),
        "tactical_briefing": _clip_text(source.get("tactical_briefing"), 900),
        "biolink_status": _clip_text(source.get("biolink_status"), 500),
        "time_gap": source.get("time_gap", 0),
        "global_tolerance": source.get("global_tolerance", 1.0),
        "self_correction_memo": _clip_text(source.get("self_correction_memo"), 700),
        "strategist_goal": _project_strategist_goal(source),
        "working_memory": _project_working_memory(source.get("working_memory", {})),
        "raw_read_report": _project_raw_read_report(source.get("raw_read_report", {})),
        "analysis_report": _project_analysis_report(source.get("analysis_report", {})),
        "reasoning_board": _project_reasoning_board(source.get("reasoning_board", {})),
        "war_room": _json_clone(source.get("war_room", {})) if isinstance(source.get("war_room", {}), dict) else {},
        "start_gate_review": _json_clone(source.get("start_gate_review", {})) if isinstance(source.get("start_gate_review", {}), dict) else {},
        "start_gate_switches": _json_clone(source.get("start_gate_switches", {})) if isinstance(source.get("start_gate_switches", {}), dict) else {},
        "s_thinking_packet": compact_s_thinking_packet_for_prompt(source.get("s_thinking_packet", {}), role="strategist")
        if isinstance(source.get("s_thinking_packet", {}), dict)
        else {},
        "tool_carryover": _json_clone(source.get("tool_carryover", {})) if isinstance(source.get("tool_carryover", {}), dict) else {},
        "evidence_ledger": _json_clone(source.get("evidence_ledger", {})) if isinstance(source.get("evidence_ledger", {}), dict) else {},
    }


def run_base_phase_minus_1a_thinker(
    state: dict[str, Any],
    *,
    llm: Any,
    strategist_reasoning_output_schema: Any,
    build_phase_minus_1a_prompt: Callable[..., str],
    build_reasoning_board_from_analysis: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    normalize_war_room_state: Callable[[dict[str, Any]], dict[str, Any]],
    analysis_packet_for_prompt: Callable[..., dict[str, Any]],
    working_memory_packet_for_prompt: Callable[[dict[str, Any]], dict[str, Any]],
    reasoning_board_packet_for_prompt: Callable[..., dict[str, Any]],
    raw_read_report_packet_for_prompt: Callable[[dict[str, Any]], dict[str, Any]],
    war_room_packet_for_prompt: Callable[[dict[str, Any]], dict[str, Any]],
    answer_mode_policy_from_state: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    answer_mode_policy_packet_for_prompt: Callable[[dict[str, Any]], str],
    evidence_ledger_for_prompt: Callable[[dict[str, Any]], str],
    fallback_strategist_output: Callable[..., tuple[dict[str, Any], dict[str, Any]]],
    force_findings_first_delivery_strategy: Callable[[dict[str, Any], dict[str, Any], str], dict[str, Any]],
    war_room_after_advocate: Callable[[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]],
    sanitize_strategist_goal_fields: Callable[[dict[str, Any], str, dict[str, Any]], dict[str, Any]],
    ensure_tool_request_in_strategist_payload: Callable[[dict[str, Any]], dict[str, Any]],
    apply_strategist_output_to_reasoning_board: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Build the base -1a strategist plan from available evidence."""
    print_fn("[Phase -1a] Building action plan from available evidence...")

    projected_state = project_state_for_strategist(state)
    user_input = projected_state["user_input"]
    analysis_data = projected_state.get("analysis_report", {})
    status = str(analysis_data.get("investigation_status") or "").upper()
    evidences = analysis_data.get("evidences", []) if isinstance(analysis_data, dict) else []
    reasoning_board = projected_state.get("reasoning_board", {})
    if not isinstance(reasoning_board, dict) or not reasoning_board:
        reasoning_board = build_reasoning_board_from_analysis(projected_state, analysis_data)

    recent_context = projected_state.get("recent_context", "")
    songryeon_thoughts = projected_state.get("songryeon_thoughts", "")
    tactical_briefing = projected_state.get("tactical_briefing", "")
    user_state = projected_state.get("user_state", "")
    user_char = projected_state.get("user_char", "")
    bio_status = projected_state.get("biolink_status", "")
    time_gap = projected_state.get("time_gap", 0)
    tolerance = projected_state.get("global_tolerance", 1.0)
    auditor_memo = projected_state.get("self_correction_memo", "")
    working_memory = projected_state.get("working_memory", {})
    raw_read_report = projected_state.get("raw_read_report", {})
    war_room = normalize_war_room_state(projected_state.get("war_room", {}))
    analysis_packet = analysis_packet_for_prompt(analysis_data, include_thought=True, role="strategist")
    working_memory_packet = working_memory_packet_for_prompt(working_memory, role="strategist")
    reasoning_board_packet = reasoning_board_packet_for_prompt(reasoning_board, approved_only=False, role="strategist")
    raw_read_packet = raw_read_report_packet_for_prompt(raw_read_report)
    war_room_packet = war_room_packet_for_prompt(war_room)
    start_gate_review_packet = json.dumps(projected_state.get("start_gate_review", {}), ensure_ascii=False, indent=2)
    s_thinking_packet = json.dumps(projected_state.get("s_thinking_packet", {}), ensure_ascii=False, indent=2)
    strategist_goal_packet = json.dumps(projected_state.get("strategist_goal", {}), ensure_ascii=False, indent=2)
    tool_carryover_packet = json.dumps(projected_state.get("tool_carryover", {}), ensure_ascii=False, indent=2)
    answer_mode_policy = answer_mode_policy_from_state(projected_state, analysis_data)
    answer_mode_policy_packet = answer_mode_policy_packet_for_prompt(answer_mode_policy)
    evidence_ledger_packet = evidence_ledger_for_prompt(projected_state.get("evidence_ledger", {}))

    if not evidences and status in {"", "INCOMPLETE"}:
        print_fn("  [Phase -1a] Evidence is thin; using fallback planner.")
        strategist_output, reasoning_board = fallback_strategist_output(
            user_input,
            analysis_data,
            working_memory,
            reasoning_board,
            recent_context=recent_context,
            start_gate_switches=projected_state.get("start_gate_switches", {}),
            tool_carryover=projected_state.get("tool_carryover", {}),
        )
        response_strategy = strategist_output.get("response_strategy", {})
        if not isinstance(response_strategy, dict):
            response_strategy = {}
        response_strategy = force_findings_first_delivery_strategy(response_strategy, analysis_data, user_input)
        strategist_output["response_strategy"] = response_strategy
        war_room = war_room_after_advocate(war_room, analysis_data, strategist_output, reasoning_board)
        print_fn(f"  [Phase -1a] current_step_goal={strategist_output.get('action_plan', {}).get('current_step_goal', '')[:120]}")
        print_fn(f"  [Phase -1a] candidate_pairs={len(reasoning_board.get('candidate_pairs', []))}")
        return {
            "strategist_output": strategist_output,
            "response_strategy": {},
            "reasoning_board": reasoning_board,
            "war_room": war_room,
            "thought_logs": [],
        }

    sys_prompt = build_phase_minus_1a_prompt(
        user_input=user_input,
        recent_context=recent_context,
        answer_mode_policy_packet=answer_mode_policy_packet,
        user_state=user_state,
        user_char=user_char,
        time_gap=time_gap,
        tolerance=tolerance,
        bio_status=bio_status,
        songryeon_thoughts=songryeon_thoughts,
        tactical_briefing=tactical_briefing,
        working_memory_packet=working_memory_packet,
        tool_carryover_packet=tool_carryover_packet,
        s_thinking_packet=s_thinking_packet,
        strategist_goal_packet=strategist_goal_packet,
        start_gate_review_packet=start_gate_review_packet,
        reasoning_board_packet=reasoning_board_packet,
        auditor_memo=auditor_memo,
        analysis_packet=analysis_packet,
        raw_read_packet=raw_read_packet,
        war_room_packet=war_room_packet,
        evidence_ledger_packet=evidence_ledger_packet,
    )

    structured_llm = llm.with_structured_output(strategist_reasoning_output_schema)
    try:
        res = structured_llm.invoke([SystemMessage(content=sys_prompt)])
        strategist_payload = res.model_dump()
        strategist_payload["answer_mode_policy"] = answer_mode_policy
        response_strategy = strategist_payload.get("response_strategy", {})
        if not isinstance(response_strategy, dict):
            response_strategy = {}
        strategist_payload["response_strategy"] = response_strategy
        response_strategy = strategist_payload.get("response_strategy", {})
        if not isinstance(response_strategy, dict):
            response_strategy = {}
        response_strategy = force_findings_first_delivery_strategy(response_strategy, analysis_data, user_input)
        strategist_payload["response_strategy"] = response_strategy
        strategist_payload = sanitize_strategist_goal_fields(
            strategist_payload,
            user_input,
            projected_state.get("start_gate_switches", {}),
        )
        strategist_payload = ensure_tool_request_in_strategist_payload(strategist_payload)
        reasoning_board = apply_strategist_output_to_reasoning_board(reasoning_board, strategist_payload)
        print_fn(f"  [Phase -1a] current_step_goal={strategist_payload.get('action_plan', {}).get('current_step_goal', '')[:120]}")
        print_fn(f"  [Phase -1a] candidate_pairs={len(reasoning_board.get('candidate_pairs', []))}")
    except Exception as exc:
        print_fn(f"[Phase -1a] structured output error: {exc}")
        strategist_payload, reasoning_board = fallback_strategist_output(
            user_input,
            analysis_data,
            working_memory,
            reasoning_board,
            recent_context=recent_context,
            start_gate_switches=projected_state.get("start_gate_switches", {}),
            tool_carryover=projected_state.get("tool_carryover", {}),
        )
        strategist_payload["answer_mode_policy"] = answer_mode_policy
        response_strategy = strategist_payload.get("response_strategy", {})
        if not isinstance(response_strategy, dict):
            response_strategy = {}
        response_strategy = force_findings_first_delivery_strategy(response_strategy, analysis_data, user_input)
        strategist_payload["response_strategy"] = response_strategy
        strategist_payload = sanitize_strategist_goal_fields(
            strategist_payload,
            user_input,
            projected_state.get("start_gate_switches", {}),
        )
        strategist_payload = ensure_tool_request_in_strategist_payload(strategist_payload)

    war_room = war_room_after_advocate(war_room, analysis_data, strategist_payload, reasoning_board)
    return {
        "strategist_output": strategist_payload,
        "response_strategy": response_strategy,
        "reasoning_board": reasoning_board,
        "war_room": war_room,
        "thought_logs": [],
    }


def run_phase_minus_1a_thinker(
    state: dict[str, Any],
    *,
    previous_phase_minus_1a_thinker: Callable[[dict[str, Any]], dict[str, Any]],
    ensure_tool_request_in_strategist_payload: Callable[[dict[str, Any]], dict[str, Any]],
    build_strategist_objection_packet: Callable[[dict[str, Any], dict[str, Any], str], dict[str, Any]],
    normalize_operation_plan: Callable[[dict[str, Any]], dict[str, Any]],
    attach_ledger_event: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Apply public -1a wrapper duties around the base strategist pass."""
    result = previous_phase_minus_1a_thinker(state)
    strategist_output = result.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    analysis_data = state.get("analysis_report", {})
    if not isinstance(analysis_data, dict):
        analysis_data = {}

    response_strategy = strategist_output.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}

    reasoning_board = result.get("reasoning_board", state.get("reasoning_board", {}))
    if not isinstance(reasoning_board, dict):
        reasoning_board = {}

    strategist_output = ensure_tool_request_in_strategist_payload(strategist_output)
    strategist_objection_packet = build_strategist_objection_packet(
        strategist_output,
        analysis_data,
        state.get("user_input", ""),
    )

    result["strategist_output"] = strategist_output
    strategist_output = result["strategist_output"]
    result["operation_plan"] = normalize_operation_plan(strategist_output.get("operation_plan", {}))
    strategist_goal = normalize_strategist_goal(
        strategist_output.get("strategist_goal")
        or strategist_output.get("normalized_goal")
        or result.get("strategist_goal")
        or result.get("normalized_goal")
        or strategist_goal_from_goal_lock(strategist_output.get("goal_lock", {}))
    )
    result["strategist_goal"] = strategist_goal
    result["normalized_goal"] = strategist_goal
    result["response_strategy"] = response_strategy
    result["reasoning_board"] = reasoning_board
    result["strategist_objection_packet"] = strategist_objection_packet
    return attach_ledger_event(
        result,
        state,
        source_kind="strategist_plan",
        producer_node="-1a_thinker",
        source_ref=str(strategist_output.get("delivery_readiness") or "plan"),
        content={
            "operation_plan": result["operation_plan"],
            "strategist_goal": strategist_goal,
            "action_plan": strategist_output.get("action_plan", {}),
            "delivery_readiness": strategist_output.get("delivery_readiness", ""),
        },
        confidence=0.75,
    )


__all__ = [
    "project_state_for_strategist",
    "run_base_phase_minus_1a_thinker",
    "run_phase_minus_1a_thinker",
]
