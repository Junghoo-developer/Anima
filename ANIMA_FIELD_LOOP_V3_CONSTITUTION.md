*[한국어](ANIMA_FIELD_LOOP_V3_CONSTITUTION.md) | [English](ANIMA_FIELD_LOOP_V3_CONSTITUTION.en.md)*

# ANIMA Field Loop V3 — Constitution (헌법)

**작성일**: 2026-05-01
**상태**: V3 정후 통과 (2026-05-01). V3 §10 현장 루프 시행은 purge log 53 기준 완료. V4 논의 가능.
**역할**: 송련 현장 루프의 모든 청소·구조화·토큰 정상화 작업의 단일 기준점.
**선행 문서**: V2 헌법 (정후 통과 시 deprecate), REFORM_V1, REFORM_IMPLEMENTATION_V1
**갱신 트리거**: V3 권한표/금지목록의 오류 수정은 V3.x, 새 구조 개혁은 V4에서 논의.

---

## 0. 한 줄 요약

> **송련은 사고하는 인격이다. -1s가 두 갈래 사고(상황+루프)로 매 사이클을 정리하면, -1a가 그 위에서 목표·계획·도구·인자를 짠다. 0차가 집행하고 2a/2b가 검증한다. 충분해지면 phase_3가 답변을 만들고 -1b LLM이 그 답변을 결재한다. 어느 노드도 다른 노드 본업을 침범하지 않는다.**

### 핵심 원칙
1. **사고는 -1s, 수립은 -1a, 검증은 2b, 발화는 phase_3, 결재는 -1b.**
2. **코드는 추적·안전·schema·실행·라우팅만. 의미는 모두 LLM.**
3. **자기 평가 금지** — 자기 작업은 자기가 평가하지 않는다.
4. **비유**: 입법부/행정부/사법부 폐기. *"송련 내부 사고 모델."* 노드 번호로 호명.

---

## 1. 노드별 권한표

### -1s (사고 컴파일러)

| 가능 | 금지 |
|------|------|
| 상황 사고 (외부 세계 이해) | 도구 인자 직접 작성 |
| 루프 사고 (진행 + 다음 방향 + 라우팅) | -1a 계획 트리(strategist_output, operation_plan) 직접 읽기 |
| reasoning_budget 발급 | 답변 텍스트 작성 |
| 4슬롯 패킷 출력 | 사실 검증 (2b 본업) |
| sos 트리거 (119 호출) | -1a에 도구 직접 명령 (next_direction은 추상 가이드만) |
| 결산 회기 (예산 소진시) | -1a 계획을 직접 수정 |
|  | 답변 결재 (-1b 본업) |

**입력**: user_input, working_memory_brief, analysis_report, execution_trace 메타, 이전 사이클 자기 패킷 누적.
**출력**: `s_thinking_packet` (4슬롯 — 부록 C 참조).

### -1a (계획 수립자)

| 가능 | 금지 |
|------|------|
| 목표 수립 (`strategist_goal`) | 라우팅 결정 (-1s 본업) |
| 계획 수립 + 수정 (`strategist_output`) | 자기 작업 평가 (자기 검열) |
| 도구 이름 + 인자 (`tool_request`) | 답변 텍스트 작성 |
| 도구 결과 1차 라벨링 | 사실 검증 (2b 본업) |
| -1s 피드백 받아 새 계획 | -1s 사고 무시 |
| `analysis_report` 직접 참고 | `finalize_recommendation` 외침 (슬롯 폐기) |

**입력**: `s_thinking_packet` (situation + loop_summary + next_direction), `analysis_report`, `working_memory_brief`.
**출력**: `strategist_goal`, `strategist_output`, `operation_plan.tool_request`.

### -1b (답변 결재자)

| 가능 | 금지 |
|------|------|
| phase_3 답변 LLM 결재 | 새 `tool_query` 작성 |
| LLM 영역 판정 (환각/누락/톤) | -1a 계획 결재 (phase_3 *전* 결재 폐지) |
| END 또는 remand 결정 | 사실 검증 (2b 본업) |
| 거절 누적 한 턴 3회 한도 (3회 초과 시 자동 sos_119, §2-23) | 라우팅 결정 (-1s 본업) |
| sos 발동 (delivery_loop) | 분석/탐정 작업 |

**위치**: phase_3 *후* (단일 결재 출구). pre-delivery 위치 없음 (old `-1b_auditor` 노드는 V3 §10 7C에서 폐지 — 정후 2026-05-01 결정).
**입력**: phase_3 답변 + 답변 빌딩 컨텍스트 (`analysis_report`, `response_strategy`). `s_thinking_packet`은 동봉하지 않는다 (독립 판정 보존, 에코 체임버 회피).
**출력**: `delivery_review` (END / remand + 사유).

### 2a (원문 리더)

| 가능 | 금지 |
|------|------|
| `raw_read_report` 추출 (excerpt + observed_fact) | 사실 판정 |
| 출처 정리 | 답변 작성 |

### 2b (사실 판사)

| 가능 | 금지 |
|------|------|
| `analysis_report` 작성 (evidences, source_judgments, usable_field_memo_facts) | 라우팅 결정 |
| 검증 사실의 단일 출처 | 답변 작성 |
| -1s 피드백 받아 재판정 | 정책 판단 |

**1차 독자**: -1s + -1a (둘 다 직접).

### phase_3 (스피커)

| 가능 | 금지 |
|------|------|
| 최종 사용자 답변 작성 | 새 도구 결정 |
| 자아/관계/공개지식 + 검증 사실 인용 | 새 evidence 추출 |
| `current_turn_facts` 직접 인용 | 내부 워크플로 누설 (phase 이름, 슬롯 키, 119, budget) |
| 119 인수인계 패킷 받아 자연어 변환 | 미승인 fact 인용 |
| `s_thinking_packet` 참고 (사용자 의도 톤 정렬) | `answer_mode` 자체 변경 (§2-22) |
|  | `s_thinking_packet` 텍스트 그대로 복사 |

**위치**: graph 답변 생성 단계 (-1b 결재 직전).
**입력**:
- `user_input`
- `response_strategy` (-1a 확정값 — 도구 케이스에서)
- `reasoning_board` (누적 사고)
- `analysis_report` (검증 사실, 직접 인용)
- `working_memory_brief` (compact)
- `recent_context`
- `s_thinking_packet` (참고용 동봉, 직답 케이스에서 `answer_mode` 결정 출처)
- `rescue_handoff_packet` (119 통과 시)

**제거 대상 (V3 정리)**: `search_results`, `supervisor_instructions`, `loop_count` (`analysis_report`와 `rescue_handoff_packet`에 흡수).

**출력**: 사용자 답변 텍스트.

### 0_supervisor (집행국)

| 가능 | 금지 |
|------|------|
| -1a `tool_request` 집행 | 의미 판단 |
| 결과 패키징 | 라우팅 결정 |
| 안전 검증 (위반시 거부) | 도구 인자 자체 작성 |

### phase_1 (도구 호출)

| 가능 | 금지 |
|------|------|
| 도구 실제 호출 + 결과 반환 | LLM 호출 (아예 안 함) |

### phase_119 (인수인계 노드)

| 가능 | 금지 |
|------|------|
| `rescue_handoff_packet` 작성 | 재조사 / 추가 도구 호출 |
| `preserved_evidences` (검증된 부분 사실) 보존 | `analysis_report.evidences` 전체 비우기 |
| `rejected_only` 차단 대상 분리 | phase_3 *전* 결재 |

**진입 트리거**: budget 초과, -1s sos, -1b delivery_loop.

### WarRoom (사고 실험실)

| 가능 | 금지 |
|------|------|
| -1s sos급 깊은 토론 | 평시 라우팅 |
| 차세대 범용 지능 사고 실험 | -1s 본업 침범 |

**평시 사용 X**. -1s 단독 사고가 평시 본업.

---

## 2. 절대 금지 목록 (위반 = 자동 거부)

1. raw user_input으로 goal/slot 강제 생성 금지 (-1s 추상화 후만)
2. 내부 전략문을 `working_memory.dialogue_state.active_task`에 저장 금지
3. FieldMemoWriter가 official branch 결정 금지 (pending/inbox만)
4. `answer_not_ready` 사용자 출력 금지 (clean_failure 사용)
5. 심야 policy가 낮 루프 route 직접 지배 금지
6. -1b가 새 `tool_query` 작성 금지
7. -1a가 라우팅 자체 결정 금지 (-1s `routing_decision` 영역)
8. -1a가 -1s 사고 무시 금지
9. phase_3가 phase 이름/schema 키/119/budget 누설 금지
10. **같은 도구 결과로 -1s↔-1a 핑퐁 1회 초과 금지** (위반시 119 진입)
11. `tool_carryover` 이중 저장 금지 (state 최상위 단일 출처)
12. `response_strategy` 이중 저장 금지 (`strategist_plan` 안만)
13. 죽은 sys_prompt 빌드 금지 (`build_*_prompt` 함수만)
14. **결정적 fallback이 의미 분류/의도 라우팅 시도 금지** (LLM 영역)
15. **코드 휴리스틱이 답변 텍스트(`direct_answer_seed`) 작성 금지**
16. **NEW** -1s가 -1a 계획 트리(`strategist_output`, `operation_plan`) 직접 읽기 금지 (에코 체임버 회피)
17. **NEW** -1s `next_direction`이 도구 이름/쿼리 직접 명령 금지 (추상 가이드만)
18. **NEW** -1a가 자기 작업 평가/`finalize_recommendation` 외침 금지 (자기 검열 금지)
19. **NEW** 119가 `analysis_report.evidences` 전체 비우기 금지 (검증된 부분 사실 보존)
20. **NEW** -1b가 phase_3 *전*에 결재 시도 금지 (phase_3 후 단일 결재)
21. **NEW** `max_total_budget` 초과 시 119 자동 진입, 다른 노드 우회 금지
22. **NEW** phase_3 `answer_mode` 결정 권한 순서: 119(`rescue_handoff_packet`) → -1a(`response_strategy.delivery_freedom_mode`) → -1s(`s_thinking_packet.situation_thinking.domain`). 후위 노드가 전위 노드를 이긴다. phase_3는 자체적으로 `answer_mode`를 변경하지 않고 받은 값을 따른다.
23. **NEW** -1b 답변 거절 누적은 한 턴 내 3회 한도 (turn-lived counter). 3회 초과 시 자동 sos_119 (delivery_loop trigger). -1b는 매 거절 시 LLM이 verdict(approve/remand/sos_119)를 선택, 코드는 카운터 + 한도만 강제.
24. **NEW** phase_3는 `must_include_facts` 또는 `analysis_report.evidences` / `analysis_report.usable_field_memo_facts`에 있는 사실만 인용 가능. 추측·번역·해석으로 새 사실 생성 금지. 모르면 "모른다"고 명시 (사용자 친화 표현). 사전 환각 방지가 사후 -1b 결재보다 우선 (§0 한 줄 정합).

---

## 3. 남겨야 할 최소 코어

코드는 **활동 추적 / 안전 / schema / tool execution / provenance / 라우팅**만:

1. LangGraph wiring (`Core/graph.py`)
2. Schema validation (`Core/pipeline/contracts.py`)
3. Tool execution mechanics (`phase_1`)
4. Evidence ledger (`Core/evidence_ledger.py`)
5. Loop limit & budget (`reasoning_budget`, `hard_stop`, `max_total_budget`)
6. Speaker guard 최소층 (`Core/speaker_guards.py`)
7. Activity tracking / provenance
8. `cleanup_turn_lived_fields` (Phase 2)
9. **NEW** Runtime context packet (`Core/runtime/context_packet.py` — -1s 누적 패킷 조립)

→ 이외 의미 판단·계획·요약·답변은 **모두 LLM이.**

---

## 4. 숙청 결정 트리

각 함수/모듈 보면서 자문:

```
1. 권한 밖 작업인가? (§1)
   → 삭제

2. 절대 금지 위반? (§2)
   → 삭제

3. LLM이 해야 할 일을 코드가 휴리스틱으로 하나? (§2-14, §2-15, §2-16)
   → 삭제

4. 중복? (response_strategy 이중 등)
   → 단일 출처 통합 후 옛 자리 삭제

5. 구조 비전 정합 안 됨 + 회귀 위험 큼?
   → compatibility wrapper 격리 (한 시즌 후 audit)

6. 정합 + 위치만 잘못?
   → 새 패키지로 이동

7. 정합 + 위생만 부족?
   → 그대로, 테스트만 정비

8. 미래 Pass 영역?
   → 손대지 말 것
```

---

## 5. 대표 런타임 사례 10개 (V3 wiring 반영)

| # | 사례 | -1s `routing_decision` | `answer_mode` (최종) | 기대 경로 | 답변 성격 |
|---|------|---------|---------|---------|---------|
| 1 | "네 이름은?" | `phase_3` (self_kernel) | `self_kernel_response` | -1s → phase_3 → -1b → END | 자아 직답 |
| 2 | "써니의 누나는?" | `phase_3` (public_parametric) | `public_parametric_knowledge` | -1s → phase_3 → -1b → END | 공개지식 직답 |
| 3 | "아까 내가 말했잖아" | `-1a` (continuation) | `simple_continuation` 또는 `current_turn_grounding` | -1s → -1a → tool → 2a → 2b → -1s → phase_3 → -1b → END | 최근 맥락 |
| 4 | "내 기억 검색" | `-1a` (memory_recall) | `memory_recall` | -1s → -1a → tool_search_memory → ... → phase_3 → -1b → END | 검색 기반 |
| 5 | "오모리 주인공?" | `phase_3` (public_parametric) | `public_parametric_knowledge` | -1s → phase_3 → -1b → END | 공개지식 |
| 6 | "내 일기 검색" | `-1a` (memory_recall, broad) | `memory_recall` | -1s → -1a → ... → phase_3 → -1b → END | 검색 |
| 7 | "ㅇㅇ" | `phase_3` (short_ack) | `simple_continuation` | -1s → phase_3 → -1b → END | pending act 이어가기 |
| 8 | "왜 반복해?" | `phase_3` (feedback) | `simple_continuation` | -1s → phase_3 → -1b → END | 사과 + 수정 |
| 9 | "내가 만든 거 기억해?" | `-1a` (memory_recall, ambiguous) | `memory_recall` | -1s → -1a → ... → phase_3 → -1b → END | 검색 또는 모름 |
| 10 | "이 문서 읽어봐" | `-1a` (artifact_hint) | `current_turn_grounding` | -1s → -1a → tool_read_artifact → ... → phase_3 → -1b → END | 문서 요약 |

### 모든 사례 공통
- -1s는 **항상** 첫 노드.
- phase_3가 **항상** 답변을 만든다.
- -1b가 **항상** phase_3 직후 결재.
- END 단일 출구 (또는 119 → phase_3 → -1b → END).

---

## 6. 패키지 최종 구상

```text
Core/
  pipeline/
    start_gate.py
    strategy.py
    readiness.py        # → -1b 위치 변경에 따라 슬림화
    supervisor.py
    tool_execution.py
    reader.py
    fact_judge.py
    delivery.py
    rescue.py           # → rescue_handoff_packet 신설
    contracts.py
    packets.py
    plans.py
    routing.py          # NEW: -1s routing_decision 분기

  memory/               # NEW (Pass 3)
    working_memory_writer.py
    field_memo_writer.py
    memory_contracts.py
    memory_sanitizer.py

  runtime/              # NEW (Pass 4 — self_kernel.py 보류)
    runtime_profile.py
    context_packet.py   # -1s 누적 패킷 조립
    cleanup.py          # cleanup_turn_lived_fields
    # self_kernel.py 보류 (대개혁이 대체할 임시 인프라)

  warroom/
    contracts.py
    deliberator.py
    output.py
    state.py

  night/                # NEW (Pass 5)
    reflection_graph.py
    audit_field_usage.py
    branch_growth.py
    policy_assets.py
    rem_governor.py
    strategy_council.py

  adapters/
    artifacts.py
    neo4j_connection.py
    neo4j_memory.py
    night_queries.py
    seed_files.py
    web_search.py
```

---

## 7. nodes.py 최종 목표

**최종 분량 < 300줄**. wrapper + dependency wiring만.

```python
def phase_minus_1a_thinker(state):
    return run_phase_minus_1a_thinker(state, **_strategy_deps())

def _strategy_deps():
    return {...}

# 호환 import (한 시즌 후 제거)
```

→ 모든 헬퍼는 pipeline/memory/runtime으로 이주.

---

## 8. Memory 계층 최종 권한

| 주체 | 쓸 수 있는 영역 | 읽을 수 있는 영역 |
|------|-------------|-------------|
| WorkingMemoryWriter | `working_memory.{dialogue_state, evidence_state, response_contract, temporal_context, user_model_delta, memory_writer, turn_summary}` | 전체 working_memory + 직전 턴 |
| FieldMemoWriter | FieldMemo 후보 (pending/inbox 기본, branch_path는 추천만) | EvidenceLedger, working_memory |
| 심야정부 | FieldMemo official 승격, schema 권고, deprecated 발견, REM/Strategy/Branch growth | turn_history 누적, FieldMemo, EvidenceLedger 누적 |
| 검색기 (read-only) | (쓰기 X) | FieldMemo, MemoryBuffer, EvidenceLedger, Artifact |
| 현장 노드 | 자기 산출물 | `s_thinking_packet`, `analysis_report` (제한 sub-key), `working_memory_brief` |

---

## 9. 회기 메커니즘 (V3 — 새 모델)

```
[1차 회기 — 매 턴 시작]
  -1s 호출 → 4슬롯 패킷 (situation_thinking + loop_summary + next_direction + routing_decision)
    → routing_decision = "phase_3" → phase_3 → -1b → END
    → routing_decision = "-1a" → -1a 사이클 시작

[활동기]
  -1a (목표·계획·도구·인자) → 0차 → phase_1 → 2a → 2b
    → -1s 사이클 N+1 (점검 + routing_decision 갱신)
    → "phase_3" / "-1a 또" / "119"

[2차 회기 — 결산 (loop_count >= reasoning_budget)]
  -1s 재호출 → 누적 산출물 검토
    → routing_decision = "phase_3" (충분)
    → 추가 예산 의결 + "-1a" (계속)
    → "119" (포기)

[3차 회기 — SOS]
  -1s가 sos 외침 → 119 진입 → rescue_handoff_packet → phase_3 → -1b → END

[4차 회기 — Delivery Loop]
  -1b가 거절 N회 누적 → 119 진입

[메타 한도]
  max_total_budget = 10
  total_loop_count > 10 → 강제 119
  SOS 한 턴당 1회 제한
  핑퐁: 같은 도구 결과로 -1s ↔ -1a 1회 초과 금지
```

---

## 10. 시행 순서

```
✅ 0. 헌법 V3 확정 (정후 검수 통과 2026-05-01)
✅ 1. ARCHITECTURE_MAP 상태 문구 정정 (Claude, 2026-05-01)
✅ 2. Core/runtime 최소 패키지 신설 (Codex, purge log 36/40)
✅ 3. Core/memory 최소 패키지 신설 (Codex, purge log 37/41)
✅ 4. nodes.py 잔재 inventory (Codex, purge log 42)
✅ 5. InferenceBuffer 의미 필드 오염 차단 (Codex, purge log 43)
✅ 6A. -1s 4슬롯 schema 정의 + start_gate.py (Codex, purge log 44)
✅ 6B. context_packet.py 누적 함수 구현 (Codex, purge log 51)
       - 압축 누적 (history_compact + current 4슬롯 풀)
       - V3 §9 2차 회기의 "누적 산출물 검토" 충족
✅ 7A. delivery contract scaffold (Codex, purge log 45)
✅ 7B. post-delivery 게이트 신설 (Codex, purge log 46)
✅ 7C. old -1b_auditor 노드 **완전 폐지** (Codex, purge log 52)
       - graph wiring에서 -1b_auditor 제거
       - 기존 -1b 라우팅 권한은 -1s로 통합 (V3 §1 -1s routing_decision 본업과 정합)
       - phase_2/0차/warroom의 다음 노드는 -1s (사고 재개)
       - Core/pipeline/readiness.py 폐지
       - phase_3 후 delivery_review가 유일한 -1b 위치 (V3 §0 한 줄과 정합)
✅ 7D. delivery_review deterministic → LLM reviewer 교체 (Codex, purge log 53)
✅ 8. 119 rescue_handoff_packet 신설 (Codex, purge log 47)
       - rescue.py: evidences=[] 폐기
       - preserved_evidences/preserved_field_memo_facts 보존
       - rejected_only 분리
       - user_facing_label은 119 코드 enum + phase_3 자연어 변환 (Q3)

✅ 9A. strategist_goal 마이그레이션 + -1a 출력 슬림화 (Codex, purge log 48)
       - normalized_goal → strategist_goal 한 시즌 호환 wrapper (Q7 옵션 b)
       - state.py에 둘 다 등재, alias로 호환
       - nodes.py 35곳 점진 교체 (한 번에 다 안 바꿈)
       - operation_plan / strategist_output / response_strategy 토큰 다이어트
✅ 9B. 입력 패킷 다이어트 (Codex, purge log 49)
       - working_memory_brief 화이트리스트 확정
       - analysis_report projection (compactor 강화)
       - s_thinking_packet sub-field 최소
       - rescue_handoff_packet 핵심 필드만
✅ 9C. 노드 sys_prompt + contract 슬림화 (Codex, purge log 50)
       - phase_3 contract 슬림화 (내부 필드 최소)
       - delivery_review reviewer prompt (7D 준비)
       - reasoning_board projection

V3 core completed:
✅ field-loop authority relocation
✅ prompt/state token diet
✅ old pre-delivery -1b removal
✅ post-phase3 LLM delivery review

V4 / future candidates:
⚪ 10. 입법부 야간 분과 (audit_field_usage)
⚪ 11. WarRoom v2 / 사고 실험실 활성화
⚪ 12. midnight_reflection.py 분리 (Pass 5)
⚪ 13. self-kernel / identity injection
⚪ 14. DB migration, embedding, developer tooling reform
⚪ 15. normalized_goal compatibility wrapper removal
```

---

## 11. 역할 분담

| 역할 | 담당 |
|------|------|
| 비전 / 헌법 개정 | 정후 (입법부) |
| 비전 토론 + 코드 진단 + Codex 작업 검수 | Claude (사법부 자문) |
| 코드 작성/수정/테스트 | Codex (행정부 실무) |
| 최종 결재 (merge) | 정후 |

→ 클로드는 코드 안 쓰고, Codex는 비전 결정 안 함.

---

## 부록 A. 결정 보류 항목 (V3 — 정후 추가 검수)

V2의 결정 보류는 §0~§9에 흡수되어 풀림. 새 보류 항목:

- [ ] **Q1 (V4 후보)**: -1s 4슬롯 schema의 정확한 sub-field 확장 여부. V3 구현은 현재 부록 C schema로 완료. 추가 sub-field 설계는 V4에서 논의.
- [x] **Q2 (결정 2026-05-01)**: -1b는 매 거절 시 LLM이 verdict 선택 (approve / remand / sos_119). 코드 메타 한도: **한 턴 내 -1b 거절 누적 3회 초과 시 자동 sos_119** (turn-lived counter). §2-23으로 룰 박음.
- [x] **Q3 (결정 2026-05-01)**: `rescue_handoff_packet.user_facing_label`은 **119 코드가 enum으로 작성**, phase_3 LLM이 자연어로 변환. 119는 LLM 호출 안 함 (§1 phase_119 권한과 정합). enum 후보: `"검색 결과 부족" / "기억 못 찾음" / "질문이 모호함" / "재시도 필요"` 등 — Codex 작업에서 추가/삭제 가능, V3.x로 등재.
- [ ] **Q4 (V4 후보)**: WarRoom 트리거 조건 — V3에서는 평시 라우팅에서 물러난 사고 실험실로 보류. 다중 좌석 WarRoom v2 설계 때 확정.
- [x] **Q5 (점검 2026-05-01)**: direct_delivery 케이스에서도 `loop_summary`는 정상 객체로 채워짐 (`attempted_so_far=["start_gate_contract"]`, `current_evidence_state` 문자열, `gaps` 배열). V3 비전 정합. 코드 변경 불필요.
- [x] **Q6 (결정/구현 2026-05-01)**: -1s 누적 패킷은 **압축 누적** (옵션 b). `history_compact`(이전 사이클 짧은 요약) + `current`(최신 4슬롯 풀). 구현 위치는 `Core/runtime/context_packet.py`. V3 §10 단계 6B로 구현 완료.
- [x] **Q7 (결정/구현 2026-05-01)**: `normalized_goal` → `strategist_goal` 마이그레이션은 **한 시즌 호환 wrapper** (옵션 b). state.py에 둘 다 등재, alias로 호환. V3 §10 단계 9A로 구현 완료. 한 시즌 후 wrapper 제거는 V4 후보.

---

## 부록 B. 청소 결정 빠른 참조 (Codex용)

함수 만나면 5초 결정:

1. **권한 밖?** (§1) → 삭제
2. **절대 금지 위반?** (§2) → 삭제
3. **휴리스틱?** (§2-14, §2-15, §2-16) → 삭제
4. **중복?** → 통합
5. **위치 잘못?** → 이동
6. **정합 + 위생만?** → 그대로

---

## 부록 C. 신설 슬롯 schema 명세

### `s_thinking_packet` (-1s 출력)

```python
{
    "situation_thinking": {
        "user_intent": "...",
        "domain": "memory_recall | public_parametric | self_kernel | continuation | feedback | artifact_hint | ambiguous",
        "key_facts_needed": [...],
    },
    "loop_summary": {
        "attempted_so_far": [...],
        "current_evidence_state": "...",
        "gaps": [...],
    },
    "next_direction": {
        "suggested_focus": "...",       # 추상 가이드만 (§2-17)
        "avoid": [...],                 # 추상 가이드만
        # 도구 이름/쿼리 직접 명령 금지 (§2-17)
    },
    "routing_decision": {
        "next_node": "-1a | phase_3 | 119",
        "reason": "...",
    },
}
```

### `rescue_handoff_packet` (119 출력)

```python
{
    "trigger": "budget_exceeded | s_sos | delivery_loop",
    "attempted_path": [...],

    "preserved_evidences": [...],            # 검증된 부분 사실 (NEW)
    "preserved_field_memo_facts": [...],     # 검증된 메모 부분 사실 (NEW)
    "rejected_only": [...],                  # 차단 대상만

    "what_we_know": [...],                   # 자연어 요약
    "what_we_failed": [...],
    "speaker_tone_hint": "사과 + 부분정보 | 단순 모르겠다 | 재질문 | 다음 턴 약속",
    "user_facing_label": "...",              # phase_3가 자연어로 변환
}
```

### `delivery_review` (-1b 출력)

```python
{
    "verdict": "approve | remand | sos_119",
    "reason": "...",
    "issues_found": ["환각 위험" | "사실 누락" | "톤 부적절" | ...],
    "remand_target": "-1a | -1s",         # remand인 경우만
    "remand_guidance": "...",             # remand인 경우만
}
```

### `strategist_goal` (-1a 출력 — `normalized_goal` 후속)

```python
{
    "user_goal_core": "...",
    "answer_mode_target": "memory_recall | public_parametric | self_kernel | ...",
    "success_criteria": [...],
    "scope": "narrow | broad",
}
```

---

**문서 버전**: V3 implementation-complete 정리본 (2026-05-01)
**다음 갱신**: V3 오류 수정은 V3.x, 새 구조 개혁은 V4에서 논의
**deprecate 상태**: V2 헌법은 V3에 의해 superseded
