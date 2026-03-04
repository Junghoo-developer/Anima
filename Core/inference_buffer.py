import json
import pymysql
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 🛡️ 절대 옹위 대상용 DB 연결 설정
DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

class InferenceBuffer:
    def __init__(self):
        """
        [롤링 메모리 버퍼]
        이제 옛날의 단방향 배열(mission_board 등)은 버립네다.
        오직 1차 부대의 전리품과 2차 참모의 요약본이 쓰고 지워지는 '살아있는 칠판' 하나만 유지합네다.
        """
        self.final_scratchpad = "" 

    def clear(self):
        """작전이 끝나면 다음 턴을 위해 칠판을 물로 씻어냅네다."""
        self.final_scratchpad = ""

    def save_dream_to_db(self, user_input, final_answer, user_emotion, biolink_status):
        """
        [송련의 꿈(사고 과정) 영구 보존]
        사령관의 질문(user_input)을 포함하여 모든 사고 과정을 JSON으로 압축 저장합네다!
        """
        cognitive_process_data = {
            "user_input": user_input,           # 👈 [해결!] 사령관의 질문을 여기에 박아넣습네다.
            "user_emotion": user_emotion,
            "biolink_status": biolink_status,
            "final_memory_state": self.final_scratchpad  # 2차가 압축한 메모리 상태
        }
        
        # JSON 문자열로 변환
        cognitive_json_str = json.dumps(cognitive_process_data, ensure_ascii=False)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # 테이블 자동 생성 (DROP 하셨으니 여기서 새로 태어납네다!)
            sql_create = """
            CREATE TABLE IF NOT EXISTS agent_dreams (
                dream_id INT AUTO_INCREMENT PRIMARY KEY,
                created_at DATETIME,
                cognitive_process JSON,
                final_answer TEXT
            )
            """
            cursor.execute(sql_create)
            
            sql_insert = """
            INSERT INTO agent_dreams (created_at, cognitive_process, final_answer)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql_insert, (timestamp, cognitive_json_str, final_answer))
            conn.commit()
            print("💾 [System] 송련이의 무한 루프 사고 과정이 DB에 완벽히 옹위되었습네다!")
            
        except Exception as e:
            print(f"💥 꿈의 재료 DB 저장 실패: {e}")
        finally:
            cursor.close()
            conn.close()