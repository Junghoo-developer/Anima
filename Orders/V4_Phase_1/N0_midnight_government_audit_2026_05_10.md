# N0 — Midnight Government Runtime Audit

작성일: 2026-05-10
상태: 감사 리포트 / N1·N2 후속 처리 완료 (2026-05-10), ARCH MAP #84 등록됨.
대상: `Core.midnight` dry-run 실행 결과와 V4 헌법/ARCH MAP/실제 코드 대조

## 실행 관찰

정후 실행:

```powershell
python -m Core.midnight
```

출력:

```json
{"status": "completed", "recent_unprocessed_count": 0, "future_decision": "approve"}
```

판정:

- 명령은 정상 종료했다.
- 이것은 `run_night()` dry-run orchestration이 한 바퀴 돈 결과다.
- DB write, semantic fork, live migration verify가 포함된 실운영 심야 학습 완료를 뜻하지 않는다.

## 기준 문서

- `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md`
  - V4 §0: "현장 루프(낮)가 매 턴 인격을 작동시키고, 심야 정부(밤)가 매일 인격을 진화시킨다."
  - V4 §1-A/§2: 현장 루프 부분만 LIVE.
  - V4 §1-B 심야 정부 권한표: 작성 예정.
  - 부록 X: Phase 0는 심야정부 인프라 캔버스 마련, Phase 2부터 본격 학습.
- `ANIMA_ARCHITECTURE_MAP.md`
  - #62~#69: R2~R8로 live `Core.midnight` package, recall/present/past/future/semantic skeleton and bodies completed.
  - #68: `run_night(graph_session, persist=True)` integration path exists, but live Neo4j migration was not executed by Codex.

## 코드 대조

### 1. CLI는 dry-run only

`Core/midnight/__main__.py` calls:

```python
packet = run_night()
```

No options are passed:

- `persist=False`
- `graph_session=None`
- `include_semantic=False`

Therefore the command is a heartbeat/dry-run entrypoint, not a production night job.

### 2. No unprocessed Dream still yields a fallback SecondDream

`Core/midnight/__init__.py` uses `_fallback_empty_seconddream()` when there is no recent day memory:

```python
seconddream_key="seconddream::dry-run"
classification="no_unprocessed_day_memory"
```

The chain still proceeds through:

```text
recent -> present -> past -> future
```

This is useful for dry-run verification, but operationally ambiguous.

### 3. Future approves even on dry-run/no-op material

`Core/midnight/future/decision_maker.py` approves whenever there are no blocking gaps and `source_persona` is non-empty.

When `recent_unprocessed_count=0`, future can still return:

```json
"decision": "approve"
```

This can be misread as "a real DreamHint-worthy night learning event occurred." In the current CLI path, it more accurately means "future department dry-run produced no blocking error."

### 4. Persist path exists but is not the default

`run_night()` can persist when called with:

```python
run_night(graph_session=session, persist=True)
```

R7 tests assert that this path can write:

- `SecondDream`
- `ChangeProposal`
- `Election`
- `DreamHint`

However, default CLI does not use this path.

### 5. Semantic fork exists but is not default

`Core.midnight.semantic` has a separate CLI:

```powershell
python -m Core.midnight.semantic
```

`run_night(include_semantic=True)` can invoke the semantic fork, but default `python -m Core.midnight` does not.

### 6. Live DB schema remains a separate operational question

R7 added migration/rollback/verify scripts, but ARCH MAP says live Neo4j migration was not executed by Codex.

Recent field-loop logs previously showed missing DreamHint label/property warnings. Therefore production readiness requires explicit DB verify before treating persisted night output as reliable.

## Mismatch Summary

| Area | V4 vision / status expectation | Current code behavior | Risk |
|---|---|---|---|
| CLI meaning | Night government runtime signal | Dry-run heartbeat | User may think real learning happened |
| No input data | Should likely idle/no-op | Builds fallback `seconddream::dry-run` and approves future | False-positive "approve" |
| Persistence | R7 path exists | Default CLI does not persist | Completed output is non-durable |
| Semantic axis | R8 exists | Not enabled by default | `Core.midnight` output covers time-axis only |
| Law | §1-B future work | Code has grown ahead of written authority table | Audit/authorization ambiguity |
| DB | Migration scripts exist | Live DB state unknown | Runtime warning / partial writes possible |

## Recommended Next Tracks

### N1 — Honest CLI Status

Change default `python -m Core.midnight` output to include:

```json
{
  "mode": "dry_run",
  "persisted": false,
  "semantic": false,
  "recent_unprocessed_count": 0,
  "night_action": "idle_no_unprocessed_dreams"
}
```

If there are no unprocessed dreams, report `idle_no_unprocessed_dreams` rather than letting `future_decision=approve` stand alone.

### N2 — No-Input Future Decision Guard

When recent recall has `unprocessed_count=0` and the only input is `seconddream::dry-run`, future should return a no-op/idle decision rather than approving a DreamHint-shaped advisory.

This must be a structural guard on known dry-run classification, not a semantic classifier.

### N3 — Production Entry Command

Add or document a separate explicit production command/path:

```text
run_night(graph_session=..., persist=True)
```

This should only be recommended after DB verify passes.

### N4 — DB Verify Before Persist

Run or expose a verification step for R7 schema expectations:

- `Dream`
- `SecondDream`
- `DreamHint`
- `TimeBranch`
- `NightGovernmentState`
- required `source_persona`
- active DreamHint `archive_at` / `expires_at`

No live migration should be performed by default.

### N5 — §1-B Draft Preparation

Use this audit as input for V4 §1-B 심야 정부 권한표:

- recall: source retrieval/provenance only
- present: summarize/problem/audit current night packet
- past/CoreEgo: proposal/election over unresolved SecondDreams
- future: DreamHint advisory decision
- semantic fork: separate meaning-axis assembly
- persistence: explicit, non-default, schema-verified

## Conclusion

`Core.midnight` is alive as a V4 Phase 0/R8 dry-run and tested integration skeleton.

It is not yet an unambiguous production "nightly learning completed" signal. The most urgent cleanup is not deeper intelligence; it is honest runtime semantics:

- distinguish dry-run from production,
- distinguish idle/no-input from approved advisory,
- distinguish time-axis default from semantic fork,
- verify DB schema before persist.
