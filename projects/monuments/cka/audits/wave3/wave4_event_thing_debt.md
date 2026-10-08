# Wave 4 debt (do not mint in Wave 3)

Sequencing lock: Wave 3 → Wave 4 → Ties edges → PR 55 rebase.

Wave 4 will add Event and Thing node types in N-1000..N-9999 and reclassify Topics that are really events or objects (keep ids and intro order, no duplicate mints).

Wave 3 explicitly did **not** mint new Topics for clear events/objects. Leave those as debt here / in deferred triage CSVs.

Examples deferred rather than tip-minted as topics:
- Memorial / concert / appointment events referenced only as narrative (ep150 memorial framing, Ye Chicago concert week) – stay claim-level or wait for Event type.
- Physical objects (receipts, SD cards, vehicles) when they would otherwise force a new topic mint – leave Related empty or use existing investigation targets.

## Wave 3 resubmission additions

- **Bride of Charlie** (former M-85, removed): series/work title, not a catchphrase. It is a Thing (work) for Wave 4, not a meme. See memes_decisions.csv.
- Works, products, events and objects named in claims that missing_nodes_triage.csv marks `DEFER` with the Wave 4 reason (for example Hollywood Babylon, Truman Show, Dodge Challenger, Lincoln Navigator, Google Maps/Drive, Microsoft Teams, Wayback Machine, Project Aurora, Operation Bright Star, Valhalla Strike, Epstein Files, Miss Universe, Paris Design Week, Arizona Commanders Summit, Sandy Hook). None were minted as Topics.
- Project Looking Glass is not debt: it already exists as topic N-1484 (missing_nodes_triage KNOWN, Transit b558034).

## Carried forward from the Transit re-audit at b558034

- **F10, named_before_intro debt:** 40 person/episode pairs (41 before the N-952 → N-916 merge removed one) for pre-Wave-3 persons named in a claim before their intro episode (e.g. Adelson named ep31, intro ep161). This is the same late-intro class Wave 3 fixed for its own mints. Listed in `named_before_intro_debt.csv` and accepted by the `named_before_intro` gate. Fix in Wave 4 by moving intros earlier, not by renumbering ids (the person band is locked).
- **F4, 19 skeleton episodes** (84, 95, 100, 101, 103–106, 108, 109, 111–119; about 358 claims and 436 artifacts missing). Pre-existing since PR #43; Transit says do not block PR 62. This is the next item after Wave 3. Known DIA bounty beats there (ep101 00:54, 05:41, 11:18; ep117 54:23) are DEFER in `dia_gaps_triage.csv` and will be claimed in that pass.
