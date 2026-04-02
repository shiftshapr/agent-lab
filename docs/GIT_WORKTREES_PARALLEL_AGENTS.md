# Git worktrees for parallel agents and big refactors

**Purpose:** Isolate parallel Cursor sessions, agent runs, and large refactors so they do not overwrite each other’s working trees. Same discipline as Claude Code’s worktree workflow; git is the tool.

**Scope:** agent-lab monorepo (`framework/deer-flow/`, `projects/`, `protocols/`, etc.).

---

## Why worktrees here

- **deer-flow** and **monuments** can change together; two agents on one tree cause merge-by-accident in the working directory.
- **Experiments** (async migration, dependency bump) stay on dedicated branches without stashing your daily work.
- **Reviews** are easier: one PR per worktree / branch.

## Basics

```bash
cd /path/to/agent-lab
git fetch origin

# Sibling directory (simple, no ignore rules)
git worktree add ../agent-lab-wt-NAME -b branch/name origin/main

cd ../agent-lab-wt-NAME
# Open this folder as the Cursor workspace root for that session
```

List and remove:

```bash
git worktree list
git worktree remove ../agent-lab-wt-NAME   # after merge or discard
```

## Naming

Use a branch name that states intent, for example:

- `experiment/deerflow-skill-loader`
- `refactor/bride-transcript-pipeline`
- `fix/draft-editor-tailwind`

Match the directory name to the branch when possible.

## Inside-repo worktrees (optional)

To keep worktrees under the repo:

```bash
mkdir -p .git-worktrees
git worktree add .git-worktrees/my-task -b branch/name origin/main
```

The repo `.gitignore` includes `.git-worktrees/` so those checkouts are not committed as project files. Prefer **sibling directories** if you use tools that assume a single root or symlink sensitive paths.

## Parallel agents (Cursor)

1. Create **one worktree + branch per parallel task**.
2. Open **each worktree as its own Cursor window** (File → New Window → Open Folder).
3. Run agents only in the tree that owns that task.
4. Open **one PR per branch** when ready.

## deer-flow submodule

If your work touches the deer-flow submodule, treat it like any other path: commit submodule pointer updates from the worktree that performed the change, and document the submodule branch in the PR description.

## Related

- Cognitive modes for how verbose the assistant should be: `.cursor/rules/cognitive-modes.mdc`
- Boris workflow mapped to Cursor: `docs/BORIS_CHERNY_WORKFLOW_CURSOR_MAP.md`
