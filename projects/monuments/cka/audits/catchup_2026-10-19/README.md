# Catch-up: Candace Ep 399–403 (CKA seq 162–166), 2026-10-19

| seq | Ep | date | YouTube | claims |
|---|---|---|---|---|
| 162 | 399 | 2026-10-07 | yrg_-D6oNHE | 89 |
| 163 | 400 | 2026-10-08 | UAdBEXs7nNc | 87 |
| 164 | 401 | 2026-10-13 | V-phmW9f0pM | 86 |
| 165 | 402 | 2026-10-14 | 6jOEN9rBePU | 77 |
| 166 | 403 (inferred; the title has no number) | 2026-10-15 | YPIYYHCNPbE | 92 |

## Method
1. **Transcripts.** YouTube's original-English auto captions (`en-orig`) were converted with
   `scripts/vtt_to_cka.py`.
   - These videos also carry dubbed audio tracks. The plain `en` track is a machine translation of a dub, so it
     must not be used.
   - The captions are punctuated, with cue-level timing. Paragraph blocks run about 30 s and break at chapter
     starts.
   - Existing name rules were applied by `apply_name_corrections.py`.
2. **Extraction.** One Opus agent per episode followed `audits/skeleton_fill_2026-10-13/EXTRACTION_SPEC.md` and
   `CATCHUP_PROMPT.md`, which adds the rulings since: relevance tags, attribution, names and the timestamp window.
   Every snippet was machine-checked as verbatim with `check_skeleton_staging.py`.
3. **Integration.** `fill_skeleton_integrate.py` (batch `catchup-2026-10-19`) produced:
   - claims C-15061 to C-15493 and artifacts to A-3408;
   - 22 new persons (N-949 to N-970), 33 new topics and orgs (N-11412 to N-11444), and 12 new memes.
4. **Intro moves.** Alex Faria (N-954) and Blake Gibson (N-955) were already named in ep147 and ep149. Their
   introductions moved there, with ids unchanged.
5. **Names.** 48 correction rules come from the agents' MISTRANSCRIPTION flags; most are scoped to these
   episodes. Examples: Katie Zacharia, Val Peterson, Wayne Niederhauser, Christopher Rhoades, Tyler Bowyer,
   Maycee Crofts and Losee Center. "Erica" becomes Erika in seq 162–166. First-name-only mappings resting on
   inference (Justin and Dan in Turek's book) were left out of Mentions.
6. **Opus check at intake.** Eight Opus reviewers checked all 431 claims, and an Opus confirm pass followed.
   - 19 material findings: 18 accepted and 1 amended. 30 fixes applied, including 11 minor.
   - Name fixes: Christine Fekete, Hank McIntire, Brandon Blackmore.
   - Material rate at intake, before fixes: 4.4%. The archive's QA sample after pass 2 was 0.7%.

## Open (for Daveed's ear)
- Matiss Tabuns (N-949 range, ep162). The host spells T-A-B-U-N-S and says the earlier "Matt Servius" (N-351) was
  wrong. A merge, or a rename of N-351, is pending confirmation.
- Unconfirmed names: Taylor Dodd, Charles Peterson (Val Peterson's brother, per the host), La Fieta Assisi (ICAC)
  and Alex Faria.
