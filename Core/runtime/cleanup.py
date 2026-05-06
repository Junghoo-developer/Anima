"""Turn-lifecycle cleanup boundary.

The implementation lives in Core.state for now because the public AnimaState
TypedDict still lives there. This module gives future runtime code a stable
import path without changing behavior.
"""

from __future__ import annotations

from ..state import LONG_LIVED_FIELDS, TURN_LIVED_FIELDS, cleanup_turn_lived_fields

__all__ = [
    "LONG_LIVED_FIELDS",
    "TURN_LIVED_FIELDS",
    "cleanup_turn_lived_fields",
]
