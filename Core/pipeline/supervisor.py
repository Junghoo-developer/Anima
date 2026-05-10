"""Phase 0 supervisor for the ANIMA field loop.

This module converts an already-approved auditor/strategist instruction into a
safe executable tool call or a control handoff. It should not own intent
classification or evidence judgment.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .packets import _compact_fact_cells_for_prompt
from .structured_io import (
    structured_failure_packet,
    validate_operation_contract_payload,
    validate_supervisor_tool_calls,
)


def _clip_text(value: Any, limit: int = 320) -> str:
    text = str(value or "").strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _clip_string_list(values: Any, *, limit: int = 8, text_limit: int = 180) -> list[str]:
    if not isinstance(values, list):
        return []
    items: list[str] = []
    for value in values:
        text = _clip_text(value, text_limit)
        if text:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def _fact_cells_for_supervisor_prompt(state: dict[str, Any]) -> list[dict[str, Any]]:
    board = state.get("reasoning_board", {})
    if not isinstance(board, dict):
        board = {}
    return _compact_fact_cells_for_prompt(board.get("fact_cells", []), limit=10)


def _s_thinking_missing_for_supervisor_prompt(state: dict[str, Any]) -> list[str]:
    packet = state.get("s_thinking_packet", {})
    if not isinstance(packet, dict):
        return []
    missing = packet.get("what_is_missing", [])
    if not isinstance(missing, list) or not missing:
        loop_summary = packet.get("loop_summary", {})
        if not isinstance(loop_summary, dict):
            loop_summary = {}
        legacy_missing = loop_summary.get("gaps", [])
        if isinstance(legacy_missing, list) and legacy_missing:
            missing = legacy_missing
    return _clip_string_list(missing, limit=8, text_limit=180)


def _extract_exact_date(value: Any) -> str:
    text = str(value or "")
    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso_match:
        return "-".join(iso_match.groups())

    spaced_match = re.search(r"\b(\d{4})\s+(\d{1,2})\s+(\d{1,2})\b", text)
    if spaced_match:
        year, month, day = spaced_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    korean_match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if korean_match:
        year, month, day = korean_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return ""


def _operation_contract_tool_message(
    *,
    user_input: str,
    operation_contract: dict[str, Any],
    build_supervisor_tool_message: Callable[[str, dict[str, Any], str, dict[str, Any] | None], AIMessage],
) -> AIMessage | None:
    if not isinstance(operation_contract, dict):
        return None

    operation_kind = str(operation_contract.get("operation_kind") or "").strip()
    source_lane = str(operation_contract.get("source_lane") or "").strip()
    if operation_kind not in {"search_new_source", "read_same_source_deeper", "review_personal_history"}:
        return None

    seed_parts = [
        user_input,
        operation_contract.get("target_scope", ""),
        operation_contract.get("source_lane", ""),
        operation_contract.get("search_subject", ""),
        operation_contract.get("missing_slot", ""),
        operation_contract.get("evidence_boundary", ""),
        operation_contract.get("query_variant", ""),
        *(
            operation_contract.get("retrieval_key_candidates", [])
            if isinstance(operation_contract.get("retrieval_key_candidates", []), list)
            else []
        ),
        *(
            operation_contract.get("source_title_candidates", [])
            if isinstance(operation_contract.get("source_title_candidates", []), list)
            else []
        ),
        *(
            operation_contract.get("query_seed_candidates", [])
            if isinstance(operation_contract.get("query_seed_candidates", []), list)
            else []
        ),
    ]
    search_blob = "\n".join(str(part or "") for part in seed_parts)
    exact_date = _extract_exact_date(search_blob)
    diary_requested = source_lane == "diary" or any(token in search_blob.lower() for token in ("diary", "일기"))
    if exact_date and diary_requested:
        return build_supervisor_tool_message(
            "tool_read_full_diary",
            {"target_date": exact_date},
            user_input,
            operation_contract,
        )
    return None


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
    available_tool_names = [str(getattr(tool, "name", "") or "").strip() for tool in available_tools]
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

    contract_message = _operation_contract_tool_message(
        user_input=user_input,
        operation_contract=planned_operation_contract,
        build_supervisor_tool_message=build_supervisor_tool_message,
    )
    if contract_message is not None:
        tool_name = str(contract_message.tool_calls[0].get("name") or "")
        tool_args = contract_message.tool_calls[0].get("args", {})
        if not isinstance(tool_args, dict):
            tool_args = {}
        print_fn(f"  [Phase 0] deterministic tool execution from operation_contract: {tool_name}")
        return {
            **base_result,
            "execution_status": "tool_call_ready",
            "execution_trace": execution_trace_after_supervisor(state, tool_name, tool_args),
            "messages": [contract_message],
        }

    planned_operation_contract, contract_failure = validate_operation_contract_payload(planned_operation_contract)
    if contract_failure:
        print_fn(
            "  [Phase 0] blocked invalid operation_contract payload: "
            f"{contract_failure.get('summary', '')}"
        )
        return {
            **base_result,
            "execution_status": "blocked",
            "execution_block_reason": "operation_contract_payload_invalid",
            "structured_failure": {
                **contract_failure,
                "node": "0_supervisor",
            },
        }

    fact_cells = _fact_cells_for_supervisor_prompt(state)
    what_is_missing = _s_thinking_missing_for_supervisor_prompt(state)

    sys_prompt = (
        "You are ANIMA's 0_supervisor: the ops layer that converts the strategist's operation_contract into one exact safe tool call.\n"
        "Authority: choose a safe tool name, arguments, and search query from the operation contract and available tool cards.\n"
        "Use operation_contract.source_lane, retrieval_key_candidates, source_title_candidates, query_seed_candidates, search_subject, missing_slot, and evidence_boundary as the primary search axis.\n"
        "retrieval_key_candidates/source_title_candidates/query_seed_candidates are non-executable seeds: convert one compact seed into safe tool args only when a tool is actually useful.\n"
        "Prefer retrieval_key_candidates and source_title_candidates over broad search_subject prose when building search args.\n"
        "If source_lane=capability_boundary, do not search just to answer access/capability; return no tool_calls unless the user explicitly asks to retrieve now.\n"
        "If the user explicitly gave two alternative search targets and the instruction names both targets, you may emit up to two tool_search_memory calls.\n"
        "If no tool would help, return no tool_calls so the graph can remand for review.\n"
        "Forbidden: do not write final-answer text, change answer_mode, re-judge facts, or invent fact_ids.\n\n"
        f"[user_input]\n{user_input}\n\n"
        f"[operation_contract]\n{json.dumps(planned_operation_contract, ensure_ascii=False)}\n"
        f"[fact_cells]\n{json.dumps(fact_cells, ensure_ascii=False, indent=2)}\n"
        f"[s_thinking_packet_what_is_missing]\n{json.dumps(what_is_missing, ensure_ascii=False, indent=2)}\n"
        f"[auditor_instruction]\n{auditor_instruction}\n"
        f"[ops_tool_cards]\n{json.dumps(ops_tool_cards(), ensure_ascii=False, indent=2)}\n\n"
        f"[ops_node_cards]\n{json.dumps(ops_node_cards(), ensure_ascii=False, indent=2)}\n"
    )

    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content="Return one safe tool call, or up to two tool_search_memory calls if the user gave explicit alternatives."),
    ]

    for attempt in range(3):
        response = llm_with_tools.invoke(messages)
        tool_calls = getattr(response, "tool_calls", []) or []
        if tool_calls:
            tool_calls, validation_failure = validate_supervisor_tool_calls(tool_calls, available_tool_names)
            if validation_failure:
                print_fn(f"  [Phase 0] invalid tool call; retrying ({attempt + 1}/3): {validation_failure.get('summary', '')}")
                messages.append(response)
                messages.append(HumanMessage(content="Return only valid available tool calls from ops_tool_cards, with dict args."))
                continue
            if len(tool_calls) == 1:
                tool_call = tool_calls[0]
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

        content = str(getattr(response, "content", "") or "").strip()
        if content:
            print_fn(f"  [Phase 0] non-tool text returned; retrying ({attempt + 1}/3)")
            messages.append(response)
            messages.append(HumanMessage(content="Do not write answer text. Return a safe tool call or no content/no tool_calls."))
            continue

        print_fn(f"  [Phase 0] tool-call parsing failed; retrying ({attempt + 1}/3)")
        if hasattr(response, "content"):
            messages.append(response)
        messages.append(HumanMessage(content="Return one safe tool call, or up to two tool_search_memory calls if the user gave explicit alternatives."))

    print_fn("[Phase 0] supervisor could not create a safe executable plan; remanding to -1b")
    return {
        **base_result,
        "execution_status": "blocked",
        "execution_block_reason": "Supervisor could not convert the auditor instruction into one safe tool call.",
        "structured_failure": structured_failure_packet(
            node="0_supervisor",
            reason_type="validation_error",
            summary="Supervisor could not produce valid tool_calls after retries.",
        ),
    }


__all__ = ["run_phase_0_supervisor"]
