import copy
import hashlib
import json
from typing import Any, Dict, List


LEDGER_SCHEMA = "EvidenceLedger.v1"
MAX_LEDGER_EVENTS = 80


def _stable_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        return str(value)


def _compact(value: Any, limit: int = 1200) -> str:
    text = _stable_json(value) if isinstance(value, (dict, list)) else str(value or "")
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 14].rstrip() + "...(truncated)"


def normalize_evidence_ledger(ledger: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(ledger, dict):
        ledger = {}
    events = ledger.get("events", [])
    if not isinstance(events, list):
        events = []

    normalized_events: List[Dict[str, Any]] = []
    seen = set()
    for raw_event in events:
        if not isinstance(raw_event, dict):
            continue
        event_id = str(raw_event.get("event_id") or "").strip()
        if not event_id or event_id in seen:
            continue
        seen.add(event_id)
        event = {
            "event_id": event_id,
            "source_kind": str(raw_event.get("source_kind") or "unknown").strip() or "unknown",
            "source_ref": str(raw_event.get("source_ref") or "").strip(),
            "producer_node": str(raw_event.get("producer_node") or "").strip(),
            "timestamp": str(raw_event.get("timestamp") or "").strip(),
            "content": raw_event.get("content"),
            "content_excerpt": _compact(raw_event.get("content"), 700),
            "confidence": raw_event.get("confidence", 1.0),
            "provenance": raw_event.get("provenance", {}) if isinstance(raw_event.get("provenance", {}), dict) else {},
        }
        normalized_events.append(event)

    return {
        "schema": str(ledger.get("schema") or LEDGER_SCHEMA),
        "policy": str(ledger.get("policy") or (
            "This ledger records observed runtime activities and source packets. "
            "It is not a semantic classifier. LLM nodes may reason over these events, "
            "but must not claim a DB/tool/source was used unless a matching event exists."
        )),
        "events": normalized_events[-MAX_LEDGER_EVENTS:],
    }


def _event_id(
    *,
    source_kind: str,
    producer_node: str,
    source_ref: str,
    content: Any,
    timestamp: str = "",
) -> str:
    digest = hashlib.sha1(
        _stable_json(
            {
                "source_kind": source_kind,
                "producer_node": producer_node,
                "source_ref": source_ref,
                "content": content,
                "timestamp": timestamp,
            }
        ).encode("utf-8", errors="ignore")
    ).hexdigest()[:16]
    return f"ev_{digest}"


def append_evidence_event(
    ledger: Dict[str, Any] | None,
    *,
    source_kind: str,
    producer_node: str,
    content: Any,
    source_ref: str = "",
    timestamp: str = "",
    confidence: float = 1.0,
    provenance: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    normalized = normalize_evidence_ledger(copy.deepcopy(ledger))
    normalized_source_kind = str(source_kind or "unknown").strip() or "unknown"
    normalized_producer = str(producer_node or "").strip()
    normalized_source_ref = str(source_ref or "").strip()
    event = {
        "event_id": _event_id(
            source_kind=normalized_source_kind,
            producer_node=normalized_producer,
            source_ref=normalized_source_ref,
            content=content,
            timestamp=timestamp,
        ),
        "source_kind": normalized_source_kind,
        "source_ref": normalized_source_ref,
        "producer_node": normalized_producer,
        "timestamp": str(timestamp or "").strip(),
        "content": copy.deepcopy(content),
        "content_excerpt": _compact(content, 700),
        "confidence": confidence,
        "provenance": copy.deepcopy(provenance or {}),
    }

    if not any(existing.get("event_id") == event["event_id"] for existing in normalized["events"]):
        normalized["events"].append(event)
    normalized["events"] = normalized["events"][-MAX_LEDGER_EVENTS:]
    return normalized


def build_runtime_profile_packet(
    *,
    user_state: str = "",
    user_char: str = "",
    songryeon_thoughts: str = "",
    biolink_status: str = "",
) -> Dict[str, Any]:
    return {
        "schema": "RuntimeProfile.v1",
        "user_state": str(user_state or "").strip(),
        "user_char": str(user_char or "").strip(),
        "songryeon_thoughts": str(songryeon_thoughts or "").strip(),
        "biolink_status": str(biolink_status or "").strip(),
        "source_policy": (
            "This runtime profile is always-available context, not a DB recall result. "
            "Use it when relevant, but do not pretend it came from a search."
        ),
    }


def build_initial_evidence_ledger(
    *,
    user_input: str,
    current_time: str = "",
    recent_context: str = "",
    user_state: str = "",
    user_char: str = "",
    songryeon_thoughts: str = "",
    biolink_status: str = "",
    working_memory: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    ledger = normalize_evidence_ledger({})
    ledger = append_evidence_event(
        ledger,
        source_kind="user_turn",
        producer_node="main.process_turn",
        source_ref="current_user_input",
        timestamp=current_time,
        content={"text": str(user_input or "")},
        confidence=1.0,
    )
    ledger = append_evidence_event(
        ledger,
        source_kind="runtime_profile",
        producer_node="main.process_turn",
        source_ref="runtime_profile",
        timestamp=current_time,
        content=build_runtime_profile_packet(
            user_state=user_state,
            user_char=user_char,
            songryeon_thoughts=songryeon_thoughts,
            biolink_status=biolink_status,
        ),
        confidence=1.0,
    )
    if str(recent_context or "").strip():
        ledger = append_evidence_event(
            ledger,
            source_kind="recent_dialogue",
            producer_node="main.process_turn",
            source_ref="memory_buffer.tactical_context",
            timestamp=current_time,
            content={"excerpt": _compact(recent_context, 2200)},
            confidence=0.85,
        )
    if isinstance(working_memory, dict) and working_memory:
        ledger = append_evidence_event(
            ledger,
            source_kind="working_memory_snapshot",
            producer_node="main.process_turn",
            source_ref="memory_buffer.working_memory",
            timestamp=current_time,
            content=working_memory,
            confidence=0.85,
        )
    return ledger


def evidence_ledger_for_contract(ledger: Dict[str, Any] | None, max_events: int = 16) -> Dict[str, Any]:
    normalized = normalize_evidence_ledger(ledger)
    events = normalized.get("events", [])[-max_events:]
    return {
        "schema": normalized.get("schema", LEDGER_SCHEMA),
        "policy": normalized.get("policy", ""),
        "events": [
            {
                "event_id": event.get("event_id", ""),
                "source_kind": event.get("source_kind", ""),
                "source_ref": event.get("source_ref", ""),
                "producer_node": event.get("producer_node", ""),
                "timestamp": event.get("timestamp", ""),
                "content_excerpt": event.get("content_excerpt", ""),
                "confidence": event.get("confidence", 1.0),
            }
            for event in events
        ],
    }


def evidence_ledger_for_prompt(ledger: Dict[str, Any] | None, max_events: int = 16) -> str:
    return json.dumps(evidence_ledger_for_contract(ledger, max_events=max_events), ensure_ascii=False, indent=2)
