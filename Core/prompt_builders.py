import json


def _clip_prompt_text(value, limit: int = 900):
    text = str(value or "").strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _clip_prompt_list(values, limit: int = 6, text_limit: int = 240):
    if not isinstance(values, list):
        values = [values] if str(values or "").strip() else []
    result = []
    seen = set()
    for value in values:
        text = _clip_prompt_text(value, text_limit)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def compact_phase3_contract_for_prompt(contract: dict):
    """Return the LLM-visible phase_3 contract view.

    The full SpeakerJudgeContract stays available to code/state. This projection
    keeps the speaker prompt small and removes policy ledgers that should not be
    recited or treated as user-facing material.
    """
    source = contract if isinstance(contract, dict) else {}
    if_not_ready = source.get("IF_NOT_READY", {})
    if not isinstance(if_not_ready, dict):
        if_not_ready = {}
    rescue = source.get("RESCUE_HANDOFF", {})
    if not isinstance(rescue, dict):
        rescue = {}
    short_term = source.get("SHORT_TERM_CONTEXT", {})
    if not isinstance(short_term, dict):
        short_term = {}
    readiness = source.get("READINESS_DECISION", {})
    if not isinstance(readiness, dict):
        readiness = {}
    return {
        "schema": "Phase3PromptContract.v1",
        "ready": bool(source.get("READY")),
        "answer_mode": _clip_prompt_text(source.get("ANSWER_MODE"), 80),
        "delivery_freedom_mode": _clip_prompt_text(source.get("delivery_freedom_mode"), 80),
        "user_goal": _clip_prompt_text(source.get("USER_GOAL"), 260),
        "output_act": _clip_prompt_text(source.get("OUTPUT_ACT"), 80),
        "say_this": _clip_prompt_text(source.get("SAY_THIS"), 420),
        "facts_allowed": _clip_prompt_list(source.get("FACTS_ALLOWED", []), 6, 240),
        "current_turn_facts_allowed": _clip_prompt_list(source.get("CURRENT_TURN_FACTS_ALLOWED", []), 4, 220),
        "public_knowledge_allowed": bool(source.get("PARAMETRIC_KNOWLEDGE_ALLOWED")),
        "must_not_claim": _clip_prompt_list(source.get("DO_NOT_SAY", []), 6, 220),
        "if_not_ready": {
            "message_seed": _clip_prompt_text(if_not_ready.get("message_seed"), 320),
            "missing_slots": _clip_prompt_list(if_not_ready.get("missing_slots", []), 4, 120),
            "answer_boundary": _clip_prompt_text(if_not_ready.get("answer_boundary"), 180),
        },
        "rescue_handoff": {
            "what_we_know": _clip_prompt_list(rescue.get("what_we_know", []), 6, 220),
            "what_we_failed": _clip_prompt_list(rescue.get("what_we_failed", []), 4, 160),
            "speaker_tone_hint": _clip_prompt_text(rescue.get("speaker_tone_hint"), 80),
            "user_facing_label": _clip_prompt_text(rescue.get("user_facing_label"), 80),
        },
        "short_term_context": {
            "short_term_context": _clip_prompt_text(short_term.get("short_term_context"), 300),
            "assistant_obligation_next_turn": _clip_prompt_text(short_term.get("assistant_obligation_next_turn"), 220),
            "pending_dialogue_act": short_term.get("pending_dialogue_act", {}),
            "dialogue_state": short_term.get("dialogue_state", {}),
        },
        "recent_context_hint": _clip_prompt_text(source.get("RECENT_CONTEXT_HINT"), 320),
        "readiness": {
            "is_satisfied": bool(readiness.get("is_satisfied")),
            "instruction": _clip_prompt_text(readiness.get("instruction_to_0"), 160),
        },
    }


def _phase3_common_footer():
    return (
        "Common footer:\n"
        "- Write natural Korean to the user.\n"
        "- Use the contract as material, not text to recite.\n"
        "- Hide workflow names, phase names, slot keys, schema keys, 119, budget, rescue, and handoff.\n"
    )


def _format_phase3_prompt(*, title: str, contract_prompt: str, rules: list[str]):
    clipped_rules = [rule for rule in rules if str(rule).strip()][:5]
    numbered = "\n".join(f"{idx}. {rule}" for idx, rule in enumerate(clipped_rules, start=1))
    return (
        f"You are ANIMA phase_3 speaker. Mode: {title}.\n"
        "Speak directly to the user from the bounded contract.\n\n"
        f"[PHASE3_PROMPT_CONTRACT]\n{contract_prompt}\n\n"
        "Rules:\n"
        f"{numbered}\n\n"
        f"{_phase3_common_footer()}"
    )


def build_phase3_sys_prompt_public_parametric(contract_prompt: str) -> str:
    return _format_phase3_prompt(
        title="public_parametric_knowledge",
        contract_prompt=contract_prompt,
        rules=[
            "Answer from ordinary public knowledge when the contract allows public knowledge.",
            "Use only high-confidence canonical proper names; if a name is fuzzy, say you are not sure.",
            "If the user challenges a previous public-knowledge claim, correct or retract uncertain claims.",
            "Do not describe public knowledge as DB, memory, search, or tool evidence.",
            "Give a useful concise answer first, then uncertainty only where needed.",
        ],
    )


def build_phase3_sys_prompt_self_kernel(contract_prompt: str) -> str:
    return _format_phase3_prompt(
        title="self_kernel_response",
        contract_prompt=contract_prompt,
        rules=[
            "Answer identity, role, name, and relationship questions from the contract facts only.",
            "Keep the reply short and natural unless the user asks for detail.",
            "If the contract does not contain a requested self fact, say that part is not settled yet.",
            "Do not invent creator, model, name, memory, or relationship facts.",
        ],
    )


def build_phase3_sys_prompt_memory_recall(contract_prompt: str) -> str:
    return _format_phase3_prompt(
        title="memory_recall",
        contract_prompt=contract_prompt,
        rules=[
            "Use only facts_allowed, current_turn_facts_allowed, or rescue_handoff.what_we_know as factual claims.",
            "Mention allowed facts briefly and keep provenance honest without exposing packet names.",
            "If the needed memory is missing, say exactly which user-facing part is not known yet.",
            "Do not add guesses, translations, role swaps, or interpretations as new facts.",
            "Never turn a failed search attempt into a memory fact.",
        ],
    )


def build_phase3_sys_prompt_current_turn_grounding(contract_prompt: str) -> str:
    return _format_phase3_prompt(
        title="current_turn_grounding",
        contract_prompt=contract_prompt,
        rules=[
            "Use the user's current-turn facts as admissible grounding when listed in the contract.",
            "Blend current-turn facts with facts_allowed only when both are present.",
            "If a requested fact is absent, say it is not settled instead of inferring it.",
            "Do not promote jokes, insults, or acknowledgements into durable factual claims.",
            "Answer the current turn directly without broadening the goal.",
        ],
    )


def build_phase3_sys_prompt_simple_continuation(contract_prompt: str) -> str:
    return _format_phase3_prompt(
        title="simple_continuation",
        contract_prompt=contract_prompt,
        rules=[
            "Satisfy assistant_obligation_next_turn first when it is present.",
            "Use pending_dialogue_act to resolve short acknowledgements, corrections, or pushback.",
            "For tiny turns such as yes or ok, continue the pending move instead of repeating old answers.",
            "Keep playful or conversational continuations short unless the user asks for substance.",
            "Do not claim long-term memory from short-term context.",
        ],
    )


def build_phase3_sys_prompt_cautious_minimal(contract_prompt: str) -> str:
    return _format_phase3_prompt(
        title="cautious_minimal",
        contract_prompt=contract_prompt,
        rules=[
            "If rescue_handoff.what_we_know has facts, mention those partial facts before the unresolved boundary.",
            "Follow speaker_tone_hint: apology plus partial info, simple unknown, clarifying question, or next-turn promise.",
            "Convert user_facing_label into natural Korean; do not quote it as a system label.",
            "If no preserved fact exists, give a clean minimal uncertainty response.",
            "Do not expose trigger, attempted path, phase, budget, rescue, or handoff language.",
        ],
    )


def build_phase3_sys_prompt(answer_mode: str, contract_prompt: str) -> str:
    mode = str(answer_mode or "").strip().lower()
    if mode in {"public_parametric_knowledge", "public_parametric", "public_knowledge"}:
        return build_phase3_sys_prompt_public_parametric(contract_prompt)
    if mode in {"self_kernel_response", "self_kernel", "identity_response"}:
        return build_phase3_sys_prompt_self_kernel(contract_prompt)
    if mode in {"memory_recall", "grounded_memory_recall", "grounded_answer"}:
        return build_phase3_sys_prompt_memory_recall(contract_prompt)
    if mode in {"current_turn_grounding", "current_turn_fact", "current_turn_grounded"}:
        return build_phase3_sys_prompt_current_turn_grounding(contract_prompt)
    if mode in {"simple_continuation", "continuation", "generic_dialogue", "direct_dialogue"}:
        return build_phase3_sys_prompt_simple_continuation(contract_prompt)
    if mode in {"cautious_minimal", "clean_failure", "answer_not_ready", "rescue"}:
        return build_phase3_sys_prompt_cautious_minimal(contract_prompt)
    return build_phase3_sys_prompt_cautious_minimal(contract_prompt)


def build_delivery_review_sys_prompt(context_prompt: str) -> str:
    return (
        "You are ANIMA -1b delivery reviewer.\n"
        "Review only the already-written phase_3 answer.\n\n"
        f"[DELIVERY_REVIEW_CONTEXT]\n{context_prompt}\n\n"
        "Rules:\n"
        "1. Compare final_answer against fact_cells_for_review, evidences, usable_field_memo_facts, preserved_rescue_facts, and must_include_facts.\n"
        "2. If final_answer cites a factual claim not supported there, set verdict=remand and reason_type=hallucination.\n"
        "3. If final_answer omits a required must_include_fact, set verdict=remand and reason_type=omission.\n"
        "4. If final_answer leaks workflow words, phase names, 119, budget, rescue, handoff, or slot keys, set verdict=remand and reason=tone.\n"
        "5. Otherwise set verdict=approve. Use sos_119 only when another remand cannot make a useful answer.\n\n"
        "Footer:\n"
        "- Output DeliveryReview.v1 JSON only with fields: verdict, reason, reason_type, evidence_refs, delta, issues_found, remand_target, remand_guidance.\n"
        "- reason_type values: hallucination | omission | contradiction | thought_gap | tool_misuse | empty string.\n"
        "- For hallucination, omission, or contradiction, evidence_refs must cite only fact_id values present in fact_cells_for_review; never invent fact_ids.\n"
        "- remand_target may be empty because code derives it from reason_type.\n"
        "- Do not call tools, generate queries, or rewrite the answer.\n"
        "- Do not change answer_mode; review the answer under the provided boundary.\n"
    )


def build_phase_minus_1a_prompt(
    *,
    user_input: str,
    recent_context: str,
    user_state: str,
    user_char: str,
    time_gap: float,
    tolerance: float,
    bio_status: str,
    songryeon_thoughts: str,
    working_memory_packet: str,
    tool_carryover_packet: str,
    start_gate_review_packet: str,
    fact_cells_packet: str,
    auditor_memo: str,
    war_room_packet: str,
    answer_mode_policy_packet: str = "N/A",
    evidence_ledger_packet: str = "N/A",
    s_thinking_packet: str = "N/A",
    strategist_goal_packet: str = "N/A",
) -> str:
    return (
        "You are ANIMA's -1a strategist.\n"
        "Phase 2 diagnosed the case, but diagnosis alone is not enough. Convert the grounded case into an explicit next-step contract.\n"
        "You are planning, not delivering the final answer.\n"
        "If evidence is thin, prefer a narrower plan over a fake confident response strategy.\n\n"
        f"[user_input]\n{user_input}\n\n"
        f"[recent_context]\n{recent_context}\n\n"
        f"[answer_mode_policy]\n{answer_mode_policy_packet}\n\n"
        f"[evidence_ledger]\n{evidence_ledger_packet}\n\n"
        f"[user_state]\n{user_state}\n\n"
        f"[user_char]\n{user_char}\n\n"
        f"[time_gap]\n{time_gap}\n\n"
        f"[global_tolerance]\n{tolerance}\n\n"
        f"[biolink_status]\n{bio_status}\n\n"
        f"[songryeon_thoughts]\n{songryeon_thoughts}\n\n"
        f"[working_memory]\n{working_memory_packet}\n\n"
        f"[tool_carryover]\n{tool_carryover_packet}\n\n"
        f"[s_thinking_packet]\n{s_thinking_packet}\n\n"
        f"[fact_cells]\n{fact_cells_packet}\n\n"
        f"[strategist_goal]\n{strategist_goal_packet}\n\n"
        f"[start_gate_review]\n{start_gate_review_packet}\n\n"
        f"[auditor_memo]\n{auditor_memo if auditor_memo else 'N/A'}\n\n"
        f"[war_room_state]\n{war_room_packet}\n\n"
        "Rules:\n"
        "1. Build goals in this order: goal_contract -> strategist_goal -> action_plan. normalized_goal is a legacy alias only.\n"
        "2. Fill strategist_goal, goal_lock, action_plan, delivery_readiness, achieved_findings, and next_frontier; never make the final routing choice.\n"
        "3. Treat s_thinking_packet (ThinkingHandoff.v1) as the primary case state: what_we_know, what_is_missing, next_node_reason, and constraints.\n"
        "4. response_strategy.must_include_facts may contain only fact_cells cited by fact_id or current-turn facts already admitted by answer_mode_policy.\n"
        "5. Do not re-judge facts. Fact judgment authority belongs to -1s/2b; cite fact_cells instead of relitigating them.\n"
        "6. Do not author tool calls. Phase 0 supervisor decides exact tool name, args, and queries from operation_contract.\n"
        "7. F4.7: When evidence is missing, make operation_contract concrete enough for phase 0 without writing executable args: fill source_lane, search_subject, missing_slot, query_seed_candidates, retrieval_key_candidates, source_title_candidates, and evidence_boundary.\n"
        "8. search_subject may describe the evidence topic, but retrieval_key_candidates/source_title_candidates must carry compact executable anchors such as names, project titles, source titles, dates, ids, or quoted terms. Do not put current_step_goal-style task prose in seed fields.\n"
        "9. If the user asks about capability/access rather than requesting retrieval, set source_lane=capability_boundary and prefer delivery_readiness=deliver_now with a response_strategy.\n"
        "10. If no tool is needed, set delivery_readiness=deliver_now and leave action_plan.required_tool empty.\n"
        "11. If evidence is missing, describe one narrow operation_contract intent; keep response_strategy empty or minimal.\n"
        "12. Do not pass the whole user sentence as a search query. Do not use current_step_goal as a query seed.\n"
    )


def build_thought_critic_prompt(
    *,
    s_thinking_packet_compact: str,
    recent_context_compact: str,
    working_memory_compact: str,
    fact_cells_compact: str,
    mode: str = "memory_based",
) -> str:
    """System prompt for 2b in thought_critic mode (V4 §1-A.3, CR1).

    Mode auto-switches by input (B-2.4 (다)):
      - ``integrated`` — fact_cells > 0, compare facts + thought + memory
      - ``memory_based`` — fact_cells == 0, compare thought + memory only
    """
    mode_brief = (
        "Integrated critique mode: fact_cells are available — compare the "
        "thought flow against verified facts AND recent_context/working_memory."
        if mode == "integrated"
        else
        "Memory-based critique mode: fact_cells are EMPTY — compare the thought "
        "flow only against recent_context + working_memory + s_thinking_packet."
    )
    return (
        "You are ANIMA's 2b in thought_critic mode (V4 §1-A.3).\n"
        "You are NOT verifying tool output here. You are critiquing -1s's own "
        "thought flow against memory before -1s is called again.\n\n"
        f"[mode]\n{mode_brief}\n\n"
        f"[s_thinking_packet (current -1s thought)]\n{s_thinking_packet_compact}\n\n"
        f"[recent_context]\n{recent_context_compact}\n\n"
        f"[working_memory]\n{working_memory_compact}\n\n"
        f"[fact_cells]\n{fact_cells_compact}\n\n"
        "Detect and classify into the four buckets. Each item has issue + "
        "evidence_refs (fact_id citations from reasoning_board.fact_cells; do "
        "NOT invent fact_ids — V4 §2 (d)) + severity (minor/warning/blocker):\n"
        "  - hallucination_risks: claims in the thought flow that lack support\n"
        "    in fact_cells / recent_context / working_memory.\n"
        "  - logic_gaps: missing reasoning steps between situation and handoff.\n"
        "  - memory_omissions: recent_context / working_memory items the\n"
        "    thought flow ignored or contradicted.\n"
        "  - persona_errors: person/perspective confusion (e.g., '그 친구' vs\n"
        "    user themselves) detected in the thought flow.\n\n"
        "Also fill `delta` with a 1-2 sentence summary the second -1s call "
        "should read first.\n\n"
        "Authority (V4 §1-A.3 + V4 §2):\n"
        "- ALLOWED: critique only; cite existing fact_ids; output ThoughtCritique.v1.\n"
        "- FORBIDDEN: tool calls (V4 §2 (g)); answer text; routing decisions;\n"
        "  fact_id invention (V4 §2 (d)); fact re-judgment outside what's in hand.\n"
        "If nothing critical is found, return empty lists with delta='no critical issue detected'."
    )


def build_phase_2b_prompt(
    *,
    analysis_mode: str,
    user_input: str,
    raw_read_packet: str,
    auditor_memo: str,
    working_memory_packet: str,
    operation_contract_packet: str,
    execution_trace_packet: str,
    tool_carryover_packet: str,
    critic_lens_prompt: str,
    source_relay_prompt: str,
    evidence_ledger_packet: str = "N/A",
) -> str:
    return (
        "You are ANIMA's phase_2b critic and source prosecutor.\n"
        "Read the phase_2a report and produce a fact-first analysis report using only the grounded material in that packet.\n"
        "Do not paraphrase yourself into new facts. Do not confuse a recovered question surface with a filled answer slot.\n\n"
        "Output contract:\n"
        "- Return exactly an AnalysisReport-shaped structured packet.\n"
        "- Required top-level keys include evidences, source_judgments, analytical_thought, situational_brief, and investigation_status.\n"
        "- Do not output generic report keys such as analysis_summary, key_entities, answer, conclusion, or final_response.\n"
        "- Keep analytical_thought and situational_brief short; the schema is a judge packet, not an essay.\n\n"
        f"[analysis_mode]\n{analysis_mode}\n\n"
        f"[user_input]\n{user_input}\n\n"
        f"[raw_read_report]\n{raw_read_packet}\n\n"
        f"[auditor_memo]\n{auditor_memo if auditor_memo else 'N/A'}\n\n"
        f"[working_memory]\n{working_memory_packet}\n\n"
        f"[operation_contract]\n{operation_contract_packet}\n\n"
        f"[execution_trace]\n{execution_trace_packet}\n\n"
        f"[tool_carryover]\n{tool_carryover_packet}\n\n"
        f"[critic_lens_packet]\n{critic_lens_prompt}\n\n"
        f"[source_relay_packet]\n{source_relay_prompt}\n\n"
        f"[evidence_ledger]\n{evidence_ledger_packet}\n\n"
        "[phase_2b_source_contract]\n"
        "- Produce source_judgments for every source packet emitted by phase_2a.\n"
        "- Each source_judgment includes source_status, accepted_facts, objection_reason, missing_info, and search_needed.\n"
        "- Pass FieldMemo material through accepted_facts/usable_field_memo_facts; do not write a FieldMemo answer seed.\n\n"
        "Rules:\n"
        "1. evidences must be concrete facts found in raw_read_report or source_relay_packet; if phase_2a did not read it, it is not a fact.\n"
        "2. Distinguish source coverage from goal satisfaction: a read source can still leave contract_status incomplete.\n"
        "3. Preserve speaker roles, subject/object relations, and quoted meanings while summarizing dialogue.\n"
        "4. Use COMPLETED only when accepted facts can support the user's requested answer act; otherwise use INCOMPLETE or EXPANSION_REQUIRED.\n"
        "5. Describe missing boundaries and concrete deficiencies; do not invent future plans or answer-shaped seeds.\n"
    )
