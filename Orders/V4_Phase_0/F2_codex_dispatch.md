# Codex 작업 의뢰: V4 Phase 0 F트랙 #F2

**의뢰일**: 2026-05-07
**의뢰자**: 정후 (입법부) — Claude (사법부 자문) 통역 검수 후 결재
**작업자**: Codex (행정부 실무)
**저장소**: SongRyeon_Project (master 브랜치, F1 commit `ab88e62` 이후)

---

## 작업 의뢰 핵심

**[Orders/V4_Phase_0/order_F2.md](order_F2.md) 발주서 그대로 따라 작업하라.**

요약 (3 schema 변경 + 1 helper 패치 + 5 테스트 신설):

### A. -1s 보강
- `Core/pipeline/start_gate.py:52` `_build_s_thinking_packet` → ThinkingHandoff.v1 9필드 schema (producer/recipient/goal_state/evidence_state/what_we_know/what_is_missing/next_node/next_node_reason/constraints_for_next_node)
- `Core/pipeline/contracts.py` → `ThinkingHandoff` schema 신설. `SThinkingPacket` 계열은 one-season legacy compatibility로만 유지.
- `Core/pipeline/packets.py:146` `compact_s_thinking_packet_for_prompt` → 9필드 압축 + 옛 schema fallback (마이그레이션 안전)
- `Core/nodes.py:2616` `_llm_start_gate_turn_contract` → `analysis_report: dict | None = None` 인자 추가, 프롬프트에 `[analysis_report_compact]` 블록 (compact_analysis_for_prompt role="-1s" 재사용)
- `Core/graph.py` `route_after_s_thinking` → ThinkingHandoff.v1 top-level `next_node` 우선, 옛 `routing_decision.next_node` fallback
- `Core/runtime/context_packet.py` → `s_thinking_history` 압축이 ThinkingHandoff.v1 top-level 필드를 우선 읽고 old schema fallback

### B. -1b 사실 대조 채널
- `Core/pipeline/delivery_review.py:223` `build_delivery_review_context` → `fact_cells_for_review` 필드 신규 (state.reasoning_board.fact_cells 압축본)
- `Core/pipeline/packets.py:788` `_compact_fact_cells_for_prompt` → 추출 순서 패치 (`extracted_fact` 우선) + `excerpt` 노출
- 정후 결재: `_compact_fact_cells_for_prompt`는 -1b 전용 임시 helper가 아니라 V4 공식 fact projection으로 정리. 별도 `_compact_fact_cells_for_review()` 신설 금지.
- `Core/prompt_builders.py:206` `build_delivery_review_sys_prompt` → fact_id 인용 규칙 + 새 출력 필드 명시

### C. remand_guidance schema
- `Core/pipeline/contracts.py:589` `DeliveryReview` → `reason_type` (enum 5+공) + `evidence_refs` (List[fact_id]) + `delta` (≤280) 3필드 추가
- `Core/pipeline/contracts.py` → `DELIVERY_REVIEW_REASON_TYPES` 또는 동등 상수 신설, 차후 F4/119 enum 분류도 재사용할 단일 출처
- `Core/pipeline/delivery_review.py:157` `normalize_delivery_review` → 자동 라우팅 매핑 (reason_type → remand_target, 코드 단일 출처)
- `Core/pipeline/delivery_review.py:276` `_merge_review_with_speaker_guard` → reason_type 추론 보강

### D. 테스트 5 신설
- `tests/test_thinking_handoff_v1.py` (4 case)
- `tests/test_minus_1s_analysis_input.py` (3 case)
- `tests/test_delivery_review_fact_cells.py` (4 case)
- `tests/test_delivery_review_reason_type.py` (6 case)
- `tests/test_delivery_review_hallucination_flow.py` (2 case)

목표: F1 이후 baseline **242 OK** + 신규 19 case = 예상 **261 OK**. 실제 test count는 최종 보고 기준. grep 검사 + ARCH MAP purge log #71 추가.

---

## 작업 시작 전 필수 read (AGENTS.md §3.1 + 본 발주 한정)

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (V3 §1·§2 LIVE LAW)
4. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (V4 §0 v0)
5. `ANIMA_ARCHITECTURE_MAP.md` (R 시리즈 #61~#69 + F1 #70)
6. **`Orders/V4_Phase_0/order_F2.md`** (본 발주 풀 본문)
7. `Core/pipeline/start_gate.py` 전체
8. `Core/pipeline/delivery_review.py` 전체
9. `Core/pipeline/contracts.py` (`EvidenceItem` / `FactCell` / `DeliveryReview` 정의)
10. `Core/pipeline/packets.py` (`compact_*_for_prompt` 패턴, 특히 role 분기)
11. `Core/prompt_builders.py:206` `build_delivery_review_sys_prompt`
12. `Core/nodes.py:2356-2390` `add_fact` (fact_cells deterministic 부여)
13. `tests/test_delivery_review_contract.py` (회귀 영향 확인)
14. `tests/test_midnight_r7_integration.py` (mock state 패턴 참고)

---

## 환경 안내 (Windows 11 / PowerShell)

- 인코딩: 모든 신설 파일 **UTF-8 (BOM 없음)**. `Set-Content -Encoding utf8` 명시. `Out-File` 기본 (UTF-16 LE) 금지.
- 테스트 실행: `python -B -m unittest discover -s tests`
- grep 실행: `Select-String` 또는 `rg` (ripgrep)

---

## V4 §1 결재 사항 (본 발주 근거)

2026-05-06 ~ 2026-05-07 정후 결재 (메모리 [project_v4_section1_field_loop_decisions.md] 박힘):

- **결재 4-1**: -1b = 대조관 (도구 X but 그 턴 산출물 비교 권한). 환각/누락 신고 가능.
- **결재 4-2**: F2 schema 안건 3종 (ThinkingHandoff.v1 + fact_cells compact + remand_guidance).
- **결재 4-3**: phase_3 cited_fact_ids = Phase 1 이후로 미룸.
- **결재 6**: -1s = ThinkingHandoff.v1 + analysis_report compact view 입력 권한.
- **결재 7 (참고)**: -1a 입력 축소는 F3. 본 발주는 길 닦기.

---

## 절대 금지 (발주서 §"의문 시 행동" 요약)

- ThinkingHandoff.v1 9필드 외 신규 필드 추가 **금지**
- 옛 SThinkingPacket.v1 잔존 코드 즉시 모두 제거 **금지** (1주 운영 후 별도 발주)
- `state.s_thinking_packet` 키 rename **금지** (V4 §1 헌법 일괄)
- DeliveryReview에 `delivery_style` reason_type 추가 **금지** (어조는 phase_3 책임)
- -1b 입력에 reasoning_board **통째** 추가 **금지** (fact_cells 압축본만)
- LLM이 박은 `remand_target` 그대로 보존 **금지** (reason_type enum이면 코드가 자동 매핑이 단일 출처)
- analysis_report compact view를 -1s 외 노드에 박는 욕구 **금지**
- `Core/nodes.py:2623` `del working_memory` 제거 **금지** (별도 X2 발주)
- 자동 라우팅에 `severity` 분기 추가 **금지** (보류 9 Phase 1)
- 본 발주 외 추가 refactor/cleanup **금지**
- V3 §2 절대 금지 24개 위반 의심 패턴 발견 시 즉시 멈추고 보고

---

## 작업 후 보고

발주서 §"작업 후 보고 형식" 그대로. 정후/Claude 검수 대기.

의문 발생 시 작업 멈추고 정후/Claude에 질의 (AGENTS.md §2).
