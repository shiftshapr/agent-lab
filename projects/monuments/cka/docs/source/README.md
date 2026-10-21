# Source of truth: episode JSON (ROADMAP 3.0)

`source/episode_NNN.json` is the master copy of each episode. `drafts/episode_NNN.md` is rendered from it.
`scripts/source/cka_source.py` defines the model:
- An episode is an ordered list of blocks.
- A register item (claim, artifact, node, meme) has an id, its header, its label and ordered lines.
- A line is a `Key: value` field or a raw line.
- Anything else is kept as text blocks, so all four generations of draft layout render back byte for byte.

CI runs `cka_source.py check`. It validates the schema (kinds, id prefixes, required claim fields, unique claim ids)
and fails if any draft is not exactly the render of its JSON.

## Writing
- **Library (preferred):** `load(seq)`, then `items`, `field` and `set_field`, then `save(doc)`. `save` writes the JSON
  and re-renders the draft.
- **Transitional (Phase A, 2026-10-21):** the older tools (integrators, name corrections, apply_fixes, renumber and
  merge) still edit the Markdown. Run `cka_source.py sync` afterwards; `scripts/daily/finalize.py` does this
  automatically. Sync refuses any draft that does not round-trip.
- **Phase B:** these tools move to the library one by one, after which `sync` is retired and the JSON is the only
  thing edited.
