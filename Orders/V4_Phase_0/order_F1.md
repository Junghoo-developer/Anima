# 발주 #F1 — 현장 자동 advisory 다리: tactical_briefing → DreamHint

**발주일**: 2026-05-06
**트랙**: V4 Phase 0 / **F 트랙 #F1** (현장 정상화 1차, 신설 트랙)
**선행**: R1~R8 (의미축 정부 fork 완료, V4 baseline commit `782a982`), Neo4j wipe 완료
**의존성**: 없음. F2/F3 (-1s 보강 / -1a 입력 축소)와 분리. 작은 fix (~15~30줄).

---

## Why

V4 심야 정부가 R3~R8에서 **DreamHint** 단일 라벨로 모든 advisory를 통합했음 (옛 RoutePolicy/ToolDoctrine/TacticalThought 폐지). 그러나 현장 (낮 turn) **자동 advisory 입력 채널**이 옛 V3 라벨을 그대로 read 중:

- `main.py:381` `tactical_briefing = recent_tactical_briefing(8)` → `initial_state["tactical_briefing"]`
- `Core/adapters/night_queries.py:112-143` `recent_tactical_briefing` 함수가 `MATCH (t:TacticalThought)` Cypher 쿼리 사용
- Neo4j wipe로 결과는 매 turn 빈 string. **V4 심야 정부 ↔ 현장 자동 advisory 다리 끊김 상태**

DreamHint를 read하는 새 함수 `recall_active_dreamhints` ([:179](Core/adapters/night_queries.py#L179))는 박혀 있으나 호출처가 LLM 도구 (`tool_search_dreamhints`)뿐 — LLM이 명시 호출해야만 옴. **자동 advisory 채널이 V4에서 비어있음.**

V4 §1 권한표 작성 직전에 자동 advisory 다리 작은 fix로 V4 심야 정부의 산출물(DreamHint)이 현장 -1a/-1s thinker LLM 프롬프트에 매 turn 자동 도달.

---

## 스코프

### 하는 것

1. **`Core/adapters/night_queries.py:112-143` `recent_tactical_briefing` 함수 본체 교체**:
   - Cypher MATCH `TacticalThought` → `DreamHint`로 교체
   - DreamHint 필드 매핑:
     - `dh.hint_text` (advisory 본문)
     - `dh.branch_path`
     - `dh.source_persona`
     - `dh.created_at` (ORDER BY)
   - active 필터 박기:
     - `coalesce(dh.archive_at, 9999999999999) > timestamp()`
     - `AND coalesce(dh.expires_at, 9999999999999) > timestamp()`
     - 같은 패턴이 `recall_active_dreamhints` ([:179-225](Core/adapters/night_queries.py#L179-L225))에 이미 있음 — **재사용 (코드 중복 생산 X)**
   - 출력 string 형식 갱신:
     - 빈 결과: `"[advisory] No active DreamHint records."`
     - 결과 있음: `"[active DreamHint advisories]\n1. branch=... | source_persona=...\n   hint: ..."`
2. **docstring 갱신**: `"""Return active DreamHint advisories for the field loop's auto-input channel."""`
3. **함수명/signature/state 키 (`tactical_briefing`)는 그대로 유지**.
   - 사유: V4 §1 결재 5번 = "노드/함수명 rename은 V4 §1 헌법 작성 시 일괄". 본 발주는 source 교체만.
4. **신설 단위 테스트** `tests/test_field_advisory_dreamhint_bridge.py`:
   - case 1: DreamHint 1개 박은 mock graph_session → `recent_tactical_briefing(8)` 결과 string에 `hint_text` 포함
   - case 2: DreamHint 0개 → "No active DreamHint records." 반환
   - case 3: 만료된 DreamHint (`archive_at < timestamp()`) → 결과 0건
   - 패턴 참고: 기존 `tests/test_midnight_r7_integration.py`의 mock session 패턴 재사용
5. `tools/toolbox.py:45-46` `recent_tactical_briefing` CLI 노출 그대로 유지 (signature 안 바꾸니 후방 호환).

### 안 하는 것 (다음 발주)

- 함수명 rename (`recent_tactical_briefing` → `recent_dreamhint_briefing`): V4 §1 헌법 작성 시 일괄.
- state 키 rename (`tactical_briefing` → `dreamhint_briefing` 또는 `auto_advisory_briefing`): 위와 같음.
- **옛 `search_tactics` 함수** ([:14-44](Core/adapters/night_queries.py#L14-L44), `TacticCard` MATCH) 폐기: 별도 발주 (CLI search 후방 호환 검토 필요. 본 발주 범위 X).
- DreamHint 가중치 활용 (T트랙): T트랙 본격화 시.
- 키워드 필터 추가 (`recall_active_dreamhints`처럼 keyword 인자): 본 발주는 자동 advisory 8개 read만. 키워드는 LLM 도구 `tool_search_dreamhints` 책임.
- -1s/-1a/-1b 권한 재배치 (F2/F3): 다음 발주.
- DreamHint 0건 시 옛 TacticalThought fallback: **금지** (V3 흔적 부활 X).

---

## 변경 대상 (코드 좌표)

- **변경**: `Core/adapters/night_queries.py` (`recent_tactical_briefing` 함수 본체 ~30줄, signature/__all__/import는 그대로)
- **신설**: `tests/test_field_advisory_dreamhint_bridge.py`
- **변경 없음 (확인만)**:
  - `main.py:381` 호출 그대로 (signature 안 바꿈)
  - `Core/state.py` `tactical_briefing` 필드 그대로
  - `Core/prompt_builders.py:264` `[tactical_briefing]` 박는 곳 그대로
  - `Core/pipeline/strategy.py:118,177,237` 사용처 그대로
  - 기존 tests (`test_evidence_ledger`, `test_state_contract`, `test_prompt_builders`) 영향 X (string mock이라 안 깨짐)

---

## 검증 기준

1. **자동 검사**: `python -B -m unittest discover -s tests` → **231 tests + 신규 3 case = 234 OK** (또는 신규 테스트 case 수에 따라 적절히 갱신).
2. **수동 검사 (Codex가 직접 verify)**:
   - DreamHint 0건 상태 (Neo4j wipe 후 = 현재 상태)에서 `python -c "from Core.adapters.night_queries import recent_tactical_briefing; print(recent_tactical_briefing(8))"` 실행 → "[advisory] No active DreamHint records." (또는 동등) 반환 확인
3. **purge log 추가**: `ANIMA_ARCHITECTURE_MAP.md`에 R 시리즈 마지막 (#69) 다음 줄 #70 추가
   - 마커: "**V4 Phase 0 F트랙 #F1: 현장 자동 advisory 다리 V3 TacticalThought → V4 DreamHint 교체**"
   - 변경 줄 수, 신설 테스트, signature 무변경 명시
4. **grep 확인**: `Core/adapters/night_queries.py` `recent_tactical_briefing` 함수 본체 안에 `TacticalThought` 라벨 grep **0건**.

---

## 롤백

- 함수 signature 안 바꾸므로 기존 호출처 영향 X.
- 문제 발견 시 `git checkout 782a982 -- Core/adapters/night_queries.py` 단일 파일 복원 가능.
- 신설 테스트 파일은 그냥 삭제 가능.

---

## 헌법 정합

- **V4 §0 v0 위반 X**: 자동 advisory 다리 박기 = "심야 정부가 매일 진화시킨다" 구현 인프라 (산출물 → 현장 도달 채널 정상화).
- **2026-05-06 V4 §1 결재 (-1b/-1s/-1a 권한) 무관**: 본 발주는 advisory source 교체만. -1b/-1s/-1a 입력 surface 재배치는 F2/F3 발주 책임.
- **V3 §2 절대 금지 24개 위반 X**: LLM 사고 규칙 변경 X, 권한 변경 X, Cypher 라벨만 교체.
- **AGENTS.md §3.3 nodes.py 수술 게이트 트리거 X**: nodes.py 안 건드림.
- **AGENTS.md §1 인코딩**: 신설 테스트 파일 UTF-8 (BOM 없음). PowerShell 사용 시 `-Encoding utf8` 명시.

---

## 코덱스가 발주 받기 전 읽어야 할 문서 (AGENTS.md §3.1 + 본 발주 한정 추가)

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (V3 §1·§2 LIVE LAW)
4. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (V4 §0 v0)
5. `ANIMA_ARCHITECTURE_MAP.md` (R 시리즈 purge log #61~#69 확인)
6. `ANIMA_V4_MIDNIGHT_GOVERNMENT_PROPOSAL.md` (DreamHint 정의 + source_persona/branch_path/expires_at/archive_at 의미)
7. (이번 발주 한정) `Core/adapters/night_queries.py` 전체 (`recall_active_dreamhints` 패턴 재사용)
8. (이번 발주 한정) `Core/pipeline/tool_execution.py:63-69` (`tool_search_dreamhints` 호출 패턴 — 출력 형식 참고)
9. (이번 발주 한정) `tests/test_midnight_r7_integration.py` (mock session 패턴)

---

## V4 §1 결재 사항 (Codex 참고 — 본 발주 무관, 향후 발주 영향)

2026-05-06 정후 결재로 박힌 V4 §1 골격 (본 발주는 안 건드림, F2/F3가 다룸):

- **delivery_review = new -1b** (post-phase3 reviewer): 권한 = `approve / remand(-1s,-1a) / sos_119`. 도구 호출/검색어 생성/답변 작성/answer_mode 변경 금지.
- **-1s 보강 (F2 발주)**: SThinkingPacket.v1 → ThinkingHandoff.v1 schema 보강. analysis_report compact view LLM 입력 권한.
- **-1a 입력 축소 (F3 발주)**: -1a strategist 직접 입력에서 analysis_report/raw_read_report/reasoning_board 제거. ThinkingHandoff만 read.

→ F1 (본 발주)는 위 결재와 **독립**. advisory source 교체만.

---

## 의문 시 행동 (AGENTS.md §2)

- 함수명 rename 욕구 → **금지**. V4 §1 헌법 작성 시 일괄.
- state 키 rename 욕구 → 위와 같음.
- DreamHint 필드 (hint_text/branch_path/source_persona) 외 추가 권한 욕구 → 금지. 본 발주는 단순 advisory text만.
- 가중치/필터링 정책 추가 욕구 → 금지 (T트랙 본격화 시).
- DreamHint 0건 시 fallback (옛 TacticalThought도 read?) → **절대 금지**. V3 흔적 부활 X.
- `search_tactics` 함수도 같이 폐기/수정 욕구 → 금지 (별도 발주). 본 발주는 `recent_tactical_briefing`만.
- 분리 도중 V3 §2 위반 의심 패턴 발견 시 → 즉시 멈추고 보고.

---

## 작업 후 보고 형식 (정후/Claude 검수용)

```
# 발주 #F1 작업 완료 보고

## 변경 파일
- Core/adapters/night_queries.py: [전] N줄 → [후] N±M줄
  - recent_tactical_briefing 함수 본체 교체 (TacticalThought → DreamHint)
- tests/test_field_advisory_dreamhint_bridge.py: 신설 N줄 (case 3개)

## 테스트
- 234 tests OK (또는 실제 수) / [실패 시 상세]

## grep 확인
- Core/adapters/night_queries.py recent_tactical_briefing 본체 TacticalThought grep: 0건

## 수동 검사
- Neo4j wipe 상태에서 recent_tactical_briefing(8) 호출 → "[advisory] No active DreamHint records." 반환 확인 (혹은 실제 출력 첨부)

## ARCH MAP purge log #70: 추가 완료

## 의문 / 발견 / V4 §1 작성 시 다룰 사항
- [있으면 작성, 없으면 "없음"]
- 특히 함수/state 키 rename 후보 발견 시 V4 §1 일괄 rename 발주 후보로 보고
```

---

**발주 OK 여부 정후 결재 후 코덱스 작업 시작.**
