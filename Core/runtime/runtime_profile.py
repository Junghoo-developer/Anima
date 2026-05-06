"""Observable runtime profile for prompt packets.

This module deliberately avoids identity claims. It only exposes bounded facts
about the current runtime turn so LLM nodes can distinguish what the system
actually observed from what they still need to infer.
"""

from __future__ import annotations

import json
from typing import Any


RUNTIME_PROFILE_SCHEMA = "RuntimeProfile.v1"


def _clip_text(value: Any, limit: int = 360) -> str:
    text = str(value or "").strip()
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def build_runtime_profile(state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return bounded, code-observable runtime facts.

    This profile is not a memory source, identity source, or routing oracle.
    It only reports activity facts the runtime can observe directly.
    """
    state = state if isinstance(state, dict) else {}
    return {
        "schema": RUNTIME_PROFILE_SCHEMA,
        "runtime_inputs": {
            "current_time": _clip_text(state.get("current_time"), 80),
            "time_gap": state.get("time_gap", 0.0),
            "global_tolerance": state.get("global_tolerance", 1.0),
            "biolink_status": _clip_text(state.get("biolink_status"), 360),
        },
        "activity_status": {
            "execution_status": _clip_text(state.get("execution_status"), 80),
            "delivery_status": _clip_text(state.get("delivery_status"), 80),
            "loop_count": state.get("loop_count", 0),
        },
        "provenance_policy": (
            "Do not claim DB/search/tool access unless the evidence ledger or "
            "execution trace contains a matching observed event."
        ),
    }


def runtime_profile_for_prompt(state: dict[str, Any] | None = None) -> str:
    packet = build_runtime_profile(state)
    try:
        return json.dumps(packet, ensure_ascii=False, indent=2)
    except TypeError:
        return str(packet)


__all__ = [
    "RUNTIME_PROFILE_SCHEMA",
    "build_runtime_profile",
    "runtime_profile_for_prompt",
]
