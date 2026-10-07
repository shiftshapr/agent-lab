// CKA epistemic graph design §5 acceptance queries (staging bolt://127.0.0.1:27687)
// Read-only. Do not run against prod 17687 from agent promote paths.

// 1. As-of claim
MATCH (e:Episode)-[:ASSERTS]->(c:Claim)
OPTIONAL MATCH (c)-[:MENTIONS]->(p:Person)
RETURN e.episode_num AS episode_num, c.id AS claim_id, c.claim_ts AS claim_ts,
       collect(DISTINCT p.id) AS mentioned_persons
ORDER BY e.episode_num, c.claim_ts, c.id
LIMIT 25;

// 2. Evidence walk
MATCH (c:Claim)-[:SUPPORTED_BY]->(a:Artifact)-[:APPEARS_IN]->(e:Episode)
RETURN c.id AS claim_id, a.id AS artifact_id, e.episode_num AS episode_num,
       a.video_ts AS video_ts
ORDER BY c.id, a.id
LIMIT 25;

// 3. Revision chain
MATCH (newer:Claim)-[:REVISES]->(older:Claim)
RETURN newer.id AS newer_id, older.id AS older_id,
       newer.claim_ts AS newer_ts, older.claim_ts AS older_ts
ORDER BY newer.id
LIMIT 25;

// 4. Disagreement set
MATCH (c:Claim)-[:CONTRADICTS]-(other:Claim)
OPTIONAL MATCH (other)-[:SUPPORTED_BY]->(a:Artifact)
RETURN c.id AS seed_claim, other.id AS neighbor_claim,
       collect(DISTINCT a.id) AS neighbor_artifacts
ORDER BY c.id, other.id
LIMIT 25;

// 5. Competitors at locus
MATCH (a:Artifact)-[:CAPTURED_AT]->(place)
MATCH (c:Claim)-[:SUPPORTED_BY]->(a)
OPTIONAL MATCH (c)-[:CONTRADICTS|REVISES]-(rival:Claim)
RETURN place.id AS place_id, c.id AS claim_id,
       collect(DISTINCT rival.id) AS rivals
ORDER BY place.id, c.id
LIMIT 25;

// 6. Person <-> org
MATCH (p:Person)-[:CONNECTED_TO]->(o)
OPTIONAL MATCH (p)-[:APPEARS_IN]->(e:Episode)<-[:APPEARS_IN]-(other:Person)
WHERE other.id <> p.id
RETURN p.id AS person_id, o.id AS org_id,
       collect(DISTINCT other.id)[0..10] AS co_appear_persons
ORDER BY p.id, o.id
LIMIT 25;

// 7. LLM retrieval spine
MATCH (c:Claim)-[:SUPPORTED_BY]->(a:Artifact)-[:APPEARS_IN]->(e:Episode)
OPTIONAL MATCH (c)-[:CONTRADICTS|REVISES|QUALIFIES]-(comp:Claim)
RETURN c.id AS seed_claim, a.id AS artifact_id, e.episode_num AS episode_num,
       c.claim_ts AS claim_ts,
       collect(DISTINCT comp.id) AS competitors
ORDER BY c.id
LIMIT 25;
