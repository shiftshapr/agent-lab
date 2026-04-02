# Name audit — Frantzve vs France (Bride of Charlie)

> **Policy:** **`Frantzve`** is **canonical** for this family on Person nodes, in the graph, and in transcripts (audio-faithful). Use **`Frantze`** **only** when you are quoting spelling **verbatim from an artifact** (scan, filing, clipping) — never as the default register name.  
> *(Filename `NAME_AUDIT_FRANTZE.md` is legacy; content follows **Frantzve** canonical.)*

**Full table of every `N-*` line in current drafts (editable worksheet):**  
→ [`NAMES_FROM_DRAFTS_AUDIT.md`](./NAMES_FROM_DRAFTS_AUDIT.md)

**Full snapshot (graph + dictionary + draft node lines):**

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
uv run --project ../../../framework/deer-flow/backend python scripts/list_names_audit.py --out names_audit.md
# or print to terminal: omit --out
```

YouTube captions and the LLM often render the family surname as **France** / **Lorie**. Repo transcripts use **`Frantzve`** (replacing bogus STT **“Fronfay”**). Person nodes and graph use **`Frantzve`**. **`Frantze`** appears only inside artifact descriptions or quoted strings when the source document actually spells it that way.

| Role | Prefer (node / records) | Transcript (audio-faithful) | Junk to ignore |
|------|-------------------------|----------------------------|----------------|
| Mother | **Lori Frantzve** | **Lori Frantzve** | `Lori France`, `Lorie France`, `Lori Frontfay` |
| Daughter | **Erika Frantzve** | **Erica/Erika Frantzve** where STT used “Erica” | `Erica France`, `Erika France`, `Erica Kirk` |
| Father | **Kent Frantzve** | *(usually Kent France in STT)* | `Kent France`, **do not** merge “Kent Bronze”, “Kent Bronzeface” |

**Dr. Jerry Frantzve** (stepmother figure) — canonical **`Frantzve`** on the register line; keep **`Dr. France`** only where quoting captions or an artifact verbatim.

**Richard Erpenbeck** — one **Person** node for Erika’s “uncle Rick” / **Erpenbeck** family thread. **Legal spelling: Erpenbeck** (witness lines, court docs, chapter titles). YouTube auto-captions often garbled the single surname **Erpenbeck**; repo **`transcripts/*.txt`** use **Erpenbeck** to match filings. Use **Richard Erpenbeck** on the `**N-*` line and in claims. Ep3 notary block: **Bill Erpenbeck** (not Rick).

**Theme nodes** — same family thread, two *investigation* nodes: **Erpenbeck fraud pattern — Lori LLCs & notaries** (`N-1021`, ep3) vs **Erpenbeck criminal connections — Erika & uncle Rick** (`N-1026`, ep4).

---

## 1. See what will change transcripts (Neo4j dictionary)

From `projects/monuments/bride_of_charlie` (or agent-lab root with adjusted paths):

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py list
```

Review every line. **Remove** bad imports from `verify_drafts` (wrong “correct” spelling):

```bash
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py remove "Kent France"
# repeat for any incorrect→garbage pair you see in `list`
```

*(Requires exact `incorrect` text as shown in `list`.)*

---

## 2. Add **high-confidence** Frantzve corrections

`apply-dir` replaces **longer** `incorrect` strings first (see `ORDER BY size(incorrect) DESC`). Add **full names before** bare surnames if you add both.

Examples (left side must match **raw** `transcripts/*.txt`):

```bash
# Given name: normalize to Erika (k) everywhere in transcripts → corrected pipeline
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py add "Erica France" "Erika Frantzve" --confidence high
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py add "Erika France" "Erika Frantzve" --confidence high
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py add "Erica Kirk" "Erika Kirk" --confidence high
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py add "Lori France" "Lori Frantzve" --confidence high
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py add "Lorie France" "Lori Frantzve" --confidence high
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py add "Kent France" "Kent Frantzve" --confidence high
```

**Optional** (only if captions use these):

```bash
# uv run ... python scripts/neo4j_corrections.py add "Lori Frontfay" "Lori Frantzve" --confidence high
# uv run ... python scripts/neo4j_corrections.py add "Kent Bronzeface" "Kent Frantzve" --confidence high
```

**Avoid** replacing bare `France` globally — it hits unrelated phrases (“Operation Enduring Freedom”, countries, etc.).

---

## 3. Rebuild corrected transcripts (raw unchanged)

```bash
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py apply-dir transcripts/
```

---

## 4. Ripgrep spot-check (raw vs corrected)

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
rg -n "Frantzve|France|Frontfay|Bronze|Bronzeface" transcripts/*.txt
rg -n "Frantzve|France|Frontfay|Bronze|Bronzeface" transcripts_corrected/*.txt
```

You want **Frantzve** on the family triple; **France** only where it is intentionally correct (e.g. country, unrelated people).

---

## 5. Graph / drafts lag behind transcripts

After transcript fixes you still need **regeneration** for drafts + graph to match (full workflow or `--only` episodes), and **`neo4j_ingest.py --force --no-fuzzy-match`** once names are stable so **Kent Frantzve** is not merged into a wrong node.

---

## 6. Landmines (historical / ingest)

- **Episode 5** often had **Lori Frontfay** in captions — treat like **Frantzve**-class noise; canonical node remains **Lori Frantzve**.
- Fuzzy ingest previously merged **Kent** into garbage labels like **Kent Bronze** — re-ingest with **`--no-fuzzy-match`** after corrections.
