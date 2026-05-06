"""Compatibility shim for the retired wiki U-math module.

The old implementation contained experimental scoring logic mixed with
mojibake text. The clean implementation now lives in Core.fact_scoring.
"""

from Core.fact_scoring import FactScoringEngine, apply_fact_scoring


WikiUMathEngine = FactScoringEngine


def apply_wiki_u_math(fact_leaves):
    return apply_fact_scoring(fact_leaves)


__all__ = ["WikiUMathEngine", "apply_wiki_u_math"]
