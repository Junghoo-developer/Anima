"""Contracts for the V4 future department."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from Core.midnight.past.contracts import PastAssemblyOutput
from Core.midnight.present.contracts import PresentSecondDreamOutput


@dataclass(frozen=True)
class PastAssemblyMockInput:
    """Temporary R3 input until the past department is implemented in R4."""

    past_assembly_thought: str
    election_result: bool
    change_proposal: dict[str, Any] = field(default_factory=dict)


PastAssemblyInput = PastAssemblyOutput | PastAssemblyMockInput
PresentSecondDreamInput = PresentSecondDreamOutput
