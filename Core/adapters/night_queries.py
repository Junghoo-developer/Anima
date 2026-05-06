"""Neo4j read helpers for night/reflection and tactical context."""

from collections.abc import Callable

from Core.adapters import neo4j_connection


def _rows(result):
    if hasattr(result, "data"):
        return result.data()
    return list(result or [])


def search_tactics(keyword: str, *, session_factory: Callable | None = None) -> str:
    """Search recent TacticCard reflections by keyword."""
    keyword = str(keyword or "").strip()
    if not keyword:
        return "[tactics] Empty keyword."
    session_factory = session_factory or neo4j_connection.get_db_session
    try:
        with session_factory() as session:
            rows = _rows(
                session.run(
                    """
                    MATCH (t:TacticCard)
                    WHERE toLower(coalesce(t.situation_tag, '')) CONTAINS toLower($keyword)
                       OR toLower(coalesce(t.reflection_text, '')) CONTAINS toLower($keyword)
                    RETURN t.situation_tag AS tag, t.reflection_text AS reflection
                    ORDER BY t.date DESC LIMIT 3
                    """,
                    keyword=keyword,
                )
            )
    except Exception as exc:
        return f"[tactics error] {exc}"

    if not rows:
        return f"[tactics] No TacticCard matched '{keyword}'."
    lines = [f"[tactics search: {keyword}]"]
    for row in rows:
        tag = str(row.get("tag") or "").strip() or "(untagged)"
        reflection = str(row.get("reflection") or "").strip()
        lines.append(f"- situation: {tag}\n  reflection: {reflection}")
    return "\n".join(lines)


def search_supply_topics(keyword: str = "", *, session_factory: Callable | None = None) -> str:
    """Search SupplyTopic nodes used by the night reflection stack."""
    kw = str(keyword or "").strip()
    session_factory = session_factory or neo4j_connection.get_db_session
    try:
        with session_factory() as session:
            if not kw:
                rows = _rows(
                    session.run(
                        """
                        MATCH (tt:SupplyTopic)
                        OPTIONAL MATCH (sd:SecondDream)-[:TRACKS_TOPIC]->(tt)
                        WITH tt, max(sd.date) AS last_seen
                        RETURN tt.slug AS slug, tt.title AS title, tt.status AS status,
                               last_seen AS last_audit
                        ORDER BY last_seen DESC NULLS LAST, tt.slug ASC LIMIT 20
                        """
                    )
                )
            else:
                rows = _rows(
                    session.run(
                        """
                        MATCH (tt:SupplyTopic)
                        WHERE toLower(coalesce(tt.title, '')) CONTAINS toLower($kw)
                           OR toLower(coalesce(tt.slug, '')) CONTAINS toLower($kw)
                        OPTIONAL MATCH (sd:SecondDream)-[:TRACKS_TOPIC]->(tt)
                        OPTIONAL MATCH (tt)-[:SUBTOPIC_OF]->(parent:SupplyTopic)
                        OPTIONAL MATCH (src:SourceRef)-[:RAW_ADDRESS]->(bt:SupplyBridgeThought)-[:SUPPORTS]->(tt)
                        RETURN DISTINCT tt.slug AS slug, tt.title AS title, tt.status AS status,
                               collect(DISTINCT parent.slug)[0..2] AS parent_slugs,
                               count(DISTINCT bt) AS bridge_count,
                               collect(DISTINCT sd.headline)[0..2] AS audit_heads
                        ORDER BY bridge_count DESC, tt.slug ASC LIMIT 15
                        """,
                        kw=kw,
                    )
                )
    except Exception as exc:
        return f"[supply topics error] {exc}"

    if not rows:
        return f"[supply topics] No topic matched '{kw}'." if kw else "[supply topics] No SupplyTopic nodes found."

    header = f"[supply topics search: {kw}]" if kw else "[recent supply topics]"
    lines = [header]
    for row in rows:
        slug = str(row.get("slug") or "").strip() or "(no slug)"
        title = str(row.get("title") or "").strip()
        status = str(row.get("status") or "").strip() or "unknown"
        if kw:
            parents = ", ".join(p for p in (row.get("parent_slugs") or []) if p) or "none"
            bridge_count = row.get("bridge_count", 0)
            audit_heads = " / ".join(h for h in (row.get("audit_heads") or []) if h) or "none"
            lines.append(
                f"- slug: {slug}\n"
                f"  title: {title}\n"
                f"  status: {status} | bridges: {bridge_count} | parents: {parents} | audits: {audit_heads}"
            )
        else:
            last_audit = row.get("last_audit") or "unknown"
            lines.append(f"- slug: {slug}\n  title: {title}\n  status: {status} | last_audit: {last_audit}")
    return "\n".join(lines)


def recent_tactical_briefing(limit: int = 8, *, session_factory: Callable | None = None) -> str:
    """Return recent TacticalThought rules for advisory context."""
    try:
        lim = max(1, min(int(limit), 24))
    except Exception:
        lim = 8
    session_factory = session_factory or neo4j_connection.get_db_session
    try:
        with session_factory() as session:
            rows = _rows(
                session.run(
                    """
                    MATCH (t:TacticalThought)
                    RETURN t.situation_trigger AS trig, t.actionable_rule AS rule,
                           t.priority_weight AS weight, t.batch_id AS batch
                    ORDER BY t.created_at DESC LIMIT $lim
                    """,
                    lim=lim,
                )
            )
    except Exception as exc:
        return f"[tactical briefing error] {exc}"

    if not rows:
        return "[tactical briefing] No TacticalThought rules recorded yet."
    lines = ["[recent TacticalThought advisory rules]"]
    for idx, row in enumerate(rows, 1):
        trigger = str(row.get("trig") or "").strip()
        rule = str(row.get("rule") or "").strip()
        weight = row.get("weight")
        lines.append(f"{idx}. weight={weight}\n   trigger: {trigger}\n   rule: {rule}")
    return "\n".join(lines)


def recall_recent_dreams(limit: int = 5, *, session_factory: Callable | None = None) -> str:
    """Return recent Dream records as reflective context."""
    try:
        lim = max(1, min(int(limit), 20))
    except Exception:
        lim = 5
    session_factory = session_factory or neo4j_connection.get_db_session
    try:
        with session_factory() as session:
            rows = _rows(
                session.run(
                    """
                    MATCH (d:Dream)
                    RETURN d.date AS date, d.user_input AS input, d.final_answer AS answer
                    ORDER BY d.date DESC LIMIT $limit
                    """,
                    limit=lim,
                )
            )
    except Exception as exc:
        return f"[recent dreams error] {exc}"

    if not rows:
        return "[recent dreams] No Dream records found."
    lines = ["[recent Dream records]"]
    for row in rows:
        lines.append(
            f"- [{row.get('date')}] user: {row.get('input') or ''}\n"
            f"  assistant: {row.get('answer') or ''}"
        )
    return "\n".join(lines)


def recall_active_dreamhints(
    keyword: str = "",
    *,
    limit: int = 5,
    session_factory: Callable | None = None,
) -> str:
    """Return active DreamHint advisories for the field loop."""
    try:
        lim = max(1, min(int(limit), 20))
    except Exception:
        lim = 5
    kw = str(keyword or "").strip()
    session_factory = session_factory or neo4j_connection.get_db_session
    try:
        with session_factory() as session:
            if kw:
                rows = _rows(
                    session.run(
                        """
                        MATCH (dh:DreamHint)
                        WHERE coalesce(dh.archive_at, 9999999999999) > timestamp()
                          AND coalesce(dh.expires_at, 9999999999999) > timestamp()
                          AND (
                            toLower(coalesce(dh.hint_text, '')) CONTAINS toLower($kw)
                            OR toLower(coalesce(dh.branch_path, '')) CONTAINS toLower($kw)
                          )
                        RETURN dh.dreamhint_key AS key, dh.hint_text AS hint,
                               dh.source_persona AS persona, dh.branch_path AS branch_path
                        ORDER BY coalesce(dh.created_at, 0) DESC LIMIT $limit
                        """,
                        kw=kw,
                        limit=lim,
                    )
                )
            else:
                rows = _rows(
                    session.run(
                        """
                        MATCH (dh:DreamHint)
                        WHERE coalesce(dh.archive_at, 9999999999999) > timestamp()
                          AND coalesce(dh.expires_at, 9999999999999) > timestamp()
                        RETURN dh.dreamhint_key AS key, dh.hint_text AS hint,
                               dh.source_persona AS persona, dh.branch_path AS branch_path
                        ORDER BY coalesce(dh.created_at, 0) DESC LIMIT $limit
                        """,
                        limit=lim,
                    )
                )
    except Exception as exc:
        return f"[dreamhint error] {exc}"

    if not rows:
        return f"[dreamhint] No active DreamHint matched '{kw}'." if kw else "[dreamhint] No active DreamHint records."
    lines = [f"[active DreamHint advisories: {kw}]" if kw else "[active DreamHint advisories]"]
    for row in rows:
        key = str(row.get("key") or "").strip()
        branch = str(row.get("branch_path") or "").strip()
        persona = str(row.get("persona") or "").strip()
        hint = str(row.get("hint") or "").strip()
        lines.append(f"- key: {key}\n  branch: {branch} | source_persona: {persona}\n  hint: {hint}")
    return "\n".join(lines)


def check_db_status(keyword: str = "", *, session_factory: Callable | None = None) -> str:
    """Return a compact count report for important Neo4j labels."""
    labels = [
        "Person",
        "CoreEgo",
        "PastRecord",
        "Diary",
        "GeminiChat",
        "SongryeonChat",
        "Dream",
        "SecondDream",
        "SupplyTopic",
        "SupplyBridgeThought",
        "SourceRef",
        "TacticalThought",
        "TacticCard",
        "Emotion",
    ]
    session_factory = session_factory or neo4j_connection.get_db_session
    try:
        with session_factory() as session:
            counts = {}
            for label in labels:
                counts[label] = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
    except Exception as exc:
        return f"[db status error] {exc}"

    lines = ["[Neo4j status]"]
    for label in labels:
        lines.append(f"- {label}: {counts.get(label, 0)}")
    return "\n".join(lines)


__all__ = [
    "check_db_status",
    "recall_active_dreamhints",
    "recall_recent_dreams",
    "recent_tactical_briefing",
    "search_supply_topics",
    "search_tactics",
]
