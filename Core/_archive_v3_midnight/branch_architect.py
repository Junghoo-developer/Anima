import json
import json
import unicodedata
from typing import List, Literal

from pydantic import BaseModel

from Core.rem_governor import (
    ArchitectHandoffReportSchema,
    branch_path_for_topic,
    dedupe_keep_order,
    topic_slug_from_branch_path,
    topic_label_ko,
)


class RootFactCard(BaseModel):
    root_entity: str
    inferred_role: str
    factual_summary: str
    supporting_signals: List[str]


class BranchBlueprintItem(BaseModel):
    branch_path: str
    topic_slug: str
    branch_title: str
    parent_root: str
    branch_kind: Literal["existing_update", "required_update", "new_growth"]
    placement_reason: str
    required_leaf_specs: List[str]
    evidence_hints: List[str]
    relay_target: str = "rem_plan"


class BranchArchitectSchema(BaseModel):
    architect_key: str
    governor_key: str
    root_fact_cards: List[RootFactCard]
    branch_blueprints: List[BranchBlueprintItem]
    relay_notes: List[str]
    create_targets: List[str]
    update_targets: List[str]
    evidence_start_points: List[str]
    objective_summary: str
    report_target_phase: str
    status: str
    architect_handoff_report: dict


def _extract_text_fragments(dream_rows):
    fragments = []
    evidence_points = []
    for row in dream_rows if isinstance(dream_rows, list) else []:
        if isinstance(row, BaseModel):
            row = row.model_dump()
        elif not isinstance(row, dict):
            try:
                row = dict(row)
            except Exception:
                row = {}
        if not isinstance(row, dict):
            continue
        for key in ("input", "answer", "turn_summary"):
            value = str(row.get(key) or "").strip()
            if value:
                fragments.append(value)
        dream_id = str(row.get("dream_id") or "").strip()
        process_id = str(row.get("process_id") or "").strip()
        if dream_id:
            evidence_points.append(f"Dream:{dream_id}")
        if process_id:
            evidence_points.append(f"TurnProcess:{process_id}")
        process_summary = row.get("process_summary")
        if isinstance(process_summary, str):
            try:
                process_summary = json.loads(process_summary)
            except Exception:
                process_summary = {}
        if isinstance(process_summary, dict):
            for source_id in process_summary.get("used_sources", []) or []:
                normalized = str(source_id or "").strip()
                if normalized:
                    evidence_points.append(normalized)
    normalized_text = unicodedata.normalize("NFKC", " ".join(fragments))
    return normalized_text, dedupe_keep_order(evidence_points)


def _infer_root_fact_cards(governor):
    root_entities = list(governor.get("root_entities", []) or [])
    root_descriptions = list(governor.get("root_descriptions", []) or [])
    evidence_roots = list(governor.get("evidence_roots", []) or [])
    root_inventory = [
        dict(item)
        for item in (governor.get("root_inventory", []) or [])
        if isinstance(item, dict)
    ]
    root_profiles = {
        str(item.get("root_entity") or "").strip(): dict(item)
        for item in (governor.get("root_profiles", []) or [])
        if isinstance(item, dict) and str(item.get("root_entity") or "").strip()
    }
    cards = []
    joined_descriptions = " ".join(str(item or "") for item in root_descriptions)
    joined_evidence = " ".join(str(item or "") for item in evidence_roots)

    for root in root_entities:
        root_text = str(root or "").strip()
        if not root_text:
            continue
        profile = root_profiles.get(root_text, {})
        inventory_hints = []
        for item in root_inventory:
            if str(item.get("root_entity") or "").strip() != root_text:
                continue
            relation_type = str(item.get("relation_type") or "").strip()
            node_type = str(item.get("node_type") or "").strip()
            node_name = str(item.get("node_name") or "").strip()
            summary = str(item.get("summary") or "").strip()
            hint = " / ".join(part for part in [relation_type, node_type, node_name or summary] if part)
            if hint:
                inventory_hints.append(hint)
        if root_text.startswith("Person:"):
            cards.append(
                RootFactCard(
                    root_entity=root_text,
                    inferred_role=str(profile.get("inferred_role") or "developer_user"),
                    factual_summary=str(profile.get("factual_summary") or "허정후는 이 시스템의 사용자이자 개발자 축으로 읽히며, 일기·기록·과거 데이터와 연결된 사람 루트입니다."),
                    supporting_signals=dedupe_keep_order(
                        list(profile.get("connected_node_types", []) or [])
                        + list(profile.get("connected_relation_types", []) or [])
                        + inventory_hints
                        + [joined_descriptions, joined_evidence, "허정후 사람 루트", "일기/과거기록 연결 문맥"]
                    )[:6],
                )
            )
        elif root_text.startswith("CoreEgo:"):
            cards.append(
                RootFactCard(
                    root_entity=root_text,
                    inferred_role=str(profile.get("inferred_role") or "system_prototype"),
                    factual_summary=str(profile.get("factual_summary") or "송련은 현장 응답과 기억 구조를 아우르는 CoreEgo 축이며, ANIMA의 프로토타입 집합체로 읽힙니다."),
                    supporting_signals=dedupe_keep_order(
                        list(profile.get("connected_node_types", []) or [])
                        + list(profile.get("connected_relation_types", []) or [])
                        + inventory_hints
                        + [joined_descriptions, joined_evidence, "송련 핵심 자아 루트", "꿈/정책/교리 연결 문맥"]
                    )[:6],
                )
            )
        else:
            cards.append(
                RootFactCard(
                    root_entity=root_text,
                    inferred_role="observed_root",
                    factual_summary=f"{root_text}는 현재 그래프에서 관측된 상위 루트입니다.",
                    supporting_signals=dedupe_keep_order([joined_descriptions, joined_evidence])[:6],
                )
            )
    return cards


def _priority_topics_from_governor(governor, normalized_text):
    topics = []
    branch_map = {
        "person_definition": ["허정후", "사용자", "사령관", "정의", "identity", "definition"],
        "person_life_history": ["허정후", "과거", "역사", "일기", "기록", "history", "past", "diary"],
        "person_current_state": ["허정후", "현재", "상태", "기분", "학교", "개발", "current", "state"],
        "person_development_pattern": ["개발", "코딩", "프로젝트", "주말", "패턴", "development", "coding"],
        "coreego_definition": ["송련", "ANIMA", "정의", "정체성", "identity", "definition"],
        "coreego_history": ["송련", "과거", "심야", "성찰", "history", "reflection"],
        "coreego_current_state": ["송련", "현재", "상태", "현장", "current", "state"],
        "coreego_field_response": ["송련", "현장", "답변", "응답", "찐빠", "수습", "field", "response"],
        "coreego_self_model": ["송련", "자의식", "자기", "페르소나", "self", "persona"],
        "personal_history_review": ["과거", "일기", "기록", "예전", "history", "past", "diary", "record"],
        "recent_dialogue_review": ["최근 대화", "대화", "요약", "정리", "dialogue", "conversation", "summary", "recap"],
        "self_analysis_snapshot": ["분석", "패턴", "자기", "나는 어떤 사람", "pattern", "self", "snapshot"],
        "tool_routing": ["도구", "검색", "자료", "부가자료", "읽고", "tool", "search", "artifact", "read"],
        "field_repair": ["오류", "문제", "왜 이래", "고쳐", "repair", "bug", "failure"],
    }

    for branch_path in governor.get("required_branches", []) or []:
        branch_text = str(branch_path or "").strip()
        branch_topic = topic_slug_from_branch_path(branch_text)
        if branch_topic:
            topics.append(branch_topic)

    for topic_slug, markers in branch_map.items():
        if any(token in normalized_text for token in markers):
            topics.append(topic_slug)

    return dedupe_keep_order(topics) or ["field_repair"]


def _build_architect_handoff_report(governor_key, architect_key, root_entities, blueprints, create_targets, update_targets, evidence_start_points):
    normalized_blueprints = []
    for item in blueprints:
        if isinstance(item, BaseModel):
            normalized_blueprints.append(item.model_dump())
        elif isinstance(item, dict):
            normalized_blueprints.append(dict(item))
    selected_branch_paths = [
        str(item.get("branch_path") or "").strip()
        for item in normalized_blueprints
        if str(item.get("branch_path") or "").strip()
    ]
    translation_gaps = []
    if not root_entities:
        translation_gaps.append("REMGovernor가 넘긴 루트 기준점이 비어 있습니다.")
    if not selected_branch_paths:
        translation_gaps.append("BranchArchitect가 실행 가능한 가지 설계도를 만들지 못했습니다.")
    if not evidence_start_points:
        translation_gaps.append("REMPlan이 시작할 근거 출발점이 없습니다.")

    preserved_constraints = [
        "루트는 Person(허정후)와 CoreEgo(송련)만 사용한다.",
        "BranchArchitect는 도구 호출, 정책 확정, 최종 판정을 하지 않는다.",
        "REMPlan은 handoff 설계도를 다시 재해석하지 않고 집행한다.",
    ]
    status = "ready" if not translation_gaps else "blocked"
    intent_alignment = "aligned" if not translation_gaps else "blocked"
    reviewer_summary = (
        "Governor의 상위 가지 설계가 REMPlan으로 안전하게 넘어갈 준비가 되었습니다."
        if status == "ready"
        else "Governor 의도와 Architect 번역 사이에 비어 있는 슬롯이 있어, 먼저 이 handoff를 보강해야 합니다."
    )
    return ArchitectHandoffReportSchema(
        report_key=f"{architect_key}::handoff",
        governor_key=governor_key,
        architect_key=architect_key,
        target_roots=dedupe_keep_order(root_entities),
        selected_branch_paths=dedupe_keep_order(selected_branch_paths),
        create_targets=dedupe_keep_order(create_targets),
        update_targets=dedupe_keep_order(update_targets),
        evidence_start_points=dedupe_keep_order(evidence_start_points)[:24],
        preserved_constraints=preserved_constraints,
        translation_gaps=translation_gaps[:8],
        intent_alignment=intent_alignment,
        reviewer_summary=reviewer_summary,
        status=status,
    ).model_dump()


def build_branch_architect_state(governor, dream_rows, branch_digests=None, strategy_council=None):
    governor = governor if isinstance(governor, dict) and governor else {}
    strategy = strategy_council if isinstance(strategy_council, dict) and strategy_council else {}
    governor_key = str(governor.get("governor_key") or "rem_governor_v1")
    known_branches = set(dedupe_keep_order(governor.get("known_branches", []) or []))
    required_branches = set(dedupe_keep_order(governor.get("required_branches", []) or []))
    existing_branch_paths = {
        str(item.get("branch_path") or "").strip()
        for item in (branch_digests or [])
        if isinstance(item, dict) and str(item.get("branch_path") or "").strip()
    }
    normalized_text, evidence_start_points = _extract_text_fragments(dream_rows)
    root_fact_cards = _infer_root_fact_cards(governor)
    priority_topics = _priority_topics_from_governor(governor, normalized_text)
    strategy_scope = [
        dict(item)
        for item in (strategy.get("tonight_scope", []) or [])
        if isinstance(item, dict)
    ]
    strategy_mandates = [str(item or "").strip() for item in (strategy.get("editorial_mandates", []) or []) if str(item or "").strip()]
    planning_self_summary = str(strategy.get("planning_self_summary") or "").strip()
    attention_shortlist = [
        dict(item)
        for item in (strategy.get("attention_shortlist", []) or [])
        if isinstance(item, dict) and str(item.get("branch_path") or "").strip()
    ]
    strategy_child_branch_proposals = [
        dict(item)
        for item in (strategy.get("child_branch_proposals", []) or [])
        if isinstance(item, dict) and str(item.get("proposed_branch_path") or "").strip()
    ]
    for attention_item in attention_shortlist:
        branch_path = str(attention_item.get("branch_path") or "").strip()
        if branch_path and len([segment for segment in branch_path.split("/") if segment]) <= 3:
            priority_topics.insert(0, topic_slug_from_branch_path(branch_path))
    for scope in strategy_scope:
        branch_path = str(scope.get("branch_path") or "").strip()
        if branch_path and len([segment for segment in branch_path.split("/") if segment]) <= 3:
            priority_topics.insert(0, topic_slug_from_branch_path(branch_path))
        for evidence_point in scope.get("evidence_start_points", []) or []:
            normalized = str(evidence_point or "").strip()
            if normalized:
                evidence_start_points.append(normalized)
    priority_topics = dedupe_keep_order(priority_topics)
    evidence_start_points = dedupe_keep_order(evidence_start_points)

    blueprints = []
    create_targets = []
    update_targets = []
    blueprint_paths_seen = set()
    relay_notes = [
        "REMGovernor가 정한 Person/CoreEgo 루트를 벗어나지 않는다.",
        "BranchArchitect는 총괄의 큰 가지를 REMPlan이 바로 실행 가능한 branch/leaf 단위로 번역한다.",
        "근거는 Dream/TurnProcess/PhaseSnapshot 및 기존 원문 주소에서 우선 회수한다.",
        "BranchArchitect는 handoff report로 Governor 의도와 설계 번역의 누락 여부를 함께 보고한다.",
    ]
    if attention_shortlist:
        relay_notes.append(
            "StrategyCouncil attention shortlist mirrored into branch placement priority: "
            + ", ".join(
                str(item.get("title") or item.get("branch_path") or "").strip()
                for item in attention_shortlist[:3]
                if str(item.get("title") or item.get("branch_path") or "").strip()
            )
        )
    if strategy_scope:
        relay_notes.append("StrategyCouncil tonight_scope mirrored into branch placement priority.")
    if strategy_child_branch_proposals:
        relay_notes.append(
            f"StrategyCouncil child branch proposals mirrored into blueprint growth ({len(strategy_child_branch_proposals)} proposals)."
        )
    relay_notes.extend(strategy_mandates[:3])

    def append_blueprint(*, branch_path, topic_slug, branch_kind, placement_reason, leaf_specs, evidence_hints):
        normalized_branch_path = str(branch_path or "").strip()
        normalized_topic_slug = str(topic_slug or "").strip() or topic_slug_from_branch_path(normalized_branch_path)
        parent_root = normalized_branch_path.split("/", 1)[0] if "/" in normalized_branch_path else normalized_branch_path
        if not normalized_branch_path or normalized_branch_path in blueprint_paths_seen:
            return
        blueprint_paths_seen.add(normalized_branch_path)
        if branch_kind == "new_growth":
            create_targets.append(normalized_branch_path)
        else:
            update_targets.append(normalized_branch_path)
        blueprints.append(
            BranchBlueprintItem(
                branch_path=normalized_branch_path,
                topic_slug=normalized_topic_slug,
                branch_title=topic_label_ko(normalized_topic_slug),
                parent_root=parent_root,
                branch_kind=branch_kind,
                placement_reason=placement_reason,
                required_leaf_specs=dedupe_keep_order(leaf_specs),
                evidence_hints=dedupe_keep_order(evidence_hints)[:12],
            )
        )

    for topic_slug in priority_topics:
        branch_path = branch_path_for_topic(topic_slug)
        if branch_path in required_branches:
            branch_kind = "required_update"
            placement_reason = f"{topic_label_ko(topic_slug)}는 REMGovernor가 이미 필수 가지로 본 축이므로 보강 우선입니다."
        elif branch_path in known_branches or branch_path in existing_branch_paths:
            branch_kind = "existing_update"
            placement_reason = f"{topic_label_ko(topic_slug)}는 기존 가지가 있으므로 새로 만들기보다 갱신이 우선입니다."
        else:
            branch_kind = "new_growth"
            placement_reason = f"{topic_label_ko(topic_slug)}는 현재 구조에 비어 있어 새 가지 성장 대상으로 잡습니다."
        append_blueprint(
            branch_path=branch_path,
            topic_slug=topic_slug,
            branch_kind=branch_kind,
            placement_reason=placement_reason,
            leaf_specs=[
                f"{topic_slug}::root_fact",
                f"{topic_slug}::grounded_min_leaf",
                f"{topic_slug}::evidence_address",
            ],
            evidence_hints=evidence_start_points + [str(item or "").strip() for item in governor.get("evidence_roots", []) or []],
        )

    for proposal in strategy_child_branch_proposals:
        proposed_branch_path = str(proposal.get("proposed_branch_path") or "").strip()
        parent_branch_path = str(proposal.get("parent_branch_path") or "").strip()
        proposal_topic_slug = str(proposal.get("topic_slug") or "").strip() or topic_slug_from_branch_path(proposed_branch_path)
        if proposed_branch_path in required_branches:
            branch_kind = "required_update"
        elif proposed_branch_path in known_branches or proposed_branch_path in existing_branch_paths:
            branch_kind = "existing_update"
        else:
            branch_kind = "new_growth"
        append_blueprint(
            branch_path=proposed_branch_path,
            topic_slug=proposal_topic_slug,
            branch_kind=branch_kind,
            placement_reason=str(
                proposal.get("proposal_reason")
                or f"{parent_branch_path} 아래 child branch growth proposal accepted for planning."
            ).strip(),
            leaf_specs=[
                f"{proposal_topic_slug}::child_branch_bootstrap",
                f"{proposal_topic_slug}::parent_branch_alignment",
                f"{proposal_topic_slug}::evidence_address",
            ],
            evidence_hints=(
                evidence_start_points
                + list(proposal.get("evidence_start_points", []) or [])
                + [str(item or "").strip() for item in governor.get("evidence_roots", []) or []]
            ),
        )

    objective_summary = (
        "REMGovernor가 읽은 상위 루트를 바탕으로, BranchArchitect가 허정후/송련 축 아래 어떤 가지를 "
        "새로 자라게 할지 또는 어떤 기존 가지를 보강할지 실행 가능한 설계도로 정리합니다."
    )
    if strategy_scope:
        objective_summary += " StrategyCouncil tonight_scope guidance is included in this handoff."
    if strategy_child_branch_proposals:
        objective_summary += f" Child branch growth proposals ({len(strategy_child_branch_proposals)}) are included in this handoff."
    if planning_self_summary:
        objective_summary += f" {planning_self_summary}"
    architect_key = f"{governor_key}::branch_architect_v1"
    handoff_report = _build_architect_handoff_report(
        governor_key,
        architect_key,
        list(governor.get("root_entities", []) or []),
        blueprints,
        create_targets,
        update_targets,
        evidence_start_points,
    )

    return BranchArchitectSchema(
        architect_key=architect_key,
        governor_key=governor_key,
        root_fact_cards=root_fact_cards,
        branch_blueprints=blueprints,
        relay_notes=relay_notes,
        create_targets=dedupe_keep_order(create_targets),
        update_targets=dedupe_keep_order(update_targets),
        evidence_start_points=evidence_start_points[:24],
        objective_summary=objective_summary,
        report_target_phase=str(governor.get("preferred_report_target") or "phase_9"),
        status="active" if handoff_report.get("status") == "ready" else "blocked",
        architect_handoff_report=handoff_report,
    ).model_dump()
