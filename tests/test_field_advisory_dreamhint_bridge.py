import unittest

from Core.adapters.night_queries import recent_tactical_briefing


class FakeDreamHintSession:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query, **params):
        self.calls.append((query, params))
        return self.rows


class FieldAdvisoryDreamHintBridgeTests(unittest.TestCase):
    def test_recent_tactical_briefing_reads_active_dreamhint(self):
        session = FakeDreamHintSession(
            [
                {
                    "dreamhint_key": "dh::1",
                    "hint_text": "Use the diary search boundary clearly.",
                    "source_persona": "future_decision_maker",
                    "branch_path": "Time/2026/05/field-loop",
                    "created_at": 1,
                }
            ]
        )

        result = recent_tactical_briefing(8, session_factory=lambda: session)

        self.assertIn("[active DreamHint advisories]", result)
        self.assertIn("Use the diary search boundary clearly.", result)
        self.assertIn("branch=Time/2026/05/field-loop", result)
        self.assertIn("source_persona=future_decision_maker", result)

    def test_recent_tactical_briefing_reports_no_active_dreamhints(self):
        session = FakeDreamHintSession()

        result = recent_tactical_briefing(8, session_factory=lambda: session)

        self.assertEqual(result, "[advisory] No active DreamHint records.")

    def test_recent_tactical_briefing_uses_archive_and_expiry_filters(self):
        session = FakeDreamHintSession()

        result = recent_tactical_briefing(8, session_factory=lambda: session)
        query = "\n".join(call[0] for call in session.calls)

        self.assertEqual(result, "[advisory] No active DreamHint records.")
        self.assertIn("MATCH (dh:DreamHint)", query)
        self.assertIn("coalesce(dh.archive_at, 9999999999999) > timestamp()", query)
        self.assertIn("coalesce(dh.expires_at, 9999999999999) > timestamp()", query)
        self.assertNotIn("TacticalThought", query)


if __name__ == "__main__":
    unittest.main()
