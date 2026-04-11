import os
import ollama
from neo4j import GraphDatabase
import json
from dotenv import load_dotenv

load_dotenv()

# =====================================================================
# ⚙️ [설정] Neo4j 및 임베딩 모델 세팅
# =====================================================================
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# 🔥 [업그레이드 완료] 1024차원 고성능 모델 장착!
EMBEDDING_MODEL = "mxbai-embed-large" 
EMBEDDING_DIMENSIONS = 1024 

class BackfillEmbeddings:
    def __init__(self):
        print("⚙️ [System] Neo4j 1024차원 하이엔드 임베딩 주입 모듈 가동...")
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def _get_embedding(self, text):
        try:
            response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
            return response["embedding"]
        except Exception as e:
            print(f"💥 임베딩 추출 실패 (모델이 없으면 'ollama pull mxbai-embed-large' 실행!): {e}")
            return None

    def setup_vector_index(self):
        print("🛠️ 1단계: 기존 768차원 좁은 길 폭파 및 1024차원 고속도로 건설 중...")
        
        # 💡 [핵심] 기존에 만들었던 인덱스를 깔끔하게 날려버립네다!
        drop_cypher = "DROP INDEX episode_embedding IF EXISTS"
        
        # 💡 [핵심] 1024차원짜리 넓은 인덱스로 다시 만듭네다!
        create_cypher = f"""
        CREATE VECTOR INDEX episode_embedding IF NOT EXISTS
        FOR (e:Episode) ON (e.embedding)
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {EMBEDDING_DIMENSIONS},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """
        try:
            with self.driver.session() as session:
                session.run(drop_cypher)
                session.run(create_cypher)
            print("  ✅ 1024차원 고성능 벡터 인덱스 재건축 완료!")
        except Exception as e:
            print(f"  🚨 인덱스 재건축 실패: {e}")

    def process_daily_summaries(self):
        print("\n🔍 2단계: 임베딩(레이더)이 없는 Episode 탐색 중...")
        
        fetch_cypher = """
        MATCH (e:Episode)
        WHERE e.embedding IS NULL
        OPTIONAL MATCH (e)-[:FEELING]->(emo:Emotion)
        RETURN elementId(e) AS node_id, e.date AS date, e.summary AS summary, e.keywords AS keywords, emo.name AS emotion
        """
        
        with self.driver.session() as session:
            records = session.run(fetch_cypher).data()
            
        if not records:
            print("  🎉 오오! 모든 에피소드에 이미 임베딩이 꽉꽉 차 있습네다! 퇴근하시라요!")
            return

        print(f"  🎯 총 {len(records)}개의 '눈먼 에피소드'를 발견했습네다. 1024차원 수술을 시작합네다!")

        success_count = 0
        with self.driver.session() as session:
            for i, record in enumerate(records, 1):
                node_id = record["node_id"]
                date = record.get("date", "알수없는날짜")
                summary = record.get("summary", "")
                emotion = record.get("emotion") or "알 수 없음" 
                keywords = record.get("keywords", "[]")

                if isinstance(keywords, str):
                    try:
                        keywords_list = json.loads(keywords)
                        keywords_str = ", ".join(keywords_list)
                    except:
                        keywords_str = keywords
                elif isinstance(keywords, list):
                    keywords_str = ", ".join(keywords)
                else:
                    keywords_str = ""

                payload = f"날짜: {date}. 감정 상태: {emotion}. 일일 요약: {summary} 관련 핵심어: {keywords_str}"
                
                print(f"  💉 [{i}/{len(records)}] {date} 에피소드에 1024차원 임베딩 투여 중...")
                
                vector = self._get_embedding(payload)
                
                if vector:
                    update_cypher = """
                    MATCH (e:Episode) WHERE elementId(e) = $node_id
                    SET e.embedding = $vector
                    """
                    session.run(update_cypher, node_id=node_id, vector=vector)
                    success_count += 1
                else:
                    print(f"    ❌ {date} 임베딩 실패. 건너뜁네다.")

        print(f"\n🎉 [작전 종료] 총 {success_count}개의 에피소드(요약본)가 진정한 '1024차원 시맨틱 레이더'를 장착했습네다!")

if __name__ == "__main__":
    backfiller = BackfillEmbeddings()
    backfiller.setup_vector_index()
    backfiller.process_daily_summaries()