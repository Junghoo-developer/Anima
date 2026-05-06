// R4 rollback helper.
// Git revert cannot restore Neo4j mutations. Run manually only if R4 graph
// cleanup/persistence has already been executed and must be reversed.

MERGE (acc:SharedAccord {kind: "shared_accord", name: "허정후-송련 어코드"})
SET acc.restored_by = "r4_rollback",
    acc.restored_at = timestamp();

MATCH (el:Election {created_by: "v4_r4_past_department"})
DETACH DELETE el;

MATCH (cp:ChangeProposal {created_by: "v4_r4_past_department"})
DETACH DELETE cp;

MATCH (cr:ChangeRationale {created_by: "v4_r4_past_department"})
DETACH DELETE cr;

MATCH (ci:ChangeImportance {created_by: "v4_r4_past_department"})
DETACH DELETE ci;

MATCH (target:ProposedChangeTarget)
WHERE NOT (target)--()
DETACH DELETE target;

MATCH (tb:TimeBranch {created_by: "v4_r4_past_department"})
WHERE NOT (tb)<-[:GUIDES_BRANCH]-(:DreamHint)
DETACH DELETE tb;
