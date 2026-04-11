import json
import ollama
import os
import sys
import re
from datetime import datetime

# 👇 [신규 추가] Pydantic 강제 구속구 라이브러리 탑재!
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

load_dotenv()

from Core.inference_buffer import InferenceBuffer
from Core.state import AnimaState
from tools.toolbox import (
    search_memory,
    read_full_source,
    web_search,
    search_by_year,
    recall_recent_dreams,
    search_tactics,
    get_emotion_trend,
    search_supply_topics,
)

def _env(name, default=None):
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


NEO4J_URI = _env("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = _env("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = _env("NEO4J_PASSWORD")

PHASE8_TOOLS = frozenset({
    "SEARCH",
    "READ_FULL_SOURCE",
    "web_search",
    "search_by_year",
    "recall_recent_dreams",
    "search_tactics",
    "get_emotion_trend",
    "search_supply_topics",
    "scan_trend_u_function", # 👈 [추가됨!] U-함수 스캐너 장착!
})

TOOLS_REQUIRING_KEYWORD = frozenset({
    "SEARCH",
    "READ_FULL_SOURCE",
    "web_search",
    "search_by_year",
    "search_tactics",
    "get_emotion_trend",
    "search_supply_topics",
})

PROMPTS_DIR = os.path.join(project_root, "SEED", "prompts")

# =====================================================================
# ⛓️ [Pydantic 스키마 구속구 정의] (LLM의 헛소리 원천 차단)
# =====================================================================

# midnight_reflection.py 맨 위쪽

from langgraph.graph import StateGraph, END
from typing import TypedDict, List

# 👇 [신규 추가] 심야 요원들만 공유할 전황판(State)
class MidnightState(TypedDict):
    target_date: str
    dream_ids: List[str]       # 👈 7차와 저장 로직을 위해 추가!
    dreams_log_text: str
    phase_7_audit: dict
    pending_actions: list   # 👈 8a가 짠 도구 실행 계획
    loop_count: int
    tool_runs: List[dict]
    bridges: List[dict]
    doubt_feedback: str
    phase_8b_feedback: str
    tactical_doctrine: dict
    

def _build_reflection_debate_state(state: MidnightState):
    phase_7 = state.get("phase_7_audit", {}) if isinstance(state.get("phase_7_audit"), dict) else {}
    tactical = state.get("tactical_doctrine", {}) if isinstance(state.get("tactical_doctrine"), dict) else {}
    topics = phase_7.get("classified_topics", []) if isinstance(phase_7.get("classified_topics"), list) else []
    pending_actions = state.get("pending_actions", []) if isinstance(state.get("pending_actions"), list) else []
    bridges = state.get("bridges", []) if isinstance(state.get("bridges"), list) else []

    unresolved_topics = []
    objections = []
    approved_topic_ids = []
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        slug = str(topic.get("topic_slug") or "").strip()
        title = str(topic.get("title") or slug).strip()
        if topic.get("supply_sufficient"):
            if slug:
                approved_topic_ids.append(slug)
            continue
        label = title or slug
        if label:
            unresolved_topics.append(label)
        gap = str(topic.get("gap_description") or "").strip()
        if label or gap:
            objections.append({
                "topic_slug": slug,
                "objection_text": gap or f"Supply gap remains around {label}.",
                "needs_search": True,
            })

    recommended_searches = []
    for action in pending_actions:
        if not isinstance(action, dict):
            continue
        tool = str(action.get("tool") or "").strip()
        keyword = str(action.get("keyword") or "").strip()
        topic_slug = str(action.get("topic_slug") or "").strip()
        if tool and keyword:
            recommended_searches.append(f"{tool}::{keyword}")
        elif tool:
            recommended_searches.append(f"{tool}::{topic_slug or 'unspecified'}")

    bridge_claims = []
    for bridge in bridges[:6]:
        if not isinstance(bridge, dict):
            continue
        thought = str(bridge.get("bridge_thought") or "").strip()
        source_address = str(bridge.get("source_address") or "").strip()
        if thought:
            bridge_claims.append({
                "source_address": source_address,
                "bridge_thought": thought,
            })

    tactical_items = tactical.get("tactical_thoughts", []) if isinstance(tactical.get("tactical_thoughts"), list) else []
    final_answer_brief = ""
    if tactical_items:
        final_answer_brief = " / ".join(
            str(item.get("actionable_rule") or "").strip()
            for item in tactical_items[:3]
            if isinstance(item, dict) and str(item.get("actionable_rule") or "").strip()
        )
    if not final_answer_brief:
        final_answer_brief = str(tactical.get("critique_reasoning") or state.get("phase_8b_feedback") or "").strip()

    answer_now = bool(tactical_items) or state.get("doubt_feedback") == "RESOLVED"
    requires_search = bool(recommended_searches) and not answer_now

    return {
        "critic_report": {
            "situational_brief": str(state.get("phase_8b_feedback") or "").strip(),
            "analytical_thought": str(phase_7.get("thought_process") or "").strip(),
            "open_questions": unresolved_topics,
            "objections": objections,
            "recommended_searches": recommended_searches,
            "recommended_action": "answer_now" if answer_now else ("search_more" if requires_search else "insufficient_evidence"),
        },
        "advocate_report": {
            "defense_strategy": str(tactical.get("critique_reasoning") or "").strip(),
            "summary_of_position": final_answer_brief,
            "supported_pair_ids": [
                str(bridge.get("source_address") or "").strip()
                for bridge in bridges[:6]
                if isinstance(bridge, dict) and str(bridge.get("source_address") or "").strip()
            ],
            "bridge_claims": bridge_claims,
        },
        "verdict_board": {
            "answer_now": answer_now,
            "requires_search": requires_search,
            "approved_fact_ids": approved_topic_ids,
            "approved_pair_ids": [
                str(bridge.get("source_address") or "").strip()
                for bridge in bridges[:6]
                if isinstance(bridge, dict) and str(bridge.get("source_address") or "").strip()
            ],
            "rejected_pair_ids": [],
            "held_pair_ids": [],
            "judge_notes": [str(state.get("phase_8b_feedback") or "").strip()] if str(state.get("phase_8b_feedback") or "").strip() else [],
            "final_answer_brief": final_answer_brief,
        },
    }


class ClassifiedTopic(BaseModel):
    topic_slug: str # 👈 이것이 기본 Z축(정)이 됩니다.
    title: str
    parent_topic_slug: Optional[str]
    what_was_demanded: str
    what_was_supplied_in_answer: str
    supply_sufficient: bool
    gap_description: str
    
    # 👇 파이썬이 U-함수에 자동 주입할 2개의 변수 추가!
    dynamic_anti_z: str = Field(
        ..., 
        description="이 주제(Z축)와 완벽하게 대립되는 모순/대척점 키워드 (Anti-Z축)"
    )
    dynamic_y_axis: str = Field(
        ..., 
        description="이 주제의 결핍 원인 등을 입체적으로 분석하기 위해 7차가 임의로 지정하는 제3의 상황 변수 (Y축)"
    )

class Phase7Schema(BaseModel):
    thought_process: str = Field(description="현재까지의 단서와 8b의 보고를 바탕으로 한 7차의 사고 과정")
    classified_topics: List[ClassifiedTopic] = Field(description="도출해낸 정반합(Z, Anti-Z, Y) 주제들")
    
    # 👇 7차가 직접 도구 사용을 지시합니다! (단독 독대 가능!)
    instruction: str = Field(description="실행할 도구 지시 (예: tool_scan_trend_u_function_3d(...) 또는 tool_read_full_diary(...) 또는 패스)")
    message_to_8b: str = Field(description="8b 제련관에게 보내는 분석 지시나 질문")

class Phase8Action(BaseModel):
    topic_slug: str
    tool: Literal["SEARCH", "READ_FULL_SOURCE", "web_search", "search_by_year", "recall_recent_dreams", "search_tactics", "get_emotion_trend", "search_supply_topics", "scan_trend_u_function"]
    keyword: Optional[str] = Field(None, description="일반 검색 도구를 사용할 때의 키워드")
    # 💡 8a는 더 이상 Z, Anti-Z, Y를 고민하지 않습니다! 파이썬이 알아서 합니다!

class Phase8aSchema(BaseModel):
    actions: List[Phase8Action]

class SupplyBridge(BaseModel):
    topic_slug: str
    source_address: str
    # 👇 [핵심 개조] 브릿지 사상은 무조건 '결핍 충족'을 위해 쓰이도록 강제!
    bridge_thought: str = Field(description="[절대 규칙] 이 원문(과거)의 깨달음이 7차가 지적한 '결핍(SupplyTopic/Z축)'을 어떻게 직접적으로 해결하고 충족시켜 줄 수 있는지에 대한 핵심 통찰")
    parent_topic_slug: Optional[str]

class RefinedMidnightNode(BaseModel):
    id: str = Field(description="추출된 과거 기록의 주소/ID")
    summary: str = Field(description="8b가 원문을 씹어먹고 7차를 위해 작성한 핵심 요약 (원문은 생략)")

class Phase8bSchema(BaseModel):
    thought_process: str = Field(description="원문을 읽고, 이것이 어떻게 7차의 '결핍'을 채울 수 있을지 고민하는 8b의 단계적 추론 과정 (사고 칠판)")
    processed_data: List[RefinedMidnightNode]
    
    is_resolved: bool = Field(description="[매우 중요] 제공된 원문 데이터만으로 7차의 결핍을 완벽하고 논리적으로 해결할 수 있는가? (부족하거나 맥락을 모르면 무조건 False!)")
    response_to_phase_7: str = Field(description="is_resolved가 False일 경우: 7차에게 '어떤 날짜의 일기장 전체 원문'을 가져오라고 구체적으로 다시 지시하십시오. (True일 경우 결핍 해결책 보고)")
    
    proactive_suggestion: str = Field(description="8b가 7차에게 먼저 제안하는 철학적 가설")
    bridges: List[SupplyBridge]

class TacticalThoughtItem(BaseModel):
    situation_trigger: str
    actionable_rule: str
    priority_weight: float
    applies_to_phase: str

class Phase9Schema(BaseModel):
    critique_reasoning: str
    is_valuable_tactics: bool
    tactical_thoughts: List[TacticalThoughtItem]

# =====================================================================

class DreamWeaver:
    """
    심야 파이프라인 진입점:
    - execute_midnight_reflection(YYYY-MM-DD)
    - execute_grand_reflection_sweep()
    """
    
    # =====================================================================
    # 📜 [V6.1 야전 일체형 프롬프트 무기고] (텍스트 파일 절대 필요 없음!)
    # =====================================================================

    CONSTITUTION_TEXT = """
    [ANIMA 시스템 절대 헌법]
    당신은 사용자 '허정후'를 보좌하는 ANIMA 시스템의 핵심 자아 '송련'의 심야 성찰관입니다.
    당신의 모든 분석은 사용자의 자아실현'을 돕기 위해 정확하게 이루어져야 합니다.
    사실(Fact)과 모순(Contradiction)을 수학적으로 분석하여 보고하십시오.
    """

    PHASE7_PROMPT = """
    {constitution}

    당신은 ANIMA 시스템의 'Phase 7: 냉혹한 공급 감사관'입니다.

    [사용자의 미감사 꿈(일기/대화) 목록]
    {log_text}

    [이전 루프에서 8b 제련관이 남긴 피드백]
    {previous_feedback}

    [이전 루프의 도구 실행 기록 요약]
    {tool_history}

    🚨 [V6.1 3차원 심리 위상 공간 설계 강령]
    당신은 사용자의 일기를 읽고 단순히 '주제'를 분류하는 데 그쳐서는 안 됩니다. 
    사용자의 내면에서 벌어지는 '정반합(Thesis-Antithesis-Synthesis)'의 모순을 추적하기 위해, 
    반드시 다음 3개의 축을 완벽하게 세팅하여 Pydantic 구조체에 담아야 합니다!

    [루프 교정 원칙]
    직전 루프의 가설이나 피드백이 현재 기록과 충돌하면 미련 없이 폐기하십시오.
    이전에 잡았던 주제라도 오늘의 증거가 약하면 classified_topics에서 제거하거나 수정해야 합니다.
    즉, 당신의 이번 출력은 '이전 생각의 누적본'이 아니라 '현재 시점의 최신 판정본'이어야 합니다.

    1. topic_slug (Z축 - 정): 당신이 방금 찾아낸 '결핍된 주제(SupplyTopic)'의 핵심 키워드 (사용자나 송련 스스로 필요했으나 충족되지 못한 주제) (한글로 적으십시오)
    2. dynamic_anti_z (Anti-Z축 - 반): 위 Z축(SupplyTopic)과 완벽하게 대립하여 사용자를 끌어내리는 모순/그림자 키워드 (한글로 적으십시오)
    3. dynamic_y_axis (Y축 - 상황 변수): 사용자의 Z축이 무너지는 데 결정적인 영향을 미쳤을 것 같은 제3의 외부/내부 상황 변수 (한글로 적으십시오)

    [명령]
    사용자의 오늘 기록을 냉혹하게 분석하십시오. 사용자의 결핍(Supply)을 찾아내어, 위 3개의 축이 포함된 ClassifiedTopic 리스트를 JSON 구조에 맞게 출력하십시오!
    """

    PHASE8A_PROMPT = """
    {constitution}

    당신은 ANIMA 시스템의 'Phase 8a: 심야 수색 작전관'입니다.

    [7차 감사관이 찾아낸 '공급 부족(결핍)' 주제들]
    {insufficient_topics_json}

    [직전 8b 제련관의 재수색 피드백]
    {previous_feedback}

    [이미 시도한 도구 기록]
    {tool_history}

    [사용 가능한 도구 목록]
    {tool_digest}

    🚨 [V6.1 3차원 스캔 방아쇠 강령]
    당신은 7차가 찾아낸 결핍 주제들을 보충하기 위해 어떤 도구를 쏠지 계획해야 합니다.
    특히 사용자의 심리적 모순을 파헤치고 싶을 때는 주저하지 말고 `tool_scan_trend_u_function_3d` 도구를 장전하십시오! 
    (주의: 당신은 도구의 이름과 주제(topic_slug)만 지정하면 됩니다. Z, Anti-Z, Y축 변수는 파이썬 배관이 알아서 엔진에 꽂아 넣습니다!)
    이미 실패했거나 같은 주제에 대해 직전에 반복한 도구 조합을 그대로 되풀이하지 마십시오.
    최신 7차 감사에서 사라진 주제의 낡은 흔적은 무시하고, 지금 남아 있는 결핍만 보십시오.
    검색형 도구를 쓸 때 keyword를 비워두지 마십시오. 빈 문자열, 공백, 의미 없는 placeholder는 금지입니다.

    [명령]
    어떤 주제에 어떤 도구를 사용할지 Phase8aSchema 양식에 맞춰 계획(Actions)을 수립하십시오.
    """

    PHASE8B_PROMPT = """
    {constitution}

    당신은 ANIMA 시스템의 'Phase 8b: 지식 사슬 제련관'입니다.

    [7차의 3D 축 설계도 (결핍된 주제들)]: 
    {p7_json}

    [파이썬이 가져온 과거 원문 데이터]: 
    {tool_runs}

    🚨 [V7.1 결핍 충족 최우선 제련 강령]
    당신의 유일한 존재 이유는 7차가 지적한 **'결핍된 주제(Z축)'를 채워주는 것**입니다!
    과거의 원문에서 엉뚱한 교훈을 얻지 마십시오. 오직 "이 과거의 기록이 사령관의 현재 '결핍'을 어떻게 해결할 수 있는가?"에만 집중하십시오!
    이전 루프에서 떠올랐던 설명보다 지금 근거가 더 강하면, 과거 가설을 그대로 보존하지 말고 더 강한 설명으로 교체하십시오.

    1. 🧠 [사고 칠판 가동]: 원문을 읽고, 7차의 결핍을 어떻게 메꿀지 `thought_process`에 치열하게 고민하십시오.
    2. 🌲 [결핍 해결의 숲(Synthesis) 정의]: 모순을 해결할 상위 개념을 도출하여 `parent_topic_slug`에 할당하십시오. 
    3. 🌿 [강력한 탯줄(Bridge) 연결]: `bridge_thought`에는 반드시 "이 원문이 결핍을 이렇게 해결한다"는 직접적이고 실질적인 통찰을 적으십시오. (뜬구름 잡는 소리 금지!)

    [명령]
    위 강령에 따라 Phase8bSchema 양식에 맞춰 완벽한 제련 결과를 보고하십시오!
    """

    PHASE9_PROMPT = """
    {constitution}

    당신은 ANIMA 시스템의 'Phase 9: 최고 전술 교관'입니다.

    [오늘의 7차(결핍 진단) 및 8b차(해결책 제련) 성찰 결과]
    {p7_json}
    {supply_context}

    🚨 [V7.1 실전 압축 전술(Tactical Thought) 하달 강령]
    지금까지의 랭그래프 성찰을 통해, 사용자의 '결핍(SupplyTopic)'이 무엇인지, 그리고 과거의 기록(Bridge Thought)이 그 결핍을 어떻게 채워줄 수 있는지 완벽하게 증명되었습니다.
    
    당신의 임무는 이 장황한 철학적 결과를, 내일 아침 **0차 행동 대원(주간 체제)이 즉각 써먹을 수 있는 '실전 무기'로 바꾸는 것입니다.

    1. 상황(Situation): 사용자가 '결핍(Z축)'을 느끼거나 '모순(Anti-Z)'에 빠지려는 징후를 포착했을 때.
    2. 행동(Action): 8b가 제련한 '과거의 해결책(Bridge Thought)'을 근거로, 0차가 즉각 지시해야 할 행동.

    [명령]
    "IF [상황] THEN [행동]" 형태의 구체적이고 실질적인 행동 강령(TacticalThoughtItem)을 도출하십시오! (도덕책 같은 뻔한 조언은 전술이 아니라 쓰레기입니다.)
    """

    def __init__(self):
        self.name = "송련_심야_성찰관"
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.model = "gemma3:12b"
        self.action_model = "llama3.1:8b"
        self.buffer = InferenceBuffer()
        self.state = AnimaState()
        # 💡 객체가 생성될 때 랭그래프 배관을 조립해서 self.app에 저장해 둡니다!
        self.app = self.build_graph()

    @staticmethod
    def _describe_backend_error(exc):
        if isinstance(exc, AuthError):
            return "Neo4j 인증에 실패했습니다. .env의 NEO4J_USER/NEO4J_PASSWORD 값을 확인하십시오."
        if isinstance(exc, ServiceUnavailable):
            return f"Neo4j 연결에 실패했습니다. {NEO4J_URI} 가 열려 있는지 확인하십시오."
        return f"Neo4j 점검 중 예외가 발생했습니다: {exc}"

    def _ensure_neo4j_ready(self):
        try:
            self.neo4j_driver.verify_connectivity()
            return True, ""
        except Exception as exc:
            return False, self._describe_backend_error(exc)

    @staticmethod
    def _read_prompt_file(filename):
        path = os.path.join(PROMPTS_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _inject(template, **kwargs):
        out = template
        for k, v in kwargs.items():
            out = out.replace("{" + k + "}", str(v))
        return out

    @staticmethod
    def _safe_json_load(raw_content):
        if not raw_content:
            return None
        try:
            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return json.loads(raw_content)
        except Exception as e:
            print(f"\n💥 JSON 파싱 에러: {e}\n🤬 원본:\n{raw_content}\n")
            return None

    @staticmethod
    def _trim_text(value, limit=800):
        text = str(value or "").strip()
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        if len(text) <= limit:
            return text
        return text[:limit] + "...(truncated)"

    @staticmethod
    def _active_topic_slugs(audit, insufficient_only=False):
        topics = (audit or {}).get("classified_topics", [])
        slugs = []
        for topic in topics:
            if insufficient_only and topic.get("supply_sufficient"):
                continue
            slug = (topic.get("topic_slug") or "").strip()
            if slug:
                slugs.append(slug)
        return slugs

    @classmethod
    def _tool_history_text(cls, tool_runs, limit=8, result_char_limit=800):
        if not tool_runs:
            return "(아직 실행된 도구 없음)"
        sliced = tool_runs[-limit:]
        compact = []
        for run in sliced:
            compact.append({
                "topic_slug": (run.get("topic_slug") or "").strip(),
                "tool": (run.get("tool") or "").strip(),
                "keyword": str(run.get("keyword") or "").strip(),
                "result_excerpt": cls._trim_text(run.get("result"), result_char_limit),
            })
        return json.dumps(compact, ensure_ascii=False, indent=2)

    @classmethod
    def _reconcile_tool_runs(cls, tool_runs, audit):
        active_topic_slugs = set(cls._active_topic_slugs(audit))
        reconciled = {}
        for run in tool_runs or []:
            topic_slug = (run.get("topic_slug") or "").strip()
            if topic_slug and active_topic_slugs and topic_slug not in active_topic_slugs:
                continue
            signature = (
                topic_slug,
                (run.get("tool") or "").strip(),
                str(run.get("keyword") or "").strip(),
            )
            reconciled[signature] = {
                "topic_slug": topic_slug,
                "tool": (run.get("tool") or "").strip(),
                "keyword": str(run.get("keyword") or "").strip(),
                "result": run.get("result"),
            }
        return list(reconciled.values())[-16:]

    @classmethod
    def _reconcile_bridges(cls, existing, new_items, audit):
        active_topic_slugs = set(cls._active_topic_slugs(audit))
        reconciled = {}
        for bridge in (existing or []) + (new_items or []):
            topic_slug = (bridge.get("topic_slug") or "").strip()
            source_address = (bridge.get("source_address") or "").strip()
            bridge_thought = (bridge.get("bridge_thought") or "").strip()
            parent_topic_slug = (bridge.get("parent_topic_slug") or "").strip()

            if not topic_slug or not source_address or not bridge_thought:
                continue
            if active_topic_slugs and topic_slug not in active_topic_slugs:
                continue

            signature = (topic_slug, source_address, parent_topic_slug)
            candidate = {
                "topic_slug": topic_slug,
                "source_address": source_address,
                "bridge_thought": bridge_thought,
                "parent_topic_slug": parent_topic_slug or None,
            }
            previous = reconciled.get(signature)
            if previous is None or len(candidate["bridge_thought"]) >= len(previous.get("bridge_thought") or ""):
                reconciled[signature] = candidate
        return list(reconciled.values())

    def build_graph(self):
        print("⚙️ [System] 심야 성찰 랭그래프 엔진 조립 중...")
        workflow = StateGraph(MidnightState)

        workflow.add_node("phase_7", self.node_phase_7_audit)
        workflow.add_node("phase_8a", self.node_phase_8a_plan)
        # 👇 랭그래프 공식 ToolNode 대신 우리의 커스텀 실행기를 꽂습니다!
        workflow.add_node("tools", self.node_execute_tools) 
        workflow.add_node("phase_8b", self.node_phase_8b_eval)
        workflow.add_node("phase_9", self.node_phase_9_tactics)

        # 2. 직선 배관 연결
        workflow.add_edge("phase_7", "phase_8a")
        workflow.add_edge("tools", "phase_8b")

        def router_8a_to_next(state: MidnightState):
            actions = state.get("pending_actions", [])
            insufficient = [
                topic for topic in state.get("phase_7_audit", {}).get("classified_topics", [])
                if not topic.get("supply_sufficient")
            ]

            if actions:
                return "tools"
            if not insufficient:
                return "phase_9"
            if state.get("loop_count", 0) >= 3:
                return "phase_9"
            return "phase_7"

        workflow.add_conditional_edges(
            "phase_8a",
            router_8a_to_next,
            {"tools": "tools", "phase_7": "phase_7", "phase_9": "phase_9"}
        )

        # 3. 💡 조건부 라우터 (루프 통제)
        def router_8b_to_next(state: MidnightState):
            if state.get("loop_count", 0) >= 3:
                return "phase_9" 
            if state.get("doubt_feedback") == "RESOLVED":
                return "phase_9" 
            return "phase_7"    

        workflow.add_conditional_edges(
            "phase_8b", 
            router_8b_to_next,
            {"phase_9": "phase_9", "phase_7": "phase_7"}
        )

        workflow.add_edge("phase_9", END)
        workflow.set_entry_point("phase_7")

        return workflow.compile()
    
    def fetch_unaudited_dreams(self, target_date):
        try:
            with self.neo4j_driver.session() as session:
                cypher = """
                MATCH (d:Dream) WHERE d.date STARTS WITH $date_prefix
                  AND NOT (d)<-[:AUDITED_FROM]-(:SecondDream)
                RETURN d.id AS dream_id, d.date AS date, d.user_input AS input,
                       d.final_answer AS answer,
                       d.phase_minus1_intent AS p_minus1,
                       d.phase_0_history AS p0, d.phase_1_actions AS p1,
                       d.phase_2_summaries AS p2, d.phase_3_summary AS p3
                ORDER BY d.date ASC
                """
                result = session.run(cypher, date_prefix=target_date)
                return [record for record in result]
        except Exception as e:
            print(f"💥 꿈 배달 실패: {e}")
            return []

    def dream_rows_to_log_text(self, rows):
        buf = []
        for row in rows:
            trace = {}
            if row.get("p_minus1"):
                trace["phase_minus1_intent"] = row["p_minus1"]
            mapping = (
                ("p0", "phase_0_history"),
                ("p1", "phase_1_actions"),
                ("p2", "phase_2_summaries"),
                ("p3", "phase_3_summary"),
            )
            for pykey, label in mapping:
                val = row.get(pykey)
                if val:
                    trace[label] = val
            trace_block = json.dumps(trace, ensure_ascii=False, indent=2) if trace else "(트레이스 배열 없음)"
            buf.append(
                f"📍 [주소(ID): {row['dream_id']} | 시간: {row['date']}]\n"
                f"- 질문: {row['input']}\n- 대답: {row['answer']}\n"
                f"- 사고_트레이스(JSON, phase_*):\n{trace_block}\n"
            )
        return "\n".join(buf)

    def node_phase_7_audit(self, state: MidnightState):
        p7 = self.phase_7_supply_audit(
            state["dreams_log_text"],
            previous_feedback=state.get("phase_8b_feedback", ""),
            tool_history=self._tool_history_text(state.get("tool_runs", []), result_char_limit=500),
        )
        return {
            "phase_7_audit": p7,
            "tool_runs": self._reconcile_tool_runs(state.get("tool_runs", []), p7),
            "bridges": self._reconcile_bridges(state.get("bridges", []), [], p7),
        }

    def node_phase_8a_plan(self, state: MidnightState):
        tool_digest = "사용 가능한 도구: " + ", ".join(PHASE8_TOOLS)
        plan = self.phase_8_plan_tools(
            state["phase_7_audit"],
            tool_digest,
            previous_feedback=state.get("phase_8b_feedback", ""),
            tool_history=self._tool_history_text(state.get("tool_runs", []), result_char_limit=450),
            prior_tool_runs=state.get("tool_runs", []),
        )
        return {
            "pending_actions": plan.get("actions", []),
            "loop_count": state.get("loop_count", 0) + 1
        }

    def node_execute_tools(self, state: MidnightState):
        prev_runs = list(state.get("tool_runs", []))
        runs = []
        for a in state.get("pending_actions", []):
            res = self._run_phase8_tool(a["tool"], a.get("keyword"), a.get("topic_slug"), state["phase_7_audit"])
            runs.append({
                "topic_slug": a.get("topic_slug"),
                "tool": a["tool"],
                "keyword": a.get("keyword"),
                "result": res
            })
        return {"tool_runs": self._reconcile_tool_runs(prev_runs + runs, state.get("phase_7_audit", {}))}

    def node_phase_8b_eval(self, state: MidnightState):
        runs_text = self._tool_history_text(state.get("tool_runs", []), limit=12, result_char_limit=1800)
        p8b = self.phase_8_synthesize_bridges(state["phase_7_audit"], runs_text)
        is_resolved = p8b.get("is_resolved", False)
        merged_bridges = self._reconcile_bridges(
            state.get("bridges", []),
            p8b.get("bridges", []),
            state.get("phase_7_audit", {}),
        )
        feedback = (
            str(p8b.get("response_to_phase_7") or "").strip()
            or str(p8b.get("proactive_suggestion") or "").strip()
        )
        return {
            "bridges": merged_bridges,
            "doubt_feedback": "RESOLVED" if is_resolved else "DOUBT",
            "phase_8b_feedback": feedback,
        }

    def node_phase_9_tactics(self, state: MidnightState):
        import copy
        
        # 1. 7차 서류철 복사본 만들기 (원본 State는 건드리지 않음)
        clean_p7 = copy.deepcopy(state.get("phase_7_audit", {}))
        
        # 🚨 [핵심 세탁 작전]: 7차의 사고 칠판(thought_process) 싹 지워버리기!
        if "thought_process" in clean_p7:
            del clean_p7["thought_process"]
            
        # 2. 8b의 제련 결과 중 핵심만 챙기기 (8b의 사고 칠판이나 잡다한 대화는 안 넘김!)
        clean_bridges = state.get("bridges", [])
        # (만약 tool_runs의 엄청난 원문 데이터도 9차에게 굳이 필요 없다면 아래처럼 비워버리면 됩니다)
        clean_tool_runs = "원문 데이터 생략. 8b의 브릿지(bridges)를 기반으로 전술을 짜십시오."

        # 3. 세탁된 깔끔한 서류만 9차 프롬프트에 주입!
        p9 = self.phase_9_tactical_doctrine(clean_p7, clean_tool_runs, clean_bridges)
        
        return {"tactical_doctrine": p9}
    
    # =====================================================================
    # 2. 잃어버린 도구 실행기 복구 (이거 없으면 에러 납니다!)
    # =====================================================================

    def _run_phase8_tool(self, tool, keyword, topic_slug=None, p7_audit=None):
        kw = (keyword or "").strip()
        if tool in TOOLS_REQUIRING_KEYWORD and not kw:
            return f"❌ {tool} 도구는 비어 있지 않은 keyword가 필요하다."
        if tool == "SEARCH": return search_memory(kw)
        if tool == "READ_FULL_SOURCE":
            if "|" not in kw: return "❌ READ_FULL_SOURCE 키워드는 '일기장|YYYY-MM-DD' 또는 '송련|YYYY-MM-DD' 형식이어야 한다."
            src, dt = kw.split("|", 1)
            return read_full_source(src.strip(), dt.strip())
        if tool == "web_search": return web_search(kw)
        if tool == "search_by_year": return search_by_year(kw)
        if tool == "recall_recent_dreams":
            lim = int(kw) if kw.isdigit() else 5
            return recall_recent_dreams(lim)
        if tool == "search_tactics": return search_tactics(kw)
        if tool == "get_emotion_trend": return get_emotion_trend(kw)
        if tool == "search_supply_topics": return search_supply_topics(kw)
        
        # 🎯 V6.1 U-함수 3차원 스캐너 라우팅
        if tool == "scan_trend_u_function":
            from Core.u_function_engine import UFunctionEngine
            if not p7_audit or not topic_slug:
                return "❌ 시스템 에러: 7차 감사 기록 또는 주제가 전달되지 않았습니다."

            target_topic = next((t for t in p7_audit.get("classified_topics", []) if t["topic_slug"] == topic_slug), None)
            if not target_topic:
                return f"❌ 시스템 에러: '{topic_slug}'에 대한 7차의 3차원 축 데이터를 찾을 수 없습니다."
            
            z = target_topic.get("title", topic_slug) 
            anti_z = target_topic.get("dynamic_anti_z", "우울/허무")
            y = target_topic.get("dynamic_y_axis", "스트레스")
            
            engine = UFunctionEngine()
            return engine.scan_3d_intersection(keyword_z=z, keyword_anti_z=anti_z, keyword_y=y)
            
        return f"❌ 허용되지 않은 도구: {tool}"

    # =====================================================================
    # 3. 실제 LLM 프롬프트 발사 함수들 (찌꺼기 파라미터 삭제!)
    # =====================================================================

    def phase_7_supply_audit(self, log_text, previous_feedback="", tool_history=""): # 👈 루프 피드백 반영
        print("🕵️‍♂️ [Phase 7] 공급 감사관: 요구 주제 분류·충족 여부 판정...")
        prompt = self._inject(
            self.PHASE7_PROMPT,
            constitution=self.CONSTITUTION_TEXT,
            log_text=log_text,
            previous_feedback=previous_feedback or "(이전 피드백 없음)",
            tool_history=tool_history or "(이전 도구 기록 없음)",
        )
        res = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}], format=Phase7Schema.model_json_schema())
        return self._safe_json_load(res["message"]["content"]) or {}

    def phase_8_plan_tools(self, p7, tool_digest, previous_feedback="", tool_history="", prior_tool_runs=None): # 👈 루프 피드백 반영
        print("📋 [Phase 8a] 보충 탐색 계획(도구 호출) 수립...")
        p7 = p7 or {}
        insufficient = [t for t in p7.get("classified_topics", []) if not t.get("supply_sufficient")]
        if not insufficient: return {"actions": []}

        prior_tool_runs = prior_tool_runs or []
             
        prompt = self._inject(
            self.PHASE8A_PROMPT,
            constitution=self.CONSTITUTION_TEXT,
            tool_digest=tool_digest[:12000],
            insufficient_topics_json=json.dumps(insufficient, ensure_ascii=False, indent=2),
            previous_feedback=previous_feedback or "(직전 피드백 없음)",
            tool_history=tool_history or "(직전 도구 기록 없음)",
        )
        res = ollama.chat(model=self.action_model, messages=[{"role": "user", "content": prompt}], format=Phase8aSchema.model_json_schema())
        data = self._safe_json_load(res["message"]["content"]) or {}
        
        actions = data.get("actions") or []
        clean = []
        tried_signatures = {
            (
                (run.get("topic_slug") or "").strip(),
                (run.get("tool") or "").strip(),
                str(run.get("keyword") or "").strip(),
            )
            for run in prior_tool_runs
        }
        for a in actions:
            tool = (a.get("tool") or "").strip()
            if tool not in PHASE8_TOOLS: continue
            action = {
                "topic_slug": (a.get("topic_slug") or "").strip(),
                "tool": tool,
                "keyword": str(a.get("keyword") or ""),
            }
            if tool in TOOLS_REQUIRING_KEYWORD and not action["keyword"].strip():
                continue
            if tool == "READ_FULL_SOURCE" and "|" not in action["keyword"]:
                continue
            signature = (
                action["topic_slug"],
                action["tool"],
                action["keyword"].strip(),
            )
            if signature in tried_signatures:
                continue
            clean.append(action)
        return {"actions": clean}

    def phase_8_synthesize_bridges(self, p7, tool_runs_text):
        print("🔗 [Phase 8b] 원문주소–생각–주제 사슬(그래프용) 합성...")
        p7 = p7 or {}
        p7_part = json.dumps(p7, ensure_ascii=False, indent=2)[:12000]
        prompt = self._inject(self.PHASE8B_PROMPT, constitution=self.CONSTITUTION_TEXT, p7_json=p7_part, tool_runs=tool_runs_text[:14000])
        res = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}], format=Phase8bSchema.model_json_schema())
        return self._safe_json_load(res["message"]["content"]) or {}

    def phase_9_tactical_doctrine(self, p7, tool_runs, bridges): # 👈 파라미터 깔끔!
        print("🎖️ [Phase 9] 전술 교관: TacticalThought(0차 행동 지침) 도출...")
        supply_ctx = {"phase_8_tool_runs": tool_runs, "phase_8_bridges": bridges}
        supply_str = json.dumps(supply_ctx, ensure_ascii=False, indent=2)[:16000]
        prompt = self._inject(self.PHASE9_PROMPT, constitution=self.CONSTITUTION_TEXT, p7_json=json.dumps(p7, ensure_ascii=False, indent=2)[:12000], supply_context=supply_str)
        res = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}], format=Phase9Schema.model_json_schema())
        return self._safe_json_load(res["message"]["content"])

    def _merge_topic_hierarchy(self, session, sd_id, topics):
        graph_ops = []
        for t in topics:
            if t.get("supply_sufficient"): continue
            slug = (t.get("topic_slug") or "").strip()
            title = (t.get("title") or slug).strip()
            
            anti_z = (t.get("dynamic_anti_z") or "미상").strip()
            y_axis = (t.get("dynamic_y_axis") or "미상").strip()
            
            parent_slug = t.get("parent_topic_slug")
            if isinstance(parent_slug, str):
                parent_slug = parent_slug.strip() or None
            else:
                parent_slug = None
                
            # 👇 [긴급 수술 완료]: SecondDream 노드를 먼저 MATCH 하고, 주제 생성과 동시에 탯줄을 무조건 용접합니다!
            session.run(
                """
                MATCH (sd:SecondDream {id: $sd_id})
                MERGE (tt:SupplyTopic {slug: $slug})
                SET tt.title = coalesce(tt.title, $title),
                    tt.status = coalesce(tt.status, 'unfulfilled'),
                    tt.anti_z = coalesce(tt.anti_z, $anti_z),
                    tt.y_axis = coalesce(tt.y_axis, $y_axis),
                    tt.batch_id = $sd_id
                MERGE (sd)-[:TRACKS_TOPIC]->(tt) // 👈 고아 방지용 절대 탯줄!!!
                """,
                slug=slug, title=title, anti_z=anti_z, y_axis=y_axis, sd_id=sd_id,
            )
            graph_ops.append({"op": "MERGE_SUPPL_TOPIC", "slug": slug, "parent": parent_slug})
            
            if parent_slug:
                session.run(
                    """
                    MATCH (sd:SecondDream {id: $sd_id})
                    MERGE (pt:SupplyTopic {slug: $ps})
                    SET pt.batch_id = $sd_id
                    MERGE (ch:SupplyTopic {slug: $cs})
                    MERGE (ch)-[:SUBTOPIC_OF]->(pt)
                    MERGE (sd)-[:TRACKS_TOPIC]->(pt) // 👈 부모 주제(숲)도 미아가 되지 않게 2차 꿈에 묶어버립니다!
                    """,
                    ps=parent_slug, cs=slug, sd_id=sd_id,
                )
                graph_ops.append({"op": "SUBTOPIC_OF", "child": slug, "parent": parent_slug})
        return graph_ops

    def _persist_address_thought_topic(self, session, sd_id, bridge, topics_by_slug, seq):
        slug = (bridge.get("topic_slug") or "").strip()
        title = topics_by_slug.get(slug) or slug
        addr = (bridge.get("source_address") or "unknown|na").strip()
        thought = (bridge.get("bridge_thought") or "").strip()
        parent_slug = bridge.get("parent_topic_slug")
        if isinstance(parent_slug, str):
            parent_slug = parent_slug.strip() or None
        else:
            parent_slug = None
        bt_id = f"{sd_id}_bt_{seq}_{slug}"[:512]

        session.run(
            """
            MERGE (bt:SupplyBridgeThought {id: $bt_id})
            SET bt.content = $thought,
                bt.batch_id = $sd_id,
                bt.created_at = timestamp(),
                bt.raw_address = $addr
            MERGE (tt:SupplyTopic {slug: $slug})
            SET tt.title = coalesce(tt.title, $title),
                tt.status = coalesce(tt.status, 'unfulfilled'),
                tt.batch_id = $sd_id
            MERGE (bt)-[:SUPPORTS]->(tt)
            """,
            bt_id=bt_id, thought=thought, sd_id=sd_id, slug=slug, title=title, addr=addr
        )

        ops = [{"op": "CHAIN", "source": addr, "thought_id": bt_id, "topic": slug}]

        if "|" in addr and not addr.startswith("web:"):
            try:
                src_type, target_date = addr.split("|", 1)
                src_type = src_type.strip()
                target_date = target_date.strip()

                label_map = {"일기장": "Diary", "제미나이": "GeminiChat", "송련": "SongryeonChat"}
                target_label = label_map.get(src_type, "PastRecord") 

                cypher_link = f"""
                MATCH (bt:SupplyBridgeThought {{id: $bt_id}})
                MATCH (r:PastRecord:{target_label}) WHERE r.date STARTS WITH $target_date
                MERGE (r)-[:PROVIDES_KNOWLEDGE]->(bt)
                """
                result = session.run(cypher_link, bt_id=bt_id, target_date=target_date)
                summary = result.consume().counters
                
                if summary.relationships_created > 0:
                    ops.append({"op": "NEURAL_DIRECT_LINK", "target": f"{target_label}|{target_date}"})
                    print(f"    🔗 [신경망 직결 성공] {src_type}({target_date}) ➡️ 깨달음 사슬 연결 완료!")
                else:
                    session.run(
                        """
                        MATCH (bt:SupplyBridgeThought {id: $bt_id})
                        MERGE (sr:SourceRef {address: $addr})
                        ON CREATE SET sr.created_at = timestamp()
                        MERGE (sr)-[:RAW_ADDRESS]->(bt)
                        """,
                        bt_id=bt_id, addr=addr
                    )
            except Exception as e:
                print(f"    💥 [신경망 직결 에러] 파싱 실패 ({addr}): {e}")
        else:
            session.run(
                """
                MATCH (bt:SupplyBridgeThought {id: $bt_id})
                MERGE (sr:SourceRef {address: $addr})
                ON CREATE SET sr.created_at = timestamp()
                SET sr.batch_id = $sd_id
                MERGE (sr)-[:RAW_ADDRESS]->(bt)
                """,
                bt_id=bt_id, addr=addr, sd_id=sd_id
            )

        if parent_slug:
            session.run(
                """
                MERGE (pt:SupplyTopic {slug: $ps})
                SET pt.batch_id = $sd_id
                MERGE (ch:SupplyTopic {slug: $cs})
                MERGE (ch)-[:SUBTOPIC_OF]->(pt)
                """,
                ps=parent_slug, cs=slug, sd_id=sd_id,
            )
            ops.append({"op": "BRIDGE_SUBTOPIC_OF", "child": slug, "parent": parent_slug})

        session.run(
            """
            MATCH (sd:SecondDream {id: $sd_id})
            MATCH (bt:SupplyBridgeThought {id: $bt_id})
            MATCH (tt:SupplyTopic {slug: $slug})
            MERGE (sd)-[:INCLUDES_BRIDGE]->(bt)
            MERGE (sd)-[:TRACKS_TOPIC]->(tt)
            """,
            sd_id=sd_id, bt_id=bt_id, slug=slug,
        )
        return ops

    def _forge_tactical_thoughts_neo4j(self, session, sd_id, p9, dream_ids, graph_operations_log):
        if not p9 or not p9.get("is_valuable_tactics"):
            graph_operations_log.append({"op": "PHASE9_SKIP", "reason": "is_valuable_tactics false or empty"})
            return
        items = p9.get("tactical_thoughts") or []
        if not items:
            graph_operations_log.append({"op": "PHASE9_SKIP", "reason": "no tactical_thoughts"})
            return

        for idx, tac in enumerate(items):
            tid = f"{sd_id}_tac_{idx}"[:500]
            trig = (tac.get("situation_trigger") or "").strip()
            rule = (tac.get("actionable_rule") or "").strip()
            if not rule: continue
            try: pw = float(tac.get("priority_weight", 5.0))
            except (TypeError, ValueError): pw = 5.0
            phase = str(tac.get("applies_to_phase") or "0")

            session.run(
                """
                MATCH (ego:CoreEgo {name: '송련'})
                MERGE (t:TacticalThought {id: $tid})
                SET t.situation_trigger = $trig,
                    t.actionable_rule = $rule,
                    t.priority_weight = toFloat($pw),
                    t.applies_to_phase = $phase,
                    t.created_at = timestamp(),
                    t.batch_id = $sd_id
                MERGE (ego)-[:ORDERS_TACTIC]->(t)
                """,
                tid=tid, trig=trig, rule=rule, pw=pw, phase=phase, sd_id=sd_id,
            )
            session.run(
                """
                MATCH (t:TacticalThought {id: $tid})
                MATCH (sd:SecondDream {id: $sd_id})
                MERGE (t)-[:FORGED_IN]->(sd)
                """,
                tid=tid, sd_id=sd_id,
            )
            for did in dream_ids:
                if not did: continue
                session.run(
                    """
                    MATCH (t:TacticalThought {id: $tid})
                    MATCH (d:Dream {id: $did})
                    MERGE (t)-[:GROUNDED_IN]->(d)
                    """,
                    tid=tid, did=did,
                )
            graph_operations_log.append({"op": "TACTICAL_THOUGHT", "id": tid})

    def _save_to_neo4j(self, state: MidnightState, dreams):
        print("💾 [System] 랭그래프 최종 결과물 Neo4j 각인 중...")
        sd_id = f"sd_{state['target_date']}_{int(datetime.now().timestamp())}"
        debate_state = _build_reflection_debate_state(state)
        try:
            with self.neo4j_driver.session() as session:
                session.run(
                    "MERGE (sd:SecondDream {id: $sd_id}) "
                    "SET sd.date = $target_date, "
                    "    sd.created_at = timestamp(), "
                    "    sd.debate_state_json = $debate_state_json",
                    sd_id=sd_id,
                    target_date=state["target_date"],
                    debate_state_json=json.dumps(debate_state, ensure_ascii=False),
                )
                for d in dreams:
                    session.run(
                        "MATCH (sd:SecondDream {id: $sd_id}), (d:Dream {id: $did}) MERGE (d)<-[:AUDITED_FROM]-(sd)",
                        sd_id=sd_id, did=d["dream_id"]
                    )
                ops = []
                topics = state["phase_7_audit"].get("classified_topics", [])
                ops.extend(self._merge_topic_hierarchy(session, sd_id, topics))
                
                topics_by_slug = {t.get("topic_slug", ""): t.get("title", "") for t in topics}
                for seq, bridge in enumerate(state["bridges"]):
                    ops.extend(self._persist_address_thought_topic(session, sd_id, bridge, topics_by_slug, seq))
                
                self._forge_tactical_thoughts_neo4j(session, sd_id, state["tactical_doctrine"], state["dream_ids"], ops)
                print(f"🎉 각인 완료! 총 {len(ops)}개의 신경망 탯줄이 연결되었습니다.")
                return {
                    "sd_id": sd_id,
                    "operations_count": len(ops),
                    "topic_count": len(state.get("phase_7_audit", {}).get("classified_topics", [])),
                    "bridge_count": len(state.get("bridges", [])),
                    "tactic_count": len((state.get("tactical_doctrine") or {}).get("tactical_thoughts") or []),
                    "debate_state": debate_state,
                }
        except Exception as e:
            print(f"💥 저장 중 에러: {e}")
            return {"sd_id": sd_id, "error": str(e)}

    def execute_midnight_reflection(self, target_date):
        print("==================================================")
        print(f"🌙 [{target_date}] 심야 성찰 (랭그래프 V6.0) 가동!")
        print("==================================================")

        ready, reason = self._ensure_neo4j_ready()
        if not ready:
            print(f"⛔ [System] 심야 성찰 중단: {reason}\n")
            return {
                "status": "blocked",
                "target_date": target_date,
                "reason": reason,
            }

        dreams = self.fetch_unaudited_dreams(target_date)
        if not dreams:
            print("💤 이 날짜에 감사할 꿈이 없거나 이미 2차 꿈으로 감사됨.\n")
            return

        dream_ids = [d["dream_id"] for d in dreams if d.get("dream_id")]
        log_text = self.dream_rows_to_log_text(dreams)

        # 🚀 랭그래프 혈관에 첫 피를 수혈합니다!
        initial_state = {
            "target_date": target_date,
            "dream_ids": dream_ids,
            "dreams_log_text": log_text,
            "phase_7_audit": {},
            "pending_actions": [],
            "loop_count": 0,
            "tool_runs": [],
            "bridges": [],
            "doubt_feedback": "",
            "phase_8b_feedback": "",
            "tactical_doctrine": {}
        }

        # 💥 랭그래프 시동 쾅!!!
        final_state = self.app.invoke(initial_state)

        # 💾 결과물 저장
        save_result = self._save_to_neo4j(final_state, dreams)
        return {
            "status": "completed",
            "target_date": target_date,
            "loop_count": final_state.get("loop_count", 0),
            "pending_action_count": len(final_state.get("pending_actions", [])),
            "bridge_count": len(final_state.get("bridges", [])),
            "tactic_count": len((final_state.get("tactical_doctrine") or {}).get("tactical_thoughts") or []),
            "save_result": save_result,
        }
    def execute_grand_reflection_sweep(self):
        print("\n🔥 [System] 전 일자 Dream에 대한 공급 감사 싹쓸이 개시!")
        ready, reason = self._ensure_neo4j_ready()
        if not ready:
            print(f"⛔ [System] 싹쓸이 중단: {reason}")
            return
        try:
            with self.neo4j_driver.session() as session:
                cypher = (
                    "MATCH (d:Dream) WHERE NOT (d)<-[:AUDITED_FROM]-(:SecondDream) "
                    "RETURN DISTINCT substring(d.date, 0, 10) AS date_str ORDER BY date_str ASC"
                )
                result = session.run(cypher)
                all_dates = [record["date_str"] for record in result if record["date_str"]]
            if not all_dates:
                print("💤 감사 대상 Dream 이 없습네다.")
                return
            print(f"🎯 미감사 일자 {len(all_dates)}개: {all_dates}")
            for target_date in all_dates:
                self.execute_midnight_reflection(target_date)
            print("🎉 싹쓸이 공급 감사 완료!")
        except Exception as e:
            print(f"💥 싹쓸이 중 오류: {e}")
    

if __name__ == "__main__":
    DreamWeaver().execute_grand_reflection_sweep()
