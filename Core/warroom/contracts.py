from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class WarRoomFreedom(BaseModel):
    granted: bool = Field(description="Whether non-tool reasoning freedom is currently granted.")
    granted_by: str = Field(description="Who most recently granted or denied the freedom.")
    scope: Literal["none", "planning_only", "bounded_speculation", "direct_empathy"] = Field(
        description="Permitted range of non-tool reasoning."
    )
    reason: Literal["none", "no_tool_needed", "no_suitable_tool", "tool_would_not_help", "user_requested_direct_thinking", "evidence_gap"] = Field(
        description="Operational reason for the current freedom state."
    )
    note: str = Field(description="Short explanation of the current freedom setting.")


class WarRoomDuty(BaseModel):
    must_label_hypotheses: bool = Field(description="Whether hypotheses must be labeled explicitly.")
    must_separate_fact_and_opinion: bool = Field(description="Whether facts and interpretations must stay separated.")
    must_report_missing_info: bool = Field(description="Whether missing information must be surfaced explicitly.")
    must_not_upgrade_guess_to_fact: bool = Field(description="Whether guesses must never be upgraded into facts.")
    boundary_note: str = Field(description="Short note about the current speech boundary.")


class WarRoomEpistemicDebt(BaseModel):
    debt_kind: List[str] = Field(description="Kinds of current epistemic debt, such as evidence_gap or tool_gap.")
    missing_items: List[str] = Field(description="Concrete missing items or unanswered points.")
    why_tool_not_used: str = Field(description="Why tools were not used or why they would not help enough.")
    next_best_action: str = Field(description="Best next action to reduce the debt.")


class WarRoomAgentNote(BaseModel):
    agent_name: str = Field(description="Agent that wrote this note, such as phase_2b, -1a, or -1b.")
    used_freedom: bool = Field(description="Whether the agent actually used non-tool reasoning freedom.")
    freedom_scope: str = Field(description="Scope of freedom used by the agent.")
    shortage_reason: str = Field(description="What was missing or constrained at this stage.")
    missing_items: List[str] = Field(description="Concrete missing items noticed by this agent.")
    why_no_tool: str = Field(description="Why the agent did not use tools or why tools were insufficient.")
    allowed_output_boundary: str = Field(description="What this agent believes may safely be said.")


class WarRoomStateV1(BaseModel):
    freedom: WarRoomFreedom
    duty: WarRoomDuty
    epistemic_debt: WarRoomEpistemicDebt
    agent_notes: List[WarRoomAgentNote]


class WarRoomDeliberationOutput(BaseModel):
    deliberation_status: Literal["COMPLETED", "NEEDS_REPLAN", "INSUFFICIENT"] = Field(
        default="COMPLETED",
        description="Whether the WarRoom produced a usable no-tool reasoning result.",
    )
    reasoning_summary: str = Field(default="", description="Short internal summary of the WarRoom reasoning.")
    usable_answer_seed: str = Field(default="", description="User-facing answer seed that phase_3 may transform naturally.")
    duty_checklist: List[str] = Field(default_factory=list, description="Checks showing freedom/duty/deficiency were respected.")
    missing_items: List[str] = Field(default_factory=list, description="Remaining missing items, if any.")
    confidence: float = Field(default=0.6, description="Confidence that the WarRoom result is usable.")


__all__ = [
    "Any",
    "Dict",
    "WarRoomAgentNote",
    "WarRoomDeliberationOutput",
    "WarRoomDuty",
    "WarRoomEpistemicDebt",
    "WarRoomFreedom",
    "WarRoomStateV1",
]
