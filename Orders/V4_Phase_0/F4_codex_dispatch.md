# Codex 작업 의뢰: V4 Phase 0 F트랙 #F4

**의뢰일**: 2026-05-07
**의뢰자**: 정후 (입법부) — Claude (사법부 자문) 통역 검수 후 결재
**작업자**: Codex (행정부 실무)
**저장소**: SongRyeon_Project (master 브랜치, F3 working tree 위에서 진행)

---

## 작업 의뢰 핵심

**[Orders/V4_Phase_0/order_F4.md](order_F4.md) 발주서 그대로 따라 작업하라.**

요약 (-1a tool_request 권한 제거 + 0_supervisor LLM 일반 흐름화):

### A. -1a tool_request 권한 제거 (F4 비전)
- `Core/pipeline/contracts.py:586` `StrategistReasoningOutput.tool_request` 필드 **제거**.
- `Core/pipeline/contracts.py:306` `StrategistToolRequest` schema는 **deprecated 표시 + 보존** (1주 호환).
- `Core/pipeline/strategy.py` `ensure_tool_request_in_strategist_payload` 호출 3곳 + 시그니처 인자 **제거**. helper 본체는 nodes.py grep으로 찾아 **deprecated no-op stub** (1주 호환).
- `Core/prompt_builders.py:225` `build_phase_minus_1a_prompt` Rules 갱신:
  - 옛 rule 5 ("mirror tool_request") **제거**.
  - 새 rule 5: "Do not author tool calls. Phase 0 supervisor decides exact tool name/args/queries from operation_contract."
  - 새 rule 6: "If no tool needed, set delivery_readiness=deliver_now and leave action_plan.required_tool empty."

### B. 0_supervisor LLM 일반 흐름화 (결재 8)
- `Core/pipeline/supervisor.py:44-64` `strategist_output.tool_request` 분기 **제거**.
- `Core/pipeline/supervisor.py:125-176` LLM 호출을 fallback only → **일반 흐름**으로 격상. 옛 auditor_decision/direct_message 직결 분기는 후방 호환으로 유지. LLM 3 attempts 보존.
- 시스템 프롬프트 권한 명시 박음:
  - **Authority**: 도구 결정/args/queries / 거부(no tool_calls 반환 가능 → -1b로 라우팅)
  - **Forbidden**: 답변 작성 X / answer_mode 변경 X / 사실 재판정 X / fact_id 발명 X
- 새 입력 packet:
  - `[fact_cells]` (`_compact_fact_cells_for_prompt` F2 helper 재사용, V4 5필드 fact_id/extracted_fact/source_id/source_type/excerpt)
  - `[s_thinking_packet_what_is_missing]` (ThinkingHandoff.v1 top-level + 옛 SThinkingPacket fallback)

### C. graph 라우팅 갱신
- `Core/graph.py:184` `route_after_strategist` 갱신:
  - `_strategist_no_tool_delivery_ready(state)` → `phase_3` (그대로).
  - 그 외 (도구 필요) → **항상 0_supervisor** (정후 결재 4-5 (2)).
  - 옛 "completed without an executable tool_request; returning to -1s" 사라짐. -1s 회귀는 -1a structured output 실패 시만 예외.
  - 옛 `_executable_tool_request` 분기는 **deprecated 로그 + 0_supervisor** (1주 호환).

### D. operation_contract schema = 현 그대로 (결재 4-5 (1))
- `Core/pipeline/plans.py` `OperationContract` 변경 X. F4 운영 검증 후 v2 별도 결재.

### E. 테스트 3 신설 + 회귀 패치
- 신설:
  - `tests/test_strategist_no_tool_request.py` (5 case)
  - `tests/test_supervisor_general_flow.py` (6 case)
  - `tests/test_graph_route_after_strategist_v2.py` (4 case)
- 회귀 패치:
  - `tests/test_strategy_projection.py`
  - `tests/test_thin_controller_normalization.py`
  - `tests/test_runtime_memory_boundaries.py`
  - 기타 0_supervisor tests (grep으로 찾기)

목표: F3 baseline 278 + 신규 15 = 예상 **293 OK**. 정확한 test count는 최종 보고. grep 검사 + ARCH MAP purge log #73 추가.

---

## 작업 시작 전 필수 read

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (V3 §1·§2 LIVE LAW)
4. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (V4 §0 v0)
5. `ANIMA_ARCHITECTURE_MAP.md` (R 시리즈 #61~#69 + F1 #70 + F2 #71 + F3 #72)
6. **`Orders/V4_Phase_0/order_F4.md`** (본 발주 풀 본문)
7. **`Orders/V4_Phase_0/order_F3.md`** (선행 — fact_cells_for_strategist / ThinkingHandoff.v1)
8. **`Orders/V4_Phase_0/order_F2.md`** (선행 — fact_cells_for_review / DeliveryReview / `_compact_fact_cells_for_prompt`)
9. `Core/pipeline/supervisor.py` 전체 (전면 갱신 대상)
10. `Core/pipeline/contracts.py:540-600` `StrategistReasoningOutput` + `StrategistToolRequest`
11. `Core/pipeline/strategy.py` 전체
12. `Core/graph.py:184-198` `route_after_strategist`
13. `Core/prompt_builders.py:225-281` `build_phase_minus_1a_prompt`
14. `Core/pipeline/packets.py:805-820` `_compact_fact_cells_for_prompt`
15. `Core/pipeline/plans.py` `OperationContract` (변경 X but 0차 LLM 입력)

---

## 환경 안내 (Windows 11 / PowerShell)

- 인코딩: 모든 신설 파일 **UTF-8 (BOM 없음)**. `Set-Content -Encoding utf8` 명시. `Out-File` 기본 (UTF-16 LE) 금지.
- 테스트 실행: `python -B -m unittest discover -s tests`
- grep 실행: `Select-String` 또는 `rg` (ripgrep)
- F2/F3 working tree 상태에서 작업 진행. F2/F3 commit은 본 발주와 평행 (정후 결재 후).

---

## V4 §1 결재 사항 (본 발주 근거)

2026-05-06 ~ 2026-05-07 정후 결재 (메모리 [project_v4_section1_field_loop_decisions.md]):

- **결재 8**: 0_supervisor LLM 일반 흐름화. 도구 호출/검색어 생성만. 답변/answer_mode/사고 재판정 X.
- **F4 비전**: -1a tool_request → 0차 이동. -1a 권한 = 작전 의도 (operation_contract) only.
- **결재 4-5 (1)**: operation_contract schema = 현 OperationContract 그대로. v2는 1주 운영 후.
- **결재 4-5 (2)**: -1a fallback 라우팅 = 도구 필요 시 항상 0_supervisor. -1s 회귀는 structured output 실패 예외만.

---

## 절대 금지 (발주서 §"의문 시 행동" 요약)

- `StrategistToolRequest` schema 즉시 제거 **금지** (deprecated 표시 + 1주 보존)
- `ensure_tool_request_in_strategist_payload` helper 본체 즉시 제거 **금지** (no-op stub 보존)
- 0_supervisor LLM에 답변 작성 / answer_mode 변경 / 사고 재판정 권한 추가 **금지** (정후 결재 8 위반)
- `OperationContract` schema 확장 **금지** (결재 4-5 (1))
- -1a fallback 라우팅에 -1s 회귀 신규 분기 추가 **금지** (결재 4-5 (2))
- -1a 프롬프트에 도구 카드 (`ops_tool_cards`) 박기 **금지** (도구 결정 = 0차 단일 출처)
- -1a에서 fact_cells_for_strategist 빼기 **금지** (결재 4-4 (2): 작전 위해 fact_id 인용 필수)
- 본 발주 외 추가 refactor/cleanup **금지**
- **F2/F3 회귀 의심 패턴 발견 시 즉시 멈추고 보고**
- V3 §2 절대 금지 24개 위반 의심 패턴 발견 시 즉시 멈추고 보고

---

## 작업 후 보고

발주서 §"작업 후 보고 형식" 그대로. 정후/Claude 검수 대기.

의문 발생 시 작업 멈추고 정후/Claude에 질의 (AGENTS.md §2).
