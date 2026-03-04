import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# 설정 가져오기
DB_CONFIG = {
    'host': os.getenv("DB_HOST", '192.168.10.10'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'peter'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'diary_db'),
    'charset': 'utf8mb4'
}

def create_chat_table():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("🏗️ 대화 로그 전용 창고(Table) 건설 중...")

    # 테이블 생성 쿼리 (conversation_id 추가됨!)
    sql = """
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        conversation_id VARCHAR(100),   -- [중요] 사용자와 제미개발자이를 묶어줄 커플링 번호
        role VARCHAR(20) NOT NULL,      -- 'user' 또는 'model'
        content LONGTEXT NOT NULL,      -- 대화 내용
        embedding LONGTEXT,             -- 임베딩 (개발자중에 채움)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        raw_json_id VARCHAR(255) UNIQUE -- 중복 방지
    );
    """
    
    try:
        cursor.execute(sql)
        print("✅ 'chat_logs' 테이블 건설 완료! (이제 커플링 가능)")
    except Exception as e:
        print(f"❌ 건설 실패: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_chat_table()