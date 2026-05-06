// R7 migration: V3 midnight labels/keys -> V4 night-government labels/keys.
// Run only after a Neo4j dump backup:
//   neo4j-admin database dump neo4j --to-path=backups/r7_premigration/

// 1. Label migrations.
MATCH (n:GovernorBranch)
SET n:TimeBranch
REMOVE n:GovernorBranch;

MATCH (n:REMGovernorState)
SET n:NightGovernmentState
REMOVE n:REMGovernorState;

// 2. Key migration.
MATCH (n)
WHERE n.governor_key = 'rem_governor_v1'
SET n.governor_key = 'night_government_v1';

// 3. R4 shared-accord cleanup.
MATCH (acc {kind: "shared_accord", name: "허정후-송련 어코드"})
DETACH DELETE acc;

// 4. DreamHint activation fields.
MATCH (dh:DreamHint)
SET dh.archive_at = coalesce(dh.archive_at, null),
    dh.expires_at = coalesce(dh.expires_at, null);

// 5. SupplyTopic embedding placeholder fields.
MATCH (topic:SupplyTopic)
SET topic.embedding = coalesce(topic.embedding, []),
    topic.embedding_model = coalesce(topic.embedding_model, ''),
    topic.updated_at = timestamp();
