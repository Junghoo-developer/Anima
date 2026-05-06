"""Legacy compatibility facade for old `tools.toolbox` imports.

Live implementations now live under `Core.adapters`. Keep this module thin so
old imports keep working while new code can depend on clearer boundaries.
"""

from Core.adapters import artifacts, neo4j_connection, neo4j_memory, night_queries, seed_files
from Core.adapters import web_search as web_search_adapter
from Core.u_function_engine import UFunctionEngine


def get_db_session():
    """Legacy shim; canonical Neo4j connection lives in Core.adapters.neo4j_connection."""
    return neo4j_connection.get_db_session()


def read_artifact(artifact_hint):
    return artifacts.read_artifact(artifact_hint)


def read_full_source(source_type, target_date):
    return neo4j_memory.read_full_source(source_type, target_date, session_factory=get_db_session)


def search_memory(keyword):
    return neo4j_memory.search_memory(keyword, session_factory=get_db_session)


def scroll_chat_log(target_id: str, direction: str = "both", limit: int = 15):
    return neo4j_memory.scroll_chat_log(target_id, direction, limit, session_factory=get_db_session)


def scan_db_schema():
    return neo4j_memory.scan_db_schema(session_factory=get_db_session)


def search_tactics(keyword):
    return night_queries.search_tactics(keyword, session_factory=get_db_session)


def search_supply_topics(keyword=""):
    return night_queries.search_supply_topics(keyword, session_factory=get_db_session)


def recent_tactical_briefing(limit=8):
    return night_queries.recent_tactical_briefing(limit, session_factory=get_db_session)


def recall_recent_dreams(limit=5):
    return night_queries.recall_recent_dreams(limit, session_factory=get_db_session)


def check_db_status(keyword=""):
    return night_queries.check_db_status(keyword, session_factory=get_db_session)


def web_search(query):
    return web_search_adapter.web_search(query)


def update_instinct_file(filename, rule_index, new_voice):
    return seed_files.update_instinct_file(filename, rule_index, new_voice)


def update_core_prompt(target_prompt, new_full_text):
    return seed_files.update_core_prompt(target_prompt, new_full_text)


def read_prompt_file(target_phase):
    return seed_files.read_prompt_file(target_phase)


def scan_trend_u_function(keyword_z, keyword_anti_z="", keyword_y="", track_type="PastRecord"):
    """Retired compatibility wrapper for the old U-function trend scan."""
    try:
        engine = UFunctionEngine()
        if keyword_anti_z and keyword_y:
            return engine.scan_3d_intersection(keyword_z, keyword_anti_z, keyword_y)
        return engine.generate_text_trend_chart(keyword_z, track_type)
    except Exception as exc:
        return f"U-function trend scan is retired and unavailable: {exc}"


__all__ = [
    "check_db_status",
    "get_db_session",
    "read_artifact",
    "read_full_source",
    "read_prompt_file",
    "recall_recent_dreams",
    "recent_tactical_briefing",
    "scan_db_schema",
    "scan_trend_u_function",
    "scroll_chat_log",
    "search_memory",
    "search_supply_topics",
    "search_tactics",
    "update_core_prompt",
    "update_instinct_file",
    "web_search",
]
