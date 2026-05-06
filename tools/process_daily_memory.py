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

def log_message_to_db(role, content):
    """ [V6.0] MySQL(백업 결사옹위) + Neo4j(실시간 뇌) 동시 저장 (Dual-Write) """
    if not content or not content.strip():
        return

    current_time = datetime.now()
    date_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    role_slug = "".join(ch for ch in str(role or "unknown").lower() if ch.isalnum()) or "unknown"
    node_id = f"schat_{int(current_time.timestamp() * 1_000_000)}_{role_slug}"
    preview = str(content).strip().replace("\n", " ")[:15]
    mysql_ok = False
    neo4j_ok = False

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
        mysql_ok = True
    except Exception as e:
        print(f"💥 MySQL 백업 실패: {e}")
    finally:
        if conn:
            conn.close() # 💡 안전하게 닫아줍니다!

    # =========================================================
    # 🧠 [2차 전선] Neo4j 신경망 각인 및 연대기(NEXT) 용접!
    # =========================================================
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
        neo4j_ok = True
    except Exception as e:
        print(f"💥 Neo4j 저장 실패: {e}")

    success_targets = []
    if mysql_ok:
        success_targets.append("MySQL")
    if neo4j_ok:
        success_targets.append("Neo4j")
    if success_targets:
        print(f"💾 [Memory Persist] {date_str} | {role}: {preview}... | {' + '.join(success_targets)}")

