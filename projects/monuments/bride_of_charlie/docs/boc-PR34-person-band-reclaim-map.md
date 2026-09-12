# Bride of Charlie — Person band reclaim (PR34)

Generated: 2026-09-12T20:30:00Z

Base tip: `5dd98939a8ec6e9967388dae5bb6bbd2b7399262`

## Daveed lock

People = N-1…N-999; Topics/Orgs/Places = N-1000+; dense first-introduction order; reclaim vacated low Person IDs (no parking Persons in Topic band).

PR33 left five Persons at N-1067..N-1071. This PR reclaims them into the Person band at N-54..N-58 (after Matt Walsh N-53). Topics remain dense N-1000..N-1066; N-1067..N-1071 vacated (not reused for Topics).

## Person old → new (full map)

| Old | New | Ep | Name | Notes |
|-----|-----|----|------|-------|
| N-1067 | N-54 | 2 | Jill Kesler | First intro ep2 Tesseract board |
| N-1068 | N-55 | 2 | Susan B. Silverstein | First intro ep2 |
| N-1069 | N-56 | 2 | John Walton | First intro ep2 |
| N-1070 | N-57 | 6 | Hugo E. Salazar | First intro ep6 |
| N-1071 | N-58 | 6 | Tracy Martin | First intro ep6 |

No N-1..N-53 identity shifts required (all five first-seen after Matt Walsh N-53).

## Validator / wiring results

| Check | Result |
|-------|--------|
| Stale Related (N-1067..N-1071 in drafts/inscription) | 0 |
| Person ids ≥ 1000 in canonical | 0 |
| draft ↔ canonical Person register | match |
| `verify_drafts.py --skip-search` grounding | PASS |
| `validate_inscription_bundle.py --episodes 1-8` | PASS |
| `build_inscription_from_drafts.py` + `export_for_inscription.py --dual-transcripts` | regenerated |

Inscription HELD — no prod Neo4j writes.

## Files touched

- `canonical/nodes.json` — persons N-54..N-58; `next_person_id` 59
- `config/retired_node_ids.json` — chain updates + pr33-person tombstones
- `drafts/episode_002.md`, `drafts/episode_006.md`
- `inscription/episode_002.json`, `inscription/episode_006.json` (+ transcripts via export)
- `scripts/reclaim_person_band_from_topic.py` — one-shot reclaim helper
- `scripts/apply_audit_grounding_fixes.py` — ep5 topic refs N-1070 → N-1054 (Iranian War topic; not Hugo)
