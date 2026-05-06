"""Phase 119 clean rescue path for the ANIMA field loop.

Phase 119 compresses a failed retrieval/search path into a rescue handoff
packet for phase 3. It must not turn rejected sources into answer evidence,
but it also must not discard facts that phase 2b already accepted.
"""

from __future__ import annotations

from typing import Any, Callable


RESCUE_HANDOFF_SCHEMA = "RescueHandoffPacket.v1"
RESCUE_USER_FACING_LABELS = {
    "검색 결과 부족",
    "기억 못 찾음",
    "질문이 모호함",
    "재시도 필요",
}


def _compact_text(value: Any, limit: int = 260) -> str:
    text = " ".join(str(value or "").split()).strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _dedupe_strings(items: list[Any], *, limit: int = 8, text_limit: int = 260) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items or []:
        text = _compact_text(item, text_limit)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _source_key(value: Any) -> str:
    return str(value or "").strip()


def _rejected_source_ids(rejected_sources: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for item in rejected_sources or []:
        if not isinstance(item, dict):
            continue
        for key in ("source_id", "memo_id", "id"):
            value = _source_key(item.get(key))
            if value:
                ids.add(value)
    return ids


def _evidence_fact_text(item: dict[str, Any]) -> str:
    return _compact_text(
        item.get("extracted_fact")
        or item.get("observed_fact")
        or item.get("fact")
        or item.get("excerpt")
        or "",
        260,
    )


def _normalize_preserved_evidence_item(
    item: dict[str, Any],
    *,
    source_id: str = "",
    source_type: str = "",
) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    fact = _evidence_fact_text(item)
    if not fact:
        return None
    normalized_source_id = _source_key(source_id or item.get("source_id") or item.get("memo_id") or item.get("id"))
    normalized_source_type = _compact_text(
        source_type or item.get("source_type") or item.get("memo_kind") or "source",
        80,
    )
    return {
        "source_id": normalized_source_id,
        "source_type": normalized_source_type or "source",
        "extracted_fact": fact,
    }


def _phase119_preserved_evidences(
    analysis_data: dict[str, Any],
    rejected_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    rejected_ids = _rejected_source_ids(rejected_sources)
    preserved: list[dict[str, Any]] = []

    for item in analysis_data.get("evidences", []) or []:
        if not isinstance(item, dict):
            continue
        source_id = _source_key(item.get("source_id") or item.get("memo_id") or item.get("id"))
        if source_id and source_id in rejected_ids:
            continue
        normalized = _normalize_preserved_evidence_item(item)
        if normalized:
            preserved.append(normalized)

    for judgment in analysis_data.get("source_judgments", []) or []:
        if not isinstance(judgment, dict):
            continue
        source_id = _source_key(judgment.get("source_id") or judgment.get("memo_id"))
        source_type = _compact_text(judgment.get("source_type") or "source", 80)
        for fact in judgment.get("accepted_facts", []) or []:
            normalized = _normalize_preserved_evidence_item(
                {"source_id": source_id, "source_type": source_type, "extracted_fact": fact},
                source_id=source_id,
                source_type=source_type,
            )
            if normalized:
                preserved.append(normalized)

    seen = set()
    deduped: list[dict[str, Any]] = []
    for item in preserved:
        key = (
            _source_key(item.get("source_id")),
            _compact_text(item.get("extracted_fact"), 260),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= 8:
            break
    return deduped


def _phase119_preserved_field_memo_facts(analysis_data: dict[str, Any]) -> list[str]:
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    facts: list[Any] = []
    facts.extend(analysis_data.get("usable_field_memo_facts", []) or [])
    for judgment in analysis_data.get("field_memo_judgments", []) or []:
        if not isinstance(judgment, dict) or not judgment.get("usable_for_current_goal"):
            continue
        facts.extend(judgment.get("accepted_facts", []) or [])
    return _dedupe_strings(facts, limit=8, text_limit=260)


def _phase119_attempted_path(state: dict[str, Any]) -> list[str]:
    state = state if isinstance(state, dict) else {}
    attempted: list[Any] = []
    executed_actions = state.get("executed_actions", [])
    if isinstance(executed_actions, list):
        attempted.extend(executed_actions[-8:])
    execution_trace = state.get("execution_trace", {})
    if isinstance(execution_trace, dict):
        for key in ("executed_tool", "operation_kind", "read_focus", "analysis_focus"):
            value = _compact_text(execution_trace.get(key), 120)
            if value:
                attempted.append(f"{key}: {value}")
    ledger = state.get("evidence_ledger", {})
    events = ledger.get("events", []) if isinstance(ledger, dict) else []
    if isinstance(events, list):
        for event in events[-8:]:
            if not isinstance(event, dict):
                continue
            bits = [
                _compact_text(event.get("producer_node"), 80),
                _compact_text(event.get("source_kind"), 80),
                _compact_text(event.get("source_ref"), 120),
            ]
            text = " / ".join(bit for bit in bits if bit)
            if text:
                attempted.append(text)
    return _dedupe_strings(attempted, limit=12, text_limit=180)


def _phase119_trigger(state: dict[str, Any]) -> str:
    state = state if isinstance(state, dict) else {}
    delivery_review = state.get("delivery_review", {})
    if isinstance(delivery_review, dict):
        verdict = str(delivery_review.get("verdict") or "").strip()
        target = str(delivery_review.get("remand_target") or "").strip()
        if verdict == "sos_119" or target == "119":
            return "delivery_loop"
    s_packet = state.get("s_thinking_packet", {})
    routing = s_packet.get("routing_decision", {}) if isinstance(s_packet, dict) else {}
    if isinstance(routing, dict) and str(routing.get("next_node") or "").strip() == "119":
        return "s_sos"
    return "budget_exceeded"


def _phase119_user_facing_label(
    state: dict[str, Any],
    analysis_data: dict[str, Any],
    *,
    what_we_know: list[str],
    what_we_failed: list[str],
    rejected_only: list[dict[str, Any]],
) -> str:
    """Select a code-owned enum label for phase_3 to naturalize later."""
    state = state if isinstance(state, dict) else {}
    raw_read_report = state.get("raw_read_report", {})
    raw_read_report = raw_read_report if isinstance(raw_read_report, dict) else {}
    operation_plan = state.get("operation_plan", {})
    operation_plan = operation_plan if isinstance(operation_plan, dict) else {}
    read_mode = str(raw_read_report.get("read_mode") or "").strip()
    source_lane = str(operation_plan.get("source_lane") or "").strip()
    rejected_types = {
        str(item.get("source_type") or "").strip()
        for item in rejected_only or []
        if isinstance(item, dict)
    }
    if read_mode == "field_memo_review" or source_lane in {"field_memo_review", "memory_search"} or "field_memo" in rejected_types:
        return "기억 못 찾음"
    failed_text = " ".join(str(item or "") for item in what_we_failed).lower()
    if not rejected_only and not what_we_know:
        return "질문이 모호함"
    if "ambiguous" in failed_text or "unclear" in failed_text or "모호" in failed_text:
        return "질문이 모호함"
    if what_we_know:
        return "재시도 필요"
    return "검색 결과 부족"


def build_rescue_handoff_packet(
    state: dict[str, Any],
    *,
    analysis_data: dict[str, Any],
    rejected_only: list[dict[str, Any]],
    missing_slots: list[str],
    compact_user_facing_summary: Callable[[Any, int], str],
) -> dict[str, Any]:
    preserved_evidences = _phase119_preserved_evidences(analysis_data, rejected_only)
    preserved_field_memo_facts = _phase119_preserved_field_memo_facts(analysis_data)
    known_from_evidence = [
        item.get("extracted_fact", "")
        for item in preserved_evidences
        if isinstance(item, dict) and str(item.get("extracted_fact") or "").strip()
    ]
    what_we_know = _dedupe_strings(
        [*known_from_evidence, *preserved_field_memo_facts],
        limit=8,
        text_limit=260,
    )
    what_we_failed = _dedupe_strings(
        missing_slots or ["usable evidence for the current answer"],
        limit=5,
        text_limit=180,
    )
    tone_hint = "사과 + 부분정보" if what_we_know else "단순 모르겠다"
    label = _phase119_user_facing_label(
        state,
        analysis_data,
        what_we_know=what_we_know,
        what_we_failed=what_we_failed,
        rejected_only=rejected_only,
    )
    return {
        "schema": RESCUE_HANDOFF_SCHEMA,
        "trigger": _phase119_trigger(state),
        "attempted_path": _phase119_attempted_path(state),
        "preserved_evidences": preserved_evidences,
        "preserved_field_memo_facts": preserved_field_memo_facts,
        "rejected_only": rejected_only[:10],
        "what_we_know": [
            compact_user_facing_summary(item, 260)
            for item in what_we_know
            if str(item or "").strip()
        ][:8],
        "what_we_failed": [
            compact_user_facing_summary(item, 180)
            for item in what_we_failed
            if str(item or "").strip()
        ][:5],
        "speaker_tone_hint": tone_hint,
        "user_facing_label": label,
    }


def _phase119_rejected_sources(
    analysis_data: dict[str, Any],
    raw_read_report: dict[str, Any],
    *,
    compact_user_facing_summary: Callable[[Any, int], str],
) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    raw_read_report = raw_read_report if isinstance(raw_read_report, dict) else {}

    for item in analysis_data.get("rejected_sources", []) or []:
        if isinstance(item, dict):
            rejected.append(item)

    for judgment in analysis_data.get("field_memo_judgments", []) or []:
        if not isinstance(judgment, dict) or judgment.get("usable_for_current_goal"):
            continue
        source_id = str(judgment.get("memo_id") or "").strip()
        if not source_id:
            continue
        rejected.append({
            "source_id": source_id,
            "source_type": "field_memo",
            "reason": compact_user_facing_summary(
                str(judgment.get("rejection_reason") or "current_goal_not_answered"),
                180,
            ),
        })

    for judgment in analysis_data.get("source_judgments", []) or []:
        if not isinstance(judgment, dict):
            continue
        status_text = str(judgment.get("source_status") or "").strip().upper()
        objection = str(judgment.get("objection_reason") or "").strip()
        search_needed = bool(judgment.get("search_needed"))
        if status_text in {"COMPLETED", "PASS"} and not objection and not search_needed:
            continue
        source_id = str(judgment.get("source_id") or "").strip()
        if not source_id:
            continue
        rejected.append({
            "source_id": source_id,
            "source_type": str(judgment.get("source_type") or "source").strip(),
            "reason": compact_user_facing_summary(objection or "current_goal_not_answered", 180),
        })

    if not rejected and raw_read_report.get("items"):
        for item in raw_read_report.get("items", [])[:8]:
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("source_id") or item.get("id") or "").strip()
            if not source_id:
                continue
            rejected.append({
                "source_id": source_id,
                "source_type": str(item.get("source_type") or raw_read_report.get("read_mode") or "source").strip(),
                "reason": "119 rescue: this source was read but did not satisfy the current user goal.",
            })

    seen = set()
    deduped: list[dict[str, Any]] = []
    for item in rejected:
        key = (
            str(item.get("source_id") or "").strip(),
            str(item.get("reason") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:10]


def _phase119_missing_slots(
    analysis_data: dict[str, Any],
    *,
    dedupe_keep_order: Callable[[list[Any]], list[Any]],
    clean_failure_missing_items: Callable[[list[str] | None], list[str]],
) -> list[str]:
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    missing: list[str] = []
    for raw in (
        analysis_data.get("unfilled_slots")
        or analysis_data.get("missing_slots")
        or analysis_data.get("missing_info")
        or []
    ):
        text = str(raw or "").strip()
        if text:
            missing.append(text)
    if not missing:
        missing.append("direct evidence for the current answer")
    return clean_failure_missing_items(dedupe_keep_order(missing)[:5])


def run_phase_119_rescue(
    state: dict[str, Any],
    *,
    operation_plan_from_state: Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]],
    normalize_goal_lock: Callable[[dict[str, Any] | None], dict[str, Any]],
    compact_user_facing_summary: Callable[[Any, int], str],
    dedupe_keep_order: Callable[[list[Any]], list[Any]],
    clean_failure_missing_items: Callable[[list[str] | None], list[str]],
    build_clean_failure_packet: Callable[..., dict[str, Any]],
    empty_reasoning_board: Callable[..., dict[str, Any]],
    empty_verdict_board: Callable[[], dict[str, Any]],
    make_auditor_decision: Callable[..., dict[str, Any]],
    normalize_readiness_decision: Callable[[dict[str, Any] | None], dict[str, Any]],
    attach_ledger_event: Callable[..., dict[str, Any]],
    print_fn: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Build a clean failure delivery packet after a stuck or failed loop."""
    print_fn("[Phase 119] Running clean rescue failure path...")

    user_input = str(state.get("user_input") or "").strip()
    analysis_data = state.get("analysis_report", {})
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    raw_read_report = state.get("raw_read_report", {})
    raw_read_report = raw_read_report if isinstance(raw_read_report, dict) else {}
    strategist_output = state.get("strategist_output", {})
    strategist_output = strategist_output if isinstance(strategist_output, dict) else {}
    operation_plan = operation_plan_from_state(state, strategist_output)
    user_goal = (
        str(operation_plan.get("user_goal") or "").strip()
        or str((normalize_goal_lock(strategist_output.get("goal_lock", {}))).get("user_goal_core") or "").strip()
        or compact_user_facing_summary(user_input, 140)
        or "the current question"
    )

    rejected_sources = _phase119_rejected_sources(
        analysis_data,
        raw_read_report,
        compact_user_facing_summary=compact_user_facing_summary,
    )
    missing_slots = _phase119_missing_slots(
        analysis_data,
        dedupe_keep_order=dedupe_keep_order,
        clean_failure_missing_items=clean_failure_missing_items,
    )
    rescue_handoff_packet = build_rescue_handoff_packet(
        state,
        analysis_data=analysis_data,
        rejected_only=rejected_sources,
        missing_slots=missing_slots,
        compact_user_facing_summary=compact_user_facing_summary,
    )
    preserved_evidences = rescue_handoff_packet.get("preserved_evidences", [])
    if not isinstance(preserved_evidences, list):
        preserved_evidences = []
    preserved_field_memo_facts = rescue_handoff_packet.get("preserved_field_memo_facts", [])
    if not isinstance(preserved_field_memo_facts, list):
        preserved_field_memo_facts = []
    preserved_fact_texts = _dedupe_strings(
        [
            *[
                item.get("extracted_fact", "")
                for item in preserved_evidences
                if isinstance(item, dict)
            ],
            *preserved_field_memo_facts,
        ],
        limit=8,
        text_limit=260,
    )
    clean_failure = build_clean_failure_packet(
        state,
        {
            **analysis_data,
            "investigation_status": "INCOMPLETE",
            "can_answer_user_goal": False,
            "contract_status": "missing_slot",
            "missing_slots": missing_slots,
            "unfilled_slots": missing_slots,
            "rejected_sources": rejected_sources,
            "usable_field_memo_facts": preserved_field_memo_facts,
        },
        raw_read_report,
        operation_plan,
        user_goal,
        missing_slots=missing_slots,
        rejected_sources=rejected_sources,
    )
    message_seed = str(clean_failure.get("message_seed") or "").strip()
    if not message_seed:
        message_seed = (
            f"I checked up to this point, but still did not find direct evidence for `{compact_user_facing_summary(user_goal, 140)}`. "
            "I will exclude irrelevant candidates from the answer evidence."
        )

    cleaned_analysis = {
        **analysis_data,
        "evidences": preserved_evidences,
        "usable_field_memo_facts": preserved_field_memo_facts,
        "can_answer_user_goal": False,
        "contract_status": "missing_slot",
        "missing_slots": missing_slots,
        "unfilled_slots": missing_slots,
        "rejected_sources": rejected_sources,
        "rejected_only": rejected_sources,
        "rescue_handoff_packet": rescue_handoff_packet,
        "investigation_status": "INCOMPLETE",
        "situational_brief": message_seed,
        "analytical_thought": (
            "Rescue compressed the failed search path. Rejected sources must not be forwarded "
            "as answer evidence; preserved evidences and FieldMemo facts remain available as partial facts."
        ),
        "replan_directive_for_strategist": (
            "Do not reuse rejected candidates. Re-anchor the next search from the user's explicit referent, "
            "recent successful topic, or ToolCarryover origin before calling another tool."
        ),
    }

    cleaned_board = empty_reasoning_board(user_input=user_input)
    cleaned_board["must_avoid_claims"] = [
        "Do not summarize rejected search results or FieldMemo candidates as facts.",
        "Do not use stale theories/tool lanes from before rescue as if they answer the question.",
    ]
    cleaned_board["verdict_board"] = {
        **empty_verdict_board(),
        "answer_now": False,
        "final_answer_brief": "",
        "judge_notes": [
            "Rescue compressed a failed retrieval chain.",
            "Preserved facts may be cited as partial information; rejected sources remain blocked.",
        ],
    }

    result = {
        "analysis_report": cleaned_analysis,
        "rescue_handoff_packet": rescue_handoff_packet,
        "reasoning_board": cleaned_board,
        "response_strategy": {
            "reply_mode": "cautious_minimal",
            "delivery_freedom_mode": "clean_failure",
            "answer_goal": "State the loop failure cleanly and exclude irrelevant evidence.",
            "tone_strategy": "Calm and direct; do not mention internal rescue or graph structure.",
            "evidence_brief": " / ".join(preserved_fact_texts) if preserved_fact_texts else message_seed,
            "reasoning_brief": "The previous search path did not satisfy the whole user goal, so deliver preserved partial facts and the unresolved boundary.",
            "direct_answer_seed": message_seed,
            "must_include_facts": preserved_fact_texts,
            "must_avoid_claims": cleaned_board["must_avoid_claims"],
            "answer_outline": [
                "If partial facts exist, mention them first.",
                "State what remains unresolved.",
                "Say irrelevant candidates are excluded from evidence.",
            ],
            "uncertainty_policy": "Do not guess unknown content.",
        },
        "auditor_decision": make_auditor_decision(
            "clean_failure",
            memo="119 compressed failed retrieval and stripped rejected evidence before phase_3.",
        ),
        "supervisor_instructions": message_seed,
        "messages": [],
    }
    result["readiness_decision"] = normalize_readiness_decision(
        result["auditor_decision"].get("readiness_decision", {})
    )
    return attach_ledger_event(
        result,
        state,
        source_kind="clean_failure",
        producer_node="phase_119_rescue",
        source_ref=str(clean_failure.get("failure_kind") or "rescue_handoff"),
        content={
            "clean_failure": clean_failure,
            "rescue_handoff_packet": rescue_handoff_packet,
        },
        confidence=0.75,
    )


__all__ = [
    "RESCUE_HANDOFF_SCHEMA",
    "RESCUE_USER_FACING_LABELS",
    "build_rescue_handoff_packet",
    "run_phase_119_rescue",
]
