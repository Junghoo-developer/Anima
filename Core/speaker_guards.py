from langchain_core.messages import AIMessage

from .state import AnimaState
from . import nodes as base_nodes


def phase_minus_1b_auditor_with_speaker_guard(state: AnimaState):
    result = base_nodes.phase_minus_1b_auditor(state)
    if not isinstance(result, dict):
        return result

    decision = result.get("auditor_decision", {})
    action = str((decision or {}).get("action") or "").strip()
    if not action:
        return result

    reasoning_board = result.get("reasoning_board", {})
    analysis_data = state.get("analysis_report", {})
    recent_context = state.get("recent_context", "")
    working_memory = state.get("working_memory", {})
    user_input = state.get("user_input", "")
    search_results = state.get("search_results", "")
    loop_count = state.get("loop_count", 0)
    raw_budget = result.get("reasoning_budget", state.get("reasoning_budget", 1))
    try:
        reasoning_budget = max(int(raw_budget or 0), 0)
    except (TypeError, ValueError):
        reasoning_budget = 1

    if action == "phase_3":
        prepared_strategy, _, speaker_review = base_nodes._prepare_phase3_delivery(
            user_input=user_input,
            recent_context=recent_context,
            working_memory=working_memory,
            reasoning_board=reasoning_board,
            analysis_data=analysis_data,
            response_strategy=result.get("response_strategy", {}),
            search_results=search_results,
            loop_count=loop_count,
        )
        if speaker_review.get("should_remand"):
            remand_missing = ", ".join(speaker_review.get("missing_for_delivery", [])[:2])
            remand_memo = "3차 송달 관점에서 아직 바로 말하기 어려운 패킷입니다."
            if remand_missing:
                remand_memo += f" 부족한 항목: {remand_missing}."

            if loop_count < max(reasoning_budget, 1):
                new_decision = base_nodes._make_auditor_decision("plan_more", memo=remand_memo + " 한 번 더 내부 계획을 보강합니다.")
                war_room = base_nodes._war_room_after_judge(
                    base_nodes._normalize_war_room_state(result.get("war_room", {})),
                    new_decision,
                    analysis_data,
                    reasoning_board,
                )
                result.update({
                    "response_strategy": {},
                    "auditor_instruction": new_decision.get("instruction", ""),
                    "auditor_decision": new_decision,
                    "self_correction_memo": new_decision.get("memo", ""),
                    "war_room": war_room,
                    "speaker_review": speaker_review,
                })
                return result

            new_decision = base_nodes._make_auditor_decision("answer_not_ready", memo=remand_memo + " 지금은 한계를 분명히 밝히는 편이 더 안전합니다.")
            war_room = base_nodes._war_room_after_judge(
                base_nodes._normalize_war_room_state(result.get("war_room", {})),
                new_decision,
                analysis_data,
                reasoning_board,
            )
            result.update({
                "response_strategy": base_nodes._answer_not_ready_strategy(user_input, war_room),
                "auditor_instruction": new_decision.get("instruction", ""),
                "auditor_decision": new_decision,
                "self_correction_memo": new_decision.get("memo", ""),
                "war_room": war_room,
                "speaker_review": speaker_review,
            })
            return result

        result["response_strategy"] = prepared_strategy
        result["speaker_review"] = speaker_review
        return result

    if action == "answer_not_ready":
        judge_speaker_packet = base_nodes._build_judge_speaker_packet(
            reasoning_board=reasoning_board,
            response_strategy=result.get("response_strategy", {}),
            phase3_reference_policy=base_nodes._phase3_reference_policy(search_results, loop_count),
        )
        result["speaker_review"] = base_nodes._build_speaker_review(
            judge_speaker_packet,
            user_input=user_input,
            recent_context_excerpt=base_nodes._phase3_recent_context_excerpt(recent_context),
        )

    return result


def phase_3_validator_with_speaker_guard(state: AnimaState):
    response_strategy = state.get("response_strategy", {})
    reasoning_board = state.get("reasoning_board", {})
    loop_count = state.get("loop_count", 0)
    recent_context_excerpt = base_nodes._phase3_recent_context_excerpt(state.get("recent_context", ""))
    judge_speaker_packet = base_nodes._build_judge_speaker_packet(
        reasoning_board=reasoning_board,
        response_strategy=response_strategy,
        phase3_reference_policy=base_nodes._phase3_reference_policy(state.get("search_results", ""), loop_count),
    )
    speaker_review = base_nodes._build_speaker_review(
        judge_speaker_packet,
        user_input=state.get("user_input", ""),
        recent_context_excerpt=recent_context_excerpt,
    )

    if speaker_review.get("should_remand"):
        print("[Phase 3] 판사 공개본 송달이 약해 안전한 응답으로 접지합니다.")
        safe_response = str(judge_speaker_packet.get("followup_instruction") or judge_speaker_packet.get("final_answer_brief") or "").strip()
        if not safe_response:
            if str(judge_speaker_packet.get("reply_mode") or "").strip() == "ask_user_question_now":
                safe_response = base_nodes._assistant_question_seed(state.get("user_input", ""), state.get("working_memory", {}))
            else:
                safe_response = "지금은 제가 바로 단정하기보다, 확인하고 싶은 지점을 한 줄로 좁혀주시면 그 부분부터 정확히 맞추겠습니다."
        return {
            "messages": [AIMessage(content=base_nodes._normalize_user_facing_text(safe_response))],
            "speaker_review": speaker_review,
        }

    result = base_nodes.phase_3_validator(state)
    if not isinstance(result, dict):
        return result

    messages = result.get("messages", [])
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, AIMessage):
            normalized_text = base_nodes._normalize_user_facing_text(last_message.content)
            if base_nodes._looks_like_internal_delivery_leak(normalized_text):
                speaker_review = dict(speaker_review)
                speaker_review["delivery_ok"] = False
                speaker_review["should_remand"] = True
                issues = speaker_review.get("issues", [])
                if isinstance(issues, list):
                    issues.append("최종 출력에 내부 역할 용어가 섞여 있어 안전한 문장으로 교체했습니다.")
                    speaker_review["issues"] = base_nodes._dedupe_keep_order([str(item).strip() for item in issues if str(item).strip()])
                safe_response = str(judge_speaker_packet.get("followup_instruction") or judge_speaker_packet.get("final_answer_brief") or "").strip()
                if not safe_response:
                    safe_response = "지금은 제가 바로 단정하기보다, 확인하고 싶은 지점을 한 줄로 좁혀주시면 그 부분부터 정확히 맞추겠습니다."
                result["messages"] = [AIMessage(content=base_nodes._normalize_user_facing_text(safe_response))]
            else:
                result["messages"] = [AIMessage(content=normalized_text)]

    result["speaker_review"] = speaker_review
    return result
