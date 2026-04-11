import builtins
import json
import ollama
import os
import pymysql
import sys
from dotenv import load_dotenv

# 환경 변수 로드 (DB 접속용)
load_dotenv()

# DB 설정 (main.py나 tools에서 쓰는 것과 동일하게 맞춤)
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

class MemoryBuffer:
    def __init__(self, model_name="gemma3:12b", max_context=30):
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
                "active_task": "",
                "active_task_source": "",
                "conversation_mode": "",
                "continuation_expected": False,
                "initiative_requested": False,
                "requested_assistant_move": "",
                "task_reset_applied": False,
                "task_reset_reason": "",
                "user_feedback_signal": "",
            },
            "evidence_state": {
                "last_investigation_status": "",
                "verdict_action": "",
                "active_source_ids": [],
                "evidence_facts": [],
                "unresolved_questions": [],
                "suggested_next_search": "",
                "judge_notes": [],
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
            "turn_summary": "구조화된 working memory가 아직 작성되지 않았습니다.",
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

        for section in ("dialogue_state", "evidence_state", "response_contract", "user_model_delta", "last_turn"):
            if isinstance(data.get(section), dict):
                base[section].update(data[section])

        base["dialogue_state"]["user_dialogue_act"] = self._normalize_text(
            base["dialogue_state"].get("user_dialogue_act")
        )
        base["dialogue_state"]["assistant_last_move"] = self._normalize_text(
            base["dialogue_state"].get("assistant_last_move")
        )
        base["dialogue_state"]["pending_question"] = self._normalize_text(
            base["dialogue_state"].get("pending_question")
        )
        base["dialogue_state"]["active_task"] = self._normalize_text(base["dialogue_state"].get("active_task"))
        base["dialogue_state"]["active_task_source"] = self._normalize_text(
            base["dialogue_state"].get("active_task_source")
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
        base["evidence_state"]["suggested_next_search"] = self._normalize_text(
            base["evidence_state"].get("suggested_next_search")
        )
        base["evidence_state"]["judge_notes"] = self._normalize_list(
            base["evidence_state"].get("judge_notes"), limit=5
        )

        base["response_contract"]["reply_mode"] = self._normalize_text(
            base["response_contract"].get("reply_mode")
        )
        base["response_contract"]["answer_goal"] = self._normalize_text(
            base["response_contract"].get("answer_goal")
        )
        base["response_contract"]["must_include_facts"] = self._normalize_list(
            base["response_contract"].get("must_include_facts"), limit=5
        )
        base["response_contract"]["must_avoid_claims"] = self._normalize_list(
            base["response_contract"].get("must_avoid_claims"), limit=5
        )
        base["response_contract"]["direct_answer_seed"] = self._normalize_text(
            base["response_contract"].get("direct_answer_seed")
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
            fallback="구조화된 working memory가 아직 작성되지 않았습니다.",
        )
        return base

    def _load_recent_history_from_db(self):
        _safe_print("📥 [Memory] 지난 대화 기록을 뇌에 로드 중...")
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
                _safe_print(f"✅ [Memory] 기억 복원 완료 ({len(self.history)}개 메시지)")
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            _safe_print(f"⚠️ 기억 로드 실패 (초기화 상태로 시작): {e}")

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
                    _safe_print("🧠 [Working Memory] 최신 구조화 상황판 복원 완료")
            finally:
                cursor.close()
                conn.close()
        except Exception as e:
            _safe_print(f"ℹ️ [Working Memory] 구조화 상황판 복원 생략: {e}")

    def add_message(self, role, content):
        self.history.append({"role": role, "content": content})
        if role in ["user", "assistant"]:
            log_message_to_db(role, content)
        if len(self.history) > self.max_context:
            self._compress_memory()

    def update_working_memory(self, new_summary):
        if isinstance(new_summary, dict):
            self.working_memory = self._normalize_working_memory(new_summary)
            _safe_print("📋 [Working Memory] 구조화 상황판 업데이트 완료")
            return
        if new_summary and str(new_summary).strip():
            snapshot = self.get_working_memory_snapshot()
            snapshot["turn_summary"] = str(new_summary).strip()
            self.working_memory = self._normalize_working_memory(snapshot)
            _safe_print(f"📋 [Working Memory] 작전 상황판 업데이트 완료: {_shorten(new_summary, 30)}")

    def _classify_user_feedback_signal(self, user_input: str):
        text = str(user_input or "").strip()
        lowered = text.lower()
        if not text:
            return "neutral"
        if any(marker in text for marker in ["아니", "틀렸", "그게 아니라", "왜 또", "환각", "엉뚱"]):
            return "correction_or_pushback"
        if any(marker in text for marker in [
            "네가 직접",
            "직접 생각",
            "스스로",
            "묻지 말고",
            "네가 판단",
            "네가 생각해봐",
            "네가 고민해봐",
            "네가 판단해봐",
            "질문해봐",
            "질문하라고",
            "네가 질문",
            "물어봐",
            "네가 물어",
        ]):
            return "assistant_initiative_requested"
        if "?" in text or any(marker in text for marker in ["찾아", "정리", "설명", "분석", "알려", "부가자료", "기획서", "pptx", "문서"]):
            return "request"
        if lowered in {"ㅇㅇ", "응", "네", "넵", "ok", "okay"}:
            return "acknowledgement"
        return "neutral"

    def _classify_user_dialogue_act(self, user_input: str):
        feedback_signal = self._classify_user_feedback_signal(user_input)
        mapping = {
            "correction_or_pushback": "correction",
            "assistant_initiative_requested": "initiative_request",
            "request": "question_or_request",
            "acknowledgement": "acknowledgement",
            "neutral": "statement",
        }
        return mapping.get(feedback_signal, "statement")

    def _classify_assistant_last_move(self, final_answer: str, response_strategy: dict):
        reply_mode = str((response_strategy or {}).get("reply_mode") or "").strip()
        text = str(final_answer or "").strip()
        if reply_mode == "ask_user_question_now":
            return "question"
        if reply_mode == "continue_previous_offer":
            return "continued_offer"
        if any(marker in text for marker in ["원하시면", "말씀해 주세요", "더 볼까요", "보실래요", "궁금하신가요"]):
            return "followup_offer"
        if "?" in text:
            return "question"
        if reply_mode in {"grounded_answer", "cautious_minimal"}:
            return "answer"
        return "statement"

    def _extract_requested_assistant_move(self, user_input: str):
        text = str(user_input or "").strip()
        lowered = text.lower()
        if not text:
            return ""
        question_request_markers = [
            "질문해봐",
            "질문해",
            "질문하라고",
            "네가 질문",
            "질문 하나",
            "질문 한 개",
            "물어봐",
            "물어보라고",
            "네가 물어",
            "하나 물어",
            "한 번 물어",
        ]
        english_markers = ["ask me a question", "you ask", "ask first", "ask one question"]
        if any(marker in text for marker in question_request_markers) or any(marker in lowered for marker in english_markers):
            return "ask_user_question_now"
        return ""

    def _extract_pending_question(self, final_answer: str):
        text = str(final_answer or "").strip()
        if "?" not in text:
            return ""
        chunks = [chunk.strip() for chunk in text.split("?") if chunk.strip()]
        if not chunks:
            return ""
        return _shorten(chunks[-1] + "?", 180)

    def _build_turn_summary(self, working_memory: dict):
        dialogue = working_memory.get("dialogue_state", {})
        evidence = working_memory.get("evidence_state", {})
        response = working_memory.get("response_contract", {})

        parts = []
        if dialogue.get("user_dialogue_act"):
            parts.append(f"사용자 발화 행위={dialogue['user_dialogue_act']}")
        if dialogue.get("active_task"):
            parts.append(f"현재 과업={dialogue['active_task']}")
        if evidence.get("last_investigation_status"):
            parts.append(f"수사 상태={evidence['last_investigation_status']}")
        if evidence.get("active_source_ids"):
            parts.append(f"근거 출처={', '.join(evidence['active_source_ids'][:3])}")
        if response.get("reply_mode"):
            parts.append(f"응답 모드={response['reply_mode']}")
        if not parts:
            return "구조화된 working memory가 아직 작성되지 않았습니다."
        return " | ".join(parts)

    def _should_carry_previous_active_task(self, user_dialogue_act: str, previous: dict):
        if user_dialogue_act == "acknowledgement":
            return True
        return False

    def _derive_active_task(self, previous: dict, user_input: str, analysis_report: dict, response_strategy: dict, user_dialogue_act: str):
        strategy_goal = self._normalize_text(response_strategy.get("answer_goal"))
        if strategy_goal:
            return _shorten(strategy_goal, 180)

        situational_brief = self._normalize_text(analysis_report.get("situational_brief"))
        if situational_brief:
            return _shorten(situational_brief, 180)

        if self._should_carry_previous_active_task(user_dialogue_act, previous):
            previous_task = self._normalize_text(previous.get("dialogue_state", {}).get("active_task"))
            if previous_task:
                return previous_task

        normalized_input = self._normalize_text(user_input)
        if normalized_input and user_dialogue_act in {"question_or_request", "correction", "statement"}:
            return _shorten(normalized_input, 180)
        return ""

    def build_working_memory_from_turn(self, final_state, user_input, final_answer):
        previous = self.get_working_memory_snapshot()
        analysis_report = final_state.get("analysis_report", {})
        if not isinstance(analysis_report, dict):
            analysis_report = {}
        response_strategy = final_state.get("response_strategy", {})
        if not isinstance(response_strategy, dict):
            response_strategy = {}

        evidences = analysis_report.get("evidences", []) if isinstance(analysis_report.get("evidences"), list) else []
        evidence_facts = []
        evidence_source_ids = []
        for item in evidences:
            if not isinstance(item, dict):
                continue
            fact = self._normalize_text(item.get("extracted_fact"))
            source_id = self._normalize_text(item.get("source_id"))
            if fact:
                evidence_facts.append(fact)
            if source_id:
                evidence_source_ids.append(source_id)

        suggested_next_search = self._normalize_text(analysis_report.get("suggested_next_search"))
        unresolved_questions = []
        if analysis_report.get("investigation_status") == "EXPANSION_REQUIRED":
            if analysis_report.get("analytical_thought"):
                unresolved_questions.append(analysis_report.get("analytical_thought"))
            if suggested_next_search:
                unresolved_questions.append(f"추가 수색 필요: {suggested_next_search}")
        elif analysis_report.get("investigation_status") == "INCOMPLETE":
            unresolved_questions.append(
                analysis_report.get("situational_brief") or "의미 있는 증거를 아직 확보하지 못했습니다."
            )

        user_feedback_signal = self._classify_user_feedback_signal(user_input)
        user_dialogue_act = self._classify_user_dialogue_act(user_input)
        assistant_last_move = self._classify_assistant_last_move(final_answer, response_strategy)
        pending_question = self._extract_pending_question(final_answer)
        continuation_expected = assistant_last_move in {"question", "followup_offer"}
        initiative_requested = user_feedback_signal == "assistant_initiative_requested"

        if analysis_report.get("investigation_status") or final_state.get("used_sources"):
            conversation_mode = "grounded_retrieval"
        elif initiative_requested:
            conversation_mode = "initiative_guidance"
        elif response_strategy.get("reply_mode") == "casual_reaction":
            conversation_mode = "casual_dialogue"
        else:
            conversation_mode = "general_dialogue"

        observed_preferences = list(previous["user_model_delta"].get("observed_preferences", []))
        friction_points = list(previous["user_model_delta"].get("friction_points", []))
        tone_preferences = list(previous["user_model_delta"].get("tone_preferences", []))

        if initiative_requested:
            observed_preferences.append("assistant_should_propose_directly")
            observed_preferences.append("avoid_bouncing_questions_back")
        if user_feedback_signal == "correction_or_pushback":
            friction_points.append(_shorten(user_input, 120))

        working_memory = {
            "version": "working_memory_v2",
            "dialogue_state": {
                "user_dialogue_act": user_dialogue_act,
                "assistant_last_move": assistant_last_move,
                "pending_question": pending_question,
                "active_task": self._derive_active_task(
                    previous=previous,
                    user_input=user_input,
                    analysis_report=analysis_report,
                    response_strategy=response_strategy,
                    user_dialogue_act=user_dialogue_act,
                ),
                "conversation_mode": conversation_mode,
                "continuation_expected": continuation_expected,
                "initiative_requested": initiative_requested,
                "user_feedback_signal": user_feedback_signal,
            },
            "evidence_state": {
                "last_investigation_status": self._normalize_text(analysis_report.get("investigation_status")),
                "active_source_ids": self._normalize_list(
                    list(final_state.get("used_sources", [])) + evidence_source_ids,
                    limit=8,
                ),
                "evidence_facts": self._normalize_list(evidence_facts, limit=5),
                "unresolved_questions": self._normalize_list(unresolved_questions, limit=5),
                "suggested_next_search": suggested_next_search,
            },
            "response_contract": {
                "reply_mode": self._normalize_text(response_strategy.get("reply_mode")),
                "answer_goal": self._normalize_text(response_strategy.get("answer_goal")),
                "must_include_facts": self._normalize_list(
                    response_strategy.get("must_include_facts", []), limit=5
                ),
                "must_avoid_claims": self._normalize_list(
                    response_strategy.get("must_avoid_claims", []), limit=5
                ),
                "direct_answer_seed": self._normalize_text(response_strategy.get("direct_answer_seed")),
            },
            "user_model_delta": {
                "observed_preferences": self._normalize_list(observed_preferences, limit=8),
                "friction_points": self._normalize_list(friction_points, limit=6),
                "tone_preferences": self._normalize_list(tone_preferences, limit=6),
            },
            "last_turn": {
                "user_input": self._normalize_text(user_input),
                "assistant_answer": self._normalize_text(final_answer),
                "auditor_instruction": self._normalize_text(final_state.get("auditor_instruction")),
                "loop_count": int(final_state.get("loop_count", 0) or 0),
                "used_sources": self._normalize_list(final_state.get("used_sources", []), limit=8),
            },
        }
        working_memory["turn_summary"] = self._build_turn_summary(working_memory)
        return self._normalize_working_memory(working_memory)

    def commit_turn_state(self, final_state, user_input, final_answer):
        self.working_memory = self.build_working_memory_from_turn(final_state, user_input, final_answer)
        _safe_print(f"📋 [Working Memory] {self.working_memory['turn_summary']}")
        return self.get_working_memory_snapshot()

    def get_working_memory_snapshot(self):
        return json.loads(json.dumps(self._normalize_working_memory(self.working_memory), ensure_ascii=False))

    def _compress_memory(self):
        """
        [기억 압축]
        용량이 차면 오래된 기억을 잘라내고 '요약본'으로 만듦.
        """
        # 절반 정도를 잘라내서 요약함
        cut_off = len(self.history) // 2
        to_compress = self.history[:cut_off]
        self.history = self.history[cut_off:] # 남은 기억

        conversation_text = ""
        for msg in to_compress:
            speaker = "개발자" if msg['role'] == 'user' else "송련"
            conversation_text += f"{speaker}: {msg['content']}\n"

        # 요약 프롬프트 (간결하게 수정)
        prompt = f"""
        [이전 요약]: {self.summary}
        
        [지나간 대화]:
        {conversation_text}
        
        [지령]:
        위 내용을 통합하여 '현재까지의 상황'을 3문장 이내로 요약하라.
        중요한 정보(사용자 의도, 현재 주제)는 남겨라.
        """
        
        try:
            response = ollama.chat(model=self.model, messages=[
                {'role': 'user', 'content': prompt}
            ])
            self.summary = response['message']['content']
            _safe_print("🧹 [Memory] 뇌 용량 확보를 위해 기억을 압축했습니다.")
        except Exception as e:
            _safe_print(f"💥 압축 실패: {e}")

    def get_full_context(self, system_prompt):
        messages = [{'role': 'system', 'content': system_prompt}]
        if self.summary:
            messages.append({
                'role': 'system', 
                'content': f"[지난 이야기 요약]: {self.summary}"
            })
        messages.extend(self.history)
        return messages
    

    def get_context_string(self, limit=6):
        """
        [수술 완료] 단기 기억을 명확한 대화 대본(Script) 형식으로 뽑아줍니다.
        limit=6 이면 (허정후->송련->허정후->송련->허정후->송련) 3턴입니다.
        """
        if not self.history:
            return "최근 대화 없음"
            
        res = "--- [최근 대화 기록 시작] ---\n"
        # 💡 너무 많은 기록이 한 번에 들어가면 환각이 오므로 limit을 철저히 지킵니다.
        for msg in self.history[-limit:]:
            speaker = "허정후(허정후)" if msg['role'] == 'user' else "송련(ANIMA)"
            res += f"{speaker}: {msg['content']}\n"
        res += "--- [최근 대화 기록 끝] ---\n"
        return res

    def get_working_memory_string(self):
        wm = self.get_working_memory_snapshot()
        dialogue = wm["dialogue_state"]
        evidence = wm["evidence_state"]
        response = wm["response_contract"]
        user_model = wm["user_model_delta"]

        lines = ["--- [구조화 단기 기억 상황판] ---"]
        lines.append(f"- turn_summary: {wm['turn_summary']}")
        lines.append(f"- user_dialogue_act: {dialogue['user_dialogue_act'] or 'unknown'}")
        lines.append(f"- assistant_last_move: {dialogue['assistant_last_move'] or 'unknown'}")
        lines.append(f"- active_task: {dialogue['active_task'] or '없음'}")
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
        lines.append("--- [구조화 단기 기억 상황판 끝] ---")
        return "\n".join(lines)


def _verdict_action_from_board(verdict: dict, fallback_status: str = ""):
    if not isinstance(verdict, dict):
        return fallback_status or ""
    answer_now = bool(verdict.get("answer_now"))
    requires_search = bool(verdict.get("requires_search"))
    if answer_now and requires_search:
        return "answer_with_search_reservation"
    if requires_search:
        return "search_more"
    if answer_now:
        return "answer_now"
    return fallback_status or "insufficient_evidence"


def _memory_buffer_derive_active_task_v3(self, previous: dict, user_input: str, analysis_report: dict, response_strategy: dict, user_dialogue_act: str, reasoning_board: dict | None = None, requested_assistant_move: str = ""):
    reasoning_board = reasoning_board if isinstance(reasoning_board, dict) else {}
    verdict = reasoning_board.get("verdict_board", {}) if isinstance(reasoning_board.get("verdict_board"), dict) else {}
    advocate = reasoning_board.get("advocate_report", {}) if isinstance(reasoning_board.get("advocate_report"), dict) else {}
    critic = reasoning_board.get("critic_report", {}) if isinstance(reasoning_board.get("critic_report"), dict) else {}
    normalized_input = self._normalize_text(user_input)

    if normalized_input and (requested_assistant_move or user_dialogue_act in {"correction", "initiative_request"}):
        return _shorten(normalized_input, 180)

    final_answer_brief = self._normalize_text(verdict.get("final_answer_brief"))
    if final_answer_brief:
        return _shorten(final_answer_brief, 180)

    advocate_summary = self._normalize_text(advocate.get("summary_of_position"))
    if advocate_summary:
        return _shorten(advocate_summary, 180)

    strategy_goal = self._normalize_text(response_strategy.get("answer_goal"))
    if strategy_goal:
        return _shorten(strategy_goal, 180)

    critic_brief = self._normalize_text(critic.get("situational_brief"))
    if critic_brief:
        return _shorten(critic_brief, 180)

    situational_brief = self._normalize_text(analysis_report.get("situational_brief"))
    if situational_brief:
        return _shorten(situational_brief, 180)

    if self._should_carry_previous_active_task(user_dialogue_act, previous):
        previous_task = self._normalize_text(previous.get("dialogue_state", {}).get("active_task"))
        if previous_task:
            return previous_task

    if normalized_input and user_dialogue_act in {"question_or_request", "correction", "statement"}:
        return _shorten(normalized_input, 180)
    return ""


def _memory_buffer_build_turn_summary_v3(self, working_memory: dict):
    dialogue = working_memory.get("dialogue_state", {})
    evidence = working_memory.get("evidence_state", {})
    response = working_memory.get("response_contract", {})

    parts = []
    if dialogue.get("user_dialogue_act"):
        parts.append(f"user_dialogue_act={dialogue['user_dialogue_act']}")
    if dialogue.get("active_task"):
        parts.append(f"active_task={dialogue['active_task']}")
    if dialogue.get("requested_assistant_move"):
        parts.append(f"requested_move={dialogue['requested_assistant_move']}")
    if dialogue.get("task_reset_applied"):
        reset_reason = str(dialogue.get("task_reset_reason") or "current_user_input_priority").strip()
        parts.append(f"task_reset={reset_reason}")
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


def _memory_buffer_build_working_memory_from_turn_v3(self, final_state, user_input, final_answer):
    previous = self.get_working_memory_snapshot()
    analysis_report = final_state.get("analysis_report", {})
    if not isinstance(analysis_report, dict):
        analysis_report = {}
    response_strategy = final_state.get("response_strategy", {})
    if not isinstance(response_strategy, dict):
        response_strategy = {}
    reasoning_board = final_state.get("reasoning_board", {})
    if not isinstance(reasoning_board, dict):
        reasoning_board = {}

    verdict = reasoning_board.get("verdict_board", {}) if isinstance(reasoning_board.get("verdict_board"), dict) else {}
    critic = reasoning_board.get("critic_report", {}) if isinstance(reasoning_board.get("critic_report"), dict) else {}
    fact_cells = reasoning_board.get("fact_cells", []) if isinstance(reasoning_board.get("fact_cells"), list) else []
    fact_map = {
        self._normalize_text(fact.get("fact_id")): fact
        for fact in fact_cells
        if isinstance(fact, dict) and self._normalize_text(fact.get("fact_id"))
    }

    approved_fact_ids = verdict.get("approved_fact_ids", []) if isinstance(verdict.get("approved_fact_ids"), list) else []
    evidence_facts = []
    evidence_source_ids = []
    for fact_id in approved_fact_ids:
        fact = fact_map.get(self._normalize_text(fact_id))
        if not fact:
            continue
        extracted_fact = self._normalize_text(fact.get("extracted_fact"))
        source_id = self._normalize_text(fact.get("source_id"))
        if extracted_fact:
            evidence_facts.append(extracted_fact)
        if source_id:
            evidence_source_ids.append(source_id)

    if not evidence_facts:
        evidences = analysis_report.get("evidences", []) if isinstance(analysis_report.get("evidences"), list) else []
        for item in evidences:
            if not isinstance(item, dict):
                continue
            fact = self._normalize_text(item.get("extracted_fact"))
            source_id = self._normalize_text(item.get("source_id"))
            if fact:
                evidence_facts.append(fact)
            if source_id:
                evidence_source_ids.append(source_id)

    recommended_searches = critic.get("recommended_searches", []) if isinstance(critic.get("recommended_searches"), list) else []
    suggested_next_search = self._normalize_text(
        (recommended_searches[0] if recommended_searches else "") or analysis_report.get("suggested_next_search")
    )

    unresolved_questions = []
    open_questions = critic.get("open_questions", []) if isinstance(critic.get("open_questions"), list) else []
    unresolved_questions.extend(self._normalize_list(open_questions, limit=5))
    objections = critic.get("objections", []) if isinstance(critic.get("objections"), list) else []
    for objection in objections:
        if not isinstance(objection, dict):
            continue
        objection_text = self._normalize_text(objection.get("objection_text"))
        if objection_text:
            unresolved_questions.append(objection_text)
    if suggested_next_search and bool(verdict.get("requires_search")):
        unresolved_questions.append(f"추가 수색 필요: {suggested_next_search}")

    user_feedback_signal = self._classify_user_feedback_signal(user_input)
    user_dialogue_act = self._classify_user_dialogue_act(user_input)
    requested_assistant_move = self._extract_requested_assistant_move(user_input)
    assistant_last_move = self._classify_assistant_last_move(final_answer, response_strategy)
    pending_question = self._extract_pending_question(final_answer)
    continuation_expected = assistant_last_move in {"question", "followup_offer"}
    initiative_requested = user_feedback_signal == "assistant_initiative_requested" or bool(requested_assistant_move)

    task_reset_applied = bool(requested_assistant_move) or user_dialogue_act == "correction"
    task_reset_reason = ""
    if requested_assistant_move:
        task_reset_reason = f"requested_move:{requested_assistant_move}"
    elif user_dialogue_act == "correction":
        task_reset_reason = "user_correction"

    verdict_action = _verdict_action_from_board(verdict, self._normalize_text(analysis_report.get("investigation_status")))
    if verdict_action in {"answer_now", "answer_with_search_reservation", "search_more"} or final_state.get("used_sources"):
        conversation_mode = "grounded_retrieval"
    elif requested_assistant_move == "ask_user_question_now":
        conversation_mode = "assistant_question_execution"
    elif initiative_requested:
        conversation_mode = "initiative_guidance"
    elif response_strategy.get("reply_mode") == "casual_reaction":
        conversation_mode = "casual_dialogue"
    else:
        conversation_mode = "general_dialogue"

    observed_preferences = list(previous["user_model_delta"].get("observed_preferences", []))
    friction_points = list(previous["user_model_delta"].get("friction_points", []))
    tone_preferences = list(previous["user_model_delta"].get("tone_preferences", []))

    if initiative_requested:
        observed_preferences.append("assistant_should_propose_directly")
        observed_preferences.append("avoid_bouncing_questions_back")
    if user_feedback_signal == "correction_or_pushback":
        friction_points.append(_shorten(user_input, 120))

    working_memory = {
        "version": "working_memory_v2",
        "dialogue_state": {
            "user_dialogue_act": user_dialogue_act,
            "assistant_last_move": assistant_last_move,
            "pending_question": pending_question,
            "active_task": self._derive_active_task(
                previous=previous,
                user_input=user_input,
                analysis_report=analysis_report,
                response_strategy=response_strategy,
                user_dialogue_act=user_dialogue_act,
                reasoning_board=reasoning_board,
                requested_assistant_move=requested_assistant_move,
            ),
            "active_task_source": "current_user_input" if task_reset_applied or user_dialogue_act in {"initiative_request", "correction"} else "inferred_context",
            "conversation_mode": conversation_mode,
            "continuation_expected": continuation_expected,
            "initiative_requested": initiative_requested,
            "requested_assistant_move": requested_assistant_move,
            "task_reset_applied": task_reset_applied,
            "task_reset_reason": task_reset_reason,
            "user_feedback_signal": user_feedback_signal,
        },
        "evidence_state": {
            "last_investigation_status": self._normalize_text(analysis_report.get("investigation_status") or verdict_action.upper()),
            "verdict_action": self._normalize_text(verdict_action),
            "active_source_ids": self._normalize_list(
                list(final_state.get("used_sources", [])) + evidence_source_ids,
                limit=8,
            ),
            "evidence_facts": self._normalize_list(evidence_facts, limit=5),
            "unresolved_questions": self._normalize_list(unresolved_questions, limit=5),
            "suggested_next_search": suggested_next_search,
            "judge_notes": self._normalize_list(verdict.get("judge_notes", []), limit=5),
        },
        "response_contract": {
            "reply_mode": self._normalize_text(response_strategy.get("reply_mode")),
            "answer_goal": self._normalize_text(response_strategy.get("answer_goal")),
            "must_include_facts": self._normalize_list(
                response_strategy.get("must_include_facts", []) or evidence_facts,
                limit=5
            ),
            "must_avoid_claims": self._normalize_list(
                response_strategy.get("must_avoid_claims", []), limit=5
            ),
            "direct_answer_seed": self._normalize_text(
                verdict.get("final_answer_brief") or response_strategy.get("direct_answer_seed")
            ),
        },
        "user_model_delta": {
            "observed_preferences": self._normalize_list(observed_preferences, limit=8),
            "friction_points": self._normalize_list(friction_points, limit=6),
            "tone_preferences": self._normalize_list(tone_preferences, limit=6),
        },
        "last_turn": {
            "user_input": self._normalize_text(user_input),
            "assistant_answer": self._normalize_text(final_answer),
            "auditor_instruction": self._normalize_text(final_state.get("auditor_instruction")),
            "loop_count": int(final_state.get("loop_count", 0) or 0),
            "used_sources": self._normalize_list(final_state.get("used_sources", []), limit=8),
        },
    }
    working_memory["turn_summary"] = self._build_turn_summary(working_memory)
    return self._normalize_working_memory(working_memory)


def _memory_buffer_get_working_memory_string_v3(self):
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
    if evidence["verdict_action"]:
        lines.append(f"- verdict_action: {evidence['verdict_action']}")
    if evidence["last_investigation_status"]:
        lines.append(f"- last_investigation_status: {evidence['last_investigation_status']}")
    if evidence["active_source_ids"]:
        lines.append(f"- active_source_ids: {', '.join(evidence['active_source_ids'])}")
    if evidence["evidence_facts"]:
        lines.append(f"- evidence_facts: {' / '.join(evidence['evidence_facts'][:3])}")
    if evidence["unresolved_questions"]:
        lines.append(f"- unresolved_questions: {' / '.join(evidence['unresolved_questions'][:2])}")
    if evidence["judge_notes"]:
        lines.append(f"- judge_notes: {' / '.join(evidence['judge_notes'][:2])}")
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


MemoryBuffer._derive_active_task = _memory_buffer_derive_active_task_v3
MemoryBuffer._build_turn_summary = _memory_buffer_build_turn_summary_v3
MemoryBuffer.build_working_memory_from_turn = _memory_buffer_build_working_memory_from_turn_v3
MemoryBuffer.get_working_memory_string = _memory_buffer_get_working_memory_string_v3


def _memory_buffer_get_tactical_context_v3(self):
    recent_raw = ""
    for msg in self.history[-5:]:
        speaker = "user" if msg["role"] == "user" else "assistant"
        recent_raw += f"[{speaker}]: {msg['content']}\n"
    return f"{self.get_working_memory_string()}\n\n[Recent Raw Turns]\n{recent_raw}"


MemoryBuffer.get_tactical_context = _memory_buffer_get_tactical_context_v3
