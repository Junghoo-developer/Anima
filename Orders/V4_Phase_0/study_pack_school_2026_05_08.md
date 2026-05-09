# 학교 자료 — 2026-05-08

> F1/F2/F3/F4 박힌 직후 V4 §1 본문 글 박기 + §2 후보 자유발화용 1~2장 요약.
> 코드 X, 문서/비전 모드.

---

## 앞면 ① — V4 §1 권한표 5조항 (글로 풀어낼 본체)

### -1s (사고 결재자)
- **입력**: user_input + recent_context + s_thinking_history + analysis_report compact (F2) + tactical_briefing (F3) + working_memory (보류 1)
- **출력**: ThinkingHandoff.v1 9필드 (producer / recipient / goal_state / evidence_state / what_we_know / what_is_missing / next_node / next_node_reason / constraints_for_next_node)
- **권한**: 사고 / 상황 재판정 / 분기 의지 / 사실 권한 (사고 흐름까지)
- **금지**: 도구 호출 X / 검색어 생성 X / 답변 작성 X / final answer text 박기 X / advisory를 goal로 복사 X

### 2b (사실 검증관)
- **입력**: raw_read_report + s_thinking_packet
- **출력**: analysis_report (evidences/source_judgments/usable_field_memo_facts) + reasoning_board.fact_cells 채움 (코드 후처리가 fact_id 자동 부여 — `fact_1`, `fact_2`...)
- **권한**: 사실 검증 / fact 추출 / source 판정
- **금지**: 사고 재판정 X (그건 -1s) / 도구 호출 X / 답변 작성 X

### -1a (전략가, 실행계획)
- **입력 (F3)**: ThinkingHandoff + fact_cells_for_strategist (5필드 카드 압축본) + working_memory + war_room + start_gate_* + tool_carryover + evidence_ledger
- **출력**: strategist_output (action_plan + tool_request + response_strategy + goal_lock + ...)
- **권한**: 실행계획 작성 / fact_id 인용해서 도구계약 박기 / 방향 제시
- **금지**: analysis_report/raw_read_report/reasoning_board 직접 read X (F3 박힘) / 사실 재판정 X / 답변 작성 X / 최종 라우팅 X
- **F4 후 변경 예정**: tool_request 생성 권한 → 0_supervisor로 이동

### -1b (대조관, post-phase3 reviewer)
- **입력 (F2)**: user_input + final_answer + speaker_review + readiness_decision + analysis_report compact + response_strategy + rescue_handoff + phase3_delivery_summary + **fact_cells_for_review (5필드 카드)**
- **출력**: DeliveryReview.v1 (verdict + reason / **reason_type** / **evidence_refs** / **delta** + remand_target + remand_guidance + issues_found)
- **권한**: approve / remand / sos_119 / 그 턴 산출물 대조 비교 (도구 X)
- **금지**: 도구 호출 X / 검색어 생성 X / 답변 작성 X / answer_mode 변경 X / 새로 사실 조회 X
- **자동 라우팅**: hallucination/omission/contradiction/thought_gap → -1s, tool_misuse → -1a (코드 단일 출처)

### phase_3 (스피커)
- **입력**: SpeakerJudgeContract (response_strategy + rescue_handoff + readiness 등)
- **출력**: 사용자 답변 텍스트
- **권한**: 자연어 작성 / 어조 결정 / 톤 책임
- **금지**: 사실 새로 박기 X / 워크플로우 단어 누설 X / 슬롯 키 인용 X

### 0_supervisor (F4 후 격상 예정)
- **입력**: -1a operation_contract + tool_carryover (예정)
- **출력**: tool_request (도구 호출/검색어 생성)
- **권한**: 도구 선택 / 검색어 생성 / 도구 호출
- **금지**: 답변 작성 X / answer_mode 변경 X / 사고 재판정 X
- **상태**: F4 발주 완료 후 박힘. 학교 들고 갈 시점에 빈 자리 또는 채워짐.

---

## 앞면 ② — 7 fallback 권한표 (V4 §1 본문 박을 때 같이)

| fallback | 위치 | 보호 대상 | V4 §1 조항 |
|---|---|---|---|
| `_fallback_start_gate_turn_contract` | start_gate.py | -1s structured output 안전망 | -1s 권한표 보충 |
| `_base_fallback_strategist_output` | nodes.py | -1a structured output 안전망 | -1a 권한표 보충 |
| raw-reader fallback (4종) | nodes.py | 2a reader schema 안전망 | 2a 권한표 보충 |
| `_fallback_response_strategy` | nodes.py | phase_3 계약 안전망 | phase_3 권한표 보충 |
| reasoning budget fallback | start_gate.py | LLM budget 안전망 | -1s 내부 도구 |
| WarRoom fallback adapter | warroom/ | WarRoom 권한표 (보류 8과 묶임) | WarRoom 별도 조항 |

---

## 뒷면 ① — V4 §2 금지목록 후보 (자유발화)

### V3 §2 24개 (양식 참고용 — 정확한 본문은 `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` §2 옆에 두고)
대분류:
- 노드 권한 위반 (도구 호출/답변 작성/사고 재판정 등을 정해진 노드 외 위치에서 X)
- LLM 사고 규칙 (raw user wording 복사 / tool name as goal / fallback fabrication 등)
- 데이터 흐름 위반 (state 키 직접 mutation / schema 우회 등)
- 라우팅 위반 (정해진 길 우회 / hardcoded 분기 등)

### V4 추가 후보 (자유발화 박을 거)
- (a) **axis 섞기 X**: 시간축/의미축 fork된 데이터를 한 사이클 안에서 섞지 마라 (의미축 정부 v0.3 결재)
- (b) **인칭 메타데이터 NULL X**: source_persona 안 박힌 DreamHint/SecondDream write 금지 (v1.6 결재, R3 박힘)
- (c) **remand_guidance 포맷 위반**: reason_type 빈 string인데 evidence_refs 박는 식 정합성 위반 X (F2 박힘)
- (d) **fact_id 발명 X**: -1b가 reasoning_board에 없는 fact_id 인용하면 violation (F2 발주 명시, V4 §2에 박는 안건)
- (e) **119 enum 무분류**: 119 진입 시 reason_type/severity enum 빈 채로 escalate X (보류 9 풀 때)
- (f) **DreamHint expires_at 우회 X**: archive_at IS NULL + expires_at > now 필터 우회 X (R7 박힘)
- (g) **tool_request 0차 외 발생 X**: F4 후 -1a/-1s/-1b 어디서도 tool_request 직접 박기 X
- (h) **0차 LLM이 답변 작성 X**: F4 후 0_supervisor가 도구 선택만, 최종 판단/답변 X

자유발화 시간 = 위 8개 외에 더 떠올린 거 + V3 24개 중 V4에서 유효성 떨어진 거 빼는 작업.

---

## 뒷면 ② — 보류 10개 정리 (어제 v2 시트 → 오늘 진척)

| # | 보류 안건 | 상태 | 다음 |
|---|---|---|---|
| 1 | working_memory → -1s 입력 (X2) | 잔존 | 별도 X2 발주 또는 보류 6과 묶음 |
| 2 | -1b remand 메시지 채널 | ✅ **F2 풀림** (reason_type/evidence_refs/delta) | 닫음 |
| 3 | -1s/-1a 권한 충돌 | ✅ **F2/F3 풀림** | 닫음 |
| 4 | operation_contract 스키마 | F4 안건 | F4 후 verify |
| 5 | phase_3이 user_input 다시 봐야? | 잔존 | 1주 모니터링 후 결정 (모니터링 신호 미정 — 학교에서 박을 거) |
| 6 | 0차 에이전트 루프 고립 | F4 안건 | F4 후 verify |
| 7 | -1b 입력 비대 (8필드) | 잔존 | 1주 운영 후 phase3_summary 인용 0건이면 제거 |
| 8 | WarRoom 격리 설계 | 잔존 | **학교에서 비전 자유발화** (v1-A sos 전용 + v2 동적 좌석 + 트리오 프렉탈) |
| 9 | 119 enum 분류 | 잔존 | Phase 1 (V4 §2 (e)와 묶음) |
| 10 | 모듈식 답변 생성 노드 | 잔존 | Phase 1 delivery_packet 미래 호환 (보류 4-3 phase_3 cited_fact_ids도 같이) |

**오늘까지 풀린 = 2, 3 (2개). F4 끝나면 4, 6도 풀림. 학교에서 = 5, 8, 9, 10 자유발화 좋음.**

---

## 학교에서 할 일 체크리스트

- [ ] **A**: V4 §1 권한표 5조항 본문 글 박기 (위 앞면 ① 표 → 헌법 문장으로 풀어내기)
- [ ] **B**: 7 fallback 권한표 §1 보충 조항으로 글 박기
- [ ] **C**: V4 §2 신규 금지 후보 자유발화 (위 뒷면 ① 8개 + α)
- [ ] **D**: 보류 5/7 모니터링 신호 정의 ("어떤 지표/현상이면 발주 진입" 박기)
- [ ] **E**: 보류 8 WarRoom v2 비전 자유발화 (격리 + 동적 좌석 + 트리오 프렉탈)
- [ ] **F**: 보류 9 119 enum 분류 후보 자유발화 (BUDGET_EXHAUSTED / TOOL_TIMEOUT / LLM_HALLUCINATION / ROUTE_DEADLOCK / 등 + reason_type과 통합)
- [ ] **G**: 보류 10 delivery_packet 미래 호환 + 보류 4-3 cited_fact_ids 묶어 비전 박기
- [ ] **H**: Phase 0 → Phase 1 진입 결재 (게이트 = midnight ≥3 ✅ + nodes ≤2 ✅ + tests ≥231 ✅ + V4 §1 작성 가능)

---

## 메모리 참고 (학교에서 핸드폰으로 검색하면 나오는 파일)

핵심 메모리 파일 (`memory/` 폴더):
- `project_v4_section1_field_loop_decisions.md` — 결재 1~7 + 4-1~4-4 LIVE
- `project_v4_section_0.md` — V4 §0 v0 LIVE LAW
- `project_purge_phase.md` — Phase 0 진행 + 보류 사항
- `project_v4_midnight_government_v1_6.md` — 시간축 심야정부 LIVE
- `project_v4_semantic_government_v0_3.md` — 의미축 정부 LIVE
- `step2_mapping_draft.md` — 11단계 매핑 + A트랙 후속 윤곽

저장소 LIVE 문서 (`.md` 루트):
- `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` — V3 §1·§2 (V4 §1·§2 박을 때 양식 참고)
- `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` — V4 §0 v0 (§1·§2 본문이 비어있음, 학교에서 채울 곳)
- `ANIMA_V4_MIDNIGHT_GOVERNMENT_PROPOSAL.md` — 심야정부 v1.6 본문
- `ANIMA_ARCHITECTURE_MAP.md` — purge log #61~#69 + F1 #70 + F2 #71 (F3/F4 추가 예정)

발주서 (`Orders/V4_Phase_0/`):
- order_F1.md / F1_codex_dispatch.md (현장 advisory 다리)
- order_F2.md / F2_codex_dispatch.md (-1s 보강 + -1b 대조 채널)
- order_F3.md / F3_codex_dispatch.md (-1a 입력 축소 + tactical_briefing 이동)
- order_F4.md (오늘까지 박을 예정 — 0차 LLM 격상)
- V4_section1_A_decision_sheet.md (어제 v2 시트)

---

**작성**: 2026-05-07 늦은 시간, 학교 가기 전 박음.
**용도**: 한 번 쓰고 버리는 학습 자료. F4 끝난 후 재갱신 가능.
