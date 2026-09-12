# Bride of Charlie — Person band dense intro-order reclaim (PR34)

Generated: 2026-09-12T20:45:00Z

Base tip: `5dd98939a8ec6e9967388dae5bb6bbd2b7399262`

## Daveed lock

People = N-1…N-999 dense by **first-seen ep1→ep8**; Topics/Orgs/Places = N-1000+ only. Reclaim vacated low Person IDs — never append Persons after later first-seen slots.

PR33 misplaced five Persons at N-1067..N-1071. PR34 first pass (wrong) appended them as N-54..58 after Matt Walsh N-53. **This fix** inserts by true intro order with cascade shifts.

## Final Person intro order (verified from `New Nodes Introduced`)

| Ep | New Person nodes (in order) |
|----|----------------------------|
| 1 | N-1..N-12 |
| 2 | N-13..N-17, **N-18 Jill Kesler**, **N-19 Susan B. Silverstein**, **N-20 John Walton** |
| 3 | N-21..N-28 (Erpenbeck family + Terry Crist + Brian Houston) |
| 4 | N-29..N-34 |
| 5 | N-35..N-38 |
| 6 | N-39..N-45, **N-46 Hugo E. Salazar**, **N-47 Tracy Martin** |
| 7 | N-48..N-50 |
| 8 | N-51..N-58 (**Matt Walsh = N-58**) |

Dense monotonic N-1..N-58 ✓ | Zero Person ≥ 1000 ✓ | Topics N-1000..N-1066 unchanged ✓ | N-6 Elizabeth Lane unchanged ✓

## Main-tip → final Person map (selected)

### PR33 topic-band reclaim (five misplaced)

| Old (main) | Final | Name |
|------------|-------|------|
| N-1067 | **N-18** | Jill Kesler |
| N-1068 | **N-19** | Susan B. Silverstein |
| N-1069 | **N-20** | John Walton |
| N-1070 | **N-46** | Hugo E. Salazar |
| N-1071 | **N-47** | Tracy Martin |

### Erpenbeck cascade (+3 from ep2 insert)

| Old (main) | Final | Name |
|------------|-------|------|
| N-18 | **N-21** | Richard Erpenbeck |
| N-19 | **N-22** | Tony Erpenbeck |
| N-20 | **N-23** | Bill Erpenbeck |
| N-21 | **N-24** | Gary Erpenbeck |
| N-22 | **N-25** | Jeff Erpenbeck |
| N-23 | **N-26** | Donna Erpenbeck |

### Walsh tail (+5 total from ep2 + ep6 inserts)

| Old (main) | Final | Name |
|------------|-------|------|
| N-43 | **N-48** | Josh Harelson |
| N-44 | **N-49** | JT Massie |
| N-45 | **N-50** | Tucker Carlson |
| N-46 | **N-51** | Cabot Phillips |
| N-47 | **N-52** | Bishop Thomas J. O'Brien |
| N-48 | **N-53** | Jim Lee Reed |
| N-49 | **N-54** | Patricia Patrick |
| N-50 | **N-55** | James Woolsey |
| N-51 | **N-56** | Kanye West |
| N-52 | **N-57** | Kouri Richins |
| N-53 | **N-58** | Matt Walsh |

(Full N-24..N-42 → N-27..N-45 cascade documented in `scripts/reclaim_person_band_from_topic.py` `DENSE_REMAP`.)

## Validator / wiring results

| Check | Result |
|-------|--------|
| Person intro-order N-1..58 monotonic | **PASS** |
| Stale N-1067..N-1071 in drafts/inscription | **0** |
| Person ids ≥ 1000 | **0** |
| draft ↔ canonical Person register | **0 mismatches** |
| Topics N-1000..N-1066 vs main tip | **unchanged** |
| `verify_drafts.py --skip-search` grounding | **PASS** |
| `validate_inscription_bundle.py --episodes 1-8` | **PASS** |

Inscription HELD — no prod Neo4j writes.

## Files touched

- `canonical/nodes.json`, `config/retired_node_ids.json`
- `drafts/episode_*.md`, cross-episode drafts, `patterns_report.md`
- `inscription/episode_*.json` (+ dual transcripts via export)
- `scripts/reclaim_person_band_from_topic.py`
