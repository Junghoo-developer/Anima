import pymysql
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

cursor = DB_CONFIG.cursor()

print("🌲 송련의 뇌세포(임베딩) 저장소를 증축합니다...")

try:
    # -------------------------------------------------------
    # 🏗️ 공사 명령: 테이블에 'embedding'이라는 칸을 추가해라!
    # 타입은 JSON (긴 숫자 리스트 저장용)
    # -------------------------------------------------------
    sql = "ALTER TABLE user_diary ADD COLUMN embedding JSON NULL;"
    
    cursor.execute(sql)
    print("✅ 공사 완료! 'embedding' 컬럼이 생성되었습니다.")

except pymysql.err.OperationalError as e:
    # 이미 만들었는데 또 실행하면 에러 개발자니까 예외 처리
    if "Duplicate column name" in str(e):
        print("💤 이미 'embedding' 컬럼이 존재합니다. (공사할 필요 없음)")
    else:
        print(f"❌ 공사 중 문제 발생: {e}")

DB_CONFIG.close()