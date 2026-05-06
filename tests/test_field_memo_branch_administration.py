import unittest

import Core.field_memo as field_memo
from Core.field_memo import (
    INBOX_BRANCH_PATH,
    PENDING_BRANCH_STATUS,
    PENDING_FIELD_MEMO_STATUS,
    apply_branch_classification_decision,
    build_branch_classification_contract,
    build_branch_offices,
    build_field_memo_candidate,
    build_layered_memos,
    field_memo_has_official_branch,
    field_memo_needs_branch_classification,
)


class FieldMemoBranchAdministrationTests(unittest.TestCase):
    def test_field_writer_branch_is_saved_as_pending_hint_only(self):
        final_state = {
            "analysis_report": {
                "accepted_facts": ["The user says SongRyeon's Song means pine tree."],
            }
        }

        original = field_memo._field_memo_writer_decision
        try:
            field_memo._field_memo_writer_decision = lambda **kwargs: {
                "should_write": True,
                "memo_kind": "identity_fact",
                "known_facts": kwargs["candidate_facts"],
                "summary": "SongRyeon's Song means pine tree.",
                "entities": ["SongRyeon"],
                "branch_path": "CoreEgo/songryeon/name",
                "root_entity": "CoreEgo:songryeon",
                "confidence": 0.91,
            }
            candidate = build_field_memo_candidate(
                final_state,
                "SongRyeon's Song means pine tree.",
                "Got it.",
                {},
            )
        finally:
            field_memo._field_memo_writer_decision = original

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["branch_path"], INBOX_BRANCH_PATH)
        self.assertEqual(candidate["status"], PENDING_FIELD_MEMO_STATUS)
        self.assertEqual(candidate["branch_status"], PENDING_BRANCH_STATUS)
        self.assertEqual(candidate["proposed_branch_path"], "CoreEgo/songryeon/name")
        self.assertEqual(candidate["proposed_root_entity"], "CoreEgo:songryeon")
        self.assertFalse(field_memo_has_official_branch(candidate))
        self.assertTrue(field_memo_needs_branch_classification(candidate))

    def test_night_classification_promotes_official_branch(self):
        pending = {
            "memo_id": "field_memo::songryeon::1",
            "branch_path": INBOX_BRANCH_PATH,
            "status": PENDING_FIELD_MEMO_STATUS,
            "branch_status": PENDING_BRANCH_STATUS,
            "proposed_branch_path": "CoreEgo/songryeon/name",
            "proposed_root_entity": "CoreEgo:songryeon",
            "known_facts": ["The user says SongRyeon's Song means pine tree."],
        }

        contract = build_branch_classification_contract(pending)
        promoted = apply_branch_classification_decision(
            pending,
            {
                "classification_status": "approved",
                "official_branch_path": "CoreEgo/songryeon/name",
                "root_entity": "CoreEgo:songryeon",
                "classification_note": "Name fact belongs under SongRyeon's name branch.",
            },
        )

        self.assertEqual(contract["contract_type"], "field_memo_branch_classification")
        self.assertEqual(promoted["branch_path"], "CoreEgo/songryeon/name")
        self.assertEqual(promoted["official_branch_path"], "CoreEgo/songryeon/name")
        self.assertEqual(promoted["status"], "active")
        self.assertEqual(promoted["branch_status"], "active")
        self.assertTrue(field_memo_has_official_branch(promoted))

    def test_layered_memos_ignore_pending_inbox_memos(self):
        original_embed = field_memo._try_embed_text
        try:
            field_memo._try_embed_text = lambda *args, **kwargs: ([], "")
            pending_a = {
                "memo_id": "pending_a",
                "branch_path": INBOX_BRANCH_PATH,
                "status": PENDING_FIELD_MEMO_STATUS,
                "branch_status": PENDING_BRANCH_STATUS,
                "known_facts": ["pending fact a"],
                "summary": "pending a",
            }
            pending_b = {
                "memo_id": "pending_b",
                "branch_path": INBOX_BRANCH_PATH,
                "status": PENDING_FIELD_MEMO_STATUS,
                "branch_status": PENDING_BRANCH_STATUS,
                "known_facts": ["pending fact b"],
                "summary": "pending b",
            }
            official_a = {
                "memo_id": "official_a",
                "branch_path": "CoreEgo/songryeon/name",
                "root_entity": "CoreEgo:songryeon",
                "status": "active",
                "branch_status": "active",
                "known_facts": ["official fact a"],
                "summary": "official a",
            }
            official_b = {
                "memo_id": "official_b",
                "branch_path": "CoreEgo/songryeon/name",
                "root_entity": "CoreEgo:songryeon",
                "status": "active",
                "branch_status": "active",
                "known_facts": ["official fact b"],
                "summary": "official b",
            }

            layered = build_layered_memos([pending_a, pending_b, official_a, official_b])
        finally:
            field_memo._try_embed_text = original_embed

        self.assertEqual(len(layered), 1)
        self.assertEqual(layered[0]["branch_path"], "CoreEgo/songryeon/name")
        self.assertEqual(layered[0]["synthesis_source_memo_ids"], ["official_a", "official_b"])

    def test_branch_offices_ignore_pending_inbox_memos(self):
        pending = {
            "memo_id": "pending_a",
            "branch_path": INBOX_BRANCH_PATH,
            "status": PENDING_FIELD_MEMO_STATUS,
            "branch_status": PENDING_BRANCH_STATUS,
            "known_facts": ["pending fact"],
            "summary": "pending",
        }
        official = {
            "memo_id": "official_a",
            "branch_path": "CoreEgo/songryeon/name",
            "root_entity": "CoreEgo:songryeon",
            "status": "active",
            "branch_status": "active",
            "known_facts": ["official fact"],
            "summary": "official",
        }

        offices, reports = build_branch_offices([pending, official])

        self.assertEqual(len(offices), 1)
        self.assertEqual(offices[0]["branch_path"], "CoreEgo/songryeon/name")
        self.assertEqual(offices[0]["memo_ids"], ["official_a"])
        self.assertEqual(reports[0]["branch_path"], "CoreEgo/songryeon/name")


if __name__ == "__main__":
    unittest.main()
