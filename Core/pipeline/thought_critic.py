"""2b thought_critic mode (V4 §1-A.3, CR1).

Entry point for the 2b_thought_critic graph node. Activated when the
deterministic gate ``_strategist_needs_thought_recursion`` passes:

    has_goal AND fact_cells == 0 AND no_tool_needed

The critic compares the current ``s_thinking_packet`` against
``recent_context`` + ``working_memory`` (and ``fact_cells`` if any),
emits a ``ThoughtCritique.v1`` packet into state under
``prior_thought_critique``, then returns to ``-1s_start_gate`` so the
second -1s call can verify-then-route (V4 §1-A.13 anchor).

The 2b critic in this mode:
  - Does NOT call tools (V4 §1-A.3 forbidden + V4 §2 (g)).
  - Does NOT author final answer text.
  - Does NOT invent fact_ids (V4 §2 (d)).
  - Auto-switches input mode (B-2.4 (다)):
      * fact_cells > 0  → integrated critique (facts + thought + memory)
      * fact_cells == 0 → memory-based critique (recent_context + working_memory)

Returning state contains ``prior_thought_critique`` (ThoughtCritique.v1
shaped dict) which becomes the *input differentiator* for the second
-1s call — the explicit-difference defense against gemma4 false negatives
(V4 §1-A.0 / §1-A.13).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .contracts import ThoughtCritique


def _empty_critique() -> Dict[str, Any]:
    """Safe fallback used when LLM call fails or returns garbage."""
    return ThoughtCritique().model_dump(by_alias=True)


def _compact_thought_packet_for_prompt(s_thinking_packet: Any) -> str:
    """Render the latest -1s ThinkingHandoff (or legacy SThinkingPacket) compactly."""
    if not isinstance(s_thinking_packet, dict):
        return "N/A"
    schema = str(s_thinking_packet.get("schema") or s_thinking_packet.get("schema_version") or "").strip()
    parts: List[str] = []
    parts.append(f"schema={schema or 'unknown'}")
    goal_state = str(s_thinking_packet.get("goal_state") or "").strip()
    if goal_state:
        parts.append(f"goal_state={goal_state[:200]}")
    what_we_know = s_thinking_packet.get("what_we_know") or []
    if isinstance(what_we_know, list) and what_we_know:
        parts.append("what_we_know=" + " | ".join(str(x).strip() for x in what_we_know[:5] if str(x).strip()))
    what_is_missing = s_thinking_packet.get("what_is_missing") or []
    if isinstance(what_is_missing, list) and what_is_missing:
        parts.append("what_is_missing=" + " | ".join(str(x).strip() for x in what_is_missing[:5] if str(x).strip()))
    next_node_reason = str(s_thinking_packet.get("next_node_reason") or "").strip()
    if next_node_reason:
        parts.append(f"next_node_reason={next_node_reason[:200]}")
    return "\n".join(parts) if parts else "N/A"


def _compact_recent_context_for_prompt(recent_context: Any, limit: int = 6) -> str:
    if not recent_context:
        return "N/A"
    if isinstance(recent_context, str):
        text = recent_context.strip()
        return text[:1200] if text else "N/A"
    if isinstance(recent_context, list):
        rows: List[str] = []
        for item in recent_context[-limit:]:
            if isinstance(item, dict):
                role = str(item.get("role") or item.get("speaker") or "").strip()
                text = str(item.get("content") or item.get("text") or "").strip()
                if text:
                    rows.append(f"[{role}] {text[:300]}" if role else text[:300])
            elif isinstance(item, str) and item.strip():
                rows.append(item.strip()[:300])
        return "\n".join(rows) if rows else "N/A"
    return "N/A"


def _compact_working_memory_for_prompt(working_memory: Any) -> str:
    if not isinstance(working_memory, dict) or not working_memory:
        return "N/A"
    parts: List[str] = []
    dialogue = working_memory.get("dialogue_state") or {}
    if isinstance(dialogue, dict):
        active = str(dialogue.get("active_topic") or "").strip()
        pending = str(dialogue.get("pending_dialogue_act") or "").strip()
        if active:
            parts.append(f"active_topic={active[:200]}")
        if pending:
            parts.append(f"pending_dialogue_act={pending[:200]}")
    user_model = working_memory.get("user_model_delta") or {}
    if isinstance(user_model, dict):
        persona = str(user_model.get("persona_hints") or "").strip()
        if persona:
            parts.append(f"persona_hints={persona[:200]}")
    return "\n".join(parts) if parts else "N/A"


def _compact_fact_cells_for_critique(fact_cells: Any, limit: int = 8) -> str:
    if not isinstance(fact_cells, list) or not fact_cells:
        return "N/A (fact_cells empty — memory-based critique mode)"
    rows: List[str] = []
    for cell in fact_cells[:limit]:
        if not isinstance(cell, dict):
            continue
        fact_id = str(cell.get("fact_id") or "").strip()
        fact = str(cell.get("extracted_fact") or "").strip()
        source = str(cell.get("source_id") or "").strip()
        if fact_id and fact:
            rows.append(f"{fact_id}: {fact[:200]} (source={source})")
    return "\n".join(rows) if rows else "N/A"


def run_2b_thought_critic_node(
    state: Dict[str, Any],
    *,
    llm: Any,
    build_thought_critic_prompt: Callable[..., str],
    print_fn: Callable[[str], None] = print,
) -> Dict[str, Any]:
    """Run 2b in thought_critic mode and stamp the result on state.

    Returns a state delta dict with ``prior_thought_critique``. The graph
    then routes back to ``-1s_start_gate`` where the second -1s call sees
    the critique as a *new* input — this is the input differentiator for
    gemma4 false-negative defense (V4 §1-A.13).
    """
    print_fn("[Phase 2b/thought_critic] Critiquing -1s thought flow against memory...")

    s_thinking_packet = state.get("s_thinking_packet") or {}
    recent_context = state.get("recent_context")
    working_memory = state.get("working_memory") or {}
    reasoning_board = state.get("reasoning_board") or {}
    fact_cells = reasoning_board.get("fact_cells", []) if isinstance(reasoning_board, dict) else []

    has_facts = isinstance(fact_cells, list) and len(fact_cells) > 0
    mode = "integrated" if has_facts else "memory_based"
    print_fn(f"  [Phase 2b/thought_critic] mode={mode} (fact_cells={len(fact_cells) if isinstance(fact_cells, list) else 0})")

    sys_prompt = build_thought_critic_prompt(
        s_thinking_packet_compact=_compact_thought_packet_for_prompt(s_thinking_packet),
        recent_context_compact=_compact_recent_context_for_prompt(recent_context),
        working_memory_compact=_compact_working_memory_for_prompt(working_memory),
        fact_cells_compact=_compact_fact_cells_for_critique(fact_cells),
        mode=mode,
    )

    critique_dict: Dict[str, Any]
    try:
        structured_llm = llm.with_structured_output(ThoughtCritique)
        critique_obj = structured_llm.invoke(sys_prompt)
        if isinstance(critique_obj, ThoughtCritique):
            critique_dict = critique_obj.model_dump(by_alias=True)
        elif isinstance(critique_obj, dict):
            critique_dict = ThoughtCritique(**critique_obj).model_dump(by_alias=True)
        else:
            print_fn("  [Phase 2b/thought_critic] LLM returned non-schema output; using empty critique.")
            critique_dict = _empty_critique()
    except Exception as exc:  # pragma: no cover - LLM runtime error path
        print_fn(f"  [Phase 2b/thought_critic] LLM call failed ({exc!r}); using empty critique.")
        critique_dict = _empty_critique()

    return {"prior_thought_critique": critique_dict}


def phase_2b_thought_critic(state: Dict[str, Any]) -> Dict[str, Any]:
    """Graph-node entry. Wired in :mod:`Core.graph`.

    Concrete dependencies (LLM client + prompt builder) are injected via
    :func:`run_2b_thought_critic_node`. The wrapper imports them lazily to
    avoid circular imports between graph.py / nodes.py / prompt_builders.py.
    """
    from ..nodes import llm  # type: ignore[attr-defined]
    from ..prompt_builders import build_thought_critic_prompt

    return run_2b_thought_critic_node(
        state,
        llm=llm,
        build_thought_critic_prompt=build_thought_critic_prompt,
        print_fn=print,
    )
