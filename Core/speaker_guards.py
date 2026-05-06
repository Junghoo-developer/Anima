from langchain_core.messages import AIMessage

from . import nodes as base_nodes
from .state import AnimaState

def phase_3_validator_with_speaker_guard(state: AnimaState):
    """Single safety check: block internal-report leaks, otherwise let phase_3 speak."""
    result = base_nodes.phase_3_validator(state)
    if not isinstance(result, dict):
        return result
    speaker_review = {
        "delivery_ok": True,
        "should_remand": False,
        "issues": [],
        "mode": "thin_controller_single_safety_check",
    }
    messages = result.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage):
        normalized_text = base_nodes._normalize_user_facing_text(messages[-1].content)
        bad_output = (
            base_nodes._looks_like_internal_delivery_leak(normalized_text)
            or base_nodes._looks_like_user_parroting_report(normalized_text, state.get("user_input", ""))
        )
        if bad_output:
            speaker_review["delivery_ok"] = False
            speaker_review["should_remand"] = True
            speaker_review["issues"] = ["phase_3 output looked like an internal report or user parroting."]
            return {"messages": [], "speaker_review": speaker_review, "delivery_status": "remand"}
        result["messages"] = [AIMessage(content=normalized_text)]
    result["speaker_review"] = speaker_review
    result["delivery_status"] = "delivered"
    return result

