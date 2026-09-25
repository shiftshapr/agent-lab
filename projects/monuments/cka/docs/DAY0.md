# CKA — Day 0 plan

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

## Promote freeze

Do not promote mixed BoC tip **`7e4c948`**. CKA is the long-term corpus path.

## Fold-later BoC series

See `input/boc_fold_later.json` for the eight-playlist episodes and planned fold window.
