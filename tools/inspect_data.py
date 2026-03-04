import pymysql
import os
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

def inspect_chat_logs():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("\n🕵️‍♂️ [데이터 생존 신고] 랜덤으로 5개 ID 먼저 뽑는 중...")

    # 1단계: 일단 ID 5개만 먼저 가져온다. (단순하게!)
    try:
        sql_get_ids = "SELECT DISTINCT conversation_id FROM chat_logs ORDER BY RAND() LIMIT 5"
        cursor.execute(sql_get_ids)
        rows = cursor.fetchall()
        
        # 가져온 ID들을 리스트로 만듦
        target_ids = [row[0] for row in rows]

        if not target_ids:
            print("🚨 데이터가 하나도 없는데요? (0건)")
            return

        # 2단계: 그 ID에 해당하는 대화 내용을 가져온다.
        # (format_strings = %s, %s, %s, %s, %s)
        format_strings = ','.join(['%s'] * len(target_ids))
        sql_get_content = f"""
            SELECT conversation_id, role, content 
            FROM chat_logs 
            WHERE conversation_id IN ({format_strings})
            ORDER BY conversation_id, role DESC
        """
        
        cursor.execute(sql_get_content, tuple(target_ids))
        results = cursor.fetchall()

        print(f"✅ 총 {len(results)}개의 대화 조각을 발견했습니다.\n")
        print("="*50)

        current_pair = ""
        for pair_id, role, content in results:
            if current_pair != pair_id:
                print(f"\n🔗 커플링 ID: {pair_id[:8]}...") # ID가 너무 기니까 앞만 조금
                print("-" * 30)
                current_pair = pair_id
                
            role_icon = "👤" if role == 'user' else "🤖"
            
            # 줄바꿈이 많으면 보기 힘드니까 한 줄로 펴서 보여줌
            clean_content = content.replace('\n', ' ')
            preview = clean_content[:80] + "..." if len(clean_content) > 80 else clean_content
            
            print(f"{role_icon} {role}: {preview}")

        print("\n" + "="*50)

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_chat_logs()