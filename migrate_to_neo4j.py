import argparse
import os

import pymysql
from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()


MYSQL_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS"),
    "db": os.getenv("DB_NAME", "songryeon_db"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

DEFAULT_PERSON_NAME = os.getenv("ANIMA_PERSON_NAME", "허정후")
DEFAULT_AGENT_NAME = os.getenv("ANIMA_AGENT_NAME", "송련")
DEFAULT_ACCORD_NAME = os.getenv("ANIMA_ACCORD_NAME", "허정후-송련 어코드")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Migrate core raw records from MySQL to Neo4j."
    )
    parser.add_argument(
        "--include-songryeon-chats",
        action="store_true",
        help="Also migrate songryeon_chats raw records.",
    )
    parser.add_argument(
        "--person-name",
        default=DEFAULT_PERSON_NAME,
        help="Root person node name.",
    )
    parser.add_argument(
        "--agent-name",
        default=DEFAULT_AGENT_NAME,
        help="CoreEgo node name.",
    )
    parser.add_argument(
        "--accord-name",
        default=DEFAULT_ACCORD_NAME,
        help="Legacy no-op. V4 migration no longer creates RelationshipAccord nodes.",
    )
    return parser.parse_args()


def mysql_connect():
    return pymysql.connect(**MYSQL_CONFIG)


def neo4j_connect():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def table_exists(cursor, table_name: str) -> bool:
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None


def safe_date_text(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        if hasattr(value, "hour"):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value.strftime("%Y-%m-%d")
    return str(value)


def create_constraints(session):
    statements = [
        "CREATE CONSTRAINT raw_diary_id IF NOT EXISTS FOR (n:Diary) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT raw_gemini_chat_id IF NOT EXISTS FOR (n:GeminiChat) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT raw_songryeon_chat_id IF NOT EXISTS FOR (n:SongryeonChat) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (n:Person) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT coreego_name IF NOT EXISTS FOR (n:CoreEgo) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT gemini_conversation_id IF NOT EXISTS FOR (n:GeminiConversation) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT gemini_agent_name IF NOT EXISTS FOR (n:ExternalAgent) REQUIRE n.name IS UNIQUE",
    ]
    for stmt in statements:
        session.run(stmt)


def ensure_core_nodes(session, person_name: str, agent_name: str, accord_name: str):
    del accord_name
    session.run(
        """
        MERGE (p:Person {name: $person_name})
        SET p.role = coalesce(p.role, 'human')

        MERGE (a:CoreEgo {name: $agent_name})
        SET a:AgentIdentity, a.role = coalesce(a.role, 'core_ego')

        MERGE (p)-[created:`창조`]->(a)
        SET created.created_at = coalesce(created.created_at, datetime()),
            created.note = coalesce(
                created.note,
                '허정후가 송련을 창조 (V4 raw migration direct relation)'
            )

        MERGE (:ExternalAgent {name: 'Gemini'})
        """
        ,
        person_name=person_name,
        agent_name=agent_name,
    )


def migrate_diaries(session, cursor, person_name: str) -> int:
    if not table_exists(cursor, "user_diary"):
        print("  - user_diary table not found, skipping diaries.")
        return 0

    cursor.execute("SELECT id, write_date, content FROM user_diary ORDER BY write_date ASC, id ASC")
    rows = cursor.fetchall()
    for row in rows:
        session.run(
            """
            MATCH (p:Person {name: $person_name})
            MERGE (d:PastRecord:Diary {id: $node_id})
            SET d.date = $date_text,
                d.content = $content,
                d.source_table = 'user_diary'
            MERGE (p)-[:WROTE]->(d)
            """,
            person_name=person_name,
            node_id=f"diary_{row['id']}",
            date_text=safe_date_text(row["write_date"]),
            content=row.get("content") or "",
        )
    return len(rows)


def migrate_gemini_chats(session, cursor, person_name: str) -> int:
    if not table_exists(cursor, "chat_logs"):
        print("  - chat_logs table not found, skipping Gemini chats.")
        return 0

    cursor.execute(
        """
        SELECT id, conversation_id, role, content, created_at
        FROM chat_logs
        ORDER BY conversation_id ASC, created_at ASC, id ASC
        """
    )
    rows = cursor.fetchall()
    for row in rows:
        conversation_id = str(row.get("conversation_id") or f"gemini_conv_{row['id']}")
        role = str(row.get("role") or "").strip() or "assistant"
        session.run(
            """
            MATCH (p:Person {name: $person_name})
            MATCH (gai:ExternalAgent {name: 'Gemini'})
            MERGE (conv:GeminiConversation {id: $conversation_id})
            SET conv.source_table = 'chat_logs'

            MERGE (m:PastRecord:GeminiChat {id: $node_id})
            SET m.conversation_id = $conversation_id,
                m.role = $role,
                m.content = $content,
                m.date = $date_text,
                m.source_table = 'chat_logs'

            MERGE (m)-[:IN_CONVERSATION]->(conv)
            FOREACH (_ IN CASE WHEN $role = 'user' THEN [1] ELSE [] END |
                MERGE (p)-[:SPOKE]->(m)
            )
            FOREACH (_ IN CASE WHEN $role <> 'user' THEN [1] ELSE [] END |
                MERGE (gai)-[:SPOKE]->(m)
            )
            """,
            person_name=person_name,
            conversation_id=conversation_id,
            node_id=f"gchat_{row['id']}",
            role=role,
            content=row.get("content") or "",
            date_text=safe_date_text(row.get("created_at")),
        )

    session.run(
        """
        MATCH (conv:GeminiConversation)<-[:IN_CONVERSATION]-(m:GeminiChat)
        WITH conv, m ORDER BY conv.id, coalesce(m.date, ''), m.id
        WITH conv, collect(m) AS msgs
        WHERE size(msgs) > 1
        UNWIND range(0, size(msgs) - 2) AS idx
        WITH msgs[idx] AS from_msg, msgs[idx + 1] AS to_msg
        MERGE (from_msg)-[:NEXT]->(to_msg)
        """
    )
    return len(rows)


def migrate_songryeon_chats(session, cursor, person_name: str, agent_name: str) -> int:
    if not table_exists(cursor, "songryeon_chats"):
        print("  - songryeon_chats table not found, skipping Songryeon chats.")
        return 0

    cursor.execute(
        """
        SELECT id, role, content, created_at
        FROM songryeon_chats
        ORDER BY created_at ASC, id ASC
        """
    )
    rows = cursor.fetchall()
    for row in rows:
        role = str(row.get("role") or "").strip() or "assistant"
        session.run(
            """
            MATCH (p:Person {name: $person_name})
            MATCH (a:CoreEgo {name: $agent_name})
            MERGE (m:PastRecord:SongryeonChat {id: $node_id})
            SET m.role = $role,
                m.content = $content,
                m.date = $date_text,
                m.source_table = 'songryeon_chats'

            FOREACH (_ IN CASE WHEN $role = 'user' THEN [1] ELSE [] END |
                MERGE (p)-[:SPOKE]->(m)
            )
            FOREACH (_ IN CASE WHEN $role <> 'user' THEN [1] ELSE [] END |
                MERGE (a)-[:SPOKE]->(m)
            )
            """,
            person_name=person_name,
            agent_name=agent_name,
            node_id=f"schat_{row['id']}",
            role=role,
            content=row.get("content") or "",
            date_text=safe_date_text(row.get("created_at")),
        )

    session.run(
        """
        MATCH (m:SongryeonChat)
        WITH m ORDER BY coalesce(m.date, ''), m.id
        WITH collect(m) AS msgs
        WHERE size(msgs) > 1
        UNWIND range(0, size(msgs) - 2) AS idx
        WITH msgs[idx] AS from_msg, msgs[idx + 1] AS to_msg
        MERGE (from_msg)-[:NEXT]->(to_msg)
        """
    )
    return len(rows)


def migrate_data(args):
    print("=== Neo4j raw migration start ===")
    print(f"- person: {args.person_name}")
    print(f"- agent: {args.agent_name}")
    print(f"- include_songryeon_chats: {args.include_songryeon_chats}")

    mysql_conn = mysql_connect()
    neo4j_driver = neo4j_connect()

    migrated = {
        "diaries": 0,
        "gemini_chats": 0,
        "songryeon_chats": 0,
    }

    try:
        with mysql_conn.cursor() as cursor:
            with neo4j_driver.session() as session:
                create_constraints(session)
                ensure_core_nodes(session, args.person_name, args.agent_name, args.accord_name)

                print("[1/3] Migrating diaries...")
                migrated["diaries"] = migrate_diaries(session, cursor, args.person_name)

                print("[2/3] Migrating Gemini chats...")
                migrated["gemini_chats"] = migrate_gemini_chats(session, cursor, args.person_name)

                if args.include_songryeon_chats:
                    print("[3/3] Migrating Songryeon chats...")
                    migrated["songryeon_chats"] = migrate_songryeon_chats(
                        session, cursor, args.person_name, args.agent_name
                    )
                else:
                    print("[3/3] Skipping Songryeon chats by default.")

        print("\n=== Neo4j raw migration complete ===")
        for key, value in migrated.items():
            print(f"- {key}: {value}")
    finally:
        mysql_conn.close()
        neo4j_driver.close()


if __name__ == "__main__":
    migrate_data(parse_args())
