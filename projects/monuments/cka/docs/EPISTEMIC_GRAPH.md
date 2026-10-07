# CKA epistemic graph (Phase A + B + C)

**Status:** Draft syntax + preflight + schema (Phase A), modern-draft typed-edge backfill (Phase B), and Neo4j ingest mapping (Phase C) are implemented. Staging smoke harness is ready; run against bolt://127.0.0.1:27687 only. No prod write, no inscription pack, no BoC promo from this track.

**Principle (Daveed lock 2026-10-06):** Preserve disagreement better than conclusions. A claim is a temporal object: what was aired, at which stamp, with which artifacts. Never mutate or delete a minted claim. Monument = memory in motion.

## Claim immutability

Once a `C-*` is minted with a label + body, it is frozen. No in-place edits to meaning, no relabel, no delete, no "update the claim to the new theory."

| Situation | Mint | Edges | Never |
|-----------|------|-------|-------|
| Host states proposition P at stamp T | New C-* | Episode asserts; anchors; Mentions people | Reuse an old C-id for a new wording |
| Host later softens / corrects / replaces P | New C-* | `Revises:` prior; `Qualifies:` if she narrows | Edit prior C-*; collapse into one "current" claim |
| Host explicitly rejects prior P or a rival's Q | New C-* | `Contradicts:` prior/rival; add `Revises:` only if replacing her own prior | Delete prior; pick a winner |
| Host reinforces prior P | New C-* or same-episode support line | `Supports:` prior | Silent duplicate id |
| Same C-id, different labels across episodes | **Fork = P0** | Remint + `Revises:` (after fix) | Treat fork as revision |

Direction is always **newer** `-[:REVISES]->` **older**. Both `Revises:` and `Contradicts:` may appear on the same newer claim.

## Draft claim block (target shape)

```text
**C-36xx** Short immutable label

Claim Timestamp: HH:MM:SS
Claim: …
Anchored Artifacts: A-….1
Mentions: N-16, N-424
Revises: C-30xx
Contradicts: C-30xx
Supports: C-30yy
Qualifies: C-30zz
Related Nodes: N-….   # non-person leftovers until further typing
Investigative Direction: …
```

## Draft lines → parser fields → Neo4j edges (Phase C)

| Draft line | Parser / inscription field | Neo4j edge |
|------------|----------------------------|------------|
| Claim Register membership | claim in episode | `Episode -[:ASSERTS]-> Claim` (keeps `Claim -[:FROM_EPISODE]-> Episode` as alias) |
| `Anchored Artifacts: A-…` | `anchored_artifacts` | `Claim -[:SUPPORTED_BY]-> Artifact` (+ existing `Artifact -[:ANCHORS]-> Claim`) |
| `Revises: C-…` | `revises_claim_refs` / `revises_claims` | `Claim -[:REVISES]-> Claim` (newer → older) |
| `Contradicts: C-…` | `contradicts_claim_refs` / `contradicts_claims` | `Claim -[:CONTRADICTS]-> Claim` |
| `Supports: C-…` | `supports_claim_refs` / `supports_claims` | `Claim -[:SUPPORTS]-> Claim` |
| `Qualifies: C-…` | `qualifies_claim_refs` / `qualifies_claims` | `Claim -[:QUALIFIES]-> Claim` |
| `Mentions: N-…` | `mentions_person_refs` / `mentions_persons` | `Claim -[:MENTIONS]-> Person` (distinct from `MENTIONS_TOPIC`) |
| `Connected: N-…` | `connected_org_refs` / `connected_orgs` | `Person -[:CONNECTED_TO]-> Org` |
| `CapturedAt: N-…` | `captured_at_place_refs` / `captured_at_places` | `Artifact -[:CAPTURED_AT]-> Place` |
| Artifact in episode register | artifact row | `Artifact -[:APPEARS_IN]-> Episode` |
| Person in Node Register | node row | `Person -[:APPEARS_IN]-> Episode` (unchanged) |

`Related Nodes:` remains valid for topic/org/place leftovers until further typing.

## Extractor checklist (CKA)

1. **Never reuse a C-id** for a new wording or walk-back. Mint fresh; wire `Revises:` (and `Contradicts:` if explicit oppose).
2. Prefer `Mentions:` for person N-* on claims; leave non-person ids on `Related Nodes:`.
3. Use `Supports:` / `Qualifies:` when the host reinforces or narrows a prior claim without replacing it.
4. On Person register rows, prefer `Connected: N-####` (org) over inventing links from name co-mention alone.
5. On artifact sub-items, add `CapturedAt: N-####` only when the clip/document has a concrete place locus.
6. Preflight `claim_fork` (P0) fails if the same C-id carries different labels or materially different `Claim:` bodies across episodes. Fix by remint + typed edges, not by editing the old id.

## Phase B backfill (implemented)

On modern CKA drafts (`projects/monuments/cka/drafts/episode_*.md`) and matching inscription claim JSON:

1. **Mentions split:** person-band `N-1..N-999` moved from claim `Related Nodes:` onto `Mentions:`; topic/org/place leftovers stay on `Related Nodes:` (empty Related lines removed).
2. **Contradicts backfill:** high-confidence explicit-oppose pairs wired (plus pre-existing Contradicts kept). Full-corpus judgment deferred where opposition is narrative-only or lacks a rival C-id.
3. **Revises:** PR 51 fork remints `C-3630/3631/3632` vs `C-1123/1124/1285` are **different propositions that collided on id only**, so no `Revises:` edge. True host walk-back remints with `Revises:` remain deferred pending clearer same-lineage pairs.
4. **Locks honored:** no Neo4j write, no pack, no BoC promo. Mark Herman stays `N-98` only (no retired `N-237/407/527`).

## Phase C Neo4j ingest mapping (implemented)

Shared ingest: `projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py`.

```bash
# Prefer staging. Prod 17687 writes are refused by default.
NEO4J_URI=bolt://127.0.0.1:27687 \
  python3 projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --monument cka
```

Unit / planner tests:

```bash
python3 projects/monuments/bride_of_charlie/scripts/test_neo4j_ingest_parse.py
```

## Staging smoke (§5 query pack)

See `docs/EPISTEMIC_GRAPH_STAGING_SMOKE.md`.

```bash
NEO4J_URI=bolt://127.0.0.1:27687 \
  python3 projects/monuments/scripts/epistemic_graph_smoke.py
```

Defaults to staging **27687**. Refuses prod **17687**. Does not start docker / openclaw-neo4j / bare 7687.

## Preflight

```bash
python3 projects/monuments/scripts/dia_preflight.py --monument cka
```

See `projects/monuments/DIA_PREFLIGHT.md` check `claim_fork`.

## Out of scope (remaining)

- Inscription pack promote / prod Neo4j write
- BoC promo (BoC is syntax/ingest reference only)
- Exhaustive corpus-wide `Revises:` / `Supports:` / `Qualifies:` / `Connected:` / `CapturedAt:` judgment
