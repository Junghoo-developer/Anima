import os
import pymysql

DB_HOST = "192.168.10.10"  
DB_PORT = 3306         
DB_USER = "peter"     
DB_PASS = "028305"    
DB_NAME = "diary_db" 
MEMORY_FOLDER = "./Songryeon_user_diary"

# 1. DB 접속
conn = pymysql.connect(
    host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, db=DB_NAME,
    charset='utf8mb4' # 한글+이모지 필수
)
cursor = conn.cursor()
print("🌲 DB 접속 성공! 무중단 업로드를 시작합니다...\n")

files = os.listdir(MEMORY_FOLDER)
success_count = 0
fail_count = 0

for filename in files:
    if filename.endswith(".txt"):
        try:
            # ----------------------------------------
            # [시도] 파일 읽고 DB에 넣기
            # ----------------------------------------
            path = os.path.join(MEMORY_FOLDER, filename)
            date_str = filename.replace(".txt", "")

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            sql = """
            INSERT INTO user_diary (write_date, content, source) 
            VALUES (%s, %s, 'diary') 
            ON DUPLICATE KEY UPDATE 
                content = VALUES(content),
                embedding = NULL 
            """
            # 개발자중에 임베딩을 단순히 NULL처리 하는 것 뿐만 아니라
            # 실시간으로 고치는 기능도 구현하면 좋음
            
            cursor.execute(sql, (date_str, content))

            conn.commit()
        
        # cursor.rowcount가 1이면 성공(새로 넣음), 0이면 무시됨(이미 있음)
            if cursor.rowcount > 0:
                print(f"✅ 신규 등록: {date_str}")
                success_count += 1
            else:
                print(f"💤 이미 있음 (건너뜀): {date_str}")
            # 이미 있는 건 실패가 아니니까 카운트 안 함

        except Exception as e:
                    print(f"❌ 실패 (건너뜀): {filename}")
                    print(f"   ㄴ이유: {e}")
                    conn.rollback() # 꼬인 거 풀어주기
                    fail_count += 1

print("\n" + "="*30)
print(f"🌲 작업 종료!")
print(f"성공: {success_count}개")
print(f"실패: {fail_count}개")
print("="*30)

conn.close()