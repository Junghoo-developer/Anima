"""Thin web search adapter used by night/reflection tools."""

from collections.abc import Callable

from ddgs import DDGS


def web_search(query: str, *, search_provider: Callable | None = None, max_results: int = 3) -> str:
    """Run a compact text web search and format candidates for LLM review."""
    query = str(query or "").strip()
    if not query:
        return "[web search] Empty query."
    try:
        provider = search_provider or (lambda q, limit: DDGS().text(q, max_results=limit))
        results = list(provider(query, max_results))
    except Exception as exc:
        return f"[web search error] {exc}"

    if not results:
        return f"[web search] No results for '{query}'."

    lines = [f"[web search: {query}]"]
    for item in results[:max_results]:
        title = str(item.get("title") or "").strip()
        body = str(item.get("body") or item.get("snippet") or "").strip()
        href = str(item.get("href") or item.get("url") or "").strip()
        line = f"- {title}: {body}"
        if href:
            line += f"\n  url: {href}"
        lines.append(line)
    return "\n".join(lines)


__all__ = ["web_search"]
