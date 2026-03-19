# Workflow Gaps — What Was Not Done or Saved (and Fixes)

Things that were **not persisted** or **not completed** in previous runs — and how they're now fixed:

---

## 1. Corrected transcripts (now fixed)

**Previously:** `verify_drafts` found name corrections but they were never imported or applied to transcripts.

**Fix applied:**
- Stage 1.3: Apply corrections to transcripts **before** clearing Neo4j
- Stage 1.4: Clear graph but **preserve** `NameCorrection` nodes
- Stage 4.2b: After verify, run `import-from-verify` and `apply-dir` so new findings are saved to transcripts for the next run

---

## 2. Name corrections wiped (now fixed)

**Previously:** `MATCH (n) DETACH DELETE n` wiped everything, including `NameCorrection`. Then `apply-dir` had nothing to apply.

**Fix applied:** Clear now excludes `NameCorrection` nodes:
```cypher
MATCH (n) WHERE NOT n:NameCorrection DETACH DELETE n
```

---

## 3. verify_drafts suggestions not fed back (now fixed)

**Previously:** No step to import verify findings into the correction dictionary or re-apply to transcripts.

**Fix applied:** Stage 4.2b runs `import-from-verify` and `apply-dir` after verify, so:
- New corrections from verify are added to `NameCorrection`
- Transcripts are updated with those corrections
- Next full run will use corrected transcripts from the start

---

## 4. Second-pass until no corrections needed (now fixed)

**Previously:** Drafts were generated once. If verify found new corrections and applied them to transcripts, those corrected transcripts were only used on the *next* run.

**Fix applied:** Stage 3 & 4 now run in a loop:
- After verify → import-from-verify → apply-dir, we count corrections applied
- If count > 0: re-run Stage 3 (generate) and Stage 4 (ingest, verify, apply)
- Repeat until 0 corrections applied or `--max-passes` (default 5) reached
- Drafts are then built from fully corrected transcripts
