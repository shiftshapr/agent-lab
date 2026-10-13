# Skeleton episode fill (2026-10-13)

Fills the 19 CKA episodes whose drafts had empty registers: seq 84, 95, 100, 101, 103–106, 108, 109 and 111–119 (Candace Ep 317–353). Seq 118 had one claim, so it is included.

## Method

1. **Extraction.** One Claude agent per episode extracted the draft from `transcripts_corrected/` following `EXTRACTION_SPEC.md`.
   - Agents used placeholder ids and reused existing node and meme ids from `canonical/`.
   - Every Transcript Snippet was machine-checked as an exact transcript substring (`check_staging.py`).
   - DIA tip-line and bounty beats got the M-12 treatment from `config/dia_scan_terms.json`. This includes the deferred ep101 and ep117 beats from the Wave 3 `dia_gaps_triage.csv`.
2. **Integration.** `cka/scripts/fill_skeleton_integrate.py` assigned global ids in airing order.
   - New persons are Tip-minted from `next_person_id`, and new topic/org/place nodes from `next_investigation_id`. Both are listed on `Tip-minted Nodes (skeleton)` ledger lines.
   - Titles were deduped across the batch by name, with the extra merges in `title_merges.json`.
   - Existing items were kept with their ids: C-3751, C-3753, A-2522, N-16, the N-163 hole-mint, and the meme occurrences.
3. **Intro moves.** These episodes air before many episodes that introduced the people and topics they cite. The 55 nodes in `intro_moved_earlier.csv` therefore now have their introduction in the skeleton episode. That episode carries a `Hole-minted Nodes (reintro-epNNN)` line, and the later episode's New/Hole-minted entry moved to Reused. Node ids are unchanged.
4. **Gate fixes.**
   - Four ungrounded Mentions were dropped (C-4227 N-276, C-4304 N-30, C-4489 N-69, C-4761 N-221).
   - Four "her husband" role references were added to `mention_grounding.reviewed`.
   - Aliases were added: Nicci, Niecy → N-576; Rothschilds → N-532.
   - Three named-before-intro pairs were accepted with reasons: Marco Rubio (ep75), Scott Bessent (ep80) and Katherine Locastro (ep83). The node is minted in this batch, but older claim text already names the person.
5. **Inscriptions and companion.** Inscriptions were rebuilt for the 19 episodes only (series "Candace Kirk Archive", model_version from the draft). Older episodes' inscriptions are unchanged, because the intro moves touch draft ledger lines only. The BRC-222 companion was regenerated.

## Result

| | Count |
|---|---|
| Claims | 1,061 new (C-3777..C-4837) |
| Artifact families | 185 new (A-2525..A-2709) |
| New persons | 114 (N-608..N-721) |
| New topic/org/place | 98 (N-10903..N-11000) |
| New memes | 35 (M-85..M-119) |
| Bridges | 9,288 → 11,580 |

Claim density averages about 56 per episode, against about 20 in earlier waves. Every claim has a verbatim snippet.

## Needs human review

**Possible wrong identity**
- **"Jessica Garza"** (ep103): the host's hedged name for an Aurora victim who had survived a Toronto shooting. The public record has **Jessica Ghawi (Redfield)**. Kept as spoken; verify.
- **Golshifteh Farahani** (ep104): inferred from the host's mispronunciations.
- **"Kayla Robinson"** (ep100, Daily Wire interim CEO): may be Caleb Robinson.
- **"Ed Galvin"** (ep108): may be Ed Gallrein.
- **Eliza McCoy (N-221):** mapped from "Elizabeth McCord" in ep84 and from "Elizabeth Kravchuk" in ep118.

**Unverified spellings (kept as the transcript has them)**
- Sergeant Dupey; "Jamie" (pilot); Ryan Ripian; Gustav Anderly; Richard Smaly; Michaela Mott; Father Klein.
- Shawn Chenowith; Raphael Schriber; Gabrielle Kuchta; James Katis; Vance Voytberg; "Auto Buscher".
- Curtis Kolvet (surname from "Kolvet's brother"); Courtney Thief; Chris Ley; Robert Golow; John Bray; Desmond Holly; Matthew Silverstone; Mark A. Liti.

**Modelling questions**
- **Gary Melton (new person) vs N-10899 "Paramount Tactical Valhalla":** C-2907 treats Paramount Tactical and Valhalla as separate entities, so the node may need splitting.
- **New Dhillon Law Group and Show Faith by Works LLC org nodes** sit next to the existing topic N-10652. Consider Ties edges.

**Links not yet added (follow-up pass)**
- Links between episodes in this batch (agents could only link to already-indexed claims). For example, ep106's host concession that the Military Office may not have sent the WHCD email should Qualify the ep104/105 email claims. In ep118, the host's two on-air self-corrections are recorded as claims without Revises links.
- Links to later episodes (for example the ep117 CPR claims against C-2968+). These are left for Wave 4 date work.

**Companion**
- Same-host `Supports:` maps to `isCorroboratedBy`, which BRC-222 defines as independent. That raised corroboration edges from 9 to 114; it is to be fixed in the companion mapping.
