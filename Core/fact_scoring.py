import math
import re
import unicodedata
from itertools import combinations
from typing import Any


def _clip(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(low, min(high, number))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _logit(value: Any, eps: float = 1e-4) -> float:
    value = _clip(value, eps, 1.0 - eps)
    return math.log(value / (1.0 - value))


def _as_dict(item: Any) -> dict:
    if isinstance(item, dict):
        return dict(item)
    model_dump = getattr(item, "model_dump", None)
    if callable(model_dump):
        return dict(model_dump())
    if hasattr(item, "__dict__"):
        return dict(vars(item))
    return {}


class FactScoringEngine:
    """
    Deterministic scoring for promoting extracted fact candidates.

    This is not a truth oracle. It is a lightweight engineering filter that
    estimates whether a candidate is well supported enough to be promoted by
    the night memory pipeline.
    """

    SOURCE_PRIORS = {
        "raw_source": 0.86,
        "diary": 0.82,
        "pastrecord": 0.78,
        "songryeonchat": 0.70,
        "geminichat": 0.66,
        "dream": 0.62,
        "fieldmemo": 0.56,
        "phase": 0.54,
        "turnprocess": 0.54,
        "unknown": 0.48,
    }

    NEGATION_MARKERS = {
        "not",
        "never",
        "no",
        "false",
        "deny",
        "denied",
        "without",
        "cannot",
        "isn't",
        "wasn't",
        "아니다",
        "아니",
        "없다",
        "않다",
        "못",
        "부정",
        "거짓",
    }

    def __init__(self, min_token_len: int = 2):
        self.min_token_len = max(1, int(min_token_len or 2))

    def normalize_text(self, text: Any) -> str:
        return unicodedata.normalize("NFKC", str(text or "").strip()).lower()

    def tokenize(self, text: Any) -> list[str]:
        normalized = self.normalize_text(text)
        pattern = rf"[0-9a-zA-Z가-힣_-]{{{self.min_token_len},}}"
        tokens = re.findall(pattern, normalized)
        stopwords = {
            "the",
            "and",
            "that",
            "this",
            "with",
            "from",
            "assistant",
            "fieldmemo",
            "known_facts",
            "unknown_slots",
            "그리고",
            "하지만",
            "그러나",
            "사용자",
            "송련",
        }
        return [token for token in tokens if token not in stopwords]

    def jaccard(self, left: Any, right: Any) -> float:
        left_tokens = set(self.tokenize(left))
        right_tokens = set(self.tokenize(right))
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    def source_prior(self, source_type: Any) -> float:
        key = self.normalize_text(source_type).replace("_", "").replace("-", "")
        for known, prior in self.SOURCE_PRIORS.items():
            if known in key:
                return prior
        return self.SOURCE_PRIORS["unknown"]

    def evidence_alignment(self, fact_text: Any, source_excerpt: Any) -> float:
        fact = self.normalize_text(fact_text)
        excerpt = self.normalize_text(source_excerpt)
        if not fact or not excerpt:
            return 0.0
        if fact in excerpt:
            return 1.0

        fact_tokens = set(self.tokenize(fact))
        excerpt_tokens = set(self.tokenize(excerpt))
        if not fact_tokens or not excerpt_tokens:
            return 0.0
        recall = len(fact_tokens & excerpt_tokens) / max(1, len(fact_tokens))
        precision = len(fact_tokens & excerpt_tokens) / max(1, len(excerpt_tokens))
        return _clip(0.78 * recall + 0.22 * min(1.0, precision * 2.0))

    def hallucination_risk(self, fact_text: Any, source_excerpt: Any, source_type: Any) -> float:
        alignment = self.evidence_alignment(fact_text, source_excerpt)
        prior = self.source_prior(source_type)
        length_penalty = 0.0
        if len(str(fact_text or "")) > max(80, len(str(source_excerpt or "")) * 1.4):
            length_penalty = 0.18
        unsupported = 1.0 - alignment
        weak_source = 1.0 - prior
        return _clip(0.64 * unsupported + 0.24 * weak_source + length_penalty)

    def contradiction_pressure(self, fact_a: Any, fact_b: Any) -> float:
        text_a = self.normalize_text(fact_a)
        text_b = self.normalize_text(fact_b)
        if not text_a or not text_b:
            return 0.0

        overlap = self.jaccard(text_a, text_b)
        if overlap < 0.12:
            return 0.0

        neg_a = any(marker in text_a for marker in self.NEGATION_MARKERS)
        neg_b = any(marker in text_b for marker in self.NEGATION_MARKERS)
        number_a = set(re.findall(r"\d+(?:\.\d+)?", text_a))
        number_b = set(re.findall(r"\d+(?:\.\d+)?", text_b))
        numeric_conflict = bool(number_a and number_b and number_a.isdisjoint(number_b))
        negation_conflict = neg_a != neg_b
        if not negation_conflict and not numeric_conflict:
            return _clip(overlap * 0.25)
        return _clip(0.45 + 0.45 * overlap + (0.1 if numeric_conflict else 0.0))

    def redundancy_support(self, fact: dict, peers: list[dict]) -> float:
        fact_text = str(fact.get("fact_text") or "")
        similarities = [
            self.jaccard(fact_text, str(peer.get("fact_text") or ""))
            for peer in peers
            if peer is not fact
        ]
        if not similarities:
            return 0.0
        return _clip(max(similarities) * 0.65 + (sum(similarities) / len(similarities)) * 0.35)

    def score_fact(self, fact: dict, peers: list[dict]) -> dict:
        fact_text = str(fact.get("fact_text") or "")
        source_excerpt = str(fact.get("source_excerpt") or "")
        confidence = _clip(fact.get("confidence", 0.5))
        source = self.source_prior(fact.get("source_type") or fact.get("source_kind") or fact.get("bucket_label"))
        alignment = self.evidence_alignment(fact_text, source_excerpt)
        redundancy = self.redundancy_support(fact, peers)
        contradiction = max(
            [
                self.contradiction_pressure(fact_text, str(peer.get("fact_text") or ""))
                for peer in peers
                if peer is not fact
            ],
            default=0.0,
        )
        hallucination = self.hallucination_risk(fact_text, source_excerpt, fact.get("source_type"))
        log_odds = (
            _logit(confidence)
            + _logit(source)
            + 1.20 * alignment
            + 0.75 * redundancy
            - 1.35 * contradiction
            - 0.90 * hallucination
        )
        purity = _sigmoid(log_odds)
        return {
            "u_support_score": round(_clip(alignment * 0.55 + source * 0.30 + redundancy * 0.15), 4),
            "u_evidence_alignment": round(alignment, 4),
            "u_source_prior": round(source, 4),
            "u_redundancy_support": round(redundancy, 4),
            "u_contradiction_pressure": round(contradiction, 4),
            "u_hallucination_risk": round(hallucination, 4),
            "u_purity_score": round(_clip(purity), 4),
        }

    def annotate_facts(self, fact_leaves: list[Any]) -> list[dict]:
        facts = [_as_dict(item) for item in fact_leaves or []]
        facts = [item for item in facts if item]
        for fact in facts:
            fact.update(self.score_fact(fact, facts))
        return facts

    def cluster_metrics(self, fact_leaves: list[dict]) -> dict:
        facts = [_as_dict(item) for item in fact_leaves or []]
        if not facts:
            return {
                "u_cluster_purity": 0.0,
                "u_coherence_score": 0.0,
                "u_tension_score": 0.0,
                "u_synthesis_score": 0.0,
                "thesis_fact_keys": [],
                "antithesis_fact_keys": [],
                "synthesis_statement": "",
                "inverse_relation_updates": [],
            }

        purities = [_clip(item.get("u_purity_score", item.get("confidence", 0.5))) for item in facts]
        pair_similarities = []
        pair_tensions = []
        for left, right in combinations(facts, 2):
            pair_similarities.append(self.jaccard(left.get("fact_text"), right.get("fact_text")))
            pair_tensions.append(self.contradiction_pressure(left.get("fact_text"), right.get("fact_text")))

        coherence = sum(pair_similarities) / len(pair_similarities) if pair_similarities else 1.0
        tension = max(pair_tensions) if pair_tensions else 0.0
        mean_purity = sum(purities) / len(purities)
        evidence_mass = math.log1p(len(facts)) / math.log(13)
        cluster_purity = _clip(mean_purity * (0.70 + 0.30 * coherence) * (1.0 - 0.55 * tension))
        synthesis_score = _clip(
            math.sqrt(max(0.0, cluster_purity) * max(0.0, coherence)) * (0.75 + 0.25 * evidence_mass)
        )

        ranked = sorted(facts, key=lambda item: _clip(item.get("u_purity_score", 0.0)), reverse=True)
        tense = sorted(facts, key=lambda item: _clip(item.get("u_contradiction_pressure", 0.0)), reverse=True)
        thesis_keys = [str(item.get("fact_key") or "") for item in ranked[:4] if str(item.get("fact_key") or "")]
        antithesis_keys = [
            str(item.get("fact_key") or "")
            for item in tense[:3]
            if _clip(item.get("u_contradiction_pressure", 0.0)) >= 0.25 and str(item.get("fact_key") or "")
        ]

        return {
            "u_cluster_purity": round(cluster_purity, 4),
            "u_coherence_score": round(_clip(coherence), 4),
            "u_tension_score": round(_clip(tension), 4),
            "u_synthesis_score": round(synthesis_score, 4),
            "thesis_fact_keys": thesis_keys,
            "antithesis_fact_keys": antithesis_keys,
            "synthesis_statement": self.synthesis_statement(facts, cluster_purity, coherence, tension),
            "inverse_relation_updates": [],
        }

    def synthesis_statement(self, facts: list[dict], purity: float, coherence: float, tension: float) -> str:
        best = sorted(facts, key=lambda item: _clip(item.get("u_purity_score", 0.0)), reverse=True)
        top_texts = [str(item.get("fact_text") or "").strip() for item in best[:3] if str(item.get("fact_text") or "").strip()]
        if not top_texts:
            return ""
        if tension >= 0.45:
            stance = "Conflicting fact cluster; keep as provisional until reviewed"
        elif purity >= 0.72 and coherence >= 0.25:
            stance = "High-purity fact cluster"
        else:
            stance = "Partially supported fact cluster"
        return f"{stance}: " + " / ".join(top_texts)


def apply_fact_scoring(fact_leaves: list[Any]) -> tuple[list[dict], dict]:
    engine = FactScoringEngine()
    scored_facts = engine.annotate_facts(fact_leaves)
    cluster_metrics = engine.cluster_metrics(scored_facts)
    return scored_facts, cluster_metrics


__all__ = ["FactScoringEngine", "apply_fact_scoring"]
