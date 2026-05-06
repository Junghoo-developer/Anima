"""Neo4j connection boundary for ANIMA infrastructure adapters."""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


@contextmanager
def get_db_session():
    """Open a Neo4j session for a single adapter operation."""
    session = neo4j_driver.session()
    try:
        yield session
    finally:
        session.close()


__all__ = ["NEO4J_PASSWORD", "NEO4J_URI", "NEO4J_USER", "get_db_session", "neo4j_driver"]
