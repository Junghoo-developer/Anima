"""Phase 0 supervisor for the ANIMA field loop.

This module converts an already-approved auditor/strategist instruction into a
safe executable tool call or a control handoff. It should not own intent
classification or evidence judgment.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


def run_phase_0_supervisor(
    state: dict[str, Any],
    *,
    llm_supervisor: Any,
    available_tools: list[Any],
    planned_operation_contract_from_state: Callable[[dict[str, Any]], dict[str, Any]],
    execution_trace_after_supervisor: Callable[[dict[str, Any], str, dict[str, Any] | None], dict[str, Any]],
    build_direct_tool_message: Callable[[str], Any],
    build_supervisor_tool_message: Callable[[str, dict[str, Any], str, dict[str, Any] | None], AIMessage],
    ops_tool_cards: Callable[[], list[dict[str, Any]]],
    ops_node_cards: Callable[[], list[dict[str, Any]]],
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Prepare tool execution from the current auditor instruction."""
    print_fn("[Phase 0] Executing auditor instruction...")
    llm_with_tools = llm_supervisor.bind_tools(available_tools)
    auditor_decision = state.get("auditor_decision", {})
    auditor_instruction = str(state.get("auditor_instruction", "") or "").strip()
    user_input = str(state.get("user_input", "") or "").strip()
    planned_operation_contract = planned_operation_contract_from_state(state)
    base_result = {
        "supervisor_instructions": auditor_instruction,
        "execution_status": "",
        "execution_block_reason": "",
        "execution_trace": execution_trace_after_supervisor(state, "", None),
        "ops_decision": {},
    }

    strategist_output = state.get("strategist_output", {})
    if isinstance(strategist_output, dict):
        tool_request = strategist_output.get("tool_request", {})
        if isinstance(tool_request, dict):
            tool_name = str(tool_request.get("tool_name") or "").strip()
            tool_args = tool_request.get("tool_args", {}) if isinstance(tool_request.get("tool_args"), dict) else {}
            if bool(tool_request.get("should_call_tool")) and tool_name:
                print_fn(f"  [Phase 0] executing strategist tool_request: {tool_name}")
                tool_message = build_supervisor_tool_message(
                    tool_name,
                    tool_args,
                    user_input,
                    planned_operation_contract,
                )
                return {
                    **base_result,
                    "supervisor_instructions": str(tool_request.get("rationale") or "").strip(),
                    "execution_status": "tool_call_ready",
                    "execution_trace": execution_trace_after_supervisor(state, tool_name, tool_args),
                    "messages": [tool_message],
                }

    if isinstance(auditor_decision, dict):
        action = str(auditor_decision.get("action") or "").strip()
        tool_name = str(auditor_decision.get("tool_name") or "").strip()
        tool_args = auditor_decision.get("tool_args", {}) if isinstance(auditor_decision.get("tool_args"), dict) else {}
        if action == "call_tool" and tool_name:
            print_fn(f"  [Phase 0] direct structured tool execution: {tool_name}")
            tool_message = build_supervisor_tool_message(
                tool_name,
                tool_args,
                user_input,
                planned_operation_contract,
            )
            return {
                **base_result,
                "execution_status": "tool_call_ready",
                "execution_trace": execution_trace_after_supervisor(state, tool_name, tool_args),
                "messages": [tool_message],
            }
        if action == "phase_3":
            return {
                **base_result,
                "execution_status": "phase_3_control",
                "messages": [AIMessage(content="", tool_calls=[{"name": "tool_pass_to_phase_3", "args": {}, "id": "auditor_pass"}])],
            }
        if action == "phase_119":
            return {
                **base_result,
                "execution_status": "phase_119_control",
                "messages": [AIMessage(content="", tool_calls=[{"name": "tool_call_119_rescue", "args": {}, "id": "auditor_119"}])],
            }

    direct_message = build_direct_tool_message(auditor_instruction)
    if direct_message is not None:
        direct_tool_name = direct_message.tool_calls[0]["name"]
        direct_tool_args = direct_message.tool_calls[0].get("args", {})
        if not isinstance(direct_tool_args, dict):
            direct_tool_args = {}
        direct_message = build_supervisor_tool_message(
            direct_tool_name,
            direct_tool_args,
            user_input,
            planned_operation_contract,
        )
        print_fn(f"  [Phase 0] direct tool execution from exact instruction: {direct_tool_name}")
        return {
            **base_result,
            "execution_status": "tool_call_ready",
            "execution_trace": execution_trace_after_supervisor(state, direct_tool_name, direct_tool_args),
            "messages": [direct_message],
        }

    if not auditor_instruction:
        print_fn("  [Phase 0] no executable auditor instruction; remanding to -1b")
        return {
            **base_result,
            "execution_status": "blocked",
            "execution_block_reason": "Supervisor received an empty auditor instruction.",
        }

    sys_prompt = (
        "You are ANIMA's active search captain.\n"
        "You are also the 0-supervisor ops hub.\n"
        "Execute the auditor/strategist instruction as an exact safe tool call.\n"
        "Do not rewrite vague search phrases here. If the instruction is not a concrete tool call, return no tool so -1a/-1b can repair it.\n"
        "If the user explicitly gave two alternative search targets and the instruction names both targets, you may emit up to two tool_search_memory calls.\n"
        "Do not reply with normal text.\n\n"
        f"[user_input]\n{user_input}\n\n"
        f"[auditor_instruction]\n{auditor_instruction}\n"
        f"[operation_contract]\n{json.dumps(planned_operation_contract, ensure_ascii=False)}\n"
        f"[ops_tool_cards]\n{json.dumps(ops_tool_cards(), ensure_ascii=False, indent=2)}\n\n"
        f"[ops_node_cards]\n{json.dumps(ops_node_cards(), ensure_ascii=False, indent=2)}\n"
    )

    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content="Return one safe tool call, or up to two tool_search_memory calls if the user gave explicit alternatives."),
    ]

    for attempt in range(3):
        response = llm_with_tools.invoke(messages)
        if response.tool_calls:
            if len(response.tool_calls) == 1:
                tool_call = response.tool_calls[0]
                response = build_supervisor_tool_message(
                    str(tool_call.get("name") or ""),
                    tool_call.get("args", {}) if isinstance(tool_call.get("args"), dict) else {},
                    user_input,
                    planned_operation_contract,
                )
            print_fn(f"  [Phase 0] parsed tool calls={len(response.tool_calls)}")
            return {
                **base_result,
                "execution_status": "tool_call_ready",
                "execution_trace": execution_trace_after_supervisor(
                    state,
                    str(response.tool_calls[0].get("name") or "") if len(response.tool_calls) == 1 else "multi_tool_plan",
                    response.tool_calls[0].get("args", {}) if len(response.tool_calls) == 1 and isinstance(response.tool_calls[0].get("args"), dict) else {},
                ),
                "messages": [response],
            }

        print_fn(f"  [Phase 0] tool-call parsing failed; retrying ({attempt + 1}/3)")
        messages.append(response)
        messages.append(HumanMessage(content="Return one safe tool call, or up to two tool_search_memory calls if the user gave explicit alternatives."))

    print_fn("[Phase 0] supervisor could not create a safe executable plan; remanding to -1b")
    return {
        **base_result,
        "execution_status": "blocked",
        "execution_block_reason": "Supervisor could not convert the auditor instruction into one safe tool call.",
    }


__all__ = ["run_phase_0_supervisor"]
