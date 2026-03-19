# Pre-Run Checklist — Before Re-Running Episodes 1-7

Before re-running the episode analysis with Neo4j enhancements, complete these steps to ensure clean, protocol-compliant output.

---

## 1. Backup Existing Drafts ✓

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie

# Backup current drafts
mv drafts drafts_backup_$(date +%Y%m%d)

# Create fresh drafts directory
mkdir drafts
```

**Why:** Existing drafts use table format for nodes. Keep them for reference.

---

## 2. Verify Template Format ✓

**Status:** FIXED

The template now uses the correct structured format for Node Register (not tables).

**File:** `templates/bride_charlie_episode_analysis.md`

**Before:**
```markdown
| ID | Entity / Target | Evidence Count | Claim Count |
|----|------------------|----------------|-------------|
| N-X | [name] | [count] | [count] |
```

**After:**
```markdown
**N-X** [Person Name]

[Short descriptive line explaining why this node matters.]

Evidence Count: [count]
Claim Count: [count]
```

---

## 3. Check Protocol File

Verify the protocol file is correct:

```bash
cat brief/monument_zero_briefing.md | grep -A 10 "## Node format"
```

**Expected output:**
```
**N-2** Erica Kirk

Short descriptive line explaining why this node matters.

Evidence Count: 0
Claim Count: 0
Episode Count: 0
```

**Status:** Already correct (checked earlier).

---

## 4. Verify Environment Variables

```bash
# Check .env file
cat .env | grep -E "MODEL_NAME|OPENAI_BASE_URL|NEO4J"
```

**Required:**
```bash
# LLM (choose one)
OPENAI_BASE_URL=http://localhost:11434/v1
MODEL_NAME=qwen2.5:7b

# OR
MINIMAX_API_KEY=your_key_here
MINIMAX_MODEL=MiniMax-M2.5

# Neo4j (optional but recommended)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw
NEO4J_AUTO_INGEST=true
```

**Action:** Add Neo4j vars to `.env` if not present.

---

## 5. Test LLM Connection

```bash
# If using Ollama
curl http://localhost:11434/api/tags

# If using MiniMax
# (check API key is valid)
```

**Why:** Ensure the LLM is running before starting a 7-episode run.

---

## 6. Clear Neo4j Graph

```bash
cd ~/workspace/agent-lab

# Clear existing graph
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --force

# Or manually via Cypher
# Open http://localhost:7474
# Run: MATCH (n) DETACH DELETE n
```

**Why:** Start with a clean graph so fuzzy matching works correctly from episode 1.

---

## 7. Verify Transcripts Are Present

```bash
ls -1 projects/monuments/bride_of_charlie/transcripts/
```

**Expected:** 7 transcript files (episode_001 through episode_007).

**If missing:**
```bash
python projects/monuments/bride_of_charlie/scripts/fetch_transcripts.py
```

---

## 8. Review Protocol Emphasis Points

Add these to the system prompt or protocol file to reinforce correct formatting:

### Critical Reminders for LLM

**Node Register Format:**
```
CRITICAL: Node Register MUST use structured format, NOT tables.

CORRECT:
**N-2** Erica Kirk

Primary biographical subject of the episode's evidentiary claims.

Evidence Count: 2
Claim Count: 2
Episode Count: 1

*Related: C-1009, C-1010, A-1004.1*

INCORRECT:
| N-2 | Erica Kirk | 2 | 2 |
```

**Artifact Family Rule:**
```
CRITICAL: Create NEW top-level artifact ID whenever evidentiary source changes.

CORRECT:
A-1000 Court Filing Bundle
A-1000.1 Separation Agreement (1995)
A-1000.2 Separation Agreement (1996)

A-1001 Instagram Story Bundle
A-1001.1 Erica at Universal Studios

INCORRECT:
A-1000 Episode Bundle
A-1000.1 divorce filing
A-1000.2 Instagram story  ← WRONG: different source
```

---

## 9. Consider Model Selection

### Option A: Qwen 2.5 7B (Local via Ollama)
- **Pros:** Free, fast, good quality
- **Cons:** May need prompt tuning for strict format compliance
- **Best for:** Development, iteration

### Option B: MiniMax M2.5 (Cloud)
- **Pros:** Faster, better instruction following
- **Cons:** Costs money, requires API key
- **Best for:** Production runs

### Option C: Larger Model (if available)
- Qwen 2.5 14B or 32B
- Better format compliance
- Slower but more accurate

**Recommendation:** Start with Qwen 7B for episode 1, check output quality, then decide.

---

## 10. Set Up Monitoring

### Terminal 1: Episode Analysis
```bash
cd ~/workspace/agent-lab
python projects/monuments/bride_of_charlie/scripts/run_workflow.py episodes --force
```

### Terminal 2: Watch Logs
```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
tail -f logs/run_*.log
```

### Terminal 3: Monitor Neo4j (optional)
```bash
# Open Neo4j Browser
open http://localhost:7474

# Watch node count grow
# Run every 30 seconds:
MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count
```

---

## 11. Prepare for Validation

After each episode completes, run quick validation:

```bash
# Check if nodes were created (not tables)
grep -E "^\*\*N-[0-9]+" drafts/episode_001_*.md | head -5

# Expected: **N-1** Name
# Not expected: | N-1 | Name |
```

If tables appear, **STOP** and fix the template/prompt before continuing.

---

## 12. Plan for Interruptions

The full run might take 1-3 hours depending on LLM speed.

**If interrupted:**
```bash
# Resume from where it stopped
python projects/monuments/bride_of_charlie/scripts/run_workflow.py episodes

# It will skip already-completed episodes
```

**If output is wrong:**
```bash
# Delete bad episodes
rm drafts/episode_00X_*.md

# Re-run (will regenerate missing episodes)
python projects/monuments/bride_of_charlie/scripts/run_workflow.py episodes
```

---

## 13. Post-Run Validation Sequence

After all 7 episodes complete:

```bash
cd ~/workspace/agent-lab

# 1. Verify numbering
python projects/monuments/bride_of_charlie/scripts/verify_drafts.py

# 2. Ingest to Neo4j with fuzzy matching
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --force

# 3. Validate graph integrity
python projects/monuments/bride_of_charlie/scripts/neo4j_validate.py

# 4. Merge any duplicates
python projects/monuments/bride_of_charlie/scripts/neo4j_merge.py --auto

# 5. Final validation
python projects/monuments/bride_of_charlie/scripts/neo4j_validate.py
```

**Expected result:** `ALL CHECKS PASSED ✓`

---

## 14. Quality Spot-Checks

After episode 1 completes, manually verify:

### Node Register Format
```bash
sed -n '/^## 4. Node Register/,/^## 5. Claim Register/p' drafts/episode_001_*.md | head -30
```

**Look for:**
- `**N-1** Name` (correct)
- NOT `| N-1 | Name |` (incorrect)

### Artifact Families
```bash
grep -E "^\*\*A-[0-9]+\*\*" drafts/episode_001_*.md
```

**Check:**
- Each family is a distinct evidentiary source
- No "Episode Bundle" or mixed-source families

### Claims Have Anchors
```bash
grep -A 5 "^\*\*C-" drafts/episode_001_*.md | grep "Anchored Artifacts"
```

**Verify:**
- Every claim has `Anchored Artifacts:` line
- At least one artifact listed

---

## 15. Rollback Plan

If the run produces bad output:

```bash
# 1. Stop the run (Ctrl+C)

# 2. Restore backup
rm -rf drafts
mv drafts_backup_YYYYMMDD drafts

# 3. Fix template/protocol

# 4. Clear Neo4j
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --force

# 5. Try again with episode 1 only
# (test before running all 7)
```

---

## Quick Start Checklist

Run these commands in order:

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie

# ✓ 1. Backup
mv drafts drafts_backup_$(date +%Y%m%d) && mkdir drafts

# ✓ 2. Verify template (already fixed)
grep -A 5 "## 4. Node Register" templates/bride_charlie_episode_analysis.md

# ✓ 3. Check .env
cat ../../.env | grep -E "MODEL_NAME|NEO4J"

# ✓ 4. Clear Neo4j
python scripts/neo4j_ingest.py --force

# ✓ 5. Verify transcripts
ls -1 transcripts/ | wc -l  # Should be 7

# ✓ 6. Test episode 1 first
cd ~/workspace/agent-lab
EPISODE_ANALYSIS_PROJECT=bride_of_charlie \
EPISODE_ANALYSIS_INPUT=transcripts \
EPISODE_ANALYSIS_OUTPUT=drafts \
python protocols/episode_analysis/episode_analysis_protocol.py

# ✓ 7. Check episode 1 output
grep -E "^\*\*N-[0-9]+" projects/monuments/bride_of_charlie/drafts/episode_001_*.md | head -3

# ✓ 8. If good, run all 7
python projects/monuments/bride_of_charlie/scripts/run_workflow.py episodes --force
```

---

## Summary

**Before running:**
1. ✓ Backup existing drafts
2. ✓ Fix template (DONE)
3. ✓ Check environment variables
4. ✓ Clear Neo4j graph
5. ✓ Verify transcripts exist
6. ✓ Test LLM connection
7. ✓ Test episode 1 first
8. ✓ Monitor output quality

**After running:**
1. Verify numbering
2. Ingest to Neo4j
3. Validate integrity
4. Merge duplicates
5. Final validation

**Expected outcome:**
- 7 clean episode drafts in correct format
- All nodes in structured format (not tables)
- Neo4j validation passes
- Ready for human review and approval

---

## Ready to Run?

Once you've completed the checklist, start with:

```bash
cd ~/workspace/agent-lab
python projects/monuments/bride_of_charlie/scripts/run_workflow.py episodes --force
```

Monitor the first episode closely. If it looks good, let it continue through all 7.
