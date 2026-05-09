*[한국어](ANIMA_REFORM_V1.md) | [English](ANIMA_REFORM_V1.en.md)*

# ANIMA Reform V1

> Document status: BACKGROUND / ABSORBED.
> Use this for reform philosophy and historical intent. If it conflicts with
> `ANIMA_FIELD_LOOP_V2_CONSTITUTION.md`, the V2 constitution wins.

이 문서는 ANIMA의 현재 사고 루프를 "더 많이 생각하는 시스템"이 아니라 "제때 수렴하고, 책임이 분리되고, 환각 없이 전달하는 시스템"으로 개혁하기 위한 1차 기준서다.

## 1. 문제 정의

현재 ANIMA의 핵심 병은 아래와 같다.

1. 같은 상태로도 루프가 다시 돈다.
2. `-1a`는 계획을 세우지만, 질문에 맞는 수렴보다 옆으로 확장하는 경향이 있다.
3. `-1b`는 결재자여야 하는데 초반 상황 해석까지 떠안아 과적재된다.
4. `2b`는 독립성은 있지만 관점 패킷이 약해 평면적인 해석으로 되돌아가기 쉽다.
5. `3차`는 좋은 내부 결론보다 빈약한 송달 패킷을 받아 보수적 generic 답으로 미끄러진다.
6. 시스템은 "몇 번 돌았는가"는 보지만 "이번 루프에서 무엇이 새로 밝혀졌는가"는 약하게 본다.

한 줄로 줄이면:

`현재 병은 사고 부족보다 상태 전이와 책임 분배의 문제다.`

## 2. 개혁 목표

개혁 목표는 다섯 가지다.

1. 시작은 빠르게, 계획은 깊게, 결재는 엄격하게.
2. 같은 입력과 같은 근거로 같은 사고를 반복하지 않기.
3. 연속 사고가 "연속 재포장"이 아니라 "연속 수렴"이 되게 하기.
4. 3차는 말만 하게 하고, 판단과 반려는 그 전에 끝내기.
5. 추후 심야 성찰이 이 구조를 자가 증류할 수 있도록 상태 계약을 먼저 정비하기.

## 3. 계층별 책임

### `-1s` Start Gate

역할:

- 고속 메타인지 센서
- 지금 바로 답해도 되는지
- grounding이 먼저인지
- planning이 먼저인지
- 긴급/특수 케이스인지

해야 하는 일:

- `answerability`
- `recommended_handler`
- `confidence`
- `risk_flags`
- `why_short`

하면 안 되는 일:

- 깊은 의미 해석
- 장기 계획 수립
- 도구 계획 세부 설계
- 판결 흉내

원칙:

`-1s는 작고 똑똑해야지, 무거워지면 안 된다.`

### `-1a` Strategist

역할:

- 초기 상황 파악의 주도권
- goal lock 고정
- operation contract 작성
- 근거 획득 후 결론 조출
- 다음 frontier 설계

매 턴 반드시 답해야 하는 네 가지:

1. 이번 루프에서 새로 얻은 사실은 무엇인가?
2. 그 사실로 현재 사용자 질문에 어디까지 답할 수 있는가?
3. 지금 결론을 조출해야 하는가?
4. 아니라면 다음 작업은 이전 작업과 무엇이 달라야 하는가?

해야 하는 일:

- `goal_lock`
- `action_plan`
- `operation_contract`
- `achieved_findings`
- `convergence_state`
- `delivery_readiness`
- `next_frontier`

하면 안 되는 일:

- 질문 축 무시하고 사회적 영향/윤리 등으로 자동 확장
- grounded findings가 충분한데도 계속 gathering 유지
- 이전 계획을 그대로 반복

원칙:

`-1a는 planner가 아니라 convergence planner여야 한다.`

### `2a` Reader

역할:

- 원문 읽기
- raw grounding 확보
- artifact fast path / deterministic parser 우선

해야 하는 일:

- `raw_read_report`
- `read_mode`
- `read_focus`
- `source_relay_packet`

하면 안 되는 일:

- 해석을 두껍게 올리기
- 계획 짜기
- 답변 수렴 판단

원칙:

`2a는 읽기만 한다.`

### `2b` Critic / Examiner

역할:

- fact-first 진단
- evidence gap 진단
- lens packet을 검증 대상으로 받아 다각적으로 검토

해야 하는 일:

- `analysis_report`
- `evidences`
- `source_judgments`
- `recommended_action`
- `objections`

추가 원칙:

- `critic_lens_packet`은 정답이 아니라 검토용 lens다.
- `-1a`의 결론을 복사하면 안 된다.

하면 안 되는 일:

- 도구 계획 짜기
- 마음대로 확장 검색 제안하기
- 사용자의 감정이나 기획을 근거 없이 과잉 일반화하기

원칙:

`2b는 독립적이어야 하지만 맹목적이면 안 된다.`

### `-1b` Final Judge

역할:

- 후반 결재
- 반려
- 루프 차단
- 송달 적합성 검사

봐야 하는 것:

- 새 근거가 생겼는가
- 새 계획이 생겼는가
- 질문 범위가 줄었는가
- 같은 작업을 반복하는가
- 이 packet이 지금 질문에 직접 답하는가

하면 안 되는 일:

- 초반 상황 해석을 혼자 떠안기
- 같은 analysis 상태로 `-1a` refresh를 무한 반복하기
- 좋은 memo를 3차 packet으로 승격하지 못한 채 흘려보내기

원칙:

`-1b는 탐정이 아니라 결재자다.`

### `3차` Speaker

역할:

- `delivery_packet` 낭독
- 허가된 자유도 안에서 말하기

해야 하는 일:

- `final_answer_brief`
- `approved_fact_cells`
- `approved_claims`
- `delivery_freedom_mode`

하면 안 되는 일:

- 질문을 다시 해석하기
- 계획 재수립하기
- generic narrowing follow-up을 자동 생성하기

원칙:

`3차는 똑똑한 판단자보다 정직한 renderer여야 한다.`

## 4. 필수 상태 계약

아래 필드는 개혁 이후 모든 사고가 공통으로 의존해야 한다.

### Start Layer

- `start_gate_review`
  - `answerability`
  - `recommended_handler`
  - `confidence`
  - `risk_flags`
  - `why_short`

### Strategic Layer

- `goal_lock`
  - `user_goal_core`
  - `answer_shape`
  - `must_not_expand_to`

- `action_plan`
  - `current_step_goal`
  - `required_tool`
  - `next_steps_forecast`
  - `operation_contract`

- `operation_contract`
  - `operation_kind`
  - `target_scope`
  - `query_variant`
  - `novelty_requirement`

- `achieved_findings`
- `convergence_state`
- `delivery_readiness`
- `next_frontier`

### Execution Layer

- `execution_trace`
  - `executed_tool`
  - `tool_args_signature`
  - `read_mode`
  - `read_focus`
  - `analysis_focus`
  - `source_ids`
  - `evidence_count`

### Critic Layer

- `critic_lens_packet`
  - `must_answer_user_goal`
  - `must_not_expand_to`
  - `lens_candidates`
  - `current_loop_delta`
  - `critic_task`

- `strategist_objection_packet`
  - `has_objection`
  - `suspected_owner`
  - `objection_text`
  - `review_focus`

### Progress Layer

- `progress_markers`
  - `last_combined_signature`
  - `last_operation_signature`
  - `last_refresh_analysis_signature`
  - `stalled_repeats`
  - `same_operation_repeats`

### Delivery Layer

- `delivery_packet`
  - `final_answer_brief`
  - `approved_fact_cells`
  - `approved_claims`
  - `must_avoid_claims`
  - `delivery_freedom_mode`
  - `followup_instruction`

## 5. 금지 행위

### 전 계층 공통

1. 같은 근거 상태로 같은 계획을 반복하지 않는다.
2. 새 근거 없이 새 결론인 척 하지 않는다.
3. 현재 사용자 질문보다 오래된 맥락을 우선하지 않는다.

### `-1a`

1. grounded findings가 충분한데도 `gathering` 유지 금지
2. `goal_lock`을 중간에 다른 목표로 바꾸는 것 금지
3. 질문보다 더 큰 사회적 서사로 자동 확장 금지

### `2b`

1. `-1a`의 결론을 정답처럼 복붙 금지
2. 근거 없는 심리 일반화 금지
3. 계획 역할 침범 금지

### `-1b`

1. 같은 `analysis_signature`에 대해 refresh 여러 번 금지
2. 좋은 결론을 3차 packet으로 승격하지 못한 채 phase_3 통과 금지
3. 결재 대신 초반 상황 해석을 과하게 떠안는 것 금지

### `3차`

1. grounded delivery 뒤 generic narrowing follow-up 금지
2. 질문 범위를 다시 사용자에게 떠넘기는 비답변 금지
3. 내부 계층 메모를 자기식으로 재해석하는 것 금지

## 6. 루프 법칙

개혁 이후 루프는 아래 규칙을 따른다.

1. 같은 `analysis_signature`에 대한 `-1b -> -1a refresh`는 1회만 허용한다.
2. 같은 `operation_contract + execution_trace`가 반복되면 재실행 금지한다.
3. 다음 셋 중 하나가 없으면 재루프를 금지한다.
   - 새 근거
   - 새 계획
   - 더 좁아진 범위
4. `2b == COMPLETED`이고 `goal_lock`을 충족하는 grounded findings가 있으면 수렴을 우선한다.
5. `proposal_1_to_3`, `fit_summary`, `feature_summary`, `findings_first`는 완결형 answer shape로 간주한다.

## 7. 3차 자유도 모드

3차는 아래 다섯 모드만 가진다.

- `grounded`
- `supportive_free`
- `proposal`
- `identity_direct`
- `answer_not_ready`

판사가 이 모드를 명시적으로 내려줘야 하며, 3차는 추측으로 바꾸지 않는다.

추가 규칙:

- `proposal`에서 generic follow-up 금지
- `grounded`에서 범위 축소 질문 금지
- `identity_direct`에서 기능 한계 설명 금지

## 8. 단계별 이행 순서

### Phase A: 책임 분리

1. `START -> -1s -> -1a` 구조 고정
2. `-1b`를 후반 결재자 역할로 축소
3. `3차`를 packet renderer로 단순화

### Phase B: 수렴 계약

1. `goal_lock`
2. `convergence_state`
3. `delivery_readiness`
4. `achieved_findings`

이 네 필드를 `-1a` 필수 산출물로 강제

### Phase C: critic 다각화

1. `-1a -> -1b -> 2b` lens packet 정식화
2. `2b`는 그 lens를 evidence로 검증
3. `-1a`는 `2b`에 대한 objection packet 생성 가능

### Phase D: 루프 통제

1. refresh latch
2. same-operation 차단
3. generic speaker follow-up 반려
4. memo findings -> `final_answer_brief` 승격

### Phase E: 심야 성찰 연동

이 단계는 나중에 한다.

심야 성찰은 아래를 학습적으로 보강해야 한다.

- 어떤 질문은 즉답 가능한지
- 어떤 루프가 진척을 냈는지
- 어떤 반려가 실제로 유효했는지
- 어떤 delivery mode가 잘 맞았는지

## 9. 성공 판정 기준

아래가 만족되면 Reform V1이 성공이다.

1. `오늘 할 일 추천` 질문에서 `2b COMPLETED` 후 즉시 `proposal` 수렴
2. `기획에 부합하는 기능` 질문에서 사회적 영향 장광설 없이 기능 요약
3. 같은 analysis 상태에서 `-1a/-1b` 왕복 1회 초과 금지
4. 3차가 grounded answer 뒤 generic narrowing follow-up을 붙이지 않음
5. correction 턴에서 stale topic이 재유입되지 않음

## 10. 최종 원칙

ANIMA는 "생각을 길게 하는 시스템"이 아니라 아래를 만족해야 한다.

1. 지금 질문을 정확히 붙잡는다.
2. 새 근거의 delta를 계산한다.
3. 적절한 시점에 결론을 조출한다.
4. 더 파야 할 때는 이전과 다른 작업을 지시한다.
5. 마지막엔 packet만 말한다.

한 줄 최종 원칙:

`연속 사고의 핵심은 더 오래 생각하는 것이 아니라, 목표를 고정하고, 변화량을 계산하고, 제때 수렴하는 것이다.`
