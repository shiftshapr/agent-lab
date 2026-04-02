# Boris Cherny / Claude Code workflow → Cursor & agent-lab

**Purpose:** Decide what to **reuse** from the installable Boris skill (`https://howborisusesclaudecode.com/api/install`) in this repo. Claude Code features are named; Cursor + agent-lab use different surfaces.

**Source skill:** tips on parallel work, plan mode, CLAUDE.md, skills, subagents, hooks, worktrees, `/simplify`, `/batch`, etc. (not reproduced here — fetch the URL if you need the full text).

---

## Already mirrored in agent-lab

| Claude Code idea | agent-lab equivalent |
|------------------|----------------------|
| Shared project memory | `docs/AGENT_AND_MONUMENT_DECISIONS.md`, `docs/PACHA_AGENT_GOVERNANCE.md`, monument `AUTOMATED_WORKFLOW.md` |
| Skills in git | `.cursor/skills/*`, `framework/deer-flow/skills/public/*` |
| Specialized agents | Orchestrator, jury, outreach, narrative layers, Drive ingestion, etc. |
| Output styles | `.cursor/rules/cognitive-modes.mdc` |
| Worktree parallelism | `docs/GIT_WORKTREES_PARALLEL_AGENTS.md` + `.cursor/rules/git-worktrees-parallel-work.mdc` |

---

## Worth translating (high value)

| Claude Code | Cursor / agent-lab action |
|-------------|---------------------------|
| **Subagents** (`code-simplifier`, `verify-app`, …) | Add or extend **`.cursor/skills/<name>/SKILL.md`** with the same playbook text; invoke by name in chat. |
| **“Do X more than once a day → skill”** | Same rule: promote repeated prompts to a skill under `.cursor/skills/`. |
| **CLAUDE.md compounding** | Keep logging corrections in **`docs/AGENT_AND_MONUMENT_DECISIONS.md`** (and monument docs); optionally add a short **`AGENTS.md`** at repo root (see below). |
| **Plan-first complex work** | Use Cursor **Plan** mode or explicit “plan only, then implement” in the first message. |
| **Parallel sessions** | Multiple Cursor windows + **git worktrees** (this doc’s companion). |

---

## Partial / different surface

| Claude Code | Notes |
|-------------|--------|
| **Hooks** (PostToolUse format, etc.) | No identical hook system in Cursor; closest wins are **format on save**, **pre-commit**, **CI**, and **narrow rules** in `.cursor/rules/`. |
| **`/permissions`, sandbox** | Editor-specific; document **allowed commands** in team docs if needed. |
| **`/simplify`, `/batch`** | No built-in slash commands; encode as **composer prompts** or a **skill** (“Run simplification checklist”, “Batch migration playbook”). |
| **MCP** | Already used (e.g. deer-flow, Zoho, Slack); align with Boris tips on **curated MCP** set, not “enable everything”. |

---

## Lower priority unless you use Claude Code daily

- Status line, spinner verbs, keybindings — Claude Code UI only.
- `@.claude` on PRs — use human or bot review comments + decision log updates instead.
- iOS / web session handoff — product-specific.

---

## How to mine the Boris skill for new Cursor skills

1. Fetch: `curl -L -o /tmp/boris-skill.md https://howborisusesclaudecode.com/api/install`
2. Skim sections: **Subagents**, **Skills & Slash Commands**, **Hooks** (rewrite for your stack), **Output Styles** (done via `cognitive-modes.mdc`).
3. For each recurring workflow, copy the **steps and checks** into a new `SKILL.md` with frontmatter `name` / `description` per your existing skills.

---

## References

- Root **`AGENTS.md`** — quick index for assistants working in this repo.
- **`docs/GIT_WORKTREES_PARALLEL_AGENTS.md`** — worktree commands and PR discipline.
