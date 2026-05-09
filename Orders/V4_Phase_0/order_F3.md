# 발주 #F3 — -1a 입력 축소 + tactical_briefing 채널 이동 + -1a fact_id 인용 채널

**발주일**: 2026-05-07
**트랙**: V4 Phase 0 / **F 트랙 #F3** ("다음 큰 수술 2단계", 결재 7 본체)
**선행**: F2 완료 (working tree, ThinkingHandoff.v1 9필드 + fact_cells_for_review + DeliveryReview reason_type/evidence_refs/delta). F2 commit은 본 발주와 평행 진행.
**의존성**: 없음. F4 (0차 LLM 격상)와 분리. **단 F2 회귀 의심 패턴 발견 시 즉시 멈추고 보고**.

---

## Why

V4 §1 권한표 결재 핵심:
- **결재 7 (2026-05-06 박힘)**: -1a strategist 직접 입력에서 `analysis_report` / `raw_read_report` / `reasoning_board` 제거. -1a는 -1s가 만든 ThinkingHandoff만 보고 실행계획/도구계약 작성. 사실 재판정 권한 = -1s로 완전 이동.
- **결재 4-4 (1) (2026-05-07 박힘)**: tactical_briefing 채널 이동 (-1a → -1s). advisory는 사고 종합용이라 -1s가 봐야. -1a는 실행계획만.
- **결재 4-4 (2) (2026-05-07 박힘)**: -1a 입력에서 reasoning_board 통째 빠지지만, fact_cells compact view (F2 박은 V4 5필드 helper)는 따로 박음. 정후 비전 = "-1a 작전 수행 능력 향상 위해 fact_id 숙지 필수".

**F2가 길 닦았음**: ThinkingHandoff.v1 9필드 + analysis_report compact view -1s 입력 권한 + fact_cells V4 5필드 projection. 이제 F3에서 -1a 입력 잘라내고 ThinkingHandoff + fact_cells 두 채널로 좁힌다.

현 상태 (2026-05-07 verify):

- `Core/pipeline/strategy.py:109` `project_state_for_strategist` = 21개 surface, **`analysis_report` / `raw_read_report` / `reasoning_board` / `tactical_briefing` 다 박혀있음** ([:118-127](Core/pipeline/strategy.py#L118-L127)).
- `Core/pipeline/strategy.py:139` `run_base_phase_minus_1a_thinker`:
  - `analysis_data.get("investigation_status")` status 분기 ([:169](Core/pipeline/strategy.py#L169))
  - `analysis_data.get("evidences")` count 분기 ([:170](Core/pipeline/strategy.py#L170))
  - `build_reasoning_board_from_analysis(projected_state, analysis_data)` board 생성 fallback ([:173](Core/pipeline/strategy.py#L173))
  - 4 packet 생성: `analysis_packet` / `working_memory_packet` / `reasoning_board_packet` / `raw_read_packet` ([:187-191](Core/pipeline/strategy.py#L187-L191))
- `Core/prompt_builders.py:225` `build_phase_minus_1a_prompt` = 인자 16개, 본문 블록 14개 (`[tactical_briefing]` / `[analysis_report]` / `[raw_read_report]` / `[reasoning_board]` 모두 박힘).
- `Core/nodes.py:2617` `_llm_start_gate_turn_contract` = F2에서 `analysis_report` 인자 추가됨. **`tactical_briefing` 인자 없음** → 결재 4-4 (1) 처리하려면 시그니처 확장 필요.
- `Core/pipeline/start_gate.py:200` 호출처에서 `state.get("analysis_report")` 전달 추가됨 (F2). `state.get("tactical_briefing")` 전달 추가 필요.

V4 §1 §2 본문 박기 직전. -1s/-1a 권한 분리의 코드 정합 마지막 큰 수술.

---

## 스코프

본 발주 = **-1a 입력 surface 4개 제거 + 1개 신설 + tactical_briefing 채널 이동 + 프롬프트 빌더 갱신 + 본체 분기 갱신 + 테스트**. F4는 별도.

### A. -1a 입력 축소 (결재 7 본체)

A-1. **`project_state_for_strategist` 갱신** ([Core/pipeline/strategy.py:109](Core/pipeline/strategy.py#L109)):
- **삭제**: `analysis_report` / `raw_read_report` / `reasoning_board` / `tactical_briefing` (4개 키 + 그 호출 helper `_project_analysis_report` / `_project_reasoning_board` / `_project_raw_read_report`).
- **신설**: `fact_cells_for_strategist` (List[dict])
  - 출처: `state.get("reasoning_board", {}).get("fact_cells", [])`
  - 압축: `_compact_fact_cells_for_prompt(values, limit=10)` ([Core/pipeline/packets.py:805](Core/pipeline/packets.py#L805) F2 박은 V4 정식 5필드 helper 재사용).
- **유지** (보류 6 별도 안건): `working_memory` / `war_room` / `start_gate_review` / `start_gate_switches` / `s_thinking_packet` / `tool_carryover` / `evidence_ledger` / 기타 사용자 환경 packet (`user_state` / `user_char` / `songryeon_thoughts` / `biolink_status` / `time_gap` / `global_tolerance` / `self_correction_memo` / `strategist_goal`).
- **`s_thinking_packet`은 핵심 입력으로 격상**: 옛 단순 인용 → 사실/사고 단일 출처. compact_s_thinking_packet_for_prompt(role="strategist") 그대로 사용 (F2 박힌 9필드 압축본).

A-2. **`run_base_phase_minus_1a_thinker` 본체 갱신** ([Core/pipeline/strategy.py:139](Core/pipeline/strategy.py#L139)):
- **`analysis_data` 의존성 제거**:
  - `status = str(analysis_data.get("investigation_status") or "").upper()` → ThinkingHandoff `evidence_state` 텍스트에서 추론. 안전한 변환 = "INCOMPLETE" if `s_thinking_packet.what_we_know` 비어있고 `what_is_missing`이 있으면, 그 외 빈 string.
  - `evidences = analysis_data.get("evidences", [])` → `fact_cells_for_strategist` (compact 5필드 list)로 대체. count 비교만 하는 곳은 `len(fact_cells_for_strategist)`로.
  - `build_reasoning_board_from_analysis(projected_state, analysis_data)` 호출 ([:173](Core/pipeline/strategy.py#L173)) **제거**: -1a는 reasoning_board 신규 생성 권한 X. `state.get("reasoning_board", {})` 그대로 사용 (외부에서 들어옴, 2b가 채움).
  - `apply_strategist_output_to_reasoning_board(reasoning_board, strategist_payload)` 호출 ([:271](Core/pipeline/strategy.py#L271)) **유지**: -1a 출력 → board 후처리 (방향 reverse). board 직접 read 권한과 무관.
- **fallback 분기 갱신** ([:200](Core/pipeline/strategy.py#L200)):
  - 옛: `if not evidences and status in {"", "INCOMPLETE"}`
  - 신: `if not fact_cells_for_strategist and not str(s_thinking_packet.get("what_we_know") or "").strip()` (또는 동등한 ThinkingHandoff 기반 판정).
  - `fallback_strategist_output(...)` 호출 시 `analysis_data` 인자 → `s_thinking_packet` + `fact_cells_for_strategist` 기반으로 변경. helper 시그니처도 같이 갱신.
- **packet 변수 정리**:
  - `analysis_packet` / `reasoning_board_packet` / `raw_read_packet` 생성 코드 제거.
  - 새 `fact_cells_packet = json.dumps(projected_state.get("fact_cells_for_strategist", []), ensure_ascii=False, indent=2)`.
- **`force_findings_first_delivery_strategy(response_strategy, analysis_data, user_input)` 호출** ([:214](Core/pipeline/strategy.py#L214) / [:289](Core/pipeline/strategy.py#L289)):
  - `analysis_data` 인자가 빠지면 helper 동작 변경 필요. 옵션 (a) helper 시그니처 변경 — `s_thinking_packet`과 `fact_cells_for_strategist`로 동일 결정 추출. 옵션 (b) helper 호출 자체 제거 (강한 결재 필요). **옵션 (a) 채택**: 시그니처 변경. `s_thinking_packet.what_we_know` + `fact_cells_for_strategist`로 findings 추출.

A-3. **`build_phase_minus_1a_prompt` 갱신** ([Core/prompt_builders.py:225](Core/prompt_builders.py#L225)):
- **인자 제거** (4개): `tactical_briefing` / `analysis_packet` / `raw_read_packet` / `reasoning_board_packet`.
- **인자 신설** (1개): `fact_cells_packet: str` (json string).
- **본문 블록 제거** (4개): `[tactical_briefing]` / `[analysis_report]` / `[raw_read_report]` / `[reasoning_board]`.
- **본문 블록 신설** (1개): `[fact_cells]\n{fact_cells_packet}\n\n` ([s_thinking_packet] 직후 위치 — 권한표 흐름상 -1s 사고 → fact_id 인용 채널 순).
- **Rules 갱신**:
  - 기존 rule 1: "Build goals in this order: goal_contract -> strategist_goal -> action_plan." 유지.
  - 기존 rule 2/3 갱신: "may contain only phase_2 evidences" → "may contain only fact_cells (cite fact_id) or current-turn facts already admitted by answer_mode_policy".
  - 새 rule 추가: "Use s_thinking_packet (ThinkingHandoff.v1) what_we_know/what_is_missing as the primary case state. fact_cells exist for fact_id citation when planning a tool query or evidence anchor."
  - 새 rule 추가: "Do not re-judge facts the start gate has not surfaced through s_thinking_packet or fact_cells. Fact judgment authority belongs to -1s."

### B. tactical_briefing 채널 이동 (-1a → -1s)

B-1. **`_llm_start_gate_turn_contract` 시그니처 확장** ([Core/nodes.py:2617](Core/nodes.py#L2617)):
- 새 인자: `tactical_briefing: str = ""` (optional, 후방 호환).
- F2 패턴 그대로 (analysis_report 인자처럼): 빈 string이면 프롬프트에 블록 미생성 (토큰 다이어트), 비어있지 않으면 `[tactical_briefing]\n{tactical_briefing}` 블록 박음 (system_prompt 또는 human_prompt 적정 위치).
- 위치 권장: human_prompt의 `[recent_context_excerpt]` 직후 (advisory 컨텍스트는 user 측 정보 흐름).

B-2. **`run_phase_minus_1s_start_gate` 호출처 갱신** ([Core/pipeline/start_gate.py:200](Core/pipeline/start_gate.py#L200)):
- `_llm_start_gate_turn_contract(... )` 호출에 `state.get("tactical_briefing", "")` 인자 추가.

B-3. **시스템 프롬프트 규칙 추가**:
- `_llm_start_gate_turn_contract` system_prompt rules에 추가 (기존 rule 1~7 다음 8번):
  - "If tactical_briefing contains active DreamHint advisories, treat them as advisory context only — do not let them override the user's current-turn meaning, do not propose tool calls, and do not copy briefing text into the contract goal."

B-4. **state 키 / `recent_tactical_briefing` 어댑터 / state schema는 그대로 유지** (rename 금지, V4 §1 헌법 일괄):
- `Core/state.py:19`/`82`/`141`/`213`/`228` `tactical_briefing` 키 유지.
- `Core/adapters/night_queries.py:113` `recent_tactical_briefing` 함수 유지.
- `Core/runtime/context_packet.py:282` `tactical_briefing` 클립 유지.

### C. `_compact_fact_cells_for_prompt` strategist 호출 안전성

C-1. **F2에서 박은 V4 5필드 schema 확인 ([Core/pipeline/packets.py:805-820](Core/pipeline/packets.py#L805-L820))**: fact_id / extracted_fact / source_id / source_type / excerpt. 본 발주 변경 X. -1a 호출 시 동일 helper 재사용.

C-2. **빈 fact_cells 시 처리**: 결재 4-4 (2)에서 fact_cells 인용은 작전 능력 향상 채널. **빈 list 자체는 정상 상태** (검증된 사실 0건). fallback 분기에서 fact_cells가 비어있으면 "검증된 사실 0건" 메시지를 ThinkingHandoff `what_is_missing`에서 추출해서 -1a 작전에 반영.

### D. 검증 (테스트)

D-1. **신설 단위 테스트** `tests/test_strategist_input_surface.py` (case 6):
1. `project_state_for_strategist` 출력 keys에 `analysis_report` / `raw_read_report` / `reasoning_board` / `tactical_briefing` **없음**.
2. `project_state_for_strategist` 출력 keys에 `fact_cells_for_strategist` **있음** + 5필드 (fact_id/extracted_fact/source_id/source_type/excerpt) 보존.
3. 빈 `state.reasoning_board` 입력 시 `fact_cells_for_strategist = []`.
4. `state.reasoning_board.fact_cells` 11개 입력 시 `len(fact_cells_for_strategist) == 10` (limit).
5. F2에서 박은 `s_thinking_packet` 압축본이 strategist projection에 포함됨 (compact_s_thinking_packet_for_prompt(role="strategist") 결과).
6. 후방 호환: 옛 `state.reasoning_board.fact_cells[].claim` (V3 흔적) 키만 있는 fact도 `_compact_fact_cells_for_prompt`가 fallback으로 잡음 (F2 패치 검증 재확인).

D-2. **신설 단위 테스트** `tests/test_strategist_prompt_blocks.py` (case 5):
1. `build_phase_minus_1a_prompt` 호출 시 `[tactical_briefing]` / `[analysis_report]` / `[raw_read_report]` / `[reasoning_board]` 블록 4개 모두 **없음**.
2. `[fact_cells]` 블록 **있음** + JSON 본문 박힘.
3. `[s_thinking_packet]` 블록 유지.
4. 새 rule (fact 재판정 금지 + ThinkingHandoff 우선) 본문 포함.
5. 후방 호환: 옛 시그니처 인자 (`tactical_briefing` 등)로 호출하면 TypeError 발생 (시그니처 변경 정합성 검증).

D-3. **신설 단위 테스트** `tests/test_minus_1s_tactical_briefing.py` (case 3):
1. 빈 `tactical_briefing` 인자로 `_llm_start_gate_turn_contract` 호출 → human_prompt에 `[tactical_briefing]` 블록 미생성.
2. 비어있지 않은 `tactical_briefing` 인자 전달 → human_prompt에 박힘.
3. 후방 호환: `tactical_briefing` 인자 없이 호출해도 정상 동작 (default `""`).

D-4. **신설 통합 테스트** `tests/test_strategist_thinking_handoff_integration.py` (case 3):
1. ThinkingHandoff.v1 + fact_cells_for_strategist 입력으로 -1a 호출 → strategist_output.action_plan 정상 생성. action_plan 또는 response_strategy.must_include_facts 안에 fact_id 인용 가능 (mock LLM).
2. ThinkingHandoff `what_we_know` 비어있고 fact_cells도 0건 → fallback 분기 진입 (옛 `not evidences and status in {"", "INCOMPLETE"}` 동등).
3. -1a 출력의 `apply_strategist_output_to_reasoning_board` 후처리는 그대로 동작 (역방향 채널 보존).

D-5. **회귀 테스트 패치**:
- `tests/test_strategy_projection.py` (F2에서 이미 modified) — F3에서 키 4개 삭제 + 1개 신설 반영해서 다시 갱신.
- `tests/test_thin_controller_normalization.py` (F2에서 이미 modified) — analysis_report/reasoning_board 의존 case가 있으면 ThinkingHandoff 기반으로 갱신.
- `tests/test_runtime_memory_boundaries.py` (F2 modified) — 키 surface 검증 case가 있으면 갱신.

D-6. **자동 검사**: `python -B -m unittest discover -s tests` → F2 baseline 261 + 신규 17 = **278 OK** (정확한 case 수는 작업 후 보고).

---

## 안 하는 것 (다음 발주)

- **F4 (0차 LLM 격상)**: tool_request 생성 권한 -1a → 0_supervisor 이동. F3 후 발주.
- **보류 6 (-1a 입력의 다른 surface 축소)**: war_room / evidence_ledger / working_memory / start_gate_review 등. 별도 결재 후. 본 발주는 결재 7 + 4-4 (1)(2) 범위만.
- **`apply_strategist_output_to_reasoning_board` 역방향 채널 폐기**: -1a 출력이 board에 반영되는 경로는 본 발주 범위 X. board read 권한과 write 권한 분리, write는 후처리 보조라 V4 §1 작성 시 함께 결재.
- **`force_findings_first_delivery_strategy` helper 폐기**: 시그니처만 갱신, helper 자체는 1주 운영 후 별도 검토.
- **노드명 rename / state 키 rename**: V4 §1 헌법 작성 시 일괄 (결재 5).
- **working_memory → -1s 입력** (보류 1, X2 발주): 본 발주 범위 X.
- **옛 SThinkingPacket.v1 fallback 분기 제거**: F2 발주에 박힌 1주 후 제거 안건. 본 발주 범위 X.

---

## 변경 대상 (코드 좌표)

### 변경
- `Core/pipeline/strategy.py` ([:53-83](Core/pipeline/strategy.py#L53-L83) 4 helper 제거 / [:109-136](Core/pipeline/strategy.py#L109-L136) `project_state_for_strategist` surface 갱신 / [:139-305](Core/pipeline/strategy.py#L139-L305) `run_base_phase_minus_1a_thinker` 본체 분기 갱신)
- `Core/prompt_builders.py` ([:225-281](Core/prompt_builders.py#L225-L281) `build_phase_minus_1a_prompt` 시그니처 + 본문 + Rules)
- `Core/nodes.py` ([:2617](Core/nodes.py#L2617) `_llm_start_gate_turn_contract` 시그니처 + 프롬프트)
- `Core/pipeline/start_gate.py` ([:200-206](Core/pipeline/start_gate.py#L200-L206) 호출처 tactical_briefing 인자 전파)
- `force_findings_first_delivery_strategy` 시그니처 (analysis_data → s_thinking_packet + fact_cells_for_strategist) — 위치는 nodes.py 안 helper, Codex가 grep으로 찾아서 같이 갱신.

### 신설
- `tests/test_strategist_input_surface.py` (case 6)
- `tests/test_strategist_prompt_blocks.py` (case 5)
- `tests/test_minus_1s_tactical_briefing.py` (case 3)
- `tests/test_strategist_thinking_handoff_integration.py` (case 3)

### 변경 없음 (확인만)
- `Core/state.py` (state schema 그대로 — `tactical_briefing` 키 유지, V4 §1 헌법 일괄 rename 안건).
- `Core/adapters/night_queries.py` (`recent_tactical_briefing` 어댑터 — F1 박힘, 변경 X).
- `Core/runtime/context_packet.py` (`tactical_briefing` 클립 — 변경 X).
- `Core/graph.py` (라우팅 그대로, F2 박힌 ThinkingHandoff top-level next_node 우선 그대로).
- `Core/pipeline/contracts.py` (F2 박힌 ThinkingHandoff/DeliveryReview schema 변경 X).
- `Core/pipeline/delivery_review.py` (F2 박힌 fact_cells_for_review/reason_type 변경 X).
- `Core/pipeline/packets.py` (F2 박힌 `_compact_fact_cells_for_prompt` 5필드 그대로 재사용).

---

## 헌법 정합

- **V4 §0 v0 위반 X**: 본 발주는 §1 권한표 본문 박기의 마지막 인프라 (-1s 사실/사고 권한 + -1a 실행계획 권한 분리).
- **V3 §2 절대 금지 24개 위반 X**: 도구 호출 권한 변경 X (F4 안건). LLM 사고 규칙 변경 X. -1a 입력 축소만.
- **AGENTS.md §3.3 대형 nodes.py 수술 게이트 트리거**: `_llm_start_gate_turn_contract` 시그니처 1개 인자 추가 + `force_findings_first_delivery_strategy` 시그니처 변경. 인벤토리 분류/일괄 이동 X. 게이트 트리거 X. 단 작업 시작 전 정후 결재 받음.
- **AGENTS.md §1 인코딩**: 신설 테스트 파일 모두 UTF-8 (BOM 없음). PowerShell 사용 시 `-Encoding utf8` 명시.
- **메모리 결재 7 + 4-4 (1)(2)(3)** 그대로 반영. 자의 해석 X.

---

## 검증 기준

1. **자동 검사**: `python -B -m unittest discover -s tests` → 261 + 17 신규 = **278 OK** (정확한 case 수 발주 후 보고).
2. **수동 검사 (Codex 직접 verify)**:
   - `python -c "from Core.pipeline.strategy import project_state_for_strategist; print(set(project_state_for_strategist({}).keys()))"` → `analysis_report` / `raw_read_report` / `reasoning_board` / `tactical_briefing` 4개 키 **없음**, `fact_cells_for_strategist` **있음**.
   - 빈 state로 `_llm_start_gate_turn_contract(...)` 호출 (analysis_report+tactical_briefing 모두 빈 string) → 프롬프트에 두 블록 모두 미생성.
3. **purge log 추가**: `ANIMA_ARCHITECTURE_MAP.md` #72 추가.
   - 마커: "**V4 Phase 0 F트랙 #F3: -1a 입력 축소 + tactical_briefing 채널 이동 + -1a fact_id 인용 채널**"
   - 변경 줄 수, 신설 테스트 4개, 시그니처 변경 명시.
4. **grep 확인**:
   - `Core/pipeline/strategy.py` 안 `analysis_data` / `raw_read_report` / `reasoning_board_packet` / `tactical_briefing` grep 분기 — 모두 0건 (단 `apply_strategist_output_to_reasoning_board` 호출은 보존, 그건 역방향).
   - `Core/prompt_builders.py:build_phase_minus_1a_prompt` 본문 안 `[analysis_report]` / `[raw_read_report]` / `[reasoning_board]` / `[tactical_briefing]` grep — 모두 0건.
   - `Core/nodes.py:_llm_start_gate_turn_contract` 시그니처 안 `tactical_briefing` grep — 1건.

---

## 롤백

- `git checkout 782a982 -- Core/pipeline/strategy.py Core/prompt_builders.py Core/nodes.py Core/pipeline/start_gate.py` 단일 커밋 복원 가능 (단 F2 변경분이 아직 commit 안 된 상태라면 working tree 보존 위해 stash 사용).
- 신설 테스트 파일 삭제 가능.
- F2 회귀 의심 발생 시 우선 F2 commit 복원 → F3 다시 진행.

---

## 코덱스가 발주 받기 전 읽어야 할 문서

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (V3 §1·§2 LIVE LAW)
4. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (V4 §0 v0)
5. `ANIMA_ARCHITECTURE_MAP.md` (R 시리즈 #61~#69 + F1 #70 + F2 #71)
6. **`Orders/V4_Phase_0/order_F3.md`** (본 발주 풀 본문)
7. `Orders/V4_Phase_0/order_F2.md` (선행 발주 — ThinkingHandoff.v1 / fact_cells_for_review / DeliveryReview.reason_type 의존성 확인)
8. `Core/pipeline/strategy.py` 전체 (`project_state_for_strategist` + `run_base_phase_minus_1a_thinker`)
9. `Core/prompt_builders.py:225-281` `build_phase_minus_1a_prompt` 전체
10. `Core/nodes.py:2617-2685` `_llm_start_gate_turn_contract` (F2 패치본)
11. `Core/pipeline/start_gate.py` 전체 (호출처 + ThinkingHandoff.v1 9필드 emit)
12. `Core/pipeline/packets.py:805-820` `_compact_fact_cells_for_prompt` (F2 박은 V4 5필드 helper)
13. `Core/pipeline/contracts.py:258-300` `ThinkingHandoff` schema (F2 박힘)
14. `tests/test_strategy_projection.py` / `tests/test_thin_controller_normalization.py` / `tests/test_runtime_memory_boundaries.py` (F2 modified, 본 발주에서 추가 갱신 가능성)

---

## V4 §1 결재 사항 (본 발주 근거)

2026-05-06 ~ 2026-05-07 정후 결재 (메모리 [project_v4_section1_field_loop_decisions.md]):

- **결재 7**: -1a 직접 입력에서 analysis_report/raw_read_report/reasoning_board 제거. -1a는 ThinkingHandoff만 read. 사실 재판정 권한 = -1s.
- **결재 4-4 (1)**: tactical_briefing 채널 이동 (-1a → -1s). advisory는 사고 종합용.
- **결재 4-4 (2)**: -1a fact_id 인용 채널 채택. reasoning_board 통째 X but fact_cells compact view 따로 박음. "-1a 작전 수행 능력 향상 위해 fact_id 숙지 필수" (정후 발화).
- **결재 4-4 (3)**: F2 1 turn 가동 검증 X, 바로 F3 발주. F2 commit은 F3 발주 평행.
- **결재 8 (참고, F4 영역)**: 0_supervisor LLM 일반 흐름화 + tool_request 이동. 본 발주는 길 닦기.

---

## 의문 시 행동 (AGENTS.md §2)

- -1a 입력에서 빠지는 4개 키 외 다른 surface 같이 축소 욕구 (예: war_room, working_memory) → **금지** (보류 6 별도 안건).
- `apply_strategist_output_to_reasoning_board` 역방향 채널 같이 폐기 욕구 → **금지** (V4 §1 작성 시 결재).
- `_compact_fact_cells_for_prompt` schema 변경 욕구 → **금지** (F2에서 박힌 V4 5필드 단일 출처).
- `state.tactical_briefing` 키 rename 욕구 → **금지** (V4 §1 일괄).
- `_llm_start_gate_turn_contract` 외 다른 노드 LLM 호출에 tactical_briefing 박는 욕구 → **금지** (본 발주는 -1s만).
- `analysis_report` / `reasoning_board` 본체 폐기 욕구 → **금지**. 두 객체는 state에 그대로 살아있고 (-1s가 read, 2b가 write), -1a만 직접 read 권한 빼는 것.
- F2 회귀 의심 패턴 발견 시 → **즉시 멈추고 보고**. F2 commit 결재 받은 후 재개.
- V3 §2 위반 의심 패턴 발견 시 → 즉시 멈추고 보고.

---

## 작업 후 보고 형식 (정후/Claude 검수용)

```
# 발주 #F3 작업 완료 보고

## 변경 파일
- Core/pipeline/strategy.py: [전] N줄 → [후] N±M줄
  - project_state_for_strategist: surface 키 4개 제거 + fact_cells_for_strategist 신설
  - run_base_phase_minus_1a_thinker: analysis_data 의존성 제거 + ThinkingHandoff/fact_cells 기반 분기
  - 4 helper 제거 (_project_analysis_report / _project_raw_read_report / _project_reasoning_board)
- Core/prompt_builders.py: [전] N줄 → [후] N±M줄
  - build_phase_minus_1a_prompt: 인자 4개 제거 + 1개 신설, 본문 블록 4개 제거 + 1개 신설, Rules 갱신
- Core/nodes.py: [전] N줄 → [후] N±M줄
  - _llm_start_gate_turn_contract: tactical_briefing 인자 + 프롬프트 블록
  - force_findings_first_delivery_strategy: 시그니처 갱신
- Core/pipeline/start_gate.py: [전] N줄 → [후] N±M줄
  - run_phase_minus_1s_start_gate: tactical_briefing 인자 전파

## 신설 테스트 (case N)
- tests/test_strategist_input_surface.py: 6 case
- tests/test_strategist_prompt_blocks.py: 5 case
- tests/test_minus_1s_tactical_briefing.py: 3 case
- tests/test_strategist_thinking_handoff_integration.py: 3 case

## 회귀 테스트 패치
- tests/test_strategy_projection.py: 키 surface 갱신
- tests/test_thin_controller_normalization.py: ThinkingHandoff 기반 분기 갱신
- tests/test_runtime_memory_boundaries.py: 키 surface 검증 갱신

## 테스트
- N tests OK / [실패 시 상세]

## 수동 검사
- project_state_for_strategist keys: [첨부]
- _llm_start_gate_turn_contract empty inputs prompt: [첨부]

## grep 확인
- strategy.py analysis_data/reasoning_board_packet grep: 0건 (역방향 apply_strategist_output_to_reasoning_board 제외)
- prompt_builders.py [analysis_report]/[raw_read_report]/[reasoning_board]/[tactical_briefing] grep: 0건
- nodes.py _llm_start_gate_turn_contract tactical_briefing grep: 1건

## ARCH MAP purge log #72: 추가 완료

## 의문 / 발견 / V4 §1 작성 시 다룰 사항
- [있으면 작성, 없으면 "없음"]
- 특히 force_findings_first_delivery_strategy helper 1주 후 폐기 후보로 보고
```

---

**발주 OK 여부 정후 결재 후 코덱스 작업 시작.**
