# 발주 #0.3 — midnight_reflection.py 분해 3차 (REMGovernor 모듈 분리)

**발주일**: 2026-05-03
**트랙**: V4 Phase 0 / A 트랙 #3 (병렬 트랙 3)
**선행**: 발주 #0.1 (StrategyCouncil 분리), 발주 #0.2 (REMPlan 분리)
**의존성**: 없음. B 트랙(#0.5~#0.7)과 *병렬 가능* — 다른 파일 건드림.

---

## Why

`Core/midnight_reflection.py` god-file (현재 4,269줄) 잔존이 V4 §0 v0의 *"심야 정부(밤)가 매일 인격을 진화시킨다"* 인프라 마련을 막고 있음. REMGovernor 모듈 분해는 야간 정부의 **과거 정부** 아키텍처 기초를 독립 에이전트 루프로 구축하는 핵심 인프라. V4 Phase 0 졸업 게이트 달성 필수.

---

## 스코프

### 하는 것

1. `Core/midnight/` 디렉토리 확인 (StrategyCouncil, REMPlan 이미 있음)
2. midnight_reflection.py 안의 **REMGovernor 관련 메서드**를 다음 기준으로 식별:
   - `_default_rem_governor_state()` (line ~1886)
   - `_load_existing_rem_governor_state()` (line ~2036)
   - `_build_rem_governor_state()` (line ~2195)
   - `_refresh_rem_governor_state()` (line ~2293)
   - `_build_governor_root_profiles()` (line ~1516)
   - `_build_governor_root_inventory()` (line ~1581)
   - `_build_governor_policy_inventory()` (line ~1613)
   - `_apply_governor_root_profiles_to_roots()` (line ~1746)
   - `_apply_governor_root_state_to_roots()` (line ~1808)
   - 관련 헬퍼: `_root_entity_from_asset_scope()`, `_parse_branch_health_map()` 등
3. 분리된 코드를 `Core/midnight/rem_governor.py`로 신설
4. midnight_reflection.py에는 *import 호환 wrapper*만 남김 (한 시즌 유지)
5. `node_rem_governor()` 메서드는 wrapper로 남겨 LangGraph 노드 이름 안정성 유지
6. 189 tests OK 유지 (테스트 깨지면 즉시 중단 + 정후/Claude에 보고)

### 안 하는 것 (다음 발주)

- REMGovernor 내부 로직 변경 (이번 발주는 *코드 위치 이동*만, 의미 변경 X)
- Architect, Phase10Policies 분리 (#0.4에서 순차 처리)
- midnight_reflection.py 완전 폐기 (#0.4 마무리 단계에서)
- V4 §0 v0 함의 외 *새 기능 추가* X
- V4 §1·§2 미작성이므로 *권한 변경* X (V3 §1·§2 그대로 유지)

---

## 변경 대상 (코드 좌표)

- **신설**: `Core/midnight/rem_governor.py`, 필요시 `Core/midnight/__init__.py` 갱신
- **변경**: `Core/midnight_reflection.py` (이전된 메서드 자리에 import wrapper로 대체)
- **영향 가능성**: 테스트는 midnight_reflection.DreamWeaver 이름 유지로 안정 (wrapper 유지)

---

## 검증 기준

1. **자동 검사**: `python -B -m unittest discover -s tests` → **189 tests OK 유지**
2. **줄 수 측정**: midnight_reflection.py 줄 수 감소 (대략 -300 ~ -500줄 예상, 메서드 크기에 따라)
3. **purge log 추가**:
   - `ANIMA_ARCHITECTURE_MAP.md`에 #55 다음 줄 추가
   - 마커: "**V4 Phase 0 midnight 분해 3차 completed for the REMGovernor department**"
   - 정확한 줄 수 변동, 신설 파일 경로, wrapper 호환성 명시
4. **import 호환 확인**: 기존 코드에서 `from Core.midnight_reflection import ...` 같은 import는 wrapper로 그대로 작동해야 함

---

## 롤백

- 분리된 REMGovernor 모듈을 *호환 wrapper*로 한 시즌 유지 (즉시 폐기 X)
- midnight_reflection.py에 deprecate marker 박되 import path는 살림
- 테스트 깨지면 즉시 중단 + 변경 reverted

---

## 헌법 정합

- **V4 §0 v0 위반 X**: 분해 = 진화 인프라 깔기. "심야 정부가 매일 진화시킨다" 함의 충족.
- **V3 §2 절대 금지 24개 위반 X**: LLM 사고 규칙 변경 X, 권한 변경 X, *코드 구조 이동만*.
- **AGENTS.md §3.3 nodes.py 수술 게이트 트리거 X**: midnight_reflection.py 작업이지 nodes.py 수술 아님.
- **AGENTS.md §1 인코딩**: 모든 신설 파일 UTF-8 (BOM 없음). PowerShell 사용 시 `-Encoding utf8` 명시.

---

## 코덱스가 발주 받기 전 읽어야 할 문서 (AGENTS.md §3.1 수술 전 기본 읽기 세트)

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` ← V4 §0 v0 + 부록 X/Y
4. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` ← V3 §1·§2 (현 LIVE LAW)
5. `ANIMA_ARCHITECTURE_MAP.md`
6. (이번 발주 한정) `Core/midnight_reflection.py` ~line 2293 범위 inventory (REMGovernor 메서드 식별)

---

## 의문 시 행동 (AGENTS.md §2)

> Codex는 비전 결정에 개입하지 않는다. 헌법 해석에 의문이 생기면 작업을 멈추고 정후/Claude에게 질의한다.

- REMGovernor 의존성 분석 결과 모호하면 → 정후에 후보 메서드 목록 제시하고 결재 받기
- 분리 도중 V3 §2 위반 의심 패턴 발견 시 → 즉시 멈추고 보고
- 분리 도중 *V4 §1 권한 결정이 필요한* 사항 발견 시 → V4 §1 미작성이므로 *V3 §1 그대로* 적용 + 보고

---

## 작업 후 보고 형식 (정후/Claude 검수용)

```
# 발주 #0.3 작업 완료 보고

## 분리한 부서: REMGovernor
## 신설 파일: [경로 목록]
## 변경 파일: [경로 목록 + 줄 수 변동]
## 줄 수 측정:
  - midnight_reflection.py: [전] 4269줄 → [후] XXXX줄 (-XXXX줄)
  - 신설 파일 합계: XXXX줄
## 테스트: 189 tests OK / [실패 시 상세]
## ARCH MAP purge log #56: 추가 완료
## 의문 / 발견 / V4 §1 작성 시 다룰 사항: [있으면]
```

---

**발주 OK 여부 정후 결재 후 코덱스 작업 시작.**
