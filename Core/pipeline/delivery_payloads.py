"""Phase 3 lane and payload assembly helpers.

This module shapes the phase 3 delivery lane and DeliveryPayload packet. It
receives semantic helpers from the caller so the graph-facing public API in
Core.nodes can stay compatible while the heavy body leaves the god-file.
"""

from __future__ import annotations

from typing import Callable

from ..readiness import readiness_from_delivery_payload


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


def _strategy_from_state_or_output(state: dict, strategist_output: dict) -> dict:
    strategy = state.get("response_strategy", {})
    if not isinstance(strategy, dict) or not strategy:
        strategy = strategist_output.get("response_strategy", {})
    return strategy if isinstance(strategy, dict) else {}


def _direct_no_tool_strategy_lane(operation_plan: dict, packet: dict, lane: str) -> bool:
    plan_type = str(operation_plan.get("plan_type") or "").strip()
    source_lane = str(packet.get("source_lane") or operation_plan.get("source_lane") or "").strip()
    if source_lane == "":
        source_lane = "none"
    return bool(
        lane == "generic"
        and plan_type == "direct_delivery"
        and source_lane in {"none", "direct_dialogue"}
    )


def _strategy_list(strategy: dict, key: str, *, compact_user_facing_summary: Callable[[str, int], str]) -> list[str]:
    values = strategy.get(key, [])
    if not isinstance(values, list):
        values = [values] if str(values or "").strip() else []
    return _dedupe_keep_order([
        compact_user_facing_summary(str(value).strip(), 220)
        for value in values
        if str(value).strip()
    ])


def build_phase3_lane_delivery_packet(
    state: dict,
    judge_speaker_packet: dict,
    *,
    operation_plan_from_state: Callable[..., dict],
    build_recent_dialogue_brief: Callable[..., dict],
    build_field_memo_user_brief: Callable[..., dict],
    build_warroom_answer_seed_packet: Callable[[dict], dict],
    strategy_needs_post_read_synthesis: Callable[[dict | None, dict | None], bool],
    build_findings_first_packet: Callable[[str, dict], dict],
    analysis_has_grounded_artifact_evidence: Callable[[dict], bool],
    build_grounded_source_findings_packet: Callable[[dict, dict, str], dict],
):
    raw_read_report = state.get("raw_read_report", {})
    analysis_data = state.get("analysis_report", {})
    user_input = str(state.get("user_input") or "")
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    operation_plan = operation_plan_from_state(
        state,
        strategist_output,
    )
    source_lane = str(operation_plan.get("source_lane") or "").strip()
    output_act = str(operation_plan.get("output_act") or "").strip()
    recent_packet = build_recent_dialogue_brief(raw_read_report, analysis_data, user_input=user_input)
    if recent_packet:
        return {
            "lane": "recent_dialogue_review",
            "source_lane": source_lane,
            "output_act": output_act,
            "user_facing_recent_dialogue_brief": recent_packet.get("user_facing_recent_dialogue_brief", ""),
            "recent_dialogue_brief": recent_packet,
        }
    memory_packet = build_field_memo_user_brief(raw_read_report, analysis_data)
    if memory_packet:
        return {
            "lane": "field_memo_review",
            "source_lane": source_lane,
            "output_act": output_act,
            "user_input": user_input,
            "user_facing_memory_brief": memory_packet.get("user_facing_memory_brief", ""),
            "known_facts": memory_packet.get("known_facts", []),
            "accepted_facts": memory_packet.get("accepted_facts", memory_packet.get("known_facts", [])),
            "usable_field_memo_facts": memory_packet.get("usable_field_memo_facts", memory_packet.get("known_facts", [])),
            "goal_contract": memory_packet.get("goal_contract", {}),
            "contract_status": memory_packet.get("contract_status", ""),
            "missing_slots": memory_packet.get("unknown_slots", []),
            "filled_slots": memory_packet.get("filled_slots", {}),
            "unfilled_slots": memory_packet.get("unfilled_slots", memory_packet.get("unknown_slots", [])),
            "rejected_sources": memory_packet.get("rejected_sources", []),
            "can_answer_user_goal": bool(analysis_data.get("can_answer_user_goal")) if isinstance(analysis_data, dict) else False,
            "replan_directive_for_strategist": memory_packet.get("replan_directive_for_strategist", ""),
            "field_memo_recall_packet": memory_packet,
        }
    warroom_packet = build_warroom_answer_seed_packet(state)
    if warroom_packet and strategy_needs_post_read_synthesis(strategist_output, analysis_data):
        return warroom_packet
    if output_act == "deliver_findings":
        findings_packet = build_findings_first_packet(user_input, judge_speaker_packet)
        if findings_packet:
            return findings_packet
    should_deliver_grounded_source = (
        analysis_has_grounded_artifact_evidence(analysis_data)
        or source_lane in {"artifact_read", "memory_search", "scroll_source"}
        or (
            str(raw_read_report.get("read_mode") or "").strip() == "full_raw_review"
            and str(operation_plan.get("plan_type") or "").strip() in {"tool_evidence", "raw_source_analysis"}
        )
    )
    if should_deliver_grounded_source:
        grounded_packet = build_grounded_source_findings_packet(raw_read_report, analysis_data, user_input)
        if grounded_packet:
            return grounded_packet
    if warroom_packet:
        return warroom_packet
    return {
        "lane": "generic",
        "source_lane": source_lane,
        "output_act": output_act,
        "generic_delivery_packet": {
            "final_answer_brief": str((judge_speaker_packet or {}).get("final_answer_brief") or "").strip(),
            "answer_boundary": "generic_judge_packet",
        },
    }


def phase3_payload_accepted_facts_from_packet(
    packet: dict,
    *,
    compact_user_facing_summary: Callable[[str, int], str],
):
    packet = packet if isinstance(packet, dict) else {}
    facts: list[str] = []
    for direct_key in ("known_facts", "accepted_facts", "usable_field_memo_facts"):
        direct_facts = packet.get(direct_key, [])
        if isinstance(direct_facts, list):
            facts.extend(str(fact).strip() for fact in direct_facts if str(fact).strip())
    recall_packet = packet.get("field_memo_recall_packet", {})
    if isinstance(recall_packet, dict):
        for recall_key in ("known_facts", "accepted_facts", "usable_field_memo_facts"):
            facts.extend(str(fact).strip() for fact in recall_packet.get(recall_key, []) or [] if str(fact).strip())
    findings = packet.get("findings_first_packet", {})
    if isinstance(findings, dict):
        for fact in findings.get("approved_fact_cells", []) or []:
            if isinstance(fact, dict):
                text = str(fact.get("extracted_fact") or fact.get("excerpt") or "").strip()
                if text:
                    facts.append(text)
    recent = packet.get("recent_dialogue_brief", {})
    if isinstance(recent, dict):
        facts.extend(str(item).strip() for item in recent.get("confirmed_turns", []) or [] if str(item).strip())
    return _dedupe_keep_order([compact_user_facing_summary(fact, 220) for fact in facts if str(fact).strip()])[:6]


def rescue_handoff_facts_for_delivery(
    rescue_handoff_packet: dict,
    *,
    compact_user_facing_summary: Callable[[str, int], str],
) -> list[str]:
    packet = rescue_handoff_packet if isinstance(rescue_handoff_packet, dict) else {}
    facts: list[str] = []
    for item in packet.get("preserved_evidences", []) or []:
        if not isinstance(item, dict):
            continue
        fact = str(item.get("extracted_fact") or item.get("observed_fact") or "").strip()
        if fact:
            facts.append(fact)
    facts.extend(str(fact).strip() for fact in packet.get("preserved_field_memo_facts", []) or [] if str(fact).strip())
    facts.extend(str(fact).strip() for fact in packet.get("what_we_know", []) or [] if str(fact).strip())
    return _dedupe_keep_order([compact_user_facing_summary(fact, 220) for fact in facts if str(fact).strip()])[:8]


def build_phase3_delivery_payload(
    state: dict,
    judge_speaker_packet: dict,
    phase3_delivery_packet: dict,
    *,
    operation_plan_from_state: Callable[..., dict],
    normalize_goal_lock: Callable[[dict | None], dict],
    compact_user_facing_summary: Callable[[str, int], str],
    derive_user_goal_contract: Callable[..., dict],
    answer_mode_policy_for_turn: Callable[..., dict],
    extract_current_turn_grounding_facts: Callable[..., list],
    contract_satisfied_by_facts: Callable[..., bool],
    turn_allows_parametric_knowledge_blend: Callable[[str, str], bool],
    field_memo_packet_ready_for_delivery: Callable[..., bool],
    has_meaningful_delivery_seed: Callable[[str, str], bool],
    build_clean_failure_packet: Callable[..., dict],
):
    packet = phase3_delivery_packet if isinstance(phase3_delivery_packet, dict) else {}
    analysis_data = state.get("analysis_report", {})
    analysis_data = analysis_data if isinstance(analysis_data, dict) else {}
    raw_read_report = state.get("raw_read_report", {})
    raw_read_report = raw_read_report if isinstance(raw_read_report, dict) else {}
    user_input = str(state.get("user_input") or "")
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    response_strategy = _strategy_from_state_or_output(state, strategist_output)
    operation_plan = operation_plan_from_state(state, strategist_output)
    goal_lock = normalize_goal_lock(strategist_output.get("goal_lock", {}))
    recent_context = str(state.get("recent_context") or "")

    lane = str(packet.get("lane") or "generic").strip() or "generic"
    output_act = str(packet.get("output_act") or operation_plan.get("output_act") or "answer").strip() or "answer"
    user_goal = (
        str(operation_plan.get("user_goal") or "").strip()
        or str(goal_lock.get("user_goal_core") or "").strip()
        or compact_user_facing_summary(user_input, 160)
    )

    answer_seed = ""
    contract_status = str(packet.get("contract_status") or "").strip() or "unknown"
    missing_slots = packet.get("missing_slots", [])
    if not isinstance(missing_slots, list):
        missing_slots = [missing_slots] if str(missing_slots or "").strip() else []
    missing_slots = [str(slot).strip() for slot in missing_slots if str(slot).strip()]
    filled_slots = packet.get("filled_slots", {})
    if not isinstance(filled_slots, dict):
        filled_slots = {}
    rejected_sources = packet.get("rejected_sources", [])
    if not isinstance(rejected_sources, list):
        rejected_sources = []
    accepted_facts = phase3_payload_accepted_facts_from_packet(
        packet,
        compact_user_facing_summary=compact_user_facing_summary,
    )
    strategy_must_include_facts = []
    strategy_must_avoid_claims = []
    direct_strategy_facts_ready = False
    rescue_handoff_packet = state.get("rescue_handoff_packet", {})
    if not isinstance(rescue_handoff_packet, dict):
        rescue_handoff_packet = {}
    rescue_facts = rescue_handoff_facts_for_delivery(
        rescue_handoff_packet,
        compact_user_facing_summary=compact_user_facing_summary,
    )
    if rescue_facts:
        accepted_facts = _dedupe_keep_order(list(accepted_facts) + rescue_facts)[:8]
    goal_contract = packet.get("goal_contract", {})
    if not isinstance(goal_contract, dict) or not goal_contract:
        goal_contract = derive_user_goal_contract(
            user_input,
            source_lane=str(packet.get("source_lane") or operation_plan.get("source_lane") or lane or "direct_dialogue"),
        )
    answer_mode_policy = answer_mode_policy_for_turn(user_input, recent_context, goal_contract)
    question_class = str(answer_mode_policy.get("question_class") or "").strip() or "generic_dialogue"
    current_turn_facts = extract_current_turn_grounding_facts(user_input, goal_contract)
    current_turn_supports_goal = bool(
        current_turn_facts and contract_satisfied_by_facts(goal_contract, current_turn_facts, "")
    )
    if current_turn_facts:
        accepted_facts = _dedupe_keep_order(list(accepted_facts) + current_turn_facts)[:8]
    if _direct_no_tool_strategy_lane(operation_plan, packet, lane):
        strategy_must_include_facts = _strategy_list(
            response_strategy,
            "must_include_facts",
            compact_user_facing_summary=compact_user_facing_summary,
        )[:6]
        strategy_must_avoid_claims = _strategy_list(
            response_strategy,
            "must_avoid_claims",
            compact_user_facing_summary=compact_user_facing_summary,
        )[:6]
        if strategy_must_include_facts:
            accepted_facts = _dedupe_keep_order(list(accepted_facts) + strategy_must_include_facts)[:8]
            direct_strategy_facts_ready = True
    parametric_knowledge_allowed = turn_allows_parametric_knowledge_blend(user_input, recent_context)
    fallback_action = "clean_failure"
    answer_boundary = str(packet.get("answer_boundary") or "").strip()
    answer_mode = "grounded_contract"

    if lane == "recent_dialogue_review":
        answer_seed = str(packet.get("user_facing_recent_dialogue_brief") or "").strip()
        contract_status = "satisfied" if answer_seed else "missing_slot"
        fallback_action = "ask_for_recent_context"
        answer_boundary = "recent_dialogue_only"
        answer_mode = "recent_dialogue_grounding"
    elif lane == "field_memo_review":
        if field_memo_packet_ready_for_delivery(packet, analysis_data, user_input):
            answer_seed = ""
            contract_status = "satisfied"
        else:
            answer_seed = ""
            contract_status = contract_status if contract_status != "unknown" else "missing_slot"
            if not missing_slots:
                missing_slots = ["usable evidence for the current answer"]
        fallback_action = "replan_or_search_more"
        answer_boundary = "field_memo_filtered_only"
        answer_mode = "field_memo_grounding"
    elif lane == "findings_first":
        findings = packet.get("findings_first_packet", {})
        if isinstance(findings, dict):
            seed = str(findings.get("user_facing_findings_brief") or "").strip()
            if seed and has_meaningful_delivery_seed(seed, user_input):
                answer_seed = seed
                contract_status = "satisfied"
        fallback_action = "search_more_or_report_limit"
        answer_boundary = "findings_only"
        answer_mode = "findings_grounding"
    elif lane == "warroom":
        seed = str(packet.get("warroom_answer_seed") or "").strip()
        if seed and has_meaningful_delivery_seed(seed, user_input):
            answer_seed = seed
            contract_status = "satisfied"
        fallback_action = "re_deliberate"
        answer_boundary = "warroom_seed_only"
        answer_mode = "warroom_synthesis"
    else:
        generic = packet.get("generic_delivery_packet", {})
        if isinstance(generic, dict):
            seed = str(generic.get("final_answer_brief") or "").strip()
            if seed and has_meaningful_delivery_seed(seed, user_input):
                answer_seed = seed
                contract_status = "satisfied"
        fallback_action = "direct_dialogue_or_replan"
        answer_boundary = "generic_payload"
        answer_mode = "generic_dialogue"

    clean_failure_packet = build_clean_failure_packet(
        state,
        analysis_data,
        raw_read_report,
        operation_plan,
        user_goal,
        missing_slots=missing_slots,
        rejected_sources=rejected_sources,
    )
    if direct_strategy_facts_ready:
        clean_failure_packet = {}
        contract_status = "satisfied"
        missing_slots = []
        fallback_action = "direct_strategy_facts"
        answer_boundary = answer_boundary or "direct no-tool strategy facts"
        answer_mode = str(response_strategy.get("reply_mode") or "grounded_answer").strip() or "grounded_answer"
    if clean_failure_packet and lane == "generic":
        answer_seed = ""
        contract_status = "missing_slot" if contract_status == "unknown" else contract_status
    if clean_failure_packet and not answer_seed:
        fallback_action = "clean_failure"
        contract_status = "missing_slot" if contract_status == "unknown" else contract_status
        if not missing_slots:
            missing_slots = list(clean_failure_packet.get("missing_slots", []) or [])
        answer_boundary = str(clean_failure_packet.get("answer_boundary") or "clean_failure_only")
        answer_mode = "clean_failure"

    facts_ready_for_delivery = bool(
        lane == "field_memo_review"
        and accepted_facts
        and contract_status in {"", "satisfied"}
        and not missing_slots
        and not clean_failure_packet
    )
    ready = bool(
        answer_seed
        and has_meaningful_delivery_seed(answer_seed, user_input)
        and contract_status in {"", "satisfied"}
        and not missing_slots
    ) or facts_ready_for_delivery or direct_strategy_facts_ready
    if current_turn_supports_goal:
        ready = True
        contract_status = "satisfied"
        missing_slots = []
        clean_failure_packet = {}
        fallback_action = "current_turn_grounding"
        answer_boundary = "current_turn_grounding + admissible user-provided facts"
        answer_mode = "current_turn_grounding"
    elif parametric_knowledge_allowed and not clean_failure_packet:
        ready = True
        if not answer_boundary:
            answer_boundary = "public_parametric_knowledge + loop evidence blend"
        if contract_status == "unknown":
            contract_status = "parametric_public_knowledge"
        fallback_action = "public_knowledge_answer"
        answer_mode = "public_parametric_knowledge"
    if ready:
        clean_failure_packet = {}
        if answer_mode == "grounded_contract":
            answer_mode = "grounded_answer"
    if rescue_handoff_packet:
        ready = False
        clean_failure_packet = clean_failure_packet or {
            "clean_failure": True,
            "message_seed": str(rescue_handoff_packet.get("user_facing_label") or "").strip(),
            "missing_slots": rescue_handoff_packet.get("what_we_failed", []),
            "answer_boundary": "rescue_handoff_only: cite preserved facts and unresolved gaps only.",
        }
        fallback_action = "clean_failure"
        contract_status = "missing_slot"
        answer_mode = "clean_failure"
        answer_boundary = "rescue_handoff_only: cite preserved facts and unresolved gaps only."
        parametric_knowledge_allowed = False
    forbidden_claims = []
    delivery_packet = judge_speaker_packet.get("delivery_packet", {}) if isinstance(judge_speaker_packet, dict) else {}
    if isinstance(delivery_packet, dict):
        forbidden_claims.extend(str(item).strip() for item in delivery_packet.get("hard_constraints", []) or [] if str(item).strip())
    forbidden_claims.extend([
        "Do not recite analysis_report, operation_plan, judge_notes, or internal labels.",
        "Do not use rejected FieldMemo candidates as answer evidence.",
        "Do not treat source_read_complete as answer_ready.",
    ])
    forbidden_claims.extend(strategy_must_avoid_claims)

    delivery_payload = {
        "schema": "DeliveryPayload.v1",
        "lane": lane,
        "question_class": question_class,
        "answer_mode_policy": answer_mode_policy,
        "source_lane": str(packet.get("source_lane") or operation_plan.get("source_lane") or "none").strip(),
        "output_act": output_act,
        "user_goal": user_goal,
        "goal_contract": goal_contract,
        "answer_seed": answer_seed,
        "accepted_facts": accepted_facts,
        "strategy_must_include_facts": strategy_must_include_facts,
        "rescue_handoff_packet": rescue_handoff_packet,
        "current_turn_facts": current_turn_facts,
        "filled_slots": filled_slots,
        "missing_slots": missing_slots,
        "unfilled_slots": missing_slots,
        "contract_status": "satisfied" if ready else contract_status,
        "ready_for_delivery": ready,
        "parametric_knowledge_allowed": parametric_knowledge_allowed,
        "answer_mode": answer_mode,
        "rejected_sources": rejected_sources,
        "clean_failure_packet": clean_failure_packet,
        "strategy_must_avoid_claims": strategy_must_avoid_claims,
        "forbidden_claims": _dedupe_keep_order(forbidden_claims),
        "fallback_action": fallback_action,
        "answer_boundary": answer_boundary,
    }
    delivery_payload["readiness_decision"] = readiness_from_delivery_payload(delivery_payload)
    return delivery_payload


__all__ = [
    "build_phase3_lane_delivery_packet",
    "phase3_payload_accepted_facts_from_packet",
    "rescue_handoff_facts_for_delivery",
    "build_phase3_delivery_payload",
]
