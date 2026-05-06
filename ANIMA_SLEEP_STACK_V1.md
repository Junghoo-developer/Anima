# ANIMA Sleep Stack V1

> Document status: FUTURE DESIGN / NIGHT LOOP.
> Use this for early sleep-stack architecture. Day-loop routing is still ruled by
> `ANIMA_FIELD_LOOP_V2_CONSTITUTION.md`.

이 문서는 ANIMA의 다음 개혁 축인 `램수면 -> 2차 꿈 -> 현장 정책` 구조를 정의한다.

목표는 단순하다.

- 조건문 라우터와 0차 재량에 과도하게 의존하지 않는다.
- 심야 성찰이 현장을 위한 정책과 공급 구조를 만든다.
- 0차는 의미 판단자가 아니라 정책 조회 + 실행기가 된다.
- 저가치 추측 노드는 영속화하지 않는다.

## 1. 핵심 원칙

### 1. 원본과 파생을 분리한다

- `Dream`, `PastRecord`, `Diary`, `ChatLog`는 원본 레이어다.
- `TurnProcess`, `PhaseSnapshot`은 현장 공정 레이어다.
- `REMPlan`, `SecondDream`, `SupplyTopic`, `RoutePolicy`, `ToolDoctrine`는 파생 인지 레이어다.

### 2. 밤이 낮의 판단 기준을 만든다

- 낮에는 사건을 처리한다.
- 밤에는 그 사건을 감사하고, 다음날 쓸 정책을 만든다.
- 다음날 0차는 그 정책을 조회하고 실행한다.

### 3. 그래프에는 영속 가치가 있는 것만 남긴다

남길 것:

- 상위 리프
- 공급 부족 주제
- 검증된 브리지
- 전술/정책 노드
- 근거 주소
- 단계별 실패 패턴

남기지 않을 것:

- 일회성 추측
- 저가치 가설 초안
- 중간 오판 메모
- 그냥 한번 튀어나온 plan 찌꺼기

## 2. 상위 구조

새 구조는 5층으로 본다.

1. `Root Leaf`
2. `Dream / TurnProcess / PhaseSnapshot`
3. `REMPlan`
4. `SecondDream`
5. `RoutePolicy / ToolDoctrine / TacticalThought`

### Root Leaf

처음 시작할 때만 강하게 쓰는 상위 리프다.

- `UserRoot`
- `SongryeonRoot`

필요하면 나중에 추가:

- `ProjectRoot`
- `RelationshipRoot`
- `IdentityRoot`

중요한 점은, 심야 성찰이 공급 부족 주제만 바로 메우는 게 아니라 먼저 이 상위 리프를 기준으로 "무엇을 배우고 재편해야 하는가"를 본다는 것이다.

## 3. 램수면 단계

`램수면`은 2차 꿈 직전의 고성능 사전 탐사 단계다.

역할:

- 상위 리프를 다시 확인
- 현장 기록을 읽고 무엇이 중요한 축인지 선택
- 공급 부족 주제를 곧장 메우지 않고 먼저 학습 계획을 세움
- 분석 범위, 우선순위, 검증 경로를 미리 정한다

한 줄 정의:

`램수면은 공급이 아니라 학습 계획을 만든다.`

### REMPlan 노드

`REMPlan`은 램수면의 핵심 산출물이다.

필수 필드:

- `id`
- `created_at`
- `plan_scope`
- `target_roots`
- `priority_topics`
- `candidate_supply_topics`
- `objective_summary`
- `evidence_start_points`
- `expected_outputs`
- `risk_notes`
- `validation_rules`
- `status`

권장 필드:

- `phase_failure_focus`
- `loop_failure_patterns`
- `top_source_ids`
- `target_user_model_axes`
- `target_songryeon_axes`

### REMPlan 관계

- `(:REMPlan)-[:TARGETS_ROOT]->(:UserRoot)`
- `(:REMPlan)-[:TARGETS_ROOT]->(:SongryeonRoot)`
- `(:REMPlan)-[:USES_DREAM]->(:Dream)`
- `(:REMPlan)-[:USES_PROCESS]->(:TurnProcess)`
- `(:REMPlan)-[:USES_PHASE]->(:PhaseSnapshot)`
- `(:REMPlan)-[:PRIORITIZES_TOPIC]->(:SupplyTopic)`

## 4. 2차 꿈의 입력 확장

기존 2차 꿈은 `Dream` 중심이었다.

이제 입력은 아래 네 층을 모두 본다.

- `Dream`
- `TurnProcess`
- `PhaseSnapshot`
- `REMPlan`

### 새 입력 규칙

2차 꿈은 다음 순서로 판단한다.

1. 원본 사건 `Dream`을 본다.
2. 공정 기록 `TurnProcess`를 본다.
3. 어느 단계에서 끊겼는지 `PhaseSnapshot`으로 본다.
4. 램수면이 미리 세운 `REMPlan`과 맞춰 본다.
5. 그 뒤에야 `SupplyTopic` 보정 또는 정책 생성을 한다.

### 2차 꿈의 역할 재정의

기존:

- 하루치 꿈 요약
- 공급 부족 주제 생성

개혁 후:

- 단계별 실패 감사
- 상위 리프 기반 재해석
- 공급 부족 주제 보정
- 기존 공급 노드와 중복 검사
- 현장 정책 생성 또는 수정

한 줄 정의:

`2차 꿈은 "생각"이 아니라 "현장과 밤을 이어주는 정책 공장"이다.`

## 5. SupplyTopic 처리 규칙

공급 부족 주제를 다루는 방식도 바꾼다.

### 새 규칙

1. 1차 꿈 실패 흔적에서 후보를 뽑는다.
2. 곧장 메우지 않는다.
3. 먼저 `REMPlan`이 이 주제가 상위 리프와 어떤 관련이 있는지 본다.
4. 기존 유사 `SupplyTopic` 또는 `ToolDoctrine`이 있는지 검사한다.
5. 있으면 신규 노드 생성보다 수정/보강이 우선이다.
6. 없을 때만 신규 생성한다.

### 해석

- 이미 비슷한 공급 노드가 있는데 현장에서 또 실패했다면
  - 새로 배우지 못한 것이 아니라
  - 정책 반영, 검색 경로, handoff, 우선순위에 문제가 있었던 것이다.

즉 실패는 곧바로 지식 부족이 아니라 `배운 지식을 현장에서 못 쓰는 문제`일 수 있다.

## 6. RoutePolicy / ToolDoctrine

이제 낮의 라우팅은 조잡한 if/else보다 그래프 정책을 더 많이 따른다.

### RoutePolicy 노드

역할:

- 어떤 사건 family는 어디로 보내야 하는가
- 어떤 조건에서 war-room을 건너뛰는가
- 어떤 경우 `phase_2a`로 바로 가는가
- 어떤 경우 `phase_3`로 직행하는가

필수 필드:

- `policy_key`
- `turn_family`
- `answer_shape_hint`
- `trigger_signals`
- `preferred_next_hop`
- `fallback_next_hop`
- `requires_grounding`
- `requires_recent_context`
- `requires_active_offer`
- `requires_history_scope`
- `confidence_gate`
- `status`

예시:

- `self_analysis_snapshot`
- `capability_boundary`
- `review_recent_dialogue`
- `review_personal_history`
- `offer_followup_execution`
- `creative_social_direct`

### ToolDoctrine 노드

역할:

- 어떤 사건 family에서 어떤 도구를 우선 써야 하는가
- broad query일 때 어떤 순서로 좁혀야 하는가
- diary / chat / artifact / memory search 중 무엇을 먼저 쓰는가

필수 필드:

- `doctrine_key`
- `target_family`
- `recommended_tools`
- `tool_order`
- `query_rewrite_rules`
- `source_priority`
- `avoid_patterns`
- `success_signals`
- `failure_signals`
- `status`

예시:

- `personal_history_doctrine`
- `recent_dialogue_review_doctrine`
- `artifact_review_doctrine`
- `offer_followup_doctrine`

### 정책 관계

- `(:SecondDream)-[:UPDATES_POLICY]->(:RoutePolicy)`
- `(:SecondDream)-[:UPDATES_DOCTRINE]->(:ToolDoctrine)`
- `(:RoutePolicy)-[:FOR_TOPIC]->(:SupplyTopic)`
- `(:ToolDoctrine)-[:FOR_TOPIC]->(:SupplyTopic)`
- `(:ToolDoctrine)-[:GROUNDED_IN]->(:PastRecord)`
- `(:ToolDoctrine)-[:GROUNDED_IN]->(:Diary)`
- `(:ToolDoctrine)-[:GROUNDED_IN]->(:Dream)`

## 7. 0차의 역할 축소

개혁 후 0차는 더 이상 의미 해석자가 아니다.

새 역할:

- `RoutePolicy` 조회
- `ToolDoctrine` 조회
- 필요한 도구 실행
- 실행 결과 handoff

하면 안 되는 것:

- 고차원 의도 재해석
- 즉석 라우팅 철학 발명
- 추측 기반 query 생성
- planner 메모를 keyword로 검색

한 줄 정의:

`0차는 정책 엔진 + 실행기다.`

### 0차 입력

- `start_gate_switches`
- `working_memory`
- `recent_context`
- `goal_lock` 요약
- `active_offer`
- `requested_move`

### 0차 출력

- `matched_route_policy`
- `matched_tool_doctrine`
- `ops_decision`
- `tool_plan`
- `next_hop`
- `execution_contract`

## 8. 저가치 추측 노드 비영속화

다음은 그래프에 영속 저장하지 않는다.

- planner 초안
- 불완전한 자아 해석 문장
- 일회성 오판 가설
- 증거 없는 사용자 성향 단정
- 중간 공정에서 튀어나온 임시 suspicion

대신 아래 중 하나로만 남긴다.

- 현장 메모리의 일시 상태
- `PhaseSnapshot.summary_json`
- 심야 루프 내부 변수
- 검증 실패 로그

즉 "기록"은 하되 "노드"로 굳히지는 않는다.

## 9. 구현 순서

### Slice A. REMPlan 도입

- `REMPlan` 스키마 추가
- 램수면 루프 초안 추가
- `UserRoot`, `SongryeonRoot` 기준 입력 확립

### Slice B. 2차 꿈 입력 확장

- `SecondDream` 생성 시 `Dream + TurnProcess + PhaseSnapshot + REMPlan` 읽기
- 실패 원인을 단계 단위로 분류

### Slice C. RoutePolicy / ToolDoctrine 추가

- 최소 5개 family에 대한 정책 노드 생성
- 기존 if/else를 정책 조회로 대체 시작

### Slice D. 0차 축소

- 0차에서 의미 추론 줄이기
- 정책 조회 + 실행 중심으로 개편

### Slice E. 비영속 추측 정리

- 저가치 추측을 그래프 노드로 만드는 경로 제거
- 기존 중간 추측 노드 정리 기준 수립

## 10. 오늘 기준 실전 우선순위

오늘 바로 구현 우선순위를 고르면 이렇다.

1. `REMPlan` 스키마 추가
2. `SecondDream` 입력 확장
3. `RoutePolicy`와 `ToolDoctrine` 최소 스키마 추가
4. 0차를 정책 조회형으로 축소
5. 추측 노드 비영속화 규칙 적용

## 11. 한 줄 결론

다음 ANIMA는

- 낮에 if/else로 버티는 시스템이 아니라
- 밤에 단련된 정책 구조를 낮이 실행하는 시스템이어야 한다.

즉 중심은 `조건문 라우터`가 아니라 `램수면 + 2차 꿈 + 정책 그래프`다.
