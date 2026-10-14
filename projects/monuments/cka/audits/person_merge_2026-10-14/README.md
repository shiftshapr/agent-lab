# Review fixes and person merge (2026-10-14)

Daveed's review rulings on the batch 3–5 review items.

## Name and transcript checks (HappyScribe as a second transcript)
HappyScribe publishes independent transcripts of the show at https://podcasts.happyscribe.com/candace. Pages are `/candace/{title-slug}`, with timestamped blocks and no speaker labels. When our corrected transcript is unclear, it serves as a second reading.
- **Ike Perlmutter (ep70, Candace Ep 303).** HappyScribe 00:04:58 reads "Charlie had taken a meeting down in Florida with Ike Perlmutter at Mar-a-Lago." Our transcript has "Ike Promoter". C-8379 and C-8380 now name Perlmutter, and "Ike Promoter" is an alias of the node.
- **Don Orrico (ep70).** HappyScribe 00:12:23 reads "Mr. Don O'Reco of Turning Point USA down in Tampa". Our transcript has "Don Oro". The node is renamed **Don Orrico** (now N-817), with aliases Don Oro and Don O'Reco. The identification follows Daveed: Don Orrico is a Florida-based major-gifts fundraiser, formerly the Mackinac Center's director of strategic partnerships (https://www.mackinac.org/about/staff/795). No public source ties him to TPUSA; C-8396's Investigative Direction says so.

## Corrections
- **C-2193 (ep62) erratum.** The earlier extraction merged two people. In the transcript, Marina Minas is mentioned as "involved in a lot of this", while the employee fired after the fake Zoom call is an unnamed part-time employee. The claim text is corrected in place and Mentions now lists the general counsel only. This was an extraction error, not a walk-back by the host, so no `Revises:` edge was added.
- **C-8598 vs C-3804 (clinic vs hospital).** C-8598 (ep88) puts Erika's mother at a treatment facility on Sept 8. C-3804 (ep84) says she was not in the hospital Sept 8–10. The facility is treated as a clinic, per ep68 C-10031 and ep76 C-10287, so C-8598 now `Qualifies: C-3804` instead of contradicting it. The flag is noted in C-8598's Investigative Direction and in ep88's Optional Flags.
- **C-8112 (ep45) departure times.** Both times come from the same tipster email: "at 12:31 p.m. … it flies from Fort Wuka to El Paso" (00:44:18) and "leaving at 11:43 a.m." (00:47:10). The hop takes about 45–50 minutes, so 11:43 is most likely the departure and 12:31 the El Paso arrival. This is recorded in the Investigative Direction.
- **Loomer quote (C-8810).** Kept as aired.
- **Ep135 Ashley Brown Guajardo.** The 11 claims about the medical examiner's wife are tagged `relevance:tangential`. C-11660, about his move to become New York chief medical examiner, stays `core`.

## Relevance tags in inscriptions
The inscription builder fills claim `tags` from sensitive-topic tags only, so the drafts' `Tags: relevance:*` lines had not reached the inscriptions. Only 28 claims, hand-tagged in batch 1, carried a relevance tag there. `scripts/sync_claim_tags.py` adds draft tags to inscription claims without removing any; 5,542 tags were added. Now 5,495 claims carry a relevance tag in both the drafts and the inscriptions.

## Person merge
`scripts/merge_person_nodes.py N-506:N-15` folded **N-506 "Justin (TPUSA COO)"** (ep63) into **N-15**. N-15 is renamed from the transcribed "Justin Strife" to **Justin Streiff**; both earlier names are kept as aliases. Person ids N-507..N-918 shift down by one (N-918 is now `next_person_id`), and the full map is in `id_map.csv`. Earlier audit READMEs keep the ids of their time, so read them through `id_map.csv`.

The other duplicate pairs listed in `../supplement_2026-10e/README.md` wait for confirmation. They can be merged in one more run of the same script.
