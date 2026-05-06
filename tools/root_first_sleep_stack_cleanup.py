import os

from dotenv import load_dotenv
from neo4j import GraphDatabase


def _driver():
    load_dotenv(".env")
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD")),
    )


def _print_rows(session, label, query):
    print(f"--- {label} ---")
    rows = [dict(record) for record in session.run(query)]
    if not rows:
        print("(none)")
        return
    for row in rows:
        print(row)


def main():
    driver = _driver()
    try:
        with driver.session() as session:
            _print_rows(
                session,
                "before_counts",
                """
                CALL {
                  MATCH (rp:REMPlan)
                  RETURN count(rp) AS rem_plan_count
                }
                CALL {
                  MATCH (rp:REMPlan:REMGovernor)
                  RETURN count(rp) AS legacy_plan_label_count
                }
                CALL {
                  MATCH (hr:ArchitectHandoffReport)
                  RETURN count(hr) AS handoff_count
                }
                CALL {
                  MATCH (sr:SourceRef)
                  RETURN count(sr) AS source_ref_count
                }
                RETURN rem_plan_count, legacy_plan_label_count, handoff_count, source_ref_count
                """,
            )

            session.run(
                """
                MATCH (rp:REMPlan)
                SET rp.selected_branch_paths = coalesce(rp.selected_branch_paths, rp.branch_paths, []),
                    rp.evidence_start_points = coalesce(rp.evidence_start_points, rp.required_evidence_addresses, []),
                    rp.name = coalesce(rp.name, 'REM 실행 계획')
                REMOVE rp:REMGovernor,
                       rp.priority_topics,
                       rp.candidate_supply_topics,
                       rp.branch_paths,
                       rp.leaf_specs,
                       rp.placement_decisions,
                       rp.required_evidence_addresses,
                       rp.handoff_targets,
                       rp.policy_biases,
                       rp.expected_outputs,
                       rp.risk_notes,
                       rp.validation_rules,
                       rp.phase_failure_focus,
                       rp.loop_failure_patterns,
                       rp.top_source_ids,
                       rp.target_user_model_axes,
                       rp.target_songryeon_axes,
                       rp.plan_scope
                """
            )

            session.run(
                """
                MATCH (rg:NightGovernmentState)
                SET rg.name = coalesce(rg.name, 'Night Government')
                """
            )

            session.run(
                """
                MATCH (ba:BranchArchitect)
                SET ba.name = coalesce(ba.name, '가지 설계자')
                """
            )

            session.run(
                """
                MATCH (hr:ArchitectHandoffReport)
                SET hr.name = coalesce(hr.name, '가지 인수인계 감사')
                """
            )

            session.run(
                """
                MATCH (sr:SourceRef)
                WHERE NOT (
                    sr.address STARTS WITH 'Dream:'
                    OR sr.address STARTS WITH 'TurnProcess:'
                    OR sr.address STARTS WITH 'Phase:'
                    OR sr.address STARTS WITH 'Diary|'
                    OR sr.address STARTS WITH 'PastRecord|'
                    OR sr.address STARTS WITH 'SongryeonChat|'
                    OR sr.address STARTS WITH 'GeminiChat|'
                    OR sr.address STARTS WITH 'http://'
                    OR sr.address STARTS WITH 'https://'
                    OR sr.address STARTS WITH 'Person:'
                    OR sr.address STARTS WITH 'CoreEgo:'
                )
                DETACH DELETE sr
                """
            )

            _print_rows(
                session,
                "after_counts",
                """
                CALL {
                  MATCH (rp:REMPlan)
                  RETURN count(rp) AS rem_plan_count
                }
                CALL {
                  MATCH (rp:REMPlan:REMGovernor)
                  RETURN count(rp) AS legacy_plan_label_count
                }
                CALL {
                  MATCH (hr:ArchitectHandoffReport)
                  RETURN count(hr) AS handoff_count
                }
                CALL {
                  MATCH (sr:SourceRef)
                  RETURN count(sr) AS source_ref_count
                }
                RETURN rem_plan_count, legacy_plan_label_count, handoff_count, source_ref_count
                """,
            )
    finally:
        driver.close()


if __name__ == "__main__":
    main()
