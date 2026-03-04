import pymysql
import json
import os
import ollama # 🔥 구글 API 숙청! 로컬 엔진 투입!
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
# 구글 API 키는 이제 필요 없으니 주석 처리 또는 삭제
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# genai.configure(api_key=GEMINI_API_KEY)

DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

# 1. [재료 수집] (기존과 동일하여 생략 없이 유지)
def get_daily_context(target_date):
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    combined_logs = []

    try:
        sql_chat = "SELECT created_at, role, content FROM chat_logs WHERE DATE(created_at) = %s"
        cursor.execute(sql_chat, (target_date,))
        for row in cursor.fetchall():
            dt, role, content = row
            speaker = '사용자' if role == 'user' else '제미나이'
            log_str = f"[{dt.strftime('%H:%M')}] (채팅) {speaker}: {content}"
            combined_logs.append({"time": dt, "text": log_str})

        formatted_date = target_date.replace('-', ' ') 
        sql_diary = "SELECT write_date, content FROM user_diary WHERE write_date = %s OR write_date = %s"
        cursor.execute(sql_diary, (target_date, formatted_date))
        for row in cursor.fetchall():
            w_date, content = row
            diary_dt = None
            if isinstance(w_date, str):
                try:
                    diary_dt = datetime.strptime(w_date.replace('-', ' '), '%Y %m %d')
                except: continue
            else:
                diary_dt = datetime.combine(w_date, datetime.min.time())
            
            log_str = f"[{diary_dt.strftime('%Y-%m-%d')}] (일기) 📝: {content}"
            combined_logs.append({"time": diary_dt, "text": log_str})

        sql_songryeon = "SELECT created_at, role, content FROM songryeon_chats WHERE DATE(created_at) = %s"
        cursor.execute(sql_songryeon, (target_date,))
        for row in cursor.fetchall():
            dt, role, content = row
            speaker = '송련' if role == 'assistant' else '개발자'
            combined_logs.append({
                'time': dt,
                'text': f"[{dt.strftime('%H:%M')}] (송련 대화) {speaker}: {content}"
            })    
    except Exception as e:
        print(f"데이터 수집 에러: {e}")
    finally:
        conn.close()
    
    if not combined_logs: return None
    combined_logs.sort(key=lambda x: x['time'])
    return "\n".join([item['text'] for item in combined_logs])


# 2. [창고 저장] 🔥 로컬 Ollama 임베딩 적용
def save_memory_to_db(target_date, analysis_data):
    print(f"💾 [Tools] {target_date} 기억 저장 중...")
    
    conn = pymysql.connect(**DB_CONFIG)
    conn.autocommit(True)
    cursor = conn.cursor()

    try:
        check_sql = "DELETE FROM memory_episodes WHERE summary_date = %s"
        cursor.execute(check_sql, (target_date,))
        if cursor.rowcount > 0:
            print(f"♻️ [System] {target_date}의 기존 기록을 덮어씁니다.")

        # 🔥 자력갱생 로컬 임베딩 (nomic-embed-text)
        text_to_embed = analysis_data.get('diary_content', '') + " " + analysis_data.get('summary_3lines', '')
        
        try:
            emb_res = ollama.embeddings(model='nomic-embed-text', prompt=text_to_embed)
            emb_json = json.dumps(emb_res['embedding'])
        except Exception as e:
            print(f"⚠️ 임베딩 실패 (안전모드 가동): {e}")
            emb_json = json.dumps([0.0] * 768) # 에러 시 0으로 채운 벡터 저장
        
        keywords = json.dumps(analysis_data.get('keywords', []), ensure_ascii=False)
        emotions = json.dumps(analysis_data.get('user_emotion', {}), ensure_ascii=False)
        monologue = analysis_data.get('diary_content', '') 
        score = analysis_data.get('importance_score', 3)

        sql = """
            INSERT INTO memory_episodes 
            (summary_date, summary_text, keywords, user_emotion, bot_internal_monologue, importance_score, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (target_date, analysis_data.get('summary_3lines', '요약 없음'), keywords, emotions, monologue, score, emb_json))
        print("✅ DB 저장 완료! (Tools 임무 끝)")

    except Exception as e:
        print(f"❌ 저장 실패 (Tools 에러): {e}")
    finally:
        conn.close()


def log_message_to_db(role, content):
    """ 송련과의 대화를 DB에 저장 (로컬 임베딩 적용) """
    conn = pymysql.connect(**DB_CONFIG)
    conn.autocommit(True)
    cursor = conn.cursor()

    try:
        current_time = datetime.now() 

        # 🔥 자력갱생 로컬 임베딩
        if content.strip():
            try:
                emb_res = ollama.embeddings(model='nomic-embed-text', prompt=content)
                emb_json = json.dumps(emb_res['embedding'])
            except Exception as e:
                emb_json = json.dumps([0.0] * 768)
        else:
            emb_json = None

        sql = """
            INSERT INTO songryeon_chats (role, content, embedding, created_at)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, (role, content, emb_json, current_time))
        print(f"💾 [기억 보존] {current_time.strftime('%H:%M:%S')} | {role}: {content[:20]}...")

    except Exception as e:
        print(f"💥 대화 저장 실패: {e}")
    finally:
        conn.close()