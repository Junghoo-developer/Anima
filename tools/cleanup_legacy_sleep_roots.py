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
                "before",
                """
                MATCH (n)
                WHERE (n:UserRoot AND coalesce(n.root_key, '') = 'current_user')
                   OR (n:SongryeonRoot AND coalesce(n.root_key, '') = 'songryeon')
                RETURN labels(n) AS labels, coalesce(n.root_key, n.name, '') AS key, count(*) AS c
                ORDER BY c DESC
                """,
            )

            session.run(
                """
                MATCH (rp:REMPlan)
                SET rp.target_roots = [
                    item IN coalesce(rp.target_roots, [])
                    | CASE
                        WHEN item = 'UserRoot' THEN 'Person:허정후'
                        WHEN item = 'SongryeonRoot' THEN 'CoreEgo:송련'
                        ELSE item
                      END
                ],
                rp.branch_paths = [
                    item IN coalesce(rp.branch_paths, [])
                    | CASE
                        WHEN item STARTS WITH 'UserRoot/' THEN 'Person/' + substring(item, 9)
                        WHEN item STARTS WITH 'SongryeonRoot/' THEN 'CoreEgo/' + substring(item, 14)
                        ELSE item
                      END
                ],
                rp.create_targets = [
                    item IN coalesce(rp.create_targets, [])
                    | CASE
                        WHEN item STARTS WITH 'UserRoot/' THEN 'Person/' + substring(item, 9)
                        WHEN item STARTS WITH 'SongryeonRoot/' THEN 'CoreEgo/' + substring(item, 14)
                        ELSE item
                      END
                ],
                rp.update_targets = [
                    item IN coalesce(rp.update_targets, [])
                    | CASE
                        WHEN item STARTS WITH 'UserRoot/' THEN 'Person/' + substring(item, 9)
                        WHEN item STARTS WITH 'SongryeonRoot/' THEN 'CoreEgo/' + substring(item, 14)
                        ELSE item
                      END
                ],
                rp.placement_decisions = [
                    item IN coalesce(rp.placement_decisions, [])
                    | CASE
                        WHEN item STARTS WITH 'create::UserRoot/' THEN 'create::Person/' + substring(item, 16)
                        WHEN item STARTS WITH 'create::SongryeonRoot/' THEN 'create::CoreEgo/' + substring(item, 21)
                        WHEN item STARTS WITH 'update::UserRoot/' THEN 'update::Person/' + substring(item, 16)
                        WHEN item STARTS WITH 'update::SongryeonRoot/' THEN 'update::CoreEgo/' + substring(item, 21)
                        ELSE item
                      END
                ]
                """
            )

            session.run(
                """
                MATCH (bg:BranchGrowth)
                SET bg.curated_branches = [
                    item IN coalesce(bg.curated_branches, [])
                    | CASE
                        WHEN item STARTS WITH 'UserRoot/' THEN 'Person/' + substring(item, 9)
                        WHEN item STARTS WITH 'SongryeonRoot/' THEN 'CoreEgo/' + substring(item, 14)
                        ELSE item
                      END
                ]
                """
            )

            session.run(
                """
                MATCH (bd:BranchDigest)
                SET bd.branch_path =
                    CASE
                        WHEN bd.branch_path STARTS WITH 'UserRoot/' THEN 'Person/' + substring(bd.branch_path, 9)
                        WHEN bd.branch_path STARTS WITH 'SongryeonRoot/' THEN 'CoreEgo/' + substring(bd.branch_path, 14)
                        ELSE bd.branch_path
                    END
                """
            )

            session.run(
                """
                MATCH (bd:BranchDigest)
                WITH bd, split(coalesce(bd.branch_path, ''), '/')[-1] AS leaf
                SET bd.title =
                    CASE leaf
                        WHEN 'history_review' THEN '과거 검토 가지'
                        WHEN 'dialogue_review' THEN '대화 검토 가지'
                        WHEN 'visible_patterns' THEN '가시 패턴 가지'
                        WHEN 'tool_doctrine' THEN '도구 원칙 가지'
                        WHEN 'field_repair' THEN '현장 수선 가지'
                        ELSE coalesce(bd.title, leaf)
                    END
                """
            )

            session.run(
                """
                MATCH (rp:REMPlan)-[r:TARGETS_ROOT]->(u:UserRoot {root_key: 'current_user'})
                MATCH (p:Person {name: '허정후'})
                MERGE (rp)-[:TARGETS_ROOT]->(p)
                DELETE r
                """
            )
            session.run(
                """
                MATCH (rp:REMPlan)-[r:TARGETS_ROOT]->(s:SongryeonRoot {root_key: 'songryeon'})
                MATCH (e:CoreEgo {name: '송련'})
                MERGE (rp)-[:TARGETS_ROOT]->(e)
                DELETE r
                """
            )

            session.run(
                """
                MATCH (n:UserRoot {root_key: 'current_user'})
                DETACH DELETE n
                """
            )
            session.run(
                """
                MATCH (n:SongryeonRoot {root_key: 'songryeon'})
                DETACH DELETE n
                """
            )

            _print_rows(
                session,
                "after",
                """
                MATCH (n)
                WHERE (n:UserRoot AND coalesce(n.root_key, '') = 'current_user')
                   OR (n:SongryeonRoot AND coalesce(n.root_key, '') = 'songryeon')
                RETURN labels(n) AS labels, coalesce(n.root_key, n.name, '') AS key, count(*) AS c
                ORDER BY c DESC
                """,
            )
            _print_rows(
                session,
                "remaining_legacy_paths",
                """
                MATCH (rp:REMPlan)
                WHERE any(x IN coalesce(rp.branch_paths, []) WHERE x STARTS WITH 'UserRoot/' OR x STARTS WITH 'SongryeonRoot/')
                   OR any(x IN coalesce(rp.create_targets, []) WHERE x STARTS WITH 'UserRoot/' OR x STARTS WITH 'SongryeonRoot/')
                   OR any(x IN coalesce(rp.update_targets, []) WHERE x STARTS WITH 'UserRoot/' OR x STARTS WITH 'SongryeonRoot/')
                RETURN count(rp) AS c
                """,
            )
            _print_rows(
                session,
                "remaining_legacy_digests",
                """
                MATCH (bd:BranchDigest)
                WHERE bd.branch_path STARTS WITH 'UserRoot/' OR bd.branch_path STARTS WITH 'SongryeonRoot/'
                RETURN count(bd) AS c
                """,
            )
    finally:
        driver.close()


if __name__ == "__main__":
    main()
