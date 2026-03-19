# Canonical Node Dictionary & Learning System

Single source of truth for node names. Logs edge cases for human review and all adjustments for learning.

---

## Overview

| File | Purpose |
|------|---------|
| `canonical/nodes.json` | Canonical node dictionary (node_id → name, confidence, aliases) |
| `canonical/edge_cases.jsonl` | Edge cases needing human review (append-only) |
| `canonical/adjustments.jsonl` | All adjustments we make (append-only, for learning) |
| `canonical/reviewed.jsonl` | Human decisions on edge cases (approve/edit/deny) |

---

## Edge Cases (for review)

Logged when the system encounters ambiguity:

- **De-dup candidate:** "Erica Smith" might be same as "Erica Kirk" — needs human confirmation
- **Low-confidence name:** Single mention, unusual spelling — web verification suggested
- **Name variation:** "Tyler Boyer" vs "Tyler Bowyer" — which is canonical?
- **Merge candidate:** Two nodes from different episodes might be same person
- **phase1_validation:** Schema or reference-integrity failures for a Phase 1 JSON (logged whenever validation reports issues; may still be saved if `EPISODE_ANALYSIS_STRICT_VALIDATION=0`)
- **extraction_review:** Batch of fields with `confidence` medium/low or a non-empty `uncertainty_note` (claims, nodes, artifacts, meme occurrences) after a successful Phase 1 save — queue for spot-check

Use `EPISODE_ANALYSIS_EXTRACTION_REVIEW=0` to disable extraction_review batching. Resolve informational items with `review --resolve ec-… deny` after you address the JSON, if the default approve/edit flow does not apply.

Each entry:
```json
{
  "id": "ec-20260318-001",
  "timestamp": "2026-03-18T12:00:00Z",
  "type": "de_dup_candidate|low_confidence|name_variation|merge_candidate",
  "episode": 2,
  "context": "Episode 2 Node Register",
  "candidates": [
    { "name": "Erica Smith", "node_id": null, "source": "episode_2" },
    { "name": "Erica Kirk", "node_id": "N-2", "source": "canonical" }
  ],
  "suggested_action": "merge|verify|add_alias|new_node",
  "status": "pending|approved|edited|denied",
  "auto_confidence": "low"
}
```

---

## Human Review Workflow

1. Run `python scripts/canonical_nodes.py review --list` — lists pending edge cases
2. For each: **approve** (accept merge/suggestion), **edit** (change canonical name), **deny** (reject)
3. Resolve: `python scripts/canonical_nodes.py review --resolve ec-20260318-001 approve`
4. Edit: `python scripts/canonical_nodes.py review --resolve ec-20260318-001 edit "Erica Kirk"`
5. Deny: `python scripts/canonical_nodes.py review --resolve ec-20260318-001 deny`
6. Decision is logged to `reviewed.jsonl`
7. Adjustment is logged to `adjustments.jsonl` (for learning)
8. Canonical dictionary is updated (approve/edit)

---

## Adjustments Log (learning)

Every change we make is logged:

```json
{
  "id": "adj-20260318-001",
  "timestamp": "2026-03-18T12:05:00Z",
  "edge_case_id": "ec-20260318-001",
  "action": "approved|edited|denied",
  "before": { "canonical_name": "Erica Smith", "node_id": null },
  "after": { "canonical_name": "Erica Kirk", "node_id": "N-2", "alias_added": "Erica Smith" },
  "human_decision": "merge into N-2; add Erica Smith as alias",
  "source": "human_review"
}
```

**Learning:** Future runs use `adjustments.jsonl` to:
- **Denials:** Pairs we've denied are skipped for de-dup suggestions (no repeated prompts)
- **Aliases:** Approved "X → Y" merges are applied automatically when we see X again
- **Patterns:** (Future) Learn from edit patterns to improve confidence heuristics

---

## Canonical Nodes Schema

```json
{
  "version": 1,
  "updated": "2026-03-18T12:00:00Z",
  "next_person_id": 10,
  "next_investigation_id": 1005,
  "nodes": {
    "N-1": {
      "canonical_name": "Charlie Kirk",
      "type": "person",
      "aliases": [],
      "confidence": "high",
      "first_seen_episode": 1,
      "episodes": [1, 2, 3],
      "corrections": [
        { "from": "Charlie Kirke", "to": "Charlie Kirk", "source": "human_review", "date": "2026-03-18" }
      ]
    }
  }
}
```
