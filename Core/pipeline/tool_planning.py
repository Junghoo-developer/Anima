"""Tool planning and memory-recall query helpers.

This module validates strategist tool requests and prepares compact recall
queries. It deliberately receives low-level lexical helpers from Core.nodes so
this pass can move the planning body without changing search semantics.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Callable

from langchain_core.messages import SystemMessage

from .contracts import StrategistToolRequest


def _dedupe_keep_order(items):
    seen = set()
    result = []
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def valid_strategist_tool_request(
    tool_request: dict | None,
    *,
    allowed_tool_names: set[str],
    repair_search_tool_request: Callable[[str, dict | None], tuple[str, dict] | None],
):
    if not isinstance(tool_request, dict):
        return None

    if not bool(tool_request.get("should_call_tool")):
        return None

    tool_name = str(tool_request.get("tool_name") or "").strip()
    tool_args = tool_request.get("tool_args", {}) if isinstance(tool_request.get("tool_args"), dict) else {}
    if tool_name not in allowed_tool_names:
        return None

    normalized_args = dict(tool_args)
    if tool_name == "tool_search_field_memos":
        repaired = repair_search_tool_request(tool_name, normalized_args)
        if not repaired:
            return None
        tool_name, normalized_args = repaired
    elif tool_name == "tool_search_memory":
        repaired = repair_search_tool_request(tool_name, normalized_args)
        if not repaired:
            return None
        tool_name, normalized_args = repaired
    elif tool_name == "tool_scroll_chat_log":
        target_id = str(normalized_args.get("target_id") or normalized_args.get("source_id") or "").strip()
        if not target_id:
            return None
        direction = str(normalized_args.get("direction") or "both").strip().lower()
        if direction not in {"past", "future", "both"}:
            direction = "both"
        try:
            limit = int(normalized_args.get("limit", 20) or 20)
        except (TypeError, ValueError):
            limit = 20
        normalized_args = {"target_id": target_id, "direction": direction, "limit": limit}
    elif tool_name == "tool_read_full_diary":
        target_date = str(normalized_args.get("target_date") or normalized_args.get("date") or "").strip()
        if not target_date:
            return None
        normalized_args["target_date"] = target_date
    elif tool_name == "tool_read_artifact":
        artifact_hint = str(normalized_args.get("artifact_hint") or normalized_args.get("path") or "").strip()
        if not artifact_hint:
            return None
        normalized_args["artifact_hint"] = artifact_hint

    return {
        "tool_name": tool_name,
        "tool_args": normalized_args,
        "memo": str(tool_request.get("rationale") or "").strip() or "The strategist supplied an exact tool call for phase 0.",
    }


def tool_request_payload_from_instruction(
    required_tool: str,
    rationale: str = "",
    *,
    build_direct_tool_message: Callable[[str], object | None],
    valid_strategist_tool_request: Callable[[dict | None], dict | None],
):
    direct_message = build_direct_tool_message(str(required_tool or "").strip())
    if direct_message is None:
        return {}
    tool_call = direct_message.tool_calls[0]
    tool_name = str(tool_call.get("name") or "").strip()
    if tool_name in {"tool_pass_to_phase_3", "tool_call_119_rescue"}:
        return {}
    candidate = valid_strategist_tool_request(
        {
            "should_call_tool": True,
            "tool_name": tool_name,
            "tool_args": tool_call.get("args", {}) if isinstance(tool_call.get("args"), dict) else {},
            "rationale": rationale or "action_plan.required_tool supplied an exact phase 0 tool call.",
        }
    )
    if not candidate:
        return {}
    return {
        "should_call_tool": True,
        "tool_name": candidate["tool_name"],
        "tool_args": candidate["tool_args"],
        "rationale": candidate["memo"],
    }


def ensure_tool_request_in_strategist_payload(
    strategist_payload: dict,
    *,
    valid_strategist_tool_request: Callable[[dict | None], dict | None],
    normalize_action_plan: Callable[[dict | None], dict],
    tool_request_payload_from_instruction: Callable[[str, str], dict],
):
    """DEPRECATED: F4 removed -1a tool_request authorship.

    This helper is a no-op stub kept for one-season compatibility. It preserves
    any legacy `tool_request` already present on read-side packets but never
    promotes `action_plan.required_tool` into a new executable tool request.
    """
    del valid_strategist_tool_request, normalize_action_plan, tool_request_payload_from_instruction
    return json.loads(json.dumps(strategist_payload if isinstance(strategist_payload, dict) else {}, ensure_ascii=False))


def decision_from_strategist_tool_contract(
    strategist_output: dict,
    analysis_data: dict | None = None,
    *,
    ensure_tool_request_in_strategist_payload: Callable[[dict], dict],
    valid_strategist_tool_request: Callable[[dict | None], dict | None],
    analysis_has_answer_relevant_evidence: Callable[[dict | None], bool],
    make_auditor_decision: Callable[..., dict],
):
    if not isinstance(strategist_output, dict):
        return None
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    status = str(analysis_data.get("investigation_status") or "").upper()
    if status == "COMPLETED" and analysis_has_answer_relevant_evidence(analysis_data):
        return None

    normalized = ensure_tool_request_in_strategist_payload(strategist_output)
    candidate = valid_strategist_tool_request(normalized.get("tool_request", {}))
    if not candidate:
        return None
    return make_auditor_decision(
        "call_tool",
        memo=candidate.get("memo") or "The strategist supplied a valid executable tool_request.",
        tool_name=candidate["tool_name"],
        tool_args=candidate["tool_args"],
    )


def recent_context_anchor_query(
    recent_context: str,
    working_memory: dict | None = None,
    *,
    extract_recent_raw_turns_from_context: Callable[..., list[dict]],
    extract_search_anchor_terms_from_text: Callable[..., list[str]],
    temporal_context_allows_carry_over: Callable[[dict], bool],
    query_from_anchor_terms: Callable[..., str],
):
    terms = []
    for turn in extract_recent_raw_turns_from_context(recent_context, max_turns=6):
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or "").strip().lower()
        content = str(turn.get("content") or "").strip()
        if role == "user":
            terms.extend(extract_search_anchor_terms_from_text(content, max_terms=8))

    working_memory = working_memory if isinstance(working_memory, dict) else {}
    dialogue_state = working_memory.get("dialogue_state", {})
    if isinstance(dialogue_state, dict) and temporal_context_allows_carry_over(working_memory):
        for key in ("last_user_goal", "current_topic"):
            terms.extend(extract_search_anchor_terms_from_text(dialogue_state.get(key, ""), max_terms=5))

    return query_from_anchor_terms(_dedupe_keep_order(terms), max_chars=60)


def compiled_memory_recall_queries(
    user_input: str,
    recent_context: str = "",
    working_memory: dict | None = None,
    strategist_output: dict | None = None,
    analysis_data: dict | None = None,
    tool_carryover: dict | None = None,
    *,
    is_memory_state_disclosure_turn: Callable[[str], bool],
    looks_like_current_turn_memory_story_share: Callable[[str], bool],
    looks_like_memo_recall_turn: Callable[[str], bool],
    extract_explicit_search_keyword: Callable[[str], str],
    looks_like_deictic_memory_query: Callable[[str], bool],
    deterministic_search_keyword_from_user_input: Callable[[str], str],
    extract_search_anchor_terms_from_text: Callable[..., list[str]],
    query_from_anchor_terms: Callable[..., str],
    recent_context_anchor_query: Callable[[str, dict | None], str],
    temporal_context_allows_carry_over: Callable[[dict], bool],
    clean_strategist_search_fragment: Callable[[str], str],
    normalize_search_keyword: Callable[[str], str],
    search_query_is_overbroad_or_instruction: Callable[[str], bool],
    is_generic_continue_seed: Callable[[str], bool],
    looks_like_generic_non_answer_text: Callable[[str], bool],
    looks_like_fake_tool_or_meta_string: Callable[[str], bool],
):
    del strategist_output, analysis_data
    if is_memory_state_disclosure_turn(user_input):
        return []
    if looks_like_current_turn_memory_story_share(user_input):
        return []
    if (
        not looks_like_memo_recall_turn(user_input)
        and not extract_explicit_search_keyword(user_input)
        and not looks_like_deictic_memory_query(user_input)
    ):
        return []
    working_memory = working_memory if isinstance(working_memory, dict) else {}
    tool_carryover = tool_carryover if isinstance(tool_carryover, dict) else {}
    deictic = looks_like_deictic_memory_query(user_input)

    candidates = []

    explicit = deterministic_search_keyword_from_user_input(user_input)
    if explicit and not deictic:
        candidates.append(explicit)

    current_terms_query = query_from_anchor_terms(
        extract_search_anchor_terms_from_text(user_input, max_terms=8)
    )
    if current_terms_query and not deictic:
        candidates.append(current_terms_query)

    recent_query = recent_context_anchor_query(recent_context, working_memory)
    if recent_query:
        candidates.append(recent_query)

    if temporal_context_allows_carry_over(working_memory):
        for value in (tool_carryover.get("origin_query", ""), tool_carryover.get("last_query", "")):
            cleaned = clean_strategist_search_fragment(value) or normalize_search_keyword(value)
            lowered_cleaned = unicodedata.normalize("NFKC", str(cleaned or "")).lower()
            if (
                cleaned
                and not search_query_is_overbroad_or_instruction(cleaned)
                and not is_generic_continue_seed(cleaned)
                and not looks_like_generic_non_answer_text(cleaned)
                and not any(
                    marker in lowered_cleaned
                    for marker in ["continue previous offer", "go on", "keep going", "continue the thread"]
                )
            ):
                candidates.append(cleaned)

    cleaned_candidates = []
    for candidate in candidates:
        cleaned = clean_strategist_search_fragment(candidate) or normalize_search_keyword(candidate)
        if not cleaned or looks_like_fake_tool_or_meta_string(cleaned):
            continue
        if deictic and unicodedata.normalize("NFKC", cleaned) == unicodedata.normalize("NFKC", str(user_input).strip()):
            continue
        cleaned_candidates.append(cleaned)

    return _dedupe_keep_order(cleaned_candidates)[:3]


def deterministic_strategist_tool_request_from_context(
    user_input: str,
    working_memory: dict | None = None,
    *,
    tool_carryover: dict | None = None,
    is_memory_state_disclosure_turn: Callable[[str], bool],
    looks_like_scroll_followup_turn: Callable[[str], bool],
    tool_carryover_anchor_id: Callable[[dict | None], str],
    scroll_direction_from_user_input: Callable[[str], str],
    deterministic_search_keyword_from_user_input: Callable[[str], str],
):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if is_memory_state_disclosure_turn(text):
        return None
    del working_memory, tool_carryover
    del looks_like_scroll_followup_turn, tool_carryover_anchor_id, scroll_direction_from_user_input

    keyword = deterministic_search_keyword_from_user_input(user_input)
    if keyword:
        return {
            "tool_name": "tool_search_memory",
            "tool_args": {"keyword": keyword},
            "memo": "-1a deterministically compiled the explicit search target into an executable memory search.",
        }

    return None


def strategist_tool_request_from_context(
    user_input: str,
    analysis_data: dict,
    working_memory: dict,
    *,
    recent_context: str = "",
    start_gate_switches: dict | None = None,
    tool_carryover: dict | None = None,
    llm,
    valid_strategist_tool_request: Callable[[dict | None], dict | None],
    is_memory_state_disclosure_turn: Callable[[str], bool],
    looks_like_scroll_followup_turn: Callable[[str], bool],
    tool_carryover_anchor_id: Callable[[dict | None], str],
    scroll_direction_from_user_input: Callable[[str], str],
    compiled_memory_recall_queries: Callable[..., list[str]],
    logger: Callable[[str], None] | None = None,
):
    start_gate_switches = start_gate_switches if isinstance(start_gate_switches, dict) else {}
    tool_carryover = tool_carryover if isinstance(tool_carryover, dict) else {}
    working_memory = working_memory if isinstance(working_memory, dict) else {}
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}

    text = unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()
    if is_memory_state_disclosure_turn(text):
        return None
    wants_scroll = looks_like_scroll_followup_turn(text) or (
        any(token in text for token in ["scroll", "\uc2a4\ud06c\ub864", "\ub354 \ucc3e\uc544", "\uc8fc\ubcc0"])
        and any(token in text for token in ["\uadf8 \uc8fc\uc18c", "\uadf8 \uacb0\uacfc", "\ubc29\uae08 \ucc3e", "\uadf8 \uae30\ub85d", "\uadf8 \ub178\ub4dc", "target_id"])
    )
    if wants_scroll:
        anchor_id = (
            str(tool_carryover.get("origin_source_id") or tool_carryover.get("last_target_id") or "").strip()
            or tool_carryover_anchor_id({"working_memory": working_memory, "tool_carryover": tool_carryover})
        )
        if anchor_id:
            return {
                "tool_name": "tool_scroll_chat_log",
                "tool_args": {
                    "target_id": anchor_id,
                    "direction": scroll_direction_from_user_input(user_input),
                    "limit": 20,
                },
                "memo": "-1a reused ToolCarryoverState as the scroll origin instead of starting a fresh keyword search.",
            }

    sys_prompt = (
        "You are ANIMA -1a's tool-query planner.\n"
        "Your only job is to produce one exact tool call for phase 0, or say no tool is needed.\n"
        "Phase 0 will execute your tool_args exactly as written, so do not leave vague placeholders.\n\n"
        "Important rules:\n"
        "1. Do not answer the user.\n"
        "2. Prefer compact entity/topic queries over full conversational sentences.\n"
        "3. Resolve pronouns using recent context, working memory, and tool carryover only when they clearly help the current goal.\n"
        "4. For FieldMemo recall, prefer topic/entity queries such as `omori sunny protagonist`.\n"
        "5. For explicit broad memory search, use tool_search_memory(keyword=...).\n"
        "6. For recent/local conversation memory, use tool_search_field_memos(query=..., limit=6).\n"
        "7. If tool_carryover has an origin_source_id and the user explicitly wants nearby context, use tool_scroll_chat_log.\n"
        "8. If no grounded tool path is useful, set should_call_tool=false.\n\n"
        f"[user_input]\n{user_input}\n\n"
        f"[recent_context]\n{recent_context}\n\n"
        f"[start_gate_switches]\n{json.dumps(start_gate_switches, ensure_ascii=False, indent=2)}\n\n"
        f"[working_memory]\n{json.dumps(working_memory, ensure_ascii=False, indent=2, default=str)[:4000]}\n\n"
        f"[analysis_report]\n{json.dumps(analysis_data, ensure_ascii=False, indent=2, default=str)[:4000]}\n\n"
        f"[tool_carryover]\n{json.dumps(tool_carryover, ensure_ascii=False, indent=2, default=str)}\n"
    )

    try:
        structured_llm = llm.with_structured_output(StrategistToolRequest)
        res = structured_llm.invoke([SystemMessage(content=sys_prompt)])
        payload = res.model_dump()
        candidate = valid_strategist_tool_request(payload)
        if candidate:
            return candidate
    except Exception as exc:
        if logger:
            logger(f"  [Phase -1a] strategist tool-query planner failed: {exc}")

    recall_contract = start_gate_switches.get("start_gate_turn_contract", {}) if isinstance(start_gate_switches, dict) else {}
    if isinstance(recall_contract, dict) and recall_contract:
        recall_allowed = (
            str(recall_contract.get("user_intent") or "").strip() == "requesting_memory_recall"
            or str(recall_contract.get("answer_mode_preference") or "").strip() == "grounded_recall"
        )
    else:
        recall_allowed = False

    if recall_allowed:
        recall_queries = compiled_memory_recall_queries(
            user_input,
            recent_context=recent_context,
            working_memory=working_memory,
            analysis_data=analysis_data,
            tool_carryover=tool_carryover,
        )
        if recall_queries:
            return {
                "tool_name": "tool_search_field_memos",
                "tool_args": {"query": recall_queries[0], "limit": 8},
                "memo": "-1a fell back to a compact FieldMemo recall query after the LLM planner did not produce a better tool call.",
            }

    return None


__all__ = [
    "compiled_memory_recall_queries",
    "decision_from_strategist_tool_contract",
    "deterministic_strategist_tool_request_from_context",
    "ensure_tool_request_in_strategist_payload",
    "recent_context_anchor_query",
    "strategist_tool_request_from_context",
    "tool_request_payload_from_instruction",
    "valid_strategist_tool_request",
]
