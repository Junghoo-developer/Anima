// R5 rollback helper.
// Git revert cannot remove Neo4j nodes written by R5. Run manually only if
// R5 SecondDream persistence has already been executed and must be reversed.

MATCH (sd:SecondDream {created_by: "v4_r5_present_department"})
DETACH DELETE sd;

MATCH (topic:SupplyTopic)
WHERE NOT (topic)--()
DETACH DELETE topic;

MATCH (tb:TimeBranch)
WHERE tb.created_by = "v4_r5_present_department"
  AND NOT (tb)<-[:GUIDES_BRANCH]-(:DreamHint)
  AND NOT (tb)<-[:GUIDES_BRANCH]-(:SecondDream)
DETACH DELETE tb;
