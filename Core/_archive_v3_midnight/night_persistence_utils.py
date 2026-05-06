ROOT_PERSON_NAME = "허정후"
ROOT_COREEGO_NAME = "송련"

_SAFE_REL_TYPES = {
    "TARGETS_ROOT",
    "TRACKS_ROOT",
    "EXPERIENCED",
}


def _safe_rel_type(rel_type: str) -> str:
    normalized = str(rel_type or "").strip() or "TARGETS_ROOT"
    if normalized not in _SAFE_REL_TYPES:
        raise ValueError(f"Unsupported root relationship type: {normalized}")
    return normalized


def link_target_root(session, source_match: str, source_var: str, params: dict, root_entity: str, rel_type: str = "TARGETS_ROOT"):
    """Connect a matched node variable to the canonical Person/CoreEgo root."""
    relationship = _safe_rel_type(rel_type)
    root_text = str(root_entity or "").strip()
    if root_text.startswith("Person:"):
        session.run(
            f"""
            {source_match}
            MATCH (root:Person {{name: $root_name}})
            MERGE ({source_var})-[:{relationship}]->(root)
            """,
            **dict(params or {}, root_name=ROOT_PERSON_NAME),
        )
    elif root_text.startswith("CoreEgo:"):
        session.run(
            f"""
            {source_match}
            MATCH (root:CoreEgo {{name: $root_name}})
            MERGE ({source_var})-[:{relationship}]->(root)
            """,
            **dict(params or {}, root_name=ROOT_COREEGO_NAME),
        )


def link_both_roots(session, source_match: str, source_var: str, params: dict, rel_type: str = "TARGETS_ROOT"):
    """Connect a matched node variable to both canonical roots."""
    relationship = _safe_rel_type(rel_type)
    session.run(
        f"""
        {source_match}
        MATCH (person:Person {{name: $person_name}})
        MATCH (ego:CoreEgo {{name: $ego_name}})
        MERGE ({source_var})-[:{relationship}]->(person)
        MERGE ({source_var})-[:{relationship}]->(ego)
        """,
        **dict(params or {}, person_name=ROOT_PERSON_NAME, ego_name=ROOT_COREEGO_NAME),
    )
