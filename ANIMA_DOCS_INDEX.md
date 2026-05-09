*[한국어](ANIMA_DOCS_INDEX.md) | [English](ANIMA_DOCS_INDEX.en.md)*

# ANIMA Documents Index

Created: 2026-05-01

This file is the navigation map for ANIMA planning documents. It does not
replace the field-loop constitution. It tells Codex, Claude, and Jeonghu which
document to trust for each kind of work.

## Reading Order

### 1. Live Law

Use these when making or reviewing code changes.

- `AGENTS.md`
  - Scope: collaboration rules for Codex, Claude, and other AI workers.
  - Use for: encoding rules, role split, document priority.
  - Owner: Jeonghu.

- `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md`
  - Scope: V4 §0 v0 (사고/학습/진화 원칙, 낮↔밤 분리, 트리오 재귀) + 부록 X (Phase 0~3 로드맵) + 부록 Y (B 통합문, 4대 축). §1·§2·§10은 작성 중.
  - Use for: V4 방향성 결정 + Phase 0 발주 게이트 검증 + V4 §1·§2 작성 출발점.
  - Status: §0 v0 정후 통과 (2026-05-02). §1·§2 통과 전까지 권한표/금지목록은 V3에서 가져옴.
  - Owner: Jeonghu.

- `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md`
  - Scope: field-loop authority, forbidden actions, node responsibilities. V3 (정후 통과 2026-05-01, §10 implementation-complete after purge log 53).
  - Use for: V4 §1·§2 통과 전까지 권한표/절대 금지 24개의 LIVE LAW. V4 §0과 충돌 시 V4가 이김 (방향성).
  - Status: §0 SUPERSEDED by V4 §0 v0 (2026-05-02). §1·§2·§10은 LIVE LAW 유지.
  - Owner: Jeonghu.

- `ANIMA_FIELD_LOOP_V2_CONSTITUTION.md`
  - Scope: previous field-loop constitution.
  - Status: SUPERSEDED by V3 (2026-05-01). Kept for diff/comparison only. Not the current law.

### 2. Live Status

Use these to understand current implementation state and immediate cleanup work.

- `ANIMA_ARCHITECTURE_MAP.md`
  - Scope: current runtime map, package boundaries, migration progress, purge log.
  - Use for: checking what already moved and what remains risky.
  - Owner: Codex updates after implementation passes.

- `ANIMA_State_Optimization_Checklist.md`
  - Scope: state size, prompt projection, turn-lived cleanup, memory writer boundaries.
  - Use for: token normalization and contamination-control work.
  - Owner: Codex updates after implementation passes.

### 3. Background / Absorbed

Use these for philosophy and historical intent. They are not the current coding
law when they conflict with the V3 constitution.

- `ANIMA_REFORM_V1.md`
  - Scope: original reform philosophy.
  - Use for: why convergence, responsibility split, and renderer-style delivery matter.
  - Status: mostly absorbed by the V3 constitution.

- `ANIMA_REFORM_IMPLEMENTATION_V1.md`
  - Scope: original implementation slices.
  - Use for: historical sequencing and old acceptance tests.
  - Status: partially implemented and partially superseded.

### 4. Future Design

Use these for later passes. Do not let them directly override the current field
loop until the constitution is amended.

- `ANIMA_WARROOM_V2_SCHEMA.md`
  - Scope: future multi-seat WarRoom.
  - Use for: designing internal deliberation packets after the field loop is stable.
  - Status: future design.

- `ANIMA_SLEEP_STACK_V1.md`
  - Scope: first sleep-stack design with REMPlan, SecondDream, RoutePolicy, ToolDoctrine.
  - Use for: early night-government planning.
  - Status: future design.

- `ANIMA_SLEEP_STACK_V2.md`
  - Scope: expanded sleep-stack city plan with REMGovernor, coverage audit, placement judge, branch growth.
  - Use for: long-term night-government architecture.
  - Status: future design.

## Conflict Rules

1. If code conflicts with `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (권한표/금지목록), the code loses.
2. If V4 §0 v0 conflicts with V3 §0 (방향성), V4 wins. V3 §1·§2·§10 (권한표/금지/시행)은 V4 §1·§2 통과 전까지 LIVE LAW 유지.
3. If old reform documents (including V2) conflict with the current constitution, the current constitution wins.
4. If future design documents conflict with the current field-loop constitution, treat them as proposals.
5. If `AGENTS.md` conflicts with tool behavior, follow `AGENTS.md` for repository-specific workflow unless the platform forbids it.
6. If a document appears mojibake, first read it with explicit UTF-8 before editing it.

## Codex Working Set

For most code surgery, Codex should open only:

1. `AGENTS.md`
2. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (방향성 + Phase 0 발주 5축 + 부록 X/Y)
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (권한표 / 금지목록 / 시행 history)
4. `ANIMA_ARCHITECTURE_MAP.md`
5. `ANIMA_State_Optimization_Checklist.md`

Then inspect source files.

## Current Boundary Note

As of 2026-05-01:

- `Core.pipeline` and `Core.warroom` contain many extracted implementations.
- `Core.nodes` is still a large compatibility/wiring module, not a completed
  thin-controller file.
- `Core.runtime` exists as a minimal runtime-profile/context/cleanup boundary.
  Self-kernel injection is deferred to a later identity reform.
- `Core.memory` exists as a writer-contract/sanitizer boundary. WorkingMemory
  and FieldMemo writer prompt/normalization code now lives there, while legacy
  modules still own persistence and compatibility shells.

V3 §0 one-line summary, §1 권한표, §2 forbidden list (21 → 22항), §5 사례 표 + answer_mode 컬럼,
부록 C schema 명세는 모두 정후 통과 (2026-05-01). V3 §10 현장 루프 시행은
ARCHITECTURE_MAP purge log 53 기준 완료. 남은 Q1/Q4 및 self-kernel,
WarRoom v2, 심야정부, DB/tooling 개혁은 V4 후보로 다룬다.

## Claude Working Set

For design review, Claude may read all documents, but should report which
document is being treated as:

- current law
- current status
- background
- future design

## Update Policy

- After code movement or deletion, update `ANIMA_ARCHITECTURE_MAP.md`.
- After token/state cleanup, update `ANIMA_State_Optimization_Checklist.md`.
- After changing node authority or forbidden actions, update `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md`.
- After a repeated AI-worker mistake, update `AGENTS.md`.
- Do not edit background/future documents merely to keep them current. Add status banners instead.
