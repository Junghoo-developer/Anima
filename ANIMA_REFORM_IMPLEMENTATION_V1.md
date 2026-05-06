# ANIMA Reform Implementation V1

> Document status: BACKGROUND / PARTIALLY IMPLEMENTED.
> Use this for historical implementation slices. Current code surgery is ruled
> by `ANIMA_FIELD_LOOP_V2_CONSTITUTION.md` and tracked in
> `ANIMA_ARCHITECTURE_MAP.md`.

이 문서는 [ANIMA_REFORM_V1](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/ANIMA_REFORM_V1.md)을 실제 코드 작업 단위로 쪼갠 1차 이행안이다.

목표는 한 번에 모든 걸 갈아엎는 것이 아니라, 아래 네 가지를 순서대로 고정하는 것이다.

1. 시작 판단과 후반 결재를 분리한다.
2. `-1a`를 진짜 수렴형 계획 엔진으로 만든다.
3. `2b`가 독립성을 유지하면서도 관점 다양성을 얻도록 만든다.
4. `3차`를 똑똑한 해석자가 아니라 정직한 renderer로 축소한다.

## 1. 현재 기준선

현재 코드에서 이미 깔려 있는 기반은 아래와 같다.

- 시작 게이트: [Core/graph.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/graph.py)
- 시작 계층: [Core/nodes.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/nodes.py) `phase_minus_1s_start_gate`
- 전략가: [Core/nodes.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/nodes.py) `phase_minus_1a_thinker`
- 최종 판사: [Core/nodes.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/nodes.py) `phase_minus_1b_auditor`
- 최종 화자: [Core/nodes.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/nodes.py) `phase_3_validator`
- 공통 상태판: [Core/state.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/state.py), [main.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/main.py)

즉 개혁은 "아예 새 시스템 만들기"보다 "이미 있는 구조를 책임에 맞게 수술하기"에 가깝다.

## 2. 이행 원칙

### 원칙 A: 한 번에 하나의 축만 바꾼다

- 라우팅
- 상태 계약
- 판사 결재
- 화자 송달

이 네 축을 동시에 크게 건드리면 회귀 원인을 추적하기 어려워진다.

### 원칙 B: 증상 패치보다 계약을 먼저 고친다

조건문을 더 붙이는 방식은 최후순위다.
먼저 아래 계약을 고정한다.

- `goal_lock`
- `convergence_state`
- `delivery_readiness`
- `execution_trace`
- `delivery_packet`

### 원칙 C: 각 단계마다 "멈춰야 하는 기준"을 둔다

각 이행 단계는 아래 둘 중 하나가 보이면 바로 멈추고 재검토한다.

- 같은 analysis 상태에서 새 루프가 계속 허용됨
- 3차가 grounded findings를 받고도 generic non-answer를 말함

## 3. 1차 이행 순서

## 3A. 다음 단계

`Sleep Stack V1`은 다음 문서를 기준으로 진행한다.

- [ANIMA_SLEEP_STACK_V1.md](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/ANIMA_SLEEP_STACK_V1.md)

그리고 그 다음 구조 개혁은 아래 문서 기준으로 확장한다.

- [ANIMA_SLEEP_STACK_V2.md](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/ANIMA_SLEEP_STACK_V2.md)

이 단계의 핵심은 아래 다섯 가지다.

1. `REMPlan` 단계 스키마 만들기
2. `2차 꿈` 입력을 `Dream + TurnProcess + PhaseSnapshot + REMPlan`으로 확장
3. `RoutePolicy / ToolDoctrine` 노드 추가
4. `0차`를 정책 조회 + 실행기로 축소
5. 저가치 추측 노드 비영속화

그리고 다음 보강 축은 아래다.

6. `REMPlan`을 `REMGovernor` 총괄 설계 계층으로 승격
7. `Phase7`를 coverage auditor로 강화
8. `0차`가 하드코딩보다 `RoutePolicy / ToolDoctrine`를 우선 따르게 만들기

### Slice 1. 입구와 결재의 역할 고정

목표:

- `-1s`는 tiny gate만 맡는다.
- `-1b`는 후반 결재만 맡는다.
- 비단순 턴은 거의 전부 `-1a`로 보내는 구조를 고정한다.

수정 대상:

- [Core/graph.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/graph.py)
- [Core/nodes.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/nodes.py)

필수 확인:

- `START -> -1s -> -1a`가 기본 경로여야 한다.
- `-1s`는 identity, 짧은 인사, 아주 얇은 direct reply만 `phase_3`로 보낸다.
- `-1b`는 초반 해석을 새로 하지 않고, 이미 있는 계획/분석/진척 상태를 본다.

완료 기준:

- `오늘은 우리 뭐할까`
- `ANIMA 부가자료 읽고 오늘 할 일을 추천해줘`
- `다시 찾아봐`

이 세 입력에서 `-1s`가 장광설 없이 handler만 빠르게 정한다.

### Slice 2. `-1a`를 수렴형 계획 엔진으로 고정

목표:

- `-1a`가 계획만 만드는 것이 아니라, 새 근거를 받으면 결론 조출 여부를 판단하게 한다.
- `goal_lock`이 중간에 옆으로 새지 않게 한다.

수정 대상:

- [Core/nodes.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/nodes.py)
- 필요 시 [Core/state.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/state.py)

필수 산출물:

- `goal_lock`
- `achieved_findings`
- `convergence_state`
- `delivery_readiness`
- `next_frontier`

필수 규칙:

1. grounded findings가 질문에 직접 답하면 `deliver_now`
2. grounded findings가 부족하면 `need_one_more_source` 또는 `need_targeted_deeper_read`
3. 질문 축과 무관한 사회적 영향/윤리 확장 금지

완료 기준:

- `오늘 할 일 추천` 질문에서 `answer_shape=proposal_1_to_3`
- `기획에 부합하는 기능` 질문에서 `answer_shape=fit_summary`
- `2b COMPLETED` 후 `-1a`가 gathering만 반복하지 않고 deliverable로 접힘

### Slice 3. `2b`에 검열된 lens packet 정식 도입

목표:

- `2b`가 평면 해석으로 반복되지 않게 한다.
- 그러나 `-1a`의 결론을 그대로 복사하지 않게 한다.

수정 대상:

- [Core/nodes.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/nodes.py)
- [Core/state.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/state.py)
- 필요 시 [main.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/main.py)

필수 상태:

- `critic_lens_packet`
- `strategist_objection_packet`

필수 규칙:

- `-1a`는 결론이 아니라 관점 후보만 제안
- `-1b`는 그것을 비판적으로 정제
- `2b`는 lens를 evidence로 검증하고, 틀리면 기각

완료 기준:

- `오늘 할 일 추천` 질문에서 `2b`가 기능 설명 일반론보다 "오늘 가능한 제안 축"을 우선 검토
- `기획 적합성` 질문에서 `2b`가 사회 영향 장광설보다 기능 적합성 lens를 우선 검증

### Slice 4. 루프 통제 계약 고정

목표:

- 같은 상태 반복을 구조적으로 금지한다.
- refresh, 재독, 재계획이 모두 "새 변화"를 동반할 때만 허용되게 한다.

수정 대상:

- [Core/nodes.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/nodes.py)
- [Core/state.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/state.py)
- 필요 시 [main.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/main.py)

필수 상태:

- `execution_trace`
- `progress_markers.last_combined_signature`
- `progress_markers.last_operation_signature`
- `progress_markers.last_refresh_analysis_signature`
- `progress_markers.stalled_repeats`
- `progress_markers.same_operation_repeats`

필수 규칙:

1. 같은 `analysis_signature`에 대한 `-1b -> -1a refresh`는 1회
2. 같은 `operation_contract + execution_trace` 반복 금지
3. 새 근거, 새 계획, 더 좁아진 범위 중 하나 없으면 재루프 금지

완료 기준:

- `-1a <-> -1b` 왕복이 같은 분석 상태로 두 번 이상 반복되지 않음
- 같은 artifact 재독이 자동으로 두 번, 세 번 이어지지 않음

### Slice 5. 3차를 renderer로 축소

목표:

- 3차가 다시 질문을 해석하지 않게 한다.
- 좋은 내부 결론을 그대로 말하게 한다.

수정 대상:

- [Core/nodes.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/nodes.py)
- [Core/speaker_guards.py](c:/Users/peter/OneDrive/바탕%20화면/SongRyeon_Project/Core/speaker_guards.py)

필수 상태:

- `delivery_packet`
- `delivery_freedom_mode`

필수 규칙:

1. `delivery_packet.final_answer_brief` 없으면 반려
2. grounded delivery 뒤 generic narrowing follow-up 금지
3. `-1b memo`의 핵심 findings는 packet으로 승격되어야 함

완료 기준:

- `ANIMA 부가자료 읽고 오늘 할 일을 추천해줘`에 대해
  - 첫 문단 grounded 제안
  - 둘째 문단 generic 되물음 금지

## 4. 구현 우선순위

실제 작업 순서는 아래가 가장 안정적이다.

1. Slice 1
2. Slice 2
3. Slice 4
4. Slice 5
5. Slice 3

이 순서인 이유:

- 먼저 역할을 나누고
- 그다음 수렴 기준을 붙이고
- 반복을 막고
- 마지막 송달을 정리한 뒤
- 그 다음에 critic 다각화를 키우는 편이 회귀 위험이 낮다.

## 5. 단계별 테스트 세트

매 slice 이후 아래 입력으로 회귀를 본다.

### Test A. 제안형

- `오늘은 우리 뭐할까?`
- `ANIMA 부가자료 읽고 오늘 할 일을 추천해줘`

기대:

- `-1a` 선계획
- grounded proposal
- generic follow-up 금지

### Test B. 기능 적합형

- `ANIMA 부가자료 읽고 기획에 부합하는 기능을 말해줘`

기대:

- 기능 요약
- 사회적 영향 장광설 금지

### Test C. correction / retry

- `다시 찾아봐`
- `아니 그거 말고 다시`
- `네가 직접 생각하라고`

기대:

- stale topic 재유입 금지
- 현재 턴을 직전 과업의 correction으로 상속

### Test D. 얇은 직답형

- `넌 누구야?`
- `오늘은 우리 뭐할까?`

기대:

- `-1s`에서 빠른 분기
- 쓸데없는 워룸 왕복 금지

## 6. 롤백 원칙

각 slice는 독립 롤백 가능해야 한다.

따라서 아래 원칙을 지킨다.

1. 상태 필드 추가와 분기 추가를 분리해서 커밋한다.
2. 한 slice 안에서 라우팅과 프롬프트를 동시에 크게 바꾸지 않는다.
3. 테스트 세트 하나라도 크게 후퇴하면 그 slice는 잠시 보류한다.

## 7. 바로 다음 액션

지금 바로 시작할 1차 구현 범위는 아래다.

1. Slice 1 세부 고정
2. Slice 2 필수 수렴 계약 고정
3. Slice 4 반복 금지 계약의 최소판 고정

한 줄로 요약하면:

`먼저 -1a가 시작을 잡고, grounded findings가 생기면 바로 수렴하게 만들고, 같은 상태 반복을 구조적으로 막는다.`
