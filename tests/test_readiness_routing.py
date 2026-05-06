import unittest

from Core.graph import route_audit_result_v2
from Core.readiness import readiness_from_auditor_action
from Core.state import empty_anima_state


class ReadinessRoutingTests(unittest.TestCase):
    def test_readiness_overrides_legacy_phase3_action_when_tool_evidence_is_needed(self):
        state = empty_anima_state()
        state["auditor_decision"] = {
            "action": "phase_3",
            "readiness_decision": readiness_from_auditor_action(
                "call_tool",
                memo="Need a real tool result first.",
                tool_name="tool_search_memory",
                tool_args={"keyword": "송련"},
            ),
        }

        self.assertEqual(route_audit_result_v2(state), "0_supervisor")

    def test_clean_failure_readiness_can_request_phase119_preparation(self):
        state = empty_anima_state()
        state["auditor_decision"] = {
            "action": "phase_3",
            "readiness_decision": readiness_from_auditor_action(
                "phase_119",
                memo="Loop is exhausted.",
            ),
        }

        self.assertEqual(route_audit_result_v2(state), "phase_119")

    def test_legacy_answer_not_ready_without_readiness_still_compat_routes_phase3(self):
        state = empty_anima_state()
        state["auditor_decision"] = {"action": "answer_not_ready", "memo": "legacy"}

        self.assertEqual(route_audit_result_v2(state), "phase_3")


if __name__ == "__main__":
    unittest.main()
