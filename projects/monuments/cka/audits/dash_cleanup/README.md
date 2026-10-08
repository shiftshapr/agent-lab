# CKA dash cleanup (8 Oct 2026)

Dash-only PR on top of main `67d42d9` (PR 60 squash). Plan: Transit's dash audit
(`/workspace/cka-audit/dash-audit-2026-10-08/`, written against PR 60 head `62442e7`), every row
re-derived against `67d42d9`. No other data changes. Staged only: no Neo4j, pack, BoC data or deploy.

## Rule (Daveed, 8 Oct 2026)

- In prose, an em dash (U+2014) becomes an en dash (U+2013).
- A dash is never rewritten as a comma, period, colon, semicolon, parentheses or a spaced hyphen.
- Claim titles and claim bodies get the same swap, as a punctuation-only change with no Revises claims.
- Quote fields (Transcript Snippet, Quote, meme quotes, quoted spans, verbatim transcript lines) stay
  exact to the transcript, em dashes included.

## Files

| File | Rows | What |
|---|---|---|
| `prose_swaps.csv` | 1459 | Prose dash fixes: drafts 973, inscription 424, docs 15, canonical 12 (nodes.json names and aliases 11, memes.json 1), config 2, scripts 10 (comments, docstrings, printed headers, the batch2 placeholder, and the neo4j assert comment), test fixtures 2, wave1 CSV ' - ' renderings 17, BoC-era spaced hyphens used as dashes 4 (A-1113 bundle name and the ep006 executive summary, md and json). |
| `claim_text_dashes.csv` | 336 | Claim-text em dashes swapped to en dashes: 168 in drafts (132 in Claim bodies, 36 in claim titles) and the same 168 in inscription (`claim` / `label`), in 128 fields per side across 127 claims. The restored originals C-1566, C-1743, C-3545, C-3561, C-3616 are included. No Revises claims. |
| `history_restorations.csv` | 26 | Dashes that commits since 27 Sep had rewritten as other punctuation, restored as en dashes: the 23 rows from Transit's audit plus 3 copies of the same 56cc8d2 rewrites in `inscription/episode_086.json` (2) and `inscription/episode_142.json` (1). |
| `companion_labels.csv` | 486 | BRC-222 companion node labels that changed after `_ascii_dashes()` was removed: 485 that the builder had flattened to '-' (381 spaced ' - ', 104 unspaced ranges like `10–19`) plus A-1113, whose source bundle name changed. Bridges unchanged (9209, `bridges.json` byte-identical). |

## Not swapped

- Code that reads legacy dashes is unchanged in behaviour: the timestamp regexes in
  `dia_preflight.py`, `batch2_fix_stamps.py`, `batch2_normalize_draft.py` and the hostile audit
  parser still accept an em dash, now written as the `\u2014` escape (7 spots).
- Quote fields: 0 em dashes before and after. The transcripts carry no em or en dashes.
- ep067 N-1/N-2 (optional in Transit's list): left as is. The node header now holds only the
  canonical name, and the description is its own sentence, so no dash was replaced by other
  punctuation in the current text.

## Other changes

- ep119 M-55: the quote was a pasted chapter list (' - ' bullets, `## Start.`). Replaced with the
  verbatim spoken line under [41:12]: "Especially cuz Tucker has been trending all weekend for saying
  the quiet part out loud regarding Charlie Kirk's death."
- `cka_brc222_companion.py`: `_ascii_dashes()` removed. Labels and Revises evidence snippets are
  emitted exactly as stored; builder-written explanations go through `_prose_dashes()` (em to en).
- `dia_preflight.py`: new opt-in gates `prose_em_dash` (P2) and `quote_dash_fidelity` (P1), enabled
  for CKA in `config/preflight_gates.json` (`dash_rule`). BoC does not opt in and its preflight output
  is unchanged.
- Checklist wording in ep160/161, `DIA_PREFLIGHT.md`, the wave1 README and wave2 README item 6
  now state the en dash rule.
