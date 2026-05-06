import builtins
import json
import math
import ollama
import os
import pymysql
import sys
import unicodedata
from dotenv import load_dotenv
from .request_intents_v4 import (
    is_directive_or_correction_turn,
)
from .temporal_context import build_temporal_context_signal as shared_build_temporal_context_signal
from .memory.working_memory_writer import (
    memory_facts_from_analysis as _writer_memory_facts_from_analysis,
    normalize_memory_writer_draft as _writer_normalize_memory_writer_draft,
    normalize_pending_dialogue_act as _writer_normalize_pending_dialogue_act,
    write_working_memory_with_llm as _write_working_memory_with_llm_boundary,
)

# Load environment variables for DB access.
load_dotenv()

# DB settings shared with main/tools.
DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from tools.process_daily_memory import log_message_to_db
except ImportError:
    from tools.process_daily_memory import log_message_to_db


def _safe_print(message: str):
    text = str(message)
    try:
        builtins.print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        builtins.print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def _dedupe_keep_order(items):
    seen = set()
    result = []
    for item in items:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _shorten(text, limit=240):
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _looks_like_internal_strategy_text(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", str(text or "").strip()).lower()
    if not normalized:
        return False
    markers = [
        "answer mode policy",
        "answer_mode_policy",
        "current approved evidence boundary",
        "current user ask",
        "current user turn",
        "deliver the best grounded answer",
        "direct evidence for the current answer",
        "fieldmemo filter",
        "goal contract",
        "grounded source",
        "grounded recall",
        "memory.referent_fact",
        "missing_slot",
        "missing slots",
        "operation_plan",
        "phase_",
        "phase 0",
        "phase 1",
        "phase 2",
        "phase 3",
        "public parametric knowledge",
        "read one stronger",
        "replan",
        "respond to the current user turn",
        "source_judgments",
        "tool_search",
        "usable_field_memo_facts",
        "use the facts supplied",
    ]
    return any(marker in normalized for marker in markers)


def _memory_safe_text(text: str, limit: int = 180) -> str:
    value = str(text or "").strip()
    if not value or _looks_like_internal_strategy_text(value):
        return ""
    return _shorten(value, limit)


def _memory_facts_from_analysis(analysis_report: dict, limit: int = 3) -> list[str]:
    return _writer_memory_facts_from_analysis(analysis_report, limit=limit)


def _json_object_from_text(text: str) -> dict:
    value = str(text or "").strip()
    if not value:
        return {}
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        pass
    start = value.find("{")
    end = value.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        loaded = json.loads(value[start : end + 1])
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_pending_dialogue_act(value) -> dict:
    return _writer_normalize_pending_dialogue_act(value)


def _normalize_memory_writer_draft(value) -> dict:
    return _writer_normalize_memory_writer_draft(value)


class MemoryBuffer:
    def __init__(self, model_name="gemma4:e4b", max_context=30):
        self.model = model_name
        self.max_context = max_context * 2
        self.history = []
        self.summary = ""
        self.working_memory = self._default_working_memory()

        self._load_recent_history_from_db()
        self._load_latest_working_memory_from_db()

    def _default_working_memory(self):
        return {
            "version": "working_memory_v2",
            "dialogue_state": {
                "user_dialogue_act": "",
                "assistant_last_move": "",
                "pending_question": "",
                "pending_dialogue_act": {
                    "kind": "none",
                    "target": "",
                    "expected_user_responses": [],
                    "expires_after_turns": 0,
                    "confidence": 0.0,
                },
                "active_task": "",
                "active_task_source": "",
                "active_offer": "",
                "active_offer_source": "",
                "conversation_mode": "",
                "continuation_expected": False,
                "initiative_requested": False,
                "requested_assistant_move": "",
                "task_reset_applied": False,
                "task_reset_reason": "",
                "user_feedback_signal": "",
            },
            "temporal_context": {
                "current_input_anchor": "",
                "continuity_score": 0.0,
                "topic_shift_score": 0.0,
                "topic_reset_confidence": 0.0,
                "carry_over_strength": 0.0,
                "active_task_bias": 0.0,
                "carry_over_allowed": False,
                "candidate_parent_turn_ids": [],
                "recent_match_briefs": [],
            },
            "evidence_state": {
                "last_investigation_status": "",
                "verdict_action": "",
                "active_source_ids": [],
                "evidence_facts": [],
                "unresolved_questions": [],
                "judge_notes": [],
            },
            "memory_writer": {
                "short_term_context": "",
                "active_topic": "",
                "unresolved_user_request": "",
                "assistant_obligation_next_turn": "",
                "ephemeral_notes": [],
                "durable_fact_candidates": [],
                "field_memo_write_recommendation": "skip",
                "confidence": 0.0,
            },
            "tool_carryover": {
                "version": "tool_carryover_v1",
                "last_tool": "",
                "last_query": "",
                "last_target_id": "",
                "last_direction": "",
                "last_limit": 0,
                "origin_source_id": "",
                "origin_query": "",
                "axis": "time",
                "source_ids": [],
                "candidate_ids": [],
                "available_followups": [],
                "recommended_next_scroll": {},
            },
            "response_contract": {
                "reply_mode": "",
                "answer_goal": "",
                "must_include_facts": [],
                "must_avoid_claims": [],
                "direct_answer_seed": "",
            },
            "user_model_delta": {
                "observed_preferences": [],
                "friction_points": [],
                "tone_preferences": [],
            },
            "last_turn": {
                "user_input": "",
                "assistant_answer": "",
                "auditor_instruction": "",
                "loop_count": 0,
                "used_sources": [],
            },
            "turn_summary": "Structured working memory has not been written yet.",
        }

    def _normalize_text(self, value, fallback=""):
        return str(value or fallback).strip()

    def _normalize_list(self, values, limit=6):
        if not isinstance(values, list):
            values = [values] if values else []
        return _dedupe_keep_order(values)[:limit]

    def _normalize_working_memory(self, data):
        base = self._default_working_memory()
        if not isinstance(data, dict):
            if isinstance(data, str) and data.strip():
                base["turn_summary"] = data.strip()
            return base

        for section in ("dialogue_state", "evidence_state", "memory_writer", "response_contract", "user_model_delta", "last_turn"):
            if isinstance(data.get(section), dict):
                base[section].update(data[section])
        if isinstance(data.get("temporal_context"), dict):
            base["temporal_context"].update(data["temporal_context"])
        if isinstance(data.get("tool_carryover"), dict):
            base["tool_carryover"].update(data["tool_carryover"])

        base["dialogue_state"]["user_dialogue_act"] = self._normalize_text(
            base["dialogue_state"].get("user_dialogue_act")
        )
        base["dialogue_state"]["assistant_last_move"] = self._normalize_text(
            base["dialogue_state"].get("assistant_last_move")
        )
        base["dialogue_state"]["pending_question"] = self._normalize_text(
            base["dialogue_state"].get("pending_question")
        )
        base["dialogue_state"]["pending_dialogue_act"] = _normalize_pending_dialogue_act(
            base["dialogue_state"].get("pending_dialogue_act")
        )
        base["dialogue_state"]["active_task"] = _memory_safe_text(
            base["dialogue_state"].get("active_task"),
            180,
        )
        base["dialogue_state"]["active_task_source"] = self._normalize_text(
            base["dialogue_state"].get("active_task_source")
        )
        base["dialogue_state"]["active_offer"] = _memory_safe_text(
            base["dialogue_state"].get("active_offer"),
            220,
        )
        base["dialogue_state"]["active_offer_source"] = self._normalize_text(
            base["dialogue_state"].get("active_offer_source")
        )
        base["dialogue_state"]["conversation_mode"] = self._normalize_text(
            base["dialogue_state"].get("conversation_mode")
        )
        base["dialogue_state"]["continuation_expected"] = bool(
            base["dialogue_state"].get("continuation_expected")
        )
        base["dialogue_state"]["initiative_requested"] = bool(
            base["dialogue_state"].get("initiative_requested")
        )
        base["dialogue_state"]["requested_assistant_move"] = self._normalize_text(
            base["dialogue_state"].get("requested_assistant_move")
        )
        base["dialogue_state"]["task_reset_applied"] = bool(
            base["dialogue_state"].get("task_reset_applied")
        )
        base["dialogue_state"]["task_reset_reason"] = self._normalize_text(
            base["dialogue_state"].get("task_reset_reason")
        )
        base["dialogue_state"]["user_feedback_signal"] = self._normalize_text(
            base["dialogue_state"].get("user_feedback_signal")
        )

        try:
            base["temporal_context"]["continuity_score"] = float(
                base["temporal_context"].get("continuity_score", 0.0) or 0.0
            )
        except (TypeError, ValueError):
            base["temporal_context"]["continuity_score"] = 0.0
        try:
            base["temporal_context"]["topic_shift_score"] = float(
                base["temporal_context"].get("topic_shift_score", 0.0) or 0.0
            )
        except (TypeError, ValueError):
            base["temporal_context"]["topic_shift_score"] = 0.0
        try:
            base["temporal_context"]["topic_reset_confidence"] = float(
                base["temporal_context"].get("topic_reset_confidence", 0.0) or 0.0
            )
        except (TypeError, ValueError):
            base["temporal_context"]["topic_reset_confidence"] = 0.0
        try:
            base["temporal_context"]["carry_over_strength"] = float(
                base["temporal_context"].get("carry_over_strength", 0.0) or 0.0
            )
        except (TypeError, ValueError):
            base["temporal_context"]["carry_over_strength"] = 0.0
        try:
            base["temporal_context"]["active_task_bias"] = float(
                base["temporal_context"].get("active_task_bias", 0.0) or 0.0
            )
        except (TypeError, ValueError):
            base["temporal_context"]["active_task_bias"] = 0.0
        base["temporal_context"]["carry_over_allowed"] = bool(
            base["temporal_context"].get("carry_over_allowed")
        )
        base["temporal_context"]["current_input_anchor"] = self._normalize_text(
            base["temporal_context"].get("current_input_anchor")
        )
        base["temporal_context"]["candidate_parent_turn_ids"] = self._normalize_list(
            base["temporal_context"].get("candidate_parent_turn_ids"), limit=4
        )
        base["temporal_context"]["recent_match_briefs"] = self._normalize_list(
            base["temporal_context"].get("recent_match_briefs"), limit=4
        )

        base["evidence_state"]["last_investigation_status"] = self._normalize_text(
            base["evidence_state"].get("last_investigation_status")
        )
        base["evidence_state"]["verdict_action"] = self._normalize_text(
            base["evidence_state"].get("verdict_action")
        )
        base["evidence_state"]["active_source_ids"] = self._normalize_list(
            base["evidence_state"].get("active_source_ids"), limit=8
        )
        base["evidence_state"]["evidence_facts"] = self._normalize_list(
            base["evidence_state"].get("evidence_facts"), limit=5
        )
        base["evidence_state"]["unresolved_questions"] = self._normalize_list(
            base["evidence_state"].get("unresolved_questions"), limit=5
        )
        base["evidence_state"]["judge_notes"] = self._normalize_list(
            base["evidence_state"].get("judge_notes"), limit=5
        )
        base["evidence_state"].pop("suggested_next_search", None)

        writer = _normalize_memory_writer_draft(base.get("memory_writer"))
        base["memory_writer"].update({
            "short_term_context": writer["short_term_context"],
            "active_topic": writer["active_topic"],
            "unresolved_user_request": writer["unresolved_user_request"],
            "assistant_obligation_next_turn": writer["assistant_obligation_next_turn"],
            "ephemeral_notes": writer["ephemeral_notes"],
            "durable_fact_candidates": writer["durable_fact_candidates"],
            "field_memo_write_recommendation": writer["field_memo_write_recommendation"],
            "confidence": writer["confidence"],
        })

        base["tool_carryover"]["version"] = self._normalize_text(
            base["tool_carryover"].get("version"), fallback="tool_carryover_v1"
        )
        for key in (
            "last_tool",
            "last_query",
            "last_target_id",
            "last_direction",
            "origin_source_id",
            "origin_query",
            "axis",
        ):
            base["tool_carryover"][key] = self._normalize_text(base["tool_carryover"].get(key))
        try:
            base["tool_carryover"]["last_limit"] = max(
                int(base["tool_carryover"].get("last_limit", 0) or 0),
                0,
            )
        except (TypeError, ValueError):
            base["tool_carryover"]["last_limit"] = 0
        base["tool_carryover"]["source_ids"] = self._normalize_list(
            base["tool_carryover"].get("source_ids"), limit=12
        )
        base["tool_carryover"]["candidate_ids"] = self._normalize_list(
            base["tool_carryover"].get("candidate_ids"), limit=12
        )
        base["tool_carryover"]["available_followups"] = self._normalize_list(
            base["tool_carryover"].get("available_followups"), limit=8
        )
        if not isinstance(base["tool_carryover"].get("recommended_next_scroll"), dict):
            base["tool_carryover"]["recommended_next_scroll"] = {}

        base["response_contract"]["reply_mode"] = self._normalize_text(
            base["response_contract"].get("reply_mode")
        )
        base["response_contract"]["answer_goal"] = _memory_safe_text(
            base["response_contract"].get("answer_goal"),
            180,
        )
        base["response_contract"]["must_include_facts"] = self._normalize_list(
            base["response_contract"].get("must_include_facts"), limit=5
        )
        base["response_contract"]["must_avoid_claims"] = self._normalize_list(
            base["response_contract"].get("must_avoid_claims"), limit=5
        )
        base["response_contract"]["direct_answer_seed"] = _memory_safe_text(
            base["response_contract"].get("direct_answer_seed"),
            220,
        )

        base["user_model_delta"]["observed_preferences"] = self._normalize_list(
            base["user_model_delta"].get("observed_preferences"), limit=8
        )
        base["user_model_delta"]["friction_points"] = self._normalize_list(
            base["user_model_delta"].get("friction_points"), limit=6
        )
        base["user_model_delta"]["tone_preferences"] = self._normalize_list(
            base["user_model_delta"].get("tone_preferences"), limit=6
        )

        base["last_turn"]["user_input"] = self._normalize_text(base["last_turn"].get("user_input"))
        base["last_turn"]["assistant_answer"] = self._normalize_text(base["last_turn"].get("assistant_answer"))
        base["last_turn"]["auditor_instruction"] = self._normalize_text(
            base["last_turn"].get("auditor_instruction")
        )
        try:
            base["last_turn"]["loop_count"] = int(base["last_turn"].get("loop_count", 0))
        except (TypeError, ValueError):
            base["last_turn"]["loop_count"] = 0
        base["last_turn"]["used_sources"] = self._normalize_list(
            base["last_turn"].get("used_sources"), limit=8
        )
        base["turn_summary"] = self._normalize_text(
            data.get("turn_summary") or base.get("turn_summary"),
            fallback="Structured working memory has not been written yet.",
        )
        if _looks_like_internal_strategy_text(base["turn_summary"]):
            safe_parts = []
            if base["dialogue_state"].get("user_dialogue_act"):
                safe_parts.append(f"user_dialogue_act={base['dialogue_state']['user_dialogue_act']}")
            if base["dialogue_state"].get("active_task"):
                safe_parts.append(f"active_task={base['dialogue_state']['active_task']}")
            if base["evidence_state"].get("evidence_facts"):
                safe_parts.append("facts=" + " / ".join(base["evidence_state"]["evidence_facts"][:2]))
            base["turn_summary"] = " | ".join(safe_parts) if safe_parts else "working_memory sanitized"
        return base

    def _load_recent_history_from_db(self):
        _safe_print("[Memory] Loading recent dialogue history...")
        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT role, content
                    FROM songryeon_chats
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (self.max_context,),
                )
                rows = cursor.fetchall()
                for role, content in reversed(rows):
                    msg_role = "user" if role == "user" else "assistant"
                    self.history.append({"role": msg_role, "content": content})
                _safe_print(f"[Memory] Restored dialogue history ({len(self.history)} messages)")
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            _safe_print(f"[Memory] History load failed; starting fresh: {e}")

    def _load_latest_working_memory_from_db(self):
        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT cognitive_process
                    FROM agent_dreams
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                if not row:
                    return

                payload = row[0]
                if isinstance(payload, (bytes, bytearray)):
                    payload = payload.decode("utf-8")
                if isinstance(payload, str):
                    payload = json.loads(payload)
                if not isinstance(payload, dict):
                    return

                trace_data = payload.get("trace_data", {})
                working_memory = trace_data.get("working_memory_snapshot")
                if not working_memory:
                    canonical_turn = trace_data.get("canonical_turn", {})
                    if isinstance(canonical_turn, dict):
                        working_memory = canonical_turn.get("working_memory")
                if working_memory:
                    self.working_memory = self._normalize_working_memory(working_memory)
                    _safe_print("[Working Memory] Restored latest structured snapshot")
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            _safe_print(f"[Working Memory] Snapshot restore skipped: {e}")

    def add_message(self, role, content):
        self.history.append({"role": role, "content": content})
        if role in ["user", "assistant"]:
            log_message_to_db(role, content)
        if len(self.history) > self.max_context:
            self._compress_memory()

    def update_working_memory(self, new_summary):
        if isinstance(new_summary, dict):
            self.working_memory = self._normalize_working_memory(new_summary)
            _safe_print("[Working Memory] Structured snapshot updated")
            return
        if new_summary and str(new_summary).strip():
            snapshot = self.get_working_memory_snapshot()
            snapshot["turn_summary"] = str(new_summary).strip()
            self.working_memory = self._normalize_working_memory(snapshot)
            _safe_print(f"[Working Memory] Turn summary updated: {_shorten(new_summary, 30)}")

    def _build_turn_summary(self, working_memory: dict):
        dialogue = working_memory.get("dialogue_state", {})
        evidence = working_memory.get("evidence_state", {})
        response = working_memory.get("response_contract", {})

        parts = []
        if dialogue.get("user_dialogue_act"):
            parts.append(f"user_dialogue_act={dialogue['user_dialogue_act']}")
        if dialogue.get("active_task"):
            parts.append(f"active_task={dialogue['active_task']}")
        if evidence.get("last_investigation_status"):
            parts.append(f"investigation_status={evidence['last_investigation_status']}")
        if evidence.get("active_source_ids"):
            parts.append(f"active_sources={', '.join(evidence['active_source_ids'][:3])}")
        if response.get("reply_mode"):
            parts.append(f"reply_mode={response['reply_mode']}")
        if not parts:
            return "Structured working memory has not been written yet."
        return " | ".join(parts)

    def commit_turn_state(self, final_state, user_input, final_answer):
        self.working_memory = self.build_working_memory_from_turn(final_state, user_input, final_answer)
        _safe_print(f"[Working Memory] {self.working_memory['turn_summary']}")
        return self.get_working_memory_snapshot()

    def get_working_memory_snapshot(self):
        return json.loads(json.dumps(self._normalize_working_memory(self.working_memory), ensure_ascii=False))

    def _compress_memory(self):
        """Compress older dialogue history into a short running summary."""
        cut_off = len(self.history) // 2
        to_compress = self.history[:cut_off]
        self.history = self.history[cut_off:]

        conversation_text = ""
        for msg in to_compress:
            speaker = "user" if msg.get("role") == "user" else "assistant"
            conversation_text += f"{speaker}: {msg['content']}\n"

        prompt = f"""
        [previous summary]: {self.summary}

        [older dialogue]:
        {conversation_text}

        Summarize the durable user-facing situation in no more than 3 sentences.
        Do not include internal strategy labels or routing/debug text.
        """
        
        try:
            response = ollama.chat(model=self.model, messages=[
                {'role': 'user', 'content': prompt}
            ])
            self.summary = response['message']['content']
            _safe_print("[Memory] compressed older dialogue history.")
        except Exception as e:
            _safe_print(f"[Memory] compression failed: {e}")

    def get_full_context(self, system_prompt):
        messages = [{'role': 'system', 'content': system_prompt}]
        if self.summary:
            messages.append({
                'role': 'system', 
                'content': f"[dialogue summary]: {self.summary}"
            })
        messages.extend(self.history)
        return messages
    

    def get_context_string(self, limit=6):
        """
        Return recent dialogue as a compact transcript.
        limit=6 usually means three user/assistant pairs.
        """
        if not self.history:
            return "No recent dialogue."
            
        res = "--- [Recent Dialogue Start] ---\n"
        # Keep this short so long histories do not crowd out the current turn.
        for msg in self.history[-limit:]:
            speaker = "user" if msg['role'] == 'user' else "assistant"
            res += f"{speaker}: {msg['content']}\n"
        res += "--- [Recent Dialogue End] ---\n"
        return res

    def get_working_memory_string(self):
        wm = self.get_working_memory_snapshot()
        dialogue = wm["dialogue_state"]
        evidence = wm["evidence_state"]
        response = wm["response_contract"]
        user_model = wm["user_model_delta"]

        lines = ["--- [Structured Working Memory] ---"]
        lines.append(f"- turn_summary: {wm['turn_summary']}")
        lines.append(f"- user_dialogue_act: {dialogue['user_dialogue_act'] or 'unknown'}")
        lines.append(f"- assistant_last_move: {dialogue['assistant_last_move'] or 'unknown'}")
        lines.append(f"- active_task: {dialogue['active_task'] or 'none'}")
        lines.append(f"- conversation_mode: {dialogue['conversation_mode'] or 'unknown'}")
        lines.append(f"- continuation_expected: {dialogue['continuation_expected']}")
        if dialogue["pending_question"]:
            lines.append(f"- pending_question: {dialogue['pending_question']}")
        if dialogue["user_feedback_signal"]:
            lines.append(f"- user_feedback_signal: {dialogue['user_feedback_signal']}")
        if evidence["last_investigation_status"]:
            lines.append(f"- last_investigation_status: {evidence['last_investigation_status']}")
        if evidence["active_source_ids"]:
            lines.append(f"- active_source_ids: {', '.join(evidence['active_source_ids'])}")
        if evidence["evidence_facts"]:
            lines.append(f"- evidence_facts: {' / '.join(evidence['evidence_facts'][:3])}")
        if evidence["unresolved_questions"]:
            lines.append(f"- unresolved_questions: {' / '.join(evidence['unresolved_questions'][:2])}")
        if response["reply_mode"]:
            lines.append(f"- reply_mode: {response['reply_mode']}")
        if response["answer_goal"]:
            lines.append(f"- answer_goal: {response['answer_goal']}")
        if response["direct_answer_seed"]:
            lines.append(f"- direct_answer_seed: {_shorten(response['direct_answer_seed'], 180)}")
        if user_model["observed_preferences"]:
            lines.append(f"- observed_preferences: {', '.join(user_model['observed_preferences'])}")
        if user_model["friction_points"]:
            lines.append(f"- friction_points: {' / '.join(user_model['friction_points'][:2])}")
        lines.append("--- [Structured Working Memory End] ---")
        return "\n".join(lines)


def _memory_buffer_build_turn_summary_v3(self, working_memory: dict):
    dialogue = working_memory.get("dialogue_state", {})
    temporal = working_memory.get("temporal_context", {})
    evidence = working_memory.get("evidence_state", {})
    response = working_memory.get("response_contract", {})

    parts = []
    if dialogue.get("user_dialogue_act"):
        parts.append(f"user_dialogue_act={dialogue['user_dialogue_act']}")
    active_task = _memory_safe_text(dialogue.get("active_task"), 180)
    if active_task:
        parts.append(f"active_task={active_task}")
    if dialogue.get("active_offer"):
        parts.append(f"active_offer={dialogue['active_offer']}")
    if dialogue.get("task_reset_applied"):
        reset_reason = str(dialogue.get("task_reset_reason") or "current_user_input_priority").strip()
        parts.append(f"task_reset={reset_reason}")
    if float(temporal.get("topic_reset_confidence", 0.0) or 0.0) >= 0.55:
        parts.append(f"topic_reset={temporal.get('topic_reset_confidence'):.2f}")
    elif float(temporal.get("continuity_score", 0.0) or 0.0) >= 0.6:
        parts.append(f"continuity={temporal.get('continuity_score'):.2f}")
    if evidence.get("verdict_action"):
        parts.append(f"verdict_action={evidence['verdict_action']}")
    if evidence.get("last_investigation_status"):
        parts.append(f"investigation_status={evidence['last_investigation_status']}")
    if evidence.get("active_source_ids"):
        parts.append(f"source_ids={', '.join(evidence['active_source_ids'][:3])}")
    if response.get("reply_mode"):
        parts.append(f"reply_mode={response['reply_mode']}")
    if not parts:
        return "working_memory not populated yet"
    return " | ".join(parts)
MemoryBuffer._build_turn_summary = _memory_buffer_build_turn_summary_v3


def _memory_buffer_recent_raw_turns_for_writer_v1(self, limit: int = 8):
    turns = []
    for msg in self.history[-limit:]:
        if not isinstance(msg, dict):
            continue
        role = "user" if msg.get("role") == "user" else "assistant"
        content = _memory_safe_text(msg.get("content"), 500) or self._normalize_text(msg.get("content"))[:500]
        if content:
            turns.append({"role": role, "content": content})
    return turns


def _memory_buffer_write_working_memory_with_llm_v1(
    self,
    *,
    previous: dict,
    final_state: dict,
    user_input: str,
    final_answer: str,
    evidence_facts: list[str],
):
    return _write_working_memory_with_llm_boundary(
        model_name=getattr(self, "model", "gemma4:e4b"),
        previous=previous,
        final_state=final_state,
        user_input=user_input,
        final_answer=final_answer,
        evidence_facts=evidence_facts,
        recent_raw_turns=self._recent_raw_turns_for_writer(limit=8),
    )


def _memory_buffer_build_working_memory_from_turn_v4(self, final_state, user_input, final_answer):
    previous = self.get_working_memory_snapshot()
    final_state = final_state if isinstance(final_state, dict) else {}
    analysis_report = final_state.get("analysis_report", {})
    if not isinstance(analysis_report, dict):
        analysis_report = {}
    response_strategy = final_state.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}

    evidence_facts = _memory_facts_from_analysis(analysis_report, limit=5)
    temporal_context = self.build_temporal_context_signal(
        user_input,
        exclude_exact_texts=[user_input, final_answer],
    )
    writer = self._write_working_memory_with_llm(
        previous=previous,
        final_state=final_state,
        user_input=user_input,
        final_answer=final_answer,
        evidence_facts=evidence_facts,
    )
    writer = _normalize_memory_writer_draft(writer)
    pending = _normalize_pending_dialogue_act(writer.get("pending_dialogue_act"))
    continuation_expected = pending.get("kind") != "none" and float(pending.get("confidence", 0.0) or 0.0) >= 0.35
    durable_facts = writer.get("durable_fact_candidates", [])

    working_memory = {
        "version": "working_memory_v2",
        "dialogue_state": {
            "user_dialogue_act": writer.get("user_dialogue_act", ""),
            "assistant_last_move": writer.get("assistant_last_move", ""),
            "pending_question": pending.get("target", "") if pending.get("kind") == "question" else "",
            "pending_dialogue_act": pending,
            "active_task": "",
            "active_task_source": "",
            "active_offer": "",
            "active_offer_source": "",
            "conversation_mode": writer.get("conversation_mode", ""),
            "continuation_expected": continuation_expected,
            "initiative_requested": bool(writer.get("assistant_obligation_next_turn")),
            "requested_assistant_move": "",
            "task_reset_applied": False,
            "task_reset_reason": "",
            "user_feedback_signal": "",
        },
        "temporal_context": temporal_context,
        "memory_writer": {
            "short_term_context": writer.get("short_term_context", ""),
            "active_topic": writer.get("active_topic", ""),
            "unresolved_user_request": writer.get("unresolved_user_request", ""),
            "assistant_obligation_next_turn": writer.get("assistant_obligation_next_turn", ""),
            "ephemeral_notes": writer.get("ephemeral_notes", []),
            "durable_fact_candidates": durable_facts,
            "field_memo_write_recommendation": writer.get("field_memo_write_recommendation", "skip"),
            "confidence": writer.get("confidence", 0.0),
        },
        "evidence_state": {
            "last_investigation_status": self._normalize_text(analysis_report.get("investigation_status")),
            "verdict_action": self._normalize_text(analysis_report.get("verdict_action")),
            "active_source_ids": self._normalize_list(final_state.get("used_sources", []), limit=8),
            "evidence_facts": self._normalize_list(evidence_facts, limit=5),
            "unresolved_questions": self._normalize_list(analysis_report.get("unresolved_questions", []), limit=5),
            "judge_notes": [],
        },
        "response_contract": {
            "reply_mode": self._normalize_text(response_strategy.get("reply_mode")),
            "answer_goal": _memory_safe_text(response_strategy.get("answer_goal"), 180),
            "must_include_facts": self._normalize_list(
                response_strategy.get("must_include_facts", []) or evidence_facts,
                limit=5,
            ),
            "must_avoid_claims": self._normalize_list(response_strategy.get("must_avoid_claims", []), limit=5),
            "direct_answer_seed": _memory_safe_text(response_strategy.get("direct_answer_seed"), 220),
        },
        "user_model_delta": {
            "observed_preferences": self._normalize_list(previous.get("user_model_delta", {}).get("observed_preferences", []), limit=8),
            "friction_points": self._normalize_list(previous.get("user_model_delta", {}).get("friction_points", []), limit=6),
            "tone_preferences": self._normalize_list(previous.get("user_model_delta", {}).get("tone_preferences", []), limit=6),
        },
        "last_turn": {
            "user_input": self._normalize_text(user_input),
            "assistant_answer": self._normalize_text(final_answer),
            "auditor_instruction": self._normalize_text(final_state.get("auditor_instruction")),
            "loop_count": int(final_state.get("loop_count", 0) or 0),
            "used_sources": self._normalize_list(final_state.get("used_sources", []), limit=8),
        },
    }
    working_memory["turn_summary"] = (
        writer.get("short_term_context")
        or self._build_turn_summary(working_memory)
    )
    return self._normalize_working_memory(working_memory)


def _memory_buffer_get_working_memory_string_v4(self):
    wm = self.get_working_memory_snapshot()
    dialogue = wm["dialogue_state"]
    temporal = wm.get("temporal_context", {})
    evidence = wm["evidence_state"]
    response = wm["response_contract"]
    user_model = wm["user_model_delta"]
    writer = wm.get("memory_writer", {})
    pending = dialogue.get("pending_dialogue_act", {}) if isinstance(dialogue.get("pending_dialogue_act"), dict) else {}

    lines = ["--- [Structured Working Memory] ---"]
    lines.append(f"- turn_summary: {wm['turn_summary']}")
    if writer.get("short_term_context"):
        lines.append(f"- short_term_context: {writer['short_term_context']}")
    if writer.get("active_topic"):
        lines.append(f"- active_topic: {writer['active_topic']}")
    if writer.get("unresolved_user_request"):
        lines.append(f"- unresolved_user_request: {writer['unresolved_user_request']}")
    if writer.get("assistant_obligation_next_turn"):
        lines.append(f"- assistant_obligation_next_turn: {writer['assistant_obligation_next_turn']}")
    lines.append(f"- user_dialogue_act: {dialogue['user_dialogue_act'] or 'unknown'}")
    lines.append(f"- assistant_last_move: {dialogue['assistant_last_move'] or 'unknown'}")
    safe_active_task = _memory_safe_text(dialogue.get("active_task"), 180)
    lines.append(f"- active_task: {safe_active_task or 'none'}")
    lines.append(f"- conversation_mode: {dialogue['conversation_mode'] or 'unknown'}")
    lines.append(f"- continuation_expected: {dialogue['continuation_expected']}")
    if pending.get("kind") and pending.get("kind") != "none":
        lines.append(
            "- pending_dialogue_act: "
            + json.dumps(pending, ensure_ascii=False, default=str)
        )
    lines.append(f"- continuity_score: {float(temporal.get('continuity_score', 0.0) or 0.0):.2f}")
    lines.append(f"- topic_shift_score: {float(temporal.get('topic_shift_score', 0.0) or 0.0):.2f}")
    lines.append(f"- topic_reset_confidence: {float(temporal.get('topic_reset_confidence', 0.0) or 0.0):.2f}")
    lines.append(f"- carry_over_strength: {float(temporal.get('carry_over_strength', 0.0) or 0.0):.2f}")
    if evidence["evidence_facts"]:
        lines.append(f"- evidence_facts: {' / '.join(evidence['evidence_facts'][:3])}")
    if writer.get("durable_fact_candidates"):
        lines.append(f"- writer_proposed_durable_fact_candidates_unverified: {' / '.join(writer['durable_fact_candidates'][:3])}")
    if writer.get("ephemeral_notes"):
        lines.append(f"- ephemeral_notes: {' / '.join(writer['ephemeral_notes'][:2])}")
    if response["reply_mode"]:
        lines.append(f"- reply_mode: {response['reply_mode']}")
    safe_answer_goal = _memory_safe_text(response.get("answer_goal"), 180)
    if safe_answer_goal:
        lines.append(f"- answer_goal: {safe_answer_goal}")
    safe_direct_seed = _memory_safe_text(response.get("direct_answer_seed"), 180)
    if safe_direct_seed:
        lines.append(f"- direct_answer_seed: {safe_direct_seed}")
    if user_model["observed_preferences"]:
        lines.append(f"- observed_preferences: {', '.join(user_model['observed_preferences'])}")
    if user_model["friction_points"]:
        lines.append(f"- friction_points: {' / '.join(user_model['friction_points'][:2])}")
    lines.append("--- [Structured Working Memory End] ---")
    return "\n".join(lines)


def _memory_buffer_get_tactical_context_v4(self, user_input: str = ""):
    snapshot = self.get_working_memory_snapshot_for_input(user_input) if user_input else self.get_working_memory_snapshot()
    wm_string = self._working_memory_string_from_snapshot(snapshot)
    recent_raw = ""
    for msg in self.history[-8:]:
        speaker = "user" if msg["role"] == "user" else "assistant"
        recent_raw += f"[{speaker}]: {msg['content']}\n"
    return f"{wm_string}\n\n[Recent Raw Turns]\n{recent_raw}"


MemoryBuffer._recent_raw_turns_for_writer = _memory_buffer_recent_raw_turns_for_writer_v1
MemoryBuffer._write_working_memory_with_llm = _memory_buffer_write_working_memory_with_llm_v1
MemoryBuffer.build_working_memory_from_turn = _memory_buffer_build_working_memory_from_turn_v4
MemoryBuffer.get_working_memory_string = _memory_buffer_get_working_memory_string_v4
MemoryBuffer.get_tactical_context = _memory_buffer_get_tactical_context_v4


def _memory_buffer_working_memory_string_from_snapshot_v1(self, snapshot: dict):
    original = self.working_memory
    try:
        self.working_memory = self._normalize_working_memory(snapshot)
        return self.get_working_memory_string()
    finally:
        self.working_memory = original


def _memory_buffer_get_working_memory_snapshot_for_input_v1(self, user_input: str):
    snapshot = self.get_working_memory_snapshot()
    snapshot["temporal_context"] = self.build_temporal_context_signal(user_input)
    return self._normalize_working_memory(snapshot)


def _memory_buffer_build_temporal_context_signal_v2(self, user_input: str, exclude_exact_texts=None, limit=8):
    return shared_build_temporal_context_signal(
        user_input=user_input,
        db_config=DB_CONFIG,
        shorten=_shorten,
        exclude_exact_texts=exclude_exact_texts or [],
        limit=limit,
    )


MemoryBuffer.build_temporal_context_signal = _memory_buffer_build_temporal_context_signal_v2
MemoryBuffer.get_working_memory_snapshot_for_input = _memory_buffer_get_working_memory_snapshot_for_input_v1
MemoryBuffer._working_memory_string_from_snapshot = _memory_buffer_working_memory_string_from_snapshot_v1
