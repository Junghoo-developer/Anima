import pymysql
import json
import uuid
import re
import html
import os
import time
from datetime import datetime
import ollama  # 👈 우리의 위대한 로컬 엔진!
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 📍 [경로 해결]
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE_PATH = os.path.join(BASE_DIR, "내활동.json") # 파일명 확인!

DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

def clean_html(raw_html):
    if not raw_html: return ""
    decoded = html.unescape(raw_html)
    clean_text = re.sub(r'<[^>]+>', '', decoded)
    return clean_text.strip()

def parse_time(time_str):
    """
    JSON의 시간 문자열(2023-10-25T12:00:00.123Z)을 
    MySQL 포맷(2023-10-25 12:00:00)으로 변환
    """
    try:
        # 파이썬 3.10 이하 호환을 위해 'Z' 처리
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        # 시간 파싱 실패하면 그냥 현재 시간 넣음
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def import_gemini_v3():
    
    print(f"📂 파일 여는 중: {JSON_FILE_PATH}")
    if not os.path.exists(JSON_FILE_PATH):
        print(f"🚨 파일이 없습니다! {JSON_FILE_PATH}")
        return

    with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    conn = pymysql.connect(**DB_CONFIG)
    conn.autocommit(True)
    cursor = conn.cursor()

    print(f"🚀 [시간 여행 모드] 총 {len(data)}개의 과거 기록 복원 시작...")
    
    success_pair = 0

    for item in data:
        user_text = item.get('title', '')
        if user_text == "Gemini 앱" or not user_text:
            continue
            
        model_text_raw = ""
        if 'safeHtmlItem' in item and len(item['safeHtmlItem']) > 0:
            model_text_raw = item['safeHtmlItem'][0].get('html', '')
        
        model_text = clean_html(model_text_raw)
        if not user_text or not model_text:
            continue

        # ==========================================
        # ⏱️ [핵심] 과거 시간 추출
        # ==========================================
        origin_time_str = item.get('time', '') # JSON에 있는 시간
        real_created_at = parse_time(origin_time_str) # 예쁘게 변환

        pair_id = str(uuid.uuid4())

        try:
            # 1. User 저장 (created_at 추가!)
            print(f"📥 [{real_created_at[:10]}] User: {user_text[:10]}...", end=" ")
            
            # 1. User 저장 파트
            user_vec_json = None
            try:
                # 👇 [소화제 투입] 너무 길면 토하니까 앞부분 4000자만 잘라서 임베딩 엔진에 먹입네다!
                safe_user_text = user_text[:4000] 
                emb_res = ollama.embeddings(model="nomic-embed-text", prompt=safe_user_text)
                user_vec_json = json.dumps(emb_res['embedding'])
            except Exception as e:
                print(f"⚠️ User 임베딩 실패: {e}")

            # SQL 쿼리에 created_at 컬럼을 명시적으로 지정
            sql_user = """
                INSERT IGNORE INTO chat_logs 
                (conversation_id, role, content, raw_json_id, embedding, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            raw_id_user = origin_time_str + "_user_" + user_text[:10] 
            cursor.execute(sql_user, (pair_id, 'user', user_text, raw_id_user, user_vec_json, real_created_at))
            
            # 2. Model 저장 파트
            print(f"-> Gemini 저장 완료")
            
            model_vec_json = None
            try:
                # 👇 [소화제 투입] 제미나이의 답변도 앞부분 4000자만 잘라서 먹입네다!
                safe_model_text = model_text[:4000]
                emb_res = ollama.embeddings(model="nomic-embed-text", prompt=safe_model_text)
                model_vec_json = json.dumps(emb_res['embedding'])
            except Exception as e:
                print(f"⚠️ Model 임베딩 실패: {e}")

            sql_model = """
                INSERT IGNORE INTO chat_logs 
                (conversation_id, role, content, raw_json_id, embedding, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            raw_id_model = origin_time_str + "_model_" + model_text[:10]
            cursor.execute(sql_model, (pair_id, 'model', model_text, raw_id_model, model_vec_json, real_created_at))

            success_pair += 1

        except Exception as e:
                print(f"\n❌ 에러: {e}")

    conn.close()
    print(f"\n🏁 [시간 여행 완료] 총 {success_pair}쌍의 기억이 제 시간에 배치되었습니다.")

if __name__ == "__main__":
    import_gemini_v3()