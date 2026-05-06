import unittest

from migrate_to_neo4j import create_constraints, ensure_core_nodes


class FakeSession:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append({"query": query, "params": params})
        return []


class Neo4jMigrationTests(unittest.TestCase):
    def test_core_node_migration_uses_direct_creation_relation_not_shared_accord(self):
        session = FakeSession()

        ensure_core_nodes(session, "허정후", "송련", "허정후-송련 어코드")

        query = session.calls[0]["query"]
        self.assertIn("MERGE (p)-[created:`창조`]->(a)", query)
        self.assertNotIn("RelationshipAccord", query)
        self.assertNotIn("SHARES_ACCORD", query)
        self.assertNotIn("accord_name", session.calls[0]["params"])

    def test_constraints_do_not_recreate_relationship_accord_constraint(self):
        session = FakeSession()

        create_constraints(session)

        joined = "\n".join(call["query"] for call in session.calls)
        self.assertNotIn("RelationshipAccord", joined)
        self.assertNotIn("accord_name", joined)


if __name__ == "__main__":
    unittest.main()
