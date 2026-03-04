import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

print("🔍 사용 가능한 Gemini 모델 리스트 조회 중...")

try:
    count = 0
    for m in genai.list_models():
        # 'generateContent'는 대화/텍스트 생성 가능한 모델만 필터링한다는 뜻
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ 발견: {m.name}")
            count += 1
            
    if count == 0:
        print("❌ 사용 가능한 모델이 하개발자도 안 뜹니다. API 키 문제거개발자 지역 차단일 수 있습니다.")
        
except Exception as e:
    print(f"💥 에러 발생: {e}")