# Pacha slate GitHub bootstrap

Scripts to match [`docs/PACHA_AGENT_GOVERNANCE.md`](../../docs/PACHA_AGENT_GOVERNANCE.md) (folder tree, `CODEOWNERS`, issue template, Discussions, labels, GitHub Projects v2 plus custom **Slate stage** field).

---

## 0. Copy-paste rules (especially zsh on macOS)

1. **Replace placeholders** — There is no folder literally named `path`. Set real paths in the variables below.
2. **Run one shell block at a time** (or use the all-in-one block in §1b).
3. **Do not paste prose lines** (e.g. “Edit CODEOWNERS…”) into the shell as commands.
4. **Avoid `**` in shell lines** — In zsh, `**` is a glob. In comments after `#` it is usually safe; if you see `no matches found`, you pasted a line where `**` was not inside a comment.
5. **`@Bridgit-DAO/...` in zsh** — If a line starts with `@`, quote it or keep it inside a `#` comment only. Prefer editing `CODEOWNERS` in an editor, not from a weird one-liner.

---

## 1a. Paths (edit these once)

```bash
# Where this agent-lab repo lives on your machine:
AGENT_LAB="$HOME/workspace/agent-lab"

# Where you want the pacha-slate-producers clone (parent directory must exist):
CLONE_PARENT="$HOME/github"
mkdir -p "$CLONE_PARENT"
```

If your agent-lab is not under `~/workspace/agent-lab`, set `AGENT_LAB` to the real directory (for you, often `/Users/shiftshapr/workspace/agent-lab`).

---

## 1b. Clone, run tree script, commit (no GitHub token)

```bash
AGENT_LAB="$HOME/workspace/agent-lab"
CLONE_PARENT="$HOME/github"
mkdir -p "$CLONE_PARENT"

git clone git@github.com:Bridgit-DAO/pacha-slate-producers.git "$CLONE_PARENT/pacha-slate-producers"
cd "$CLONE_PARENT/pacha-slate-producers"

bash "$AGENT_LAB/scripts/pacha-slate-github-bootstrap/create_repo_tree.sh"
```

Then open **`CODEOWNERS`** in an editor:

- **If you use a GitHub org team:** Create the team first (**Org → Teams → New team**). The file must use the **team slug** from the URL (usually lowercase, e.g. `pacha-team`), not the display name: `@Bridgit-DAO/pacha-team`.
- **If you skip teams:** Use one or more GitHub usernames on each line, e.g. `* @alice @bob` (space-separated).

Invalid `@` handles are ignored for those paths, so double-check spelling.

```bash
cd "$CLONE_PARENT/pacha-slate-producers"
git add .
git status
git commit -m "Bootstrap slate repo tree, CODEOWNERS, issue template"
git push
```

---

## 2. Automate GitHub (token)

Create a **fine-grained PAT** (or classic PAT) with access to `pacha-slate-producers`:

- Repository: Contents, Issues, Metadata, Pull requests (read/write as needed).
- Organization: read and write **GitHub Projects** for `Bridgit-DAO` (needed for GraphQL project mutations).
- If Discussions PATCH returns 403, enable Discussions once: repo **Settings → General → Features**.

```bash
AGENT_LAB="$HOME/workspace/agent-lab"
# Use a real PAT from GitHub — not the words "your_token" or "paste_real_token_here".
# Classic: https://github.com/settings/tokens
# Fine-grained: https://github.com/settings/personal-access-tokens
export GITHUB_TOKEN="ghp_…………"   # your secret

python3 "$AGENT_LAB/scripts/pacha-slate-github-bootstrap/setup_github_api.py" \
  --owner Bridgit-DAO \
  --repo pacha-slate-producers
```

**Or use `agent-lab/.env`** (already in `.gitignore`): add a line `GITHUB_TOKEN=ghp_...` or `GITHUB_TOKEN=github_pat_...` to your agent-lab `.env`. The script loads it **only if** `GITHUB_TOKEN` / `GH_TOKEN` are **not** already set in the shell — so if you ever ran `export GITHUB_TOKEN=your_token`, run `unset GITHUB_TOKEN GH_TOKEN` first or use a fresh terminal. Inline `#` comments on the same line are stripped when parsing `.env`.

Dry run (no token required):

```bash
AGENT_LAB="$HOME/workspace/agent-lab"
python3 "$AGENT_LAB/scripts/pacha-slate-github-bootstrap/setup_github_api.py" \
  --owner Bridgit-DAO \
  --repo pacha-slate-producers \
  --dry-run
```

---

## 3. If something fails

| Symptom | Cause | Fix |
|--------|--------|-----|
| `cd: too many arguments` | Copied `cd /path/to/...` literally or merged two paths. | Use real paths; use the `CLONE_PARENT` block in §1b. |
| `No such file or directory` (bash script) | Wrong `AGENT_LAB`. | `ls "$HOME/workspace/agent-lab/scripts/pacha-slate-github-bootstrap/"` |
| `fatal: not a git repository` | Not inside the clone; stayed in `~`. | `cd` into `pacha-slate-producers` before `git add`. |
| `zsh: no matches found` and `**` | zsh glob on a pasted line. | Use §2 as written; do not put bare `**` in commands. |
| `401 Bad credentials` | Placeholder token or wrong/expired PAT. | Create a new token; paste the real `ghp_...` or `github_pat_...` value (see §2). |
| `zsh: unknown file attribute: B` | zsh parsed `@` or `(...)` as a glob. | Edit `CODEOWNERS` in an editor; do not run `@Bridgit-DAO/...` as a shell command. |
| `403` / Discussions | Token or policy. | Enable Discussions in the UI once. |
| GraphQL project errors | Missing org Projects permission. | Regenerate PAT with Projects read/write for the org. |
| `createProjectV2Field` error | API / policy. | Add field **Slate stage** manually in project settings. |
| Labels `422` | Already exists. | Safe to ignore. |

---

## 4. After the script

1. Open the **Project** URL printed in the terminal.
2. Add a **Board** (or Table) view grouped by **Slate stage**.
3. Optionally ignore or hide the default **Status** field if you only use **Slate stage** for governance §10.

---

## 5. Canonical doc

[`docs/PACHA_AGENT_GOVERNANCE.md`](../../docs/PACHA_AGENT_GOVERNANCE.md) §4 and §10.
