#!/usr/bin/env bash
# Create folder tree + CODEOWNERS + issue template + README under the current repo root.
# Usage: from a clone of pacha-slate-producers:
#   bash scripts/pacha-slate-github-bootstrap/create_repo_tree.sh
# Or copy this script into the repo and run from repo root with path adjusted.

set -euo pipefail

ROOT="$(pwd)"
echo "Repo root: $ROOT"

DIRS=(
  slate
  films/foodlandia
  films/sats
  films/sats-ii
  films/sats-iii
  films/civic-mason
  outreach/partners
  outreach/community
  content/campaigns
  .github/ISSUE_TEMPLATE
)

for d in "${DIRS[@]}"; do
  mkdir -p "$d"
  # keep empty dirs in git
  if [[ ! -f "$d/.gitkeep" ]] && [[ "$d" != .github/ISSUE_TEMPLATE ]]; then
    touch "$d/.gitkeep"
  fi
done

# --- CODEOWNERS (edit @handles before merge) ---
if [[ ! -f CODEOWNERS ]]; then
  cat > CODEOWNERS << 'EOF'
# Code owners = who GitHub requests reviews from for matching paths.
# Docs: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
#
# Option A — GitHub org TEAM (display name can be "Pacha Team"; URL slug is usually lowercase, e.g. pacha-team):
#   1. Org owner: Settings → Teams → New team → name it, add members, note the slug in the URL.
#   2. Replace every line below with @Bridgit-DAO/pacha-team (use YOUR org slug + team slug).
#
# Option B — INDIVIDUAL usernames (no team required):
#   Use * @githubuser1 @githubuser2  (space-separated on each rule line)
#
# Replace the placeholder lines before merge; invalid @handles break CODEOWNERS silently for those paths.

* @Bridgit-DAO/pacha-team
films/** @Bridgit-DAO/pacha-team
outreach/** @Bridgit-DAO/pacha-team
content/** @Bridgit-DAO/pacha-team
slate/** @Bridgit-DAO/pacha-team
.github/** @Bridgit-DAO/pacha-team
EOF
  echo "Wrote CODEOWNERS — set @Bridgit-DAO/pacha-team (after creating team) or switch to @user handles."
else
  echo "CODEOWNERS already exists; skipped."
fi

# --- Issue template (matches docs/PACHA_AGENT_GOVERNANCE.md §10.4) ---
TEMPLATE=".github/ISSUE_TEMPLATE/producer-milestone.md"
if [[ ! -f "$TEMPLATE" ]]; then
  cat > "$TEMPLATE" << 'EOF'
---
name: Producer milestone
description: Pacha slate deliverable (governance §10)
title: "[film-key] YYYY-MM-DD_id Short title"
labels: []
---

## Milestone ID
`YYYY-MM-DD_scope_shortname_vN`

## Definition of done
- [ ] …

## Links
- **Draft PR:** 
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
EOF
  echo "Wrote $TEMPLATE"
else
  echo "$TEMPLATE already exists; skipped."
fi

# --- Short README stub if missing ---
# Do not use `wc -l < README.md` when README is absent — the redirect fails before stderr can be masked.
if [[ -f README.md ]]; then
  _lines="$(wc -l < README.md | awk '{print $1}')"
else
  _lines=0
fi
if [[ ! -f README.md ]] || [[ "${_lines:-0}" -lt 3 ]]; then
  cat > README.md << 'EOF'
# pacha-slate-producers

Private mono-repo for **Pacha** film slate: producer packets, outreach, content, and cross-film slate notes.

- **Governance & GitHub setup:** [agent-lab `docs/PACHA_AGENT_GOVERNANCE.md`](https://github.com/YOUR_ORG/agent-lab/blob/main/docs/PACHA_AGENT_GOVERNANCE.md) (adjust link to your canonical doc).
- **Board columns:** use Project field **Slate stage** (created by `setup_github_api.py`) or match §10 in that doc.

## Layout

| Path | Purpose |
|------|---------|
| `slate/` | Jury outputs, timeline, cross-film |
| `films/*/` | Per-film producer materials |
| `outreach/` | Partners, community plans |
| `content/` | Campaign briefs |

EOF
  echo "Wrote README.md stub — customize links."
fi

echo "Done. Next: edit CODEOWNERS, commit, then run setup_github_api.py with GITHUB_TOKEN."
