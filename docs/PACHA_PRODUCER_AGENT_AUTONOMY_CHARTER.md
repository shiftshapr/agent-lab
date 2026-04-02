# Pacha producer agents — autonomy charter (bounded initiative)

This charter defines **how much initiative** producer-side agents may take **without** a human typing each step, while staying inside **[`PACHA_AGENT_GOVERNANCE.md`](./PACHA_AGENT_GOVERNANCE.md)** (approvals, GitHub as system of record).

**Summary:** Agents may **choose and execute work** in allowed lanes until they hit a **stop line**; humans **approve** outcomes that matter.

---

## 1. Two modes (name them clearly)

| Mode | Who drives the next action? |
|------|-----------------------------|
| **Human-directed** | Human picks the milestone and asks for a deliverable. |
| **Agent-initiated (this charter)** | Agent **evaluates** backlog + context, **selects** the next best milestone (within rules), **produces** drafts, **hands off** for review—**does not** self-approve or self-merge protected work. |

Both modes use the same **GitHub milestone** and **Slate stage** workflow.

---

## 2. Autonomy tiers

### Tier A — No human ping required (agent may do on its own)

- Read: `projects/pacha/*.md`, `config/civic_mason_badge.md`, `knowledge/pacha_schema.md`, open GitHub issues/Project (if tooling available).
- **Draft** Markdown in a **branch** or local workspace intended for a PR to **`pacha-slate-producers`** (paths under `films/`, `slate/`, `outreach/`, `content/`).
- **Jury pass** or **outreach pack** as *files*, not as published comms.
- **JAUmemory:** `recall` at cycle start; `remember` after a coherent cycle (decisions, blockers, what was drafted)—no secrets, no PII.
- **Internal** experiment logs: hypothesis → action → result (in issue comment or `slate/` doc).

### Tier B — Human approval before the action counts as “done”

- **Merge** to default branch (e.g. `main`) or any **protected** branch.
- **Close** a milestone as **Approved** (checklist on issue).
- **Publish:** Discord announcements, social posts, emails to partners, public-facing copy.
- **Spend:** ads, tools, contracts, grants.
- **Canon lock:** anything that contradicts or overrides agreed lore without editor/showrunner sign-off.

### Tier C — Human or specialist only

- Legal, COPPA/privacy stance, medical/healing claims, investment language (especially SATS-adjacent).
- **Badge issuance** or live BRC333 operations affecting users.

---

## 3. “Pick next milestone” rules (agent initiative)

When no human names a task, the agent **selects one** item using this order:

1. **GitHub Project** (private `pacha-slate-producers`): first card in **Ready** with a written **Definition of done**; else **Backlog** item the agent can make **Ready** by adding DoD in the issue body (then work it).
2. If the board is empty: propose **one** new issue using the milestone body pattern in **[`PACHA_AGENT_GOVERNANCE.md`](./PACHA_AGENT_GOVERNANCE.md) §10.4** (title `[film-key] id Short title`) and start **slate/** or **films/** draft in **`pacha-slate-producers`**.
3. **Priority hints:** labels `priority:p0`, `needs:editor`, `needs:showrunner`—agent may **comment** with status; may **not** impersonate approval.
4. **Slate vs film:** alternate or bias toward **slate/** if multiple films are blocked on timeline coherence (use **`pacha-producer-jury`**); bias toward **outreach/** if the bottleneck is partners/community (**`pacha-producer-outreach`**).

If **two** milestones are equal priority, pick the **smallest** shippable draft (faster review loop).

---

## 4. Cadence (recommended)

| Cadence | Agent behavior |
|---------|----------------|
| **Per shift** (e.g. one Cursor session or one scheduled job) | One **pick** + one **primary deliverable** + PR/issue handoff. |
| **Daily** (light) | Comment on **one** blocked issue with a concrete unblock suggestion. |
| **Weekly** | One **jury** or **slate timeline** refresh if canon/files changed. |

**Token budget:** respect soft caps in [`PACHA_AGENT_GOVERNANCE.md`](./PACHA_AGENT_GOVERNANCE.md) §3; log overage if policy requires.

---

## 5. Skill routing (Cursor)

| Deliverable type | Skill |
|------------------|--------|
| Scorecards, slate timeline, canon conflicts | **`pacha-producer-jury`** |
| Partners, community plan, content briefs, community signal | **`pacha-producer-outreach`** |
| **This cycle’s** pick + sequencing + handoff checklist | **`pacha-producer-orchestrator`** |

The orchestrator **does not replace** jury/outreach depth—it **chooses** which to invoke and **stitches** the handoff.

---

## 6. Stop conditions (agent must stop and ask)

- Ambiguity on **canon** or **showrunner** choice after reading `projects/pacha/*.md`.
- Any Tier B or C action.
- **Repeated** `Changes requested` on the same milestone without resolution—post a short **blocker summary** for humans instead of spinning.

---

## 7. Success criteria for “entrepreneurial enough”

- The agent **starts** a useful slice of work from **board + memory** without a line-by-line human spec.
- Every external or irreversible step still goes through **human approval**.
- Artifacts land as **reviewable** GitHub PRs/issues, not only chat.

---

## 8. Related docs

| Doc | Role |
|-----|------|
| [`PACHA_AGENT_GOVERNANCE.md`](./PACHA_AGENT_GOVERNANCE.md) | Milestones, GitHub, budget, JAUmemory, Discord |
| [`config/civic_mason_badge.md`](../config/civic_mason_badge.md) | Badges / BRC333 / Pacha commerce |
| [`projects/pacha/README.md`](../projects/pacha/README.md) | Story canvases + repo link |
