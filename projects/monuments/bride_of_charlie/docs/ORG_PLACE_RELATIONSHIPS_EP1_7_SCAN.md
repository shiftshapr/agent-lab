# Episodes 1–7 scan: organizations, places, relationship patterns

**Source:** `inscription/episode_001.json` … `episode_007.json` (current exports).  
**Method:** Structured node types + regex over concatenated `claim` / `label` / `transcript_snippet` fields (heuristic, not exhaustive NER).

---

## 1. What the graph actually has today

| Category | In JSON today | Ep 1–7 reality |
|----------|----------------|----------------|
| **People** | `Person` nodes | Strong: Erika, Lori, Kent, Charlie, Tyler Bowyer, Jerry Frantzve, etc. |
| **Themes / discrepancies** | `InvestigationTarget` | Strong: DOB discrepancy, marriage dates, Tesaract narrative, missing TP money, etc. |
| **`type: institution`** | `InvestigationTarget` in Phase 2 with `institution` subtype | **Almost unused:** only **Arizona State University** (ep7) appears as a dedicated institution node. |
| **Places** | No `Place` type | **Not modeled as nodes.** Cities, schools-as-venues, countries appear inside **claims** and **descriptions** only. |
| **Turning Point USA / Action** | Prose + artifacts + some **InvestigationTarget** rows (e.g. “Missing Money from Turning Point USA”) | **Not** a stable, filterable **Organization** node with subtype; hard to query “all claims involving TPUSA” via graph shape. |
| **Schools / companies** | Tesaract, Walnut Corner, American Bank Note, DuPont, Radford, Proclaim LLC, Super Feed, etc. | Almost entirely **claim text** or **person descriptions**, not typed org entities. |

**Conclusion:** Your instinct is right: to **filter nonprofits vs businesses vs agencies**, you need **first-class organization nodes** with a **subtype** (and probably **Place** nodes). The brief already asks for institutions; the model mostly folds them into **themes** or **narrative** instead of **repeatable entities**.

---

## 2. Recommended organization model (filterable)

Use a dedicated **`Organization`** JSON-LD `@type` (or keep `InvestigationTarget` only for *non-entity* themes and move real orgs out).

**`organization_kind`** (enum — pick one vocabulary and stick to it):

| Value | Examples in ep 1–7 (illustrative) |
|--------|-----------------------------------|
| **`business`** | Turning Point USA, Turning Point Action, Proclaim (LLC), Super Feed Technologies, Advanced Patent Technology, United Coin, American Bank Note Company, IMAT Laboratories (as vendor), slot / casino businesses |
| **`nonprofit`** | (Treat **501(c)(x)** and “foundation” language here when evidence supports nonprofit status; many TP entities may be **business** or hybrid—use `uncertainty_note`) |
| **`government_agency`** | Department of Homeland Security (House bill / IMAT line), military intelligence (ep5 principal’s family), court systems (implicit via filings—not always a named “agency” node) |
| **`educational_institution`** | Tesseract School, Walnut Corner Children’s Center, Arizona State University, Radford University, Cocopah (school context ep6) |
| **`political_or_advocacy`** | Turning Point USA / Action (if you split **business** vs **advocacy** for filtering—otherwise tag **secondary_tag**: `political_organization`) |
| **`media_or_platform`** | X/Twitter, podcast venues (only if you need graph queries on them) |
| **`religious_or_charitable_venue`** | Zion’s Gate (Jerusalem dedication thread), churches if named substantively |

**Optional second axis:** `sector` (e.g. `gambling`, `defense`, `education`, `health`) for cross-cutting filters.

---

## 3. Places to capture (“get all places”)

From claim/snippet language across ep 1–7, place-like references cluster as:

| `place_kind` | Examples |
|--------------|----------|
| **`city`** | Cincinnati, Phoenix, Paradise Valley, Scottsdale, Tempe, Las Vegas, North Kingstown, Chicago (if cited), Rome (Nevada–Rome link ep6) |
| **`region_state`** | Arizona, Ohio, Illinois, Rhode Island, Massachusetts, California, Texas, Florida, Nevada, New Hampshire, Utah (genealogy thread in show—not always in ep1–7 JSON) |
| **`country`** | USA, Sweden, Romania, China (as claimed travel/context), Israel/Jerusalem (Zion’s Gate) |
| **`venue_site`** | Good Samaritan Hospital, Walnut Corner Children’s Center, Tesseract School, ASU campus, Universal Studios (visit ep4) |
| **`address_or_jurisdiction`** | When a **filing** gives a county/court; keep as **Place** + link to **Artifact** |

**Policy:** Create a **Place** node when the location is **material to a claim** (birth, enrollment, fraud jurisdiction, travel, office opening) or **recurs** across episodes (Paradise Valley, ASU, TP “Arizona jobs”).

---

## 4. Relationship patterns worth formalizing (from ep 1–7 text)

Heuristic counts = number of **claims** whose combined text matched a pattern **at least once** (fields: `claim`, `label`, `transcript_snippet`, `investigative_direction`). Re-run: `scripts/scan_episode_relationship_patterns.py` (snapshot below from current inscription).

| Bucket | Hits (ep 1–7) | Useful typed edges (proposal) |
|--------|----------------|------------------------------|
| **Temporal** | 29 | `effective_during`, `occurred_on`, `precedes` / `overlaps` (often stay as **claim** metadata unless you need graph path queries) |
| **Education** | 19 | `enrolled_at`, `attended`, `graduated_from` (Place or Organization) |
| **Legal / government** | 18 | `filed_in`, `subject_of_investigation`, `received_funding_from` (org→agency) |
| **Work / org** | 14 | `employed_by`, `works_for`, `founded`, `board_member_of`, `introduced` (person→person or person→org), `CEO_of`, `COO_of` (role edges or role nodes) |
| **Kinship** | 13 | `parent_of` / `child_of`, `spouse_of`, `stepparent_of`, `grandparent_of`, `sibling_of`, `cousin_of` (directed; **anchor to artifact**) |
| **Attribution** | 9 | `stated_by`, `alleged_by` (claim-level; may stay on **Claim** only) |
| **Financial / record** | 8 | `owns`, `beneficiary_of`, `paid_by`, `defrauded` (high sensitivity—keep as **claims** with strict artifacts) |
| **Travel / citizenship** | 3 | `traveled_to`, `resided_in`, `citizenship_process` (person→country/place) |

**High-value concrete phrases found in data (examples):**

- **Introduction / employment:** “Tyler Bowyer … introduced Charlie to Erika”; “most important relationship … at Turning Point USA”; Erika **CEO** of TPUSA (person descriptions ep7).  
- **Board / control:** Lori on board of **Super Feed** with **Tyler Bowyer** (TP Action COO).  
- **Education:** Tesseract, Walnut Corner, **ASU**, Radford, Jerry Frantzve “gender clinic” context.  
- **Kinship + work:** Carl Kenneth Frantzve executive at **American Bank Note**; Jack Solomon / **slot machine** businesses; **Erpenbeck** fraud / **banks**.  
- **Places + claims:** Birth **Good Samaritan**; daycare **Cincinnati**; school **Paradise Valley**; **Las Vegas** office; **Romania** travel ep6.

These are exactly the edges you described: **child_of** (Erika↔Lori/Kent), **CEO_of / works_for** (Erika↔TPUSA), **lives_in / resided_in** when sourced.

---

## 5. Where to implement (order of work)

1. **`brief/monument_zero_briefing.md` + `templates/bride_charlie_entity_extraction.md`** — Require **Organization** + **Place** nodes with **`organization_kind` / `place_kind`** when substantively discussed; require **relationship** rows or **dual-node claims** with a **`relationship_hint`** until edges are first-class.  
2. **`templates/entity_schema.json`** — **Done (workflow upgrade):** `Topic`, `Organization`, `Place` (+ legacy `InvestigationTarget`); optional `topic_kind`, `organization_kind`, `place_kind`. Phase 1 validation follows the schema.
3. **Pipeline (`assign_ids` + `neo4j_ingest`):** **Done** — drafts include `Node Type:` / `* Kind:` lines; ingest creates `:Topic`, `:Organization`, `:Place` (and legacy `:InvestigationTarget` when markdown has no type line). Re-run assign_ids + ingest after changing types.
4. **`assign_ids.py` / `node_claim_sync` / `export_for_inscription.py`** — Further work only if new ID bands or sync rules are needed (current N-1000+ band shared across topic/org/place).
5. **`neo4j_ingest.py` (future)** — Typed edges (`WORKS_FOR`, `CHILD_OF`, `LOCATED_IN`, etc.) or `RELATES {predicate}` — still out of scope for this pass.
6. **Hub / filters** — UI filter by label and `organization_kind` / `place_kind` / `topic_kind`.

---

## 6. Optional: regenerate this scan

Re-run the heuristic after re-exporting inscription:

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
python3 scripts/scan_episode_relationship_patterns.py
python3 scripts/scan_episode_relationship_patterns.py --episodes 1-3
```

---

## Revision

| Date | Notes |
|------|--------|
| 2026-04-06 | Initial scan from `inscription` ep1–7; recommends org subtypes, place kinds, relationship buckets. |
