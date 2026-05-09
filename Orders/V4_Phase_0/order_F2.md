# 발주 #F2 — -1s 보강 + -1b 사실 대조 채널 (ThinkingHandoff.v1 + fact_cells compact + remand_guidance schema)

**발주일**: 2026-05-07
**트랙**: V4 Phase 0 / **F 트랙 #F2** (현장 정상화 2차, "다음 큰 수술 1단계")
**선행**: F1 완료 (commit `ab88e62`, 자동 advisory 다리 V3→V4 교체). V4 baseline `782a982`.
**의존성**: 없음. F3 (-1a 입력 축소) / F4 (0차 LLM 격상)와 분리.

---

## Why

V4 §1 권한표 결재 (2026-05-06, 메모리 [project_v4_section1_field_loop_decisions.md](memory)) 핵심 4 결재가 본 발주의 근거:

1. **결재 6 — -1s 보강**: SThinkingPacket.v1 → ThinkingHandoff.v1 schema 보강. analysis_report compact view를 -1s LLM 입력에 정식 박음.
2. **결재 4-1 — -1b = 대조관**: -1b는 도구 호출 X, 그 턴 내 산출물 (2a/2b/phase_3) 대조만. 사실 검증 ≠ 도구 조회. 환각/누락 발견 시 신고 채널 필요.
3. **결재 4-2 — F2 schema 3종**: ThinkingHandoff.v1 + 2b→-1b fact_cells compact view + remand_guidance schema (5필드).
4. **결재 4-3 — phase_3 cited_fact_ids 미룸**: Phase 1 이후. 본 발주 범위 외.

현 상태 (2026-05-07 verify):

- `Core/pipeline/start_gate.py:52` `_build_s_thinking_packet` = SThinkingPacket.v1, 4블록 (situation/loop/next_direction/routing). 9필드 ThinkingHandoff.v1 형식 아님.
- `Core/nodes.py:2616` `_llm_start_gate_turn_contract` 인자에 `analysis_report` 없음 → -1s LLM이 2b 결과 직접 read 불가 (현재는 boolean check만).
- `Core/pipeline/delivery_review.py:223` `build_delivery_review_context` = -1b 입력 8필드 (user_input/final_answer/speaker_review/readiness_decision/analysis_report/response_strategy/rescue_handoff_packet/phase3_delivery_summary). **`fact_cells` 없음**.
- `Core/pipeline/contracts.py:589` `DeliveryReview` = verdict/reason/issues_found/remand_target/remand_guidance (모두 free-form). **reason_type enum X, evidence_refs X**.
- `Core/pipeline/packets.py:788` `_compact_fact_cells_for_prompt` = `claim or fact or text` 추출. **`extracted_fact` (실제 fact_cells 필드) 빠짐 → 압축 시 fact 본문이 빈 문자열로 떨어지는 결함**.

V4 §1 §2 작성 직전에 위 결함을 일괄 보강. -1s가 사고 재판정 권한을 정식 갖고, -1b가 fact_id 인용으로 환각/누락 신고 채널을 박는다.

---

## 스코프

본 발주는 **3개 schema 변경 + 1개 압축 helper 패치 + 프롬프트 빌더 인자 갱신 + 테스트 신설**. F3/F4는 별도 발주.

### A. ThinkingHandoff.v1 (-1s 보강)

A-1. **SThinkingPacket.v1 → ThinkingHandoff.v1 schema 교체** ([Core/pipeline/start_gate.py:52-124](Core/pipeline/start_gate.py#L52-L124) `_build_s_thinking_packet`):
- 새 schema 9필드:
  - `producer` (str, 고정값 `"-1s"`)
  - `recipient` (str, 라우팅 결과 — `"-1a"` / `"phase_3"` / `"phase_119"`)
  - `goal_state` (str, 정규화된 목표. `start_gate_contract.normalized_goal` 매핑)
  - `evidence_state` (str, 현재 증거 상태. `current_turn_facts` 개수 + `requires_grounding` + `analysis_report` 압축 요약)
  - `what_we_know` (List[str], 손에 들어온 사실. `current_turn_facts` + `analysis_report.evidences[].extracted_fact` + `analysis_report.source_judgments[].accepted_facts` + `analysis_report.usable_field_memo_facts`)
  - `what_is_missing` (List[str], 빈 슬롯. 옛 `gaps`)
  - `next_node` (str, 라우팅 결과. `recipient`와 동일하나 명시 보존)
  - `next_node_reason` (str, 라우팅 이유. 옛 `routing_decision.reason`)
  - `constraints_for_next_node` (List[str], 옛 `next_direction.avoid` + 새 제약 — "do not bypass 2b fact judgment", "do not write tool args in -1s" 등)
- `schema` 필드 = `"ThinkingHandoff.v1"` (옛 `"SThinkingPacket.v1"` 교체).
- **state 키 (`s_thinking_packet`, `s_thinking_history`)는 변경 X** (rename 욕구 금지 — V4 §1 헌법 일괄 작업).
- `Core/pipeline/contracts.py`에 `ThinkingHandoff` Pydantic schema 신설. 기존 `SThinkingPacket` / `SThinkingSituation` / `SThinkingLoopSummary` / `SThinkingNextDirection` / `SThinkingRoutingDecision`는 **one-season legacy compatibility**로 유지하되 live builder는 `ThinkingHandoff.v1`만 emit.

A-2. **`compact_s_thinking_packet_for_prompt` 갱신** ([Core/pipeline/packets.py:146](Core/pipeline/packets.py#L146)):
- 입력 schema가 ThinkingHandoff.v1로 바뀌었으니 9필드 압축 형식으로 갱신.
- `_clip_text` / `_clip_string_list` 기존 helper 그대로 재사용.
- 옛 SThinkingPacket.v1 구조도 fallback (방어적): `situation_thinking` / `loop_summary` / `next_direction` / `routing_decision` 박혀있으면 9필드로 매핑해서 반환. 신/구 patcket 둘 다 처리해서 마이그레이션 시 깨짐 방지.

A-3. **-1s LLM 입력에 analysis_report compact view 정식 부여**:
- `_llm_start_gate_turn_contract` ([Core/nodes.py:2616](Core/nodes.py#L2616)) 시그니처에 `analysis_report: dict | None = None` 인자 추가 (optional, 후방 호환).
- `analysis_report`가 비어있지 않으면 `compact_analysis_for_prompt(analysis_report, role="-1s")` (이미 [Core/pipeline/packets.py:254](Core/pipeline/packets.py#L254)에 정의됨, status_packet만 반환) 으로 압축해서 프롬프트에 `[analysis_report_compact]` 블록으로 박음.
- `Core/pipeline/start_gate.py:200-206` 호출처에 `state.get("analysis_report", {})` 전달 추가.
- **빈 analysis_report 시 패킷 박지 X** ("No analysis_report" 헤더 출력하지 말고, 블록 자체 생략) → 토큰 다이어트.

A-4. **graph 라우터 호환 보강** ([Core/graph.py](Core/graph.py) `route_after_s_thinking`):
- `packet["next_node"]` (ThinkingHandoff.v1 top-level)을 우선 읽음.
- 없으면 옛 `packet["routing_decision"]["next_node"]` fallback 유지.
- `"phase_119"` / `"119"` 둘 다 119로 처리.
- 이 보강 없으면 새 handoff를 만들어도 graph가 옛 4블록만 읽어 라우팅 fallback으로 샐 수 있음.

A-5. **s_thinking_history 누적 함수 보강** ([Core/runtime/context_packet.py](Core/runtime/context_packet.py)):
- `compact_s_thinking_cycle()`은 ThinkingHandoff.v1 top-level 필드를 우선 압축.
  - `domain`: `goal_state` 또는 `evidence_state`에서 안전하게 축약 (없으면 old fallback)
  - `next_node`: top-level `next_node`
  - `main_gap`: `what_is_missing[0]`
  - `brief_thought`: `next_node_reason` 또는 `goal_state`
- 옛 SThinkingPacket.v1 4블록은 fallback으로 유지.
- `s_thinking_history` 키/schema는 그대로 유지.

### B. 2b → -1b fact_cells compact view

B-1. **`_compact_fact_cells_for_prompt` 패치** ([Core/pipeline/packets.py:788](Core/pipeline/packets.py#L788)):
- **정후 결재: fact_cells projection 전체를 V4식 공식 projection으로 정리한다.**
- 별도 `_compact_fact_cells_for_review()` 신설 금지. 기존 공유 helper `_compact_fact_cells_for_prompt`를 고쳐 -1a/-1b/phase_3 등 모든 role-aware reasoning-board projection이 같은 V4 fact shape을 보게 한다.
- 이 변경은 -1b 전용 임시 뷰가 아니라 `FactCell` 본체 schema에 맞춘 전역 projection 정리다.
- 현재 `claim or fact or text` 만 봄 → `extracted_fact` 추가 (실제 [Core/nodes.py:2362](Core/nodes.py#L2362) `add_fact` 가 박는 필드).
- 새 추출 순서: `extracted_fact or claim or fact or text` (앞에 있을수록 우선).
- 동시에 `excerpt` 필드도 압축본에 노출 (160 char 제한): -1b가 환각 판정 시 인용 컨텍스트로 사용.
- 출력 schema (필드 순서 박힘):
  ```
  {
    "fact_id": str,
    "extracted_fact": str (260 char 제한),
    "source_id": str (140 char 제한),
    "source_type": str (80 char 제한),
    "excerpt": str (160 char 제한)
  }
  ```
- **기존 `claim`/`status` 필드는 제거**: 옛 reasoning board 형식 잔존, V3 god-file 흔적. fact_cells 본체 schema는 [Core/pipeline/contracts.py:303-312](Core/pipeline/contracts.py#L303-L312) `FactCell` (fact_id/source_id/source_type/excerpt/extracted_fact/fact_kind/confidence) 단일 출처.

B-2. **-1b 입력에 fact_cells compact view 추가** ([Core/pipeline/delivery_review.py:223](Core/pipeline/delivery_review.py#L223) `build_delivery_review_context`):
- 새 필드 `fact_cells_for_review` (DeliveryReviewContext.v1):
  - 출처: `state.get("reasoning_board", {}).get("fact_cells", [])`
  - 압축: `_compact_fact_cells_for_prompt(values, limit=10)` (B-1 패치본).
- **reasoning_board 통째 X** (보류 7 -1b 입력 비대 우려). fact_cells 압축본만 (≈10개 × 4-5필드).
- `_analysis_review_projection` ([delivery_review.py:95](Core/pipeline/delivery_review.py#L95))은 그대로 (이미 `evidences` 압축 박혀있음). 단, fact_id 인용 채널은 위 새 필드 단일 출처.

B-3. **`build_delivery_review_sys_prompt` 갱신** ([Core/prompt_builders.py:206](Core/prompt_builders.py#L206)):
- 기존 rule 1~5 유지. 다음 항목 추가:
  - `[fact_cells_for_review]` 블록을 context_prompt에서 직접 인용 가능 명시.
  - "When verdict=remand and reason_type ∈ {hallucination, omission, contradiction}, populate `evidence_refs` with the `fact_id`s that were violated. Do not invent fact_ids — only cite ones that appear in [fact_cells_for_review]."
  - "If the answer claim has no matching fact_id in [fact_cells_for_review], that itself is `hallucination` evidence."

### C. remand_guidance schema (DeliveryReview 확장)

C-1. **`DeliveryReview` schema 확장** ([Core/pipeline/contracts.py:589](Core/pipeline/contracts.py#L589)):
- `Core/pipeline/contracts.py`에 `DELIVERY_REVIEW_REASON_TYPES` 또는 동등 상수를 둔다. `DeliveryReview`, `normalize_delivery_review`, prompt builder, 차후 F4/119 enum 분류가 이 단일 출처를 재사용한다.
- 새 필드 3개:
  - `reason_type: Literal["", "hallucination", "omission", "contradiction", "thought_gap", "tool_misuse"]` (default `""`).
  - `evidence_refs: List[str]` (default `[]`. fact_cells_for_review의 fact_id만 박음).
  - `delta: str` (default `""`. 사람 읽기용 1~2문장. ≤ 280 char).
- 기존 필드 (verdict/reason/issues_found/remand_target/remand_guidance) **모두 유지**: 후방 호환.
- `delivery_style` enum 없음 (결재 4-2: 어조는 phase_3 자체 책임, -1b 권한 범위 외).

C-2. **`normalize_delivery_review` 갱신** ([Core/pipeline/delivery_review.py:157](Core/pipeline/delivery_review.py#L157)):
- 새 정규화 규칙:
  - `reason_type` enum 5종 외 값은 `""` 강제.
  - `evidence_refs` 비-str 항목 제거, 중복 dedupe, 최대 8개.
  - `delta` `_compact_text(value, 280)`.
  - **자동 라우팅 매핑** (LLM의 remand_target을 코드가 덮어쓸 때):
    - `reason_type ∈ {hallucination, omission, contradiction, thought_gap}` → `remand_target = "-1s"` (정후 결재: -1s = 사실 재판정 + 사고 흐름).
    - `reason_type == "tool_misuse"` → `remand_target = "-1a"` (결재 7: -1a = 실행계획 책임).
    - `reason_type == ""` 또는 빈 enum → 기존 LLM/guard target 인정 (후방 호환).
  - 후방 호환: 옛 `remand_guidance` (free-form) 비어있으면 `delta`로 채움 (마이그레이션 보조).

C-3. **`_merge_review_with_speaker_guard` 보강** ([Core/pipeline/delivery_review.py:276](Core/pipeline/delivery_review.py#L276)):
- LLM review의 `reason_type` / `evidence_refs` / `delta`가 비어있고 guard가 remand 박을 때, guard의 `issues_found`에서 `reason_type` 추론:
  - 메시지에 `"hallucination"` 또는 `"unsupported"` 포함 → `hallucination`
  - `"missing"` 또는 `"omit"` 포함 → `omission`
  - 그 외 → `""` (빈 enum 그대로, 옛 동작 유지)
- 너무 무리한 추론은 X — 단순 prefix 매칭만, 못 잡으면 빈 enum.

C-4. **`build_delivery_review_sys_prompt` 갱신** (B-3와 같이):
- 새 출력 필드 명시:
  - "Output DeliveryReview.v1 JSON with fields: verdict, reason, reason_type, evidence_refs, delta, issues_found, remand_target, remand_guidance."
  - "reason_type values: hallucination | omission | contradiction | thought_gap | tool_misuse | empty string."
  - "remand_target may be left empty — code derives it from reason_type."

### D. 검증 (테스트)

D-1. **신설 단위 테스트** `tests/test_thinking_handoff_v1.py` (case 4):
1. `_build_s_thinking_packet` 출력이 9필드 모두 박혀있고 `schema == "ThinkingHandoff.v1"`.
2. 9필드 중 빈 string/리스트 처리 (필드 누락 없음, 단지 빈 값).
3. `compact_s_thinking_packet_for_prompt` 신 schema 압축 결과가 9필드 보존.
4. `compact_s_thinking_packet_for_prompt` **옛 SThinkingPacket.v1 입력**도 fallback으로 9필드 매핑 반환 (마이그레이션 안전).

D-2. **신설 단위 테스트** `tests/test_minus_1s_analysis_input.py` (case 3):
1. 빈 `analysis_report`로 `_llm_start_gate_turn_contract` 호출 시 프롬프트에 `[analysis_report_compact]` 블록 미생성.
2. 비어있지 않은 `analysis_report` 전달 시 프롬프트에 `compact_analysis_for_prompt(role="-1s")` 결과 박힘 (status_packet 형식 검증).
3. 후방 호환: `analysis_report` 인자 없이 호출해도 정상 동작 (기존 호출처 영향 X).

D-3. **신설 단위 테스트** `tests/test_delivery_review_fact_cells.py` (case 4):
1. `build_delivery_review_context`가 `state.reasoning_board.fact_cells`를 받아 `fact_cells_for_review` 필드에 압축본 박음 (≤10개).
2. `_compact_fact_cells_for_prompt`가 `extracted_fact` 필드를 정확히 추출 (claim 없는 경우).
3. 옛 `claim` 필드만 있는 입력도 fallback으로 추출 (후방 호환).
4. 빈 reasoning_board 입력 시 `fact_cells_for_review = []`.

D-4. **신설 단위 테스트** `tests/test_delivery_review_reason_type.py` (case 6):
1. `DeliveryReview` schema가 `reason_type`/`evidence_refs`/`delta` 필드 박힘 (default 값 검증).
2. `normalize_delivery_review`가 잘못된 `reason_type` 값을 빈 string으로 정규화.
3. `reason_type="hallucination"` + LLM이 `remand_target=""` → 코드가 `"-1s"`로 덮어씀.
4. `reason_type="tool_misuse"` → 코드가 `"-1a"`로 덮어씀.
5. `reason_type=""` (옛 호환) → LLM/guard `remand_target` 그대로 인정.
6. `evidence_refs` dedupe + 비-str 제거 + 최대 8개 trim.

D-5. **신설 통합 테스트** `tests/test_delivery_review_hallucination_flow.py` (case 2):
1. 답변 텍스트가 reasoning_board.fact_cells에 없는 사실 박음 → -1b LLM mock이 `verdict=remand` + `reason_type=hallucination` + `evidence_refs=[]` (실제 LLM은 mock으로 정해진 출력 반환) 반환 → `remand_target=-1s` + `loop_count` 증가 검증.
2. 답변이 모든 fact_cells 인용 + 누락 없음 → mock LLM이 `verdict=approve` 반환 → `remand_target=""` + `delivery_review_rejections=0`.

D-6. **기존 테스트 회귀**:
- `tests/test_delivery_review_contract.py` (현존)는 옛 schema 기준이므로 새 필드 default 추가에 따라 깨지지 않는지 확인. 옛 case가 fail하면 default 값 추가만으로 해결되는지 verify.
- `tests/test_state_contract.py` `s_thinking_packet` 형식 검증 case 있으면 ThinkingHandoff.v1 9필드로 갱신.

D-7. **자동 검사**: `python -B -m unittest discover -s tests` → 기존 234 + 신규 19 case = **253 OK** (또는 정확한 신규 case 수에 맞춤).

---

## 안 하는 것 (다음 발주)

- **F3 (-1a 입력 축소)**: `analysis_report` / `raw_read_report` / `reasoning_board`를 -1a 직접 입력에서 제거. 본 발주 범위 X. 단, F2가 -1s를 강화함으로써 F3 발주 시 -1a는 ThinkingHandoff만 받으면 되도록 길 닦기 완료.
- **F4 (0차 LLM 격상)**: tool_request 생성 권한 -1a → 0_supervisor 이동. F2/F3 후 발주.
- **phase_3 cited_fact_ids**: 결재 4-3 미룸. delivery_packet schema 확장 = Phase 1 모듈식 답변 안건 (보류 10).
- **working_memory → -1s 입력** (보류 1): `Core/nodes.py:2623 del working_memory` 라인 제거 안건. 정후 비전 = "낮+과거 통합". 하지만 phase_3와 중복 우려 미해소 → 본 발주 범위 X. 별도 X2 발주 또는 F3와 묶음.
- **노드명 rename** (`phase_delivery_review` → `phase_minus_1b_delivery_review`): V4 §1 헌법 작성 시 일괄 (결재 5).
- **119 enum 분류** (보류 9): Phase 1 V4 §2 신규 금지. reason_type enum이 119에서도 재사용되도록 본 발주에서 단일 출처 박았으니, Phase 1 작업 시 enum 그대로 import하면 됨.
- **delivery_packet schema version**: 보류 10 — Phase 1.
- **2b 직접 LLM 출력 (`EvidenceItem`)에 fact_id 부여**: 후처리 deterministic 부여가 더 안전하다는 verify 결론 (메모리 결재 4-2 verify 절). 변경 X.

---

## 변경 대상 (코드 좌표)

### 변경
- `Core/pipeline/start_gate.py` ([:52-124](Core/pipeline/start_gate.py#L52-L124) `_build_s_thinking_packet` 9필드 schema 교체 + [:200-206](Core/pipeline/start_gate.py#L200-L206) 호출처 `analysis_report` 전달)
- `Core/nodes.py` ([:2616](Core/nodes.py#L2616) `_llm_start_gate_turn_contract` 시그니처 + 프롬프트 빌더 인자 추가)
- `Core/pipeline/packets.py` ([:146](Core/pipeline/packets.py#L146) `compact_s_thinking_packet_for_prompt` 9필드 압축 + fallback / [:788](Core/pipeline/packets.py#L788) `_compact_fact_cells_for_prompt` 추출 순서 패치)
- `Core/pipeline/delivery_review.py` ([:157](Core/pipeline/delivery_review.py#L157) `normalize_delivery_review` 새 필드 + 자동 라우팅 / [:223](Core/pipeline/delivery_review.py#L223) `build_delivery_review_context` `fact_cells_for_review` 추가 / [:276](Core/pipeline/delivery_review.py#L276) `_merge_review_with_speaker_guard` reason_type 추론)
- `Core/pipeline/contracts.py` (`ThinkingHandoff` schema 신설 + [:589](Core/pipeline/contracts.py#L589) `DeliveryReview` schema 3필드 추가 + reason_type 상수 단일 출처)
- `Core/prompt_builders.py` ([:206](Core/prompt_builders.py#L206) `build_delivery_review_sys_prompt` 출력 필드/규칙 갱신 + -1s 프롬프트 빌더에 analysis_report compact 블록 추가 — `_llm_start_gate_turn_contract` 호출 경로 따라 `Core/nodes.py` 안 sys_prompt 빌더에서 처리될 수도 있음. 실제 호출 흐름 verify 후 적정 위치에 박음.)
- `Core/graph.py` (`route_after_s_thinking` top-level `next_node` 우선 + old routing_decision fallback)
- `Core/runtime/context_packet.py` (`compact_s_thinking_cycle` ThinkingHandoff.v1 우선 + old SThinkingPacket.v1 fallback)

### 신설
- `tests/test_thinking_handoff_v1.py` (case 4)
- `tests/test_minus_1s_analysis_input.py` (case 3)
- `tests/test_delivery_review_fact_cells.py` (case 4)
- `tests/test_delivery_review_reason_type.py` (case 6)
- `tests/test_delivery_review_hallucination_flow.py` (case 2)

### 변경 없음 (확인만)
- `Core/state.py` — `s_thinking_packet` / `delivery_review` / `delivery_review_context` 필드명 그대로 (rename 금지).
- `Core/state.py` — `s_thinking_packet` / `delivery_review` / `delivery_review_context` 필드명 그대로 (rename 금지).
- `Core/nodes.py:2623` `del working_memory` — 본 발주 범위 X (위 "안 하는 것" 참조).
- `Core/pipeline/strategy.py` (-1a strategist) — F3 발주 책임.

---

## 헌법 정합

- **V4 §0 v0 위반 X**: 본 발주는 §1 권한표 본문 박기의 인프라 정비 (-1s 사고 권한 + -1b 사실 대조 채널).
- **V3 §2 절대 금지 24개 위반 X**: 도구 호출 권한 변경 X, fallback 추가 X, LLM 사고 규칙 변경 X. -1b는 여전히 도구 X (정규식 차단 그대로). -1s는 사고만 (도구 X).
- **AGENTS.md §3.3 대형 nodes.py 수술 게이트 트리거**: `_llm_start_gate_turn_contract` 시그니처 변경은 nodes.py 한 함수 패치, 인벤토리 분류/일괄 이동이 아니므로 게이트 트리거 X. 단, 작업 시작 전 정후 결재 받음.
- **AGENTS.md §1 인코딩**: 신설 테스트 파일 모두 UTF-8 (BOM 없음). PowerShell 사용 시 `-Encoding utf8` 명시.
- **메모리 결재 4-1/4-2/4-3** 그대로 반영. 자의 해석 X.

---

## 검증 기준

1. **자동 검사**: `python -B -m unittest discover -s tests` → F1 이후 baseline은 **242 OK**. 신규 19 case 추가 시 예상은 **261 OK**. 단, 기존 테스트 갱신/병합에 따라 실제 수를 최종 보고 기준으로 삼는다.
2. **수동 검사 (Codex 직접 verify)**:
   - `python -c "from Core.pipeline.contracts import DeliveryReview; r = DeliveryReview(); print(r.model_dump(by_alias=True))"` → `reason_type`/`evidence_refs`/`delta` 필드 default 값 출력 확인.
   - `python -c "from Core.pipeline.start_gate import _build_s_thinking_packet; ..."` → 9필드 박힌 dict 출력 (실제 인자 mock으로).
   - 옛 SThinkingPacket.v1 입력으로 `compact_s_thinking_packet_for_prompt` 호출 → 9필드 매핑 결과 반환 (fallback 동작 verify).
3. **purge log 추가**: `ANIMA_ARCHITECTURE_MAP.md` #71 추가.
   - 마커: "**V4 Phase 0 F트랙 #F2: -1s ThinkingHandoff.v1 + -1b fact_cells 대조 채널 + remand_guidance schema**"
   - 변경 줄 수, 신설 테스트 5개, schema 3종 갱신, 후방 호환 명시.
4. **grep 확인**:
   - `Core/pipeline/start_gate.py` 안 `"SThinkingPacket.v1"` 신 schema 박힌 후 0건 (옛 schema 잔존 X). 단, `compact_s_thinking_packet_for_prompt` fallback 분기 안에는 옛 키 (`situation_thinking` 등) 검사 코드 그대로 OK.
   - `Core/pipeline/contracts.py` `DeliveryReview` 안 `reason_type` / `evidence_refs` / `delta` grep 1+건.

---

## 롤백

- schema 추가 = 후방 호환 (기존 필드 유지). 문제 발견 시 신 필드 default 빈 값으로 옛 코드와 동일 동작 보장.
- `git checkout 782a982 -- Core/pipeline/start_gate.py Core/pipeline/contracts.py Core/pipeline/delivery_review.py Core/pipeline/packets.py Core/prompt_builders.py Core/nodes.py` 단일 commit 복원 가능.
- 신설 테스트 파일은 그냥 삭제 가능.

---

## 코덱스가 발주 받기 전 읽어야 할 문서 (AGENTS.md §3.1 + 본 발주 한정 추가)

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (V3 §1·§2 LIVE LAW)
4. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (V4 §0 v0)
5. `ANIMA_ARCHITECTURE_MAP.md` (R 시리즈 purge log #61~#69 + F1 #70)
6. (이번 발주 한정) `Orders/V4_Phase_0/order_F2.md` (본 발주 본문)
7. (이번 발주 한정) `Core/pipeline/start_gate.py` 전체
8. (이번 발주 한정) `Core/pipeline/delivery_review.py` 전체
9. (이번 발주 한정) `Core/pipeline/contracts.py` (`EvidenceItem`/`FactCell`/`DeliveryReview` 정의)
10. (이번 발주 한정) `Core/pipeline/packets.py` (`compact_*_for_prompt` 패턴)
11. (이번 발주 한정) `Core/prompt_builders.py:206` `build_delivery_review_sys_prompt`
12. (이번 발주 한정) `Core/nodes.py:2356-2390` `add_fact` (fact_cells 부여 메커니즘)
13. (이번 발주 한정) `tests/test_delivery_review_contract.py` (회귀 영향 확인)
14. (이번 발주 한정) `tests/test_midnight_r7_integration.py` (mock state 패턴 참고)

---

## V4 §1 결재 사항 (Codex 참고 — 본 발주 근거)

2026-05-06 ~ 2026-05-07 정후 결재 (메모리 [project_v4_section1_field_loop_decisions.md](memory)에 박힘):

- **결재 6**: -1s 보강 = ThinkingHandoff.v1 schema + analysis_report compact view 정식 입력 권한 → 본 발주 §A.
- **결재 4-1**: -1b = 대조관 (도구 X but 사실 비교는 권한). 새로 조회 X but 환각/누락 신고 가능 → 본 발주 §B.
- **결재 4-2**: F2 schema 안건 3종 (ThinkingHandoff.v1 + fact_cells compact + remand_guidance) → 본 발주 §A/§B/§C.
- **결재 4-3**: phase_3 `cited_fact_ids` = Phase 1 이후로 미룸 → 본 발주 범위 X.
- **결재 7 (보존)**: -1a 입력 축소 = F3 발주 책임. 본 발주는 -1s 강화로 F3 진입 길 닦기.

---

## 의문 시 행동 (AGENTS.md §2)

- ThinkingHandoff.v1 9필드 외 신규 필드 추가 욕구 → **금지** (정후 결재 9필드 그대로).
- 옛 SThinkingPacket.v1 schema 잔존 코드 즉시 모두 제거 욕구 → **금지** (compact 함수 fallback 분기는 1주 운영 후 별도 발주로 제거).
- `state.s_thinking_packet` 키 rename 욕구 → **금지** (V4 §1 헌법 작성 시 일괄).
- DeliveryReview에 `delivery_style` reason_type 추가 욕구 → **금지** (결재 4-2: 어조는 phase_3 책임).
- -1b 입력에 reasoning_board **통째** 추가 욕구 → **금지** (보류 7 입력 비대 우려, fact_cells 압축본만).
- -1b LLM이 `remand_target` 직접 박은 결과 보존 욕구 → **금지** (코드가 reason_type 기반 자동 매핑이 단일 출처. LLM이 박았어도 reason_type이 enum이면 코드가 덮어씀. reason_type 빈 enum일 때만 LLM/guard target 인정).
- analysis_report compact view를 -1s 외 다른 노드에도 박는 욕구 → **금지** (본 발주는 -1s만).
- `working_memory` `del` 라인 ([Core/nodes.py:2623](Core/nodes.py#L2623)) 제거 욕구 → **금지** (별도 X2 발주).
- 자동 라우팅 매핑에 `severity` 분기 추가 욕구 → **금지** (sos_119 escalation은 보류 9 Phase 1 작업).
- V3 §2 위반 의심 패턴 발견 시 → 즉시 멈추고 보고.

---

## 작업 후 보고 형식 (정후/Claude 검수용)

```
# 발주 #F2 작업 완료 보고

## 변경 파일
- Core/pipeline/start_gate.py: [전] N줄 → [후] N±M줄
  - _build_s_thinking_packet: SThinkingPacket.v1 → ThinkingHandoff.v1 9필드 schema
  - run_phase_minus_1s_start_gate: analysis_report 인자 전파
- Core/nodes.py: [전] N줄 → [후] N±M줄
  - _llm_start_gate_turn_contract: analysis_report 인자 추가 + 프롬프트 블록
- Core/pipeline/packets.py: [전] N줄 → [후] N±M줄
  - compact_s_thinking_packet_for_prompt: 9필드 압축 + 옛 schema fallback
  - _compact_fact_cells_for_prompt: extracted_fact 추출 순서 + excerpt 노출
- Core/pipeline/delivery_review.py: [전] N줄 → [후] N±M줄
  - build_delivery_review_context: fact_cells_for_review 필드 추가
  - normalize_delivery_review: reason_type/evidence_refs/delta + 자동 라우팅
  - _merge_review_with_speaker_guard: reason_type 추론 보강
- Core/pipeline/contracts.py: [전] N줄 → [후] N±M줄
  - DeliveryReview: reason_type/evidence_refs/delta 3필드 추가
- Core/prompt_builders.py: [전] N줄 → [후] N±M줄
  - build_delivery_review_sys_prompt: 새 출력 필드 + 규칙 + fact_cells 인용 명시

## 신설 테스트 (case N)
- tests/test_thinking_handoff_v1.py: 4 case
- tests/test_minus_1s_analysis_input.py: 3 case
- tests/test_delivery_review_fact_cells.py: 4 case
- tests/test_delivery_review_reason_type.py: 6 case
- tests/test_delivery_review_hallucination_flow.py: 2 case

## 테스트
- N tests OK / [실패 시 상세]

## 수동 검사
- DeliveryReview default 출력: [첨부]
- ThinkingHandoff.v1 9필드 출력: [첨부]
- 옛 SThinkingPacket.v1 fallback 결과: [첨부]

## grep 확인
- start_gate.py SThinkingPacket.v1 본 함수 안 grep: 0건
- contracts.py DeliveryReview reason_type/evidence_refs/delta grep: 3+건

## ARCH MAP purge log #71: 추가 완료

## 의문 / 발견 / V4 §1 작성 시 다룰 사항
- [있으면 작성, 없으면 "없음"]
- 특히 옛 SThinkingPacket.v1 fallback 분기 제거 시점 (1주 운영 후) 후보로 보고
```

---

**발주 OK 여부 정후 결재 후 코덱스 작업 시작.**
