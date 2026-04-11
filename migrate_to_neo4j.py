import os
import pymysql
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 환경변수 로드
load_dotenv()

# ---------------------------------------------------------
# 1. MySQL 접속 정보 (기존 감옥)
# ---------------------------------------------------------
MYSQL_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

# ---------------------------------------------------------
# 2. Neo4j 접속 정보 (새로운 신경망 벙커)
# ---------------------------------------------------------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD") 

def migrate_data():
    print("🚀 [System] V3.5 계층형 신경망 대규모 이주 작전을 개시합니다 (MySQL -> Neo4j)...")
    
    mysql_conn = pymysql.connect(**MYSQL_CONFIG)
    mysql_cursor = mysql_conn.cursor()
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        with neo4j_driver.session() as session:
            # ==========================================
            # 1단계: 세계관 뼈대 생성 (신체제 COMMANDS 연결)
            # ==========================================
            print("👤 [1/7] 세계관 뼈대(개발자, 송련) 및 지휘 계통 생성 중...")
            session.run("MERGE (p:Person {name: '허정후', role: 'Commander'})")
            session.run("MERGE (a:CoreEgo {name: '송련'}) SET a:Agent, a.role = 'A-life'")
            session.run("""
            MATCH (p:Person {name: '허정후'}), (a:CoreEgo {name: '송련'})
            MERGE (p)-[:COMMANDS]->(a)
            """)

            # ==========================================
            # 2단계: 에피소드(요약) 선발대 이주 (부모 노드 먼저 생성!)
            # ==========================================
            print("📚 [2/7] 부모 노드: 회고록(Episodes) 이주 및 감정망 구축 중...")
            mysql_cursor.execute("SELECT episode_id, summary_date, summary_text, keywords, user_emotion, bot_internal_monologue, importance_score FROM memory_episodes")
            for row in mysql_cursor.fetchall():
                ep_id, ep_date, ep_summary, ep_keys, ep_emo, ep_mono, ep_score = row
                date_str = ep_date.strftime('%Y-%m-%d') if hasattr(ep_date, 'strftime') else str(ep_date)
                
                cypher = """
                MATCH (p:Person {name: '허정후'})
                MERGE (e:Episode {id: $ep_id})
                SET e.date = $date_str, e.summary = $summary, e.keywords = $keywords, 
                    e.monologue = $monologue, e.importance_score = $score
                MERGE (p)-[:EXPERIENCED]->(e)
                
                WITH p, e, $emotion AS emo_name
                WHERE emo_name IS NOT NULL AND emo_name <> '' AND emo_name <> '파악 불가'
                MERGE (emo:Emotion {name: emo_name})
                MERGE (e)-[:FEELING]->(emo)
                MERGE (p)-[:FELT]->(emo)
                """
                session.run(cypher, ep_id=f"ep_{ep_id}", date_str=date_str, summary=ep_summary, 
                            keywords=ep_keys, monologue=ep_mono, score=ep_score, emotion=ep_emo)

            # ==========================================
            # 3단계: 일기장 이주 및 탯줄 연결 (PastRecord 계층화)
            # ==========================================
            print("📝 [3/7] 자식 노드: 일기장 기록 이주 및 에피소드 연결 중...")
            mysql_cursor.execute("SELECT id, write_date, content FROM user_diary")
            for row in mysql_cursor.fetchall():
                d_id, d_date, d_content = row
                date_str = d_date.strftime('%Y-%m-%d') if hasattr(d_date, 'strftime') else str(d_date)
                cypher = """
                MATCH (p:Person {name: '허정후'})
                // 👇 PastRecord 통합 라벨 부착!
                MERGE (m:PastRecord:Diary {id: $d_id})
                SET m.date = $date_str, m.content = $content
                MERGE (p)-[:WROTE]->(m)
                
                // 👇 부모 에피소드를 찾아 탯줄(HAS_RAW_DATA) 연결!
                WITH m, $date_str AS target_date
                MATCH (e:Episode) WHERE e.date = target_date
                MERGE (e)-[:HAS_RAW_DATA]->(m)
                """
                session.run(cypher, d_id=f"diary_{d_id}", date_str=date_str, content=d_content)

            # ==========================================
            # 4단계: 제미나이 대화록 이주 및 탯줄 연결
            # ==========================================
            print("🤖 [4/7] 자식 노드: 제미나이 대화 기록 이주 및 연결 중...")
            mysql_cursor.execute("SELECT id, conversation_id, role, content, created_at FROM chat_logs")
            for row in mysql_cursor.fetchall():
                cl_id, cl_conv, cl_role, cl_content, cl_date = row
                date_str = cl_date.strftime('%Y-%m-%d %H:%M:%S') if hasattr(cl_date, 'strftime') else str(cl_date)
                cypher = """
                MATCH (p:Person {name: '허정후'})
                // 👇 PastRecord 통합 라벨 부착!
                MERGE (g:PastRecord:GeminiChat {id: $cl_id})
                SET g.conversation_id = $cl_conv, g.date = $date_str, g.role = $cl_role, g.content = $cl_content
                MERGE (p)-[:CHATTED_WITH_GEMINI]->(g)
                
                // 👇 날짜 앞 10자리(YYYY-MM-DD)로 부모 에피소드 찾아 연결!
                WITH g
                MATCH (e:Episode) WHERE g.date STARTS WITH e.date
                MERGE (e)-[:HAS_RAW_DATA]->(g)
                """
                session.run(cypher, cl_id=f"gchat_{cl_id}", cl_conv=cl_conv, date_str=date_str, cl_role=cl_role, cl_content=cl_content)

            # ==========================================
            # 5단계: 송련 대화록 이주 및 탯줄 연결
            # ==========================================
            print("💬 [5/7] 자식 노드: 송련 대화 기록 이주 및 연결 중...")
            mysql_cursor.execute("SELECT id, role, content, created_at FROM songryeon_chats")
            for row in mysql_cursor.fetchall():
                sc_id, sc_role, sc_content, sc_date = row
                date_str = sc_date.strftime('%Y-%m-%d %H:%M:%S') if hasattr(sc_date, 'strftime') else str(sc_date)
                
                cypher = """
                // 👇 PastRecord 통합 라벨 부착!
                MERGE (c:PastRecord:SongryeonChat {id: $sc_id})
                SET c.date = $date_str, c.role = $sc_role, c.content = $sc_content
                
                WITH c, $sc_role AS role
                OPTIONAL MATCH (p:Person {name: '허정후'}) WHERE role = 'user'
                OPTIONAL MATCH (a:CoreEgo {name: '송련'}) WHERE role <> 'user'
                
                // 화자에 따라 발화자 연결
                FOREACH (x IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END | MERGE (p)-[:SPOKE]->(c))
                FOREACH (x IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END | MERGE (a)-[:SPOKE]->(c))
                
                // 👇 부모 에피소드 연결!
                WITH c
                MATCH (e:Episode) WHERE c.date STARTS WITH e.date
                MERGE (e)-[:HAS_RAW_DATA]->(c)
                """
                session.run(cypher, sc_id=f"schat_{sc_id}", date_str=date_str, sc_role=sc_role, sc_content=sc_content)

        print("\n🎉 [System] V3.5 대규모 이주 작전 완수! 이제 송련이는 계층화된 완벽한 과거를 기억합니다!")

    except Exception as e:
        print(f"💥 이주 작전 중 치명적 에러: {e}")
    finally:
        mysql_cursor.close()
        mysql_conn.close()
        neo4j_driver.close()

if __name__ == "__main__":
    migrate_data()