import unittest

from langchain_core.messages import AIMessage
from langgraph.graph import END

import Core.nodes as nodes
from Core.graph import route_after_delivery_review
from Core.pipeline.delivery_review import (
    build_delivery_review_context,
    build_delivery_review_prompt,
    delivery_review_from_speaker_guard,
    normalize_delivery_review,
    run_phase3_delivery_review,
)
from Core.state import empty_anima_state


class _FakeStructuredResult:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self, **_kwargs):
        return dict(self._payload)


class _FakeReviewLLM:
    def __init__(self, payload=None, exc=None):
        self.payload = payload or {"verdict": "approve", "reason": "ok", "issues_found": []}
        self.exc = exc
        self.messages = None

    def with_structured_output(self, _schema):
        return self

    def invoke(self, messages):
        self.messages = messages
        if self.exc:
            raise self.exc
        return _FakeStructuredResult(self.payload)


def _attach(result, *_args, **_kwargs):
    return result


class DeliveryReviewContractTests(unittest.TestCase):
    def test_normalize_delivery_review_cannot_route_to_tools(self):
        review = normalize_delivery_review({
            "verdict": "remand",
            "reason": "Needs a better answer.",
            "issues_found": ["too vague"],
            "remand_target": "0_supervisor",
            "remand_guidance": "tool_search_memory(query='x')",
        })

        self.assertEqual(review["schema"], "DeliveryReview.v1")
        self.assertEqual(review["verdict"], "remand")
        self.assertEqual(review["remand_target"], "")
        self.assertNotIn("tool_search_memory", review["remand_guidance"])

    def test_speaker_guard_remand_maps_to_delivery_review(self):
        review = delivery_review_from_speaker_guard(
            {
                "should_remand": True,
                "issues": ["phase_3 output looked like an internal report"],
                "missing_for_delivery": ["clear user-facing answer"],
            },
            delivery_status="remand",
            loop_count=0,
            hard_stop=2,
        )

        self.assertEqual(review["verdict"], "remand")
        self.assertEqual(review["remand_target"], "-1a")
        self.assertIn("internal report", " ".join(review["issues_found"]))

    def test_speaker_guard_budget_exhaustion_maps_to_sos(self):
        review = delivery_review_from_speaker_guard(
            {"should_remand": True, "issues": ["unsafe answer"]},
            delivery_status="remand",
            loop_count=3,
            hard_stop=3,
        )

        self.assertEqual(review["verdict"], "sos_119")
        self.assertEqual(review["remand_target"], "")

    def test_delivery_review_context_is_bounded(self):
        context = build_delivery_review_context(
            {
                "user_input": "hello",
                "speaker_review": {"delivery_ok": True},
                "readiness_decision": {"status": "ready_for_direct_answer"},
                "phase3_delivery_payload": {
                    "answer_mode": "public_parametric_knowledge",
                    "ready_for_delivery": True,
                    "fallback_action": "",
                    "source_lane": "direct_dialogue",
                },
            },
            final_answer="hi",
        )

        self.assertEqual(context["schema"], "DeliveryReviewContext.v1")
        self.assertEqual(context["final_answer"], "hi")
        self.assertEqual(context["phase3_delivery_summary"]["answer_mode"], "public_parametric_knowledge")

    def test_delivery_review_context_includes_only_reviewer_evidence_surface(self):
        context = build_delivery_review_context(
            {
                "user_input": "써니의 누나는?",
                "analysis_report": {
                    "evidences": [{"claim": "써니의 누나는 마리다.", "source_id": "wiki"}],
                    "usable_field_memo_facts": ["송련의 이름은 송련이다."],
                    "missing_slots": ["location"],
                },
                "response_strategy": {
                    "must_include_facts": ["써니의 누나는 마리다."],
                    "must_avoid_claims": ["써니의 누나는 켈리다."],
                },
                "rescue_handoff_packet": {
                    "preserved_field_memo_facts": ["부분 사실"],
                    "attempted_path": ["hidden", "path"],
                },
                "s_thinking_packet": {"should": "not leak"},
                "working_memory": {"should": "not leak"},
                "reasoning_board": {"should": "not leak"},
            },
            final_answer="써니의 누나는 마리입니다.",
        )

        self.assertIn("analysis_report", context)
        self.assertIn("response_strategy", context)
        self.assertIn("rescue_handoff_packet", context)
        self.assertNotIn("s_thinking_packet", context)
        self.assertNotIn("working_memory", context)
        self.assertNotIn("reasoning_board", context)
        prompt = build_delivery_review_prompt(context)
        self.assertIn("Output DeliveryReview.v1 JSON only", prompt)
        self.assertIn("Do not call tools", prompt)

    def test_phase_delivery_review_approves_guarded_answer(self):
        state = empty_anima_state()
        state["user_input"] = "hello"
        state["messages"] = [AIMessage(content="hi")]
        state["speaker_review"] = {"delivery_ok": True, "should_remand": False, "issues": []}
        state["delivery_status"] = "delivered"

        original_llm = nodes.llm
        try:
            nodes.llm = _FakeReviewLLM({"verdict": "approve", "reason": "answer is supported", "issues_found": []})
            result = nodes.phase_delivery_review(state)
        finally:
            nodes.llm = original_llm

        self.assertEqual(result["delivery_review"]["verdict"], "approve")
        self.assertEqual(route_after_delivery_review({**state, **result}), END)

    def test_phase_delivery_review_remands_speaker_guard_failure(self):
        state = empty_anima_state()
        state["user_input"] = "hello"
        state["messages"] = []
        state["speaker_review"] = {
            "delivery_ok": False,
            "should_remand": True,
            "issues": ["phase_3 output looked like an internal report"],
        }
        state["delivery_status"] = "remand"
        state["reasoning_budget"] = 2

        original_llm = nodes.llm
        try:
            nodes.llm = _FakeReviewLLM({"verdict": "approve", "reason": "llm missed guard issue", "issues_found": []})
            result = nodes.phase_delivery_review(state)
        finally:
            nodes.llm = original_llm
        routed = route_after_delivery_review({**state, **result})

        self.assertEqual(result["delivery_review"]["verdict"], "remand")
        self.assertEqual(result["delivery_review"]["remand_target"], "-1a")
        self.assertEqual(result["loop_count"], 1)
        self.assertEqual(routed, "-1a_thinker")

    def test_delivery_review_rejection_counter_escalates_after_three_remands(self):
        state = empty_anima_state()
        state["user_input"] = "hello"
        state["speaker_review"] = {
            "delivery_ok": False,
            "should_remand": True,
            "issues": ["still leaking internals"],
        }
        state["delivery_status"] = "remand"
        state["reasoning_budget"] = 10
        state["delivery_review_rejections"] = 3

        original_llm = nodes.llm
        try:
            nodes.llm = _FakeReviewLLM({
                "verdict": "remand",
                "reason": "tone",
                "issues_found": ["still leaking internals"],
                "remand_target": "-1a",
            })
            result = nodes.phase_delivery_review(state)
        finally:
            nodes.llm = original_llm

        self.assertEqual(result["delivery_review_rejections"], 4)
        self.assertEqual(result["delivery_review"]["verdict"], "sos_119")
        self.assertEqual(route_after_delivery_review({**state, **result}), "phase_119")

    def test_llm_reviewer_remands_hallucinated_answer(self):
        state = empty_anima_state()
        state["messages"] = [AIMessage(content="써니의 누나는 켈리입니다.")]
        state["speaker_review"] = {"delivery_ok": True, "should_remand": False, "issues": []}
        state["delivery_status"] = "delivered"
        state["analysis_report"] = {"evidences": [{"claim": "써니의 누나는 마리다."}]}
        state["response_strategy"] = {"must_avoid_claims": ["써니의 누나는 켈리다."]}

        result = run_phase3_delivery_review(
            state,
            llm=_FakeReviewLLM({
                "verdict": "remand",
                "reason": "hallucination",
                "issues_found": ["answer cites unsupported sister name"],
                "remand_target": "-1a",
                "remand_guidance": "Rebuild the answer from accepted evidences only.",
            }),
            attach_ledger_event=_attach,
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result["delivery_review"]["verdict"], "remand")
        self.assertEqual(result["delivery_review"]["remand_target"], "-1a")
        self.assertIn("hallucination", result["delivery_review"]["reason"])

    def test_llm_reviewer_remands_omitted_required_fact(self):
        state = empty_anima_state()
        state["messages"] = [AIMessage(content="써니는 오모리의 주인공입니다.")]
        state["speaker_review"] = {"delivery_ok": True, "should_remand": False, "issues": []}
        state["delivery_status"] = "delivered"
        state["response_strategy"] = {
            "must_include_facts": ["써니는 오모리의 주인공이다.", "써니의 누나는 마리다."]
        }

        result = run_phase3_delivery_review(
            state,
            llm=_FakeReviewLLM({
                "verdict": "remand",
                "reason": "omission",
                "issues_found": ["missing required fact about Mari"],
                "remand_target": "-1a",
                "remand_guidance": "Include all must_include_facts or narrow the answer.",
            }),
            attach_ledger_event=_attach,
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result["delivery_review"]["verdict"], "remand")
        self.assertIn("omission", result["delivery_review"]["reason"])

    def test_llm_reviewer_remands_internal_workflow_leak(self):
        state = empty_anima_state()
        state["messages"] = [AIMessage(content="phase_119 rescue 결과로는 모릅니다.")]
        state["speaker_review"] = {"delivery_ok": True, "should_remand": False, "issues": []}
        state["delivery_status"] = "delivered"

        result = run_phase3_delivery_review(
            state,
            llm=_FakeReviewLLM({
                "verdict": "remand",
                "reason": "tone",
                "issues_found": ["internal workflow term leaked"],
                "remand_target": "-1s",
                "remand_guidance": "Restate the conversational boundary without internal labels.",
            }),
            attach_ledger_event=_attach,
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result["delivery_review"]["verdict"], "remand")
        self.assertEqual(result["delivery_review"]["remand_target"], "-1s")

    def test_llm_reviewer_can_request_sos_119(self):
        state = empty_anima_state()
        state["messages"] = [AIMessage(content="I cannot produce a stable answer.")]
        state["speaker_review"] = {"delivery_ok": True, "should_remand": False, "issues": []}
        state["delivery_status"] = "delivered"

        result = run_phase3_delivery_review(
            state,
            llm=_FakeReviewLLM({
                "verdict": "sos_119",
                "reason": "fundamentally unfixable within delivery loop",
                "issues_found": ["delivery loop cannot converge"],
                "remand_target": "",
                "remand_guidance": "Prepare a clean rescue handoff.",
            }),
            attach_ledger_event=_attach,
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result["delivery_review"]["verdict"], "sos_119")
        self.assertEqual(route_after_delivery_review({**state, **result}), "phase_119")

    def test_llm_reviewer_failure_falls_back_to_deterministic_guard(self):
        state = empty_anima_state()
        state["messages"] = [AIMessage(content="hi")]
        state["speaker_review"] = {"delivery_ok": True, "should_remand": False, "issues": []}
        state["delivery_status"] = "delivered"

        result = run_phase3_delivery_review(
            state,
            llm=_FakeReviewLLM(exc=ValueError("bad structured output")),
            attach_ledger_event=_attach,
            print_fn=lambda *_args, **_kwargs: None,
        )

        self.assertEqual(result["delivery_review"]["verdict"], "approve")
        self.assertIn("fallback", " ".join(result["delivery_review"]["issues_found"]))


if __name__ == "__main__":
    unittest.main()
