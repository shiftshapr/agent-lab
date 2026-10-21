# Wave 4 proposal: typed nodes (3.1) and topic consolidation (3.2)

**Status: approved by Daveed and applied on 2026-10-21** (merge id map: `audits/person_merge_2026-10-21-topics/id_map.csv`; ids in `proposal.json`, `types.csv` and `merges.csv` are pre-merge). Ten Opus reviewers drafted it on
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

## Applied (2026-10-21)
- **Merges.** 89 merged and 1,327 ids shifted, so the topic band has no holes.
  - In each group the earliest-introduced node keeps its id, which keeps intro order valid. It takes the reviewers'
    chosen name, and the other names become aliases.
- **Types.** 1,360 nodes typed in `canonical/nodes.json` (`type`, `schema_org`, `wikidata_class`, `event_time`,
  `place`, `parent`).
  - Register `Node Type` lines are updated, and `scripts/sync_node_types.py` carries the types into the inscriptions
    (it is part of the daily finalize step).
  - Preflight and the inscription builder accept Event, Thing and Investigation Question.
- **Core events.**
  - N-10002 is now the Event "Assassination of Charlie Kirk" (2025-09-10, N-10012 Utah Valley University, Wikidata
    Q3882219). "Charlie Kirk Death and Memorial" is kept as an alias.
  - New Event N-11360 "Tyler Robinson arrest" (2025-09-11/12), introduced in ep3, cited by 21 claims.
  - New Event N-11361 "Charlie Kirk memorial service" (2025-09-21), introduced in ep5, cited by 78 claims.
  - An Opus reviewer assigned the claims (`event_assign` decisions): 21 of N-10002's 33 claims moved to the memorial
    event, and 13 claims stay on the assassination.
