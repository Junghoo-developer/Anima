import re
import unicodedata
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class UserGoalContract(BaseModel):
    user_goal: str = Field(
        default="",
        description="The user's literal current objective, preserved without broadening.",
    )
    source_lane: str = Field(
        default="field_memo_review",
        description="Evidence lane currently responsible for filling the goal.",
    )
    output_act: Literal[
        "answer_identity_slot",
        "answer_memory_recall",
        "answer_narrative_fact",
        "self_analysis_snapshot",
        "diagnose_system",
        "direct_answer",
        "unknown",
    ] = Field(
        default="unknown",
        description="User-facing act required after the lane finishes.",
    )
    slot_to_fill: str = Field(
        default="",
        description="Specific answer slot that must be filled before phase_3 is allowed.",
    )
    success_criteria: List[str] = Field(
        default_factory=list,
        description="Concrete checks that make the answer deliverable.",
    )
    forbidden_drift: List[str] = Field(
        default_factory=list,
        description="Nearby but wrong goals that must not replace the current ask.",
    )
    evidence_required: bool = Field(
        default=False,
        description="Whether the answer requires grounded memory/source evidence.",
    )


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _compact_summary(text: str, limit: int = 160) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "").strip())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


def compact_contract_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or "").lower())
    return re.sub(r"\s+", "", normalized)


def _contains_any(text: str, markers: List[str]) -> bool:
    normalized = unicodedata.normalize("NFKC", str(text or "").lower())
    return any(str(marker or "").lower() in normalized for marker in markers)


def _normalize_contract_fact_candidates(facts: List[str], answer_brief: str = "") -> List[str]:
    candidates = [str(item or "").strip() for item in list(facts or []) + ([answer_brief] if answer_brief else [])]
    return [item for item in candidates if item]


def _normalize_name_candidate(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(name or "")).strip()
    if normalized.endswith("\ub2e4") and len(normalized) >= 3:
        normalized = normalized[:-1]
    for suffix in ["\uc785\ub2c8\ub2e4", "\uc774\ub2e4", "\uc57c", "\uc774\uc57c", "\uc784"]:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized.strip()


def derive_user_goal_contract(user_input: str, source_lane: str = "field_memo_review") -> Dict[str, Any]:
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    lowered = text.lower()
    compact = compact_contract_key(text)

    assistant_name_markers = ["\ub124\uc774\ub984", "\ub108\uc774\ub984", "\uc1a1\ub828\uc774\ub984", "assistantname"]
    user_name_markers = ["\ub0b4\uc774\ub984", "\uc720\uc800\uc774\ub984", "\uc0ac\uc6a9\uc790\uc774\ub984", "\ubcf8\uba85", "canonical_name", "user_name"]
    if _contains_any(compact, user_name_markers) and not _contains_any(compact, assistant_name_markers):
        return UserGoalContract(
            user_goal=text,
            source_lane=source_lane,
            output_act="answer_identity_slot",
            slot_to_fill="user.canonical_name",
            success_criteria=[
                "Fill the user's canonical name directly.",
                "Do not replace the name slot with friend lists, self-analysis, fiction, or tool logs.",
                "Metadata alone is never enough evidence for the name slot.",
            ],
            forbidden_drift=["self_analysis", "friend_list", "fictional_story", "tool_log"],
            evidence_required=True,
        ).model_dump()

    deictic_memory_markers = [
        "\uadf8\ub54c",
        "\uadf8\uc0ac\uac74",
        "\uadf8\uc0c1\ud669",
        "\uadf8\uc7a5\uba74",
        "\uc544\uae4c",
        "\ubc29\uae08",
        "\uc774\uc804",
        "previous",
        "that event",
        "thatevent",
        "that moment",
        "thatmoment",
    ]
    recall_markers = [
        "\uae30\uc5b5",
        "\ud68c\uc0c1",
        "\ub5a0\uc62c",
        "\uc0dd\uac01",
        "remember",
        "recall",
    ]
    if _contains_any(compact, deictic_memory_markers) and _contains_any(compact, recall_markers):
        return UserGoalContract(
            user_goal=text,
            source_lane=source_lane,
            output_act="answer_memory_recall",
            slot_to_fill="memory.referent_fact",
            success_criteria=[
                "Recover the concrete situation or event being pointed to.",
                "A repeated question surface does not satisfy this slot.",
                "Use grounded recall evidence before delivery.",
            ],
            forbidden_drift=["generic_answer", "question_echo", "tool_log"],
            evidence_required=True,
        ).model_dump()

    omori_markers = [
        "\uc624\ubaa8\ub9ac",
        "omori",
        "\uc368\ub2c8",
        "sunny",
        "\ub9c8\ub9ac",
        "mari",
        "\ubc14\uc9c8",
        "basil",
        "\uc624\ube0c\ub9ac",
        "aubrey",
        "\ud788\ub85c",
        "hero",
        "\ucf08",
        "kel",
        "\uadf8 \uac8c\uc784",
    ]
    if _contains_any(lowered, omori_markers):
        return UserGoalContract(
            user_goal="Answer the public OMORI/story question directly.",
            source_lane=source_lane,
            output_act="answer_narrative_fact",
            slot_to_fill="",
            success_criteria=[
                "Treat this as public or parametric knowledge unless the user explicitly asks for private stored memory.",
                "Answer the concrete story, character, or relationship question without forcing FieldMemo recall.",
            ],
            forbidden_drift=["system_diagnosis", "private_memory_retrieval"],
            evidence_required=False,
        ).model_dump()

    system_markers = [
        "\ucf54\ub4dc",
        "\ubc84\uadf8",
        "\uc5d0\ub7ec",
        "\uc6b0\ud68c\ub85c",
        "\uad6c\uc870",
        "\uac80\uc0c9\uc5b4",
        "phase",
        "fieldmemo",
        "-1a",
        "-1b",
    ]
    if _contains_any(lowered, system_markers):
        return UserGoalContract(
            user_goal=text,
            source_lane=source_lane,
            output_act="diagnose_system",
            slot_to_fill="",
            success_criteria=["Diagnose the structure, failure mode, or repair path being asked about."],
            forbidden_drift=["personal_psychology", "fictional_story"],
            evidence_required=False,
        ).model_dump()

    analysis_markers = [
        "\uc815\uc2e0 \ubd84\uc11d",
        "\uc2ec\ub9ac \ubd84\uc11d",
        "\uc790\uae30\ubd84\uc11d",
        "\ub098\ub294 \uc5b4\ub5a4 \uc0ac\ub78c",
        "\ub0b4\uac00 \uc5b4\ub5a4 \uc0ac\ub78c",
        "\uac00\uce58\uad00",
    ]
    if _contains_any(lowered, analysis_markers):
        return UserGoalContract(
            user_goal=text,
            source_lane=source_lane,
            output_act="self_analysis_snapshot",
            slot_to_fill="",
            success_criteria=[
                "State a grounded observation-based snapshot.",
                "Do not present it as a clinical diagnosis.",
            ],
            forbidden_drift=["fictional_story", "tool_log"],
            evidence_required=True,
        ).model_dump()

    return UserGoalContract(
        user_goal=text,
        source_lane=source_lane,
        output_act="direct_answer",
        slot_to_fill="",
        success_criteria=["Answer the user's ask directly."],
        forbidden_drift=[],
        evidence_required=False,
    ).model_dump()


def _looks_like_question_surface(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    if not normalized:
        return False
    question_markers = [
        "?",
        "\uc9c8\ubb38",
        "\ubb3c\uc5b4\ubd10",
        "\ub9d0\ud574\uc918",
        "\uae30\uc5b5\ub098",
        "\ub5a0\uc62c\ub824\ubd10",
        "remember",
        "recall",
        "who",
        "what",
    ]
    return any(marker in normalized for marker in question_markers)


def _supports_memory_referent_fact(facts: List[str], answer_brief: str = "") -> bool:
    usable = [item for item in _normalize_contract_fact_candidates(facts, answer_brief) if not _looks_like_question_surface(item)]
    return bool(usable)


def _supports_character_identity(facts: List[str], answer_brief: str = "") -> bool:
    role_markers = [
        "\uc8fc\uc778\uacf5",
        "\uce90\ub9ad\ud130",
        "\uc778\ubb3c",
        "\uac8c\uc784 \uc18d",
        "\uac00\uc0c1",
        "\uc2e4\uc874",
        "\ub2e4\ub978 \uc774\ub984",
        "\ubd84\uc2e0",
        "\uc790\uc544",
        "protagonist",
        "character",
        "fictional",
        "real person",
        "alter ego",
    ]
    entity_markers = ["\uc368\ub2c8", "\uc624\ubaa8\ub9ac", "sunny", "omori"]
    for candidate in _normalize_contract_fact_candidates(facts, answer_brief):
        lowered = unicodedata.normalize("NFKC", candidate).lower()
        if _looks_like_question_surface(lowered):
            continue
        if _contains_any(lowered, role_markers) and _contains_any(lowered, entity_markers):
            return True
    return False


def _supports_character_fictionality(facts: List[str], answer_brief: str = "") -> bool:
    fictionality_markers = [
        "\uac00\uc0c1",
        "\ud5c8\uad6c",
        "\uc2e4\uc874",
        "\uac8c\uc784 \uc18d",
        "\uce90\ub9ad\ud130",
        "\uc778\ubb3c",
        "fictional",
        "fiction",
        "real person",
        "not real",
        "game character",
    ]
    for candidate in _normalize_contract_fact_candidates(facts, answer_brief):
        lowered = unicodedata.normalize("NFKC", candidate).lower()
        if _looks_like_question_surface(lowered):
            continue
        if _contains_any(lowered, fictionality_markers):
            return True
    return False


def _supports_character_relationship(facts: List[str], answer_brief: str = "") -> bool:
    relationship_markers = [
        "\uad00\uacc4",
        "\uc0c1\uad00\uad00\uacc4",
        "\uac19\uc740 \uc778\ubb3c",
        "\ub3d9\uc77c\uc778\ubb3c",
        "\ub3d9\uc77c \uc778\ubb3c",
        "\ubd84\uc2e0",
        "\uc790\uc544",
        "\ub2e4\ub978 \uc774\ub984",
        "\ub610 \ub2e4\ub978 \uc774\ub984",
        "\uc5f0\uacb0",
        "relationship",
        "same person",
        "same character",
        "alter ego",
        "other self",
        "connected",
    ]
    entity_markers = ["\uc368\ub2c8", "\uc624\ubaa8\ub9ac", "sunny", "omori"]
    for candidate in _normalize_contract_fact_candidates(facts, answer_brief):
        lowered = unicodedata.normalize("NFKC", candidate).lower()
        if _looks_like_question_surface(lowered):
            continue
        if _contains_any(lowered, relationship_markers) and _contains_any(lowered, entity_markers):
            return True
    return False


def contract_satisfied_by_facts(contract: Dict[str, Any], facts: List[str], answer_brief: str = "") -> bool:
    slot = str((contract or {}).get("slot_to_fill") or "").strip()
    if slot == "user.canonical_name":
        return bool(contract_identity_names_from_facts(facts, answer_brief))
    if slot == "memory.referent_fact":
        return _supports_memory_referent_fact(facts, answer_brief)
    if slot == "character.identity":
        return _supports_character_identity(facts, answer_brief)
    if slot == "character.fictionality":
        return _supports_character_fictionality(facts, answer_brief)
    if slot == "character.relationship":
        return _supports_character_relationship(facts, answer_brief)
    return True


def contract_missing_item_label(slot: str) -> str:
    labels = {
        "user.canonical_name": "the grounded identity fact being asked for",
        "memory.referent_fact": "the specific remembered event being referenced",
        "character.identity": "the character identity fact being asked for",
        "character.fictionality": "whether the character is fictional or real",
        "character.relationship": "the relationship being asked about",
        "story.narrative_fact": "the story fact being asked for",
        "user.pattern_snapshot": "grounded observations about the visible pattern",
        "system.failure_or_fix": "the concrete system failure or fix",
        "current_goal_answer_seed": "usable evidence for the current answer",
    }
    normalized = str(slot or "").strip()
    if not normalized:
        return "usable evidence for the current answer"
    return labels.get(normalized, "usable evidence for the current answer")


def contract_status_packet(contract: Dict[str, Any], facts: List[str], answer_brief: str = ""):
    slot = str((contract or {}).get("slot_to_fill") or "").strip()
    if not slot:
        return "satisfied", [], ""
    if contract_satisfied_by_facts(contract, facts, answer_brief):
        return "satisfied", [], ""
    missing_item = contract_missing_item_label(slot)
    directive = (
        f"The current evidence still lacks {missing_item}. "
        "Do not widen into a nearby but different answer. Read or judge a source that can answer that item directly."
    )
    return "missing_slot", [missing_item], directive


def filled_slots_from_contract(contract: Dict[str, Any], facts: List[str], answer_brief: str = "") -> Dict[str, Any]:
    slot = str((contract or {}).get("slot_to_fill") or "").strip()
    if not slot:
        return {}
    normalized_facts = [str(fact).strip() for fact in facts or [] if str(fact).strip()]
    if not contract_satisfied_by_facts(contract, normalized_facts, answer_brief):
        return {}
    if slot == "user.canonical_name":
        names = contract_identity_names_from_facts(normalized_facts, answer_brief)
        return {slot: names[0]} if names else {}
    if slot == "memory.referent_fact":
        usable = [fact for fact in normalized_facts if not _looks_like_question_surface(fact)]
        if not usable and answer_brief and not _looks_like_question_surface(answer_brief):
            return {slot: _compact_summary(answer_brief, 240)}
        return {slot: usable[:4]} if usable else {}
    if slot in {"character.identity", "character.fictionality", "character.relationship"}:
        if answer_brief and not _looks_like_question_surface(answer_brief):
            return {slot: _compact_summary(answer_brief, 240)}
        return {slot: normalized_facts[:4]} if normalized_facts else {}
    if answer_brief:
        return {slot: _compact_summary(answer_brief, 240)}
    return {slot: normalized_facts[:4]} if normalized_facts else {}


# Canonical identity parsing overrides: keep user-name extraction broad enough
# for older FieldMemo phrasings such as "사용자의 이름은 ..." and "개발자는 ...".
def extract_user_name_candidates_from_text(text: str) -> List[str]:
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    if not normalized.strip():
        return []
    patterns = [
        r"(?:\ub0b4\s*\uc774\ub984|\uc0ac\uc6a9\uc790(?:\uc758)?\s*\uc774\ub984|\ubcf8\uba85)\s*(?:\uc740|\ub294|\uc774|\uac00|:|=)?\s*([가-힣]{2,4})",
        r"(?:\uac1c\ubc1c\uc790(?:\ub294|\uac00)?)\s*([가-힣]{2,4})",
        r"(?:my\s+name\s+is|user\s+name\s+is)\s*([A-Za-z]{2,30})",
    ]
    names: List[str] = []
    for pattern in patterns:
        names.extend(re.findall(pattern, normalized, flags=re.IGNORECASE))
    return _dedupe_keep_order([str(name).strip() for name in names])[:3]


def extract_canonical_name_candidates_from_identity_claim(value: str) -> List[str]:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    if not text:
        return []
    names: List[str] = []
    patterns = [
        r"(?:\uc0ac\uc6a9\uc790(?:\ub294|\uac00|\uc758)?\s*\uc774\ub984(?:\uc740|\ub294|\uc774|\uac00)?|my\s+name\s+is|user\s+name\s+is)\s*([가-힣A-Za-z]{2,30})",
        r"(?:\ub0b4\s*\uc774\ub984|\ubcf8\uba85)\s*(?:\uc740|\ub294|\uc774|\uac00|:|=)?\s*([가-힣A-Za-z]{2,30})",
        r"(?:\uac1c\ubc1c\uc790(?:\ub294|\uac00)?)\s*([가-힣A-Za-z]{2,30})",
    ]
    for pattern in patterns:
        names.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return _dedupe_keep_order([_normalize_name_candidate(name) for name in names if _normalize_name_candidate(name)])[:3]


def fact_supports_user_canonical_name_claim(value: str) -> bool:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    if not text:
        return False
    if _contains_any(text, ["\uce5c\uad6c", "\ub4f1\uc7a5\uc778\ubb3c", "\uce90\ub9ad\ud130", "friend list", "character list"]):
        return False
    identity_markers = [
        "\ub0b4 \uc774\ub984",
        "\uc0ac\uc6a9\uc790 \uc774\ub984",
        "\uc0ac\uc6a9\uc790\uc758 \uc774\ub984",
        "\ubcf8\uba85",
        "\uac1c\ubc1c\uc790",
        "my name is",
        "user name is",
        "canonical_name",
    ]
    return _contains_any(text, identity_markers)


def contract_identity_names_from_facts(facts: List[str], answer_brief: str = "") -> List[str]:
    names: List[str] = []
    for value in list(facts or []) + ([answer_brief] if answer_brief else []):
        value_text = str(value or "")
        if not fact_supports_user_canonical_name_claim(value_text):
            continue
        names.extend(extract_canonical_name_candidates_from_identity_claim(value_text))
        names.extend(extract_user_name_candidates_from_text(value_text))
    return _dedupe_keep_order(names)[:3]
