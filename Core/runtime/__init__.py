"""Runtime boundary helpers for ANIMA.

This package owns observable runtime context packets and turn cleanup imports.
It should not read databases, infer user intent, define identity, or route the
graph.
"""

from .cleanup import LONG_LIVED_FIELDS, TURN_LIVED_FIELDS, cleanup_turn_lived_fields
from .context_packet import (
    append_cycle_to_history,
    build_cumulative_s_thinking_packet,
    build_runtime_context_packet,
    compact_s_thinking_cycle,
    normalize_s_thinking_history,
    runtime_context_packet_for_prompt,
    s_thinking_history_for_prompt,
)
from .runtime_profile import build_runtime_profile, runtime_profile_for_prompt

__all__ = [
    "LONG_LIVED_FIELDS",
    "TURN_LIVED_FIELDS",
    "append_cycle_to_history",
    "build_cumulative_s_thinking_packet",
    "build_runtime_context_packet",
    "build_runtime_profile",
    "compact_s_thinking_cycle",
    "cleanup_turn_lived_fields",
    "normalize_s_thinking_history",
    "runtime_context_packet_for_prompt",
    "runtime_profile_for_prompt",
    "s_thinking_history_for_prompt",
]
