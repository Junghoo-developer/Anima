# Codex 작업 의뢰: V4 Phase 0 F트랙 #F1

**의뢰일**: 2026-05-06
**의뢰자**: 정후 (입법부) — Claude (사법부 자문) 통역 검수 후 결재
**작업자**: Codex (행정부 실무)
**저장소**: SongRyeon_Project (master 브랜치, V4 baseline commit `782a982` 이후)

---

## 작업 의뢰 핵심

**[Orders/V4_Phase_0/order_F1.md](order_F1.md) 발주서 그대로 따라 작업하라.**

요약:
- `Core/adapters/night_queries.py` `recent_tactical_briefing` 함수 본체의 Cypher MATCH `TacticalThought` → `DreamHint` 교체
- signature/함수명/state 키 무변경 (rename 금지 — V4 §1 헌법 작성 시 일괄)
- 신설 단위 테스트 `tests/test_field_advisory_dreamhint_bridge.py` (case 3개)
- 234 tests OK + grep 0건 + purge log #70 추가

---

## 작업 시작 전 필수 read (AGENTS.md §3.1 + 본 발주 한정)

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (V3 §1·§2 LIVE LAW)
4. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (V4 §0 v0)
5. `ANIMA_ARCHITECTURE_MAP.md` (R 시리즈 purge log #61~#69 확인)
6. `ANIMA_V4_MIDNIGHT_GOVERNMENT_PROPOSAL.md` (DreamHint 정의)
7. **`Orders/V4_Phase_0/order_F1.md`** (본 발주 풀 본문)
8. `Core/adapters/night_queries.py` (`recall_active_dreamhints` 패턴 재사용)
9. `Core/pipeline/tool_execution.py:63-69` (`tool_search_dreamhints` 호출 패턴)
10. `tests/test_midnight_r7_integration.py` (mock session 패턴)

---

## 환경 안내 (Windows 11 / PowerShell)

- 인코딩: 모든 신설 파일 **UTF-8 (BOM 없음)**. PowerShell에서 `Set-Content` 사용 시 `-Encoding utf8` 명시. `Out-File` 기본 (UTF-16 LE) 금지.
- 테스트 실행: `python -B -m unittest discover -s tests`
- grep 실행: `Select-String` 또는 `rg` (ripgrep)

---

## V4 §1 결재 사항 (참고, 본 발주 무관)

2026-05-06 정후 결재로 박힌 V4 §1 골격 — **본 발주 F1과 독립**, F2/F3에서 다룸:

- delivery_review = new -1b (post-phase3 reviewer): 권한 = approve / remand(-1s,-1a) / sos_119
- -1s 보강 (F2): SThinkingPacket → ThinkingHandoff.v1 + analysis_report compact view 권한
- -1a 입력 축소 (F3): analysis_report/raw_read_report/reasoning_board 직접 read 제거

→ 본 F1 발주는 advisory source 교체만. -1b/-1s/-1a 입력 surface 안 건드림.

---

## 절대 금지 (발주서 §"의문 시 행동" 요약)

- 함수명 rename (`recent_tactical_briefing` → 다른 이름) **금지**
- state 키 rename (`tactical_briefing` → 다른 이름) **금지**
- DreamHint 0건 시 옛 TacticalThought fallback **절대 금지** (V3 흔적 부활 X)
- `search_tactics` 함수 (`TacticCard` MATCH)도 같이 폐기/수정 욕구 **금지** (별도 발주)
- 본 발주 외 추가 refactor/cleanup **금지**
- 가중치/필터링 정책 추가 **금지** (T트랙 본격화 시)
- DreamHint 필드 (hint_text/branch_path/source_persona) 외 추가 권한 **금지**
- V3 §2 절대 금지 24개 위반 의심 패턴 발견 시 즉시 멈추고 보고

---

## 작업 후 보고

발주서 §"작업 후 보고 형식" 그대로. 정후/Claude 검수 대기.

의문 발생 시 작업 멈추고 정후/Claude에 질의 (AGENTS.md §2).
