import sys
import os
import time
import datetime
from dotenv import load_dotenv
from langchain_core.messages import messages_to_dict
import json

# 👇 [신체제 랭그래프 엔진 수입!]
from Core.graph import anima_app
from Core.state import AnimaState, normalize_anima_state
from Core.evidence_ledger import build_initial_evidence_ledger

from Core.brain_metabolism import Brain      
from Core.memory_buffer import MemoryBuffer  
from Core.biolink import BioLink             
from Core.inference_buffer import InferenceBuffer
from Core.field_memo import build_field_memo_candidate, persist_field_memo
from Core.memory.memory_sanitizer import (
    looks_like_internal_memory_text,
    sanitize_durable_turn_record,
    sanitize_memory_text,
    sanitize_memory_trace_value,
)
from Core.runtime import cleanup_turn_lived_fields
from Core.utils import get_token_count, get_time_gap
from Core.adapters.neo4j_connection import get_db_session
from Core.adapters.night_queries import recent_tactical_briefing

load_dotenv()

class SongRyeonAgentV5:
    def __init__(self):
        print("⚙️ [System] ANIMA V5.0 랭그래프 지휘소 가동 준비 완료!")
        self.brain = Brain()
        memory_model = os.getenv("ANIMA_MEMORY_MODEL", "gemma4:e4b").strip() or "gemma4:e4b"
        print(f"[ANIMA Models] memory={memory_model}")
        self.memory = MemoryBuffer(model_name=memory_model, max_context=30)
        self.scratchpad = InferenceBuffer()
        self.biolink = BioLink()   
        self.name = "송련" 
        self.last_timestamp = time.time()

    def _scan_dual_core_soul(self):
        cypher = """
        MATCH (u:Person {name: "허정후"})-[r:COMMANDS]->(ego:CoreEgo {name: "송련"})
        OPTIONAL MATCH (ego)-[:BELIEVES]->(t:Thought)
        WITH u, ego, t ORDER BY t.weight DESC LIMIT 3
        RETURN u.state AS user_state, u.characteristic AS user_char, ego.global_tolerance AS tolerance, collect(t.content) AS thoughts
        """
        try:
            with get_db_session() as session:
                record = session.run(cypher).single()
                if record:
                    thoughts_list = record["thoughts"]
                    thoughts_str = "\n".join([f"✔️ {th}" for th in thoughts_list]) if thoughts_list and thoughts_list[0] else "✔️ 사상 없음"
                    return {"user_state": record["user_state"], "user_char": record["user_char"], "tolerance": record["tolerance"], "songryeon_thoughts": thoughts_str}
        except Exception as e:
            print(f"💥 듀얼 코어 스캔 실패: {e}")
        return {"user_state": "알 수 없음", "user_char": "알 수 없음", "tolerance": 0.2, "songryeon_thoughts": "사상 없음"}

    def _connect_dream_to_source(self, dream_id: str, final_state: dict):
        """
        [GraphRAG 순정판]: 1차가 서류철(used_sources)에 남겨둔 ID 배열을 싹 다 가져와서 1차 꿈(Dream)과 용접합니다!
        """
        # 💡 [핵심 수술]: candidate_board(구체제) 대신 used_sources(신체제)를 꺼냅니다!
        used_sources = final_state.get("used_sources", [])

        if not used_sources:
            print("ℹ️ [System] 이번 턴에는 1차 수색대가 긁어온 과거 원본(ID)이 없습니다. 용접 생략.")
            return

        print(f"🔗 [GraphRAG] 1차 꿈(Dream)과 읽혀진 후보 노드 {len(used_sources)}개 전체 용접 시작...")

        # V5.0에서는 단순 배열이므로, 가중치(weight)를 기본값 1.0으로 통일해서 딕셔너리 리스트로 묶어줍니다.
        sources_with_weights = [{"id": t_id, "weight": 1.0} for t_id in used_sources]

        # Cypher 쿼리 (변경 없음! 완벽합니다!)
        query = """
        MATCH (dr:Dream {id: $dream_id})
        UNWIND $sources AS src
        
        MATCH (target) 
        WHERE target.date = src.id OR target.node_id = src.id OR target.id = src.id
        
        // 검색된 모든 후보군과 다이렉트 연결!
        MERGE (dr)-[r:BASED_ON]->(target)
        SET r.weight = src.weight, 
            r.connected_at = timestamp()
            
        // 💡 중요도 상승!
        SET target.importance_score = coalesce(target.importance_score, 0) + (src.weight * 0.5)
        
        RETURN count(r) AS connected_count
        """
        
        try:
            with get_db_session() as session:
                result = session.run(query, dream_id=dream_id, sources=sources_with_weights)
                count = result.single()["connected_count"]
                print(f"✨ [GraphRAG 대성공] 1차 꿈이 {count}개의 모든 후보 노드와 완벽하게 용접되었습니다!")
        except Exception as e:
            print(f"🚨 1차 꿈 용접 실패: {e}")

    def _truncate_text(self, value, limit: int = 320):
        if value is None:
            return ""
        text = str(value).strip()
        if len(text) <= limit:
            return text
        return text[: max(limit - 3, 0)].rstrip() + "..."

    def _looks_like_internal_memory_text(self, value) -> bool:
        return looks_like_internal_memory_text(value)

    def _memory_storage_text(self, value, limit: int = 320):
        return self._truncate_text(sanitize_memory_text(value), limit=limit)

    def _memory_storage_fact_summary(self, analysis_report: dict, user_input: str, limit: int = 320):
        facts = []
        if isinstance(analysis_report, dict):
            for key in ("current_turn_facts", "usable_field_memo_facts", "accepted_facts", "verified_facts"):
                values = analysis_report.get(key, [])
                if isinstance(values, list):
                    facts.extend(str(item).strip() for item in values if str(item).strip())
            for evidence in analysis_report.get("evidences", []) or []:
                if isinstance(evidence, dict):
                    fact = str(evidence.get("extracted_fact") or "").strip()
                    if fact:
                        facts.append(fact)
            for judgment in analysis_report.get("source_judgments", []) or []:
                if isinstance(judgment, dict):
                    facts.extend(str(item).strip() for item in judgment.get("accepted_facts", []) or [] if str(item).strip())
        facts = [fact for fact in dict.fromkeys(facts) if not self._looks_like_internal_memory_text(fact)]
        if facts:
            return self._truncate_text(" / ".join(facts[:3]), limit=limit)
        return self._memory_storage_text(user_input, limit=limit)

    def _sanitize_memory_trace_value(self, value, key: str = ""):
        return sanitize_memory_trace_value(value, key=key)

    def _first_text(self, data: dict, *keys: str, limit: int = 320):
        if not isinstance(data, dict):
            return ""
        for key in keys:
            value = data.get(key)
            if value:
                return self._truncate_text(value, limit=limit)
        return ""

    def _build_phase_snapshots(self, final_state: dict, working_memory_snapshot: dict):
        snapshots = []

        def add_snapshot(phase_name: str, phase_order: int, status: str, summary: str, payload: dict):
            normalized_payload = payload if isinstance(payload, dict) else {}
            normalized_payload = self._sanitize_memory_trace_value(normalized_payload, key="phase_payload")
            if not normalized_payload and not str(summary or "").strip():
                return
            safe_summary = self._memory_storage_text(summary, limit=420)
            if not safe_summary and normalized_payload:
                safe_summary = "activity_record"
            snapshots.append({
                "phase_name": phase_name,
                "phase_order": phase_order,
                "status": str(status or "").strip(),
                "summary": safe_summary,
                "payload": normalized_payload,
            })

        start_gate_review = final_state.get("start_gate_review", {})
        start_gate_switches = final_state.get("start_gate_switches", {})
        if isinstance(start_gate_review, dict) or isinstance(start_gate_switches, dict):
            answerability = str(start_gate_review.get("answerability") or "").strip() if isinstance(start_gate_review, dict) else ""
            recommended_handler = str(start_gate_review.get("recommended_handler") or "").strip() if isinstance(start_gate_review, dict) else ""
            why_short = str(start_gate_review.get("why_short") or "").strip() if isinstance(start_gate_review, dict) else ""
            add_snapshot(
                "-1s_start_gate",
                10,
                answerability or "evaluated",
                f"{answerability or 'coarse_gate'} -> {recommended_handler or 'unspecified'} | {why_short}".strip(" |"),
                {
                    "review": start_gate_review if isinstance(start_gate_review, dict) else {},
                    "switches": start_gate_switches if isinstance(start_gate_switches, dict) else {},
                },
            )

        ops_decision = final_state.get("ops_decision", {})
        execution_status = str(final_state.get("execution_status") or "").strip()
        execution_block_reason = str(final_state.get("execution_block_reason") or "").strip()
        if isinstance(ops_decision, dict) or execution_status:
            add_snapshot(
                "0_supervisor",
                20,
                execution_status or "evaluated",
                " | ".join(
                    part for part in [
                        execution_status or "switchboard",
                        self._first_text(ops_decision, "decision_mode", "next_hop", limit=120),
                        execution_block_reason,
                    ] if part
                ),
                {
                    "ops_decision": ops_decision if isinstance(ops_decision, dict) else {},
                    "execution_status": execution_status,
                    "execution_block_reason": execution_block_reason,
                },
            )

        strategist_output = final_state.get("strategist_output", {})
        response_strategy = final_state.get("response_strategy", {})
        reasoning_board = final_state.get("reasoning_board", {})
        if isinstance(strategist_output, dict) or isinstance(response_strategy, dict):
            action_plan = strategist_output.get("action_plan", {}) if isinstance(strategist_output, dict) else {}
            add_snapshot(
                "-1a_thinker",
                30,
                str(strategist_output.get("convergence_state") or "").strip() if isinstance(strategist_output, dict) else "planned",
                " | ".join(
                    part for part in [
                        self._first_text(action_plan, "current_step_goal", limit=220),
                        self._first_text(strategist_output, "delivery_readiness", limit=120),
                        f"candidate_pairs={len(reasoning_board.get('candidate_pairs', []))}" if isinstance(reasoning_board, dict) else "",
                    ] if part
                ),
                {
                    "goal_lock": strategist_output.get("goal_lock", {}) if isinstance(strategist_output, dict) else {},
                    "action_plan": action_plan if isinstance(action_plan, dict) else {},
                    "delivery_readiness": str(strategist_output.get("delivery_readiness") or "").strip() if isinstance(strategist_output, dict) else "",
                    "response_strategy": response_strategy if isinstance(response_strategy, dict) else {},
                },
            )

        raw_read_report = final_state.get("raw_read_report", {})
        if isinstance(raw_read_report, dict) and raw_read_report:
            add_snapshot(
                "phase_2a_reader",
                40,
                self._first_text(raw_read_report, "status", "read_mode", limit=120) or "read",
                self._first_text(raw_read_report, "source_summary", "coverage_notes", "summary", limit=260),
                raw_read_report,
            )

        analysis_report = final_state.get("analysis_report", {})
        if isinstance(analysis_report, dict) and analysis_report:
            add_snapshot(
                "phase_2_analyzer",
                50,
                self._first_text(analysis_report, "investigation_status", "status", limit=120) or "analyzed",
                self._first_text(analysis_report, "summary", "analysis_summary", "answer_brief", "coverage_notes", limit=260),
                analysis_report,
            )

        auditor_decision = final_state.get("auditor_decision", {})
        execution_trace = final_state.get("execution_trace", {})
        progress_markers = final_state.get("progress_markers", {})
        if isinstance(auditor_decision, dict) and auditor_decision:
            add_snapshot(
                "-1b_auditor",
                60,
                str(auditor_decision.get("action") or "").strip() or "audited",
                self._truncate_text(auditor_decision.get("memo") or "", limit=320),
                {
                    "decision": auditor_decision,
                    "execution_trace": execution_trace if isinstance(execution_trace, dict) else {},
                    "progress_markers": progress_markers if isinstance(progress_markers, dict) else {},
                },
            )

        speaker_review = final_state.get("speaker_review", {})
        delivery_status = str(final_state.get("delivery_status") or "").strip()
        if isinstance(speaker_review, dict) or delivery_status:
            add_snapshot(
                "phase_3_validator",
                70,
                delivery_status or ("remand" if isinstance(speaker_review, dict) and speaker_review.get("should_remand") else "prepared"),
                self._first_text(speaker_review, "safe_reply_candidate", "review_note", "suggested_action", limit=260),
                {
                    "speaker_review": speaker_review if isinstance(speaker_review, dict) else {},
                    "delivery_status": delivery_status,
                },
            )

        return snapshots

    def _build_canonical_turn_record(self, user_input: str, final_answer: str, final_state: dict, working_memory_snapshot: dict):
        analysis_report = final_state.get("analysis_report", {})
        if not isinstance(analysis_report, dict):
            analysis_report = {}
        strategist_output = final_state.get("strategist_output", {})
        if not isinstance(strategist_output, dict):
            strategist_output = {}
        response_strategy = final_state.get("response_strategy", {})
        if not isinstance(response_strategy, dict):
            response_strategy = {}

        dialogue_state = working_memory_snapshot.get("dialogue_state", {}) if isinstance(working_memory_snapshot.get("dialogue_state"), dict) else {}
        response_contract = working_memory_snapshot.get("response_contract", {}) if isinstance(working_memory_snapshot.get("response_contract"), dict) else {}
        execution_trace = final_state.get("execution_trace", {}) if isinstance(final_state.get("execution_trace"), dict) else {}
        ops_decision = final_state.get("ops_decision", {}) if isinstance(final_state.get("ops_decision"), dict) else {}
        auditor_decision = final_state.get("auditor_decision", {}) if isinstance(final_state.get("auditor_decision"), dict) else {}

        requested_move = str(dialogue_state.get("requested_move") or analysis_report.get("requested_assistant_move") or "").strip()
        goal_lock = strategist_output.get("goal_lock", {}) if isinstance(strategist_output.get("goal_lock"), dict) else {}
        answer_shape = str(goal_lock.get("answer_shape") or response_strategy.get("answer_shape") or "").strip()
        turn_summary = self._memory_storage_text(working_memory_snapshot.get("turn_summary", ""), limit=320)
        active_task = self._memory_storage_text(dialogue_state.get("active_task", ""), limit=220)
        active_offer = self._memory_storage_text(dialogue_state.get("active_offer", ""), limit=220)
        if not turn_summary:
            turn_summary = self._memory_storage_fact_summary(analysis_report, user_input, limit=320)
        used_sources = list(final_state.get("used_sources", [])) if isinstance(final_state.get("used_sources"), list) else []

        dream_record = {
            "schema_version": "dream_v3",
            "turn_summary": turn_summary,
            "user_input": user_input,
            "final_answer": final_answer,
            "user_dialogue_act": str(dialogue_state.get("user_dialogue_act") or "").strip(),
            "active_task": active_task,
            "active_offer": active_offer,
            "requested_move": requested_move,
            "answer_shape": answer_shape,
            "reply_mode": str(response_contract.get("reply_mode") or "").strip(),
            "verdict_action": str(analysis_report.get("verdict_action") or "").strip(),
            "investigation_status": str(analysis_report.get("investigation_status") or "").strip(),
            "delivery_status": str(final_state.get("delivery_status") or "").strip(),
            "used_sources": used_sources,
        }
        turn_process = {
            "schema_version": "turn_process_v1",
            "process_kind": "field_turn_pipeline",
            "turn_summary": turn_summary,
            "active_task": active_task,
            "active_offer": active_offer,
            "requested_move": requested_move,
            "answer_shape": answer_shape,
            "loop_count": int(final_state.get("loop_count", 0) or 0),
            "reasoning_budget": int(final_state.get("reasoning_budget", 0) or 0),
            "delivery_status": str(final_state.get("delivery_status") or "").strip(),
            "execution_status": str(final_state.get("execution_status") or "").strip(),
            "execution_block_reason": str(final_state.get("execution_block_reason") or "").strip(),
            "operation_kind": str(execution_trace.get("operation_kind") or "").strip(),
            "target_scope": str(execution_trace.get("target_scope") or "").strip(),
            "executed_tool": str(execution_trace.get("executed_tool") or "").strip(),
            "used_sources": used_sources,
            "field_status": {
                "start_gate": "ready" if final_state.get("start_gate_review") else "empty",
                "ops": "ready" if ops_decision else "empty",
                "strategist": "ready" if strategist_output else "empty",
                "reader": "ready" if final_state.get("raw_read_report") else "empty",
                "analyzer": "ready" if analysis_report else "empty",
                "auditor": "ready" if auditor_decision else "empty",
                "speaker": "ready" if final_state.get("speaker_review") else "empty",
            },
            "handoff_summary": {
                "ops_next_hop": str(ops_decision.get("next_hop") or "").strip(),
                "ops_mode": str(ops_decision.get("decision_mode") or "").strip(),
                "auditor_action": str(auditor_decision.get("action") or "").strip(),
            },
        }
        dream_record = sanitize_durable_turn_record(dream_record)
        turn_process = sanitize_durable_turn_record(turn_process)

        return {
            "schema_version": "dream_v3",
            "dream_record": dream_record,
            "turn_process": turn_process,
            "phase_snapshots": self._build_phase_snapshots(final_state, working_memory_snapshot),
        }

    # 🚀 [V5.0 메인 엔진 가동 메서드]
    def process_turn(self, user_input):
        print("\n==================================================")
        print("🏛️ [State Machine] V5.0 랭그래프 신경망 개시")
        print("==================================================\n")

        # 1. 첩보 수집 (서류철에 넣을 데이터들 긁어오기)
        now_time = datetime.datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
        current_time_gap = get_time_gap(self.last_timestamp)
        vertical_state = self._scan_dual_core_soul()
        bio_status_report = self.biolink.get_current_status(self.brain.body)
        tactical_briefing = recent_tactical_briefing(8)
        working_memory_snapshot = self.memory.get_working_memory_snapshot_for_input(user_input)
        full_recent_context = self.memory.get_tactical_context(user_input)

        # 2. 🌟 대망의 [초기 서류철 세팅] (AnimaState 규격에 맞춤!)
        initial_state: AnimaState = {
            "user_input": user_input,
            "current_time": now_time,
            "time_gap": current_time_gap,
            "recent_context": full_recent_context,
            "global_tolerance": vertical_state.get('tolerance', 1.0),
            
            "user_state": vertical_state.get('user_state', '알 수 없음'),
            "user_char": vertical_state.get('user_char', '알 수 없음'),
            "songryeon_thoughts": vertical_state.get('songryeon_thoughts', '사상 없음'),
            "tactical_briefing": tactical_briefing,
            "biolink_status": bio_status_report,
            "working_memory": working_memory_snapshot,
            "reasoning_board": {},
            "war_room": {},
            "speaker_review": {},
            "start_gate_review": {},
            "start_gate_switches": {},
            "s_thinking_packet": {},
            "ops_decision": {},
            "critic_lens_packet": {},
            "strategist_objection_packet": {},
            "delivery_status": "",
            "reasoning_budget": 0,
            "reasoning_plan": {},
            "progress_markers": {},
            "readiness_decision": {},
            "evidence_ledger": build_initial_evidence_ledger(
                user_input=user_input,
                current_time=now_time,
                recent_context=full_recent_context,
                user_state=vertical_state.get('user_state', '알 수 없음'),
                user_char=vertical_state.get('user_char', '알 수 없음'),
                songryeon_thoughts=vertical_state.get('songryeon_thoughts', '사상 없음'),
                biolink_status=bio_status_report,
                working_memory=working_memory_snapshot,
            ),
            
            # 👇 [V8.0 수술]: 낡은 router_report를 버리고 3대 신규 바구니를 장착합니다!
            "thought_logs": [],
            "strategist_output": {},
            "response_strategy": {},
            "auditor_instruction": "",
            "auditor_decision": {},
            "self_correction_memo": "",
            
            "supervisor_instructions": "",
            "execution_status": "",
            "execution_block_reason": "",
            "execution_trace": {},
            "tool_carryover": {},
            "search_results": "",
            "raw_read_report": {},
            "analysis_report": {}, # 👈 문자열("")이 아니라 빈 딕셔너리({})로 세팅해야 안전합니다!
            "rescue_handoff_packet": {},
            "phase3_delivery_packet": {},
            "delivery_review": {},
            "delivery_review_context": {},
            "loop_count": 0,
            "executed_actions": [],
            "tool_result_cache": {},
            "used_sources": [],
            "messages": []
        }

        # 3. 💥 랭그래프 엔진 점화!!! 
        initial_state = normalize_anima_state(initial_state)
        final_state = anima_app.invoke(
        initial_state, 
        config={"recursion_limit": 50} 
        )

        # 4. 💡 3차의 답변 추출
        if final_state.get("messages"):
            final_answer = final_state["messages"][-1].content
        else:
            final_answer = "개발자님, 신경망 처리 중 응답을 생성하지 못했습니다."

        print(f"\n🤖 {self.name} (응답): \n{final_answer}\n")

        # 5. 기억 탱크 업데이트
        # 5. 기억 탱크 업데이트
        self.memory.add_message("user", user_input)
        self.memory.add_message("assistant", final_answer)
        working_memory_snapshot = self.memory.commit_turn_state(final_state, user_input, final_answer)
        canonical_turn = self._build_canonical_turn_record(
            user_input=user_input,
            final_answer=final_answer,
            final_state=final_state,
            working_memory_snapshot=working_memory_snapshot,
        )
        field_memo_candidate = None
        try:
            field_memo_candidate = build_field_memo_candidate(
                final_state,
                user_input,
                final_answer,
                working_memory_snapshot,
                canonical_turn,
                recent_context=full_recent_context,
            )
        except Exception as e:
            print(f"[FieldMemo] 후보 생성 실패: {e}")

        # 6. 💾 위대한 듀얼 DB 라이터 가동!
        bio_status_str = json.dumps({"stats": self.brain.body.stats, "full_log": "V5.0 LangGraph"}, ensure_ascii=False)
        
        # 💡 [JSON 폭발 완벽 방어막]
        # final_state의 모든 요소를 검사하여, 메시지 객체는 안전한 딕셔너리로 강제 변환합니다!
        safe_trace_data = {}
        for key, value in final_state.items():
            if key == "messages":
                safe_trace_data[key] = messages_to_dict(value)
            else:
                safe_trace_data[key] = self._sanitize_memory_trace_value(value, key=key)
        safe_trace_data["working_memory_snapshot"] = self._sanitize_memory_trace_value(
            working_memory_snapshot,
            key="working_memory_snapshot",
        )
        safe_trace_data["canonical_turn"] = self._sanitize_memory_trace_value(canonical_turn, key="canonical_turn")
        safe_trace_data["dream_record"] = self._sanitize_memory_trace_value(canonical_turn.get("dream_record", {}), key="dream_record")
        safe_trace_data["turn_process"] = self._sanitize_memory_trace_value(canonical_turn.get("turn_process", {}), key="turn_process")
        safe_trace_data["phase_snapshots"] = self._sanitize_memory_trace_value(canonical_turn.get("phase_snapshots", []), key="phase_snapshots")
        safe_trace_data["field_memo_candidate"] = self._sanitize_memory_trace_value(field_memo_candidate or {}, key="field_memo_candidate")

        dream_id = self.scratchpad.save_dream_to_db(
            user_input=user_input,           
            final_answer=final_answer, 
            user_emotion="상태 추론 엔진 이관", 
            biolink_status=bio_status_str,
            trace_data=safe_trace_data  # 👈 완벽하게 소독된 무균 복사본 투척!
        )

        if field_memo_candidate:
            persist_field_memo(field_memo_candidate, dream_id=dream_id, canonical_turn=canonical_turn)
        self._connect_dream_to_source(dream_id, final_state)
        cleaned_final_state = cleanup_turn_lived_fields(final_state)
        final_state.clear()
        final_state.update(cleaned_final_state)
        self.last_timestamp = time.time()

if __name__ == "__main__":
    agent = SongRyeonAgentV5()
    print("\n🖥️  [Terminal] ANIMA V5.0 구동 완료. 입력 대기 중... (종료: exit)")
    while True:
        try:
            user_cmd = input("\n👤 사용자: ").strip()
            if not user_cmd: continue
            if user_cmd.lower() in ['exit', 'quit']: break
            agent.process_turn(user_cmd)
        except KeyboardInterrupt:
            print("\n🚨 시스템 강제 종료.")
            break
