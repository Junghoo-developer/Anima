# 발주 #F4 — 0차 LLM 일반 흐름화 + -1a tool_request 권한 이동

**발주일**: 2026-05-07
**트랙**: V4 Phase 0 / **F 트랙 #F4** (V4 §1 권한분리 마지막 인프라)
**선행**: F3 완료 (commit 또는 working tree, -1a 입력 축소 + tactical_briefing 채널 이동 + fact_cells_for_strategist 박힘, 278 tests OK).
**의존성**: 없음. F1/F2/F3 통합. **F2/F3 회귀 의심 패턴 발견 시 즉시 멈추고 보고**.

---

## Why

V4 §1 권한표 결재 핵심:
- **결재 8 (2026-05-06 박힘)**: 0_supervisor LLM = 일반 흐름의 도구 결정 LLM으로 격상. 현재 fallback only. 권한 = 도구 호출/검색어 생성만. 답변 작성 X / answer_mode 변경 X / 사고 재판정 X.
- **F4 비전 (2026-05-06 정후 채택)**: -1a strategist에서 tool_request 생성 권한 제거 → 0차가 자체 LLM으로 도구 호출 결정.
- **결재 4-5 (2026-05-07 박힘, 본 발주 직전)**:
  - (1) operation_contract schema = 현 `OperationContract` 그대로. F4 운영 검증 후 v2 별도 결재.
  - (2) -1a fallback 라우팅 = 도구 필요 시 **항상 0_supervisor** (-1s 회귀는 -1a가 작전 자체 못 짤 때만 예외).

**F2/F3가 길 닦았음**:
- F2 = -1s 사고 권한 + ThinkingHandoff.v1 9필드 + -1b fact_id 인용 채널.
- F3 = -1a 입력 surface 18개 (analysis/raw_read/reasoning_board/tactical_briefing 4개 빠짐, fact_cells_for_strategist 박힘).
- F4 = -1a 출력에서 tool_request 빼서 0차로 옮김 → 권한 분리 최종형.

현 상태 (2026-05-07 verify):

- `Core/pipeline/contracts.py:586` `StrategistReasoningOutput.tool_request` 필드 박혀있음 (`StrategistToolRequest` schema = should_call_tool/tool_name/tool_args/rationale).
- `Core/pipeline/strategy.py:159` `ensure_tool_request_in_strategist_payload` callable 호출 ([:270](Core/pipeline/strategy.py#L270) / [:296](Core/pipeline/strategy.py#L296) / [:334](Core/pipeline/strategy.py#L334)) — -1a 출력 정규화 시 tool_request 강제 채움.
- `Core/pipeline/supervisor.py:44-64` `strategist_output.tool_request` 우선 분기 박혀있음. LLM 호출 ([:125-176](Core/pipeline/supervisor.py#L125-L176))은 fallback only.
- `Core/graph.py:191-193` `_executable_tool_request(strategist_output)` 분기로 0_supervisor 진입.

V4 §1 권한분리 마지막 단계. 이거 끝나면 §1 본문 글 박는 단계 (학교 모드).

---

## 스코프

본 발주 = **-1a tool_request 권한 제거 + 0_supervisor LLM 일반 흐름화 + graph 라우팅 갱신 + 테스트**. 이후 V4 §1 본문 작성.

### A. -1a strategist tool_request 생성 권한 제거

A-1. **`StrategistReasoningOutput` schema에서 `tool_request` 필드 제거** ([Core/pipeline/contracts.py:586-589](Core/pipeline/contracts.py#L586-L589)):
- `StrategistReasoningOutput.tool_request` 필드 삭제.
- `StrategistToolRequest` Pydantic 모델 자체는 **deprecated 표시 + 보존** (1주 운영 호환, 옛 state 잔존 packet 처리용). docstring 추가: "DEPRECATED: -1a no longer authors tool calls (F4). Kept for one-season legacy compatibility on read-side."
- 새 출력 형식 검증: -1a structured output에 tool_request 없어도 정상 작동.

A-2. **`ensure_tool_request_in_strategist_payload` 호출 모두 제거**:
- `Core/pipeline/strategy.py:159` callable 시그니처 인자 제거.
- 호출처 ([:270](Core/pipeline/strategy.py#L270) / [:296](Core/pipeline/strategy.py#L296) / [:334](Core/pipeline/strategy.py#L334)) 모두 제거. -1a 출력 정규화 후 tool_request 채우는 단계 사라짐.
- helper 본체 (nodes.py 또는 다른 파일, Codex가 grep으로 찾음) **deprecated 표시 + 본체 보존**: docstring "DEPRECATED: F4 removed -1a tool_request authorship. This helper is a no-op stub kept for one-season compatibility." + 호출 시 그냥 입력 payload 그대로 반환 (no-op).
- 1주 운영 후 helper 본체 + StrategistToolRequest schema 완전 제거 = 별도 발주.

A-3. **-1a 프롬프트 Rules 갱신** ([Core/prompt_builders.py:225](Core/prompt_builders.py#L225) `build_phase_minus_1a_prompt`):
- 옛 rule 5: "if action_plan.required_tool is executable, mirror it in tool_request with schema-valid args" **제거**.
- 새 rule (5번 자리): "Do not author tool calls. Phase 0 supervisor decides exact tool name, args, and queries. You only specify operation_contract intent (kind/source/target/scope) and let phase 0 LLM convert it to one safe tool call."
- 새 rule 추가 (6번): "If no tool is needed (direct answer is possible from fact_cells and ThinkingHandoff), set delivery_readiness=deliver_now and leave action_plan.required_tool empty."

### B. 0_supervisor LLM 일반 흐름화

B-1. **strategist_output.tool_request 분기 제거** ([Core/pipeline/supervisor.py:44-64](Core/pipeline/supervisor.py#L44-L64)):
- 통째 삭제. -1a가 더 이상 tool_request 안 박으니 분기 자체가 dead code.

B-2. **fallback LLM → 일반 흐름 LLM으로 격상** ([Core/pipeline/supervisor.py:125-176](Core/pipeline/supervisor.py#L125-L176)):
- 옛 흐름: auditor_decision/direct_message 분기 다 실패하면 LLM (3 attempts) → 못 만들면 "blocked".
- 신 흐름:
  - **auditor_decision.action == "call_tool"** + **direct_message** 분기는 **유지** (옛 직결 instruction 처리, 후방 호환).
  - 위 두 직결 분기에서 결정 안 났을 때 = **일반 흐름 LLM 진입** (옛 fallback이지만 위치는 일반 흐름).
  - LLM 호출 횟수 = 3 attempts 그대로 (안전 마진).
  - LLM이 3회 모두 못 만들면 "blocked" → "remanding to -1b" 그대로 (예외 흐름 보존).

B-3. **0_supervisor LLM 시스템 프롬프트 갱신** ([Core/pipeline/supervisor.py:125-137](Core/pipeline/supervisor.py#L125-L137)):
- 옛: "active search captain" + "0-supervisor ops hub". 권한 명시 약함.
- 신: 권한 명시 박음.
  - "You are ANIMA's 0_supervisor — the ops layer that converts the strategist's operation_contract into one exact safe tool call."
  - "Inputs:"
    - `[user_input]`
    - `[operation_contract]` (-1a 작전 의도)
    - `[fact_cells]` (fact_id 인용 가능한 검증된 사실 카드 5필드)
    - `[s_thinking_packet_what_is_missing]` (ThinkingHandoff.v1의 빠진 슬롯 텍스트)
    - `[ops_tool_cards]` / `[ops_node_cards]` (도구/노드 메타)
  - "Authority:"
    - "Decide one safe tool call (or up to two `tool_search_memory` calls if user gave explicit alternatives)."
    - "Generate exact tool args and search queries."
    - "May refuse: if no tool would help, return no tool_calls so the graph routes to -1b for review."
  - "Forbidden:"
    - "Do not write final-answer text."
    - "Do not change answer_mode."
    - "Do not re-judge facts (that authority belongs to -1s/2b)."
    - "Do not invent fact_ids — only cite ones that appear in [fact_cells]."

B-4. **0_supervisor LLM 입력 packet 박기** ([Core/pipeline/supervisor.py:125-142](Core/pipeline/supervisor.py#L125-L142)):
- 새 변수 추출:
  - `fact_cells = state.get("reasoning_board", {}).get("fact_cells", [])` → `_compact_fact_cells_for_prompt(fact_cells, limit=10)` (F2 V4 5필드 helper 재사용).
  - `s_thinking_packet = state.get("s_thinking_packet", {})` → `what_is_missing = s_thinking_packet.get("what_is_missing", [])` (top-level ThinkingHandoff.v1).
- 옛 SThinkingPacket.v1 fallback (`s_thinking_packet.get("loop_summary", {}).get("gaps", [])`) **추가**: F2가 박은 1주 호환 보존.
- 프롬프트 본문에 `[fact_cells]` / `[s_thinking_packet_what_is_missing]` 블록 박음.

### C. graph 라우팅 갱신

C-1. **`route_after_strategist` 갱신** ([Core/graph.py:184](Core/graph.py#L184)):
- 옛 분기 ([:191-193](Core/graph.py#L191-L193)) `_executable_tool_request(strategist_output)` → "0_supervisor": **분기 그대로 유지하되 deprecation 로그**. -1a가 더 이상 tool_request 안 박으니 평시 trigger 0회. 단 옛 state (1주 운영 호환) trigger 시 deprecated 로그 + 0_supervisor.
- 신 평시 분기:
  - `_strategist_no_tool_delivery_ready(state)` → `phase_3` (직접 답변 가능).
  - 그 외 (도구 필요) → **항상 0_supervisor** (정후 결재 4-5 (2)).
  - 옛 "-1a completed without an executable tool_request; returning to -1s.": **사라짐**. -1a가 작전 짤 권한 있고 -1s로 회귀할 명시 신호 없으면 0_supervisor 진입이 단일 출처.
  - 단 -1a structured output 자체 실패 (fallback_strategist_output 진입) 시 -1s 회귀는 보존 (예외 흐름).

C-2. **`_executable_tool_request` helper 제거 vs 보존**:
- 옛 helper (graph.py 안 또는 별도 파일): -1a structured output에 tool_request 박혀있는지 검사.
- F4 후 평시 trigger 0회. 1주 호환 보존 + deprecation 로그 추가. 1주 후 별도 발주로 제거.

C-3. **route_audit_result_v2 ([Core/graph.py:247-279](Core/graph.py#L247-L279))**: `readiness_status in {"needs_memory_recall", "needs_tool_evidence"}` → `0_supervisor` 분기 그대로. 변경 X.

### D. 테스트

D-1. **신설 단위 테스트** `tests/test_strategist_no_tool_request.py` (case 5):
1. `StrategistReasoningOutput()` instantiate 시 `tool_request` 필드 **없음** (AttributeError 또는 model_fields에 미포함).
2. -1a structured output mock으로 `run_base_phase_minus_1a_thinker` 호출 → 결과 strategist_output에 `tool_request` 키 없음 (ensure helper no-op).
3. `ensure_tool_request_in_strategist_payload(payload)` 호출 (deprecated stub) → payload 그대로 반환 (no-op).
4. 옛 state에 `strategist_output.tool_request` 박혀있어도 (1주 호환 input) -1a 흐름이 깨지지 않음.
5. -1a 프롬프트 Rules에 "Do not author tool calls" 박힘 verify (build_phase_minus_1a_prompt 본문 검사).

D-2. **신설 단위 테스트** `tests/test_supervisor_general_flow.py` (case 6):
1. 빈 strategist_output + auditor_decision/direct_message 모두 비어있음 + auditor_instruction 채워진 state → 0_supervisor LLM 일반 흐름 진입 (mock LLM이 tool_call 반환) → tool_call_ready 결과.
2. 옛 strategist_output.tool_request 박힌 state (1주 호환 input) → 분기 dead code 확인 (LLM 일반 흐름 진입 또는 옛 분기 trigger 시 deprecated 경고 로그).
3. fact_cells가 reasoning_board에 박혀있을 때 → 0_supervisor 프롬프트에 `[fact_cells]` 블록 박힘 (5필드).
4. ThinkingHandoff `what_is_missing` 박혀있을 때 → 프롬프트에 `[s_thinking_packet_what_is_missing]` 블록 박힘.
5. mock LLM이 tool_call 0개 반환 (3 attempts 모두) → "blocked" + "remanding to -1b".
6. mock LLM이 시스템 프롬프트 권한 위반 ("answer_mode 변경" 시도) 시도 → schema-valid tool_call이 아니면 그냥 거부됨 (LLM 출력은 graph가 검사 안 함, 다음 노드가 처리. 이 case는 LLM 출력 schema 검증).

D-3. **신설 단위 테스트** `tests/test_graph_route_after_strategist_v2.py` (case 4):
1. -1a 출력 = 도구 필요 (action_plan.required_tool 채워짐) → 0_supervisor.
2. -1a 출력 = no_tool delivery ready (delivery_readiness=deliver_now, response_strategy 채워짐) → phase_3.
3. -1a structured output 실패 (fallback_strategist_output 진입) → -1s_start_gate 회귀.
4. 옛 strategist_output.tool_request 박힌 case (1주 호환 input) → 0_supervisor (deprecated 로그).

D-4. **회귀 테스트 패치**:
- `tests/test_strategy_projection.py` — F3에서 modified, F4에서 tool_request 의존 case 갱신.
- `tests/test_thin_controller_normalization.py` — tool_request 정규화 case 있으면 deprecated stub 검증으로 갱신.
- `tests/test_runtime_memory_boundaries.py` — strategist_output 키 surface 검증 갱신.
- 0_supervisor 관련 기존 tests (`tests/test_supervisor_*` 등 grep으로 찾음) — LLM 일반 흐름화 반영해서 갱신.

D-5. **자동 검사**: `python -B -m unittest discover -s tests` → 278 + 신규 15 = 예상 **293 OK** (정확한 case 수 작업 후 보고).

---

## 안 하는 것 (다음 발주)

- **operation_contract schema 확장** (보류 4): 결재 4-5 (1) = 현 OperationContract 그대로. F4 운영 검증 후 v2 별도 결재.
- **`StrategistToolRequest` schema 완전 제거**: 1주 운영 후 별도 발주.
- **`ensure_tool_request_in_strategist_payload` helper 본체 제거**: 1주 운영 후 별도 발주 (deprecated stub 보존).
- **`_executable_tool_request` helper 제거**: 1주 운영 후 별도 발주.
- **보류 6 (-1a 다른 surface 축소)**: working_memory / war_room / evidence_ledger / start_gate_review. 별도 결재.
- **working_memory → -1s 입력** (보류 1, X2): 별도 발주.
- **노드명 rename** (`phase_delivery_review` → `phase_minus_1b_delivery_review` 등): V4 §1 헌법 일괄.
- **0_supervisor 시스템 프롬프트의 두-도구 (`tool_search_memory` 두 개) 옵션 검토**: 본 발주 그대로 보존 ([supervisor.py:130](Core/pipeline/supervisor.py#L130) "explicit alternatives" rule). 1주 후 별도.
- **119 enum 분류** (보류 9): Phase 1 V4 §2 작성 시.
- **delivery_packet 미래 호환** (보류 10): Phase 1.

---

## 변경 대상 (코드 좌표)

### 변경
- `Core/pipeline/contracts.py` ([:586-589](Core/pipeline/contracts.py#L586-L589) `StrategistReasoningOutput.tool_request` 필드 제거 / [:306-323](Core/pipeline/contracts.py#L306-L323) `StrategistToolRequest` deprecated 표시).
- `Core/pipeline/strategy.py` ([:139-369](Core/pipeline/strategy.py#L139-L369) `ensure_tool_request_in_strategist_payload` 호출 3개 + 시그니처 인자 제거).
- `Core/nodes.py` (`ensure_tool_request_in_strategist_payload` helper 본체 — Codex가 grep으로 찾아 deprecated stub 처리).
- `Core/prompt_builders.py` ([:225-281](Core/prompt_builders.py#L225-L281) `build_phase_minus_1a_prompt` Rules 갱신 — 옛 rule 5 제거 + 새 rule 5/6 박음).
- `Core/pipeline/supervisor.py` (전면 갱신: [:44-64](Core/pipeline/supervisor.py#L44-L64) tool_request 분기 제거 + [:125-176](Core/pipeline/supervisor.py#L125-L176) LLM 일반 흐름화 + 시스템 프롬프트 + 입력 packet).
- `Core/graph.py` ([:184-198](Core/graph.py#L184-L198) `route_after_strategist` 갱신 — 신 평시 분기 + deprecated 로그).

### 신설
- `tests/test_strategist_no_tool_request.py` (5 case)
- `tests/test_supervisor_general_flow.py` (6 case)
- `tests/test_graph_route_after_strategist_v2.py` (4 case)

### 변경 없음 (확인만)
- `Core/pipeline/start_gate.py` (F2/F3 박힘, 변경 X).
- `Core/pipeline/delivery_review.py` (F2 박힘, 변경 X).
- `Core/pipeline/packets.py` (`_compact_fact_cells_for_prompt` F2 V4 5필드 helper, F4에서 0_supervisor도 재사용).
- `Core/state.py` (state schema 그대로 — `strategist_output` 키 유지, 그 안 `tool_request` subkey만 옛 state에 잔존).
- `Core/pipeline/plans.py` (`OperationContract` 그대로 — 결재 4-5 (1)).

---

## 헌법 정합

- **V4 §0 v0 위반 X**: 본 발주는 §1 권한표 본문 박기의 마지막 인프라.
- **V3 §2 절대 금지 24개 위반 X**: 도구 호출 권한 이동 (-1a → 0차)은 V3 §2가 다루지 않은 V4 추가 안건. fallback fabrication / hardcoded 분기 추가 X. 사고 권한 변경 X.
- **AGENTS.md §3.3 대형 nodes.py 수술 게이트 트리거**: `ensure_tool_request_in_strategist_payload` helper 1개 deprecated 처리 + 호출처 3곳 제거. 인벤토리 분류/일괄 이동 X. 게이트 트리거 X. 단 작업 시작 전 정후 결재 받음.
- **AGENTS.md §1 인코딩**: 신설 테스트 파일 모두 UTF-8 (BOM 없음). PowerShell 사용 시 `-Encoding utf8` 명시.
- **메모리 결재 8 + 결재 4-5 (1)(2)** 그대로 반영.

---

## 검증 기준

1. **자동 검사**: `python -B -m unittest discover -s tests` → 278 + 15 신규 = 예상 **293 OK** (정확한 case 수 발주 후 보고).
2. **수동 검사 (Codex 직접 verify)**:
   - `python -c "from Core.pipeline.contracts import StrategistReasoningOutput; print('tool_request' in StrategistReasoningOutput.model_fields)"` → `False`.
   - 빈 state로 `run_phase_0_supervisor(...)` 호출 (auditor_instruction 채움, strategist_output.tool_request 비움) → LLM 일반 흐름 진입 확인 (mock LLM 사용).
3. **purge log 추가**: `ANIMA_ARCHITECTURE_MAP.md` #73 추가.
   - 마커: "**V4 Phase 0 F트랙 #F4: 0차 LLM 일반 흐름화 + -1a tool_request 권한 이동**"
   - 변경 줄 수, 신설 테스트 3개, deprecated stub 처리 명시.
4. **grep 확인**:
   - `Core/pipeline/contracts.py` `StrategistReasoningOutput.tool_request` grep — 0건.
   - `Core/pipeline/strategy.py` `ensure_tool_request_in_strategist_payload` 호출 grep — 0건 (시그니처 인자 제거 후).
   - `Core/pipeline/supervisor.py` `strategist_output.get("tool_request"` grep — 0건.

---

## 롤백

- `git checkout 782a982 -- Core/pipeline/contracts.py Core/pipeline/strategy.py Core/pipeline/supervisor.py Core/graph.py Core/prompt_builders.py Core/nodes.py` 단일 커밋 복원 가능 (단 F2/F3 변경분이 아직 commit 안 된 상태라면 stash 사용).
- 신설 테스트 파일 삭제 가능.
- F2/F3 회귀 의심 시: 우선 F2/F3 commit 복원 → F4 다시 진행.
- deprecated stub 보존이라 옛 호출처가 잘못된 import 시도해도 깨지지 않음 (no-op).

---

## 코덱스가 발주 받기 전 읽어야 할 문서

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (V3 §1·§2 LIVE LAW)
4. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (V4 §0 v0)
5. `ANIMA_ARCHITECTURE_MAP.md` (R 시리즈 #61~#69 + F1 #70 + F2 #71 + F3 #72)
6. **`Orders/V4_Phase_0/order_F4.md`** (본 발주 풀 본문)
7. `Orders/V4_Phase_0/order_F3.md` (선행 — fact_cells_for_strategist / ThinkingHandoff.v1 의존성)
8. `Orders/V4_Phase_0/order_F2.md` (선행 — fact_cells_for_review / DeliveryReview / `_compact_fact_cells_for_prompt`)
9. `Core/pipeline/supervisor.py` 전체 (전면 갱신 대상)
10. `Core/pipeline/contracts.py:540-600` `StrategistReasoningOutput` + `StrategistToolRequest`
11. `Core/pipeline/strategy.py` 전체 (`ensure_tool_request_in_strategist_payload` 호출처)
12. `Core/graph.py:184-198` `route_after_strategist` + `_executable_tool_request`
13. `Core/prompt_builders.py:225-281` `build_phase_minus_1a_prompt` Rules
14. `Core/pipeline/packets.py:805-820` `_compact_fact_cells_for_prompt` (F2 helper)
15. `Core/pipeline/plans.py` `OperationContract` (변경 X but 0차 LLM 입력)

---

## V4 §1 결재 사항 (본 발주 근거)

2026-05-06 ~ 2026-05-07 정후 결재 (메모리 [project_v4_section1_field_loop_decisions.md]):

- **결재 8**: 0_supervisor LLM 일반 흐름화. 권한 = 도구 호출/검색어 생성만. 답변 작성 / answer_mode 변경 / 사고 재판정 금지.
- **F4 비전**: -1a tool_request → 0차 이동.
- **결재 4-5 (1)**: operation_contract schema = 현 OperationContract 그대로. F4 운영 검증 후 v2 별도.
- **결재 4-5 (2)**: -1a fallback 라우팅 = 도구 필요 시 항상 0_supervisor. -1s 회귀는 -1a 작전 자체 못 짤 때만 예외.

---

## 의문 시 행동 (AGENTS.md §2)

- `StrategistToolRequest` schema 통째 즉시 제거 욕구 → **금지**. 1주 호환 보존 (deprecated 표시만).
- `ensure_tool_request_in_strategist_payload` helper 본체 즉시 제거 욕구 → **금지**. no-op stub 보존.
- 0_supervisor LLM에 답변 작성 권한 추가 욕구 → **금지** (정후 결재 8 위반).
- 0_supervisor LLM에 answer_mode 변경 권한 추가 욕구 → **금지**.
- 0_supervisor LLM에 사고 재판정 권한 추가 욕구 → **금지**.
- `OperationContract` schema 확장 욕구 → **금지** (결재 4-5 (1): 1주 운영 후 v2).
- -1a fallback 라우팅에 -1s 회귀 신규 분기 추가 욕구 → **금지** (결재 4-5 (2): -1a structured output 실패 외 -1s 회귀 X).
- -1a 프롬프트에 도구 카드 (`ops_tool_cards`) 박는 욕구 → **금지** (도구 결정은 0차 단일 출처).
- F4 후 fact_cells_for_strategist를 -1a에서도 빼는 욕구 → **금지** (결재 4-4 (2): -1a 작전 수행 위해 fact_id 인용 필수).
- F2/F3 회귀 의심 패턴 발견 시 → **즉시 멈추고 보고**.
- V3 §2 위반 의심 패턴 발견 시 → 즉시 멈추고 보고.

---

## 작업 후 보고 형식 (정후/Claude 검수용)

```
# 발주 #F4 작업 완료 보고

## 변경 파일
- Core/pipeline/contracts.py: [전] N줄 → [후] N±M줄
  - StrategistReasoningOutput: tool_request 필드 제거
  - StrategistToolRequest: deprecated 표시 (1주 보존)
- Core/pipeline/strategy.py: [전] N줄 → [후] N±M줄
  - ensure_tool_request_in_strategist_payload 호출 3개 + 시그니처 인자 제거
- Core/nodes.py: [전] N줄 → [후] N±M줄
  - ensure_tool_request_in_strategist_payload 본체: deprecated no-op stub
- Core/prompt_builders.py: [전] N줄 → [후] N±M줄
  - build_phase_minus_1a_prompt: 옛 rule 5 제거 + 새 rule 5/6 박음
- Core/pipeline/supervisor.py: [전] N줄 → [후] N±M줄
  - strategist_output.tool_request 분기 제거
  - LLM 호출 일반 흐름화 + 시스템 프롬프트 + 입력 packet (fact_cells/what_is_missing)
- Core/graph.py: [전] N줄 → [후] N±M줄
  - route_after_strategist: 신 평시 분기 + 옛 분기 deprecated 로그

## 신설 테스트 (case N)
- tests/test_strategist_no_tool_request.py: 5 case
- tests/test_supervisor_general_flow.py: 6 case
- tests/test_graph_route_after_strategist_v2.py: 4 case

## 회귀 테스트 패치
- tests/test_strategy_projection.py: tool_request 의존 case 갱신
- tests/test_thin_controller_normalization.py: 정규화 case 갱신
- tests/test_runtime_memory_boundaries.py: surface 검증 갱신
- (기타 0_supervisor tests grep으로 찾아 갱신)

## 테스트
- N tests OK / [실패 시 상세]

## 수동 검사
- StrategistReasoningOutput.model_fields 안 'tool_request': False
- 빈 strategist_output + auditor_instruction 채움 → 0_supervisor LLM 일반 흐름 진입 확인

## grep 확인
- contracts.py StrategistReasoningOutput.tool_request grep: 0건
- strategy.py ensure_tool_request_in_strategist_payload 호출 grep: 0건
- supervisor.py strategist_output.get("tool_request" grep: 0건

## ARCH MAP purge log #73: 추가 완료

## 의문 / 발견 / V4 §1 작성 시 다룰 사항
- [있으면 작성, 없으면 "없음"]
- 특히 deprecated stub 1주 후 제거 후보로 보고:
  - StrategistToolRequest schema
  - ensure_tool_request_in_strategist_payload helper
  - _executable_tool_request helper
  - graph.py 옛 tool_request 분기
```

---

**발주 OK 여부 정후 결재 후 코덱스 작업 시작.**
