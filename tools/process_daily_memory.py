import pymysql
import json
import os
import ollama # 🔥 구글 API 숙청! 로컬 엔진 투입!
from datetime import datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase # 👈 [신규 추가] Neo4j 접속 라이브러리

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

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

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

        # 👇 [수술 부위 1] 임베딩할 때 '요약'뿐만 아니라 송련이의 '독백'까지 합쳐서 지능을 높입네다!
        text_to_embed = analysis_data.get('bot_internal_monologue', '') + " " + analysis_data.get('summary_3lines', '')
        
        try:
            emb_res = ollama.embeddings(model='nomic-embed-text', prompt=text_to_embed)
            emb_json = json.dumps(emb_res['embedding'])
        except Exception as e:
            print(f"⚠️ 임베딩 실패 (안전모드 가동): {e}")
            emb_json = json.dumps([0.0] * 768) 
        
        keywords = json.dumps(analysis_data.get('keywords', []), ensure_ascii=False)
        emotions = json.dumps(analysis_data.get('user_emotion', '파악 불가'), ensure_ascii=False)
        
        # 👇 [수술 부위 2] 엉뚱한 diary_content 대신 진짜 독백과 중요도를 챙깁네다!
        monologue = analysis_data.get('bot_internal_monologue', '독백 없음') 
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
    """ [V6.0] MySQL(백업 결사옹위) + Neo4j(실시간 뇌) 동시 저장 (Dual-Write) """
    if not content or not content.strip():
        return

    current_time = datetime.now() 
    date_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    node_id = f"schat_{int(current_time.timestamp())}"

    # 1. 🔥 자력갱생 실시간 공통 로컬 임베딩
    try:
        emb_res = ollama.embeddings(model='nomic-embed-text', prompt=content)
        embedding_vector = emb_res['embedding']
        emb_json = json.dumps(embedding_vector)
    except Exception as e:
        print(f"⚠️ 임베딩 실패 (안전모드): {e}")
        embedding_vector = [0.0] * 768
        emb_json = json.dumps(embedding_vector)

    # =========================================================
    # 🛡️ [1차 방어선] MySQL 데이터 결사옹위 (Raw 백업)
    # =========================================================
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        conn.autocommit(True)
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO songryeon_chats (role, content, embedding, created_at)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (role, content, emb_json, current_time))
        print(f"💾 [MySQL 백업] {date_str} | {role}: {content[:15]}...")
    except Exception as e:
        print(f"💥 MySQL 백업 실패: {e}")
    finally:
        if conn:
            conn.close() # 💡 안전하게 닫아줍니다!

    # =========================================================
    # 🧠 [2차 전선] Neo4j 신경망 각인 및 연대기(NEXT) 용접!
    # =========================================================
    print("💾 [System] 현장 요원의 대화를 Neo4j 신경망에 각인합니다...")
    cypher = """
    // [1단계] 새로운 발화 노드 생성
    CREATE (n:PastRecord:SongryeonChat {
        id: $node_id,
        role: $role,
        content: $content,
        date: $date_str,
        created_at: timestamp()
    })
    SET n.embedding = $embedding_vector
    
    WITH n
    // [2단계] 현재 DB에 존재하는 가장 마지막(최신) PastRecord를 찾습니다.
    OPTIONAL MATCH (prev:PastRecord)
    WHERE prev.id <> n.id AND prev.date <= n.date
    WITH n, prev ORDER BY prev.date DESC LIMIT 1
    
    // [3단계] 찾은 꼬리가 있다면, 새로운 노드와 NEXT 탯줄로 자동 용접!
    FOREACH (x IN CASE WHEN prev IS NOT NULL THEN [1] ELSE [] END |
        MERGE (prev)-[:NEXT]->(n)
    )
    
    // [4단계] 발화자(허정후 vs 송련)를 명확히 연결합니다.
    WITH n
    OPTIONAL MATCH (p:Person {name: '허정후'}) WHERE n.role = 'user'
    OPTIONAL MATCH (a:CoreEgo {name: '송련'}) WHERE n.role <> 'user'
    FOREACH (x IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END | MERGE (p)-[:SPOKE]->(n))
    FOREACH (x IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END | MERGE (a)-[:SPOKE]->(n))
    """
    
    try:
        with neo4j_driver.session() as session:
            session.run(cypher, node_id=node_id, role=role, content=content, 
                        date_str=date_str, embedding_vector=embedding_vector)
            
        print(f"🔗 [신경망 직결] {role}: NEXT 탯줄 자동 연결 성공!")
    except Exception as e:
        print(f"💥 Neo4j 저장 실패: {e}")