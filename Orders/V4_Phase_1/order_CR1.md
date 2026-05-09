# 발주 #CR1 — 2b 사고 비판자 (thought_critic mode) + -1s 사고 재귀 + deterministic 게이트

**발주일**: 2026-05-09
**트랙**: V4 Phase 1 / **CR 트랙 #CR1** (Critic Recursion 1차, Phase 1 1순위)
**선행**: V4 §1-A LIVE (commit `556bbd0`, 2026-05-09 정후 통과). F1~F4 다 박힘.
**의존성**: TR1 (F4 후 같은 input 1턴 verify) **CR1 진입 전 즉시 진행 권고**. T1/B9/B10/C0.8/0.9/0.10과는 평행 가능.

---

## Why

V4 §1-A 통과의 핵심 비전 박혔지만 **코드는 비전 미반영 상태**. 핵심:

1. **정후 정의 명문화 (V3 → V4 진화)**: -1s = 상황 판단자, -1a = 목표 수립자, 2b = 사실 판사 + 사고 비판자.
2. **2b를 -1s 사이클 중간 비판자로 끼움** (정후 비전 2026-05-09): 2b의 사실 판사 권한 위에 thought_critic mode 신설. Input differentiator 역할로 gemma4 false negative 자동 방어.
3. **deterministic 게이트** = `has_goal AND fact_cells == 0 AND no_tool_needed`. delivery_readiness 의존 제거 (LLM 라벨 false negative 차단).
4. **트리오 재귀 anchor** (V4 §0 부록 Y v1.0 *최초 인스턴스*): -1s ↔ 2b_thought_critic ↔ -1a 사이에서 트리오 재귀. §1-C 일반화의 reference.

현 상태 (2026-05-09 verify):

- `Core/pipeline/contracts.py:258-277` `ThinkingHandoff` schema 9필드 박힘. **`recipient` / `next_node` Literal에 `warroom_deliberator` / `2b_thought_critic` 없음**.
- `Core/pipeline/contracts.py` 2b 입력 schema = raw_read_report + planned_operation_contract + working_memory_packet + reasoning_board. **mode 필드 X, thought_critic 입력 X**.
- `Core/pipeline/contracts.py` `ThoughtCritique.v1` schema **없음**.
- `Core/graph.py:184-198` `route_after_strategist` = `_executable_tool_request` (deprecated) / `_strategist_no_tool_delivery_ready` → phase_3 / 그 외 → 0_supervisor. **`_strategist_needs_thought_recursion` 게이트 없음, 2b_thought_critic 분기 없음**.
- `Core/graph.py:156-181` `route_after_s_thinking` = -1a/phase_3/phase_119 분기. **warroom_deliberator/2b_thought_critic 라우팅 없음**.
- `Core/prompt_builders.py` -1s 시스템 프롬프트 = 일반 사고. **2차 호출 검증 우선 + 워룸/CoT 라우팅 rule 없음**.
- `Core/pipeline/` 2b thought_critic mode 모듈 **없음**.

CR1은 위 결함을 일괄 보강. 정후 비전 코드 박음.

---

## 스코프

**3개 schema 변경 + graph 분기 신설 + 프롬프트 모드 분기 + 새 모듈 1개 + 새 tests 13건**. ~230줄 본 코드 + ~80줄 tests.

### A. ThinkingHandoff.v1 Literal 확장

A-1. **`Core/pipeline/contracts.py:261-272` `ThinkingHandoff` Literal 확장**:
- `recipient: Literal["-1a", "phase_3", "phase_119", "warroom_deliberator", "2b_thought_critic"]`
- `next_node: Literal["-1a", "phase_3", "phase_119", "warroom_deliberator", "2b_thought_critic"]`
- description 갱신: "Includes thought-recursion routes (warroom/thought_critic) when -1s second-call decides depth."

A-2. **`Core/pipeline/start_gate.py:178` `_handoff_next_node`** 헬퍼 갱신:
- 새 라우팅 옵션 mapping 추가 (`warroom_deliberator`, `2b_thought_critic`).
- 기존 `_handoff_next_node` 분기 보존, 신규 두 개만 추가.

### B. 2b 입력 schema 확장 + ThoughtCritique.v1 신설

B-1. **`Core/pipeline/contracts.py` `Phase2bInput` (또는 동등 입력 schema) `mode` 필드 추가**:
- `mode: Literal["fact_judge", "thought_critic"] = Field(default="fact_judge")`
- 기존 fact_judge 입력 6필드는 변경 X.
- thought_critic mode 입력: `s_thinking_packet` + `recent_context` + `working_memory` + (있으면) `fact_cells_for_critique` (V4 5필드 compact).

B-2. **`Core/pipeline/contracts.py` `ThoughtCritique` schema 신설** (v1):
```python
class ThoughtCritique(BaseModel):
    schema_version: Literal["ThoughtCritique.v1"] = Field(default="ThoughtCritique.v1", alias="schema")
    producer: Literal["2b_thought_critic"] = Field(default="2b_thought_critic")
    hallucination_risks: List[CritiqueItem] = Field(default_factory=list)  # 사고가 사실 없는데 박은 주장
    logic_gaps: List[CritiqueItem] = Field(default_factory=list)  # 추론 단계 누락
    memory_omissions: List[CritiqueItem] = Field(default_factory=list)  # 최근 기억 못 본 부분
    persona_errors: List[CritiqueItem] = Field(default_factory=list)  # 인칭/맥락 혼동
    delta: str = Field(default="", description="Compact 1-2 sentence summary for second -1s call")
    evidence_refs: List[str] = Field(default_factory=list, description="fact_id list cited from reasoning_board")
```

`CritiqueItem` 도 신설 (sub-schema):
```python
class CritiqueItem(BaseModel):
    issue: str
    evidence_refs: List[str] = Field(default_factory=list)
    severity: Literal["minor", "warning", "blocker"] = Field(default="warning")
```

### C. 2b 시스템 프롬프트 모드 분기

C-1. **`Core/prompt_builders.py` 2b 시스템 프롬프트 builder 갱신** (정확한 함수명은 grep으로 찾기, 보통 `build_phase_2b_prompt` 또는 유사):
- 현 builder = fact_judge 모드 단일.
- 신규: `mode` 인자 추가. `mode == "thought_critic"` 시 다른 시스템 프롬프트 emit.
- thought_critic 모드 프롬프트 핵심:
  - "You are -1s's thought critic. Compare the s_thinking_packet against recent_context + working_memory + fact_cells (if any)."
  - "Detect: hallucination_risks (claims without evidence), logic_gaps (missing reasoning steps), memory_omissions (recent info missed), persona_errors (인칭/맥락 혼동)."
  - "If fact_cells > 0 → unified critique mode. If fact_cells == 0 → memory-based critique mode (auto-switch by input)."
  - "Output ThoughtCritique.v1. Cite fact_id where possible. Do NOT call tools. Do NOT write final answer."
  - "Authority: critique only. Forbidden: routing decision, fact 새로 조회, answer text 작성, fact_id 발명."

### D. -1s 시스템 프롬프트 2차 호출 동작 rule

D-1. **`Core/prompt_builders.py` -1s 시스템 프롬프트 builder 갱신**:
- 입력 인자에 `prior_thought_critique: ThoughtCritique | None` 추가.
- prompt에 새 블록 추가:
  ```
  [prior_thought_critique]
  {compact representation if not None, else "N/A"}
  ```
- 새 rule (기존 rule 뒤에 추가):
  ```
  Rule X (recursion mode): If [prior_thought_critique] is not "N/A":
    Step 1 (verification — MUST run first):
      Re-read working_memory + recent_context + fact_cells thoroughly.
      Ask: "Given the critique, is the evidence actually thin, or did the previous step miss something?"
      If verified evidence is sufficient → set next_node="phase_3" and skip recursion.
    Step 2 (recursion routing — only if Step 1 fails):
      Decide warroom_deliberator vs another 2b_thought_critic call based on depth needed.
      "Deep deliberation needed" → warroom_deliberator.
      "Light critique sufficient" → set next_node="phase_3" anyway (do not loop critique).
  ```

### E. graph 분기 신설

E-1. **`Core/graph.py` `_strategist_needs_thought_recursion` 헬퍼 신설** (helpers 영역, `_strategist_no_tool_delivery_ready` 부근):
```python
def _strategist_needs_thought_recursion(state: AnimaState) -> bool:
    """Detect deterministic gate for 2b_thought_critic recursion.

    Gate conditions (V4 §1-A.3, all AND):
      - has_goal: strategist_goal.user_goal_core 박힘 (-1a fallback도 박음)
      - no_facts: reasoning_board.fact_cells == 0
      - no_tool_needed: action_plan.required_tool 비어있음 + tool_request 없음

    delivery_readiness 의존 제거 (V4 §1-A.0 정후 우려 — LLM 라벨 false negative 차단).
    """
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        return False

    strategist_goal = strategist_output.get("strategist_goal", {})
    if not isinstance(strategist_goal, dict):
        strategist_goal = {}
    has_goal = bool(str(strategist_goal.get("user_goal_core") or "").strip())

    reasoning_board = state.get("reasoning_board", {})
    if not isinstance(reasoning_board, dict):
        reasoning_board = {}
    fact_cells = reasoning_board.get("fact_cells", [])
    no_facts = isinstance(fact_cells, list) and len(fact_cells) == 0

    action_plan = strategist_output.get("action_plan", {})
    if not isinstance(action_plan, dict):
        action_plan = {}
    required_tool = str(action_plan.get("required_tool") or "").strip()
    no_tool_needed = (
        not required_tool
        and not _executable_tool_request(strategist_output)
    )

    return has_goal and no_facts and no_tool_needed
```

E-2. **`Core/graph.py:184-198` `route_after_strategist` 새 분기 추가** (기존 분기 사이):
```python
def route_after_strategist(state: AnimaState):
    if _graph_hard_stop_exceeded(state):
        _log("[System] Strategist loop budget exhausted; routing to phase_119.")
        return "phase_119"
    strategist_output = state.get("strategist_output", {})
    if not isinstance(strategist_output, dict):
        strategist_output = {}
    if _executable_tool_request(strategist_output):
        _log("[System] Deprecated -1a tool_request detected; routing to 0_supervisor.")
        return "0_supervisor"
    if _strategist_no_tool_delivery_ready(state):
        _log("[System] -1a supplied a no-tool delivery contract; routing to phase_3.")
        return "phase_3"
    if _strategist_needs_thought_recursion(state):  # NEW
        _log("[System] -1a fallback with no facts; routing to 2b_thought_critic.")
        return "2b_thought_critic"
    _log("[System] -1a asks phase 0 to select the concrete tool operation.")
    return "0_supervisor"
```

E-3. **`Core/graph.py:156-181` `route_after_s_thinking` 새 분기 추가** (warroom/2b_thought_critic 라우팅 추가):
```python
    if next_node == "warroom_deliberator":
        _log("[System] -1s requests warroom deliberation.")
        return "warroom_deliberator"
    if next_node == "2b_thought_critic":
        _log("[System] -1s requests another thought critique.")
        return "2b_thought_critic"
```
(기존 phase_3/-1a/phase_119 분기 사이에 추가)

E-4. **graph 노드 추가 + 회귀 분기**:
- 새 노드 `2b_thought_critic` graph에 등록 (StateGraph.add_node).
- 회귀 분기: `2b_thought_critic` → `-1s_start_gate` (강제, 2차 -1s 호출).
- LangGraph compile 갱신.

### F. 새 모듈 — `Core/pipeline/thought_critic.py`

F-1. **`Core/pipeline/thought_critic.py` 신설** (~50줄):
- `run_2b_thought_critic_node(state, ...)` entrypoint.
- 입력 추출 (s_thinking_packet, recent_context, working_memory, fact_cells_for_critique).
- 2b LLM 호출 (`mode="thought_critic"`, structured output `ThoughtCritique`).
- state에 `prior_thought_critique` 박음 (다음 -1s 호출 input differentiator).
- fallback: LLM 실패 시 빈 ThoughtCritique 박음 (안전장치).

F-2. **`Core/nodes.py` 또는 `Core/graph.py`에서 `run_2b_thought_critic_node` import + register**.

### G. 새 tests (~80줄)

G-1. `tests/test_2b_thought_critic.py` (4 cases):
- mode 자동 전환 (fact_cells > 0 → 통합 / == 0 → 기억 기반)
- ThoughtCritique.v1 9필드 정합성
- 도구 호출 차단 (정규식 또는 schema 차단)
- fallback 안전장치

G-2. `tests/test_thought_recursion_routing.py` (5 cases):
- route_after_strategist 새 분기 (게이트 통과 → 2b_thought_critic)
- route_after_s_thinking 새 분기 (warroom_deliberator / 2b_thought_critic)
- 2b_thought_critic → -1s_start_gate 회귀
- ThinkingHandoff Literal 확장 호환성
- hard_stop 우선 (게이트 통과해도 hard_stop 도달 시 phase_119)

G-3. `tests/test_strategist_needs_thought_recursion_gate.py` (4 cases):
- has_goal AND fact_cells==0 AND no_tool_needed → True
- fact_cells > 0 → False
- delivery_readiness=need_reframe (LLM 라벨)인데 fact_cells > 0 → False (의존 제거 verify)
- has_goal == False → False

목표: F4 baseline 294 + 신규 13 = 예상 **307 OK**. 정확한 test count는 최종 보고.

---

## 작업 시작 전 필수 read

1. `AGENTS.md` (인코딩 규칙 + Codex 작업 규칙)
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` **§1-A 전체** (LIVE LAW 본 발주의 근거)
4. **`Orders/V4_Phase_0/V4_section1_decision_sheet_v3_1_2026_05_09.md`** (결재 결과 단일 출처, 본 발주의 정후 비전 출처)
5. `ANIMA_ARCHITECTURE_MAP.md` (R 시리즈 #61~#69 + F1~F4 #70~#73 + Phase 0→1 진입 marker)
6. `Core/pipeline/contracts.py` 전체 (ThinkingHandoff/StrategistGoal/StrategistReasoningOutput/DeliveryReview/ FactCell)
7. `Core/pipeline/start_gate.py` (`_build_s_thinking_packet`, `_handoff_next_node`)
8. `Core/graph.py` (route_after_s_thinking / route_after_strategist / `_strategist_no_tool_delivery_ready` / `_executable_tool_request`)
9. `Core/prompt_builders.py` (-1s / 2b 시스템 프롬프트 builders)
10. `Core/pipeline/strategy.py` (`run_base_phase_minus_1a_thinker` — 게이트 진입 시 fallback 동작 검증)
11. `Core/nodes.py:5140-5306` `_base_fallback_strategist_output` (게이트 trigger 시점 동작 verify)

---

## 검증 기준

- 새 tests 13건 신규 통과 + 기존 294건 회귀 X. **307 OK 목표**.
- ThinkingHandoff Literal 확장 회귀 X (기존 `recipient="-1a"` / `next_node="-1a"` 등 정상 동작).
- `_strategist_needs_thought_recursion` 게이트 false positive X (정상 케이스에서 게이트 안 탐).
- thought_critic mode → -1s_start_gate 회귀 시 `prior_thought_critique` state 박혀있음.
- 2차 -1s 호출 시 `prior_thought_critique` not None → 검증 우선 rule 적용 (verify by prompt inspection).
- hard_stop 우선 (게이트 통과해도 hard_stop 시 phase_119) — 무한 회귀 차단.

## ARCH MAP 갱신

- purge log #74 신규 추가: "CR1: 2b thought_critic mode + -1s 사고 재귀 + deterministic 게이트 + 트리오 재귀 첫 인스턴스".

## 의존성 / 후속

- TR1 verify는 CR1 진입 *전* 또는 *직후* 즉시. F4 commit 후 정후 trace 케이스 다시 실행 → 무한 핑퐁 사라짐 verify.
- §1-C 트리오 재귀 본문 작성 = CR1 박힌 후 가능 (§1-A.13 anchor reference).
- T1 (DreamHint 가중치 + 과거 정부 통합) = 평행 발주 가능.
- C0.8/0.9/0.10 (legacy cleanup) = CR1과 평행 가능. graph.py route_audit_result_v2 fallback 정리는 CR1과 같은 파일이라 충돌 주의.

## 결재 root

- V4 §1-A LIVE (commit `556bbd0`, 2026-05-09)
- 결재 시트 v3.1 (X6 = A/B/C/D + B-1/B-2/B-2.1/B-2.2/B-2.3/B-2.4/B-3 다 박힘)
- 정후 비전 (2026-05-09): "이미 2b라는 훌룡한 비판자가 있음. 얘를 -1s 경량 CoT 중간중간에 넣으면 될 듯"
