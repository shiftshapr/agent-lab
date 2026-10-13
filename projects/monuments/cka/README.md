# CKA (Candace Kirk Archive)

Greenfield monument for **Candace Owens** numbered show episodes (`@RealCandaceO`) plus **Charlie Kirk–related specials** from **2025-09-11** onward. Chronological ingest order is defined in `input/episode_manifest.json` (~10 episodes/day in later batches).

## Relationship to Bride of Charlie (BoC)

| Monument | Role |
|----------|------|
| **BoC** (`projects/monuments/bride_of_charlie/`) | **Demonstration only** – protocol and workflow reference. |
| **CKA** (this tree) | **Production Candace corpus** – numbered show + Kirk specials; BoC series folds in when chronology reaches Feb–Mar 2026. |

**Daveed lock (2026-09-25):** Freeze further Candace ingest into BoC. Do **not** treat mixed BoC tip `7e4c948` as the long-term promote target. Former BoC monument slots **9–18** (Kirk tribute + Candace Ep **235–243**) are **remap** targets in CKA – see manifest notes; do not re-extract.

## ID bands (ledger)

Same convention as BoC / episode analysis protocol:

- **Person:** `N-1` … `N-9999` (Daveed, 2026-10-13). `N-1` … `N-999` is the original band (full; see the lock below); new persons are minted from `N-1000` upward (`canonical/nodes.json` `next_person_id`). A person id at `N-10000` or above is not allowed.
- **Person band lock (Daveed via Transit, 2026-10-08; capacity widened by Daveed 2026-10-13):** `N-1` … `N-999` is full. *Superseded 2026-10-13:* new persons no longer DEFER; they are minted from `N-1000` (the rest of this paragraph is the original 10-08 rule, which still holds for `N-1` … `N-999`). The band is pinned in `config/person_band_snapshot.json` (live + tombstoned + reserved = 999). While the lock is in force, do not reuse a retired, tombstoned or reserved id (`config/retired_node_ids.json`), and do not mint a person at `N-10000` or above; whether retired ids may ever be reused is pending with Daveed. Tombstones and reservations can only be added. A new person found by the daily run goes into the audit triage as **DEFER "person band full, awaiting Daveed"**. *Temporary rule, until Daveed rules:* a claim may name a DEFERred person in prose with no Mentions id. Enforced by preflight gate `person_band_lock` (`config/preflight_gates.json`), which fails closed (a missing key or unreadable config keeps it ON). Refresh the snapshot only with `dia_preflight.py --monument cka --refresh-band-snapshot`, which is append-only.
- **Topic / Org / Place:** `N-10000+`. Renumbered on 2026-10-13 from `N-1000` … `N-2393` (offset +9000, so old `N-1234` is now `N-11234`; full map in `audits/renumber_10000/renumber_map.csv`). The PR 47 person tombstones `N-10000` … `N-10033` were renamed `pr47-N-100xx` so the topic band could take those ids (Daveed ruling).
- **Claims / artifacts / memes:** global cross-episode ledger (continue from CKA ingest, not BoC demo ledger)

## Neo4j

**No Neo4j writes from agents** without explicit Daveed approval. Staging/prod promote remains a human gate (`projects/monuments/DIA_PREFLIGHT.md`).

## Layout

| Path | Purpose |
|------|---------|
| `input/` | `episode_manifest.json` (source of truth), optional `youtube_links.txt` (generated later) |
| `transcripts/` | Raw fetched transcripts |
| `transcripts_corrected/` | Name-correction pass (analysis input) |
| `drafts/` | Episode analysis drafts |
| `inscription/` | Inscription JSON (post-review) |
| `canonical/` | Canonical nodes / edges |
| `config/` | Claim lenses, membership tags, scaffold flags |
| `docs/` | Day-0 plan, ingest notes |

## DIA tip-line scan

Daily runs scan transcripts for DIA tip-line beats with the cues in `config/dia_scan_terms.json` (includes **bounty**). Each hit is claimed (claim + verbal-reference artifact + M-12 occurrence) or triaged with a reason.

## Claim lenses (first-class)

Investigation-adjacent tags for extractors (see `config/claim_lenses.json`). Full protocol schema wiring may follow in a later PR; tags are documented to match BoC `tags` arrays on claims.

## Epistemic graph (Phase A)

Claims are **immutable**. Walk-backs and corrections mint a new C-id with `Revises:` (newer → older); explicit oppose also uses `Contradicts:`. Typed draft splits: `Mentions:` (persons), `Connected:` (person→org), `CapturedAt:` (artifact→place). Port BoC `Supports:` / `Qualifies:` as well.

Extractor checklist and Appendix B claim shape: [`docs/EPISTEMIC_GRAPH.md`](docs/EPISTEMIC_GRAPH.md). Preflight gate: `claim_fork` in `projects/monuments/DIA_PREFLIGHT.md`. Phase B backfill and Phase C Neo4j mapping wait on separate unlocks.

## QA

Before merge/promote packs: `dia_preflight.py --monument cka` (scaffold exits clean until drafts exist), `verify_drafts` / Transit + Bill D review, Tessie sample – **no prod Neo4j**.

## Manifest maintenance

```bash
python3 projects/monuments/cka/scripts/build_episode_manifest.py --streams-cache /tmp/candace_streams.txt
```

See `input/MANIFEST_GAPS.md` if YouTube/Invidious blocks date backfill.
