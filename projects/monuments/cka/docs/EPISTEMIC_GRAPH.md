# CKA epistemic graph (Phase A)

**Status:** Draft syntax + preflight + schema only. Neo4j ingest mapping is Phase C (locked). Episode draft backfill is Phase B.

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

## Draft lines → parser fields

| Draft line | Parser / inscription field | Notes |
|------------|----------------------------|-------|
| `Revises: C-…` | `revises_claim_refs` | **New.** Newer claim revises older. |
| `Contradicts: C-…` | `contradicts_claim_refs` | Port from BoC; mint when airing explicitly opposes. |
| `Supports: C-…` | `supports_claim_refs` | Port from BoC; host reinforces prior without replacing. |
| `Qualifies: C-…` | `qualifies_claim_refs` | Port from BoC; host narrows prior. |
| `Mentions: N-…` | `mentions_person_refs` | Thin typed split of Related (person band). |
| `Connected: N-…` | `connected_org_refs` | On Person node blocks; org link when known. |
| `CapturedAt: N-…` | `captured_at_place_refs` | On artifact sub-items; concrete locus only. |

`Related Nodes:` remains valid for topic/org/place leftovers until further typing. `Anchored Artifacts:` stays the evidence spine (Phase C maps to `SUPPORTED_BY`).

## Extractor checklist (CKA)

1. **Never reuse a C-id** for a new wording or walk-back. Mint fresh; wire `Revises:` (and `Contradicts:` if explicit oppose).
2. Prefer `Mentions:` for person N-* on claims; leave non-person ids on `Related Nodes:`.
3. Use `Supports:` / `Qualifies:` when the host reinforces or narrows a prior claim without replacing it.
4. On Person register rows, prefer `Connected: N-####` (org) over inventing links from name co-mention alone.
5. On artifact sub-items, add `CapturedAt: N-####` only when the clip/document has a concrete place locus.
6. Preflight `claim_fork` (P0) fails if the same C-id carries different labels or materially different `Claim:` bodies across episodes. Fix by remint + typed edges, not by editing the old id.

## Preflight

```bash
python3 projects/monuments/scripts/dia_preflight.py --monument cka
```

See `projects/monuments/DIA_PREFLIGHT.md` check `claim_fork`.

## Out of scope (this phase)

- Phase B: mass backfill of Mentions/Revises/Contradicts on existing episode drafts
- Phase C: Neo4j edge ingest (`ASSERTS`, `REVISES`, `CONNECTED_TO`, `CAPTURED_AT`, …)
- Inscription pack promote / Neo4j write
- BoC promo (BoC is syntax/ingest reference only)
