# Agent & monument decisions (repo-wide)

**Purpose:** Append-only style log of **conversations, strategy, and technical choices** that drive **agent-lab** tooling — protocols, skills, workflows, and cross-monument patterns.  
**Audience:** You / team. Not public marketing copy.

---

## Related docs

| Scope | Document |
|--------|-----------|
| **Bride of Charlie — public rollout order** (inscribe → gov hub → Substack → video) | [`projects/monuments/bride_of_charlie/docs/LAUNCH_AND_COMMS_STRATEGY.md`](../projects/monuments/bride_of_charlie/docs/LAUNCH_AND_COMMS_STRATEGY.md) |
| **Episode analysis pipeline** | [`protocols/episode_analysis/`](../protocols/episode_analysis/) — `episode_analysis_protocol.py`, `phase1_validation.py` |
| **Bride automation** | [`projects/monuments/bride_of_charlie/docs/AUTOMATED_WORKFLOW.md`](../projects/monuments/bride_of_charlie/docs/AUTOMATED_WORKFLOW.md) |
| **DIA — data sat, off-chain index, resolver (Ordinals)** | [`MONUMENT_DATA_SAT_AND_RESOLVER_SPEC.md`](./MONUMENT_DATA_SAT_AND_RESOLVER_SPEC.md); JSON Schemas: [`docs/schemas/dia/`](./schemas/dia/) |
| **Deer-flow fork** | Submodule `framework/deer-flow` → [shiftshapr/deer-flow](https://github.com/shiftshapr/deer-flow); upstream [bytedance/deer-flow](https://github.com/bytedance/deer-flow) |
| **Cognitive modes & parallel git work** | Root [`AGENTS.md`](../AGENTS.md), `.cursor/rules/cognitive-modes.mdc`, [`GIT_WORKTREES_PARALLEL_AGENTS.md`](./GIT_WORKTREES_PARALLEL_AGENTS.md), [`BORIS_CHERNY_WORKFLOW_CURSOR_MAP.md`](./BORIS_CHERNY_WORKFLOW_CURSOR_MAP.md) |

Log **monument-specific launch/comms** details in `LAUNCH_AND_COMMS_STRATEGY.md`.  
Use **this file** for anything that applies to **agent-lab as a whole** or **multiple monuments**.

---

## Cursor skills (draft from chat)

- **draft-decision-log** — `.cursor/skills/draft-decision-log/`: ask the agent to *draft a decision log entry for what we discussed*.
- **capture-idea** — `.cursor/skills/capture-idea/`: ask to *capture this idea* → [`IDEAS_BACKLOG.md`](./IDEAS_BACKLOG.md).

## Conversation → build log (append newest at top)

<!--
Template:

### YYYY-MM-DD — <title>
- **Source:** e.g. Cursor chat, call, solo note (no PII).
- **Decision:** What we agreed or inferred.
- **Implementation:** Paths, commits (`git log -1 --oneline`), PRs — **no API keys or private URLs**.
- **Follow-ups:** Optional checklist.
-->

_(Start logging here.)_

---

## Conventions

- **Secrets:** Never paste `.env`, tokens, or private endpoints here.
- **Commits:** Reference SHA or `main @ date` when useful.
- **Monuments:** New monuments can add their own `docs/LAUNCH_AND_COMMS_STRATEGY.md` and link back to this file for shared agent patterns.
