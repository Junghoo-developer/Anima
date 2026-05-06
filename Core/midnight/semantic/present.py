"""Semantic present seat."""

from __future__ import annotations

from typing import Any, Mapping


def build_semantic_present(
    *,
    recall_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = dict(recall_packet or {})
    result = packet.get("result") if isinstance(packet.get("result"), Mapping) else {}
    results = list(result.get("results", []) or [])
    return {
        "role": "semantic_present",
        "axis": "semantic",
        "summary": f"Semantic present received {len(results)} recall candidate(s).",
        "recall_results": results,
    }


__all__ = ["build_semantic_present"]
