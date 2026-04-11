import os
import ollama
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

EMBEDDING_MODEL = "mxbai-embed-large" 
EMBEDDING_DIMENSIONS = 1024 

class PastRecordEmbedder:
    def __init__(self):
        print("⚙️ [System] PastRecord(원문) 1024차원 전면 임베딩 모듈 가동...")
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def _get_embedding(self, text):
        try:
            # 텍스트가 비어있으면 임베딩 안 함
            if not text or len(text.strip()) < 2:
                return None
            response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=text)
            return response["embedding"]
        except Exception as e:
            print(f"💥 임베딩 실패: {e}")
            return None

    def setup_vector_index(self):
        print("🛠️ 1단계: PastRecord(원문)용 1024차원 고속도로(Index) 건설 중...")
        
        # 하위 노드 전용 인덱스 생성!
        create_cypher = f"""
        CREATE VECTOR INDEX past_record_embedding IF NOT EXISTS
        FOR (p:PastRecord) ON (p.embedding)
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {EMBEDDING_DIMENSIONS},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """
        try:
            with self.driver.session() as session:
                session.run(create_cypher)
            print("  ✅ PastRecord 전용 1024차원 벡터 인덱스 확보 완료!")
        except Exception as e:
            print(f"  🚨 인덱스 생성 실패: {e}")

    def process_past_records(self):
        print("\n🔍 2단계: 임베딩(레이더)이 없는 하위 원문(PastRecord) 수색 중...")
        
        # 💡 [핵심] 임베딩 안 된 원문을 싹 다 긁어옵네다!
        fetch_cypher = """
        MATCH (p:PastRecord)
        WHERE p.embedding IS NULL
        RETURN elementId(p) AS node_id, p.date AS date, p.content AS content, labels(p) AS labels
        """
        
        with self.driver.session() as session:
            records = session.run(fetch_cypher).data()
            
        if not records:
            print("  🎉 모든 하위 원문에 1024차원 무장이 완료되어 있습네다! 퇴근!")
            return

        total_records = len(records)
        print(f"  🎯 맙소사! 총 {total_records}개의 무장 해제된 원문을 발견했습네다! 대공사를 시작합네다!")

        success_count = 0
        with self.driver.session() as session:
            for i, record in enumerate(records, 1):
                node_id = record["node_id"]
                content = record.get("content", "")
                date = record.get("date", "알수없음")
                labels = record.get("labels", [])
                
                # 라벨(종류) 확인해서 로그에 이쁘게 찍기
                record_type = "원문"
                if "Diary" in labels: record_type = "일기"
                elif "GeminiChat" in labels: record_type = "제미나이 채팅"
                elif "SongryeonChat" in labels: record_type = "송련 채팅"

                print(f"  💉 [{i}/{total_records}] {date} {record_type} 임베딩 투여 중...")
                
                vector = self._get_embedding(content)
                
                if vector:
                    update_cypher = """
                    MATCH (p:PastRecord) WHERE elementId(p) = $node_id
                    SET p.embedding = $vector
                    """
                    session.run(update_cypher, node_id=node_id, vector=vector)
                    success_count += 1
                else:
                    print(f"    ⚠️ 내용이 없거나 짧아서 임베딩 스킵.")

        print(f"\n🎉 [작전 종료] 총 {success_count}개의 하위 원문이 1024차원 무장을 마쳤습네다!")

if __name__ == "__main__":
    embedder = PastRecordEmbedder()
    embedder.setup_vector_index()
    embedder.process_past_records()