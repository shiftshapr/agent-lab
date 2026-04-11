# Ideal Workflow — Bride of Charlie

The complete end-to-end flow from raw transcripts to final investigative conclusions.

---

## Overview

```
Transcripts → Episode Analysis → Drafts → Verify → Neo4j → Cross-Episode → Reports → Review → Output
```

### Workflow diagram (`run_workflow.py` and surrounding steps)

Rough ASCII only (no Mermaid): safe to paste into slides, email, or any markdown viewer.

The scripted **`all`** step does **not** re-fetch YouTube transcripts (avoids Transcript API spend); run `fetch` when you need new captions. During episode analysis, if **`NEO4J_URI`** is set, the protocol can read **max ledger IDs** from Neo4j instead of scanning markdown. **`NEO4J_AUTO_INGEST=true`** pushes each new draft into the graph as episodes complete; otherwise run **`neo4j_ingest.py`** after drafts settle (Stage 4).

```text
  OPTIONAL                         ALREADY HAVE FILES
  ---------                        --------------------
  [ YouTube / input ]              [ transcripts/ on disk ]
         |                                    |
         v                                    |
  [ run_workflow.py fetch ] ------------------+
         |
         v
  +----------------------+
  |    transcripts/      |  (raw; never edited by name pass)
  +----------+-----------+
             |
             v
  +------------------------------+
  | neo4j_corrections.py apply-dir
  +----------+-------------------+
             |
             v
  +------------------------------+
  |  transcripts_corrected/    |  (input to episode protocol)
  +----------+-------------------+
             |
             v
  +------------------------------+
  | Episode Analysis Protocol    |
  | (protocol_agent.py)          |
  +----------+-------------------+
             |
             v
  +------------------------------+
  |  drafts/  (episode *.md)     |
  +----------+-------------------+
             |
      NEO4J_AUTO_INGEST?
        /            \
      yes             no
      |               |
      v               |
  [ neo4j_ingest ]    |
  (incremental)       |
      \               /
       \             /
        v           v
  +------------------------------+
  |      verify_drafts.py        |
  +----------+-------------------+
             |
             v
  +------------------------------+
  |  cross_episode_analysis.py   |
  +----------+-------------------+
             |
     --validate + NEO4J_URI ?
        /            \
      yes             no
      |               |
      v               v
  +--------------+   +---------------------------+
  | neo4j_       |   | Review drafts/, log in     |
  | validate.py  |   | protocol_updates/          |
  +------+-------+   +---------------------------+
         |
         v
   (same review / handoff as "no" branch)
```

After you edit drafts or need a full reload, Stage 4’s sequence still applies: **`neo4j_ingest.py --force`**, **`verify_drafts.py`**, **`neo4j_merge.py --auto`**, **`neo4j_validate.py`**, then optional **`neo4j_patterns.py`** / **`neo4j_quality.py`**.

### Neo4j graph structure (ingestion model)

Node labels and relationship types match `scripts/neo4j_ingest.py`. **`InvestigationTarget`** is a legacy label for older drafts or high-numbered nodes without an explicit `Node Type:` line. **`NameCorrection`** nodes are created by `neo4j_corrections.py` (transcript dictionary), not episode markdown; `neo4j_ingest.py --force` clears the graph but **preserves** `NameCorrection`.

Rough ASCII only (no Mermaid).

**A. Episode and evidence spine**

```text
                         CONTAINS_FAMILY
  [ Episode ] ------------------------------------> [ ArtifactFamily ]
       ^                                                     |
       | APPEARS_IN (many things tie back here)             | HAS_ARTIFACT
       |                                                     v
       |                                            [ Artifact ]
       |                                                     |
       +------------------------ APPEARS_IN -----------------+
       |                         (LegalMatter, Meme,       |
       |                          Person, Topic, ...)       |
       |                                                     |
       |              IN_LEGAL_MATTER                        |
       +----------- [ LegalMatter ] <------------------------+
       |
       |   Artifact --DERIVED_FROM / RECORDING_OF--> other Artifact
```

**B. Register entities (ledger “people / places / orgs / threads”)**

```text
  Labels (examples):
    (Person)  (Topic)  (Organization)  (Place)  (InvestigationTarget*)

  * legacy / fallback typing from markdown

  Episode --APPEARS_IN--> each entity above (and LegalMatter, Meme)
```

**C. Claims hub (how evidence and entities meet)**

```text
  [ Artifact ] --ANCHORS------------> [ Claim ] <----FROM_EPISODE---- [ Episode ]

  [ Artifact ] --INVOLVES---------> (Person | Topic | Org | Place | Inv.Target*)
  [ Claim ]    --INVOLVES---------> (same set)

  [ Claim ] --CONTRADICTS / SUPPORTS / QUALIFIES--> [ other Claim ]

  [ Claim ] --CITES_SOURCE--------> [ Artifact ]
  [ Claim ] --SUPPORTED_BY--------> [ Artifact ]   (when sensitive_topic_tags)

  [ Claim ] --MENTIONS_TOPIC------> (Topic | InvestigationTarget*)
```

**D. Organizations, roles, identity, memes**

```text
  (Organization) --OrgLink types--> (Organization)   [also Inv.Target* endpoints]

  OrgLink types (whitelist):
    SUBSIDIARY_OF, AFFILIATED_WITH, CONTRACTOR_FOR, FUNDED_BY,
    DONATED_TO, PARENT_OF, SAME_ENTERPRISE_AS

  (Person) --HOLDS_ROLE / MEMBER_OF / CHAIR_OF--> (Organization | Inv.Target*)

  (Entity) --SAME_AS-- (Entity)   [Person|Topic|Org|Place|Inv.Target pairs]

  [ Meme ] --APPEARS_IN--> [ Episode ]
  [ Claim ] --INVOKES_MEME--> [ Meme ]
  (Person) --INVOKES_MEME--> [ Meme ]
  [ Meme ] --TARGETS_NODE--> (Person | Topic | Org | Place | Inv.Target*)

  [ NameCorrection ]     <-- NOT wired by episode ingest; lives in graph for
                           transcript dictionary; survives neo4j_ingest --force
```

**E. Legal matter (parties and locus)**

```text
  (Person|Topic|Org|Place|Inv.Target) --PARTY_IN_MATTER--> [ LegalMatter ]

  [ LegalMatter ] --LOCUS_AT--> (Place | Topic | Org | Inv.Target*)
```

**Organization ↔ organization** edges use the types from markdown `OrgLink:` lines: `SUBSIDIARY_OF`, `AFFILIATED_WITH`, `CONTRACTOR_FOR`, `FUNDED_BY`, `DONATED_TO`, `PARENT_OF`, `SAME_ENTERPRISE_AS` (endpoints may be `Organization` or legacy `InvestigationTarget` where the parser allows).

**SAME_AS** links two distinct register nodes (Person, Topic, Organization, Place, or InvestigationTarget) declared equivalent in drafts. **TARGETS_NODE** on `Meme` can point to any of those register labels, not only Person.

---

## Stage 1: Prepare

**Purpose:** Clean slate, ensure prerequisites.

| Step | Command | What It Does |
|------|---------|--------------|
| 1.1 | Backup drafts | `mv drafts drafts_backup_$(date +%Y%m%d)` |
| 1.2 | Create fresh drafts | `mkdir drafts` |
| 1.3 | Start Neo4j | `docker compose up -d` |
| 1.4 | Clear Neo4j graph | `python scripts/neo4j_ingest.py --force` |
| 1.5 | Build corrected transcripts | `python scripts/neo4j_corrections.py apply-dir transcripts/ --output-dir transcripts_corrected/` |
| 1.6 | Verify raw + corrected exist | `ls transcripts/*.txt` and `ls transcripts_corrected/*.txt` (expect 7 each) |

**Output:** Clean drafts dir, empty Neo4j, `transcripts_corrected/` populated from raw `transcripts/`.

---

## Stage 2: Fetch (Optional)

**Purpose:** Get transcripts if missing.

| Step | Command | What It Does |
|------|---------|--------------|
| 2.1 | Fetch transcripts | `python scripts/run_workflow.py fetch` |

**Skip if:** Transcripts already exist in `transcripts/`.

**Output:** `transcripts/episode_001_*.txt` through `episode_007_*.txt`

---

## Stage 3: Generate Episodes

**Purpose:** Run LLM analysis on each transcript → structured draft.

| Step | Command | What It Does |
|------|---------|--------------|
| 3.1 | Run episode analysis | `python scripts/run_workflow.py episodes --force` |

**What happens:**
- Reads from `transcripts_corrected/` (raw stays in `transcripts/`)
- Writes to `drafts/`
- Uses Neo4j for ledger state (when NEO4J_URI set)
- Injects cross-episode context (recurring nodes)
- Uses fixed template (structured Node Register)
- **Collision prevention:** Stronger ledger prompts, post-processing (`fix_collisions.py`), optional two-phase mode
- Auto-ingests to Neo4j after each episode (when NEO4J_AUTO_INGEST=true)

**Output:** `drafts/episode_001_*.md` through `episode_007_*.md`

**Collision prevention options:**
- `EPISODE_ANALYSIS_TWO_PHASE=1` — Two-phase: Phase 1 extracts entities (JSON) for *all* episodes → `phase1_output/`; Phase 2 assigns IDs from a *single central ledger* across the batch → `drafts/`
- `fix_collisions.py` runs automatically after generation (in `run_full_workflow.py`)
- See `docs/STRUCTURED_OUTPUT_AND_COLLISIONS.md` for details

**Duration:** ~1-3 hours depending on LLM.

---

## Stage 4: Ingest & Verify

**Purpose:** Load drafts into Neo4j, verify numbering and names.

| Step | Command | What It Does |
|------|---------|--------------|
| 4.1 | Ingest to Neo4j | `python scripts/neo4j_ingest.py --force` |
| 4.2 | Verify drafts | `python scripts/verify_drafts.py` |
| 4.3 | Merge duplicates | `python scripts/neo4j_merge.py --auto` |
| 4.4 | Validate integrity | `python scripts/neo4j_validate.py` |

**Output:** 
- Full graph in Neo4j
- Verification report (numbering OK, name suggestions)
- Merged duplicate nodes
- Integrity report (should pass)

**Fix if needed:** Address any numbering collisions or name corrections, then re-run from 4.1.

---

## Stage 5: Cross-Episode Analysis

**Purpose:** Synthesize patterns across all episodes.

| Step | Command | What It Does |
|------|---------|--------------|
| 5.1 | Cross-episode synthesis | `python scripts/run_workflow.py cross` |
| 5.2 | Pattern detection | `python scripts/neo4j_patterns.py all --output drafts/patterns_report.md` |
| 5.3 | Quality metrics | `python scripts/neo4j_quality.py --output drafts/quality_report.md` |

**Output:**
- `drafts/cross_episode_analysis_draft.md`
- `drafts/patterns_report.md`
- `drafts/quality_report.md`

---

## Stage 6: Investigate & Report

**Purpose:** Interactive exploration, export dossiers.

| Step | Command | What It Does |
|------|---------|--------------|
| 6.1 | Interactive assistant | `python scripts/investigative_assistant.py` |
| 6.2 | Export person dossier | `python scripts/investigative_assistant.py --export person --id N-2 --output reports/erica_kirk.md` |

**Output:** 
- Interactive Q&A session
- Exported markdown dossiers for key persons

---

## Stage 7: Review & Publish

**Purpose:** Human review, approve inscriptions, publish.

| Step | Action | What It Does |
|------|---------|--------------|
| 7.1 | Review drafts | Human reviews `drafts/` |
| 7.2 | Fix issues | Correct any errors in drafts |
| 7.3 | Re-ingest if fixed | `python scripts/neo4j_ingest.py --force` |
| 7.4 | Approve inscriptions | Move approved files to `output/` |
| 7.5 | Log changes | Document in `protocol_updates/` |

**Output:** 
- `output/episode_001_*.md` through `episode_007_*.md`
- `output/cross_episode_analysis.md`
- `protocol_updates/` change log

---

## Stage 8: Final Conclusion

**Purpose:** Generate final investigative summary.

| Step | Action | What It Does |
|------|---------|--------------|
| 8.1 | Review cross-episode | Human reviews synthesis |
| 8.2 | Export key reports | Person dossiers, pattern report |
| 8.3 | Document conclusions | Final summary in `output/` |
| 8.4 | Standby | Ready for future episodes |

**Output:** Complete investigative record, ready for publication or further investigation.

---

## One-Command Run

Use the master script to run stages 1-6 automatically:

```bash
cd ~/workspace/agent-lab
./projects/monuments/bride_of_charlie/scripts/run_ideal_workflow.sh
```

Or with options:

```bash
# Skip backup (keep existing drafts)
./projects/monuments/bride_of_charlie/scripts/run_ideal_workflow.sh --no-backup

# Skip DuckDuckGo search (faster verify)
./projects/monuments/bride_of_charlie/scripts/run_ideal_workflow.sh --skip-search

# Skip transcript fetch (use existing)
./projects/monuments/bride_of_charlie/scripts/run_ideal_workflow.sh --skip-fetch

# Stop after stage 3 (inspect drafts before verify)
./projects/monuments/bride_of_charlie/scripts/run_ideal_workflow.sh --stop-after 3
```

---

## Prerequisites

- **Docker/OrbStack** — Neo4j
- **Ollama** or **MiniMax API** — LLM for episode analysis
- **Python** — uv, neo4j driver
- **.env** — NEO4J_URI, MODEL config

---

## Directory Structure After Run

```
bride_of_charlie/
├── drafts_backup_YYYYMMDD/    # Backup of previous run
├── drafts/
│   ├── episode_001_*.md       # Episode inscriptions
│   ├── episode_002_*.md
│   ├── ... (through 007)
│   ├── cross_episode_analysis_draft.md
│   ├── patterns_report.md
│   └── quality_report.md
├── inscription/                # Inscription-ready: episode_NNN.json + episode_NNN_transcript.txt
├── output/                     # Approved (after human review)
├── transcripts/                # Raw source transcripts (never modified by corrections)
├── transcripts_corrected/    # Generated: raw + NameCorrection replacements
├── canonical/                  # nodes.json, memes.json (shared across monuments)
├── logs/                       # Run logs
└── reports/                    # Exported dossiers (optional)
```

---

## Troubleshooting

**Episode analysis fails:**
- Check LLM is running (Ollama: `curl localhost:11434/api/tags`)
- Check transcripts exist in `transcripts/`
- Check .env has correct MODEL config

**Neo4j validation fails:**
- Run `neo4j_merge.py --auto` to fix duplicates
- Check drafts use structured format (not tables) for Node Register

**Import errors:**
- Run from agent-lab: `cd ~/workspace/agent-lab`
- Use: `uv run --project framework/deer-flow/backend python ...`

---

## Summary

| Stage | Key Output |
|-------|------------|
| 1. Prepare | Clean state |
| 2. Fetch | Transcripts |
| 3. Generate | Draft inscriptions |
| 4. Ingest & Verify | Validated graph |
| 5. Cross-Episode | Synthesis + patterns |
| 6. Investigate | Reports, dossiers |
| 7. Review | Approved inscriptions |
| 8. Conclusion | Final record |
