# check_db.py
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

# 1. 개수 세기
cursor.execute("SELECT count(*) FROM user_diary;")
count = cursor.fetchone()[0]

print(f"📈 현재 DB에 저장된 일기 개수: {count}개")

if count > 0:
    print(f"\n🔎 최근 일기 5개를 검사합니다:")
    print("-" * 50)
    
    # LIMIT 5로 변경!
    cursor.execute("SELECT write_date, content FROM user_diary ORDER BY id DESC LIMIT 5;")
    
    # fetchone(하개발자) -> fetchall(전부)로 변경
    rows = cursor.fetchall() 
    
    for row in rows:
        date = row[0]
        summary = row[1][:30].replace("\n", " ") # 줄바꿈 제거해서 깔끔하게
        print(f"📅 {date} | 📝 {summary}...")
        
    print("-" * 50)

DB_CONFIG.close()