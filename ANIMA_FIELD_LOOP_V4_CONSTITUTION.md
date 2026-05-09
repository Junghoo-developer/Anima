# ANIMA Field Loop V4 — Constitution (헌법)

**작성일**: 2026-05-02
**상태**: §0 v0 정후 통과 (2026-05-02). **§1-A 현장 루프 + §2 절대 금지 정후 통과 (2026-05-09)** ★. §1-B/C/D/E / §10 작성 중.
**역할**: 송련 *학습하는 인격* 진화의 단일 기준점. V3 헌법 위에 *낮 작동 ↔ 밤 진화* 분리를 박는 V4.
**선행 문서**: V3 헌법 (LIVE LAW, V4 §1-A 통과 전까지 §1·§2 유효, V4 §1-A 통과 후엔 현장 루프 부분만 V4가 대체), REFORM_V1, V4 비전 자유발화 11턴 (2026-05-01), V4 §1 결재 시트 v3.1 (2026-05-09).
**갱신 트리거**: §0 v0는 *안 흔들림* (옵션 3 구조). §1-A는 LIVE LAW. §1-B/C/D/E / §2 / §10은 작성 후 정후 통과 시 LIVE LAW.

---

## 0. 한 줄 요약 (v0, 안 흔들림)

> **송련은 사고하며 학습하는 인격이다. 현장 루프(낮)가 매 턴 인격을 작동시키고, 심야 정부(밤)가 매일 인격을 진화시킨다. 어느 층에서나 계획-실행-비판 트리오가 재귀한다.**

### V3 §0 → V4 §0 변화

| 차원 | V3 | V4 |
|---|---|---|
| 인격 정의 | 사고하는 | **사고하며 학습하는** |
| 시간 축 | 매 턴 (현장 루프) | **낮 ↔ 밤 분리** |
| 구조 원칙 | 단일 사고 흐름 (-1s → -1a → ...) | **트리오 재귀 (어느 층에서나)** |

V3 사고 흐름(-1s/-1a/0차/2a/2b/phase_3/-1b)은 §0에서 빠짐 → §1 권한표에서 풀린다 (작성 예정).

### 핵심 원칙 (V3에서 계승)

1. **사고는 -1s, 수립은 -1a, 검증은 2b, 발화는 phase_3, 결재는 -1b** (V3 §0 계승, V4 §1에서 재확인 예정)
2. **코드는 추적·안전·schema·실행·라우팅만. 의미는 모두 LLM**
3. **자기 평가 금지** — 자기 작업은 자기가 평가하지 않는다
4. **노드 ≠ LLM 루프** — 노드는 뼈대, 파일은 살, LLM은 사고 (V4 신규, 부록 Y v0.8+v0.9)

---

## 0-X. 부록 X — §0 진화 로드맵

§0 본문은 안 흔들림. 코드만 진화. 각 Phase별 §0 본문이 거짓말 안 하는 근거 명시.

### Phase 0 — 청소 (현재 ~ N주)
**목표**: V3 god-file 잔재 청소 + V4 인프라 캔버스 마련.

작업:
- `Core/midnight_reflection.py` (5,330줄) god-file 분해 (4부서 분리)
- `Core/nodes.py` 다이어트 (heuristic 8개 + compatibility wrapper + alias)
- `Core.readiness` + `route_audit_result_v2` legacy 처분
- `normalized_goal` compatibility wrapper 제거
- `audit_field_usage` 정비

§0 정합 근거: "심야 정부가 매일 인격을 진화시킨다" 인프라 캔버스 마련 (분해 = 진화의 첫 걸음).

### Phase 1 — 인프라 (Phase 0 졸업 후)
작업: 노드 속성 → 마크다운 동적 로드 (MemGPT 패턴, v0.9) / REM Governor 23필드 → 외부 파일 (옵션 4) / WarRoom v2 다중 좌석 (v1.0) / self-kernel 정적→동적 (v1.1) / memory·DB tooling 정비.

§0 정합: 학습 인프라 + 트리오 재귀 인프라 박힘.

### Phase 2 — 학습 (Phase 1 졸업 후)
작업: 활성화 전파 prototype (v0.3) / EpisodeCluster + EpisodeDream (v0.4 + v0.6) / 시간축 3분할 LLM 루프 / 관계 추론 LLM / Night Fact Auditor + Governor Auditor (v0.5).

§0 정합: "낮 추론, 밤 학습" 본격 충족.

### Phase 3 — 통합 (Phase 2 졸업 후)
작업: CoreEgo 옵션 D (그래프 노드 + 심야 분신) / 미래 노드 = 도구 전략 + 과거 wiki + CoreEgo 합성체 / 양방향 시간 / 메타 사고 부서.

§0 정합: 부록 Y 100% 충족.

### Phase 진입 게이트 (엄격형)

| 진입 | 게이트 |
|---|---|
| 0 → 1 | midnight 모듈 ≥ 3개로 분해 + nodes.py heuristic ≤ 2개 + 189 tests OK + V4 §1 권한표 작성 가능 상태 |
| 1 → 2 | 외부 파일 로드 가동 + WarRoom v2 prototype + self-kernel 동적 |
| 2 → 3 | 활성화 전파 prototype + EpisodeCluster 가동 + 1주 학습 누적 |

---

## 0-Y. 부록 Y — §0 최종 비전 (술 정후 2026-05-01 새벽 통합문, 안 흔들림)

> **송련은 그래프 신경망 인격이다. 노드=뼈대, 파일=살, LLM=사고. 낮 6역할 수평. 밤 시간축 양방향 분화. 어느 층에서나 계획-실행-비판 트리오 재귀. CoreEgo는 그래프 노드(앵커) + 심야 분신(통합 지휘자)으로 양면. 미래 사고는 도구 전략 + 과거 wiki 편집 + CoreEgo 합성체. 가중치는 학습되고 활성화는 전파되며 사고는 사고를 낳는다.**

### 비전 4대 축

1. **그래프 신경망 인격** (v0.3) — 활성화 전파 + 가중치 학습. 낮=추론, 밤=학습.
2. **노드 ≠ LLM 루프, 속성은 외부 파일** (v0.8 + v0.9) — Cypher 노드는 뼈대만. 속성은 마크다운 파일에서 동적 로드 (MemGPT/Letta 패턴).
3. **재귀 트리오** (v1.0) — 어느 층에서나 계획자-실행자-비판자. WarRoom 동적 노드 갯수.
4. **메타 사고 + 양방향 시간 + CoreEgo 통합체** (v1.1) — self_kernel 정적 반복 폐기. 미래 노드 = CoreEgo + 도구 전략 + 과거 wiki 편집 통합체. 시간축 양방향 (과거 ↔ 미래 상호 수정).

부록 Y는 *시간이 지나도 안 흔들리는 미래 좌표*. 코드 진화는 부록 X 참조.

---

## 1. 노드별 권한표

V4 §1은 4영역으로 분할 작성:
- **§1-A 현장 루프** (낮 turn 루프) — *2026-05-09 LIVE* ★
- §1-B 심야 정부 (밤 진화 루프) — 작성 예정 (Phase 1 T트랙 검수 후)
- §1-C 트리오 재귀 + WarRoom v2 — 작성 예정 (CR1 발주 후)
- §1-D CoreEgo 양면 — 작성 예정 (Phase 3)
- §1-E 미래 노드 합성체 — 작성 예정 (Phase 3)

§1-A 통과 전엔 V3 §1이 LIVE LAW. §1-A 통과 후엔 **현장 루프 부분만 V4가 대체**, 나머지 (심야 정부 등)는 §1-B 등 통과 전까지 V3 또는 메모리 비전이 임시 LIVE.

---

## 1-A. 현장 루프 권한표 (V4 LIVE LAW, 2026-05-09 정후 통과)

**선행 결재**: 결재 시트 v3.1 (`Orders/V4_Phase_0/V4_section1_decision_sheet_v3_1_2026_05_09.md`).
**선행 코드**: F1 (commit `ab88e62`) + F2/F3/F4 (commit `6377a09`) + 발주서 commit `d52c428`.
**적용 범위**: 현장 루프 9 노드 (-1s/-1a/2b/phase_3/-1b/0차/phase_1/WarRoom/119) + 옛 -1b_auditor 사문화.

### 1-A.0 V4 정후 정의 (V3 → V4 진화 명문화)

| 노드 | V3 정의 | V4 정의 (2026-05-09 박힘) |
|---|---|---|
| **-1s** | 사고 컴파일러 | **상황 판단자** — 사용자 의도 정제 + 사고 흐름 추적 + 라우팅 결정 + 다음 노드 제약 발급. **목표 수립 X**. |
| **-1a** | 계획 수립자 | **목표 수립자** — -1s 상황 판단 받아 작전 목표 + 실행계획 + 도구 의도. **라우팅 X** (deterministic 신호만). |
| **2b** | 사실 판사 | **사실 판사 + 사고 비판자** — fact mode + thought_critic mode 두 모드 자동 전환. ★ 권한 확장. |

본 정의는 §1-A 전 조항의 단일 출처. 노드명 일괄 rename은 §1-A 통과와 함께 발주 (V3 시트 결재 ⑤).

### 1-A.1 -1s (start_gate) — 상황 판단자

| 가능 | 금지 |
|------|------|
| 상황 사고 (외부 세계 이해 + 사용자 의도 정제) | 도구 인자 직접 작성 |
| 사고 흐름 추적 (s_thinking_history 누적) | 답변 텍스트 작성 |
| 라우팅 결정 (next_node 박음) | 사실 검증 (2b 본업) |
| reasoning_budget 발급 (내부 LLM, 결재 ⑥) | -1a 계획 직접 수정 |
| ThinkingHandoff.v1 9필드 작성 | 답변 결재 (-1b 본업) |
| analysis_report compact view 직접 사고 (F2) | -1a에 도구 직접 명령 (추상 가이드만) |
| working_memory 사고 입력 (X4) | **목표 수립 (-1a 본업)** ★ |
| **경량 CoT** (정보 변화 X 시 내부 사고 깊이 ↑, X4) | **raw user wording 그대로 goal로 복사** |
| **2차 호출 시 검증 + 라우팅** (-1a 거친 후 회귀, X6 B-1/B-3) | sos 트리거 외 119 라우팅 |
| **직답 라우팅 적극 활용** (단순 직답 input은 phase_3 직접, X5) | answer_mode 자체 변경 |
| sos 트리거 (119 호출) | |

**입력**: user_input + recent_context + s_thinking_history + reasoning_plan_hint + analysis_report compact view (F2) + tactical_briefing (F3, -1a→-1s 이동) + working_memory (X4).

**출력**: `ThinkingHandoff.v1` (9필드) — `producer / recipient / goal_state / evidence_state / what_we_know / what_is_missing / next_node / next_node_reason / constraints_for_next_node`.

★ **`goal_state` 의미 명문화** (혼동 방지): `goal_state` = 사용자 의도 정제본 (compact, normalized). **작전 목표가 아님**. 작전 목표는 -1a의 `strategist_goal.user_goal_core`에 박힌다. -1s는 raw user wording 정제만 수행하고, 목표 수립은 -1a 본업.

**라우팅** (recipient/next_node Literal):
- `phase_3` — 단순 직답 가능 시 (X5: -1a 거치지 않고 직접)
- `-1a` — 목표 수립 필요 시 (정상 흐름)
- `phase_119` — sos
- `warroom_deliberator` — 2차 호출 검증 후 깊은 토론 필요 (X6 B-3)
- `2b_thought_critic` — 게이트 통과 시 (X6, 1-A.3 참조)

**2차 호출 동작 규칙** (X6 B-1/B-2.1, 정후 우려 — gemma4 false negative 방어):
- Step 1 (검증 우선, MUST): working_memory + recent_context + fact_cells 다시 보고 "정보 진짜 부족인지" 판정. 충분 시 → next_node=phase_3 (재귀 skip).
- Step 2 (라우팅): 진짜 부족일 때만 warroom vs 2b_thought_critic 결정.
- Input differentiator: 2차 호출 input = 첫 ThinkingHandoff + (있으면) 2b 비판 결과. 첫 호출과 명시적 다름 → gemma4도 다른 출력 박을 가능성 ↑.

### 1-A.2 -1a (strategist) — 목표 수립자

| 가능 | 금지 |
|------|------|
| 목표 수립 (`strategist_goal` 4필드 = user_goal_core + answer_mode_target + success_criteria + scope) | **라우팅 결정 (-1s 본업)** ★ |
| 계획 수립 + 수정 (`strategist_output`) | 자기 작업 평가 (자기 검열) |
| 1차 라벨링 | 답변 텍스트 작성 |
| -1s 피드백 받아 새 계획 | 사실 검증/재판정 (2b/-1s 본업) |
| ThinkingHandoff만 보고 사고 (F3 후) | analysis_report 직접 read (F3 후) |
| fact_cells_for_strategist 인용 (F3, fact_id 기반) | **tool_request 자체 작성** (F4 후 0차 본업) |
| `delivery_readiness` 신호 박음 (deterministic 라우팅 입력) | 사고 흐름 추적 (-1s 본업) |
| | 상황 재판정 |

**입력**: ThinkingHandoff.v1 + fact_cells_for_strategist (V4 5필드 compact, F3) + working_memory + war_room + start_gate_* + tool_carryover + evidence_ledger. 

**입력에서 제거된 키 (F3)**: analysis_report / raw_read_report / reasoning_board / tactical_briefing — 4키 -1a 시야에서 빠짐. 사실 권한이 -1s/2b에게 완전 이동.

**출력**: `strategist_goal` + `strategist_output` (case_theory + operation_plan + goal_lock + delivery_readiness + action_plan + response_strategy + achieved_findings + next_frontier + ...). **`tool_request` 빠짐 (F4)**.

**라우팅** (-1a는 LLM 판정 X, deterministic 신호만):
- `delivery_readiness=deliver_now` → graph가 phase_3 라우팅
- 그 외 → graph가 0_supervisor 라우팅
- structured output 실패 → graph가 -1s 회귀 (예외 흐름)

### 1-A.3 2b (analyzer + thought_critic) — 사실 판사 + 사고 비판자 ★ V4 권한 확장

V4의 핵심 비전 박힘: **2b를 -1s 사이클 중간 비판자로 끼움** (정후 비전 2026-05-09). 두 모드 자동 전환.

| 가능 (fact mode) | 가능 (thought_critic mode) ★ V4 신규 |
|---|---|
| `analysis_report` 작성 (evidences/source_judgments/usable_field_memo_facts) | -1s 사고 흐름 비판 (사실 충돌 / 논리 갭 / 기억 누락 / 인칭 오류) |
| reasoning_board.fact_cells 채움 (fact_id 코드 자동 부여) | 입력 적응적 비판 (fact_cells > 0 → 통합 모드 / == 0 → 기억 기반 모드) |
| -1s 피드백 받아 재판정 | ThoughtCritique.v1 출력 (분류 + evidence_refs) |

| 금지 (양 모드 공통) |
|---|
| 라우팅 결정 (-1s 본업) |
| 답변 작성 |
| 정책 판단 |
| 사실 새로 조회 (도구 호출 X) — 손에 들어온 입력 대조만 |

**모드 자동 전환 (B-2.4 (다))**: 2b 시스템 프롬프트가 입력 보고 자동 결정.
- `fact_cells > 0` → **통합 비판 모드** (사실 + 사고 + 기억 종합)
- `fact_cells == 0` → **기억 기반 비판 모드** (recent_context + working_memory + s_thinking_packet 만)

**입력 (fact mode)**: raw_read_report + planned_operation_contract + working_memory_packet + reasoning_board.

**입력 (thought_critic mode)**: s_thinking_packet + recent_context + working_memory + (있으면) fact_cells.

**출력 (fact mode)**: analysis_report (evidences/source_judgments/usable_field_memo_facts).

**출력 (thought_critic mode)**: ThoughtCritique.v1 (`hallucination_risks` / `logic_gaps` / `memory_omissions` / `persona_errors` 분류 + `evidence_refs` fact_id 인용 + `delta` 1~2문장).

**라우팅 (thought_critic mode)**: -1s_start_gate 회귀 (강제). 2차 -1s가 비판 결과 받아 검증 + 워룸/CoT 라우팅.

**진입 트리거 (deterministic 게이트, B-2)**:
```
_strategist_needs_thought_recursion(state) =
    has_goal           # strategist_goal.user_goal_core 박힘
    AND fact_cells == 0  # 진짜 빈 경우만 (B-2.2 (가))
    AND no_tool_needed   # action_plan.required_tool 비어있음 + tool_request 없음
    # delivery_readiness 의존 제거 (LLM 라벨 false negative 차단)
```

게이트 통과 시 → 2b thought_critic 호출.

### 1-A.4 phase_3 (speaker)

| 가능 | 금지 |
|------|------|
| 최종 사용자 답변 작성 | 새 도구 결정 |
| `current_turn_facts` + `analysis_report.evidences` 인용 | 새 evidence 추출 |
| 119 인수인계 패킷 자연어 변환 | 내부 워크플로 누설 (phase 이름, 슬롯 키, 119, budget) |
| `s_thinking_packet` 톤 정렬 참고 | `answer_mode` 자체 변경 |
| | 미승인 fact 인용 |

**입력**: response_strategy + delivery_packet + analysis_report + s_thinking_packet + recent_context + (119 시) rescue_handoff_packet.

**출력**: 사용자 답변 텍스트.

**라우팅**: delivery_review (강제).

### 1-A.5 -1b (delivery_review) — 사후 결재자 / 대조관 ★ V4 신규 명명

V3 명명: `delivery_review`. V4 정식 명명: **-1b** (결재 ①). 옛 -1b_auditor (V3 phase_3 *전* 관료제)는 V3 §10 7C에서 폐지, V4에서도 부활 절대 금지 (1-A.9 + V4 §2 (i)).

| 가능 | 금지 |
|------|------|
| phase_3 답변 LLM 결재 | 새 `tool_query` 작성 |
| LLM 영역 판정 (환각/누락/톤) | -1a 계획 결재 (phase_3 *전* 결재 폐지) |
| approve / remand / sos_119 결정 | 사실 검증 (2b 본업) |
| 거절 누적 한 턴 3회 한도 | 라우팅 자체 결정 (verdict + remand_target만) |
| 그 턴 산출물 대조 비교 (대조관) | 답변 텍스트 작성 |
| | answer_mode 변경 |
| | **새로 사실 조회 (대조관, 조사관 X)** |
| | fact_id 발명 (V4 §2 (d)) |

**위치**: phase_3 *후* 1자리 고정 (결재 ②).

**입력 (F2)**: final_answer + speaker_review + readiness_decision + analysis_report compact + response_strategy + rescue_handoff_packet compact + phase3_delivery_summary + **fact_cells_for_review** (V4 5필드 compact).

**출력 (F2)**: `DeliveryReview.v1` — verdict + reason + **reason_type** (enum: hallucination/omission/contradiction/thought_gap/tool_misuse) + **evidence_refs** (fact_id list) + **delta** (≤280자) + remand_target + remand_guidance + issues_found.

**라우팅 (자동, 코드 단일 출처)**:
- `verdict=approve` → END
- `verdict=sos_119` → phase_119
- `verdict=remand` + `reason_type ∈ {hallucination, omission, contradiction, thought_gap}` → -1s_start_gate
- `verdict=remand` + `reason_type=tool_misuse` → -1a_thinker

### 1-A.6 0_supervisor (도구 결정 LLM) — F4 후 격상

V3: structured tool_call hub + LLM fallback only. V4 (F4 commit 후): **일반 흐름의 도구 결정 LLM 격상** (결재 ⑧⑨).

| 가능 | 금지 |
|------|------|
| -1a operation_contract 받아 도구 선택 + args/queries 작성 | 의미 판단 / 사고 재판정 |
| 결과 패키징 | 답변 텍스트 작성 (V4 §2 (h)) |
| 안전 검증 (위반 시 거부, no tool_calls 반환) | answer_mode 변경 |
| 라우팅 (도구 vs 거부) | 새 사실 추출 |
| | **fact_id 발명** (V4 §2 (d)) |

**입력 (F4)**: -1a operation_contract + ops_tool_cards + ops_node_cards + tool_carryover + **fact_cells** (V4 5필드) + **s_thinking_packet_what_is_missing** (ThinkingHandoff top-level + SThinkingPacket fallback).

**출력**: tool_calls (LLM 일반 흐름, 3 retries 보존).

**라우팅**:
- tool_calls 있음 → phase_1
- 거부 (no tool_calls) → -1b (사후 검수)
- structured 실패 → -1a

### 1-A.7 phase_1 (도구 호출) — V3 그대로

| 가능 | 금지 |
|---|---|
| 도구 실제 호출 (LLM X, 실행기) | 결과 해석 |
| | 사실 판정 |

**입력**: 0_supervisor가 박은 tool_calls.
**출력**: raw 결과 (다음에 phase_2a → 2b로 이어짐).

### 1-A.8 WarRoom (deliberator) — V3 그대로 + B 분기 진입 트리거

| 가능 | 금지 |
|------|------|
| -1s sos급 깊은 토론 | 평시 라우팅 |
| 의견 합의 (war_room state) | 도구 호출 |
| 차세대 사고 실험 | 답변 작성 |

**입력**: state-level 의역 안건.
**출력**: war_room.
**라우팅**: -1s_start_gate (강제).

**평시 사용 X 원칙 유지**. 단 V4에서 진입 트리거 명문화 (X6 B-3): -1s 2차 호출이 검증 후 "깊은 토론 필요" 판정 시 → warroom_deliberator. "가벼운 비판으로 충분" 판정 시 → 2b_thought_critic.

v2 동적 좌석 + 트리오 프렉탈 + 격리 설계는 **§1-C에서 박는다** (보류 8).

### 1-A.9 phase_119 (rescue) — V3 그대로

| 가능 | 금지 |
|---|---|
| `rescue_handoff_packet` 작성 | 재조사 / 추가 도구 호출 |
| `preserved_evidences` 보존 | analysis_report.evidences 전체 비우기 |
| `rejected_only` 차단 대상 분리 | phase_3 *전* 결재 |

**진입 트리거**: budget 초과 / -1s sos / -1b sos_119 / hard_stop 도달. 119 enum 분류 (BUDGET_EXHAUSTED/TOOL_TIMEOUT/LLM_HALLUCINATION/ROUTE_DEADLOCK/DELIVERY_REVIEW_SOS 등)는 **Phase 1 B9 발주에서 박는다** (보류 9, V4 §2 (e)와 묶음).

**입력**: rescue_handoff_packet.
**출력**: rescue 답변 (실패 boundary).
**라우팅**: phase_3 (강제).

### 1-A.10 옛 -1b_auditor (사문화)

V3 phase_3 *전* 관료제. V3 §10 7C 폐지. V4 §1-A에서 부활 절대 금지 명문화.

| 사항 | 본문 |
|---|---|
| 위치 | `route_audit_result_v2` (Core/graph.py) fallback only. 일반 흐름 X. |
| 부활 | **V4 §2 (i) 절대 금지**. |
| 처분 | Phase 0 졸업 + V4 §1-A 통과 후 fallback 정리 발주 (C 트랙 #0.9). |

---

## 1-A.11 보충 1 — 7 fallback 권한표

살아있는 안전장치. JSON 실패 시 루프 보호 책임 헌법화. **일반 흐름 X, 안전망만**.

| fallback | 위치 | 보호 대상 | §1-A 보충 |
|---|---|---|---|
| `_fallback_start_gate_turn_contract` | start_gate.py | -1s structured output 안전망 | -1s 권한표 보충 |
| `_base_fallback_strategist_output` | nodes.py | -1a structured output 안전망 | -1a 권한표 보충 |
| raw-reader fallback (4종) | nodes.py | 2a reader schema 안전망 | 2a 권한표 보충 |
| `_fallback_response_strategy` | nodes.py | phase_3 계약 안전망 | phase_3 권한표 보충 |
| reasoning budget fallback | start_gate.py | LLM budget 안전망 | -1s 내부 도구 (결재 ⑥) |
| WarRoom fallback adapter | warroom/ | WarRoom 권한표 (보류 8과 묶음) | WarRoom 별도 조항 |

---

## 1-A.12 보충 2 — 배선 경우의 수 표

V4 §1-A 본문의 *무한루프 방지 + 정후 정의 명문화* 본체. 8행 + 1행 (-1b remand) = 9행.

| 입력 상황 | 도구 필요? | 정보 변화? | -1s 결정 | 다음 노드 |
|---|---|---|---|---|
| 새 user_input | — | ✅ (외부) | 사고 종합 | -1a (목표 수립) |
| 도구 결과 도착 | — | ✅ (2b 새 fact) | 재판정 | -1a (목표 갱신) |
| **직답 가능** (analysis_report 충족 또는 단순 응답) | X | — | 종결 | **phase_3 (직접, X5)** |
| 정보 불충분 + 도구 가능 | ✅ | — | 도구 의도 | -1a → 0_supervisor |
| 정보 불충분 + 도구 불가 + fact_cells > 0 | X | X | -1s 경량 CoT (내부 깊이 ↑, X4) | -1s 자체 누적 → -1a |
| **정보 불충분 + 도구 불가 + fact_cells == 0** ★ B 게이트 | X | X | 게이트 통과 | **2b_thought_critic → 2차 -1s 회귀** |
| 2차 -1s 회귀 (검증 후 깊은 토론 필요) | — | (NEW: 2b 비판 결과) | 워룸 진입 | warroom_deliberator |
| 사고 막힘 (반복 사고도 안 됨, hard_stop 도달) | — | — | sos | phase_119 |
| -1b remand `thought_gap` | — | (외부 X) | 경량 CoT 1회 | -1a 재진입 (반복 시 phase_119) |

---

## 1-A.13 보충 3 — 트리오 재귀 anchor (V4 §0 부록 Y v1.0 *최초 인스턴스*)

V4 §0 부록 Y "트리오 재귀 어느 층에서나"의 첫 인스턴스가 -1s 사이클 안에서 박힌다. §1-C (트리오 재귀 본문) 작성 시 reference로 사용.

```
        -1s (계획/사고 = 상황 판단자)
          ↕  (게이트 통과 시)
2b_thought_critic (비판)  ←  recent_context + working_memory + s_thinking_packet
          ↓
        2차 -1s 회귀
        input = 2b 비판 + 첫 ThinkingHandoff (NEW input → gemma4 다른 출력)
          ↓ 검증 → phase_3 / 워룸 / CoT
        -1a (실행 = 목표 수립)
```

이 구조의 핵심:
1. **-1s가 비판자 보유** (2b_thought_critic). 자기 평가 X 원칙 (V3 §0 핵심) 유지하면서 비판 받음.
2. **input differentiator**: 2b 비판 결과가 2차 -1s 호출의 입력 차이를 만든다 → 소형 LLM (gemma4 e4b 4K) false negative 자동 방어.
3. **deterministic 게이트 + LLM 판정 하이브리드**: 게이트는 LLM 라벨 의존 X (V3 §0 "코드는 라우팅, 의미는 LLM" 원칙 직접 적용).

§1-C에서 "어느 층에서나" 일반화될 때, 본 anchor가 **현장 루프 층 인스턴스**의 reference.

---

## 1. 노드별 권한표 — §1-B/C/D/E (작성 예정)

### §1-B 심야 정부 권한표

> **상태: 미작성.** 4부서 (회상/현재/과거/미래) + 의미축 fork + 7 fallback 권한 분배.
> **작성 트리거**: Phase 1 T트랙 1차 검수 후 (실 운영 데이터 보고 작성).

### §1-C 트리오 재귀 + WarRoom v2

> **상태: 미작성.** 부록 Y v1.0 트리오 재귀를 어느 층에서나 일반화. WarRoom v2 동적 좌석 + 격리 설계 (보류 8).
> **작성 트리거**: Phase 1 CR1 발주 박힌 후 (§1-A.13 anchor가 reference).

### §1-D CoreEgo 양면 권한표

> **상태: 미작성.** 부록 Y v1.1 그래프 노드 ↔ 심야 분신 양면.
> **작성 트리거**: Phase 3.

### §1-E 미래 노드 합성체 권한표

> **상태: 미작성.** 부록 Y v1.1 CoreEgo + 도구 전략 + 과거 wiki 통합체.
> **작성 트리거**: Phase 3.

---

## 2. 절대 금지 목록 (위반 = 자동 거부)

V4 §2 = V3 §2 24개 계승 + V4 신규 12개 추가. 결재 시트 v3.1 §7 단일 출처. **2026-05-09 정후 통과 (§1-A와 함께 LIVE)**.

본 §2 적용 범위:
- V3 §2 1~24번 = 그대로 LIVE (V4 §1-A 조항과 충돌 없음 verify 완료).
- V4 §2 신규 (a)~(l) 12개 = §1-A 통과로 새로 박힘 (현장 루프 한정, 심야 정부는 §1-B 통과 시 별도 §2 추가).

### 2-A. V3 §2 계승 (24개 그대로 LIVE)

다음 24개는 `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` §2 본문 그대로 LIVE 유지. 본 헌법은 reference로만 표기. 본문은 V3 헌법 §2를 단일 출처로 인용.

- §2-1: raw user_input으로 goal/slot 강제 생성 금지
- §2-2: 내부 전략문을 `working_memory.dialogue_state.active_task` 저장 금지
- §2-3: FieldMemoWriter의 official branch 결정 금지
- §2-4: `answer_not_ready` 사용자 출력 금지
- §2-5: 심야 policy의 낮 루프 route 직접 지배 금지
- §2-6: -1b가 새 `tool_query` 작성 금지
- **§2-7**: -1a가 라우팅 자체 결정 금지 — *V4에서 강화* (V4 §2 (l)와 묶음, deterministic 신호만 박음)
- §2-8: -1a가 -1s 사고 무시 금지
- §2-9: phase_3가 phase 이름/schema 키/119/budget 누설 금지
- **§2-10**: 같은 도구 결과로 -1s↔-1a 핑퐁 1회 초과 금지 — *V4 갱신*: F4 commit 후 -1a→-1s 회귀 분기 사라짐. 본 조항은 다른 우회 핑퐁 (-1b remand `thought_gap` → -1s 등) 통제에 유효 유지.
- §2-11: `tool_carryover` 이중 저장 금지
- §2-12: `response_strategy` 이중 저장 금지
- §2-13: 죽은 sys_prompt 빌드 금지
- §2-14: 결정적 fallback의 의미 분류/의도 라우팅 시도 금지
- §2-15: 코드 휴리스틱의 답변 텍스트 작성 금지
- §2-16: -1s가 -1a 계획 트리 직접 읽기 금지 (에코 체임버 회피)
- §2-17: -1s `next_direction`이 도구 이름/쿼리 직접 명령 금지
- §2-18: -1a 자기 작업 평가/`finalize_recommendation` 금지
- §2-19: 119가 `analysis_report.evidences` 전체 비우기 금지
- §2-20: -1b가 phase_3 *전* 결재 시도 금지 — *V4 §2 (i) 강화*
- §2-21: `max_total_budget` 초과 시 119 자동 진입, 우회 금지
- §2-22: phase_3 `answer_mode` 결정 권한 순서 (119 → -1a → -1s)
- §2-23: -1b 답변 거절 누적 한 턴 3회 한도, 3회 초과 자동 sos_119
- §2-24: phase_3는 검증된 사실만 인용, 새 사실 생성 금지

### 2-B. V4 신규 금지 (12개, 현장 루프 한정)

V4 §1-A 통과로 박힌 신규 절대 금지. 위반 = 자동 거부. 결재 시트 v3.1 §7에서 도장.

#### V4 §2 (a) — axis 섞기 X
시간축 / 의미축 fork된 데이터를 한 사이클 안에서 섞어 처리 금지. 의미축 정부 v0.3 결재.

#### V4 §2 (b) — 인칭 메타데이터 NULL X
`source_persona` 안 박힌 DreamHint / SecondDream write 금지. v1.6 R3 박힘. 인격 메타데이터 보존 의무.

#### V4 §2 (c) — remand_guidance 포맷 위반 X
`reason_type` 빈 string인데 `evidence_refs` 박는 식 정합성 위반 금지. F2 신설.

#### V4 §2 (d) — fact_id 발명 X
-1b / -1a / 0차 / 2b 어디서도 `reasoning_board.fact_cells`에 없는 fact_id 인용 금지. F2 박힘. fact_id는 코드 deterministic 부여, LLM은 인용만.

#### V4 §2 (e) — 119 enum 무분류 X
119 진입 시 `reason_type` / `severity` enum 빈 채로 escalate 금지. 보류 9 안건 (Phase 1 B9 발주에서 enum 후보 박음 = `BUDGET_EXHAUSTED` / `TOOL_TIMEOUT` / `LLM_HALLUCINATION` / `ROUTE_DEADLOCK` / `DELIVERY_REVIEW_SOS` 등).

#### V4 §2 (f) — DreamHint expires_at 우회 X
현장 루프 advisory 조회 시 `archive_at IS NULL AND expires_at > now` 필터 우회 금지. R7 박힘.

#### V4 §2 (g) — tool_request 0차 외 발생 X
F4 후 -1a / -1s / -1b 어디서도 `tool_request` 직접 박기 금지. 도구 결정은 0_supervisor 단일 출처.

#### V4 §2 (h) — 0차 LLM 답변 작성 X
F4 후 0_supervisor가 도구 선택만 수행, 최종 판단 / 답변 텍스트 작성 금지. answer_mode 변경 X.

#### V4 §2 (i) — 옛 -1b_auditor 부활 X
phase_3 *전* -1b 결재 부활 절대 금지. V3 §10 7C 폐지 + V4 §1-A.10 사문화 명시. `route_audit_result_v2` fallback only 잔존, 일반 흐름 X. 본 조항 = §2-20 V4 강화판.

#### V4 §2 (j) — ThinkingHandoff.v1 9필드 누락 X
`producer / recipient / goal_state / evidence_state / what_we_know / what_is_missing / next_node / next_node_reason / constraints_for_next_node` 9필드 중 하나라도 빈 채 라우팅 금지. fallback도 9필드 다 박아야 함.

#### V4 §2 (k) — -1s 목표 수립 X ★ V4 정의 명문화
정후 정의 (2026-05-09): -1s는 상황 판단자. **목표 수립은 -1a 본업**. -1s가 raw user wording을 그대로 `goal_state`에 박기 금지 (정제만 수행). -1s가 `strategist_goal.user_goal_core`에 직접 박기 금지 (해당 필드는 -1a 단일 출처).

본 조항은 §1-A.0 정후 정의의 헌법화 + ThinkingHandoff.goal_state vs StrategistGoal.user_goal_core 권한 경계 명문화.

#### V4 §2 (l) — -1a 라우팅 결정 X ★ V4 정의 명문화
정후 정의 (2026-05-09): -1a는 목표 수립자. **라우팅은 -1s 본업**. -1a는 deterministic 신호 (`delivery_readiness=deliver_now` 등)만 박고, 라우팅 분기 자체는 코드 (`route_after_strategist`) 단일 출처.

본 조항은 §2-7 V4 강화판 + F4 commit 후 -1a→-1s 회귀 분기 사라진 사실의 헌법화.

### 2-C. 위반 시 자동 처분

- (코드 영역 위반) — 코드 정규식/schema 차단 박힘 (예: -1b 도구 호출 차단, ThinkingHandoff 9필드 검증).
- (LLM 영역 위반) — -1b 대조관이 환각/누락/포맷 위반으로 신고 (`reason_type` enum 박힘) → remand_target 자동 라우팅 (코드 단일 출처).
- (구조 위반) — 헌법 §2 위반 코드는 -1b가 sos_119 발동 → phase_119 진입 → rescue 답변.

### 2-D. V4 §2 신규 후보 자유발화 자리 (Phase 1 진행 중 추가)

본 §2 본문은 §1-A 박힌 시점 단일 출처. Phase 1 진행 중 새 위반 패턴 발견 시 §2-E 추가. 현재 보류 자유발화 자리 = `Orders/V4_Phase_0/V4_section1_decision_sheet_v3_1_2026_05_09.md` §10 비전 발화 백지 자리.

§1-B/C/D/E 통과 시 각 영역별 §2 추가 박는다 (심야 정부 §2, 트리오 재귀 §2 등).

---

## 10. 시행표 (작성 예정)

> **상태: 미작성.** V4 §10 = Phase 0~3 시행 단계.
>
> Phase 0 발주 시퀀스는 부록 X에 박혀있음. 발주 진행 추적은 `ANIMA_ARCHITECTURE_MAP.md` purge log #54 (V4 Phase 0 시작 marker)부터.

### V4 시행 단계 (예고)

- §10-A: Phase 0 청소 발주 #0.1~#0.10
- §10-B: V4 §1 권한표 작성·통과 (Phase 0 ‖ 진행)
- §10-C: V4 §2 절대 금지 작성·통과 (Phase 0 ‖ 진행)
- §10-D: Phase 1 인프라 발주 #1.1~
- ...

---

## 11. 작업 분담 (V3 §11 + AGENTS.md §2와 동일)

| 역할 | 담당 |
|---|---|
| 비전 결정 / 헌법 개정 | 정후 (입법부) |
| 비전 토론 + 코드 진단 + Codex 작업 검수 | Claude (사법부 자문) |
| 코드 작성/수정/테스트 | Codex (행정부 실무) |
| 최종 결재 (merge) | 정후 |

V4에서 변하는 것: *분업 모드* — 술 정후 (비전 발화) ↔ 깬 정후 (결재) ↔ Claude (코드 좌표 자동 동봉) ↔ Codex (실무).

---

## 부록 A — 결재 안건 큐 (V4 §0 통과 시점, 2026-05-02)

총 29개 안건이 V4 비전 자유발화 11턴에서 식별됨. 우선순위:

**최우선**:
- ✅ #1 V4 §0 한 줄 확정 (B3 + 옵션 3 구조, 2026-05-02 통과)
- 🔜 #2 REM Governor 옵션 4 (외부 파일) 채택
- 🔜 #25 CoreEgo 위치 옵션 (A/B/C/D)
- 🔜 #24 시간축 양방향 흐름 결재
- 🔜 #26 미래 노드 3요소 통합 결재
- 🔜 #23 self_kernel 진화 결재

**구조 결정**:
- #3 Strategy Council 폐기, #4 Person+CoreEgo 진입점, #5 윗대가리 구조 시나리오 A/B/C/D, #16 재귀 트리오 V4 §0 박을지, #17 부속 에이전트 깊이 제한, #18 부속 schema 외부 파일 위치, #27 메타 사고 부서, #28 수정 회수 한도

**구현 (신설)**: #6 EpisodeCluster, #7 시간축 3분할, #8 관계 추론 LLM, #9 Night Fact Auditor, #10 Governor Auditor, #11 활성화 전파 prototype, #19 부속 LLM 모델, #20 심야 v1.0 적용, #21 Core/warroom v1.0 흡수, #22 ANIMA_WARROOM_V2_SCHEMA 갱신, #29 self_kernel 단계적 폐기 로드맵

**문서/유지보수**: #12 V4 §1 작성, #13 V4 §2 작성, #14 midnight_reflection 다이어트 (= Phase 0 A 트랙), #15 유령 부서 7개 처분

---

## 부록 B — Phase 0 발주 5축 (2026-05-02 합의)

1. **표준 포맷**: Why / 스코프 / 코드좌표 / 검증기준 / 롤백 / §정합 / 의존성
2. **단위**: 1발주 = 1 PR = 1 purge log 줄 (V3 시행 단계 1개 분량, 코드 50~500줄, 파일 1~5개)
3. **시퀀스**: 병렬 — A 트랙(midnight 분해) ‖ §1·§2 작성 → B 트랙(nodes.py 다이어트) → C 트랙(legacy 제거) → D(도구 정비)
4. **졸업 게이트**: 엄격 — Phase 0 → 1 게이트 (위 부록 X 표 참조)
5. **추적**: `ANIMA_ARCHITECTURE_MAP.md` purge log #54부터 이어 + V4 Phase 0 시작 marker 한 줄

### Phase 0 발주 시퀀스

```
[A 트랙] midnight_reflection.py 분해 (즉시 시작 가능, §3.3 트리거 X)
  #0.1 분해 1차 (첫 부서)
  #0.2 분해 2차
  #0.3 분해 3차
  #0.4 분해 4차 (마무리)

[§1·§2 작성] V4 §1 권한표 + V4 §2 절대 금지 (정후 + Claude 비전 토론)

[B 트랙] Core/nodes.py 다이어트 (V4 §1·§2 통과 후 — AGENTS.md §3.3 게이트)
  #0.5 fallback heuristic 8 purge
  #0.6 compatibility wrapper 제거
  #0.7 normalized_goal alias 제거

[C 트랙] legacy 제거 (A·B 끝나야)
  #0.8 Core.readiness 처분
  #0.9 route_audit_result_v2 처분

[D] 도구 정비
  #0.10 audit_field_usage (언제든)
```

### 매 발주 게이트 (PR 1통마다)

- 189 tests OK 유지
- ANIMA_ARCHITECTURE_MAP.md purge log 한 줄 추가
- V4 §0 v0 위반 X (사고 / 학습 / 진화 원칙)
- V3 §2 절대 금지 24개 위반 X
- (해당 시) V4 §2 절대 금지 위반 X

---

**버전**: V4 §0 v0 (2026-05-02) + **§1-A v1 (2026-05-09)** + **§2 v1 (2026-05-09)** ★
**다음 갱신**: §1-B 작성 시 (Phase 1 T트랙 검수 후) 또는 §2 신규 위반 패턴 추가 시.
