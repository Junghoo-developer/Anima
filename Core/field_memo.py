import hashlib
import json
import math
import os
import re
import time
import unicodedata
from collections import defaultdict
from typing import Any, List

import ollama
from pydantic import BaseModel, Field

from Core.adapters.neo4j_connection import get_db_session
from Core.memory.field_memo_writer import (
    FieldMemoWriterDecision,
    normalize_field_memo_writer_decision,
    write_field_memo_decision,
)


INBOX_BRANCH_PATH = "Inbox/unclassified"
PENDING_FIELD_MEMO_STATUS = "pending_classification"
PENDING_BRANCH_STATUS = "pending"
OFFICIAL_FIELD_MEMO_STATUSES = {"active", "verified"}
OFFICIAL_BRANCH_STATUSES = {"active", "verified"}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _norm(text: Any) -> str:
    return unicodedata.normalize("NFKC", str(text or "")).strip()


def _trim(text: Any, limit: int = 320) -> str:
    value = _norm(text)
    if len(value) <= limit:
        return value
    return value[: max(limit - 3, 0)].rstrip() + "..."


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return json.dumps(str(value), ensure_ascii=False)


def _json_object_from_text(text: Any) -> dict:
    value = _norm(text)
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_json_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    try:
        loaded = json.loads(str(value))
        return loaded if isinstance(loaded, list) else []
    except Exception:
        return []


def _dedupe_keep_order(items: list[Any], limit: int | None = None) -> list:
    seen = set()
    result = []
    for item in items or []:
        text = _norm(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if limit and len(result) >= limit:
            break
    return result


def _safe_slug(text: Any, limit: int = 80) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    normalized = re.sub(r"[^0-9a-zA-Z가-힣_-]+", "_", normalized).strip("_")
    if not normalized:
        normalized = hashlib.sha1(str(text or "").encode("utf-8", errors="ignore")).hexdigest()[:12]
    return normalized[:limit]


def _memo_hash(*parts: Any) -> str:
    joined = "\n".join(_norm(part) for part in parts if _norm(part))
    return hashlib.sha1(joined.encode("utf-8", errors="ignore")).hexdigest()[:18]


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not isinstance(v1, list) or not isinstance(v2, list) or len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(float(a) * float(a) for a in v1))
    norm2 = math.sqrt(sum(float(b) * float(b) for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def _try_embed_text(text: Any, model_name: str = "nomic-embed-text") -> tuple[list[float], str]:
    payload = _trim(text, 1800)
    if len(payload) < 4:
        return [], ""
    try:
        response = ollama.embeddings(model=model_name, prompt=payload)
        embedding = response.get("embedding") if isinstance(response, dict) else None
        if isinstance(embedding, list) and embedding:
            return [float(value) for value in embedding], model_name
    except Exception:
        return [], ""
    return [], ""


def _memo_embedding_text(props: dict) -> str:
    if not isinstance(props, dict):
        return ""
    parts = [
        props.get("title"),
        props.get("summary"),
        " / ".join(str(item) for item in props.get("known_facts", []) or []),
        " / ".join(str(item) for item in props.get("entities", []) or []),
        " / ".join(str(item) for item in props.get("events", []) or []),
        props.get("branch_path"),
        props.get("official_branch_path"),
        props.get("proposed_branch_path"),
        props.get("branch_hint"),
        props.get("summary_scope"),
    ]
    return "\n".join(_norm(part) for part in parts if _norm(part))


def _memo_level(memo: dict) -> int:
    try:
        level = int(memo.get("memo_level", 1) or 1)
    except Exception:
        level = 1
    return max(1, min(level, 8))


def _is_inbox_branch(branch_path: Any) -> bool:
    return _norm(branch_path).lower() == INBOX_BRANCH_PATH.lower()


def field_memo_has_official_branch(memo: dict) -> bool:
    """True only when a FieldMemo has been classified by the night branch authority."""
    if not isinstance(memo, dict):
        return False
    status = (_norm(memo.get("status")) or "active").lower()
    if status not in OFFICIAL_FIELD_MEMO_STATUSES:
        return False
    branch_path = _norm(memo.get("branch_path"))
    if not branch_path or _is_inbox_branch(branch_path):
        return False
    branch_status = _norm(memo.get("branch_status")).lower()
    if branch_status and branch_status not in OFFICIAL_BRANCH_STATUSES:
        return False
    return True


def official_field_memos(field_memos: list[dict]) -> list[dict]:
    return [memo for memo in field_memos or [] if field_memo_has_official_branch(memo)]


def field_memo_needs_branch_classification(memo: dict) -> bool:
    if not isinstance(memo, dict):
        return False
    status = (_norm(memo.get("status")) or PENDING_FIELD_MEMO_STATUS).lower()
    branch_status = (_norm(memo.get("branch_status")) or PENDING_BRANCH_STATUS).lower()
    return status == PENDING_FIELD_MEMO_STATUS or branch_status == PENDING_BRANCH_STATUS or _is_inbox_branch(memo.get("branch_path"))


def build_branch_classification_contract(memo: dict) -> dict:
    """Build the night-loop contract for assigning an official branch path."""
    memo = memo if isinstance(memo, dict) else {}
    known_facts = _load_json_list(memo.get("known_facts_json")) or list(memo.get("known_facts", []) or [])
    return {
        "contract_type": "field_memo_branch_classification",
        "memo_id": _norm(memo.get("memo_id")),
        "current_branch_path": _norm(memo.get("branch_path")) or INBOX_BRANCH_PATH,
        "current_status": _norm(memo.get("status")) or PENDING_FIELD_MEMO_STATUS,
        "current_branch_status": _norm(memo.get("branch_status")) or PENDING_BRANCH_STATUS,
        "proposed_branch_path": _norm(memo.get("proposed_branch_path")),
        "branch_hint": _norm(memo.get("branch_hint")),
        "proposed_root_entity": _norm(memo.get("proposed_root_entity")),
        "memo_kind": _norm(memo.get("memo_kind")),
        "title": _norm(memo.get("title")),
        "summary": _trim(memo.get("summary"), 520),
        "known_facts": _dedupe_keep_order(known_facts, limit=8),
        "entities": _memo_list_field(memo, "entities", "entities_json", limit=8),
        "required_output_schema": {
            "classification_status": "approved | needs_more_review | rejected",
            "official_branch_path": "Existing or newly approved REM branch path; never Inbox/unclassified.",
            "root_entity": "Official root entity for the branch.",
            "classification_note": "Brief reason tied to memo facts and branch taxonomy.",
        },
        "rules": [
            "Do not trust proposed_branch_path as official; treat it only as a hint.",
            "Approve only if the branch path matches the night taxonomy and the memo facts support it.",
            "If unsure, return needs_more_review and keep the memo in Inbox/unclassified.",
        ],
    }


def apply_branch_classification_decision(memo: dict, decision: dict) -> dict:
    """Apply a night-loop branch classification decision without inventing taxonomy in the field loop."""
    memo = dict(memo or {})
    decision = decision if isinstance(decision, dict) else {}
    classification_status = _norm(decision.get("classification_status")).lower()
    official_branch_path = _norm(decision.get("official_branch_path") or decision.get("branch_path"))
    if classification_status not in {"approved", "active", "verified"} or not official_branch_path or _is_inbox_branch(official_branch_path):
        memo["branch_status"] = PENDING_BRANCH_STATUS
        memo["status"] = PENDING_FIELD_MEMO_STATUS
        memo["classification_note"] = _trim(decision.get("classification_note") or "Night branch classification is still pending.", 260)
        return memo

    memo["branch_path"] = official_branch_path
    memo["official_branch_path"] = official_branch_path
    memo["root_entity"] = _norm(decision.get("root_entity")) or _norm(memo.get("proposed_root_entity"))
    memo["branch_status"] = "verified" if classification_status == "verified" else "active"
    memo["status"] = "verified" if classification_status == "verified" else "active"
    memo["classification_note"] = _trim(decision.get("classification_note") or "Approved by night branch classification.", 260)
    memo["classified_at"] = _now_ms()
    return memo


class FieldMemoItem(BaseModel):
    memo_id: str
    memo_kind: str = "field_observation"
    title: str = ""
    summary: str = ""
    known_facts: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    events: List[str] = Field(default_factory=list)
    place_refs: List[str] = Field(default_factory=list)
    causal_links: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    branch_path: str = ""
    root_entity: str = ""
    branch_status: str = PENDING_BRANCH_STATUS
    official_branch_path: str = ""
    proposed_branch_path: str = ""
    branch_hint: str = ""
    proposed_root_entity: str = ""
    classification_note: str = ""
    classified_at: int = 0
    source_turn_process_ids: List[str] = Field(default_factory=list)
    source_phase_snapshot_ids: List[str] = Field(default_factory=list)
    queried_field_memo_ids: List[str] = Field(default_factory=list)
    status: str = "active"
    supersedes_memo_ids: List[str] = Field(default_factory=list)
    contradicts_memo_ids: List[str] = Field(default_factory=list)
    truth_maintenance_note: str = ""
    memo_level: int = 1
    parent_memo_ids: List[str] = Field(default_factory=list)
    synthesis_source_memo_ids: List[str] = Field(default_factory=list)
    summary_scope: str = "turn"
    embedding_model: str = ""
    embedding: List[float] = Field(default_factory=list)
    confidence: float = 0.55
    created_at: int = Field(default_factory=_now_ms)


class FieldMemoRecallPacket(BaseModel):
    query: str
    matched_memo_ids: List[str] = Field(default_factory=list)
    known_facts: List[str] = Field(default_factory=list)
    unknown_slots: List[str] = Field(default_factory=list)
    relevance_notes: List[str] = Field(default_factory=list)
    answer_boundary: str = ""


class BranchOfficeItem(BaseModel):
    office_key: str
    branch_path: str
    root_entity: str
    title: str
    local_summary: str = ""
    active_questions: List[str] = Field(default_factory=list)
    memo_pressure: float = 0.0
    fact_health: str = "unknown"
    policy_health: str = "unknown"
    last_report: str = ""
    status: str = "active"
    memo_ids: List[str] = Field(default_factory=list)
    layered_memo_ids: List[str] = Field(default_factory=list)


class LocalReportItem(BaseModel):
    office_key: str
    branch_path: str
    report_summary: str = ""
    wiki_candidates: List[str] = Field(default_factory=list)
    policy_candidates: List[str] = Field(default_factory=list)
    blocked_reasons: List[str] = Field(default_factory=list)
    governor_feedback: List[str] = Field(default_factory=list)


class LayeredMemoItem(FieldMemoItem):
    memo_kind: str = "layered_synthesis"
    memo_level: int = 2
    summary_scope: str = "branch_synthesis"
    status: str = "active"
    branch_status: str = "active"


def is_memory_state_disclosure_turn(user_input: str) -> bool:
    """Current-turn memory/reset disclosures are not memory-recall requests."""
    text = _norm(user_input).lower()
    if not text or len(text) < 5:
        return False
    compact = re.sub(r"\s+", "", text)

    memory_terms = [
        "\uae30\uc5b5",
        "memory",
        "memories",
    ]
    reset_terms = [
        "\uc18c\uac70",
        "\uc9c0\uc6e0",
        "\uc9c0\uc6cc",
        "\uc0ad\uc81c",
        "\ucd08\uae30\ud654",
        "\ucd08\uae30",
        "\ube44\uc6e0",
        "\ube44\uc6cc",
        "\ub0a0\ub824",
        "\ub9ac\ubd80\ud2b8",
        "reset",
        "wipe",
        "wiped",
        "erase",
        "erased",
        "delete",
        "deleted",
        "clear",
        "cleared",
        "reboot",
    ]
    request_terms = [
        "?",
        "\uae30\uc5b5\ub098",
        "\uae30\uc5b5\ud574",
        "\ucc3e\uc544",
        "\uac80\uc0c9",
        "\ud655\uc778",
        "\uc54c\uc544",
        "\ub9d0\ud574",
        "\uc124\uba85",
        "\uc815\ub9ac",
        "\ud68c\uc218",
        "remember?",
        "recall",
        "search",
        "find",
        "look up",
        "tell me",
        "explain",
    ]
    apology_or_report_terms = [
        "\ubbf8\uc548",
        "\uc654\uc5b4",
        "\ud588\uc5b4",
        "\ud588\ub2e4",
        "\ud574\ub450\uc5c8",
        "\ud574\ub193",
        "\uc54c\ub824",
        "sorry",
        "i ",
        "i'",
        "ive",
        "i've",
        "we ",
    ]

    has_memory = any(term in compact or term in text for term in memory_terms)
    has_reset = any(term in compact or term in text for term in reset_terms)
    asks_recall = any(term in compact or term in text for term in request_terms)
    is_report = any(term in compact or term in text for term in apology_or_report_terms)
    return bool(has_memory and has_reset and is_report and not asks_recall)


def _looks_like_memory_story_share(user_input: str) -> bool:
    text = _norm(user_input)
    if not text or "?" in text:
        return False
    lowered = text.lower()
    request_markers = ["remember", "recall", "search", "find", "\uae30\uc5b5\ud574", "\ucc3e\uc544", "\uac80\uc0c9"]
    if any(marker in lowered for marker in request_markers):
        return False
    story_markers = ["when i", "back then", "as a kid", "\uc5b4\ub9b4", "\uadf8\ub54c", "\uc608\uc804", "\uc720\uce58\uc6d0", "\ud559\uad50"]
    first_person_markers = [" i ", " my ", "\ub098", "\ub0b4", "\ub0b4\uac00"]
    has_story_signal = any(marker in lowered for marker in story_markers)
    has_personal_signal = any(marker in lowered for marker in first_person_markers)
    return bool((has_story_signal and has_personal_signal) or (len(text) >= 45 and has_personal_signal))
def looks_like_memo_recall_turn(user_input: str) -> bool:
    text = _norm(user_input)
    lowered = text.lower()
    if not text or len(text) < 5:
        return False
    if is_memory_state_disclosure_turn(text):
        return False
    if _looks_like_memory_story_share(text):
        return False

    explicit_markers = [
        "recall",
        "remember",
        "previous",
        "earlier",
        "\uae30\uc5b5\ub098",
        "\uae30\uc5b5\ud574",
        "\uc544\uae4c",
        "\uc608\uc804\uc5d0",
        "\ub9d0\ud588\uc796\uc544",
    ]
    return any(marker in lowered for marker in explicit_markers)


def _looks_like_short_chitchat(text: str) -> bool:
    compact = re.sub(r"\s+", "", _norm(text).lower())
    if not compact:
        return True
    if len(compact) > 38:
        return False
    return compact in {"ok", "okay", "yes", "yep", "lol", "haha", "ㅇㅇ", "응", "그래", "좋아", "아니"}


def _extract_entities(text: str) -> list[str]:
    text = _norm(text)
    quoted = re.findall(r"[\"'`“”‘’](.{1,32}?)[\"'`“”‘’]", text)
    named_by_phrase = re.findall(r"\b([가-힣A-Za-z0-9][가-힣A-Za-z0-9_-]{1,24})(?:이라고|라는|called|named)\b", text, flags=re.IGNORECASE)
    known_names = re.findall(r"\b(OMORI|ANIMA|Gemini|Codex|SongRyeon|Sunny)\b", text, flags=re.IGNORECASE)
    english = re.findall(r"\b[A-Z][A-Za-z0-9_-]{2,}\b", text)
    korean_candidates = re.findall(r"\b[가-힣]{2,12}\b", text)
    return _dedupe_keep_order(quoted + named_by_phrase + known_names + english + korean_candidates, limit=12)


def _split_fact_sentences(text: str, limit: int = 8) -> list[str]:
    normalized = re.sub(r"\s+", " ", _norm(text))
    if not normalized:
        return []
    chunks = re.split(r"(?<=[.!?])\s+", normalized)
    results = []
    for chunk in chunks:
        cleaned = chunk.strip(" -")
        if len(cleaned) < 12:
            continue
        results.append(_trim(cleaned, 260))
    return _dedupe_keep_order(results, limit=limit)


def _extract_places(text: str) -> list[str]:
    _ = text
    return []


def _extract_open_questions(final_state: dict, user_input: str, final_answer: str) -> list[str]:
    questions = []
    analysis = final_state.get("analysis_report", {}) if isinstance(final_state.get("analysis_report"), dict) else {}
    for judgment in analysis.get("source_judgments", []) or []:
        if isinstance(judgment, dict):
            questions.extend(judgment.get("missing_info", []) or [])
    if "?" in user_input:
        questions.append(_trim(user_input, 180))
    answer = _norm(final_answer)
    if any(marker in answer.lower() for marker in ["not enough", "cannot confirm", "unclear"]):
        questions.append("The answer reported insufficient evidence.")
    return _dedupe_keep_order(questions, limit=8)


def _infer_branch_path(user_input: str, final_state: dict, memo_kind: str) -> tuple[str, str]:
    _ = (user_input, final_state, memo_kind)
    return "Person/knowledge/field_memory", "Person:field_memory"

def _looks_like_story_listening_input(user_input: str) -> bool:
    text = _norm(user_input)
    lowered = text.lower()
    if not text:
        return False
    if "?" in text:
        return False
    if any(marker in lowered for marker in ["recall", "remember", "search", "find", "\ucc3e\uc544", "\uac80\uc0c9"]):
        return False
    personal_markers = [" i ", " my ", "\ub098", "\ub0b4", "\ub0b4\uac00"]
    story_markers = ["story", "when i", "back then", "\uc774\uc57c\uae30", "\uadf8\ub54c", "\uc608\uc804", "\uc5b4\ub9b4"]
    return len(text) >= 45 and (
        any(marker in lowered for marker in personal_markers)
        or any(marker in lowered for marker in story_markers)
    )


def extract_queried_field_memo_ids(search_results: str) -> list[str]:
    text = _norm(search_results)
    if not text:
        return []
    ids = re.findall(r"memo_id\s*[:=]\s*([A-Za-z0-9가-힣.:/-]+)", text)
    ids.extend(re.findall(r"\b(field_memo::[A-Za-z0-9가-힣.:/-]+)", text))
    return _dedupe_keep_order(ids, limit=12)


def _field_memo_ids_from_working_memory(working_memory: dict | None) -> list[str]:
    working_memory = working_memory if isinstance(working_memory, dict) else {}
    ids: list[str] = []
    evidence = working_memory.get("evidence_state", {})
    if isinstance(evidence, dict):
        ids.extend(str(item).strip() for item in evidence.get("active_source_ids", []) if str(item).strip())
    tool_carryover = working_memory.get("tool_carryover", {})
    if isinstance(tool_carryover, dict):
        ids.extend(str(item).strip() for item in tool_carryover.get("source_ids", []) if str(item).strip())
    return _dedupe_keep_order([item for item in ids if item.startswith("field_memo::")], limit=12)


def _looks_like_user_correction(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", _norm(text)).lower()
    if not normalized:
        return False
    stable_markers = [
        "\uc544\ub2c8",
        "\uadf8\uac8c \uc544\ub2c8",
        "\uadf8 \ubc18\ub300",
        "\ubc18\ub300\uc57c",
        "\uc815\ud655\ud788\ub294",
        "\uc2e4\uc740",
        "\ud2c0\ub838",
        "\ud2c0\ub9b0",
        "\uc624\ub2f5",
        "\uac1c\uc18c\ub9ac",
        "\ubb50\ub77c\uace0",
        "\ubb50\ub77c",
        "\ubb54 \uc18c\ub9ac",
        "\ubb54\uc18c\ub9ac",
        "\uace0\uc9d1",
        "\ucc29\uac01",
        "\ub2e4\uc2dc \ub9d0",
    ]
    if any(marker in normalized for marker in stable_markers):
        return True
    return False


def _field_memo_fact_text(value) -> str:
    if isinstance(value, dict):
        for key in ("fact", "text", "extracted_fact", "claim", "summary", "answer_brief"):
            text = _norm(value.get(key))
            if text:
                return text
        return ""
    return _norm(value)


def _looks_like_low_trust_field_memo_fact(text: str) -> bool:
    normalized = _norm(text).lower()
    if not normalized:
        return True
    low_trust_markers = [
        "answer_not_ready",
        "current_goal_answer_seed",
        "memory.referent_fact",
        "missing_slot",
        "unfilled_slot",
        "field_memo_empty",
        "tool_search_field_memos",
        "tool_search_memory",
        "search result",
        "no direct answer",
        "not enough evidence",
    ]
    return any(marker in normalized for marker in low_trust_markers)


def _verified_field_memo_facts(final_state: dict) -> list[str]:
    final_state = final_state if isinstance(final_state, dict) else {}
    analysis = final_state.get("analysis_report", {}) if isinstance(final_state.get("analysis_report"), dict) else {}
    payload = final_state.get("phase3_delivery_payload", {}) if isinstance(final_state.get("phase3_delivery_payload"), dict) else {}
    start_gate_contract = final_state.get("start_gate_contract", {}) if isinstance(final_state.get("start_gate_contract"), dict) else {}
    start_gate_switches = final_state.get("start_gate_switches", {}) if isinstance(final_state.get("start_gate_switches"), dict) else {}
    response_strategy = final_state.get("response_strategy", {}) if isinstance(final_state.get("response_strategy"), dict) else {}
    facts: list[str] = []

    for key in ("accepted_facts", "verified_facts", "usable_field_memo_facts"):
        facts.extend(_field_memo_fact_text(item) for item in analysis.get(key, []) or [])
        facts.extend(_field_memo_fact_text(item) for item in payload.get(key, []) or [])

    for judgment in analysis.get("source_judgments", []) or []:
        if not isinstance(judgment, dict):
            continue
        status = _norm(judgment.get("source_status") or judgment.get("status")).lower()
        if status not in {"pass", "accepted", "completed", "usable"}:
            continue
        for key in ("accepted_facts", "facts", "known_facts"):
            facts.extend(_field_memo_fact_text(item) for item in judgment.get(key, []) or [])

    policy_candidates = [
        final_state.get("answer_mode_policy"),
        start_gate_contract.get("answer_mode_policy"),
        start_gate_switches.get("answer_mode_policy"),
        payload.get("answer_mode_policy"),
    ]
    current_turn_grounded = any(
        isinstance(policy, dict)
        and (
            str(policy.get("preferred_answer_mode") or "").strip() == "current_turn_grounding"
            or bool(policy.get("current_turn_grounding_ready"))
        )
        for policy in policy_candidates
    )
    turn_contract = start_gate_contract.get("turn_contract", {})
    if isinstance(turn_contract, dict):
        current_turn_grounded = current_turn_grounded or str(turn_contract.get("answer_mode_preference") or "").strip() == "current_turn_grounding"
    if current_turn_grounded:
        for packet in (payload, start_gate_contract, start_gate_switches, response_strategy):
            if not isinstance(packet, dict):
                continue
            for key in ("current_turn_facts", "must_include_facts"):
                facts.extend(_field_memo_fact_text(item) for item in packet.get(key, []) or [])
        if isinstance(turn_contract, dict):
            facts.extend(_field_memo_fact_text(item) for item in turn_contract.get("current_turn_facts", []) or [])

    clean = [
        fact
        for fact in (_norm(item) for item in facts)
        if fact and not _looks_like_low_trust_field_memo_fact(fact)
    ]
    return _dedupe_keep_order(clean, limit=8)


def should_create_field_memo(final_state: dict, user_input: str, final_answer: str, working_memory: dict | None = None) -> bool:
    text = _norm(user_input)
    if not text:
        return False
    final_state = final_state if isinstance(final_state, dict) else {}
    del final_answer, working_memory
    return bool(_verified_field_memo_facts(final_state))


def _working_memory_durable_fact_candidates(working_memory: dict | None) -> list[str]:
    working_memory = working_memory if isinstance(working_memory, dict) else {}
    memory_writer = working_memory.get("memory_writer", {})
    if not isinstance(memory_writer, dict):
        return []
    recommendation = _norm(memory_writer.get("field_memo_write_recommendation")).lower()
    if recommendation != "write":
        return []
    facts = memory_writer.get("durable_fact_candidates", [])
    if not isinstance(facts, list):
        return []
    clean = [
        fact
        for fact in (_norm(item) for item in facts)
        if fact and not _looks_like_low_trust_field_memo_fact(fact)
    ]
    return _dedupe_keep_order(clean, limit=8)


def _normalize_field_memo_writer_decision(value: Any, candidate_facts: list[str]) -> dict:
    return normalize_field_memo_writer_decision(value, candidate_facts)


def _field_memo_writer_decision(
    *,
    final_state: dict,
    user_input: str,
    final_answer: str,
    working_memory: dict,
    canonical_turn: dict,
    candidate_facts: list[str],
    recent_context: str = "",
) -> dict:
    return write_field_memo_decision(
        final_state=final_state,
        user_input=user_input,
        final_answer=final_answer,
        working_memory=working_memory,
        canonical_turn=canonical_turn,
        candidate_facts=candidate_facts,
        recent_context=recent_context,
    )

def _build_verified_field_memo_candidate_v2(
    final_state: dict,
    user_input: str,
    final_answer: str,
    working_memory: dict,
    canonical_turn: dict,
    verified_facts: list[str],
    writer_decision: dict | None = None,
) -> dict | None:
    search_results = _norm(final_state.get("search_results"))
    writer_decision = writer_decision if isinstance(writer_decision, dict) else {}
    memo_kind = _norm(writer_decision.get("memo_kind")) or "verified_fact_packet"
    if memo_kind == "durable_fact":
        memo_kind = "verified_fact_packet"
    if memo_kind == "correction_to_existing_fact":
        memo_kind = "user_correction_fact"
    correction_turn = memo_kind == "user_correction_fact"
    inferred_branch_path, inferred_root_entity = _infer_branch_path(user_input, final_state, memo_kind)
    proposed_branch_path = _norm(writer_decision.get("branch_path")) or inferred_branch_path
    proposed_root_entity = _norm(writer_decision.get("root_entity")) or inferred_root_entity
    branch_hint = proposed_branch_path
    branch_path = INBOX_BRANCH_PATH
    root_entity = ""
    known_facts = _dedupe_keep_order(writer_decision.get("known_facts") or verified_facts, limit=8)
    if not known_facts:
        return None

    queried_memo_ids = _dedupe_keep_order(
        extract_queried_field_memo_ids(search_results) + _field_memo_ids_from_working_memory(working_memory),
        limit=12,
    )
    summary = _trim(writer_decision.get("summary") or " / ".join(known_facts[:3]), 520)
    entities = _dedupe_keep_order(
        list(writer_decision.get("entities", []) or [])
        + _extract_entities("\n".join([user_input, search_results, summary])),
        limit=8,
    )
    title_branch = proposed_branch_path or branch_path
    title_base = _norm(writer_decision.get("title")) or (entities[0] if entities else (title_branch.split("/")[-1] if title_branch else memo_kind))
    memo_id = f"field_memo::{_safe_slug(title_branch, 48)}::{_memo_hash(user_input, final_answer, summary)}"
    turn_process = canonical_turn.get("turn_process", {}) if isinstance(canonical_turn.get("turn_process"), dict) else {}
    phase_snapshots = canonical_turn.get("phase_snapshots", []) if isinstance(canonical_turn.get("phase_snapshots"), list) else []
    source_phase_ids = [
        str(snapshot.get("id") or "").strip()
        for snapshot in phase_snapshots
        if isinstance(snapshot, dict) and str(snapshot.get("id") or "").strip()
    ]
    truth_note = (
        writer_decision.get("truth_maintenance_note")
        or "User correction/pushback: verify against referenced FieldMemos before reuse."
        if correction_turn
        else writer_decision.get("truth_maintenance_note")
        or "Verified fact packet only; failed searches and answer_not_ready turns are excluded."
    )
    return FieldMemoItem(
        memo_id=memo_id,
        memo_kind=memo_kind,
        title=_trim(title_base if str(title_base).endswith("field memo") else f"{title_base} field memo", 80),
        summary=summary,
        known_facts=known_facts,
        entities=entities,
        events=_dedupe_keep_order(list(writer_decision.get("events", []) or []) + known_facts, limit=6),
        place_refs=_dedupe_keep_order(list(writer_decision.get("place_refs", []) or []) + _extract_places(user_input), limit=6),
        causal_links=_dedupe_keep_order(writer_decision.get("causal_links", []) or [], limit=6),
        open_questions=_dedupe_keep_order(writer_decision.get("open_questions", []) or [], limit=6),
        branch_path=branch_path,
        root_entity=root_entity,
        branch_status=PENDING_BRANCH_STATUS,
        official_branch_path="",
        proposed_branch_path=proposed_branch_path,
        branch_hint=branch_hint,
        proposed_root_entity=proposed_root_entity,
        source_turn_process_ids=_dedupe_keep_order([turn_process.get("process_id") or turn_process.get("id")], limit=4),
        source_phase_snapshot_ids=source_phase_ids,
        queried_field_memo_ids=queried_memo_ids,
        status=PENDING_FIELD_MEMO_STATUS,
        supersedes_memo_ids=queried_memo_ids if correction_turn else [],
        contradicts_memo_ids=queried_memo_ids if correction_turn else [],
        truth_maintenance_note=truth_note,
        memo_level=1,
        parent_memo_ids=[],
        synthesis_source_memo_ids=[],
        summary_scope=memo_kind,
        confidence=max(0.5, min(_safe_float(writer_decision.get("confidence"), 0.82), 1.0)),
    ).model_dump()


def build_field_memo_candidate(
    final_state: dict,
    user_input: str,
    final_answer: str,
    working_memory: dict | None = None,
    canonical_turn: dict | None = None,
    recent_context: str = "",
) -> dict | None:
    final_state = final_state if isinstance(final_state, dict) else {}
    working_memory = working_memory if isinstance(working_memory, dict) else {}
    canonical_turn = canonical_turn if isinstance(canonical_turn, dict) else {}
    if not should_create_field_memo(final_state, user_input, final_answer, working_memory):
        return None
    candidate_facts = _dedupe_keep_order(
        _verified_field_memo_facts(final_state),
        limit=8,
    )
    if not candidate_facts:
        return None
    writer_decision = _field_memo_writer_decision(
        final_state=final_state,
        user_input=user_input,
        final_answer=final_answer,
        working_memory=working_memory,
        canonical_turn=canonical_turn,
        candidate_facts=candidate_facts,
        recent_context=recent_context,
    )
    if not bool(writer_decision.get("should_write")):
        return None
    return _build_verified_field_memo_candidate_v2(
        final_state,
        user_input,
        final_answer,
        working_memory,
        canonical_turn,
        candidate_facts,
        writer_decision=writer_decision,
    )

def _phase_snapshot_id(process_id: str, phase_name: str, phase_order: int) -> str:
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in str(phase_name or "").strip()) or "phase"
    return f"{process_id}_{phase_order}_{safe_name}"[:500]


def _root_parts(root_entity: str) -> tuple[str, str]:
    root = _norm(root_entity)
    if ":" in root:
        label, _, name = root.partition(":")
        label = label if label in {"Person", "CoreEgo"} else "Person"
        return label, name or ("songryeon" if label == "CoreEgo" else "stable")
    if root == "CoreEgo":
        return "CoreEgo", "songryeon"
    return "Person", "stable"


def persist_field_memo(
    memo: dict | None,
    *,
    dream_id: str = "",
    canonical_turn: dict | None = None,
    log_prefix: str = "[FieldMemo]",
) -> bool:
    if not isinstance(memo, dict) or not memo.get("memo_id"):
        return False
    canonical_turn = canonical_turn if isinstance(canonical_turn, dict) else {}
    process_id = str((canonical_turn.get("turn_process") or {}).get("process_id") or (f"{dream_id}_process" if dream_id else "")).strip()
    phase_snapshots = canonical_turn.get("phase_snapshots", []) if isinstance(canonical_turn.get("phase_snapshots"), list) else []
    phase_snapshot_ids = []
    for snapshot in phase_snapshots:
        if not isinstance(snapshot, dict):
            continue
        phase_name = str(snapshot.get("phase_name") or "").strip()
        phase_order = int(snapshot.get("phase_order", 0) or 0)
        if process_id and phase_name:
            phase_snapshot_ids.append(_phase_snapshot_id(process_id, phase_name, phase_order))

    source_turn_process_ids = _dedupe_keep_order(list(memo.get("source_turn_process_ids", []) or []) + ([process_id] if process_id else []), limit=6)
    source_phase_snapshot_ids = _dedupe_keep_order(list(memo.get("source_phase_snapshot_ids", []) or []) + phase_snapshot_ids, limit=16)
    root_label, root_name = _root_parts(str(memo.get("root_entity") or ""))
    memo_level = _memo_level(memo)
    parent_memo_ids = _dedupe_keep_order(list(memo.get("parent_memo_ids", []) or []), limit=24)
    synthesis_source_memo_ids = _dedupe_keep_order(list(memo.get("synthesis_source_memo_ids", []) or []), limit=48)
    props = {
        "memo_id": str(memo.get("memo_id") or "").strip(),
        "memo_kind": str(memo.get("memo_kind") or "field_observation").strip(),
        "title": str(memo.get("title") or "").strip(),
        "summary": str(memo.get("summary") or "").strip(),
        "known_facts_json": _safe_json(list(memo.get("known_facts", []) or [])),
        "entities_json": _safe_json(list(memo.get("entities", []) or [])),
        "events_json": _safe_json(list(memo.get("events", []) or [])),
        "place_refs_json": _safe_json(list(memo.get("place_refs", []) or [])),
        "causal_links_json": _safe_json(list(memo.get("causal_links", []) or [])),
        "open_questions_json": _safe_json(list(memo.get("open_questions", []) or [])),
        "known_facts": list(memo.get("known_facts", []) or []),
        "entities": list(memo.get("entities", []) or []),
        "events": list(memo.get("events", []) or []),
        "place_refs": list(memo.get("place_refs", []) or []),
        "open_questions": list(memo.get("open_questions", []) or []),
        "branch_path": str(memo.get("branch_path") or "").strip(),
        "root_entity": str(memo.get("root_entity") or "").strip(),
        "branch_status": str(memo.get("branch_status") or PENDING_BRANCH_STATUS).strip() or PENDING_BRANCH_STATUS,
        "official_branch_path": str(memo.get("official_branch_path") or "").strip(),
        "proposed_branch_path": str(memo.get("proposed_branch_path") or "").strip(),
        "branch_hint": str(memo.get("branch_hint") or "").strip(),
        "proposed_root_entity": str(memo.get("proposed_root_entity") or "").strip(),
        "classification_note": str(memo.get("classification_note") or "").strip(),
        "classified_at": int(memo.get("classified_at", 0) or 0),
        "source_turn_process_ids": source_turn_process_ids,
        "source_phase_snapshot_ids": source_phase_snapshot_ids,
        "queried_field_memo_ids": list(memo.get("queried_field_memo_ids", []) or []),
        "queried_field_memo_ids_json": _safe_json(list(memo.get("queried_field_memo_ids", []) or [])),
        "status": str(memo.get("status") or "active").strip() or "active",
        "supersedes_memo_ids": list(memo.get("supersedes_memo_ids", []) or []),
        "supersedes_memo_ids_json": _safe_json(list(memo.get("supersedes_memo_ids", []) or [])),
        "contradicts_memo_ids": list(memo.get("contradicts_memo_ids", []) or []),
        "contradicts_memo_ids_json": _safe_json(list(memo.get("contradicts_memo_ids", []) or [])),
        "truth_maintenance_note": str(memo.get("truth_maintenance_note") or "").strip(),
        "memo_level": memo_level,
        "parent_memo_ids": parent_memo_ids,
        "parent_memo_ids_json": _safe_json(parent_memo_ids),
        "synthesis_source_memo_ids": synthesis_source_memo_ids,
        "synthesis_source_memo_ids_json": _safe_json(synthesis_source_memo_ids),
        "summary_scope": str(memo.get("summary_scope") or "turn").strip(),
        "embedding": list(memo.get("embedding", []) or []),
        "embedding_model": str(memo.get("embedding_model") or "").strip(),
        "confidence": float(memo.get("confidence", 0.55) or 0.55),
        "created_at": int(memo.get("created_at", _now_ms()) or _now_ms()),
        "dream_id": str(dream_id or "").strip(),
        "process_id": process_id,
    }
    if not props["embedding"]:
        props["embedding"], props["embedding_model"] = _try_embed_text(_memo_embedding_text(props))
    try:
        with get_db_session() as session:
            session.run(
                """
                MERGE (fm:FieldMemo {memo_id: $memo_id})
                SET fm.created_at = coalesce(fm.created_at, $created_at),
                    fm.updated_at = timestamp(),
                    fm.id = $memo_id,
                    fm.name = $title,
                    fm.title = $title,
                    fm.memo_kind = $memo_kind,
                    fm.summary = $summary,
                    fm.known_facts = $known_facts,
                    fm.known_facts_json = $known_facts_json,
                    fm.entities = $entities,
                    fm.entities_json = $entities_json,
                    fm.events = $events,
                    fm.events_json = $events_json,
                    fm.place_refs = $place_refs,
                    fm.place_refs_json = $place_refs_json,
                    fm.causal_links_json = $causal_links_json,
                    fm.open_questions = $open_questions,
                    fm.open_questions_json = $open_questions_json,
                    fm.branch_path = $branch_path,
                    fm.root_entity = $root_entity,
                    fm.branch_status = $branch_status,
                    fm.official_branch_path = $official_branch_path,
                    fm.proposed_branch_path = $proposed_branch_path,
                    fm.branch_hint = $branch_hint,
                    fm.proposed_root_entity = $proposed_root_entity,
                    fm.classification_note = $classification_note,
                    fm.classified_at = toInteger($classified_at),
                    fm.source_turn_process_ids = $source_turn_process_ids,
                    fm.source_phase_snapshot_ids = $source_phase_snapshot_ids,
                    fm.queried_field_memo_ids = $queried_field_memo_ids,
                    fm.queried_field_memo_ids_json = $queried_field_memo_ids_json,
                    fm.status = $status,
                    fm.supersedes_memo_ids = $supersedes_memo_ids,
                    fm.supersedes_memo_ids_json = $supersedes_memo_ids_json,
                    fm.contradicts_memo_ids = $contradicts_memo_ids,
                    fm.contradicts_memo_ids_json = $contradicts_memo_ids_json,
                    fm.truth_maintenance_note = $truth_maintenance_note,
                    fm.memo_level = toInteger($memo_level),
                    fm.parent_memo_ids = $parent_memo_ids,
                    fm.parent_memo_ids_json = $parent_memo_ids_json,
                    fm.synthesis_source_memo_ids = $synthesis_source_memo_ids,
                    fm.synthesis_source_memo_ids_json = $synthesis_source_memo_ids_json,
                    fm.summary_scope = $summary_scope,
                    fm.embedding = $embedding,
                    fm.embedding_model = $embedding_model,
                    fm.confidence = toFloat($confidence),
                    fm.dream_id = $dream_id,
                    fm.process_id = $process_id
                """,
                **props,
            )
            if dream_id:
                session.run(
                    "MATCH (fm:FieldMemo {memo_id: $memo_id}) MATCH (d:Dream {id: $dream_id}) MERGE (fm)-[:DERIVED_FROM_DREAM]->(d)",
                    memo_id=props["memo_id"],
                    dream_id=dream_id,
                )
            if process_id:
                session.run(
                    "MATCH (fm:FieldMemo {memo_id: $memo_id}) MATCH (tp:TurnProcess {id: $process_id}) MERGE (fm)-[:SUMMARIZES_PROCESS]->(tp)",
                    memo_id=props["memo_id"],
                    process_id=process_id,
                )
            for snapshot_id in source_phase_snapshot_ids:
                session.run(
                    "MATCH (fm:FieldMemo {memo_id: $memo_id}) MATCH (ps:PhaseSnapshot {id: $snapshot_id}) MERGE (fm)-[:SUMMARIZES_PHASE]->(ps)",
                    memo_id=props["memo_id"],
                    snapshot_id=snapshot_id,
                )
            for referenced_id in props["queried_field_memo_ids"]:
                session.run(
                    "MATCH (fm:FieldMemo {memo_id: $memo_id}) MATCH (prior:FieldMemo {memo_id: $referenced_id}) MERGE (fm)-[:REFERENCES_MEMO]->(prior)",
                    memo_id=props["memo_id"],
                    referenced_id=referenced_id,
                )
            for contradicted_id in props["contradicts_memo_ids"]:
                session.run(
                    """
                    MATCH (fm:FieldMemo {memo_id: $memo_id})
                    MATCH (prior:FieldMemo {memo_id: $contradicted_id})
                    MERGE (fm)-[:CONTRADICTS_MEMO]->(prior)
                    SET prior.status = CASE
                            WHEN coalesce(prior.status, 'active') = 'rejected' THEN prior.status
                            ELSE 'disputed'
                        END,
                        prior.confidence = toFloat(coalesce(prior.confidence, 0.55)) * 0.75,
                        prior.disputed_at = timestamp()
                    """,
                    memo_id=props["memo_id"],
                    contradicted_id=contradicted_id,
                )
            for superseded_id in props["supersedes_memo_ids"]:
                session.run(
                    """
                    MATCH (fm:FieldMemo {memo_id: $memo_id})
                    MATCH (prior:FieldMemo {memo_id: $superseded_id})
                    MERGE (fm)-[:SUPERSEDES_MEMO]->(prior)
                    SET prior.status = CASE
                            WHEN coalesce(prior.status, 'active') = 'rejected' THEN prior.status
                            ELSE 'superseded'
                        END,
                        prior.confidence = toFloat(coalesce(prior.confidence, 0.55)) * 0.55,
                        prior.superseded_at = timestamp()
                    """,
                    memo_id=props["memo_id"],
                    superseded_id=superseded_id,
                )
            for parent_id in parent_memo_ids:
                session.run(
                    "MATCH (fm:FieldMemo {memo_id: $memo_id}) MATCH (parent:FieldMemo {memo_id: $parent_id}) MERGE (fm)-[:PARENT_MEMO]->(parent)",
                    memo_id=props["memo_id"],
                    parent_id=parent_id,
                )
            for source_memo_id in synthesis_source_memo_ids:
                session.run(
                    """
                    MATCH (fm:FieldMemo {memo_id: $memo_id})
                    MATCH (source:FieldMemo {memo_id: $source_memo_id})
                    MERGE (fm)-[:DERIVED_FROM_MEMO]->(source)
                    MERGE (source)-[:SUMMARIZED_BY]->(fm)
                    """,
                    memo_id=props["memo_id"],
                    source_memo_id=source_memo_id,
                )
            if field_memo_has_official_branch(props):
                if root_label == "CoreEgo":
                    session.run(
                        "MATCH (fm:FieldMemo {memo_id: $memo_id}) MERGE (root:CoreEgo {name: $root_name}) MERGE (fm)-[:TARGETS_ROOT]->(root)",
                        memo_id=props["memo_id"],
                        root_name=root_name,
                    )
                else:
                    session.run(
                        "MATCH (fm:FieldMemo {memo_id: $memo_id}) MERGE (root:Person {name: $root_name}) MERGE (fm)-[:TARGETS_ROOT]->(root)",
                        memo_id=props["memo_id"],
                        root_name=root_name,
                    )
        print(f"{log_prefix} saved: {props['title']} ({props['memo_kind']})")
        return True
    except Exception as exc:
        print(f"{log_prefix} save failed: {exc}")
        return False


def _tokenize_query(query: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", str(query or "").lower())
    raw_tokens = re.findall(r"[0-9a-zA-Z가-힣:-]{2,}", normalized)
    stopwords = {
        "그거", "그때", "아까", "방금", "기억", "기억나", "기억해", "있는지",
        "무엇", "누구", "말해", "내용", "사건", "이제",
        "what", "that", "this", "remember", "recall", "please",
    }
    tokens = []
    suffixes = ["입니다", "이라는", "라는", "에게", "한테", "에서", "으로", "부터", "까지", "은", "는", "이", "가", "을", "를", "에", "와", "과", "도"]
    for token in raw_tokens:
        if token not in stopwords:
            tokens.append(token)
        for suffix in suffixes:
            if token.endswith(suffix) and len(token) > len(suffix) + 1:
                stem = token[: -len(suffix)]
                if stem and stem not in stopwords:
                    tokens.append(stem)
                break
    return _dedupe_keep_order(tokens, limit=12)


def _field_memo_label_exists(session) -> bool:
    try:
        row = session.run(
            "CALL db.labels() YIELD label WITH collect(label) AS labels RETURN 'FieldMemo' IN labels AS exists"
        ).single()
        return bool(row and row.get("exists"))
    except Exception:
        return False




def search_field_memos(query: str, limit: int = 5) -> tuple[str, list[str]]:
    """Hybrid FieldMemo recall: higher-level memos first, then drill down into child memos."""
    query_text = _norm(query)
    try:
        limit = int(limit or 5)
    except Exception:
        limit = 5
    limit = max(1, min(limit, 12))
    tokens = _tokenize_query(query_text)
    allow_recent = False
    query_embedding, query_embedding_model = _try_embed_text(query_text)
    try:
        with get_db_session() as session:
            if not _field_memo_label_exists(session):
                return (
                    "[FieldMemo search result]\nNo FieldMemo entries exist yet. FieldMemo is created only from verified fact packets.",
                    [],
                )
            rows = session.run(
                """
                MATCH (fm:FieldMemo)
                WITH fm,
                     toLower(
                       coalesce(fm.title, '') + ' ' +
                       coalesce(fm.summary, '') + ' ' +
                       coalesce(fm.known_facts_json, '') + ' ' +
                       coalesce(fm.entities_json, '') + ' ' +
                       coalesce(fm.events_json, '') + ' ' +
                       coalesce(fm.open_questions_json, '') + ' ' +
                       coalesce(fm.branch_path, '') + ' ' +
                       coalesce(fm.summary_scope, '')
                     ) AS search_text
                WITH fm,
                     reduce(score = 0.0, token IN $tokens |
                       score + CASE WHEN search_text CONTAINS toLower(token) THEN 1.0 ELSE 0.0 END
                     ) AS lexical_score
                WHERE lexical_score > 0.0 OR $allow_recent = true OR ($has_query_embedding = true AND fm.embedding IS NOT NULL)
                RETURN fm{.*} AS props, lexical_score
                ORDER BY lexical_score DESC, coalesce(fm.updated_at, fm.created_at, 0) DESC
                LIMIT $scan_limit
                """,
                tokens=tokens,
                allow_recent=allow_recent,
                has_query_embedding=bool(query_embedding),
                scan_limit=max(limit * 30, 300),
            ).data()
    except Exception as exc:
        return (f"[FieldMemo search error]\nFieldMemo search failed: {exc}", [])

    scored_rows = []
    for row in rows or []:
        props = row.get("props") if isinstance(row, dict) else {}
        props = props if isinstance(props, dict) else {}
        lexical_score = float(row.get("lexical_score") or 0.0)
        embedding = props.get("embedding")
        semantic_score = 0.0
        if query_embedding and isinstance(embedding, list) and len(embedding) == len(query_embedding):
            semantic_score = _cosine_similarity(query_embedding, embedding)
        status = (_norm(props.get("status")) or "active").lower()
        status_penalty = {
            "active": 0.0,
            "verified": 0.1,
            "pending_classification": -0.25,
            "disputed": -1.5,
            "superseded": -4.0,
            "rejected": -6.0,
        }.get(status, 0.0)
        hybrid_score = lexical_score + (semantic_score * 2.0 if semantic_score >= 0.20 else 0.0) + status_penalty
        if status in {"rejected", "superseded"} and hybrid_score < 2.5:
            continue
        if lexical_score <= 0.0 and semantic_score < 0.25 and not allow_recent:
            continue
        scored_rows.append({
            "props": props,
            "lexical_score": lexical_score,
            "semantic_score": semantic_score,
            "hybrid_score": hybrid_score,
            "status": status,
            "memo_level": _memo_level(props),
        })
    scored_rows.sort(
        key=lambda row: (
            float(row.get("hybrid_score", 0.0) or 0.0),
            int((row.get("props") or {}).get("updated_at", (row.get("props") or {}).get("created_at", 0)) or 0),
        ),
        reverse=True,
    )
    rows = scored_rows[:limit]
    if not rows:
        return (
            f"[FieldMemo search result]\nquery: {query_text}\nNo matching FieldMemo entries were found.",
            [],
        )

    child_ids = []
    for row in rows[:4]:
        props = row.get("props") if isinstance(row, dict) else {}
        if not isinstance(props, dict) or _memo_level(props) <= 1:
            continue
        child_ids.extend(_load_json_list(props.get("synthesis_source_memo_ids_json")) or list(props.get("synthesis_source_memo_ids", []) or []))
        child_ids.extend(_load_json_list(props.get("parent_memo_ids_json")) or list(props.get("parent_memo_ids", []) or []))
    child_ids = _dedupe_keep_order(child_ids, limit=24)
    child_map = {}
    if child_ids:
        try:
            with get_db_session() as session:
                child_rows = session.run(
                    """
                    MATCH (fm:FieldMemo)
                    WHERE fm.memo_id IN $child_ids
                    RETURN fm{.*} AS props
                    LIMIT 24
                    """,
                    child_ids=child_ids,
                ).data()
            child_map = {
                _norm((row.get("props") or {}).get("memo_id")): row.get("props")
                for row in child_rows
                if isinstance(row.get("props"), dict)
            }
        except Exception:
            child_map = {}

    matched_ids = []
    known_facts = []
    unknown_slots = []
    search_mode = "hybrid_lexical_semantic" if query_embedding else "lexical_with_level_drilldown"
    lines = [
        "[FieldMemo search result]",
        f"query: {query_text}",
        f"search_mode: {search_mode}",
        f"embedding_model: {query_embedding_model or '(none)'}",
        "ranking: lexical_score + semantic_score - stale_status_penalty; recency breaks ties",
    ]
    for idx, row in enumerate(rows, start=1):
        props = row.get("props") if isinstance(row, dict) else {}
        props = props if isinstance(props, dict) else {}
        memo_id = _norm(props.get("memo_id"))
        matched_ids.append(memo_id)
        facts = _memo_known_facts(props, limit=5)
        unknowns = _memo_open_questions(props, limit=5)
        known_facts.extend(facts)
        unknown_slots.extend(unknowns)
        source_ids = _load_json_list(props.get("synthesis_source_memo_ids_json")) or list(props.get("synthesis_source_memo_ids", []) or [])
        lines.extend([
            "",
            f"[FieldMemo {idx}]",
            f"memo_id: {memo_id}",
            f"memo_level: {_memo_level(props)}",
            f"summary_scope: {_norm(props.get('summary_scope')) or '(none)'}",
            f"branch_path: {_norm(props.get('branch_path'))}",
            f"branch_status: {_norm(props.get('branch_status')) or '(none)'}",
            f"official_branch_path: {_norm(props.get('official_branch_path')) or '(none)'}",
            f"proposed_branch_path: {_norm(props.get('proposed_branch_path')) or '(none)'}",
            f"root_entity: {_norm(props.get('root_entity'))}",
            f"proposed_root_entity: {_norm(props.get('proposed_root_entity')) or '(none)'}",
            f"memo_kind: {_norm(props.get('memo_kind'))}",
            f"status: {_norm(props.get('status')) or 'active'}",
            f"summary: {_trim(props.get('summary'), 520)}",
            f"known_facts: {' / '.join(facts) if facts else '(none)'}",
            f"unknown_slots: {' / '.join(unknowns) if unknowns else '(none)'}",
            f"synthesis_source_memo_ids: {' / '.join(source_ids[:8]) if source_ids else '(none)'}",
            f"lexical_score: {float(row.get('lexical_score') or 0.0):.2f}",
            f"semantic_score: {float(row.get('semantic_score') or 0.0):.3f}",
            f"relevance_score: {float(row.get('hybrid_score') or 0.0):.3f}",
        ])
        if _memo_level(props) > 1 and source_ids:
            lines.append("[Drilldown children]")
            for child_id in source_ids[:5]:
                child = child_map.get(_norm(child_id))
                if not child:
                    continue
                child_facts = _memo_known_facts(child, limit=2)
                known_facts.extend(child_facts)
                lines.append(
                    f"- {child_id} | level={_memo_level(child)} | "
                    f"status={_norm(child.get('status')) or 'active'} | "
                    f"summary={_trim(child.get('summary'), 180)} | "
                    f"facts={' / '.join(child_facts) if child_facts else '(none)'}"
                )

    packet = FieldMemoRecallPacket(
        query=query_text,
        matched_memo_ids=_dedupe_keep_order(matched_ids, limit=limit),
        known_facts=_dedupe_keep_order(known_facts, limit=12),
        unknown_slots=_dedupe_keep_order(unknown_slots, limit=12),
        relevance_notes=[
            f"search_mode={search_mode}",
            "If a LayeredMemo is present, show the parent memo first and attach child FieldMemo entries as drilldown candidates.",
            "FieldMemo recall returns retrieval candidates only; phase_2b must judge final factual usability.",
        ],
        answer_boundary="Separate verified facts from uncertain or missing slots before answering.",
    )
    lines.extend(["", "[FieldMemoRecallPacket]", _safe_json(packet.model_dump())])
    return "\n".join(lines), packet.matched_memo_ids


def load_recent_field_memos(limit: int = 120) -> list[dict]:
    try:
        limit = int(limit or 120)
    except Exception:
        limit = 120
    limit = max(1, min(limit, 300))
    try:
        with get_db_session() as session:
            if not _field_memo_label_exists(session):
                return []
            rows = session.run(
                """
                MATCH (fm:FieldMemo)
                RETURN fm{.*} AS props
                ORDER BY coalesce(fm.updated_at, fm.created_at, 0) DESC
                LIMIT $limit
                """,
                limit=limit,
            ).data()
    except Exception:
        return []
    return [row.get("props") for row in rows if isinstance(row.get("props"), dict)]


def field_memo_fact_leaf_candidates(field_memos: list[dict], branch_path: str = "") -> list[dict]:
    candidates = []
    target_branch = _norm(branch_path)
    for memo in field_memos or []:
        if not isinstance(memo, dict):
            continue
        if not field_memo_has_official_branch(memo):
            continue
        memo_branch = _norm(memo.get("branch_path"))
        if target_branch and memo_branch and memo_branch != target_branch:
            continue
        facts = _load_json_list(memo.get("known_facts_json")) or list(memo.get("known_facts", []) or [])
        facts = _dedupe_keep_order(facts, limit=6)
        if not facts:
            continue
        memo_id = _norm(memo.get("memo_id"))
        process_ids = list(memo.get("source_turn_process_ids", []) or [])
        source_id = _norm(process_ids[0]) if process_ids else memo_id
        source_kind = "TurnProcess" if process_ids else "FieldMemo"
        source_address = f"{source_kind}:{source_id}" if source_id else f"FieldMemo:{memo_id}"
        topic_slug = _safe_slug(memo_branch.split("/")[-1] if memo_branch else "field_memo")
        excerpt = " / ".join([_norm(memo.get("summary"))] + facts[:3])
        for idx, fact in enumerate(facts, start=1):
            candidates.append({
                "topic_slug": topic_slug,
                "source_address": source_address,
                "source_kind": source_kind,
                "fact_text": fact,
                "source_excerpt": excerpt,
                "support_weight": min(0.88, max(0.52, float(memo.get("confidence", 0.55) or 0.55))),
                "field_memo_id": memo_id,
                "field_memo_fact_index": idx,
            })
    return candidates[:36]


def _memo_known_facts(memo: dict, limit: int = 8) -> list[str]:
    if not isinstance(memo, dict):
        return []
    return _dedupe_keep_order(
        _load_json_list(memo.get("known_facts_json")) or list(memo.get("known_facts", []) or []),
        limit=limit,
    )


def _memo_open_questions(memo: dict, limit: int = 8) -> list[str]:
    if not isinstance(memo, dict):
        return []
    return _dedupe_keep_order(
        _load_json_list(memo.get("open_questions_json")) or list(memo.get("open_questions", []) or []),
        limit=limit,
    )


def _memo_list_field(memo: dict, field_name: str, json_field_name: str = "", limit: int = 12) -> list[str]:
    if not isinstance(memo, dict):
        return []
    values = _load_json_list(memo.get(json_field_name)) if json_field_name else []
    if not values:
        values = list(memo.get(field_name, []) or [])
    return _dedupe_keep_order(values, limit=limit)


def _build_one_layered_memo(branch_path: str, source_memos: list[dict], next_level: int) -> dict | None:
    source_memos = [memo for memo in source_memos if isinstance(memo, dict) and _norm(memo.get("memo_id"))]
    if len(source_memos) < 2:
        return None
    source_ids = _dedupe_keep_order([memo.get("memo_id") for memo in source_memos], limit=24)
    if len(source_ids) < 2:
        return None

    root_entity = _norm(source_memos[0].get("root_entity")) or ("CoreEgo" if branch_path.startswith("CoreEgo/") else "Person")
    facts = []
    entities = []
    events = []
    places = []
    questions = []
    summaries = []
    confidence_values = []
    for memo in source_memos[:24]:
        summaries.append(_trim(memo.get("summary"), 150))
        facts.extend(_memo_known_facts(memo, limit=6))
        entities.extend(_memo_list_field(memo, "entities", "entities_json", limit=8))
        events.extend(_memo_list_field(memo, "events", "events_json", limit=8))
        places.extend(_memo_list_field(memo, "place_refs", "place_refs_json", limit=8))
        questions.extend(_memo_open_questions(memo, limit=6))
        try:
            confidence_values.append(float(memo.get("confidence", 0.55) or 0.55))
        except Exception:
            pass
    facts = _dedupe_keep_order(facts, limit=12)
    entities = _dedupe_keep_order(entities, limit=16)
    events = _dedupe_keep_order(events, limit=16)
    places = _dedupe_keep_order(places, limit=12)
    questions = _dedupe_keep_order(questions, limit=12)
    source_digest = " / ".join(part for part in summaries[:5] if part)
    if facts:
        summary = _trim(f"{branch_path} layered memo: " + " / ".join(facts[:5]), 640)
    else:
        summary = _trim(f"{branch_path} layered memo: {source_digest}", 640)
    memo_id = f"layered_memo::{_safe_slug(branch_path, 72)}::lvl{next_level}::{_memo_hash(*source_ids)}"
    confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.58
    confidence = min(0.93, max(0.45, confidence + 0.04))
    title = f"{branch_path.split('/')[-1] or branch_path} L{next_level} layered memo"
    embedding, embedding_model = _try_embed_text("\n".join([title, summary, " / ".join(facts), branch_path]))
    return LayeredMemoItem(
        memo_id=memo_id,
        title=_trim(title, 90),
        summary=summary,
        known_facts=facts,
        entities=entities,
        events=events,
        place_refs=places,
        causal_links=[],
        open_questions=questions,
        branch_path=branch_path,
        root_entity=root_entity,
        branch_status="active",
        official_branch_path=branch_path,
        proposed_branch_path="",
        branch_hint="",
        proposed_root_entity="",
        source_turn_process_ids=_dedupe_keep_order(
            [pid for memo in source_memos for pid in list(memo.get("source_turn_process_ids", []) or [])],
            limit=20,
        ),
        source_phase_snapshot_ids=_dedupe_keep_order(
            [pid for memo in source_memos for pid in list(memo.get("source_phase_snapshot_ids", []) or [])],
            limit=40,
        ),
        queried_field_memo_ids=[],
        memo_level=next_level,
        parent_memo_ids=source_ids[:12],
        synthesis_source_memo_ids=source_ids,
        summary_scope="branch_synthesis" if next_level == 2 else "meta_synthesis",
        embedding_model=embedding_model,
        embedding=embedding,
        confidence=round(confidence, 3),
    ).model_dump()


def build_layered_memos(field_memos: list[dict], *, max_level: int = 4, max_per_run: int = 16) -> list[dict]:
    grouped: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for memo in field_memos or []:
        if not isinstance(memo, dict):
            continue
        if not field_memo_has_official_branch(memo):
            continue
        branch_path = _norm(memo.get("branch_path"))
        memo_id = _norm(memo.get("memo_id"))
        if not branch_path or not memo_id:
            continue
        grouped[branch_path][_memo_level(memo)].append(memo)

    layered = []
    for branch_path, by_level in grouped.items():
        for level in sorted(by_level.keys()):
            if level >= max_level:
                continue
            source_memos = sorted(
                by_level[level],
                key=lambda memo: int(memo.get("updated_at", memo.get("created_at", 0)) or 0),
                reverse=True,
            )[:24]
            if len(source_memos) < 2:
                continue
            item = _build_one_layered_memo(branch_path, source_memos, next_level=level + 1)
            if item:
                layered.append(item)
            if len(layered) >= max_per_run:
                return layered
    return layered


def persist_layered_memos(session, sd_id: str, layered_memos: list[dict], graph_operations_log: list | None = None):
    graph_operations_log = graph_operations_log if isinstance(graph_operations_log, list) else []
    for memo in layered_memos or []:
        if not isinstance(memo, dict):
            continue
        memo_id = _norm(memo.get("memo_id"))
        branch_path = _norm(memo.get("branch_path"))
        if not memo_id or not branch_path:
            continue
        root_label, root_name = _root_parts(memo.get("root_entity"))
        props = {
            "memo_id": memo_id,
            "memo_kind": _norm(memo.get("memo_kind")) or "layered_synthesis",
            "title": _norm(memo.get("title")) or branch_path,
            "summary": _norm(memo.get("summary")),
            "known_facts": list(memo.get("known_facts", []) or []),
            "known_facts_json": _safe_json(list(memo.get("known_facts", []) or [])),
            "entities": list(memo.get("entities", []) or []),
            "entities_json": _safe_json(list(memo.get("entities", []) or [])),
            "events": list(memo.get("events", []) or []),
            "events_json": _safe_json(list(memo.get("events", []) or [])),
            "place_refs": list(memo.get("place_refs", []) or []),
            "place_refs_json": _safe_json(list(memo.get("place_refs", []) or [])),
            "open_questions": list(memo.get("open_questions", []) or []),
            "open_questions_json": _safe_json(list(memo.get("open_questions", []) or [])),
            "branch_path": branch_path,
            "root_entity": _norm(memo.get("root_entity")),
            "branch_status": _norm(memo.get("branch_status")) or "active",
            "official_branch_path": _norm(memo.get("official_branch_path")) or branch_path,
            "proposed_branch_path": _norm(memo.get("proposed_branch_path")),
            "branch_hint": _norm(memo.get("branch_hint")),
            "proposed_root_entity": _norm(memo.get("proposed_root_entity")),
            "classification_note": _norm(memo.get("classification_note")),
            "classified_at": int(memo.get("classified_at", 0) or 0),
            "memo_level": _memo_level(memo),
            "summary_scope": _norm(memo.get("summary_scope")) or "branch_synthesis",
            "parent_memo_ids": list(memo.get("parent_memo_ids", []) or []),
            "parent_memo_ids_json": _safe_json(list(memo.get("parent_memo_ids", []) or [])),
            "synthesis_source_memo_ids": list(memo.get("synthesis_source_memo_ids", []) or []),
            "synthesis_source_memo_ids_json": _safe_json(list(memo.get("synthesis_source_memo_ids", []) or [])),
            "source_turn_process_ids": list(memo.get("source_turn_process_ids", []) or []),
            "source_phase_snapshot_ids": list(memo.get("source_phase_snapshot_ids", []) or []),
            "confidence": float(memo.get("confidence", 0.6) or 0.6),
            "created_at": int(memo.get("created_at", _now_ms()) or _now_ms()),
            "embedding": list(memo.get("embedding", []) or []),
            "embedding_model": _norm(memo.get("embedding_model")),
        }
        if not props["embedding"]:
            props["embedding"], props["embedding_model"] = _try_embed_text(_memo_embedding_text(props))
        session.run(
            """
            MERGE (lm:FieldMemo:LayeredMemo:SynthesisMemo {memo_id: $memo_id})
            SET lm.created_at = coalesce(lm.created_at, $created_at),
                lm.updated_at = timestamp(),
                lm.id = $memo_id,
                lm.name = $title,
                lm.title = $title,
                lm.memo_kind = $memo_kind,
                lm.summary = $summary,
                lm.known_facts = $known_facts,
                lm.known_facts_json = $known_facts_json,
                lm.entities = $entities,
                lm.entities_json = $entities_json,
                lm.events = $events,
                lm.events_json = $events_json,
                lm.place_refs = $place_refs,
                lm.place_refs_json = $place_refs_json,
                lm.open_questions = $open_questions,
                lm.open_questions_json = $open_questions_json,
                lm.branch_path = $branch_path,
                lm.root_entity = $root_entity,
                lm.branch_status = $branch_status,
                lm.official_branch_path = $official_branch_path,
                lm.proposed_branch_path = $proposed_branch_path,
                lm.branch_hint = $branch_hint,
                lm.proposed_root_entity = $proposed_root_entity,
                lm.classification_note = $classification_note,
                lm.classified_at = toInteger($classified_at),
                lm.memo_level = toInteger($memo_level),
                lm.summary_scope = $summary_scope,
                lm.parent_memo_ids = $parent_memo_ids,
                lm.parent_memo_ids_json = $parent_memo_ids_json,
                lm.synthesis_source_memo_ids = $synthesis_source_memo_ids,
                lm.synthesis_source_memo_ids_json = $synthesis_source_memo_ids_json,
                lm.source_turn_process_ids = $source_turn_process_ids,
                lm.source_phase_snapshot_ids = $source_phase_snapshot_ids,
                lm.confidence = toFloat($confidence),
                lm.embedding = $embedding,
                lm.embedding_model = $embedding_model
            MERGE (gb:TimeBranch {governor_key: 'night_government_v1', branch_path: $branch_path})
            MERGE (lm)-[:FOLLOWS_BRANCH]->(gb)
            """,
            **props,
        )
        for source_memo_id in props["synthesis_source_memo_ids"]:
            session.run(
                """
                MATCH (lm:FieldMemo {memo_id: $memo_id})
                MATCH (src:FieldMemo {memo_id: $source_memo_id})
                MERGE (lm)-[:DERIVED_FROM_MEMO]->(src)
                MERGE (lm)-[:REFERENCES_MEMO]->(src)
                MERGE (src)-[:SUMMARIZED_BY]->(lm)
                """,
                memo_id=memo_id,
                source_memo_id=source_memo_id,
            )
        if sd_id:
            session.run(
                """
                MATCH (lm:FieldMemo {memo_id: $memo_id})
                MATCH (sd:SecondDream {id: $sd_id})
                MERGE (lm)-[:FORGED_IN]->(sd)
                MERGE (lm)-[:REPORTS_TO]->(sd)
                """,
                memo_id=memo_id,
                sd_id=sd_id,
            )
        if root_label == "CoreEgo":
            session.run(
                "MATCH (lm:FieldMemo {memo_id: $memo_id}) MERGE (root:CoreEgo {name: $root_name}) MERGE (lm)-[:TARGETS_ROOT]->(root)",
                memo_id=memo_id,
                root_name=root_name,
            )
        else:
            session.run(
                "MATCH (lm:FieldMemo {memo_id: $memo_id}) MERGE (root:Person {name: $root_name}) MERGE (lm)-[:TARGETS_ROOT]->(root)",
                memo_id=memo_id,
                root_name=root_name,
            )
        session.run(
            """
            MATCH (lm:FieldMemo {memo_id: $memo_id})
            MATCH (bo:BranchOffice {branch_path: $branch_path})
            MERGE (bo)-[:CURATES_MEMO]->(lm)
            """,
            memo_id=memo_id,
            branch_path=branch_path,
        )
        graph_operations_log.append({"op": "LAYERED_MEMO", "key": memo_id})
    return graph_operations_log


def build_branch_offices(
    field_memos: list[dict],
    *,
    required_branches: list[str] | None = None,
    tonight_scope: list[str] | None = None,
    fact_leaves: list[dict] | None = None,
    branch_digests: list[dict] | None = None,
    route_policies: list[dict] | None = None,
    tool_doctrines: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for memo in field_memos or []:
        if not isinstance(memo, dict):
            continue
        if not field_memo_has_official_branch(memo):
            continue
        branch_path = _norm(memo.get("branch_path"))
        if branch_path:
            grouped[branch_path].append(memo)

    required_set = set(_dedupe_keep_order(required_branches or []))
    scope_set = set()
    for item in tonight_scope or []:
        path = _norm(item.get("branch_path") or item.get("scope_key") or item.get("target_branch")) if isinstance(item, dict) else _norm(item)
        if path:
            scope_set.add(path)

    fact_count_by_branch = defaultdict(int)
    for fact in fact_leaves or []:
        if isinstance(fact, dict):
            fact_count_by_branch[_norm(fact.get("branch_path"))] += 1
    digest_count_by_branch = defaultdict(int)
    for digest in branch_digests or []:
        if isinstance(digest, dict):
            digest_count_by_branch[_norm(digest.get("branch_path"))] += 1
    policy_count_by_branch = defaultdict(int)
    for item in list(route_policies or []) + list(tool_doctrines or []):
        if isinstance(item, dict):
            policy_count_by_branch[_norm(item.get("branch_path") or item.get("branch_scope"))] += 1

    offices = []
    reports = []
    for branch_path, memos in grouped.items():
        memo_ids = _dedupe_keep_order([memo.get("memo_id") for memo in memos], limit=40)
        failure_count = len([memo for memo in memos if _norm(memo.get("memo_kind")) in {"field_failure", "interaction_repair"}])
        should_create = (
            len(memos) >= 2
            or failure_count > 0
            or branch_path in required_set
            or branch_path in scope_set
            or fact_count_by_branch[branch_path] == 0
            or digest_count_by_branch[branch_path] == 0
        )
        if not should_create:
            continue
        root_entity = _norm(memos[0].get("root_entity")) or ("CoreEgo:songryeon" if branch_path.startswith("CoreEgo/") else "Person:stable")
        layered_memo_ids = _dedupe_keep_order(
            [memo.get("memo_id") for memo in memos if _memo_level(memo) > 1],
            limit=24,
        )
        active_questions = []
        summaries = []
        for memo in memos[:8]:
            summaries.append(_trim(memo.get("summary"), 120))
            active_questions.extend(_load_json_list(memo.get("open_questions_json")) or list(memo.get("open_questions", []) or []))
        fact_health = "healthy" if fact_count_by_branch[branch_path] > 0 else "needs_fact_audit"
        policy_health = "covered" if policy_count_by_branch[branch_path] > 0 else "needs_policy"
        pressure = min(1.0, 0.2 + 0.12 * len(memos) + 0.16 * failure_count + (0.10 if branch_path in required_set else 0.0))
        office_key = f"branch_office::{_safe_slug(branch_path, 96)}"
        local_summary = _trim(f"{branch_path} branch currently holds {len(memos)} FieldMemo items. " + " / ".join(summaries[:3]), 520)
        blocked = []
        if fact_health != "healthy":
            blocked.append("approved_fact_leaf_missing")
        if not memo_ids:
            blocked.append("field_memo_missing")
        wiki_candidates = []
        if len(memos) >= 2:
            wiki_candidates.append(f"{branch_path}::field_memo_cluster")
        if fact_health != "healthy":
            wiki_candidates.append(f"{branch_path}::fact_leaf_audit_needed")
        policy_candidates = []
        if failure_count > 0 or policy_health != "covered":
            policy_candidates.append(f"{branch_path}::field_response_policy_candidate")
        report_summary = _trim(
            f"Local branch report: {branch_path} has {len(memos)} memos and {failure_count} failure/correction markers. "
            f"fact_health={fact_health}, policy_health={policy_health}.",
            520,
        )
        offices.append(BranchOfficeItem(
            office_key=office_key,
            branch_path=branch_path,
            root_entity=root_entity,
            title=f"{branch_path.split('/')[-1]} local branch office",
            local_summary=local_summary,
            active_questions=_dedupe_keep_order(active_questions, limit=12),
            memo_pressure=round(pressure, 3),
            fact_health=fact_health,
            policy_health=policy_health,
            last_report=report_summary,
            status="blocked" if blocked else "active",
            memo_ids=memo_ids,
            layered_memo_ids=layered_memo_ids,
        ).model_dump())
        reports.append(LocalReportItem(
            office_key=office_key,
            branch_path=branch_path,
            report_summary=report_summary,
            wiki_candidates=_dedupe_keep_order(wiki_candidates, limit=8),
            policy_candidates=_dedupe_keep_order(policy_candidates, limit=8),
            blocked_reasons=_dedupe_keep_order(blocked, limit=8),
            governor_feedback=_dedupe_keep_order([
                f"{branch_path}: FieldMemo local office reports {fact_health}/{policy_health} status.",
                *active_questions[:3],
            ], limit=8),
        ).model_dump())
    return offices[:24], reports[:24]


def apply_local_reports_to_night_government(night_government: dict, local_reports: list[dict]) -> dict:
    governor = dict(night_government or {})
    if not local_reports:
        return governor
    required = list(governor.get("required_branches", []) or [])
    open_unknowns = list(governor.get("open_unknowns", []) or [])
    branch_health = list(governor.get("branch_health", []) or [])
    last_growth_actions = list(governor.get("last_growth_actions", []) or [])
    for report in local_reports:
        if not isinstance(report, dict):
            continue
        branch_path = _norm(report.get("branch_path"))
        if not branch_path:
            continue
        if report.get("blocked_reasons"):
            required.append(branch_path)
        open_unknowns.extend(report.get("governor_feedback", []) or [])
        last_growth_actions.append(f"branch_office_report::{branch_path}")
        health = "local_blocked" if report.get("blocked_reasons") else "local_active"
        branch_health.append(f"{branch_path}::{health}")
    governor["required_branches"] = _dedupe_keep_order(required, limit=80)
    governor["open_unknowns"] = _dedupe_keep_order(open_unknowns, limit=80)
    governor["branch_health"] = _dedupe_keep_order(branch_health, limit=80)
    governor["last_growth_actions"] = _dedupe_keep_order(last_growth_actions, limit=80)
    return governor


def persist_branch_offices(session, sd_id: str, offices: list[dict], reports: list[dict], graph_operations_log: list | None = None):
    graph_operations_log = graph_operations_log if isinstance(graph_operations_log, list) else []
    reports_by_office = {
        _norm(report.get("office_key")): report
        for report in reports or []
        if isinstance(report, dict) and _norm(report.get("office_key"))
    }
    for office in offices or []:
        if not isinstance(office, dict):
            continue
        office_key = _norm(office.get("office_key"))
        branch_path = _norm(office.get("branch_path"))
        if not office_key or not branch_path:
            continue
        report = reports_by_office.get(office_key, {})
        root_label, root_name = _root_parts(office.get("root_entity"))
        session.run(
            """
            MERGE (bo:BranchOffice {office_key: $office_key})
            SET bo.created_at = coalesce(bo.created_at, timestamp()),
                bo.updated_at = timestamp(),
                bo.name = $title,
                bo.title = $title,
                bo.branch_path = $branch_path,
                bo.root_entity = $root_entity,
                bo.local_summary = $local_summary,
                bo.active_questions = $active_questions,
                bo.memo_pressure = toFloat($memo_pressure),
                bo.fact_health = $fact_health,
                bo.policy_health = $policy_health,
                bo.last_report = $last_report,
                bo.status = $status,
                bo.memo_ids = $memo_ids,
                bo.layered_memo_ids = $layered_memo_ids
            MERGE (rg:NightGovernmentState {governor_key: 'night_government_v1'})
            MERGE (bo)-[:REPORTS_TO]->(rg)
            MERGE (gb:TimeBranch {governor_key: 'night_government_v1', branch_path: $branch_path})
            SET gb.name = coalesce(gb.name, $title),
                gb.root_entity = coalesce(gb.root_entity, $root_entity),
                gb.updated_at = timestamp()
            MERGE (bo)-[:GOVERNS_BRANCH]->(gb)
            """,
            office_key=office_key,
            title=_norm(office.get("title")) or branch_path,
            branch_path=branch_path,
            root_entity=_norm(office.get("root_entity")),
            local_summary=_norm(office.get("local_summary")),
            active_questions=list(office.get("active_questions", []) or []),
            memo_pressure=float(office.get("memo_pressure", 0.0) or 0.0),
            fact_health=_norm(office.get("fact_health")) or "unknown",
            policy_health=_norm(office.get("policy_health")) or "unknown",
            last_report=_norm(office.get("last_report")),
            status=_norm(office.get("status")) or "active",
            memo_ids=list(office.get("memo_ids", []) or []),
            layered_memo_ids=list(office.get("layered_memo_ids", []) or []),
        )
        if root_label == "CoreEgo":
            session.run(
                "MATCH (bo:BranchOffice {office_key: $office_key}) MERGE (root:CoreEgo {name: $root_name}) MERGE (bo)-[:TARGETS_ROOT]->(root)",
                office_key=office_key,
                root_name=root_name,
            )
        else:
            session.run(
                "MATCH (bo:BranchOffice {office_key: $office_key}) MERGE (root:Person {name: $root_name}) MERGE (bo)-[:TARGETS_ROOT]->(root)",
                office_key=office_key,
                root_name=root_name,
            )
        for memo_id in office.get("memo_ids", []) or []:
            session.run(
                "MATCH (bo:BranchOffice {office_key: $office_key}) MATCH (fm:FieldMemo {memo_id: $memo_id}) MERGE (bo)-[:CURATES_MEMO]->(fm)",
                office_key=office_key,
                memo_id=memo_id,
            )
        if report:
            report_key = f"local_report::{office_key}::{_safe_slug(sd_id or str(_now_ms()), 40)}"
            session.run(
                """
                MATCH (bo:BranchOffice {office_key: $office_key})
                MATCH (sd:SecondDream {id: $sd_id})
                MERGE (lr:LocalReport {report_key: $report_key})
                SET lr.created_at = coalesce(lr.created_at, timestamp()),
                    lr.updated_at = timestamp(),
                    lr.name = $title,
                    lr.office_key = $office_key,
                    lr.branch_path = $branch_path,
                    lr.report_summary = $report_summary,
                    lr.wiki_candidates = $wiki_candidates,
                    lr.policy_candidates = $policy_candidates,
                    lr.blocked_reasons = $blocked_reasons,
                    lr.governor_feedback = $governor_feedback
                MERGE (bo)-[:HAS_LOCAL_REPORT]->(lr)
                MERGE (lr)-[:REPORTS_TO]->(sd)
                """,
                office_key=office_key,
                sd_id=sd_id,
                report_key=report_key,
                title=f"{branch_path} local branch report",
                branch_path=branch_path,
                report_summary=_norm(report.get("report_summary")),
                wiki_candidates=list(report.get("wiki_candidates", []) or []),
                policy_candidates=list(report.get("policy_candidates", []) or []),
                blocked_reasons=list(report.get("blocked_reasons", []) or []),
                governor_feedback=list(report.get("governor_feedback", []) or []),
            )
        graph_operations_log.append({"op": "BRANCH_OFFICE", "key": office_key})
