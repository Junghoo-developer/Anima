import unittest

import Core.nodes as nodes
from Core.state import empty_anima_state


class ScrollPriorityTests(unittest.TestCase):
    def test_operation_plan_prefers_current_field_memo_contract_before_scroll(self):
        self.assertFalse(hasattr(nodes, "_preferred_decision_from_operation_plan"))

    def test_old_main_auditor_no_longer_owns_autonomous_scroll_decision(self):
        state = empty_anima_state()
        state["user_input"] = "Do you remember Sunny?"
        state["analysis_report"] = {
            "investigation_status": "INCOMPLETE",
            "situational_brief": "The current source drifted away from the Sunny question.",
            "contract_status": "wrong_source",
            "missing_slots": ["character.identity"],
            "rejected_sources": [{"source_id": "memory_bad_1"}],
            "can_answer_user_goal": False,
            "usable_field_memo_facts": [],
        }
        state["raw_read_report"] = {
            "read_mode": "full_raw_review",
            "items": [
                {
                    "source_type": "memory_node",
                    "source_id": "2026-03-18 22:09:54",
                    "excerpt": "Unrelated idea contest discussion.",
                }
            ],
        }
        state["tool_carryover"] = {
            "last_tool": "tool_search_memory",
            "origin_source_id": "2026-03-18 22:09:54",
            "last_target_id": "2026-03-18 22:09:54",
            "recommended_next_scroll": {
                "target_id": "2026-03-18 22:09:54",
                "direction": "both",
                "limit": 20,
            },
        }

        self.assertFalse(hasattr(nodes, "phase_minus_1b_auditor"))


if __name__ == "__main__":
    unittest.main()
