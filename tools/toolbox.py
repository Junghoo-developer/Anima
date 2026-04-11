import pymysql
import json
import os
import sys
import math
import ollama 
import re # 👈 함수 위쪽에 정규식 모듈이 없다면 추가!
import html
import zipfile
from dotenv import load_dotenv
from neo4j import GraphDatabase 
from dbutils.pooled_db import PooledDB
from ddgs import DDGS
from contextlib import contextmanager 

load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
desktop_root = os.path.dirname(project_root)
onedrive_root = os.path.dirname(desktop_root)
ARTIFACT_EXTENSIONS = {".pptx", ".txt", ".md", ".json", ".py", ".docx"}

# =========================================================
# 🗄️ [1. 기존 RDBMS 감옥] MySQL 접속 정보 (백업용)
# =========================================================
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
# 🌌 [2. 새로운 신경망 벙커] Neo4j 접속 정보
# =========================================================
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD") 

neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

@contextmanager
def get_db_session():
    """[마법의 자동문] Neo4j 세션을 안전하게 열고 닫습네다."""
    session = neo4j_driver.session()
    try:
        yield session
    finally:
        session.close()

# ---------------------------------------------------------
# 📐 수학 및 유틸리티
# ---------------------------------------------------------
def cosine_similarity(v1, v2):
    if not v1 or not v2 or len(v1) != len(v2): return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0 or norm_v2 == 0: return 0.0
    return dot_product / (norm_v1 * norm_v2)


def _normalize_artifact_key(text):
    return re.sub(r"[\s_\-./\\]+", "", str(text or "").strip()).lower()


def _iter_artifact_candidates():
    seen = set()

    for root, _, files in os.walk(project_root):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in ARTIFACT_EXTENSIONS:
                continue
            path = os.path.join(root, name)
            if path not in seen:
                seen.add(path)
                yield path

    try:
        for entry in os.scandir(onedrive_root):
            if not entry.is_file():
                continue
            ext = os.path.splitext(entry.name)[1].lower()
            if ext not in ARTIFACT_EXTENSIONS:
                continue
            if entry.path not in seen:
                seen.add(entry.path)
                yield entry.path
    except OSError:
        return


def _find_artifact_path(artifact_hint):
    hint = str(artifact_hint or "").strip().strip('"').strip("'")
    if not hint:
        return ""

    if os.path.isfile(hint):
        return os.path.abspath(hint)

    hint_key = _normalize_artifact_key(os.path.basename(hint))
    hint_tokens = [token for token in re.split(r"\s+", hint.lower()) if token]
    best_score = -1
    best_path = ""

    for candidate in _iter_artifact_candidates():
        base = os.path.basename(candidate)
        stem = os.path.splitext(base)[0]
        candidate_key = _normalize_artifact_key(base)
        stem_key = _normalize_artifact_key(stem)

        score = 0
        if hint_key and hint_key == candidate_key:
            score += 100
        if hint_key and hint_key == stem_key:
            score += 95
        if hint_key and hint_key in candidate_key:
            score += 70
        if hint_key and hint_key in stem_key:
            score += 65
        if hint_tokens:
            token_hits = sum(1 for token in hint_tokens if token and token in base.lower())
            score += token_hits * 10
        if "ANIMA" in base.upper():
            score += 2

        if score > best_score:
            best_score = score
            best_path = candidate

    return best_path if best_score > 0 else ""


def _read_text_like_artifact(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _read_pptx_artifact(path):
    slides = []
    with zipfile.ZipFile(path) as zf:
        slide_names = [
            name for name in zf.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ]
        slide_names.sort(key=lambda name: int(re.search(r"slide(\d+)\.xml$", name).group(1)))

        for idx, name in enumerate(slide_names[:20], start=1):
            xml_text = zf.read(name).decode("utf-8", errors="ignore")
            texts = [html.unescape(t).strip() for t in re.findall(r"<a:t>(.*?)</a:t>", xml_text, re.DOTALL)]
            texts = [t for t in texts if t]
            if texts:
                slides.append(f"[slide {idx}] " + " ".join(texts))

    return "\n".join(slides)


def _read_docx_artifact(path):
    with zipfile.ZipFile(path) as zf:
        xml_text = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    texts = [html.unescape(t).strip() for t in re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml_text, re.DOTALL)]
    texts = [t for t in texts if t]
    return "\n".join(texts)


def read_artifact(artifact_hint):
    """
    Resolve and read a local artifact by path or fuzzy name.
    Supported: pptx, txt, md, json, py, docx.
    """
    hint = str(artifact_hint or "").strip()
    if not hint:
        return "[artifact error] Empty artifact hint.", []

    path = _find_artifact_path(hint)
    if not path:
        return f"[artifact not found] Could not resolve '{hint}'.", []

    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in {".txt", ".md", ".json", ".py"}:
            body = _read_text_like_artifact(path)
        elif ext == ".pptx":
            body = _read_pptx_artifact(path)
        elif ext == ".docx":
            body = _read_docx_artifact(path)
        else:
            return f"[artifact unsupported] {ext} is not supported yet for '{path}'.", [path]
    except Exception as e:
        return f"[artifact read error] Failed to read '{path}': {e}", [path]

    body = body.strip()
    if not body:
        body = "(No readable text extracted.)"

    header = (
        f"[artifact]\n"
        f"path: {path}\n"
        f"type: {ext or 'unknown'}\n"
        f"name: {os.path.basename(path)}\n\n"
    )
    return header + body[:12000], [path]

# tools/toolbox.py 내부 read_full_source 함수 수정

def read_full_source(source_type, target_date):
    """특정 날짜의 특정 출처의 원문 전체와 그날의 맥락(에피소드)을 함께 가져옵니다."""
    
    import re
    alt_date = target_date
    match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", target_date)
    if match:
        y, m, d = match.groups()
        alt_date = f"{y} {int(m)} {int(d)}"

    # 💡 [안전장치]: 파이썬 단에서 미리 공백을 제거해줍니다!
    t_date = target_date.strip()
    a_date = alt_date.strip()

    try:
        with get_db_session() as session:
            # 👇 [V8.7 잔소리 제거 수술]: node_id를 지우고, coalesce로 빈 값을 방어합니다!
            if source_type == "일기장":
                cypher = """
                MATCH (r) 
                WHERE (r:PastRecord OR r:Diary)
                  AND (
                       trim(coalesce(r.date, '')) STARTS WITH $date 
                    OR trim(coalesce(r.date, '')) = $alt_date 
                    OR trim(coalesce(r.date, '')) STARTS WITH ($alt_date + ' ')
                    OR trim(coalesce(r.id, '')) STARTS WITH $date 
                    OR trim(coalesce(r.id, '')) = $alt_date 
                    OR trim(coalesce(r.id, '')) STARTS WITH ($alt_date + ' ')
                  )
                OPTIONAL MATCH (e:Episode)-[:HAS_RAW_DATA]->(r)
                RETURN e.summary AS summary, r.content AS content
                ORDER BY coalesce(r.date, r.id, '') ASC
                """
            elif source_type == "제미나이":
                cypher = """
                MATCH (r) 
                WHERE (r:PastRecord OR r:GeminiChat)
                  AND (
                       trim(coalesce(r.date, '')) STARTS WITH $date 
                    OR trim(coalesce(r.date, '')) = $alt_date 
                    OR trim(coalesce(r.date, '')) STARTS WITH ($alt_date + ' ')
                    OR trim(coalesce(r.id, '')) STARTS WITH $date 
                    OR trim(coalesce(r.id, '')) = $alt_date 
                    OR trim(coalesce(r.id, '')) STARTS WITH ($alt_date + ' ')
                  )
                OPTIONAL MATCH (e:Episode)-[:HAS_RAW_DATA]->(r)
                RETURN e.summary AS summary, r.role AS role, r.content AS content 
                ORDER BY coalesce(r.date, r.id, '') ASC
                """
            elif source_type == "송련":
                cypher = """
                MATCH (r) 
                WHERE (r:PastRecord OR r:SongryeonChat)
                  AND (
                       trim(coalesce(r.date, '')) STARTS WITH $date 
                    OR trim(coalesce(r.date, '')) = $alt_date 
                    OR trim(coalesce(r.date, '')) STARTS WITH ($alt_date + ' ')
                    OR trim(coalesce(r.id, '')) STARTS WITH $date 
                    OR trim(coalesce(r.id, '')) = $alt_date 
                    OR trim(coalesce(r.id, '')) STARTS WITH ($alt_date + ' ')
                  )
                OPTIONAL MATCH (e:Episode)-[:HAS_RAW_DATA]->(r)
                RETURN e.summary AS summary, r.role AS role, r.content AS content 
                ORDER BY coalesce(r.date, r.id, '') ASC
                """
            else:
                return "❌ 잘못된 source_type 입네다.", []

            result = session.run(cypher, date=t_date, alt_date=a_date)
            rows = [record for record in result]
            
            if not rows: 
                return f"❌ [{target_date}] 해당 날짜의 [{source_type}] 원문을 찾을 수 없습네다. (DB에 데이터가 존재하지 않습니다)", []
                
            res_str = f"📜 [{target_date} {source_type} 원문 열람]\n"
            
            # 에피소드 요약이 있으면 붙여주고, 없으면 생략합니다!
            first_summary = rows[0].get('summary')
            if first_summary:
                res_str += f"📌 [그날의 시대적 배경 요약]: {first_summary}\n\n"
            else:
                res_str += f"📌 [그날의 시대적 배경 요약]: (에피소드 요약 노드가 존재하지 않습니다)\n\n"
                
            res_str += "--- [원문 기록 시작] ---\n"

            for row in rows:
                if source_type == "일기장":
                    res_str += f"{row.get('content', '(내용 없음)')}\n\n"
                else:
                    speaker = "허정후" if row.get('role') == 'user' else source_type
                    res_str += f"[{speaker}]: {row.get('content', '(내용 없음)')}\n\n"
                    
            if source_type == "송련":
                warning_label = "🧠 [INTERNAL_SELF: 나의 과거 기록] 아래 원문은 '나(송련)'와 개발자의 대화 기록이다. 성찰 기준으로 삼아라!\n"
            else:
                warning_label = "🌐 [EXTERNAL_WORLD: 사용자의 기록] 아래 원문은 개발자(허정후)의 과거 기록이다. 혼동하지 마라!\n"
                
            return warning_label + res_str, [target_date]
            
    except Exception as e: 
        return f"💥 원문 열람 실패: {e}", []

def search_memory(keyword):
    """
    [V4.6 하이브리드 벡터 검색 엔진]
    단순 키워드 일치가 아닌, 1024차원 의미(Semantic) 공간에서 가장 가까운 기억을 찾아냅네다!
    """
    print(f"🔍 [시맨틱 레이더 가동] '{keyword}'의 의미를 1024차원 공간에서 추적 중...")
    
    try:
        # 1. 동무의 키워드를 1024차원 벡터로 변환!
        response = ollama.embeddings(model="mxbai-embed-large", prompt=keyword)
        query_vector = response["embedding"]

        # 2. Neo4j 벡터 인덱스 타격! (가장 의미가 비슷한 상위 3개의 일일 요약을 물어옵네다)
        cypher = """
        CALL db.index.vector.queryNodes('episode_embedding', 3, $query_vector)
        YIELD node, score
        // 유사도가 0.5 이상인 유의미한 기억만 필터링! (숫자는 조절 가능)
        WHERE score >= 0.5 
        RETURN node.date AS date, node.summary AS summary, node.keywords AS keywords, score
        ORDER BY score DESC
        """
        
        with get_db_session() as session: 
            records = session.run(cypher, query_vector=query_vector).data()

        if not records:
            # 💡 [핵심] 실패해도 텍스트와 빈 배열([])을 함께 반환!
            return f"❌ '{keyword}'와(과) 의미적으로 일치하는 과거 기억이 없습네다.", []

        result_text = f"🎯 '{keyword}'에 대한 시맨틱 검색 결과 (유사도 순):\n\n"
        found_dates = [] # 💡 진짜 좌표를 담을 바구니!

        for r in records:
            result_text += f"📅 [출처: 일기장|{r['date']}] (유사도: {r['score']:.3f})\n"
            result_text += f"📝 핵심 요약: {r['summary']}\n"
            result_text += f"🔑 관련 키워드: {r['keywords']}\n"
            result_text += "-" * 30 + "\n"
            
            # 💡 [핵심] DB에서 꺼낸 정확한 날짜를 배열에 저장!
            found_dates.append(r['date'])
            
        return result_text, found_dates # 💡 두 개를 동시에 반환!

    except Exception as e:
        error_msg = f"🚨 벡터 검색 엔진 고장: {e}"
        print(error_msg)
        return error_msg

def get_emotion_trend(keyword, target_query="주요 사건 및 감정 변화"):
    """[대규모 토너먼트 수색 도구]"""
    try:
        with get_db_session() as session:
            date_prefix = str(keyword).strip()
            cypher = """
            MATCH (e:Episode)-[:FEELING]->(emo:Emotion)
            WHERE e.date STARTS WITH $date_prefix
            RETURN e.date AS date, emo.name AS emotion, e.keywords AS keywords
            ORDER BY e.date ASC
            """
            result = session.run(cypher, date_prefix=date_prefix)
            rows = [record for record in result]

            if not rows: return f"❌ '{date_prefix}' 기간의 감정/키워드 기록이 없습니다."

            if len(rows) <= 31:
                res = f"📅 [{date_prefix} 감정/키워드 원본 데이터]\n"
                for row in rows: res += f"- {row['date']}: [감정: {row['emotion']}] / 키워드: {row['keywords']}\n"
                return res

            print(f"⚠️ [System] 데이터 폭주 감지({len(rows)}건)! '토너먼트(Map-Reduce)' 압축을 개시합니다.")
            chunk_size = 30
            chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
            survivors = []
            
            for idx, chunk in enumerate(chunks):
                chunk_text = "".join([f"- {row['date']}: [감정: {row['emotion']}] / 키워드: {row['keywords']}\n" for row in chunk])
                prompt = f"[심판 지침]\n당신은 지능형 데이터 압축기다. 목표('{target_query}')의 맥락에 맞춰 선별하되 날짜 좌표를 문장 앞에 명시하라.\n[데이터]\n{chunk_text}"
                res = ollama.chat(model="gemma3:12b", messages=[{'role': 'user', 'content': prompt}])
                survivors.append(f"[구간 {idx+1} 예선]\n" + res['message']['content'])
                print(f"   -> ⚔️ {idx+1}조 예선 완료")

            final_prompt = f"[최종 결승전 지침]\n예선전을 통과한 핵심 기록들이다. 5~7문장으로 브리핑하되 '날짜(YYYY-MM-DD)' 좌표를 그대로 살려라!\n[예선 통과 데이터]\n{chr(10).join(survivors)}"
            final_res = ollama.chat(model="gemma3:12b", messages=[{'role': 'user', 'content': final_prompt}])
            print(f"🏆 [System] 토너먼트 결승 종료!")
            return f"🏆 [{date_prefix} 대규모 토너먼트 최종 압축 보고서]\n{final_res['message']['content']}"
    except Exception as e: return f"💥 시대 탐색 실패: {e}"

def _dream_row_trace_section(row):
    """Dream 노드 사고 과정: phase_* 를 JSON으로 합침"""
    data = dict(row)
    trace = {}
    if data.get("p_minus1"):
        trace["phase_minus1_intent"] = data["p_minus1"]
    for pykey, label in (
        ("p0", "phase_0_history"),
        ("p1", "phase_1_actions"),
        ("p2", "phase_2_summaries"),
        ("p3", "phase_3_summary"),
    ):
        val = data.get(pykey)
        if val:
            trace[label] = val
    if trace:
        body = json.dumps(trace, ensure_ascii=False, indent=2)
        return f"\n- 사고_트레이스(JSON, phase_*):\n{body}"
    legacy = data.get("full_log")
    if legacy:
        return f"\n- 사고과정(레거시 full_log):\n{legacy}"
    return ""


def search_tactics(keyword):
    """과거 자아 성찰(TacticCard) 수색기"""
    try:
        with get_db_session() as session:
            cypher = """
            MATCH (t:TacticCard)
            WHERE t.situation_tag CONTAINS $keyword OR t.reflection_text CONTAINS $keyword
            RETURN t.situation_tag AS tag, t.reflection_text AS reflection
            ORDER BY t.date DESC LIMIT 3
            """
            result = session.run(cypher, keyword=keyword)
            rows = [record for record in result]
            if not rows: return f"🔍 [{keyword}] 관련 과거 전술 카드가 없습네다."
            res_str = f"🏆 [과거 오답노트 검색 결과: '{keyword}']\n"
            for row in rows: res_str += f"📍 상황: {row['tag']}\n   반성문: {row['reflection']}\n\n"
            return res_str
    except Exception as e: return f"💥 전술 카드 검색 실패: {e}"

def search_supply_topics(keyword=""):
    """
    [공급 감사 주제] SupplyTopic 노드 검색
    """
    kw = (keyword or "").strip()
    try:
        with get_db_session() as session:
            if not kw:
                cypher = """
                MATCH (tt:SupplyTopic)
                OPTIONAL MATCH (sd:SecondDream)-[:TRACKS_TOPIC]->(tt)
                WITH tt, max(sd.date) AS last_seen
                RETURN tt.slug AS slug, tt.title AS title, tt.status AS status,
                       last_seen AS last_audit
                ORDER BY last_seen DESC NULLS LAST, tt.slug ASC LIMIT 20
                """
                result = session.run(cypher)
            else:
                cypher = """
                MATCH (tt:SupplyTopic)
                WHERE toLower(coalesce(tt.title, '')) CONTAINS toLower($kw)
                   OR toLower(coalesce(tt.slug, '')) CONTAINS toLower($kw)
                OPTIONAL MATCH (sd:SecondDream)-[:TRACKS_TOPIC]->(tt)
                OPTIONAL MATCH (tt)-[:SUBTOPIC_OF]->(parent:SupplyTopic)
                OPTIONAL MATCH (src:SourceRef)-[:RAW_ADDRESS]->(bt:SupplyBridgeThought)-[:SUPPORTS]->(tt)
                RETURN DISTINCT tt.slug AS slug, tt.title AS title, tt.status AS status,
                       collect(DISTINCT parent.slug)[0..2] AS parent_slugs,
                       count(DISTINCT bt) AS bridge_count,
                       collect(DISTINCT sd.headline)[0..2] AS audit_heads
                ORDER BY bridge_count DESC, tt.slug ASC LIMIT 15
                """
                result = session.run(cypher, kw=kw)

            rows = [record for record in result]
            if not rows: return "❌ SupplyTopic(공급 감사 주제)가 없거나 검색어와 일치하는 항목이 없습네다."

            hdr = "📑 [공급 감사 주제 SupplyTopic — 요구·공급 갭 목록]\n"
            hdr += f"🔎 검색어: '{kw}'\n\n" if kw else "🔎 (키워드 없음 → 최근 감사 연결 순)\n\n"

            lines = []
            for row in rows:
                slug = row.get("slug") or "(slug 없음)"
                title = row.get("title") or ""
                st = row.get("status") or "?"
                if kw:
                    ps = row.get("parent_slugs") or []
                    parents = ", ".join([p for p in ps if p]) if ps else "—"
                    bc = row.get("bridge_count", 0)
                    ah = " / ".join([h for h in (row.get("audit_heads") or []) if h][:2]) or "—"
                    lines.append(f"▸ slug: {slug}\n  제목: {title}\n  상태: {st} | 브릿지 수: {bc} | 관련 꿈: {ah}\n")
                else:
                    la = row.get("last_audit") or "—"
                    lines.append(f"▸ slug: {slug}\n  제목: {title}\n  상태: {st} | 마지막 감사: {la}\n")

            return hdr + "\n".join(lines)
    except Exception as e: return f"💥 SupplyTopic 검색 실패: {e}"

def recent_tactical_briefing(limit=8):
    """심야 9차가 각인한 TacticalThought"""
    try: lim = max(1, min(int(limit), 24))
    except: lim = 8
    try:
        with get_db_session() as session:
            cypher = """
            MATCH (t:TacticalThought)
            RETURN t.situation_trigger AS trig, t.actionable_rule AS rule,
                   t.priority_weight AS w, t.batch_id AS batch
            ORDER BY t.created_at DESC LIMIT $lim
            """
            result = session.run(cypher, lim=lim)
            rows = [record for record in result]
            if not rows: return "(아직 등록된 TacticalThought 전술 지침이 없습니다.)"
            lines = ["🎖️ [심야 전술 지침 TacticalThought — 최근 우선]\n"]
            for i, row in enumerate(rows, 1):
                trig, rule, w = (row.get("trig") or "").strip(), (row.get("rule") or "").strip(), row.get("w")
                lines.append(f"{i}. (가중치 {w})\n   ▶ 조건: {trig}\n   ▶ 지침: {rule}\n")
            return "\n".join(lines)
    except Exception as e: return f"💥 TacticalThought 열람 실패: {e}"

def recall_recent_dreams(limit=5):
    """최근 송련이의 꿈(사고 과정) 회상"""
    try: limit = int(limit)
    except: limit = 5
    try:
        with get_db_session() as session:
            cypher = "MATCH (d:Dream) RETURN d.date AS date, d.user_input AS input, d.final_answer AS answer ORDER BY d.date DESC LIMIT $limit"
            result = session.run(cypher, limit=limit)
            rows = [record for record in result]
            if not rows: return "❌ 최근 사고 기록(꿈)이 없습네다."
            res = "🧠 [직전 턴 송련의 내부 사고 흐름 (꿈)]\n"
            for row in rows: res += f"[{row['date']}] 👤 질문: {row['input']}\n   🤖 최종대답: {row['answer']}\n\n"
            return res
    except Exception as e: return f"💥 꿈 회상 실패: {e}"

def check_db_status(keyword=""):
    """현재 Neo4j 신경망 벙커의 노드 지형도 스캔 (V3.5 라벨 적용)"""
    try:
        with get_db_session() as session:
            counts = {}
            for label in [
                'Person', 'CoreEgo', 'Episode', 'PastRecord', 'Diary', 'GeminiChat', 'SongryeonChat', 
                'Dream', 'SecondDream', 'SupplyTopic', 'SupplyBridgeThought', 'SourceRef', 
                'TacticalThought', 'TacticCard', 'Emotion'
            ]:
                res = session.run(f"MATCH (n:{label}) RETURN count(n) AS c")
                counts[label] = res.single()['c']
                
            report = "📊 [Neo4j V3.5 신경망 지형도 및 현재 상태]\n"
            report += f" 👤 정체성 축 : Person({counts['Person']}), CoreEgo({counts['CoreEgo']})\n"
            report += f" 📚 에피소드(요약) : Episode({counts['Episode']})\n"
            report += f" 📂 과거 원본 통합(PastRecord) : {counts['PastRecord']}개 노드\n"
            report += f"   - 📝 Diary: {counts['Diary']} / 🤖 Gemini: {counts['GeminiChat']} / 💬 Songryeon: {counts['SongryeonChat']}\n"
            report += f" 🧠 인지 로그 : Dream({counts['Dream']}) / SecondDream({counts['SecondDream']})\n"
            report += f" 📑 심야 성찰 : SupplyTopic({counts['SupplyTopic']}) / SupplyBridge({counts['SupplyBridgeThought']})\n"
            report += f" 🎖️ 행동 전술 : TacticalThought({counts['TacticalThought']}) / TacticCard({counts['TacticCard']})\n"
            report += f" ❤️ 감정 축 : Emotion({counts['Emotion']})\n"
            return report
    except Exception as e: return f"💥 DB 스캔 실패: {e}"

def web_search(query):
    print(f"🌐 [System] 인터넷 무료 수색 개시: '{query}'")
    try:
        results = DDGS().text(query, max_results=3) 
        if not results: return f"❌ '{query}'에 대한 인터넷 검색 결과가 없습네다."
        res_text = f"🌐 [인터넷 수색: {query}]\n"
        for r in results: res_text += f"- {r['title']}: {r['body']}\n"
        return res_text
    except Exception as e: return f"❌ 인터넷 수색 실패: {e}"

def search_by_year(year_str):
    try:
        with get_db_session() as session:
            cypher = "MATCH (e:Episode) WHERE e.date STARTS WITH $year RETURN e.date AS date, e.keywords AS keywords, e.summary AS summary ORDER BY rand() LIMIT 7"
            result = session.run(cypher, year=str(year_str))
            rows = [record for record in result]
            if not rows: return f"❌ {year_str}년도에는 기록된 회고록(요약본)이 없습네다."
            res_str = f"📋 [{year_str}년도 요약 목록]\n"
            for row in rows: res_str += f"- [주소: {row['date']}] 🔑키워드: {row['keywords']} | 📝요약: {row['summary']}\n"
            return "🚨 [시스템 경고] 아래는 '허정후'의 과거 기록입니다!\n" + res_str
    except Exception as e: return f"💥 연도별 발굴 실패: {e}"

def get_daily_report(date_str):
    try:
        with get_db_session() as session:
            cypher = "MATCH (e:Episode) WHERE e.date = $date_str OPTIONAL MATCH (e)-[:FEELING]->(emo:Emotion) RETURN e.summary AS summary, e.keywords AS keywords, emo.name AS emotion, e.importance_score AS score"
            result = session.run(cypher, date_str=date_str)
            record = result.single()
            if not record: return f"❌ {date_str}에는 기록된 '회고록(Episode)'이 없습네다."
            return f"📜 [역사 기록: {date_str}]\n⭐ 중요도: {record['score']}/5\n🔑 키워드: {record['keywords']}\n❤️ 당시 감정: {record['emotion']}\n[3줄 요약]\n{record['summary']}"
    except Exception as e: return f"💥 역사 조회 실패: {e}"

def update_instinct_file(filename, rule_index, new_voice):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(os.path.dirname(current_dir), "SEED", "Instincts", filename)
    if not os.path.exists(target_path): return f"❌ 파일이 없습니다: {filename}"
    try:
        with open(target_path, 'r', encoding='utf-8') as f: data = json.load(f)
        if 0 <= rule_index < len(data.get("rules", [])):
            old_voice = data["rules"][rule_index].get("voice", "(없음)")
            data["rules"][rule_index]["voice"] = new_voice 
            with open(target_path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
            return f"✅ {filename} 수정 완료! ({old_voice}) -> ({new_voice})"
        return "❌ 인덱스 오류"
    except Exception as e: return f"💥 파일 수정 실패: {e}"

def update_core_prompt(target_prompt, new_full_text):
    import os
    clean_target = str(target_prompt).replace("차", "").replace("phase_", "").replace("Phase_", "").strip()
    file_map = {"0": "0_meta_prompt.txt", "2": "2_analyzer_prompt.txt", "3": "3_validator_prompt.txt"}
    if clean_target not in file_map: return f"❌ 대상 오류: {target_prompt}"
    if not new_full_text or str(new_full_text).upper() == "NONE": return "❌ 수술 내용이 비어있습네다."
    target_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SEED", "prompts", file_map[clean_target])
    try:
        with open(target_path, 'w', encoding='utf-8') as f: f.write(str(new_full_text).strip())
        return f"✅ {file_map[clean_target]} 진화 완료!"
    except Exception as e: return f"💥 프롬프트 수정 실패: {e}"

def read_prompt_file(target_phase):
    import os
    clean_target = str(target_phase).replace("차", "").replace("phase_", "").replace("Phase_", "").strip()
    file_map = {"0": "0_meta_prompt.txt", "2": "2_analyzer_prompt.txt", "3": "3_validator_prompt.txt"}
    if clean_target not in file_map: return f"❌ [열람 실패] 대상 오류: {target_phase}."
    target_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SEED", "prompts", file_map[clean_target])
    try:
        with open(target_path, "r", encoding="utf-8") as f: return f"🧠 [{file_map[clean_target]} 현재 뇌 구조]\n{f.read()}"
    except Exception as e: return f"💥 프롬프트 열람 실패: {e}"
def scan_db_schema():
    """Neo4j DB의 라벨, 관계, 속성을 실시간으로 스캔합니다."""
    query_labels = "CALL db.labels() YIELD label RETURN collect(label) AS labels"
    query_rels = "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS rels"
    query_props = "CALL db.propertyKeys() YIELD propertyKey RETURN collect(propertyKey) AS props"
    
    try:
        with get_db_session() as session:
            labels = session.run(query_labels).single()["labels"]
            rels = session.run(query_rels).single()["rels"]
            props = session.run(query_props).single()["props"]
            
            # 속성이 너무 많으면 토큰이 터지므로 앞의 일부만 자르거나 핵심만 보여줍니다.
            safe_props = props[:30] if props else []
            
            result = (
                f"📌 [실시간 DB 구조 스캔 결과]\n"
                f"1. 존재하는 노드 라벨(Label): {labels}\n"
                f"2. 존재하는 관계 타입(Relationship): {rels}\n"
                f"3. 활용 가능한 속성 키(Property): {safe_props}..."
            )
            return result, [] # (결과 텍스트, 빈 날짜 배열)
    except Exception as e:
        return f"🚨 DB 스캔 실패: {e}", []
    
def scroll_chat_log(target_id: str, direction: str = "both", limit: int = 15):
    """대화록 스크롤 후 (XML텍스트, ID배열) 2개를 반환합네다!"""
    safe_limit = min(int(limit), 30) 
    
    # 💡 [V9.5 수술 1]: 날짜 돌연변이(Shape-shifter) 패치! (일기장과 동일한 방어막)
    import re
    alt_id = target_id
    match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", target_id)
    if match:
        y, m, d = match.groups()
        alt_id = f"{y} {int(m)} {int(d)}"
        
    t_id = target_id.strip()
    a_id = alt_id.strip()
    
    # 💡 [V9.5 수술 2]: Cypher 문법 오류 해결! (관계 길이는 파이썬 f-string으로 직접 주입!!!)
    query = f"""
    MATCH (target)
    WHERE trim(coalesce(target.id, '')) = $t_id OR trim(coalesce(target.id, '')) = $a_id
       OR trim(coalesce(target.date, '')) = $t_id OR trim(coalesce(target.date, '')) = $a_id
       OR trim(coalesce(target.node_id, '')) = $t_id OR trim(coalesce(target.node_id, '')) = $a_id
    CALL {{
        WITH target
        MATCH (prev)-[:NEXT*1..{safe_limit}]->(target) // 👈 $limit 대신 파이썬 변수 직접 삽입!
        WHERE $direction IN ['past', 'both']
        RETURN prev AS node, "context_before" AS tag
        UNION
        WITH target
        RETURN target AS node, "target_hit" AS tag
        UNION
        WITH target
        MATCH (target)-[:NEXT*1..{safe_limit}]->(next) // 👈 여기도 직접 삽입!
        WHERE $direction IN ['future', 'both']
        RETURN next AS node, "context_after" AS tag
    }}
    RETURN coalesce(node.id, node.date, node.node_id) AS id, 
           coalesce(node.speaker, node.role, '알 수 없음') AS speaker, 
           node.content AS content, tag
    ORDER BY coalesce(node.timestamp, node.date, node.id, "") ASC
    """
    
    try:
        with get_db_session() as session:
            # 쿼리에 t_id와 a_id 파라미터를 넘겨줍니다.
            records = session.run(query, t_id=t_id, a_id=a_id, direction=direction)
            
            xml_result = f"🎯 [스나이퍼 스크롤 보고서] 기준 노드: {target_id} | 탐색 방향: {direction}\n\n"
            current_tag = ""
            exact_dates = [] 
            
            for r in records:
                if r['tag'] != current_tag:
                    if current_tag != "": xml_result += f"</{current_tag}>\n\n"
                    xml_result += f"<{r['tag']}>\n"
                    current_tag = r['tag']
                
                xml_result += f"[ID: {r['id']}] {r['speaker']}: {r['content']}\n"
                
                # 💡 None(null)이 아닌 진짜 ID만 중복 없이 탯줄에 연결!
                if r['id'] and r['id'] not in exact_dates:
                    exact_dates.append(r['id']) 
            
            if current_tag != "": xml_result += f"</{current_tag}>\n"
            
            # 검색된 게 아무것도 없다면 빈 배열과 실패 메시지 반환!
            if not exact_dates:
                return f"🚨 스크롤 실패: 해당 날짜/ID({target_id})를 DB에서 찾을 수 없습네다.", []
                
            return xml_result, exact_dates 
            
    except Exception as e:
        return f"🚨 스크롤 실패 DB 에러. (사유: {e})", []
def scan_trend_u_function(keyword_z, keyword_anti_z="", keyword_y="", track_type="PastRecord"):
    """[V7.1 3차원 위상 스캐너 실구현체]"""
    # 💡 실제 연산은 Core/u_function_engine.py 에 위임하거나 여기서 직접 계산 로직을 돌립니다.
    # 일단은 엔진을 호출하는 배관만 연결합니다!
    try:
        from Core.u_function_engine import UFunctionEngine
        engine = UFunctionEngine()
        if keyword_anti_z and keyword_y:
            # 3차원 스캔 모드 (심야)
            return engine.scan_3d_intersection(keyword_z, keyword_anti_z, keyword_y)
        else:
            # 1차원 스캔 모드 (주간)
            return engine.generate_text_trend_chart(keyword_z, track_type)
    except Exception as e:
        return f"🚨 U-함수 엔진 가동 실패: {e}"
