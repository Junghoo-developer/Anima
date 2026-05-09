# V4 §1-A 결재 결과 단일 출처 — v3.1 (2026-05-09 단숨 모드 종료)

**작성일**: 2026-05-09 (토)
**작성**: Claude (사법부 자문)
**결재**: 정후 (입법부) — 도장 다 박힘 ✓
**선행**: v3 시트 (`V4_section1_decision_sheet_v3_2026_05_09.md`) — 펼친 결재 → 본 v3.1이 결과 단일 출처
**다음**: 본 시트 기반 §1-A 본문 글 작성 → ANIMA_FIELD_LOOP_V4_CONSTITUTION.md §1 자리에 박힘 → Phase 0→1 진입 → Phase 1 CR1 발주.

---

## 0. 큰 결정 정리 (한눈에)

정후 정의 박힘:
- **-1s = 사이클 시작점 상황 판단자**. 사용자 의도 정제 + 사고 흐름 추적 + 라우팅 결정 + 다음 노드 제약 발급. **목표 수립 X**.
- **-1a = 사이클 중 목표 수립자**. -1s 상황 판단 받아 작전 목표 + 실행계획 + 도구 의도. **라우팅 X** (deterministic 신호만).

★ V4 핵심 비전 박힘: **2b가 -1s 사이클 중간 비판자 (thought_critic mode 신설)**. -1s가 목표 수립이 아닌 "상황 판단 + 사고 흐름" 본업이고, 사고 흐름이 막힐 때 2b 사고 비판자가 input differentiator 역할 = gemma4 false negative 자동 방어 ★.

---

## 1. 박힌 결재 도장 (9건, 코드 굳어진 상태)

| # | 결재 | 도장 |
|---|---|---|
| ① | delivery_review = new -1b 명명 | ✓ |
| ② | -1b 위치 = phase_3 후 1자리 | ✓ |
| ③ | -1b 권한 3종 (approve/remand/sos_119) | ✓ |
| ④ | -1b 금지 4종 (도구/검색어/답변/answer_mode) | ✓ |
| ⑤ | 노드명 rename = V4 §1과 함께 일괄 | ✓ |
| ⑥ | reasoning_budget LLM = -1s 내부 흡수 | ✓ |
| ⑦ | -1a tool_planner = -1a 내부 흡수 → F4 후 0차 이동 | ✓ |
| ⑧ | 0_supervisor LLM = 일반 흐름화 (F4) | ✓ |
| ⑨ | F4 비전 (0차 = 도구 결정 LLM) | ✓ |

---

## 2. §1-A 본문 권한표 (9 노드, 본문 박힐 단일 출처)

### 2-1. -1s (start_gate) — **상황 판단자** ★

| 권한 | 본문 (V4 정의 + F2 코드 반영) |
|---|---|
| 한 줄 | 사이클 시작점 상황 판단자. 사용자 의도 정제 + 사고 흐름 추적 + 라우팅 결정. 목표 수립 X. |
| 입력 | user_input + recent_context + s_thinking_history + reasoning_plan_hint + analysis_report compact view + tactical_briefing (F3) + working_memory (X4 박힘) |
| 출력 | ThinkingHandoff.v1 9필드 (producer/recipient/goal_state/evidence_state/what_we_know/what_is_missing/next_node/next_node_reason/constraints_for_next_node). **`goal_state` = 사용자 의도 정제본, 작전 목표 X** (정후 정의 명문화) |
| 라우팅 | phase_3 (직답 가능 시 직접) / -1a (목표 수립 필요) / phase_119 (sos) / **warroom_deliberator** (B 분기) / **2b_thought_critic** (B 분기) |
| 금지 | 도구 인자 직접 작성 / 답변 텍스트 / 사실 검증 (2b 본업) / -1a 계획 직접 수정 / 답변 결재 (-1b 본업) / -1a에 도구 직접 명령 / **목표 수립** (-1a 본업) / **raw user wording 그대로 goal로 복사** |

**신규 권한** (정후 비전 박힘):
- **경량 CoT** (X4): 정보 변화 없을 때 -1s 내부 사고 깊이 ↑ (s_thinking_history 누적). WarRoom의 평시 가벼운 버전.
- **2차 호출 시 검증 + 라우팅 두 권한** (X6 B-1/B-3): -1a 거친 후 회귀 시 (1) 직전 정보 다시 보기 (검증 우선) (2) 워룸/CoT/phase_3 라우팅.
- **직답 라우팅 적극 활용** (X5): 단순 직답 가능 input은 phase_3로 직접 라우팅, -1a 거치지 않음.

### 2-2. -1a (strategist) — **목표 수립자** ★

| 권한 | 본문 (F3/F4 코드 반영) |
|---|---|
| 한 줄 | 사이클 중 목표 수립자. -1s 상황 판단 받아 작전 목표 + 실행계획 + 도구 의도. 라우팅 X (deterministic 신호만). |
| 입력 | ThinkingHandoff.v1 + fact_cells_for_strategist (V4 5필드 compact) + working_memory + war_room + start_gate_* + tool_carryover + evidence_ledger. **analysis_report/raw_read_report/reasoning_board/tactical_briefing 4키 제거 (F3)**. |
| 출력 | strategist_goal (user_goal_core + answer_mode_target + success_criteria + scope) + strategist_output (case_theory + operation_plan + goal_lock + delivery_readiness + action_plan + response_strategy + ...). **tool_request 빠짐 (F4)**. |
| 라우팅 | (LLM 결정 X) deterministic 신호만: delivery_readiness=deliver_now → phase_3 / 그 외 → 0_supervisor / structured 실패 → -1s |
| 금지 | 라우팅 결정 (-1s 본업) / 자기 검열 / 답변 작성 / 사실 재판정 / tool_request 직접 작성 (F4) / **사고 흐름 추적** (-1s 본업) / **상황 재판정** |

### 2-3. 2b (analyzer / fact_judge + thought_critic) — **사실 판사 + 사고 비판자** ★ V4 권한 확장

| 권한 | 본문 (정후 비전 X6 박힘) |
|---|---|
| 한 줄 | 두 모드 자동 전환. **fact mode**: 도구 raw → 사실 정제. **thought_critic mode**: -1s 사고 흐름 + 기억 대조해서 사고 비판. |
| 입력 (fact mode) | raw_read_report + planned_operation_contract + working_memory_packet + reasoning_board |
| 입력 (thought_critic mode) | s_thinking_packet + recent_context + working_memory + (fact_cells 있으면 같이) |
| **모드 자동 전환** (B-2.4 (다)) | 2b 시스템 프롬프트가 입력 보고 자동 결정: fact_cells > 0 → 통합 비판 모드 / fact_cells == 0 → 기억 기반 비판 모드 |
| 출력 (fact mode) | analysis_report (evidences/source_judgments/usable_field_memo_facts) + reasoning_board.fact_cells (fact_id 자동 부여) |
| 출력 (thought_critic mode) | ThoughtCritique.v1 (사실 충돌 / 논리 갭 / 기억 누락 / 인칭 오류 등 분류 + evidence_refs) |
| 라우팅 | fact mode → -1s (강제) / thought_critic mode → -1s_start_gate (회귀, 2차 -1s가 비판 결과 받음) |
| 금지 | 라우팅 결정 / 답변 작성 / 정책 판단 / 사고 재판정 (-1s 본업) — **단 thought_critic mode는 사고 비판이 본업이라 "재판정 금지"는 fact mode 한정** |

**진입 트리거 (deterministic 게이트, B/B-2 결정)**:
```
_strategist_needs_thought_recursion(state) =
    has_goal (strategist_goal.user_goal_core 박힘)
    AND len(fact_cells) == 0  # B-2.2 (가) 진짜 빈 경우만
    AND no_tool_needed (action_plan.required_tool 비어있음 + tool_request 없음)
    # delivery_readiness 의존 제거 — LLM 라벨 false negative 차단
```

게이트 통과 시 → 2b thought_critic 호출 → 결과 → 2차 -1s 회귀 (B-1 (나)).

### 2-4. phase_3 (speaker) — V3 그대로

| 권한 | 본문 |
|---|---|
| 한 줄 | 최종 답변 텍스트. 검증된 사실만 인용. |
| 입력 | response_strategy + delivery_packet + analysis_report + s_thinking_packet + recent_context + (119 시) rescue_handoff_packet |
| 출력 | 사용자 답변 텍스트 |
| 라우팅 | delivery_review (강제) |
| 금지 | 새 도구 결정 / 새 evidence 추출 / 내부 워크플로 누설 (phase 이름/슬롯 키/119/budget) / answer_mode 변경 / 미승인 fact 인용 |

### 2-5. -1b (delivery_review) — V4 신규 명명, F2 코드 반영

| 권한 | 본문 |
|---|---|
| 위치 | phase_3 후 1자리 고정. 옛 -1b_auditor (phase_3 전 관료제) 부활 절대 금지. |
| 입력 | final_answer + speaker_review + readiness_decision + analysis_report compact + response_strategy + rescue_handoff_packet compact + phase3_delivery_summary + fact_cells_for_review (F2 5필드) |
| 출력 | DeliveryReview.v1 (verdict + reason + reason_type + evidence_refs + delta + remand_target + remand_guidance + issues_found) |
| 라우팅 (자동, 코드 단일 출처) | hallucination/omission/contradiction/thought_gap → -1s_start_gate / tool_misuse → -1a_thinker / sos_119 → phase_119 / approve → END |
| 금지 | 도구 호출 / 검색어 생성 / 답변 작성 / answer_mode 변경 / 새로 사실 조회 (대조관, 조사관 X) |

### 2-6. 0차 (supervisor) — F4 후 격상

| 권한 | 본문 |
|---|---|
| 한 줄 | 일반 흐름의 도구 결정 LLM. -1a operation_contract 받아 도구 선택/args/queries 작성. |
| 입력 | -1a operation_contract + ops_tool_cards + ops_node_cards + tool_carryover + fact_cells (F2 5필드) + s_thinking_packet_what_is_missing |
| 출력 | tool_calls (LLM 일반 흐름, 3 retries 보존) |
| 라우팅 | tool_calls 있음 → phase_1 / 거부 (no tool_calls) → -1b / structured 실패 → -1a |
| 금지 | 답변 작성 / answer_mode 변경 / 사실 재판정 / fact_id 발명 |

### 2-7. WarRoom (deliberator)

| 권한 | 본문 |
|---|---|
| 한 줄 | -1s sos급 깊은 토론 자리. **평시 사용 X**. v2 동적 좌석은 §1-C에서. |
| 입력 | state-level 의역 안건 |
| 출력 | war_room (의견 합의) |
| 라우팅 | -1s_start_gate (강제) |
| 금지 | 평시 라우팅 / 도구 호출 / 답변 작성 |
| **B 분기 진입 트리거** (X6 B-3) | -1s 2차 호출 시스템 프롬프트가 (검증 후) "깊은 토론 필요" 판정 시 → warroom_deliberator. "가벼운 비판" 판정 시 → 2b_thought_critic. |

### 2-8. 119 (rescue) — V3 그대로

| 권한 | 본문 |
|---|---|
| 한 줄 | 모든 시도 실패 시 깔끔한 실패 답변. 새 도구 호출 X. |
| 입력 | rescue_handoff_packet |
| 출력 | rescue 답변, preserved_evidences 보존 |
| 진입 트리거 | budget 초과 / -1s sos / -1b sos_119 (보류 9 enum 분류 = Phase 1 발주) |
| 라우팅 | phase_3 (강제) |
| 금지 | 재조사 / 추가 도구 호출 / phase_3 *전* 결재 |

### 2-9. 옛 -1b_auditor (사문화)

| 사항 | 본문 |
|---|---|
| 위치 | route_audit_result_v2 fallback only (Core/graph.py). 일반 흐름 X. |
| 부활 | V4 §2 (i) 절대 금지. |
| 처분 | Phase 0 졸업 + V4 §1 통과 후 fallback 정리 발주 (C 트랙). |

---

## 3. §1-A 보충 — 7 fallback 권한표

| fallback | 위치 | 보호 대상 | §1-A 보충 |
|---|---|---|---|
| `_fallback_start_gate_turn_contract` | start_gate.py | -1s structured output 안전망 | -1s 권한표 보충 |
| `_base_fallback_strategist_output` | nodes.py | -1a structured output 안전망 | -1a 권한표 보충 |
| raw-reader fallback (4종) | nodes.py | 2a reader schema 안전망 | 2a 권한표 보충 |
| `_fallback_response_strategy` | nodes.py | phase_3 계약 안전망 | phase_3 권한표 보충 |
| reasoning budget fallback | start_gate.py | LLM budget 안전망 | -1s 내부 도구 (결재 ⑥) |
| WarRoom fallback adapter | warroom/ | WarRoom 권한표 (보류 8과 묶음) | WarRoom 별도 조항 |

**원칙**: 일반 흐름 X, 안전망만. JSON 실패 시 루프 보호 책임 헌법화.

---

## 4. §1-A 본문 — 배선 경우의 수 표 (8행, 정후 안건 B 결정 반영)

| 입력 상황 | 도구 필요? | 정보 변화? | -1s 결정 | 다음 노드 |
|---|---|---|---|---|
| 새 user_input | — | ✅ (외부) | 사고 종합 | -1a (목표 수립) |
| 도구 결과 도착 | — | ✅ (2b 새 fact) | 재판정 | -1a (목표 갱신) |
| **직답 가능** (analysis_report 충족 또는 단순 응답) | X | — | 종결 | **phase_3 (직접, X5)** |
| 정보 불충분 + 도구 가능 | ✅ | — | 도구 의도 | -1a → 0차 |
| **정보 불충분 + 도구 불가 + fact_cells > 0** | X | X | -1s 경량 CoT (내부 깊이 ↑) | -1s 자체 누적 → -1a |
| **정보 불충분 + 도구 불가 + fact_cells == 0** (★ B 게이트) | X | X | 게이트 통과 | **2b_thought_critic → 2차 -1s 회귀** |
| 2차 -1s 회귀 (검증 후 깊은 토론 필요) | — | (NEW: 2b 비판 결과) | 워룸 진입 | warroom_deliberator |
| 사고 막힘 (반복 사고도 안 됨, hard_stop 도달) | — | — | sos | phase_119 |
| -1b remand `thought_gap` | — | (외부 X) | 경량 CoT 1회 | -1a 재진입 (반복 시 phase_119) |

---

## 5. §1-A 본문 — 트리오 재귀 anchor (V4 §0 부록 Y v1.0 *최초 인스턴스*)

```
-1s (계획/사고)
  ↕ (게이트 통과 시)
2b_thought_critic (비판)  ←  recent_context + working_memory + s_thinking_packet
  ↓
2차 -1s 회귀 (input = 2b 비판 + 첫 ThinkingHandoff)
  ↓ 검증 → phase_3 / 워룸 / CoT
-1a (실행 = 목표 수립)
```

이게 V4 §0 부록 Y "트리오 재귀 어느 층에서나"의 첫 인스턴스. §1-C (트리오 재귀 본문) 작성 시 reference로 사용.

---

## 6. 결재 결과 사항 (X 시리즈)

| 결재 | 결정 | 출처 |
|---|---|---|
| **#1** ThinkingHandoff.goal_state 의미 명문화 | "사용자 의도 정제본 (목표 X)" — §1-A 본문에 박힘. 코드 description rename은 선택 (보류) | 정후 정의 verify |
| **#2** -1s goal_state vs -1a strategist_goal 권한 경계 | §1-A 본문 2-1/2-2에 명문화 | 정후 정의 |
| **#3** 시트 -1s 한 줄 "사고 종합" → "상황 판단" | 정정 박음 | 정후 정의 |
| **#4** ThinkingHandoff 7 → 9 필드 | 정정 (next_node_reason 추가) | 코드 사실 |
| **#5** "사고 흐름 추적 = -1s 본업, 목표 수립 = -1a 본업" | §1-A 본문에 명문화 | 정후 정의 |
| **X1** §1 박는 범위 | (나) §1-A만 박음, §1-B/C/D/E placeholder | Claude 추천 박음 (잠정 결재 — 정후 명시 결재 X시 본문 작성 시 확인) |
| **X2** working_memory → -1s LLM 입력 | 추가 (X4와 묶음) | Claude 추천 박음 |
| **X3** F1.5 V3 잔재 cleanup | (다) Phase 0 cleanup 트랙 일괄 | Claude 추천 박음 |
| **X4** -1s 경량 CoT | 박음. -1s 권한표 2-1에 신규 권한 명시 | 핑퐁 진단 + 정후 정의 |
| **X5** -1s 직답 라우팅 강화 | 박음. 배선 표 3행 + 2-1 권한표에 명시 | -1s 본업 강화 |
| **X6** 2b 사고 비판자 권한 확장 | **박음 (전체 묶음)** | 정후 비전 ★ |
| ⮕ X6-A | (라) fact_cells + 최근 기억 | ✓ |
| ⮕ X6-B | 하이브리드 (deterministic 게이트 + LLM 판정) | ✓ |
| ⮕ X6-B-1 | (나) -1a 거친 후 두 번째 -1s 회귀 시 판정 | ✓ |
| ⮕ X6-B-2 | deterministic 게이트 = `has_goal AND fact_cells==0 AND no_tool` (delivery_readiness 의존 제거) | ✓ |
| ⮕ X6-B-2.1 | 두 번째 -1s 검증 우선 rule 박음 | ✓ |
| ⮕ X6-B-2.2 | fact_cells == 0 (보수적) | ✓ |
| ⮕ X6-B-2.3 | 2b 비판 결과가 input differentiator → marker 불필요 | ✓ |
| ⮕ X6-B-2.4 | 2b 시스템 프롬프트 입력 적응 자동 모드 전환 | ✓ |
| ⮕ X6-B-3 | (가) 두 번째 -1s 호출 자체에서 워룸/CoT 판정 | ✓ |
| ⮕ X6-C | (가) -1s가 받아서 ThinkingHandoff 갱신 | ✓ |
| ⮕ X6-D | (다) 2b 권한 확장 + 모드 명시 | ✓ |
| **TR1** F4 후 같은 input 1턴 verify | 즉시 진행 (Phase 1 진입 전 또는 평행) | trace 진단 |

---

## 7. V4 §2 절대 금지 신규 후보 (10건, §2 본문 박을 때 단일 출처)

> X1 (나) 결정대로 §2는 §1-A 박힌 후 별도 박음. 본 시트에 단일 출처 보존.

| 신규 금지 | 사유 | 결재 |
|---|---|---|
| (a) axis 섞기 X | 시간축/의미축 fork된 데이터 한 사이클 안에서 섞지 X | ✓ 박음 |
| (b) 인칭 메타데이터 NULL X | source_persona 안 박힌 DreamHint/SecondDream write 금지 | ✓ |
| (c) remand_guidance 포맷 위반 X | reason_type 빈데 evidence_refs 박는 식 정합성 위반 X | ✓ |
| (d) fact_id 발명 X | -1b/-1a/0차 어디서도 reasoning_board에 없는 fact_id 인용 X | ✓ |
| (e) 119 enum 무분류 X | 119 진입 시 reason_type/severity enum 빈 채로 escalate X | ✓ |
| (f) DreamHint expires_at 우회 X | archive_at IS NULL + expires_at > now 필터 우회 X | ✓ |
| (g) tool_request 0차 외 발생 X | F4 후 -1a/-1s/-1b 어디서도 tool_request 직접 박기 X | ✓ |
| (h) 0차 LLM 답변 작성 X | F4 후 0_supervisor가 도구 선택만, 최종 판단/답변 X | ✓ |
| (i) 옛 -1b_auditor 부활 X | phase_3 *전* -1b 결재 부활 차단 | ✓ |
| (j) ThinkingHandoff.v1 9필드 누락 X | 9필드 중 하나라도 빈 채 라우팅 X | ✓ |
| **(k) -1s 목표 수립 X** ★ V4 정의 명문화 | -1s가 raw user wording 그대로 goal로 박지 X (이미 코드에) + strategist_goal 권한 침해 X | Claude 신규 추가 박음 |
| **(l) -1a 라우팅 결정 X** ★ V4 정의 명문화 | -1a는 deterministic 신호 (delivery_readiness)만, 라우팅 분기는 코드 | Claude 신규 추가 박음 |

---

## 8. 보류 10개 처분 (잔존 6개 결정)

| # | 보류 | 처분 |
|---|---|---|
| 1 | working_memory → -1s 입력 (= X4 묶음) | ✓ 박음 |
| 5 | phase_3이 user_input 다시 봐야? | (가) 1주 모니터링 후 결정 |
| 7 | -1b 입력 비대 (8필드) | (가) 1주 모니터링 후 phase3_summary 인용 0건이면 제거 |
| 8 | WarRoom 격리 설계 | §1-C 발주에서 박음 |
| 9 | 119 enum 분류 | Phase 1 1차 발주 (V4 §2 (e)와 묶음) |
| 10 | 모듈식 답변 생성 노드 | Phase 1 1차 발주 (delivery_packet 미래 호환 + 보류 4-3 cited_fact_ids 묶음) |

---

## 9. Phase 0 → 1 진입 게이트 (5건, 다 박힘)

| 게이트 | 상태 | 결재 |
|---|---|---|
| midnight 모듈 ≥3개 | recall/present/past/future + semantic = 5+ ✓ | ✓ |
| nodes.py heuristic ≤2 | B트랙 #0.5 완료, 살아있는 fallback 7종 = §1-A 보충 | ✓ |
| tests OK 유지 | 294 OK ✓ | ✓ |
| V4 §1 권한표 작성 가능 | §1-A 본문 박힌 직후 충족 | ✓ |
| **Phase 0 → 1 진입** | §1-A LIVE 박힌 직후 자동 진입 commit | ✓ |

---

## 10. Phase 1 1차 발주 묶음 (정후 (가) 박음)

**T트랙 + 보류 9 + 보류 10 + C트랙 평행 + CR1 (신설 트랙)**:

| 트랙 | 내용 | 우선 |
|---|---|---|
| **CR1** ★ 신설 | 2b 사고 비판자 권한 확장 (X6 본체 = A/B/C/D + B 시리즈 다) | 1순위 (정후 비전 직결) |
| **T1** | DreamHint 가중치 + 과거 정부 통합 | 2순위 (Phase 2 활성화 전파 디딤돌) |
| **C0.8/0.9/0.10** | readiness 처분 + route_audit_result_v2 처분 + verify | 평행 |
| **B9/B10** | 119 enum 분류 + 모듈식 답변 (delivery_packet 미래 호환) | 평행 |
| **TR1** | F4 후 같은 input 1턴 verify | CR1 진입 전 즉시 |

§1-B/C/D/E 박는 시점:
- §1-B 심야 정부 권한표 → T트랙 1차 검수 후
- §1-C 트리오 재귀 + WarRoom v2 → CR1 박힌 후 (트리오 재귀 *최초 인스턴스* = §1-A에 박혔으니 §1-C는 reference로 박음)
- §1-D CoreEgo 양면 → Phase 3
- §1-E 미래 노드 합성체 → Phase 3

---

## 11. CR1 발주 윤곽 (Phase 1 1순위)

**제목**: V4 Phase 1 #CR1 — 2b 사고 비판자 (thought_critic mode) + -1s 사고 재귀 + deterministic 게이트

**의뢰일**: 2026-05-09 (Phase 1 진입 commit 직후)

**규모**: ~230줄 (F2/F3/F4 합친 절반)

**작업**:
1. `Core/pipeline/contracts.py` ThinkingHandoff Literal 확장 (recipient/next_node에 `warroom_deliberator`, `2b_thought_critic` 추가, ~5줄)
2. `Core/pipeline/contracts.py` 2b 입력 schema 확장 (mode 필드, ~10줄)
3. `Core/pipeline/contracts.py` ThoughtCritique.v1 schema 신설 (~25줄)
4. `Core/prompt_builders.py` 2b 시스템 프롬프트 모드 분기 (~40줄)
5. `Core/prompt_builders.py` -1s 시스템 프롬프트: 2차 호출 검증 우선 rule + 워룸/CoT 판정 rule (~30줄)
6. `Core/graph.py` `_strategist_needs_thought_recursion(state)` helper (~20줄)
7. `Core/graph.py` `route_after_strategist`에 새 분기 + `route_after_s_thinking`에 워룸/2b_thought_critic 라우팅 (~30줄)
8. `Core/graph.py` `2b_thought_critic` → `-1s_start_gate` 회귀 분기 (~15줄)
9. 2b thought_critic mode 노드 본체 (`Core/pipeline/thought_critic.py` 신설, ~50줄)
10. 새 tests (~80줄):
    - `tests/test_2b_thought_critic.py` (4 case)
    - `tests/test_thought_recursion_routing.py` (5 case)
    - `tests/test_strategist_needs_thought_recursion_gate.py` (4 case)

**예상 tests**: 294 + 13 신규 = **307 OK**.

---

## 12. 다음 신호

1. ✅ **시트 v3.1 박음** (본 파일)
2. ⮕ **§1-A 본문 글 작성** = `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` §1 자리에 박음 (~250~300줄)
3. ⮕ 정후 검수
4. ⮕ Phase 0 → 1 진입 commit
5. ⮕ CR1 발주서 + dispatch 작성 → Codex 발사
6. ⮕ TR1 verify 평행

---

**버전**: v3.1 (2026-05-09 토)
**선행**: v2 (2026-05-06), v3 (2026-05-09 펼침)
**상태**: 결재 도장 다 박힘. §1-A 본문 글 작성 단계.
