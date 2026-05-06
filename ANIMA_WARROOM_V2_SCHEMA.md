# ANIMA War Room V2

> Document status: FUTURE DESIGN.
> Use this when implementing WarRoom V2 deliberation. Do not let it override the
> current field-loop constitution until that constitution is amended.

## 목표

ANIMA의 워룸은 `엄격한 지시서 엔진`이 아니라, `자유롭게 사고하되 바깥으로 나갈 때만 엄격한 계약을 따르는 내부 토론장`이어야 한다.

핵심 원칙은 하나다.

- 내부 토론: 자유
- 외부 전달: 계약

즉 `-1a`, `2b`, `0차`는 워룸 안에서 서로 직접 말할 수 있어야 하고, `-1b`는 그 대화를 중간에 끊는 검열자가 아니라 마지막 결재자여야 한다.

## 현재 구조의 문제

현재 구조는 안전성과 추적성을 확보하는 데는 도움이 되었지만, 아래 문제가 반복된다.

- `2b`가 `-1a`의 문제의식을 직접 못 듣기 때문에 왜 그런 관점으로 읽어야 하는지 모른다.
- `-1a`는 `2b`가 왜 평면적인 일반론만 내놓는지 모른다.
- `0차`는 도구 감각은 좋지만, 상위 reasoning과 분리돼 있다.
- `-1b`가 대화 중간에서 너무 많이 개입해 워룸의 사고 흐름을 끊는다.
- 결과적으로 연속 사고가 아니라 `연속 재포장`, `연속 지시 하달`처럼 보인다.

## V2 원칙

### 1. 직접 소통 허용

워룸 안에서는 다음 경로를 허용한다.

- `-1a -> 2b`
- `2b -> -1a`
- `-1a -> 0차`
- `0차 -> -1a`
- `2b -> 0차`
- `0차 -> 2b`

단, 이는 `내부 토론`에 한정한다. 외부 노드 전이와 최종 송달은 여전히 `-1b`가 결재한다.

### 2. 자유 사고와 엄격한 산출 구분

워룸 내부 메시지는 자유 서술을 허용한다.

- 가설
- 반론
- 관점
- 대안 경로
- 수색 제안

하지만 각 메시지는 반드시 구조화된 산출 슬롯으로도 요약되어야 한다.

### 3. 2b의 독립성은 유지하되 격리는 풀기

`2b`는 `-1a`의 full 결론을 복붙하면 안 된다. 그러나 `-1a`의 관점 제안과 질문 틀은 직접 들을 수 있어야 한다.

즉 `2b`는 다음을 받아야 한다.

- 어떤 질문에 답하려는지
- 어떤 관점으로 읽는지
- 무엇은 확장하면 안 되는지

하지만 다음은 받으면 안 된다.

- 최종 결론 강요
- delivery 문안
- 근거 없이 확정된 해석

### 4. 0차를 조사/도구 허브로 승격

`0차`는 전체 허브가 아니라 `tool-heavy 사건의 현장 지휘관`이다.

`0차`는 다음에 강해야 한다.

- 어떤 도구가 적절한지
- 같은 도구 반복인지
- query_variant가 필요한지
- 다른 source로 갈지 같은 source를 다른 focus로 읽을지

## 워룸 참여자 역할

### `-1a`

역할:

- 초기 의미 파악
- 질문 축 고정
- 가설 제안
- 수렴 방향 제시

금지:

- grounded findings가 충분한데도 계속 gathering 유지
- 사용자 질문을 다른 과업으로 바꾸기
- 2b를 설득하려고 결론을 강요하기

### `2b`

역할:

- fact-first 검증
- 반론 제기
- coverage 검사
- 수렴 가능성 검사

금지:

- 계획 수립
- 도구 실행 지시
- 근거 없는 심리 일반화

### `0차`

역할:

- 도구 경로 제안
- query rewrite
- source switch 제안
- 반복 작업 차단

금지:

- 질문 의미 재정의
- 송달 문안 작성
- 창작/감정 턴을 무조건 도구 사건으로 만들기

### `-1b`

역할:

- 최종 결재
- 반복 금지
- 외부 송달 허가
- 내부 충돌 정리

금지:

- 토론 중간에서 관점 자체를 너무 일찍 잘라내기
- 매 단계마다 직접 해석자 역할 떠맡기
- 전략 존재를 곧 수렴 완료로 오판하기

### `3차`

역할:

- `delivery_packet` 렌더링

금지:

- 질문 재해석
- generic narrowing follow-up 자동 생성
- 내부 대화를 자기 멋대로 요약하며 왜곡하기

## 워룸 메시지 타입

V2에서는 자유 서술을 허용하되, 각 메시지에 구조화 슬롯을 함께 둔다.

### 1. `problem_frame_packet`

주체: `-1a`

필드:

- `user_goal`
- `answer_shape`
- `active_context`
- `must_not_expand_to`
- `suspected_question_type`
- `why_this_case_is_not_trivial`

의도:

이번 사건을 어떤 문제로 볼지 제안한다.

### 2. `lens_packet`

주체: `-1a -> 2b`

필드:

- `candidate_lenses`
- `must_answer_user_goal`
- `must_not_drift`
- `current_step_goal`
- `working_hypotheses`
- `do_not_treat_as_truth`

의도:

`2b`에게 “이 관점들로 검토해봐”라고 말하되, 정답으로 강요하지 않는다.

### 3. `critic_reply_packet`

주체: `2b -> -1a`

필드:

- `supported_lenses`
- `unsupported_lenses`
- `grounded_facts`
- `missing_anchor`
- `off_target_elements`
- `direct_answer_supported`
- `coverage_of_user_goal`

의도:

`-1a`에게 “이건 맞고, 이건 틀리고, 지금 어디까지 답 가능한지”를 돌려준다.

### 4. `ops_packet`

주체: `0차 -> -1a / 2b`

필드:

- `tool_options`
- `best_tool`
- `query_variant`
- `new_source_option`
- `same_operation_risk`
- `expected_novelty`

의도:

조사/도구 관점에서 다음 행동을 제안한다.

### 5. `synthesis_packet`

주체: `-1a`

필드:

- `achieved_findings`
- `best_current_answer`
- `remaining_gap`
- `delivery_readiness`
- `next_frontier`
- `convergence_state`

의도:

워룸 대화를 바탕으로 지금 결론을 낼지, 더 볼지 정리한다.

### 6. `delivery_packet`

주체: `-1b -> 3차`

필드:

- `final_answer_brief`
- `approved_fact_cells`
- `approved_claims`
- `must_avoid_claims`
- `reply_mode`
- `delivery_freedom_mode`
- `followup_instruction`

의도:

3차는 이것만 말한다.

## 워룸 V2 흐름

### A. 일반 비단순 턴

1. `-1s`가 얇게 분류한다.
2. `-1a`가 `problem_frame_packet`과 `lens_packet`을 만든다.
3. `2b`가 비판적으로 읽고 `critic_reply_packet`을 만든다.
4. 필요하면 `0차`가 `ops_packet`을 만든다.
5. `-1a`가 `synthesis_packet`으로 수렴 여부를 정리한다.
6. `-1b`가 결재한다.
7. `3차`는 `delivery_packet`만 렌더링한다.

### B. tool-heavy 턴

1. `-1s`
2. `-1a`
3. `0차`가 tool path를 우선 정리
4. `2a`
5. `2b`
6. `-1a synthesize`
7. `-1b final`
8. `3차`

### C. creative/social direct 턴

1. `-1s`가 creative/social direct로 분류
2. 필요하면 `-1a`가 아주 짧은 creative framing
3. 바로 `3차`

이 경우에는 `2a/2b`를 태우지 않는다.

## 핵심 계약

### 자유 사고 계약

워룸 안에서는 자유롭게 말해도 된다. 단, 각 발언은 아래를 포함해야 한다.

- `what I think`
- `what supports it`
- `what does not support it`
- `what is still missing`

### 수렴 계약

`-1a`는 매번 다음 4개를 반드시 답한다.

1. 이번 루프에서 새로 확보한 사실은?
2. 그 사실로 현재 질문에 어디까지 답 가능한가?
3. 지금 조출할 결론은 무엇인가?
4. 아니라면 다음 작업은 이전 작업과 무엇이 달라야 하는가?

### 반복 금지 계약

동일한 아래 조합은 반복으로 본다.

- `analysis_signature`
- `operation_contract_signature`
- `tool_args_signature`
- `same grounded findings`

이 경우 `-1b`는 다음 중 하나만 허용한다.

- 다른 lens로 재검토
- 다른 source로 전환
- 즉시 수렴

## 왜 이 구조가 경량 모델에도 맞는가

경량 모델에게 완전 자유를 주면 흔들린다. 하지만 완전 엄격한 지시서만 주면 범용성이 죽는다.

그래서 V2는 다음 균형을 택한다.

- 사고는 자유롭게
- 출력 슬롯은 고정
- 근거와 불확실성 표시는 강제

즉 “아무렇게나 생각하라”가 아니라,

- 자유롭게 토론하라
- 그러나 마지막엔 반드시 구조화 슬롯으로 제출하라

를 강제한다.

이게 경량 모델에서 제일 현실적이다.

## 지금 구조에서 우선 개혁 순서

### Slice A

`2b`가 `-1a`의 `lens_packet`을 직접 받게 만든다.

### Slice B

`0차`를 조사/도구 허브로 올리고, `ops_packet`을 도입한다.

### Slice C

`-1b`를 토론 중간 개입자에서 최종 결재자로 축소한다.

### Slice D

`3차`를 `delivery_packet renderer`로 더 단순화한다.

### Slice E

심야 성찰이 `warroom usefulness`, `loop value`, `tool path quality`를 학습적으로 보강하게 한다.

## 한 줄 결론

ANIMA의 다음 워룸은 `격리된 부서들의 지시서 교환소`가 아니라,
`-1a, 2b, 0차가 자유롭게 토론하고 -1b가 마지막에만 결재하는 메타인지 협업실`이어야 한다.
