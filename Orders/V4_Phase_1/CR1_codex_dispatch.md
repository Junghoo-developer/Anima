# Codex 작업 의뢰: V4 Phase 1 CR 트랙 #CR1

**의뢰일**: 2026-05-09
**의뢰자**: 정후 (입법부) — Claude (사법부 자문) 통역 검수 후 결재
**작업자**: Codex (행정부 실무)
**저장소**: SongRyeon_Project (master 브랜치, V4 §1-A LIVE commit `556bbd0` 직후)

---

## 작업 의뢰 핵심

**[Orders/V4_Phase_1/order_CR1.md](order_CR1.md) 발주서 그대로 따라 작업하라.**

요약 (3 schema 변경 + graph 분기 + 프롬프트 모드 분기 + 새 모듈 1개 + 13 tests):

### A. ThinkingHandoff Literal 확장
- `Core/pipeline/contracts.py:261-272` recipient/next_node Literal에 `warroom_deliberator`, `2b_thought_critic` 추가
- `Core/pipeline/start_gate.py:178` `_handoff_next_node` 헬퍼에 새 옵션 mapping

### B. 2b 입력 schema + ThoughtCritique.v1 신설
- 2b 입력 schema에 `mode: Literal["fact_judge", "thought_critic"]` 필드 추가
- `Core/pipeline/contracts.py`에 `ThoughtCritique` schema 신설 (hallucination_risks/logic_gaps/memory_omissions/persona_errors + delta + evidence_refs)
- `CritiqueItem` sub-schema 신설 (issue + evidence_refs + severity)

### C. 2b 시스템 프롬프트 모드 분기
- `Core/prompt_builders.py` 2b builder에 `mode` 인자 추가
- thought_critic 모드 프롬프트:
  - "compare s_thinking_packet against recent_context + working_memory + fact_cells"
  - 입력 적응 자동 전환 (fact_cells > 0 → 통합 / == 0 → 기억 기반)
  - "Output ThoughtCritique.v1. Cite fact_id where possible. NO tools, NO answer text, NO fact_id 발명"

### D. -1s 시스템 프롬프트 2차 호출 rule
- `Core/prompt_builders.py` -1s builder에 `prior_thought_critique` 인자 추가
- 새 rule: "If prior_thought_critique not N/A → Step 1 검증 우선 (다시 보기) → Step 2 라우팅 (warroom vs phase_3)"

### E. graph 분기 신설
- `Core/graph.py` `_strategist_needs_thought_recursion(state)` helper 신설 (~20줄)
  - 게이트: `has_goal AND fact_cells == 0 AND no_tool_needed` (delivery_readiness 의존 제거)
- `Core/graph.py:184-198` `route_after_strategist`에 새 분기 (`_strategist_needs_thought_recursion → "2b_thought_critic"`)
- `Core/graph.py:156-181` `route_after_s_thinking`에 새 라우팅 (warroom_deliberator/2b_thought_critic)
- 새 graph 노드 등록 + 회귀 분기 (`2b_thought_critic` → `-1s_start_gate`)

### F. 새 모듈
- `Core/pipeline/thought_critic.py` 신설 (~50줄)
  - `run_2b_thought_critic_node(state, ...)` entrypoint
  - 2b LLM 호출 (mode="thought_critic", structured ThoughtCritique)
  - state에 `prior_thought_critique` 박음
  - fallback (LLM 실패 시 빈 ThoughtCritique)

### G. 테스트 13 신설
- `tests/test_2b_thought_critic.py` (4 case)
- `tests/test_thought_recursion_routing.py` (5 case)
- `tests/test_strategist_needs_thought_recursion_gate.py` (4 case)

목표: F4 baseline **294 OK** + 신규 13 case = 예상 **307 OK**. 실제 test count는 최종 보고. grep 검사 + ARCH MAP purge log #74 추가.

---

## 작업 시작 전 필수 read (AGENTS.md §3.1 + 본 발주 한정)

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` **§1-A 전체** (LIVE LAW, 본 발주의 헌법 근거)
4. **`Orders/V4_Phase_1/order_CR1.md`** (본 발주 풀 본문)
5. **`Orders/V4_Phase_0/V4_section1_decision_sheet_v3_1_2026_05_09.md`** (결재 결과 단일 출처, X6 시리즈 본체)
6. `ANIMA_ARCHITECTURE_MAP.md` (purge log #61~#73 + Phase 0→1 진입 marker)
7. `Core/pipeline/contracts.py` 전체 (ThinkingHandoff/StrategistGoal/DeliveryReview/FactCell 정의)
8. `Core/pipeline/start_gate.py` (`_build_s_thinking_packet`, `_handoff_next_node`)
9. `Core/graph.py` (route_after_s_thinking / route_after_strategist / `_strategist_no_tool_delivery_ready` / `_executable_tool_request` / `_graph_hard_stop_exceeded`)
10. `Core/prompt_builders.py` (-1s / 2b 시스템 프롬프트 builders, 정확한 함수명은 grep으로)
11. `Core/pipeline/strategy.py` (`run_base_phase_minus_1a_thinker` — 게이트 진입 시점 동작)
12. `Core/nodes.py:5140-5306` `_base_fallback_strategist_output` (게이트 trigger 동작 verify)

---

## 절대 금지 (본 발주 한정)

- ThinkingHandoff Literal에 새 옵션 추가 시 기존 `-1a/phase_3/phase_119` 분기 회귀 X.
- `_strategist_needs_thought_recursion` 게이트 조건에 `delivery_readiness` 포함 X (LLM 라벨 false negative 차단 = 정후 우려, V4 §1-A.0 명문화).
- 2b thought_critic mode에서 fact_id 발명 X (V4 §2 (d)).
- 2b thought_critic mode에서 도구 호출 X (정규식 또는 schema 차단).
- 2b thought_critic mode에서 답변 텍스트 작성 X.
- `prior_thought_critique` state 박을 때 schema 위반 X (ThoughtCritique.v1 정합).
- hard_stop 우선 (게이트 통과해도 hard_stop 시 phase_119 — 무한 회귀 차단).
- 노드명 일괄 rename은 본 발주 외 (V4 §1 통과와 함께 박는 안건이지만 별도 발주).

---

## 검증 기준

- 새 tests 13건 신규 통과 + 기존 294건 회귀 X (307 OK 목표).
- 기존 ThinkingHandoff 사용 노드 (start_gate / -1s / -1a / 0차 / -1b) 회귀 X.
- 2b fact_judge mode 동작 회귀 X (mode 인자 default fact_judge).
- 게이트 false positive 검증 (정상 케이스에서 게이트 안 탐).
- thought_critic → -1s 회귀 시 `prior_thought_critique` 정상 박힘 verify.
- hard_stop 우선순위 verify.

---

## ARCH MAP 갱신 의무

- purge log #74 추가: "CR1: 2b thought_critic mode + -1s 사고 재귀 + deterministic 게이트 + 트리오 재귀 첫 인스턴스 (V4 §0 부록 Y v1.0 anchor)".
- §1-A 통과 marker (commit `556bbd0`)와 §1-A.13 트리오 anchor 정합 명시.

---

## 결재 root

- V4 §1-A LIVE (commit `556bbd0`, 2026-05-09)
- 결재 시트 v3.1 (X6 = A/B/C/D + B 시리즈 다 박힘)
- 정후 비전 (2026-05-09): "이미 2b라는 훌룡한 비판자가 있음. 얘를 -1s 경량 CoT 중간중간에 넣으면 될 듯"
- 메모리: [project_v4_section_1_a_live.md](memory)
