"""Structured-output guards for graph-boundary LLM packets.

The helpers in this module are intentionally mechanical. They validate schema
shape, provenance refs, tool-call names, and typed failure packets; they do not
classify user intent or rewrite node meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import re

from langchain_core.messages import HumanMessage
from pydantic import BaseModel


FAILURE_REASON_TYPES = {
    "parse_error",
    "validation_error",
    "model_refusal",
    "max_tokens",
    "unknown",
}

OPERATION_CONTRACT_SEARCH_KINDS = {
    "search_new_source",
    "read_same_source_deeper",
    "review_personal_history",
}

OPERATION_CONTRACT_SEARCH_LANES = {
    "memory",
    "diary",
    "field_memo",
    "artifact",
    "gemini_chat",
    "songryeon_chat",
    "mixed_private_sources",
}

_INTERNAL_OPERATION_SEED_SENTINELS = {
    "stored or external evidence has not been read yet",
    "a planner must choose the next action",
    "direct evidence required by the start-gate contract",
    "downstream handler must preserve the answer boundary",
    "no explicit current-turn facts were extracted",
}


def structured_failure_packet(
    *,
    node: str,
    reason_type: str = "unknown",
    summary: str = "",
) -> dict[str, Any]:
    reason = str(reason_type or "unknown").strip()
    if reason not in FAILURE_REASON_TYPES:
        reason = "unknown"
    return {
        "schema": "StructuredFailure.v1",
        "node": str(node or "").strip() or "unknown_node",
        "reason_type": reason,
        "summary": str(summary or "").strip()[:700],
    }


def _normalized_seed_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def is_internal_operation_contract_seed(value: Any) -> bool:
    """Return whether a candidate is an internal state/sentinel sentence.

    This is deliberately not a user-intent classifier. It only strips known
    workflow status strings that should never become executable search targets.
    """
    normalized = _normalized_seed_text(value)
    if not normalized:
        return True
    if normalized in _INTERNAL_OPERATION_SEED_SENTINELS:
        return True
    internal_fragments = (
        "evidence has not been read",
        "planner must choose",
        "downstream handler",
        "start-gate contract",
        "safe fallback route",
    )
    return any(fragment in normalized for fragment in internal_fragments)


def clean_operation_contract_seed_candidates(values: Any, *, limit: int = 5) -> list[str]:
    if not isinstance(values, list):
        values = [values] if str(values or "").strip() else []
    result: list[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text or is_internal_operation_contract_seed(text):
            continue
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _operation_contract_search_seeds(contract: dict[str, Any], *, include_subject: bool = True) -> list[str]:
    values: list[Any] = []
    for key in ("retrieval_key_candidates", "source_title_candidates", "query_seed_candidates"):
        raw = contract.get(key, [])
        if isinstance(raw, list):
            values.extend(raw)
        elif str(raw or "").strip():
            values.append(raw)
    if include_subject:
        values.append(contract.get("search_subject", ""))
    return clean_operation_contract_seed_candidates(values)


def _operation_contract_has_exact_date(contract: dict[str, Any]) -> bool:
    parts: list[str] = []
    for key in (
        "target_scope",
        "source_lane",
        "search_subject",
        "missing_slot",
        "evidence_boundary",
        "query_variant",
    ):
        parts.append(str(contract.get(key) or ""))
    parts.extend(_operation_contract_search_seeds(contract))
    blob = "\n".join(parts)
    return bool(
        re.search(r"\b\d{4}-\d{2}-\d{2}\b", blob)
        or re.search(r"\b\d{4}\s+\d{1,2}\s+\d{1,2}\b", blob)
        or re.search(r"\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일", blob)
    )


def validate_operation_contract_payload(operation_contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate operation_contract execution payload quality.

    The validator checks structural executability only: operation/source lane,
    non-empty executable search subject or seeds, and known internal sentinel
    leakage. It does not infer whether the user *intended* a search.
    """
    if not isinstance(operation_contract, dict):
        return {}, structured_failure_packet(
            node="operation_contract",
            reason_type="validation_error",
            summary="operation_contract was not a dict",
        )

    contract = dict(operation_contract)
    operation_kind = str(contract.get("operation_kind") or "").strip()
    source_lane = str(contract.get("source_lane") or "").strip()
    search_subject = str(contract.get("search_subject") or "").strip()
    cleaned_query_seeds = clean_operation_contract_seed_candidates(contract.get("query_seed_candidates", []))
    cleaned_retrieval_keys = clean_operation_contract_seed_candidates(contract.get("retrieval_key_candidates", []))
    cleaned_source_titles = clean_operation_contract_seed_candidates(contract.get("source_title_candidates", []))
    if is_internal_operation_contract_seed(search_subject):
        search_subject = ""
    contract["search_subject"] = search_subject
    contract["query_seed_candidates"] = cleaned_query_seeds
    contract["retrieval_key_candidates"] = cleaned_retrieval_keys
    contract["source_title_candidates"] = cleaned_source_titles

    if operation_kind not in OPERATION_CONTRACT_SEARCH_KINDS:
        return contract, {}
    if source_lane == "capability_boundary":
        return contract, structured_failure_packet(
            node="operation_contract",
            reason_type="validation_error",
            summary="operation_contract source_lane=capability_boundary cannot execute a search",
        )
    if source_lane and source_lane not in OPERATION_CONTRACT_SEARCH_LANES:
        return contract, structured_failure_packet(
            node="operation_contract",
            reason_type="validation_error",
            summary=f"operation_contract source_lane is not executable for search: {source_lane}",
        )

    diary_exact_date = source_lane == "diary" and _operation_contract_has_exact_date(contract)
    executable_seeds = _operation_contract_search_seeds(contract)
    if not executable_seeds and not diary_exact_date:
        return contract, structured_failure_packet(
            node="operation_contract",
            reason_type="validation_error",
            summary="operation_contract_payload_invalid: empty search_subject and no executable retrieval/query seed candidates",
        )
    return contract, {}


@dataclass
class StructuredInvokeResult:
    ok: bool
    value: dict[str, Any]
    failure: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "value": self.value, "failure": self.failure}


def _dump_structured(value: Any, schema: Any | None = None) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=True)
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(by_alias=True)
        except TypeError:
            return value.model_dump()
    if schema is not None and isinstance(value, schema):
        return value.model_dump(by_alias=True)
    return {}


def _validate_with_schema(value: Any, schema: Any) -> dict[str, Any]:
    if isinstance(value, schema):
        return value.model_dump(by_alias=True)
    if isinstance(value, dict):
        schema_name = str(getattr(schema, "__name__", "") or "")
        snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", schema_name).lower()
        wrapper_keys = {schema_name, snake_name}
        if len(value) == 1:
            only_key = next(iter(value.keys()))
            inner = value.get(only_key)
            if only_key in wrapper_keys and isinstance(inner, dict):
                value = inner
        return schema(**value).model_dump(by_alias=True)
    dumped = _dump_structured(value, schema)
    if dumped:
        return schema(**dumped).model_dump(by_alias=True)
    raise TypeError(f"Structured output was {type(value).__name__}, not {getattr(schema, '__name__', schema)!r}")


def invoke_structured_with_repair(
    *,
    llm: Any,
    schema: Any,
    messages: Any,
    node_name: str,
    repair_prompt: str,
    max_repairs: int = 1,
) -> StructuredInvokeResult:
    """Invoke ``llm.with_structured_output`` with bounded repair retries."""
    attempts = max(0, int(max_repairs or 0)) + 1
    current_messages = list(messages) if isinstance(messages, list) else [messages]
    last_error = ""
    for attempt in range(attempts):
        try:
            structured_llm = llm.with_structured_output(schema)
            result = structured_llm.invoke(current_messages)
            value = _validate_with_schema(result, schema)
            return StructuredInvokeResult(ok=True, value=value, failure={})
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt >= attempts - 1:
                break
            current_messages = [
                *current_messages,
                HumanMessage(
                    content=(
                        f"{repair_prompt}\n\n"
                        f"Previous structured-output error:\n{last_error[:700]}"
                    )
                ),
            ]
    return StructuredInvokeResult(
        ok=False,
        value={},
        failure=structured_failure_packet(
            node=node_name,
            reason_type="validation_error" if "validation" in last_error.lower() else "parse_error",
            summary=last_error,
        ),
    )


def _clean_ref_list(values: Any, allowed_fact_ids: Iterable[str] | None) -> list[str]:
    allowed = {str(item or "").strip() for item in (allowed_fact_ids or []) if str(item or "").strip()}
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen = set()
    for value in values:
        ref = str(value or "").strip()
        if not ref or ref in seen:
            continue
        if allowed and ref not in allowed:
            continue
        seen.add(ref)
        result.append(ref)
    return result[:12]


def validate_thought_critique(critique: dict[str, Any], allowed_fact_ids: Iterable[str] | None) -> dict[str, Any]:
    packet = dict(critique if isinstance(critique, dict) else {})
    packet["evidence_refs"] = _clean_ref_list(packet.get("evidence_refs", []), allowed_fact_ids)
    for group in ("hallucination_risks", "logic_gaps", "memory_omissions", "persona_errors"):
        items = packet.get(group, [])
        if not isinstance(items, list):
            packet[group] = []
            continue
        cleaned_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            next_item = dict(item)
            next_item["evidence_refs"] = _clean_ref_list(next_item.get("evidence_refs", []), allowed_fact_ids)
            cleaned_items.append(next_item)
        packet[group] = cleaned_items
    return packet


def validate_thinking_handoff(packet: dict[str, Any], raw_user_input: str = "") -> dict[str, Any]:
    handoff = dict(packet if isinstance(packet, dict) else {})
    defaults = {
        "schema": "ThinkingHandoff.v1",
        "producer": "-1s",
        "recipient": "-1a",
        "goal_state": "current turn intent requires downstream handling",
        "evidence_state": "no evidence state was provided",
        "what_we_know": [],
        "what_is_missing": ["downstream handler must preserve the answer boundary"],
        "next_node": "-1a",
        "next_node_reason": "safe fallback route after handoff validation",
        "constraints_for_next_node": ["do not invent facts"],
    }
    for key, value in defaults.items():
        if key not in handoff or handoff.get(key) in ("", None):
            handoff[key] = value
    for list_key in ("what_we_know", "what_is_missing", "constraints_for_next_node"):
        if not isinstance(handoff.get(list_key), list):
            handoff[list_key] = [str(handoff.get(list_key) or "").strip()] if str(handoff.get(list_key) or "").strip() else defaults[list_key]
    recipient = str(handoff.get("recipient") or "").strip()
    next_node = str(handoff.get("next_node") or "").strip()
    if recipient != next_node:
        mapping = {"-1a_thinker": "-1a", "119": "phase_119"}
        if mapping.get(next_node, next_node) != mapping.get(recipient, recipient):
            handoff["structured_warning"] = "recipient and next_node differed; next_node was aligned to recipient."
            handoff["next_node"] = recipient
    raw = str(raw_user_input or "").strip()
    if raw and str(handoff.get("goal_state") or "").strip() == raw:
        handoff["structured_warning"] = "goal_state matched raw user wording; -1s should provide a normalized intent."
    return handoff


def validate_delivery_review(review: dict[str, Any], allowed_fact_ids: Iterable[str] | None) -> dict[str, Any]:
    packet = dict(review if isinstance(review, dict) else {})
    packet["evidence_refs"] = _clean_ref_list(packet.get("evidence_refs", []), allowed_fact_ids)
    return packet


def validate_supervisor_tool_calls(tool_calls: Any, available_tool_names: Iterable[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    allowed = {str(name or "").strip() for name in available_tool_names if str(name or "").strip()}
    if not isinstance(tool_calls, list) or not tool_calls:
        return [], {}
    cleaned: list[dict[str, Any]] = []
    for call in tool_calls:
        if not isinstance(call, dict):
            return [], structured_failure_packet(node="0_supervisor", reason_type="validation_error", summary="tool_call was not a dict")
        name = str(call.get("name") or "").strip()
        if not name or name not in allowed:
            return [], structured_failure_packet(node="0_supervisor", reason_type="validation_error", summary=f"Unknown tool name: {name}")
        args = call.get("args", {})
        if not isinstance(args, dict):
            return [], structured_failure_packet(node="0_supervisor", reason_type="validation_error", summary=f"Tool args for {name} were not a dict")
        cleaned.append({**call, "name": name, "args": args})
    return cleaned, {}


def validate_warroom_output(output: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(output, dict) or not output:
        return {}, structured_failure_packet(node="warroom_deliberator", reason_type="validation_error", summary="WarRoom output was not a structured dict")
    status = str(output.get("deliberation_status") or "").strip()
    if status not in {"COMPLETED", "NEEDS_REPLAN", "INSUFFICIENT"}:
        return {}, structured_failure_packet(node="warroom_deliberator", reason_type="validation_error", summary=f"Invalid WarRoom status: {status}")
    return dict(output), {}


__all__ = [
    "StructuredInvokeResult",
    "invoke_structured_with_repair",
    "structured_failure_packet",
    "clean_operation_contract_seed_candidates",
    "is_internal_operation_contract_seed",
    "validate_operation_contract_payload",
    "validate_delivery_review",
    "validate_supervisor_tool_calls",
    "validate_thinking_handoff",
    "validate_thought_critique",
    "validate_warroom_output",
]
