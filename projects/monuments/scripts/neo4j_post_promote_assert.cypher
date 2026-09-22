// Read-only post-promote checklist (staging 27687 or prod 17687 — query only on prod).
// Run via cypher-shell / Browser; set $PersonBandMax to current dense person ceiling (58 on ep1–8 tip).

// 1) No Person label with id >= 1000
MATCH (p:Person)
WHERE p.node_ref STARTS WITH 'N-'
  AND toInteger(replace(p.node_ref, 'N-', '')) >= 1000
RETURN p.node_ref AS bad_ref, p.canonical_name AS name
LIMIT 25;

// 2) Person band should be dense 1..$PersonBandMax (sample gaps)
UNWIND range(1, $PersonBandMax) AS i
WITH 'N-' + toString(i) AS ref
OPTIONAL MATCH (p:Person {node_ref: ref})
WITH ref, p
WHERE p IS NULL
RETURN ref AS missing_person_ref
LIMIT 25;

// 3) Erpenbeck-style: same surname, distinct persons must not share one node_ref
MATCH (p:Person)
WHERE p.canonical_name CONTAINS 'Erpenbeck'
RETURN p.node_ref, p.canonical_name
ORDER BY p.canonical_name;

// 4) Sample high-pressure nodes exist
UNWIND ['N-2', 'N-3', 'N-1000'] AS ref
OPTIONAL MATCH (n {node_ref: ref})
RETURN ref, labels(n) AS labels, n.canonical_name AS name;
