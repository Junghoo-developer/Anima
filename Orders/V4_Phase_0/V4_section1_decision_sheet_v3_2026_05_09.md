# V4 §1 본문 박기 — 단숨 결재 시트 v3 (2026-05-09 주말 단숨 모드)

**작성일**: 2026-05-09 (토)
**작성**: Claude (사법부 자문)
**결재**: 정후 (입법부)
**선행**: v2 시트 (`V4_section1_A_decision_sheet.md`, 2026-05-06) — F2/F3/F4 코드 박혀서 결재 ①~⑨가 *코드로 사실 굳어진* 상태로 갱신.
**용도**: 정후가 한 번에 도장 찍으면 §1 본문 글 작성 → §1 LIVE 박힘 → Phase 1 발주로 직진.

---

## 0. v2 → v3 갱신 사유 (1분)

| 항목 | v2 (2026-05-06) | v3 (2026-05-09) |
|---|---|---|
| F1 | 코드 commit `ab88e62` | 그대로 |
| F2 (-1s 보강 + -1b 대조) | 발주서 작성 직전 | **코드 박힘** (`6377a09` 일부) |
| F3 (-1a 입력 축소) | 발주 안건 | **코드 박힘** (`6377a09` 일부) |
| F4 (tool_request 0차 이동) | 비전 채택 | **코드 박힘** (`6377a09` 일부) |
| 294 tests OK | 231 baseline | **294 OK** (+63) |
| 보류 2, 3 | 잔존 | ✅ F2로 풀림 |
| 보류 4, 6 | 잔존 | ✅ F4로 풀림 |
| §1-A 본문 | 미작성 | **오늘 박는 대상** |
| Phase 0 → 1 게이트 | 4/4 중 1개 미충족 (V4 §1) | **§1 박히면 4/4 충족** |

**v3 결재 양**: 약 **70 항목** (도장 9 + 권한표 ~30 + fallback 6 + X 3 + V4 §2 8+α + 보류 6 + Phase 1 게이트 5 + 발주 순서). 정후 단숨 결재 가능하게 카테고리별 묶음.

---

## 1. 박힌 결재 도장 (9건, 코드 굳어진 상태 verify만)

> v2 결재 ①~⑨가 F2/F3/F4 코드로 박힘. 도장만 찍으면 §1 본문에 그대로 박힘.

| # | 결재 | 코드 verify | 결재 |
|---|---|---|---|
| ① | delivery_review = new -1b 명명 | `producer_node="-1b_delivery_review"` (delivery_review.py) ✅ | □ 박음 / □ 보류 |
| ② | -1b 위치 = phase_3 후 1자리 | `route_after_phase3 → delivery_review` (graph.py) ✅ | □ 박음 / □ 보류 |
| ③ | -1b 권한 3종 (approve/remand/sos_119) | `DELIVERY_REVIEW_VERDICTS` 상수 (contracts.py) ✅ | □ 박음 / □ 보류 |
| ④ | -1b 금지 4종 (도구/검색어/답변/answer_mode) | 정규식 차단 박힘 (delivery_review.py) ✅ | □ 박음 / □ 보류 |
| ⑤ | 노드명 rename = V4 §1과 함께 일괄 | `phase_delivery_review` 그대로, docstring/ledger만 박힘 ✅ | □ 박음 / □ 보류 |
| ⑥ | reasoning_budget LLM = -1s 내부 흡수 | `_base_plan_reasoning_budget` 호출 위치 = start_gate.py ✅ | □ 박음 / □ 보류 |
| ⑦ | -1a tool_planner = -1a 내부 흡수 (F4 전), F4 후 0차로 이동 | F4 commit `6377a09`로 `tool_request` -1a에서 제거, 0차 일반 흐름화 ✅ | □ 박음 / □ 보류 |
| ⑧ | 0_supervisor LLM = 일반 흐름화 (F4) | `supervisor.py` LLM 호출 fallback only → 일반 흐름 ✅ | □ 박음 / □ 보류 |
| ⑨ | F4 비전 (0차 = 도구 결정 LLM) | F4 코드 박힘 ✅ | □ 박음 / □ 보류 |

**Claude 추천**: ⑨건 다 박음. 코드와 헌법 정합 일관.

---

## 2. §1-A 본문 권한표 결재 (9 노드)

> V3 §1 양식 그대로. **체크박스 = 본문에 그대로 박음/수정/보류** 선택. v2 시트에서 빈 박스로 둔 부분만 모음.

### 2-1. -1s (start_gate)

**한 줄**: 매 사이클 시작에서 user_input + 직전 흐름 + 사고 종합 + 라우팅 결정.

| 권한 항목 | v3 본문 (F2 코드 반영) | 결재 |
|---|---|---|
| 입력 | user_input + recent_context + s_thinking_history + reasoning_plan_hint + **analysis_report compact view** + tactical_briefing (F3로 -1a→-1s 이동) + (X2 결재 시) working_memory | □ 박음 / □ 수정 / □ 보류 |
| 출력 | **ThinkingHandoff.v1 9필드** (producer/recipient/goal_state/evidence_state/what_we_know/what_is_missing/next_node/next_node_reason/constraints_for_next_node) | □ 박음 / □ 보류 |
| 라우팅 | phase_3 (직답) / -1a (계획) / phase_119 (sos) | □ 박음 / □ 보류 |
| 금지 | 도구 인자 직접 작성 / 답변 텍스트 / 사실 검증 (2b 본업) / -1a 계획 직접 수정 / 답변 결재 (-1b 본업) / -1a에 도구 직접 명령 (추상 가이드만) | □ 박음 / □ 보류 |

### 2-2. -1a (strategist)

**한 줄**: ThinkingHandoff 받아 실행계획 + 방향만. F3/F4 후 입력 축소 + tool_request 권한 0차로 이동.

| 권한 항목 | v3 본문 (F3/F4 코드 반영) | 결재 |
|---|---|---|
| 입력 | ThinkingHandoff.v1 + **fact_cells_for_strategist** (V4 5필드 compact) + working_memory + war_room + start_gate_* + tool_carryover + evidence_ledger (analysis_report/raw_read_report/reasoning_board/tactical_briefing 4키 **제거**) | □ 박음 / □ 보류 |
| 출력 | strategist_goal + strategist_output (action_plan + response_strategy + goal_lock + ...) — **tool_request 빠짐** | □ 박음 / □ 보류 |
| 라우팅 | 도구 필요 → 0_supervisor 항상 / 직답 → phase_3 / structured 실패 → -1s | □ 박음 / □ 보류 |
| 금지 | 라우팅 결정 (-1s 본업) / 자기 검열 / 답변 작성 / 사실 재판정 / **tool_request 직접 작성 (F4 후)** | □ 박음 / □ 보류 |

### 2-3. 2b (analyzer / fact_judge)

**한 줄**: raw_read_report → analysis_report. fact_cells deterministic 부여 (코드 후처리).

| 권한 항목 | v3 본문 (V3 그대로) | 결재 |
|---|---|---|
| 입력 | raw_read_report + planned_operation_contract + working_memory_packet + reasoning_board | □ 박음 / □ 보류 |
| 출력 | analysis_report (evidences/source_judgments/usable_field_memo_facts) + reasoning_board.fact_cells (fact_id 자동 부여) | □ 박음 / □ 보류 |
| 라우팅 | -1s (강제) | □ 박음 / □ 보류 |
| 금지 | 라우팅 결정 / 답변 작성 / 정책 판단 / 사고 재판정 (-1s 본업) | □ 박음 / □ 보류 |

### 2-4. phase_3 (speaker)

**한 줄**: 최종 답변 텍스트. 검증된 사실만 인용.

| 권한 항목 | v3 본문 (V3 그대로) | 결재 |
|---|---|---|
| 입력 | response_strategy + delivery_packet + analysis_report + s_thinking_packet + recent_context + (119 시) rescue_handoff_packet | □ 박음 / □ 보류 |
| 출력 | 사용자 답변 텍스트 | □ 박음 / □ 보류 |
| 라우팅 | delivery_review (강제) | □ 박음 / □ 보류 |
| 금지 | 새 도구 결정 / 새 evidence 추출 / 내부 워크플로 누설 (phase 이름/슬롯 키/119/budget) / answer_mode 변경 / 미승인 fact 인용 | □ 박음 / □ 보류 |

### 2-5. -1b (delivery_review) ★ V4 신규 명명

**한 줄**: phase_3 답변 텍스트 LLM 검수. approve / remand / sos_119. **옛 -1b_auditor (phase_3 전 관료제) 부활 절대 금지**.

| 권한 항목 | v3 본문 (F2 코드 반영) | 결재 |
|---|---|---|
| 위치 | phase_3 후 1자리 고정 | □ 박음 / □ 보류 |
| 입력 | final_answer + speaker_review + readiness_decision + analysis_report compact + response_strategy + rescue_handoff_packet compact + phase3_delivery_summary + **fact_cells_for_review** (F2 5필드) | □ 박음 / □ 보류 |
| 출력 | DeliveryReview.v1 (verdict + reason + **reason_type** + **evidence_refs** + **delta** + remand_target + remand_guidance + issues_found) | □ 박음 / □ 보류 |
| 라우팅 (자동, 코드 단일 출처) | hallucination/omission/contradiction/thought_gap → -1s_start_gate / tool_misuse → -1a_thinker / sos_119 → phase_119 / approve → END | □ 박음 / □ 보류 |
| 금지 | 도구 호출 / 검색어 생성 / 답변 작성 / answer_mode 변경 / **새로 사실 조회 (대조관, 조사관 X)** | □ 박음 / □ 보류 |
| 옛 -1b_auditor 부활 절대 금지 | route_audit_result_v2 fallback only, 일반 흐름 X | □ 박음 / □ 보류 |

### 2-6. 0차 (supervisor) — F4 후 격상

**한 줄**: F4 후 = 일반 흐름의 도구 결정 LLM. -1a operation_contract 받아 도구 선택/args/queries 작성.

| 권한 항목 | v3 본문 (F4 코드 반영) | 결재 |
|---|---|---|
| 입력 | -1a operation_contract + ops_tool_cards + ops_node_cards + tool_carryover + **fact_cells (F2 5필드)** + **s_thinking_packet_what_is_missing (ThinkingHandoff top-level + SThinkingPacket fallback)** | □ 박음 / □ 보류 |
| 출력 | tool_calls (LLM 일반 흐름, 3 retries 보존) | □ 박음 / □ 보류 |
| 라우팅 | tool_calls 있음 → phase_1 / 거부 (no tool_calls) → -1b (사후 검수) / structured 실패 → -1a | □ 박음 / □ 보류 |
| 금지 | 답변 작성 / answer_mode 변경 / 사실 재판정 / **fact_id 발명** | □ 박음 / □ 보류 |

### 2-7. WarRoom (deliberator)

**한 줄**: -1s sos급 깊은 토론 자리. **평시 사용 X**. v2 동적 좌석 = §1-C에서.

| 권한 항목 | v3 본문 (V3 그대로) | 결재 |
|---|---|---|
| 입력 | state-level 의역 안건 | □ 박음 / □ 보류 |
| 출력 | war_room (의견 합의) | □ 박음 / □ 보류 |
| 라우팅 | -1s_start_gate (강제) | □ 박음 / □ 보류 |
| 금지 | 평시 라우팅 / 도구 호출 / 답변 작성 | □ 박음 / □ 보류 |
| §1-C 예고 박을 자리 (v2 동적 좌석 + 트리오 프렉탈 + 격리 설계) | placeholder만 박음, 본문은 보류 8 결재 후 | □ 박음 / □ 보류 |

### 2-8. 119 (rescue)

**한 줄**: 모든 시도 실패 시 깔끔한 실패 답변. 새 도구 호출 X.

| 권한 항목 | v3 본문 (V3 그대로) | 결재 |
|---|---|---|
| 입력 | rescue_handoff_packet | □ 박음 / □ 보류 |
| 출력 | rescue 답변 (실패 boundary), preserved_evidences 보존 | □ 박음 / □ 보류 |
| 진입 트리거 | budget 초과 / -1s sos / -1b sos_119 (보류 9 enum 분류 안건) | □ 박음 / □ 보류 |
| 라우팅 | phase_3 (강제) | □ 박음 / □ 보류 |
| 금지 | 재조사 / 추가 도구 호출 / phase_3 *전* 결재 | □ 박음 / □ 보류 |

### 2-9. 옛 -1b_auditor (사문화)

**한 줄**: V3 phase_3 *전* 관료제. V3 §10 7C 폐지. V4 §1-A 부활 절대 금지.

| 권한 항목 | v3 본문 | 결재 |
|---|---|---|
| 위치 | route_audit_result_v2 fallback only (Core/graph.py) | □ 박음 / □ 보류 |
| 부활 | V4 §2 절대 금지 (아래 (i) 신설) | □ 박음 / □ 보류 |
| 처분 | Phase 0 졸업 + V4 §1 통과 후 fallback 정리 발주 (C 트랙) | □ 박음 / □ 보류 |

---

## 3. §1-A 보충 조항: 7 fallback 권한표

> 살아있는 안전장치. V4 §1-A 본문에 보충 조항으로 묶어 박음.

| fallback | 위치 | 보호 대상 | §1-A 보충 조항 | 결재 |
|---|---|---|---|---|
| `_fallback_start_gate_turn_contract` | start_gate.py | -1s structured output 안전망 | -1s 권한표 보충 | □ 박음 / □ 보류 |
| `_base_fallback_strategist_output` | nodes.py | -1a structured output 안전망 | -1a 권한표 보충 | □ 박음 / □ 보류 |
| raw-reader fallback (4종) | nodes.py | 2a reader schema 안전망 | 2a 권한표 보충 | □ 박음 / □ 보류 |
| `_fallback_response_strategy` | nodes.py | phase_3 계약 안전망 | phase_3 권한표 보충 | □ 박음 / □ 보류 |
| reasoning budget fallback | start_gate.py | LLM budget 안전망 | -1s 내부 도구 | □ 박음 / □ 보류 |
| WarRoom fallback adapter | warroom/ | WarRoom 권한표 (보류 8과 묶음) | WarRoom 별도 조항 | □ 박음 / □ 보류 |

**Claude 추천**: 6건 다 박음. fallback 권한 명문화 = JSON 실패 시 루프 보호 책임 헌법화. 단순 "이런 fallback 있다" 명시 + "정상 흐름 X, 안전망만"이라고 박는 게 §2 위반 방지에 도움.

---

## 4. 잔존 결재 X 시리즈 (3건)

### X1 — §1 박는 범위
- **(가)** §1 한 번에 박음 (현장 + 심야 + 트리오 + CoreEgo + 미래) — 큰 작업, 결재 안 박힌 부분 많음
- **(나)** **§1-A 현장 루프만 박음** (§1-B/C/D/E placeholder) — Claude 추천 ✅
- **(다)** 추가 발주 끝나고 §1-A — 안전, 본 시트 정합성 약함

□ (가) / □ **(나) Claude 추천** / □ (다)

### X2 — working_memory를 -1s LLM 입력에 추가?
- **현재**: -1s 함수가 working_memory 받자마자 폐기 (Core/nodes.py).
- **박으면**: -1s 두꺼워짐. 별도 발주 ~20줄 추가.
- **박지 않으면**: -1s 가볍게 유지. 정후 비전 "-1s 두꺼워짐"과 부분 충돌.
- **Claude 추천**: 추가 (정후 비전 정합).

□ 추가 / □ 보류

### X3 — F1.5 V3 잔재 cleanup 시점
F1 검수 중 발견:
- `Core/adapters/night_queries.py:14-44` `search_tactics` 함수
- `Core/adapters/night_queries.py:257` `check_db_status` 라벨 list `"TacticalThought"` 1건

- **(가)** §1-A 박힌 직후 (별도 발주 #F1.5)
- **(나)** 다음 발주에 끼워박음
- **(다)** **§1 + Phase 0 cleanup 트랙 일괄** (Claude 추천) ✅

□ (가) / □ (나) / □ **(다) Claude 추천**

---

## 5. V4 §2 절대 금지 신규 후보 (8개 + α)

> study_pack 뒷면 ① + V3 §2 24개 위에 신규. V4 §2 본문 박을 때 같이 결재.

| 신규 금지 | 사유 | Claude 추천 | 결재 |
|---|---|---|---|
| (a) **axis 섞기 X** | 시간축/의미축 fork된 데이터를 한 사이클 안에서 섞지 X (의미축 정부 v0.3) | ✅ | □ 박음 / □ 보류 |
| (b) **인칭 메타데이터 NULL X** | source_persona 안 박힌 DreamHint/SecondDream write 금지 (v1.6 R3) | ✅ | □ 박음 / □ 보류 |
| (c) **remand_guidance 포맷 위반 X** | reason_type 빈 string인데 evidence_refs 박는 식 정합성 위반 X (F2) | ✅ | □ 박음 / □ 보류 |
| (d) **fact_id 발명 X** | -1b/-1a/0차 어디서도 reasoning_board에 없는 fact_id 인용 X (F2) | ✅ | □ 박음 / □ 보류 |
| (e) **119 enum 무분류 X** | 119 진입 시 reason_type/severity enum 빈 채로 escalate X (보류 9와 묶음) | ✅ | □ 박음 / □ 보류 |
| (f) **DreamHint expires_at 우회 X** | archive_at IS NULL + expires_at > now 필터 우회 X (R7) | ✅ | □ 박음 / □ 보류 |
| (g) **tool_request 0차 외 발생 X** | F4 후 -1a/-1s/-1b 어디서도 tool_request 직접 박기 X | ✅ | □ 박음 / □ 보류 |
| (h) **0차 LLM 답변 작성 X** | F4 후 0_supervisor가 도구 선택만, 최종 판단/답변 X | ✅ | □ 박음 / □ 보류 |
| **(i) 옛 -1b_auditor 부활 X** | phase_3 *전* -1b 결재 부활 차단 (§2-9와 묶음) | ✅ Claude 추가 제안 | □ 박음 / □ 보류 |
| **(j) ThinkingHandoff.v1 9필드 누락 X** | producer/recipient/goal_state/evidence_state/what_we_know/what_is_missing/next_node/next_node_reason/constraints_for_next_node 중 하나라도 빈 채 라우팅 X | ✅ Claude 추가 제안 | □ 박음 / □ 보류 |

**자유발화 자리** (V3 §2 24개 중 V4에서 유효성 떨어진 것 제거 / 추가 후보):

____________________________________________

____________________________________________

____________________________________________

---

## 6. 보류 10개 중 잔존 6개 처분

> v2 시트 보류 10개 중 F2/F4로 4개 풀림. 잔존 6개 단숨 결재.

| # | 보류 | v3 처분 후보 | Claude 추천 | 결재 |
|---|---|---|---|---|
| 1 | working_memory → -1s 입력 (= X2) | (가) 추가 / (나) 보류 / (다) §1-A 박힌 후 별도 발주 | (가) 추가 | □ (가) / □ (나) / □ (다) |
| 5 | phase_3이 user_input 다시 봐야? | (가) Phase 1 전 1주 모니터링 후 결정 / (나) 즉시 채택 (V3 그대로 = 안 봄) / (다) 즉시 추가 | (가) 모니터링. 신호 = "phase_3 답변이 user 의도 빗나간 사례 ≥3건/주" | □ (가) / □ (나) / □ (다) |
| 7 | -1b 입력 비대 (8필드) | (가) 1주 운영 후 phase3_summary 인용 0건이면 제거 / (나) 즉시 제거 / (다) 그대로 | (가) 1주 모니터링. 신호 = "-1b LLM 출력에 phase3_summary 인용 0건/주" | □ (가) / □ (나) / □ (다) |
| 8 | WarRoom 격리 설계 | **§1-C 자유발화 안건** (v2 동적 좌석 + 트리오 프렉탈 + 격리). 본문은 §1-A 박힌 후 §1-C 발주에서 | §1-C 발주에서 박음 | □ 박음 / □ 보류 |
| 9 | 119 enum 분류 | **Phase 1 발주** (V4 §2 (e)와 묶음). enum 후보 = BUDGET_EXHAUSTED / TOOL_TIMEOUT / LLM_HALLUCINATION / ROUTE_DEADLOCK / DELIVERY_REVIEW_SOS / 등 | Phase 1 1차 발주에서 박음 | □ 박음 / □ 보류 |
| 10 | 모듈식 답변 생성 노드 | **Phase 1 발주** (delivery_packet 미래 호환 + 보류 4-3 cited_fact_ids 묶음) | Phase 1 1차 발주에서 박음 | □ 박음 / □ 보류 |

---

## 7. Phase 0 → Phase 1 진입 게이트 결재

> 부록 X 게이트 (§0 박힌 후) verify.

| 게이트 | 현재 상태 (2026-05-09) | 정합 | 결재 |
|---|---|---|---|
| midnight 모듈 ≥3개로 분해 | recall/present/past/future + semantic = 5+ ✅ | OK | □ 박음 / □ 보류 |
| nodes.py heuristic ≤2개 | B트랙 #0.5 완료 (`_fallback_strategist_output` 제거), 살아있는 fallback 7종 = 안전망 (§1-A 보충) | OK | □ 박음 / □ 보류 |
| tests OK 유지 | 189 → 294 OK ✅ | OK | □ 박음 / □ 보류 |
| V4 §1 권한표 작성 가능 상태 | 본 시트 결재 → §1-A 본문 박음 | **오늘 박으면 OK** | □ 박음 / □ 보류 |
| **Phase 0 → 1 진입** | 위 4 게이트 통과 시 자동 | — | □ **진입** / □ 보류 |

**Claude 추천**: 5건 다 박음. §1-A LIVE 박힌 직후 Phase 1 진입 선언 가능.

---

## 8. Phase 1 진입 후 다음 발주 순서 결재

> §1-A LIVE 박힌 직후 어느 트랙부터 발사할지.

### 8-1. Phase 1 1차 발주 후보

| 트랙 | 내용 | Phase 1 정합도 | Claude 우선순위 추천 |
|---|---|---|---|
| **T트랙** | DreamHint 가중치 + 과거 정부 통합 (project_t_track_dreamhint_weights.md) | Phase 2 활성화 전파 첫 디딤돌 = 정후 끝점 직결 | ★★★ 1순위 |
| **E트랙** | 임베딩 제공자 + Neo4j K-NN + 1024차원 모델 | T트랙/의미축 정부 의존 | ★★ 2순위 (T트랙 후) |
| **C트랙** | #0.8 readiness 처분 + #0.9 route_audit_result_v2 처분 + #0.10 verify | Phase 0 cleanup 마무리 (§1-A §2-9와 묶음) | ★★ 2순위 |
| **§1-B** | 심야 정부 권한표 (4부서 + 의미축 fork + 7 fallback) | §1 시리즈 본문 | ★ 3순위 |
| **A트랙 후속** | step2_mapping_draft.md 박힌 8~10개 | Phase 0 결말 + Phase 1 인프라 | ★ 3순위 |
| **보류 9, 10 발주** | 119 enum + 모듈식 답변 | Phase 1 1차 박음 (위 6번 결재로 묶임) | T트랙과 평행 가능 |

### 8-2. Phase 1 1차 발주 묶음 결재

- **(가)** **T트랙 1차 + 보류 9 + 보류 10 + C트랙** 평행 (Claude 추천 ✅, 정후 끝점 = Phase 2 활성화 전파 직진)
- **(나)** §1-B 먼저 + T트랙 차후 (안전, 정후 끝점 멀어짐)
- **(다)** A트랙 후속 8~10개 먼저 (Phase 0 잔재 우선, 정후 끝점 멀어짐)

□ (가) / □ (나) / □ (다)

### 8-3. §1-B/C/D/E 박는 시점 결재

| §1 부분 | 내용 | Claude 추천 시점 |
|---|---|---|
| §1-B 심야 정부 권한표 | 4부서 + 의미축 fork + 7 fallback | T트랙 1차 검수 후 (실 운영 데이터 보고) |
| §1-C 트리오 재귀 + WarRoom v2 | 부록 Y v1.0. WarRoom v2 후 | Phase 2 진입 전 |
| §1-D CoreEgo 양면 | 그래프 노드 ↔ 심야 분신 | Phase 3 |
| §1-E 미래 노드 합성체 | CoreEgo + 도구 전략 + 과거 wiki | Phase 3 |

**결재**: □ Claude 추천 그대로 / □ 수정 / □ 보류

---

## 9. 결재 의존성 트리

```
1. 도장 9건 (①~⑨) ──→ §1-A 본문 그대로 박음
                       ↓
2. §1-A 본문 권한표 9 노드 (~30 체크박스) ──→ §1-A 본문
                       ↓
3. 7 fallback 권한표 ──→ §1-A 보충 조항
                       ↓
4. X1 (§1 범위) ──→ §1-A 박는 범위 결정
   X2 (working_memory) ──→ §2-1 -1s 입력 권한
   X3 (F1.5 cleanup) ──→ Phase 1 발주 순서
                       ↓
5. V4 §2 신규 (a~j) ──→ §2 본문 박음 (§1과 같이 박을지, 별도 박을지 = X1 결재로)
                       ↓
6. 보류 6개 ──→ §1-A 박음 / 모니터링 / Phase 1 발주로 분배
                       ↓
7. Phase 0 → 1 진입 게이트 5 ──→ §1-A LIVE 박힌 직후 자동 진입
                       ↓
8. Phase 1 1차 발주 묶음 ──→ T트랙 + 보류 9/10 + C트랙 평행
                       ↓
   §1-B/C/D/E 박는 시점 ──→ 차후
```

**보류 영향**:
- ⑤ 보류 → §1 본문 노드명 거짓말
- X1 (다) 보류 → §1-A 박는 시점 차후로 밀림 (오늘 단숨 모드 X)
- X2 보류 → -1s 입력 권한 working_memory 빠짐
- 보류 9/10 → Phase 1 1차 발주 묶음에서 빠짐
- Phase 0 → 1 진입 게이트 1건 보류 → §1-A LIVE 안 박힘 → Phase 1 직진 X

---

## 10. 비전 발화 백지 자리

### 비전 발화 #1 — V4 §2 신규 금지 추가 후보

주제: ____________________________________________

내용:

____________________________________________

____________________________________________

### 비전 발화 #2 — 보류 8 WarRoom v2 (격리 + 동적 좌석 + 트리오 프렉탈)

주제: ____________________________________________

내용:

____________________________________________

____________________________________________

### 비전 발화 #3 — 보류 9 119 enum 분류 후보 (reason_type과 통합)

후보:
- BUDGET_EXHAUSTED
- TOOL_TIMEOUT
- LLM_HALLUCINATION
- ROUTE_DEADLOCK
- DELIVERY_REVIEW_SOS
- 추가: ____________________________________________

### 비전 발화 #4 — 자유 (트리오/CoreEgo/미래/기타)

주제: ____________________________________________

내용:

____________________________________________

____________________________________________

---

## 11. 결재 후 다음 신호 (정후 → Claude 단숨 모드)

본 시트 결재 다 박히면:

1. Claude가 §1-A 본문 글 작성 (`ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` §1 자리에 박음, ~1시간)
2. V4 §2 본문 글 작성 (X1 (나)면 §1-A와 같이, (가)면 §1 통째)
3. 정후 검수 → 헌법 LIVE 박힘
4. Phase 0 → 1 진입 선언 commit
5. Phase 1 1차 발주서 (T트랙 + 보류 9 + 보류 10 + C트랙) 작성 시작
6. Codex 발사 → 단숨 개발 모드

---

## 12. 결재 항목 총계

| 카테고리 | 항목 수 |
|---|---|
| §1. 도장 9건 (①~⑨) | 9 |
| §2. §1-A 본문 권한표 (9 노드 × ~3 체크박스) | ~30 |
| §3. 7 fallback 권한표 | 6 |
| §4. X 시리즈 (X1/X2/X3) | 3 |
| §5. V4 §2 신규 (a~j 10개) | 10 |
| §6. 보류 6개 처분 | 6 |
| §7. Phase 0 → 1 게이트 5 | 5 |
| §8. Phase 1 발주 순서 (8-2 + 8-3) | 2 |
| §10. 비전 발화 백지 4 자리 | 4 |
| **총** | **~75** |

정후 단숨 결재 가능 (체크박스 □ → ✓로 도장).

---

**버전**: v3 (2026-05-09 토)
**선행**: v2 (2026-05-06 V4_section1_A_decision_sheet.md)
**다음**: 본 시트 결재 → §1-A + §2 본문 박힘 → Phase 1 진입.
