// R4 cleanup: remove the old shared accord bridge.
// Run manually only after explicit operator approval.

MATCH (acc {kind: "shared_accord", name: "허정후-송련 어코드"})
DETACH DELETE acc;

MATCH (acc {kind: "shared_accord", name: "허정후-송련 어코드"})
RETURN count(acc) AS remaining_shared_accord;
