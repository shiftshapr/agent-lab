# Name rulings and duplicate-person merge (2026-10-14, second pass)

## Rulings (Daveed)
- **A mis-transcribed name is not an alias**, and it must not survive anywhere, including transcript snippets and meme quotes. Daveed listened to "Ike Promoter" and "Don Oro": the host said Perlmutter and Orrico, and the transcriber got them wrong.
- **Fort Wuka is always Fort Huachuca.**
- **"Bobby Saucelito" is Bobby Sausalito.**

## How the corrections are applied
`config/transcript_name_corrections.json` lists the corrections as regexes. `scripts/apply_name_corrections.py` applies them everywhere a name can live: `transcripts_corrected/` (62 files), drafts on every line, snippets and quotes included (43), and inscriptions on every string (42). It also drops the 7 node aliases they rewrite. Because the transcript is corrected along with the snippets, the snippets are still verbatim substrings and the preflight snippet check passes. The script should run on each new transcript before extraction.

Corrections in this pass:
- Fort Wuka → Fort Huachuca
- Saucelito → Sausalito
- Ike Promoter → Ike Perlmutter
- Don Oro → Don Orrico
- Fraudsham, Rodsham and Frodshem → Frodsham
- Eric Bowling → Eric Bolling
- Brendan Tatum → Brandon Tatum
- Phil Turney → Phil Tourney
- Paul Valli and Paul Vali → Paul Vallely
- Ian Carol → Ian Carroll
- Rob Koy and Bob Koy → Bob Coy
- Kaye McAney and Kaylee Mcaney → Kayleigh McEnany
- Constantine Kissen → Konstantin Kisin
- Justin Strife, Stripe, Streif and Strieff → Justin Streiff

## Duplicate persons merged
`scripts/merge_person_nodes.py` folds each later node into the one introduced first, so no introduction moves. Where an episode had only the later node's register row, that row was renamed to the kept node. The kept node takes the correct name. The ids below are the pre-merge ids; `id_map.csv` gives every shift.

| Kept (pre-merge id) | Merged in | Name |
|---|---|---|
| N-58 | N-228 | Brandon Tatum |
| N-72 | N-289 | Eric Bolling |
| N-131 | N-384 | Ian Carroll |
| N-771 | N-261 | Bob Coy |
| N-394 | N-816 | David Frodsham |
| N-814 | N-459 | Paul Vallely |
| N-509 | N-662 | Phil Tourney |

N-699 Philip Goldsberry Jr. and N-700 Dr. Philip Goldsberry are father and son, so they stay separate. After the merge, person ids are dense from N-1 to N-910, and `next_person_id` is N-911.
