# Node register names — full dump from current drafts

**→ Fix names (copy-paste): [`FIX_NAMES.md`](./FIX_NAMES.md)** — `neo4j_corrections` → `apply-dir` → regen → `neo4j_ingest --no-fuzzy-match`.

**Purpose:** One place to review every `**N-*` label in `drafts/episode_*.md`, spot bad caption/LLM spellings, and fix them (transcript corrections → regen → re-ingest).

**Regenerate this table** (if drafts change):

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
rg '^\*\*N-\d+\*\*' drafts/episode_*.md
```

**Graph + `NameCorrection` snapshot:**

```bash
uv run --project ../../../framework/deer-flow/backend python scripts/list_names_audit.py --out names_audit.md
```

**Frantzve / Erika policy:** see `docs/NAME_AUDIT_FRANTZE.md`. **Surname:** canonical **`Frantzve`** everywhere (nodes, graph, transcripts). **`Frantze`** only when quoting an artifact’s exact spelling.

### Same person, more than one name (one `N-*`, not two nodes)

Use **one** register title for the canonical label you want in the graph (e.g. **Erika Kirk** after marriage). On the next line, an italic **Also known as** row lists other strings that refer to that **same** person (maiden/pre-marriage name, caption garbage, etc.):

```markdown
**N-12** Erika Kirk

*Also known as: Erika Frantzve (birth / pre-marriage name); Erika Frantzve Feay (caption variant). Same person — married name Kirk.*

Primary subject of investigation. …
```

- Separate alternate names with **`;`** (semicolons).  
- `neo4j_ingest.py` reads this line and stores each segment (minus the register title) on the Person as **`aliases`**; **`canonical_name`** stays the `**N-*` title.  
- Phase 1 JSON may use **`also_known_as`** (array) on the same node object — see `templates/entity_schema.json`.

---

## When a name is wrong — what to do (in order)

**A. The bad string comes from the YouTube captions** (same garbage in `transcripts/*.txt`):

1. **Teach the dictionary** (substring replace on raw → corrected copies only):

   ```bash
   cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
   uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py add "WRONG" "RIGHT" --confidence high
   ```

2. **Kill bad auto-imports** (verify_drafts once suggested something stupid):

   ```bash
   uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py list
   uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py remove "exact WRONG string as shown in list"
   ```

3. **Rebuild corrected transcripts** (raw files stay untouched):

   ```bash
   uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py apply-dir transcripts/
   ```

4. **Regenerate analysis** so drafts + phase1 match new text — full workflow, or one episode:

   ```bash
   # See AUTOMATED_WORKFLOW.md — EPISODE_ANALYSIS_ONLY + FORCE
   ```

5. **Reload the graph** (after drafts look right):

   ```bash
   uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_ingest.py --force --no-fuzzy-match
   ```

   Use `--no-fuzzy-match` while you’re fixing names so bad captions (e.g. “Kent Bronze”) don’t get merged into the wrong people.

**B. Transcript is already right, only the draft / graph is wrong**

- Edit the **markdown draft** Node Register line for that `N-*`, or fix **phase1 JSON** + rerun **`assign_ids.py --batch`**, then **`neo4j_ingest.py --force`**.

**C. Neo4j already has a wrong `canonical_name` or alias** (merge fallout)

- Either fix in **Browser** (edit node props / remove bad alias) or **clear non–NameCorrection graph** and re-ingest from fixed drafts:

  ```bash
  # ingest --force already clears graph but keeps NameCorrection; then re-ingest
  ```

**Rule of thumb:** fix **source text** (`NameCorrection` + `transcripts_corrected/`) for systematic caption errors; fix **drafts/graph** for one-off extraction mistakes.

**Just need to say “this is wrong” on the record (before you fix it):**  
→ [`NAME_ISSUES.md`](./NAME_ISSUES.md) + `scripts/flag_issue.py` (see that file for the one-liner).

---

## 1. Every node line by episode file

*(Regenerate with `rg '^\*\*N-\d+\*\*' drafts/episode_*.md` if drafts change.)*

**Deduping policy:** one **Person** node per real individual — caption variants go in the blurb under the `**N-*` line, not in a second register title. **Erpenbeck** scandal thread uses *two* investigation-theme nodes (same family; caption noise normalized in transcripts), split by episode focus: Lori LLC/notary pattern vs Erika & uncle Rick — not two unrelated themes.

| Episode file | N-id | Label (exactly as in draft) |
|----------------|------|----------------------------|
| episode_001_episode_001_ZAsV0fHGBiM.md | N-11 | Charlie Kirk |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-12 | Erika Kirk |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-13 | Lori Frantzve |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-14 | Kent Frantzve |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-15 | Loretta Lynn Abbis |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-16 | Mason Abbis |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-17 | Carl Fron |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-18 | Jack Solomon |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-19 | Elizabeth Lane |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-20 | Larry Ginta |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-1008 | Date of Birth Discrepancy |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-1009 | Marriage Date Inconsistencies |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-1010 | Early Childhood Location Timeline |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-1011 | Family Gambling/Casino History |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-1012 | Swedish Citizenship Pursuit |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-1013 | Morfar vs Farfar Language Error |
| episode_001_episode_001_ZAsV0fHGBiM.md | N-1014 | Zion's Gate Family Dedication Claim |
| episode_002_episode_002_1IY2oD-_xVA.md | N-21 | Charlie Kirk |
| episode_002_episode_002_1IY2oD-_xVA.md | N-22 | Candace Owens |
| episode_002_episode_002_1IY2oD-_xVA.md | N-23 | Erika Kirk |
| episode_002_episode_002_1IY2oD-_xVA.md | N-24 | Dr. Jerry Frantzve |
| episode_002_episode_002_1IY2oD-_xVA.md | N-25 | Kent Frantzve |
| episode_002_episode_002_1IY2oD-_xVA.md | N-26 | Lori Frantzve |
| episode_002_episode_002_1IY2oD-_xVA.md | N-27 | Tyler Bowyer |
| episode_002_episode_002_1IY2oD-_xVA.md | N-28 | Elizabeth Lane |
| episode_002_episode_002_1IY2oD-_xVA.md | N-29 | Phil Bliss |
| episode_002_episode_002_1IY2oD-_xVA.md | N-30 | Dr. John Money |
| episode_002_episode_002_1IY2oD-_xVA.md | N-1015 | Date of Birth Discrepancy |
| episode_002_episode_002_1IY2oD-_xVA.md | N-1016 | Jerry Frantzve Background Verification |
| episode_002_episode_002_1IY2oD-_xVA.md | N-1017 | Missing Money from Turning Point USA |
| episode_002_episode_002_1IY2oD-_xVA.md | N-1018 | Tesaract School Investigation |
| episode_002_episode_002_1IY2oD-_xVA.md | N-1019 | Radford University Report Credibility |
| episode_002_episode_002_1IY2oD-_xVA.md | N-1020 | Erika Pageant Narrative |
| episode_003_episode_003_cZxHqYsWRYg.md | N-31 | Candace Owens |
| episode_003_episode_003_cZxHqYsWRYg.md | N-32 | Erika Kirk |
| episode_003_episode_003_cZxHqYsWRYg.md | N-33 | Lori Frantzve |
| episode_003_episode_003_cZxHqYsWRYg.md | N-34 | Richard Erpenbeck |
| episode_003_episode_003_cZxHqYsWRYg.md | N-35 | Tyler Bowyer |
| episode_003_episode_003_cZxHqYsWRYg.md | N-1021 | Erpenbeck fraud pattern — Lori LLCs & notaries |
| episode_003_episode_003_cZxHqYsWRYg.md | N-1022 | Erika Timeline Discrepancies |
| episode_004_episode_004_jTj9Ip46r4w.md | N-36 | Charlie Kirk |
| episode_004_episode_004_jTj9Ip46r4w.md | N-37 | Erika Kirk |
| episode_004_episode_004_jTj9Ip46r4w.md | N-38 | Lori Abbis Stanley |
| episode_004_episode_004_jTj9Ip46r4w.md | N-39 | Dr. Jerry Frantzve |
| episode_004_episode_004_jTj9Ip46r4w.md | N-40 | Kent Frantzve |
| episode_004_episode_004_jTj9Ip46r4w.md | N-41 | Angelina Lombardo-Abbis |
| episode_004_episode_004_jTj9Ip46r4w.md | N-42 | Vince Lombardi |
| episode_004_episode_004_jTj9Ip46r4w.md | N-43 | Uncle Jack Solomon |
| episode_004_episode_004_jTj9Ip46r4w.md | N-44 | Richard Erpenbeck |
| episode_004_episode_004_jTj9Ip46r4w.md | N-1023 | Date of Birth Discrepancy |
| episode_004_episode_004_jTj9Ip46r4w.md | N-1024 | Lombardi Lineage Claim |
| episode_004_episode_004_jTj9Ip46r4w.md | N-1025 | Missing Years Timeline |
| episode_004_episode_004_jTj9Ip46r4w.md | N-1026 | Erpenbeck criminal connections — Erika & uncle Rick |
| episode_005_episode_005_2tFYJf1klgY.md | N-45 | Charlie Kirk |
| episode_005_episode_005_2tFYJf1klgY.md | N-46 | Erika Kirk |
| episode_005_episode_005_2tFYJf1klgY.md | N-47 | Lori Frantzve |
| episode_005_episode_005_2tFYJf1klgY.md | N-48 | Dr. Jerry Frantzve |
| episode_005_episode_005_2tFYJf1klgY.md | N-49 | Nancy Gerard Hall |
| episode_005_episode_005_2tFYJf1klgY.md | N-50 | Tyler Bowyer |
| episode_005_episode_005_2tFYJf1klgY.md | N-51 | Richard Erpenbeck |
| episode_005_episode_005_2tFYJf1klgY.md | N-52 | Jeffrey Epstein |
| episode_005_episode_005_2tFYJf1klgY.md | N-53 | Colonel Otto Busher |
| episode_005_episode_005_2tFYJf1klgY.md | N-1027 | Erika Kirk Missing Years 2000-2002 |
| episode_005_episode_005_2tFYJf1klgY.md | N-1028 | E3 Tech Military Contracts |
| episode_005_episode_005_2tFYJf1klgY.md | N-1029 | Romanian Base Trafficking Connection |
| episode_006_episode_006_y8lak3CRwDw.md | N-54 | Candace Owens |
| episode_006_episode_006_y8lak3CRwDw.md | N-55 | Erika Kirk |
| episode_006_episode_006_y8lak3CRwDw.md | N-56 | Charlie Kirk |
| episode_006_episode_006_y8lak3CRwDw.md | N-57 | Tyler Bowyer |
| episode_006_episode_006_y8lak3CRwDw.md | N-58 | Dennis Frantzve |
| episode_006_episode_006_y8lak3CRwDw.md | N-59 | Colonel Otto Busher |
| episode_006_episode_006_y8lak3CRwDw.md | N-60 | Curtis Kolvet |
| episode_006_episode_006_y8lak3CRwDw.md | N-61 | Robert Kolvet |
| episode_006_episode_006_y8lak3CRwDw.md | N-62 | Andrew Kolvet |
| episode_006_episode_006_y8lak3CRwDw.md | N-63 | Justin Strife |
| episode_006_episode_006_y8lak3CRwDw.md | N-64 | Lori Frantzve |
| episode_006_episode_006_y8lak3CRwDw.md | N-1030 | Romania Connection Pattern |
| episode_006_episode_006_y8lak3CRwDw.md | N-1031 | Reno Nevada Military Connection |
| episode_006_episode_006_y8lak3CRwDw.md | N-1032 | How Erika Met Tyler Bowyer |
| episode_006_episode_006_y8lak3CRwDw.md | N-1033 | E3 Tech Purpose |
| episode_006_episode_006_y8lak3CRwDw.md | N-1034 | Turning Point Shooting Adjacencies |
| episode_007_episode_007_DdPjoy5W-wY.md | N-65 | Charlie Kirk |
| episode_007_episode_007_DdPjoy5W-wY.md | N-66 | Erika Kirk |
| episode_007_episode_007_DdPjoy5W-wY.md | N-67 | Candace Owens |
| episode_007_episode_007_DdPjoy5W-wY.md | N-68 | Tyler Bowyer |
| episode_007_episode_007_DdPjoy5W-wY.md | N-69 | Jonah |
| episode_007_episode_007_DdPjoy5W-wY.md | N-70 | Jan Brewer |
| episode_007_episode_007_DdPjoy5W-wY.md | N-71 | Josh Harelson |
| episode_007_episode_007_DdPjoy5W-wY.md | N-72 | Jeffrey Epstein |
| episode_007_episode_007_DdPjoy5W-wY.md | N-1035 | Arizona State University |
| episode_007_episode_007_DdPjoy5W-wY.md | N-73 | JT Massie |
| episode_007_episode_007_DdPjoy5W-wY.md | N-1036 | Pre-Marriage Business Claims |
| episode_007_episode_007_DdPjoy5W-wY.md | N-1037 | Sole Provider Narrative |
| episode_007_episode_007_DdPjoy5W-wY.md | N-1038 | Life Insurance and Fundraising |
| episode_007_episode_007_DdPjoy5W-wY.md | N-1039 | Epstein-ASU-Bowyer Connection |
| episode_007_episode_007_DdPjoy5W-wY.md | N-1040 | Education Credentials |

---

## 2. Worksheet — still TBD / verify

| Label as in draft | Your correct name | Notes |
|-------------------|-------------------|--------|
| Loretta Lynn Abbis | | historical **Loretta Abbis** (1940s PA) — not the singer; draft blurb updated |
| Carl Fron | | *Also known as* **Frantzve** / Fron (ep1); **Frantze** only if a document spells it (quote on artifact) |
| Richard Erpenbeck | | **transcript_snippet** = raw audio; ep3 notary = **Bill Erpenbeck** (not “Rick Erpenbeck”) |
| *(add rows as needed)* | | |

---

## 3. Deduped label strings (A→Z)

Andrew Kolvet  
Angelina Lombardo-Abbis  
Arizona State University  
Candace Owens  
Carl Fron  
Charlie Kirk  
Colonel Otto Busher  
Curtis Kolvet  
Date of Birth Discrepancy  
Dennis Frantzve  
Dr. Jerry Frantzve  
Dr. John Money  
E3 Tech Military Contracts  
E3 Tech Purpose  
Early Childhood Location Timeline  
Education Credentials  
Elizabeth Lane  
Epstein-ASU-Bowyer Connection  
Erika Kirk  
Erika Kirk Missing Years 2000-2002  
Erika Pageant Narrative  
Erika Timeline Discrepancies  
Family Gambling/Casino History  
How Erika Met Tyler Bowyer  
Jack Solomon  
Jan Brewer  
Jeffrey Epstein  
Jerry Frantzve Background Verification  
Jonah  
Josh Harelson  
JT Massie  
Justin Strife  
Kent Frantzve  
Larry Ginta  
Life Insurance and Fundraising  
Lombardi Lineage Claim  
Loretta Lynn Abbis  
Lori Abbis Stanley  
Lori Frantzve  
Marriage Date Inconsistencies  
Mason Abbis  
Missing Money from Turning Point USA  
Missing Years Timeline  
Morfar vs Farfar Language Error  
Nancy Gerard Hall  
Phil Bliss  
Pre-Marriage Business Claims  
Radford University Report Credibility  
Reno Nevada Military Connection  
Richard Erpenbeck  
Robert Kolvet  
Romania Connection Pattern  
Romanian Base Trafficking Connection  
Sole Provider Narrative  
Swedish Citizenship Pursuit  
Tesaract School Investigation  
Turning Point Shooting Adjacencies  
Tyler Bowyer  
Uncle Jack Solomon  
Erpenbeck criminal connections — Erika & uncle Rick  
Erpenbeck fraud pattern — Lori LLCs & notaries  
Vince Lombardi  
Zion's Gate Family Dedication Claim  

---

## 4. After you edit the worksheet

1. Encode transcript fixes: `scripts/neo4j_corrections.py add` / `remove` — see `NAME_AUDIT_FRANTZE.md`.  
2. `apply-dir transcripts/` → refreshes `transcripts_corrected/`.  
3. Re-run episode analysis (full or `--only` affected episodes) or edit drafts manually if you prefer.  
4. `neo4j_ingest.py --force` (consider `--no-fuzzy-match` once names are stable).
