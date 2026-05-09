*[한국어](ANIMA_REFORM_V1.md) | [English](ANIMA_REFORM_V1.en.md)*

# ANIMA Reform V1

> Document status: BACKGROUND / ABSORBED.
> Use this for reform philosophy and historical intent. If it conflicts with
> `ANIMA_FIELD_LOOP_V2_CONSTITUTION.md`, the V2 constitution wins.

This document is the first-draft reference for reforming ANIMA's current thinking loop — not into "a system that thinks more" but into "a system that converges on time, separates responsibility, and delivers without hallucination."

## 1. Problem Definition

The core diseases of ANIMA today are as follows:

1. The same state still triggers another loop.
2. `-1a` makes plans, but tends to expand laterally instead of converging on the question.
3. `-1b` should be a reviewer, but is overloaded with early situation interpretation.
4. `2b` has independence, but its perspective packet is weak, so it slides back to flat interpretation.
5. `phase_3` ("3rd") receives weak delivery packets instead of good internal conclusions, and slides into conservative generic answers.
6. The system sees "how many times did it loop" but only weakly sees "what new fact emerged in this loop."

In one line:

`The current disease is not a lack of thinking, but state transition and responsibility distribution.`

## 2. Reform Goals

There are five reform goals.

1. Start fast, plan deeply, review strictly.
2. Do not repeat the same thinking on the same input with the same evidence.
3. Make continuous thinking "continuous convergence" rather than "continuous repackaging."
4. Make `phase_3` only speak; finish judgment and remand before it.
5. Prepare the state contract first so that future midnight reflection can self-distill this structure.

## 3. Layered Responsibility

### `-1s` Start Gate

Role:

- Fast metacognition sensor
- Whether to answer immediately
- Whether grounding comes first
- Whether planning comes first
- Whether it is an emergency / special case

Must do:

- `answerability`
- `recommended_handler`
- `confidence`
- `risk_flags`
- `why_short`

Must not do:

- Deep semantic interpretation
- Long-term planning
- Detailed tool-plan design
- Imitate verdicts

Principle:

`-1s must be small and smart, never heavy.`

### `-1a` Strategist

Role:

- Initial situation understanding
- Lock the goal (`goal_lock`)
- Author the operation contract
- Issue conclusions after evidence is in hand
- Design the next frontier

Four mandatory questions every turn:

1. What new fact did this loop produce?
2. How far does that fact answer the current user question?
3. Should the conclusion be issued now?
4. If not, how must the next operation differ from the previous?

Must do:

- `goal_lock`
- `action_plan`
- `operation_contract`
- `achieved_findings`
- `convergence_state`
- `delivery_readiness`
- `next_frontier`

Must not do:

- Ignore the question's axis and auto-expand to social impact / ethics
- Stay in `gathering` while grounded findings are already sufficient
- Repeat a previous plan verbatim

Principle:

`-1a must be a convergence planner, not a planner.`

### `2a` Reader

Role:

- Read source text
- Secure raw grounding
- Prefer artifact fast path / deterministic parser

Must do:

- `raw_read_report`
- `read_mode`
- `read_focus`
- `source_relay_packet`

Must not do:

- Stack thick interpretation
- Plan
- Decide answer convergence

Principle:

`2a only reads.`

### `2b` Critic / Examiner

Role:

- Fact-first diagnosis
- Evidence-gap diagnosis
- Receive lens packets as objects of inspection and examine multi-angled

Must do:

- `analysis_report`
- `evidences`
- `source_judgments`
- `recommended_action`
- `objections`

Additional principles:

- `critic_lens_packet` is not the answer — it is a lens for examination.
- Do not copy `-1a`'s conclusion.

Must not do:

- Plan tools
- Propose arbitrary expansion searches
- Over-generalize the user's emotion or plan without evidence

Principle:

`2b must be independent but not blind.`

### `-1b` Final Judge

Role:

- Late-stage review
- Remand
- Loop blocking
- Delivery suitability check

Must observe:

- Did new evidence appear?
- Did a new plan appear?
- Did the question scope narrow?
- Is the same operation being repeated?
- Does this packet directly answer the current question?

Must not do:

- Take on early situation interpretation alone
- Infinitely refresh `-1a` against the same analysis state
- Let a good memo pass through without promoting it to a phase_3 packet

Principle:

`-1b is a reviewer, not a detective.`

### `phase_3` Speaker

Role:

- Read out the `delivery_packet`
- Speak within the granted degree of freedom

Must do:

- `final_answer_brief`
- `approved_fact_cells`
- `approved_claims`
- `delivery_freedom_mode`

Must not do:

- Re-interpret the question
- Re-plan
- Auto-generate generic narrowing follow-ups

Principle:

`phase_3 must be an honest renderer, not a clever judge.`

## 4. Mandatory State Contracts

The following fields must be commonly relied upon by all thinking after the reform.

### Start Layer

- `start_gate_review`
  - `answerability`
  - `recommended_handler`
  - `confidence`
  - `risk_flags`
  - `why_short`

### Strategic Layer

- `goal_lock`
  - `user_goal_core`
  - `answer_shape`
  - `must_not_expand_to`

- `action_plan`
  - `current_step_goal`
  - `required_tool`
  - `next_steps_forecast`
  - `operation_contract`

- `operation_contract`
  - `operation_kind`
  - `target_scope`
  - `query_variant`
  - `novelty_requirement`

- `achieved_findings`
- `convergence_state`
- `delivery_readiness`
- `next_frontier`

### Execution Layer

- `execution_trace`
  - `executed_tool`
  - `tool_args_signature`
  - `read_mode`
  - `read_focus`
  - `analysis_focus`
  - `source_ids`
  - `evidence_count`

### Critic Layer

- `critic_lens_packet`
  - `must_answer_user_goal`
  - `must_not_expand_to`
  - `lens_candidates`
  - `current_loop_delta`
  - `critic_task`

- `strategist_objection_packet`
  - `has_objection`
  - `suspected_owner`
  - `objection_text`
  - `review_focus`

### Progress Layer

- `progress_markers`
  - `last_combined_signature`
  - `last_operation_signature`
  - `last_refresh_analysis_signature`
  - `stalled_repeats`
  - `same_operation_repeats`

### Delivery Layer

- `delivery_packet`
  - `final_answer_brief`
  - `approved_fact_cells`
  - `approved_claims`
  - `must_avoid_claims`
  - `delivery_freedom_mode`
  - `followup_instruction`

## 5. Forbidden Actions

### All layers (common)

1. Do not repeat the same plan with the same evidence state.
2. Do not pretend to have a new conclusion without new evidence.
3. Do not prioritize older context over the current user question.

### `-1a`

1. Do not stay in `gathering` when grounded findings are already sufficient
2. Do not change `goal_lock` mid-cycle to a different goal
3. Do not auto-expand to a larger social narrative beyond the question

### `2b`

1. Do not copy `-1a`'s conclusion as if it were the answer
2. Do not generalize psychology without evidence
3. Do not invade the planning role

### `-1b`

1. Do not refresh multiple times against the same `analysis_signature`
2. Do not let a good conclusion pass phase_3 without promoting it to the speaker packet
3. Do not over-take early situation interpretation in place of review

### `phase_3`

1. After grounded delivery, do not append generic narrowing follow-ups
2. Do not push the question scope back onto the user as a non-answer
3. Do not re-interpret internal-layer memos in your own way

## 6. Loop Laws

After the reform, the loop follows these rules.

1. `-1b -> -1a refresh` against the same `analysis_signature` is allowed at most once.
2. If the same `operation_contract + execution_trace` repeats, re-execution is forbidden.
3. Re-looping is forbidden unless one of these is present:
   - new evidence
   - a new plan
   - a narrowed scope
4. If `2b == COMPLETED` and grounded findings satisfy `goal_lock`, prioritize convergence.
5. `proposal_1_to_3`, `fit_summary`, `feature_summary`, `findings_first` are treated as complete answer shapes.

## 7. phase_3 Freedom Modes

`phase_3` has only the following five modes:

- `grounded`
- `supportive_free`
- `proposal`
- `identity_direct`
- `answer_not_ready`

The judge must explicitly assign the mode; `phase_3` does not change it by guessing.

Additional rules:

- No generic follow-up in `proposal`
- No scope-narrowing question in `grounded`
- No capability-boundary explanation in `identity_direct`

## 8. Phased Migration Order

### Phase A: Responsibility Separation

1. Lock the `START -> -1s -> -1a` structure
2. Reduce `-1b` to a late-stage reviewer
3. Simplify `phase_3` to a packet renderer

### Phase B: Convergence Contracts

1. `goal_lock`
2. `convergence_state`
3. `delivery_readiness`
4. `achieved_findings`

These four fields are enforced as `-1a` mandatory output.

### Phase C: Critic Multi-Lens

1. Formalize `-1a -> -1b -> 2b` lens packets
2. `2b` verifies the lens against evidence
3. `-1a` may produce an objection packet against `2b`

### Phase D: Loop Control

1. Refresh latch
2. Same-operation block
3. Generic speaker follow-up rejection
4. Memo findings -> `final_answer_brief` promotion

### Phase E: Midnight Reflection Integration

This stage comes later.

Midnight reflection must learnedly reinforce the following:

- Which questions are immediately answerable
- Which loops actually made progress
- Which remands were actually effective
- Which delivery modes fit well

## 9. Success Criteria

Reform V1 is successful when the following are met:

1. For "recommend today's tasks" questions, `2b COMPLETED` is followed by immediate `proposal` convergence
2. For "features matching the plan" questions, feature summary is produced without lengthy social-impact narrative
3. `-1a/-1b` round trips against the same analysis state do not exceed one
4. `phase_3` does not append generic narrowing follow-ups after grounded answers
5. Stale topics do not re-enter on correction turns

## 10. Final Principle

ANIMA is not "a system that thinks longer." It must satisfy:

1. Pin down the current question precisely.
2. Compute the delta of new evidence.
3. Issue conclusions at the appropriate moment.
4. When deeper digging is needed, prescribe a different operation than before.
5. At the end, speak only the packet.

One-line final principle:

`The core of continuous thinking is not thinking longer, but locking the goal, computing the delta, and converging on time.`
