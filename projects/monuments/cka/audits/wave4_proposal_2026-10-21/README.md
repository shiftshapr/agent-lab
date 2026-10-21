# Wave 4 proposal: typed nodes (3.1) and topic consolidation (3.2)

**Status: proposal for Daveed's approval. Nothing here has been applied.** Ten Opus reviewers drafted it on
2026-10-21, covering all 1,449 non-person nodes (ids N-10000+). Each reviewer worked from the node's name, aliases,
register description and citation counts, and saw the full list so it could find duplicates anywhere.

## Proposed types

| Type | Nodes | schema.org | Notes |
|---|---|---|---|
| InvestigationQuestion | 672 | Question | most "… Question / Discrepancy / Verification / Identification" topics |
| Topic | 393 | Thing (topic) | themes and narratives that are none of the others |
| Organization | 205 | Organization | today 201 |
| Event | 104 | Event | 9 dated 2025-09-10; `event_time` and `place` set where the record gives them |
| Place | 37 | Place | today 31 |
| Thing | 38 | Thing / CreativeWork / Product | objects and works: posts, books, documents, devices |

Today these 1,449 nodes are 1,217 topic, 201 organization and 31 place. Ids are unchanged, and all stay in the
N-10000+ band (Daveed, 2026-10-21). Each type maps to a schema.org type and, where confident, a Wikidata class:
see `types.csv` and `proposal.json`.

## Proposed merges: 89 nodes into 75 kept nodes
`merges.csv` lists each pair with its reason; the node with the earlier introduction or more citations is kept. There
are no chains, cycles or missing targets. Examples:
- **Fort Huachuca:** the 19 nodes become 1 Topic (N-10352 Fort Huachuca Investigation) and 1 Place (N-11338).
  - 6 merges: N-10365 and N-10370 into N-10326 (the Sept 9 JTF-SB meeting); N-10375 into N-10367; N-10435 and N-10472
    into N-10417 (Erika's presence); N-10643 into N-10373 (Harpole's presence).
  - The rest stay as distinct sub-questions, with `parent` set to N-10352.
- **Other merges:**
  - APAC into AIPAC.
  - "Egyptian Planes Investigation" into "Egyptian Military Plane Tracking Investigation".
  - "TPUSA Employee Purge and Leak Hunt" into "TPUSA Leak Hunt and Employee Firings".
  - The two Aspen-donor discrepancies into "Aspen Donor Recall Verification".

The merges use the same mechanics as person merges: references are rewritten, register rows are folded, and the map
is kept. In addition, 300 narrower questions get a `parent` instead of being merged.

## Decisions for Daveed
1. **Core events (ROADMAP 3.1: "a Sept 10 event absorbs N-10002").** The reviewers left N-10002 "Charlie Kirk Death and
   Memorial" as a Topic. Proposed:
   - (a) retype N-10002 as the Event "Assassination of Charlie Kirk", dated 2025-09-10, place N-10012 Utah Valley
     University;
   - (b) mint an Event "Charlie Kirk memorial service" (2025-09-21) for the memorial claims;
   - (c) mint an Event "Tyler Robinson arrest" (2025-09-11/12). N-10021 and N-11012 stay as the questions about it.
2. **Approve the 89 merges** as listed in `merges.csv`, or mark rows to drop.
3. **Approve the types** in `types.csv`. Spot-checks look right: "Operation Valhalla Strike" (Event, 2025-08-24),
   "Kanye Tweet About Candace Owens" (Thing), "MK Ultra" (Topic), "COVID Test DNA Collection Hypothesis"
   (InvestigationQuestion). Some event dates are the reviewers' inference and are flagged in their notes.

Once approved, the changes are applied through the JSON source (3.0), with a merge map and a renumber-free id
policy: kept ids are unchanged, and merged ids are removed with the band compacted, as for persons.
