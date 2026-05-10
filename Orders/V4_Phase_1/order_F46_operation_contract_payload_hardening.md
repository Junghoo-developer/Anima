# 발주 #F4.6 — operation_contract payload hardening / 오염된 검색 seed 차단

**작성일**: 2026-05-09  
**상태**: 결재 도장 박힘 (2026-05-10) / Codex 실행 완료, ARCH MAP #83 등록됨.  
**트랙**: V4 Phase 1 / F 트랙 #F4.6 (F4.5 후속 검색 계약 보강)  
**선행**: V4 §1-A LIVE + V4 §2 LIVE, F4/F4.5, CR1.1~CR1.3, SO1, C0.8/C0.9.  
**목표**: thin-case fallback planner가 빈약하거나 오염된 `operation_contract`를 만들고, 0_supervisor가 그 추상 payload를 실제 memory search target으로 소비하는 경로를 차단한다.

---

## Why

현장 trace에서 다음 패턴이 확인됐다.

```text
-1s -> -1a fallback planner
current_step_goal=Ask phase 0 to convert the operation contract into one safe tool call.
0_supervisor -> tool_search_memory(target="stored or external evidence has not been read yet")
```

이 문제의 핵심은 0차가 갑자기 의미 판단을 잘못한 것이 아니라, 0차로 넘어간 F4.5 `operation_contract` payload가 이미 오염되어 있었다는 점이다.

확인된 원인:

1. thin case에서 -1a LLM strategist를 건너뛰고 fallback planner가 실행된다.
2. fallback planner가 `start_gate_switches["goal_contract"]`를 `GoalLock`처럼 읽는다.
3. `UserGoalContract`의 정식 필드는 `user_goal`인데 fallback은 `user_goal_core`를 찾는다.
4. 그 결과 `operation_contract.search_subject`가 비거나 추상화될 수 있다.
5. -1s의 `what_is_missing`에 들어간 상태 설명문이 `query_seed_candidates`로 섞인다.
6. 0_supervisor는 형식상 유효한 tool call을 만들 수 있으므로 오염된 target으로 검색을 실행한다.

따라서 F4.6의 원칙은:

> **의미 판단은 LLM에 맡기되, 검색 계약의 출처·필드·실행가능성은 코드가 구조적으로 검증한다.**

F4.6은 raw user wording 기반 의미분류나 키워드 휴리스틱을 추가하지 않는다. 오직 schema/source/provenance/contract quality guard만 추가한다.

---

## 헌법 정합

### V4 §1-A와 정합

- `-1s`: 사용자 의도 정제와 라우팅만 수행한다. 검색어/도구 인자를 직접 만들지 않는다.
- `-1a`: 작전 목표와 `operation_contract`를 만든다. 단, F4 후 도구명/인자는 만들지 않는다.
- `0_supervisor`: `operation_contract`를 exact safe tool call로 변환한다. 의미 재판정이나 답변 작성은 하지 않는다.
- `phase_1`: 실제 도구 실행만 수행한다.
- `2b`: 검색 결과가 들어온 뒤 사실 판정한다.

### V4 §2와 정합

직접 관련 금지:

- V3 §2-1: raw user_input으로 goal/slot 강제 생성 금지.
- V3 §2-14: 결정적 fallback의 의미 분류/의도 라우팅 시도 금지.
- V3 §2-15: 코드 휴리스틱의 답변 텍스트 작성 금지.
- V4 §2 (g): tool_request 0차 외 발생 X.
- V4 §2 (h): 0차 LLM 답변 작성 X.
- V4 §2 (j): ThinkingHandoff.v1 9필드 누락 X.
- V4 §2 (k): -1s 목표 수립 X.
- V4 §2 (l): -1a 라우팅 결정 X.

F4.6은 새 의미 classifier를 만들지 않는다. 계약 필드가 비어 있거나 상태 설명문만 들어 있을 때 실행을 막는 구조 안전장치다.

---

## 현재 코드 좌표

### A. thin-case fallback planner

- `Core/pipeline/strategy.py`
  - `thin_case = not fact_cells_for_strategist and not _handoff_has_known_material(s_packet_dict)`
  - thin case면 `fallback_strategist_output(...)` 호출 후 즉시 return.

문제:

- 초기 기억검색형 턴은 보통 fact cell이 없으므로 -1a LLM planning을 건너뛰기 쉽다.
- fallback planner가 검색 계약 품질을 책임져야 하는데, 현재 필드 source가 흔들린다.

### B. goal contract / goal lock schema mismatch

- `Core/nodes.py`
  - `_base_fallback_strategist_output`
  - `start_gate_goal_contract = start_gate_switches.get("goal_contract", {})`
  - `goal_lock = start_gate_goal_contract if isinstance(...) else _derive_goal_lock_v2(...)`
  - `goal_core = str(goal_lock.get("user_goal_core") or "").strip()`

문제:

- `start_gate_switches["goal_contract"]`는 대개 `UserGoalContract` 계열이다.
- `UserGoalContract` 필드는 `user_goal`, `slot_to_fill`, `evidence_required` 등이다.
- `GoalLock` 필드인 `user_goal_core`가 없으므로 `goal_core=""`가 된다.

### C. status sentence contamination

- `Core/pipeline/start_gate.py`
  - `gaps.append("stored or external evidence has not been read yet")`
  - 이후 `what_is_missing = gaps or key_facts_needed`

문제:

- 이 문장은 사용자 질문의 missing slot이 아니라 evidence state 설명이다.
- fallback planner가 `what_is_missing`을 `query_seed_candidates` 재료로 쓰면 검색 seed가 오염된다.

### D. supervisor contract guard 부족

- `Core/pipeline/supervisor.py`
  - `validate_supervisor_tool_calls(...)`는 tool name / dict args를 검증한다.
  - operation_contract의 `search_subject`, `query_seed_candidates`, `source_lane` 품질 검증은 약하다.

문제:

- tool call 형식은 안전하지만, target이 상태 설명문이면 실행 의미가 무너진다.

### E. Neo4j memory adapter schema warning

- `Core/adapters/neo4j_memory.py`
  - chunk query가 `(record:PastRecord)-[:HAS_CHUNK]->(node)`, `node.text`, `node.chunk_index`를 기대한다.

문제:

- 현재 DB에 `HAS_CHUNK`, `text`, `chunk_index`가 없다는 warning이 발생한다.
- fallback raw vector/lexical 경로가 있어 즉사는 아니지만, 운영 로그와 검색 신뢰도를 흐린다.

---

## 스코프

### F4.6-A. fallback goal source 정식화

`_base_fallback_strategist_output`에서 goal source를 명시적으로 정한다.

권장 helper:

```python
def _goal_core_from_start_gate_contracts(
    *,
    user_input: str,
    start_gate_switches: dict,
    handoff: dict,
) -> tuple[str, dict]:
    ...
```

우선순위:

1. `strategist_goal.user_goal_core`가 이미 있으면 사용.
2. `GoalLock.user_goal_core` 형태면 사용.
3. `UserGoalContract.user_goal`이 있으면 `_derive_goal_lock_v2` 또는 기존 normalizer를 통해 `user_goal_core`로 변환.
4. `turn_contract.normalized_goal` 또는 `handoff.goal_state`를 compact fallback으로 사용.
5. 그래도 비면 `goal_core=""`로 두되, 검색 operation_contract를 실행 가능 상태로 만들지 않는다.

주의:

- raw user_input을 그대로 `user_goal_core`에 복사하지 않는다.
- 기존 `_normalized_goal_from_contract(...)`, `_derive_goal_lock_v2(...)` 등 이미 있는 contract normalizer를 우선 사용한다.

### F4.6-B. `what_is_missing`와 evidence state 분리

`_build_s_thinking_packet`에서 상태 설명문과 실제 missing slot을 분리한다.

권장 방향:

- `what_is_missing`: 실제로 채워야 할 slot/fact만 담는다.
- `evidence_state`: "stored or external evidence has not been read yet" 같은 상태 설명을 담는다.
- `constraints_for_next_node`: "stored/external evidence must be read before grounded answer" 같은 실행 제약을 담는다.

수용 가능한 compatibility:

- ThinkingHandoff 9필드 구조는 유지한다.
- 기존 테스트가 `what_is_missing` non-empty를 기대하면, 상태 설명문 대신 "direct evidence required by the start-gate contract" 같은 slot-like 표현을 넣는다.
- 이 표현도 검색 seed로 직접 쓰이지 않도록 F4.6-C에서 seed filter를 둔다.

### F4.6-C. query_seed_candidates 정화

fallback planner에서 `query_seed_candidates`를 만들 때 상태 설명문을 제거한다.

허용되는 seed:

- `goal_core`
- `UserGoalContract.slot_to_fill`
- `turn_contract.normalized_goal`
- `handoff.goal_state`
- LLM/contract가 이미 만든 짧은 topic/entity seed

금지되는 seed:

- evidence state 설명문
- tool capability 설명문
- 내부 workflow 문장
- `stored or external evidence has not been read yet`
- `a planner must choose the next action`
- `downstream handler must preserve the answer boundary`
- 빈 문자열

중요:

- 이 필터는 의미분류가 아니라 **known internal status string / schema fallback sentinel 제거**다.
- 새로운 사용자 의미 키워드 분류를 추가하지 않는다.

### F4.6-D. operation_contract quality guard

공통 validator 후보:

- 위치 후보: `Core/pipeline/structured_io.py` 또는 `Core/pipeline/plans.py`
- 이름 후보: `validate_operation_contract_payload(...)`

검증 규칙:

```text
operation_kind in {search_new_source, review_personal_history, read_same_source_deeper}
AND source_lane in {memory, diary, field_memo, artifact, gemini_chat, songryeon_chat, mixed_private_sources}
이면:
  - search_subject 또는 query_seed_candidates 중 하나는 non-empty여야 함.
  - seed가 internal sentinel/status sentence만 있으면 invalid.
  - source_lane=diary + exact date가 있으면 허용.
  - source_lane=capability_boundary면 0차는 검색하지 않음.
```

실패 시:

- 0_supervisor는 tool call을 만들지 않는다.
- `structured_failure` 또는 `execution_block_reason`에 `operation_contract_payload_invalid`를 남긴다.
- graph는 기존 blocked/remand 경로를 사용한다.

주의:

- validator는 "이 질문은 검색형인가?"를 새로 판단하지 않는다.
- 이미 -1a가 만든 `operation_contract`가 실행 가능한지 검사할 뿐이다.

### F4.6-E. 0_supervisor abstract target guard

`run_phase_0_supervisor` LLM 호출 전, `planned_operation_contract`를 검증한다.

권장 동작:

1. diary exact-date deterministic fallback은 기존대로 먼저 허용 가능.
2. 그 외 search operation은 `validate_operation_contract_payload`를 통과해야 LLM tool-call path로 간다.
3. 실패하면 no tool_calls + structured failure로 차단한다.

로그 예:

```text
[Phase 0] blocked invalid operation_contract payload: empty search_subject and status-only seeds
```

### F4.6-F. Neo4j memory schema warning 정리

별도 mini-pass로 수행하되, F4.6에 포함 가능하다.

권장 방향:

- `tool_scan_db_schema` 또는 Neo4j metadata check 결과를 기준으로 chunk query 사용 여부를 결정한다.
- `HAS_CHUNK` relationship이 없으면 chunk vector query를 skip하고 raw PastRecord vector/lexical 경로로 바로 간다.
- warning을 예외처럼 삼키는 대신, adapter 내부 debug trace에 "chunk schema unavailable" 정도만 남긴다.

비범위:

- live DB migration 실행.
- chunk schema를 새로 생성.
- embedding 재생성.

### F4.6-G. 2b truncation 후속 메모

이번 수술의 주된 범위는 아니지만, SO1 후속 관찰로 남긴다.

권장 후속:

- `AnalysisReport` prompt compact.
- max token / max output setting 점검.
- 2b fallback 발생 시 `structured_failure.reason_type=max_tokens|parse_error` 구분.

F4.6 본 PR에서는 테스트가 커지면 메모만 남기고 분리해도 된다.

---

## 구현 순서

### 1. 코드 좌표 재확인

필수 read:

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` §1-A / §2
4. `ANIMA_ARCHITECTURE_MAP.md` purge log #77~#82
5. `Core/pipeline/strategy.py`
6. `Core/nodes.py` `_base_fallback_strategist_output`
7. `Core/pipeline/start_gate.py` `_build_s_thinking_packet`
8. `Core/pipeline/supervisor.py`
9. `Core/pipeline/plans.py`
10. `Core/pipeline/structured_io.py`
11. `Core/adapters/neo4j_memory.py`

### 2. tests 먼저 추가

신규 테스트 후보:

- `tests/test_operation_contract_payload_hardening.py`
- `tests/test_supervisor_operation_contract_guard.py`
- `tests/test_start_gate_missing_payload.py`
- `tests/test_neo4j_memory_schema_fallback.py` 또는 기존 adapter test 확장

필수 케이스:

1. `UserGoalContract.user_goal`만 있는 fallback에서도 `search_subject`가 비지 않는다.
2. `stored or external evidence has not been read yet`가 `query_seed_candidates`에 들어가지 않는다.
3. `what_is_missing` 상태 설명문만 있는 계약은 0_supervisor에서 tool call로 실행되지 않는다.
4. diary exact-date contract는 기존처럼 `tool_read_full_diary(target_date=YYYY-MM-DD)`로 간다.
5. `source_lane=capability_boundary`는 검색하지 않는다.
6. invalid operation_contract는 `structured_failure` 또는 blocked status를 남긴다.
7. Neo4j에 `HAS_CHUNK`가 없을 때 warning 없이 raw PastRecord fallback으로 간다.

### 3. fallback goal source helper 추가

- `_base_fallback_strategist_output` 내부에 직접 길게 쓰지 말고 helper로 분리한다.
- 기존 goal normalizer를 재사용한다.
- raw user_input 복사 방지 테스트를 유지한다.

### 4. start_gate packet contamination 제거

- `what_is_missing`의 status sentence 유입을 줄인다.
- `evidence_state`와 `constraints_for_next_node`에 상태 설명을 옮긴다.
- ThinkingHandoff 9필드 validation은 유지한다.

### 5. operation_contract validator 추가

- 공통 validator 구현.
- fallback planner와 0_supervisor 양쪽에서 재사용한다.
- 실패 이유는 내부 trace용 짧은 enum/string으로 남긴다.

### 6. 0_supervisor guard 적용

- LLM 호출 전 invalid contract 차단.
- deterministic diary exact-date path는 회귀 없이 통과.
- blocked 결과는 기존 graph 라우팅과 충돌하지 않게 한다.

### 7. Neo4j adapter warning 정리

- schema unavailable이면 chunk query skip.
- raw vector/lexical fallback 경로 유지.
- live migration은 실행하지 않는다.

### 8. ARCH MAP 갱신

- `ANIMA_ARCHITECTURE_MAP.md` purge log에 #83 후보로 추가.
- full tests 결과 기록.

---

## 검증 기준

- `python -m pytest -q` 전체 통과.
- 기존 SO1/CR1/C0.8 tests 회귀 없음.
- 현장 trace 재현 시 더 이상 `tool_search_memory(target="stored or external evidence has not been read yet")`가 나오지 않음.
- diary/date exact read trace는 유지:

```text
-1s -> -1a -> 0_supervisor -> phase_1(tool_read_full_diary) -> 2a -> 2b
```

- memory recall trace에서 search target은 `goal_core` / `slot_to_fill` / valid seed 중 하나로만 생성됨.
- invalid contract는 tool 실행이 아니라 structured failure/remand로 남음.
- raw user wording 기반 의미분류/라우팅 휴리스틱 추가 없음.
- `__pycache__` 변경은 보고/커밋 대상에서 제외.

---

## 비범위

F4.6에서 하지 않는다:

- 새 answer_mode classifier 추가.
- `알아?`, `아니야`, 특정 작품명 등 raw marker 기반 의미분류 추가.
- live Neo4j migration 실행.
- DB chunk schema 생성.
- phase_3 답변 텍스트 생성 규칙 변경.
- WarRoom v2 설계.
- 119 enum B9 본체 구현.
- 2b truncation 전면 개편.

---

## 위험 / 롤백

### 위험 1. 너무 강한 guard로 필요한 검색까지 막음

완화:

- diary exact-date path는 명시적으로 통과.
- `goal_core` 또는 `query_seed_candidates` 중 하나만 있어도 허용.
- blocked result는 phase_119 직행이 아니라 기존 remand/repair 경로와 맞춘다.

### 위험 2. `what_is_missing` compatibility test 깨짐

완화:

- 9필드는 유지.
- missing slot이 없을 때는 internal status sentence 대신 slot-like fallback을 넣는다.
- 검색 seed filter가 fallback sentinel을 제거한다.

### 위험 3. Neo4j schema check가 DB 없는 테스트 환경을 깨움

완화:

- schema check는 optional/injected session 기반.
- 실패 시 기존 raw query fallback으로 간다.
- live DB 접속 없는 unit test 가능하게 mock session 사용.

### 롤백

- validator 적용을 supervisor guard에서만 제거하면 기존 F4.5 behavior로 복귀 가능.
- start_gate contamination 변경은 `what_is_missing` 생성부만 되돌리면 된다.
- Neo4j adapter schema skip은 chunk query block만 되돌리면 된다.

---

## 예상 산출

코드 변경 후보:

- `Core/nodes.py`
- `Core/pipeline/start_gate.py`
- `Core/pipeline/supervisor.py`
- `Core/pipeline/plans.py` 또는 `Core/pipeline/structured_io.py`
- `Core/adapters/neo4j_memory.py`
- `ANIMA_ARCHITECTURE_MAP.md`

테스트 후보:

- `tests/test_operation_contract_payload_hardening.py`
- `tests/test_supervisor_operation_contract_guard.py`
- `tests/test_start_gate_missing_payload.py`
- `tests/test_neo4j_memory_schema_fallback.py`

예상 purge log:

```text
83. V4 Phase 1 #F4.6 — operation_contract payload hardening completed.
    Thin-case fallback planner now derives search_subject from normalized
    goal contracts instead of treating UserGoalContract as GoalLock, filters
    internal evidence-state sentinel strings out of query_seed_candidates, and
    blocks 0_supervisor execution when search contracts are empty/status-only.
    Neo4j memory search skips unavailable chunk schema before falling back to
    raw PastRecord vector/lexical search. Full tests: N OK.
```

---

## 결론

F4.6은 F4.5의 자연스러운 후속이다.

F4.5가 `operation_contract`에 검색 축을 열었다면, F4.6은 그 축이 빈 문자열이나 내부 상태문으로 오염된 채 실행되지 않도록 잠근다.

이 발주는 의미를 코드로 판단하는 패치가 아니라, **LLM이 만든 계약이 실행 가능한 계약인지 검문하는 패치**다.
