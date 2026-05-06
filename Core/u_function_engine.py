"""Retired U-function trend engine compatibility shim.

The old engine mixed DB trend scans, embedding calls, and experimental
dialectic scoring in one module. Live agent tools no longer expose this path.
Only the clean fact-scoring bridge is kept for legacy callers.
"""

import json

from Core.fact_scoring import apply_fact_scoring


class UFunctionEngine:
    def __init__(self, *_, **__):
        self.retired_reason = (
            "The U-function trend scan engine is retired from the live loop. "
            "Use Core.fact_scoring for night-time fact promotion scoring."
        )

    def _retired_payload(self, scan_type: str, **kwargs) -> str:
        return json.dumps(
            {
                "scan_type": scan_type,
                "status": "retired",
                "reason": self.retired_reason,
                "inputs": kwargs,
                "results": [],
            },
            ensure_ascii=False,
            indent=2,
        )

    def scan_3d_intersection(self, keyword_z: str, keyword_anti_z: str, keyword_y: str, threshold: float = 0.5) -> str:
        return self._retired_payload(
            "3D_Intersection",
            keyword_z=keyword_z,
            keyword_anti_z=keyword_anti_z,
            keyword_y=keyword_y,
            threshold=threshold,
        )

    def scan_pure_shadow(self, keyword_z: str) -> str:
        return self._retired_payload("Inverse_Shadow", keyword_z=keyword_z)

    def generate_text_trend_chart(self, keyword_z: str, track_type: str = "PastRecord") -> str:
        return self._retired_payload("Text_Trend", keyword_z=keyword_z, track_type=track_type)

    def score_wiki_fact_cluster(self, fact_leaves) -> str:
        scored_facts, cluster_metrics = apply_fact_scoring(fact_leaves or [])
        return json.dumps(
            {
                "scan_type": "FactScoring",
                "status": "ok",
                "scored_facts": scored_facts,
                "cluster_metrics": cluster_metrics,
            },
            ensure_ascii=False,
            indent=2,
        )


__all__ = ["UFunctionEngine"]
