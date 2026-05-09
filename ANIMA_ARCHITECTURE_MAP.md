  # ANIMA Architecture Map

> Document status: LIVE STATUS.
> 헌법 V3 정후 통과 (2026-05-01). 이 문서는 V3 §10 시행 순서대로 Codex가 갱신.
> Update this after code movement, deletion, or package-boundary changes.

This document maps the current ANIMA field loop before the next structural
refactor. It is intentionally descriptive: no behavior change is implied here.

## Current Runtime Entry

`main.py` owns the outer turn lifecycle.

1. Collect runtime signals:
   - user input
   - current time and time gap
   - dual core / vertical state from Neo4j
   - biolink status
   - recent tactical briefing
   - working memory snapshot
   - recent raw context
2. Build `AnimaState`.
3. Invoke `anima_app` from `Core.graph`.
4. Read final assistant message from graph state.
5. Append raw user/assistant messages to `MemoryBuffer`.
6. Commit structured working memory.
7. Build canonical turn record.
8. Ask FieldMemo writer for a durable memo candidate.
9. Persist Dream / TurnProcess / PhaseSnapshot.
10. Persist FieldMemo if the candidate passes.
11. Link used sources to the Dream.
12. Clear turn-lived graph fields with `cleanup_turn_lived_fields`.

The field loop therefore has two distinct halves:

- live reasoning: `Core.graph` and `Core.nodes`
- post-turn memory production: `MemoryBuffer`, `InferenceBuffer`, `FieldMemo`

## LangGraph Wiring

`Core.graph` is the graph owner. Public node names are stable and should not be
renamed during structural moves.

```text
START
  -> -1s_start_gate
      -> phase_3
      -> -1a_thinker
      -> phase_119

-1a_thinker
  -> 0_supervisor
  -> -1s_start_gate
  -> phase_119

0_supervisor
  -> phase_1
  -> phase_3
  -> phase_119
  -> phase_2a
  -> -1a_thinker
  -> -1s_start_gate

phase_1 -> phase_2a -> phase_2 -> -1s_start_gate
warroom_deliberator -> -1s_start_gate
phase_119 -> phase_3
phase_3 -> delivery_review
delivery_review -> END or -1a_thinker or -1s_start_gate or phase_119
```

Routing owner:

- `route_after_s_thinking`: reads `s_thinking_packet.routing_decision` and
  sends the next cycle to `phase_3`, `-1a_thinker`, or `phase_119`.
- `route_after_strategist`: sends executable `strategist_output.tool_request`
  to `0_supervisor`; otherwise returns control to `-1s_start_gate`.
- `route_after_supervisor`: execution status and tool-call dispatch.
- `route_after_delivery_review`: post-phase3 answer approval/remand/end
  decision.
- `route_after_phase3`: compatibility shim only.
- `route_audit_result_v2`: legacy compatibility fallback only. It is no longer
  a live graph edge owner.

## Field Loop Nodes

The live public node functions still live in `Core.nodes` except speaker guard
wrappers and WarRoom internals.

Important status note:

- Most public graph node implementations have been extracted into
  `Core.pipeline.*`.
- `Core.nodes` is not yet a true thin-controller file. It is still a large
  compatibility and dependency-wiring module with fallback helpers, legacy
  aliases, and purge candidates.
- 실측: `Core.nodes` = 6,922 lines (2026-05-01, after 7C). V3 헌법 §7의 thin-wrapper 목표(<300 lines)와 약 23배 차이.
- Treat any "thin wrapper" claim as directional progress, not a completed
  architecture state.

| Node | Current role | Should remain public? | Refactor direction |
| --- | --- | --- | --- |
| `phase_minus_1s_start_gate` | thin start contract | yes | internals moved to `Core.pipeline.start_gate` |
| `phase_minus_1a_thinker` | strategist / action plan | yes | internals moved to `Core.pipeline.strategy` |
| `phase_0_supervisor` | supervisor message/tool-call preparation | yes | internals moved to `Core.pipeline.supervisor` |
| `phase_1_searcher` | actual tool execution | yes | internals moved to `Core.pipeline.tool_execution` |
| `phase_2a_reader` | raw read report | yes | internals moved to `Core.pipeline.reader` |
| `phase_2_analyzer` | fact judge | yes | internals moved to `Core.pipeline.fact_judge` |
| `phase_3_validator` | final response generation | wrapper via speaker guard | internals moved to `Core.pipeline.delivery` |
| `phase_delivery_review` | post-phase3 delivery review | yes | internals live in `Core.pipeline.delivery_review`; this is the V3 -1b position |
| `phase_119_rescue` | clean rescue boundary | yes | internals moved to `Core.pipeline.rescue` |
| `phase_warroom_deliberator` | WarRoom wrapper | yes | keep wrapper; implementation already under `Core.warroom` |

## V3 §10 Step 4 — `Core.nodes` Inventory

Inventory date: 2026-05-01.

Scope: classification only. No deletion is authorized by this inventory by
itself.

Observed size:

- `Core.nodes`: 6,922 lines after 7C compatibility/test scaffolding.
- top-level `def`/`class` declarations: 328.
- public graph node wrappers: 10. The old pre-delivery `phase_minus_1b_*`
  wrappers were removed in V3 §10 단계 7C.

Classification key:

- **Keep wrapper**: public graph/API compatibility surface; keep in `nodes.py`
  until graph/test imports are migrated.
- **Move**: structurally valid code living in the wrong module.
- **Purge candidate**: violates or strongly risks V3 §1/§2 authority rules.
- **Review**: useful but coupled; needs a smaller decision before code changes.

### Public Surface

| Range | Functions | Class | Reason | Next action |
| --- | --- | --- | --- | --- |
| 5355-5379, 5723, 6284, 6619-6735 | `phase_0_supervisor`, `phase_1_searcher`, `phase_2a_reader`, `phase_minus_1a_thinker`, `phase_warroom_deliberator`, `phase_119_rescue`, `phase_3_validator`, `phase_delivery_review`, `phase_minus_1s_start_gate`, `phase_2_analyzer` | Keep wrapper | Graph public names stay stable after 7C. Most implementations already delegate to `Core.pipeline` / `Core.warroom`. | Keep short-term; later migrate tests/imports away from `Core.nodes` and shrink wrappers in batches. |
| 317-370 | `_env_model_name`, `_log`, clean-failure/action/ledger helpers | Keep/Move | Code-owned runtime/provenance helpers are legitimate. | Move to `Core.runtime` or `Core.pipeline.runtime_context` after tests cover imports. |
| 379-466 | topology/tool-description/tool-expression/auditor-decision adapters | Review | Tool-expression parsing is execution mechanics; auditor-decision construction may become obsolete after V3 -1b relocation. | Split execution parsing from old -1b decision helpers. |

### Compatibility Delegation Already Extracted

| Range | Functions | Class | Reason | Next action |
| --- | --- | --- | --- | --- |
| 821-1421 | source relay, FieldMemo review, answer-mode, delivery packet/gate wrappers | Move complete / keep wrapper | Mostly thin calls into `Core.pipeline.*`. | Keep short-term; migrate tests/imports away from `Core.nodes`, then delete wrappers in batches. |
| 3360-3654, 3881-3900 | continuation/social/follow-up wrappers | Move complete / review | Many delegate to `Core.pipeline.continuation`; remaining social strategy wrappers still risk meaning classification. | Keep delegate wrappers; review non-delegating semantic strategy builders below. |
| 4235-4386, 4520-4765 | progress signatures, execution trace, operation contracts, strategy arbitration, tool-request adapters | Move mostly complete | These are mostly code-owned activity tracking or thin wrappers to `Core.pipeline.progress`, `runtime_context`, `tool_planning`. | Move remaining local glue into pipeline modules; preserve only imports needed by tests. |
| 6766-6873 | compatibility classifier/tool-planning tail | Review | Contains no-op classifier plus memory-query/tool-request wrappers. Some call extracted implementations, some still pass raw-user heuristics. | Keep for compatibility until V3 step 6/7; purge deterministic query generation after replacement. |

### Valid Code In Wrong Place

| Range | Functions | Class | Reason | Next action |
| --- | --- | --- | --- | --- |
| 5379-5617, 6058-6101 | raw-read fallback parsers | Move | Deterministic parsing of already obtained source text is allowed as execution/source processing, not meaning judgment. | Move fully to `Core.pipeline.reader`. |
| 4113-4238 | tool expression parsing and direct tool message builder | Move/Review | AST parsing and tool-call normalization are execution mechanics. Query cleaning can drift into semantic repair. | Move AST/tool parsing to `Core.pipeline.tool_planning`; isolate query cleaning. |
| 4322-4490 | tool carryover, source-id extraction, scroll follow-up helpers | Move/Review | Carryover/source ids are code-observable activity; autonomous scroll/follow-up detection can become routing heuristic. | Move state normalization to runtime context; review scroll decision authority before reuse. |
| 2338-2446, 3030-3305 | reasoning-board construction/audit helpers | Move/Review | Reasoning-board storage is valid; audit/rewrite helpers may duplicate -1s/-1b authority. | Move neutral packet storage; review audit logic against V3 -1b-after-phase3 model. |

### Purge Candidates Before Further Moves

| Range | Functions | Why risky under V3 | Next action |
| --- | --- | --- | --- |
| 497-568, 6470-6497 | `_fallback_reasoning_budget_plan`, `_base_plan_reasoning_budget`, `_plan_reasoning_budget` | Fallback budget planner still reads raw wording and chooses `delivery_contract/internal_reasoning/tool_first`. V3 wants -1s LLM loop thinking, not deterministic meaning routing. | Replace with bounded default budget + -1s output after V3 step 6. |
| 886-1042, 1609-1815 | goal contract / identity slot helpers | Marker-heavy identity/name/slot satisfaction can recreate heuristic ontology. | Keep only schema normalization; move fact satisfaction to 2b or -1s packet. |
| 1722-1784, 3305-3354, 4023-4085 | strategy builders that write `direct_answer_seed` or answer text | V3 §2-15 forbids code-authored answer text. | Convert to contract/tone labels only, or delete after phase_3 prompt handles wording. |
| 2147-2168, 3364-3417, 3705-4015, 5058-5128, 5741-5828 | raw-turn semantic classifiers (`social`, `creative`, `self_analysis`, `identity`, `persona`, `emotion`, story share, follow-up inheritance) | Code is still deciding user meaning from keywords. V3 §2-14 says meaning classification belongs to LLM. | Delete or demote to safety/activity signals only after -1s 4-slot schema exists. |
| 2462-2747 | fallback start-gate contract and fast gate | This is the old -1s heuristic core. It compiles intent/answer mode from raw input when LLM fails. | V3 step 6 replacement target: `s_thinking_packet` schema + LLM first, fallback only schema-safe `ambiguous`. |
| 2864-2889, 4775-5043, 6295-6372 | date/deictic/search keyword repair and deterministic query builders | Can turn raw user wording into tool queries, violating -1a authority if used outside explicit tool planning. | Keep explicit tool expression parsing only; remove deterministic query invention. |
| 4673-4704 | `_rescue_answer_not_ready_decision` | Legacy answer-not-ready rescue vocabulary can re-open old loop behavior. | Fold into V3 119 `rescue_handoff_packet`; no user-facing/internal slot leaks. |
| 5815, 6004, 6032, 6055, 6769 | `_previous_*` aliases and reassignment wrappers | Monkey-patch compatibility obscures true call path. | Delete after tests import the final function paths directly. |
| 6766 | `_classify_requested_assistant_move` | Compatibility no-op from old request-intent system. | Delete after remaining tests stop asserting compatibility behavior. |

### V3 Wiring Mismatches To Track

| Area | Current state | V3 target | Blocking step |
| --- | --- | --- | --- |
| -1b | The old pre-delivery `-1b_auditor` node is gone. Normal phase 3 delivery passes through `delivery_review`, whose primary path is now an LLM reviewer constrained to `DeliveryReview.v1`; deterministic speaker guard remains fallback/hard safety. | Post-phase3 `delivery_review` is the only live -1b position. | V3 §10 steps 7C/7D complete. |
| -1s | Current start gate now emits `s_thinking_packet`, but still keeps `start_gate_review/start_gate_switches` compatibility and fallback contracts. | `s_thinking_packet` becomes the primary -1s packet; old start-gate compatibility surfaces shrink behind it. | V3 §10 step 6 complete; cleanup continues in later passes. |
| 119 | Rescue now emits `rescue_handoff_packet` and preserves accepted evidences/FieldMemo facts while separating rejected candidates. | 119 preserves known facts and hands phase_3 a natural-language boundary. | V3 §10 step 8 complete; later refine tone/LLM handoff if needed. |
| phase_3 | Some helpers still prepare seeds/contracts in code. | phase_3 should render from contracts/facts; code must not write answer text. | V3 §10 steps 6-9. |

## V3 §10 Step 7 — Readiness / -1b Relocation

Inventory date: 2026-05-01.

Goal: move -1b to the V3 role, which is answer review after phase_3.
Status after 7C: the old pre-delivery `-1b_auditor` node has been removed from
the live graph. `-1s` owns cycle routing, `-1a` owns planning/tool requests, and
`delivery_review` is the only live -1b-style review point.

### Current Graph Reality

```text
START
  -> -1s_start_gate
       -> route_after_s_thinking
          -> phase_3 | -1a_thinker | phase_119

-1a_thinker
  -> route_after_strategist
       -> 0_supervisor | -1s_start_gate | phase_119

0_supervisor
  -> phase_1 | phase_3 | phase_2a | -1a_thinker | -1s_start_gate | phase_119

phase_1 -> phase_2a -> phase_2 -> -1s_start_gate
warroom_deliberator -> -1s_start_gate
phase_119 -> phase_3

phase_3
  -> delivery_review
       -> END when delivery_review approves
       -> -1a_thinker when delivery_review remands for planning
       -> -1s_start_gate when delivery_review remands to the start contract
       -> phase_119 when delivery_review requests rescue
```

Important consequence after 7C: phase 2 and WarRoom no longer return to a
pre-delivery auditor. They return to `-1s_start_gate`, which reviews the compact
cycle packet/history and chooses delivery, planning, or 119.

### Old `Core.pipeline.readiness` Disposition

| Duty | Current location | V3 owner | Migration decision |
| --- | --- | --- | --- |
| Typed readiness alias helpers | `Core.readiness` | compatibility/runtime | Kept because delivery-payload and routing tests still import the typed helper API. |
| Strategist tool-request execution handoff | old `run_phase_minus_1b_auditor` branch | `route_after_strategist` + `0_supervisor` | Migrated. `0_supervisor` now consumes executable `strategist_output.tool_request` directly. |
| Strategy arbitration / grounded guard before delivery | old readiness node | `-1s` loop review and 2b analysis flags | Removed from live graph. `-1s` now re-enters after 2b and can deliver when analysis is complete. |
| `answer_not_ready` rescue | old readiness finalizer | `phase_119` + `rescue_handoff_packet` | Replaced by V3 step 8 rescue handoff. |
| Phase3 remand handling | old readiness speaker branch | `delivery_review` | Migrated. Post-phase3 review owns approve/remand/119 decisions. |
| LLM auditor deciding phase_3/tool/planning | `Core.pipeline.readiness` | removed | Deleted with `Core.pipeline.readiness.py`; no live pre-delivery LLM auditor remains. |

### Completed 7C Changes

1. Removed `-1b_auditor` and `-1b_lite_auditor` graph registration.
2. Removed `Core.nodes.phase_minus_1b_auditor` and
   `phase_minus_1b_lite_auditor` wrappers.
3. Removed `Core.speaker_guards.phase_minus_1b_auditor_with_speaker_guard`.
4. Deleted `Core.pipeline.readiness.py`.
5. Rewired `phase_2 -> -1s_start_gate` and
   `warroom_deliberator -> -1s_start_gate`.
6. Added `route_after_strategist` so -1a tool requests go straight to
   `0_supervisor`.
7. Added delivery-review rejection counting with a 3-remand 119 escalation
   guard.

### Compatibility Left Intentionally

- `Core.readiness` remains as typed readiness-contract compatibility.
- `Core.graph.route_audit_result_v2` remains for legacy tests and fallback
  packets, but it is not a live graph owner in the normal V3 route.
- `delivery_review` now calls the LLM reviewer first. The deterministic
  speaker guard remains as fallback and hard blocker for obvious internal-report
  leaks.

## State Buckets

`Core.state.AnimaState` is a broad shared state object. These buckets are useful
for ownership decisions:

- Runtime inputs:
  - `user_input`
  - `current_time`
  - `time_gap`
  - `recent_context`
  - `global_tolerance`
  - `user_state`
  - `user_char`
  - `songryeon_thoughts`
  - `tactical_briefing`
  - `biolink_status`
- Short memory / context:
  - `working_memory`
  - `evidence_ledger`
  - `tool_carryover`
  - `used_sources`
- Planning and readiness:
  - `start_gate_review`
  - `start_gate_switches`
  - `operation_plan`
  - `reasoning_plan`
  - `reasoning_budget`
  - `readiness_decision`
  - `progress_markers`
  - `strategist_output`
  - `strategist_goal`
  - `normalized_goal` (one-season compatibility alias for `strategist_goal`)
  - `auditor_instruction`
  - `auditor_decision`
  - `strategy_audit`
- Deliberation:
  - `reasoning_board`
  - `war_room`
  - `war_room_output`
  - `critic_lens_packet`
  - `strategist_objection_packet`
- Execution:
  - `supervisor_instructions`
  - `execution_status`
  - `execution_block_reason`
  - `execution_trace`
  - `executed_actions`
  - `tool_result_cache`
  - `search_results`
  - `raw_read_report`
- Judging and delivery:
  - `analysis_report`
  - `rescue_handoff_packet`
  - `response_strategy`
  - `phase3_delivery_packet`
  - `speaker_review`
  - `delivery_status`
  - `delivery_review`
  - `delivery_review_context`
  - `delivery_review_rejections`
- LangGraph plumbing:
  - `loop_count`
  - `messages`
  - `thought_logs`
  - `ops_decision`
  - `self_correction_memo`

Risk: this state is convenient but too flat. Later refactors should split the
implementation, not the public TypedDict, until graph stability is proven.

## Tool Flow

Live registry:

```text
Core.tools.available_tools
  -> tool_search_field_memos
  -> tool_search_memory
  -> tool_read_full_diary
  -> tool_read_artifact
  -> tool_scroll_chat_log
  -> tool_pass_to_phase_3
  -> tool_scan_db_schema
  -> tool_call_119_rescue
```

Implementation boundary:

```text
Core.tools
  -> Core.field_memo.search_field_memos
  -> Core.adapters.neo4j_memory
  -> Core.adapters.artifacts

tools.toolbox
  -> legacy compatibility facade only
```

Current status:

- live graph code no longer depends on `tools.toolbox`
- tests still import `tools.toolbox` to verify compatibility
- night/reflection helper tools now use `Core.adapters`

## Memory Flow

Post-turn memory production:

```text
final_state + user_input + final_answer
  -> MemoryBuffer.commit_turn_state
      -> WorkingMemoryWriter LLM
      -> normalized working memory snapshot
  -> canonical turn record in main.py
      -> dream_record
      -> turn_process
      -> phase_snapshots
  -> FieldMemoWriter LLM
      -> durable memo candidate only if verified facts exist
      -> branch_path defaults to Inbox/unclassified
      -> proposed_branch_path is only a hint
  -> InferenceBuffer.save_dream_to_db
      -> MySQL backup
      -> Neo4j Dream
      -> Neo4j TurnProcess
      -> Neo4j PhaseSnapshot
  -> persist_field_memo
      -> Neo4j FieldMemo
  -> link used_sources to Dream
  -> cleanup_turn_lived_fields
      -> reset turn-lived graph artifacts after persistence
```

Important current design wins:

- WorkingMemoryWriter exists and is the intended short-term meaning writer.
- FieldMemoWriter exists and is separate from WorkingMemoryWriter.
- WorkingMemory durable fact candidates are advisory only.
- FieldMemo known facts must come from verified candidate facts.
- New FieldMemo branch status is pending by default.
- Layered/Branch office generation has official memo filters.
- `main.py` and `InferenceBuffer` now run durable-memory payloads through the
  shared `Core.memory.memory_sanitizer` boundary before Dream/TurnProcess/
  PhaseSnapshot persistence.
- Dream/TurnProcess no longer persist `active_task`, `active_offer`, or
  `requested_move` as durable meaning fields. Those remain short-term writer
  material or runtime trace only.

Remaining risk:

- `MemoryBuffer` still contains older implementations plus later monkey-patch
  assignments to v3/v4 functions.
- PhaseSnapshot still stores phase activity metadata. Its text is sanitized,
  but the night loop must continue treating it as process telemetry, not user
  memory.
- `main.py` and `inference_buffer.py` have mojibake in live strings/comments,
  which makes audits harder.

## Night Loop

`Core.midnight_reflection.DreamWeaver` owns the large night pipeline. It reads
Dream / TurnProcess / PhaseSnapshot evidence, generates SecondDream records,
and persists:

- strategy council assets
- route policies
- tool doctrines
- tactical thoughts
- REM governor state
- branch growth assets
- layered memos / branch offices

Current risk:

- This file is still a god-file, though REMGovernor, StrategyCouncil, REMPlan,
  and Phase10 policy/doctrine compilation have now been split into
  `Core.midnight.*` department modules as the first V4 Phase 0 night-government
  boundary.
- It consumes many memory and policy assets.
- It should be refactored after the field loop and memory writer boundaries are
  stable.

## Current Package Boundaries

Existing packages:

```text
Core/
  adapters/
    artifacts.py
    neo4j_connection.py
    neo4j_memory.py
    night_queries.py
    seed_files.py
    web_search.py
  warroom/
    contracts.py
    deliberator.py
    output.py
    state.py
  pipeline/
    __init__.py
    contracts.py
    delivery.py
    delivery_packets.py
    fact_judge.py
    packets.py
    plans.py
    reader.py
    rescue.py
    start_gate.py
    strategy.py
    supervisor.py
    tool_execution.py
  memory/
    __init__.py
    field_memo_writer.py
    memory_contracts.py
    memory_sanitizer.py
    working_memory_writer.py
  midnight/
    __init__.py
    policy_doctrine.py
    rem_governor.py
    rem_plan.py
    strategy_council.py
  runtime/
    __init__.py
    cleanup.py
    context_packet.py
    runtime_profile.py
```

Recommended next packages:

```text
Core/pipeline/
  __init__.py
  contracts.py
  packets.py
  delivery_packets.py
  start_gate.py
  strategy.py
  supervisor.py
  tool_execution.py
  reader.py
  fact_judge.py
  delivery.py
  plans.py
  rescue.py

Core/memory/
  __init__.py
  working_memory_writer.py
  field_memo_writer.py
  memory_contracts.py
  memory_sanitizer.py
  # current status: writer prompt/normalization boundaries exist;
  # MemoryBuffer and FieldMemo delegate writer calls here while keeping
  # persistence/compatibility wrappers in their legacy modules

Core/runtime/
  __init__.py
  runtime_profile.py
  context_packet.py
  cleanup.py
  # current status: runtime profile/context/cleanup import boundary exists;
  # self kernel is deferred to a later identity reform
```

## Refactor Order

### Pass 1: low-risk `Core.nodes` helper extraction

Do not move graph public node functions yet. Move pure helper groups first:

1. start gate contract helpers
2. readiness/status helpers
3. tool instruction parsing / result cache helpers
4. delivery packet helpers
5. clean failure/rescue helpers

Keep compatibility imports in `Core.nodes`.

### Pass 2: node implementation extraction

Move internals while keeping public wrappers:

```python
def phase_1_searcher(state):
    return run_phase_1_searcher(state)
```

Move in this order:

1. `phase_1_searcher`
2. `phase_0_supervisor`
3. `phase_119_rescue`
4. `phase_3_validator`
5. `phase_2a_reader`
6. `phase_2_analyzer`
7. `phase_minus_1s_start_gate`
8. `phase_minus_1a_thinker`
9. `phase_delivery_review`

The old pre-delivery `phase_minus_1b_*` wrappers are gone after V3 §10 단계 7C.
Future extraction work should focus on wrapper shrinkage, not reviving the old
readiness node.

### Pass 3: memory package extraction

Extract from `Core.memory_buffer` and `Core.field_memo`:

1. WorkingMemory writer prompt and schema normalization. (done)
2. FieldMemo writer prompt and decision normalization. (done)
3. Memory sanitizers / internal-text blockers. (done)
4. FieldMemo official/pending branch helpers. (partially still in `Core.field_memo`)

Avoid changing persistence schemas in this pass.

### Pass 4: runtime profile/context

Create a small runtime activity/context packet and inject it into:

- start gate
- strategist
- auditor
- fact judge
- delivery
- working memory writer
- field memo writer

This should not be a DB recall mechanism or identity source. It is the minimal
runtime-observation layer. Self-kernel/identity injection is deferred.

### Pass 5: night loop split

Only after field/memory boundaries are stable:

```text
Core/night/
  reflection_graph.py
  phase7_audit.py
  phase8_actions.py
  phase8_review.py
  phase9_persistence.py
  branch_growth.py
  policy_assets.py
```

## Verification Policy

Each pass should end with:

```text
python -B -m unittest discover -s tests
```

For pure documentation changes, AST check is enough:

```text
python -B -m py_compile Core/graph.py Core/nodes.py Core/tools.py main.py
```

## Immediate Next Move

Completed first coding passes:

1. create `Core/pipeline/`
2. move phase 1 mechanical tool execution into `Core.pipeline.tool_execution`
3. keep `phase_1_searcher` public wrapper in `Core.nodes`
4. move phase 0 supervisor execution preparation into `Core.pipeline.supervisor`
5. keep `phase_0_supervisor` public wrapper in `Core.nodes`
6. move phase 119 clean rescue preparation into `Core.pipeline.rescue`
7. keep `phase_119_rescue` public wrapper in `Core.nodes`
8. move phase 3 final delivery into `Core.pipeline.delivery`
9. keep `phase_3_validator` public wrapper in `Core.nodes`
10. move phase 2a raw-source reading into `Core.pipeline.reader`
11. keep `phase_2a_reader` public wrapper in `Core.nodes`
12. move phase 2b fact judging into `Core.pipeline.fact_judge`
13. keep `phase_2_analyzer` public wrapper in `Core.nodes`
14. move phase -1s thin start gate into `Core.pipeline.start_gate`
15. keep `phase_minus_1s_start_gate` public wrapper in `Core.nodes`
16. move phase -1a strategist into `Core.pipeline.strategy`
17. keep `_previous_phase_minus_1a_thinker` and `phase_minus_1a_thinker` public compatibility in `Core.nodes`
18. move pipeline Pydantic contracts into `Core.pipeline.contracts`
19. keep compatibility imports/aliases in `Core.nodes`
20. move source relay/raw-read packet helpers into `Core.pipeline.packets`
21. keep compatibility imports/aliases in `Core.nodes`
22. run full tests
23. move prompt serialization helpers into `Core.pipeline.packets`
24. keep compatibility imports/aliases in `Core.nodes`
25. run full tests
26. move operation/action/goal normalization helpers into `Core.pipeline.plans`
27. keep compatibility imports/aliases in `Core.nodes`
28. run full tests
29. move strategist/reasoning-board packet helpers into `Core.pipeline.packets`
30. keep compatibility imports/aliases in `Core.nodes`
31. run full tests
32. move judge-speaker delivery packet assembly into `Core.pipeline.delivery_packets`
33. keep compatibility imports/aliases in `Core.nodes`
34. run full tests
35. delete old pre-delivery `Core.pipeline.readiness` and remove
    `phase_minus_1b_*` wrappers from `Core.nodes`
36. rewire `phase_2` and WarRoom back to `-1s_start_gate`
37. run full tests

Next structural pass:

1. V3 §10 implementation is complete enough to close this reform round after
   Jeonghu approval.
2. Continue deleting `Core.nodes` compatibility wrappers that no tests import.
3. Keep shrinking prompt projections and state surfaces around phase 3,
   delivery review, and -1s loop history.
4. run full tests after each graph-routing or prompt-contract change.

The public graph node implementations are mostly extracted, but `Core.nodes` is
still a large compatibility and dependency-wiring god-file (6,922 lines as of
2026-05-01 after 7C). The packet serialization layer is mostly isolated, the plan
normalization layer is isolated, and the judge-speaker delivery packet assembly
now has its own boundary. `Core/runtime` is installed for V3 §10 단계 2,
`Core/memory` is strengthened for V3 §10 단계 3, `nodes.py` inventory is
recorded for V3 §10 단계 4, InferenceBuffer durable-memory contamination
control is complete for V3 §10 단계 5, -1s now emits the V3
`s_thinking_packet` for 단계 6, and phase 3 now exits through the V3
`delivery_review` gate for 단계 7B. Phase 119 now emits a V3
`rescue_handoff_packet` for 단계 8. Destructive cleanup in `nodes.py` should
still be done wrapper-by-wrapper with tests, but the old pre-delivery -1b
auditor has been removed from live wiring in 단계 7C.

## Current Purge Log

> 35번부터는 V3 §10 시행 순서대로 등재.

Recent thin-controller cleanup:

1. Operation contracts no longer classify raw user wording into identity,
   feature, recent-dialogue, or personal-history target scopes. They record
   selected tools, completed analysis, or existing response strategy only.
2. Phase -1b readiness no longer owns fallback memory search. Memory recall
   must come from a start-gate recall contract, a strategist tool request, or an
   explicit tool path.
3. Grounding and memory recall are split. `requires_grounding` alone does not
   authorize FieldMemo/DB recall.
4. The grounded phase3 guard honors state-level grounded contracts over
   delivery-payload reclassification from raw user text, and exits through clean
   failure after an unproductive non-memory planning pass.
5. Phase -1b readiness no longer reclassifies requested moves from raw user
   wording. It reads the start-gate `needs_planning` contract.
6. `_derive_operation_plan` no longer routes from raw words like "investigate"
   or recent-dialogue markers. Source lanes come from executable tools or
   operation contracts.
7. Deterministic findings-first response-strategy rewriting is retired.
   Retrieved facts are no longer turned into a hardcoded "Retrieved findings"
   answer seed by a raw intent classifier.
8. Phase3 lane assembly and phase 2a reader no longer call
   `classify_requested_assistant_move`. The classifier remains only as a
   compatibility helper, not a field-loop routing authority.
9. WarRoom operating-contract derivation no longer imports or calls
   `classify_requested_assistant_move`. WarRoom freedom is now derived from
   existing action-plan and response-strategy contracts, not raw user wording.
10. WorkingMemory no longer upgrades requested-move classifier output into
    `requested_assistant_move`, `initiative_requested`, task reset, or
    conversation mode. The compatibility hook now returns an empty signal.
11. Dead supervisor policy scoring helpers and the unused situation-frame
    classifier map were removed instead of being moved into another module.
12. FieldMemo consumption now treats `field_memo_judgments` from phase 2b as
    the primary acceptance authority. If phase 2b provides no memo judgment,
    FieldMemo items stay retrieval candidates and are not auto-promoted to
    usable facts by lexical overlap or memo-kind heuristics.
13. Unused FieldMemo consumer helpers (`field_memo_goal_lane`,
    `field_memo_has_any`, `field_memo_query_overlap`) were removed instead of
    being kept as compatibility routing hooks.
14. WorkingMemory v4 no longer copies LLM-writer semantic fields into
    `dialogue_state.active_task`. Writer-authored meaning stays under
    `memory_writer` (`active_topic`, `unresolved_user_request`,
    `assistant_obligation_next_turn`), while runtime dialogue state keeps the
    compatibility field blank unless a future code-tracked activity signal
    explicitly owns it.
15. Continuation helpers can still read LLM-authored short-term obligations
    from `memory_writer`, so phase3/follow-up context survives without storing
    that semantic text as a durable `active_task`.
16. Goal contracts no longer predeclare broad system/self-analysis slots from
    raw keyword markers. Those turns keep output intent and success criteria,
    but leave `slot_to_fill` blank unless a narrow identity or memory-referent
    contract is actually needed.
17. OMORI/story turns remain public/parametric by default. The unreachable
    legacy branch that tried to force character identity/fictionality/relation
    slots was removed.
18. Contract-status packets now expose user-facing missing-item labels instead
    of leaking raw internal slot names such as `memory.referent_fact` into
    clean-failure copy.
19. Fallback start-gate contracts no longer convert every grounded review into
    memory recall. Non-memory grounded review keeps `requires_grounding=True`
    but uses generic task/tool planning rather than `grounded_recall`.
20. Dead identity-parser definitions in `goal_contracts.py` were removed so the
    canonical parser is the only active definition.
21. FieldMemo answer brief generation was fully retired. FieldMemo review now
    forwards only accepted facts.
22. Mojibake search-expression cleanup in `request_intents_v4` was replaced
    with clean UTF-8/ASCII quote and search-term extraction.
23. Dead no-op role-fidelity and retired total-war helper stubs were removed
    from `Core.nodes` instead of being carried forward as fake safety layers.
24. WorkingMemory v2/v3 legacy builders, raw `active_task` derivation, requested
    move classifiers, and monkey-patched compatibility builders were removed.
    The v4 LLM writer path is now the sole active WorkingMemory builder.
25. Phase -1b readiness no longer calls preferred-decision compatibility stubs
    that always returned `None`. It now either honors real contracts/tool plans,
    asks the structured auditor, or takes the explicit clean fallback path.
26. Supervisor policy bundle and branch-guided switchboard stubs were removed
    from `Core.nodes`. Night policy/branch data cannot enter the day loop
    through these private helpers.
27. Personal-history date/anchor tool-candidate heuristics that were already
    disconnected from active planning were removed rather than preserved as
    dead routing hints.
28. Preferred decision routers for analysis, verdict, operation plan, and
    strategist output were deleted. Tests now assert that those deterministic
    routing hooks are absent.
29. `field_memo_answer_brief` was removed from the active schema and delivery
    packets. FieldMemo delivery now depends on `usable_field_memo_facts`,
    `accepted_facts`, contract status, and phase 2b judgment.
30. The mojibake state optimization checklist was rewritten as a clean
    Korean/English maintenance checklist for state projection, turn-lived
    cleanup, WorkingMemory writer, FieldMemo writer, and readiness vocabulary.
31. Phase -1a now receives `project_state_for_strategist`, a bounded projection
    of the graph state. Bulk tool caches, raw messages, and phase3 delivery
    packets stay out of strategist prompts.
32. `Core.state` now defines explicit long-lived and turn-lived state buckets
    plus `cleanup_turn_lived_fields`. The cleanup helper is a contract for the
    post-persistence boundary, not an automatic graph mutation.
33. `working_memory_packet_for_prompt` now forwards a compact WorkingMemory
    prompt packet. Raw `last_turn` transcripts and large writer/evidence lists
    are clipped before reaching -1b, 2b, WarRoom, or delivery prompts.
34. Raw-read, analysis, and source-relay prompt packets now share centralized
    compactors. Full source relay objects still feed normalization, but prompt
    text no longer receives unbounded source/report dumps.
35. The architecture map now distinguishes extracted graph node implementations
    from the still-large `Core.nodes` compatibility/wiring god-file. The system
    is not yet a fully thin controller.
36. `Core.runtime` now exists as a minimal boundary for runtime-profile,
    runtime-context, and turn-lived cleanup imports. Self-kernel/identity
    injection is explicitly deferred to a later reform.
37. `Core.memory` now exists as a minimal boundary for writer authority
    contracts and internal-text sanitizers. WorkingMemoryWriter and
    FieldMemoWriter extraction still remains.
38. `main.py` now calls `cleanup_turn_lived_fields` only after answer
    extraction, MemoryBuffer/FieldMemo/Dream/TurnProcess persistence,
    used-source welding, and FieldMemo persistence have consumed `final_state`.
39. Large `Core.nodes` inventory/purge now has a required constitution review
    gate: §0 one-line summary, §1 core five-node authority table, and §2
    forbidden list must be approved before using the constitution as a
    deletion/move classifier.
40. V3 §10 단계 2 completed for `Core.runtime`: the package contains
    `runtime_profile.py`, `context_packet.py`, and `cleanup.py`; no
    `self_kernel.py` exists. `context_packet.py` explicitly marks itself as the
    future -1s cumulative packet assembly boundary.
41. V3 §10 단계 3 completed for `Core.memory`: `working_memory_writer.py` now
    owns the WorkingMemoryWriter prompt, JSON normalization, evidence-fact
    extraction, and LLM call boundary; `field_memo_writer.py` now owns the
    FieldMemoWriter prompt and decision normalization. `MemoryBuffer` and
    `field_memo` delegate writer calls to these modules while keeping storage,
    retrieval, and compatibility monkey-patch points stable.
42. V3 §10 단계 4 completed as an inventory-only pass for `Core.nodes`.
    At inventory time, `Core.nodes` had 6,876 lines, 328 top-level declarations, and 11
    public graph wrappers. The inventory classifies public wrappers,
    already-extracted compatibility delegates, valid-but-misplaced code,
    purge candidates, and V3 wiring mismatches. No source deletion was
    performed in this step.
43. V3 §10 단계 5 completed for InferenceBuffer contamination control.
    `Core.memory.memory_sanitizer` now owns durable-memory text/trace
    sanitization, fixes marker matching case-sensitivity, and blanks dialogue
    control fields (`active_task`, `active_offer`, `requested_move`) before
    Dream/TurnProcess persistence. `main.py` and `InferenceBuffer` both use the
    shared sanitizer so user input/final answers are preserved while internal
    planning text, direct answer seeds, answer goals, and phase-summary leakage
    are filtered from durable memory payloads. Regression tests cover the
    boundary, and the full test suite passes (`157 OK`).
44. V3 §10 단계 6 completed for the -1s four-slot packet. `Core.state` now has
    `s_thinking_packet`, `Core.pipeline.contracts` declares the
    `SThinkingPacket` nested schema, and `Core.pipeline.start_gate` emits
    situation/loop/next_direction/routing_decision packets for both direct
    delivery and -1a planning paths. The packet is built only from existing
    start-gate contract/policy outputs, not raw-user keyword matching, and -1a
    receives it through the bounded strategist projection and prompt surface.
45. V3 §10 단계 7A completed as a readiness relocation inventory plus
    post-delivery contract scaffold. The graph inventory shows that normal
    `phase_3` delivery currently ends without -1b review, while the existing
    At 7A time, `-1b_auditor` still owned pre-delivery readiness, tool-plan validation,
    strategy arbitration, grounded-delivery guards, and phase3-remand handling.
    `Core.pipeline.contracts` now declares `DeliveryReview`, and
    `Core.pipeline.delivery_review` exposes `normalize_delivery_review`,
    `delivery_review_from_speaker_guard`, and `build_delivery_review_context`.
    The new contract can approve, remand to `-1a`/`-1s`, or request `119`; it
    cannot route to tools or author tool calls.
46. V3 §10 단계 7B completed for post-phase3 delivery-review wiring.
    `Core.state` now carries `delivery_review` and `delivery_review_context`,
    `Core.nodes.phase_delivery_review` wraps
    `Core.pipeline.delivery_review.run_phase3_delivery_review`, and
    `Core.graph` routes `phase_3 -> delivery_review -> END/-1a/-1s/119`.
    At 7B time, this first wired pass used the existing speaker guard as the
    deterministic hard signal; the LLM answer reviewer was activated later in
    7D. The old `-1b_auditor` remained in its pre-delivery
    readiness role until the later 7C removal pass. `DeliveryReview.v1` is
    aligned with V3 appendix C: `sos_119` is a verdict, not a `remand_target`.
    The full test suite passes (`166 OK` after step 8).
47. V3 §10 단계 8 completed for `rescue_handoff_packet`. `Core.state` now
    carries `rescue_handoff_packet`, `Core.pipeline.contracts` declares
    `RescueHandoffPacket`, and `Core.pipeline.rescue` no longer blanks
    `analysis_report.evidences` or `usable_field_memo_facts` wholesale.
    Phase 119 now separates `rejected_only` from preserved partial facts,
    forwards preserved evidences/FieldMemo facts through
    `response_strategy.must_include_facts`, and gives phase 3 a bounded
    `RESCUE_HANDOFF` contract without exposing trigger/path internals.
    `user_facing_label` is code-owned enum only (`검색 결과 부족`, `기억 못 찾음`,
    `질문이 모호함`, `재시도 필요`); phase 3 receives a policy to naturalize it
    rather than quote it. Targeted rescue tests pass (`2 OK`), and the full
    test suite passes (`166 OK`).
48. V3 §10 단계 9A completed for `strategist_goal` migration. `Core.state`
    now carries `strategist_goal` plus the one-season `normalized_goal`
    compatibility alias, `Core.pipeline.contracts` declares `StrategistGoal`,
    and -1a prompt/projection surfaces now name `strategist_goal` as the
    planner-owned goal contract. `Core.nodes._sanitize_strategist_goal_fields`
    writes both aliases from one normalized packet and keeps raw user wording
    out of `strategist_goal.user_goal_core`, `operation_plan.user_goal`, and
    `action_plan.current_step_goal` when the old path leaks it. Exact
    `normalized_goal` usage remains in the start-gate contract/tests as
    compatibility surface; the active -1a output path now emits top-level
    `strategist_goal` and `normalized_goal` aliases. Targeted strategist-goal
    tests pass (`17 OK`), and the full test suite passes (`172 OK`).
49. V3 §10 단계 9B completed for input packet dieting. `Core.pipeline.packets`
    now owns role-aware prompt projections for WorkingMemory, analysis reports,
    `s_thinking_packet`, and `rescue_handoff_packet`. -1a receives only
    strategist-relevant dialogue/evidence/memory-writer fields, -1b receives
    response contract plus turn summary, 2b receives evidence state, and
    phase 3 receives only short-term conversational obligations plus approved
    delivery/rescue facts. Full analysis/source objects remain available for
    normalization and provenance, but prompt paths use node-specific compactors.
    A large synthetic packet comparison showed approximate prompt-surface
    reductions of -87.9% (-1a), -60.9% (-1b), -12.0% (2b packet surface), and
    -92.5% (phase 3). Targeted packet tests pass, and the full test suite
    passes (`175 OK`).
50. V3 §10 단계 9C completed for node sys_prompt and contract slimming.
    `Core.prompt_builders` now provides answer-mode-specific phase 3 prompt
    builders for public knowledge, self-kernel, memory recall, current-turn
    grounding, simple continuation, and cautious minimal delivery. Phase 3 now
    receives a compact `Phase3PromptContract.v1` view instead of the full
    `SpeakerJudgeContract` policy ledger, while the full contract remains in
    state for code/provenance. -1a, -1b, and 2b prompts were reduced to compact
    five-rule task cards, `reasoning_board` prompt packets now have role-aware
    projections, and `Core.pipeline.delivery_review` received the bounded LLM
    reviewer prompt scaffold later activated by 7D. A synthetic
    phase 3 comparison showed about 75.5%-77.1% reduction versus the old
    hardcoded phase 3 prompt plus full contract surface. The full test suite
    passes (`178 OK`).
51. V3 §10 단계 6B completed for cumulative -1s context packets.
    `Core.runtime.context_packet` now owns `SThinkingHistory.v1` assembly:
    previous -1s `s_thinking_packet` outputs are compressed into
    `history_compact` rows (`cycle`, `domain`, `next_node`, `main_gap`,
    `brief_thought`) and paired with the current four-slot packet. `Core.state`
    now carries turn-lived `s_thinking_history`, and `Core.pipeline.start_gate`
    appends the previous -1s packet before each new start-gate LLM call without
    reading -1a plans, tool args, or answer text. The -1s prompt now receives
    compact history and has a six-rule card that tells it to avoid repeating the
    same broad direction/main gap when prior cycles stalled. Compact history
    measured about 41 tokens for N=1, 113 tokens for N=3, and 185 tokens for
    N=5. The full test suite passes (`180 OK`).
52. V3 §10 단계 7C completed for old pre-delivery -1b removal. `Core.graph` no
    longer registers `-1b_auditor` or `-1b_lite_auditor`, `Core.nodes` no
    longer exposes `phase_minus_1b_auditor` or `phase_minus_1b_lite_auditor`,
    and `Core.speaker_guards` no longer has
    `phase_minus_1b_auditor_with_speaker_guard`. `Core.pipeline.readiness.py`
    was deleted. Live cycle wiring is now `-1s -> -1a/phase_3/119`,
    `-1a -> 0_supervisor/-1s/119`, and
    `phase_1 -> phase_2a -> phase_2 -> -1s`; WarRoom also returns to `-1s`.
    `0_supervisor` can execute an explicit `strategist_output.tool_request`
    without an auditor instruction, and `delivery_review_rejections` is
    turn-lived with a three-remand escalation to 119. The full test suite
    passes (`183 OK`).
53. V3 §10 단계 7D completed for the post-phase3 LLM delivery reviewer.
    `Core.prompt_builders.build_delivery_review_sys_prompt` now provides a
    Gemma4-friendly five-rule -1b reviewer prompt, and
    `Core.pipeline.delivery_review.run_phase3_delivery_review` now calls an LLM
    through `with_structured_output(DeliveryReview)` before routing. The bounded
    `DeliveryReviewContext.v1` contains the final answer, compact
    `analysis_report` evidence, `response_strategy.must_include_facts`,
    `must_avoid_claims`, and rescue preserved facts; it deliberately excludes
    `s_thinking_packet`, full WorkingMemory, and full reasoning board. Invalid
    or failed structured output falls back to the deterministic speaker guard,
    while deterministic guard remands still block an accidental LLM approve.
    Regression tests cover approve, hallucination remand, required-fact
    omission remand, internal-workflow leak remand, `sos_119`, structured-output
    fallback, and the three-remand 119 counter. A synthetic reviewer prompt
    measured about 566 tokens (`chars/4` approximation). The full test suite
    passes (`189 OK`).
54. V4 Phase 0 시작 — midnight 분해 1차 completed for the StrategyCouncil
    department. `Core.midnight.strategy_council` now owns the extracted
    StrategyCouncil state builder, attention shortlist scoring, evidence-point
    collection, and related dedupe helpers. `Core.midnight_reflection.DreamWeaver`
    keeps same-name compatibility wrappers so graph node names and external
    imports remain stable. `Core.midnight_reflection.py` decreased from 5,330
    lines to 4,461 lines (-869), and the extracted module has 964 lines.
55. V4 Phase 0 midnight 분해 2차 completed for the REMPlan department.
    `Core.midnight.rem_plan` now owns REMPlan branch/topic/evidence helper
    extraction, `REMPlanSchema` construction, and branch-growth feedback
    attachment. `Core.midnight_reflection.DreamWeaver` keeps same-name
    compatibility wrappers for `_plan_branch_paths`, `_plan_topics`,
    `_plan_evidence_points`, `_build_rem_plan_from_rows`, and
    `_attach_branch_growth_feedback_to_rem_plan`. `Core.midnight_reflection.py`
    decreased from 4,461 lines to 4,269 lines (-192), and the extracted module
    has 226 lines.
56. V4 Phase 0 midnight 분해 3차 completed for the REMGovernor department.
    `Core.midnight.rem_governor` now owns REMGovernor root scanning,
    root-profile/root-inventory construction, policy inventory assembly,
    root-state Neo4j application, default/load/build/refresh governor state,
    and the branch-health/root-scope helper wrappers. `Core.midnight_reflection.DreamWeaver`
    keeps same-name compatibility wrappers so `node_rem_governor`, persistence
    helpers, StrategyCouncil, REMPlan, and branch-growth refresh paths keep the
    same call surface. `Core.midnight_reflection.py` decreased from 4,269 lines
    to 3,482 lines (-787), and the extracted module has 846 lines.
57. V4 Phase 0 midnight 분해 4차 completed for the Phase10Policies /
    PolicyDoctrine department. `Core.midnight.policy_doctrine` now owns tactic
    family blueprints, tactical-family inference, tactical-card normalization,
    RoutePolicy compilation, ToolDoctrine compilation, and the phase 10
    policy/doctrine bundle builder. `Core.midnight_reflection.DreamWeaver`
    keeps same-name compatibility wrappers, and `node_phase_10_policies` keeps
    the existing LangGraph node surface. `Core.midnight_reflection.py`
    decreased from 3,482 lines to 2,888 lines (-594), and the extracted module
    has 631 lines.
58. V4 Phase 0 B-track #0.5 fallback heuristic purge pass completed for the
    safest dead candidates in `Core.nodes`. The retired
    `_turn_needs_total_war_evidence` broad evidence guard and unused
    `_rescue_answer_not_ready_decision` clean-failure override were removed;
    active fallback parsers/planners remain inventoried because they are still
    schema/runtime safety fallbacks rather than confirmed dead code.
59. V4 Phase 0 B-track #0.6 compatibility shim purge completed.
    `_extract_operation_target_scope` had no runtime callers and was removed
    from `Core.nodes`; grep now reports zero references.
60. V4 Phase 0 B-track #0.7 normalized-goal alias cleanup pass completed for
    `Core.nodes`/`Core.pipeline.strategy` naming. The stale `legacy_goal`
    variable path was removed; the one-season `normalized_goal` state alias is
    still present pending the broader V4 schema migration.
61. V4 Phase 0 #R1 old midnight-government archive completed. The obsolete V3
    midnight god-file island was moved to `Core/_archive_v3_midnight/`,
    including `midnight_reflection.py`, the old governor/branch/strategy
    modules, and their night persistence dependencies. The archive README marks
    `rem_governor.py`, `midnight/strategy_council.py`, and
    `branch_architect.py` as meaning-axis revival candidates for the future V4
    government build. Post-move MD5 validation passed for all archived files;
    live grep shows only `Core.field_memo` old governor labels/helpers and a
    stale `tools.__init__` comment as #R2 cleanup targets. Contrary to the
    initial expectation, the full test suite still passes (`189 OK`).
62. V4 Phase 0 #R2 new midnight-government skeleton completed. `Core.midnight`
    is now the live V4 package entrypoint with `run_night()` and
    `python -m Core.midnight` support; the command intentionally raises
    `NotImplementedError("v4 미작성, R3~R6에서 채움")` until R3-R6 fill the
    departments. New `recall`, `present`, `past`, and `future` subpackages
    provide 12 callable stubs for recent/random recall, present summarizer /
    problem-raiser / fact-checker, CoreEgo/local past assembly, and future
    witness / field critic / decision-maker roles. Old live governor writes in
    `Core.field_memo` now use `night_government_v1`, `TimeBranch`, and
    `NightGovernmentState`; the old `midnight_reflection` entrypoint comment in
    `tools.__init__` was updated. Live grep outside the archive reports zero
    `midnight_reflection`, `rem_governor_v1`, `GovernorBranch`,
    `REMGovernorState`, or `apply_local_reports_to_governor` references. The
    full test suite passes (`189 OK`).
63. V4 Phase 0 #R3 future department body completed. The future department now
    instantiates the V3 trio pattern as witness -> field critic -> decision
    maker: `build_future_witness` compacts past assembly thought plus prior
    future decision thought, `build_future_field_critique` raises present gaps
    and invokes the random-recall interface once, and `make_future_decision`
    approves a DreamHint advisory or remands to the field critic. The random
    recall interface moved to `Core.midnight.recall.random` as a package and
    exposes `RandomRecallResult` plus an empty R6 `invoke()` stub. DreamHint
    persistence now writes `DreamHint` nodes with mandatory `source_persona`,
    `TimeBranch` guidance, past-thought citation refs, and recall-result refs.
    `run_future_assembly` provides the R3 future-package entrypoint while
    `python -m Core.midnight` still raises the expected R3-R6
    `NotImplementedError`. New regression tests cover the future node cycle,
    DreamHint persistence, missing `source_persona` rejection, random recall
    stub behavior, and live-code absence of old RoutePolicy/ToolDoctrine. The
    full test suite passes (`196 OK`).
64. V4 Phase 0 B-track #0.5 fallback heuristic audit/purge completed. The live
    `Core.nodes` fallback inventory found one safe dead compatibility wrapper:
    `_fallback_strategist_output`, which only forwarded to
    `_base_fallback_strategist_output`; -1a now injects the base function
    directly and the wrapper was removed. The remaining `nodes.py` fallback
    surfaces are still active schema/runtime safety fallbacks
    (`_fallback_start_gate_turn_contract`, raw-reader fallback packets,
    `_base_fallback_strategist_output`, response strategy fallback, reasoning
    budget fallback, and WarRoom fallback adapter), so they are not safe to
    purge under #0.5 without a separate V4 authority decision. `Core.nodes.py`
    decreased from 6,876 to 6,857 lines. The full test suite passes
    (`196 OK`).
65. V4 Phase 0 #R4 past department body completed. `Core.midnight.past` now
    defines `PastAssemblyOutput`, CoreEgo designer/self/approval functions, a
    local-council assembly function, and graph persistence helpers for the R4
    time-axis government shape. `assemble_coreego` emits separated
    rationale/importance data in `change_proposal`, `approve_coreego` runs the
    first-pass majority election contract and raises the expected
    `NotImplementedError("비상계엄령 v1.7 빵구")` after three reruns, and
    `build_future_witness` accepts the new `PastAssemblyOutput`. Past
    persistence helpers cover the approved shared-accord cleanup Cypher,
    `TimeBranch` year/month/day hierarchy plus `NEXT_SIBLING` sliding windows,
    `ChangeRationale` / `ChangeImportance` split writes, and `Election` nodes.
    Live Neo4j cleanup was not executed in this code pass; manual scripts
    `tools/r4_cleanup_shared_accord.cypher` and `tools/r4_rollback.cypher`
    document the forward and rollback graph operations. New tests cover
    CoreEgo/local past outputs, shared-accord cleanup verification,
    TimeBranch windows, separated rationale/importance writes, pass/fail/3-rerun
    election behavior, and Election persistence. The full test suite passes
    (`204 OK`).
66. V4 Phase 0 #R5 present department body completed. `Core.midnight.present`
    now defines `PresentSecondDreamOutput` plus summary/problem/audit contracts,
    fills the three present seats (`summarize_day_memory`,
    `raise_present_problems`, `check_present_facts`), and persists filled
    `SecondDream` nodes with mandatory `source_persona`, `TimeBranch` guidance,
    source `Dream` citations through `AUDITED_FROM`, and `SupplyTopic` links
    through `CONTAINS_TOPIC`. The R6 recent-recall interface moved to
    `Core.midnight.recall.recent` as a package with empty stubs for
    `prepare_empty_seconddreams`, `formatter.format`, and `auditor.audit`.
    Future-department input now uses `PresentSecondDreamOutput` instead of the
    removed `PresentSecondDreamMockInput`, and regression tests assert the mock
    name is absent from live code. Live Neo4j writes were not executed in this
    code pass; `tools/r5_rollback.cypher` documents the rollback shape for
    future manual graph runs. New tests cover the present three-node chain,
    `source_persona` rejection, SecondDream persistence, `AUDITED_FROM` /
    `CONTAINS_TOPIC` relations, R6 recall stubs, and future integration. The
    full test suite passes (`212 OK`).
67. V4 Phase 0 #R6 recall department body completed. `Core.midnight.recall`
    now has executable recent and random recall departments: recent recall
    fetches or accepts unaudited `Dream` rows, prepares day-level empty
    `SecondDream` shells, formats source packets, and audits them with
    mandatory `source_persona`; random recall accepts injected or DB-fetched
    Diary/SecondDream/graph candidates, ranks them by cosine similarity, applies
    persona filtering, and emits formatter/auditor packets with persona maps.
    The R5 mock names (`EmptySecondDreamMock`, `RecallFormatterOutputMock`,
    `RecallAuditorOutputMock`) were removed from live code, and
    `python -m Core.midnight` now completes a dry-run night cycle instead of
    raising the R3-R6 `NotImplementedError`. New tests cover recent recall,
    random cosine ranking, persona rejection, the recall -> present -> past ->
    future chain, and the live command path.
68. V4 Phase 0 #R7 integration/migration pass completed. `run_night()` now
    accepts a live `graph_session` plus `persist=True` and can read real
    unaudited Dream rows, run random recall against Diary/SecondDream/graph
    candidates, persist SecondDream, ChangeProposal, Election, and DreamHint
    packets, and return a graph operation log. Destructive shared-accord
    cleanup remains opt-in via `cleanup_shared_accord_now`; it is not executed
    during the default night cycle. DreamHint persistence now includes
    `archive_at`, active DreamHint reads use lazy `archive_at`/`expires_at`
    filters, and the live field-loop tool registry exposes
    `tool_search_dreamhints` for active advisory lookup. SupplyTopic writes now
    reserve embedding/embedding_model fields for the v1.7 embedding pass.
    R7 migration, rollback, verify, and backup-first PowerShell scripts were
    added under `tools/`; live Neo4j migration was not executed by Codex in this
    code pass. New tests cover live-session integration, non-default accord
    cleanup safety, migration script presence, active DreamHint filtering, and
    the field-loop DreamHint tool.
69. V4 Phase 0 #R8 semantic-government fork completed. `Core.midnight.semantic`
    now provides the semantic-axis government entrypoint
    (`python -m Core.midnight.semantic`) plus CoreEgo designer/self/approver
    seats, local semantic councils, present/past/future semantic seats, and
    graph persistence for `SemanticBranch`, `ConceptCluster`, and
    `TimeBucket` bridges. The revived archive ideas are explicitly limited to
    root inventory, attention/scope selection, and branch blueprint concepts;
    old RoutePolicy/ToolDoctrine routing remains retired. Random recall now
    supports `axis="semantic"` by searching SemanticBranch/ConceptCluster
    candidates, while `axis="time"` remains unchanged. `run_night()` gained
    `include_semantic=True` to run the time-axis chain and then the semantic
    fork. ChangeProposal, ChangeRationale, and ChangeImportance now carry an
    `axis` field (`time` or `semantic`) so the shared CoreEgo can distinguish
    time-axis and semantic-axis proposals. New tests cover semantic assembly,
    SemanticBranch/ConceptCluster persistence, TimeBucket bridging, semantic
    recall, shared CoreEgo axis proposals, and `run_night(include_semantic=True)`.
70. **V4 Phase 0 F트랙 #F1: 현장 자동 advisory 다리 V3 TacticalThought → V4 DreamHint 교체** completed.
    `Core.adapters.night_queries.recent_tactical_briefing` keeps the legacy
    function name, signature, and `tactical_briefing` state surface, but its
    source is now active `DreamHint` advisories via the shared
    `fetch_active_dreamhints` query boundary. The automatic field-loop advisory
    channel now reads `hint_text`, `branch_path`, and `source_persona` from
    non-archived, non-expired DreamHint records instead of the retired
    `TacticalThought` label. `search_tactics` / `TacticCard` compatibility was
    left untouched as ordered. New regression tests cover active DreamHint
    output, empty active advisory output, and archive/expiry filter presence.
71. **V4 Phase 0 F트랙 #F2: -1s ThinkingHandoff.v1 + -1b fact_cells 대조 채널 + remand_guidance schema** completed.
    The live -1s packet is now `ThinkingHandoff.v1` with the approved 9-field
    handoff surface, while `SThinkingPacket.v1` remains as one-season legacy
    compatibility input. -1s may receive compact `analysis_report` material and
    the graph router now prefers top-level `next_node`. `fact_cells` projection
    was normalized into the V4 `fact_id` / `extracted_fact` / source surface and
    `delivery_review` now receives `fact_cells_for_review`. `DeliveryReview.v1`
    gained `reason_type`, `evidence_refs`, and `delta`, with code-owned
    `reason_type -> remand_target` mapping. New regression tests cover the
    ThinkingHandoff builder/compat path, -1s analysis input, fact-cell review
    projection, delivery-review reason routing, and hallucination remand flow.
72. **V4 Phase 0 F트랙 #F3: -1a 입력 축소 + tactical_briefing 채널 이동 + -1a fact_id 인용 채널** completed.
    `project_state_for_strategist` no longer projects `analysis_report`,
    `raw_read_report`, the full `reasoning_board`, or `tactical_briefing`.
    The strategist now receives `ThinkingHandoff.v1` as the primary case state
    plus `fact_cells_for_strategist` using the V4 `fact_id` / `extracted_fact`
    projection. `build_phase_minus_1a_prompt` dropped the old diagnostic/source
    blocks and added a `[fact_cells]` block with rules that forbid -1a fact
    re-judgment. `tactical_briefing` is now passed to -1s only as advisory
    context for the start-gate contract, while the state key and adapter names
    remain unchanged for one-season compatibility. New tests cover strategist
    input surface, prompt blocks, -1s tactical briefing input, and ThinkingHandoff
    strategist integration.
73. **V4 Phase 0 F트랙 #F4: 0차 LLM 일반 흐름화 + -1a tool_request 권한 이동** completed.
    `StrategistReasoningOutput` no longer exposes `tool_request`; the
    `StrategistToolRequest` model and `ensure_tool_request_in_strategist_payload`
    helper remain only as one-season deprecated read-side compatibility. -1a now
    writes operation intent and delivery readiness, while phase 0 owns exact tool
    name, args, and query generation. `run_phase_0_supervisor` no longer shortcuts
    `strategist_output.tool_request`; it uses the LLM path as the general flow
    after direct structured/auditor compatibility branches, with prompt inputs for
    `operation_contract`, compact `fact_cells`, and ThinkingHandoff missing items.
    `route_after_strategist` now sends non-deliverable plans to `0_supervisor`
    instead of looping back to -1s, while legacy `tool_request` packets still route
    to phase 0 with a deprecated log. New tests cover strategist schema/no-op
    compatibility, supervisor general-flow prompts, and graph routing. Full tests:
    `294 OK`.
