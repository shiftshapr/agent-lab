# CKA (Candace Kirk Archive)

Greenfield monument for **Candace Owens** numbered show episodes (`@RealCandaceO`) plus **Charlie Kirk–related specials** from **2025-09-11** onward. Chronological ingest order is defined in `input/episode_manifest.json` (~10 episodes/day in later batches).

## Relationship to Bride of Charlie (BoC)

| Monument | Role |
|----------|------|
| **BoC** (`projects/monuments/bride_of_charlie/`) | **Demonstration only** — protocol and workflow reference. |
| **CKA** (this tree) | **Production Candace corpus** — numbered show + Kirk specials; BoC series folds in when chronology reaches Feb–Mar 2026. |

**Daveed lock (2026-09-25):** Freeze further Candace ingest into BoC. Do **not** treat mixed BoC tip `7e4c948` as the long-term promote target. Former BoC monument slots **9–18** (Kirk tribute + Candace Ep **235–243**) are **remap** targets in CKA — see manifest notes; do not re-extract.

## ID bands (ledger)

Same convention as BoC / episode analysis protocol:

- **Person:** `N-1` … `N-999`
- **Topic / Org / Place:** `N-1000+`
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

## Claim lenses (first-class)

Investigation-adjacent tags for extractors (see `config/claim_lenses.json`). Full protocol schema wiring may follow in a later PR; tags are documented to match BoC `tags` arrays on claims.

## QA

Before merge/promote packs: `dia_preflight.py --monument cka` (scaffold exits clean until drafts exist), `verify_drafts` / Transit + Bill D review, Tessie sample — **no prod Neo4j**.

## Manifest maintenance

```bash
python3 projects/monuments/cka/scripts/build_episode_manifest.py --streams-cache /tmp/candace_streams.txt
```

See `input/MANIFEST_GAPS.md` if YouTube/Invidious blocks date backfill.
