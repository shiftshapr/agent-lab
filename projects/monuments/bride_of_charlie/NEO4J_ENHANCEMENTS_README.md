# Neo4j Workflow Enhancements — Implementation Complete

## What Was Added

Three major enhancements to make Neo4j the "investigative memory" for the OpenClaw workflow:

1. **Name Standardization** — Fuzzy matching, canonical names, aliases
2. **Verification Caching** — Store name verification results in Neo4j
3. **Node Merge Tool** — Interactive tool to merge duplicate nodes

---

## 1. Name Standardization (`neo4j_ingest.py`)

### What It Does

- **Fuzzy name matching** during ingest using Levenshtein distance
- **Automatic node merging** when similar names are detected
- **Alias tracking** — stores alternate spellings
- **Canonical names** — one authoritative name per entity

### How It Works

When ingesting episodes, the script:
1. Checks if a similar node already exists (distance ≤ 3)
2. If found, merges into existing node and adds name as alias
3. If not found, creates new node with `canonical_name` and empty `aliases`

### Usage

```bash
# Enable fuzzy matching (default)
python scripts/neo4j_ingest.py

# Disable fuzzy matching (exact matches only)
python scripts/neo4j_ingest.py --no-fuzzy-match

# Clear and re-ingest with fuzzy matching
python scripts/neo4j_ingest.py --force
```

### Example Output

```
[neo4j-ingest] Fuzzy name matching: ENABLED
[neo4j-ingest] Ingesting 7 episode(s)...
  [1/7] episode_001_episode_001_ZAsV0fHGBiM.md
       OK (Episode 1)
  [2/7] episode_002_episode_002_1IY2oD-_xVA.md
       OK (Episode 2)
  → Merged 'Erica France Kirk' (N-8) into 'Erica Kirk' (N-2) [distance: 2]
  → Merged 'Tyler Boyer' (N-15) into 'Tyler Bowyer' (N-12) [distance: 1]
```

### Graph Properties

Nodes now have:
- `canonical_name` — authoritative spelling
- `aliases` — list of alternate spellings

```cypher
// Query a person by any name variant
MATCH (p:Person)
WHERE p.canonical_name = "Erica Kirk" 
   OR "Erica France Kirk" IN p.aliases
RETURN p
```

---

## 2. Verification Caching (`verify_drafts.py`)

### What It Does

- **Caches verification results** in Neo4j (no re-searching)
- **Stores metadata**: source, date, confidence level
- **Cache expiration**: 30-day default
- **Automatic cache updates** when names are verified

### How It Works

When verifying names:
1. Check Neo4j cache first
2. If cached and < 30 days old, use cached result
3. If not cached, search DuckDuckGo
4. Store result in Neo4j for future use

### Usage

```bash
# With Neo4j caching (default if NEO4J_URI is set)
python scripts/verify_drafts.py

# Disable cache (always search)
python scripts/verify_drafts.py --no-cache

# Skip search entirely (numbering audit only)
python scripts/verify_drafts.py --skip-search
```

### Example Output

```
--- Name Verification ---
  Found 12 person(s) in Node Register
  Neo4j cache: ENABLED
  Cache: 8 hits, 4 misses
  OK: Charlie Kirk [cached]
  OK: Erica Kirk [cached]
  CHECK: "Tyler Boyer" → possible correct spelling: "Tyler Bowyer"
  OK: Jerry France [cached]
```

### Graph Properties

Nodes now have:
- `verified_spelling` — verified correct spelling
- `verification_source` — where it was verified (e.g., "DuckDuckGo search")
- `verification_date` — when it was verified
- `verification_confidence` — high/medium/low

```cypher
// Find names that need verification
MATCH (p:Person)
WHERE p.verified_spelling IS NULL
RETURN p.id, p.canonical_name

// Show verification metadata
MATCH (p:Person {id: "N-2"})
RETURN p.canonical_name, 
       p.verified_spelling,
       p.verification_source,
       p.verification_date
```

---

## 3. Node Merge Tool (`neo4j_merge.py`)

### What It Does

- **Finds potential duplicates** using fuzzy matching
- **Interactive merging** with user prompts
- **Auto-merge mode** for batch operations
- **Dry-run mode** to preview changes
- **Relationship transfer** — all edges moved to merged node
- **Alias preservation** — merged name added as alias

### How It Works

1. Scans all Person and InvestigationTarget nodes
2. Finds pairs with Levenshtein distance ≤ threshold
3. Prompts user to merge or skip (or auto-merges)
4. Transfers all relationships to kept node
5. Adds merged node's name as alias
6. Deletes merged node

### Usage

```bash
# Interactive mode (prompts for each duplicate)
python scripts/neo4j_merge.py

# Auto-merge mode (keep lower ID)
python scripts/neo4j_merge.py --auto

# Dry-run (show what would happen)
python scripts/neo4j_merge.py --dry-run

# Custom threshold
python scripts/neo4j_merge.py --threshold 2

# Specific node type
python scripts/neo4j_merge.py --node-type Person
```

### Example Output (Interactive)

```
[neo4j-merge] Scanning Person nodes (threshold: 3)...
  Found 2 potential duplicate(s)

[1/2] Potential duplicate (distance: 1):
  1. N-12: Tyler Bowyer
  2. N-15: Tyler Boyer

  Merge? [1→2 / 2→1 / skip / quit]: 2→1
  ✓ Merged N-15 into N-12

[2/2] Potential duplicate (distance: 2):
  1. N-2: Erica Kirk
  2. N-8: Erica France Kirk

  Merge? [1→2 / 2→1 / skip / quit]: 2→1
  ✓ Merged N-8 into N-2

[neo4j-merge] Complete. Merged: 2, Skipped: 0
```

### Example Output (Auto)

```
[neo4j-merge] Scanning Person nodes (threshold: 3)...
  Found 2 potential duplicate(s)
  ✓ Merged N-15 (Tyler Boyer) into N-12 (Tyler Bowyer)
  ✓ Merged N-8 (Erica France Kirk) into N-2 (Erica Kirk)

[neo4j-merge] Auto-merged 2 node(s)
```

---

## Workflow Integration

### Before (Without Enhancements)

```bash
# Ingest episodes
python scripts/neo4j_ingest.py

# Validate
python scripts/neo4j_validate.py

# Verify names (searches every time)
python scripts/verify_drafts.py
```

**Problems:**
- Duplicate nodes created for similar names
- Name verification searches DuckDuckGo every time
- No way to merge duplicates
- No alias tracking

### After (With Enhancements)

```bash
# Ingest with fuzzy matching (auto-merges similar names)
python scripts/neo4j_ingest.py --force

# Validate
python scripts/neo4j_validate.py

# Verify names (uses cache)
python scripts/verify_drafts.py

# Merge any remaining duplicates
python scripts/neo4j_merge.py --auto
```

**Benefits:**
- Fewer duplicate nodes (fuzzy matching during ingest)
- Faster verification (cached results)
- Easy duplicate cleanup (merge tool)
- Alias tracking for name variants

---

## Configuration

### Environment Variables

```bash
# .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw
```

### Fuzzy Matching Threshold

Default: 3 (Levenshtein distance)

- **0** = exact match only
- **1** = 1 character different (e.g., "Boyer" vs "Bowyer")
- **2** = 2 characters different
- **3** = 3 characters different (default, catches most typos)
- **4+** = very loose (may merge unrelated names)

### Cache Expiration

Default: 30 days

To change, modify `check_verification_cache()` in `verify_drafts.py`:

```python
def check_verification_cache(session, name: str, cache_days: int = 30):
```

---

## Cypher Queries

### Find All Aliases

```cypher
MATCH (p:Person)
WHERE size(p.aliases) > 0
RETURN p.id, p.canonical_name, p.aliases
ORDER BY p.id
```

### Find Unverified Names

```cypher
MATCH (p:Person)
WHERE p.verified_spelling IS NULL
RETURN p.id, p.canonical_name
ORDER BY p.id
```

### Show Verification History

```cypher
MATCH (p:Person)
WHERE p.verification_date IS NOT NULL
RETURN p.canonical_name,
       p.verified_spelling,
       p.verification_source,
       p.verification_date,
       p.verification_confidence
ORDER BY p.verification_date DESC
```

### Find Potential Duplicates (Manual)

```cypher
MATCH (p1:Person), (p2:Person)
WHERE p1.id < p2.id
  AND apoc.text.levenshteinDistance(p1.canonical_name, p2.canonical_name) <= 3
RETURN p1.id, p1.canonical_name,
       p2.id, p2.canonical_name,
       apoc.text.levenshteinDistance(p1.canonical_name, p2.canonical_name) AS distance
ORDER BY distance
```

---

## Testing

### Test Name Standardization

```bash
# Clear graph
python scripts/neo4j_ingest.py --force

# Check merge log
# Should show: "Merged 'X' into 'Y'"
```

### Test Verification Caching

```bash
# First run (cache misses)
python scripts/verify_drafts.py
# Output: "Cache: 0 hits, 12 misses"

# Second run (cache hits)
python scripts/verify_drafts.py
# Output: "Cache: 12 hits, 0 misses"
```

### Test Merge Tool

```bash
# Dry run
python scripts/neo4j_merge.py --dry-run
# Shows what would be merged

# Interactive
python scripts/neo4j_merge.py
# Prompts for each duplicate

# Auto
python scripts/neo4j_merge.py --auto
# Merges all automatically
```

---

## Troubleshooting

### "APOC procedure not found"

The merge tool requires APOC. It's already enabled in `docker-compose.yml`.

If you see this error:
```bash
docker compose down
docker compose up -d
```

### "No duplicates found" but you know there are duplicates

Increase the threshold:
```bash
python scripts/neo4j_merge.py --threshold 5
```

### Cache not working

Check that `NEO4J_URI` is set in `.env`:
```bash
echo $NEO4J_URI
# Should print: bolt://localhost:7687
```

### Fuzzy matching too aggressive

Disable it:
```bash
python scripts/neo4j_ingest.py --no-fuzzy-match
```

Or lower the threshold in the code (edit `neo4j_ingest.py`, change `threshold=3` to `threshold=1`).

---

## Files Modified

1. **`scripts/neo4j_ingest.py`**
   - Added `levenshtein_distance()`, `normalize_name()`, `find_similar_node()`, `add_alias_to_node()`
   - Modified `ingest_episode()` to use fuzzy matching
   - Added `--no-fuzzy-match` flag
   - Added merge logging

2. **`scripts/verify_drafts.py`**
   - Added `get_neo4j_session()`, `check_verification_cache()`, `store_verification_result()`
   - Modified `verify_names_with_search()` to use cache
   - Added `--no-cache` flag
   - Added cache hit/miss reporting

3. **`scripts/neo4j_merge.py`** (NEW)
   - Interactive duplicate merging tool
   - Auto-merge mode
   - Dry-run mode
   - Relationship transfer
   - Alias preservation

---

## Next Steps

1. **Re-ingest episodes** with fuzzy matching:
   ```bash
   python scripts/neo4j_ingest.py --force
   ```

2. **Verify names** (builds cache):
   ```bash
   python scripts/verify_drafts.py
   ```

3. **Merge any remaining duplicates**:
   ```bash
   python scripts/neo4j_merge.py --auto
   ```

4. **Validate integrity**:
   ```bash
   python scripts/neo4j_validate.py
   ```

5. **View graph**:
   Open [http://localhost:7474](http://localhost:7474)

---

## Summary

Neo4j is now more than just a ledger — it's the **investigative memory** that:

✅ **Prevents duplicates** (fuzzy matching during ingest)  
✅ **Caches verifications** (no re-searching)  
✅ **Tracks aliases** (name variants)  
✅ **Merges duplicates** (interactive tool)  
✅ **Stores metadata** (verification source, date, confidence)  

The graph gets smarter with each episode.
