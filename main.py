import sys
import os
import time
import datetime
from dotenv import load_dotenv
from langchain_core.messages import messages_to_dict
import json

# 👇 [신체제 랭그래프 엔진 수입!]
from Core.graph import anima_app
from Core.state import AnimaState

# 👇 [구체제의 위대한 유산들 수입]
from Core.brain_metabolism import Brain      
from Core.memory_buffer import MemoryBuffer  
from Core.biolink import BioLink             
from Core.inference_buffer import InferenceBuffer
from Core.utils import get_token_count, get_time_gap
from tools.toolbox import get_db_session, recent_tactical_briefing

load_dotenv()

class SongRyeonAgentV5:
    def __init__(self):
        print("⚙️ [System] ANIMA V5.0 랭그래프 지휘소 가동 준비 완료!")
        self.brain = Brain()       
        self.memory = MemoryBuffer(model_name="gemma3:12b", max_context=30) 
        self.scratchpad = InferenceBuffer()
        self.biolink = BioLink()   
        self.name = "송련" 
        self.last_timestamp = time.time()

    # 👻 [위대한 유산 1]: 사상 및 상태 스캔 (기존 코드 그대로 유지!)
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
        reasoning_board = final_state.get("reasoning_board", {})
        if not isinstance(reasoning_board, dict):
            reasoning_board = {}

        return {
            "schema_version": "dream_v2",
            "user_input": user_input,
            "final_answer": final_answer,
            "routing": {
                "auditor_instruction": final_state.get("auditor_instruction", ""),
                "auditor_decision": final_state.get("auditor_decision", {}),
                "self_correction_memo": final_state.get("self_correction_memo", ""),
                "loop_count": final_state.get("loop_count", 0),
                "supervisor_instructions": final_state.get("supervisor_instructions", ""),
            },
            "dialogue_state": working_memory_snapshot.get("dialogue_state", {}),
            "evidence_state": working_memory_snapshot.get("evidence_state", {}),
            "response_contract": working_memory_snapshot.get("response_contract", {}),
            "reasoning_meta": {
                "reasoning_budget": final_state.get("reasoning_budget", 0),
                "reasoning_plan": final_state.get("reasoning_plan", {}),
            },
            "reasoning_board": reasoning_board,
            "war_room": final_state.get("war_room", {}),
            "speaker_review": final_state.get("speaker_review", {}),
            "debate_state": {
                "critic_report": reasoning_board.get("critic_report", {}),
                "advocate_report": reasoning_board.get("advocate_report", {}),
                "verdict_board": reasoning_board.get("verdict_board", {}),
            },
            "investigation": {
                "raw_read_report": final_state.get("raw_read_report", {}),
                "analysis_report": analysis_report,
                "used_sources": final_state.get("used_sources", []),
                "executed_actions": final_state.get("executed_actions", []),
                "search_results_excerpt": str(final_state.get("search_results", "") or "")[:2000],
            },
            "memory_writeback": {
                "turn_summary": working_memory_snapshot.get("turn_summary", ""),
                "working_memory": working_memory_snapshot,
            },
            "strategist_output": strategist_output,
            "response_strategy": response_strategy,
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
        full_recent_context = self.memory.get_tactical_context()
        working_memory_snapshot = self.memory.get_working_memory_snapshot()

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
            "reasoning_budget": 0,
            "reasoning_plan": {},
            
            # 👇 [V8.0 수술]: 낡은 router_report를 버리고 3대 신규 바구니를 장착합니다!
            "thought_logs": [],
            "strategist_output": {},
            "response_strategy": {},
            "auditor_instruction": "",
            "auditor_decision": {},
            "self_correction_memo": "",
            
            "supervisor_instructions": "",
            "search_results": "",
            "raw_read_report": {},
            "analysis_report": {}, # 👈 문자열("")이 아니라 빈 딕셔너리({})로 세팅해야 안전합니다!
            "loop_count": 0,
            "executed_actions": [],
            "used_sources": [],
            "messages": []
        }

        # 3. 💥 랭그래프 엔진 점화!!! 
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

        # 6. 💾 위대한 듀얼 DB 라이터 가동!
        bio_status_str = json.dumps({"stats": self.brain.body.stats, "full_log": "V5.0 LangGraph"}, ensure_ascii=False)
        
        # 💡 [JSON 폭발 완벽 방어막]
        # final_state의 모든 요소를 검사하여, 메시지 객체는 안전한 딕셔너리로 강제 변환합니다!
        safe_trace_data = {}
        for key, value in final_state.items():
            if key == "messages":
                safe_trace_data[key] = messages_to_dict(value)
            else:
                safe_trace_data[key] = value
        safe_trace_data["working_memory_snapshot"] = working_memory_snapshot
        safe_trace_data["canonical_turn"] = canonical_turn

        dream_id = self.scratchpad.save_dream_to_db(
            user_input=user_input,           
            final_answer=final_answer, 
            user_emotion="상태 추론 엔진 이관", 
            biolink_status=bio_status_str,
            trace_data=safe_trace_data  # 👈 완벽하게 소독된 무균 복사본 투척!
        )

        self._connect_dream_to_source(dream_id, final_state)
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
