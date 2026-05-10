"""Phase 2a raw-source reader for the ANIMA field loop.

Phase 2a turns tool/search output, FieldMemo packets, artifact reads, or the
current turn into a raw-read report. It should read and relay source material,
not decide the final answer.
"""

from __future__ import annotations

from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage

from .structured_io import invoke_structured_with_repair


def run_phase_2a_reader(
    state: dict[str, Any],
    *,
    llm_supervisor: Any,
    raw_read_report_schema: Any,
    is_recent_dialogue_review_turn: Callable[[str, str], bool],
    fallback_recent_dialogue_raw_read_report: Callable[[str], dict[str, Any]],
    recent_dialogue_review_failed: Callable[[dict[str, Any]], bool],
    fallback_current_turn_with_recent_context_report: Callable[..., dict[str, Any]],
    execution_trace_after_phase2a: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    field_memo_raw_read_report: Callable[[str], dict[str, Any]],
    artifact_grounded_raw_read_report: Callable[[str], dict[str, Any]],
    phase3_recent_context_excerpt: Callable[..., str],
    fallback_tool_grounded_raw_read_report: Callable[[str], dict[str, Any]],
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Read available raw source material and return a raw-read report."""
    print_fn("[Phase 2a] Reading raw sources end-to-end...")

    search_data = str(state.get("search_results", "") or "")
    if not search_data.strip():
        if is_recent_dialogue_review_turn(state.get("user_input", ""), state.get("recent_context", "")):
            raw_read_report = fallback_recent_dialogue_raw_read_report(state.get("recent_context", ""))
            if recent_dialogue_review_failed(raw_read_report):
                print_fn("  [Phase 2a] recent_dialogue_review_failed | recent raw turn parsing returned no concrete turns")
            else:
                print_fn(f"  [Phase 2a] recent_dialogue_review | raw turns={len(raw_read_report.get('items', []))}")
            return {
                "raw_read_report": raw_read_report,
                "execution_trace": execution_trace_after_phase2a(state, raw_read_report),
            }
        raw_read_report = fallback_current_turn_with_recent_context_report(
            state.get("user_input", ""),
            state.get("recent_context", ""),
        )
        recent_hint_count = max(len(raw_read_report.get("items", [])) - 1, 0)
        print_fn(f"  [Phase 2a] current_turn_only | recent hints={recent_hint_count}")
        return {
            "raw_read_report": raw_read_report,
            "execution_trace": execution_trace_after_phase2a(state, raw_read_report),
        }

    field_memo_fast_path = field_memo_raw_read_report(search_data)
    if field_memo_fast_path.get("items"):
        item_count = len(field_memo_fast_path.get("items", []))
        print_fn(f"  [Phase 2a] field_memo_review | items={item_count}")
        return {
            "raw_read_report": field_memo_fast_path,
            "execution_trace": execution_trace_after_phase2a(state, field_memo_fast_path),
        }

    artifact_fast_path = artifact_grounded_raw_read_report(search_data)
    if artifact_fast_path.get("items"):
        item_count = len(artifact_fast_path.get("items", []))
        print_fn(f"  [Phase 2a] artifact_fast_path | items={item_count}")
        return {
            "raw_read_report": artifact_fast_path,
            "execution_trace": execution_trace_after_phase2a(state, artifact_fast_path),
        }

    sys_prompt = (
        "You are ANIMA phase 2a: the raw-source reader.\n\n"
        "Read the provided raw source from beginning to end and write a raw-read report.\n"
        "Do not judge the final answer yet. Report only what was read, what concrete items were found, and what coverage is still unclear.\n"
        "Write all free-text fields in Korean or plain English, never mojibake.\n\n"
        f"[user_input]\n{state.get('user_input', '')}\n\n"
        f"[recent_context_excerpt]\n{phase3_recent_context_excerpt(state.get('recent_context', ''), max_chars=800) or 'N/A'}\n\n"
        f"[raw_search_results]\n{search_data}\n\n"
        "Rules:\n"
        "1. reviewed_all_input must reflect whether the provided raw input was actually reviewed.\n"
        "2. items should contain source-level observations and direct evidence candidates.\n"
        "3. observed_fact must be grounded in the reviewed source.\n"
        "4. excerpt must be short and traceable to the source.\n"
        "5. source_summary summarizes what was read, not what you infer.\n"
        "6. coverage_notes must state what was sufficient and what remains unclear.\n"
        "7. Do not fake source coverage for tool results that were not present.\n"
    )

    result = invoke_structured_with_repair(
        llm=llm_supervisor,
        schema=raw_read_report_schema,
        messages=[
            SystemMessage(content=sys_prompt),
            HumanMessage(content="Read the provided raw source and produce a raw-read report."),
        ],
        node_name="phase_2a_reader",
        repair_prompt="Return valid RawReadReport JSON only. Do not judge the final answer.",
        max_repairs=1,
    )
    try:
        if not result.ok:
            raise ValueError(result.failure.get("summary", "structured output failed"))
        raw_read_report = result.value
        raw_items = raw_read_report.get("items", []) if isinstance(raw_read_report.get("items"), list) else []
        usable_items = [
            item
            for item in raw_items
            if isinstance(item, dict)
            and (
                str(item.get("observed_fact") or "").strip()
                or str(item.get("excerpt") or "").strip()
            )
        ]
        if not usable_items:
            raw_read_report = fallback_tool_grounded_raw_read_report(search_data)
        item_count = len(raw_read_report.get("items", []))
        print_fn(f"  [Phase 2a] read_mode={raw_read_report.get('read_mode', '')} | items={item_count}")
    except Exception as exc:
        print_fn(f"[Phase 2a] structured output error: {exc}")
        raw_read_report = fallback_tool_grounded_raw_read_report(search_data)
        if not result.ok:
            raw_read_report["structured_failure"] = result.failure

    return {
        "raw_read_report": raw_read_report,
        "execution_trace": execution_trace_after_phase2a(state, raw_read_report),
    }


__all__ = ["run_phase_2a_reader"]
