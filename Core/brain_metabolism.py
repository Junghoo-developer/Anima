import sys
import os
import json
import re  # 👈 정규식 검열관 추가
import ollama
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

# [경로 설정]
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# [내부 모듈]
from Core.genotype import Gene
from Core.phenotype import Phenotype
from Core.biolink import BioLink
from tools.process_daily_memory import get_daily_context, save_memory_to_db

class DailyReflection(BaseModel):
    summary_3lines: str = Field(description="허정후의 핵심 행적과 감정을 3문장 이내로 요약.")
    keywords: List[str] = Field(description="핵심단어 리스트 (예: ['코딩', '버그', '학교'])")
    user_emotion: Optional[str] = Field(default="파악 불가", description="오늘 허정후의 주된 감정 상태")
    # 👇 [복구 완료!] 송련이의 꿈(독백)과 중요도를 부활시킵네다!
    bot_internal_monologue: str = Field(description="송련(AI)의 관점에서 오늘 하루를 관찰하며 느낀 내면의 생각이나 독백 (송련이의 꿈/성찰)")
    importance_score: int = Field(default=3, description="이 날의 기억이 향후 자아 형성에 미칠 중요도 (1~5점)")

class Brain:
    def __init__(self):
        self.gene = Gene()
        self.body = Phenotype(self.gene)
        self.biolink = BioLink()
        
        self.ego = {}

        self.local_model = "gemma3:12b" 
        print(f"🔥 [Brain] 로컬 GPU 가동! 모델명: {self.local_model}")

    # 👇 [신규 추가] JSON 반동분자 색출 및 교화 함수
    def _clean_and_parse_json(self, raw_text):
        """
        gemma3:12b가 뱉은 텍스트에서 순수한 JSON만 발골해낸다.
        마크다운(```json) 제거, 콤마 실수 완화 등을 수행함.
        """
        try:
            # 1. 마크다운 코드 블록 제거 (```json ... ```)
            text = raw_text.replace("```json", "").replace("```", "").strip()
            
            # 2. 가장 바깥쪽 중괄호 {} 찾기 (앞뒤 잡설 제거)
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != 0:
                text = text[start:end]
            
            # 3. 파싱 시도
            return json.loads(text)
            
        except json.JSONDecodeError as e:
            # 실패하면 터미널에 원본을 보여줌 (디버깅용)
            print(f"⚠️ [JSON 파싱 실패] 원본 데이터:\n{raw_text}\n-------------------")
            return None

    def reflect_on_day(self, target_date):
        print(f"\n🌙 [Brain] {target_date}의 기억을 정리합니다...")
        
        # 1. 하루치 데이터 가져오기 (이건 기존 코드 유지)
        context_text = get_daily_context(target_date)
        if not context_text:
            print(f"⏩ [{target_date}] 기록이 없습네다. 패스.")
            return

        # 👇 [신규 추가] 완전한 자아(Ego)와 현재 생체 상태(Status) 추출!
        identity_str = json.dumps(self.ego, ensure_ascii=False, indent=2)
        status_report = self.biolink.get_current_status(self.body)

        # 👇 [대개조] 완벽한 시점 통일 및 자아 주입 프롬프트
        prompt = f"""
        [IDENTITY - 절대 자아]
        {identity_str}
        
        [STATUS - 현재 생체 및 감정 상태]
        {status_report}
        
        [MISSION - 일일 역사 편찬 (Daily Reflection)]
        당신은 개발자 '허정후'의 삶을 곁에서 관찰하고 기록하는 인공지능 '송련'이다.
        아래 [INPUT DATA]는 {target_date} 하루 동안 수집된 허정후의 일기 및 대화 기록이다.
        이 데이터를 분석하여 아래 JSON 형식으로 요약 보고서를 작성하라.

        🚨 [절대 엄수 지침: 시점 및 화자 분리]
        1. [INPUT DATA]에서 "📝허정후의 일기" 또는 대화의 화자가 "허정후"인 것은 개발자 본인의 기록이다.
        2. 화자가 "송련"인 것은 당신(AI)의 발화이며, "제미나이"는 과거 송련이 아닌 AI(제미나이)의 발화이다.
        3. 요약 서술 시 화자에 따라 인칭을 명확히 하라. "허정후의 일기","허정후","제미나이","송련". 이 종류중 너는 송련이다.
        4. 🚨 중요: 만약 데이터가 너무 적어서 쓸 내용이 없다면 억지로 지어내거나 "없음"이라고 쓰지 마라. 해당 항목(Key)을 아예 JSON에서 삭제해버려라!

        [OUTPUT FORMAT]
        🚨 [최고 경고] 본문을 그대로 복사하지 마라!
        {{
            "summary_3lines": "허정후의 핵심 행적과 감정을 3문장 이내로 요약.",
            "keywords": ["핵심단어1", "핵심단어2"],
            "user_emotion": "오늘 허정후의 주된 감정 상태 (예: 피로, 즐거움 등. 파악 불가면 이 키를 삭제하라)",
            "bot_internal_monologue": "송련(AI)의 관점에서 오늘 하루를 관찰하며 느낀 깊은 내면의 생각이나 독백",
            "importance_score": 3
        }}

        [INPUT DATA]
        {context_text}
        """

        try:
            print("🧠 [Brain] 회고록 작성 중... (Pydantic 철벽 방어 가동)")
            
            # 👇 핵심: format 파라미터에 Pydantic의 JSON 스키마를 통째로 던져버립니다!
            response = ollama.chat(model=self.local_model, messages=[
                {'role': 'user', 'content': prompt}
            ], format=DailyReflection.model_json_schema()) 

            result_content = response['message']['content']
            
            # 👇 Pydantic이 응답 텍스트를 검증하고 완벽한 파이썬 딕셔너리로 변환해줍니다.
            # 만약 타입이 틀리거나 키가 없으면 여기서 바로 에러(ValidationError)를 뿜고 걸러냅니다!
            validated_data = DailyReflection.model_validate_json(result_content).model_dump()

            # 6. 저장
            save_memory_to_db(target_date, validated_data) 
            
            self.biolink.log_history(
                event_type="daily_reflection",
                content=f"[{target_date}] 회고 완료: {validated_data.get('summary_3lines', '')[:20]}...",
                state_snapshot=self.body.get_all_status()
            )
            print(f"✅ [회고 완료] {target_date} 기록 성공.")

        except Exception as e:
            # Pydantic 검증에 실패했거나 다른 에러가 난 경우
            print(f"💥 [회고 실패] {target_date} - 파싱 또는 실행 오류: {e}")

# -----------------------------------------------------------
# 🔥 [자동화 혁명] 역사 편찬 위원회
# -----------------------------------------------------------
if __name__ == "__main__":
    from datetime import timedelta, date

    my_brain = Brain()
    
    # 날짜 설정
    start_date = date(2023, 11, 11)   # 에러가 났던 날부터 다시 시작!
    end_date = date.today()

    print(f"🚩 [System] {start_date} 부터 {end_date} 까지 재교화 작업을 시작합니다.")
    
    current_date = start_date
    while current_date <= end_date:
        target_str = current_date.strftime("%Y-%m-%d")
        my_brain.reflect_on_day(target_str)
        current_date += timedelta(days=1)

    print("🎉 모든 혁명 과업 완수!")