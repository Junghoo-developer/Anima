*[한국어](ANIMA_REFORM_IMPLEMENTATION_V1.md) | [English](ANIMA_REFORM_IMPLEMENTATION_V1.en.md)*

# ANIMA Reform Implementation V1

> Document status: BACKGROUND / PARTIALLY IMPLEMENTED.
> Use this for historical implementation slices. Current code surgery is governed
> by `ANIMA_FIELD_LOOP_V2_CONSTITUTION.md` and tracked in `ANIMA_ARCHITECTURE_MAP.md`.

This document is the first-draft implementation plan that breaks [ANIMA_REFORM_V1](ANIMA_REFORM_V1.md) into actual code-work units.

The goal is not to flip everything at once, but to lock the following four in order:

1. Separate start-time judgment and late-stage review.
2. Make `-1a` a true convergence-style planning engine.
3. Make `2b` keep its independence while gaining perspective diversity.
4. Reduce `phase_3` to an honest renderer rather than a clever interpreter.

## 1. Current Baseline

The base already laid down in code is as follows:

- Start gate: [Core/graph.py](Core/graph.py)
- Start layer: [Core/nodes.py](Core/nodes.py) `phase_minus_1s_start_gate`
- Strategist: [Core/nodes.py](Core/nodes.py) `phase_minus_1a_thinker`
- Final judge: [Core/nodes.py](Core/nodes.py) `phase_minus_1b_auditor`
- Final speaker: [Core/nodes.py](Core/nodes.py) `phase_3_validator`
- Common state board: [Core/state.py](Core/state.py), [main.py](main.py)

So the reform is closer to "surgically realigning the existing structure to responsibility" than "building an entirely new system."

## 2. Migration Principles

### Principle A: Change one axis at a time

- Routing
- State contracts
- Judge review
- Speaker delivery

Touching all four large axes simultaneously makes regression causes hard to trace.

### Principle B: Fix the contract before patching the symptom

Adding more conditionals is a last resort. Lock the following contracts first:

- `goal_lock`
- `convergence_state`
- `delivery_readiness`
- `execution_trace`
- `delivery_packet`

### Principle C: Each step has a "must-stop" criterion

Each migration step must immediately stop and re-review if either of the following is observed:

- New loops are still allowed against the same analysis state
- `phase_3` says a generic non-answer despite receiving grounded findings

## 3. First-Draft Migration Order

## 3A. Next stage

`Sleep Stack V1` proceeds based on the following document:

- [ANIMA_SLEEP_STACK_V1.md](ANIMA_SLEEP_STACK_V1.md)

The next structural reform extends from:

- [ANIMA_SLEEP_STACK_V2.md](ANIMA_SLEEP_STACK_V2.md)

The core of this stage is the following five:

1. Build the `REMPlan` stage schema
2. Expand `Second Dream` input to `Dream + TurnProcess + PhaseSnapshot + REMPlan`
3. Add `RoutePolicy / ToolDoctrine` nodes
4. Reduce `0_supervisor` to policy lookup + executor
5. De-persist low-value speculation nodes

The next reinforcement axis is:

6. Promote `REMPlan` to the `REMGovernor` overarching design layer
7. Strengthen `Phase7` as a coverage auditor
8. Make `0_supervisor` follow `RoutePolicy / ToolDoctrine` over hardcoding

### Slice 1. Lock the roles of entry and review

Goals:

- `-1s` only handles a tiny gate.
- `-1b` only handles late-stage review.
- Lock the structure where almost all non-trivial turns are sent to `-1a`.

Targets:

- [Core/graph.py](Core/graph.py)
- [Core/nodes.py](Core/nodes.py)

Mandatory checks:

- `START -> -1s -> -1a` must be the default path.
- `-1s` only sends identity, short greetings, and very thin direct replies to `phase_3`.
- `-1b` does not redo early interpretation; it observes the existing plan / analysis / progress state.

Completion criteria:

- "What shall we do today?"
- "Read the ANIMA supplementary materials and recommend today's tasks"
- "Search again"

For these three inputs, `-1s` quickly chooses a handler without prolixity.

### Slice 2. Lock `-1a` as a convergence-style planning engine

Goals:

- `-1a` not only makes plans but also decides when to issue conclusions upon receiving new evidence.
- `goal_lock` does not drift sideways mid-cycle.

Targets:

- [Core/nodes.py](Core/nodes.py)
- [Core/state.py](Core/state.py) if necessary

Mandatory outputs:

- `goal_lock`
- `achieved_findings`
- `convergence_state`
- `delivery_readiness`
- `next_frontier`

Mandatory rules:

1. If grounded findings directly answer the question → `deliver_now`
2. If grounded findings are insufficient → `need_one_more_source` or `need_targeted_deeper_read`
3. No social-impact / ethics expansion outside the question's axis

Completion criteria:

- "Recommend today's tasks" question → `answer_shape=proposal_1_to_3`
- "Features matching the plan" question → `answer_shape=fit_summary`
- After `2b COMPLETED`, `-1a` does not loop only in gathering but folds into deliverable

### Slice 3. Introduce reviewed lens packets to `2b`

Goals:

- `2b` must not repeat flat interpretation.
- But it must not copy `-1a`'s conclusion verbatim.

Targets:

- [Core/nodes.py](Core/nodes.py)
- [Core/state.py](Core/state.py)
- [main.py](main.py) if necessary

Mandatory state:

- `critic_lens_packet`
- `strategist_objection_packet`

Mandatory rules:

- `-1a` proposes only candidate perspectives, not conclusions
- `-1b` critically refines them
- `2b` verifies the lens against evidence and rejects if wrong

Completion criteria:

- "Recommend today's tasks" question → `2b` prioritizes "today-feasible proposal axes" over feature explanations
- "Plan fit" question → `2b` verifies feature-fit lens before social-impact narrative

### Slice 4. Lock loop-control contracts

Goals:

- Structurally forbid same-state repetition.
- Allow refresh, re-read, and re-plan only when accompanied by "new change."

Targets:

- [Core/nodes.py](Core/nodes.py)
- [Core/state.py](Core/state.py)
- [main.py](main.py) if necessary

Mandatory state:

- `execution_trace`
- `progress_markers.last_combined_signature`
- `progress_markers.last_operation_signature`
- `progress_markers.last_refresh_analysis_signature`
- `progress_markers.stalled_repeats`
- `progress_markers.same_operation_repeats`

Mandatory rules:

1. `-1b -> -1a refresh` against the same `analysis_signature` is once
2. Repeating the same `operation_contract + execution_trace` is forbidden
3. Re-looping is forbidden without one of: new evidence, new plan, narrowed scope

Completion criteria:

- `-1a <-> -1b` round trips do not exceed once for the same analysis state
- The same artifact is not auto-re-read two or three times in a row

### Slice 5. Reduce phase_3 to a renderer

Goals:

- `phase_3` does not re-interpret the question.
- It speaks the good internal conclusion as-is.

Targets:

- [Core/nodes.py](Core/nodes.py)
- [Core/speaker_guards.py](Core/speaker_guards.py)

Mandatory state:

- `delivery_packet`
- `delivery_freedom_mode`

Mandatory rules:

1. Reject if `delivery_packet.final_answer_brief` is missing
2. No generic narrowing follow-up after grounded delivery
3. Core findings of `-1b memo` must be promoted to the packet

Completion criteria:

- For "Read ANIMA supplementary materials and recommend today's tasks":
  - First paragraph: grounded proposal
  - Second paragraph: no generic re-questioning

## 4. Implementation Priority

The most stable actual work order is the following:

1. Slice 1
2. Slice 2
3. Slice 4
4. Slice 5
5. Slice 3

Why this order:

- First divide the roles
- Then attach convergence criteria
- Then block repetition
- Then organize the final delivery
- Then grow the critic multi-lens — this minimizes regression risk

## 5. Per-Stage Test Set

After each slice, run regression with the inputs below.

### Test A. Proposal-style

- "What shall we do today?"
- "Read the ANIMA supplementary materials and recommend today's tasks"

Expected:

- `-1a` plans first
- Grounded proposal
- No generic follow-up

### Test B. Feature-fit style

- "Read the ANIMA supplementary materials and tell me features matching the plan"

Expected:

- Feature summary
- No social-impact prolixity

### Test C. Correction / retry

- "Search again"
- "No, not that, again"
- "Think for yourself"

Expected:

- No stale topic re-entry
- Inherit the current turn as a correction of the immediately previous task

### Test D. Thin direct-answer style

- "Who are you?"
- "What shall we do today?"

Expected:

- Quick branching at `-1s`
- No unnecessary war-room round trips

## 6. Rollback Principles

Each slice must be independently rollback-able.

Therefore, observe the following:

1. Commit state-field additions and branching additions separately.
2. Within one slice, do not change routing and prompts both significantly at once.
3. If even one test set regresses significantly, the slice is temporarily on hold.

## 7. Immediate Next Actions

The first implementation scope to start now is:

1. Slice 1 detail lock
2. Slice 2 mandatory convergence-contract lock
3. Slice 4 minimum repetition-prevention contract lock

In one line:

`First, -1a takes the start; once grounded findings appear, converge immediately; structurally block same-state repetition.`
