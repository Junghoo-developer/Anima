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

# "테이블 구조(Description) 좀 보여줘!"
cursor.execute("DESCRIBE user_diary;")
rows = cursor.fetchall()

print(f"\n{'Field':<15} | {'Type':<15} | {'Null':<5}")
print("-" * 40)

for row in rows:
    # row[0]: 컬럼 이름, row[1]: 타입
    print(f"{row[0]:<15} | {row[1]:<15} | {row[2]:<5}")

DB_CONFIG.close()