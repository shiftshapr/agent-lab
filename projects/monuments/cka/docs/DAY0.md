# CKA – Day 0 plan

## Month plan

- Ingest in **chronological airdate order** from `input/episode_manifest.json` (~**10 episodes per day** in batch runs).
- **Remap, do not re-extract** for content already analyzed under BoC monument eps **9–18** (Kirk tribute + Candace **235–243**). Point ledger/artifact IDs at CKA `seq` and preserve transcript SHA alignment.
- When chronology reaches **Feb–Mar 2026**, fold **Bride of Charlie** series eps **1–8** from `input/boc_fold_later.json` into CKA (membership tags pre-declared in `config/membership_tags.json`).
- **BoC** remains demo-only; no new Candace ingest there.

## QA bar

1. `python3 projects/monuments/scripts/dia_preflight.py --monument cka --tip "$(git rev-parse HEAD)"`
2. Pipeline verify / Tessie sample on first batch
3. Transit pack review (Bill D) before promote
4. **No production Neo4j** from agents
5. **Person band lock** (until Daveed rules): no new person ids; new persons are DEFER "person band full, awaiting Daveed"; while the lock is in force, no reuse of a retired/tombstoned/reserved id and no person at N-1000+; the reuse policy itself is pending with Daveed (gate `person_band_lock`, pinned band `config/person_band_snapshot.json`, see README ID bands)
6. **DIA scan:** run the tip-line cues in `config/dia_scan_terms.json` (includes `bounty`) over each new transcript; claim or triage every hit

## Promote freeze

Do not promote mixed BoC tip **`7e4c948`**. CKA is the long-term corpus path.

## Fold-later BoC series

See `input/boc_fold_later.json` for the eight-playlist episodes and planned fold window.

## Epistemic graph (Phase A)

See [`EPISTEMIC_GRAPH.md`](EPISTEMIC_GRAPH.md) for claim immutability, `Revises:` / `Contradicts:` / `Mentions:` draft syntax, and preflight `claim_fork`. Phase B/C wait.
