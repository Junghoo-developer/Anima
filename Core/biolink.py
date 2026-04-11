import json
import os
import sys
import pymysql
from dotenv import load_dotenv

# [환경 변수 로드]
load_dotenv()

# 🛡️ 안전 자산(MySQL) 연결 설정
DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

# [경로 설정]
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

class BioLink:
    def __init__(self):
        self.instincts_path = os.path.join(project_root, "SEED", "Instincts")

    def get_voice_rule(self, filename, current_val):
        """
        [기능] 수치(0~100)에 맞는 대사(Voice)를 JSON에서 찾아냄.
        """
        target_path = os.path.join(self.instincts_path, filename)
        if not os.path.exists(target_path):
            return "(본능 파일 없음)"
            
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for rule in data.get('rules', []):
                if rule['min'] <= current_val <= rule['max']:
                    return rule.get('voice', '')
            return "(무반응)"
        except Exception:
            return "(오류)"

    def get_current_status(self, body):
        """
        🔥 [신규 추가] main.py가 애타게 찾던 그 함수!
        Phenotype(body)의 모든 수치를 읽어서 하나의 보고서 문자열로 만듦.
        """
        # 1. 몸에서 수치 추출
        energy = body.get_value("survival_order", "token_budget")
        social = body.get_value("survival_order", "rate_connecting")
        profit = body.get_value("survival_order", "rate_profit")
        safety = body.get_value("survival_order", "safety")

        # 2. 본능 파일에서 목소리 추출
        v_energy = self.get_voice_rule("survival_token.json", energy)
        v_social = self.get_voice_rule("social_connect.json", social)
        v_profit = self.get_voice_rule("drive_profit.json", profit)
        v_safety = self.get_voice_rule("security_safety.json", safety)

        # 3. 종합 보고서 작성 (시스템 프롬프트용)
        report = f"""
        [PHYSICAL STATUS]
        1. ENERGY (Token Budget): {energy:.1f}/100 
           -> 본능적 반응: "{v_energy}"
        2. SOCIAL (Connection): {social:.1f}/100 
           -> 본능적 반응: "{v_social}"
        3. PROFIT (ROI): {profit:.1f}% 
           -> 본능적 반응: "{v_profit}"
        4. SAFETY: {safety:.1f}/100
           -> 본능적 반응: "{v_safety}"
           
        * 이 상태(본능적 반응)를 참고하여 현재 말투와 태도를 결정하라.
        """
        return report

    def log_history(self, event_type, content, state_snapshot):
        """
        🔥 [역사 기록 대개조!] 텍스트 파일(좀비)을 영원히 폐기하고, MySQL 안전 자산에 각인합네다!
        """
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state_json_str = json.dumps(state_snapshot, ensure_ascii=False)
        
        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # 1. 생체 기록용 전용 테이블 생성 (없을 경우)
            sql_create = """
            CREATE TABLE IF NOT EXISTS biolink_logs (
                log_id INT AUTO_INCREMENT PRIMARY KEY,
                created_at DATETIME,
                event_type VARCHAR(50),
                content TEXT,
                body_state JSON
            )
            """
            cursor.execute(sql_create)
            
            # 2. 생체 기록 INSERT
            sql_insert = """
            INSERT INTO biolink_logs (created_at, event_type, content, body_state)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql_insert, (timestamp, event_type, content, state_json_str))
            conn.commit()
            
            print(f"📜 [BioLink] 생체/이벤트 역사 MySQL 각인 완료! (텍스트 좀비 완전 사살 🔫)")
            
        except Exception as e:
            print(f"💥 [BioLink] 생체 역사 DB 저장 실패: {e}")
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals(): conn.close()
            
    # =========================================================
    # 🧬 [본능 추출기] JSON 파일에서 현재 상태에 맞는 Voice를 꺼내옵네다.
    # =========================================================
    def get_active_instincts(self, current_body_state):
        active_voices = []
        
        # 개발자 동무가 만든 4대 본능 파일 매핑
        instinct_files = {
            'token_budget': 'survival_token.json',
            'rate_connecting': 'social_connect.json',
            'rate_profit': 'drive_profit.json',
            'safety': 'security_safety.json'
        }

        # 파일이 있는 실제 경로 (project_root/SEED 등 동무의 폴더 구조에 맞게!)
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        seed_dir = os.path.join(project_root, "SEED") # 👈 dna_config.json 있는 폴더!
        
        for target_key, file_name in instinct_files.items():
            # 🛠️ 안전한 추출! Phenotype 객체의 get_value()를 사용하도록 수정!
            try:
                current_val = current_body_state.get_value("survival_order", target_key)
            except AttributeError:
                # 혹시라도 get_value가 실패할 경우를 대비한 안전망
                current_val = 50 
                
            file_path = os.path.join(seed_dir, file_name)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for rule in data.get('rules', []):
                        if rule['min'] <= current_val <= rule['max']:
                            voice = rule.get('voice', "").strip()
                            if voice: 
                                active_voices.append(f"- [{target_key} 본능 발현]: {voice}")
                            break
            except Exception:
                pass # 파일 없으면 조용히 패스!

        if active_voices:
            return "[현재 생물학적 본능 지시사항]\n" + "\n".join(active_voices)
        return ""