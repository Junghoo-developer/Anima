import pymysql
import uuid
import json
import os
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 설정 로드
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

def quick_add():
    print("\n⚡ [초고속 대화 주입기] 테이크아웃 없이 바로 넣습니다.")
    print("="*50)

    # 1. 사용자 질문 입력
    print("👤 [사장님 질문]을 복사해서 붙여넣고 엔터 2번 (종료하려면 Ctrl+C):")
    lines = []
    while True:
        line = input()
        if line: lines.append(line)
        else: break # 엔터 두 번 치면 입력 끝
    user_text = '\n'.join(lines).strip()

    if not user_text:
        print("❌ 내용이 없어서 취소합니다.")
        return

    # 2. 제미나이 답변 입력
    print("\n🤖 [제미나이 답변]을 복사해서 붙여넣고 엔터 2번:")
    lines = []
    while True:
        line = input()
        if line: lines.append(line)
        else: break
    model_text = '\n'.join(lines).strip()

    if not model_text:
        print("❌ 답변이 없어서 취소합니다.")
        return

    # 3. DB 저장 및 임베딩
    conn = pymysql.connect(**DB_CONFIG)
    conn.autocommit(True)
    cursor = conn.cursor()

    pair_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    print("\n...뇌세포 이식 중 (임베딩)...")
    
    try:
        # User 임베딩 & 저장
        u_emb = genai.embed_content(model="models/text-embedding-004", content=user_text)
        sql_u = "INSERT INTO chat_logs (conversation_id, role, content, raw_json_id, embedding) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql_u, (pair_id, 'user', user_text, timestamp+"_manual_u", json.dumps(u_emb['embedding'])))

        # Model 임베딩 & 저장
        m_emb = genai.embed_content(model="models/text-embedding-004", content=model_text)
        sql_m = "INSERT INTO chat_logs (conversation_id, role, content, raw_json_id, embedding) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql_m, (pair_id, 'model', model_text, timestamp+"_manual_m", json.dumps(m_emb['embedding'])))

        print(f"✅ 저장 완료! (ID: {pair_id})")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    while True:
        quick_add()
        if input("\n계속 추가하시겠습니까? (y/n): ").lower() != 'y':
            break