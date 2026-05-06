import json
import math
import unicodedata

import ollama
import pymysql

from .request_intents_v4 import topic_reset_confidence


def empty_temporal_context():
    return {
        "current_input_anchor": "",
        "continuity_score": 0.0,
        "topic_shift_score": 0.0,
        "topic_reset_confidence": 0.0,
        "carry_over_strength": 0.0,
        "active_task_bias": 0.0,
        "carry_over_allowed": False,
        "candidate_parent_turn_ids": [],
        "recent_match_briefs": [],
    }


def parse_embedding(raw_embedding):
    payload = raw_embedding
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8", errors="ignore")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return []
    if not isinstance(payload, list):
        return []

    result = []
    for value in payload:
        try:
            result.append(float(value))
        except (TypeError, ValueError):
            return []
    return result


def cosine_similarity(vec1, vec2):
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def fetch_recent_songryeon_chat_vectors(db_config, limit=8, exclude_exact_texts=None):
    exclude_exact_texts = {
        unicodedata.normalize("NFKC", str(text or "").strip())
        for text in (exclude_exact_texts or [])
        if str(text or "").strip()
    }
    records = []
    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT role, content, embedding, created_at
                FROM songryeon_chats
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (max(limit * 3, 12),),
            )
            for role, content, embedding, created_at in cursor.fetchall():
                normalized_content = unicodedata.normalize("NFKC", str(content or "").strip())
                if not normalized_content or normalized_content in exclude_exact_texts:
                    continue
                vector = parse_embedding(embedding)
                if not vector:
                    continue
                records.append(
                    {
                        "role": str(role or "").strip(),
                        "content": normalized_content,
                        "embedding": vector,
                        "turn_id": str(created_at),
                    }
                )
                if len(records) >= limit:
                    break
        finally:
            cursor.close()
            conn.close()
    except Exception:
        return []
    records.reverse()
    return records


def build_temporal_context_signal(user_input: str, db_config, shorten, exclude_exact_texts=None, limit=8):
    text = unicodedata.normalize("NFKC", str(user_input or "").strip())
    if not text:
        return empty_temporal_context()

    base = empty_temporal_context()
    base["current_input_anchor"] = shorten(text, 120)
    reset_confidence = topic_reset_confidence(text)
    records = fetch_recent_songryeon_chat_vectors(
        db_config,
        limit=limit,
        exclude_exact_texts=exclude_exact_texts or [],
    )
    if not records:
        base["topic_reset_confidence"] = reset_confidence
        base["topic_shift_score"] = max(0.55, reset_confidence)
        return base

    try:
        current_embedding = ollama.embeddings(model="nomic-embed-text", prompt=text)["embedding"]
    except Exception:
        base["topic_reset_confidence"] = reset_confidence
        return base

    scored = []
    for record in records:
        similarity = cosine_similarity(current_embedding, record["embedding"])
        scored.append(
            {
                "turn_id": record["turn_id"],
                "role": record["role"],
                "content": record["content"],
                "similarity": round(float(similarity), 4),
            }
        )

    scored.sort(key=lambda item: item["similarity"], reverse=True)
    top_matches = scored[:3]
    max_similarity = top_matches[0]["similarity"] if top_matches else 0.0
    continuity_score = max_similarity
    if len(text) <= 8 and any(token in text for token in ["응", "ㅇㅋ", "그래", "맞아", "음", "ㅇㅇ"]):
        continuity_score = max(continuity_score, 0.68)

    topic_shift_score = min(1.0, max(reset_confidence, 1.0 - continuity_score))
    carry_over_strength = max(0.0, min(1.0, continuity_score * (1.0 - (reset_confidence * 0.85))))
    carry_over_allowed = carry_over_strength >= 0.35 and reset_confidence < 0.55

    base.update(
        {
            "continuity_score": round(continuity_score, 3),
            "topic_shift_score": round(topic_shift_score, 3),
            "topic_reset_confidence": round(reset_confidence, 3),
            "carry_over_strength": round(carry_over_strength, 3),
            "active_task_bias": round(min(carry_over_strength, 0.65), 3),
            "carry_over_allowed": carry_over_allowed,
            "candidate_parent_turn_ids": [item["turn_id"] for item in top_matches if item["similarity"] >= 0.35],
            "recent_match_briefs": [
                f"{item['turn_id']}|{item['role']}|sim={item['similarity']:.2f}|{shorten(item['content'], 70)}"
                for item in top_matches
            ],
        }
    )
    return base


__all__ = [
    "build_temporal_context_signal",
    "empty_temporal_context",
]
