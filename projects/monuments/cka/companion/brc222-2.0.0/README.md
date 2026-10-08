# CKA BRC-222 companion package (staged)

**Status:** staged for Transit review. Not deployed.

| Field | Value |
|-------|-------|
| vocabulary | 2.0.0 (2026-10-07) |
| vocab source | https://brc222.org/vocabulary.json |
| generated_at (UTC) | 2026-10-08T19:08:43Z |
| bridges | 9209 |
| revises candidate rows | 24 (both terms per edge) |
| revises heuristic primary | {'isQualifiedBy': 12} |

## Edge counts (emitted relationship names from vocab)

```
{
  "contradicts": 19,
  "isCorroboratedBy": 8,
  "isMemberOf": 6355,
  "isQualifiedBy": 4,
  "isSupportedBy": 2823
}
```

## Ledger -> BRC-222 map

Resolved at runtime from vendored `vocabulary.json` (never emitted as raw literals):

| Ledger | Lookup key | Vocab term |
|--------|------------|------------|
| Artifact backs claim | artifact_backs_claim | (vocab) |
| Supports / later confirms | independent_or_later_confirms | (vocab) |
| CONTRADICTS | airing_opposes | (vocab) |
| Refutes / evidence shows false | evidence_shows_false | (vocab) |
| REVISES softening / Qualifies | revises_softening | (vocab) |
| REVISES builds on | revises_builds_on | (vocab) |
| Belongs to episode / show | belongs_to_collection | (vocab) |

No `direction` field. Retired terms rejected: amplifies, contextualizes, timeline, related, isContradictedBy.

## REVISES split heuristic

For each ledger `Revises:` edge the builder emits **one** bridge. Edges whose newer claim has a
Transit ruling in `config/companion_revises_rulings.json` use the ruled term
(`review_status: transit_ruled`); other edges use the heuristic primary
(`review_status: pending_transit`). The CSV keeps both candidate terms per edge.

Primary pick rule:
1. Score QUALIFY_CUES vs EXTEND_CUES in claim label+body.
2. Higher qualify score -> softening term as primary.
3. Higher extend score -> builds-on term as primary.
4. Tie / no cues -> default softening term at low confidence (no builds-on default).

Latent rows (`source=supports_latent`) come from every `Supports:` edge that lacks a
minted `Revises:` line. Cue hits raise confidence; otherwise primary defaults to the
softening term at low confidence. Those rows do **not** change the firm corroboration
bridge; they are CSV-only hints because the live CKA tip still has few minted `Revises:` lines.

Transit confirms the final term per edge before any deploy.
