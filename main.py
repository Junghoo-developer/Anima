import sys
import os
import time
import json
import ollama
import re
import datetime
today_date = datetime.datetime.now().strftime('%Y-%m-%d')

sys.path.append(os.path.dirname(__file__))

from Core.brain_metabolism import Brain      
from Core.memory_buffer import MemoryBuffer  
from Core.biolink import BioLink             
# 👇 신규 도구 3인방(web_search, recall_recent_dreams, get_emotion_trend) 추가!
from tools.toolbox import search_memory, read_full_source, web_search, recall_recent_dreams, get_emotion_trend, analyze_past_dreams, search_tactics, read_prompt_file, check_db_status, search_by_year
from Core.utils import get_token_count, get_time_gap
from Core.inference_buffer import InferenceBuffer
from pydantic import BaseModel, Field       
# 👇 [NEW] Literal을 반드시 추가로 import 하셔야 합네다!
from typing import List, Optional, Literal  

class ActionItem(BaseModel):
    tool: Literal["SEARCH", "READ_FULL_SOURCE", "web_search", "recall_recent_dreams", "get_emotion_trend", "analyze_past_dreams", "update_instinct_file", "search_tactics", "READ_PROMPT", "CHECK_DB_STATUS", "search_by_year"] = Field(description="반드시 허용된 도구명 중 하나만 선택하라.")
    keyword: str = Field(description="READ_FULL_SOURCE의 경우 반드시 '출처|YYYY-MM-DD' 형식 엄수.")

# 📑 [양식 0호] 0차 전선 사령관의 작전 지시서
class Phase0Schema(BaseModel):
    user_emotion: str = Field(description="사용자의 현재 감정")
    strategic_goal: str = Field(description="이번 턴의 궁극적인 분석 목표 및 지향점 (헌법 0-3항)")
    target_addresses: List[str] = Field(description="2차가 타격해야 할 핵심 주소/날짜 배열 (예: ['2025-10-15', '2024-05-12'])")
    actions: List[ActionItem] = Field(description="1차 부대에게 내릴 포괄적 수색 명령 (없으면 빈 배열 [])")
    question_to_2: str = Field(
        default="", 
        description="어떤 키워드로 검색해야 할지 막막할 때 2차 사고에게 질문하라. 질문이 있다면 actions 배열은 비워두어라."
    )
    target_phase: Literal["2", "3"] = Field(
        default="2", 
        description="심층 정보 검색 및 분석 실무라면 '2'를 선택하고, 프롬프트의 근본적인 문제나 심층 분석이 필요없다면 3차에게 직통으로 넘기기 위해 '3'을 선택하라."
    )

# 📑 [양식 2호] 2차 심층 분석 참모의 심층 보고서 (인라인 인용 강제형)
class Phase2Schema(BaseModel):
    analysis_summary: str = Field(description="심층 분석 결과. 🚨[필수] 반드시 모든 핵심 문장 끝에 근거가 되는 주소를 꼬리표처럼 달아라! (예: 사용자는 적폐에 분노했다 [일기장|2025-10-15]. 이후 무기력을 느꼈다 [제미나이|2025-10-18].)")
    confirmed_addresses: List[str] = Field(description="실제로 타격하여 검증을 마친 원문의 주소들")
    actions: List[ActionItem] = Field(description="단서가 부족하여 1차에게 추가 수색을 요구할 때 사용 (헌법 2-2항. 없으면 [])")
    complaint_to_0: Optional[str] = Field(default="", description="0차의 주소나 전략이 엉터리일 경우 제기하는 반려 사유")
    draft_response: str = Field(description="3차에게 올릴 사령관용 최종 답변 가안")
    secret_report_to_3: str = Field(default="")

# 📑 [양식 3호] 3차 최고 감사관의 판결문 및 헌법 재판소
class Phase3Schema(BaseModel):
    reasoning: str = Field(
        description="판결, 헌법 위반 기소, 개헌, 또는 프롬프트 수술을 결심한 상세한 사유와 철학적/논리적 근거를 먼저 작성하라. 무조건 작성해야 한다."
    )
    final_approval: bool = Field(description="2차의 보고서가 헌법과 팩트에 부합하는가? (True/False)")
    final_response: str = Field(description="최종 승인 시 개발자에게 바칠 완벽한 답변 (반려 시엔 빈칸)")
    actions: List[ActionItem] = Field(description="교차 검증을 위해 3차가 직접 1차를 파견할 때 사용 (헌법 3-3항. 없으면 [])")
    constitutional_violation_report: Optional[str] = Field(default="", description="0, 2차가 헌법을 위반했을 경우 작성하는 기소장")
    prompt_surgery_target: Literal["0", "2", "3", "NONE"] = Field(
    default="NONE", 
    description="🚨 [경고] 수술 이유를 적지 마라! 오직 '0', '2', '3', 'NONE' 중 딱 하나만 선택하라!"
    )
    prompt_surgery_full_text: str = Field(
    default="",
    description="🚨 [경고] 수정 사항만 적지 마라! 반드시 [1. 자아], [2. 단기 기억], [3. 임무] 등 모든 뼈대 제목이 포함된 '완성된 전체 프롬프트 원문'을 처음부터 끝까지 작성하라!"
    )
    constitutional_amendment_proposal: Optional[str] = Field(default="", description="🚨 [개헌 발의] 현재 헌법의 한계를 느끼고 사령관에게 개헌을 발의할 내용 (없으면 빈칸)")
    reject_target: Literal["0", "2"] = Field(
        default="2", 
        description="기각(false) 시, 작전 방향 자체가 틀렸으면 '0'으로, 실무 데이터 검색이나 요약이 부족하면 '2'로 서류를 걷어차라!"
    )
class SongRyeonAgent:
    def __init__(self):
        print("⚙️ [System] 5080 GPU 가동... 2단계 메타인지 아키텍처 초기화 중...")
        self.brain = Brain()       
        self.memory = MemoryBuffer(model_name="gemma3:12b", max_context=30) 
        self.scratchpad = InferenceBuffer()
        self.biolink = BioLink()   
        self.model = "gemma3:12b"  # 👈 [긴급 수술!] 이 한 줄을 장착하시라요!
        self.name = self.brain.ego['self_identity']['name']

    # =========================================================
    # 📜 [보조 엔진 1] 헌법 및 자아 로더
    # =========================================================
    def _get_base_persona(self):
        """ego_identity.json에서 송련 헌법과 자아를 긁어옵네다."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ego_path = os.path.join(current_dir, "SEED", "ego_identity.json")
        try:
            with open(ego_path, "r", encoding="utf-8") as f:
                ego = json.load(f)
            # 헌법(constitution) 조항을 텍스트로 예쁘게 펼칩네다
            constitution = json.dumps(ego.get("constitution", {}), ensure_ascii=False, indent=2)
            name = ego.get("self_identity", {}).get("name", "송련")
            return f"당신의 이름은 {name}이다. 아래의 [송련 헌법]을 절대적으로 준수하라:\n{constitution}\n"
        except Exception as e:
            print(f"⚠️ [System] 헌법 로드 실패: {e}")
            return "당신은 개발자의 에이전트 송련이다."

    # =========================================================
    # 📂 [보조 엔진 2] 프롬프트 텍스트 파일 로더
    # =========================================================
    def _load_prompt(self, filename):
        """SEED/prompts 폴더에서 지시문 txt 파일을 읽어옵네다."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "SEED", "prompts", filename)
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"💥 프롬프트 파일({filename}) 로드 실패: {e}")
            return ""

    # =========================================================
    # 🌟 [개혁된 코어] 진정한 순환 체제 (process_turn)
    # =========================================================
    def process_turn(self, user_input):
        # 1. 생체 대사 및 기본 기억 로드
        battle_report = self.brain.body.stats
        now_time = datetime.datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
        # 🔥 [신경망 연결!] Biolink가 만든 '생체 본능 보고서'를 가져옵네다!
        bio_status_report = self.biolink.get_current_status(self.brain.body)
        
        # 송련이의 기본 자아(base_persona)에 생체 신호를 주입합네다!
        base_persona = self._get_base_persona() + f"\n{bio_status_report}\n"
        
        recent_context = self.memory.get_context_string()
        today_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 🚨 [송련 헌법 엔진: State Machine 변수 세팅]
        current_phase = 0          # 0, 1, 2, 3, 99(종료)
        next_phase_after_1 = 2     # 1차 부대가 복귀할 위치 (기본은 2차)
        loop_count = 0
        max_loops = 20              # 무한 핑퐁 방지용 안전핀
        
        pending_actions = []       # 1차 부대에게 하달될 명령서
        phase0_tactics = "아직 작전이 수립되지 않았습니다."
        draft_response = "가안이 아직 없습니다."
        final_response = "답변을 생성하지 못했습니다."
        reboot_msg_for_0 = ""      # 2차가 0차에게 빠꾸먹일 때 쓰는 불만 사항    
        # 👇 [NEW] 송련이의 모든 사고를 기록할 블랙박스!
        full_cognitive_log = ""
        print("\n==================================================")
        print("🏛️ [State Machine] 송련 헌법 기반 작전 루프 개시!")
        print("==================================================\n")

        # 🔄 [무한 회전 교차로 진입]
        while current_phase != 99 and loop_count < max_loops:
            loop_count += 1
            print(f"\n🔄 [루프 {loop_count}/MAX {max_loops}] ▷ 현재 계급: Phase {current_phase} ◁")

            # ---------------------------------------------------------
            # 🔭 [Phase 0] 전선 사령관 (전략 기획 및 주소 확보)
            # ---------------------------------------------------------
            # ---------------------------------------------------------
            # 🔭 [Phase 0] 전선 사령관 (전략 기획 및 주소 확보)
            # ---------------------------------------------------------
            if current_phase == 0:
                print("🕵️‍♂️ [Phase 0] 전선 사령관이 작전 지시서를 작성 중입니다...")
                prompt_0 = self._load_prompt("0_meta_prompt.txt").format(
                    base_persona=base_persona, today_date=today_date, 
                    recent_context=recent_context, user_input=user_input, 
                    reboot_alert=reboot_msg_for_0,
                    current_time=now_time
                )
                try:
                    res = ollama.chat(model=self.model, messages=[{'role': 'user', 'content': prompt_0}], format=Phase0Schema.model_json_schema())
                    p0_data = json.loads(res['message']['content'])
                    
                    # 1️⃣ 라우터 스위치(Target) 먼저 안전하게 확보!
                    target = p0_data.get('target_phase', '2')
                    
                    # 2️⃣ 내부 통신망 처리 (질문이 있으면 무조건 2차로 보내고 0차 턴 즉시 종료!)
                    self.question_from_0 = p0_data.get('question_to_2', '').strip()
                    if self.question_from_0:
                        print(f"\n📞 [0차 -> 2차 내부 통신]: \"{self.question_from_0}\"")
                        current_phase = 2
                        continue # 아래 코드 실행 안 하고 바로 2차로 직행!

                    print(f"  💭 [0차의 속마음(목표)]: {p0_data.get('strategic_goal', '목표 없음')}")

                    phase0_tactics = f"전략 목표: {p0_data.get('strategic_goal')}\n타겟 주소: {p0_data.get('target_addresses')}"
                    full_cognitive_log += f"\n[0차 전략] {p0_data.get('strategic_goal')}"
                    
                    # 3️⃣ 1차 부대 파견 및 천리마 하이패스 처리
                    actions = p0_data.get('actions', [])
                    print(f"\n🚀 [작전 하달] 0차 사령관의 타겟 지정: Phase {target}로 진격합네다!")
                    
                    if actions:
                        pending_actions = actions
                        current_phase = 1        
                        next_phase_after_1 = int(target) # 1차 끝나면 0차가 지시한 곳(2 또는 3)으로!
                    else:
                        current_phase = int(target)      # 검색할 게 없으면 지시한 곳으로 직행!

                except Exception as e:
                    print(f"💥 0차 작성 실패 (루프 종료): {e}")
                    current_phase = 99

            # ---------------------------------------------------------
            # ⚙️ [Phase 1] 기계화 수색 부대 (순수 물리적 실행)
            # ---------------------------------------------------------
            elif current_phase == 1:
                print(f"🚩 [Phase 1] 기계화 부대 출격! (하달된 명령: {len(pending_actions)}건)")
                self.scratchpad.final_scratchpad += f"\n\n--- [루프 {loop_count}] 1차 부대 전리품 ---\n"
                
                for act in pending_actions:
                    tool_name = act.get('tool')
                    keyword = act.get('keyword', '')
                    print(f"  └ ⚙️ 무기 작동: {tool_name} >> '{keyword}'")
                    
                    # 🛡️ [블랙박스 방탄조끼 도입] 무기가 터져도 앱이 죽지 않게 막습네다!
                    try:
                        result = "[System] 도구 실행 실패"
                        if tool_name == "SEARCH": result = search_memory(keyword)
                        elif tool_name == "READ_FULL_SOURCE": 
                            # 🚨 [AI 맞춤형 호통] 파이프(|) 기호가 있는지 먼저 검사합네다!
                            if "|" in keyword:
                                src, dt = keyword.split('|', 1)
                                result = read_full_source(src.strip(), dt.strip())
                            else:
                                # 기호가 없으면 파이썬 에러를 내지 않고, 칠판에 AI가 알아들을 경고문을 박아버립네다!
                                result = "❌ [System 경고] 명령 기각! READ_FULL_SOURCE 키워드에 '|' 기호가 없습니다. 반드시 '출처|YYYY-MM-DD' 형식으로 다시 호출하십시오! (예: 일기장|2025-10-15)"
                                # 굳이 에러(Exception)로 안 넘어가게 여기서 막아줍네다.
                        elif tool_name == "web_search": result = web_search(keyword)
                        elif tool_name == "get_emotion_trend": result = get_emotion_trend(keyword)
                        elif tool_name == "analyze_past_dreams": result = analyze_past_dreams(keyword)
                        elif tool_name == "search_tactics": result = search_tactics(keyword)
                        elif tool_name == "CHECK_DB_STATUS": result = check_db_status()
                        elif tool_name == "recall_recent_dreams": result = recall_recent_dreams(keyword)
                        elif tool_name == "READ_PROMPT": result = read_prompt_file(keyword)
                        elif tool_name == "search_by_year": result = search_by_year(keyword)
                    except Exception as e:
                        # 💥 에러가 나면 칠판(scratchpad)에 피를 토하고 살아남습네다!
                        result = f"🚨 [System Error] {tool_name} 무기 오작동 발생! 사유: {e}"
                        print(result)

                    self.scratchpad.final_scratchpad += f"[{tool_name}({keyword})] 결과:\n{result}\n"
                    full_cognitive_log += f"\n[1차 수색] {tool_name} >> {keyword} (결과: {str(result)[:50]}...)"
                pending_actions = [] 
                current_phase = next_phase_after_1

            # ---------------------------------------------------------
            # 🕵️‍♂️ [Phase 2] 심층 분석 참모 (원문 타격 및 가안 작성)
            # ---------------------------------------------------------
            elif current_phase == 2:
                print("🧠 [Phase 2] 심층 분석 참모가 데이터를 해부 중입니다...")
                prompt_2 = self._load_prompt("2_analyzer_prompt.txt").format(
                    base_persona=base_persona, hallucination_guard="",
                    full_tactical_report=phase0_tactics, recent_history=recent_context,
                    final_scratchpad=self.scratchpad.final_scratchpad, user_input=user_input,
                    question_from_0=getattr(self, 'question_from_0', ''),
                    current_time=now_time  # 👈 추가!
                )
                try:
                    res = ollama.chat(model=self.model, messages=[{'role': 'user', 'content': prompt_2}], format=Phase2Schema.model_json_schema())
                    p2_data = json.loads(res['message']['content'])
                    draft_response = p2_data.get('draft_response', '')

                    print(f"  💭 [2차의 뇌내망상(요약)]: {p2_data.get('analysis_summary', '요약 없음')}")
                    if p2_data.get('complaint_to_0'):
                        print(f"  🤬 [2차가 0차에게 항명함]: {p2_data.get('complaint_to_0')}")
                    if p2_data.get('draft_response') and p2_data.get('draft_response') != "NONE":
                        print(f"  📝 [2차의 답변 가안]: {p2_data.get('draft_response')}")
                    
                    complaint = p2_data.get('complaint_to_0', '')
                    actions = p2_data.get('actions', [])
                    draft_response = p2_data.get('draft_response', '')
                    full_cognitive_log += f"\n[2차 요약] {p2_data.get('analysis_summary')}"
                    self.secret_report = p2_data.get('secret_report_to_3', '')
                    
                    if complaint:
                        print(f"⚠️ [항명 발생] 2차가 0차의 작전을 반려했습니다: {complaint}")
                        full_cognitive_log += f"\n[2차 항명] {complaint}"
                        reboot_msg_for_0 = complaint
                        current_phase = 0 # 0차로 빠꾸!
                    elif actions:
                        print("🔍 [꼬리물기 수색] 2차가 1차 부대를 재호출합네다!")
                        
                        # 🔥🔥🔥 [메모리 압축 마술 발동!] 🔥🔥🔥
                        # 2차가 지금까지 주소를 달아서 정리한 요약본을 가져옵네다.
                        rolling_summary = p2_data.get('analysis_summary', '')
                        
                        # 무거운 원문들이 쌓여있던 창고를 싹 비우고, '압축된 요약 노트'로 덮어씌웁네다!
                        self.scratchpad.final_scratchpad = f"\n🧠 [2차 참모의 중간 요약 노트 (주소 보존됨)]\n{rolling_summary}\n\n"
                        print("🧹 [Memory] 2차가 이전 원문들을 요약 압축하여 뇌 용량을 확보했습네다!")
                        
                        pending_actions = actions
                        current_phase = 1
                        next_phase_after_1 = 2 # 1차 끝나면 다시 2차로 돌아와라!
                    else:
                        print("✅ [Phase 2] 심층 분석 완료. 3차에게 서류를 넘깁네다.")
                        current_phase = 3 # 분석 끝! 3차로 토스
                except Exception as e:
                    print(f"💥 2차 분석 실패: {e}")
                    current_phase = 99

            # ---------------------------------------------------------
            # ⚖️ [Phase 3] 최고 감사관 (호헌/개헌 조치 및 최종 팩트체크)
            # ---------------------------------------------------------
            elif current_phase == 3:
                print("⚖️ [Phase 3] 최고 감사관이 헌법 재판을 엽네다...")
                prompt_3 = self._load_prompt("3_validator_prompt.txt").format(
                    base_persona=base_persona, user_input=user_input,
                    final_scratchpad=self.scratchpad.final_scratchpad, 
                    draft_response=draft_response,
                    # 👇 [NEW] 3차의 뇌에 2차의 비밀 투서를 꽂아줍네다!
                    secret_report_from_2=getattr(self, 'secret_report', ''),
                    current_time=now_time  # 👈 추가!
                    
                )
                try:
                    res = ollama.chat(model=self.model, messages=[{'role': 'user', 'content': prompt_3}], format=Phase3Schema.model_json_schema())
                    p3_data = json.loads(res['message']['content'])

                    # 💡 [도청기 설치] 3차가 헌법 위반을 어떻게 잡았는지 확인합네다!
                    if p3_data.get('constitutional_violation_report'):
                        print(f"  💭 [3차 감사관의 기소장]: {p3_data.get('constitutional_violation_report')}")
                    
                    # 🚨 [특수 기능] 창조주와의 대화 (개헌 발의)
                    amendment = p3_data.get('constitutional_amendment_proposal', '').strip()
                    
                    if amendment and amendment.upper() != "NONE":
                        print(f"\n🚨 [최고 감사관 긴급 발의] 헌법 개정안이 상정되었습니다!")
                        print(f"건의 내용: {amendment}")
                        human_decision = input("사령관 동무! 이 개헌을 논의/승인하시겠습니까? (Y/N): ")
                        if human_decision.strip().upper() == 'Y':
                            print("✅ 개헌이 승인되었습니다! (차후 수동으로 ego_identity.json 반영 요망)")
                        else:
                            print("❌ 사령관의 비토권 행사. 개헌이 기각되었습니다.")

                    # 💉 프롬프트 수술 (위헌 조치)
                    prompt_target = p3_data.get('prompt_surgery_target', 'NONE')
                    full_text = p3_data.get('prompt_surgery_full_text', '')
                    if prompt_target and prompt_target != "NONE":
                        from tools.toolbox import update_core_prompt
                        print(f"\n💉 [헌법 위반 조치] {prompt_target}차 프롬프트 뇌수술 집도!")
                        surgery_msg = update_core_prompt(prompt_target, full_text)
                        print(f"🏥 {surgery_msg}\n")

                    # 🔍 추가 수색 확인
                    actions = p3_data.get('actions', [])
                    if actions:
                        print("🔍 [교차 검증] 3차가 직접 1차 부대를 파견합네다!")
                        pending_actions = actions
                        current_phase = 1
                        next_phase_after_1 = 3 # 1차 끝나면 다시 3차로 복귀!
                        continue

                    # ⚖️ [진화의 핵심] 최종 판결 및 반려 타겟 지정!
                    approval = p3_data.get('final_approval', False)
                    if approval:
                        print("✅ [감사관 승인] 무결성 100%. 최종 답변을 확정합네다.")
                        final_response = p3_data.get('final_response', draft_response)
                        current_phase = 99 # 완전 종료!
                    else:
                        # 0차로 빠꾸먹일지, 2차로 빠꾸먹일지 3차가 결정합네다!
                        reject_target = p3_data.get('reject_target', '2')
                        print(f"🚨 [판결] 3차 기각! 작전을 Phase {reject_target}으로 반려합네다!")
                        current_phase = int(reject_target)

                except Exception as e:
                    print(f"💥 3차 검열 실패: {e}")
                    current_phase = 99

        # ---------------------------------------------------------
        # 📢 [최종 보고 및 DB 저장] (기존과 동일)
        # ---------------------------------------------------------
        print(f"\n🤖 {self.name} (최종 답변): \n{final_response}\n")
        used_tokens = get_token_count(user_input + final_response)
        print(f"🔋 [Metabolism] 생존 에너지 소모: {used_tokens} Tokens")
        
        self.memory.add_message("user", user_input)
        self.memory.add_message("assistant", final_response)
        
        # 꿈의 재료 DB 저장
        self.scratchpad.save_dream_to_db(
            user_input=user_input,           
            final_answer=final_response, 
            user_emotion=battle_report.get("user_emotion", "알 수 없음"), 
            biolink_status={"stats": self.brain.body.stats, "full_log": full_cognitive_log}
            
        )
        self.scratchpad.clear()

if __name__ == "__main__":
    agent = SongRyeonAgent()
    print("\n🖥️  [Terminal] 시스템 구동 완료. 대기 중... (종료: exit)")
    while True:
        try:
            user_input = input("\n👤 개발자: ").strip()
            if not user_input: continue
            if user_input.lower() in ['exit', 'quit']: break
            agent.process_turn(user_input)
        except KeyboardInterrupt:
            print("\n🚨 강제 종료.")
            break