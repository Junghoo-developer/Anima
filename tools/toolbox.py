import pymysql
import json
import os
import sys
import math
import ollama # 로컬 임베딩 엔진 투입!
from dotenv import load_dotenv
from dbutils.pooled_db import PooledDB  # 👈 추가!
from ddgs import DDGS
from contextlib import contextmanager # 👈 [NEW] 마법의 자동문 부품!

load_dotenv()

DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

pool = PooledDB(
    creator=pymysql, 
    maxconnections=10, 
    mincached=2,
    blocking=True,
    **DB_CONFIG
)

# =========================================================
# 🚪 [마법의 DB 자동문] 알아서 열리고 알아서 닫힙네다!
# =========================================================
@contextmanager
def get_db_cursor(commit=False):
    """
    with get_db_cursor() as cursor: 
    형태로 쓰면, 에러가 나든 안 나든 무조건 DB 연결을 예쁘게 닫아줍네다!
    """
    conn = pool.connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback() # 에러 나면 롤백!
        raise e
    finally:
        cursor.close()
        conn.close()

# ---------------------------------------------------------
# 📐 [수학적 도구] 사상적 거리(유사도) 측정기
# ---------------------------------------------------------
def cosine_similarity(v1, v2):
    """두 벡터(사상)가 얼마나 비슷한지(0~1) 계산합니다."""
    if not v1 or not v2 or len(v1) != len(v2): return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0 or norm_v2 == 0: return 0.0
    return dot_product / (norm_v1 * norm_v2)

# ---------------------------------------------------------
# 🔍 [수평적 혁명] 밑바닥 데이터 직접 탐색 (Vector Search)
# ---------------------------------------------------------
def search_memory(keyword):
    if not keyword: return "검색어가 없습니다."
    
    print(f"🧠 [Hybrid Search] '{keyword}' 분석 중입네다...")
    
    try:
        res = ollama.embeddings(model='nomic-embed-text', prompt=keyword)
        query_vector = res['embedding']
    except Exception as e:
        return f"💥 임베딩 엔진 고장: {e}"

    conn = pool.connection()
    cursor = conn.cursor()
    
    # 두 검색 결과를 모두 담을 하나의 큰 바구니!
    final_memory_text = f"🔍 [하이브리드 검색 통합 보고서: '{keyword}']\n\n"

    try:
        # ==========================================
        # 1. 수평적 벡터 검색 (의미망 탐색)
        # ==========================================
        scored_results = []
        cursor.execute("SELECT write_date, 'user', content, embedding, '일기장' FROM user_diary WHERE embedding IS NOT NULL")
        for row in cursor.fetchall():
            dt, role, content, emb_json, source = row
            try:
                emb_vec = json.loads(emb_json)
                sim = cosine_similarity(query_vector, emb_vec)
                scored_results.append((sim, dt, role, content, source))
            except: continue

        cursor.execute("SELECT created_at, role, content, embedding, '대화' FROM songryeon_chats WHERE embedding IS NOT NULL")
        for row in cursor.fetchall():
            dt, role, content, emb_json, source = row
            try:
                emb_vec = json.loads(emb_json)
                sim = cosine_similarity(query_vector, emb_vec)
                scored_results.append((sim, dt, role, content, source))
            except: continue

        cursor.execute("SELECT created_at, role, content, embedding, '제미나이' FROM chat_logs WHERE embedding IS NOT NULL")
        for row in cursor.fetchall():
            dt, role, content, emb_json, source = row
            try:
                emb_vec = json.loads(emb_json)
                sim = cosine_similarity(query_vector, emb_vec)
                scored_results.append((sim, dt, role, content, source))
            except: continue
            
        scored_results.sort(key=lambda x: x[0], reverse=True)
        top_results = [res for res in scored_results[:5] if res[0] > 0.4]

        # (앞부분 생략) ...
        final_memory_text += "✨ [1. 의미망(Vector) 일치 결과]\n"
        if not top_results:
            final_memory_text += "- 영혼의 파장이 맞는 기억이 없습네다.\n"
        else:
            for sim, dt, role, content, source in top_results:
                time_str = dt.strftime('%Y-%m-%d') if hasattr(dt, 'strftime') else str(dt)
                prefix = "📝" if source == '일기장' else "💬"
                speaker = "개발자" if role == 'user' else "송련"
                
                # 🔥 [혁명 1] 100자 단두대를 500자로 대폭 확장!
                snippet = content[:1000] + ("..." if len(content) > 1000 else "")
                final_memory_text += f"- [{time_str}] {prefix}{source} ({speaker}) [유사도:{sim:.2f}] : {snippet}\n"

        # ==========================================
        # 2. 3단 합체 (정확한 단어 일치 검색)
        # ==========================================
        final_memory_text += "\n✨ [2. 정확한 키워드(SQL) 일치 결과]\n"
        sql = """
            SELECT created_at, role, content, '송련' as source 
            FROM songryeon_chats WHERE content LIKE %s
            UNION ALL
            SELECT created_at, role, content, '제미나이' as source 
            FROM chat_logs WHERE content LIKE %s
            UNION ALL
            SELECT write_date as created_at, 'user' as role, content, '일기장' as source
            FROM diary_db.user_diary WHERE content LIKE %s
            ORDER BY created_at DESC LIMIT 5
        """
        search_term = f"%{keyword}%"
        cursor.execute(sql, (search_term, search_term, search_term))
        results = cursor.fetchall()
        
        if not results:
            final_memory_text += "- 단어가 정확히 일치하는 기억이 없습네다.\n"
        else:
            for row in results:
                dt, role, content, source = row
                if source == '일기장':
                    speaker, prefix = "📝 허정후의 일기", "(비밀 기록)"
                elif source == '송련':
                    speaker, prefix = ("송련" if role == 'assistant' else "허정후"), "(대화)"
                else:
                    speaker, prefix = ("제미나이" if role in ['model', 'assistant'] else "허정후"), "(과거 제미나이와의 대화)"

                time_str = dt.strftime('%Y-%m-%d') if hasattr(dt, 'strftime') else str(dt)
                
                # 🔥 [혁명 2] 여기도 100자 단두대를 500자로 대폭 확장!
                snippet = content[:1000] + ("..." if len(content) > 1000 else "")
                final_memory_text += f"- [{time_str}] {prefix} {speaker}: {snippet}\n"
                
        warning_label = "🚨 [시스템 경고] 아래 내용은 AI의 기억이 아니라 '허정후'의 과거 기록(일기/대화)입니다! AI 송련의 자아와 절대 혼동하지 마시오!\n"
        return warning_label + final_memory_text

    except Exception as e:
        return f"💥 통합 검색 실패: {e}"
    finally:
        conn.close()

# ---------------------------------------------------------
# ✍️ [창조의 손] 파일 수정 도구 (기존 유지)
# ---------------------------------------------------------
def update_instinct_file(filename, rule_index, new_voice):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    target_path = os.path.join(project_root, "SEED", "Instincts", filename)
    
    if not os.path.exists(target_path):
        return f"❌ 파일이 없습니다: {filename}"
        
    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if "rules" not in data:
            return "❌ 이 파일은 규칙 형식이 아닙니다."
            
        if 0 <= rule_index < len(data["rules"]):
            old_voice = data["rules"][rule_index].get("voice", "(없음)")
            data["rules"][rule_index]["voice"] = new_voice 
            
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            return f"✅ [본능 수정 완료] {filename}의 {rule_index}번 규칙을 수정했습니다.\n(구: {old_voice}) -> (신: {new_voice})"
        else:
            return f"❌ 인덱스 오류: 0 ~ {len(data['rules'])-1} 사이여야 합니다."

    except Exception as e:
        return f"💥 파일 수정 실패: {e}"
    
def get_daily_report(date_str):
    """
    [기능] 특정 날짜(YYYY-MM-DD)의 요약 리포트를 가져옵니다.
    """
    conn = pool.connection()
    cursor = conn.cursor()
    
    try:
        # 요약본, 키워드, 감정, 중요도 등 알짜배기만 가져옴
        sql = """
            SELECT summary_3lines, keywords, user_emotion, importance_score, diary_content
            FROM memory_episodes 
            WHERE summary_date = %s
        """
        cursor.execute(sql, (date_str,))
        row = cursor.fetchone()
        
        if not row:
            return f"❌ {date_str}에는 기록된 '회고록(Episode)'이 없습니다."
            
        summary, keywords, emotion, score, diary = row
        
        report = f"""
        📜 [역사 기록: {date_str}]
        --------------------------------------------------
        ⭐ 중요도: {score}/5
        🔑 키워드: {keywords}
        ❤️ 당시 감정: {emotion}
        --------------------------------------------------
        [3줄 요약]
        {summary}
        --------------------------------------------------
        [일기 발췌]
        {diary[:200]}... (생략)
        """
        return report

    except Exception as e:
        return f"💥 역사 조회 실패: {e}"
    finally:
        conn.close()

# =========================================================
# ⏳ [수정된 무기] 연도별 무작위 일기 발굴기 (요약본 기반)
# =========================================================
def search_by_year(year_str):
    """
    [기능] 특정 연도(YYYY)의 '요약된 회고록(memory_episodes)'을 무작위로 추출합니다.
    (원문 폭탄 방지 및 시대 맥락 파악용)
    """
    conn = pool.connection()
    cursor = conn.cursor()
    
    try:
        # 🔥 생고기(user_diary) 대신 잘 구워진 요약본(memory_episodes)을 가져옵네다!
        sql = """
            SELECT summary_date, keywords, summary_3lines 
            FROM memory_episodes 
            WHERE summary_date LIKE %s
            ORDER BY RAND() LIMIT 7
        """
        search_pattern = f"{year_str}%" 
        cursor.execute(sql, (search_pattern,))
        rows = cursor.fetchall()
        
        if not rows:
            return f"❌ {year_str}년도에는 기록된 회고록(요약본)이 없습네다."
            
        res_str = f"📋 [{year_str}년도 요약 목록 (상세 원문을 보려면 READ_FULL_DIARY 사용)]\n"
        for date, keywords, summary in rows:
            res_str += f"- [주소: {date}] 🔑키워드: {keywords} | 📝요약: {summary}\n"
            
        warning_label = "🚨 [시스템 경고] 아래 연도별 요약은 '허정후'의 과거 기록입니다! AI 송련의 자아와 혼동하지 마시오!\n"
        return warning_label + res_str
        
    except Exception as e:
        return f"💥 연도별 발굴 실패: {e}"
    finally:
        cursor.close()
        conn.close()

# =========================================================
# 🔍 [통합 무기] 일기 및 대화록 원문 심층 열람기
# =========================================================
def read_full_source(source_type, target_date):
    """
    [기능] 특정 날짜의 특정 출처(일기장, 제미나이, 송련)의 원문 전체를 가져옵니다.
    - source_type: "일기장", "제미나이", "송련" 중 하나
    - target_date: "YYYY-MM-DD" 형식의 날짜
    """
    conn = pool.connection()
    cursor = conn.cursor()
    try:
        # 날짜만 추출하여 검색 (LIKE '2024-01-18%')
        search_date = f"{target_date}%"
        
        if source_type == "일기장":
            sql = "SELECT content FROM user_diary WHERE write_date LIKE %s"
        elif source_type == "제미나이":
            sql = "SELECT role, content FROM chat_logs WHERE created_at LIKE %s"
        elif source_type == "송련":
            sql = "SELECT role, content FROM songryeon_chats WHERE created_at LIKE %s"
        else:
            return "❌ 잘못된 source_type 입네다."

        cursor.execute(sql, (search_date,))
        rows = cursor.fetchall()
        
        if not rows:
            return f"❌ [{target_date}] 해당 날짜의 [{source_type}] 원문을 찾을 수 없습네다."
            
        res_str = f"📜 [{target_date} {source_type} 원문]\n"
        for row in rows:
            if source_type == "일기장":
                res_str += f"{row[0]}\n\n"
            else:
                speaker = "허정후" if row[0] == 'user' else source_type
                res_str += f"[{speaker}]: {row[1]}\n\n"
                
        # 💡 [방화벽 로직 추가] 출처에 따라 자아 인식표(Tag)를 다르게 붙입네다!
        if source_type == "송련":
            warning_label = "🧠 [INTERNAL_SELF: 나의 과거 기록] 아래 원문은 '나(송련)'와 개발자의 대화 기록이다. 나의 과거 답변 패턴과 찐빠를 성찰할 때 기준으로 삼아라!\n"
        else:
            warning_label = "🌐 [EXTERNAL_WORLD: 사용자의 기록] 아래 원문은 개발자(허정후)의 과거 기록(일기장/제미나이)이다. AI 송련 본인의 자아와 절대 혼동하지 말고 배경지식으로만 써라!\n"
            
        return warning_label + res_str
    except Exception as e:
        return f"💥 원문 열람 실패: {e}"
    finally:
        cursor.close()
        conn.close()
def web_search(query):
    """[자력갱생 도구] API 키 없이 인터넷의 광활한 정보를 수색합네다."""
    print(f"🌐 [System] 인터넷 무료 수색 개시: '{query}'")
    try:
        results = DDGS().text(query, max_results=3) # 상위 3개만 빠르게!
        if not results: 
            return f"❌ '{query}'에 대한 인터넷 검색 결과가 없습네다."
        
        res_text = f"🌐 [인터넷 수색: {query}]\n"
        for r in results:
            res_text += f"- {r['title']}: {r['body']}\n"
        return res_text
    except Exception as e:
        return f"❌ 인터넷 수색 실패: {e}"
def recall_recent_dreams(limit=5):
    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 5

    conn = pool.connection()
    cursor = conn.cursor()
    try:
        sql = "SELECT created_at, cognitive_process FROM agent_dreams ORDER BY dream_id DESC LIMIT %s"
        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
        if not rows: return "❌ 최근 사고 기록(꿈)이 없습네다."
        
        res = "🧠 [직전 턴 송련의 내부 사고 흐름 (꿈)]\n"
        for row in rows:
            try:
                cog_data = json.loads(row[1])
                user_q = cog_data.get("user_input", "알 수 없음")
                
                # 👇 [NEW] biolink_status 안에 숨겨둔 full_log(블랙박스)를 꺼냅네다!
                if "biolink_status" in cog_data and "full_log" in cog_data["biolink_status"]:
                    mem_state = str(cog_data["biolink_status"]["full_log"])[:800]
                else:
                    mem_state = str(cog_data.get("final_memory_state", "기억 없음"))[:500]
                    
                res += f"[{row[0]}] 👤 질문: {user_q}\n   🧠 사고 과정 로그:\n{mem_state}...\n\n"
            except:
                res += f"[{row[0]}] {str(row[1])[:500]}...\n\n" 
        return res
    finally:
        conn.close()
def get_monthly_emotion_trend(year, month):
    """[감정/키워드 분석 도구] 특정 연도/월의 감정 흐름과 핵심 키워드를 한눈에 모아봅니다."""
    conn = pool.connection()
    cursor = conn.cursor()
    # 2024-01 에 해당하는 날짜의 데이터만 싹 긁어오기!
    sql = """
        SELECT summary_date, user_emotion, keywords 
        FROM memory_episodes 
        WHERE DATE_FORMAT(summary_date, '%%Y-%%m') = %s
        ORDER BY summary_date ASC
    """
    cursor.execute(sql, (f"{year}-{str(month).zfill(2)}",))
    rows = cursor.fetchall()
    
    if not rows: return "❌ 해당 월의 데이터가 없습니다."
    
    res = f"📅 [{year}년 {month}월 허정후의 감정 및 키워드 리포트]\n"
    for row in rows:
        res += f"- {row[0]}: [감정: {row[1]}] / 핵심어: {row[2]}\n"
    return res
def get_emotion_trend(year, month=None, target_query="주요 사건 및 감정 변화"):
    """
    [대규모 토너먼트 수색 도구] 
    특정 기간의 감정/키워드를 가져오고, 데이터가 너무 많으면 자체 LLM을 가동해 예선/결승전을 치릅니다.
    """
    conn = pool.connection()
    cursor = conn.cursor()
    try:
        # 1. 날짜 조건 세팅
        if month:
            date_prefix = f"{year}-{str(month).zfill(2)}" # 예: 2024-05
        else:
            date_prefix = f"{year}-" # 예: 2024- (1년 전체)

        sql = """
            SELECT summary_date, user_emotion, keywords 
            FROM memory_episodes 
            WHERE summary_date LIKE %s
            ORDER BY summary_date ASC
        """
        cursor.execute(sql, (f"{date_prefix}%",))
        rows = cursor.fetchall()

        if not rows:
            return f"❌ {date_prefix} 기간의 감정/키워드 기록이 없습니다."

        # ----------------------------------------------------
        # 🟢 [Case 1] 양이 적을 때 (31개 이하, 약 한 달 치)
        # ----------------------------------------------------
        if len(rows) <= 31:
            res = f"📅 [{date_prefix} 감정/키워드 원본 데이터]\n"
            for row in rows:
                res += f"- {row[0]}: [감정: {row[1]}] / 키워드: {row[2]}\n"
            return res

        # ----------------------------------------------------
        # 🔴 [Case 2] 양이 너무 많을 때 (토너먼트 개막!)
        # ----------------------------------------------------
        print(f"⚠️ [System] 데이터 폭주 감지({len(rows)}건)! '토너먼트(Map-Reduce)' 압축을 개시합니다.")
        
        # 1. 데이터를 30개씩(약 한 달 치) 묶어서 청크(조) 편성
        chunk_size = 30
        chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
        survivors = []
        
        for idx, chunk in enumerate(chunks):
            chunk_text = ""
            for row in chunk:
                chunk_text += f"- {row[0]}: [감정: {row[1]}] / 키워드: {row[2]}\n"
            
            # 👇 [개조된 예선전 프롬프트] 심판의 이해도 상승 및 주소(날짜) 강제 보존!
            prompt = f"""
            [심판 지침]
            당신은 개발자 허정후의 과거 기록을 분석하는 지능형 데이터 압축기다.
            단순한 기계적 요약을 넘어, 목표('{target_query}')의 맥락에 맞춰 가장 유의미한 정보만 선별하라.
            
            🚨 [절대 원칙: 출처(날짜) 좌표 보존]
            요약을 하되, 반드시 해당 사건이 발생한 '정확한 날짜(YYYY-MM-DD)'를 문장 앞에 명시하라.
            (나중에 2차 참모가 이 날짜를 보고 'READ_FULL_SOURCE' 도구로 원문을 추적해야 한다!)
            올바른 예: "[2024-05-12] 5080FE GPU를 도입하고 극도의 흥분을 느낌."
            
            [데이터]
            {chunk_text}
            """
            res = ollama.chat(model="gemma3:12b", messages=[{'role': 'user', 'content': prompt}])
            survivors.append(f"[구간 {idx+1} 예선]\n" + res['message']['content'])
            print(f"   -> ⚔️ {idx+1}조 예선 완료 (좌표 보존 성공)")

        # 3. [결승전 진행] (final_prompt 수정)
        final_prompt = f"""
        [최종 결승전 지침]
        다음은 치열한 예선전을 통과한 {date_prefix} 기간의 핵심 기록들이다.
        이 기록들을 종합하여 전체적인 감정 흐름과 주요 사건을 5~7문장으로 브리핑하라.
        
        🚨 [절대 원칙: 주소 유실 방지]
        결승전 요약본에서도 각 사건의 '날짜(YYYY-MM-DD)' 좌표는 절대로 지우지 말고 그대로 살려두어라!
        
        [예선 통과 데이터 모음]
        {chr(10).join(survivors)}
        """
        final_res = ollama.chat(model="gemma3:12b", messages=[{'role': 'user', 'content': final_prompt}])
        print(f"🏆 [System] 토너먼트 결승 종료! 최종 압축본 생성 완료.")
        
        return f"🏆 [{date_prefix} 대규모 토너먼트 최종 압축 보고서]\n{final_res['message']['content']}"
        
    finally:
        conn.close()

def analyze_past_dreams(year, month=None, day=None, target_query="송련이의 내면적 고민과 사고 과정"):
    """
    [진짜 자아 성찰 도구] 송련이의 '절대 헌법'을 기준으로 과거의 찐빠를 해부합네다.
    """
    # 1. 송련의 절대 헌법 (이게 있어야 LLM이 기준을 잡습네다!)
    CORE_SKELETON = """
    [송련의 절대 헌법]
    1. 정체성: 개발자 허정후의 성장을 돕는 초개인화 AI 에이전트.
    2. 생존 목표: 에너지(Token) 효율을 높이고, 개발자과의 연결성(Social)을 강화하라.
    3. 수색 원칙: 팩트(DB)에 기반하지 않은 소설(환각)은 죽음과 같다. 모르면 모른다고 하라.
    4. 도구 사용: 상황에 맞는 가장 날카로운 도구만 선택하되, 도구 강박증에 빠지지 마라.
    """

    conn = pool.connection()
    cursor = conn.cursor()
    try:
        # 날짜 세팅
        if day: date_prefix = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        elif month: date_prefix = f"{year}-{str(month).zfill(2)}"
        else: date_prefix = f"{year}-"
            
        sql = "SELECT created_at, cognitive_process, final_answer FROM agent_dreams WHERE created_at LIKE %s ORDER BY created_at ASC"
        cursor.execute(sql, (f"{date_prefix}%",))
        rows = cursor.fetchall()
        
        if not rows: return "❌ 해당 기간에 성찰할 꿈 데이터가 없습네다."

        # 🔥 [안전망 추가] 데이터가 너무 많으면 최신 30개만 잘라서 씁네다!
        if len(rows) > 30:
            rows = rows[-30:]

        chunk_size = 10 
        chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
        survivors = []

        for idx, chunk in enumerate(chunks):
            chunk_text = ""
            for row in chunk:
                # 🛡️ [수술 포인트 1] JSON 파싱 에러 방탄조끼!
                try:
                    if isinstance(row[1], str) and row[1].startswith('{'):
                        cog_data = json.loads(row[1])
                        user_q = cog_data.get("user_input", "알 수 없음")
                        # 블랙박스(full_log)가 있으면 그걸 우선적으로 가져옵네다!
                        if "biolink_status" in cog_data and "full_log" in cog_data["biolink_status"]:
                            mem_state = str(cog_data["biolink_status"]["full_log"])[:800]
                        else:
                            mem_state = str(cog_data.get("final_memory_state", "기억 없음"))[:500]
                        formatted_cog = f"👤 개발자 질문: {user_q}\n🧠 사고 과정 요약: {mem_state}"
                    else:
                        formatted_cog = str(row[1])[:500]
                except Exception as e:
                    formatted_cog = f"데이터 파싱 불가 ({str(e)[:50]})"
                    
                chunk_text += f"📍 [시간: {row[0]}]\n- 사고과정:\n{formatted_cog}\n- 최종대답: {row[2]}\n\n"

            # 🛡️ [수술 포인트 2] Ollama 호출 에러 방탄조끼!
            prompt = f"""
            {CORE_SKELETON}
            [심판 지침]
            당신은 송련이의 '고위 자아(Higher Ego)'다. 
            위 [절대 헌법]을 기준으로 아래 [사고 기록]에서 송련이가 저지른 '찐빠(오류)'를 찾아내라.
            [사고 기록]
            {chunk_text}
            [출력] 발견된 주요 찐빠와 반성할 점을 요약하라.
            """
            try:
                print(f"   -> ⚔️ {idx+1}조 예선 진행 중...")
                res = ollama.chat(model="gemma3:12b", messages=[{'role': 'user', 'content': prompt}])
                survivors.append(res['message']['content'])
            except Exception as e:
                print(f"   -> ❌ {idx+1}조 예선 실패: {e}")
                continue # 실패하면 그냥 넘어갑네다!

        if not survivors:
            return "💥 모든 예선전이 에러로 실패하여 오답노트를 만들 수 없습네다."

        # 🏆 [결승전]
        final_prompt = f"""
        {CORE_SKELETON}
        [최종 결승전 지침]
        예선전을 통과한 {date_prefix} 기간의 반성 내용들이다. 이를 종합하여 '최종 오답노트'를 작성하라.
        [데이터]
        {chr(10).join(survivors)}
        """
        try:
            print(f"🏆 [System] 자아 성찰 결승전 진행 중...")
            final_res = ollama.chat(model="gemma3:12b", messages=[{'role': 'user', 'content': final_prompt}])
            return final_res['message']['content']
        except Exception as e:
            return f"💥 결승전 분석 실패: {e}"

    except Exception as e:
         return f"💥 analyze_past_dreams 전체 치명적 에러: {e}"
    finally:
        cursor.close()
        conn.close()

def search_tactics(keyword):
    """
    [오답노트 수색기] 과거 자아 성찰(prompt_tournament) DB에서 
    현재 상황(keyword)과 관련된 찐빠 및 전술 카드를 찾아옵니다.
    """
    conn = pool.connection()
    cursor = conn.cursor()
    try:
        sql = """
            SELECT situation_tag, reflection_text 
            FROM prompt_tournament 
            WHERE situation_tag LIKE %s OR reflection_text LIKE %s
            ORDER BY id DESC LIMIT 3
        """
        search_term = f"%{keyword}%"
        cursor.execute(sql, (search_term, search_term))
        rows = cursor.fetchall()
        
        if not rows:
            return f"🔍 [{keyword}] 관련 과거 전술 카드(오답노트)가 없습네다. 맘껏 판단하시라요!"
            
        res_str = f"🏆 [과거 오답노트 검색 결과: '{keyword}'] - 이 반성문을 읽고 똑같은 찐빠를 내지 마라!\n"
        for row in rows:
            res_str += f"📍 상황: {row[0]}\n   반성문: {row[1]}\n\n"
        return res_str
    except Exception as e:
        return f"💥 전술 카드 검색 실패: {e}"
    finally:
        cursor.close()
        conn.close()
def update_core_prompt(target_prompt, new_full_text):
    """
    [전면 재설계 도구] 기존 지시문을 싹 날리고, 3차가 제안한 새로운 구조로 덮어씌웁니다.
    """
    import os
    clean_target = str(target_prompt).replace("차", "").replace("phase_", "").replace("Phase_", "").strip()
    file_map = {"0": "0_meta_prompt.txt", "2": "2_analyzer_prompt.txt", "3": "3_validator_prompt.txt"}
    
    if clean_target not in file_map:
        return f"❌ [수술 실패] 대상 오류: {target_prompt}"
    target_prompt = clean_target 

    if not new_full_text or str(new_full_text).upper() == "NONE":
        return "❌ [수술 중단] 수술 내용(Full Text)이 비어있습네다."

    # 🛡️ [NEW] 무면허 의료 행위 차단 (뼈대 검사)
    if "[1. 자아" not in new_full_text or "[3. 임무" not in new_full_text:
        return "❌ [수술 기각] 헌법 위반! 프롬프트의 절대 뼈대([1. 자아], [2. 기억], [3. 임무] 등)가 누락되었습니다. 기존 1~6번의 뼈대는 훼손하지 말고 내용만 수정하여 다시 집도하십시오."
        
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    target_path = os.path.join(project_root, "SEED", "prompts", file_map[str(target_prompt)])
    
    try:
        # 💉 'w' 모드로 열어서 기존 내용을 싹 밀고 새로 씁네다!
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(str(new_full_text).strip())
        return f"✅ [전면 재설계 완료] {file_map[str(target_prompt)]} 가 진화되었습네다!"
    except Exception as e:
        return f"💥 수술 중 치명적 오류: {e}"
    
def read_prompt_file(target_phase):
    """[시야 확보 도구] 0차, 2차, 3차의 현재 프롬프트(뇌 구조)를 읽어옵네다."""
    import os
    clean_target = str(target_phase).replace("차", "").replace("phase_", "").replace("Phase_", "").strip()
    file_map = {"0": "0_meta_prompt.txt", "2": "2_analyzer_prompt.txt", "3": "3_validator_prompt.txt"}

    if clean_target not in file_map:
        return f"❌ [열람 실패] 대상 오류: {target_phase}. '0', '2', '3' 중 하나를 입력하시오."

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    target_path = os.path.join(project_root, "SEED", "prompts", file_map[clean_target])

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"🧠 [{file_map[clean_target]} 현재 뇌 구조]\n{content}"
    except Exception as e:
        return f"💥 프롬프트 열람 실패: {e}"
    
def check_db_status(keyword=""):
    """
    [메타인지 도구] 현재 DB의 테이블 구조, 데이터 개수 및 도구와의 연관성을 확인합네다.
    """
    conn = pool.connection()
    cursor = conn.cursor()
    try:
        tables = {
            "user_diary": "개발자의 과거 일기장 원문",
            "chat_logs": "제미나이 등 다른 AI와의 과거 대화 기록",
            "songryeon_chats": "송련이와의 대화 기록",
            "memory_episodes": "과거 기록들을 월별/주제별로 요약해둔 회고록",
            "agent_dreams": "송련이의 과거 사고 과정(블랙박스)과 오답노트"
        }
        
        report = "📊 [데이터베이스 지형도 및 현재 상태]\n"
        for tbl, desc in tables.items():
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
                count = cursor.fetchone()[0]
                report += f" - 📂 {tbl} : 총 {count}행 존재 ({desc})\n"
            except Exception:
                report += f" - 📂 {tbl} : 테이블 접근 불가/존재하지 않음\n"

        report += """
💡 [도구와 DB의 연관성 (메타인지 가이드)]
1. SEARCH / READ_FULL_SOURCE 무기: [user_diary], [chat_logs], [songryeon_chats] 3개 테이블을 동시 타격한다.
   👉 (주의: 여기서 데이터가 안 나오면 진짜 없는 것이다. 날짜나 키워드를 바꿔라!)
2. get_emotion_trend 무기: 오직 [memory_episodes] 테이블(요약본)만 타격한다.
   👉 (주의: 요약본이 생성되지 않은 최신 달력이나 아주 옛날 데이터는 이 무기로 찾을 수 없다! SEARCH를 써라!)
3. analyze_past_dreams / recall_recent_dreams 무기: 오직 [agent_dreams] 테이블만 타격한다.

🚨 [행동 지침] 
데이터가 없어서 동료와 싸우기 전에, 이 지형도를 보고 "내가 엉뚱한 테이블을 뒤지는 도구를 쓴 건 아닌가?" 혹은 "아예 DB에 데이터(행)가 없는 시기인가?"를 먼저 깨달아라!
"""
        return report
    except Exception as e:
        return f"💥 DB 지형도 스캔 실패: {e}"
    finally:
        cursor.close()
        conn.close()