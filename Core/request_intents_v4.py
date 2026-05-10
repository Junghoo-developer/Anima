import re
import unicodedata


def _normalize_text(user_input: str) -> str:
    return unicodedata.normalize("NFKC", str(user_input or "").strip()).lower()


def is_assistant_question_request_turn(user_input: str) -> bool:
    text = _normalize_text(user_input)
    if not text:
        return False
    markers = [
        "\uc9c8\ubb38\ud574\ubd10",
        "\uc9c8\ubb38 \uc880 \ud574\ubd10",
        "\ub124\uac00 \uc9c8\ubb38\ud574",
        "\ub124\uac00 \ubb3c\uc5b4\ubd10",
        "\ub2c8\uac00 \uc9c8\ubb38\ud574",
    ]
    english = ["ask me a question", "you ask", "ask first", "ask one question"]
    return any(marker in text for marker in markers) or any(marker in text for marker in english)


def is_recent_dialogue_review_turn(user_input: str, recent_context: str = "") -> bool:
    text = _normalize_text(user_input)
    if not text:
        return False
    markers = [
        "\ucd5c\uadfc \ub300\ud654",
        "\uc9c0\uae08\uae4c\uc9c0\uc758 \ub300\ud654",
        "\uc774\uc804 \ub300\ud654",
        "\ubc29\uae08 \ub300\ud654",
        "\uc5b4\ub514\uac00 \uc774\uc0c1",
        "\ucd5c\uadfc \ub300\ud654\ub97c \uc77d\uace0",
        "\uc9c1\uc811 \ud655\uc778\ud574\ubd10",
        "\ub124\uac00 \uc54c\uc544\ubcf4\ub77c\uace0",
        "\ub124\uac00 \uc54c\uc544\ubd10",
        "\ub124\uac00 \uc9c1\uc811 \uc54c\uc544\ubd10",
        "\ub2e4\uc2dc \uc77d\uc5b4\ubd10",
        "\uc77d\uace0 \ud310\ub2e8",
        "\uacfc\uac70 \uae30\ud68d \ucc3e\uc544\ubd10",
        "\uacfc\uac70 \uae30\ud68d \ucc3e\uc544\uc640",
        "\uc774\uc804 \uae30\ud68d \ucc3e\uc544\uc640",
        "seed \ud30c\uc77c \ubcf4\uace0",
    ]
    if any(marker in text for marker in markers):
        return True
    if recent_context and any(
        marker in text for marker in ["what was weird", "review the conversation", "read the recent chat"]
    ):
        return True
    return False


def is_personal_history_review_turn(user_input: str) -> bool:
    text = _normalize_text(user_input)
    if not text:
        return False

    direct_markers = [
        "\ub0b4 \uacfc\uac70",
        "\ub098\uc758 \uacfc\uac70",
        "\uacfc\uac70\uc758 \ub098",
        "\uc608\uc804\uc758 \ub098",
        "\uc608\uc804 \ub098",
        "\ub0b4 \uc60c\ub0a0",
        "\ub0b4 \uc9c0\ub09c \uae30\ub85d",
        "\ub0b4 \uae30\ub85d",
        "\ub0b4 \uc77c\uae30",
    ]
    review_markers = [
        "\ubd10\ubd10",
        "\ubd10\uc918",
        "\uc77d\uace0",
        "\uc815\ub9ac",
        "\uc694\uc57d",
        "\ubd84\uc11d",
        "\ud310\ub2e8",
        "\ub3cc\uc544\ubd10",
    ]
    english = [
        "my past",
        "my history",
        "look into my past",
        "review my past",
        "personal history",
    ]

    if any(marker in text for marker in direct_markers) and any(marker in text for marker in review_markers):
        return True
    return any(marker in text for marker in english)


def is_initiative_request_turn(user_input: str) -> bool:
    text = _normalize_text(user_input)
    if not text:
        return False
    if is_assistant_question_request_turn(text):
        return True
    markers = [
        "\ub108 \ubb50\ud558\uace0 \uc2f6\uc5b4",
        "\ub108 \ubb50\ud558\uace0 \uc2f6\ub0d0\uace0",
        "\ubb50\ud558\uace0 \uc2f6\uc5b4",
        "\ubb50\ud558\uace0 \uc2f6\ub0d0\uace0",
        "\uc624\ub298\uc740 \uc6b0\ub9ac \ubb50\ud560\uae4c",
        "\uc6b0\ub9ac \ubb50\ud560\uae4c",
        "\uc624\ub298 \ubb50\ud560\uae4c",
        "\ubb50\ud558\uace0 \ub180\uae4c",
        "\uc624\ub298\uc740 \ubb50\ud558\uc9c0",
        "\uac19\uc774 \ubb50\ud560\uae4c",
        "\uc544\ubb34\uac70\ub098 \ud574\ubd10",
        "\ub124\uac00 \ud558\uace0 \uc2f6\uc740 \uac70 \ud574\ubd10",
        "\ub124\uac00 \ud558\uace0 \uc2f6\uc740 \uac70 \ud574",
        "\ub124\uac00 \uc54c\uc544\ubd10",
        "\ub124\uac00 \uc54c\uc544\ubcf4\ub77c\uace0",
        "\ub124\uac00 \uc0dd\uac01\ud574",
        "\ub124\uac00 \uc815\ud574",
        "\ub124\uac00 \ud310\ub2e8\ud574",
        "\uadf8\ub0e5 \ud574\ubd10",
        "\ub124\uac00 \uc81c\uc548\ud574",
        "\uc9c1\uc811 \ud574\ubd10",
    ]
    english = ["you decide", "you think", "don't ask", "just propose", "figure it out"]
    return any(marker in text for marker in markers) or any(marker in text for marker in english)


def is_directive_or_correction_turn(user_input: str) -> bool:
    text = _normalize_text(user_input)
    if not text:
        return False
    if is_assistant_question_request_turn(text):
        return True
    markers = [
        "\ub2e4\uc2dc \ud574",
        "\uc9c1\uc811 \ud655\uc778\ud574\ubd10",
        "\ub124\uac00 \ud655\uc778\ud574\ubd10",
        "\ub124\uac00 \uc54c\uc544\ubd10",
        "\uc774\uc0c1\ud574",
        "\ub2f5\ubcc0\uc774 \uc774\uc0c1\ud574",
        "\uc544\ub2c8\ub77c\uace0",
        "\ub611\ubc14\ub85c",
        "\uc9c1\uc811 \uc77d\uc5b4\ubd10",
        "\uadf8\uac70 \ub9d0\uace0",
        "\uc4f8\ub370\uc5c6\ub294 \uc18c\ub9ac",
        "\ubc18\ubcf5\ud558\uc9c0 \ub9d0",
        "\uac19\uc740 \ub9d0 \ubc18\ubcf5\ud558\uc9c0 \ub9d0",
    ]
    english = ["you decide", "you think", "don't ask", "just propose", "check it yourself"]
    return any(marker in text for marker in markers) or any(marker in text for marker in english)


def is_assistant_investigation_request_turn(user_input: str) -> bool:
    text = _normalize_text(user_input)
    if not text:
        return False
    markers = [
        "\ub124\uac00 \uc9c1\uc811 \uc54c\uc544\uc640",
        "\ub124\uac00 \uc54c\uc544\uc640",
        "\ub124\uac00 \uc9c1\uc811 \uc54c\uc544\ubd10",
        "\ub124\uac00 \ucc3e\uc544\uc640",
        "\ub124\uac00 \uc9c1\uc811 \ucc3e\uc544\uc640",
        "\uc9c1\uc811 \uc77d\uace0 \ud310\ub2e8",
        "\uc9c1\uc811 \uc77d\uace0 \uc815\ub9ac",
        "\ub124\uac00 \uc77d\uace0 \ud310\ub2e8",
        "\ub124\uac00 \uc77d\uace0 \uc815\ub9ac",
        "\uacfc\uac70 \uae30\ud68d \ucc3e\uc544\uc640",
        "\uc774\uc804 \uae30\ud68d \ucc3e\uc544\uc640",
        "seed \ud30c\uc77c \ubcf4\uace0",
        "\ud30c\uc77c \ubcf4\uace0 \uc54c\uc544\ub0b4",
        "\ub124\uac00 \uc54c\uc544\ubcf4\ub77c\uace0",
        "\ub124\uac00 \uc9c1\uc811 \ud655\uc778\ud574",
    ]
    english = [
        "figure it out yourself",
        "investigate it yourself",
        "go find out",
        "read it yourself",
        "look it up yourself",
    ]
    return any(marker in text for marker in markers) or any(marker in text for marker in english)


def extract_explicit_search_phrase(user_input: str) -> str:
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    if not text:
        return ""

    candidate = ""
    lowered = text.lower()
    search_intent = any(marker in lowered for marker in ["검색", "임베딩", "search", "semantic", "찾아"])

    if search_intent:
        for pattern in [
            r'"([^"]{1,80})"',
            r"'([^']{1,80})'",
            r"“([^”]{1,80})”",
            r"‘([^’]{1,80})’",
        ]:
            match = re.search(pattern, text)
            if match:
                candidate = match.group(1).strip()
                break

    if not candidate:
        embedding_search_match = re.search(
            r"([A-Za-z0-9\uac00-\ud7a3 _-]{1,80})\s*(?:이라고|라고)\s*(?:임베딩\s*)?(?:검색|서치)(?:을|를)?(?:\s*(?:해봐|해|해줘|돌려|조져))?",
            text,
            flags=re.IGNORECASE,
        )
        if embedding_search_match:
            candidate = embedding_search_match.group(1).strip()

    if not candidate:
        search_match = re.match(r"^\s*(?:다시\s+)?search\s+(.+?)\s*$", text, flags=re.IGNORECASE)
        if search_match:
            candidate = search_match.group(1).strip()

    if not candidate:
        korean_search_match = re.match(r"^\s*(?:다시\s+)?검색\s+(.+?)\s*$", text)
        if korean_search_match:
            candidate = korean_search_match.group(1).strip()

    if not candidate:
        quote_match = re.search(
            r"([A-Za-z0-9\uac00-\ud7a3 _-]{1,80})\s*(?:이라고|라고)\s*(?:쳐봐|검색해봐|검색해|찾아봐|찾아와)",
            text,
            flags=re.IGNORECASE,
        )
        if quote_match:
            candidate = quote_match.group(1).strip()

    if not candidate:
        object_match = re.search(
            r"([A-Za-z0-9\uac00-\ud7a3 _-]{1,80})\s*(?:을|를)\s*(?:쳐봐|검색해봐|검색해|검색해줘|찾아봐|찾아와|찾아줘)",
            text,
            flags=re.IGNORECASE,
        )
        if object_match:
            candidate = object_match.group(1).strip()

    if not candidate:
        return ""

    candidate = re.sub(r"^\s*(?:다시|저기|그럼|그러면|그|그거|그것|좀)\s+", "", candidate, flags=re.IGNORECASE).strip()
    candidate = re.sub(r"^\s*(?:search|검색)\s+", "", candidate, flags=re.IGNORECASE).strip()
    candidate = re.split(r"\s*(?:그리고|그럼|결과|결과가|아니면|or)\s+", candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    candidate = re.sub(
        r"\s*(?:이라고|라고)\s*(?:쳐봐|검색해봐|검색해|검색해줘|찾아봐|찾아와|찾아줘).*$",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip()
    candidate = re.sub(r"\s*(?:검색|search)\s*(?:결과|결과가).*$", "", candidate, flags=re.IGNORECASE).strip()
    return candidate.strip("\"'“”‘’ ")

def classify_requested_assistant_move(user_input: str, recent_context: str = "") -> str:
    """Compatibility shim for old callers.

    The thin-controller field loop no longer lets this helper create routing
    decisions such as ``investigate_now`` or ``review_recent_dialogue``.  Callers
    that need a narrow predicate should use the explicit ``is_*`` helpers
    below, while phase -1s owns the only initial turn contract.
    """
    _ = (user_input, recent_context)
    return ""


def topic_reset_confidence(user_input: str) -> float:
    text = _normalize_text(user_input)
    if not text:
        return 0.0

    high_markers = [
        "\ub410\ub2e4",
        "\uc774\uc81c \ub410\ub2e4",
        "\uadf8\ub9cc",
        "\uc544\ubb34\uac70\ub098 \ud574\ubd10",
        "\ub108 \ubb50\ud558\uace0 \uc2f6\uc5b4",
        "\ub108 \ubb50\ud558\uace0 \uc2f6\ub0d0\uace0",
        "\ubb50\ud558\uace0 \uc2f6\uc5b4",
        "\ubb50\ud558\uace0 \uc2f6\ub0d0\uace0",
        "\ub2e4\ub978 \uc598\uae30",
        "\uc8fc\uc81c \ubc14\uafd4",
        "\uc598\uae30 \ubc14\uafb8\uc790",
    ]
    medium_markers = [
        "\uc774\uc81c",
        "\ub9d0\uace0",
        "\uadf8\uac74 \ub410",
        "\uadf8\uac70 \ub9d0\uace0",
        "\uad00\uc2ec \uc5c6\uc5b4",
        "\uc0c1\uad00 \uc5c6\uc5b4",
    ]
    if any(marker in text for marker in high_markers):
        return 0.9
    if any(marker in text for marker in medium_markers):
        return 0.65
    return 0.0


__all__ = [
    "classify_requested_assistant_move",
    "extract_explicit_search_phrase",
    "is_assistant_investigation_request_turn",
    "is_assistant_question_request_turn",
    "is_directive_or_correction_turn",
    "is_initiative_request_turn",
    "is_personal_history_review_turn",
    "is_recent_dialogue_review_turn",
    "topic_reset_confidence",
]
