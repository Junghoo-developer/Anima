# ANIMA Field Loop V2 — Constitution (헌법)

> Document status: LIVE LAW.
> This is the current authority for field-loop code surgery. If older reform or
> future design documents conflict with this file, this file wins.

**작성일**: 2026-04-30
**상태**: 초안. 정후 검토 후 확정.
**역할**: 현장 루프의 모든 청소/구조화/토큰 정상화 작업의 단일 기준점.
**선행 문서**: REFORM_V1, REFORM_IMPLEMENTATION_V1, State_Optimization_Checklist (이 헌법으로 흡수)

---

## 검수 게이트 (대형 nodes.py 분류 전 필수)

이 문서는 아직 초안이다. `Core/nodes.py` 대형 inventory, 삭제, 이동 작업을
시작하기 전에는 정후가 최소한 아래 세 항목을 명시적으로 승인해야 한다.

1. §0 한 줄 요약
2. §1 핵심 5노드 권한표 (`-1s`, `-1a`, `-1b`, `2b`, `phase_3`)
3. §2 절대 금지 15개

§3 이후의 세부 패키지 계획은 작업 중 검수해도 되지만, 위 세 항목은 분류
기준 자체이므로 먼저 확정한다.

---

## 0. 한 줄 요약

> **-1s가 턴 헌법을 제정하면, -1a가 그 안에서 행동(도구/사고)하고, -1b는 승인/반려/SOS만 한다. 사실 판정은 2b, 발화는 phase_3 단독.**

---

## 1. 노드별 권한표

### -1s (입법부 주간 분과)
| 가능 | 금지 |
|------|------|
| turn_contract 제정 (user_intent, answer_mode_policy, normalized_goal, requires_grounding, current_turn_facts) | tool query 직접 작성 |
| reasoning_budget 책정 | final response_strategy 작성 |
| 결산 회기 (예산 소진시) | branch 결정 (FieldMemo 영역) |
| SOS 회기 (-1b 요청시 헌법 개정) | slot 세부 판정 (2b 영역) |
| 추가 예산 의결 / 폐회 의결 | -1a 요청 무시 후 자체 행동 |

### -1a (행정부 정책국, 실권자)
| 가능 | 금지 |
|------|------|
| action_plan 수립 | 라우팅 자체 결정 (요청만) |
| tool_request 작성 (이름 + 인자 + 근거) | -1s 헌법 무시 |
| inner_thought (사고 갈래 발동시) | 사실 판정 (2b 영역) |
| next_routing_request (`tool`/`thinking`/`phase_3`/`sos`) | 자체 phase_3 직행 |
| response_strategy (direct delivery 가능 시) | 같은 analysis로 무한 재시도 |

### -1b (사법부, 4결정자)
| 가능 | 금지 |
|------|------|
| `approve` (-1a 요청 통과) | 새 tool_query 작성 |
| `phase_3` (출력 OK) | 자체 라우팅 결정 (-1a 요청 없이) |
| `sos` (-1s 회의 요청) | 분석/탐정 작업 |
| `phase_119` (비상) | 같은 analysis_signature 핑퐁 (1회 제한) |
| approved_fact_cells, approved_claims 도장 | 도구 인자 직접 작성 |

### 0_supervisor (행정부 집행국)
| 가능 | 금지 |
|------|------|
| -1a/-1b가 정한 tool 집행 | 의미 판단 |
| 도구 결과 패키징 | 도구 인자 자체 작성 (-1a tool_request 그대로) |
| 안전 검증 (위반시 거부) | 라우팅 결정 |

### phase_1 (도구 실행)
| 가능 | 금지 |
|------|------|
| 도구 실제 호출 + 결과 반환 | LLM 호출 (지금도 안 함) |

### 2a (원문 리더)
| 가능 | 금지 |
|------|------|
| search_data → raw_read_report 정제 | 사실 판정 |
| items[] 추출 (excerpt + observed_fact) | 답변 작성 |

### 2b (증거 판사)
| 가능 | 금지 |
|------|------|
| raw_read_report → analysis_report | 라우팅 결정 |
| -1a 사고 fact-check (사고 갈래 발동시 추가 호출) | 답변 작성 |
| evidence judgments | 정책 판단 |

### phase_3 (스피커)
| 가능 | 금지 |
|------|------|
| 최종 사용자 발화 | 새 도구 결정 |
| 자아/관계/공개지식 기반 답변 (contract 한도 내) | 새 evidence 추출 |
| SHORT_TERM_CONTEXT 활용 follow-up | 내부 워크플로 누설 (phase 이름/schema 키) |
| current_turn_facts 직접 인용 | 미승인 fact 인용 |

---

## 2. 절대 금지 목록 (위반 = 자동 거부)

1. raw user_input으로 goal/slot 강제 생성 금지 (-1s가 normalized_goal로 추상화 후만)
2. 내부 전략문을 working_memory.dialogue_state.active_task에 저장 금지
3. FieldMemoWriter가 official branch 결정 금지 (pending/inbox만, official은 심야)
4. `answer_not_ready` 사용자 출력 금지 (clean_failure 메시지 사용)
5. 심야 policy가 낮 루프 route 직접 지배 금지 (도구 사전/예산 가이드만)
6. -1b가 새 tool_query 작성 금지
7. -1a가 라우팅 자체 결정 금지 (next_routing_request 형태로 요청만)
8. -1a가 -1s turn_contract 무시 금지
9. phase_3가 phase 이름/schema 키 누설 금지
10. 같은 analysis_signature로 -1a→-1b→-1a 핑퐁 1회 초과 금지 (위반시 -1b는 sos 발동)
11. tool_carryover 이중 저장 금지 (state 최상위 단일 출처, working_memory에서 제거)
12. response_strategy 이중 저장 금지 (strategist_plan 안만)
13. 죽은 sys_prompt 빌드 금지 (build_*_prompt 함수만 사용)
14. 결정적(deterministic) fallback이 의미 분류/의도 라우팅 시도 금지 (LLM 영역)
15. 코드 휴리스틱이 답변 텍스트(direct_answer_seed) 작성 금지

---

## 3. 남겨야 할 최소 코어 (코드만 책임)

코드는 **활동 추적 / 안전 / schema / tool execution / provenance**만:

1. LangGraph wiring (`Core/graph.py`)
2. Schema validation (`Core/pipeline/contracts.py`)
3. Tool execution mechanics (`phase_1`)
4. Evidence ledger (`Core/evidence_ledger.py`) — 누가 뭘 했는지 추적
5. Loop limit & budget (`reasoning_budget`, `hard_stop`, `max_total_budget`)
6. Speaker guard 최소층 (`Core/speaker_guards.py`) — 누설 방지
7. Activity tracking / provenance (코드가 강하게 추적)
8. `cleanup_turn_lived_fields` (Phase 2 — 턴 종료 자동 정리)
9. Runtime profile/context (`Core/runtime/*`) — 실행 사실/cleanup 경계만

> 보류: self kernel은 이번 runtime 최소 패키지 범위가 아니다. 자아 정보 주입은
> 별도 대개혁에서 다시 설계한다.

→ 이외 의미 판단/계획/요약/답변은 **모두 LLM이**.

---

## 4. 숙청 결정 트리

각 함수/모듈을 봤을 때 순서대로 자문:

```
1. 권한 밖 작업인가? (예: -1b가 도구 인자 작성)
   → 삭제 (decisive)

2. 중복인가? (예: response_strategy 이중 저장)
   → 단일 출처로 통합 후 옛 자리 삭제

3. LLM이 해야 할 일을 코드가 휴리스틱으로 하나? (예: 의도 분류 정규식)
   → 삭제

4. 구조 비전과 정합 안 됨 + 회귀 위험 큼?
   → compatibility wrapper로 격리 (한 시즌 후 night 입법부가 audit 후 제거)

5. 구조 정합 + 위치만 잘못됨? (예: nodes.py에 있는 pipeline 헬퍼)
   → 새 패키지로 이동, nodes.py에 thin wrapper만

6. 구조 정합 + 코드 위생만 부족?
   → 그대로 두고 테스트만 정비

7. 미래 Pass에서 다룰 영역? (예: night loop 내부)
   → 손대지 말 것
```

---

## 5. 대표 런타임 사례 10개 — 기대 경로 + 답변 성격

| # | 사례 | -1s turn_contract | 기대 경로 | 답변 성격 |
|---|------|------------------|---------|---------|
| 1 | "네 이름은 뭐야?" | answer_mode=`public_parametric`, requires_grounding=false, direct_delivery_allowed=true | -1s → phase_3 | 승인된 현재 컨텍스트 기반 직접 답변 |
| 2 | "써니의 누나는?" | answer_mode=`public_parametric`, intent=`public_knowledge_question` | -1s → phase_3 | 공개지식 직답, 불확실시 모른다고 |
| 3 | "아까 내가 말했잖아" | intent=`continuation`, source_lane=`recent_dialogue_review` | -1s → -1a → 2a (recent_dialogue_review) → 2b → -1b → phase_3 | 최근 맥락 이어가기 |
| 4 | "내 기억 검색해봐" | intent=`requesting_memory_recall`, requires_grounding=true | -1s → -1a → tool_search_memory → 2a → 2b → -1b → phase_3 | 검색 결과 기반 요약 |
| 5 | "오모리 주인공은?" | answer_mode=`public_parametric`, intent=`public_knowledge_question` | -1s → phase_3 | 공개지식 답변 |
| 6 | "내 일기 아무거나 검색해봐" | intent=`memory_recall`, broad | -1s → -1a → tool_search_memory → 2a → 2b → -1b → phase_3 | 검색 결과 기반 |
| 7 | "ㅇㅇ" | short ack, pending dialogue_act 있음 | -1s → -1b lite → phase_3 | SHORT_TERM_CONTEXT의 pending act 이어가기 |
| 8 | "왜 반복해?" | feedback/correction | -1s → phase_3 (clean failure or correction) | 모르면 모른다고 / 사과 + 수정 |
| 9 | "내가 만든 거 기억해?" | intent=`requesting_memory_recall`, ambiguous | -1s → -1a → tool_search_field_memos → 2a → 2b → -1b → phase_3 | 검색 결과 또는 모른다고 |
| 10 | "이 문서 읽어봐" | artifact_hint 감지 | -1s → -1a → tool_read_artifact → 2a → 2b → -1b → phase_3 | 문서 요약 |

### 모든 사례 공통 룰
- -1s는 **항상** 첫 노드 (turn_contract 제정)
- phase_3는 **항상** 마지막 (clean_failure 포함)
- 어떤 사례도 -1b가 라우팅 자체 결정 안 함
- 사례 1, 2, 5는 -1a 거치지 않고 -1s에서 phase_3로 직행 (direct_delivery_allowed)
- 사례 7은 lite_auditor 활용 (가벼운 follow-up)

---

## 6. 패키지 최종 구상

```text
Core/
  pipeline/        # 현장 노드 내부 로직 (이미 진행 중)
    start_gate.py
    strategy.py
    readiness.py
    supervisor.py
    tool_execution.py
    reader.py
    fact_judge.py
    delivery.py
    rescue.py
    contracts.py
    packets.py
    plans.py
    shared_packets.py     # NEW: user_meta + projection
    routing.py            # NEW: SOS / approve / phase_3 분기
    review_session.py     # NEW: -1s 결산 회기 + SOS 회기
    
  memory/          # NEW (REFORM Pass 3)
    working_memory_writer.py
    field_memo_writer.py
    memory_contracts.py
    memory_sanitizer.py
    
  runtime/         # NEW (REFORM Pass 4)
    runtime_profile.py
    context_packet.py
    cleanup.py            # cleanup_turn_lived_fields
    
  warroom/         # 이미 진행 중
    contracts.py
    deliberator.py
    output.py
    state.py
    
  night/           # NEW (REFORM Pass 5, 입법부 야간 분과)
    reflection_graph.py
    audit_field_usage.py  # 입법부 자동 감시
    branch_growth.py
    policy_assets.py
    rem_governor.py       # 옮김
    strategy_council.py
    
  adapters/        # 이미 진행 중
    artifacts.py
    neo4j_connection.py
    neo4j_memory.py
    night_queries.py
    seed_files.py
    web_search.py
```

---

## 7. nodes.py 최종 목표

**최종 분량 < 300줄**. 다음만 남음:

```python
# 1. Public graph node functions (각 1~3줄 wrapper)
def phase_minus_1a_thinker(state):
    return run_phase_minus_1a_thinker(state, **_strategy_deps())

# 2. Dependency wiring (또는 Core/runtime/wiring.py로 분리 가능)
def _strategy_deps():
    return {...}

# 3. Backward compatibility imports (한 시즌 후 제거)
from .pipeline.shared_packets import build_user_meta_packet  # noqa: F401
```

→ 모든 헬퍼는 pipeline/memory/runtime으로 이주. 의미 분류/휴리스틱은 삭제.

---

## 8. Memory 계층 최종 권한

| 주체 | 쓸 수 있는 영역 | 읽을 수 있는 영역 |
|------|-------------|-------------|
| **WorkingMemoryWriter** | working_memory.{dialogue_state, evidence_state, response_contract, temporal_context, user_model_delta, memory_writer, turn_summary} | 전체 working_memory + 직전 턴 결과 |
| **FieldMemoWriter** | FieldMemo 후보 작성 (branch_path는 **추천만**, 기본 pending/inbox) | EvidenceLedger 활동 기록, 직전 working_memory |
| **심야정부 (Night Loop)** | FieldMemo official branch 승격, schema 변경 권고, deprecated field 발견, REM/Strategy/Branch growth assets | 모든 turn_history (장기), 모든 FieldMemo, EvidenceLedger 누적 |
| **검색기 (read-only adapters)** | (쓰기 권한 없음) | FieldMemo 검색, MemoryBuffer 읽기, EvidenceLedger 읽기, Artifact 읽기 |
| **현장 노드들** | 자기 산출물 (state 자기 영역) | turn_contract (-1s 발급), -1a 결과 (-1b/2b가 읽음), analysis (-1a/-1b가 읽음), working_memory_brief (제한 sub-key) |

---

## 9. 회기 메커니즘 (-1s 발동 트리거)

```
[1차 회기 - 매 턴 시작]
  -1s 호출 → reasoning_budget 책정 + turn_contract 제정
  → direct_delivery 가능시 phase_3 직행
  → 아니면 -1a로

[활동기]
  -1a → -1b 루프, reasoning_budget 한도 내에서

[2차 회기 - 결산 (loop_count >= reasoning_budget)]
  -1s 재호출 → -1a 누적 산출물 검토
  → phase_3 (충분함)
  → 추가 예산 의결 + -1a로 (계속)
  → phase_119 (포기)

[3차 회기 - SOS (-1b 요청)]
  -1b가 sos 발동 → -1s 재호출 → 헌법 개정 옵션
  → 새 normalized_goal 발급
  → 또는 기존 무효화 + clean_failure
  → 또는 추가 예산 없이 폐회

[메타 한도]
  max_total_budget = 10
  total_loop_count > 10 시 → 강제 phase_3 (clean_failure) 또는 phase_119
  SOS도 한 턴당 1회 제한 (남용 방지)
```

---

## 10. 시행 순서 (대숙청 작업 순서)

이 헌법 확정 후 작업 단계:

```
0. 헌법 확정 (지금)
   ↓
1. 비전 정합 적폐 청소 (Codex 작업)
   - 권한 밖 코드 식별 & 삭제
   - 절대 금지 목록 위반 코드 식별 & 삭제
   - 죽은 코드 (sys_prompt 26줄, lite_auditor 라우팅 등) 정리
   ↓
2. 구조 이전
   - response_strategy + operation_plan → strategist_plan (Phase 1)
   - turn-lived/long-lived 분리 + cleanup (Phase 2)
   - SOS 라우트 신설, plan_with_strategist 폐기
   - lite_auditor 라우팅 활성화
   - Core/memory/, Core/runtime/ 패키지 신설
   ↓
3. 토큰 정상화 마무리
   - prompt packet projection 마무리 (Phase 3)
   - working_memory_brief 화이트리스트 확정
   - phase_3 contract 슬림화
   - -1b sys_prompt 12룰 → 4룰
   ↓
4. 입법부 야간 분과 (audit_field_usage)
   - 안 쓰는 필드 자동 발견
   - schema 변경 권고
   ↓
5. WarRoom v2 / 사고 갈래 / -1s 회기 메커니즘 활성화
```

---

## 11. 역할 분담 (사람 ↔ AI)

| 역할 | 담당 |
|------|------|
| 비전 결정 / 헌법 개정 | 정후 (입법부 본인) |
| 비전 토론 + 코드 진단 + Codex 작업 검수 | Claude (사법부 자문) |
| 코드 작성/수정/테스트 | Codex (행정부 실무) |
| 최종 결재 (merge) | 정후 |

→ 클로드는 코드 안 쓰고, Codex는 비전 결정 안 함. 각자 본업.

---

## 부록 A. 결정 보류 항목 (헌법 확정 시 정후가 답할 것)

- [ ] **Q3**: -1s가 SOS 받아 목표 변경시 형식 — 새 발급 / 패치 / 무효화 중 무엇?
- [ ] **메타 한도 정책** — `max_total_budget = 10`이 적절? 다른 값?
- [ ] **-1s 결산 회기에서 추가 예산 최대치** — 한 회기에 +1? +2? +N?
- [ ] **lite_auditor 라우팅 활성화 범위** — 사례 7만? 다른 가벼운 사례도?
- [ ] **Q1 Q2 확정 여부** — 결산 회기 + SOS 라우트 = 확정. 동의?

---

## 부록 B. 청소 결정 빠른 참조 (Codex용)

함수를 만났을 때 5초 안에 결정:

1. **이 함수가 어떤 노드의 권한 영역?** 1번 표 보고 매칭.
2. **그 노드가 만들면 안 되는 거?** 2번 금지 목록 보고 매칭.
3. 둘 중 하나라도 위반 → **삭제 후보**.
4. 정합되면 → 위치 점검 (4번 트리), 보통 **이동 또는 그대로**.

---

**문서 버전**: V2 초안
**다음 갱신**: 정후 확정 후 V2.0
