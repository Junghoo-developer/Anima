import json
import pymysql
import os
from datetime import datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase # 👈 [신규 투입!] 진짜 뇌(Neo4j)로 향하는 신경망 접속기!

from Core.memory.memory_sanitizer import sanitize_durable_turn_record, sanitize_memory_trace_value

load_dotenv()

# 🛡️ 1. 안전 자산(MySQL) 연결 설정
DB_CONFIG = {
    'host': os.getenv("DB_HOST", 'localhost'),
    'port': int(os.getenv("DB_PORT", 3306)),
    'user': os.getenv("DB_USER", 'root'),
    'password': os.getenv("DB_PASS"),
    'db': os.getenv("DB_NAME", 'songryeon_db'),
    'charset': 'utf8mb4'
}

# 🧠 2. 진짜 뇌(Neo4j) 연결 설정
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class InferenceBuffer:
    def __init__(self):
        """
        [롤링 메모리 버퍼 및 듀얼 DB 라이터]
        """
        self.final_scratchpad = "" 
        # 👇 Neo4j 드라이버 시동!
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def clear(self):
        """작전이 끝나면 다음 턴을 위해 칠판을 물로 씻어냅네다."""
        self.final_scratchpad = ""

    # 👇 trace_data 파라미터가 추가되었습네다!
    def save_dream_to_db(self, user_input, final_answer, user_emotion, biolink_status, trace_data=None):
        """
        [송련의 꿈(사고 과정) 듀얼 라이팅 영구 보존]
        MySQL에는 안전하게 JSON으로 통째로 백업하고,
        Neo4j에는 검색과 학습을 위해 배열(Array) 속성으로 예쁘게 쪼개서 각인합네다!
        """
        if trace_data is None:
            trace_data = {}
        trace_data = sanitize_memory_trace_value(trace_data, key="trace_data")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Dream slim v1: the new execution path below returns early after
        # writing lean Dream / TurnProcess / PhaseSnapshot records.
        dream_id_str = datetime.now().strftime("%Y%m%d_%H%M%S") # Neo4j 고유 ID용

        canonical_turn = trace_data.get("canonical_turn", {}) if isinstance(trace_data.get("canonical_turn"), dict) else {}
        dream_record = trace_data.get("dream_record", {}) if isinstance(trace_data.get("dream_record"), dict) else {}
        turn_process = trace_data.get("turn_process", {}) if isinstance(trace_data.get("turn_process"), dict) else {}
        phase_snapshots = trace_data.get("phase_snapshots", []) if isinstance(trace_data.get("phase_snapshots"), list) else []

        if not dream_record and canonical_turn:
            dream_record = canonical_turn.get("dream_record", {}) if isinstance(canonical_turn.get("dream_record"), dict) else {}
        if not turn_process and canonical_turn:
            turn_process = canonical_turn.get("turn_process", {}) if isinstance(canonical_turn.get("turn_process"), dict) else {}
        if not phase_snapshots and canonical_turn:
            phase_snapshots = canonical_turn.get("phase_snapshots", []) if isinstance(canonical_turn.get("phase_snapshots"), list) else []
        dream_record = sanitize_durable_turn_record(dream_record)
        turn_process = sanitize_durable_turn_record(turn_process)
        phase_snapshots = sanitize_memory_trace_value(phase_snapshots, key="phase_snapshots") if isinstance(phase_snapshots, list) else []

        process_id = str(turn_process.get("process_id") or f"{dream_id_str}_process").strip()
        legacy_phase2 = {
            "raw_read_report": trace_data.get("raw_read_report", {}),
            "analysis_report": trace_data.get("analysis_report", {}),
            "used_sources": trace_data.get("used_sources", []),
        }

        def _safe_snapshot_id(phase_name: str, phase_order: int):
            safe_name = "".join(ch if ch.isalnum() else "_" for ch in str(phase_name or "").strip()) or "phase"
            return f"{process_id}_{phase_order}_{safe_name}"[:500]

        cognitive_process_data = {
            "user_input": user_input,
            "user_emotion": user_emotion,
            "biolink_status": biolink_status,
            "trace_data": trace_data
        }
        cognitive_json_str = json.dumps(cognitive_process_data, ensure_ascii=False)

        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            sql_create = """
            CREATE TABLE IF NOT EXISTS agent_dreams (
                dream_id INT AUTO_INCREMENT PRIMARY KEY,
                created_at DATETIME,
                cognitive_process JSON,
                final_answer TEXT
            )
            """
            cursor.execute(sql_create)
            sql_insert = """
            INSERT INTO agent_dreams (created_at, cognitive_process, final_answer)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql_insert, (timestamp, cognitive_json_str, final_answer))
            conn.commit()
            print("💾 [안전 자산] MySQL 금고에 사고 기록이 안전하게 백업되었습네다!")
        except Exception as e:
            print(f"💥 MySQL 백업 실패: {e}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

        cypher_dream = """
        MERGE (d:Dream {id: $dream_id})
        SET d.date = $timestamp,
            d.schema_version = $schema_version,
            d.user_input = $user_input,
            d.final_answer = $final_answer,
            d.user_emotion = $user_emotion,
            d.turn_summary = $turn_summary,
            d.user_dialogue_act = $user_dialogue_act,
            d.active_task = $active_task,
            d.active_offer = $active_offer,
            d.requested_move = $requested_move,
            d.answer_shape = $answer_shape,
            d.reply_mode = $reply_mode,
            d.verdict_action = $verdict_action,
            d.investigation_status = $investigation_status,
            d.delivery_status = $delivery_status,
            d.used_sources = $used_sources,
            d.process_id = $process_id,
            d.phase_minus1_intent = $p_minus1_intent,
            d.phase_0_history = $p0_history,
            d.phase_1_actions = $p1_history,
            d.phase_2_summaries = $p2_history,
            d.phase_3_summary = $p3_summary
        """

        cypher_process = """
        MATCH (d:Dream {id: $dream_id})
        MERGE (tp:TurnProcess {id: $process_id})
        SET tp.date = $timestamp,
            tp.schema_version = $schema_version,
            tp.process_kind = $process_kind,
            tp.turn_summary = $turn_summary,
            tp.active_task = $active_task,
            tp.active_offer = $active_offer,
            tp.requested_move = $requested_move,
            tp.answer_shape = $answer_shape,
            tp.loop_count = toInteger($loop_count),
            tp.reasoning_budget = toInteger($reasoning_budget),
            tp.delivery_status = $delivery_status,
            tp.execution_status = $execution_status,
            tp.execution_block_reason = $execution_block_reason,
            tp.operation_kind = $operation_kind,
            tp.target_scope = $target_scope,
            tp.executed_tool = $executed_tool,
            tp.used_sources = $used_sources,
            tp.field_status_json = $field_status_json,
            tp.handoff_summary_json = $handoff_summary_json,
            tp.process_summary_json = $process_summary_json,
            tp.dream_id = $dream_id
        MERGE (d)-[:HAS_PROCESS]->(tp)
        """

        cypher_phase = """
        MATCH (tp:TurnProcess {id: $process_id})
        MERGE (ps:PhaseSnapshot {id: $snapshot_id})
        SET ps.phase_name = $phase_name,
            ps.phase_order = toInteger($phase_order),
            ps.status = $status,
            ps.summary = $summary,
            ps.summary_json = $summary_json,
            ps.dream_id = $dream_id,
            ps.created_at = coalesce(ps.created_at, timestamp())
        MERGE (tp)-[r:HAS_PHASE]->(ps)
        SET r.phase_order = toInteger($phase_order)
        """

        try:
            with self.neo4j_driver.session() as session:
                session.run(
                    cypher_dream,
                    dream_id=dream_id_str,
                    timestamp=timestamp,
                    schema_version=str(dream_record.get("schema_version") or "dream_v3"),
                    user_input=user_input,
                    final_answer=final_answer,
                    user_emotion=user_emotion,
                    turn_summary=str(dream_record.get("turn_summary") or ""),
                    user_dialogue_act=str(dream_record.get("user_dialogue_act") or ""),
                    active_task=str(dream_record.get("active_task") or ""),
                    active_offer=str(dream_record.get("active_offer") or ""),
                    requested_move=str(dream_record.get("requested_move") or ""),
                    answer_shape=str(dream_record.get("answer_shape") or ""),
                    reply_mode=str(dream_record.get("reply_mode") or ""),
                    verdict_action=str(dream_record.get("verdict_action") or ""),
                    investigation_status=str(dream_record.get("investigation_status") or ""),
                    delivery_status=str(dream_record.get("delivery_status") or ""),
                    used_sources=list(dream_record.get("used_sources", [])) if isinstance(dream_record.get("used_sources"), list) else [],
                    process_id=process_id,
                    p_minus1_intent=json.dumps(
                        trace_data.get("start_gate_review")
                        or trace_data.get("response_strategy")
                        or {"legacy_thought_logs": trace_data.get("thought_logs", [])},
                        ensure_ascii=False,
                    ),
                    p0_history=json.dumps(
                        {
                            "messages": trace_data.get("messages", []),
                            "ops_decision": trace_data.get("ops_decision", {}),
                        },
                        ensure_ascii=False,
                    ),
                    p1_history=trace_data.get("executed_actions", []),
                    p2_history=json.dumps(legacy_phase2, ensure_ascii=False),
                    p3_summary=final_answer,
                )

                session.run(
                    cypher_process,
                    dream_id=dream_id_str,
                    process_id=process_id,
                    timestamp=timestamp,
                    schema_version=str(turn_process.get("schema_version") or "turn_process_v1"),
                    process_kind=str(turn_process.get("process_kind") or "field_turn_pipeline"),
                    turn_summary=str(turn_process.get("turn_summary") or ""),
                    active_task=str(turn_process.get("active_task") or ""),
                    active_offer=str(turn_process.get("active_offer") or ""),
                    requested_move=str(turn_process.get("requested_move") or ""),
                    answer_shape=str(turn_process.get("answer_shape") or ""),
                    loop_count=int(turn_process.get("loop_count", 0) or 0),
                    reasoning_budget=int(turn_process.get("reasoning_budget", 0) or 0),
                    delivery_status=str(turn_process.get("delivery_status") or ""),
                    execution_status=str(turn_process.get("execution_status") or ""),
                    execution_block_reason=str(turn_process.get("execution_block_reason") or ""),
                    operation_kind=str(turn_process.get("operation_kind") or ""),
                    target_scope=str(turn_process.get("target_scope") or ""),
                    executed_tool=str(turn_process.get("executed_tool") or ""),
                    used_sources=list(turn_process.get("used_sources", [])) if isinstance(turn_process.get("used_sources"), list) else [],
                    field_status_json=json.dumps(turn_process.get("field_status", {}), ensure_ascii=False),
                    handoff_summary_json=json.dumps(turn_process.get("handoff_summary", {}), ensure_ascii=False),
                    process_summary_json=json.dumps(turn_process, ensure_ascii=False),
                )

                for snapshot in phase_snapshots:
                    if not isinstance(snapshot, dict):
                        continue
                    phase_name = str(snapshot.get("phase_name") or "").strip()
                    phase_order = int(snapshot.get("phase_order", 0) or 0)
                    session.run(
                        cypher_phase,
                        process_id=process_id,
                        snapshot_id=_safe_snapshot_id(phase_name, phase_order),
                        phase_name=phase_name,
                        phase_order=phase_order,
                        status=str(snapshot.get("status") or ""),
                        summary=str(snapshot.get("summary") or ""),
                        summary_json=json.dumps(snapshot.get("payload", {}), ensure_ascii=False),
                        dream_id=dream_id_str,
                    )

                session.run(
                    """
                    MATCH (u:Person {name: '허정후'})
                    MATCH (e:CoreEgo {name: '송련'})
                    MATCH (d:Dream {id: $dream_id})
                    MATCH (tp:TurnProcess {id: $process_id})
                    MERGE (u)-[:EXPERIENCED]->(d)
                    MERGE (e)-[:EXPERIENCED]->(d)
                    MERGE (u)-[:EXPERIENCED]->(tp)
                    MERGE (e)-[:EXPERIENCED]->(tp)
                    """,
                    dream_id=dream_id_str,
                    process_id=process_id,
                )

            print("✨ [진짜 뇌] Dream를 슬림하게 저장하고 TurnProcess/PhaseSnapshot까지 분리 각인했습네다!\n")
        except Exception as e:
            print(f"💥 Neo4j Dream 각인 실패: {e}")

        return dream_id_str

        # =========================================================
        # 🛡️ 1단계: MySQL (안전 자산 백업 - 기존 로직 유지)
        # =========================================================
        cognitive_process_data = {
            "user_input": user_input,
            "user_emotion": user_emotion,
            "biolink_status": biolink_status,
            "trace_data": trace_data # 👈 main.py가 던져준 트레이스 배열 덩어리를 통째로 보관!
        }
        
        cognitive_json_str = json.dumps(cognitive_process_data, ensure_ascii=False)

        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            sql_create = """
            CREATE TABLE IF NOT EXISTS agent_dreams (
                dream_id INT AUTO_INCREMENT PRIMARY KEY,
                created_at DATETIME,
                cognitive_process JSON,
                final_answer TEXT
            )
            """
            cursor.execute(sql_create)
            
            sql_insert = """
            INSERT INTO agent_dreams (created_at, cognitive_process, final_answer)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql_insert, (timestamp, cognitive_json_str, final_answer))
            conn.commit()
            print("💾 [안전 자산] MySQL 금고에 사고 기록이 안전하게 백업되었습네다!")
            
        except Exception as e:
            print(f"💥 MySQL 백업 실패: {e}")
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals(): conn.close()

        # =========================================================
        # 🧠 2단계: Neo4j (트레이스는 phase_* 배열만 — full_log는 MySQL JSON에만 보관)
        # =========================================================
        cypher = """
        MERGE (d:Dream {id: $dream_id})
        SET d.date = $timestamp,
            d.user_input = $user_input,
            d.final_answer = $final_answer,
            d.user_emotion = $user_emotion,
            d.phase_minus1_intent = $p_minus1_intent,  // (DB 속성명은 기존 유지)
            d.phase_0_history = $p0_history,
            d.phase_1_actions = $p1_history,
            d.phase_2_summaries = $p2_history,
            d.phase_3_summary = $p3_summary,
            d.working_memory_json = $working_memory_json,
            d.turn_schema_json = $turn_schema_json,
            d.dialogue_state_json = $dialogue_state_json,
            d.response_contract_json = $response_contract_json,
            d.reasoning_board_json = $reasoning_board_json
        """
        
        try:
            with self.neo4j_driver.session() as session:
                session.run(cypher, 
                            dream_id=dream_id_str,
                            timestamp=timestamp,
                            user_input=user_input,
                            final_answer=final_answer,
                            user_emotion=user_emotion,
                            p_minus1_intent=json.dumps(
                                trace_data.get("response_strategy")
                                or {"legacy_thought_logs": trace_data.get("thought_logs", [])},
                                ensure_ascii=False
                            ),
                            
                            # 💡 [핵심 수술]: messages 배열을 json.dumps로 꽉꽉 눌러서 '하나의 문자열'로 만듭니다!
                            p0_history=json.dumps(trace_data.get("messages", []), ensure_ascii=False),
                            
                            p1_history=trace_data.get("executed_actions", []),
                            p2_history=json.dumps(trace_data.get("analysis_report", {}), ensure_ascii=False),
                            p3_summary=final_answer,
                            working_memory_json=json.dumps(
                                trace_data.get("working_memory_snapshot", {}),
                                ensure_ascii=False
                            ),
                            turn_schema_json=json.dumps(
                                trace_data.get("canonical_turn", {}),
                                ensure_ascii=False
                            ),
                            dialogue_state_json=json.dumps(
                                trace_data.get("canonical_turn", {}).get("dialogue_state", {}),
                                ensure_ascii=False
                            ),
                            response_contract_json=json.dumps(
                                trace_data.get("canonical_turn", {}).get("response_contract", {}),
                                ensure_ascii=False
                            ),
                            reasoning_board_json=json.dumps(
                                trace_data.get("canonical_turn", {}).get("reasoning_board", {}),
                                ensure_ascii=False
                            )
                )
            print("✨ [진짜 뇌] Neo4j에 와이드 노드(배열) 형태의 위대한 Dream이 완벽하게 각인되었습네다!\n")
            
        except Exception as e:
            print(f"💥 Neo4j Dream 각인 실패: {e}")

        return dream_id_str

    def save_second_dream_to_db(self, headline, audit_summary, trace_data=None, source_dream_ids=None, preset_id=None):
        """
        [2차 꿈: 공급 감사·보충 탐색 파이프라인]
        MySQL agent_second_dreams + Neo4j :SecondDream (7·8차 트레이스·도구 로그 동일 패턴 보관)
        preset_id: 그래프(공급 사슬)와 동일한 SecondDream id를 미리 쓸 때 지정
        """
        if trace_data is None:
            trace_data = {}
        if source_dream_ids is None:
            source_dream_ids = []

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sd_id = preset_id if preset_id else f"sd_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        cognitive_process_data = {
            "headline": headline,
            "kind": "second_dream_supply_audit",
            "source_dream_ids": source_dream_ids,
            "trace_data": trace_data,
        }
        cognitive_json_str = json.dumps(cognitive_process_data, ensure_ascii=False)

        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            sql_create = """
            CREATE TABLE IF NOT EXISTS agent_second_dreams (
                second_dream_id INT AUTO_INCREMENT PRIMARY KEY,
                created_at DATETIME,
                cognitive_process JSON,
                audit_summary TEXT
            )
            """
            cursor.execute(sql_create)
            sql_insert = """
            INSERT INTO agent_second_dreams (created_at, cognitive_process, audit_summary)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql_insert, (timestamp, cognitive_json_str, audit_summary))
            conn.commit()
            print("💾 [2차 꿈] MySQL agent_second_dreams 백업 완료!")
        except Exception as e:
            print(f"💥 [2차 꿈] MySQL 백업 실패: {e}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

        p7 = trace_data.get("phase_7_audit", {})
        p8_tools = trace_data.get("phase_8_tool_runs", [])
        p8_plan = trace_data.get("phase_8_plan", [])
        bridges = trace_data.get("phase_8_bridges", [])
        graph_ops = trace_data.get("graph_operations_log", [])
        p9 = trace_data.get("phase_9_tactical", {})

        cypher_sd = """
        MERGE (sd:SecondDream {id: $sd_id})
        SET sd.date = $timestamp,
            sd.headline = $headline,
            sd.audit_summary = $audit_summary,
            sd.phase_7_audit_json = $phase_7_json,
            sd.phase_8_tool_runs_json = $phase_8_tools_json,
            sd.phase_8_plan_json = $phase_8_plan_json,
            sd.phase_8_bridges_json = $bridges_json,
            sd.phase_9_tactical_json = $phase_9_json,
            sd.graph_operations_log_json = $graph_ops_json,
            sd.source_dream_ids = $source_dream_ids
        """
        try:
            with self.neo4j_driver.session() as session:
                session.run(
                    cypher_sd,
                    sd_id=sd_id,
                    timestamp=timestamp,
                    headline=headline,
                    audit_summary=audit_summary,
                    phase_7_json=json.dumps(p7, ensure_ascii=False) if isinstance(p7, dict) else str(p7),
                    phase_8_tools_json=json.dumps(p8_tools, ensure_ascii=False),
                    phase_8_plan_json=json.dumps(p8_plan, ensure_ascii=False),
                    bridges_json=json.dumps(bridges, ensure_ascii=False),
                    phase_9_json=json.dumps(p9, ensure_ascii=False) if isinstance(p9, dict) else str(p9),
                    graph_ops_json=json.dumps(graph_ops, ensure_ascii=False),
                    source_dream_ids=source_dream_ids,
                )
                for did in source_dream_ids:
                    if not did:
                        continue
                    session.run(
                        """
                        MATCH (sd:SecondDream {id: $sd_id})
                        MATCH (d:Dream {id: $did})
                        MERGE (sd)-[:AUDITED_FROM]->(d)
                        """,
                        sd_id=sd_id,
                        did=did,
                    )
                    session.run(
                        """
                        MATCH (sd:SecondDream {id: $sd_id})
                        MATCH (d:Dream {id: $did})-[:HAS_PROCESS]->(tp:TurnProcess)
                        MERGE (sd)-[:AUDITS_PROCESS]->(tp)
                        """,
                        sd_id=sd_id,
                        did=did,
                    )
                session.run(
                    """
                    MATCH (sd:SecondDream {id: $sd_id})
                    MATCH (u:Person {name: '허정후'})
                    MATCH (e:CoreEgo {name: '송련'})
                    MERGE (sd)-[:TARGETS_ROOT]->(u)
                    MERGE (sd)-[:TARGETS_ROOT]->(e)
                    MERGE (u)-[:EXPERIENCED]->(sd)
                    MERGE (e)-[:EXPERIENCED]->(sd)
                    """,
                    sd_id=sd_id,
                )
            print(f"✨ [2차 꿈] Neo4j SecondDream 각인 완료 (id={sd_id})\n")
        except Exception as e:
            print(f"💥 [2차 꿈] Neo4j 각인 실패: {e}")

        return sd_id
