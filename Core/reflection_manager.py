import time
from tools.toolbox import analyze_past_dreams, pool 

class ReflectionManager:
    def __init__(self):
        self.name = "송련_자아성찰_모듈"

    # 🛡️ [NEW] 밀린 숙제(성찰 안 한 날짜)를 DB에서 싹 다 찾아오는 탐지기!
    def get_unreflected_dates(self):
        conn = pool.connection()
        cursor = conn.cursor()
        try:
            # 1. 송련이가 속마음(꿈)을 가졌던 '모든 날짜'를 중복 없이 가져옵네다.
            cursor.execute("SELECT DISTINCT DATE_FORMAT(created_at, '%Y-%m-%d') FROM agent_dreams ORDER BY created_at ASC")
            dream_dates = [row[0] for row in cursor.fetchall() if row[0]]

            # 2. 이미 오답노트를 작성한 '완료된 날짜'를 가져옵네다.
            cursor.execute("SELECT situation_tag FROM prompt_tournament WHERE situation_tag LIKE '일일_자아성찰_%'")
            reflected_tags = [row[0] for row in cursor.fetchall()]
            reflected_dates = [tag.replace("일일_자아성찰_", "") for tag in reflected_tags]

            # 3. 꿈은 꿨는데 성찰은 안 한 '밀린 날짜'만 골라냅네다!
            unreflected = [d for d in dream_dates if d not in reflected_dates]
            return unreflected
        except Exception as e:
            print(f"💥 미처리 날짜 조회 실패: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def start_reflection_loop(self):
        print(f"\n🌙 [{self.name}] 가동... 무의식의 바다에서 '밀린 반성문'을 찾습네다.")
        
        while True:
            # 💡 [핵심] 컴퓨터 시계가 아니라 DB를 보고 밀린 날짜를 가져옵네다!
            unreflected_dates = self.get_unreflected_dates()
            
            if not unreflected_dates:
                print(f"💤 [Reflection] 밀린 반성문이 없습네다. 완벽하게 최신 상태입네다! (1분 대기)")
                time.sleep(60)
                continue

            # 가장 오래된 밀린 숙제부터 하나씩 처리합네다.
            target_date_str = unreflected_dates[0]
            year, month, day = target_date_str.split('-')

            print(f"🔍 [Reflection] 과거의 찐빠 발견! '{target_date_str}' 날짜의 밀린 일일 성찰을 개시합네다.")
            
            # 💡 밀린 날짜를 LLM(고위 자아)에게 넘겨 반성문을 쓰게 합네다!
            reflection_report = analyze_past_dreams(year=year, month=int(month), day=int(day))
            
            if "❌" not in reflection_report:
                self.save_to_tournament_db(reflection_report, target_date_str)
            else:
                print(f"💤 [Reflection] '{target_date_str}' 꿈 데이터가 분석할 만큼 길지 않아 건너뜁네다.")
                # 무한 루프 방지를 위해, 분석 실패한 날짜도 '빈 껍데기'로 저장해버립네다 (다시 검사 안 하도록)
                self.save_to_tournament_db("데이터 부족으로 성찰 생략됨", target_date_str)

            print("⏳ 15초 후 다음 밀린 성찰을 진행합네다...\n")
            time.sleep(15) 

    # 💾 저장 태그: 무조건 해당 날짜로 고정!
    def save_to_tournament_db(self, report, target_date_str):
        print(f"🏆 [Tournament DB] '{target_date_str}' 전술 카드를 보관소로 전송합네다...")
        try:
            conn = pool.connection()
            cursor = conn.cursor()
            
            sql = """
                INSERT INTO prompt_tournament (situation_tag, reflection_text) 
                VALUES (%s, %s)
            """
            tag = f"일일_자아성찰_{target_date_str}"
            
            cursor.execute(sql, (tag, report))
            conn.commit()
            print(f"💾 [저장 완료] 전술 카드가 성공적으로 기록되었습네다! (카드 번호: {cursor.lastrowid})\n")
        except Exception as e:
            print(f"💥 [저장 실패] DB가 파업했습네다: {e}")
        finally:
            cursor.close()
            conn.close()