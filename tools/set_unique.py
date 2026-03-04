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

print("🌲 DB 규칙을 변경합니다...")

# 1. 일단 싹 비우기 (중복 데이터 제거를 위해 깔끔하게 초기화)
cursor.execute("TRUNCATE TABLE user_diary;")
print("🧹 기존 데이터 초기화 완료.")

# 2. 'write_date' 컬럼에 '유일(UNIQUE)' 속성 부여
# 이제 똑같은 날짜가 들어오면 DB가 알아서 튕겨냅니다.
sql = "ALTER TABLE user_diary ADD UNIQUE INDEX (write_date);"
cursor.execute(sql)
print("✅ 이제 '날짜'는 중복될 수 없습니다 (Unique 설정 완료).")

DB_CONFIG.close()