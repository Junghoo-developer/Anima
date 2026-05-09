*[한국어](ANIMA_DOCS_INDEX.md) | [English](ANIMA_DOCS_INDEX.en.md)*

# ANIMA Documents Index

Created: 2026-05-01 | Last updated: 2026-05-09 (V4 §1-A LIVE)

This file is the navigation map for ANIMA planning documents. It does not
replace the field-loop constitution. It tells Codex, Claude, and Junghoo which
document to trust for each kind of work.

## Reading Order

### 1. Live Law

Use these when making or reviewing code changes.

- `AGENTS.md`
  - Scope: collaboration rules for Codex, Claude, and other AI workers.
  - Use for: encoding rules, role split, document priority.
  - Owner: Junghoo.

- `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md`
  - Scope: V4 §0 v0 (think/learn/evolve principles, day↔night separation, trio recursion) + Appendix X (Phase 0~3 roadmap) + Appendix Y (B integrated text, four pillars). **§1-A and §2 are now LIVE LAW (ratified 2026-05-09)**. §1-B/C/D/E and §10 are still in drafting.
  - Use for: V4 directional decisions + Phase 0/1 dispatch gate verification + V4 §1-B/C drafting starting points.
  - Status: §0 v0 ratified by Junghoo (2026-05-02). **§1-A field-loop authority table and §2 absolute prohibitions ratified by Junghoo (2026-05-09)**. §1-B/C/D/E pending.
  - Owner: Junghoo.

- `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md`
  - Scope: field-loop authority, forbidden actions, node responsibilities. V3 (ratified by Junghoo 2026-05-01, §10 implementation-complete after purge log 53).
  - Use for: LIVE LAW outside the V4 §1-A field-loop scope (e.g., midnight government areas not yet covered by V4 §1-B/C/D/E). Where V4 §0 / §1-A / §2 conflict, V4 wins.
  - Status: §0 SUPERSEDED by V4 §0 v0 (2026-05-02). §1 field-loop portion SUPERSEDED by V4 §1-A (2026-05-09). §2 SUPERSEDED by V4 §2 (2026-05-09). §1 non-field-loop portions and §10 remain LIVE LAW.
  - Owner: Junghoo.

- `ANIMA_FIELD_LOOP_V2_CONSTITUTION.md`
  - Scope: previous field-loop constitution.
  - Status: SUPERSEDED by V3 (2026-05-01). Kept for diff/comparison only. Not the current law.

### 2. Live Status

Use these to understand current implementation state and immediate cleanup work.

- `ANIMA_ARCHITECTURE_MAP.md`
  - Scope: current runtime map, package boundaries, migration progress, purge log.
  - Use for: checking what already moved and what remains risky. Includes purge log #74 (V4 §1-A LIVE + Phase 0→1 entry marker) and #75 (CR1 dispatch stand-by).
  - Owner: Codex updates after implementation passes.

- `ANIMA_State_Optimization_Checklist.md`
  - Scope: state size, prompt projection, turn-lived cleanup, memory writer boundaries.
  - Use for: token normalization and contamination-control work.
  - Owner: Codex updates after implementation passes.

### 3. Background / Absorbed

Use these for philosophy and historical intent. They are not the current coding
law when they conflict with the V4/V3 constitution.

- `ANIMA_REFORM_V1.md`
  - Scope: original reform philosophy.
  - Use for: why convergence, responsibility split, and renderer-style delivery matter.
  - Status: mostly absorbed by the V3 constitution and carried into V4.

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
  - Status: future design (V4 §1-C will integrate this).

- `ANIMA_SLEEP_STACK_V1.md`
  - Scope: first sleep-stack design with REMPlan, SecondDream, RoutePolicy, ToolDoctrine.
  - Use for: early night-government planning.
  - Status: future design.

- `ANIMA_SLEEP_STACK_V2.md`
  - Scope: expanded sleep-stack city plan with REMGovernor, coverage audit, placement judge, branch growth.
  - Use for: long-term night-government architecture.
  - Status: future design.

- `ANIMA_V4_MIDNIGHT_GOVERNMENT_PROPOSAL.md`
  - Scope: V4 midnight-government vision v1.6 (DreamHint, V3 trio future-department instantiation, persona metadata, R3~R8 roadmap).
  - Use for: V4 §1-B drafting starting point.
  - Status: vision LIVE (drove R3~R8 implementation). §1-B body pending.

## Conflict Rules

1. If code conflicts with `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` §1-A or §2 (field-loop authority/prohibitions), the code loses.
2. For non-field-loop authority (midnight government, etc.), V3 §1·§10 remain LIVE LAW until V4 §1-B/C/D/E ratify.
3. If old reform documents (including V2) conflict with the current constitution, the current constitution wins.
4. If future design documents conflict with the current field-loop constitution, treat them as proposals.
5. If `AGENTS.md` conflicts with tool behavior, follow `AGENTS.md` for repository-specific workflow unless the platform forbids it.
6. If a document appears as mojibake, first read it with explicit UTF-8 before editing it.

## Codex Working Set

For most code surgery, Codex should open only:

1. `AGENTS.md`
2. `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (V4 directional + §1-A LIVE + §2 LIVE + Appendix X/Y + Phase 0 dispatch axes)
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` (non-field-loop authority + history)
4. `ANIMA_ARCHITECTURE_MAP.md`
5. `ANIMA_State_Optimization_Checklist.md`

Then inspect source files.

## Current Boundary Note

As of 2026-05-09 (V4 §1-A LIVE):

- `Core.pipeline` and `Core.warroom` contain many extracted implementations. After F2/F3/F4 (commit `62934d2`), -1s/-1a/-1b authority alignment matches V4 §1-A.
- `Core.nodes` is still a large compatibility/wiring module, not a completed thin-controller file. B-track #0.5 removed `_fallback_strategist_output` dead code.
- `Core.runtime` exists as a minimal runtime-profile/context/cleanup boundary. Self-kernel injection is deferred to a later identity reform.
- `Core.memory` exists as a writer-contract/sanitizer boundary. WorkingMemory and FieldMemo writer prompt/normalization code now lives there.
- `Core.midnight` is divided into 4 departments + semantic-axis fork (R1~R8 complete). Phase 0 → 1 entry gate satisfied.

V3 ratified items (2026-05-01) and V4 §0 v0 (2026-05-02) plus V4 §1-A and §2 (2026-05-09) are all LIVE LAW. The remaining areas (self-kernel, WarRoom v2, midnight-government V4 §1-B, DB/tooling reform) are tracked as Phase 1~3 candidates.

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
- After changing node authority or forbidden actions, update `ANIMA_FIELD_LOOP_V4_CONSTITUTION.md` (V3 if outside field-loop scope).
- After a repeated AI-worker mistake, update `AGENTS.md`.
- Do not edit background/future documents merely to keep them current. Add status banners instead.
