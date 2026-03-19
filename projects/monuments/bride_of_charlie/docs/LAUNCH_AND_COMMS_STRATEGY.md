# Launch & communications strategy (internal)

**Classification:** Internal — not for public release until after inscription.  
**Purpose:** Single place for rollout order, constraints, and notes that turn conversations into agent/tooling work.

---

## Public narrative order (do not skip)

1. **Inscription first** — Monument goes on-chain (or equivalent final commitment) before public “story” begins.
2. **Gov hub** — Publish / point to the governance or canonical hub that hosts the monument and provenance.
3. **Substack** — Long-form explanation, methodology, findings (after hub is live and inscription is done).
4. **Video** — Broader reach last; can reference Substack and hub.

**Rule of thumb:** Do **not** talk publicly about the monument *before* inscription. Prevents narrative drift, commitment issues, and half-published claims.

---

## Internal records that feed agent builds

| Record | Location | What to capture |
|--------|----------|-----------------|
| **Comms / launch** | This file | Order above, timing notes, what “done” means per stage. |
| **Product & protocol decisions** | `docs/` adjacent files (e.g. `STRUCTURED_OUTPUT_AND_COLLISIONS.md`, `AUTOMATED_WORKFLOW.md`, `TAGS_AND_MEME_OCCURRENCES.md`) | Schema, validation, workflow gaps closed. |
| **Canonical learning** | `canonical/adjustments.jsonl`, `canonical/edge_cases.jsonl` | Human-reviewed merges, denials, Phase 1 validation edge cases. |
| **Conversation → build log** | Section below | Date, trigger (e.g. Cursor chat), decision, code/docs changed. |

---

## Conversation → build log (append newest at top)

<!--
Template:
### YYYY-MM-DD — <short title>
- **Context:** (chat / meeting / solo decision)
- **Decision:** …
- **Artifacts:** commit SHA, paths, PR links (no secrets)
-->

_(Start logging here as you go.)_

---

## Agent-lab note

**Repo-wide decision log** (protocols, skills, workflows, multi-monument):  
[`agent-lab/docs/AGENT_AND_MONUMENT_DECISIONS.md`](../../../../docs/AGENT_AND_MONUMENT_DECISIONS.md)

This file stays **Bride of Charlie–specific** (rollout order + monument edge cases). Cross-cutting agent builds go in the doc above; link both ways when a change touches both.
