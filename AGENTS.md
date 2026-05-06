# AGENTS.md — Codex / AI 협업자 작업 규칙

이 저장소에서 Codex 또는 다른 AI 협업자가 따라야 하는 운영 규칙.
헌법(`ANIMA_FIELD_LOOP_V3_CONSTITUTION.md`)이 *무엇을* 만드는지 정한다면,
이 문서는 *어떻게* 다루는지를 정한다.

---

## 1. 인코딩 규칙 (한글/UTF-8 문서)

이 저장소의 모든 `.md`, `.py`, `.json`, `.yml`, `.txt` 문서는 **UTF-8 (BOM 없음)** 이다.
Windows PowerShell의 `Get-Content` / `Set-Content` 기본 인코딩은 UTF-8이 아니므로
한글이 모지바케로 보일 수 있다. 이건 파일이 깨진 것이 아니라 **읽는 쪽의 설정 문제**다.

### 1.1 PowerShell에서 파일을 읽을 때
```powershell
# OK
Get-Content path\to\file.md -Encoding UTF8
Get-Content path\to\file.md -Raw -Encoding UTF8

# 금지 (모지바케 발생)
Get-Content path\to\file.md
cat path\to\file.md
```

### 1.2 PowerShell에서 파일을 쓸 때
```powershell
# OK (BOM 없는 UTF-8)
$content | Out-File -FilePath path\to\file.md -Encoding utf8 -NoNewline
$content | Set-Content -Path path\to\file.md -Encoding utf8

# 금지 (UTF-16 LE 또는 BOM 포함 UTF-8이 됨)
$content > path\to\file.md
$content | Out-File path\to\file.md
```

### 1.3 Python에서 파일을 읽고 쓸 때
```python
# OK
with open(path, "r", encoding="utf-8") as f: ...
with open(path, "w", encoding="utf-8") as f: ...

# 금지 (Windows에서 cp949로 열려 UnicodeDecodeError 또는 모지바케)
with open(path) as f: ...
```

### 1.4 진단 절차

문서가 깨져 보이면 **재작성하기 전에** 반드시 다음을 먼저 확인한다:

1. `file path/to/file.md` (Git Bash) 또는 별도 도구로 실제 인코딩 확인
2. PowerShell이라면 `Get-Content -Encoding UTF8`로 다시 읽기
3. 그래도 깨져 보이면 그때 재작성 검토

**문서 재작성은 최후의 수단이다.** 인코딩 진단을 건너뛰고 "한글이 깨졌으니 ASCII로 다시 쓰자"는 결정은 금지.

---

## 2. 작업 분담 (사람 ↔ AI, 헌법 §11과 동일)

| 역할 | 담당 |
|------|------|
| 비전 결정 / 헌법 개정 | 정후 (입법부) |
| 비전 토론 + 코드 진단 + Codex 작업 검수 | Claude (사법부 자문) |
| 코드 작성/수정/테스트 | Codex (행정부 실무) |
| 최종 결재 (merge) | 정후 |

Codex는 비전 결정에 개입하지 않는다. 헌법 해석에 의문이 생기면 작업을 멈추고 정후/Claude에게 질의한다.

---

## 3. 단일 진실 원천 (Single Source of Truth)

모든 작업의 기준은 다음 순서로 우선한다:

0. `ANIMA_DOCS_INDEX.md` — 문서 내비게이션 (어떤 문서를 언제 볼지)
1. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` — 헌법 (권한표, 절대 금지 목록, 정후 통과 2026-05-01)
2. `ANIMA_ARCHITECTURE_MAP.md` — 현재 구조 지도와 숙청 로그
3. `ANIMA_State_Optimization_Checklist.md` — 토큰 정상화 체크리스트
4. `ANIMA_REFORM_V1.md`, `ANIMA_REFORM_IMPLEMENTATION_V1.md` — 배경/흡수된 비전 문서
5. `ANIMA_WARROOM_V2_SCHEMA.md`, `ANIMA_SLEEP_STACK_V1.md`, `ANIMA_SLEEP_STACK_V2.md` — 미래 설계 문서
6. 이 문서 (`AGENTS.md`) — 운영 규칙

기존 코드와 위 문서가 충돌하면 **문서가 이긴다.** 코드를 헌법에 맞춘다.

### 3.1 수술 전 기본 읽기 세트

Codex가 현장 루프 코드를 수정하기 전에는 기본적으로 아래 네 문서만 먼저 읽는다.

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md`
4. `ANIMA_ARCHITECTURE_MAP.md`

토큰/상태 최적화 작업이면 `ANIMA_State_Optimization_Checklist.md`를 추가로 읽는다.
WarRoom 또는 심야정부 작업이 아니면 `ANIMA_WARROOM_V2_SCHEMA.md`,
`ANIMA_SLEEP_STACK_V1.md`, `ANIMA_SLEEP_STACK_V2.md`는 직접 코딩 기준으로 삼지 않는다.

### 3.2 문서 상태 규칙

- `LIVE LAW`: 현재 코드 변경의 법적 기준.
- `LIVE STATUS`: 현재 구현 상태와 작업 로그.
- `BACKGROUND / ABSORBED`: 철학과 역사. 현재 헌법과 충돌하면 헌법이 이긴다.
- `FUTURE DESIGN`: 다음 pass 제안. 현재 헌법을 자동으로 덮어쓰지 않는다.

새 기획서가 생기면 먼저 `ANIMA_DOCS_INDEX.md`에 상태를 등록한 뒤 사용한다.

### 3.2.1 Codex 메모리 접근 규칙

Claude나 정후가 `memory/...` 또는 "내 메모리"에 있는 기획서를 언급해도,
Codex가 현재 파일시스템에서 그 경로를 직접 읽을 수 있다고 가정하지 않는다.

- 먼저 `rg --files` 또는 명시 경로 확인으로 실제 파일 존재 여부를 확인한다.
- 파일이 없으면 **없다고 보고**하고, 사용자/Claude가 메시지에 붙여준 발주문이나
  저장소의 LIVE 문서만 근거로 작업한다.
- 보이지 않는 memory 내용을 추측해서 구현하거나 헌법/ARCH MAP보다 우선하지 않는다.
- memory 문서를 코드 기준으로 쓰려면 먼저 저장소 파일로 추가하고
  `ANIMA_DOCS_INDEX.md`에 상태를 등록한다.

### 3.3 대형 nodes.py 수술 전 헌법 검수

`Core/nodes.py`의 대형 inventory, 삭제, 이동 작업을 시작하기 전에는
`ANIMA_FIELD_LOOP_V3_CONSTITUTION.md`의 아래 항목을 정후가 먼저 승인해야 한다.

1. §0 한 줄 요약
2. §1 핵심 5노드 권한표 (`-1s`, `-1a`, `-1b`, `2b`, `phase_3`)
3. §2 절대 금지 15개

승인 전에는 문서를 기준으로 6천 줄대 코드를 일괄 분류하지 않는다.

---

**버전**: V1 초안 (2026-05-01)
**갱신 트리거**: Codex가 같은 실수를 두 번 반복하면 그 항목을 이 문서에 추가한다.
