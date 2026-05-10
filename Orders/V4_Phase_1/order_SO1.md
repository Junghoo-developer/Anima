# 발주 #SO1 — Structured Output 전면 강화 / 구조화 실패 방어선

**작성일**: 2026-05-09  
**상태**: 결재 도장 박힘 (2026-05-10) / Codex 실행 완료, ARCH MAP #81 등록됨.  
**트랙**: V4 Phase 1 / SO 트랙 #SO1 (Structured Output 1차)  
**선행**: V4 §1-A LIVE + V4 §2 LIVE, CR1/CR1.1 현장 루프 보정 직후.  
**목표**: 현장 구조화 에러가 라우팅/워룸/결재 루프 전체를 오염시키지 않도록, LLM 출력 계약을 노드별로 강화하고 실패를 typed failure packet으로 흡수한다.

---

## Why

현장 로그에서 WarRoom structured output failure와 CR1 thought-recursion 오분기가 결합해, 도구가 필요한 턴이 `2b_thought_critic` / WarRoom no-tool lane으로 새는 현상이 확인됐다.

CR1.1은 해당 오분기 자체를 보정했지만, 더 큰 문제는 남아 있다.

1. LLM structured output 실패가 자유 텍스트로 새면 graph가 다음 상태를 안정적으로 판정할 수 없다.
2. 노드별 fallback이 제각각이라 실패가 `phase_119`, remand, 재시도 중 어디로 가야 하는지 일관성이 없다.
3. V4 §2 신규 금지(`fact_id 발명 X`, `ThinkingHandoff 9필드 누락 X`, `119 enum 무분류 X`)는 문서상 박혔지만 일부는 prompt 규칙에 기대고 있다.
4. WarRoom은 내부 자유 사고가 필요하지만 graph로 나가는 산출은 반드시 구조화되어야 한다.

따라서 SO1의 원칙은:

> **사고는 자유롭게 하되, graph 경계 밖으로 나가는 모든 LLM 산출은 typed schema + validator + retry + typed failure로만 통과한다.**

---

## 헌법 정합

### V4 §1-A와 정합

- `-1s`: `ThinkingHandoff.v1` 9필드 누락 금지 강화.
- `-1a`: 목표/계획 산출은 schema로 고정하되, 도구명/인자 작성 금지는 유지.
- `2b`: fact mode와 thought_critic mode 모두 output schema 및 evidence ref 검증.
- `0_supervisor`: 도구 결정 LLM은 tool call/ops decision만 작성, 답변 텍스트 금지.
- `WarRoom`: 내부 토론은 자유, 외부 산출은 `WarRoomOutput` 계열 schema만 통과.
- `-1b`: `DeliveryReview.v1` reason_type/evidence_refs/remand_target 정합 검증.
- `119`: 구조 실패가 반복되면 enum 있는 rescue reason으로 흡수.

### V4 §2와 정합

직접 관련 금지:

- §2 (c) remand_guidance 포맷 위반 X
- §2 (d) fact_id 발명 X
- §2 (e) 119 enum 무분류 X
- §2 (g) tool_request 0차 외 발생 X
- §2 (h) 0차 LLM 답변 작성 X
- §2 (j) ThinkingHandoff.v1 9필드 누락 X
- §2 (k) -1s 목표 수립 X
- §2 (l) -1a 라우팅 결정 X

SO1은 새 권한을 만들지 않는다. 기존 권한표의 산출 계약을 더 강하게 검증한다.

---

## 범위

### A. Structured-output 공통 유틸 신설

신규 후보:

- `Core/pipeline/structured_io.py`

역할:

1. LLM structured output 호출 공통 wrapper.
2. parse/validation 실패 시 1회 repair retry.
3. 재실패 시 노드별 typed failure packet 반환.
4. Pydantic model dump 표준화 (`by_alias=True` 기본).
5. validation error 요약을 내부 trace로만 보존.

초안 API:

```python
def invoke_structured_with_repair(
    *,
    llm,
    schema,
    messages,
    node_name: str,
    repair_prompt: str,
    max_repairs: int = 1,
) -> StructuredInvokeResult:
    ...
```

`StructuredInvokeResult`:

```python
{
    "ok": bool,
    "value": dict,
    "failure": {
        "schema": "StructuredFailure.v1",
        "node": "...",
        "reason_type": "parse_error | validation_error | model_refusal | max_tokens | unknown",
        "summary": "...",
    },
}
```

### B. 노드별 schema validator 추가

필수 validators:

1. `validate_thinking_handoff(packet)`
   - 9필드 non-empty 검사.
   - `next_node == recipient` 또는 허용된 compatibility mapping 검사.
   - `goal_state`가 raw user wording 그대로면 warning/failure 후보.

2. `validate_delivery_review(review, allowed_fact_ids)`
   - `reason_type`과 `remand_target` 정합.
   - `evidence_refs`가 `allowed_fact_ids` 밖이면 제거 또는 failure.

3. `validate_thought_critique(critique, allowed_fact_ids)`
   - top-level 및 item-level `evidence_refs` allowlist 검사.
   - 없는 `fact_id` 발명 차단.

4. `validate_supervisor_output(tool_calls, available_tool_names)`
   - 존재하지 않는 tool name 차단.
   - 0차 답변 텍스트 작성 차단.
   - tool args schema 검증은 기존 LangChain tool schema와 연동.

5. `validate_warroom_output(output)`
   - 자유 텍스트만 반환한 경우 graph state로 통과 금지.
   - typed failure packet으로 변환.

### C. WarRoom 구조화 실패 방어

현 증상:

- WarRoom structured output error가 자유 텍스트 자기소개/일반 답변으로 새어 나옴.

SO1 목표:

- WarRoom LLM이 schema를 깨면 `war_room.structured_failure`만 남긴다.
- WarRoom은 답변 텍스트를 만들지 않는다.
- `route_after_s_thinking` / WarRoom edge는 실패 시 `-1s_start_gate` 또는 `phase_119`로만 돌아간다.
- phase_3에 WarRoom 자유 텍스트가 직접 전달되지 않게 한다.

### D. Provider-native structured output 사용 가능성 점검

현 LangChain 문서 기준:

- Provider-native structured output이 가능하면 가장 신뢰도 높음.
- 불가능하면 ToolStrategy / tool-calling structured output + retry 사용.

SO1에서는 다음을 점검한다.

1. 현재 `llm.with_structured_output(PydanticModel)`이 provider-native인지 tool strategy인지 확인.
2. provider-native strict mode 사용 가능 모델이면 우선 적용.
3. strict mode 불가 모델은 repair retry + Pydantic validator로 보강.
4. parallel tool calls가 schema strict와 충돌하면 해당 노드에서 `parallel_tool_calls=False` 후보 검토.

### E. 실패 라우팅 표준화

구조화 실패는 노드별로 다르게 폭발하지 않고 아래 규칙을 따른다.

| 실패 위치 | 1회 repair 실패 후 | 반복 실패 |
|---|---|---|
| -1s | safe fallback ThinkingHandoff 또는 phase_119 | phase_119 |
| -1a | `_base_fallback_strategist_output` + validation | phase_119 또는 0_supervisor 차단 |
| 0차 | no tool_calls + structured_failure | -1a remand 또는 phase_119 |
| 2b fact mode | empty/incomplete analysis_report + failure reason | -1s가 119 판단 |
| 2b thought mode | empty ThoughtCritique + failure reason | -1s가 검증 후 phase_3/119 |
| WarRoom | `war_room.structured_failure` | phase_119 |
| -1b | deterministic hard safety review | 3회 초과 phase_119 |

### F. Golden trace 회귀 세트

SO1은 단위 테스트뿐 아니라 대표 trace를 회귀로 박는다.

필수 trace:

1. `2023년 11월 23일의 일기를 읽고 그날의 나는 어떤 하루를 보냈는지 말해줄 수 있어?`
   - 기대: `-1s -> -1a -> 0_supervisor -> phase_1(tool_read_full_diary 또는 적절한 diary/memory read)`.
   - 금지: `2b_thought_critic` 선진입, WarRoom 선진입.

2. WarRoom structured output failure stub
   - 기대: 자유 텍스트가 graph state 답변 후보로 유입되지 않음.

3. ThoughtCritique invented fact_id
   - 기대: 없는 fact_id 제거 또는 validation failure.

4. DeliveryReview invented fact_id
   - 기대: 없는 fact_id 제거 또는 validation failure/remand.

5. ThinkingHandoff missing field
   - 기대: repair 1회, 실패 시 safe fallback/119.

---

## 구현 순서

### SO1-A: Inventory / failure 좌표 수집

- `with_structured_output` 사용 지점 grep.
- `json.loads`, `model_validate`, custom parser 사용 지점 grep.
- WarRoom structured output 실패 경로 확인.
- 기존 fallback이 자유 텍스트를 state에 넣는지 확인.

산출:

- `Orders/V4_Phase_1/SO1_structured_output_inventory.md` 또는 ARCH MAP audit block 후보.

### SO1-B: 공통 structured_io 유틸

- `Core/pipeline/structured_io.py` 신설.
- 최소 wrapper + result schema + failure packet.
- 아직 모든 노드에 적용하지 않고 tests 먼저.

### SO1-C: fact_id allowlist validators

- `ThoughtCritique` / `DeliveryReview` evidence_refs 검증.
- V4 §2 (d) 코드 차단.

### SO1-D: WarRoom boundary guard

- WarRoom 자유 텍스트 parse failure를 typed failure로 봉인.
- graph state에 답변 텍스트로 유입 금지.

### SO1-E: -1s / -1a / 0차 적용

- ThinkingHandoff validator.
- Strategist output validation.
- Supervisor output guard.

### SO1-F: Golden trace + ARCH MAP

- 대표 trace test 추가.
- `python -B -m unittest discover -s tests` 또는 `python -m pytest -q`.
- `ANIMA_ARCHITECTURE_MAP.md` purge log 추가.

---

## 검증 기준

- 기존 test 전체 통과.
- 새 tests 최소 8~12개 추가.
- 구조화 실패 stub이 자유 텍스트 답변/WarRoom state로 새지 않음.
- 없는 `fact_id` 인용 차단.
- 일기 날짜 요청이 thought recursion / WarRoom으로 선진입하지 않음.
- 119 진입 시 reason enum이 비어 있지 않음.
- `__pycache__` 변경은 커밋/보고 대상에서 제외.

---

## 비범위

SO1에서 하지 않는다:

- V4 §1-C WarRoom v2 본문 작성.
- 노드명 일괄 rename.
- self-kernel 개혁.
- 심야정부 §1-B 작성.
- DB migration 실행.
- 모델 교체 자체.

단, provider-native structured output 가능성은 조사하고 권고까지 남긴다.

---

## 검토 질문

1. 구조화 실패를 1회 repair 후 바로 typed failure로 보낼지, 노드별 2회까지 허용할지?
2. 없는 `fact_id`는 조용히 제거할지, validation failure로 보고 remand할지?
3. WarRoom structured failure는 항상 119로 보낼지, 1회는 -1s로 돌려도 되는지?
4. Provider-native strict mode를 지원하지 않는 로컬/저가 모델에 대해 ToolStrategy 강제 도입을 허용할지?
5. Golden trace test를 unit test 수준으로 만들지, 실제 graph integration trace로 만들지?

---

## 임시 결론

SO1은 기능 추가가 아니라 **현장 루프 안전 인프라**다.

CR1이 "사고 재귀"를 열었다면, SO1은 그 재귀가 구조화 실패 때문에 흐물거리거나 자유 텍스트로 새지 않게 하는 잠금장치다.

승인 시 권장 실행 순서:

1. SO1-A inventory
2. SO1-C fact_id validator
3. SO1-D WarRoom boundary guard
4. SO1-B 공통 wrapper
5. SO1-E 전체 적용
6. SO1-F golden trace + ARCH MAP

**단숨 실행 후보**: A~D를 한 번에, E~F를 같은 pass 후반에 실행. 단, WarRoom과 graph routing 파일 충돌 가능성 때문에 CR1.1 변경점과 diff를 먼저 확인해야 한다.
