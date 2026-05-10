# SO1 structured-output inventory

Date: 2026-05-09
Status: SO1-A inventory, generated during implementation.

## Live structured-output call sites

- `Core/nodes.py`
  - `_plan_reasoning_budget`: `ReasoningBudgetPlan` legacy/fallback budget surface.
  - `_llm_start_gate_turn_contract`: `StartGateTurnContract` for -1s.
- `Core/pipeline/strategy.py`
  - `run_base_phase_minus_1a_thinker`: `StrategistReasoningOutput` for -1a.
- `Core/pipeline/supervisor.py`
  - `run_phase_0_supervisor`: tool-calling output via `bind_tools`, now guarded by tool-name allowlist.
- `Core/pipeline/reader.py`
  - `run_phase_2a_reader`: `RawReadReport` for raw-source reading.
- `Core/pipeline/fact_judge.py`
  - `run_phase_2_analyzer`: `AnalysisReport` for 2b fact mode.
- `Core/pipeline/thought_critic.py`
  - `run_2b_thought_critic_node`: `ThoughtCritique` for 2b thought mode.
- `Core/warroom/deliberator.py`
  - `run_phase_warroom_deliberator`: `WarRoomDeliberationOutput`.
- `Core/pipeline/delivery_review.py`
  - `run_delivery_review_llm`: `DeliveryReview`.
- `Core/pipeline/tool_planning.py`
  - `strategist_tool_request_from_context`: legacy compatibility `StrategistToolRequest`.

## SO1 pass disposition

- Added `Core/pipeline/structured_io.py` as the shared boundary utility for typed failure packets, bounded repair retry, fact-id allowlist checks, tool-call allowlist checks, and ThinkingHandoff shape validation.
- Applied bounded repair wrapper to -1s, -1a, 2a, 2b fact mode, 2b thought mode, WarRoom, and delivery review.
- Added validator guards for:
  - `ThoughtCritique.evidence_refs`
  - `DeliveryReview.evidence_refs`
  - 0_supervisor tool names and args shape
  - WarRoom structured-output boundary
  - ThinkingHandoff 9-field shape

## Provider-native structured output note

Local runtime uses LangChain `with_structured_output(PydanticModel)`. In this repository's current Ollama-backed setup, no local code path proves provider-native strict JSON schema support. SO1 therefore treats provider-native strict mode as unavailable for now and uses tool/structured-output calling plus repair retry and Pydantic validation. If a future model provider exposes strict schema mode, `invoke_structured_with_repair` is the intended single insertion point.

## Known remaining follow-up

- `ReasoningBudgetPlan` and legacy `StrategistToolRequest` compatibility paths are still structured-output call sites but were not made graph-boundary blockers in this pass.
- Additional tests should be added if SO2 expands the wrapper into midnight-government LLM seats after §1-B is live.
