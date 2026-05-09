import unittest
import json

from Core.pipeline.packets import (
    analysis_packet_for_prompt,
    compact_rescue_handoff_for_prompt,
    compact_s_thinking_packet_for_prompt,
    reasoning_board_packet_for_prompt,
    raw_read_report_packet_for_prompt,
    source_relay_packet_for_prompt,
    working_memory_packet_for_prompt,
)
from Core.pipeline.strategy import project_state_for_strategist


class StrategyProjectionTests(unittest.TestCase):
    def test_projection_excludes_turn_cache_bulk(self):
        state = {
            "user_input": "What should we do next?",
            "recent_context": "recent",
            "search_results": "x" * 5000,
            "tool_result_cache": {"huge": "x" * 5000},
            "phase3_delivery_packet": {"answer_seed": "internal"},
            "messages": ["hidden turn transcript"],
            "strategist_goal": {
                "user_goal_core": "Answer the current memory behavior question.",
                "answer_mode_target": "memory_recall",
                "success_criteria": ["answer the asked question"],
                "scope": "narrow",
            },
            "normalized_goal": {
                "user_goal_core": "Legacy duplicate that should not be projected separately.",
                "answer_mode_target": "ambiguous",
                "success_criteria": [],
                "scope": "broad",
            },
            "s_thinking_packet": {
                "schema": "SThinkingPacket.v1",
                "routing_decision": {"next_node": "-1a", "reason": "needs planner"},
            },
            "working_memory": {
                "turn_summary": "summary",
                "last_turn": {"user_input": "raw", "assistant_answer": "raw"},
                "memory_writer": {
                    "short_term_context": "context",
                    "active_topic": "memory audit",
                    "unresolved_user_request": "explain memory behavior",
                    "assistant_obligation_next_turn": "answer directly",
                },
            },
        }

        projected = project_state_for_strategist(state)

        self.assertNotIn("search_results", projected)
        self.assertNotIn("tool_result_cache", projected)
        self.assertNotIn("phase3_delivery_packet", projected)
        self.assertNotIn("messages", projected)
        self.assertNotIn("normalized_goal", projected)
        self.assertEqual(projected["strategist_goal"]["answer_mode_target"], "memory_recall")
        self.assertNotIn("last_turn", projected["working_memory"])
        self.assertEqual(projected["s_thinking_packet"]["schema"], "ThinkingHandoff.v1")
        self.assertEqual(projected["working_memory"]["memory_writer"]["active_topic"], "memory audit")
        self.assertNotIn("short_term_context", projected["working_memory"]["memory_writer"])

    def test_projection_excludes_judge_surfaces_and_exposes_fact_cells(self):
        long_text = "x" * 2000
        state = {
            "tactical_briefing": "advisory should move to -1s only",
            "raw_read_report": {
                "read_mode": "full_raw_review",
                "items": [
                    {
                        "source_id": f"source-{idx}",
                        "source_type": "memory_node",
                        "excerpt": long_text,
                        "observed_fact": long_text,
                    }
                    for idx in range(20)
                ],
            },
            "analysis_report": {
                "investigation_status": "COMPLETED",
                "analytical_thought": long_text,
                "evidences": [
                    {"source_id": f"source-{idx}", "source_type": "memory_node", "extracted_fact": long_text}
                    for idx in range(20)
                ],
                "source_judgments": [
                    {"source_id": f"source-{idx}", "accepted_facts": [long_text]}
                    for idx in range(20)
                ],
            },
            "reasoning_board": {
                "fact_cells": [
                    {
                        "fact_id": f"fact-{idx}",
                        "claim": f"legacy claim {idx}",
                        "source_id": f"source-{idx}",
                        "source_type": "memory_node",
                        "excerpt": long_text,
                    }
                    for idx in range(12)
                ],
                "verdict_board": {"judge_notes": ["should not project the whole board"]},
            },
        }

        projected = project_state_for_strategist(state)

        self.assertNotIn("raw_read_report", projected)
        self.assertNotIn("analysis_report", projected)
        self.assertNotIn("reasoning_board", projected)
        self.assertNotIn("tactical_briefing", projected)
        self.assertEqual(len(projected["fact_cells_for_strategist"]), 10)
        self.assertEqual(projected["fact_cells_for_strategist"][0]["fact_id"], "fact-0")
        self.assertEqual(projected["fact_cells_for_strategist"][0]["extracted_fact"], "legacy claim 0")
        self.assertIn("excerpt", projected["fact_cells_for_strategist"][0])

    def test_working_memory_prompt_packet_excludes_bulk_last_turn(self):
        packet_text = working_memory_packet_for_prompt({
            "turn_summary": "This turn should stay visible.",
            "last_turn": {
                "user_input": "raw user transcript should not be forwarded",
                "assistant_answer": "raw assistant transcript should not be forwarded",
            },
            "dialogue_state": {
                "user_dialogue_act": "question_or_request",
                "assistant_last_move": "answered",
                "pending_question": "Do we still need to answer?",
            },
            "memory_writer": {
                "short_term_context": "User is checking memory behavior.",
                "active_topic": "memory audit",
                "unresolved_user_request": "Explain what the agent remembers.",
                "assistant_obligation_next_turn": "Answer directly.",
                "ephemeral_notes": [f"note-{idx}" for idx in range(20)],
                "durable_fact_candidates": [f"fact-{idx}" for idx in range(20)],
            },
            "evidence_state": {
                "last_investigation_status": "COMPLETED",
                "verdict_action": "ready_for_delivery",
                "active_source_ids": [f"source-{idx}" for idx in range(20)],
                "evidence_facts": [f"evidence-{idx}" for idx in range(20)],
                "unresolved_questions": [f"question-{idx}" for idx in range(20)],
            },
            "response_contract": {
                "reply_mode": "grounded_answer",
                "answer_goal": "Answer the current memory question.",
                "must_include_facts": [f"include-{idx}" for idx in range(20)],
                "must_avoid_claims": [f"avoid-{idx}" for idx in range(20)],
            },
        })

        self.assertNotIn("last_turn", packet_text)
        self.assertNotIn("raw user transcript", packet_text)
        self.assertNotIn("raw assistant transcript", packet_text)

        packet = json.loads(packet_text)
        self.assertEqual(packet["turn_summary"], "This turn should stay visible.")
        self.assertEqual(packet["memory_writer"]["short_term_context"], "User is checking memory behavior.")
        self.assertEqual(len(packet["memory_writer"]["ephemeral_notes"]), 4)
        self.assertEqual(len(packet["evidence_state"]["active_source_ids"]), 6)
        self.assertEqual(len(packet["response_contract"]["must_include_facts"]), 5)

    def test_working_memory_role_whitelists(self):
        working_memory = {
            "turn_summary": "visible only to readiness",
            "dialogue_state": {
                "user_dialogue_act": "question_or_request",
                "assistant_last_move": "answered",
                "pending_dialogue_act": {"kind": "answer", "target": "continue the joke"},
                "active_task": "internal strategy text must not leak",
            },
            "memory_writer": {
                "short_term_context": "immediate context",
                "active_topic": "memory audit",
                "unresolved_user_request": "explain the behavior",
                "assistant_obligation_next_turn": "answer the pending request",
                "ephemeral_notes": ["hidden note"],
                "durable_fact_candidates": ["candidate fact"],
            },
            "evidence_state": {
                "last_investigation_status": "COMPLETED",
                "verdict_action": "ready_for_delivery",
                "active_source_ids": ["source-1"],
                "evidence_facts": ["fact-1"],
                "unresolved_questions": ["gap-1"],
            },
            "response_contract": {
                "reply_mode": "grounded_answer",
                "answer_goal": "answer",
                "must_include_facts": ["fact-1"],
                "must_avoid_claims": ["claim-1"],
            },
        }

        strategist = json.loads(working_memory_packet_for_prompt(working_memory, role="strategist"))
        readiness = json.loads(working_memory_packet_for_prompt(working_memory, role="readiness"))
        fact_judge = json.loads(working_memory_packet_for_prompt(working_memory, role="fact_judge"))
        phase3 = json.loads(working_memory_packet_for_prompt(working_memory, role="phase_3"))

        self.assertEqual(set(strategist.keys()), {"dialogue_state", "memory_writer", "evidence_state"})
        self.assertIn("active_topic", strategist["memory_writer"])
        self.assertNotIn("short_term_context", strategist["memory_writer"])

        self.assertEqual(set(readiness.keys()), {"turn_summary", "response_contract"})
        self.assertNotIn("dialogue_state", readiness)

        self.assertEqual(set(fact_judge.keys()), {"evidence_state"})
        self.assertIn("evidence_facts", fact_judge["evidence_state"])

        self.assertEqual(set(phase3.keys()), {"short_term_context", "assistant_obligation_next_turn", "pending_dialogue_act", "dialogue_state"})
        self.assertEqual(phase3["short_term_context"], "immediate context")
        self.assertIn("assistant_obligation_next_turn", phase3)
        self.assertNotIn("active_topic", phase3)
        self.assertNotIn("ephemeral_notes", phase3)
        self.assertNotIn("internal strategy text", json.dumps(phase3, ensure_ascii=False))

    def test_prompt_packets_bound_raw_analysis_and_source_relay(self):
        long_text = "x" * 3000
        raw_packet = json.loads(raw_read_report_packet_for_prompt({
            "read_mode": "full_raw_review",
            "reviewed_all_input": True,
            "source_summary": long_text,
            "coverage_notes": long_text,
            "items": [
                {
                    "source_id": f"source-{idx}",
                    "source_type": "diary",
                    "excerpt": long_text,
                    "observed_fact": long_text,
                }
                for idx in range(30)
            ],
        }))
        analysis_packet = json.loads(analysis_packet_for_prompt({
            "investigation_status": "COMPLETED",
            "analytical_thought": long_text,
            "evidences": [
                {"source_id": f"source-{idx}", "source_type": "diary", "extracted_fact": long_text}
                for idx in range(30)
            ],
            "source_judgments": [
                {"source_id": f"source-{idx}", "accepted_facts": [long_text]}
                for idx in range(30)
            ],
        }))
        relay_packet = json.loads(source_relay_packet_for_prompt({
            "read_mode": "full_raw_review",
            "reviewed_all_input": True,
            "global_source_summary": long_text,
            "global_coverage_notes": long_text,
            "source_packets": [
                {
                    "source_id": f"source-{idx}",
                    "source_type": "diary",
                    "source_summary": long_text,
                    "coverage_notes": long_text,
                    "must_forward_facts": [long_text] * 12,
                    "quoted_excerpts": [long_text] * 12,
                    "coverage_complete": True,
                }
                for idx in range(30)
            ],
        }))

        self.assertEqual(len(raw_packet["items"]), 12)
        self.assertLessEqual(len(raw_packet["items"][0]["excerpt"]), 900)
        self.assertEqual(len(analysis_packet["evidences"]), 10)
        self.assertEqual(len(analysis_packet["source_judgments"]), 8)
        self.assertLessEqual(len(analysis_packet["analytical_thought"]), 900)
        self.assertEqual(len(relay_packet["source_packets"]), 12)
        self.assertEqual(len(relay_packet["source_packets"][0]["must_forward_facts"]), 6)
        self.assertLessEqual(len(relay_packet["source_packets"][0]["quoted_excerpts"][0]), 700)

    def test_analysis_role_projection_keeps_node_specific_fields(self):
        long_text = "x" * 2000
        analysis = {
            "investigation_status": "COMPLETED",
            "contract_status": "satisfied",
            "can_answer_user_goal": True,
            "missing_slots": ["gap"],
            "situational_brief": long_text,
            "analytical_thought": long_text,
            "evidences": [
                {"source_id": f"source-{idx}", "source_type": "diary", "extracted_fact": f"fact-{idx}"}
                for idx in range(12)
            ],
            "source_judgments": [
                {"source_id": f"source-{idx}", "source_type": "diary", "source_status": "pass", "accepted_facts": [f"accepted-{idx}"]}
                for idx in range(12)
            ],
            "usable_field_memo_facts": [f"memo-{idx}" for idx in range(12)],
        }

        strategist = json.loads(analysis_packet_for_prompt(analysis, role="strategist"))
        readiness = json.loads(analysis_packet_for_prompt(analysis, role="readiness"))
        delivery = json.loads(analysis_packet_for_prompt(analysis, role="phase_3"))

        self.assertIn("evidences", strategist)
        self.assertIn("usable_field_memo_facts", strategist)
        self.assertNotIn("source_judgments", strategist)
        self.assertLessEqual(len(strategist["analytical_thought"]), 420)

        self.assertIn("source_judgments", readiness)
        self.assertLessEqual(len(readiness["source_judgments"]), 6)

        self.assertEqual(set(delivery.keys()), {"investigation_status", "contract_status", "usable_field_memo_facts", "accepted_facts"})
        self.assertEqual(len(delivery["accepted_facts"]), 6)

    def test_s_thinking_and_rescue_prompt_packets_are_bounded(self):
        s_packet = compact_s_thinking_packet_for_prompt(
            {
                "schema": "SThinkingPacket.v1",
                "situation_thinking": {
                    "user_intent": "ask",
                    "domain": "memory_recall",
                    "key_facts_needed": [f"fact-{idx}" for idx in range(10)],
                    "extra": "drop me",
                },
                "loop_summary": {
                    "attempted_so_far": [f"step-{idx}" for idx in range(10)],
                    "current_evidence_state": "x" * 1000,
                    "gaps": [f"gap-{idx}" for idx in range(10)],
                },
                "next_direction": {"suggested_focus": "y" * 1000, "avoid": [f"avoid-{idx}" for idx in range(10)]},
                "routing_decision": {"next_node": "-1a", "reason": "z" * 1000},
                "unknown_section": "drop me",
            },
            role="strategist",
        )
        self.assertLessEqual(len(s_packet["what_is_missing"]), 8)
        self.assertNotIn("unknown_section", s_packet)
        self.assertLessEqual(len(s_packet["next_node_reason"]), 220)

        rescue = compact_rescue_handoff_for_prompt(
            {
                "schema": "RescueHandoffPacket.v1",
                "trigger": "budget_exceeded",
                "attempted_path": [f"internal-step-{idx}" for idx in range(20)],
                "preserved_evidences": [
                    {"source_id": f"s-{idx}", "source_type": "diary", "extracted_fact": "x" * 1000}
                    for idx in range(20)
                ],
                "preserved_field_memo_facts": ["y" * 1000 for _ in range(20)],
                "rejected_only": [{"source_id": "bad", "reason": "wrong goal"}],
                "what_we_know": ["known"] * 20,
                "what_we_failed": ["failed"] * 20,
                "speaker_tone_hint": "사과 + 부분정보",
                "user_facing_label": "재시도 필요",
            }
        )
        self.assertNotIn("trigger", rescue)
        self.assertLessEqual(len(rescue["attempted_path_summary"]), 4)
        self.assertLessEqual(len(rescue["preserved_evidences"]), 6)
        self.assertLessEqual(len(rescue["what_we_failed"]), 4)

    def test_reasoning_board_role_projection_limits_node_views(self):
        board = {
            "fact_cells": [
                {"fact_id": f"f{idx}", "claim": "x" * 1000, "source_id": f"s{idx}", "extra": "drop"}
                for idx in range(20)
            ],
            "candidate_pairs": [
                {"pair_id": f"p{idx}", "claim": f"claim-{idx}", "audit_status": "approved", "extra": "drop"}
                for idx in range(20)
            ],
            "open_questions": [f"q{idx}" for idx in range(20)],
            "search_requests": [f"search-{idx}" for idx in range(20)],
            "final_fact_ids": ["f1", "f2"],
            "final_pair_ids": ["p1"],
            "must_avoid_claims": [f"avoid-{idx}" for idx in range(20)],
            "direct_answer_seed": "seed",
            "strategist_plan": {
                "case_theory": "theory",
                "action_plan": {"current_step_goal": "goal", "required_tool": "tool_search_field_memos"},
            },
            "critic_report": {"long_note": "y" * 2000},
            "advocate_report": {"should_not": "be in readiness"},
            "verdict_board": {"verdict": "approved", "notes": ["note"]},
        }

        strategist = json.loads(reasoning_board_packet_for_prompt(board, role="strategist"))
        readiness = json.loads(reasoning_board_packet_for_prompt(board, role="readiness"))
        phase3 = json.loads(reasoning_board_packet_for_prompt(board, role="phase_3"))

        self.assertEqual(len(strategist["fact_cells"]), 8)
        self.assertNotIn("candidate_pairs", strategist)
        self.assertEqual(strategist["candidate_pair_count"], 20)
        self.assertIn("search_requests", strategist)

        self.assertNotIn("fact_cells", readiness)
        self.assertNotIn("advocate_report", readiness)
        self.assertEqual(readiness["candidate_pair_count"], 20)
        self.assertIn("verdict_board", readiness)

        self.assertIn("final_fact_cells", phase3)
        self.assertIn("approved_pairs", phase3)
        self.assertNotIn("search_requests", phase3)


if __name__ == "__main__":
    unittest.main()
