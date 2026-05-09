# Codex 작업 의뢰: V4 Phase 0 F트랙 #F3

**의뢰일**: 2026-05-07
**의뢰자**: 정후 (입법부) — Claude (사법부 자문) 통역 검수 후 결재
**작업자**: Codex (행정부 실무)
**저장소**: SongRyeon_Project (master 브랜치, F2 working tree 위에서 진행)

---

## 작업 의뢰 핵심

**[Orders/V4_Phase_0/order_F3.md](order_F3.md) 발주서 그대로 따라 작업하라.**

요약 (-1a 입력 4개 제거 + 1개 신설 + tactical_briefing 채널 이동):

### A. -1a 입력 축소 (결재 7 본체)
- `Core/pipeline/strategy.py:109` `project_state_for_strategist` → `analysis_report` / `raw_read_report` / `reasoning_board` / `tactical_briefing` 4개 키 **제거**, `fact_cells_for_strategist` (V4 5필드 compact, F2 helper 재사용) **신설**
- `Core/pipeline/strategy.py:139` `run_base_phase_minus_1a_thinker` → `analysis_data` 의존성 제거. status/evidences 분기는 ThinkingHandoff `what_we_know`/`what_is_missing` + `fact_cells_for_strategist` len으로 변경. `build_reasoning_board_from_analysis` 호출 제거 (-1a는 board 신규 생성 권한 X). `apply_strategist_output_to_reasoning_board` 역방향 후처리는 유지.
- `Core/prompt_builders.py:225` `build_phase_minus_1a_prompt` → 인자 4개 제거 + `fact_cells_packet` 1개 신설. 본문 블록 4개 (`[tactical_briefing]` / `[analysis_report]` / `[raw_read_report]` / `[reasoning_board]`) 제거 + `[fact_cells]` 신설. Rules에 "fact 재판정 금지 + ThinkingHandoff 우선" 추가.
- `force_findings_first_delivery_strategy` helper 시그니처 갱신: `analysis_data` → `s_thinking_packet` + `fact_cells_for_strategist`.

### B. tactical_briefing 채널 이동 (-1a → -1s, 결재 4-4 (1))
- `Core/nodes.py:2617` `_llm_start_gate_turn_contract` → `tactical_briefing: str = ""` 인자 추가. 빈 string이면 블록 미생성 (F2 analysis_report 패턴 그대로).
- `Core/pipeline/start_gate.py:200` 호출처에 `state.get("tactical_briefing", "")` 인자 전파.
- system_prompt rules 8번 추가: "tactical_briefing은 advisory context only — 도구 호출 금지, 컨트랙트 goal로 복사 금지, 사용자 의도 덮어쓰기 금지."
- state 키 / `recent_tactical_briefing` 어댑터 / state schema는 그대로 유지 (V4 §1 헌법 일괄 rename 안건).

### C. fact_cells helper 재사용
- `Core/pipeline/packets.py:805` `_compact_fact_cells_for_prompt` (F2에서 박은 V4 5필드 fact_id/extracted_fact/source_id/source_type/excerpt) **변경 X**, -1a 호출 시 동일 helper 재사용. 빈 list 정상 처리.

### D. 테스트 4 신설 + 3 회귀 패치
- 신설:
  - `tests/test_strategist_input_surface.py` (6 case)
  - `tests/test_strategist_prompt_blocks.py` (5 case)
  - `tests/test_minus_1s_tactical_briefing.py` (3 case)
  - `tests/test_strategist_thinking_handoff_integration.py` (3 case)
- 회귀 패치:
  - `tests/test_strategy_projection.py`
  - `tests/test_thin_controller_normalization.py`
  - `tests/test_runtime_memory_boundaries.py`

목표: F2 baseline 261 + 신규 17 = 예상 **278 OK**. 실제 test count는 최종 보고. grep 검사 + ARCH MAP purge log #72 추가.

---

## 작업 시작 전 필수 read

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (V3 §1·§2 LIVE LAW)
4. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (V4 §0 v0)
5. `ANIMA_ARCHITECTURE_MAP.md` (R 시리즈 #61~#69 + F1 #70 + F2 #71)
6. **`Orders/V4_Phase_0/order_F3.md`** (본 발주 풀 본문)
7. **`Orders/V4_Phase_0/order_F2.md`** (선행 — ThinkingHandoff/fact_cells_for_review/DeliveryReview.reason_type 의존성)
8. `Core/pipeline/strategy.py` 전체
9. `Core/prompt_builders.py:225-281` `build_phase_minus_1a_prompt`
10. `Core/nodes.py:2617-2685` `_llm_start_gate_turn_contract` (F2 패치본)
11. `Core/pipeline/start_gate.py` 전체
12. `Core/pipeline/packets.py:805-820` `_compact_fact_cells_for_prompt` (F2 helper)
13. `Core/pipeline/contracts.py:258-300` `ThinkingHandoff` schema (F2)
14. `tests/test_strategy_projection.py` / `test_thin_controller_normalization.py` / `test_runtime_memory_boundaries.py`

---

## 환경 안내 (Windows 11 / PowerShell)

- 인코딩: 모든 신설 파일 **UTF-8 (BOM 없음)**. `Set-Content -Encoding utf8` 명시. `Out-File` 기본 (UTF-16 LE) 금지.
- 테스트 실행: `python -B -m unittest discover -s tests`
- grep 실행: `Select-String` 또는 `rg` (ripgrep)
- F2 working tree 상태에서 작업 진행. F2 commit은 본 발주와 평행 (정후 결재 후).

---

## V4 §1 결재 사항 (본 발주 근거)

2026-05-06 ~ 2026-05-07 정후 결재 (메모리 [project_v4_section1_field_loop_decisions.md]):

- **결재 7**: -1a 직접 입력에서 analysis_report/raw_read_report/reasoning_board 제거. ThinkingHandoff만 read. 사실 재판정 권한 = -1s.
- **결재 4-4 (1)**: tactical_briefing 채널 이동 (-1a → -1s). advisory = 사고 종합용.
- **결재 4-4 (2)**: -1a fact_id 인용 채널. fact_cells compact view 따로 박음. "작전 수행 능력 향상 위해 fact_id 숙지 필수".
- **결재 4-4 (3)**: F2 1 turn 가동 검증 X, 바로 F3. F2 commit 평행.

---

## 절대 금지 (발주서 §"의문 시 행동" 요약)

- -1a 입력에서 빠지는 4개 외 다른 surface 같이 축소 (war_room/working_memory 등) **금지** — 보류 6 별도
- `apply_strategist_output_to_reasoning_board` 역방향 채널 폐기 **금지** — V4 §1 작성 시 결재
- `_compact_fact_cells_for_prompt` schema 변경 **금지** — F2 V4 5필드 단일 출처
- `state.tactical_briefing` 키 rename **금지** — V4 §1 일괄
- `_llm_start_gate_turn_contract` 외 다른 노드에 tactical_briefing 박기 **금지** — 본 발주는 -1s만
- `analysis_report` / `reasoning_board` 본체 폐기 **금지** — state에 살아있음, -1a만 read 권한 X
- 본 발주 외 추가 refactor/cleanup **금지**
- **F2 회귀 의심 패턴 발견 시 즉시 멈추고 보고**
- V3 §2 절대 금지 24개 위반 의심 패턴 발견 시 즉시 멈추고 보고

---

## 작업 후 보고

발주서 §"작업 후 보고 형식" 그대로. 정후/Claude 검수 대기.

의문 발생 시 작업 멈추고 정후/Claude에 질의 (AGENTS.md §2).
