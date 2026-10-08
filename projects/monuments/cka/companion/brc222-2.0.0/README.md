# CKA BRC-222 companion package (staged)

**Status:** staged for Transit review. Not deployed.

| Field | Value |
|-------|-------|
| vocabulary | 2.0.0 (2026-10-07) |
| vocab source | https://brc222.org/vocabulary.json |
| generated_at (UTC) | 2026-10-07T16:26:36Z |
| bridges | 8977 |
| revises candidate rows | 16 (both terms per edge) |
| revises heuristic primary | {'extends': 8} |

## Edge counts (emitted relationship names from vocab)

```
{
  "contradicts": 18,
  "isCorroboratedBy": 8,
  "isMemberOf": 6209,
  "isSupportedBy": 2742
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

For each ledger `Revises:` edge the builder emits **both** candidate terms for Transit review
(package bridges with `review_status: pending_transit`, plus CSV rows).

Primary pick rule:
1. Score QUALIFY_CUES vs EXTEND_CUES in claim label+body.
2. Higher qualify score -> softening term as primary.
3. Higher extend score -> builds-on term as primary.
4. Tie / no cues -> default builds-on term at low confidence.

Latent rows (`source=supports_latent`) come from every `Supports:` edge that lacks a
minted `Revises:` line. Cue hits raise confidence; otherwise primary defaults to the
builds-on term at low confidence. Those rows do **not** change the firm corroboration
bridge; they are CSV-only hints because the live CKA tip still has few minted `Revises:` lines.

Transit confirms the final term per edge before any deploy.
