// R7 rollback: V4 night-government labels/keys -> V3 midnight labels/keys.
// Prefer restoring from the R7 premigration dump if data integrity is in doubt.

MATCH (n:TimeBranch)
SET n:GovernorBranch
REMOVE n:TimeBranch;

MATCH (n:NightGovernmentState)
SET n:REMGovernorState
REMOVE n:NightGovernmentState;

MATCH (n)
WHERE n.governor_key = 'night_government_v1'
SET n.governor_key = 'rem_governor_v1';

// Restore only the archived shared-accord placeholder. Historical relationships
// cannot be reconstructed by this rollback script; restore the dump if needed.
MERGE (acc:SharedAccord {kind: "shared_accord", name: "허정후-송련 어코드"})
SET acc.restored_by = 'r7_rollback',
    acc.restored_at = timestamp();

MATCH (dh:DreamHint)
REMOVE dh.archive_at;

MATCH (topic:SupplyTopic)
REMOVE topic.embedding,
       topic.embedding_model;
