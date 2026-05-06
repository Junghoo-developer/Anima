import re

from Core.night_persistence_utils import link_target_root


def _safe_key_fragment(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"[^0-9a-zA-Z가-힣_.:-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:120] or "unknown"


def persist_branch_growth_header(session, sd_id, branch_growth_report, graph_operations_log):
    if not isinstance(branch_growth_report, dict):
        branch_growth_report = {}

    branch_growth_id = f"{sd_id}::branch_growth"
    session.run(
        """
        MATCH (sd:SecondDream {id: $sd_id})
        MERGE (bg:BranchGrowth {id: $branch_growth_id})
        SET bg.created_at = coalesce(bg.created_at, timestamp()),
            bg.name = '가지 성장 보고',
            bg.batch_id = $sd_id,
            bg.growth_scope = $growth_scope,
            bg.growth_status = $growth_status,
            bg.curated_branches = $curated_branches,
            bg.rejected_branch_paths = $rejected_branch_paths,
            bg.consistency_findings = $consistency_findings,
            bg.rejection_reasons = $rejection_reasons,
            bg.rem_plan_feedback = $rem_plan_feedback,
            bg.governor_feedback = $governor_feedback,
            bg.architect_feedback = $architect_feedback,
            bg.digest_count = toInteger($digest_count),
            bg.branch_pressure_hints = $branch_pressure_hints,
            bg.child_branch_proposal_count = toInteger($child_branch_proposal_count),
            bg.fact_leaf_count = toInteger($fact_leaf_count),
            bg.fact_audit_count = toInteger($fact_audit_count),
            bg.source_fact_pair_count = toInteger($source_fact_pair_count),
            bg.approved_fact_leaf_count = toInteger($approved_fact_leaf_count),
            bg.rejected_fact_leaf_count = toInteger($rejected_fact_leaf_count),
            bg.time_bucket_count = toInteger($time_bucket_count),
            bg.concept_cluster_count = toInteger($concept_cluster_count),
            bg.synthesis_bridge_count = toInteger($synthesis_bridge_count),
            bg.difference_note_count = toInteger($difference_note_count)
        MERGE (sd)-[:CURATES_BRANCH_STRUCTURE]->(bg)
        """,
        sd_id=sd_id,
        branch_growth_id=branch_growth_id,
        growth_scope=str(branch_growth_report.get("growth_scope") or "nightly_branch_curator"),
        growth_status=str(branch_growth_report.get("growth_status") or "ready"),
        curated_branches=list(branch_growth_report.get("curated_branches", []) or []),
        rejected_branch_paths=list(branch_growth_report.get("rejected_branch_paths", []) or []),
        consistency_findings=list(branch_growth_report.get("consistency_findings", []) or []),
        rejection_reasons=list(branch_growth_report.get("rejection_reasons", []) or []),
        rem_plan_feedback=list(branch_growth_report.get("rem_plan_feedback", []) or []),
        governor_feedback=list(branch_growth_report.get("governor_feedback", []) or []),
        architect_feedback=list(branch_growth_report.get("architect_feedback", []) or []),
        digest_count=int(branch_growth_report.get("digest_count", 0) or 0),
        branch_pressure_hints=list(branch_growth_report.get("branch_pressure_hints", []) or []),
        child_branch_proposal_count=int(branch_growth_report.get("child_branch_proposal_count", 0) or 0),
        fact_leaf_count=int(branch_growth_report.get("fact_leaf_count", 0) or 0),
        fact_audit_count=int(branch_growth_report.get("fact_audit_count", 0) or 0),
        source_fact_pair_count=int(branch_growth_report.get("source_fact_pair_count", 0) or 0),
        approved_fact_leaf_count=int(branch_growth_report.get("approved_fact_leaf_count", 0) or 0),
        rejected_fact_leaf_count=int(branch_growth_report.get("rejected_fact_leaf_count", 0) or 0),
        time_bucket_count=int(branch_growth_report.get("time_bucket_count", 0) or 0),
        concept_cluster_count=int(branch_growth_report.get("concept_cluster_count", 0) or 0),
        synthesis_bridge_count=int(branch_growth_report.get("synthesis_bridge_count", 0) or 0),
        difference_note_count=int(branch_growth_report.get("difference_note_count", 0) or 0),
    )
    graph_operations_log.append({"op": "BRANCH_GROWTH", "id": branch_growth_id})
    return branch_growth_id


def persist_time_buckets(session, branch_growth_id, time_buckets, graph_operations_log):
    for bucket in time_buckets or []:
        if not isinstance(bucket, dict):
            continue
        bucket_key = str(bucket.get("bucket_key") or "").strip()
        if not bucket_key:
            continue
        session.run(
            """
            MATCH (bg:BranchGrowth {id: $branch_growth_id})
            MERGE (tb:TimeBucket {bucket_key: $bucket_key})
            SET tb.created_at = coalesce(tb.created_at, timestamp()),
                tb.label = $label,
                tb.time_scope = $time_scope
            MERGE (bg)-[:CURATES]->(tb)
            """,
            branch_growth_id=branch_growth_id,
            bucket_key=bucket_key,
            label=str(bucket.get("label") or "unknown"),
            time_scope=str(bucket.get("time_scope") or "unknown"),
        )
        graph_operations_log.append({"op": "TIME_BUCKET", "key": bucket_key})


def persist_fact_leaves(weaver, session, branch_growth_id, fact_leaves, graph_operations_log):
    for fact in fact_leaves or []:
        if not isinstance(fact, dict):
            continue
        fact_key = str(fact.get("fact_key") or "").strip()
        if not fact_key:
            continue
        branch_path = str(fact.get("branch_path") or "").strip()
        root_entity, _, _ = weaver._branch_root_info(branch_path)
        session.run(
            """
            MATCH (bg:BranchGrowth {id: $branch_growth_id})
            MERGE (fl:FactLeaf {fact_key: $fact_key})
            SET fl.created_at = coalesce(fl.created_at, timestamp()),
                fl.name = $fact_name,
                fl.branch_path = $branch_path,
                fl.root_entity = $root_entity,
                fl.topic_slug = $topic_slug,
                fl.source_address = $source_address,
                fl.source_type = $source_type,
                fl.source_id = $source_id,
                fl.fact_text = $fact_text,
                fl.source_excerpt = $source_excerpt,
                fl.verification_status = $verification_status,
                fl.verification_reason = $verification_reason,
                fl.confidence = toFloat($confidence),
                fl.support_weight = toFloat($support_weight),
                fl.u_purity_score = toFloat($u_purity_score),
                fl.u_support_score = toFloat($u_support_score),
                fl.u_evidence_alignment = toFloat($u_evidence_alignment),
                fl.u_source_prior = toFloat($u_source_prior),
                fl.u_redundancy_support = toFloat($u_redundancy_support),
                fl.u_contradiction_pressure = toFloat($u_contradiction_pressure),
                fl.u_hallucination_risk = toFloat($u_hallucination_risk),
                fl.inverse_relation_hints = $inverse_relation_hints,
                fl.tags = $tags
            MERGE (bg)-[:CURATES]->(fl)
            """,
            branch_growth_id=branch_growth_id,
            fact_key=fact_key,
            fact_name=f"fact::{str(fact.get('topic_slug') or 'unknown').strip()}",
            branch_path=branch_path,
            root_entity=root_entity,
            topic_slug=str(fact.get("topic_slug") or "").strip(),
            source_address=str(fact.get("source_address") or "").strip(),
            source_type=str(fact.get("source_type") or "").strip(),
            source_id=str(fact.get("source_id") or "").strip(),
            fact_text=str(fact.get("fact_text") or "").strip(),
            source_excerpt=str(fact.get("source_excerpt") or "").strip(),
            verification_status=str(fact.get("verification_status") or "approved").strip(),
            verification_reason=str(fact.get("verification_reason") or "").strip(),
            confidence=float(fact.get("confidence", 0.5) or 0.5),
            support_weight=float(fact.get("support_weight", 0.5) or 0.5),
            u_purity_score=float(fact.get("u_purity_score", 0.0) or 0.0),
            u_support_score=float(fact.get("u_support_score", 0.0) or 0.0),
            u_evidence_alignment=float(fact.get("u_evidence_alignment", 0.0) or 0.0),
            u_source_prior=float(fact.get("u_source_prior", 0.0) or 0.0),
            u_redundancy_support=float(fact.get("u_redundancy_support", 0.0) or 0.0),
            u_contradiction_pressure=float(fact.get("u_contradiction_pressure", 0.0) or 0.0),
            u_hallucination_risk=float(fact.get("u_hallucination_risk", 0.0) or 0.0),
            inverse_relation_hints=list(fact.get("inverse_relation_hints", []) or []),
            tags=list(fact.get("tags", []) or []),
        )

        bucket_key = str(fact.get("time_bucket_key") or "").strip()
        if bucket_key:
            session.run(
                """
                MATCH (fl:FactLeaf {fact_key: $fact_key})
                MATCH (tb:TimeBucket {bucket_key: $bucket_key})
                MERGE (fl)-[:IN_TIME_BUCKET]->(tb)
                """,
                fact_key=fact_key,
                bucket_key=bucket_key,
            )

        topic_slug = str(fact.get("topic_slug") or "").strip()
        if topic_slug:
            session.run(
                """
                MATCH (fl:FactLeaf {fact_key: $fact_key})
                MATCH (tt:SupplyTopic {slug: $topic_slug})
                MERGE (fl)-[:ABOUT_TOPIC]->(tt)
                """,
                fact_key=fact_key,
                topic_slug=topic_slug,
            )

        source_address = str(fact.get("source_address") or "").strip()
        source_type = str(fact.get("source_type") or "").strip()
        source_id = str(fact.get("source_id") or "").strip()
        label_map = {"Diary": "Diary", "SongryeonChat": "SongryeonChat", "GeminiChat": "GeminiChat", "PastRecord": "PastRecord"}
        target_label = label_map.get(source_type, "PastRecord")
        if source_address and source_id:
            if re.match(r"^\d{4}-\d{2}-\d{2}$", source_id):
                session.run(
                    f"""
                    MATCH (fl:FactLeaf {{fact_key: $fact_key}})
                    MATCH (r:PastRecord{'' if target_label == 'PastRecord' else ':' + target_label})
                    WHERE coalesce(r.date, '') STARTS WITH $source_id
                    MERGE (fl)-[:EXTRACTED_FROM]->(r)
                    """,
                    fact_key=fact_key,
                    source_id=source_id,
                )
            else:
                session.run(
                    """
                    MATCH (fl:FactLeaf {fact_key: $fact_key})
                    MATCH (r:PastRecord)
                    WHERE elementId(r) = $source_id OR coalesce(r.id, '') = $source_id
                    MERGE (fl)-[:EXTRACTED_FROM]->(r)
                    """,
                    fact_key=fact_key,
                    source_id=source_id,
                )

        if branch_path:
            session.run(
                """
                MATCH (fl:FactLeaf {fact_key: $fact_key})
                MATCH (gb:GovernorBranch {governor_key: 'rem_governor_v1', branch_path: $branch_path})
                MERGE (fl)-[:FOLLOWS_BRANCH]->(gb)
                """,
                fact_key=fact_key,
                branch_path=branch_path,
            )

        link_target_root(
            session,
            "MATCH (fl:FactLeaf {fact_key: $fact_key})",
            "fl",
            {"fact_key": fact_key},
            root_entity,
        )

        for dream_id in fact.get("supporting_dream_ids", []) or []:
            normalized_dream_id = str(dream_id or "").strip()
            if not normalized_dream_id:
                continue
            session.run(
                """
                MATCH (fl:FactLeaf {fact_key: $fact_key})
                MATCH (d:Dream {id: $dream_id})
                MERGE (fl)-[:GROUNDED_IN]->(d)
                """,
                fact_key=fact_key,
                dream_id=normalized_dream_id,
            )

        graph_operations_log.append({"op": "FACT_LEAF", "key": fact_key})


def persist_fact_leaf_audits(session, branch_growth_id, fact_leaf_audits, graph_operations_log):
    for audit in fact_leaf_audits or []:
        if not isinstance(audit, dict):
            continue
        audit_key = str(audit.get("audit_key") or "").strip()
        if not audit_key:
            continue
        fact_key = str(audit.get("fact_key") or "").strip()
        session.run(
            """
            MATCH (bg:BranchGrowth {id: $branch_growth_id})
            MERGE (fa:FactLeafAudit {audit_key: $audit_key})
            SET fa.created_at = coalesce(fa.created_at, timestamp()),
                fa.name = $audit_name,
                fa.fact_key = $fact_key,
                fa.branch_path = $branch_path,
                fa.source_address = $source_address,
                fa.source_type = $source_type,
                fa.source_id = $source_id,
                fa.fact_text = $fact_text,
                fa.verdict = $verdict,
                fa.rejection_reason = $rejection_reason,
                fa.source_pair_key = $source_pair_key
            MERGE (bg)-[:AUDITED_FACT]->(fa)
            """,
            branch_growth_id=branch_growth_id,
            audit_key=audit_key,
            audit_name=f"팩트 검열::{str(audit.get('verdict') or 'unknown')}",
            fact_key=fact_key,
            branch_path=str(audit.get("branch_path") or "").strip(),
            source_address=str(audit.get("source_address") or "").strip(),
            source_type=str(audit.get("source_type") or "").strip(),
            source_id=str(audit.get("source_id") or "").strip(),
            fact_text=str(audit.get("fact_text") or "").strip(),
            verdict=str(audit.get("verdict") or "rejected").strip(),
            rejection_reason=str(audit.get("rejection_reason") or "").strip(),
            source_pair_key=str(audit.get("source_pair_key") or "").strip(),
        )
        if fact_key:
            session.run(
                """
                MATCH (fa:FactLeafAudit {audit_key: $audit_key})
                MATCH (fl:FactLeaf {fact_key: $fact_key})
                MERGE (fa)-[:APPROVES_OR_REJECTS]->(fl)
                """,
                audit_key=audit_key,
                fact_key=fact_key,
            )
        graph_operations_log.append({"op": "FACT_LEAF_AUDIT", "key": audit_key})


def _link_source_fact_pair_to_source(session, pair_key, source_type, source_id, source_address):
    normalized_type = str(source_type or "").strip()
    normalized_id = str(source_id or "").strip()
    normalized_address = str(source_address or "").strip()
    if not normalized_address:
        return

    if normalized_type == "Dream" and normalized_id:
        session.run(
            """
            MATCH (sfp:SourceFactPair {pair_key: $pair_key})
            MATCH (d:Dream {id: $source_id})
            MERGE (sfp)-[:CHECKS_SOURCE]->(d)
            """,
            pair_key=pair_key,
            source_id=normalized_id,
        )
        return

    if normalized_type == "TurnProcess" and normalized_id:
        session.run(
            """
            MATCH (sfp:SourceFactPair {pair_key: $pair_key})
            MATCH (tp:TurnProcess {id: $source_id})
            MERGE (sfp)-[:CHECKS_SOURCE]->(tp)
            """,
            pair_key=pair_key,
            source_id=normalized_id,
        )
        return

    if normalized_type == "FieldMemo" and normalized_id:
        session.run(
            """
            MATCH (sfp:SourceFactPair {pair_key: $pair_key})
            MATCH (fm:FieldMemo {memo_id: $source_id})
            MERGE (sfp)-[:CHECKS_SOURCE]->(fm)
            """,
            pair_key=pair_key,
            source_id=normalized_id,
        )
        return

    if normalized_type == "Phase" and normalized_id:
        parts = normalized_id.split(":")
        process_id = parts[0].strip() if parts else ""
        phase_name = parts[1].strip() if len(parts) > 1 else ""
        if process_id and phase_name:
            session.run(
                """
                MATCH (sfp:SourceFactPair {pair_key: $pair_key})
                MATCH (tp:TurnProcess {id: $process_id})-[hp:HAS_PHASE]->(ps:PhaseSnapshot)
                WHERE ps.phase_name = $phase_name
                MERGE (sfp)-[:CHECKS_SOURCE]->(ps)
                """,
                pair_key=pair_key,
                process_id=process_id,
                phase_name=phase_name,
            )
            return

    if normalized_type in {"Diary", "PastRecord", "SongryeonChat", "GeminiChat"} and normalized_id:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", normalized_id):
            session.run(
                """
                MATCH (sfp:SourceFactPair {pair_key: $pair_key})
                MATCH (r:PastRecord)
                WHERE coalesce(r.date, '') STARTS WITH $source_id
                MERGE (sfp)-[:CHECKS_SOURCE]->(r)
                """,
                pair_key=pair_key,
                source_id=normalized_id,
            )
            return
        session.run(
            """
            MATCH (sfp:SourceFactPair {pair_key: $pair_key})
            MATCH (r:PastRecord)
            WHERE elementId(r) = $source_id OR coalesce(r.id, '') = $source_id
            MERGE (sfp)-[:CHECKS_SOURCE]->(r)
            """,
            pair_key=pair_key,
            source_id=normalized_id,
        )
        return

    session.run(
        """
        MATCH (sfp:SourceFactPair {pair_key: $pair_key})
        MERGE (sr:SourceRef {address: $source_address})
        ON CREATE SET sr.created_at = timestamp()
        MERGE (sfp)-[:CHECKS_SOURCE_REF]->(sr)
        """,
        pair_key=pair_key,
        source_address=normalized_address,
    )


def persist_source_fact_pairs(session, branch_growth_id, source_fact_pairs, graph_operations_log):
    for pair in source_fact_pairs or []:
        if not isinstance(pair, dict):
            continue
        pair_key = str(pair.get("pair_key") or "").strip()
        if not pair_key:
            continue
        fact_key = str(pair.get("fact_key") or "").strip()
        source_type = str(pair.get("source_type") or "").strip()
        source_id = str(pair.get("source_id") or "").strip()
        source_address = str(pair.get("source_address") or "").strip()
        session.run(
            """
            MATCH (bg:BranchGrowth {id: $branch_growth_id})
            MERGE (sfp:SourceFactPair {pair_key: $pair_key})
            SET sfp.created_at = coalesce(sfp.created_at, timestamp()),
                sfp.name = '원본-팩트 검증쌍',
                sfp.fact_key = $fact_key,
                sfp.branch_path = $branch_path,
                sfp.source_address = $source_address,
                sfp.source_type = $source_type,
                sfp.source_id = $source_id,
                sfp.fact_text = $fact_text,
                sfp.source_excerpt = $source_excerpt,
                sfp.pair_status = $pair_status,
                sfp.verifier_name = $verifier_name,
                sfp.verifier_confidence = toFloat($verifier_confidence),
                sfp.mismatch_reason = $mismatch_reason
            MERGE (bg)-[:CHECKED_SOURCE_FACT]->(sfp)
            """,
            branch_growth_id=branch_growth_id,
            pair_key=pair_key,
            fact_key=fact_key,
            branch_path=str(pair.get("branch_path") or "").strip(),
            source_address=source_address,
            source_type=source_type,
            source_id=source_id,
            fact_text=str(pair.get("fact_text") or "").strip(),
            source_excerpt=str(pair.get("source_excerpt") or "").strip(),
            pair_status=str(pair.get("pair_status") or "rejected").strip(),
            verifier_name=str(pair.get("verifier_name") or "phase11_fact_pair_guard").strip(),
            verifier_confidence=float(pair.get("verifier_confidence", 0.0) or 0.0),
            mismatch_reason=str(pair.get("mismatch_reason") or "").strip(),
        )
        if fact_key:
            session.run(
                """
                MATCH (sfp:SourceFactPair {pair_key: $pair_key})
                MATCH (fl:FactLeaf {fact_key: $fact_key})
                MERGE (sfp)-[:CHECKS_FACT]->(fl)
                """,
                pair_key=pair_key,
                fact_key=fact_key,
            )
        _link_source_fact_pair_to_source(session, pair_key, source_type, source_id, source_address)
        graph_operations_log.append({"op": "SOURCE_FACT_PAIR", "key": pair_key})


def persist_concept_clusters(weaver, session, branch_growth_id, concept_clusters, graph_operations_log):
    for cluster in concept_clusters or []:
        if not isinstance(cluster, dict):
            continue
        cluster_key = str(cluster.get("cluster_key") or "").strip()
        if not cluster_key:
            continue
        branch_path = str(cluster.get("branch_path") or "").strip()
        root_entity, _, _ = weaver._branch_root_info(branch_path)
        attention_text = weaver._strategy_cluster_attention_text(cluster)
        attention_embedding = weaver._strategy_embed_text(attention_text)
        session.run(
            """
            MATCH (bg:BranchGrowth {id: $branch_growth_id})
            MERGE (cc:ConceptCluster {cluster_key: $cluster_key})
            SET cc.created_at = coalesce(cc.created_at, timestamp()),
                cc.name = $title,
                cc.title = $title,
                cc.summary = $summary,
                cc.branch_path = $branch_path,
                cc.root_entity = $root_entity,
                cc.topic_slug = $topic_slug,
                cc.support_weight = toFloat($support_weight),
                cc.u_cluster_purity = toFloat($u_cluster_purity),
                cc.u_coherence_score = toFloat($u_coherence_score),
                cc.u_tension_score = toFloat($u_tension_score),
                cc.u_synthesis_score = toFloat($u_synthesis_score),
                cc.thesis_fact_keys = $thesis_fact_keys,
                cc.antithesis_fact_keys = $antithesis_fact_keys,
                cc.synthesis_statement = $synthesis_statement,
                cc.inverse_relation_updates = $inverse_relation_updates,
                cc.tags = $tags,
                cc.attention_text = $attention_text,
                cc.attention_embedding = $attention_embedding
            MERGE (bg)-[:CURATES]->(cc)
            """,
            branch_growth_id=branch_growth_id,
            cluster_key=cluster_key,
            title=str(cluster.get("title") or cluster_key),
            summary=str(cluster.get("summary") or ""),
            branch_path=branch_path,
            root_entity=root_entity,
            topic_slug=str(cluster.get("topic_slug") or "").strip(),
            support_weight=float(cluster.get("support_weight", 0.5) or 0.5),
            u_cluster_purity=float(cluster.get("u_cluster_purity", 0.0) or 0.0),
            u_coherence_score=float(cluster.get("u_coherence_score", 0.0) or 0.0),
            u_tension_score=float(cluster.get("u_tension_score", 0.0) or 0.0),
            u_synthesis_score=float(cluster.get("u_synthesis_score", 0.0) or 0.0),
            thesis_fact_keys=list(cluster.get("thesis_fact_keys", []) or []),
            antithesis_fact_keys=list(cluster.get("antithesis_fact_keys", []) or []),
            synthesis_statement=str(cluster.get("synthesis_statement") or "").strip(),
            inverse_relation_updates=list(cluster.get("inverse_relation_updates", []) or []),
            tags=list(cluster.get("tags", []) or []),
            attention_text=attention_text,
            attention_embedding=attention_embedding,
        )
        if branch_path:
            session.run(
                """
                MATCH (cc:ConceptCluster {cluster_key: $cluster_key})
                MATCH (gb:GovernorBranch {governor_key: 'rem_governor_v1', branch_path: $branch_path})
                MERGE (cc)-[:FOLLOWS_BRANCH]->(gb)
                """,
                cluster_key=cluster_key,
                branch_path=branch_path,
            )
        topic_slug = str(cluster.get("topic_slug") or "").strip()
        if topic_slug:
            session.run(
                """
                MATCH (cc:ConceptCluster {cluster_key: $cluster_key})
                MATCH (tt:SupplyTopic {slug: $topic_slug})
                MERGE (cc)-[:SUMMARIZES_TOPIC]->(tt)
                """,
                cluster_key=cluster_key,
                topic_slug=topic_slug,
            )
        link_target_root(
            session,
            "MATCH (cc:ConceptCluster {cluster_key: $cluster_key})",
            "cc",
            {"cluster_key": cluster_key},
            root_entity,
        )
        for fact_key in cluster.get("fact_keys", []) or []:
            normalized_fact_key = str(fact_key or "").strip()
            if not normalized_fact_key:
                continue
            session.run(
                """
                MATCH (cc:ConceptCluster {cluster_key: $cluster_key})
                MATCH (fl:FactLeaf {fact_key: $fact_key})
                MERGE (cc)-[:ABSTRACTS]->(fl)
                """,
                cluster_key=cluster_key,
                fact_key=normalized_fact_key,
            )
        for bucket_key in cluster.get("time_bucket_keys", []) or []:
            normalized_bucket_key = str(bucket_key or "").strip()
            if not normalized_bucket_key:
                continue
            session.run(
                """
                MATCH (cc:ConceptCluster {cluster_key: $cluster_key})
                MATCH (tb:TimeBucket {bucket_key: $bucket_key})
                MERGE (cc)-[:USES_TIME_BUCKET]->(tb)
                """,
                cluster_key=cluster_key,
                bucket_key=normalized_bucket_key,
            )
        for idx, update_text in enumerate(cluster.get("inverse_relation_updates", []) or [], start=1):
            normalized_update = str(update_text or "").strip()
            if not normalized_update:
                continue
            update_key = f"inverse_relation_update::{_safe_key_fragment(cluster_key)}::{idx}"
            session.run(
                """
                MATCH (cc:ConceptCluster {cluster_key: $cluster_key})
                MERGE (iru:InverseRelationUpdate {update_key: $update_key})
                SET iru.created_at = coalesce(iru.created_at, timestamp()),
                    iru.name = 'inverse relation update',
                    iru.branch_path = $branch_path,
                    iru.root_entity = $root_entity,
                    iru.topic_slug = $topic_slug,
                    iru.update_text = $update_text,
                    iru.u_cluster_purity = toFloat($u_cluster_purity),
                    iru.u_synthesis_score = toFloat($u_synthesis_score)
                MERGE (cc)-[:SUGGESTS_INVERSE_RELATION]->(iru)
                """,
                cluster_key=cluster_key,
                update_key=update_key,
                branch_path=branch_path,
                root_entity=root_entity,
                topic_slug=topic_slug,
                update_text=normalized_update,
                u_cluster_purity=float(cluster.get("u_cluster_purity", 0.0) or 0.0),
                u_synthesis_score=float(cluster.get("u_synthesis_score", 0.0) or 0.0),
            )
            graph_operations_log.append({"op": "INVERSE_RELATION_UPDATE", "key": update_key})
        graph_operations_log.append({"op": "CONCEPT_CLUSTER", "key": cluster_key})


def persist_synthesis_bridges(weaver, session, branch_growth_id, synthesis_bridges, graph_operations_log):
    for bridge in synthesis_bridges or []:
        if not isinstance(bridge, dict):
            continue
        bridge_key = str(bridge.get("bridge_key") or "").strip()
        if not bridge_key:
            continue
        branch_path = str(bridge.get("branch_path") or "").strip()
        root_entity, _, _ = weaver._branch_root_info(branch_path)
        session.run(
            """
            MATCH (bg:BranchGrowth {id: $branch_growth_id})
            MERGE (sb:SynthesisBridgeThought {bridge_key: $bridge_key})
            SET sb.created_at = coalesce(sb.created_at, timestamp()),
                sb.name = $title,
                sb.title = $title,
                sb.bridge_thought = $bridge_thought,
                sb.branch_path = $branch_path,
                sb.root_entity = $root_entity,
                sb.topic_slug = $topic_slug,
                sb.support_weight = toFloat($support_weight),
                sb.u_synthesis_score = toFloat($u_synthesis_score)
            MERGE (bg)-[:CURATES]->(sb)
            """,
            branch_growth_id=branch_growth_id,
            bridge_key=bridge_key,
            title=str(bridge.get("title") or bridge_key),
            bridge_thought=str(bridge.get("bridge_thought") or ""),
            branch_path=branch_path,
            root_entity=root_entity,
            topic_slug=str(bridge.get("topic_slug") or "").strip(),
            support_weight=float(bridge.get("support_weight", 0.5) or 0.5),
            u_synthesis_score=float(bridge.get("u_synthesis_score", 0.0) or 0.0),
        )
        if branch_path:
            session.run(
                """
                MATCH (sb:SynthesisBridgeThought {bridge_key: $bridge_key})
                MATCH (gb:GovernorBranch {governor_key: 'rem_governor_v1', branch_path: $branch_path})
                MERGE (sb)-[:FOLLOWS_BRANCH]->(gb)
                """,
                bridge_key=bridge_key,
                branch_path=branch_path,
            )
        link_target_root(
            session,
            "MATCH (sb:SynthesisBridgeThought {bridge_key: $bridge_key})",
            "sb",
            {"bridge_key": bridge_key},
            root_entity,
        )
        cluster_key = str(bridge.get("cluster_key") or "").strip()
        if cluster_key:
            session.run(
                """
                MATCH (sb:SynthesisBridgeThought {bridge_key: $bridge_key})
                MATCH (cc:ConceptCluster {cluster_key: $cluster_key})
                MERGE (sb)-[:SUPPORTS]->(cc)
                """,
                bridge_key=bridge_key,
                cluster_key=cluster_key,
            )
        for fact_key in bridge.get("supporting_fact_keys", []) or []:
            normalized_fact_key = str(fact_key or "").strip()
            if not normalized_fact_key:
                continue
            session.run(
                """
                MATCH (sb:SynthesisBridgeThought {bridge_key: $bridge_key})
                MATCH (fl:FactLeaf {fact_key: $fact_key})
                MERGE (sb)-[:GROUNDED_IN]->(fl)
                """,
                bridge_key=bridge_key,
                fact_key=normalized_fact_key,
            )
        graph_operations_log.append({"op": "SYNTHESIS_BRIDGE", "key": bridge_key})


def persist_difference_notes(weaver, session, branch_growth_id, difference_notes, graph_operations_log):
    for note in difference_notes or []:
        if not isinstance(note, dict):
            continue
        note_key = str(note.get("note_key") or "").strip()
        if not note_key:
            continue
        branch_path = str(note.get("branch_path") or "").strip()
        root_entity, _, _ = weaver._branch_root_info(branch_path)
        session.run(
            """
            MATCH (bg:BranchGrowth {id: $branch_growth_id})
            MERGE (dn:DifferenceNote {note_key: $note_key})
            SET dn.created_at = coalesce(dn.created_at, timestamp()),
                dn.name = $title,
                dn.title = $title,
                dn.summary = $summary,
                dn.branch_path = $branch_path,
                dn.root_entity = $root_entity,
                dn.topic_slug = $topic_slug,
                dn.contrast_axis = $contrast_axis,
                dn.support_weight = toFloat($support_weight),
                dn.u_tension_score = toFloat($u_tension_score)
            MERGE (bg)-[:CURATES]->(dn)
            """,
            branch_growth_id=branch_growth_id,
            note_key=note_key,
            title=str(note.get("title") or note_key),
            summary=str(note.get("summary") or ""),
            branch_path=branch_path,
            root_entity=root_entity,
            topic_slug=str(note.get("topic_slug") or "").strip(),
            contrast_axis=str(note.get("contrast_axis") or "").strip(),
            support_weight=float(note.get("support_weight", 0.5) or 0.5),
            u_tension_score=float(note.get("u_tension_score", 0.0) or 0.0),
        )
        if branch_path:
            session.run(
                """
                MATCH (dn:DifferenceNote {note_key: $note_key})
                MATCH (gb:GovernorBranch {governor_key: 'rem_governor_v1', branch_path: $branch_path})
                MERGE (dn)-[:FOLLOWS_BRANCH]->(gb)
                """,
                note_key=note_key,
                branch_path=branch_path,
            )
        link_target_root(
            session,
            "MATCH (dn:DifferenceNote {note_key: $note_key})",
            "dn",
            {"note_key": note_key},
            root_entity,
        )
        for fact_key in note.get("compared_fact_keys", []) or []:
            normalized_fact_key = str(fact_key or "").strip()
            if not normalized_fact_key:
                continue
            session.run(
                """
                MATCH (dn:DifferenceNote {note_key: $note_key})
                MATCH (fl:FactLeaf {fact_key: $fact_key})
                MERGE (dn)-[:COMPARES]->(fl)
                """,
                note_key=note_key,
                fact_key=normalized_fact_key,
            )
        for bucket_key in note.get("compared_time_bucket_keys", []) or []:
            normalized_bucket_key = str(bucket_key or "").strip()
            if not normalized_bucket_key:
                continue
            session.run(
                """
                MATCH (dn:DifferenceNote {note_key: $note_key})
                MATCH (tb:TimeBucket {bucket_key: $bucket_key})
                MERGE (dn)-[:COMPARES]->(tb)
                """,
                note_key=note_key,
                bucket_key=normalized_bucket_key,
            )
        graph_operations_log.append({"op": "DIFFERENCE_NOTE", "key": note_key})


def persist_child_branch_proposals(weaver, session, branch_growth_id, child_branch_proposals, graph_operations_log):
    for proposal in child_branch_proposals or []:
        if not isinstance(proposal, dict):
            continue
        proposal_key = str(proposal.get("proposal_key") or "").strip()
        proposed_branch_path = str(proposal.get("proposed_branch_path") or "").strip()
        parent_branch_path = str(proposal.get("parent_branch_path") or "").strip()
        root_entity = str(proposal.get("root_entity") or weaver._root_entity_from_asset_scope(parent_branch_path)).strip()
        if not proposal_key or not proposed_branch_path:
            continue
        session.run(
            """
            MATCH (bg:BranchGrowth {id: $branch_growth_id})
            MERGE (cbp:ChildBranchProposal {proposal_key: $proposal_key})
            SET cbp.created_at = coalesce(cbp.created_at, timestamp()),
                cbp.name = $proposal_name,
                cbp.parent_branch_path = $parent_branch_path,
                cbp.proposed_branch_path = $proposed_branch_path,
                cbp.root_entity = $root_entity,
                cbp.topic_slug = $topic_slug,
                cbp.proposal_reason = $proposal_reason,
                cbp.pressure_score = toFloat($pressure_score),
                cbp.evidence_start_points = $evidence_start_points,
                cbp.trigger_notes = $trigger_notes,
                cbp.status = $status
            MERGE (bg)-[:CURATES]->(cbp)
            """,
            branch_growth_id=branch_growth_id,
            proposal_key=proposal_key,
            proposal_name=weaver._branch_title_ko(proposed_branch_path) or proposed_branch_path,
            parent_branch_path=parent_branch_path,
            proposed_branch_path=proposed_branch_path,
            root_entity=root_entity,
            topic_slug=str(proposal.get("topic_slug") or "").strip(),
            proposal_reason=str(proposal.get("proposal_reason") or ""),
            pressure_score=float(proposal.get("pressure_score", 0.5) or 0.5),
            evidence_start_points=list(proposal.get("evidence_start_points", []) or []),
            trigger_notes=list(proposal.get("trigger_notes", []) or []),
            status=str(proposal.get("status") or "proposed"),
        )
        if parent_branch_path:
            session.run(
                """
                MATCH (cbp:ChildBranchProposal {proposal_key: $proposal_key})
                MATCH (gb:GovernorBranch {governor_key: 'rem_governor_v1', branch_path: $parent_branch_path})
                MERGE (cbp)-[:EXTENDS_BRANCH]->(gb)
                """,
                proposal_key=proposal_key,
                parent_branch_path=parent_branch_path,
            )
        link_target_root(
            session,
            "MATCH (cbp:ChildBranchProposal {proposal_key: $proposal_key})",
            "cbp",
            {"proposal_key": proposal_key},
            root_entity,
        )
        graph_operations_log.append({"op": "CHILD_BRANCH_PROPOSAL", "key": proposal_key})


def persist_strategy_attention(session, strategy_council, graph_operations_log):
    if not isinstance(strategy_council, dict) or not strategy_council:
        return
    strategy_key = str(strategy_council.get("strategy_key") or "strategy_council_v1").strip() or "strategy_council_v1"
    for item in strategy_council.get("attention_shortlist", []) or []:
        if not isinstance(item, dict):
            continue
        asset_type = str(item.get("asset_type") or "branch_digest").strip() or "branch_digest"
        asset_key = str(item.get("asset_key") or item.get("digest_key") or item.get("cluster_key") or "").strip()
        if not asset_key:
            continue
        common_params = dict(
            strategy_key=strategy_key,
            attention_score=float(item.get("final_score", 0.0) or 0.0),
            semantic_score=float(item.get("semantic_score", 0.0) or 0.0),
            lexical_score=float(item.get("lexical_score", 0.0) or 0.0),
            support_score=float(item.get("support_score", 0.0) or 0.0),
            pressure_score=float(item.get("pressure_score", 0.0) or 0.0),
            why_now=str(item.get("why_now") or ""),
        )
        if asset_type == "concept_cluster":
            session.run(
                """
                MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})
                MATCH (cc:ConceptCluster {cluster_key: $cluster_key})
                MERGE (sc)-[r:ATTENDS_TO_CLUSTER]->(cc)
                SET r.attention_score = toFloat($attention_score),
                    r.semantic_score = toFloat($semantic_score),
                    r.lexical_score = toFloat($lexical_score),
                    r.support_score = toFloat($support_score),
                    r.pressure_score = toFloat($pressure_score),
                    r.why_now = $why_now,
                    r.updated_at = timestamp()
                """,
                cluster_key=asset_key,
                **common_params,
            )
        else:
            session.run(
                """
                MATCH (sc:StrategyCouncil {strategy_key: $strategy_key})
                MATCH (bd:BranchDigest {digest_key: $digest_key})
                MERGE (sc)-[r:ATTENDS_TO_DIGEST]->(bd)
                SET r.attention_score = toFloat($attention_score),
                    r.semantic_score = toFloat($semantic_score),
                    r.lexical_score = toFloat($lexical_score),
                    r.support_score = toFloat($support_score),
                    r.pressure_score = toFloat($pressure_score),
                    r.why_now = $why_now,
                    r.updated_at = timestamp()
                """,
                digest_key=asset_key,
                **common_params,
            )
        graph_operations_log.append({"op": "STRATEGY_ATTENTION", "asset_type": asset_type, "asset_key": asset_key})


def persist_branch_digests(weaver, session, sd_id, branch_growth_id, branch_digests, graph_operations_log):
    for digest in branch_digests or []:
        if not isinstance(digest, dict):
            continue
        digest_key = str(digest.get("digest_key") or "").strip()
        if not digest_key:
            continue
        branch_path = str(digest.get("branch_path") or "").strip()
        root_entity, root_name_ko, root_rank = weaver._branch_root_info(branch_path)
        attention_text = weaver._strategy_digest_attention_text(digest)
        attention_embedding = weaver._strategy_embed_text(attention_text)
        session.run(
            """
            MATCH (bg:BranchGrowth {id: $branch_growth_id})
            MERGE (bd:BranchDigest {digest_key: $digest_key})
            SET bd.created_at = coalesce(bd.created_at, timestamp()),
                bd.name = $title,
                bd.batch_id = $sd_id,
                bd.branch_path = $branch_path,
                bd.title = $title,
                bd.summary = $summary,
                bd.root_entity = $root_entity,
                bd.root_name_ko = $root_name_ko,
                bd.root_rank = toInteger($root_rank),
                bd.related_topics = $related_topics,
                bd.evidence_addresses = $evidence_addresses,
                bd.supporting_dream_ids = $supporting_dream_ids,
                bd.attached_tactic_ids = $attached_tactic_ids,
                bd.attached_policy_keys = $attached_policy_keys,
                bd.attached_doctrine_keys = $attached_doctrine_keys,
                bd.attention_text = $attention_text,
                bd.attention_embedding = $attention_embedding,
                bd.status = $status
            MERGE (bg)-[:CURATES]->(bd)
            """,
            branch_growth_id=branch_growth_id,
            sd_id=sd_id,
            digest_key=digest_key,
            branch_path=branch_path,
            title=str(digest.get("title") or ""),
            summary=str(digest.get("summary") or ""),
            root_entity=root_entity,
            root_name_ko=root_name_ko,
            root_rank=root_rank,
            related_topics=list(digest.get("related_topics", []) or []),
            evidence_addresses=list(digest.get("evidence_addresses", []) or []),
            supporting_dream_ids=list(digest.get("supporting_dream_ids", []) or []),
            attached_tactic_ids=list(digest.get("attached_tactic_ids", []) or []),
            attached_policy_keys=list(digest.get("attached_policy_keys", []) or []),
            attached_doctrine_keys=list(digest.get("attached_doctrine_keys", []) or []),
            attention_text=attention_text,
            attention_embedding=attention_embedding,
            status=str(digest.get("status") or "active"),
        )
        session.run(
            """
            MATCH (bd:BranchDigest {digest_key: $digest_key})
            MATCH (sd:SecondDream {id: $sd_id})
            MERGE (bd)-[:GROUNDED_IN]->(sd)
            """,
            digest_key=digest_key,
            sd_id=sd_id,
        )
        if branch_path:
            session.run(
                """
                MATCH (bd:BranchDigest {digest_key: $digest_key})
                MATCH (gb:GovernorBranch {governor_key: 'rem_governor_v1', branch_path: $branch_path})
                MERGE (bd)-[:FOLLOWS_BRANCH]->(gb)
                """,
                digest_key=digest_key,
                branch_path=branch_path,
            )
        link_target_root(
            session,
            "MATCH (bd:BranchDigest {digest_key: $digest_key})",
            "bd",
            {"digest_key": digest_key},
            root_entity,
        )

        for topic_slug in digest.get("related_topics", []) or []:
            normalized_topic_slug = str(topic_slug or "").strip()
            if not normalized_topic_slug:
                continue
            session.run(
                """
                MATCH (bd:BranchDigest {digest_key: $digest_key})
                MATCH (tt:SupplyTopic {slug: $topic_slug})
                MERGE (bd)-[:SUMMARIZES_TOPIC]->(tt)
                """,
                digest_key=digest_key,
                topic_slug=normalized_topic_slug,
            )

        for dream_id in digest.get("supporting_dream_ids", []) or []:
            normalized_dream_id = str(dream_id or "").strip()
            if not normalized_dream_id:
                continue
            session.run(
                """
                MATCH (bd:BranchDigest {digest_key: $digest_key})
                MATCH (d:Dream {id: $dream_id})
                MERGE (bd)-[:GROUNDED_IN]->(d)
                """,
                digest_key=digest_key,
                dream_id=normalized_dream_id,
            )

        for policy_key in digest.get("attached_policy_keys", []) or []:
            normalized_policy_key = str(policy_key or "").strip()
            if not normalized_policy_key:
                continue
            session.run(
                """
                MATCH (bd:BranchDigest {digest_key: $digest_key})
                MATCH (rp:RoutePolicy {policy_key: $policy_key})
                MERGE (bd)-[:LINKS_POLICY]->(rp)
                """,
                digest_key=digest_key,
                policy_key=normalized_policy_key,
            )

        for tactic_key in digest.get("attached_tactic_ids", []) or []:
            normalized_tactic_key = str(tactic_key or "").strip()
            if not normalized_tactic_key:
                continue
            session.run(
                """
                MATCH (bd:BranchDigest {digest_key: $digest_key})
                MATCH (t:TacticalThought {id: $tactic_key})
                MERGE (bd)-[:LINKS_TACTIC]->(t)
                """,
                digest_key=digest_key,
                tactic_key=normalized_tactic_key,
            )

        for doctrine_key in digest.get("attached_doctrine_keys", []) or []:
            normalized_doctrine_key = str(doctrine_key or "").strip()
            if not normalized_doctrine_key:
                continue
            session.run(
                """
                MATCH (bd:BranchDigest {digest_key: $digest_key})
                MATCH (td:ToolDoctrine {doctrine_key: $doctrine_key})
                MERGE (bd)-[:LINKS_DOCTRINE]->(td)
                """,
                digest_key=digest_key,
                doctrine_key=normalized_doctrine_key,
            )

        graph_operations_log.append({"op": "BRANCH_DIGEST", "key": digest_key})
