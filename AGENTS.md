# agent-lab — notes for coding assistants

Monorepo: **protocols**, **DeerFlow** (`framework/deer-flow/`), **monuments** (e.g. `projects/monuments/bride_of_charlie/`), **apps** (e.g. draft editor).

## Behavior defaults (repo-wide)

- **Cognitive modes** (explanatory / learning / minimal): `.cursor/rules/cognitive-modes.mdc`
- **Parallel work / refactors:** prefer **git worktrees** — `.cursor/rules/git-worktrees-parallel-work.mdc` and `docs/GIT_WORKTREES_PARALLEL_AGENTS.md`

## Where “why we did X” lives

- Repo-wide decisions: `docs/AGENT_AND_MONUMENT_DECISIONS.md`
- Producer / outreach / Discord governance: `docs/PACHA_AGENT_GOVERNANCE.md`
- Mapping Claude Code–style workflows to Cursor: `docs/BORIS_CHERNY_WORKFLOW_CURSOR_MAP.md`

## Cursor skills (examples)

Under `.cursor/skills/`: producer orchestrator, jury, outreach, draft decision log, work-log ingestion, narrative layers, Google Drive ingestion, Discord, meta-layer draft, etc. Read the relevant `SKILL.md` when the task matches its description.

## DeerFlow

Skills and MCP: `framework/deer-flow/skills/public/`, `framework/deer-flow/extensions_config.json`. Scaffold / cron: `docs/SCAFFOLDING.md`.

## Python (repo root)

Monument and episode-analysis scripts expect the **agent-lab** dependency set (e.g. `jsonschema`). From the repo root:

- **Preferred:** `uv sync` once, then `uv run python <path-to-script> …` (or activate `.venv`).
- **SSH / bare `python3`:** If `.venv` exists and contains deps, `assign_ids.py` and `episode_analysis_protocol.py` will **re-exec** with `.venv/bin/python` when `jsonschema` is missing on the current interpreter. Set `AGENT_LAB_NO_VENV_REEXEC=1` to disable.
- **Without a venv:** install deps on that interpreter (e.g. `pip install -r requirements-shiftshapr.txt` plus other project needs, or install from `pyproject.toml`).
