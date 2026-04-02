"""Draft editor API — basic auth, CRUD, publish trigger."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_httpauth import HTTPBasicAuth

APP_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = APP_DIR.parent.parent

app = Flask(__name__, static_folder="static")
auth = HTTPBasicAuth()


def _load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


@auth.verify_password
def verify_password(username: str, password: str) -> bool:
    _load_env()
    expected = os.environ.get("DRAFT_EDITOR_PASSWORD", "")
    expected_user = os.environ.get("DRAFT_EDITOR_USER", "draft")
    return username == expected_user and password == expected and bool(expected)


# --- API ---

@app.route("/api/drafts", methods=["GET"])
@auth.login_required
def list_drafts():
    from .store import list_drafts as _list
    return jsonify(_list())


@app.route("/api/drafts", methods=["POST"])
@auth.login_required
def create_draft():
    from .store import create_draft
    data = request.get_json() or {}
    draft = create_draft(
        content=data.get("content", ""),
        platform=data.get("platform", "linkedin"),
        metadata=data.get("metadata"),
        author=data.get("author", "agent"),
    )
    return jsonify(draft), 201


@app.route("/api/drafts/<draft_id>", methods=["GET"])
@auth.login_required
def get_draft(draft_id: str):
    from .store import get_draft
    draft = get_draft(draft_id)
    if not draft:
        return jsonify({"error": "Not found"}), 404
    return jsonify(draft)


@app.route("/api/drafts/<draft_id>", methods=["PUT"])
@auth.login_required
def update_draft(draft_id: str):
    from .store import update_draft
    data = request.get_json() or {}
    content = data.get("content")
    if content is None:
        return jsonify({"error": "content required"}), 400
    draft = update_draft(draft_id, content, author="user", milestone=data.get("milestone"))
    if not draft:
        return jsonify({"error": "Not found"}), 404
    return jsonify(draft)


@app.route("/api/drafts/<draft_id>/publish", methods=["POST"])
@auth.login_required
def publish_draft(draft_id: str):
    from .store import get_draft, publish_draft

    draft = get_draft(draft_id)
    if not draft:
        return jsonify({"error": "Not found"}), 404

    # Invoke publish agent via run-deerflow-task
    prompt = f"""Post this draft to {draft.get('platform', 'linkedin')}. Content:
{draft['content']}

Metadata: {draft.get('metadata', {})}
Use Playwright MCP to post. Attach image if metadata has image path."""
    try:
        result = subprocess.run(
            [sys.executable, str(AGENT_LAB_ROOT / "scripts" / "run-deerflow-task.py"), prompt, "--timeout", "300"],
            cwd=str(AGENT_LAB_ROOT),
            env={**os.environ, "AGENT_LAB_ROOT": str(AGENT_LAB_ROOT)},
            capture_output=True,
            text=True,
            timeout=320,
        )
        if result.returncode != 0:
            return jsonify({"error": "Publish failed", "detail": (result.stderr or "")[:500]}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Publish timed out"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    published = publish_draft(draft_id)
    return jsonify({"status": "published", "draft": published})


@app.route("/api/drafts/<draft_id>", methods=["DELETE"])
@auth.login_required
def delete_draft(draft_id: str):
    from .store import delete_draft
    if not delete_draft(draft_id):
        return jsonify({"error": "Not found"}), 404
    return jsonify({"status": "deleted"})


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/<path:path>")
def static_files(path: str):
    return send_from_directory("static", path)


def main() -> None:
    _load_env()
    port = int(os.environ.get("DRAFT_EDITOR_PORT", "8081"))
    if not os.environ.get("DRAFT_EDITOR_PASSWORD"):
        print("Set DRAFT_EDITOR_PASSWORD in .env", file=sys.stderr)
        sys.exit(1)
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
