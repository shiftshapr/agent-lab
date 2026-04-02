#!/usr/bin/env python3
"""
Automate GitHub settings for Bridgit-DAO/pacha-slate-producers (or override via args).

Requires:
  - GITHUB_TOKEN (or GH_TOKEN) with repo + project scopes (fine-grained: Contents RW,
    Issues RW, Metadata R, Pull requests RW, Administration R/W for discussions if needed).

Does:
  - PATCH repo: enable Discussions
  - POST labels (idempotent skip on 422)
  - GraphQL: create org Project v2, link to repo, add custom single-select "Slate stage" (§10 columns)

Usage:
  export GITHUB_TOKEN=ghp_...
  python3 setup_github_api.py --owner Bridgit-DAO --repo pacha-slate-producers

  Or put GITHUB_TOKEN=... in agent-lab/.env (gitignored); this script loads it if unset.

  python3 setup_github_api.py ... --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

GRAPHQL_URL = "https://api.github.com/graphql"
REST_BASE = "https://api.github.com"

SLATE_STAGE_OPTIONS = [
    ("Backlog", "GRAY"),
    ("Ready", "BLUE"),
    ("In progress", "YELLOW"),
    ("Submitted", "ORANGE"),
    ("In review", "PINK"),
    ("Changes requested", "RED"),
    ("Approved", "GREEN"),
]

LABELS = [
    ("agent:jury", "0E8A16", "Jury / slate scoring workflow"),
    ("agent:outreach", "1D76DB", "Outreach / community / content workflow"),
    ("agent:writer", "5319E7", "Writer-facing drafts"),
    ("film:foodlandia", "FBCA04", None),
    ("film:sats", "D4C5F9", None),
    ("film:sats-ii", "C5DEF5", None),
    ("film:sats-iii", "BFD4F2", None),
    ("film:civic-mason", "FFD8CC", None),
    ("scope:slate", "0075CA", "Cross-film slate"),
    ("type:producer-packet", "EDEDED", None),
    ("type:outreach", "EDEDED", None),
    ("type:community-plan", "EDEDED", None),
    ("type:content-brief", "EDEDED", None),
    ("type:jury-pass", "EDEDED", None),
    ("needs:editor", "B60205", None),
    ("needs:showrunner", "B60205", None),
    ("needs:legal", "B60205", None),
    ("needs:canon", "B60205", None),
    ("priority:p0", "E11D48", None),
    ("priority:p1", "F97316", None),
    ("promoted", "6F42C1", "Snapshot promoted to IPFS / ordinals"),
]


# Obvious documentation placeholders — not valid PATs.
def _agent_lab_root() -> Path:
    """…/agent-lab (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent.parent


def _load_github_token_from_dotenv() -> None:
    """If GITHUB_TOKEN/GH_TOKEN not set, load them from agent-lab/.env (no override)."""
    path = _agent_lab_root() / ".env"
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if key not in ("GITHUB_TOKEN", "GH_TOKEN"):
            continue
        if os.environ.get(key):
            continue
        val = val.strip().strip("'\"")
        if "#" in val:
            val = val.split("#", 1)[0].strip().strip("'\"")
        os.environ[key] = val


_BAD_TOKEN_LITERALS = frozenset(
    {
        "",
        "your_token",
        "paste_real_token_here",
        "ghp_xxxxxxxx",
        "ghp_xxxx",
        "xxx",
        "token",
    }
)


def _looks_like_masked_x_only_token(t: str) -> bool:
    """True if value looks like doc shorthand ghp_xxxx… (all x), not a real PAT."""
    low = t.lower()
    if low.startswith("ghp_"):
        core = t[4:]
    elif low.startswith("github_pat_"):
        core = t[11:]
    else:
        return False
    if len(core) > 32:
        return False
    core_nounderscore = core.replace("_", "")
    return bool(core_nounderscore) and all(c == "x" for c in core_nounderscore.lower())


def token() -> str:
    t = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if not t:
        sys.stderr.write(
            "Set GITHUB_TOKEN or GH_TOKEN to a real PAT (not a placeholder), "
            "or add GITHUB_TOKEN=... to agent-lab/.env (see .gitignore).\n"
        )
        sys.exit(1)
    low = t.lower()
    if low in _BAD_TOKEN_LITERALS or _looks_like_masked_x_only_token(t):
        sys.stderr.write(
            "GITHUB_TOKEN looks like a placeholder. Create a real token:\n"
            "  Classic: https://github.com/settings/tokens\n"
            "  Fine-grained: https://github.com/settings/personal-access-tokens\n"
            "Then: put GITHUB_TOKEN=... in agent-lab/.env or export it (use your actual secret).\n"
            "\nIf .env is correct but you still see this, an old shell export may be overriding it — run:\n"
            "  unset GITHUB_TOKEN GH_TOKEN\n"
            "then run this script again (environment variables win over .env).\n"
        )
        sys.exit(1)
    if len(t) < 20:
        sys.stderr.write(
            "GITHUB_TOKEN is unusually short — if you get 401, use a full PAT from GitHub settings.\n"
        )
    return t


def _auth_failed_hint() -> None:
    sys.stderr.write(
        "\n401 Unauthorized — the token is missing, revoked, or lacks scope.\n"
        "Fine-grained PAT: grant this repository Contents + Issues + Pull requests, "
        "and the Bridgit-DAO org read/write for Projects.\n"
        "Classic PAT: repo scope + read:org + project (or admin:org for some project APIs).\n\n"
    )


def rest_json(
    method: str,
    url: str,
    tok: str,
    data: dict | None = None,
    dry_run: bool = False,
) -> tuple[int, dict | list | None]:
    if dry_run:
        print(f"[dry-run] {method} {url}")
        if data is not None:
            print(f"          body: {json.dumps(data)[:200]}...")
        return 200, None

    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Content-Type": "application/json"} if body else {}),
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            if not raw:
                return resp.status, None
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            err = json.loads(raw)
        except json.JSONDecodeError:
            err = {"message": raw}
        return e.code, err


def gql(tok: str, query: str, variables: dict | None = None, dry_run: bool = False):
    if dry_run:
        print(f"[dry-run] graphql: {query[:80].strip()}...")
        return None

    payload = {"query": query}
    if variables is not None:
        payload["variables"] = variables

    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            out = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            err = json.loads(raw)
        except json.JSONDecodeError:
            err = raw
        sys.stderr.write(f"GraphQL HTTP {e.code}: {err}\n")
        if e.code == 401:
            _auth_failed_hint()
        raise SystemExit(1) from e
    if out.get("errors"):
        sys.stderr.write(json.dumps(out["errors"], indent=2) + "\n")
        raise SystemExit("GraphQL error")
    return out.get("data")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner", default="Bridgit-DAO")
    ap.add_argument("--repo", default="pacha-slate-producers")
    ap.add_argument("--project-title", default="Pacha producer slate")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.dry_run:
        _load_github_token_from_dotenv()

    tok = token() if not args.dry_run else ""

    repo_url = f"{REST_BASE}/repos/{args.owner}/{args.repo}"

    # --- Enable discussions ---
    code, body = rest_json("PATCH", repo_url, tok, {"has_discussions_enabled": True}, args.dry_run)
    if code in (200, 204) or args.dry_run:
        print("Discussions: enabled (or dry-run).")
    elif code == 401:
        print(f"Discussions: PATCH returned {code}: {body}")
        _auth_failed_hint()
        raise SystemExit(1)
    else:
        print(f"Discussions: PATCH returned {code}: {body}")

    # --- Labels ---
    labels_url = f"{repo_url}/labels"
    for name, color, desc in LABELS:
        payload = {"name": name, "color": color}
        if desc:
            payload["description"] = desc
        code, body = rest_json("POST", labels_url, tok, payload, args.dry_run)
        if args.dry_run:
            continue
        if code == 401:
            print(f"Label {name}: HTTP {code} {body}")
            _auth_failed_hint()
            raise SystemExit(1)
        if code == 201:
            print(f"Label created: {name}")
        elif code == 422 and isinstance(body, dict):
            errs = body.get("errors") or []
            if any(e.get("code") == "already_exists" for e in errs if isinstance(e, dict)):
                print(f"Label exists: {name}")
            else:
                print(f"Label {name}: HTTP {code} {body}")
        else:
            print(f"Label {name}: HTTP {code} {body}")

    if args.dry_run:
        print("[dry-run] Skipping GraphQL project steps.")
        return

    # --- Org + repo node IDs ---
    data = gql(
        tok,
        """
        query($login: String!, $owner: String!, $name: String!) {
          organization(login: $login) { id }
          repository(owner: $owner, name: $name) { id }
        }
        """,
        {"login": args.owner, "owner": args.owner, "name": args.repo},
    )
    org_id = data["organization"]["id"]
    repo_id = data["repository"]["id"]

    # --- Create project ---
    data = gql(
        tok,
        """
        mutation($ownerId: ID!, $title: String!) {
          createProjectV2(input: {ownerId: $ownerId, title: $title}) {
            projectV2 { id title url number }
          }
        }
        """,
        {"ownerId": org_id, "title": args.project_title},
    )
    proj = data["createProjectV2"]["projectV2"]
    project_id = proj["id"]
    print(f"Project created: {proj.get('title')} — {proj.get('url')} (number {proj.get('number')})")

    # --- Link repo ---
    data = gql(
        tok,
        """
        mutation($projectId: ID!, $repositoryId: ID!) {
          linkProjectV2ToRepository(input: {projectId: $projectId, repositoryId: $repositoryId}) {
            repository { nameWithOwner }
          }
        }
        """,
        {"projectId": project_id, "repositoryId": repo_id},
    )
    linked = data["linkProjectV2ToRepository"]["repository"]["nameWithOwner"]
    print(f"Linked project to repository: {linked}")

    # --- Custom field "Slate stage" (§10 columns) ---
    options = [
        {"name": n, "color": c, "description": f"PACHA_AGENT_GOVERNANCE §10 — {n}"}
        for n, c in SLATE_STAGE_OPTIONS
    ]
    data = gql(
        tok,
        """
        mutation($input: CreateProjectV2FieldInput!) {
          createProjectV2Field(input: $input) {
            projectV2Field {
              ... on ProjectV2SingleSelectField {
                id
                name
                options { id name }
              }
            }
          }
        }
        """,
        {
            "input": {
                "projectId": project_id,
                "dataType": "SINGLE_SELECT",
                "name": "Slate stage",
                "singleSelectOptions": options,
            }
        },
    )
    field = data["createProjectV2Field"]["projectV2Field"]
    print(f"Field created: {field['name']} with {len(field.get('options', []))} options.")
    print(
        "\nNext: In GitHub Projects UI, add a view (Board or Table) and "
        "group/sort by **Slate stage**. You can hide or ignore the default **Status** "
        "field if you only use Slate stage for the §10 workflow."
    )


if __name__ == "__main__":
    main()
