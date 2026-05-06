import json
import math
import ollama
import os
import sys
import re
import unicodedata
import builtins
from datetime import datetime

from dotenv import load_dotenv


def _configure_console_streams():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_configure_console_streams()

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

load_dotenv()


def _log(message: str):
    text = str(message)
    try:
        builtins.print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        builtins.print(safe_text)


print = _log

from Core.inference_buffer import InferenceBuffer
from Core.branch_architect import build_branch_architect_state
from Core.midnight import strategy_council as strategy_council_department
from Core.midnight import rem_plan as rem_plan_department
from Core.midnight import rem_governor as rem_governor_department
from Core.midnight import policy_doctrine as policy_doctrine_department
from Core.midnight_reflection_contracts import (
    CONSTITUTION_TEXT as CONTRACT_CONSTITUTION_TEXT,
    PHASE7_PROMPT as CONTRACT_PHASE7_PROMPT,
    PHASE8A_PROMPT as CONTRACT_PHASE8A_PROMPT,
    PHASE8B_PROMPT as CONTRACT_PHASE8B_PROMPT,
    PHASE9_PROMPT as CONTRACT_PHASE9_PROMPT,
    ClassifiedTopic,
    FactLeafCandidate,
    MidnightState,
    Phase7Schema,
    Phase8Action,
    Phase8aSchema,
    Phase8bSchema,
    Phase9Schema,
    RefinedMidnightNode,
    SupplyBridge,
    TacticalThoughtItem,
    build_reflection_debate_state,
)
from Core.night_persistence_utils import link_both_roots, link_target_root
from Core.night_government_persistence import (
    persist_branch_architect,
    persist_rem_governor_state,
    persist_rem_plan,
)
from Core.night_policy_persistence import persist_route_policies, persist_tool_doctrines
from Core.night_strategy_persistence import persist_strategy_council
from Core.night_tactical_persistence import forge_tactical_thoughts_neo4j, merge_topic_hierarchy
from Core.night_branch_growth_persistence import (
    persist_branch_digests,
    persist_branch_growth_header,
    persist_child_branch_proposals,
    persist_concept_clusters,
    persist_difference_notes,
    persist_fact_leaf_audits,
    persist_fact_leaves,
    persist_source_fact_pairs,
    persist_strategy_attention,
    persist_synthesis_bridges,
    persist_time_buckets,
)
from Core.field_memo import (
    apply_local_reports_to_governor,
    build_branch_offices,
    build_layered_memos,
    field_memo_fact_leaf_candidates,
    load_recent_field_memos,
    official_field_memos,
    persist_branch_offices,
    persist_layered_memos,
)
from Core.rem_governor import (
    AttentionDigestItem,
    ArchitectHandoffReportSchema,
    BranchDigestItem,
    BranchGrowthReportSchema,
    ConceptClusterItem,
    ChildBranchProposalItem,
    DifferenceNoteItem,
    FactLeafAuditItem,
    FactLeafItem,
    FactLeafVerificationBatchSchema,
    GoalGapItem,
    GoalTreeItem,
    GovernorInventoryItem,
    GovernorPolicyAssetItem,
    NightlyScopeItem,
    Phase8ReviewPacket,
    REMGovernorStateSchema,
    REMPlanSchema,
    RoutePolicyItem,
    SourceFactPairItem,
    StrategyCouncilStateSchema,
    SynthesisBridgeThoughtItem,
    TimeBucketItem,
    ToolDoctrineItem,
    branch_path_for_topic,
    branch_title_ko,
    dedupe_keep_order,
    normalize_branch_path_to_existing_roots,
    parse_branch_health_map,
    topic_slug_from_branch_path,
    topic_branch_templates,
    topic_label_ko,
)
from Core.state import AnimaState
from Core.fact_scoring import apply_fact_scoring
from Core.adapters.neo4j_memory import read_full_source, search_memory
from Core.adapters.night_queries import recall_recent_dreams, search_supply_topics, search_tactics
from Core.adapters.web_search import web_search

def _env(name, default=None):
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


NEO4J_URI = _env("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = _env("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = _env("NEO4J_PASSWORD")

PHASE8_TOOLS = frozenset({
    "SEARCH",
    "READ_FULL_SOURCE",
    "web_search",
    "recall_recent_dreams",
    "search_tactics",
    "search_supply_topics",
})

TOOLS_REQUIRING_KEYWORD = frozenset({
    "SEARCH",
    "READ_FULL_SOURCE",
    "web_search",
    "search_tactics",
    "search_supply_topics",
})

PROMPTS_DIR = os.path.join(project_root, "SEED", "prompts")

from langgraph.graph import StateGraph, END

class DreamWeaver:
    """
    Midnight reflection pipeline entry point.
    - execute_midnight_reflection(YYYY-MM-DD)
    - execute_grand_reflection_sweep()
    """
    CONSTITUTION_TEXT = CONTRACT_CONSTITUTION_TEXT
    PHASE7_PROMPT = CONTRACT_PHASE7_PROMPT
    PHASE8A_PROMPT = CONTRACT_PHASE8A_PROMPT
    PHASE8B_PROMPT = CONTRACT_PHASE8B_PROMPT
    PHASE9_PROMPT = CONTRACT_PHASE9_PROMPT

    def __init__(self):
        self.name = "SongRyeon_midnight_reflection"
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.model = os.getenv("ANIMA_MEMORY_MODEL", "gemma4:e4b").strip() or "gemma4:e4b"
        self.action_model = "llama3.1:8b"
        self.buffer = InferenceBuffer()
        self.state = AnimaState()
        # Build the graph after all runtime dependencies are ready.
        self.app = self.build_graph()

    @staticmethod
    def _describe_backend_error(exc):
        if isinstance(exc, AuthError):
            return "Neo4j authentication failed. Check NEO4J_USER and NEO4J_PASSWORD in .env."
        if isinstance(exc, ServiceUnavailable):
            return f"Neo4j connection failed. Check whether {NEO4J_URI} is reachable."
        return f"Neo4j processing failed: {exc}"

    def _ensure_neo4j_ready(self):
        try:
            self.neo4j_driver.verify_connectivity()
            return True, ""
        except Exception as exc:
            return False, self._describe_backend_error(exc)

    def _neo4j_label_exists(self, label_name: str):
        normalized = str(label_name or "").strip()
        if not normalized or not self.neo4j_driver:
            return False
        try:
            with self.neo4j_driver.session() as session:
                rows = session.run("CALL db.labels() YIELD label RETURN collect(label) AS labels")
                record = next(iter(rows), None)
                labels = set(record["labels"] or []) if record else set()
                return normalized in labels
        except Exception:
            return False

    def _neo4j_relationship_type_exists(self, relationship_type: str):
        normalized = str(relationship_type or "").strip()
        if not normalized or not self.neo4j_driver:
            return False
        try:
            with self.neo4j_driver.session() as session:
                rows = session.run(
                    "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS relationship_types"
                )
                record = next(iter(rows), None)
                relationship_types = set(record["relationship_types"] or []) if record else set()
                return normalized in relationship_types
        except Exception:
            return False

    @staticmethod
    def _read_prompt_file(filename):
        path = os.path.join(PROMPTS_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _inject(template, **kwargs):
        out = template
        for k, v in kwargs.items():
            out = out.replace("{" + k + "}", str(v))
        return out

    @staticmethod
    def _safe_json_load(raw_content):
        if not raw_content:
            return None
        try:
            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return json.loads(raw_content)
        except Exception as e:
            print(f"\n[JSON parse error] {e}\nraw_content:\n{raw_content}\n")
            return None

    @staticmethod
    def _trim_text(value, limit=800):
        text = str(value or "").strip()
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        if len(text) <= limit:
            return text
        return text[:limit] + "...(truncated)"

    @staticmethod
    def _dedupe_keep_order(items):
        return dedupe_keep_order(items)

    @staticmethod
    def _dedupe_dicts_by_key(items, key):
        seen = set()
        result = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            marker = str(item.get(key) or "").strip()
            if not marker or marker in seen:
                continue
            seen.add(marker)
            result.append(item)
        return result

    @staticmethod
    def _topic_label_ko(topic_slug: str):
        return topic_label_ko(topic_slug)

    @classmethod
    def _branch_title_ko(cls, branch_path: str):
        return branch_title_ko(branch_path)

    @staticmethod
    def _normalize_branch_path_to_existing_roots(branch_path: str):
        return normalize_branch_path_to_existing_roots(branch_path)
        path = str(branch_path or "").strip()
        if not path:
            return ""
        if path.startswith("UserRoot/"):
            return "Person/" + path.split("/", 1)[1]
        if path.startswith("SongryeonRoot/"):
            return "CoreEgo/" + path.split("/", 1)[1]
        return path

    @staticmethod
    def _branch_root_info(branch_path: str):
        path = str(branch_path or "").strip()
        if path.startswith("Person/"):
            return ("Person:stable", "stable", 0)
        if path.startswith("CoreEgo/"):
            return ("CoreEgo:songryeon", "songryeon", 1)
        return ("", "", 99)

    @staticmethod
    def _active_topic_slugs(audit, insufficient_only=False):
        topics = (audit or {}).get("classified_topics", [])
        slugs = []
        for topic in topics:
            if insufficient_only and topic.get("supply_sufficient"):
                continue
            slug = (topic.get("topic_slug") or "").strip()
            if slug:
                slugs.append(slug)
        return slugs

    @classmethod
    def _tool_history_text(cls, tool_runs, limit=8, result_char_limit=800):
        if not tool_runs:
            return "(empty source excerpt)"
        sliced = tool_runs[-limit:]
        compact = []
        for run in sliced:
            compact.append({
                "topic_slug": (run.get("topic_slug") or "").strip(),
                "tool": (run.get("tool") or "").strip(),
                "keyword": str(run.get("keyword") or "").strip(),
                "result_excerpt": cls._trim_text(run.get("result"), result_char_limit),
            })
        return json.dumps(compact, ensure_ascii=False, indent=2)

    @classmethod
    def _reconcile_tool_runs(cls, tool_runs, audit):
        active_topic_slugs = set(cls._active_topic_slugs(audit))
        reconciled = {}
        for run in tool_runs or []:
            topic_slug = (run.get("topic_slug") or "").strip()
            if topic_slug and active_topic_slugs and topic_slug not in active_topic_slugs:
                continue
            signature = (
                topic_slug,
                (run.get("tool") or "").strip(),
                str(run.get("keyword") or "").strip(),
            )
            reconciled[signature] = {
                "topic_slug": topic_slug,
                "tool": (run.get("tool") or "").strip(),
                "keyword": str(run.get("keyword") or "").strip(),
                "result": run.get("result"),
            }
        return list(reconciled.values())[-16:]

    @classmethod
    def _reconcile_bridges(cls, existing, new_items, audit):
        active_topic_slugs = set(cls._active_topic_slugs(audit))
        reconciled = {}
        for bridge in (existing or []) + (new_items or []):
            topic_slug = (bridge.get("topic_slug") or "").strip()
            source_address = (bridge.get("source_address") or "").strip()
            bridge_thought = (bridge.get("bridge_thought") or "").strip()
            parent_topic_slug = (bridge.get("parent_topic_slug") or "").strip()

            if not topic_slug or not source_address or not bridge_thought:
                continue
            if active_topic_slugs and topic_slug not in active_topic_slugs:
                continue

            signature = (topic_slug, source_address, parent_topic_slug)
            candidate = {
                "topic_slug": topic_slug,
                "source_address": source_address,
                "bridge_thought": bridge_thought,
                "parent_topic_slug": parent_topic_slug or None,
            }
            previous = reconciled.get(signature)
            if previous is None or len(candidate["bridge_thought"]) >= len(previous.get("bridge_thought") or ""):
                reconciled[signature] = candidate
        return list(reconciled.values())

    @classmethod
    def _reconcile_fact_leaf_candidates(cls, existing, new_items, audit):
        active_topic_slugs = set(cls._active_topic_slugs(audit))
        reconciled = {}
        for item in (existing or []) + (new_items or []):
            if not isinstance(item, dict):
                continue
            topic_slug = str(item.get("topic_slug") or "").strip()
            source_address = str(item.get("source_address") or "").strip()
            fact_text = cls._trim_text(str(item.get("fact_text") or "").strip(), 320)
            if not topic_slug or not source_address or not fact_text:
                continue
            if active_topic_slugs and topic_slug not in active_topic_slugs:
                continue
            source_kind = str(item.get("source_kind") or "").strip()
            inferred_time_bucket = str(item.get("inferred_time_bucket") or "").strip()
            parent_topic_slug = str(item.get("parent_topic_slug") or "").strip()
            try:
                support_weight = float(item.get("support_weight", 0.55) or 0.55)
            except Exception:
                support_weight = 0.55
            signature = (
                topic_slug,
                source_address,
                fact_text.lower(),
                inferred_time_bucket,
            )
            candidate = {
                "topic_slug": topic_slug,
                "source_address": source_address,
                "fact_text": fact_text,
                "parent_topic_slug": parent_topic_slug or None,
                "source_kind": source_kind,
                "inferred_time_bucket": inferred_time_bucket,
                "support_weight": round(max(0.0, min(1.0, support_weight)), 3),
            }
            previous = reconciled.get(signature)
            if previous is None or len(candidate["fact_text"]) >= len(previous.get("fact_text") or ""):
                reconciled[signature] = candidate
        return list(reconciled.values())[:24]

    @classmethod
    def _extract_fact_leaf_candidates_from_tool_runs_text(cls, tool_runs_text, active_topic_slugs):
        active_topic_slugs = [str(slug or "").strip() for slug in (active_topic_slugs or []) if str(slug or "").strip()]
        default_topic_slug = active_topic_slugs[0] if active_topic_slugs else ""
        try:
            parsed = json.loads(tool_runs_text)
        except Exception:
            return []
        if not isinstance(parsed, list):
            return []

        candidates = []
        hit_pattern = re.compile(
            r"\[異쒖쿂:\s*([^\]]+)\]\s*(?:\([^)]*\))?\s*(?:\n| )*??듭떖 ?붿빟:\s*(.+?)(?=(?:\n\[異쒖쿂:)|$)",
            re.DOTALL,
        )

        for run in parsed:
            if not isinstance(run, dict):
                continue
            topic_slug = str(run.get("topic_slug") or default_topic_slug).strip()
            if not topic_slug:
                continue
            excerpt = cls._trim_text(str(run.get("result_excerpt") or "").strip(), 2000)
            if not excerpt:
                continue
            lowered = excerpt.lower()
            if "duplicate warning" in lowered:
                continue
            matches = list(hit_pattern.finditer(excerpt))
            for match in matches:
                source_address = str(match.group(1) or "").strip()
                fact_text = cls._trim_text(re.sub(r"\s+", " ", str(match.group(2) or "").strip()), 280)
                source_kind, _, inferred_time_bucket, _ = cls._source_address_parts(source_address)
                if not source_address or not fact_text:
                    continue
                candidates.append({
                    "topic_slug": topic_slug,
                    "source_address": source_address,
                    "fact_text": fact_text,
                    "source_kind": source_kind,
                    "inferred_time_bucket": inferred_time_bucket,
                    "support_weight": 0.61,
                })

        return cls._reconcile_fact_leaf_candidates([], candidates, {"classified_topics": [{"topic_slug": slug} for slug in active_topic_slugs]})

    @staticmethod
    def _normalize_phase_payload(value):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped and stripped[0] in "[{":
                try:
                    return json.loads(stripped)
                except Exception:
                    return value
        return value

    @staticmethod
    def _topic_branch_templates():
        return topic_branch_templates()
        return {
            "personal_history_review": "Person/personal_history/history_review",
            "recent_dialogue_review": "CoreEgo/conversation/dialogue_review",
            "self_analysis_snapshot": "Person/self_model/visible_patterns",
            "tool_routing": "CoreEgo/ops/tool_doctrine",
            "field_repair": "CoreEgo/ops/field_repair",
        }

    def _branch_path_for_topic(self, topic_slug):
        return branch_path_for_topic(topic_slug)
        topic = str(topic_slug or "").strip()
        templates = self._topic_branch_templates()
        return self._normalize_branch_path_to_existing_roots(
            templates.get(topic, f"CoreEgo/misc/{topic or 'field_repair'}")
        )

    @staticmethod
    def _parse_branch_health_map(rem_governor):
        return rem_governor_department._parse_branch_health_map(rem_governor)

    @staticmethod
    def _topic_slug_from_branch_path(branch_path: str):
        return topic_slug_from_branch_path(branch_path)

    @classmethod
    def _plan_branch_paths(cls, rem_plan):
        return rem_plan_department._plan_branch_paths(cls, rem_plan)

    @classmethod
    def _plan_topics(cls, rem_plan):
        return rem_plan_department._plan_topics(cls, rem_plan)

    @classmethod
    def _plan_evidence_points(cls, rem_plan):
        return rem_plan_department._plan_evidence_points(cls, rem_plan)

    @staticmethod
    def _safe_slug_fragment(value: str):
        text = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
        return text or "unknown"

    @classmethod
    def _source_address_parts(cls, source_address: str):
        text = str(source_address or "").strip()
        if not text:
            return ("unknown", "", "", "unknown")

        matched_date = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        day_label = matched_date.group(1) if matched_date else ""
        if day_label:
            return (
                text.split(":", 1)[0].split("|", 1)[0].strip() or "unknown",
                text.split(":", 1)[-1].strip() if ":" in text else text.split("|", 1)[-1].strip(),
                day_label,
                "day",
            )

        if "|" in text:
            source_type, _, source_id = text.partition("|")
            return (source_type.strip() or "unknown", source_id.strip(), "", "unknown")
        if ":" in text:
            source_type, _, source_id = text.partition(":")
            return (source_type.strip() or "unknown", source_id.strip(), "", "unknown")
        return ("unknown", text, "", "unknown")

    @classmethod
    def _bucket_key_for_label(cls, label: str, scope: str):
        normalized_label = str(label or "").strip() or "unknown"
        normalized_scope = str(scope or "unknown").strip() or "unknown"
        return f"time_bucket::{normalized_scope}::{cls._safe_slug_fragment(normalized_label)}"

    @classmethod
    def _materialize_time_bucket(cls, label: str, scope: str):
        normalized_label = str(label or "").strip() or "unknown"
        normalized_scope = str(scope or "unknown").strip() or "unknown"
        return TimeBucketItem(
            bucket_key=cls._bucket_key_for_label(normalized_label, normalized_scope),
            label=normalized_label,
            time_scope=normalized_scope if normalized_scope in {"day", "month", "year", "unknown"} else "unknown",
        ).model_dump()

    def _collect_branch_source_addresses(self, branch_path, evidence_addresses, dream_rows):
        root_entity, _, _ = self._branch_root_info(branch_path)
        collected = []
        for address in evidence_addresses or []:
            normalized = str(address or "").strip()
            if not normalized:
                continue
            if self._looks_like_source_address(normalized):
                collected.append(normalized)

        for row in dream_rows or []:
            if not isinstance(row, dict):
                continue
            process_summary = self._normalize_phase_payload(row.get("process_summary"))
            if isinstance(process_summary, dict):
                for source_id in process_summary.get("used_sources", []) or []:
                    normalized = str(source_id or "").strip()
                    if not normalized:
                        continue
                    if self._looks_like_source_address(normalized):
                        collected.append(normalized)
                    elif re.match(r"^\d{4}-\d{2}-\d{2}$", normalized):
                        if root_entity.startswith("Person:"):
                            collected.append(f"Diary|{normalized}")
                        elif root_entity.startswith("CoreEgo:"):
                            collected.append(f"SongryeonChat|{normalized}")
                        collected.append(f"PastRecord|{normalized}")

        return self._dedupe_keep_order(collected)[:24]

    @staticmethod
    def _split_raw_fact_candidates(text):
        normalized = re.sub(r"\s+", " ", str(text or "").strip())
        if not normalized:
            return []
        chunks = re.split(r"(?<=[\.\!\???)\s+|\n+", normalized)
        candidates = []
        for chunk in chunks:
            cleaned = str(chunk or "").strip(" -")
            if len(cleaned) < 12:
                continue
            candidates.append(cleaned)
        return candidates[:6]

    def _query_connected_topic_density(self, branch_path, topic_slug):
        if not self.neo4j_driver or not topic_slug:
            return 0
        try:
            with self.neo4j_driver.session() as session:
                row = session.run(
                    """
                    MATCH (tt:SupplyTopic {slug: $topic_slug})
                    OPTIONAL MATCH (sd:SecondDream)-[:TRACKS_TOPIC]->(tt)
                    WITH tt, count(DISTINCT sd) AS second_dream_count
                    OPTIONAL MATCH (bd:BranchDigest)-[:SUMMARIZES_TOPIC]->(tt)
                    WITH tt, second_dream_count, count(DISTINCT bd) AS digest_count
                    OPTIONAL MATCH (rp:RoutePolicy)-[:TRACKS_TOPIC]->(tt)
                    WITH tt, second_dream_count, digest_count, count(DISTINCT rp) AS policy_count
                    OPTIONAL MATCH (gb:GovernorBranch {governor_key: 'rem_governor_v1', branch_path: $branch_path})
                    OPTIONAL MATCH (gb)-[:HAS_POLICY|HAS_DOCTRINE]->(asset)
                    RETURN second_dream_count, digest_count, policy_count, count(DISTINCT asset) AS branch_asset_count
                    """,
                    topic_slug=topic_slug,
                    branch_path=branch_path,
                ).single()
                if not row:
                    return 0
                fact_count = 0
                if self._neo4j_label_exists("FactLeaf") and self._neo4j_relationship_type_exists("ABOUT_TOPIC"):
                    fact_row = session.run(
                        """
                        MATCH (tt:SupplyTopic {slug: $topic_slug})
                        OPTIONAL MATCH (fl:FactLeaf)-[:ABOUT_TOPIC]->(tt)
                        RETURN count(DISTINCT fl) AS fact_count
                        """,
                        topic_slug=topic_slug,
                    ).single()
                    if fact_row:
                        fact_count = int(fact_row.get("fact_count") or 0)
                return int(
                    (row.get("second_dream_count") or 0)
                    + (row.get("digest_count") or 0)
                    + (row.get("policy_count") or 0)
                    + fact_count
                    + (row.get("branch_asset_count") or 0)
                )
        except Exception:
            return 0

    def _measure_branch_topic_pressure(
        self,
        branch_path,
        topic_slug,
        dream_rows,
        branch_coverage,
        supporting_dream_ids,
        source_addresses,
        raw_source_fragments,
    ):
        local_tool_hits = 0
        local_used_source_hits = 0
        for row in dream_rows or []:
            if not isinstance(row, dict):
                continue
            process_summary = self._normalize_phase_payload(row.get("process_summary"))
            if not isinstance(process_summary, dict):
                continue
            executed_tool = str(process_summary.get("executed_tool") or "").strip()
            if executed_tool in {"tool_search_memory", "tool_read_full_diary", "tool_scroll_chat_log", "tool_read_artifact"}:
                local_tool_hits += 1
            used_sources = process_summary.get("used_sources", []) or []
            local_used_source_hits += len([item for item in used_sources if str(item or "").strip()])

        connected_density = self._query_connected_topic_density(branch_path, topic_slug)
        pressure = (
            0.20
            + 0.10 * min(local_tool_hits, 4)
            + 0.03 * min(local_used_source_hits, 8)
            + 0.07 * min(len(self._dedupe_keep_order(source_addresses)), 6)
            + 0.05 * min(len(raw_source_fragments), 6)
            + 0.10 * min(len(branch_coverage), 4)
            + 0.05 * min(len(self._dedupe_keep_order(supporting_dream_ids)), 6)
            + 0.03 * min(connected_density, 10)
        )
        return round(min(1.0, pressure), 3)

    def _load_raw_source_fragments_for_branch(self, branch_path, source_addresses, topic_slug):
        if not self.neo4j_driver:
            return []
        root_entity, _, _ = self._branch_root_info(branch_path)
        fragments = []
        topic_markers = self._dedupe_keep_order([
            str(topic_slug or "").strip(),
            self._topic_label_ko(topic_slug),
            branch_path.split("/")[-1].strip(),
        ])
        label_map = {
            "Diary": "Diary",
            "PastRecord": "PastRecord",
            "SongryeonChat": "SongryeonChat",
            "GeminiChat": "GeminiChat",
        }
        try:
            with self.neo4j_driver.session() as session:
                for address in source_addresses or []:
                    source_type, source_id, day_label, _ = self._source_address_parts(address)
                    target_label = label_map.get(source_type, "PastRecord")
                    target_id = str(source_id or day_label or "").strip()
                    if not target_id:
                        continue

                    rows = []
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", target_id):
                        if target_label == "PastRecord":
                            rows = session.run(
                                """
                                MATCH (r:PastRecord)
                                WHERE coalesce(r.date, '') STARTS WITH $target_id
                                RETURN labels(r) AS labels, coalesce(r.date, '') AS date,
                                       coalesce(r.role, '') AS role, coalesce(r.content, '') AS content
                                ORDER BY coalesce(r.date, '') ASC
                                LIMIT 6
                                """,
                                target_id=target_id,
                            ).data()
                        else:
                            rows = session.run(
                                f"""
                                MATCH (r:PastRecord:{target_label})
                                WHERE coalesce(r.date, '') STARTS WITH $target_id
                                RETURN labels(r) AS labels, coalesce(r.date, '') AS date,
                                       coalesce(r.role, '') AS role, coalesce(r.content, '') AS content
                                ORDER BY coalesce(r.date, '') ASC
                                LIMIT 6
                                """,
                                target_id=target_id,
                            ).data()
                    else:
                        rows = session.run(
                            """
                            MATCH (r:PastRecord)
                            WHERE elementId(r) = $target_id OR coalesce(r.id, '') = $target_id
                            RETURN labels(r) AS labels, coalesce(r.date, '') AS date,
                                   coalesce(r.role, '') AS role, coalesce(r.content, '') AS content
                            LIMIT 4
                            """,
                            target_id=target_id,
                        ).data()

                    for row in rows:
                        labels = set(row.get("labels") or [])
                        if root_entity.startswith("Person:") and "SongryeonChat" in labels and "Diary" not in labels:
                            continue
                        content = str(row.get("content") or "").strip()
                        if not content:
                            continue
                        candidates = self._split_raw_fact_candidates(content)
                        if not candidates:
                            candidates = [self._trim_text(content, 280)]
                        for candidate in candidates:
                            lowered = candidate.lower()
                            if topic_markers and not any(str(marker or "").strip().lower() in lowered for marker in topic_markers if str(marker or "").strip()):
                                continue
                            fragments.append({
                                "source_address": address,
                                "source_type": next(iter(labels), target_label) if labels else target_label,
                                "source_id": target_id,
                                "date": str(row.get("date") or "").strip(),
                                "fact_text": candidate,
                                "source_excerpt": self._trim_text(content, 900),
                            })
        except Exception:
            return []

        deduped = []
        seen = set()
        for fragment in fragments:
            signature = (str(fragment.get("source_address") or "").strip(), str(fragment.get("fact_text") or "").strip())
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(fragment)
        return deduped[:12]

    @classmethod
    def _dream_row_fact_candidates(cls, row):
        if not isinstance(row, dict):
            return []
        process_id = str(row.get("process_id") or "").strip()
        dream_id = str(row.get("dream_id") or "").strip()
        date_label = str(row.get("date") or "").strip()
        items = []

        def append_candidate(source_address, fact_text, source_excerpt=""):
            normalized_text = cls._trim_text(fact_text, 320)
            if not normalized_text:
                return
            items.append({
                "source_address": source_address,
                "fact_text": normalized_text,
                "source_excerpt": cls._trim_text(source_excerpt or fact_text, 900),
                "dream_id": dream_id,
                "date_label": date_label,
            })

        if dream_id:
            dream_excerpt = " ".join(str(row.get(key) or "").strip() for key in ("input", "answer", "turn_summary") if str(row.get(key) or "").strip())
            append_candidate(f"Dream:{dream_id}", row.get("turn_summary") or row.get("answer") or row.get("input"), dream_excerpt)
            append_candidate(f"Dream:{dream_id}", row.get("input"), dream_excerpt)
            append_candidate(f"Dream:{dream_id}", row.get("answer"), dream_excerpt)

        if process_id:
            process_summary = cls._normalize_phase_payload(row.get("process_summary"))
            if isinstance(process_summary, dict):
                append_candidate(
                    f"TurnProcess:{process_id}",
                    process_summary.get("summary") or process_summary.get("final_answer_brief") or json.dumps(process_summary, ensure_ascii=False),
                    json.dumps(process_summary, ensure_ascii=False),
                )

        for snapshot in row.get("phase_snapshots") or []:
            if not isinstance(snapshot, dict):
                continue
            phase_name = str(snapshot.get("phase_name") or "").strip() or "unknown_phase"
            source_address = f"Phase:{process_id}:{phase_name}" if process_id else f"Phase:{phase_name}"
            append_candidate(
                source_address,
                snapshot.get("summary") or snapshot.get("summary_json"),
                snapshot.get("summary_json") or snapshot.get("summary"),
            )

        deduped = []
        seen = set()
        for item in items:
            signature = (item["source_address"], item["fact_text"])
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(item)
        return deduped[:8]

    @classmethod
    def _build_branch_wiki_bundle(
        cls,
        weaver,
        branch_path,
        related_topics,
        evidence_addresses,
        dream_rows,
        supporting_dream_ids,
        coverage_map,
        fact_leaf_candidates=None,
    ):
        normalized_branch = cls._normalize_branch_path_to_existing_roots(branch_path)
        root_entity, _, _ = cls._branch_root_info(normalized_branch)
        topic_slug = str((related_topics or [cls._topic_slug_from_branch_path(normalized_branch)])[0] or "").strip() or "field_repair"

        branch_coverage = [
            item for item in (coverage_map or [])
            if isinstance(item, dict) and (
                str(item.get("branch_hint") or "").strip() == normalized_branch
                or str(item.get("topic_slug") or "").strip() == topic_slug
            )
        ]
        branch_source_addresses = weaver._collect_branch_source_addresses(
            branch_path,
            evidence_addresses,
            dream_rows,
        )
        raw_source_fragments = weaver._load_raw_source_fragments_for_branch(
            branch_path,
            branch_source_addresses,
            topic_slug,
        )
        branch_pressure = weaver._measure_branch_topic_pressure(
            branch_path=normalized_branch,
            topic_slug=topic_slug,
            dream_rows=dream_rows,
            branch_coverage=branch_coverage,
            supporting_dream_ids=supporting_dream_ids,
            source_addresses=branch_source_addresses,
            raw_source_fragments=raw_source_fragments,
        )

        time_bucket_map = {}
        fact_leaves = []
        fact_keys = []
        fact_texts = []
        seen_fact_signatures = set()

        def append_fact_candidate(
            *,
            source_address,
            source_type,
            source_id,
            fact_text,
            bucket_label,
            bucket_scope,
            confidence,
            support_weight,
            tags,
            local_supporting_dream_ids,
            source_excerpt="",
        ):
            normalized_text = cls._trim_text(str(fact_text or "").strip(), 320)
            normalized_excerpt = cls._trim_text(str(source_excerpt or fact_text or "").strip(), 900)
            normalized_source_address = str(source_address or "").strip()
            normalized_source_type = str(source_type or "").strip() or "unknown"
            normalized_source_id = str(source_id or normalized_source_address or len(fact_leaves) + 1).strip()
            normalized_bucket_label = str(bucket_label or "").strip() or "unknown"
            normalized_bucket_scope = str(bucket_scope or "").strip() or "unknown"
            if not normalized_text or not normalized_source_address:
                return
            bucket = cls._materialize_time_bucket(normalized_bucket_label, normalized_bucket_scope)
            signature = (
                topic_slug,
                normalized_source_address,
                normalized_text.lower(),
                bucket["bucket_key"],
            )
            if signature in seen_fact_signatures:
                return
            seen_fact_signatures.add(signature)
            time_bucket_map[bucket["bucket_key"]] = bucket
            fact_key = (
                f"fact_leaf::{cls._safe_slug_fragment(normalized_branch)}::"
                f"{cls._safe_slug_fragment(topic_slug)}::"
                f"{cls._safe_slug_fragment(normalized_source_id)}::{len(fact_leaves) + 1}"
            )
            fact = FactLeafItem(
                fact_key=fact_key,
                branch_path=normalized_branch,
                root_entity=root_entity,
                topic_slug=topic_slug,
                time_bucket_key=bucket["bucket_key"],
                source_address=normalized_source_address,
                source_type=normalized_source_type,
                source_id=normalized_source_id,
                fact_text=normalized_text,
                source_excerpt=normalized_excerpt,
                verification_status="pending",
                verification_reason="awaiting_phase11_verifier",
                confidence=float(confidence or 0.55),
                support_weight=round(float(support_weight or branch_pressure), 3),
                supporting_dream_ids=cls._dedupe_keep_order(list(local_supporting_dream_ids or []) + list(supporting_dream_ids or []))[:12],
                tags=cls._dedupe_keep_order(list(tags or []) + [topic_slug]),
            ).model_dump()
            fact_leaves.append(fact)
            fact_keys.append(fact_key)
            fact_texts.append(normalized_text)

        branch_topic_slugs = set(
            cls._dedupe_keep_order(
                [topic_slug]
                + [str(item or "").strip() for item in (related_topics or []) if str(item or "").strip()]
            )
        )

        for candidate in fact_leaf_candidates or []:
            if not isinstance(candidate, dict):
                continue
            candidate_topic_slug = str(candidate.get("topic_slug") or "").strip()
            if branch_topic_slugs and candidate_topic_slug and candidate_topic_slug not in branch_topic_slugs:
                continue
            source_address = str(candidate.get("source_address") or "").strip()
            source_type, source_id, inferred_day, inferred_scope = cls._source_address_parts(source_address)
            if root_entity.startswith("Person:") and source_type == "SongryeonChat":
                continue
            bucket_label = (
                str(candidate.get("inferred_time_bucket") or "").strip()
                or inferred_day
                or "unknown"
            )
            bucket_scope = inferred_scope if inferred_day else ("day" if re.match(r"^\d{4}-\d{2}-\d{2}$", bucket_label) else "unknown")
            append_fact_candidate(
                source_address=source_address,
                source_type=str(candidate.get("source_kind") or "").strip() or source_type,
                source_id=source_id or source_address,
                fact_text=candidate.get("fact_text"),
                bucket_label=bucket_label,
                bucket_scope=bucket_scope,
                confidence=0.69,
                support_weight=candidate.get("support_weight", branch_pressure),
                tags=[normalized_branch.split("/")[-1], "phase_8b_candidate"],
                local_supporting_dream_ids=[],
                source_excerpt=candidate.get("source_excerpt") or candidate.get("fact_text"),
            )

        for row in dream_rows or []:
            for candidate in cls._dream_row_fact_candidates(row):
                source_type, source_id, inferred_day, inferred_scope = cls._source_address_parts(candidate.get("source_address"))
                bucket_label = inferred_day or str(candidate.get("date_label") or "").strip() or "unknown"
                bucket_scope = inferred_scope if inferred_day else ("day" if re.match(r"^\d{4}-\d{2}-\d{2}$", bucket_label) else "unknown")
                append_fact_candidate(
                    source_address=str(candidate.get("source_address") or "").strip(),
                    source_type=source_type,
                    source_id=source_id or str(candidate.get("source_address") or "").strip(),
                    fact_text=str(candidate.get("fact_text") or "").strip(),
                    bucket_label=bucket_label,
                    bucket_scope=bucket_scope,
                    confidence=0.58,
                    support_weight=branch_pressure,
                    tags=[normalized_branch.split("/")[-1], source_type],
                    local_supporting_dream_ids=[candidate.get("dream_id")],
                    source_excerpt=candidate.get("source_excerpt") or candidate.get("fact_text"),
                )

        for raw_index, fragment in enumerate(raw_source_fragments[:8], start=1):
            source_address = str(fragment.get("source_address") or "").strip()
            source_type = str(fragment.get("source_type") or "").strip() or "PastRecord"
            source_id = str(fragment.get("source_id") or "").strip() or source_address or f"raw_{raw_index}"
            bucket_label = str(fragment.get("date") or "").strip() or "unknown"
            bucket_scope = "day" if re.match(r"^\d{4}-\d{2}-\d{2}$", bucket_label) else "unknown"
            append_fact_candidate(
                source_address=source_address,
                source_type=source_type,
                source_id=f"raw::{source_id}::{raw_index}",
                fact_text=cls._trim_text(str(fragment.get("fact_text") or "").strip(), 320),
                bucket_label=bucket_label,
                bucket_scope=bucket_scope,
                confidence=0.74,
                support_weight=branch_pressure,
                tags=["raw_source", source_type],
                local_supporting_dream_ids=[],
                source_excerpt=fragment.get("source_excerpt") or fragment.get("fact_text"),
            )

        fact_leaves = fact_leaves[:12]
        fact_leaves, u_cluster_metrics = apply_fact_scoring(fact_leaves)
        fact_keys = [item["fact_key"] for item in fact_leaves]
        fact_texts = [item["fact_text"] for item in fact_leaves]
        time_bucket_keys = list(time_bucket_map.keys())[:12]
        time_buckets = list(time_bucket_map.values())[:12]
        pressure_hints = []

        cluster_key = f"concept_cluster::{cls._safe_slug_fragment(normalized_branch)}::{cls._safe_slug_fragment(topic_slug)}"
        cluster_title = f"{cls._branch_title_ko(normalized_branch) or normalized_branch} / {cls._topic_label_ko(topic_slug) or topic_slug}"
        u_synthesis_statement = cls._trim_text(str(u_cluster_metrics.get("synthesis_statement") or ""), 420)
        cluster_summary = " ".join(
            part for part in [
                f"{cluster_title} common pattern.",
                u_synthesis_statement,
                cls._trim_text(" / ".join(fact_texts[:3]), 360),
            ] if part
        ).strip()
        concept_clusters = []
        u_cluster_purity = float(u_cluster_metrics.get("u_cluster_purity", 0.0) or 0.0)
        u_synthesis_score = float(u_cluster_metrics.get("u_synthesis_score", 0.0) or 0.0)
        cluster_is_promotable = bool(fact_keys) and u_cluster_purity >= 0.32 and u_synthesis_score >= 0.20
        if cluster_is_promotable:
            concept_clusters.append(
                ConceptClusterItem(
                    cluster_key=cluster_key,
                    branch_path=normalized_branch,
                    root_entity=root_entity,
                    topic_slug=topic_slug,
                    title=cluster_title,
                    summary=cluster_summary or f"{cluster_title} cluster",
                    fact_keys=fact_keys[:12],
                    time_bucket_keys=time_bucket_keys[:12],
                    support_weight=round((branch_pressure * 0.55) + (u_synthesis_score * 0.45), 3),
                    u_cluster_purity=round(u_cluster_purity, 4),
                    u_coherence_score=round(float(u_cluster_metrics.get("u_coherence_score", 0.0) or 0.0), 4),
                    u_tension_score=round(float(u_cluster_metrics.get("u_tension_score", 0.0) or 0.0), 4),
                    u_synthesis_score=round(u_synthesis_score, 4),
                    thesis_fact_keys=list(u_cluster_metrics.get("thesis_fact_keys", []) or [])[:6],
                    antithesis_fact_keys=list(u_cluster_metrics.get("antithesis_fact_keys", []) or [])[:6],
                    synthesis_statement=u_synthesis_statement,
                    inverse_relation_updates=list(u_cluster_metrics.get("inverse_relation_updates", []) or [])[:8],
                    tags=cls._dedupe_keep_order([topic_slug, normalized_branch.split("/")[1] if "/" in normalized_branch else normalized_branch]),
                ).model_dump()
            )
        elif fact_keys:
            pressure_hints.append(
                f"{normalized_branch}::{topic_slug}::u_cluster_blocked::purity={u_cluster_purity:.2f}::synthesis={u_synthesis_score:.2f}"
            )

        synthesis_bridges = []
        if concept_clusters:
            fact_bridge_hint = cls._trim_text(" / ".join(fact_texts[:3]), 220)
            bridge_thought = (
                u_synthesis_statement
                or (
                    f"{cluster_title} and {fact_bridge_hint} appear to share a verified branch structure. "
                    f"{normalized_branch} can treat this as a factual bridge node."
                )
            )
            synthesis_bridges.append(
                SynthesisBridgeThoughtItem(
                    bridge_key=f"synthesis_bridge::{cls._safe_slug_fragment(normalized_branch)}::{cls._safe_slug_fragment(topic_slug)}",
                    branch_path=normalized_branch,
                    root_entity=root_entity,
                    topic_slug=topic_slug,
                    cluster_key=cluster_key,
                    title=f"{cluster_title} bridge",
                    bridge_thought=cls._trim_text(bridge_thought, 260),
                    supporting_fact_keys=fact_keys[:8],
                    support_weight=round((branch_pressure * 0.5) + (u_synthesis_score * 0.5), 3),
                    u_synthesis_score=round(u_synthesis_score, 4),
                ).model_dump()
            )

        difference_notes = []
        u_tension_score = float(u_cluster_metrics.get("u_tension_score", 0.0) or 0.0)
        antithesis_fact_keys = list(u_cluster_metrics.get("antithesis_fact_keys", []) or [])
        if (len(time_bucket_keys) > 1 or u_tension_score >= 0.25) and fact_keys:
            difference_notes.append(
                DifferenceNoteItem(
                    note_key=f"difference_note::{cls._safe_slug_fragment(normalized_branch)}::{cls._safe_slug_fragment(topic_slug)}",
                    branch_path=normalized_branch,
                    root_entity=root_entity,
                    topic_slug=topic_slug,
                    title=f"{cluster_title} time contrast",
                    summary=cls._trim_text(
                        f"{cluster_title} has U-tension {u_tension_score:.2f} across {len(time_bucket_keys)} time buckets; compare thesis facts with antithesis facts before higher promotion.",
                        240,
                    ),
                    compared_fact_keys=cls._dedupe_keep_order(antithesis_fact_keys + fact_keys)[:12],
                    compared_time_bucket_keys=time_bucket_keys[:12],
                    contrast_axis="time",
                    support_weight=round(branch_pressure, 3),
                    u_tension_score=round(u_tension_score, 4),
                ).model_dump()
            )
        elif len(cls._dedupe_keep_order(related_topics)) > 1 and fact_keys:
            difference_notes.append(
                DifferenceNoteItem(
                    note_key=f"difference_note::{cls._safe_slug_fragment(normalized_branch)}::multi_topic",
                    branch_path=normalized_branch,
                    root_entity=root_entity,
                    topic_slug=topic_slug,
                    title=f"{cluster_title} topic contrast",
                    summary=cls._trim_text(
                        f"{normalized_branch} currently concentrates multiple related topics, so the next nightly pass should compare them before splitting a new child branch.",
                        240,
                    ),
                    compared_fact_keys=fact_keys[:12],
                    compared_time_bucket_keys=time_bucket_keys[:12],
                    contrast_axis="topic",
                    support_weight=round(branch_pressure, 3),
                    u_tension_score=round(u_tension_score, 4),
                ).model_dump()
            )

        child_branch_proposals = []
        proposal_triggers = []
        if len(time_bucket_keys) > 1:
            proposal_triggers.append("time_contrast")
        if len(cls._dedupe_keep_order(related_topics)) > 1:
            proposal_triggers.append("topic_overlap")
        if len(raw_source_fragments) >= 2:
            proposal_triggers.append("raw_source_density")
        if len(fact_keys) >= 3:
            proposal_triggers.append("fact_density")

        should_propose_child_branch = (
            bool(concept_clusters)
            and len(fact_keys) >= 2
            and branch_pressure >= 0.72
            and bool(proposal_triggers)
        )
        if should_propose_child_branch:
            child_suffix = (
                "time_axis"
                if "time_contrast" in proposal_triggers
                else ("topic_axis" if "topic_overlap" in proposal_triggers else f"focus_{cls._safe_slug_fragment(topic_slug)}")
            )
            proposed_branch_path = f"{normalized_branch}/{child_suffix}"
            proposal_reason = cls._trim_text(
                (
                    f"{normalized_branch} has branch pressure {branch_pressure:.2f} around {cls._topic_label_ko(topic_slug) or topic_slug}. "
                    f"Concept clustering is stable enough to justify a child branch for more focused nightly growth."
                ),
                280,
            )
            proposal = ChildBranchProposalItem(
                proposal_key=f"child_branch_proposal::{cls._safe_slug_fragment(normalized_branch)}::{cls._safe_slug_fragment(child_suffix)}",
                parent_branch_path=normalized_branch,
                proposed_branch_path=proposed_branch_path,
                root_entity=root_entity,
                topic_slug=topic_slug,
                proposal_reason=proposal_reason,
                pressure_score=round(branch_pressure, 3),
                evidence_start_points=cls._dedupe_keep_order(branch_source_addresses + evidence_addresses)[:10],
                trigger_notes=proposal_triggers[:6],
                status="proposed",
            ).model_dump()
            child_branch_proposals.append(proposal)
            pressure_hints.append(
                f"{normalized_branch}::{topic_slug}::branch_pressure={branch_pressure:.2f}::proposed={proposed_branch_path}"
            )
        elif branch_pressure >= 0.72:
            pressure_hints.append(
                f"{normalized_branch}::{topic_slug}::branch_pressure={branch_pressure:.2f}::consider_child_branch"
            )

        return {
            "time_buckets": time_buckets,
            "fact_leaves": fact_leaves,
            "concept_clusters": concept_clusters,
            "synthesis_bridges": synthesis_bridges,
            "difference_notes": difference_notes,
            "pressure_hints": pressure_hints,
            "child_branch_proposals": child_branch_proposals,
        }

    @classmethod
    def _fact_support_overlap_score(cls, source_excerpt, fact_text):
        excerpt = unicodedata.normalize("NFKC", str(source_excerpt or "").lower())
        fact = unicodedata.normalize("NFKC", str(fact_text or "").lower())
        if not excerpt or not fact:
            return 0.0
        if fact in excerpt:
            return 1.0
        fact_tokens = set(re.findall(r"[0-9a-zA-Z가-힣:-]{2,}", fact))
        excerpt_tokens = set(re.findall(r"[0-9a-zA-Z가-힣:-]{2,}", excerpt))
        if not fact_tokens or not excerpt_tokens:
            return 0.0
        return min(1.0, len(fact_tokens & excerpt_tokens) / max(1, len(fact_tokens)))

    @classmethod
    def _fallback_fact_verification(cls, fact):
        fact_key = str(fact.get("fact_key") or "").strip()
        fact_text = str(fact.get("fact_text") or "").strip()
        source_excerpt = str(fact.get("source_excerpt") or "").strip()
        overlap = cls._fact_support_overlap_score(source_excerpt, fact_text)
        if overlap >= 0.62:
            return {
                "fact_key": fact_key,
                "verdict": "supported",
                "reason": f"deterministic overlap {overlap:.2f}",
                "confidence": min(0.92, max(0.68, overlap)),
            }
        if overlap >= 0.25:
            return {
                "fact_key": fact_key,
                "verdict": "too_weak",
                "reason": f"source/fact overlap is weak ({overlap:.2f}); needs human/LLM review",
                "confidence": overlap,
            }
        return {
            "fact_key": fact_key,
            "verdict": "unsupported",
            "reason": "fact text is not visibly grounded in source excerpt",
            "confidence": overlap,
        }

    def _verify_fact_leaf_batch_with_llm(self, branch_path, facts):
        candidates = []
        for fact in facts or []:
            if not isinstance(fact, dict):
                continue
            fact_key = str(fact.get("fact_key") or "").strip()
            fact_text = str(fact.get("fact_text") or "").strip()
            source_excerpt = str(fact.get("source_excerpt") or "").strip()
            source_address = str(fact.get("source_address") or "").strip()
            if not fact_key or not fact_text:
                continue
            candidates.append({
                "fact_key": fact_key,
                "source_address": source_address,
                "fact_text": self._trim_text(fact_text, 320),
                "source_excerpt": self._trim_text(source_excerpt or fact_text, 900),
            })
        if not candidates:
            return {}

        fallback = {
            item["fact_key"]: self._fallback_fact_verification(item)
            for item in candidates
        }
        prompt = (
            "You are Phase11FactVerifier, a strict evidence censor for a graph wiki.\n"
            "Task: judge whether each FactLeaf is directly supported by its source_excerpt.\n"
            "Rules:\n"
            "- verdict=supported only when the fact can be read from the excerpt without extra inference.\n"
            "- verdict=too_weak when it is plausible but the excerpt is too thin, ambiguous, or only indirectly related.\n"
            "- verdict=unsupported when the excerpt does not support the fact or the fact adds causation/identity not present.\n"
            "- Keep reasons short. Do not rewrite the facts.\n\n"
            f"Branch path: {branch_path}\n"
            "Candidates JSON:\n"
            + json.dumps(candidates[:10], ensure_ascii=False, indent=2)
        )
        try:
            response = ollama.chat(
                model=self.action_model,
                messages=[{"role": "user", "content": prompt}],
                format=FactLeafVerificationBatchSchema.model_json_schema(),
            )
            data = self._safe_json_load(response["message"]["content"]) or {}
        except Exception:
            return fallback

        verified = {}
        for item in data.get("verifications", []) or []:
            if not isinstance(item, dict):
                continue
            fact_key = str(item.get("fact_key") or "").strip()
            if not fact_key:
                continue
            verdict = str(item.get("verdict") or "too_weak").strip()
            if verdict not in {"supported", "too_weak", "unsupported"}:
                verdict = "too_weak"
            try:
                confidence = float(item.get("confidence", 0.0) or 0.0)
            except Exception:
                confidence = 0.0
            verified[fact_key] = {
                "fact_key": fact_key,
                "verdict": verdict,
                "reason": self._trim_text(str(item.get("reason") or "").strip(), 220),
                "confidence": round(max(0.0, min(1.0, confidence)), 3),
            }
        for fact_key, fallback_item in fallback.items():
            verified.setdefault(fact_key, fallback_item)
        return verified

    def _audit_fact_leaf_pairs(self, branch_path, fact_leaves):
        structurally_valid = []
        structural_reasons = {}
        for fact in fact_leaves or []:
            if not isinstance(fact, dict):
                continue
            fact_key = str(fact.get("fact_key") or "").strip()
            source_address = str(fact.get("source_address") or "").strip()
            source_type = str(fact.get("source_type") or "").strip()
            fact_text = str(fact.get("fact_text") or "").strip()
            reasons = []
            if not fact_key:
                reasons.append("fact_key missing")
            if not source_address:
                reasons.append("source_address missing")
            if not fact_text or len(fact_text) < 8:
                reasons.append("fact_text too short")
            if source_address and source_type == "unknown" and not any(source_address.startswith(prefix) for prefix in ("Dream:", "TurnProcess:", "Phase:", "PastRecord:", "Diary|", "SongryeonChat|", "GeminiChat|")):
                reasons.append("source type is not traceable")
            if "u_purity_score" in fact and float(fact.get("u_purity_score", 0.0) or 0.0) < 0.28:
                reasons.append(f"u_purity_score too low ({float(fact.get('u_purity_score', 0.0) or 0.0):.2f})")
            if "u_hallucination_risk" in fact and float(fact.get("u_hallucination_risk", 0.0) or 0.0) >= 0.82:
                reasons.append(f"u_hallucination_risk too high ({float(fact.get('u_hallucination_risk', 0.0) or 0.0):.2f})")
            structural_reasons[id(fact)] = reasons
            if not reasons:
                structurally_valid.append(fact)

        verification_map = self._verify_fact_leaf_batch_with_llm(branch_path, structurally_valid)
        approved = []
        audits = []
        source_fact_pairs = []
        for fact in fact_leaves or []:
            if not isinstance(fact, dict):
                continue
            fact_key = str(fact.get("fact_key") or "").strip()
            source_address = str(fact.get("source_address") or "").strip()
            source_type = str(fact.get("source_type") or "").strip()
            source_id = str(fact.get("source_id") or "").strip()
            fact_text = str(fact.get("fact_text") or "").strip()
            rejection_reasons = list(structural_reasons.get(id(fact), []) or [])
            verification = verification_map.get(fact_key) or self._fallback_fact_verification(fact)
            if not rejection_reasons:
                if str(verification.get("verdict") or "") != "supported":
                    rejection_reasons.append(
                        f"verifier_{verification.get('verdict')}: {verification.get('reason') or 'not directly supported'}"
                    )
            verdict = "rejected" if rejection_reasons else "approved"
            source_pair_key = f"{source_address}::{self._safe_slug_fragment(fact_text[:80])}"
            pair_key = f"source_fact_pair::{self._safe_slug_fragment(fact_key or source_pair_key)}"
            audit_key = f"fact_leaf_audit::{self._safe_slug_fragment(fact_key or source_pair_key)}"
            source_excerpt = self._trim_text(str(fact.get("source_excerpt") or fact_text).strip(), 900)
            normalized_fact = dict(fact)
            normalized_fact["source_excerpt"] = source_excerpt
            normalized_fact["verification_status"] = verdict
            normalized_fact["verification_reason"] = "; ".join(rejection_reasons) or str(verification.get("reason") or "supported by source excerpt")
            verifier_confidence = float(verification.get("confidence", 0.0) or 0.0)
            if "u_purity_score" in fact:
                verifier_confidence = round((verifier_confidence * 0.65) + (float(fact.get("u_purity_score", 0.0) or 0.0) * 0.35), 3)
            source_fact_pairs.append(
                SourceFactPairItem(
                    pair_key=pair_key,
                    fact_key=fact_key,
                    branch_path=str(fact.get("branch_path") or branch_path or "").strip(),
                    source_address=source_address,
                    source_type=source_type,
                    source_id=source_id,
                    fact_text=self._trim_text(fact_text, 320),
                    source_excerpt=source_excerpt,
                    pair_status=verdict,
                    verifier_name="phase11_llm_fact_pair_guard",
                    verifier_confidence=verifier_confidence,
                    mismatch_reason="; ".join(rejection_reasons),
                ).model_dump()
            )
            audits.append(
                FactLeafAuditItem(
                    audit_key=audit_key,
                    fact_key=fact_key,
                    branch_path=str(fact.get("branch_path") or branch_path or "").strip(),
                    source_address=source_address,
                    source_type=source_type,
                    source_id=source_id,
                    fact_text=self._trim_text(fact_text, 320),
                    verdict=verdict,
                    rejection_reason="; ".join(rejection_reasons),
                    source_pair_key=source_pair_key,
                ).model_dump()
            )
            if verdict == "approved":
                approved.append(normalized_fact)
        return approved, audits, source_fact_pairs

    def _scan_root_graph_context(self):
        return rem_governor_department._scan_root_graph_context(self)

    def _build_governor_root_profiles(self, governor, root_context):
        return rem_governor_department._build_governor_root_profiles(self, governor, root_context)

    def _build_governor_root_inventory(self, root_context):
        return rem_governor_department._build_governor_root_inventory(self, root_context)

    def _root_entity_from_asset_scope(self, branch_path="", root_scope=""):
        return rem_governor_department._root_entity_from_asset_scope(self, branch_path, root_scope)

    def _build_governor_policy_inventory(self, state: MidnightState, rem_governor=None):
        return rem_governor_department._build_governor_policy_inventory(self, state, rem_governor)

    @staticmethod
    def _looks_like_source_address(address):
        text = str(address or "").strip()
        if not text:
            return False
        if text.startswith(("web:", "Dream:", "TurnProcess:", "Phase:", "Person:", "CoreEgo:")):
            return True
        if "|" in text:
            left = text.split("|", 1)[0].strip()
            return left in {
                "Diary",
                "SongryeonChat",
                "GeminiChat",
                "PastRecord",
            }
        return False

    def _apply_governor_root_profiles_to_roots(self, session, rem_governor):
        return rem_governor_department._apply_governor_root_profiles_to_roots(self, session, rem_governor)

    def _apply_governor_root_state_to_roots(self, session, rem_governor):
        return rem_governor_department._apply_governor_root_state_to_roots(self, session, rem_governor)

    def _default_rem_governor_state(self):
        return rem_governor_department._default_rem_governor_state(self)

    def _default_strategy_council_state(self, rem_governor=None):
        return strategy_council_department._default_strategy_council_state(self, rem_governor)

    def _load_existing_strategy_council_state(self, strategy_key="strategy_council_v1"):
        return strategy_council_department._load_existing_strategy_council_state(self, strategy_key)

    def _collect_strategy_evidence_points(self, dream_rows):
        return strategy_council_department._collect_strategy_evidence_points(self, dream_rows)

    @staticmethod
    def _strategy_attention_tokens(text):
        return strategy_council_department._strategy_attention_tokens(text)

    @classmethod
    def _strategy_lexical_overlap_score(cls, query_text, candidate_text):
        return strategy_council_department._strategy_lexical_overlap_score(cls, query_text, candidate_text)

    @staticmethod
    def _strategy_cosine_similarity(vec1, vec2):
        return strategy_council_department._strategy_cosine_similarity(vec1, vec2)

    @staticmethod
    def _strategy_embed_text(text):
        return strategy_council_department._strategy_embed_text(text)

    def _strategy_digest_attention_text(self, digest):
        return strategy_council_department._strategy_digest_attention_text(self, digest)

    def _strategy_cluster_attention_text(self, cluster):
        return strategy_council_department._strategy_cluster_attention_text(self, cluster)

    @staticmethod
    def _dedupe_attention_shortlist(items):
        return strategy_council_department._dedupe_attention_shortlist(items)

    def _build_strategy_attention_shortlist(
        self,
        *,
        existing_branch_digests,
        existing_concept_clusters,
        normalized_text,
        remembered_self_summary,
        goal_tree,
        goal_gaps,
        branch_health_map,
        required_branches,
    ):
        return strategy_council_department._build_strategy_attention_shortlist(
            self,
            existing_branch_digests=existing_branch_digests,
            existing_concept_clusters=existing_concept_clusters,
            normalized_text=normalized_text,
            remembered_self_summary=remembered_self_summary,
            goal_tree=goal_tree,
            goal_gaps=goal_gaps,
            branch_health_map=branch_health_map,
            required_branches=required_branches,
        )

    def _build_strategy_council_state(self, state: MidnightState):
        return strategy_council_department._build_strategy_council_state(self, state)

    @staticmethod
    def _dedupe_goal_tree(items):
        return strategy_council_department._dedupe_goal_tree(items)

    @staticmethod
    def _dedupe_goal_gaps(items):
        return strategy_council_department._dedupe_goal_gaps(items)

    @staticmethod
    def _dedupe_scope_items(items):
        return strategy_council_department._dedupe_scope_items(items)

    @staticmethod
    def _dedupe_child_branch_proposals(items):
        return strategy_council_department._dedupe_child_branch_proposals(items)

    def _load_existing_rem_governor_state(self, governor_key="rem_governor_v1"):
        return rem_governor_department._load_existing_rem_governor_state(self, governor_key)

    def _load_existing_branch_digests(self, limit=16):
        if not self.neo4j_driver:
            return []
        try:
            with self.neo4j_driver.session() as session:
                rows = session.run(
                    """
                    MATCH (bd:BranchDigest)
                    WHERE coalesce(bd.status, 'active') = 'active'
                    RETURN bd
                    ORDER BY coalesce(bd.created_at, 0) DESC, coalesce(bd.updated_at, 0) DESC
                    LIMIT $limit
                    """,
                    limit=int(limit),
                )
                return [dict(record["bd"]) for record in rows if record.get("bd")]
        except Exception:
            return []

    def _load_existing_concept_clusters(self, limit=24):
        if not self.neo4j_driver:
            return []
        if not self._neo4j_label_exists("ConceptCluster"):
            return []
        try:
            with self.neo4j_driver.session() as session:
                rows = session.run(
                    """
                    MATCH (cc:ConceptCluster)
                    RETURN cc
                    ORDER BY coalesce(cc.created_at, 0) DESC
                    LIMIT $limit
                    """,
                    limit=int(limit),
                )
                return [dict(record["cc"]) for record in rows if record.get("cc")]
        except Exception:
            return []

    def _build_rem_governor_state(self, dream_rows):
        return rem_governor_department._build_rem_governor_state(self, dream_rows)

    def _refresh_rem_governor_state(self, state: MidnightState):
        return rem_governor_department._refresh_rem_governor_state(self, state)

    def _build_rem_plan_from_rows(self, dream_rows, rem_governor=None, branch_architect=None, architect_handoff_report=None, strategy_council=None):
        return rem_plan_department._build_rem_plan_from_rows(
            self,
            dream_rows,
            rem_governor=rem_governor,
            branch_architect=branch_architect,
            architect_handoff_report=architect_handoff_report,
            strategy_council=strategy_council,
        )

    def _build_phase7_coverage_map(self, phase_7_audit, rem_plan):
        audit = phase_7_audit if isinstance(phase_7_audit, dict) else {}
        topics = audit.get("classified_topics", []) if isinstance(audit.get("classified_topics"), list) else []
        governor = rem_plan if isinstance(rem_plan, dict) else {}
        create_targets = set(str(item or "").strip() for item in governor.get("create_targets", []) or [])
        update_targets = set(str(item or "").strip() for item in governor.get("update_targets", []) or [])
        branch_paths = self._plan_branch_paths(governor)
        coverage_map = []
        seen = set()

        for topic in topics:
            if not isinstance(topic, dict):
                continue
            topic_slug = str(topic.get("topic_slug") or "").strip()
            if not topic_slug or topic_slug in seen:
                continue
            seen.add(topic_slug)
            branch_hint = next((path for path in branch_paths if topic_slug in path), "")
            preferred_action = "update"
            if branch_hint and branch_hint in create_targets:
                preferred_action = "create"
            elif branch_hint and branch_hint in update_targets:
                preferred_action = "update"
            elif topic_slug in {"field_repair", "tool_routing"}:
                preferred_action = "create"
            coverage_map.append({
                "topic_slug": topic_slug,
                "branch_hint": branch_hint,
                "preferred_action": preferred_action,
                "merged_from": [
                    str(topic.get("title") or "").strip(),
                    str(topic.get("parent_topic_slug") or "").strip(),
                ],
                "uncovered_risks": [
                    str(topic.get("gap_description") or "").strip(),
                ],
            })

        return coverage_map

    def _build_phase8_review_packet(self, state: MidnightState, p8b: dict):
        audit = state.get("phase_7_audit", {}) if isinstance(state.get("phase_7_audit"), dict) else {}
        topics = audit.get("classified_topics", []) if isinstance(audit.get("classified_topics"), list) else []
        pending_actions = state.get("pending_actions", []) if isinstance(state.get("pending_actions"), list) else []
        fact_leaf_candidates = p8b.get("fact_leaf_candidates", []) if isinstance(p8b, dict) and isinstance(p8b.get("fact_leaf_candidates"), list) else []

        unresolved_topics = [
            str(topic.get("topic_slug") or "").strip()
            for topic in topics
            if isinstance(topic, dict) and not topic.get("supply_sufficient") and str(topic.get("topic_slug") or "").strip()
        ]

        rejected_actions = []
        for action in pending_actions:
            if not isinstance(action, dict):
                continue
            tool = str(action.get("tool") or "").strip()
            keyword = str(action.get("keyword") or "").strip()
            if tool:
                rejected_actions.append(f"{tool}::{keyword}")

        carry_forward_addresses = [
            str(item.get("source_address") or "").strip()
            for item in fact_leaf_candidates
            if isinstance(item, dict) and str(item.get("source_address") or "").strip()
        ]

        reviewer_summary = str(p8b.get("response_to_phase_7") or p8b.get("proactive_suggestion") or "").strip()
        is_resolved = bool(p8b.get("is_resolved"))

        if is_resolved:
            review_target = "phase_9"
            objection_kind = "resolved"
            revision_requests = []
        elif rejected_actions:
            review_target = "phase_8a"
            objection_kind = "plan_revision"
            revision_requests = [
                reviewer_summary or "Revise the tool plan before the next field loop.",
                "Narrow the evidence scope or change the tool order before retrying.",
            ]
        else:
            review_target = "phase_7"
            objection_kind = "coverage_gap"
            revision_requests = [
                reviewer_summary or "Run the coverage audit again and check whether any topic remains empty.",
                "Check whether repeated gaps need a narrower branch or a different evidence target.",
            ]

        return Phase8ReviewPacket(
            review_target=review_target,
            objection_kind=objection_kind,
            reviewer_summary=reviewer_summary or ("resolved" if is_resolved else "Additional branch review is needed from evidence first."),
            target_topics=unresolved_topics[:12],
            rejected_actions=rejected_actions[:12],
            revision_requests=revision_requests[:8],
            carry_forward_addresses=carry_forward_addresses[:12],
        ).model_dump()

    def _build_branch_growth_bundle(self, state: MidnightState):
        rem_plan = state.get("rem_plan", {}) if isinstance(state.get("rem_plan"), dict) else {}
        coverage_map = state.get("phase_7_audit", {}).get("coverage_map", []) if isinstance(state.get("phase_7_audit"), dict) else []
        route_policies = state.get("route_policies", []) if isinstance(state.get("route_policies"), list) else []
        tool_doctrines = state.get("tool_doctrines", []) if isinstance(state.get("tool_doctrines"), list) else []
        tactical = state.get("tactical_doctrine", {}) if isinstance(state.get("tactical_doctrine"), dict) else {}
        dream_rows = state.get("dream_rows", []) if isinstance(state.get("dream_rows"), list) else []
        raw_field_memos = state.get("field_memos", []) if isinstance(state.get("field_memos"), list) else []
        field_memos = official_field_memos(raw_field_memos)
        memo_branch_counts = {}
        for memo in field_memos:
            if not isinstance(memo, dict):
                continue
            memo_branch = str(memo.get("branch_path") or "").strip()
            if memo_branch:
                memo_branch_counts[memo_branch] = memo_branch_counts.get(memo_branch, 0) + 1
        field_memo_branch_paths = [
            path for path, count in memo_branch_counts.items()
            if count >= 2 or path in set(rem_plan.get("selected_branch_paths", []) or [])
        ]
        branch_paths = self._dedupe_keep_order(self._plan_branch_paths(rem_plan) + field_memo_branch_paths[:8])
        priority_topics = self._plan_topics(rem_plan)
        evidence_addresses = self._plan_evidence_points(rem_plan)
        supporting_dream_ids = [str(row.get("dream_id") or "").strip() for row in dream_rows if isinstance(row, dict) and str(row.get("dream_id") or "").strip()]
        attached_policy_keys = [str(item.get("policy_key") or "").strip() for item in route_policies if isinstance(item, dict) and str(item.get("policy_key") or "").strip()]
        attached_doctrine_keys = [str(item.get("doctrine_key") or "").strip() for item in tool_doctrines if isinstance(item, dict) and str(item.get("doctrine_key") or "").strip()]
        normalized_tactics = self._normalize_tactical_cards(
            tactical,
            rem_plan,
            state.get("phase_7_audit", {}) if isinstance(state.get("phase_7_audit"), dict) else {},
        )
        time_buckets = []
        fact_leaves = []
        fact_leaf_audits = []
        source_fact_pairs = []
        concept_clusters = []
        synthesis_bridges = []
        difference_notes = []
        branch_pressure_hints = []
        child_branch_proposals = []
        rejected_branch_paths = []

        branch_digests = []
        for index, branch_path in enumerate(branch_paths, start=1):
            branch_topic_slug = self._topic_slug_from_branch_path(branch_path)
            related_topics = [topic for topic in priority_topics if topic and topic in branch_path]
            if not related_topics:
                related_topics = [
                    str(item.get("topic_slug") or "").strip()
                    for item in coverage_map
                    if isinstance(item, dict) and str(item.get("branch_hint") or "").strip() == branch_path and str(item.get("topic_slug") or "").strip()
                ]
            if not related_topics and branch_topic_slug:
                related_topics = [branch_topic_slug]
            if not related_topics:
                related_topics = priority_topics[:1]
            related_topic_labels = [self._topic_label_ko(topic) for topic in related_topics]
            attached_tactic_ids = self._dedupe_keep_order([
                str(item.get("tactic_key") or "").strip()
                for item in normalized_tactics
                if isinstance(item, dict) and (
                    self._normalize_branch_path_to_existing_roots(str(item.get("branch_scope") or "").strip()) == branch_path
                    or str(item.get("target_family") or "").strip() in related_topics
                )
            ])

            wiki_bundle = self._build_branch_wiki_bundle(
                self,
                branch_path=branch_path,
                related_topics=related_topics,
                evidence_addresses=evidence_addresses,
                dream_rows=dream_rows,
                supporting_dream_ids=supporting_dream_ids,
                coverage_map=coverage_map,
                fact_leaf_candidates=list(state.get("fact_leaf_candidates", []) or []) + field_memo_fact_leaf_candidates(field_memos, branch_path),
            )
            approved_facts, local_audits, local_source_fact_pairs = self._audit_fact_leaf_pairs(branch_path, wiki_bundle.get("fact_leaves", []) or [])
            fact_leaf_audits.extend(local_audits)
            source_fact_pairs.extend(local_source_fact_pairs)
            approved_fact_keys = {
                str(item.get("fact_key") or "").strip()
                for item in approved_facts
                if isinstance(item, dict) and str(item.get("fact_key") or "").strip()
            }
            if not approved_fact_keys:
                rejected_branch_paths.append(branch_path)
                branch_pressure_hints.append(f"{branch_path}::phase11_rejected::no_approved_fact_leaf")
                continue

            local_time_bucket_keys = {
                str(item.get("time_bucket_key") or "").strip()
                for item in approved_facts
                if isinstance(item, dict) and str(item.get("time_bucket_key") or "").strip()
            }
            local_clusters = []
            for cluster in wiki_bundle.get("concept_clusters", []) or []:
                if not isinstance(cluster, dict):
                    continue
                filtered_fact_keys = [
                    str(key or "").strip()
                    for key in (cluster.get("fact_keys", []) or [])
                    if str(key or "").strip() in approved_fact_keys
                ]
                if not filtered_fact_keys:
                    continue
                cluster = dict(cluster)
                cluster["fact_keys"] = filtered_fact_keys
                cluster["time_bucket_keys"] = [
                    str(key or "").strip()
                    for key in (cluster.get("time_bucket_keys", []) or [])
                    if str(key or "").strip() in local_time_bucket_keys
                ]
                local_clusters.append(cluster)
            local_cluster_keys = {
                str(item.get("cluster_key") or "").strip()
                for item in local_clusters
                if isinstance(item, dict) and str(item.get("cluster_key") or "").strip()
            }
            local_synthesis_bridges = []
            for bridge in wiki_bundle.get("synthesis_bridges", []) or []:
                if not isinstance(bridge, dict):
                    continue
                if str(bridge.get("cluster_key") or "").strip() not in local_cluster_keys:
                    continue
                bridge = dict(bridge)
                bridge["supporting_fact_keys"] = [
                    str(key or "").strip()
                    for key in (bridge.get("supporting_fact_keys", []) or [])
                    if str(key or "").strip() in approved_fact_keys
                ]
                if bridge["supporting_fact_keys"]:
                    local_synthesis_bridges.append(bridge)
            local_difference_notes = []
            for note in wiki_bundle.get("difference_notes", []) or []:
                if not isinstance(note, dict):
                    continue
                note = dict(note)
                note["compared_fact_keys"] = [
                    str(key or "").strip()
                    for key in (note.get("compared_fact_keys", []) or [])
                    if str(key or "").strip() in approved_fact_keys
                ]
                note["compared_time_bucket_keys"] = [
                    str(key or "").strip()
                    for key in (note.get("compared_time_bucket_keys", []) or [])
                    if str(key or "").strip() in local_time_bucket_keys
                ]
                if note["compared_fact_keys"]:
                    local_difference_notes.append(note)

            branch_findings = []
            for item in coverage_map:
                if not isinstance(item, dict):
                    continue
                topic_slug = str(item.get("topic_slug") or "").strip()
                if topic_slug and (topic_slug in branch_path or topic_slug in related_topics):
                    branch_findings.append(str(item.get("uncovered_risks", [""])[0] or "").strip())
            summary_parts = [
                f"`{branch_path}` was organized from {len(approved_facts)} verified FactLeaf items.",
                f"Related topics: {', '.join(label for label in related_topic_labels if label) or 'none'}.",
            ]
            if branch_findings:
                summary_parts.append(f"Remaining structural risks: {' / '.join(part for part in branch_findings if part)}.")
            summary_parts.append("This digest ties Dream and SecondDream evidence to verified source links.")
            branch_digests.append(
                BranchDigestItem(
                    digest_key=f"branch_digest::{index}::{branch_path}",
                    branch_path=branch_path,
                    title=self._branch_title_ko(branch_path) or branch_path,
                    summary=" ".join(summary_parts).strip(),
                    related_topics=related_topics[:6],
                    evidence_addresses=evidence_addresses[:12],
                    supporting_dream_ids=supporting_dream_ids[:12],
                    attached_tactic_ids=attached_tactic_ids[:12],
                    attached_policy_keys=attached_policy_keys[:12],
                    attached_doctrine_keys=attached_doctrine_keys[:12],
                ).model_dump()
            )
            time_buckets.extend([
                bucket for bucket in (wiki_bundle.get("time_buckets", []) or [])
                if isinstance(bucket, dict) and str(bucket.get("bucket_key") or "").strip() in local_time_bucket_keys
            ])
            fact_leaves.extend(approved_facts)
            concept_clusters.extend(local_clusters)
            synthesis_bridges.extend(local_synthesis_bridges)
            difference_notes.extend(local_difference_notes)
            branch_pressure_hints.extend(wiki_bundle.get("pressure_hints", []) or [])
            child_branch_proposals.extend(wiki_bundle.get("child_branch_proposals", []) or [])

        time_buckets = self._dedupe_dicts_by_key(time_buckets, "bucket_key")
        fact_leaves = self._dedupe_dicts_by_key(fact_leaves, "fact_key")
        fact_leaf_audits = self._dedupe_dicts_by_key(fact_leaf_audits, "audit_key")
        source_fact_pairs = self._dedupe_dicts_by_key(source_fact_pairs, "pair_key")
        concept_clusters = self._dedupe_dicts_by_key(concept_clusters, "cluster_key")
        synthesis_bridges = self._dedupe_dicts_by_key(synthesis_bridges, "bridge_key")
        difference_notes = self._dedupe_dicts_by_key(difference_notes, "note_key")
        branch_pressure_hints = self._dedupe_keep_order(branch_pressure_hints)
        child_branch_proposals = self._dedupe_child_branch_proposals(child_branch_proposals)

        consistency_findings = []
        if not branch_paths:
            consistency_findings.append("No branch paths were produced from tonight's initial plan.")
        if not branch_digests:
            consistency_findings.append("No BranchDigest was created; episode support summaries or branch summaries are still needed.")
        if branch_paths and len(branch_digests) < len(branch_paths):
            consistency_findings.append("Some planned branches still have no matching digest.")
        if coverage_map and not priority_topics:
            consistency_findings.append("Coverage map exists but priority topics are empty; initial organization is weak.")

        if not fact_leaves:
            consistency_findings.append("No FactLeaf was created; source-grounded fact candidates are insufficient.")
        if fact_leaves and not concept_clusters:
            consistency_findings.append("FactLeaf items exist but ConceptCluster is empty.")
        if branch_pressure_hints and not child_branch_proposals:
            consistency_findings.append("Branch pressure was detected but not converted into a structured child branch proposal.")

        rejected_branch_paths = self._dedupe_keep_order(rejected_branch_paths)
        approved_fact_leaf_count = len(fact_leaves)
        rejected_fact_leaf_count = len([
            item for item in fact_leaf_audits
            if isinstance(item, dict) and str(item.get("verdict") or "").strip() == "rejected"
        ])
        growth_status = "ready"
        if branch_paths and not approved_fact_leaf_count:
            growth_status = "blocked"
        elif rejected_branch_paths or rejected_fact_leaf_count:
            growth_status = "partial"
        rejection_reasons = []
        if rejected_branch_paths:
            rejection_reasons.append(
                "Phase11 rejected branch growth without approved FactLeaf: "
                + ", ".join(rejected_branch_paths[:8])
            )
        if branch_paths and not approved_fact_leaf_count:
            rejection_reasons.append("No branch was allowed to emit BranchDigest/ConceptCluster because no source-fact pair passed audit.")
        rem_plan_feedback = []
        governor_feedback = []
        architect_feedback = []
        if growth_status != "ready":
            rem_plan_feedback.append("REMPlan must provide concrete source addresses that Phase11 can resolve into source-fact pairs.")
            governor_feedback.append("Keep rejected branches as needs_growth/blocked_no_fact_leaf until verified FactLeaf exists.")
            architect_feedback.append("BranchArchitect should translate the next handoff into smaller branch scopes with explicit evidence_start_points.")

        report = BranchGrowthReportSchema(
            growth_scope="nightly_branch_growth",
            growth_status=growth_status,
            curated_branches=self._dedupe_keep_order([item.get("branch_path") for item in branch_digests if isinstance(item, dict)]),
            rejected_branch_paths=rejected_branch_paths,
            consistency_findings=consistency_findings or ["Branch structure is currently connected to nightly evidence in a stable way."],
            rejection_reasons=rejection_reasons,
            rem_plan_feedback=rem_plan_feedback,
            governor_feedback=governor_feedback,
            architect_feedback=architect_feedback,
            digest_count=len(branch_digests),
            branch_pressure_hints=branch_pressure_hints[:24],
            child_branch_proposal_count=len(child_branch_proposals),
            fact_leaf_count=len(fact_leaves),
            fact_audit_count=len(fact_leaf_audits),
            source_fact_pair_count=len(source_fact_pairs),
            approved_fact_leaf_count=approved_fact_leaf_count,
            rejected_fact_leaf_count=rejected_fact_leaf_count,
            time_bucket_count=len(time_buckets),
            concept_cluster_count=len(concept_clusters),
            synthesis_bridge_count=len(synthesis_bridges),
            difference_note_count=len(difference_notes),
        ).model_dump()

        return {
            "branch_growth_report": report,
            "branch_digests": branch_digests,
            "time_buckets": time_buckets,
            "fact_leaves": fact_leaves,
            "fact_leaf_audits": fact_leaf_audits,
            "source_fact_pairs": source_fact_pairs,
            "concept_clusters": concept_clusters,
            "synthesis_bridges": synthesis_bridges,
            "difference_notes": difference_notes,
            "child_branch_proposals": child_branch_proposals,
        }

    def _tactic_family_blueprints(self):
        return policy_doctrine_department._tactic_family_blueprints(self)

    def _infer_tactical_family(self, tactic: dict, rem_plan: dict, phase_7: dict):
        return policy_doctrine_department._infer_tactical_family(self, tactic, rem_plan, phase_7)

    def _normalize_tactical_cards(self, tactical: dict, rem_plan: dict, phase_7: dict):
        return policy_doctrine_department._normalize_tactical_cards(self, tactical, rem_plan, phase_7)

    def _route_policy_from_tactic(self, tactic: dict, policy_source: str):
        return policy_doctrine_department._route_policy_from_tactic(self, tactic, policy_source)

    def _tool_doctrine_from_tactic(self, tactic: dict, policy_source: str):
        return policy_doctrine_department._tool_doctrine_from_tactic(self, tactic, policy_source)

    def _build_policy_doctrine_bundle(self, state: MidnightState):
        return policy_doctrine_department._build_policy_doctrine_bundle(self, state)

    def node_strategy_council(self, state: MidnightState):
        strategy_council = self._build_strategy_council_state(state)
        return {"strategy_council": strategy_council}

    def node_rem_governor(self, state: MidnightState):
        rem_governor = self._build_rem_governor_state(state.get("dream_rows", []))
        return {"rem_governor": rem_governor}

    def node_branch_architect(self, state: MidnightState):
        branch_architect = build_branch_architect_state(
            state.get("rem_governor", {}),
            state.get("dream_rows", []),
            state.get("existing_branch_digests", []),
            state.get("strategy_council", {}),
        )
        return {
            "branch_architect": branch_architect,
            "architect_handoff_report": dict(branch_architect.get("architect_handoff_report") or {}),
        }

    def node_rem_plan(self, state: MidnightState):
        rem_plan = self._build_rem_plan_from_rows(
            state.get("dream_rows", []),
            rem_governor=state.get("rem_governor", {}),
            branch_architect=state.get("branch_architect", {}),
            architect_handoff_report=state.get("architect_handoff_report", {}),
            strategy_council=state.get("strategy_council", {}),
        )
        return {"rem_plan": rem_plan}

    def node_phase_10_policies(self, state: MidnightState):
        return self._build_policy_doctrine_bundle(state)

    def build_graph(self):
        print("[System] Building midnight reflection graph...")
        workflow = StateGraph(MidnightState)

        workflow.add_node("rem_governor", self.node_rem_governor)
        workflow.add_node("strategy_council", self.node_strategy_council)
        workflow.add_node("branch_architect", self.node_branch_architect)
        workflow.add_node("rem_plan", self.node_rem_plan)
        workflow.add_node("phase_7", self.node_phase_7_audit)
        workflow.add_node("phase_8a", self.node_phase_8a_plan)
        # Midnight graph uses the custom tool executor instead of a generic ToolNode.
        workflow.add_node("tools", self.node_execute_tools) 
        workflow.add_node("phase_8b", self.node_phase_8b_eval)
        workflow.add_node("phase_9", self.node_phase_9_tactics)
        workflow.add_node("phase_10_policy", self.node_phase_10_policies)
        workflow.add_node("phase_11_branch_growth", self.node_phase_11_branch_growth)

        # 2. Direct graph edges
        workflow.add_edge("rem_governor", "strategy_council")
        workflow.add_edge("strategy_council", "branch_architect")
        workflow.add_edge("branch_architect", "rem_plan")
        workflow.add_edge("rem_plan", "phase_7")
        workflow.add_edge("phase_7", "phase_8a")
        workflow.add_edge("tools", "phase_8b")

        def router_8a_to_next(state: MidnightState):
            actions = state.get("pending_actions", [])
            insufficient = [
                topic for topic in state.get("phase_7_audit", {}).get("classified_topics", [])
                if not topic.get("supply_sufficient")
            ]

            if actions:
                return "tools"
            if not insufficient:
                return "phase_9"
            if state.get("loop_count", 0) >= 3:
                return "phase_9"
            return "phase_7"

        workflow.add_conditional_edges(
            "phase_8a",
            router_8a_to_next,
            {"tools": "tools", "phase_7": "phase_7", "phase_9": "phase_9"}
        )

        # 3. Conditional review loop
        def router_8b_to_next(state: MidnightState):
            if state.get("loop_count", 0) >= 3:
                return "phase_9" 
            if state.get("doubt_feedback") == "RESOLVED":
                return "phase_9" 
            review_packet = state.get("phase_8_review_packet", {}) if isinstance(state.get("phase_8_review_packet"), dict) else {}
            review_target = str(review_packet.get("review_target") or "").strip()
            if review_target == "phase_8a":
                return "phase_8a"
            return "phase_7"    

        workflow.add_conditional_edges(
            "phase_8b", 
            router_8b_to_next,
            {"phase_9": "phase_9", "phase_7": "phase_7", "phase_8a": "phase_8a"}
        )

        workflow.add_edge("phase_9", "phase_10_policy")
        workflow.add_edge("phase_10_policy", "phase_11_branch_growth")
        workflow.add_edge("phase_11_branch_growth", END)
        workflow.set_entry_point("rem_governor")

        return workflow.compile()
    
    def fetch_unaudited_dreams(self, target_date):
        try:
            with self.neo4j_driver.session() as session:
                cypher = """
                MATCH (d:Dream) WHERE d.date STARTS WITH $date_prefix
                  AND NOT (d)<-[:AUDITED_FROM]-(:SecondDream)
                OPTIONAL MATCH (d)-[:HAS_PROCESS]->(tp:TurnProcess)
                OPTIONAL MATCH (tp)-[hp:HAS_PHASE]->(ps:PhaseSnapshot)
                WITH d, tp, hp, ps
                ORDER BY hp.phase_order ASC
                RETURN d.id AS dream_id, d.date AS date, d.user_input AS input,
                       d.final_answer AS answer,
                       d.turn_summary AS turn_summary,
                       tp.id AS process_id,
                       tp.process_summary_json AS process_summary,
                       d.phase_minus1_intent AS p_minus1,
                       d.phase_0_history AS p0, d.phase_1_actions AS p1,
                       d.phase_2_summaries AS p2, d.phase_3_summary AS p3,
                       collect(
                           CASE
                               WHEN ps IS NULL THEN null
                               ELSE {
                                   phase_name: ps.phase_name,
                                   phase_order: hp.phase_order,
                                   status: ps.status,
                                   summary: ps.summary,
                                   summary_json: ps.summary_json
                               }
                           END
                       ) AS phase_snapshots
                ORDER BY d.date ASC
                """
                result = session.run(cypher, date_prefix=target_date)
                return [record for record in result]
        except Exception as e:
            print(f"[Midnight] delivery failed: {e}")
            return []

    def dream_rows_to_log_text(self, rows):
        buf = []
        for row in rows:
            def _normalize_trace_value(value):
                if isinstance(value, str):
                    stripped = value.strip()
                    if stripped and stripped[0] in "[{":
                        try:
                            return json.loads(stripped)
                        except Exception:
                            return value
                return value

            trace = {}
            if row.get("turn_summary"):
                trace["turn_summary"] = row["turn_summary"]
            if row.get("process_summary"):
                trace["turn_process"] = _normalize_trace_value(row["process_summary"])
            if row.get("p_minus1"):
                trace["phase_minus1_intent"] = _normalize_trace_value(row["p_minus1"])
            mapping = (
                ("p0", "phase_0_history"),
                ("p1", "phase_1_actions"),
                ("p2", "phase_2_summaries"),
                ("p3", "phase_3_summary"),
            )
            for pykey, label in mapping:
                val = row.get(pykey)
                if val:
                    trace[label] = _normalize_trace_value(val)
            phase_snapshots = [item for item in (row.get("phase_snapshots") or []) if item]
            if phase_snapshots:
                normalized_phase_snapshots = []
                for snapshot in phase_snapshots:
                    if not isinstance(snapshot, dict):
                        continue
                    normalized = dict(snapshot)
                    normalized["summary_json"] = _normalize_trace_value(snapshot.get("summary_json"))
                    normalized_phase_snapshots.append(normalized)
                phase_snapshots = normalized_phase_snapshots
                trace["phase_snapshots"] = phase_snapshots
            trace_block = json.dumps(trace, ensure_ascii=False, indent=2) if trace else "(no phase trace)"
            buf.append(
                f"[Dream ID: {row['dream_id']} | Time: {row['date']}]\n"
                f"- User: {row['input']}\n- Assistant: {row['answer']}\n"
                f"- Field Trace (JSON):\n{trace_block}\n"
            )
        return "\n".join(buf)

    def node_phase_7_audit(self, state: MidnightState):
        p7 = self.phase_7_supply_audit(
            state["dreams_log_text"],
            rem_governor=state.get("rem_governor", {}),
            branch_architect=state.get("branch_architect", {}),
            rem_plan=state.get("rem_plan", {}),
            previous_feedback=state.get("phase_8b_feedback", ""),
            tool_history=self._tool_history_text(state.get("tool_runs", []), result_char_limit=500),
        )
        if isinstance(p7, dict):
            p7["coverage_map"] = self._build_phase7_coverage_map(p7, state.get("rem_plan", {}))
        return {
            "phase_7_audit": p7,
            "tool_runs": self._reconcile_tool_runs(state.get("tool_runs", []), p7),
            "fact_leaf_candidates": self._reconcile_fact_leaf_candidates(state.get("fact_leaf_candidates", []), [], p7),
        }

    def node_phase_8a_plan(self, state: MidnightState):
        tool_digest = "Available tools: " + ", ".join(PHASE8_TOOLS)
        plan = self.phase_8_plan_tools(
            state["phase_7_audit"],
            tool_digest,
            rem_governor=state.get("rem_governor", {}),
            branch_architect=state.get("branch_architect", {}),
            rem_plan=state.get("rem_plan", {}),
            previous_feedback=state.get("phase_8b_feedback", ""),
            tool_history=self._tool_history_text(state.get("tool_runs", []), result_char_limit=450),
            prior_tool_runs=state.get("tool_runs", []),
            review_packet=state.get("phase_8_review_packet", {}),
        )
        return {
            "pending_actions": plan.get("actions", []),
            "loop_count": state.get("loop_count", 0) + 1
        }

    def node_execute_tools(self, state: MidnightState):
        prev_runs = list(state.get("tool_runs", []))
        runs = []
        for a in state.get("pending_actions", []):
            res = self._run_phase8_tool(a["tool"], a.get("keyword"), a.get("topic_slug"), state["phase_7_audit"])
            runs.append({
                "topic_slug": a.get("topic_slug"),
                "tool": a["tool"],
                "keyword": a.get("keyword"),
                "result": res
            })
        return {"tool_runs": self._reconcile_tool_runs(prev_runs + runs, state.get("phase_7_audit", {}))}

    def node_phase_8b_eval(self, state: MidnightState):
        runs_text = self._tool_history_text(state.get("tool_runs", []), limit=12, result_char_limit=1800)
        p8b = self.phase_8_synthesize_bridges(state["phase_7_audit"], runs_text)
        is_resolved = p8b.get("is_resolved", False)
        merged_fact_candidates = self._reconcile_fact_leaf_candidates(
            state.get("fact_leaf_candidates", []),
            p8b.get("fact_leaf_candidates", []),
            state.get("phase_7_audit", {}),
        )
        feedback = (
            str(p8b.get("response_to_phase_7") or "").strip()
            or str(p8b.get("proactive_suggestion") or "").strip()
        )
        review_packet = self._build_phase8_review_packet(state, p8b)
        return {
            "fact_leaf_candidates": merged_fact_candidates,
            "doubt_feedback": "RESOLVED" if is_resolved else "DOUBT",
            "phase_8b_feedback": feedback,
            "phase_8_review_packet": review_packet,
        }

    def node_phase_9_tactics(self, state: MidnightState):
        import copy
        
        # 1. Compact Phase 7 policy state before evaluation.
        clean_p7 = copy.deepcopy(state.get("phase_7_audit", {}))
        
        # Keep tool-run payloads compact before Phase 8b evaluation.
        if "thought_process" in clean_p7:
            del clean_p7["thought_process"]
            
        # 2. Build a concise Phase 8b evaluation payload.
        clean_fact_leaf_candidates = state.get("fact_leaf_candidates", [])
        # Raw tool payloads can be large; Phase 8b should reason from fact-leaf candidates.
        clean_tool_runs = "Raw tool data is omitted. Use Phase 8b fact-leaf candidates as the evidence base."

        # 3. Evaluate whether Phase 9 can proceed.
        p9 = self.phase_9_tactical_doctrine(
            clean_p7,
            clean_tool_runs,
            clean_fact_leaf_candidates,
            rem_governor=state.get("rem_governor", {}),
            branch_architect=state.get("branch_architect", {}),
            rem_plan=state.get("rem_plan", {}),
        )
        
        return {"tactical_doctrine": p9}

    def node_phase_11_branch_growth(self, state: MidnightState):
        return self._build_branch_growth_bundle(state)
    
    # =====================================================================
    # 2. Validate tool action shape before execution.
    # =====================================================================

    def _run_phase8_tool(self, tool, keyword, topic_slug=None, p7_audit=None):
        kw = (keyword or "").strip()
        if tool in TOOLS_REQUIRING_KEYWORD and not kw:
            return f"`{tool}` requires a non-empty keyword."
        if tool == "SEARCH": return search_memory(kw)
        if tool == "READ_FULL_SOURCE":
            if "|" not in kw: return "READ_FULL_SOURCE keyword must look like `diary|YYYY-MM-DD` or `songryeon|YYYY-MM-DD`."
            src, dt = kw.split("|", 1)
            return read_full_source(src.strip(), dt.strip())
        if tool == "web_search": return web_search(kw)
        if tool == "recall_recent_dreams":
            lim = int(kw) if kw.isdigit() else 5
            return recall_recent_dreams(lim)
        if tool == "search_tactics": return search_tactics(kw)
        if tool == "search_supply_topics": return search_supply_topics(kw)
        
        return f"Unsupported tool: {tool}"

    # =====================================================================
    # 3. LLM supply planning phases.
    # =====================================================================

    def phase_7_supply_audit(self, log_text, rem_governor=None, branch_architect=None, rem_plan=None, previous_feedback="", tool_history=""):
        print("[Phase 7] Auditing supply topics and evidence gaps...")
        prompt = self._inject(
            self.PHASE7_PROMPT,
            constitution=self.CONSTITUTION_TEXT,
            log_text=log_text,
            previous_feedback=previous_feedback or "(no previous feedback)",
            tool_history=tool_history or "(no previous tool history)",
        )
        if rem_governor:
            prompt += "\n\n[REMGovernor]\n" + json.dumps(rem_governor, ensure_ascii=False, indent=2)
        if branch_architect:
            prompt += "\n\n[BranchArchitect]\n" + json.dumps(branch_architect, ensure_ascii=False, indent=2)
        if rem_plan:
            prompt += "\n\n[REMPlan]\n" + json.dumps(rem_plan, ensure_ascii=False, indent=2)
        res = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}], format=Phase7Schema.model_json_schema())
        return self._safe_json_load(res["message"]["content"]) or {}

    def phase_8_plan_tools(self, p7, tool_digest, rem_governor=None, branch_architect=None, rem_plan=None, previous_feedback="", tool_history="", prior_tool_runs=None, review_packet=None):
        print("[Phase 8a] Planning evidence-gathering tool calls...")
        p7 = p7 or {}
        insufficient = [t for t in p7.get("classified_topics", []) if not t.get("supply_sufficient")]
        if not insufficient: return {"actions": []}

        prior_tool_runs = prior_tool_runs or []
             
        prompt = self._inject(
            self.PHASE8A_PROMPT,
            constitution=self.CONSTITUTION_TEXT,
            tool_digest=tool_digest[:12000],
            insufficient_topics_json=json.dumps(insufficient, ensure_ascii=False, indent=2),
            previous_feedback=previous_feedback or "(no previous feedback)",
            tool_history=tool_history or "(no previous tool history)",
        )
        if rem_governor:
            prompt += "\n\n[REMGovernor]\n" + json.dumps(rem_governor, ensure_ascii=False, indent=2)
        if branch_architect:
            prompt += "\n\n[BranchArchitect]\n" + json.dumps(branch_architect, ensure_ascii=False, indent=2)
        if rem_plan:
            prompt += "\n\n[REMPlan]\n" + json.dumps(rem_plan, ensure_ascii=False, indent=2)
        if review_packet:
            prompt += "\n\n[Phase8ReviewPacket]\n" + json.dumps(review_packet, ensure_ascii=False, indent=2)
        res = ollama.chat(model=self.action_model, messages=[{"role": "user", "content": prompt}], format=Phase8aSchema.model_json_schema())
        data = self._safe_json_load(res["message"]["content"]) or {}
        
        actions = data.get("actions") or []
        clean = []
        tried_signatures = {
            (
                (run.get("topic_slug") or "").strip(),
                (run.get("tool") or "").strip(),
                str(run.get("keyword") or "").strip(),
            )
            for run in prior_tool_runs
        }
        for a in actions:
            tool = (a.get("tool") or "").strip()
            if tool not in PHASE8_TOOLS: continue
            action = {
                "topic_slug": (a.get("topic_slug") or "").strip(),
                "tool": tool,
                "keyword": str(a.get("keyword") or ""),
            }
            if tool in TOOLS_REQUIRING_KEYWORD and not action["keyword"].strip():
                continue
            if tool == "READ_FULL_SOURCE" and "|" not in action["keyword"]:
                continue
            signature = (
                action["topic_slug"],
                action["tool"],
                action["keyword"].strip(),
            )
            if signature in tried_signatures:
                continue
            clean.append(action)
        return {"actions": clean}

    def phase_8_synthesize_bridges(self, p7, tool_runs_text):
        print("[Phase 8b] Preparing FactLeaf candidates from source/tool results...")
        p7 = p7 or {}
        p7_part = json.dumps(p7, ensure_ascii=False, indent=2)[:12000]
        prompt = self._inject(self.PHASE8B_PROMPT, constitution=self.CONSTITUTION_TEXT, p7_json=p7_part, tool_runs=tool_runs_text[:14000])
        prompt += (
            "\n\n[Phase 8b FactLeaf Contract]\n"
            "Return grounded fact_leaf_candidates only.\n"
            "Do not invent new bridge thoughts.\n"
            "Each candidate should be a short factual sentence tied to a concrete source_address.\n"
            "Leave bridges empty unless you are preserving a legacy record for compatibility."
        )
        res = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}], format=Phase8bSchema.model_json_schema())
        data = self._safe_json_load(res["message"]["content"]) or {}
        deterministic_candidates = self._extract_fact_leaf_candidates_from_tool_runs_text(
            tool_runs_text,
            self._active_topic_slugs(p7),
        )
        legacy_bridge_candidates = []
        for bridge in data.get("bridges", []) or []:
            if not isinstance(bridge, dict):
                continue
            source_address = str(bridge.get("source_address") or "").strip()
            topic_slug = str(bridge.get("topic_slug") or "").strip()
            fact_text = self._trim_text(str(bridge.get("bridge_thought") or "").strip(), 280)
            if not source_address or not topic_slug or not fact_text:
                continue
            source_kind, _, inferred_time_bucket, _ = self._source_address_parts(source_address)
            legacy_bridge_candidates.append({
                "topic_slug": topic_slug,
                "source_address": source_address,
                "fact_text": fact_text,
                "parent_topic_slug": bridge.get("parent_topic_slug"),
                "source_kind": source_kind,
                "inferred_time_bucket": inferred_time_bucket,
                "support_weight": 0.58,
            })
        data["fact_leaf_candidates"] = self._reconcile_fact_leaf_candidates(
            [],
            (data.get("fact_leaf_candidates", []) or []) + deterministic_candidates + legacy_bridge_candidates,
            p7,
        )
        data["bridges"] = []
        return data

    def phase_9_tactical_doctrine(self, p7, tool_runs, fact_leaf_candidates, rem_governor=None, branch_architect=None, rem_plan=None):
        print("[Phase 9] Generating advisory tactical doctrine...")
        supply_ctx = {"phase_8_tool_runs": tool_runs, "phase_8_fact_leaf_candidates": fact_leaf_candidates}
        supply_str = json.dumps(supply_ctx, ensure_ascii=False, indent=2)[:16000]
        prompt = self._inject(self.PHASE9_PROMPT, constitution=self.CONSTITUTION_TEXT, p7_json=json.dumps(p7, ensure_ascii=False, indent=2)[:12000], supply_context=supply_str)
        prompt += (
            "\n\n[Structured Tactical Card Contract]\n"
            "Each TacticalThoughtItem should be as executable as possible.\n"
            "Fill these fields when possible: tactic_key, target_family, root_scope, branch_scope, semantic_signals, "
            "preferred_next_hop, preferred_direct_strategy, preferred_tools, disallowed_tools, tone_recipe, must_include, "
            "must_avoid, repair_recipe, evidence_priority, confidence_gate, status.\n"
            "Use short grounded strings, not long essays.\n"
            "Ground your tactics in phase_8_fact_leaf_candidates instead of legacy bridge thoughts whenever possible."
        )
        if rem_governor:
            prompt += "\n\n[REMGovernor]\n" + json.dumps(rem_governor, ensure_ascii=False, indent=2)
        if branch_architect:
            prompt += "\n\n[BranchArchitect]\n" + json.dumps(branch_architect, ensure_ascii=False, indent=2)
        if rem_plan:
            prompt += "\n\n[REMPlan]\n" + json.dumps(rem_plan, ensure_ascii=False, indent=2)
        res = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}], format=Phase9Schema.model_json_schema())
        return self._safe_json_load(res["message"]["content"])

    def _merge_topic_hierarchy(self, session, sd_id, topics):
        return merge_topic_hierarchy(session, sd_id, topics)

    def _persist_address_thought_topic(self, session, sd_id, bridge, topics_by_slug, seq):
        slug = (bridge.get("topic_slug") or "").strip()
        title = topics_by_slug.get(slug) or slug
        addr = (bridge.get("source_address") or "unknown|na").strip()
        valid_addr = self._looks_like_source_address(addr)
        thought = (bridge.get("bridge_thought") or "").strip()
        parent_slug = bridge.get("parent_topic_slug")
        if isinstance(parent_slug, str):
            parent_slug = parent_slug.strip() or None
        else:
            parent_slug = None
        bt_id = f"{sd_id}_bt_{seq}_{slug}"[:512]

        session.run(
            """
            MERGE (bt:SupplyBridgeThought {id: $bt_id})
            SET bt.content = $thought,
                bt.batch_id = $sd_id,
                bt.created_at = timestamp(),
                bt.raw_address = $addr
            MERGE (tt:SupplyTopic {slug: $slug})
            SET tt.title = coalesce(tt.title, $title),
                tt.status = coalesce(tt.status, 'unfulfilled'),
                tt.batch_id = $sd_id
            MERGE (bt)-[:SUPPORTS]->(tt)
            """,
            bt_id=bt_id, thought=thought, sd_id=sd_id, slug=slug, title=title, addr=addr
        )

        ops = [{"op": "CHAIN", "source": addr, "thought_id": bt_id, "topic": slug}]

        if not valid_addr:
            session.run(
                """
                MATCH (bt:SupplyBridgeThought {id: $bt_id})
                SET bt.address_valid = false,
                    bt.address_resolution = 'invalid_text'
                """,
                bt_id=bt_id,
            )
            ops.append({"op": "INVALID_SOURCE_ADDRESS", "address": addr, "thought_id": bt_id})
        elif "|" in addr and not addr.startswith("web:"):
            try:
                src_type, target_date = addr.split("|", 1)
                src_type = src_type.strip()
                target_date = target_date.strip()

                label_map = {"Diary": "Diary", "GeminiChat": "GeminiChat", "SongryeonChat": "SongryeonChat"}
                target_label = label_map.get(src_type, "PastRecord") 

                cypher_link = f"""
                MATCH (bt:SupplyBridgeThought {{id: $bt_id}})
                MATCH (r:PastRecord:{target_label}) WHERE r.date STARTS WITH $target_date
                MERGE (r)-[:PROVIDES_KNOWLEDGE]->(bt)
                """
                result = session.run(cypher_link, bt_id=bt_id, target_date=target_date)
                summary = result.consume().counters
                
                if summary.relationships_created > 0:
                    session.run(
                        """
                        MATCH (bt:SupplyBridgeThought {id: $bt_id})
                        SET bt.address_valid = true,
                            bt.address_resolution = 'direct_link'
                        """,
                        bt_id=bt_id,
                    )
                    ops.append({"op": "NEURAL_DIRECT_LINK", "target": f"{target_label}|{target_date}"})
                    print(f"    [direct link] connected {src_type}({target_date}) source to bridge.")
                else:
                    session.run(
                        """
                        MATCH (bt:SupplyBridgeThought {id: $bt_id})
                        MERGE (sr:SourceRef {address: $addr})
                        ON CREATE SET sr.created_at = timestamp()
                        SET sr.batch_id = $sd_id
                        MERGE (sr)-[:RAW_ADDRESS]->(bt)
                        SET bt.address_valid = true,
                            bt.address_resolution = 'source_ref_fallback'
                        """,
                        bt_id=bt_id, addr=addr, sd_id=sd_id
                    )
            except Exception as e:
                print(f"    [address parse error] {addr}: {e}")
                session.run(
                    """
                    MATCH (bt:SupplyBridgeThought {id: $bt_id})
                    SET bt.address_valid = false,
                        bt.address_resolution = 'parse_error'
                    """,
                    bt_id=bt_id,
                )
                ops.append({"op": "SOURCE_ADDRESS_PARSE_ERROR", "address": addr, "thought_id": bt_id})
        else:
            session.run(
                """
                MATCH (bt:SupplyBridgeThought {id: $bt_id})
                MERGE (sr:SourceRef {address: $addr})
                ON CREATE SET sr.created_at = timestamp()
                SET sr.batch_id = $sd_id
                MERGE (sr)-[:RAW_ADDRESS]->(bt)
                SET bt.address_valid = true,
                    bt.address_resolution = 'source_ref_fallback'
                """,
                bt_id=bt_id, addr=addr, sd_id=sd_id
            )

        if parent_slug:
            session.run(
                """
                MERGE (pt:SupplyTopic {slug: $ps})
                SET pt.batch_id = $sd_id
                MERGE (ch:SupplyTopic {slug: $cs})
                MERGE (ch)-[:SUBTOPIC_OF]->(pt)
                """,
                ps=parent_slug, cs=slug, sd_id=sd_id,
            )
            ops.append({"op": "BRIDGE_SUBTOPIC_OF", "child": slug, "parent": parent_slug})

        session.run(
            """
            MATCH (sd:SecondDream {id: $sd_id})
            MATCH (bt:SupplyBridgeThought {id: $bt_id})
            MATCH (tt:SupplyTopic {slug: $slug})
            MERGE (sd)-[:INCLUDES_BRIDGE]->(bt)
            MERGE (sd)-[:TRACKS_TOPIC]->(tt)
            """,
            sd_id=sd_id, bt_id=bt_id, slug=slug,
        )
        return ops

    def _forge_tactical_thoughts_neo4j(self, session, sd_id, p9, dream_ids, graph_operations_log, rem_plan=None, phase_7=None):
        return forge_tactical_thoughts_neo4j(self, session, sd_id, p9, dream_ids, graph_operations_log, rem_plan, phase_7)

    def _persist_strategy_council(self, session, sd_id, strategy_council, graph_operations_log):
        return persist_strategy_council(self, session, sd_id, strategy_council, graph_operations_log)

    def _persist_rem_governor_state(self, session, sd_id, rem_governor, rem_plan, graph_operations_log):
        return persist_rem_governor_state(self, session, sd_id, rem_governor, rem_plan, graph_operations_log)

    def _persist_branch_architect(self, session, sd_id, branch_architect, dreams, graph_operations_log):
        return persist_branch_architect(self, session, sd_id, branch_architect, dreams, graph_operations_log)

    def _persist_rem_plan(self, session, sd_id, rem_plan, dreams, graph_operations_log):
        return persist_rem_plan(self, session, sd_id, rem_plan, dreams, graph_operations_log)

    def _persist_route_policies(self, session, sd_id, route_policies, graph_operations_log):
        return persist_route_policies(self, session, sd_id, route_policies, graph_operations_log)

    def _persist_tool_doctrines(self, session, sd_id, tool_doctrines, graph_operations_log):
        return persist_tool_doctrines(self, session, sd_id, tool_doctrines, graph_operations_log)

    def _persist_branch_growth(
        self,
        session,
        sd_id,
        branch_growth_report,
        branch_digests,
        time_buckets,
        fact_leaves,
        fact_leaf_audits,
        source_fact_pairs,
        concept_clusters,
        synthesis_bridges,
        difference_notes,
        child_branch_proposals,
        strategy_council,
        graph_operations_log,
    ):
        branch_growth_id = persist_branch_growth_header(session, sd_id, branch_growth_report, graph_operations_log)
        persist_time_buckets(session, branch_growth_id, time_buckets, graph_operations_log)
        persist_fact_leaves(self, session, branch_growth_id, fact_leaves, graph_operations_log)
        persist_fact_leaf_audits(session, branch_growth_id, fact_leaf_audits, graph_operations_log)
        persist_source_fact_pairs(session, branch_growth_id, source_fact_pairs, graph_operations_log)

        persist_concept_clusters(self, session, branch_growth_id, concept_clusters, graph_operations_log)

        persist_synthesis_bridges(self, session, branch_growth_id, synthesis_bridges, graph_operations_log)

        persist_difference_notes(self, session, branch_growth_id, difference_notes, graph_operations_log)

        persist_child_branch_proposals(self, session, branch_growth_id, child_branch_proposals, graph_operations_log)

        persist_branch_digests(self, session, sd_id, branch_growth_id, branch_digests, graph_operations_log)

        persist_strategy_attention(session, strategy_council, graph_operations_log)

    @classmethod
    def _attach_branch_growth_feedback_to_rem_plan(cls, rem_plan, branch_growth_report):
        return rem_plan_department._attach_branch_growth_feedback_to_rem_plan(cls, rem_plan, branch_growth_report)

    def _save_to_neo4j(self, state: MidnightState, dreams):
        print("[System] Persisting midnight graph outputs to Neo4j...")
        sd_id = f"sd_{state['target_date']}_{int(datetime.now().timestamp())}"
        debate_state = build_reflection_debate_state(state)
        try:
            with self.neo4j_driver.session() as session:
                session.run(
                    "MERGE (sd:SecondDream {id: $sd_id}) "
                    "SET sd.date = $target_date, "
                    "    sd.created_at = timestamp(), "
                    "    sd.debate_state_json = $debate_state_json",
                    sd_id=sd_id,
                    target_date=state["target_date"],
                    debate_state_json=json.dumps(debate_state, ensure_ascii=False),
                )
                for d in dreams:
                    session.run(
                        "MATCH (sd:SecondDream {id: $sd_id}), (d:Dream {id: $did}) MERGE (d)<-[:AUDITED_FROM]-(sd)",
                        sd_id=sd_id, did=d["dream_id"]
                    )
                ops = []
                state["rem_plan"] = self._attach_branch_growth_feedback_to_rem_plan(
                    state.get("rem_plan", {}),
                    state.get("branch_growth_report", {}),
                )
                refreshed_governor = self._refresh_rem_governor_state(state)
                state["rem_governor"] = refreshed_governor
                refreshed_strategy = self._build_strategy_council_state(state)
                state["strategy_council"] = refreshed_strategy
                branch_offices, local_reports = build_branch_offices(
                    state.get("field_memos", []),
                    required_branches=refreshed_governor.get("required_branches", []) if isinstance(refreshed_governor, dict) else [],
                    tonight_scope=refreshed_strategy.get("tonight_scope", []) if isinstance(refreshed_strategy, dict) else [],
                    fact_leaves=state.get("fact_leaves", []),
                    branch_digests=state.get("branch_digests", []),
                    route_policies=state.get("route_policies", []),
                    tool_doctrines=state.get("tool_doctrines", []),
                )
                state["branch_offices"] = branch_offices
                state["local_reports"] = local_reports
                layered_memos = build_layered_memos(state.get("field_memos", []))
                state["layered_memos"] = layered_memos
                refreshed_governor = apply_local_reports_to_governor(refreshed_governor, local_reports)
                state["rem_governor"] = refreshed_governor
                self._persist_rem_governor_state(session, sd_id, refreshed_governor, state.get("rem_plan", {}), ops)
                self._persist_strategy_council(session, sd_id, refreshed_strategy, ops)
                persist_branch_offices(session, sd_id, branch_offices, local_reports, ops)
                persist_layered_memos(session, sd_id, layered_memos, ops)
                self._persist_branch_architect(session, sd_id, state.get("branch_architect", {}), dreams, ops)
                self._persist_rem_plan(session, sd_id, state.get("rem_plan", {}), dreams, ops)
                topics = state["phase_7_audit"].get("classified_topics", [])
                ops.extend(self._merge_topic_hierarchy(session, sd_id, topics))
                
                self._forge_tactical_thoughts_neo4j(
                    session,
                    sd_id,
                    state["tactical_doctrine"],
                    state["dream_ids"],
                    ops,
                    rem_plan=state.get("rem_plan", {}),
                    phase_7=state.get("phase_7_audit", {}),
                )
                self._persist_route_policies(session, sd_id, state.get("route_policies", []), ops)
                self._persist_tool_doctrines(session, sd_id, state.get("tool_doctrines", []), ops)
                self._persist_branch_growth(
                    session,
                    sd_id,
                    state.get("branch_growth_report", {}),
                    state.get("branch_digests", []),
                    state.get("time_buckets", []),
                    state.get("fact_leaves", []),
                    state.get("fact_leaf_audits", []),
                    state.get("source_fact_pairs", []),
                    state.get("concept_clusters", []),
                    state.get("synthesis_bridges", []),
                    state.get("difference_notes", []),
                    state.get("child_branch_proposals", []),
                    state.get("strategy_council", {}),
                    ops,
                )
                print(f"[System] Persistence complete: {len(ops)} graph operations.")
                return {
                    "sd_id": sd_id,
                    "operations_count": len(ops),
                    "topic_count": len(state.get("phase_7_audit", {}).get("classified_topics", [])),
                    "fact_leaf_candidate_count": len(state.get("fact_leaf_candidates", [])),
                    "tactic_count": len((state.get("tactical_doctrine") or {}).get("tactical_thoughts") or []),
                    "route_policy_count": len(state.get("route_policies", [])),
                    "tool_doctrine_count": len(state.get("tool_doctrines", [])),
                    "branch_digest_count": len(state.get("branch_digests", [])),
                    "fact_leaf_count": len(state.get("fact_leaves", [])),
                    "fact_leaf_audit_count": len(state.get("fact_leaf_audits", [])),
                    "source_fact_pair_count": len(state.get("source_fact_pairs", [])),
                    "concept_cluster_count": len(state.get("concept_clusters", [])),
                    "synthesis_bridge_count": len(state.get("synthesis_bridges", [])),
                    "difference_note_count": len(state.get("difference_notes", [])),
                    "child_branch_proposal_count": len(state.get("child_branch_proposals", [])),
                    "branch_office_count": len(state.get("branch_offices", [])),
                    "local_report_count": len(state.get("local_reports", [])),
                    "layered_memo_count": len(state.get("layered_memos", [])),
                    "governor_key": str((state.get("rem_governor") or {}).get("governor_key") or "rem_governor_v1"),
                    "strategy_key": str((state.get("strategy_council") or {}).get("strategy_key") or "strategy_council_v1"),
                    "debate_state": debate_state,
                }
        except Exception as e:
            print(f"[System] Persistence error: {e}")
            return {"sd_id": sd_id, "error": str(e)}

    def execute_midnight_reflection(self, target_date):
        print("==================================================")
        print(f"[{target_date}] Midnight reflection graph V6.0 start")
        print("==================================================")

        ready, reason = self._ensure_neo4j_ready()
        if not ready:
            print(f"[System] Midnight reflection stopped: {reason}\n")
            return {
                "status": "blocked",
                "target_date": target_date,
                "reason": reason,
            }

        dreams = self.fetch_unaudited_dreams(target_date)
        if not dreams:
            print("[System] No unreviewed Dream rows for that date.\n")
            return

        dream_ids = [d["dream_id"] for d in dreams if d.get("dream_id")]
        log_text = self.dream_rows_to_log_text(dreams)
        existing_branch_digests = self._load_existing_branch_digests()
        existing_concept_clusters = self._load_existing_concept_clusters()
        recent_field_memos = load_recent_field_memos(160)

        # Initialize graph state.
        initial_state = {
            "target_date": target_date,
            "dream_ids": dream_ids,
            "dream_rows": dreams,
            "dreams_log_text": log_text,
            "existing_branch_digests": existing_branch_digests,
            "existing_concept_clusters": existing_concept_clusters,
            "strategy_council": {},
            "rem_governor": {},
            "branch_architect": {},
            "architect_handoff_report": {},
            "rem_plan": {},
            "phase_7_audit": {},
            "pending_actions": [],
            "loop_count": 0,
            "tool_runs": [],
            "fact_leaf_candidates": [],
            "doubt_feedback": "",
            "phase_8b_feedback": "",
            "phase_8_review_packet": {},
            "tactical_doctrine": {},
            "route_policies": [],
            "tool_doctrines": [],
            "branch_growth_report": {},
            "branch_digests": [],
            "time_buckets": [],
            "fact_leaves": [],
            "fact_leaf_audits": [],
            "source_fact_pairs": [],
            "concept_clusters": [],
            "synthesis_bridges": [],
            "difference_notes": [],
            "child_branch_proposals": [],
            "field_memos": recent_field_memos,
            "layered_memos": [],
            "branch_offices": [],
            "local_reports": [],
        }

        # Run graph.
        final_state = self.app.invoke(initial_state)

        # Persist results.
        save_result = self._save_to_neo4j(final_state, dreams)
        return {
            "status": "completed",
            "target_date": target_date,
            "loop_count": final_state.get("loop_count", 0),
            "pending_action_count": len(final_state.get("pending_actions", [])),
            "strategy_scope_count": len((final_state.get("strategy_council") or {}).get("tonight_scope") or []),
            "fact_leaf_candidate_count": len(final_state.get("fact_leaf_candidates", [])),
            "field_memo_count": len(final_state.get("field_memos", [])),
            "tactic_count": len((final_state.get("tactical_doctrine") or {}).get("tactical_thoughts") or []),
            "branch_digest_count": len(final_state.get("branch_digests", [])),
            "fact_leaf_count": len(final_state.get("fact_leaves", [])),
            "fact_leaf_audit_count": len(final_state.get("fact_leaf_audits", [])),
            "source_fact_pair_count": len(final_state.get("source_fact_pairs", [])),
            "concept_cluster_count": len(final_state.get("concept_clusters", [])),
            "synthesis_bridge_count": len(final_state.get("synthesis_bridges", [])),
            "difference_note_count": len(final_state.get("difference_notes", [])),
            "child_branch_proposal_count": len(final_state.get("child_branch_proposals", [])),
            "branch_office_count": len(final_state.get("branch_offices", [])),
            "local_report_count": len(final_state.get("local_reports", [])),
            "save_result": save_result,
        }
    def execute_grand_reflection_sweep(self):
        print("\n[System] Starting batch midnight reflection over unreviewed Dream rows.")
        ready, reason = self._ensure_neo4j_ready()
        if not ready:
            print(f"[System] Batch stopped: {reason}")
            return
        try:
            with self.neo4j_driver.session() as session:
                cypher = (
                    "MATCH (d:Dream) WHERE NOT (d)<-[:AUDITED_FROM]-(:SecondDream) "
                    "RETURN DISTINCT substring(d.date, 0, 10) AS date_str ORDER BY date_str ASC"
                )
                result = session.run(cypher)
                all_dates = [record["date_str"] for record in result if record["date_str"]]
            if not all_dates:
                print("[System] No unreviewed Dream rows.")
                return
            print(f"[System] Unreviewed dates: {len(all_dates)} {all_dates}")
            for target_date in all_dates:
                self.execute_midnight_reflection(target_date)
            print("[System] Batch midnight reflection complete.")
        except Exception as e:
            print(f"[System] Batch midnight reflection error: {e}")
    

if __name__ == "__main__":
    DreamWeaver().execute_grand_reflection_sweep()
