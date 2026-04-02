# Pacha & slate producer agents — governance, memory, and artifacts

This document is the **human-facing source of truth** for how **producer / outreach agents**, **milestones**, **budgets**, **GitHub artifacts**, **JAUmemory**, and **Discord** work together. Cursor skills **`pacha-producer-jury`** and **`pacha-producer-outreach`** implement the creative split; **`pacha-producer-orchestrator`** runs **bounded agent-initiated** shifts per **[`PACHA_PRODUCER_AGENT_AUTONOMY_CHARTER.md`](./PACHA_PRODUCER_AGENT_AUTONOMY_CHARTER.md)**. This doc implements **ops**.

---

## 1. Roles (RACI-style)

| Role | Responsibility |
|------|----------------|
| **Showrunner** | Tie-breaks, slate-level greenlight, final canon calls. |
| **Editor** | One voice for merged drafts (rotating “editor of the week” if you have 3–5 editors). |
| **Approvers** | Named checks: brand/safety, lore/canon, legal/comms when needed. |
| **Agent operators** | Run agents with budgets; never self-approve canon or public comms. |

**Approval rule:** Agents produce **drafts**. Only humans move a milestone to **Approved** (or record sign-off in GitHub).

---

## 2. Milestones and review loop

Every deliverable is a **milestone** with an ID, e.g. `2026-03-21_foodlandia_producer_packet_v1`.

**States**

`Draft` → `Submitted` → `In review` → `Approved`  
or `Changes requested` → `Revised` → `Approved`

**Requirements**

- **Definition of done** per milestone type (which sections exist, what “v1” means).
- **Changes requested** = bullet list (specific), not vague feedback.
- **Approved** = named approvers + date (issue comment, PR review, or checklist in a tracking issue).

---

## 3. Daily token budget (soft cap + penalty)

Cursor/LLM UIs do **not** enforce per-agent daily caps automatically. Treat this as **policy + ledger**.

- Assign each agent role a **soft daily budget** (tokens or approximate USD).
- **Overage is allowed** with consequences you enforce, for example:
  - Log overage (date, agent, task, rough usage).
  - **Penalty:** reduce next-day budget by a fraction of overage; or require **human pre-approval** before the next large run; or enforce a **short output format** for the next cycle.
- **Goal:** predictability and accountability, not perfect metering on day one.

---

## 4. Private GitHub — producer tracking and artifacts

**Default:** Use a **private GitHub org/repo** (or one repo per film, or mono-repo with paths—your choice) for:

- Producer packets, outreach drafts, community plans (Markdown).
- **Milestone tracking** (Issues, Projects, or simple labels).
- **Approvals** via PR review or issue checklists.
- **Version history** and audit trail.

**Configure / publish / “make repos”**

- Use **repo templates** under your org for new producer or film repos.
- **Humans** (or a tightly scoped automation with PAT/GitHub App) create repos—agents suggest names and structure; **do not** give agents unbounded repo-creation without review.
- Document the **naming convention** (e.g. `pacha-slate-producers`, `pacha-film-foodlandia`).

### Storage: GitHub vs Neo4j vs JAUmemory

| Layer | What it stores | Do you “need a database”? |
|-------|----------------|---------------------------|
| **Private GitHub** (Issues, Projects, PRs, Markdown in repo) | Producer milestones, approvals, drafts, audit trail | **This is your ops database** for the producer workflow—no extra DB required unless you want reporting. |
| **Neo4j** | Pacha **story graph**: characters, realms, arcs, themes, evidence—see [`knowledge/pacha_schema.md`](../knowledge/pacha_schema.md) | **Yes for narrative/canon graph**, not for replacing GitHub columns. Same Neo4j instance can hold meta-layer + Pacha ontologies as separate label sets. |
| **JAUmemory** (MCP) | Cross-session **agent context**: decisions, partner stance, norms | Complements GitHub; not a substitute for versioned artifacts or graph canon. |

**Optional upgrade:** If you later need one graph that joins **lore + operations**, add nodes such as `ProductionMilestone` (or reuse a doc label) with a property `github_issue_url` linking to the canonical issue—only when you have queries that justify the sync cost.

### Canonical producer repository (mono-repo)

**All productions** (every film on the slate, slate-wide jury passes, outreach, shared content) can live in **one private repo**:

**[https://github.com/Bridgit-DAO/pacha-slate-producers](https://github.com/Bridgit-DAO/pacha-slate-producers)**

Use **folders** to separate films and workstreams (layout below). Issues/Projects reference paths under this repo.

*This agent-lab tree under `projects/pacha/*.md` is creative canon you may **mirror** or **sync** into `films/` in that repo—pick one system of truth for Markdown and stick to it.*

### Folder layout (`pacha-slate-producers`)

Suggested tree (create empty dirs with `.gitkeep` if needed):

```text
pacha-slate-producers/
├── README.md                 # Link to this governance doc or short onboarding
├── CODEOWNERS                # Optional: required reviewers for docs (you said yes)
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   └── milestone.md      # Paste §10.4 body into form template
│   └── (workflows/)          # Optional: Actions that react to labels
├── slate/                    # Cross-film: timeline, jury outputs, slate notes
├── films/
│   ├── foodlandia/
│   ├── sats/
│   ├── sats-ii/
│   ├── sats-iii/
│   └── civic-mason/
├── outreach/                 # Partner lists, outreach drafts, community plans
│   ├── partners/
│   └── community/
└── content/                  # Campaign briefs, calendars, asset copy
    └── campaigns/
```

Paths in milestone issues should match real files, e.g. `films/foodlandia/producer_packet_v1.md`.

### Humans vs “agents” on GitHub

- **Approvers and final sign-off stay human** (editor, showrunner, legal, canon). Agents **draft**; they do not replace approval policy.
- **Labels** like `agent:jury` / `agent:outreach` mean *which workflow produced the draft*, not that a GitHub user named “Producer Agent” is a real person.
- **Enable GitHub Discussions** for advisory topics and reaction-based signal (you confirmed yes). **Use `CODEOWNERS`** on `films/**`, `outreach/**`, etc., so the right humans get review requests (you confirmed yes).

### GitHub accounts for automation (don’t spin up five “people”)

Prefer **one integration identity** for all tooling:

| Approach | When to use |
|----------|-------------|
| **Fine-grained Personal Access Token** on a single **machine/bot user** (e.g. `bridgit-agent` in the org) | Simplest: Cursor, scripts, or small bots push branches, open PRs, create issues. |
| **GitHub App** | Stricter org policies, short-lived tokens, multiple repos with scoped install. |

Avoid creating **multiple personal GitHub accounts** for each fictional producer agent—credential sprawl and ToS/account-type issues. If you want **attribution in commit messages**, use `Co-authored-by:` or issue assignees = **humans**; automation user stays one service account.

### Can an agent set up or drive GitHub Projects?

**Yes, with API access and scopes.**

- **Issues & PRs:** REST or `gh` CLI — create/update issues, labels, comments, PRs (token needs `contents`, `issues`, `pull_requests`).
- **Projects (v2):** **GraphQL** — create items, set **Status** field to match board columns (e.g. Backlog → Approved). Requires **project** scope on the token and the **project node ID** (look up via API once).
- **First-time board setup** (columns, workflow): often faster **once in the GitHub UI**; then agents **move cards** and **open issues** via API day to day.

Typical pattern: human creates the Project + columns; agent (with PAT) **adds issues**, **links PRs**, **updates Status** when a draft moves from *In progress* → *Submitted*.

**Bootstrap scripts (agent-lab):** [`scripts/pacha-slate-github-bootstrap/`](../scripts/pacha-slate-github-bootstrap/) — `create_repo_tree.sh` (folders, `CODEOWNERS`, issue template) and `setup_github_api.py` (Discussions, labels, org Project v2 + **Slate stage** field matching §10). See that folder’s `README.md`.

---

## 5. Gov hub and artifact ladder (GitHub → IPFS / ordinals)

**Baseline:** **GitHub** (or Git-backed) artifacts are the **default** public or partner-visible layer for **review, discussion, and lightweight governance**:

- Issues/Discussions for **comment threads**.
- **Reactions** or labeled issues for **non-binding sentiment** (“vote” on directions)—clearly labeled as **signal**, not binding corporate vote unless your legal setup says otherwise.

**Upgrade path**

- **IPFS** (or similar): immutable snapshots of approved text, hashes linked from GitHub.
- **Ordinals / inscriptions**: monument-class or canonical commitments when you are ready—see `config/civic_mason_badge.md` and monument workflows elsewhere in agent-lab.

**Principle:** GitHub is the **working and review** layer; stronger permanence is an **explicit promotion** step, not the default for every draft.

---

## 6. Do you need Notion?

**Not required** if GitHub Issues/Projects/Discussions + Markdown in repo cover:

- Milestones, approvers, and links to drafts.

**Consider Notion** if you need:

- Non-technical stakeholders who refuse GitHub.
- Visual roadmaps and narrative “one-pagers” without PR friction.

**Avoid double maintenance:** pick a **system of record** (recommend **GitHub** for producer artifacts) and treat Notion as **mirror or summary** if used at all.

---

## 7. JAUmemory — contextual memory

Use **JAUmemory** for **cross-session context** that should survive beyond a single Cursor chat: slate decisions, partner stance, recurring community themes, penalty/budget policy tweaks, Discord norms.

**Practice**

- After **`mcp_login`** (when using the JAUmemory MCP), use **`recall`** at the start of substantive producer/outreach work when context may exist.
- After **approved** milestones or major decisions, use **`remember`** with clear **`content`**, optional **`context`**, **`tags`** (e.g. `pacha`, `producer-slate`, `discord`, `partner-x`), and **`importance`** when useful.

**Repo pointers:** [`docs/JAUMEMORY_AGENT_LAB.md`](./JAUMEMORY_AGENT_LAB.md), paste-ready logs pattern in [`docs/JAUMEMORY_LOG_2026-03_Bride_Charlie_Workflow.md`](./JAUMEMORY_LOG_2026-03_Bride_Charlie_Workflow.md).

---

## 8. Discord — Pacha and Meta-Layer

Two servers (or two clear channel groups) need **consistent moderation and handoff**:

- **Pacha:** family-adjacent tone, kid safety, parent/guardian framing; strict on medical/investment claims (especially SATS-adjacent metaphors—**no financial advice**).
- **Meta-Layer:** governance, DPs, gov hub links, agent coordination; link out to **reviewable artifacts** on GitHub/gov hub.

**Skill:** use **`discord-community-management`** (`.cursor/skills/discord-community-management/SKILL.md`) for channel structure, mod norms, escalation, and “what lives in Discord vs GitHub.”

---

## 9. Related paths and skills

| Item | Location |
|------|-----------|
| Film canvases | `projects/pacha/*.md` |
| Badge / BRC333 policy | `config/civic_mason_badge.md` |
| Lore / schema | `knowledge/pacha_schema.md` |
| Jury scoring & slate alignment | `.cursor/skills/pacha-producer-jury/SKILL.md` |
| Partners, community, content | `.cursor/skills/pacha-producer-outreach/SKILL.md` |
| Agent-initiated shift (pick + handoff) | `.cursor/skills/pacha-producer-orchestrator/SKILL.md` |
| Autonomy charter (bounded initiative) | [`PACHA_PRODUCER_AGENT_AUTONOMY_CHARTER.md`](./PACHA_PRODUCER_AGENT_AUTONOMY_CHARTER.md) |
| Decision logging | `.cursor/skills/draft-decision-log/SKILL.md` |
| Work log → memory | `.cursor/skills/work-log-ingestion/SKILL.md` |

---

## 10. GitHub Projects — columns, labels, milestone checklist

Use this as a **one-page setup** for a private **producer** repo (org template or existing repo). Works with **GitHub Projects** (classic Kanban or Projects v2—map columns to **Status** field in v2).

### 10.1 Board columns (Kanban)

Use **seven** columns, or merge adjacent ones if the board feels heavy.

| Column | Meaning |
|--------|---------|
| **Backlog** | Captured ideas; no Definition of Done yet. |
| **Ready** | DoD written; owner (human/agent operator) assigned; may start work. |
| **In progress** | Draft actively being produced (Cursor / agent). |
| **Submitted** | Draft linked; waiting for reviewers to pick up. |
| **In review** | Approvers commenting / checklist in flight. |
| **Changes requested** | Specific bullet feedback; needs revision before re-review. |
| **Approved** | Named sign-off recorded; merge or tag release as policy dictates. |

**Optional:** Add a label **`promoted`** (or column **Promoted**) for artifacts snapshotted to IPFS / ordinals—see §5.

### 10.2 Issue title convention

```
[<film-key>] <milestone_id> <short title>
```

**Examples**

- `[foodlandia] 2026-03-21_producer_packet_v1 Producer packet`
- `[slate] 2026-03-22_jury_pass_q1 Jury scorecard + timeline note`

**`film-key`:** `foodlandia`, `sats`, `sats-ii`, `sats-iii`, `civic-mason`, `slate`, `outreach`, etc.

### 10.3 Labels (create in repo Settings → Labels)

| Prefix | Examples |
|--------|-----------|
| Agent role | `agent:jury`, `agent:outreach`, `agent:writer` |
| Film / scope | `film:foodlandia`, `film:sats`, `film:civic-mason`, `scope:slate` |
| Deliverable type | `type:producer-packet`, `type:outreach`, `type:community-plan`, `type:content-brief`, `type:jury-pass` |
| Blocking | `needs:editor`, `needs:showrunner`, `needs:legal`, `needs:canon` |
| Priority | `priority:p0`, `priority:p1` |

Keep the set **small**; add labels only when the board gets noisy.

### 10.4 Milestone issue body (paste into each issue)

```markdown
## Milestone ID
`YYYY-MM-DD_scope_shortname_vN`

## Definition of done
- [ ] …

## Links
- **Draft PR:** (or branch)
- **Doc path in repo:** `path/to/file.md`

## Approvers (human — check when satisfied)
- [ ] Editor:
- [ ] Canon / lore:
- [ ] Brand / safety:
- [ ] Legal / comms (if needed):
- [ ] Showrunner (if needed):

## Operator
- **Human / agent role:**
- **Token / budget note** (optional):

## Status log
- YYYY-MM-DD — …
```

### 10.5 PR vs issue

- **Prefer a PR** when the deliverable is a concrete Markdown (or doc) change: review = line comments + approval.
- **Use an issue first** when the work is exploratory; open a **PR** once the draft stabilizes, or attach the final file in the issue after approval if your team prefers issue-only for some types.

### 10.6 “Voting” / community signal (optional)

For non-binding direction (e.g. “which theme for next read-along”), use **GitHub Discussions** or a **labeled issue** with reactions; state in the post that results are **advisory** unless the showrunner promotes them to a milestone.

---

## 11. One-line policy (for onboarding)

**Soft daily token budget per agent; overage allowed with logged penalty; every canon- or public-impacting deliverable is a GitHub-tracked milestone with named human approval; contextual memory in JAUmemory; Discord for live community, GitHub for reviewable artifacts and upgrade path to IPFS/ordinals when promoted.**
