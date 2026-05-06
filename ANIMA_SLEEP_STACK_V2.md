# ANIMA Sleep Stack V2

> Document status: FUTURE DESIGN / NIGHT LOOP.
> Use this for long-term night-government architecture. Treat policy graph
> control over the day loop as a proposal until the field-loop constitution is
> amended.

이 문서는 `ANIMA_SLEEP_STACK_V1`을 확장한 구조 개혁안이다.

V1이 `REMPlan -> 2차 꿈 -> 정책`의 최소 골격을 세웠다면, V2는 `REMPlan`을 단순 계획 노드가 아니라 상위 총괄 업무 계층으로 승격시키고, 심야 성찰과 장기 구조 유지 부서를 분리한다.

핵심 방향은 한 줄이다.

- 조건문 라우터 대신 밤에 단련된 정책 그래프가 낮의 현장을 이끈다.
- `REMGovernor`는 설계만 하고, 검토와 배치는 다른 단계가 맡는다.
- 저가치 추측은 영속화하지 않고, 결과물과 근거 주소만 남긴다.

## 1. V2가 필요한 이유

기존 `REMPlan`은 너무 얇다.

- 공급 부족 주제를 본다
- 대략적인 우선순위를 정한다
- 심야 성찰의 입력으로만 쓰인다

하지만 앞으로 필요한 것은 단순 계획이 아니라 `계획 도시`다.

즉 `REMGovernor`는 아래를 알아야 한다.

- 어떤 공급 부족 주제가 기존 가지 수정 대상인지
- 어떤 주제가 새 가지 생성 대상인지
- 어떤 최상위 루트 아래로 내려가야 하는지
- 어떤 최소 리프 단위까지 분해해야 하는지
- 심야 성찰과 2차 꿈의 결과물을 어느 위치에 재배치해야 하는지

## 2. V2의 상위 구조

V2는 아래의 8개 계층으로 본다.

1. `UserRoot / SongryeonRoot`
2. `Dream / TurnProcess / PhaseSnapshot`
3. `REMGovernor`
4. `Phase7CoverageAudit`
5. `Phase8aSupplyPlanner`
6. `Phase8bSupplyReviewer`
7. `Phase9PlacementJudge`
8. `Phase10PolicyFruit`
9. `BranchGrowth`
10. `BranchDigest`

실제 흐름은 아래와 같다.

`원본 사건 -> REMGovernor 설계 -> Phase7 coverage 감사 -> Phase8a 계획 -> Phase8b 이의제기/반려 -> Phase9 배치 판정 -> Phase10 정책 열매 생성 -> BranchGrowth 장기 구조 보정`

## 3. 상위 루트

심야 성찰의 모든 재귀 학습은 처음엔 아래 루트에서 시작한다.

- `UserRoot`
- `SongryeonRoot`

선택적 상위 루트:

- `ProjectRoot`
- `RelationshipRoot`
- `IdentityRoot`

원칙:

- 공급 부족 주제를 발견했다고 바로 메우지 않는다.
- 먼저 그 주제가 어느 루트에서 출발하는지 찾는다.
- 그 다음 어느 가지 경로를 타야 하는지 정한다.

## 4. REMGovernor

`REMGovernor`는 V2의 총괄 설계 계층이다.

역할:

- 원본 1차 꿈과 현장 공정 기록을 본다
- 공급 부족 주제를 읽는다
- 주제의 속성을 파악한다
- 어느 루트에서 시작해야 하는지 정한다
- 어느 가지 경로로 내려갈지 정한다
- 기존 가지 수정인지 새 가지 생성인지 판정한다
- 최소 리프 단위까지 정의한다
- 심야 성찰 결과물을 어디에 배치할지 큰 구조를 짠다

중요한 제한:

- `REMGovernor`는 최종 판정자가 아니다
- 실행 결과를 다시 직접 승인하지 않는다
- 결과 보고는 `Phase9` 또는 `Phase10`으로 간다

즉 `REMGovernor`는 총괄 설계자이지, 총괄 집행자나 총괄 판정자가 아니다.

### REMGovernor 핵심 필드

- `governor_id`
- `plan_scope`
- `target_roots`
- `priority_supply_topics`
- `branch_paths`
- `leaf_specs`
- `placement_decisions`
- `create_targets`
- `update_targets`
- `required_evidence_addresses`
- `handoff_targets`
- `risk_notes`
- `validation_rules`
- `status`

### REMGovernor 산출물

- `RootTarget`
- `BranchPlacement`
- `LeafSpec`
- `PlacementDecision`
- `EvidenceDemand`

## 5. Phase 7: Coverage Audit

`Phase7`은 단순 topic 분류기가 아니라 `coverage auditor`가 되어야 한다.

역할:

- 여러 1차 꿈의 부족 주제를 합친다
- 중복되는 부족 주제는 통합한다
- 통합하는 과정에서 빠진 다른 주제가 없는지 검사한다
- "같아 보이지만 실제로는 다른 결핍"을 놓치지 않는다
- 최소 리프 단위 coverage map을 만든다

즉 `Phase7`은 "무엇이 부족한가"뿐 아니라 "무엇을 놓쳤는가"도 봐야 한다.

### Phase7 핵심 산출물

- `CoverageGap`
- `MergedSupplyTopic`
- `MissedTopicAlert`
- `CoverageMap`

## 6. Phase 8a / 8b

### Phase 8a: Supply Planner

역할:

- `Phase7`이 잡은 부족 주제를 메우기 위한 실행 계획 수립
- 어떤 원본을 읽을지 결정
- 어떤 브리지 사상이 필요한지 예측
- 어떤 도구와 어떤 순서가 적절한지 제안

산출물:

- `SupplyPlan`
- `ToolPlan`
- `EvidenceAcquisitionPlan`

### Phase 8b: Supply Reviewer

역할:

- `8a`의 계획을 비판적으로 검토
- 부족한 근거, 과도한 추정, 잘못된 주제 통합을 반려
- 필요하면 `7`에게 coverage 문제를 직접 제기
- 필요하면 `8a`에게 보완 지시

이 단계는 현장 워룸처럼 직접 소통할 수 있어야 한다.

허용되는 소통:

- `8a -> 8b` 계획 전달
- `8b -> 8a` 반려 / 이의 제기 / 보완 요구
- `8b -> 7` coverage 누락 신고

금지:

- `8b`가 혼자 최종 판정까지 해버리는 것

## 7. Phase 9 / Phase 10

### Phase 9: Placement Judge

`Phase9`는 최종 배치 판정 계층이다.

역할:

- `REMGovernor`가 설계한 큰 구조를 기준으로
- `Phase8a/8b`의 결과를 받아
- 실제로 어디에 배치할지 판정
- 가지 수정 / 신규 가지 / 열매 생성 여부 확정

중요:

- 결과 보고는 `REMGovernor`가 아니라 `Phase9`로 간다
- 여기서 월권 충돌을 막는다

산출물:

- `PlacementVerdict`
- `StructureApproval`
- `RejectionNote`

### Phase 10: Policy Fruit

`Phase10`이 만드는 전술 카드와 정책은 `열매`다.

열매 종류:

- `RoutePolicy`
- `ToolDoctrine`
- `TacticCard`
- `TacticalThought`

원칙:

- 열매는 반드시 가지에 달려야 한다
- 동시에 2차 꿈 및 1차 꿈 근거와 연결되어야 한다
- 그래서 `REMGovernor`가 재배열해도 근거를 잃지 않는다

즉 정책 열매는 아래를 동시에 붙든다.

- `SupplyTopic` 또는 `BranchPlacement`
- `SecondDream`
- `Dream / TurnProcess / PhaseSnapshot`
- `EvidenceAddress`

## 8. BranchGrowth

`BranchGrowth`는 심야 성찰과 겹치지 않는 별도 부서다.

심야 성찰이 "당일/최근 수리"라면, `BranchGrowth`는 "장기 구조 유지와 확장"이다.

역할:

- 루트-가지-열매 사이의 구조 일관성 검사
- 여러 원문 1차 꿈을 묶어 더 큰 패턴 확인
- 2차 꿈과 정책 열매가 잘못 매달린 곳 재배치 후보 탐지
- 오래된 가지 가지치기
- 부족하지만 중복 생성된 가지 통합
- 상황에 따라 episode를 대체하거나 보완하는 상위 요약 생성

즉 `BranchGrowth`는 "도시 확장과 정비국"에 가깝다.

## 9. BranchDigest

`BranchDigest`는 episode를 대체하거나 보완하는 새 상위 요약 단위다.

역할:

- 하루 요약보다 더 넓은 범위를 다룬다
- 특정 가지나 줄기 중심으로 요약한다
- 상황에 따라 요약 범위를 바꾼다
- 어떤 원문을 참고했는지 모두 연결한다

원칙:

- 요약 중 참고한 근거는 전부 직접 연결
- `Dream`, `SecondDream`, `EvidenceAddress`, `SupplyTopic`, `RoutePolicy`와 바로 이어진다
- 추측이 아니라 구조화된 상위 요약 자산으로 남는다

### BranchDigest가 다룰 수 있는 범위 예시

- 특정 사용자 자기이해 가지
- 최근 대화 품질 가지
- 도구 사용 실패/성공 가지
- 장기 패턴 가지

## 10. 그래프 노드/관계 초안

### 노드

- `UserRoot`
- `SongryeonRoot`
- `Dream`
- `TurnProcess`
- `PhaseSnapshot`
- `REMGovernor`
- `BranchPlacement`
- `LeafSpec`
- `SupplyTopic`
- `SecondDream`
- `RoutePolicy`
- `ToolDoctrine`
- `TacticCard`
- `TacticalThought`
- `BranchGrowth`
- `BranchDigest`
- `EvidenceAddress`

### 관계

- `(:REMGovernor)-[:TARGETS_ROOT]->(:UserRoot)`
- `(:REMGovernor)-[:TARGETS_ROOT]->(:SongryeonRoot)`
- `(:REMGovernor)-[:DESIGNS_BRANCH]->(:BranchPlacement)`
- `(:BranchPlacement)-[:HAS_LEAF_SPEC]->(:LeafSpec)`
- `(:BranchPlacement)-[:TRACKS_TOPIC]->(:SupplyTopic)`
- `(:SecondDream)-[:FULFILLS_PLAN]->(:BranchPlacement)`
- `(:SecondDream)-[:SUPPORTS_TOPIC]->(:SupplyTopic)`
- `(:Phase9PlacementJudge)-[:APPROVES]->(:BranchPlacement)`
- `(:RoutePolicy)-[:FRUIT_OF]->(:BranchPlacement)`
- `(:ToolDoctrine)-[:FRUIT_OF]->(:BranchPlacement)`
- `(:RoutePolicy)-[:GROUNDED_IN]->(:Dream)`
- `(:ToolDoctrine)-[:GROUNDED_IN]->(:Dream)`
- `(:RoutePolicy)-[:GROUNDED_IN]->(:SecondDream)`
- `(:ToolDoctrine)-[:GROUNDED_IN]->(:SecondDream)`
- `(:BranchDigest)-[:SUMMARIZES]->(:BranchPlacement)`
- `(:BranchDigest)-[:GROUNDED_IN]->(:Dream)`
- `(:BranchDigest)-[:GROUNDED_IN]->(:SecondDream)`
- `(:BranchGrowth)-[:CURATES]->(:BranchDigest)`

## 11. 비영속 원칙

절대 영속화하지 않을 것:

- 중간 오판
- 저가치 추측 노드
- 잠깐 나왔다 사라지는 가설
- planner 찌꺼기
- reviewer의 일회성 메모

영속화할 것:

- 구조적으로 재사용 가치가 있는 배치 결과
- 근거 주소
- 검증된 브리지
- 정책 열매
- 장기 요약 자산

## 12. 구현 순서 제안

1. `REMPlan`를 `REMGovernor` 개념으로 재정의
2. `Phase7`를 coverage auditor로 승격
3. `8a/8b`의 직접 소통 패킷 추가
4. `Phase9`를 최종 배치 판정 계층으로 도입
5. `Phase10`의 정책 열매를 가지/근거와 동시 연결
6. `BranchGrowth`와 `BranchDigest` 추가
7. episode 대체/보완 경로 설계

## 13. 핵심 원칙

- 총괄은 설계만 한다
- 검토는 reviewer가 한다
- 최종 판정은 9/10이 한다
- 장기 구조는 BranchGrowth가 맡는다
- 열매는 가지와 근거를 동시에 잡아야 한다
- 저가치 추측은 남기지 않는다

한 줄 결론:

`ANIMA V2 수면 스택은 공급 부족 주제를 즉흥적으로 메우는 시스템이 아니라, 루트에서 가지와 리프를 설계하고 심야 성찰 결과물을 올바른 위치에 재배치하며 정책 열매를 맺게 하는 계획 도시형 두 번째 뇌다.`

## 14. 하드코딩 라우터 철거 방향

낮의 현장에서 `if / else`와 0차 재량을 줄이려면, 심야 팀이 아래 산출물을 꾸준히 공급해야 한다.

- `REMGovernor`
  - 어떤 루트와 가지가 우선인지 정한다.
- `CoverageMap`
  - 어떤 결핍이 합쳐졌고 무엇을 놓쳤는지 알려준다.
- `RoutePolicy`
  - 어떤 family와 answer shape가 어느 다음 단계로 가야 하는지 정한다.
- `ToolDoctrine`
  - 어떤 도구를 어떤 순서로 써야 하는지 정한다.
- `BranchDigest`
  - 현장이 바로 참고할 수 있는 상위 요약 자산을 제공한다.

낮의 0차는 점점 아래처럼 바뀌어야 한다.

1. coarse signal 수집
2. 정책 그래프 조회
3. `RoutePolicy` 우선 매칭
4. `ToolDoctrine` 우선 실행
5. 정책이 비어 있을 때만 fallback 조건문 사용

즉 목표는 `하드코딩 라우터 -> 정책 조회기 -> 실행기` 순서로 0차를 축소하는 것이다.
