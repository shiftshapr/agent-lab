# Source of truth: episode JSON (ROADMAP 3.0)

`source/episode_NNN.json` is the master copy of each episode. `drafts/episode_NNN.md` is rendered from it.
`scripts/source/cka_source.py` defines the model:
- An episode is an ordered list of blocks.
- A register item (claim, artifact, node, meme) has an id, its header, its label and ordered lines.
- A line is a `Key: value` field or a raw line.
- Anything else is kept as text blocks, so all four generations of draft layout render back byte for byte.

CI runs `cka_source.py check`. It validates the schema (kinds, id prefixes, required claim fields, unique claim ids)
and fails if any draft is not exactly the render of its JSON.

## Writing (phase B, 2026-10-21)
The JSON is the only thing edited:
- **Tools:** every tool that changes an episode reads it with `read_draft_text(seq)`, which renders it from the JSON,
  and writes with `write_draft_text(seq, text)`. That parses the text, checks the round trip and the schema, saves the
  JSON and re-renders the draft. This covers the integrators, `apply_name_corrections`, `qa/apply_fixes`,
  `renumber_claims`, `merge_person_nodes`, `supplement_memes_backfill`, `daily/intake` and
  `catchup_build_inscription`.
- **Structured edits:** `load(seq)`, `items` / `field` / `set_field`, then `save(doc)`.
- **Hand edits:** `cka_source.py export NNN > ep.md`, edit, then `cka_source.py import NNN ep.md`.
- **One-off scripts from before the switch** (`batch2_*`, `catchup_*` except `catchup_build_inscription`, `pr43_*`,
  `remap_boc_batch1`, `hostile_fix_batch1`, `compact_node_ids`, and the old `.sh` drivers) edit drafts directly. They
  now refuse to run unless `CKA_ALLOW_LEGACY=1`.
- **Recovery:** `cka_source.py sync --from-drafts` only.
