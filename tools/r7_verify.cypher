// R7 verification queries.

MATCH (old:GovernorBranch)
RETURN 'GovernorBranch_remaining' AS check_name, count(old) AS count;

MATCH (old:REMGovernorState)
RETURN 'REMGovernorState_remaining' AS check_name, count(old) AS count;

MATCH (n {governor_key: 'rem_governor_v1'})
RETURN 'rem_governor_v1_remaining' AS check_name, count(n) AS count;

MATCH (acc {kind: "shared_accord", name: "허정후-송련 어코드"})
RETURN 'shared_accord_remaining' AS check_name, count(acc) AS count;

MATCH (tb:TimeBranch)
RETURN 'TimeBranch_count' AS check_name, count(tb) AS count;

MATCH (ng:NightGovernmentState)
RETURN 'NightGovernmentState_count' AS check_name, count(ng) AS count;

MATCH (dh:DreamHint)
WHERE coalesce(dh.archive_at, 9999999999999) > timestamp()
  AND coalesce(dh.expires_at, 9999999999999) > timestamp()
RETURN 'active_DreamHint_count' AS check_name, count(dh) AS count;

MATCH (topic:SupplyTopic)
RETURN 'SupplyTopic_with_embedding_slot' AS check_name,
       count(topic) AS count,
       count(topic.embedding) AS embedding_property_count;
