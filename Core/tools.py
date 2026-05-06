"""LangChain tool registry for the live ANIMA graph.

This module is intentionally thin. Tool wrappers expose a stable schema to the
agent; implementation details stay in adapters or the legacy tools.toolbox
module until those are split out.
"""

import os
import sys

from langchain_core.tools import tool


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from Core.adapters import artifacts, neo4j_memory, night_queries
from Core.field_memo import search_field_memos


@tool
def tool_search_field_memos(query: str, limit: int = 5) -> str:
    """
    Search FieldMemo, the short and mid-term structured memory from live turns.

    Use compact entity/topic queries. Results are recall candidates; phase 2
    must still judge relevance and truth.
    """
    res_text, _ = search_field_memos(query, limit=limit)
    return res_text


@tool
def tool_search_memory(keyword: str) -> str:
    """
    Search long-term raw memory and Neo4j PastRecord nodes by keyword.

    Use this for older diary/chat/raw evidence, especially after FieldMemo does
    not answer the goal or when the user explicitly asks to search.
    """
    res_text, _ = neo4j_memory.search_memory(keyword)
    return res_text


@tool
def tool_scroll_chat_log(target_id: str, direction: str = "both", limit: int = 15) -> str:
    """
    Scroll around a known chat/log id or timestamp.

    Use only after a search returned a concrete source id/date, or when
    ToolCarryoverState has an origin_source_id.
    """
    res_text, _ = neo4j_memory.scroll_chat_log(target_id, direction, limit)
    return res_text


@tool
def tool_read_full_diary(target_date: str) -> str:
    """
    Read the full diary/source text for an exact date.
    """
    res_text, _ = neo4j_memory.read_full_source("diary", target_date)
    return res_text


@tool
def tool_read_artifact(artifact_hint: str) -> str:
    """
    Read a local artifact such as PPTX, TXT, MD, JSON, DOCX, or source material.
    """
    res_text, _ = artifacts.read_artifact(artifact_hint)
    return res_text


@tool
def tool_pass_to_phase_3() -> str:
    """
    Hand the approved delivery packet to phase_3.
    """
    return "BYPASS_TO_3"


@tool
def tool_scan_db_schema(dummy_keyword: str = "") -> str:
    """
    Inspect the current Neo4j schema: labels, relationship types, and property keys.
    """
    result_str, _ = neo4j_memory.scan_db_schema()
    return result_str


@tool
def tool_search_dreamhints(keyword: str = "", limit: int = 5) -> str:
    """
    Search active DreamHint night-government advisories.

    Returns only hints whose archive_at/expires_at fields indicate they are
    still active. Treat results as advisory context, not as direct evidence.
    """
    return night_queries.recall_active_dreamhints(keyword, limit=limit)


@tool
def tool_call_119_rescue() -> str:
    """
    Emergency rescue handoff for stuck loops or explicit recovery paths.
    """
    return "EMERGENCY_RESCUE_119"


available_tools = [
    tool_search_field_memos,
    tool_search_memory,
    tool_read_full_diary,
    tool_read_artifact,
    tool_scroll_chat_log,
    tool_search_dreamhints,
    tool_pass_to_phase_3,
    tool_scan_db_schema,
    tool_call_119_rescue,
]
