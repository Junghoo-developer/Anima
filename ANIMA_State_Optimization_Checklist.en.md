*[한국어](ANIMA_State_Optimization_Checklist.md) | [English](ANIMA_State_Optimization_Checklist.en.md)*

# ANIMA State Optimization Checklist

> Document status: LIVE STATUS / TODO.
> Update this after state projection, prompt compacting, turn-lived cleanup, or
> memory contamination-control work.

Created: 2026-04-30 | Last updated: 2026-05-09 (V4 §1-A LIVE)

Goal: reduce field-loop state size, prevent internal runtime text from becoming
memory material, and keep code responsible for observable runtime facts rather
than meaning judgment.

## Operating Rule

- Code owns: execution facts, tool calls, source ids, timestamps, schema checks,
  loop limits, safety boundaries, and provenance.
- LLMs own: intent interpretation, goal wording, WorkingMemory meaning, durable
  memo writing, evidence synthesis, and final response wording.
- Night government and branch assets are advisory to the day loop unless a
  narrow verified contract explicitly authorizes use.
- FieldMemo stores verified fact packets. New memos remain branch-pending until
  the night classification path assigns an official branch.

## Completed Cleanup

- WarRoom internals moved into `Core/warroom/`.
- Live tool registry centered on `Core/tools.py`; `tools/toolbox.py` remains a
  compatibility facade.
- WorkingMemory v4 LLM writer is the sole active writer path.
- Legacy v2/v3 raw `active_task` builders and monkey-patch assignments were
  removed.
- Readiness no longer calls no-op preferred-decision routers.
- Supervisor policy bundle and branch-guided switchboard stubs were removed.
- `field_memo_answer_brief` was retired from schema and delivery packets.
- Internal boilerplate such as `Read one stronger...` and
  `current approved evidence boundary` is blocked from becoming active memory
  material.
- Phase -1a now receives a bounded strategist state projection instead of the
  full graph state.
- `working_memory_packet_for_prompt` now emits a bounded prompt packet instead
  of dumping raw WorkingMemory.
- Raw-read, source-relay, and phase-2 analysis prompt packets now use shared
  compactors, so prompt text is bounded even when source objects are larger.
- V3 step 9B added role-aware prompt packet projections. `working_memory`,
  `analysis_report`, `s_thinking_packet`, and `rescue_handoff_packet` now pass
  through node-specific compactors before reaching -1a, -1b, 2b, and phase_3.
- V3 step 9C replaced the monolithic phase_3 prompt with answer-mode-specific
  prompt builders and a compact `Phase3PromptContract.v1` view. -1a, -1b, and
  2b now use compact task-card prompts, and `reasoning_board` prompt packets
  are role-projected before reaching strategist/readiness/delivery surfaces.
- V3 step 6B added compact -1s cycle history. `s_thinking_history` is
  turn-lived, stores only compressed -1s-owned rows plus current
  `s_thinking_packet`, and keeps -1s from re-entering each cycle as a fresh
  context-free judge.
- V3 step 7C removed the old pre-delivery `-1b_auditor` path. Phase 2 and
  WarRoom now return to `-1s`; -1a executable tool requests go directly to
  `0_supervisor`; phase 3 remains followed by `delivery_review`.
- `delivery_review_rejections` is turn-lived and escalates repeated remands to
  119 after the configured limit.
- V3 step 7D made `delivery_review` a real LLM reviewer behind
  `DeliveryReview.v1`. Its prompt sees only final answer text, compact approved
  evidence, `must_include_facts`, `must_avoid_claims`, and rescue preserved
  facts; it does not see full `s_thinking_packet`, WorkingMemory, or reasoning
  board.
- Deterministic speaker guard remains as fallback and hard safety for obvious
  internal-report leaks, but normal post-phase3 answer approval/remand now runs
  through the LLM reviewer.
- `Core.state` now defines long-lived and turn-lived state buckets plus a
  cleanup helper contract.
- `Core.runtime` now provides a minimal runtime-profile/context/cleanup import
  boundary. Self-kernel identity injection is deferred.
- `Core.memory` now provides writer authority contracts and an internal-text
  sanitizer boundary.
- `Core.memory.working_memory_writer` now owns the WorkingMemoryWriter prompt,
  JSON normalization, evidence-fact extraction, and LLM call boundary.
- `Core.memory.field_memo_writer` now owns the FieldMemoWriter prompt and
  decision normalization boundary.

## Next Structural Targets

1. State projection
   - Give each node only the state slice it needs.
   - Remove prompt paths that serialize full state, raw messages, or tool cache
     payloads.
   - Current role whitelist:
     - `-1a`: dialogue state essentials, evidence state essentials,
       `memory_writer.active_topic`, `memory_writer.unresolved_user_request`.
     - `-1b`: `turn_summary` and `response_contract`.
     - `2b`: `evidence_state`.
     - `phase_3`: short-term context, assistant next-turn obligation, pending
       dialogue act, and minimal dialogue-state continuity.

2. Turn-lived cleanup
   - Cleanup is wired after post-turn persistence consumes final state.
   - Keep canonical turn records, WorkingMemory, evidence ledger, and used
     sources before clearing transient reports and caches.

3. WorkingMemory writer contract
   - Document which fields are LLM-authored meaning and which are code-observed
     runtime facts.
   - Keep phase names, tool names, fallback labels, and internal strategy text
     out of memory material.
   - Active writer prompt/normalization now lives under `Core.memory`; remaining
     work is moving persistence/compatibility shell only when safe.

4. FieldMemo writer contract
   - Persist only selected candidate facts with provenance.
   - Keep writer branch output as `proposed_branch_path` only.
   - Official branch assignment belongs to the night classification path.
   - Active writer prompt/decision normalization now lives under `Core.memory`;
     remaining work is separating candidate assembly/persistence later.

5. Delivery review
   - Keep `delivery_review` as the only live -1b position.
   - Current implementation uses the V3 LLM reviewer plus deterministic
     fallback. Next work is quality tuning, not wiring.

6. Readiness vocabulary
   - `Core.pipeline.readiness.py` is gone.
   - `Core.readiness` remains only as typed compatibility helpers.
   - Keep `answer_not_ready` as a legacy alias only, never user-facing output.

## Guardrails

- Do not relocate heuristics into new modules just to make files smaller.
- Delete no-op compatibility hooks when tests can assert their absence.
- Do not touch `__pycache__` or pyc churn during source refactors.
- Prefer projection over broad prompt dumps for token optimization.
- End each code pass with `python -B -m unittest discover -s tests`.
