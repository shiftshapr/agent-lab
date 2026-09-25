# CKA Batch 1 — BoC remap (seq 1–10)

## Mapping (BoC monument ep → CKA seq)

| BoC ep | CKA seq | kind | Candace Ep | YouTube id |
|--------|---------|------|------------|------------|
| 9 | 1 | kirk_special | — | `_dRaEO47-co` |
| 10 | 2 | numbered_show | 235 | `czVBmqZP6Ss` |
| 11 | 3 | numbered_show | 236 | `q7f8r-THr84` |
| 12 | 4 | numbered_show | 237 | `2WEHTk0Xewg` |
| 13 | 5 | numbered_show | 238 | `sreYYcID-QY` |
| 14 | 6 | numbered_show | 239 | `aDlhjfW6hz8` |
| 15 | 7 | numbered_show | 240 | `ja26iltROkM` |
| 16 | 8 | numbered_show | 241 | `UBkFkg4UNY8` |
| 17 | 9 | numbered_show | 242 | `QZWSsq8ZWzw` |
| 18 | 10 | numbered_show | 243 | `K5GjF53bfN4` |

YouTube ids match `input/episode_manifest.json` and BoC transcript filenames. No manifest conflicts.

## What was copied vs edited

| Artifact | Action |
|----------|--------|
| `transcripts/episode_XXX_<youtubeId>.txt` | Copied from BoC (bytes identical; SHA preserved) |
| `transcripts_corrected/` | Copied where BoC had corrected files |
| `drafts/.transcript_sha/episode_XXX.sha256` | Copied from BoC sidecars |
| `drafts/episode_001–010.md` | Remapped metadata (monument `cka`, seq, YouTube id, Candace Ep); series label → Candace Kirk Archive; claim lens tags added where existing claim text matched `config/claim_lenses.json` |
| `drafts/episode_000.md` | **New** ledger-only baseline (BoC eps 1–8 `New Nodes Introduced` order) for preflight intro order |
| `config/preflight_ledger_baseline.json` | **New** density baseline (BoC 1–8 N-ids) — no duplicate register rows |
| `inscription/episode_001–010.json` | Regenerated from CKA drafts via BoC `build_inscription_from_drafts.py` (meta patched for CKA) |
| `inscription/episode_*_transcript*.txt` | Copied from BoC inscription twins (renamed to CKA seq) |
| `canonical/nodes.json` | Filtered from BoC canonical for active register nodes; episode lists remapped to CKA seq |
| `config/retired_node_ids.json` | Copied from BoC (same tombstone ledger) |
| `config/batch1_remap_from_boc.json` | Remap index + `remapped_from_boc` membership tag |
| `input/youtube_links.txt` | Filled for seq 1–10 URLs |

**Not done:** Neo4j writes, staging/prod promote, YouTube re-fetch, BoC series 1–8 fold (`boc_fold_later.json` unchanged).

## Preflight

```text
python3 projects/monuments/scripts/dia_preflight.py --monument cka --tip "$(git rev-parse HEAD)"
# RESULT: PASS (no P0/P1)
```

Shared preflight update: optional `config/preflight_ledger_baseline.json` for partial CKA ingest; episode `0` drafts skipped for citation/orphan checks (ledger-only).

## Known gaps

- Seq 11+ not ingested (future batches).
- BoC series eps 1–8 remain fold-later; ledger baseline is preflight-only, not full CKA ingest.
- `verify_drafts` / Tessie / Transit not run in this PR.

## Neo4j

**No Neo4j** writes or promote in this batch.
