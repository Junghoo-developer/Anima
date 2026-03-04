import json
import ollama
import sys
import os
import pymysql
from dotenv import load_dotenv

# 환경 변수 로드 (DB 접속용)
load_dotenv()

# DB 설정 (main.py나 tools에서 쓰는 것과 동일하게 맞춤)
DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

# 도구 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# 저장 도구 가져오기
try:
    from tools.process_daily_memory import log_message_to_db
except ImportError:
    from tools.process_daily_memory import log_message_to_db

class MemoryBuffer:
    def __init__(self, model_name="gemma3:12b", max_context=30):
        """
        [기억 탱크]
        - max_context: 한 번에 기억할 대화 턴 수 (늘렸습니다! 10 -> 30)
        """
        self.model = model_name
        self.max_context = max_context * 2 # (질문+답변) 쌍이므로 2배
        self.history = []     # 대화 내용 (RAM)
        self.summary = ""     # 요약본
        
        # 🔥 [핵심] 태어나자마자 지난 기억을 로드한다!
        self._load_recent_history_from_db()

    def _load_recent_history_from_db(self):
        """
        [기억 복원 장치]
        DB에 접속해서 가장 최근 대화 내용을 RAM으로 퍼올린다.
        이게 있어야 껐다 켜도 "아까 하던 얘기"를 기억함!
        """
        print("📥 [Memory] 지난 대화 기록을 뇌에 로드 중...")
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # 최근 N개의 대화를 가져옴 (송련이와 개발자의 대화만)
            # chat_logs(제미나이)는 헷갈리니까 안 가져옴 (필요하면 UNION 가능)
            sql = """
                SELECT role, content 
                FROM songryeon_chats 
                ORDER BY created_at DESC 
                LIMIT %s
            """
            cursor.execute(sql, (self.max_context,))
            rows = cursor.fetchall()
            
            # DB는 최신순(DESC)으로 가져오지만, 대화는 시간순(ASC)이어야 함 -> 뒤집기
            for role, content in reversed(rows):
                # DB의 role을 Ollaam 포맷으로 변환
                msg_role = "user" if role == "user" else "assistant"
                self.history.append({"role": msg_role, "content": content})
                
            print(f"✅ [Memory] 기억 복원 완료 ({len(self.history)}개 메시지)")
            
        except Exception as e:
            print(f"⚠️ 기억 로드 실패 (초기화 상태로 시작): {e}")
        finally:
            conn.close()

    def add_message(self, role, content):
        """
        메시지 추가 및 DB 즉시 저장
        """
        self.history.append({"role": role, "content": content})
        
        # 1. DB에 영구 저장 (잊지 않도록)
        # (시스템 메시지나 검색 결과 같은 건 DB에 굳이 안 넣어도 됨, 대화만 저장)
        if role in ["user", "assistant"]:
            log_message_to_db(role, content)

        # 2. 기억 용량 관리 (오래된 것 삭제 및 요약)
        if len(self.history) > self.max_context:
            self._compress_memory()

    def _compress_memory(self):
        """
        [기억 압축]
        용량이 차면 오래된 기억을 잘라내고 '요약본'으로 만듦.
        """
        # 절반 정도를 잘라내서 요약함
        cut_off = len(self.history) // 2
        to_compress = self.history[:cut_off]
        self.history = self.history[cut_off:] # 남은 기억

        conversation_text = ""
        for msg in to_compress:
            speaker = "개발자" if msg['role'] == 'user' else "송련"
            conversation_text += f"{speaker}: {msg['content']}\n"

        # 요약 프롬프트 (간결하게 수정)
        prompt = f"""
        [이전 요약]: {self.summary}
        
        [지나간 대화]:
        {conversation_text}
        
        [지령]:
        위 내용을 통합하여 '현재까지의 상황'을 3문장 이내로 요약하라.
        중요한 정보(사용자 의도, 현재 주제)는 남겨라.
        """
        
        try:
            response = ollama.chat(model=self.model, messages=[
                {'role': 'user', 'content': prompt}
            ])
            self.summary = response['message']['content']
            print(f"🧹 [Memory] 뇌 용량 확보를 위해 기억을 압축했습니다.")
            
        except Exception as e:
            print(f"💥 압축 실패: {e}")

    def get_full_context(self, system_prompt):
        """
        [최종 프롬프트 조립]
        System Prompt + Summary + History
        """
        messages = [{'role': 'system', 'content': system_prompt}]
        
        # 요약된 과거가 있으면 넣어줌
        if self.summary:
            messages.append({
                'role': 'system', 
                'content': f"[지난 이야기 요약]: {self.summary}"
            })
            
        # 최근 대화 붙이기
        messages.extend(self.history)
        
        return messages
    def get_context_string(self, limit=10):
        """최근 대화 N개를 문자열로 예쁘게 묶어서 반환합네다."""
        res = ""
        for msg in self.history[-limit:]:
            speaker = "사령관" if msg['role'] == 'user' else "송련"
            res += f"{speaker}: {msg['content']}\n"
        return res