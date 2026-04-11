# Core/tools.py
import os
import sys
from langchain_core.tools import tool

# 🚀 파이썬이 폴더 헷갈리지 않게 프로젝트 루트 경로 강제 주입!
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0,project_root)

from tools import toolbox
from tools.toolbox import get_db_session, scan_db_schema

@tool
def tool_search_memory(keyword: str) -> str:
    """
    과거 기억을 검색하는 시맨틱 검색 도구입니다.
    
    - keyword: 사용자가 찾고자 하는 '실제 검색어'
    🚨 [경고]: 절대 이 도구의 설명문이나 이름("지식 그래프 시맨틱 검색기" 등)을 키워드 파라미터에 집어넣지 마십시오! 오직 검색할 단어만 넣어야 합니다.
    """
    res_text, _ = toolbox.search_memory(keyword)
    return res_text

@tool
def tool_scroll_chat_log(target_id: str, direction: str = "both", limit: int = 15) -> str:
    """
    [대화록 전용 스크롤 스나이퍼 도구]
    특정 대화 노드(target_id)를 기준으로 앞(과거) 또는 뒤(미래)의 대화 맥락을 지정한 개수만큼 긁어옵니다.
    0차 감독관이 특정 대화의 전후 맥락을 파악하고 싶을 때 이 도구를 사용하십시오.
    
    - target_id: 기준이 되는 대화 노드의 ID(YYYY-MM-DD 등)
    - direction: 'past' (과거만), 'future' (미래만), 'both' (양방향 모두) 중 택 1
    - limit: 한 방향당 가져올 대화의 최대 개수 (안전을 위해 최대 30으로 제한됨)
    """
    res_text, _ = toolbox.scroll_chat_log(target_id, direction, limit)
    return res_text
    
@tool
def tool_read_full_diary(target_date: str) -> str:
    """
    [일기장 전용 덤프 도구]
    특정 날짜의 '일기장(Diary)' 원문을 통째로 읽어옵니다. (주의: 대화록에는 사용하지 마십시오)
    - target_date: 검색할 날짜 (예: '2026-04-01')
    """
    # 💡 [V8.0 수술 완료]: 낡은 날쿼리를 버리고, 우리가 강화해둔 toolbox의 고성능 무기를 호출합니다!
    res_text, _ = toolbox.read_full_source("일기장", target_date)
    return res_text

@tool
def tool_read_artifact(artifact_hint: str) -> str:
    """
    [범용 문서/아티팩트 열람 도구]
    PPTX, TXT, MD, JSON, DOCX, 코드 파일 같은 로컬 아티팩트를 읽습니다.
    - artifact_hint: 파일명 일부, 문서 이름, 또는 로컬 경로
    """
    res_text, _ = toolbox.read_artifact(artifact_hint)
    return res_text

@tool
def tool_pass_to_phase_3() -> str:
    """
    [수사 종료 및 패스 도구]
    허정후의 발화가 일상적인 대화(인사 등)이거나, 이미 충분한 수색이 완료되어 
    더 이상의 과거 데이터 탐색이 필요 없을 때 이 도구를 호출하여 3차 검증관에게 제어권을 넘깁니다.
    """
    return "BYPASS_TO_3"

@tool
def tool_scan_db_schema(dummy_keyword: str = "") -> str:
    """
    [Neo4j 실시간 구조 스캔 도구]
    현재 그래프 데이터베이스의 전체 구조(노드, 관계)를 스캔합니다.
    - dummy_keyword: 이 도구는 파라미터가 필요 없으므로, 그냥 "스캔" 이라는 단어를 넣거나 비워두십시오.
    """
    result_str, _ = scan_db_schema()
    return result_str

@tool
def tool_scan_trend_u_function(keyword: str, track_type: str = "Episode") -> str:
    """
    [심야 8차/주간 1차 공용 도구: U-함수 시계열 트렌드 스캐너]
    특정 키워드(사상, 감정, 주제)가 과거부터 현재까지 어떻게 변해왔는지 절대값 기반의 텍스트 막대그래프(Trend)로 분석합니다.
    - keyword: 추적할 주제나 감정 단어 
    - track_type: "Episode" (거시적 일일 요약 트랙) 또는 "PastRecord" (미시적 대화/일기 트랙). 기본값은 "Episode".
    """
    # 💡 텅 비어있던 뱃속을 채웠습니다! toolbox에 깎아둔 무기를 직접 꺼내옵니다!
    return toolbox.scan_trend_u_function(keyword, track_type)

@tool
def tool_call_119_rescue() -> str:
    """
    [긴급 119 구조대 호출 도구 / 환각 정정 모드]
    사용자(허정후)가 시스템의 이전 대답에 강한 불만을 표출하거나, 
    "아니야", "틀렸어", "인칭 헷갈리지 마" 등 팩트 오류를 지적하며 화를 낼 때 무조건 호출하십시오.
    이 도구를 호출하면 즉시 변명을 멈추고 시스템 환각 정정 프로세스로 진입합니다.
    """
    return "EMERGENCY_RESCUE_119"

# Core/agent_tools.py 내부 도구 선언 수정

@tool
def tool_scan_trend_u_function_3d(keyword_z: str, keyword_anti_z: str, keyword_y: str, track_type: str = "PastRecord") -> str:
    """
    [V6.1 심야 전용 도구: 3차원 위상 공간 U-함수 스캐너 & 교점 추출기]
    허정후의 심리를 3차원 축으로 스캔하여, '정반합'을 도출할 수 있는 유의미한 '리프 노드'만 걸러냅니다.
    
    - keyword_z: 분석하고자 하는 주제 ("SupplyTopic의 값이 들어가는 곳")
    - keyword_anti_z: Z와 대립되는 모순/그림자 ("SupplyTopic과 의미가 정반대일 것으로 추정되는 키워드")
    - keyword_y: 7차 감사관이 지정한 상황 변수 ("7차가 SupplyTopic 분석에 용이하다고 생각되는 주제")
    - track_type: "Episode" 또는 "PastRecord". 기본값은 "PastRecord" (미시적 대화 추적).
    
    🚨 반드시 3개의 축(Z, Anti-Z, Y) 키워드를 모두 입력해야 엔진이 돌아갑니다!
    """
    return toolbox.scan_trend_u_function(keyword_z, keyword_anti_z, keyword_y, track_type)

# (아래 available_tools 배열은 그대로 유지!)

# 🚨 배열 하나로 깔끔하게 정리 끝!
available_tools = [
    tool_search_memory, 
    tool_read_full_diary, 
    tool_read_artifact,
    tool_scroll_chat_log,
    tool_pass_to_phase_3,
    tool_scan_db_schema,
    tool_scan_trend_u_function, # 👈 U-함수 등록 완료!
    tool_scan_trend_u_function_3d, # 👈 3D 스캐너 추가!
    tool_call_119_rescue # 👈 [긴급 추가됨!] 119 구조대 버튼!
]
