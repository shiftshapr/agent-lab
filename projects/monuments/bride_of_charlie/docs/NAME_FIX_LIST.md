# Name fix list — tick these off

**Regenerate live dump anytime:**

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
uv run --project ../../../framework/deer-flow/backend python scripts/list_names_audit.py --out names_audit.md
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py list
```

**Full playbook:** [`FIX_NAMES.md`](./FIX_NAMES.md) · **Frantzve policy:** [`NAME_AUDIT_FRANTZE.md`](./NAME_AUDIT_FRANTZE.md)

**Repo note (drafts / phase1 / inscription / audit table):** canonical names below are applied in markdown + JSON. You still need **`neo4j_corrections.py add` + `apply-dir`** when you change dictionary rows, then **re-ingest**.

**Surname policy:** **`Frantzve`** = canonical on **`N-*`**, JSON, graph, and transcripts (audio-faithful; replaces bogus **“Fronfay”**). **`Frantze`** = **only** when quoting an artifact’s exact spelling — never the default person label.

---

## A. Transcript dictionary (`neo4j_corrections.py add` — left side must match **raw** transcript text)

Use these **wrong → right** pairs (not the same as draft labels if captions still say Erica/France):

- [ ] `Erica France` → `Erika Frantzve`
- [ ] `Erika France` → `Erika Frantzve`
- [ ] `Erica Kirk` → `Erika Kirk`
- [ ] `Lori France` → `Lori Frantzve`
- [ ] `Lorie France` → `Lori Frantzve`
- [ ] `Kent France` → `Kent Frantzve`
- [ ] `Lori Frontfay` → `Lori Frantzve` *(caption → audio-faithful transcript)*
- [ ] `Kent Bronzeface` → `Kent Frantzve` *(only if that exact substring is in raw — `rg` first)*
- [ ] `Tyler Boyer` → `Tyler Bowyer`
- [ ] `Dr. Jerry France` → `Dr. Jerry Frantzve`
- [ ] `Jerry France` → `Jerry Frantzve` *(where it’s the person, not “Dr. France” as title)*
- [ ] Legacy caption tokens (`Rick Urban…`, two-word surname splits) → **Erpenbeck** in `transcripts/` *(normalized in repo)*; optional `Rick Erpenbeck` → `Richard Erpenbeck` for one Person node *(ep3 notary: **Bill Erpenbeck**)*

**Remove bad dictionary rows first** (`neo4j_corrections.py remove "exact incorrect"`).

---

## B. Draft / graph fixes (applied in repo)

- [x] **Kent Bronze** → **Kent Frantzve**
- [x] **Kent (Kent Bronzeface, Kent Wasn Fay)** → **Kent Frantzve**
- [x] **Loretta Lynn Abbis** — historical **Loretta Abbis** (1940s PA), not the singer; draft blurb on N-15 *(title kept for continuity; verify records)*
- [x] **Carl Kenneth Frantzve** (N-7) — paternal grandfather; **Kent Frantzve** (N-4) is Erika's father. No **Carl Fron** (STT/LLM error). **Frantze** only when quoting an artifact verbatim.
- [x] **Dennis Frantzve** — node + transcript canonical **Frantzve**; **Frantze** only on artifact quote if seen
- [x] **Dr. Jerry France** → **Dr. Jerry Frantzve**
- [x] **Dr. Jerry Frantzve** — single register line; audio/transcript **Frantzve**; caption variants (Fay / France) under blurb
- [x] **Lori Frantzve** — single line; “Lorie” called out as caption spelling in blurb only
- [x] **Erpenbeck family** — legal spelling **Erpenbeck**; repo transcripts use **Erpenbeck** (caption-garble normalized). **Richard Erpenbeck** = one Person (uncle Rick); ep3 notary = **Bill Erpenbeck**.

---

## C. Theme / section nodes (applied in drafts)

- [x] Erica Pageant Narrative → **Erika Pageant Narrative**
- [x] Erica Timeline Discrepancies → **Erika Timeline Discrepancies**
- [x] Erica Kirk Missing Years 2000-2002 → **Erika Kirk Missing Years 2000-2002**
- [x] How Erica Met Tyler Bowyer → **How Erika Met Tyler Bowyer**
- [x] Jerry France Background Verification → **Jerry Frantzve Background Verification**
- [x] Theme nodes: **Erpenbeck fraud pattern — Lori LLCs & notaries** (`N-1021`, ep3) vs **Erpenbeck criminal connections — Erika & uncle Rick** (`N-1026`, ep4)

---

## D. After any A or B change

1. `neo4j_corrections.py apply-dir transcripts/`
2. Regen affected episodes (or full workflow)
3. `neo4j_ingest.py --force --no-fuzzy-match`

---

## E. Deduped person-ish strings (canonical after draft pass)

Andrew Kolvet · Angelina Lombardo-Abbis · Candace Owens · Carl Kenneth Frantzve · Charlie Kirk · Colonel Otto Busher · Curtis Kolvet · Dennis Frantzve · Dr. Jerry Frantzve · Dr. John Money · Elizabeth Lane · Erika Kirk · Jack Solomon · Jan Brewer · Jeffrey Epstein · Jonah · Josh Harelson · JT Massie · Kent Frantzve · Larry Ginta · Lori Abbis Stanley · Lori Frantzve · Loretta Lynn Abbis · Mason Abbis · Nancy Gerard Hall · Phil Bliss · Richard Erpenbeck · Robert Kolvet · Tyler Bowyer · Uncle Jack Solomon · Vince Lombardi

*(Institutions / themes omitted — see `NAMES_FROM_DRAFTS_AUDIT.md` §3 for the full A→Z.)*
