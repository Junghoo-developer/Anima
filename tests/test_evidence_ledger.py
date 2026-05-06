import unittest

from Core.evidence_ledger import (
    append_evidence_event,
    build_initial_evidence_ledger,
    evidence_ledger_for_contract,
    evidence_ledger_for_prompt,
)
from Core.state import build_initial_anima_state


class EvidenceLedgerTests(unittest.TestCase):
    def test_initial_ledger_records_activity_sources_not_semantic_lanes(self):
        ledger = build_initial_evidence_ledger(
            user_input="네 이름은 뭐야?",
            current_time="2026-04-27 10:00",
            recent_context="[user]: hi",
            user_state="focused",
            user_char="direct",
            songryeon_thoughts="core notes",
            biolink_status="stable",
            working_memory={"active_task": "talk"},
        )

        kinds = [event["source_kind"] for event in ledger["events"]]
        self.assertIn("user_turn", kinds)
        self.assertIn("runtime_profile", kinds)
        self.assertIn("recent_dialogue", kinds)
        self.assertIn("working_memory_snapshot", kinds)
        self.assertNotIn("identity_question", kinds)
        runtime_events = [event for event in ledger["events"] if event["source_kind"] == "runtime_profile"]
        self.assertEqual(runtime_events[0]["source_ref"], "runtime_profile")
        self.assertNotIn("assistant_name", runtime_events[0]["content_excerpt"])

    def test_tool_activity_can_be_locked_to_an_event_id(self):
        ledger = build_initial_evidence_ledger(user_input="찾아봐")
        ledger = append_evidence_event(
            ledger,
            source_kind="tool_result",
            producer_node="phase_1_searcher",
            source_ref="tool_search_field_memos:abc",
            content={"tool_name": "tool_search_field_memos", "result_excerpt": "memo result"},
        )

        contract = evidence_ledger_for_contract(ledger)
        tool_events = [event for event in contract["events"] if event["source_kind"] == "tool_result"]

        self.assertEqual(len(tool_events), 1)
        self.assertTrue(tool_events[0]["event_id"].startswith("ev_"))
        self.assertIn("must not claim a DB/tool/source was used", contract["policy"])

    def test_initial_state_includes_evidence_ledger(self):
        state = build_initial_anima_state(
            user_input="hi",
            current_time="now",
            time_gap=0,
            recent_context="",
            global_tolerance=1,
            user_state="state",
            user_char="char",
            songryeon_thoughts="thoughts",
            tactical_briefing="brief",
            biolink_status="stable",
        )

        self.assertIn("evidence_ledger", state)
        self.assertIn("runtime_profile", evidence_ledger_for_prompt(state["evidence_ledger"]))


if __name__ == "__main__":
    unittest.main()
