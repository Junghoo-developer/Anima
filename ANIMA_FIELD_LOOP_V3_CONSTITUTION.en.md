*[한국어](ANIMA_FIELD_LOOP_V3_CONSTITUTION.md) | [English](ANIMA_FIELD_LOOP_V3_CONSTITUTION.en.md)*

# ANIMA Field Loop V3 — Constitution

**Drafted**: 2026-05-01
**Status**: V3 ratified by Junghoo (2026-05-01). V3 §10 field-loop implementation complete as of purge log 53. V4 discussion enabled. As of 2026-05-09, V4 §1-A (field-loop authority table) and V4 §2 (absolute prohibitions) are LIVE — only the field-loop portion of V3 §1·§2 is replaced; the rest of V3 remains LIVE LAW until V4 §1-B/C/D/E pass.
**Role**: Single point of reference for all cleanup, restructuring, and token-normalization work for the SongRyeon field loop.
**Predecessor documents**: V2 constitution (deprecated upon Junghoo's ratification), REFORM_V1, REFORM_IMPLEMENTATION_V1.
**Update trigger**: V3 authority-table / forbidden-list errata are V3.x; new structural reforms are discussed in V4.

---

## 0. One-Line Summary

> **SongRyeon is a thinking persona. -1s organizes each cycle through two-branched thinking (situation + loop), and on top of that -1a sets goals, plans, tools, and arguments. 0_supervisor executes; 2a/2b verify. When sufficient, phase_3 produces the answer and the -1b LLM reviews it. No node intrudes upon another node's role.**

### Core Principles
1. **Thinking belongs to -1s, planning to -1a, verification to 2b, speech to phase_3, review to -1b.**
2. **Code handles tracking / safety / schema / execution / routing only. Meaning belongs entirely to the LLM.**
3. **No self-evaluation** — work is never evaluated by its author.
4. **Metaphor**: Abolish the legislature/executive/judiciary metaphor. *"SongRyeon's internal thought model."* Address by node number.

---

## 1. Per-Node Authority Tables

### -1s (Thought Compiler)

| Permitted | Forbidden |
|------|------|
| Situation reasoning (external-world understanding) | Direct authoring of tool arguments |
| Loop reasoning (progress + next direction + routing) | Direct read of -1a's plan tree (`strategist_output`, `operation_plan`) |
| Issue reasoning_budget | Final answer text |
| Output 4-slot packet | Fact verification (2b's job) |
| sos trigger (call 119) | Direct tool commands to -1a (`next_direction` is abstract guidance only) |
| Settlement session (when budget is exhausted) | Direct modification of -1a plan |
|  | Final-answer review (-1b's job) |

**Inputs**: user_input, working_memory_brief, analysis_report, execution_trace meta, accumulated previous-cycle self packets.
**Outputs**: `s_thinking_packet` (4 slots — see Appendix C).

### -1a (Planner)

| Permitted | Forbidden |
|------|------|
| Goal-setting (`strategist_goal`) | Routing decision (-1s's job) |
| Plan authoring + revision (`strategist_output`) | Self-evaluation (self-censorship) |
| Tool name + arguments (`tool_request`) | Final answer text |
| First-pass labeling of tool results | Fact verification (2b's job) |
| Receiving -1s feedback for a new plan | Ignoring -1s thought |
| Direct reference of `analysis_report` | Calling `finalize_recommendation` (slot abolished) |

**Inputs**: `s_thinking_packet` (situation + loop_summary + next_direction), `analysis_report`, `working_memory_brief`.
**Outputs**: `strategist_goal`, `strategist_output`, `operation_plan.tool_request`.

### -1b (Answer Reviewer)

| Permitted | Forbidden |
|------|------|
| LLM review of phase_3 answer | Authoring new `tool_query` |
| LLM-domain judgment (hallucination/omission/tone) | Reviewing -1a plan (pre-phase_3 review abolished) |
| END or remand decision | Fact verification (2b's job) |
| Per-turn rejection cap of 3 (over 3 = automatic sos_119, §2-23) | Routing decision (-1s's job) |
| sos invocation (delivery_loop) | Analysis / detective work |

**Position**: *After* phase_3 (single review exit). No pre-delivery position (the legacy `-1b_auditor` node was abolished in V3 §10 7C — Junghoo decision 2026-05-01).
**Inputs**: phase_3 answer + answer-building context (`analysis_report`, `response_strategy`). `s_thinking_packet` is not bundled (preserves independent judgment, avoids echo chamber).
**Outputs**: `delivery_review` (END / remand + reason).

### 2a (Source Reader)

| Permitted | Forbidden |
|------|------|
| Extract `raw_read_report` (excerpt + observed_fact) | Fact judgment |
| Source organization | Final answer text |

### 2b (Fact Judge)

| Permitted | Forbidden |
|------|------|
| Author `analysis_report` (evidences, source_judgments, usable_field_memo_facts) | Routing decision |
| Single source for verified facts | Final answer text |
| Re-judge upon -1s feedback | Policy judgment |

**Primary readers**: -1s + -1a (both directly).

### phase_3 (Speaker)

| Permitted | Forbidden |
|------|------|
| Author the final user-facing answer | Decide a new tool |
| Cite self/relationship/public knowledge + verified facts | Extract new evidence |
| Cite `current_turn_facts` directly | Leak internal workflow (phase names, slot keys, 119, budget) |
| Convert 119 handoff packets into natural language | Cite unapproved facts |
| Reference `s_thinking_packet` (for tone-aligning to user intent) | Change `answer_mode` itself (§2-22) |
|  | Copy `s_thinking_packet` text verbatim |

**Position**: graph answer-generation step (right before -1b review).
**Inputs**:
- `user_input`
- `response_strategy` (-1a-confirmed value — for tool cases)
- `reasoning_board` (accumulated thought)
- `analysis_report` (verified facts, directly cited)
- `working_memory_brief` (compact)
- `recent_context`
- `s_thinking_packet` (reference attachment, source of `answer_mode` for direct-answer cases)
- `rescue_handoff_packet` (when 119 is engaged)

**Removal targets (V3 cleanup)**: `search_results`, `supervisor_instructions`, `loop_count` (absorbed into `analysis_report` and `rescue_handoff_packet`).

**Outputs**: User-facing answer text.

### 0_supervisor (Execution Bureau)

| Permitted | Forbidden |
|------|------|
| Execute -1a `tool_request` | Semantic judgment |
| Result packaging | Routing decision |
| Safety checks (refuse on violation) | Authoring tool arguments itself |

### phase_1 (Tool Invocation)

| Permitted | Forbidden |
|------|------|
| Actual tool invocation + result return | LLM calls (none at all) |

### phase_119 (Handoff Node)

| Permitted | Forbidden |
|------|------|
| Author `rescue_handoff_packet` | Re-investigation / additional tool calls |
| Preserve `preserved_evidences` (verified partial facts) | Empty out `analysis_report.evidences` entirely |
| Separate `rejected_only` blocked items | Pre-phase_3 review |

**Entry triggers**: budget overrun, -1s sos, -1b delivery_loop.

### WarRoom (Thought Lab)

| Permitted | Forbidden |
|------|------|
| -1s sos-tier deep deliberation | Routine routing |
| Next-generation general-intelligence thought experiments | Encroaching on -1s's job |

**Not used in normal operation.** -1s solo thinking is the routine job.

---

## 2. Absolute Prohibition List (Violation = Auto-Reject)

1. No forced goal/slot generation from raw user_input (only after -1s normalization)
2. No storing internal strategic text in `working_memory.dialogue_state.active_task`
3. FieldMemoWriter cannot decide official branches (pending/inbox only)
4. No user-facing `answer_not_ready` (use clean_failure)
5. Midnight policy cannot directly govern day-loop routes
6. -1b cannot author new `tool_query`
7. -1a cannot decide routing itself (-1s `routing_decision` domain)
8. -1a cannot ignore -1s thought
9. phase_3 cannot leak phase names / schema keys / 119 / budget
10. **No more than one -1s↔-1a ping-pong on the same tool result** (violation → 119 entry)
11. No double-storage of `tool_carryover` (state top-level single source)
12. No double-storage of `response_strategy` (only inside `strategist_plan`)
13. No dead sys_prompt builds (only `build_*_prompt` functions)
14. **Deterministic fallback cannot attempt semantic classification / intent routing** (LLM domain)
15. **Code heuristics cannot author final answer text (`direct_answer_seed`)**
16. **NEW** -1s cannot directly read -1a's plan tree (`strategist_output`, `operation_plan`) — anti-echo-chamber
17. **NEW** -1s `next_direction` cannot directly command tool name/query (abstract guidance only)
18. **NEW** -1a cannot self-evaluate / call `finalize_recommendation` (no self-censorship)
19. **NEW** 119 cannot empty out `analysis_report.evidences` entirely (preserve verified partial facts)
20. **NEW** -1b cannot attempt review *before* phase_3 (single review after phase_3)
21. **NEW** When `max_total_budget` exceeded, automatic 119 entry; bypass via other nodes is forbidden
22. **NEW** phase_3 `answer_mode` decision priority order: 119 (`rescue_handoff_packet`) → -1a (`response_strategy.delivery_freedom_mode`) → -1s (`s_thinking_packet.situation_thinking.domain`). The downstream node beats the upstream. phase_3 does not change `answer_mode` itself; it follows the value received.
23. **NEW** -1b rejection cap is 3 per turn (turn-lived counter). Over 3 = automatic sos_119 (delivery_loop trigger). On each rejection, the LLM picks the verdict (approve/remand/sos_119); code only enforces the counter + cap.
24. **NEW** phase_3 may cite only facts in `must_include_facts` or `analysis_report.evidences` / `analysis_report.usable_field_memo_facts`. No fact creation by guessing/translating/interpreting. When unknown, state "I don't know" (user-friendly phrasing). Pre-hallucination prevention takes priority over post-hoc -1b review (consistent with §0 one-line).

---

## 3. Minimum Core to Preserve

Code only handles **activity tracking / safety / schema / tool execution / provenance / routing**:

1. LangGraph wiring (`Core/graph.py`)
2. Schema validation (`Core/pipeline/contracts.py`)
3. Tool execution mechanics (`phase_1`)
4. Evidence ledger (`Core/evidence_ledger.py`)
5. Loop limit & budget (`reasoning_budget`, `hard_stop`, `max_total_budget`)
6. Speaker guard minimum layer (`Core/speaker_guards.py`)
7. Activity tracking / provenance
8. `cleanup_turn_lived_fields` (Phase 2)
9. **NEW** Runtime context packet (`Core/runtime/context_packet.py` — -1s accumulated packet assembly)

→ All other semantic judgment / planning / summarization / answering belongs to **the LLM.**

---

## 4. Purge Decision Tree

For each function/module, ask:

```
1. Out-of-authority work? (§1)
   → Delete

2. Absolute-prohibition violation? (§2)
   → Delete

3. Code uses heuristics where the LLM should think? (§2-14, §2-15, §2-16)
   → Delete

4. Duplicate? (e.g., dual response_strategy)
   → Consolidate to single source, then delete the old place

5. Vision-misaligned + high regression risk?
   → Isolate as compatibility wrapper (audit after one season)

6. Aligned + only wrong location?
   → Move to a new package

7. Aligned + only hygiene lacking?
   → Keep as-is, only tidy tests

8. Future-Pass area?
   → Do not touch
```

---

## 5. Representative Runtime Cases (10, V3 wiring)

| # | Case | -1s `routing_decision` | `answer_mode` (final) | Expected path | Answer character |
|---|------|---------|---------|---------|---------|
| 1 | "What's your name?" | `phase_3` (self_kernel) | `self_kernel_response` | -1s → phase_3 → -1b → END | Self direct answer |
| 2 | "Who is Sunny's older sister?" | `phase_3` (public_parametric) | `public_parametric_knowledge` | -1s → phase_3 → -1b → END | Public-knowledge direct |
| 3 | "I told you earlier" | `-1a` (continuation) | `simple_continuation` or `current_turn_grounding` | -1s → -1a → tool → 2a → 2b → -1s → phase_3 → -1b → END | Recent context |
| 4 | "Search my memory" | `-1a` (memory_recall) | `memory_recall` | -1s → -1a → tool_search_memory → ... → phase_3 → -1b → END | Search-based |
| 5 | "OMORI's protagonist?" | `phase_3` (public_parametric) | `public_parametric_knowledge` | -1s → phase_3 → -1b → END | Public knowledge |
| 6 | "Search my diary" | `-1a` (memory_recall, broad) | `memory_recall` | -1s → -1a → ... → phase_3 → -1b → END | Search |
| 7 | "yeah" | `phase_3` (short_ack) | `simple_continuation` | -1s → phase_3 → -1b → END | Continue pending act |
| 8 | "Why are you repeating?" | `phase_3` (feedback) | `simple_continuation` | -1s → phase_3 → -1b → END | Apology + correction |
| 9 | "Do you remember what I made?" | `-1a` (memory_recall, ambiguous) | `memory_recall` | -1s → -1a → ... → phase_3 → -1b → END | Search or unknown |
| 10 | "Read this document" | `-1a` (artifact_hint) | `current_turn_grounding` | -1s → -1a → tool_read_artifact → ... → phase_3 → -1b → END | Document summary |

### All cases share
- -1s is **always** the first node.
- phase_3 **always** produces the answer.
- -1b **always** reviews immediately after phase_3.
- Single END exit (or 119 → phase_3 → -1b → END).

---

## 6. Final Package Layout

```text
Core/
  pipeline/
    start_gate.py
    strategy.py
    readiness.py        # → slimmed as -1b position changes
    supervisor.py
    tool_execution.py
    reader.py
    fact_judge.py
    delivery.py
    rescue.py           # → rescue_handoff_packet new
    contracts.py
    packets.py
    plans.py
    routing.py          # NEW: -1s routing_decision branch

  memory/               # NEW (Pass 3)
    working_memory_writer.py
    field_memo_writer.py
    memory_contracts.py
    memory_sanitizer.py

  runtime/              # NEW (Pass 4 — self_kernel.py deferred)
    runtime_profile.py
    context_packet.py   # -1s accumulated packet assembly
    cleanup.py          # cleanup_turn_lived_fields
    # self_kernel.py deferred (interim infrastructure to be replaced)

  warroom/
    contracts.py
    deliberator.py
    output.py
    state.py

  night/                # NEW (Pass 5)
    reflection_graph.py
    audit_field_usage.py
    branch_growth.py
    policy_assets.py
    rem_governor.py
    strategy_council.py

  adapters/
    artifacts.py
    neo4j_connection.py
    neo4j_memory.py
    night_queries.py
    seed_files.py
    web_search.py
```

---

## 7. nodes.py Final Goal

**Final size < 300 lines**. Wrappers + dependency wiring only.

```python
def phase_minus_1a_thinker(state):
    return run_phase_minus_1a_thinker(state, **_strategy_deps())

def _strategy_deps():
    return {...}

# Compatibility imports (remove after one season)
```

→ All helpers migrate to pipeline / memory / runtime.

---

## 8. Memory-Layer Final Authority

| Owner | Write area | Read area |
|------|-------------|-------------|
| WorkingMemoryWriter | `working_memory.{dialogue_state, evidence_state, response_contract, temporal_context, user_model_delta, memory_writer, turn_summary}` | All working_memory + immediately previous turn |
| FieldMemoWriter | FieldMemo candidates (pending/inbox default; branch_path is recommendation only) | EvidenceLedger, working_memory |
| Midnight government | FieldMemo official promotion, schema recommendation, deprecated discovery, REM/Strategy/Branch growth | turn_history accumulation, FieldMemo, EvidenceLedger accumulation |
| Searcher (read-only) | (no writes) | FieldMemo, MemoryBuffer, EvidenceLedger, Artifact |
| Field-loop nodes | Own outputs | `s_thinking_packet`, `analysis_report` (limited sub-keys), `working_memory_brief` |

---

## 9. Session Mechanism (V3 — new model)

```
[1st session — every turn start]
  Call -1s → 4-slot packet (situation_thinking + loop_summary + next_direction + routing_decision)
    → routing_decision = "phase_3" → phase_3 → -1b → END
    → routing_decision = "-1a" → start -1a cycle

[Active period]
  -1a (goal·plan·tool·args) → 0_supervisor → phase_1 → 2a → 2b
    → -1s cycle N+1 (review + update routing_decision)
    → "phase_3" / "-1a again" / "119"

[2nd session — settlement (loop_count >= reasoning_budget)]
  Re-call -1s → review accumulated outputs
    → routing_decision = "phase_3" (sufficient)
    → motion for additional budget + "-1a" (continue)
    → "119" (give up)

[3rd session — SOS]
  -1s declares sos → 119 entry → rescue_handoff_packet → phase_3 → -1b → END

[4th session — Delivery Loop]
  -1b accumulates N rejections → 119 entry

[Meta caps]
  max_total_budget = 10
  total_loop_count > 10 → forced 119
  SOS limited to once per turn
  Ping-pong: -1s ↔ -1a on same tool result must not exceed 1
```

---

## 10. Implementation Order

```
✅ 0. V3 constitution finalized (Junghoo review-passed 2026-05-01)
✅ 1. ARCHITECTURE_MAP status text correction (Claude, 2026-05-01)
✅ 2. New minimum Core/runtime package (Codex, purge log 36/40)
✅ 3. New minimum Core/memory package (Codex, purge log 37/41)
✅ 4. nodes.py residual inventory (Codex, purge log 42)
✅ 5. InferenceBuffer semantic-field contamination block (Codex, purge log 43)
✅ 6A. -1s 4-slot schema definition + start_gate.py (Codex, purge log 44)
✅ 6B. context_packet.py accumulator implementation (Codex, purge log 51)
       - Compressed accumulation (history_compact + current 4-slot full)
       - Satisfies V3 §9 2nd-session "review of accumulated outputs"
✅ 7A. delivery contract scaffold (Codex, purge log 45)
✅ 7B. New post-delivery gate (Codex, purge log 46)
✅ 7C. Old -1b_auditor node **fully abolished** (Codex, purge log 52)
       - Removed from graph wiring
       - Existing -1b routing authority consolidated into -1s (consistent with V3 §1 -1s routing_decision job)
       - Next nodes for phase_2/0_supervisor/warroom are -1s (resume thinking)
       - Core/pipeline/readiness.py abolished
       - delivery_review after phase_3 is the sole -1b position (consistent with V3 §0 one-line)
✅ 7D. delivery_review deterministic → LLM reviewer (Codex, purge log 53)
✅ 8. New 119 rescue_handoff_packet (Codex, purge log 47)
       - rescue.py: evidences=[] abolition
       - preserved_evidences/preserved_field_memo_facts retained
       - rejected_only separated
       - user_facing_label is 119 code enum + phase_3 natural-language conversion (Q3)

✅ 9A. strategist_goal migration + -1a output slimming (Codex, purge log 48)
       - normalized_goal → strategist_goal one-season compatibility wrapper (Q7 option b)
       - both registered in state.py with alias compatibility
       - 35 spots in nodes.py replaced gradually (not all at once)
       - operation_plan / strategist_output / response_strategy token diet
✅ 9B. Input packet diet (Codex, purge log 49)
       - working_memory_brief whitelist locked
       - analysis_report projection (compactor strengthened)
       - s_thinking_packet sub-fields minimized
       - rescue_handoff_packet core fields only
✅ 9C. Node sys_prompt + contract slimming (Codex, purge log 50)
       - phase_3 contract slimmed (internal fields minimized)
       - delivery_review reviewer prompt (7D preparation)
       - reasoning_board projection

V3 core completed:
✅ field-loop authority relocation
✅ prompt/state token diet
✅ old pre-delivery -1b removal
✅ post-phase3 LLM delivery review

V4 / future candidates:
⚪ 10. Legislative night branch (audit_field_usage)
⚪ 11. WarRoom v2 / thought-lab activation
⚪ 12. midnight_reflection.py separation (Pass 5)
⚪ 13. self-kernel / identity injection
⚪ 14. DB migration, embedding, developer tooling reform
⚪ 15. normalized_goal compatibility wrapper removal
```

---

## 11. Roles

| Role | Owner |
|------|------|
| Vision / constitutional amendment | Junghoo (legislature) |
| Vision discussion + code diagnosis + Codex review | Claude (judicial advisory) |
| Code authoring/modification/testing | Codex (executive implementation) |
| Final approval (merge) | Junghoo |

→ Claude does not write code; Codex does not decide vision.

---

## Appendix A. Pending Items (V3 — Junghoo additional review)

V2 pending items were absorbed into §0~§9 and resolved. New pending items:

- [ ] **Q1 (V4 candidate)**: Exact sub-field expansion of -1s 4-slot schema. V3 implementation is complete with the current Appendix C schema. Additional sub-field design is discussed in V4.
- [x] **Q2 (decided 2026-05-01)**: -1b's verdict (approve / remand / sos_119) is chosen by the LLM on each rejection. Code-side meta cap: **per-turn -1b rejection cap is 3, over which automatic sos_119** (turn-lived counter). Stamped as §2-23.
- [x] **Q3 (decided 2026-05-01)**: `rescue_handoff_packet.user_facing_label` is **authored by 119 code as an enum**; phase_3 LLM converts to natural language. 119 does not call the LLM (consistent with §1 phase_119 authority). Enum candidates: `"insufficient search results" / "memory not found" / "ambiguous question" / "retry needed"`, etc. — Codex may add/remove during work, registered as V3.x.
- [ ] **Q4 (V4 candidate)**: WarRoom trigger conditions — V3 keeps WarRoom withdrawn from routine routing as a thought lab. Confirmed during multi-seat WarRoom v2 design.
- [x] **Q5 (verified 2026-05-01)**: For direct_delivery cases, `loop_summary` is also filled with normal objects (`attempted_so_far=["start_gate_contract"]`, `current_evidence_state` string, `gaps` array). Consistent with V3 vision. No code change needed.
- [x] **Q6 (decided/implemented 2026-05-01)**: -1s accumulated packet is **compressed accumulation** (option b). `history_compact` (short summary of previous cycles) + `current` (latest 4-slot full). Implementation location is `Core/runtime/context_packet.py`. Implemented as V3 §10 stage 6B.
- [x] **Q7 (decided/implemented 2026-05-01)**: `normalized_goal` → `strategist_goal` migration is a **one-season compatibility wrapper** (option b). Both registered in state.py with alias compatibility. Implemented as V3 §10 stage 9A. Wrapper removal after one season is a V4 candidate.

---

## Appendix B. Quick Cleanup Reference (for Codex)

5-second decision when encountering a function:

1. **Out of authority?** (§1) → Delete
2. **Absolute-prohibition violation?** (§2) → Delete
3. **Heuristic?** (§2-14, §2-15, §2-16) → Delete
4. **Duplicate?** → Consolidate
5. **Wrong location?** → Move
6. **Aligned + only hygiene?** → Keep as-is

---

## Appendix C. New Slot Schema Specifications

### `s_thinking_packet` (-1s output)

```python
{
    "situation_thinking": {
        "user_intent": "...",
        "domain": "memory_recall | public_parametric | self_kernel | continuation | feedback | artifact_hint | ambiguous",
        "key_facts_needed": [...],
    },
    "loop_summary": {
        "attempted_so_far": [...],
        "current_evidence_state": "...",
        "gaps": [...],
    },
    "next_direction": {
        "suggested_focus": "...",       # abstract guidance only (§2-17)
        "avoid": [...],                 # abstract guidance only
        # No direct tool name/query commands (§2-17)
    },
    "routing_decision": {
        "next_node": "-1a | phase_3 | 119",
        "reason": "...",
    },
}
```

### `rescue_handoff_packet` (119 output)

```python
{
    "trigger": "budget_exceeded | s_sos | delivery_loop",
    "attempted_path": [...],

    "preserved_evidences": [...],            # Verified partial facts (NEW)
    "preserved_field_memo_facts": [...],     # Verified memo partial facts (NEW)
    "rejected_only": [...],                  # Blocked items only

    "what_we_know": [...],                   # Natural-language summary
    "what_we_failed": [...],
    "speaker_tone_hint": "apology + partial info | simple don't-know | re-question | next-turn promise",
    "user_facing_label": "...",              # phase_3 converts to natural language
}
```

### `delivery_review` (-1b output)

```python
{
    "verdict": "approve | remand | sos_119",
    "reason": "...",
    "issues_found": ["hallucination risk" | "fact omission" | "tone inappropriate" | ...],
    "remand_target": "-1a | -1s",         # only if remand
    "remand_guidance": "...",             # only if remand
}
```

### `strategist_goal` (-1a output — successor to `normalized_goal`)

```python
{
    "user_goal_core": "...",
    "answer_mode_target": "memory_recall | public_parametric | self_kernel | ...",
    "success_criteria": [...],
    "scope": "narrow | broad",
}
```

---

**Document version**: V3 implementation-complete consolidation (2026-05-01)
**Next update**: V3 errata are V3.x; new structural reforms are discussed in V4
**Deprecate status**: V2 constitution is superseded by V3
