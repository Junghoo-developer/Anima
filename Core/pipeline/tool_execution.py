"""Phase 1 tool execution for the ANIMA field loop.

This module owns the mechanical execution of approved tool calls. It should not
decide user intent or rewrite the plan; planner/auditor nodes remain upstream.
"""

from __future__ import annotations

from typing import Any, Callable

from langchain_core.messages import ToolMessage

from Core.adapters import artifacts, neo4j_memory, night_queries
from Core.evidence_ledger import append_evidence_event
from Core.field_memo import search_field_memos


def _tool_target_from_args(tool_name: str, tool_args: dict[str, Any]) -> str:
    keyword = (
        tool_args.get("keyword")
        or tool_args.get("query")
        or tool_args.get("target_date")
        or tool_args.get("target_id")
        or tool_args.get("artifact_hint")
        or tool_args.get("keyword_z")
        or tool_args.get("dummy_keyword")
        or ""
    )
    if tool_name == "tool_scan_db_schema" and not keyword:
        keyword = "database schema"
    if isinstance(keyword, list):
        return ", ".join(str(item) for item in keyword)
    if not isinstance(keyword, str):
        return str(keyword)
    return keyword


def _tuple_result(value: Any) -> tuple[str, list[str]]:
    if isinstance(value, tuple) and len(value) == 2:
        text, exact_dates = value
        if not isinstance(exact_dates, list):
            exact_dates = []
        return str(text), exact_dates
    return str(value), []


def _execute_tool_call(tool_name: str, tool_args: dict[str, Any]) -> tuple[str, list[str]]:
    if tool_name == "tool_search_field_memos":
        return _tuple_result(
            search_field_memos(
                tool_args.get("query", "") or tool_args.get("keyword", ""),
                tool_args.get("limit", 5),
            )
        )
    if tool_name == "tool_search_memory":
        return _tuple_result(neo4j_memory.search_memory(tool_args.get("keyword", "")))
    if tool_name == "tool_read_full_diary":
        return _tuple_result(neo4j_memory.read_full_source("diary", tool_args.get("target_date", "")))
    if tool_name == "tool_read_artifact":
        return _tuple_result(artifacts.read_artifact(tool_args.get("artifact_hint", "")))
    if tool_name == "tool_scan_db_schema":
        return neo4j_memory.scan_db_schema()[0], []
    if tool_name == "tool_search_dreamhints":
        return _tuple_result(
            night_queries.recall_active_dreamhints(
                tool_args.get("keyword", "") or tool_args.get("query", ""),
                limit=tool_args.get("limit", 5),
            )
        )
    if tool_name == "tool_scroll_chat_log":
        return _tuple_result(
            neo4j_memory.scroll_chat_log(
                tool_args.get("target_id", ""),
                tool_args.get("direction", "both"),
                tool_args.get("limit", 15),
            )
        )
    return f"Unknown tool: {tool_name}", []


def run_phase_1_searcher(
    state: dict[str, Any],
    *,
    stable_action_signature: Callable[[str, dict[str, Any]], str],
    tool_carryover_from_state: Callable[[dict[str, Any] | None], dict[str, Any]],
    update_tool_carryover_after_tool: Callable[
        [dict[str, Any] | None, dict[str, Any] | None, str, dict[str, Any] | None, str, list[str] | None],
        dict[str, Any],
    ],
    extract_local_topology: Callable[[list[str]], str],
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Execute tool calls already selected by supervisor/auditor nodes."""
    print_fn("[Phase 1] Executing tool calls...")

    last_message = state["messages"][-1]
    used_sources = state.get("used_sources", [])
    search_results_text = ""
    tool_messages: list[ToolMessage] = []
    executed_actions = state.get("executed_actions", [])
    tool_result_cache = state.get("tool_result_cache", {})
    if not isinstance(tool_result_cache, dict):
        tool_result_cache = {}
    tool_carryover = tool_carryover_from_state(state)
    evidence_ledger = state.get("evidence_ledger", {})

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            if not isinstance(tool_args, dict):
                tool_args = {}

            keyword = _tool_target_from_args(tool_name, tool_args)
            action_signature = stable_action_signature(tool_name, tool_args)
            was_duplicate = action_signature in executed_actions
            print_fn(f"  [Phase 1] tool={tool_name} | target={keyword}")

            if tool_name in {"tool_pass_to_phase_3", "tool_call_119_rescue"}:
                result_str = "Control tool acknowledged."
                exact_dates: list[str] = []
            elif not keyword.strip():
                result_str = "[system warning] Empty search target detected."
                exact_dates = []
            elif was_duplicate:
                cached_result = tool_result_cache.get(action_signature, {}) if isinstance(tool_result_cache, dict) else {}
                cached_text = str(cached_result.get("result_str") or "").strip() if isinstance(cached_result, dict) else ""
                cached_dates = cached_result.get("exact_dates", []) if isinstance(cached_result, dict) else []
                if cached_text:
                    result_str = cached_text
                    exact_dates = [str(item).strip() for item in cached_dates if str(item).strip()]
                    print_fn("  [Phase 1] duplicate tool call detected -> cached result reused")
                else:
                    tactic_note = night_queries.search_tactics(keyword)
                    result_str = (
                        f"[duplicate warning] '{keyword}' was already searched.\n"
                        f"Use this tactic note before retrying.\n\n{tactic_note}"
                    )
                    exact_dates = []
            else:
                executed_actions.append(action_signature)
                try:
                    result_str, exact_dates = _execute_tool_call(tool_name, tool_args)
                    if exact_dates and tool_name != "tool_read_artifact":
                        extracted_topology = extract_local_topology(exact_dates)
                        result_str = f"[local_topology]\n{extracted_topology}\n\n[source_data]\n{result_str}"
                    tool_result_cache[action_signature] = {
                        "result_str": result_str,
                        "exact_dates": [str(item).strip() for item in exact_dates if str(item).strip()],
                    }
                except Exception as exc:
                    print_fn(f"  [Phase 1] tool error: {exc}")
                    result_str = f"[tool error] Search failed for target '{keyword}'."
                    exact_dates = []

            for source_id in exact_dates:
                if source_id not in used_sources:
                    used_sources.append(source_id)

            tool_carryover = update_tool_carryover_after_tool(
                state,
                tool_carryover,
                tool_name,
                tool_args,
                result_str,
                exact_dates,
            )
            evidence_ledger = append_evidence_event(
                evidence_ledger,
                source_kind="tool_result",
                producer_node="phase_1_searcher",
                source_ref=action_signature,
                timestamp=str(state.get("current_time") or ""),
                content={
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "target": keyword,
                    "result_excerpt": str(result_str or "")[:3000],
                    "source_ids": exact_dates,
                    "duplicate": was_duplicate,
                },
                confidence=0.9 if exact_dates or result_str else 0.5,
            )
            search_results_text += f"[{tool_name} result]\n{result_str}\n\n"
            tool_messages.append(ToolMessage(content=result_str, tool_call_id=tool_call["id"]))

    return {
        "search_results": search_results_text,
        "used_sources": used_sources,
        "executed_actions": executed_actions,
        "tool_result_cache": tool_result_cache,
        "tool_carryover": tool_carryover,
        "evidence_ledger": evidence_ledger,
        "messages": tool_messages,
    }


__all__ = ["run_phase_1_searcher"]
