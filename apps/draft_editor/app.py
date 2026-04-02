"""Draft editor API — basic auth, CRUD, publish trigger."""

from __future__ import annotations

import sys
from pathlib import Path

# Running `python apps/draft_editor/app.py` loads this file as __main__ with no package;
# relative imports (`from . import …`) would fail. Mirror `python -m apps.draft_editor.app`.
if __name__ == "__main__" and __package__ is None:
    _repo_root = Path(__file__).resolve().parent.parent.parent
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    __package__ = "apps.draft_editor"

import html
import importlib.util
import json
import os
import re
import subprocess
import threading
import time
import uuid
from typing import Any

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_httpauth import HTTPBasicAuth

APP_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = APP_DIR.parent.parent

app = Flask(__name__, static_folder="static")
auth = HTTPBasicAuth()

from . import bride_hub as _bride_hub  # noqa: E402
from . import bride_neo4j_hub as _bride_neo4j_hub  # noqa: E402
from . import bride_run_ops as _bride_run_ops  # noqa: E402

# LLM sense scan can exceed Cloudflare’s ~100s proxy timeout — run in a thread and poll GET …/job/<id>
# Jobs are stored on disk so polls survive process restarts and work if multiple workers are added later.
_SENSE_SCAN_JOBS_LOCK = threading.Lock()
_SENSE_SCAN_JOB_MAX_AGE_SEC = 7200


def _sense_scan_jobs_base() -> Path:
    """Directory for sense-scan job JSON files (may not exist yet)."""
    return AGENT_LAB_ROOT / ".draft-editor-cache" / "sense-scan-jobs"


def _ensure_sense_scan_jobs_dir() -> Path:
    d = _sense_scan_jobs_base()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sense_scan_job_path(job_id: str) -> Path | None:
    jid = re.sub(r"[^a-fA-F0-9]", "", job_id or "")
    if not jid or len(jid) > 32:
        return None
    return _sense_scan_jobs_base() / f"{jid.lower()}.json"


def _sense_scan_job_read(job_id: str) -> dict[str, Any] | None:
    path = _sense_scan_job_path(job_id)
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _sense_scan_job_write(job_id: str, data: dict[str, Any]) -> None:
    path = _sense_scan_job_path(job_id)
    if path is None:
        return
    _ensure_sense_scan_jobs_dir()
    with _SENSE_SCAN_JOBS_LOCK:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)


def _prune_sense_scan_jobs() -> None:
    d = _sense_scan_jobs_base()
    if not d.is_dir():
        return
    cutoff = time.time() - _SENSE_SCAN_JOB_MAX_AGE_SEC
    for p in d.glob("*.json"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink(missing_ok=True)
        except OSError:
            pass


def _execute_transcript_sense_scan(body: dict[str, Any]) -> dict[str, Any]:
    """Run full sense scan + optional apply + YouTube enrichment; same payload as POST body."""
    try:
        from dotenv import load_dotenv

        load_dotenv(AGENT_LAB_ROOT / ".env", override=False)
    except ImportError:
        pass

    ep = body.get("episode")
    ep_int = int(ep)
    max_batches = body.get("max_batches")
    if max_batches is not None:
        try:
            max_batches = int(max_batches)
        except (TypeError, ValueError):
            max_batches = None

    do_apply = body.get("apply") in (True, 1, "1", "true", "yes")
    apply_min_sev = body.get("apply_min_severity")
    if isinstance(apply_min_sev, str):
        apply_min_sev = apply_min_sev.strip() or None
    elif apply_min_sev is not None:
        apply_min_sev = str(apply_min_sev).strip() or None

    sense_mod = _load_transcript_sense_scan_module()
    if sense_mod is None:
        return {"error": "transcript_sense_scan.py not found"}

    result = sense_mod.sense_scan_episode(
        _bride_project_dir(), ep_int, max_batches=max_batches
    )
    if isinstance(result, dict) and result.get("error"):
        return result

    if do_apply and not result.get("error"):
        try:
            apply_out = sense_mod.sense_scan_apply_inscription(
                _bride_project_dir(),
                ep_int,
                result.get("findings") or [],
                dry_run=False,
                min_severity=apply_min_sev,
            )
            result["apply"] = apply_out
            if apply_out.get("written"):
                sync_script = _bride_project_dir() / "scripts" / "sync_transcript_hashes.py"
                if sync_script.is_file():
                    sr = subprocess.run(
                        [sys.executable, str(sync_script), "--episode", str(ep_int)],
                        cwd=str(AGENT_LAB_ROOT),
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    result["sync_transcript_hashes"] = {
                        "returncode": sr.returncode,
                        "stderr": (sr.stderr or "")[-1500:],
                    }
        except Exception as e:
            result["apply"] = {"error": str(e)}

    media_mod = _load_bride_transcript_media_module()
    if media_mod is not None and not result.get("error"):
        vid = media_mod.video_id_for_episode(ep_int, _bride_project_dir())
        if vid:
            for f in result.get("findings") or []:
                if f.get("error") or f.get("raw_tail"):
                    continue
                sec = f.get("caption_seconds")
                if sec is not None:
                    f["youtube"] = media_mod.youtube_urls(vid, sec)

    return result


def _sense_scan_worker(job_id: str, body: dict[str, Any]) -> None:
    prev = _sense_scan_job_read(job_id) or {}
    started = float(prev.get("started") or time.time())
    _sense_scan_job_write(
        job_id,
        {
            "status": "running",
            "started": started,
            "result": None,
            "error": None,
        },
    )
    try:
        out = _execute_transcript_sense_scan(body)
        _sense_scan_job_write(
            job_id,
            {
                "status": "done",
                "started": started,
                "result": out,
                "error": None,
            },
        )
    except Exception as e:
        _sense_scan_job_write(
            job_id,
            {
                "status": "error",
                "started": started,
                "result": None,
                "error": str(e),
            },
        )


def _load_env() -> None:
    """Load agent-lab ``.env`` into ``os.environ`` (does not override existing vars)."""
    env_path = AGENT_LAB_ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv

        # interpolate=False: passwords and secrets often contain ``$``; do not expand as variables.
        load_dotenv(env_path, override=False, interpolate=False)
    except ImportError:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(
                        k.strip(), v.strip().strip('"').strip("'")
                    )


@auth.verify_password
def verify_password(username: str, password: str) -> bool:
    _load_env()
    expected = os.environ.get("DRAFT_EDITOR_PASSWORD", "")
    expected_user = os.environ.get("DRAFT_EDITOR_USER", "draft")
    return username == expected_user and password == expected and bool(expected)


# --- API ---

CONTEXT_PATH = AGENT_LAB_ROOT / "data" / "shiftshapr_context.json"


def _bride_project_dir() -> Path:
    root = (os.environ.get("BRIDE_PROJECT_ROOT") or "").strip()
    if root:
        return Path(root).expanduser().resolve()
    return (AGENT_LAB_ROOT / "projects" / "monuments" / "bride_of_charlie").resolve()


def _load_bride_transcript_overrides_module():
    script = _bride_project_dir() / "scripts" / "apply_transcript_overrides.py"
    if not script.is_file():
        return None, script
    spec = importlib.util.spec_from_file_location("bride_apply_transcript_overrides", script)
    if spec is None or spec.loader is None:
        return None, script
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, script


def _load_bride_transcript_media_module():
    script = _bride_project_dir() / "scripts" / "bride_transcript_media.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("bride_transcript_media", script)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_transcript_sense_scan_module():
    script = _bride_project_dir() / "scripts" / "transcript_sense_scan.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("transcript_sense_scan", script)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _default_publish_profiles() -> list[dict[str, Any]]:
    return [
        {"platform": "substack", "destination": "Substack · metaweb", "id": "substack_metaweb", "url": "https://metaweb.substack.com", "draft_location": "external", "draft_url": "https://metaweb.substack.com/publish/posts/drafts"},
        {"platform": "linkedin", "destination": "LinkedIn · Meta-Layer Initiative", "id": "linkedin_meta_layer"},
        {"platform": "linkedin", "destination": "LinkedIn · Daveed Benjamin (personal)", "id": "linkedin_personal"},
        {"platform": "x", "destination": "X · @shiftshapr", "id": "x_shiftshapr"},
        {"platform": "x", "destination": "X · @themetalayer (quote)", "id": "x_metalayer"},
    ]


@app.route("/api/profiles", methods=["GET"])
@auth.login_required
def list_profiles():
    """Return publish profiles (LinkedIn, X, WhatsApp hybrid, …) for the draft editor."""
    profiles: list[dict[str, Any]] = []
    if CONTEXT_PATH.exists():
        try:
            import json

            data = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
            profiles = list(data.get("publish_profiles") or [])
        except Exception:
            profiles = []
    if not profiles:
        profiles = _default_publish_profiles()
    if not any((p.get("platform") or "").lower() == "whatsapp" for p in profiles):
        profiles.append(
            {
                "platform": "whatsapp",
                "destination": "WhatsApp · hybrid (copy/paste)",
                "id": "whatsapp_hybrid",
            }
        )
    by_platform = {
        "substack": [p for p in profiles if p.get("platform") == "substack"],
        "linkedin": [p for p in profiles if p.get("platform") == "linkedin"],
        "x": [p for p in profiles if p.get("platform") == "x"],
        "whatsapp": [p for p in profiles if p.get("platform") == "whatsapp"],
    }
    return jsonify({"profiles": profiles, "by_platform": by_platform})


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
    meta = data.get("metadata") or {}
    dest = data.get("destination") or meta.get("destination", "")
    if dest:
        meta = {**meta, "destination": dest}
    if data.get("draft_location"):
        meta["draft_location"] = data["draft_location"]
    if data.get("draft_url"):
        meta["draft_url"] = data["draft_url"]
    draft = create_draft(
        content=data.get("content", ""),
        platform=data.get("platform", "linkedin"),
        metadata=meta,
        author=data.get("author", "agent"),
        destination=dest,
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
    from .store import update_draft, update_draft_metadata, merge_draft_metadata, get_draft
    data = request.get_json() or {}
    content = data.get("content")
    destination = data.get("destination")
    platform = data.get("platform")
    draft_location = data.get("draft_location")
    draft_url = data.get("draft_url")
    metadata_patch = data.get("metadata")

    if (
        content is None
        and destination is None
        and platform is None
        and draft_location is None
        and draft_url is None
        and metadata_patch is None
    ):
        return jsonify({"error": "Provide content, destination, platform, draft_location, draft_url, or metadata"}), 400

    draft = None
    if content is not None:
        draft = update_draft(draft_id, content, author="user", milestone=data.get("milestone"))
    else:
        draft = get_draft(draft_id)

    if draft and (destination is not None or platform is not None or draft_location is not None or draft_url is not None):
        draft = update_draft_metadata(
            draft_id,
            destination=destination,
            platform=platform,
            draft_location=draft_location,
            draft_url=draft_url,
        )

    if draft and metadata_patch is not None and isinstance(metadata_patch, dict):
        draft = merge_draft_metadata(draft_id, metadata_patch)

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

    # WhatsApp hybrid: no API publish — user copies from Draft Editor → WhatsApp tab
    if draft.get("platform") == "whatsapp":
        return jsonify(
            {
                "status": "whatsapp_hybrid",
                "message": "WhatsApp is manual: open the WhatsApp tab, copy the message, paste into your group or chat.",
            }
        )

    # Invoke publish agent via run-deerflow-task
    meta = draft.get("metadata", {})
    dest = meta.get("destination", "")
    # Resolve profile URL from shiftshapr_context
    profile_url = ""
    if CONTEXT_PATH.exists():
        try:
            import json
            ctx = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
            for p in ctx.get("publish_profiles", []):
                if p.get("destination") == dest:
                    profile_url = p.get("url", "")
                    break
        except Exception:
            pass
    # Substack external drafts: user publishes on Substack; we just open the URL
    draft_url = meta.get("draft_url", "")
    is_substack_external = draft.get("platform") == "substack" and meta.get("draft_location") == "external"
    if is_substack_external and draft_url:
        # Return a response that tells the frontend to open the URL (frontend handles this)
        return jsonify({
            "status": "open_external",
            "url": draft_url,
            "message": "Open Substack to complete publishing.",
        })

    scheduled_for = meta.get("scheduled_for", "")
    dest_line = f"\nPost to: {dest}" + (f" — navigate to {profile_url}" if profile_url else "")
    if draft_url:
        dest_line += f"\nDraft URL: {draft_url}"
    action = f"Schedule this post for {scheduled_for}" if scheduled_for else "Post this draft"
    schedule_instruction = (
        f"\n\nSCHEDULE for {scheduled_for}: Use the platform's scheduling UI (Substack: set schedule in editor; LinkedIn/X: click Schedule and pick date/time)."
        if scheduled_for
        else ""
    )
    prompt = f"""{action}.{dest_line}

Platform: {draft.get('platform', 'linkedin')}

Content:
{draft['content']}

Metadata: {meta}
Use Playwright MCP to post (or schedule) to the specified destination. Navigate to the URL if provided. Attach image if metadata has image path.{schedule_instruction}"""
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


@app.route("/api/drafts/<draft_id>/improve", methods=["POST"])
@auth.login_required
def improve_draft(draft_id: str):
    """Ask the agent to improve a specific aspect of the draft. Runs run-deerflow-task."""
    from .store import get_draft

    draft = get_draft(draft_id)
    if not draft:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json() or {}
    aspect = data.get("aspect", "opening").strip().lower()
    custom_instruction = (data.get("custom_instruction") or "").strip()

    aspect_labels = {
        "opening": "opening (story/scenario that draws the reader in)",
        "problem": "problem (what's broken, who's affected)",
        "solution": "solution (the proposed fix or feature)",
        "meta_layer": "meta-layer section (infrastructure, governance, coordination)",
        "cta": "CTA (call to action / invitation)",
        "custom": custom_instruction or "overall clarity and flow",
    }
    aspect_desc = aspect_labels.get(aspect, aspect_labels.get(aspect.replace(" ", "_"), aspect))

    prompt = f"""Improve the draft below. Focus ONLY on improving this aspect: **{aspect_desc}**

Draft ID: {draft_id}
Destination: {(draft.get('metadata') or {}).get('destination', '')}

Current content (HTML):
{draft.get('content', '')}

Instructions:
1. Parse the content above (convert HTML to structure if needed)
2. Rewrite the FULL draft, improving only the specified aspect — keep everything else intact
3. Use the update_draft tool with draft_id="{draft_id}", the full revised content in markdown format, and milestone="improved_{aspect}"
4. Do NOT create a new draft. Update the existing one only."""
    if custom_instruction and aspect == "custom":
        prompt += f"\n\nAdditional instruction: {custom_instruction}"

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
            return jsonify({"error": "Improve failed", "detail": (result.stderr or result.stdout or "")[:800]}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Improve timed out (agent took >5 min)"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    draft = get_draft(draft_id)
    return jsonify({"status": "improved", "draft": draft})


@app.route("/api/drafts/<draft_id>", methods=["DELETE"])
@auth.login_required
def delete_draft(draft_id: str):
    from .store import delete_draft
    if not delete_draft(draft_id):
        return jsonify({"error": "Not found"}), 404
    return jsonify({"status": "deleted"})


# --- Substack links (separate from drafts) ---

SUBSTACK_DRAFTS_URL = "https://metaweb.substack.com/publish/posts/drafts"
SUBSTACK_PUBLISHED_URL = "https://metaweb.substack.com/publish/posts"


@app.route("/api/substack-links", methods=["GET"])
@auth.login_required
def list_substack_links():
    from .substack_store import list_links
    return jsonify(list_links())


@app.route("/api/substack-links", methods=["POST"])
@auth.login_required
def add_substack_link():
    from .substack_store import add_link
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400
    entry = add_link(
        url=url,
        link_type=data.get("type", "draft"),
        title=data.get("title", ""),
    )
    return jsonify(entry), 201


@app.route("/api/substack-links/<link_id>", methods=["DELETE"])
@auth.login_required
def delete_substack_link(link_id: str):
    from .substack_store import delete_link
    if not delete_link(link_id):
        return jsonify({"error": "Not found"}), 404
    return jsonify({"status": "deleted"})


def _get_substack_publications() -> list[dict]:
    """Return substack_publications from context. Default to gometa + metaweb if missing."""
    if not CONTEXT_PATH.exists():
        return [
            {"id": "gometa", "name": "GoMeta", "domain": "gometa.substack.com"},
            {"id": "metaweb", "name": "Metaweb", "domain": "metaweb.substack.com"},
        ]
    try:
        import json
        data = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
        pubs = data.get("substack_publications", [])
        return pubs if pubs else [
            {"id": "gometa", "name": "GoMeta", "domain": "gometa.substack.com"},
            {"id": "metaweb", "name": "Metaweb", "domain": "metaweb.substack.com"},
        ]
    except Exception:
        return [{"id": "gometa", "name": "GoMeta", "domain": "gometa.substack.com"}]


@app.route("/api/substack-publications", methods=["GET"])
@auth.login_required
def substack_publications():
    """Return list of Substack publications to choose from."""
    return jsonify({"publications": _get_substack_publications()})


# --- Master calendar & work log (agents + Draft Editor) ---


def _calendar_embed_token_ok() -> bool:
    _load_env()
    expected = (os.environ.get("CALENDAR_EMBED_TOKEN") or "").strip()
    got = (request.args.get("token") or "").strip()
    return bool(expected) and got == expected


@app.route("/api/calendar", methods=["GET"])
@auth.login_required
def api_calendar_list():
    from .calendar_store import list_events

    df = request.args.get("from")
    dt = request.args.get("to")
    tag = (request.args.get("tag") or "").strip() or None
    return jsonify({"events": list_events(date_from=df, date_to=dt, tag=tag)})


@app.route("/api/calendar/events", methods=["POST"])
@auth.login_required
def api_calendar_create_event():
    from .calendar_store import add_event

    data = request.get_json() or {}
    if not data.get("title") or not data.get("starts_at"):
        return jsonify({"error": "title and starts_at required"}), 400
    ev = add_event(
        kind=data.get("kind", "alert"),
        title=data["title"],
        starts_at=data["starts_at"],
        ends_at=data.get("ends_at"),
        notes=data.get("notes", ""),
        draft_id=data.get("draft_id"),
        destination=data.get("destination"),
        alert_minutes_before=data.get("alert_minutes_before"),
        attachments=data.get("attachments"),
        tags=data.get("tags"),
        source=data.get("source", "user"),
    )
    return jsonify(ev), 201


@app.route("/api/calendar/events/<eid>", methods=["PUT"])
@auth.login_required
def api_calendar_update_event(eid: str):
    from .calendar_store import get_event, update_event

    if not get_event(eid):
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    allowed = (
        "kind",
        "title",
        "starts_at",
        "ends_at",
        "notes",
        "draft_id",
        "destination",
        "alert_minutes_before",
        "attachments",
        "tags",
    )
    fields = {k: data[k] for k in allowed if k in data}
    ev = update_event(eid, **fields)
    return jsonify(ev)


@app.route("/api/calendar/events/<eid>", methods=["DELETE"])
@auth.login_required
def api_calendar_delete_event(eid: str):
    from .calendar_store import delete_event

    if not delete_event(eid):
        return jsonify({"error": "Not found"}), 404
    return jsonify({"status": "deleted"})


@app.route("/api/calendar/sync-draft", methods=["POST"])
@auth.login_required
def api_calendar_sync_draft():
    from .calendar_store import sync_draft_schedule

    data = request.get_json() or {}
    draft_id = (data.get("draft_id") or "").strip()
    starts_at = (data.get("starts_at") or "").strip()
    title = (data.get("title") or "").strip() or None
    if not draft_id or not starts_at:
        return jsonify({"error": "draft_id and starts_at required"}), 400
    tags = data.get("tags")
    try:
        draft, ev = sync_draft_schedule(draft_id, starts_at, title=title, tags=tags)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"draft": draft, "event": ev})


@app.route("/api/calendar/public", methods=["GET"])
def api_calendar_public():
    """Read-only JSON for embed pages. Set CALENDAR_EMBED_TOKEN in .env; pass ?token=."""
    if not _calendar_embed_token_ok():
        return jsonify({"error": "unauthorized"}), 401
    from .calendar_store import list_events, load_calendar

    df = request.args.get("from")
    dt = request.args.get("to")
    tag = (request.args.get("tag") or "").strip() or None
    cal = load_calendar()
    return jsonify(
        {
            "events": list_events(date_from=df, date_to=dt, tag=tag),
            "updated_at": cal.get("updated_at"),
        }
    )


@app.route("/api/calendar/feed.ics", methods=["GET"])
def api_calendar_feed_ics():
    """Subscribe in Apple Calendar / Google Calendar for phone & watch reminders. ?token=CALENDAR_EMBED_TOKEN"""
    if not _calendar_embed_token_ok():
        return jsonify({"error": "unauthorized"}), 401
    from .calendar_store import events_to_ical, list_events

    df = request.args.get("from")
    dt = request.args.get("to")
    tag = (request.args.get("tag") or "").strip() or None
    events = list_events(date_from=df, date_to=dt, tag=tag)
    body = events_to_ical(events)
    return Response(
        body,
        mimetype="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="master_calendar.ics"'},
    )


@app.route("/api/work-log", methods=["GET"])
@auth.login_required
def api_work_log_get():
    from .calendar_store import list_work_log

    limit = int(request.args.get("limit", 100))
    return jsonify({"entries": list_work_log(limit=limit)})


@app.route("/api/work-log", methods=["POST"])
@auth.login_required
def api_work_log_post():
    from .calendar_store import add_work_log_entry

    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    attachments = data.get("attachments")
    if attachments is None:
        raw = (data.get("links_or_paths") or "").strip()
        if raw:
            attachments = [{"type": "url", "value": line.strip()} for line in raw.split("\n") if line.strip()]
    entry = add_work_log_entry(
        text=text,
        status=data.get("status", "note"),
        attachments=attachments or [],
        ingest=bool(data.get("ingest", True)),
        tags=data.get("tags") or [],
        source=data.get("source", "user"),
    )
    return jsonify(entry), 201


@app.route("/api/substack-fetch", methods=["GET"])
@auth.login_required
def substack_fetch():
    """Return cached data for a publication. ?publication=X&refresh=1 spawns async merge."""
    import threading
    from .substack_cache import load
    from .substack_fetch import run_refresh_background

    publications = _get_substack_publications()
    pub_id = request.args.get("publication", "gometa")
    pub = next((p for p in publications if p.get("id") == pub_id), publications[0] if publications else None)
    if not pub:
        return jsonify({"error": "Unknown publication", "drafts": [], "published": []}), 400

    pub_id = pub["id"]
    domain = pub["domain"]
    data = load(pub_id)
    out = {
        "publication": pub,
        "drafts": data["drafts"],
        "scheduled": data.get("scheduled", []),
        "published": data["published"],
        "refreshing": data.get("refreshing", False),
        "updated_at": data.get("updated_at"),
    }
    if request.args.get("refresh"):
        if not data.get("refreshing"):
            threading.Thread(target=run_refresh_background, args=(pub_id, domain), daemon=True).start()
    return jsonify(out)


# --- Replies (Substack comments → draft responses) ---


# --- Bride of Charlie: transcript override queue (STT / scholarly fixes) ---


@app.route("/api/bride/transcript-overrides", methods=["GET"])
@auth.login_required
def bride_transcript_overrides_list():
    mod, script = _load_bride_transcript_overrides_module()
    if mod is None:
        return jsonify({"error": "Bride scripts not found", "path": str(script)}), 404
    data = mod.load_store()
    proj = _bride_project_dir()
    return jsonify(
        {
            "project_dir": str(proj),
            "store_path": str(getattr(mod, "DEFAULT_STORE", proj / "config" / "transcript_overrides.json")),
            "version": data.get("version", 1),
            "description": data.get("description", ""),
            "items": data.get("items", []),
        }
    )


@app.route("/api/bride/transcript-overrides", methods=["POST"])
@auth.login_required
def bride_transcript_overrides_create():
    mod, script = _load_bride_transcript_overrides_module()
    if mod is None:
        return jsonify({"error": "Bride scripts not found", "path": str(script)}), 404
    body = request.get_json() or {}
    body.setdefault("status", "proposed")
    item, err = mod.validate_item_body(body)
    if err:
        return jsonify({"error": err}), 400
    data = mod.upsert_item(None, item)
    return jsonify({"ok": True, "items": data.get("items", []), "item": item}), 201


@app.route("/api/bride/transcript-overrides/propose-from-scan", methods=["POST"])
@auth.login_required
def bride_transcript_overrides_propose_from_scan():
    """
    Bulk-create proposed overrides from heuristic or LLM scan rows (Draft Editor).
    Body: { "episode": int, "source": "heuristic"|"llm"|str, "items": [ { "find", "replace", "note"? } ], "dedupe"?: bool }
    """
    mod, script = _load_bride_transcript_overrides_module()
    if mod is None:
        return jsonify({"error": "Bride scripts not found", "path": str(script)}), 404
    if not hasattr(mod, "bulk_propose_items"):
        return jsonify({"error": "bulk_propose_items not available; update apply_transcript_overrides.py"}), 500
    body = request.get_json(silent=True) or {}
    try:
        ep = int(body.get("episode"))
    except (TypeError, ValueError):
        return jsonify({"error": "body.episode required (integer)"}), 400
    if ep < 1:
        return jsonify({"error": "episode must be ≥ 1"}), 400
    source = (body.get("source") or "scan").strip()
    raw_items = body.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        return jsonify({"error": "body.items must be a non-empty array"}), 400
    dedupe = body.get("dedupe", True)
    if isinstance(dedupe, str):
        dedupe = dedupe.strip().lower() in ("1", "true", "yes")

    prefix = f"[{source}] "
    normalized: list[dict[str, Any]] = []
    for it in raw_items:
        if not isinstance(it, dict):
            continue
        find = (it.get("find") or "").strip()
        if not find:
            continue
        replace = it.get("replace")
        if replace is None:
            replace = ""
        if not isinstance(replace, str):
            replace = str(replace)
        note = (it.get("note") or "").strip()
        note = prefix + note if note else prefix.rstrip()
        entry: dict[str, Any] = {
            "episode": ep,
            "find": find,
            "replace": replace,
            "note": note,
            "match_mode": (it.get("match_mode") or "literal").strip().lower(),
        }
        if it.get("tiers") is not None:
            entry["tiers"] = it.get("tiers")
        if it.get("flags") is not None:
            entry["flags"] = it.get("flags")
        if it.get("priority") is not None:
            try:
                entry["priority"] = int(it.get("priority"))
            except (TypeError, ValueError):
                pass
        if it.get("max_replacements") is not None:
            try:
                entry["max_replacements"] = int(it.get("max_replacements"))
            except (TypeError, ValueError):
                pass
        normalized.append(entry)

    if not normalized:
        return jsonify({"error": "no valid items (each needs non-empty find)"}), 400

    result = mod.bulk_propose_items(normalized, dedupe=bool(dedupe))
    return jsonify(result), 201


@app.route("/api/bride/transcript-overrides/<item_id>", methods=["PUT"])
@auth.login_required
def bride_transcript_overrides_update(item_id: str):
    mod, script = _load_bride_transcript_overrides_module()
    if mod is None:
        return jsonify({"error": "Bride scripts not found", "path": str(script)}), 404
    data = mod.load_store()
    old = next((x for x in (data.get("items") or []) if x.get("id") == item_id), None)
    if not old:
        return jsonify({"error": "Not found"}), 404
    patch = request.get_json() or {}
    merged = {**old, **patch, "id": item_id}
    item, err = mod.validate_item_body(merged)
    if err:
        return jsonify({"error": err}), 400
    data = mod.upsert_item(None, item)
    return jsonify({"ok": True, "items": data.get("items", []), "item": item})


@app.route("/api/bride/transcript-overrides/<item_id>", methods=["DELETE"])
@auth.login_required
def bride_transcript_overrides_delete(item_id: str):
    mod, script = _load_bride_transcript_overrides_module()
    if mod is None:
        return jsonify({"error": "Bride scripts not found", "path": str(script)}), 404
    if not mod.delete_item(item_id, None):
        return jsonify({"error": "Not found"}), 404
    data = mod.load_store()
    return jsonify({"ok": True, "items": data.get("items", [])})


@app.route("/api/bride/transcript-overrides/<item_id>/preview", methods=["GET"])
@auth.login_required
def bride_transcript_overrides_preview(item_id: str):
    mod, script = _load_bride_transcript_overrides_module()
    if mod is None:
        return jsonify({"error": "Bride scripts not found", "path": str(script)}), 404
    data = mod.load_store()
    item = next((x for x in (data.get("items") or []) if x.get("id") == item_id), None)
    if not item:
        return jsonify({"error": "Not found"}), 404
    prev = mod.preview_item(_bride_project_dir(), item) or {}
    media_mod = _load_bride_transcript_media_module()
    if media_mod is not None and item.get("episode") is not None:
        try:
            prev = media_mod.enrich_preview(_bride_project_dir(), int(item["episode"]), prev)
        except Exception as e:
            prev["_enrich_error"] = str(e)
    return jsonify({"preview": prev})


@app.route("/api/bride/transcript-scan", methods=["GET"])
@auth.login_required
def bride_transcript_scan():
    """Scan inscription transcript for suspicious patterns; include YouTube deep links per hit."""
    ep = request.args.get("episode", type=int)
    if ep is None or ep < 1:
        return jsonify({"error": "episode query param required (integer ≥ 1)"}), 400
    media_mod = _load_bride_transcript_media_module()
    if media_mod is None:
        return jsonify({"error": "bride_transcript_media.py not found"}), 404
    try:
        result = media_mod.scan_episode_inscription(ep, _bride_project_dir())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(result)


@app.route("/api/bride/transcript-sense-scan", methods=["POST"])
@auth.login_required
def bride_transcript_sense_scan():
    """
    LLM pass: flag transcript stretches that read like garbled STT / nonsense.

    Default: **202** + ``job_id`` — run scan in a background thread (avoids Cloudflare **524**
    when the scan exceeds ~100s). Poll ``GET …/job/<job_id>`` until ``status`` is ``done``.

    Sync (localhost / tests only): ``POST ?sync=1`` or env ``DRAFT_EDITOR_SENSE_SCAN_SYNC=1``.
    """
    body = request.get_json(silent=True) or {}
    ep = body.get("episode")
    try:
        ep_int = int(ep)
    except (TypeError, ValueError):
        return jsonify({"error": "body.episode required (integer ≥ 1)"}), 400
    if ep_int < 1:
        return jsonify({"error": "episode must be ≥ 1"}), 400

    if _load_transcript_sense_scan_module() is None:
        return jsonify({"error": "transcript_sense_scan.py not found"}), 404

    sync = request.args.get("sync") == "1" or os.environ.get(
        "DRAFT_EDITOR_SENSE_SCAN_SYNC", ""
    ).strip().lower() in ("1", "true", "yes")

    if sync:
        try:
            result = _execute_transcript_sense_scan(body)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        return jsonify(result)

    _prune_sense_scan_jobs()
    job_id = uuid.uuid4().hex[:12]
    _sense_scan_job_write(
        job_id,
        {
            "status": "queued",
            "started": time.time(),
            "result": None,
            "error": None,
        },
    )
    body_copy = dict(body)
    threading.Thread(
        target=_sense_scan_worker,
        args=(job_id, body_copy),
        daemon=True,
    ).start()
    return jsonify({"job_id": job_id, "status": "queued"}), 202


@app.route("/api/bride/transcript-sense-scan/job/<job_id>", methods=["GET"])
@auth.login_required
def bride_transcript_sense_scan_job(job_id: str):
    """Poll async sense-scan job started by POST ``/api/bride/transcript-sense-scan``."""
    try:
        _prune_sense_scan_jobs()
        job = _sense_scan_job_read(job_id)
        if not job:
            return jsonify({"error": "unknown or expired job_id"}), 404
        out: dict[str, Any] = {
            "job_id": job_id,
            "status": job.get("status"),
        }
        if job.get("status") == "done" and job.get("result") is not None:
            out["result"] = job["result"]
        if job.get("status") == "error":
            out["error"] = job.get("error", "job failed")
        return jsonify(out)
    except Exception as e:
        app.logger.exception("transcript-sense-scan job poll failed job_id=%s", job_id)
        return jsonify({"error": "job poll failed", "detail": str(e)}), 500


_HUB_EDITABLE_SUFFIXES = frozenset({".txt", ".md", ".json", ".yaml", ".yml"})


def _bride_hub_activate_worker(job_id: str, youtube_url: str) -> None:
    _bride_hub.activate_worker(job_id, youtube_url, _bride_project_dir(), AGENT_LAB_ROOT)


@app.route("/api/bride/hub/index", methods=["GET"])
@auth.login_required
def bride_hub_index():
    """Cached Bride hub index (episodes, file_ids, global entity ids). ?rebuild=1 forces refresh."""
    force = request.args.get("rebuild") == "1"
    bride = _bride_project_dir()
    try:
        doc = _bride_hub.get_or_build_index(bride, AGENT_LAB_ROOT, force=force)
        return jsonify(doc)
    except Exception as e:
        app.logger.exception("bride hub index failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/bride/hub/entity-detail", methods=["GET"])
@auth.login_required
def bride_hub_entity_detail():
    """JSON for one node / claim / artifact (inscription lookup + YouTube embed URLs)."""
    eid = (request.args.get("id") or request.args.get("entity_id") or "").strip()
    if not eid:
        return jsonify({"found": False, "error": "id query parameter required"}), 400
    ep_raw = (request.args.get("episode") or "").strip()
    episode_hint: int | None = None
    if ep_raw.isdigit():
        episode_hint = int(ep_raw)
    bride = _bride_project_dir()
    try:
        out = _bride_hub.resolve_entity_detail(
            bride, AGENT_LAB_ROOT, eid, episode_hint=episode_hint
        )
    except Exception as e:
        app.logger.exception("bride hub entity-detail failed id=%s", eid)
        return jsonify({"found": False, "error": str(e)}), 500
    if not out.get("found"):
        return jsonify(out), 404
    return jsonify(out)


@app.route("/api/bride/hub/episodes", methods=["GET"])
@auth.login_required
def bride_hub_episodes():
    """Episode numbers for UI dropdowns (same rules as hub index — not a hardcoded 1..20)."""
    bride = _bride_project_dir()
    try:
        if not bride.is_dir():
            # 503 (not 404): route exists; deployment is missing monument checkout under AGENT_LAB_ROOT.
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "bride project not found",
                        "episodes": [],
                        "hint": str(bride.resolve()),
                    }
                ),
                503,
            )
        nums = _bride_hub.episode_numbers_for_ui(bride)
        return jsonify({"ok": True, "episodes": nums, "count": len(nums)})
    except Exception as e:
        app.logger.exception("bride hub episodes failed")
        return jsonify({"ok": False, "error": str(e), "episodes": []}), 500


@app.route("/api/bride/hub/health", methods=["GET"])
@auth.login_required
def bride_hub_health():
    """Lightweight hub status (no full index build)."""
    bride = _bride_project_dir()
    try:
        exists = bride.is_dir()
        fp = _bride_hub.compute_fingerprint(bride) if exists else None
        ip = _bride_hub.index_path(AGENT_LAB_ROOT)
        cache_age = None
        if ip.is_file():
            cache_age = time.time() - ip.stat().st_mtime
        return jsonify(
            {
                "ok": exists,
                "bride_project": str(bride.resolve()),
                "fingerprint": fp,
                "index_cache_exists": ip.is_file(),
                "index_cache_age_sec": round(cache_age, 3) if cache_age is not None else None,
            }
        )
    except Exception as e:
        app.logger.exception("bride hub health failed")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/bride/hub/validate-node-claims", methods=["GET"])
@auth.login_required
def bride_hub_validate_node_claims():
    """
    Cross-check ``nodes[].related_claims`` vs ``claims[].related_nodes`` per inscription file.

    Query: ``include_backlinks=0`` to omit reverse-edge warnings (claim lists node but node omits claim).
    """
    bride = _bride_project_dir()
    try:
        if not bride.is_dir():
            return jsonify({"ok": False, "error": "bride project not found"}), 404
        include_backlinks = request.args.get("include_backlinks", "1") != "0"
        out = _bride_hub.screen_node_claim_consistency(bride, include_backlinks=include_backlinks)
        return jsonify(out)
    except Exception as e:
        app.logger.exception("bride hub validate-node-claims failed")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/bride/hub/neo4j", methods=["GET"])
@auth.login_required
def bride_hub_neo4j():
    """Read-only Neo4j stats (and optional integrity checks). ?validate=1 runs validation queries."""
    _load_env()
    validate = request.args.get("validate") == "1"
    bride = _bride_project_dir()
    try:
        summary = _bride_neo4j_hub.fetch_neo4j_summary(bride, validate=validate)
        return jsonify(summary)
    except Exception as e:
        app.logger.exception("bride hub neo4j failed")
        return jsonify({"available": False, "error": str(e), "stats": {}}), 500


@app.route("/api/bride/hub/run-status", methods=["GET"])
@auth.login_required
def bride_hub_run_status():
    """Workflow log tail, suggestions, last run — for dashboard polling (?skip_validate=1 for lighter checks)."""
    _load_env()
    bride = _bride_project_dir()
    skip_v = request.args.get("skip_validate") == "1"
    neo_sum = _bride_neo4j_hub.fetch_neo4j_summary(bride, validate=False)
    neo_ok = bool(neo_sum.get("available"))
    try:
        payload = _bride_run_ops.build_run_status_json(
            AGENT_LAB_ROOT,
            bride,
            neo_available=neo_ok,
            skip_validate=skip_v,
        )
        return jsonify(payload)
    except Exception as e:
        app.logger.exception("bride hub run-status failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/bride/hub/workflow/run", methods=["POST"])
@auth.login_required
def bride_hub_workflow_run():
    """Start run_full_workflow.py in the background (same flags as bride_run_ops)."""
    _load_env()
    bride = _bride_project_dir()
    if not bride.is_dir():
        return jsonify({"error": "bride project not found"}), 404
    body = request.get_json(silent=True) or {}
    opts: dict[str, Any] = {
        "skip_fetch": bool(body.get("skip_fetch")),
        "editorial_pass": bool(body.get("editorial_pass")),
        "dual_transcripts": bool(body.get("dual_transcripts")),
        "display_clean": bool(body.get("display_clean")),
        "stop_after_green_validate": bool(body.get("stop_after_green_validate")),
        "no_backup": bool(body.get("no_backup")),
        "skip_search": bool(body.get("skip_search")),
    }
    sa = body.get("stop_after")
    if sa is not None and sa != "":
        try:
            opts["stop_after"] = int(sa)
        except (TypeError, ValueError):
            pass
    mp = body.get("max_passes")
    if mp is not None and mp != "":
        try:
            opts["max_passes"] = int(mp)
        except (TypeError, ValueError):
            pass
    try:
        job_id, log_path = _bride_run_ops.start_workflow_background(
            AGENT_LAB_ROOT, bride, opts
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        app.logger.exception("bride workflow run failed")
        return jsonify({"error": str(e)}), 500
    return jsonify(
        {
            "job_id": job_id,
            "log": str(log_path.relative_to(AGENT_LAB_ROOT)),
            "status": "started",
        }
    )


@app.route("/api/bride/hub/workflow/job/<job_id>", methods=["GET"])
@auth.login_required
def bride_hub_workflow_job(job_id: str):
    """Poll a workflow or Neo4j ingest job started from the dashboard."""
    try:
        detail = _bride_run_ops.read_workflow_job_detail(AGENT_LAB_ROOT, job_id)
        if not detail:
            return jsonify({"error": "unknown job_id"}), 404
        return jsonify(detail)
    except Exception as e:
        app.logger.exception("bride workflow job poll failed job_id=%s", job_id)
        return jsonify({"error": str(e)}), 500


@app.route("/api/bride/hub/neo4j-ingest", methods=["POST"])
@auth.login_required
def bride_hub_neo4j_ingest():
    """Run neo4j_ingest.py --force in the background (graph refresh after draft edits)."""
    _load_env()
    bride = _bride_project_dir()
    if not bride.is_dir():
        return jsonify({"error": "bride project not found"}), 404
    try:
        job_id, log_path = _bride_run_ops.start_neo4j_ingest_background(
            AGENT_LAB_ROOT, bride
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        app.logger.exception("bride neo4j ingest start failed")
        return jsonify({"error": str(e)}), 500
    return jsonify(
        {
            "job_id": job_id,
            "log": str(log_path.relative_to(AGENT_LAB_ROOT)),
            "status": "started",
        }
    )


@app.route("/api/bride/hub/activate", methods=["POST"])
@auth.login_required
def bride_hub_activate():
    """Append episode URL, update registry, fetch transcript + build corrected (async). Returns 202 + job_id."""
    body = request.get_json(silent=True) or {}
    url = (body.get("youtube_url") or body.get("url") or "").strip()
    if not url:
        return jsonify({"error": "youtube_url required"}), 400
    bride = _bride_project_dir()
    vid = _bride_hub.parse_video_id_from_url(url)
    if not vid:
        return jsonify({"error": "could not parse YouTube video id from URL"}), 400
    allow_dup = body.get("allow_duplicate") in (True, 1, "1", "true", "yes")
    dup_ep = _bride_hub.find_existing_episode_for_video_id(bride, vid)
    if dup_ep is not None and not allow_dup:
        return jsonify(
            {
                "error": "video_id already registered",
                "video_id": vid,
                "episode": dup_ep,
            }
        ), 409
    _bride_hub.prune_activate_jobs(AGENT_LAB_ROOT)
    job_id = uuid.uuid4().hex[:12]
    _bride_hub.activate_job_write(
        AGENT_LAB_ROOT,
        job_id,
        {
            "status": "queued",
            "stage": "queued",
            "started": time.time(),
            "result": None,
            "error": None,
        },
    )
    threading.Thread(
        target=_bride_hub_activate_worker,
        args=(job_id, url),
        daemon=True,
    ).start()
    return jsonify({"job_id": job_id, "status": "queued"}), 202


@app.route("/api/bride/hub/activate/job/<job_id>", methods=["GET"])
@auth.login_required
def bride_hub_activate_job(job_id: str):
    try:
        _bride_hub.prune_activate_jobs(AGENT_LAB_ROOT)
        job = _bride_hub.activate_job_read(AGENT_LAB_ROOT, job_id)
        if not job:
            return jsonify({"error": "unknown or expired job_id"}), 404
        out: dict[str, Any] = {
            "job_id": job_id,
            "status": job.get("status"),
            "stage": job.get("stage"),
        }
        if job.get("episode") is not None:
            out["episode"] = job["episode"]
        if job.get("youtube_url"):
            out["youtube_url"] = job["youtube_url"]
        if job.get("video_id"):
            out["video_id"] = job["video_id"]
        if job.get("fetch"):
            out["fetch"] = job["fetch"]
        if job.get("status") == "done" and job.get("result") is not None:
            out["result"] = job["result"]
        if job.get("status") == "error":
            out["error"] = job.get("error", "job failed")
        return jsonify(out)
    except Exception as e:
        app.logger.exception("bride hub activate job poll failed job_id=%s", job_id)
        return jsonify({"error": "job poll failed", "detail": str(e)}), 500


@app.route("/api/bride/hub/file/<file_id>", methods=["GET"])
@auth.login_required
def bride_hub_file_get(file_id: str):
    fid = re.sub(r"[^a-fA-F0-9]", "", file_id or "")
    if len(fid) != 16:
        return jsonify({"error": "invalid file_id"}), 400
    bride = _bride_project_dir()
    p, rel = _bride_hub.resolve_file_id(fid, bride, AGENT_LAB_ROOT)
    if not rel or p is None:
        return jsonify({"error": "unknown file_id"}), 404
    if not p.is_file():
        return jsonify({"error": "file missing on disk", "path": rel}), 404
    if p.suffix.lower() not in _HUB_EDITABLE_SUFFIXES:
        return jsonify({"error": "file type not editable in hub"}), 415
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return jsonify({"error": str(e)}), 500
    etag = _bride_hub.etag_for_path(p)
    resp = jsonify({"path": rel, "content": content})
    if etag:
        resp.headers["ETag"] = etag
    return resp


@app.route("/api/bride/hub/file/<file_id>", methods=["PUT"])
@auth.login_required
def bride_hub_file_put(file_id: str):
    fid = re.sub(r"[^a-fA-F0-9]", "", file_id or "")
    if len(fid) != 16:
        return jsonify({"error": "invalid file_id"}), 400
    bride = _bride_project_dir()
    p, rel = _bride_hub.resolve_file_id(fid, bride, AGENT_LAB_ROOT)
    if not rel or p is None:
        return jsonify({"error": "unknown file_id"}), 404
    if p.suffix.lower() not in _HUB_EDITABLE_SUFFIXES:
        return jsonify({"error": "file type not editable in hub"}), 415
    if_match = request.headers.get("If-Match")
    cur_etag = _bride_hub.etag_for_path(p)
    if p.is_file():
        if not if_match:
            return jsonify({"error": "If-Match header required for existing file"}), 428
        if cur_etag and if_match != cur_etag:
            return jsonify({"error": "precondition failed", "path": rel}), 412
    body = request.get_json(silent=True) or {}
    if "content" not in body or not isinstance(body["content"], str):
        return jsonify({"error": "body.content (string) required"}), 400
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(body["content"], encoding="utf-8")
        tmp.replace(p)
    except OSError as e:
        return jsonify({"error": str(e)}), 500
    new_etag = _bride_hub.etag_for_path(p)
    _bride_hub.invalidate_index_cache(AGENT_LAB_ROOT)
    resp = jsonify({"ok": True, "path": rel})
    if new_etag:
        resp.headers["ETag"] = new_etag
    return resp


@app.route("/api/bride/hub/episode/<int:ep>/transcript-diff", methods=["GET"])
@auth.login_required
def bride_hub_transcript_diff(ep: int):
    """Unified diff raw vs enhanced transcript. ?normalize=1 (Unicode NFC), ?context=N (default 3)."""
    normalize = request.args.get("normalize") == "1"
    ctx = request.args.get("context", type=int)
    if ctx is None:
        ctx = 3
    bride = _bride_project_dir()
    out = _bride_hub.transcript_diff_for_episode(
        bride, ep, normalize=normalize, context_lines=ctx
    )
    if out.get("error"):
        return jsonify(out), 404
    fmt = (request.args.get("format") or "").strip().lower()
    if fmt in ("text", "txt", "plain"):
        body = (out.get("unified_diff") or "") + "\n"
        if out.get("truncated"):
            body += "\n# [truncated by server]\n"
        return Response(
            body,
            mimetype="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="episode_{ep:03d}_transcript.diff.txt"'
                )
            },
        )
    return jsonify(out)


_BRIDE_DASH_FILE_ORDER = (
    "raw_transcript",
    "enhanced_transcript",
    "inscription",
    "phase1_output",
    "draft_markdown",
    "suspicious_patterns",
    "editorial_transcript_rules",
)
_BRIDE_DASH_LABELS = {
    "raw_transcript": "Raw transcript",
    "enhanced_transcript": "Enhanced transcript",
    "inscription": "Inscription JSON",
    "phase1_output": "Phase-1 output",
    "draft_markdown": "Draft markdown",
    "suspicious_patterns": "Suspicious patterns",
    "editorial_transcript_rules": "Editorial rules",
}


def _dash_related_cell(row: dict[str, Any]) -> str:
    """Counts + cross-link buttons for related nodes / claims / artifacts."""
    rc = row.get("related_counts") or {}
    rel = row.get("related") or {}
    try:
        nn = int(rc.get("nodes") or 0)
        nc = int(rc.get("claims") or 0)
        na = int(rc.get("artifacts") or 0)
    except (TypeError, ValueError):
        nn = nc = na = 0
    badges: list[str] = []
    if nn:
        badges.append(f'<span class="badge">N ×{nn}</span>')
    if nc:
        badges.append(f'<span class="badge">C ×{nc}</span>')
    if na:
        badges.append(f'<span class="badge">A ×{na}</span>')
    counts = (
        '<div class="rel-counts">' + " ".join(badges) + "</div>" if badges else ""
    )
    raw_ep = str(row.get("episode") or "")
    ep_attr = html.escape(raw_ep, quote=True)
    mini: list[str] = []
    for rid in rel.get("nodes") or []:
        mini.append(
            '<button type="button" class="rel-mini" data-boc-entity="'
            f'{html.escape(str(rid), quote=True)}" data-boc-episode="{ep_attr}">'
            f"{html.escape(str(rid))}</button>"
        )
    for rid in rel.get("claims") or []:
        mini.append(
            '<button type="button" class="rel-mini" data-boc-entity="'
            f'{html.escape(str(rid), quote=True)}" data-boc-episode="{ep_attr}">'
            f"{html.escape(str(rid))}</button>"
        )
    for rid in rel.get("artifacts") or []:
        mini.append(
            '<button type="button" class="rel-mini" data-boc-entity="'
            f'{html.escape(str(rid), quote=True)}" data-boc-episode="{ep_attr}">'
            f"{html.escape(str(rid))}</button>"
        )
    preview = (
        '<div class="rel-mini-wrap">' + "".join(mini) + "</div>" if mini else ""
    )
    return f'<td class="rel-cell">{counts}{preview}</td>'


def _dash_global_entity_section(
    rows: list[dict[str, Any]],
    section_id: str,
    title: str,
    description: str,
) -> str:
    """HTML block: full global nodes / claims / artifacts table (from hub index)."""
    sid = html.escape(section_id, quote=True)
    if not rows:
        return (
            f'<section id="{sid}" class="card entity-roll">'
            f"<h2>{html.escape(title)}</h2>"
            f'<p class="entity-desc muted">{html.escape(description)} '
            f"<em>None in index.</em></p></section>"
        )

    trs: list[str] = []
    for r in sorted(rows, key=_bride_hub.global_row_sort_key):
        eid = html.escape(str(r.get("id") or ""))
        ep = html.escape(str(r.get("episode") or ""))
        tit = html.escape(str(r.get("title") or r.get("id") or ""))
        sub = r.get("subtitle")
        subt = (
            f'<div class="subtit">{html.escape(str(sub))}</div>'
            if sub
            else ""
        )
        kind = r.get("entity_kind")
        kind_b = (
            f'<span class="kind-pill">{html.escape(str(kind))}</span>'
            if kind
            else ""
        )
        raw_id = str(r.get("id") or "")
        raw_ep = str(r.get("episode") or "")
        eid_attr = html.escape(raw_id, quote=True)
        ep_attr = html.escape(raw_ep, quote=True)
        detail_btn = (
            f'<button type="button" class="boc-detail-btn" '
            f'data-boc-entity="{eid_attr}" data-boc-episode="{ep_attr}">Detail</button>'
        )
        trs.append(
            "<tr>"
            f"<td><code>{eid}</code></td>"
            f'<td class="num">{ep}</td>'
            f'<td class="title-cell"><div class="tit">{kind_b}{tit}</div>{subt}</td>'
            f"{_dash_related_cell(r)}"
            f"<td>{detail_btn}</td>"
            "</tr>"
        )
    tbody = "\n".join(trs)
    return (
        f'<section id="{sid}" class="card entity-roll">'
        f"<h2>{html.escape(title)}</h2>"
        f'<p class="entity-desc muted">{html.escape(description)}</p>'
        '<div class="table-wrap">'
        '<table class="entity-table">'
        "<thead><tr><th>ID</th><th>Ep</th><th>Title</th><th>Related</th>"
        "<th>Explore</th></tr></thead>"
        "<tbody>\n"
        f"{tbody}\n"
        "</tbody></table></div></section>"
    )


def _bride_dashboard_entity_modal_block() -> str:
    """Native <dialog> + JS for entity detail, YouTube embed, cross-links (no external deps)."""
    return r"""
<style>
  dialog#boc-entity-dialog {
    max-width: 720px; width: 92vw; max-height: 90vh; overflow: auto;
    border: 1px solid #27272f; border-radius: 12px; padding: 0;
    background: #141418; color: #e4e4e7; font-family: system-ui, sans-serif;
  }
  dialog#boc-entity-dialog::backdrop { background: rgba(0,0,0,0.72); }
  .boc-dlg-head {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.75rem 1rem; border-bottom: 1px solid #27272f; position: sticky; top: 0; background: #141418;
  }
  .boc-dlg-head h3 { margin: 0; font-size: 1.05rem; }
  .boc-dlg-head .kind { color: #71717a; font-weight: 400; font-size: 0.85rem; margin-left: 0.35rem; }
  #boc-modal-close {
    border: none; background: transparent; color: #a1a1aa; font-size: 1.5rem;
    line-height: 1; cursor: pointer; padding: 0 0.25rem;
  }
  #boc-modal-close:hover { color: #e4e4e7; }
  #boc-modal-body { padding: 1rem; font-size: 0.9rem; }
  #boc-modal-body pre.snip {
    white-space: pre-wrap; background: #0c0c0f; border: 1px solid #27272f;
    border-radius: 8px; padding: 0.75rem; font-size: 0.85rem; color: #d4d4d8;
  }
  #boc-modal-body .vid-wrap {
    position: relative; padding-bottom: 56.25%; height: 0; margin: 0.75rem 0;
    border-radius: 8px; overflow: hidden; border: 1px solid #27272f;
  }
  #boc-modal-body .vid-wrap iframe {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;
  }
  #boc-modal-body .rel-btns { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.35rem 0 0.75rem; }
  #boc-modal-body .rel-btn {
    border: 1px solid #3f3f46; background: #27272f; color: #7dd3fc;
    border-radius: 6px; padding: 0.2rem 0.5rem; font-size: 0.8rem; cursor: pointer;
  }
  #boc-modal-body .rel-btn:hover { background: #3f3f46; }
  #boc-modal-body h4 { margin: 0.75rem 0 0.25rem; font-size: 0.8rem; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.04em; }
  #boc-modal-body .aux, #boc-modal-body .muted { color: #71717a; font-size: 0.8rem; }
  #boc-modal-body .claim-text { line-height: 1.45; }
  #boc-modal-loading { color: #71717a; }
</style>
<dialog id="boc-entity-dialog" aria-labelledby="boc-dlg-title">
  <div class="boc-dlg-head">
    <h3 id="boc-dlg-title">Entity</h3>
    <button type="button" id="boc-modal-close" aria-label="Close">&times;</button>
  </div>
  <div id="boc-modal-body"><p id="boc-modal-loading" class="boc-modal-loading">Loading…</p></div>
</dialog>
<script>
(function () {
  function escapeHtml(t) {
    if (t == null) return "";
    var d = document.createElement("div");
    d.textContent = String(t);
    return d.innerHTML;
  }
  function relGroup(title, ids) {
    if (!ids || !ids.length) return "";
    var b = "<h4>" + escapeHtml(title) + "</h4><div class=\"rel-btns\">";
    for (var i = 0; i < ids.length; i++) {
      var id = ids[i];
      b += "<button type=\"button\" class=\"rel-btn\" data-boc-entity=\"" + escapeHtml(id) + "\">"
        + escapeHtml(id) + "</button>";
    }
    b += "</div>";
    return b;
  }
  function recordSummary(j) {
    var rec = j.record || {};
    if (j.kind === "claim") {
      var h = "";
      if (rec.label) h += "<p><strong>" + escapeHtml(rec.label) + "</strong></p>";
      if (rec.claim) h += "<p class=\"claim-text\">" + escapeHtml(rec.claim) + "</p>";
      return h;
    }
    if (j.kind === "node") {
      var nh = "";
      if (rec.name) nh += "<p><strong>" + escapeHtml(rec.name) + "</strong></p>";
      if (rec.description) nh += "<p class=\"muted\">" + escapeHtml(rec.description) + "</p>";
      return nh;
    }
    if (j.kind === "artifact") {
      return rec.description ? "<p>" + escapeHtml(rec.description) + "</p>" : "";
    }
    if (j.kind === "artifact_family") {
      var subs = [];
      (rec.sub_items || []).forEach(function (s) {
        var sid = s["@id"] || s.ref;
        if (sid) subs.push(String(sid));
      });
      var out = rec.bundle_name ? "<p>" + escapeHtml(rec.bundle_name) + "</p>" : "";
      if (subs.length) {
        out += "<p class=\"muted\">Sub-items: " + subs.map(escapeHtml).join(", ") + "</p>";
      }
      return out;
    }
    if (j.kind === "meme") {
      var mh = "";
      if (rec.canonical_term) {
        mh += "<p><strong>" + escapeHtml(rec.canonical_term) + "</strong></p>";
      }
      if (rec.type) {
        mh += "<p class=\"muted\">Type: " + escapeHtml(rec.type) + "</p>";
      }
      var epAttr = escapeHtml(String(j.episode != null ? j.episode : ""));
      (rec.occurrences || []).forEach(function (oc, ix) {
        mh += "<h4>Occurrence " + (ix + 1) + "</h4>";
        if (oc.video_timestamp) {
          mh += "<p class=\"muted\">Video: " + escapeHtml(String(oc.video_timestamp)) + "</p>";
        }
        if (oc.quote) {
          mh += "<pre class=\"snip\">" + escapeHtml(String(oc.quote)) + "</pre>";
        }
        if (oc.context) {
          mh += "<p class=\"aux\">" + escapeHtml(String(oc.context)) + "</p>";
        }
        if (oc.speaker_node_ref) {
          var sp = String(oc.speaker_node_ref);
          mh += "<p class=\"aux\">Speaker: <button type=\"button\" class=\"rel-mini\" data-boc-entity=\""
            + escapeHtml(sp) + "\" data-boc-episode=\"" + epAttr + "\">"
            + escapeHtml(sp) + "</button></p>";
        }
        if (oc.confidence) {
          mh += "<p class=\"aux\">Confidence: " + escapeHtml(String(oc.confidence)) + "</p>";
        }
        if (oc.uncertainty_note) {
          mh += "<p class=\"aux\">" + escapeHtml(String(oc.uncertainty_note)) + "</p>";
        }
      });
      return mh;
    }
    return "";
  }
  var dlg = document.getElementById("boc-entity-dialog");
  var bodyEl = document.getElementById("boc-modal-body");
  var titleEl = document.getElementById("boc-dlg-title");
  if (!dlg || !bodyEl) return;

  function renderDetail(j) {
    if (!j || !j.found) {
      bodyEl.innerHTML = "<p class=\"muted\">" + escapeHtml((j && j.error) || "Not found") + "</p>";
      return;
    }
    titleEl.innerHTML = escapeHtml(j.id) + " <span class=\"kind\">(" + escapeHtml(j.kind) + ")</span>";
    var h = "";
    h += "<p class=\"muted\">Episode " + escapeHtml(j.episode) + " · <a href=\"/bride_of_charlie/"
      + escapeHtml(j.inscription_file_id) + "\">Inscription JSON</a></p>";
    h += recordSummary(j);
    if (j.video_timestamp_raw) {
      h += "<p><strong>Time in episode (analysis)</strong> " + escapeHtml(j.video_timestamp_raw);
      if (j.start_seconds != null) h += " → ~" + escapeHtml(j.start_seconds) + "s";
      h += "</p>";
    }
    var snips = j.transcript_snippets;
    if (snips && snips.length) {
      h += "<h4>Transcript snippets</h4>";
      if (snips.length > 1) {
        h += "<p class=\"aux\">Multiple claims reference this node; the player seeks to the segment chosen below (name match or earliest timestamp).</p>";
      }
      for (var si = 0; si < snips.length; si++) {
        var s = snips[si];
        var line = escapeHtml(s.claim_id || "");
        if (s.label) line += (line ? " — " : "") + escapeHtml(s.label);
        if (s.video_timestamp_raw) line += (line ? " · " : "") + escapeHtml(s.video_timestamp_raw);
        if (line) h += "<p class=\"muted\" style=\"font-size:0.82rem;margin:0.35rem 0 0.15rem\">" + line + "</p>";
        if (s.text) h += "<pre class=\"snip\">" + escapeHtml(s.text) + "</pre>";
      }
    } else if (j.transcript_snippet && j.kind !== "meme") {
      h += "<h4>Transcript snippet</h4><pre class=\"snip\">" + escapeHtml(j.transcript_snippet) + "</pre>";
    }
    if (j.youtube && j.youtube.embed) {
      h += "<h4>Video</h4>";
      if (j.start_seconds != null && Number(j.start_seconds) > 0) {
        h += "<p class=\"aux\">Starts at the analysis timestamp above (not at 0:00).</p>";
      }
      h += "<div class=\"vid-wrap\"><iframe title=\"YouTube\" src=\""
        + escapeHtml(j.youtube.embed) + "\" allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture\" allowfullscreen></iframe></div>";
      h += "<p class=\"aux\"><a href=\"" + escapeHtml(j.youtube.watch) + "\" target=\"_blank\" rel=\"noreferrer\">Open on YouTube</a> (new tab — use background playback / PIP if you want sound without this page).</p>";
    } else if (j.video_id) {
      h += "<p class=\"muted\">No timestamp on this row; open a related artifact or claim for a seek, or watch from the start.</p>";
    }
    h += "<p class=\"aux\"><strong>Audio-only:</strong> this hub does not store extracted audio. To strip audio locally, use a tool such as yt-dlp against the YouTube URL.</p>";
    var rel = j.related || {};
    h += relGroup("Nodes", rel.nodes);
    h += relGroup("Claims", rel.claims);
    h += relGroup("Artifacts", rel.artifacts);
    bodyEl.innerHTML = h;
  }

  async function openEntity(id, epHint) {
    if (!id) return;
    bodyEl.innerHTML = "<p id=\"boc-modal-loading\" class=\"boc-modal-loading\">Loading…</p>";
    if (!dlg.open) dlg.showModal();
    var url = "/api/bride/hub/entity-detail?id=" + encodeURIComponent(id);
    if (epHint) url += "&episode=" + encodeURIComponent(epHint);
    try {
      var r = await fetch(url, { credentials: "same-origin", cache: "no-store" });
      var j = await r.json();
      renderDetail(j);
    } catch (e) {
      bodyEl.innerHTML = "<p class=\"muted\">" + escapeHtml(String(e)) + "</p>";
    }
  }

  document.body.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-boc-entity]");
    if (!btn) return;
    ev.preventDefault();
    var id = btn.getAttribute("data-boc-entity");
    var ep = btn.getAttribute("data-boc-episode") || "";
    openEntity(id, ep || null);
  });
  document.getElementById("boc-modal-close").addEventListener("click", function () { dlg.close(); });
  dlg.addEventListener("click", function (ev) { if (ev.target === dlg) dlg.close(); });
})();
</script>
"""


def _draft_editor_listen_port() -> str:
    return os.environ.get("PORT") or os.environ.get("FLASK_RUN_PORT") or "8081"


def _draft_editor_local_base_url() -> str:
    """Origin for copy-paste local links (tunnel 502 fallback). Override with DRAFT_EDITOR_LOCAL_URL."""
    env = (os.environ.get("DRAFT_EDITOR_LOCAL_URL") or "").strip().rstrip("/")
    if env:
        return env
    return f"http://127.0.0.1:{_draft_editor_listen_port()}"


def _should_show_bride_local_fallback_banner(host: str) -> bool:
    """
    Yellow “open localhost” tip is for **ephemeral** tunnels (trycloudflare), not stable DNS like
    ``*.metawebbook.com``. Override with env when needed.
    """
    h = (host or "").split(":")[0].strip().lower()
    if h in ("127.0.0.1", "localhost", "::1"):
        return False
    if os.environ.get("DRAFT_EDITOR_HIDE_LOCAL_FALLBACK_BANNER", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return False
    if os.environ.get("DRAFT_EDITOR_SHOW_LOCAL_FALLBACK_BANNER", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return True
    if "trycloudflare.com" in h:
        return True
    for suf in (
        s.strip().lower()
        for s in (os.environ.get("DRAFT_EDITOR_LOCAL_FALLBACK_BANNER_HOST_SUFFIXES") or "").split(
            ","
        )
        if s.strip()
    ):
        if h == suf or h.endswith("." + suf) or h.endswith(suf):
            return True
    return False


def _bride_tunnel_fallback_banner_html() -> str:
    """HTML for the localhost fallback tip (see ``_should_show_bride_local_fallback_banner``)."""
    local = _draft_editor_local_base_url()
    dash = f"{local}/bride_of_charlie/"
    port = html.escape(_draft_editor_listen_port())
    dash_e = html.escape(dash, quote=True)
    dash_vis = html.escape(dash)
    return (
        '<p class="banner access-tip"><strong>Tunnel 502 or flaky URL?</strong> '
        "Quick tunnels can drop; this app still listens on your machine. "
        f'Open the same dashboard locally: <a href="{dash_e}">{dash_vis}</a>. '
        f"If Flask runs on another port, set <code>DRAFT_EDITOR_LOCAL_URL</code> in <code>.env</code> "
        f"(default assumes port <strong>{port}</strong>). "
        f'See <code>docs/CLOUDFLARED_DRAFT_EDITOR.md</code> § HTTP 502.</p>'
    )


def _render_bride_hub_dashboard(
    doc: dict[str, Any],
    health: dict[str, Any],
    neo: dict[str, Any],
    *,
    rebuild_used: bool,
    access_tip_html: str = "",
    run_ops_html: str = "",
) -> str:
    glo = doc.get("global") or {}
    gn = len(glo.get("nodes") or [])
    gc = len(glo.get("claims") or [])
    ga = len(glo.get("artifacts") or [])
    gm = len(glo.get("memes") or [])
    fp = html.escape(str(health.get("fingerprint") or "—"))
    ok = bool(health.get("ok"))
    age = health.get("index_cache_age_sec")
    age_s = f"{age:.0f}s" if isinstance(age, int | float) else "—"
    root = html.escape(str(doc.get("bride_project_root") or ""))
    neo_line = ""
    if neo.get("available"):
        stats = neo.get("stats") or {}
        bits = [f"{html.escape(str(k))}: {html.escape(str(v))}" for k, v in list(stats.items())[:10]]
        neo_line = (
            "<p class=\"neo ok\"><strong>Neo4j</strong> · " + " · ".join(bits) + "</p>"
            if bits
            else "<p class=\"neo ok\"><strong>Neo4j</strong> connected.</p>"
        )
    else:
        err = html.escape(str(neo.get("error") or "unavailable"))
        neo_line = f'<p class="neo bad"><strong>Neo4j</strong> · {err}</p>'

    ep_blocks: list[str] = []
    for ep in doc.get("episodes") or []:
        epn = ep.get("episode")
        if epn is None:
            continue
        vid = ep.get("video_id")
        yurl = ep.get("youtube_url")
        files = ep.get("files") or {}
        ent = ep.get("entity_ids") or {}
        nn = len(ent.get("nodes") or [])
        cn = len(ent.get("claims") or [])
        an = len(ent.get("artifacts") or [])
        mn = len(ent.get("memes") or [])
        title = f"Episode {int(epn)}"
        vid_s = f' <span class="vid">{html.escape(str(vid))}</span>' if vid else ""
        y_link = ""
        if yurl:
            y_link = (
                f'<a class="yt" href="{html.escape(str(yurl), quote=True)}" '
                f'target="_blank" rel="noreferrer">{html.escape(str(yurl))}</a>'
            )
        lis: list[str] = []
        for key in _BRIDE_DASH_FILE_ORDER:
            slot = files.get(key) or {}
            label = _BRIDE_DASH_LABELS.get(key, key)
            fid = slot.get("file_id")
            path = slot.get("path")
            exists = slot.get("exists")
            if fid:
                st = "ok" if exists else "missing"
                lis.append(
                    "<li>"
                    f"<strong>{html.escape(label)}</strong> · "
                    f'<a href="/bride_of_charlie/{html.escape(str(fid))}">Open editor</a>'
                    f' <code class="path">{html.escape(str(path or ""))}</code>'
                    f' <span class="tag {st}">{"on disk" if exists else "missing"}</span>'
                    "</li>"
                )
            else:
                lis.append(
                    f'<li class="muted"><strong>{html.escape(label)}</strong> · n/a</li>'
                )
        diff_href = f"/api/bride/hub/episode/{int(epn)}/transcript-diff?format=text"
        ep_blocks.append(
            "<section class=\"card\">"
            f"<h2>{html.escape(title)}{vid_s}</h2>"
            f"{y_link}"
            "<ul class=\"files\">" + "".join(lis) + "</ul>"
            f'<p class="meta">Inscription entities: {nn} nodes · {cn} claims · {an} artifacts · {mn} memes · '
            f'<a href="{diff_href}">Transcript diff (download)</a></p>'
            "</section>"
        )

    rebuild_note = (
        '<p class="banner">Index was rebuilt for this request.</p>' if rebuild_used else ""
    )

    entity_sections = (
        _dash_global_entity_section(
            glo.get("nodes") or [],
            "global-nodes",
            "All nodes (N-*)",
            "Deduped across episodes (first occurrence in index order).",
        )
        + _dash_global_entity_section(
            glo.get("claims") or [],
            "global-claims",
            "All claims (C-*)",
            "Deduped across episodes.",
        )
        + _dash_global_entity_section(
            glo.get("artifacts") or [],
            "global-artifacts",
            "All artifacts (A-* families and A-*.* sub-items)",
            "Same flat list as hub JSON global.artifacts (family + sub-item ids).",
        )
        + _dash_global_entity_section(
            glo.get("memes") or [],
            "global-memes",
            "All memes (M-*)",
            "Meme / euphemism / code rows from inscription JSON (per-episode analysis).",
        )
    )

    modal_block = _bride_dashboard_entity_modal_block()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Bride of Charlie — dashboard</title>
  <style>
    :root {{
      --bg: #0c0c0f;
      --card: #141418;
      --border: #27272f;
      --text: #e4e4e7;
      --muted: #71717a;
      --link: #7dd3fc;
      --link-hover: #e0f2fe;
      --ok: #22c55e;
      --bad: #f87171;
    }}
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 1.25rem 1rem 3rem;
      line-height: 1.5;
    }}
    .wrap {{ max-width: 60rem; margin: 0 auto; }}
    /* Override Safari default blue/purple visited links on dark bg */
    .wrap a:link,
    .wrap a:visited {{
      color: var(--link);
      text-decoration: none;
      border-bottom: 1px solid rgba(125, 211, 252, 0.4);
    }}
    .wrap a:hover {{
      color: var(--link-hover);
      border-bottom-color: rgba(224, 242, 254, 0.65);
    }}
    h1 {{ font-size: 1.5rem; font-weight: 600; margin: 0 0 0.5rem; }}
    .sub {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 1rem; }}
    .stats {{
      display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem;
      font-size: 0.85rem; color: var(--muted); margin-bottom: 1rem;
    }}
    .stats strong {{ color: var(--text); }}
    .banner {{ background: #1e3a2f; color: #86efac; padding: 0.5rem 0.75rem; border-radius: 6px; font-size: 0.9rem; }}
    .banner.access-tip {{ background: #292524; color: #fde68a; border: 1px solid #78350f; }}
    .neo.ok {{ color: #86efac; font-size: 0.9rem; }}
    .neo.bad {{ color: var(--bad); font-size: 0.9rem; }}
    .toolbar {{ margin-bottom: 1.25rem; display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; align-items: center; }}
    .toolbar a {{ font-size: 0.9rem; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 1rem 1.1rem;
      margin-bottom: 1rem;
    }}
    .card h2 {{ font-size: 1.1rem; margin: 0 0 0.35rem; }}
    .vid {{ font-weight: 400; color: var(--muted); font-size: 0.9rem; }}
    .yt {{ display: inline-block; font-size: 0.85rem; margin-bottom: 0.5rem; word-break: break-all; }}
    ul.files {{ list-style: none; padding: 0; margin: 0.5rem 0 0; font-size: 0.9rem; }}
    ul.files li {{ padding: 0.25rem 0; border-bottom: 1px solid var(--border); }}
    ul.files li:last-child {{ border-bottom: none; }}
    code.path {{ font-size: 0.8rem; color: var(--muted); }}
    .tag.ok {{ color: var(--ok); font-size: 0.75rem; margin-left: 0.35rem; }}
    .tag.missing {{ color: #fbbf24; font-size: 0.75rem; margin-left: 0.35rem; }}
    li.muted {{ color: var(--muted); }}
    p.meta {{ font-size: 0.8rem; color: var(--muted); margin: 0.75rem 0 0; }}
    .stats a {{ border-bottom: none; }}
    .entity-roll {{ margin-bottom: 1rem; }}
    .entity-desc {{ margin: 0.25rem 0 0; font-size: 0.85rem; }}
    .table-wrap {{ overflow-x: auto; margin-top: 0.75rem; }}
    table.entity-table {{
      width: 100%; border-collapse: collapse; font-size: 0.85rem;
    }}
    table.entity-table th, table.entity-table td {{
      text-align: left; padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--border); vertical-align: top;
    }}
    table.entity-table th {{ color: var(--muted); font-weight: 600; }}
    table.entity-table td.num {{ color: var(--muted); white-space: nowrap; width: 3rem; }}
    .boc-detail-btn {{
      background: #27272f;
      border: 1px solid var(--border);
      color: var(--link);
      border-radius: 6px;
      padding: 0.25rem 0.55rem;
      font-size: 0.8rem;
      cursor: pointer;
    }}
    .boc-detail-btn:hover {{ background: #3f3f46; color: var(--link-hover); }}
    .title-cell .tit {{ font-weight: 500; color: var(--text); line-height: 1.35; }}
    .title-cell .subtit {{ font-size: 0.78rem; color: var(--muted); margin-top: 0.2rem; line-height: 1.35; }}
    .kind-pill {{
      display: inline-block; font-size: 0.65rem; text-transform: uppercase;
      letter-spacing: 0.04em; color: #a1a1aa; border: 1px solid var(--border);
      border-radius: 4px; padding: 0.05rem 0.35rem; margin-right: 0.4rem; vertical-align: middle;
    }}
    .rel-cell {{ min-width: 9rem; max-width: 22rem; }}
    .rel-counts {{ margin-bottom: 0.35rem; }}
    .badge {{
      display: inline-block; font-size: 0.7rem; color: #a1a1aa; margin-right: 0.35rem;
      padding: 0.1rem 0.35rem; background: #1c1c22; border-radius: 4px;
    }}
    .rel-mini-wrap {{ display: flex; flex-wrap: wrap; gap: 0.25rem; }}
    .rel-mini {{
      font-family: inherit; font-size: 0.72rem; cursor: pointer;
      border: 1px solid #3f3f46; background: #1c1c22; color: var(--link);
      border-radius: 4px; padding: 0.1rem 0.35rem;
    }}
    .rel-mini:hover {{ background: #27272f; color: var(--link-hover); }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Bride of Charlie — dashboard</h1>
    <p class="sub">Draft Editor · same index as
      <a href="/api/bride/hub/index">GET /api/bride/hub/index</a>.
      Filterable tables for the same lists: DeerFlow
      <code>/bride-of-charlie/nodes</code>,
      <code>/claims</code>, <code>/artifacts</code> (port <strong>3000</strong>).
    </p>
    {rebuild_note}
    {access_tip_html}
    <div class="stats">
      <span><strong>Project</strong> {root}</span>
      <span><strong>Fingerprint</strong> {fp}</span>
      <span><strong>Index cache age</strong> {html.escape(age_s)}</span>
      <span><strong>Status</strong> {"ok" if ok else "check path"}</span>
      <span><strong>Global</strong> <a href="#global-nodes">{gn} nodes</a> · <a href="#global-claims">{gc} claims</a> · <a href="#global-artifacts">{ga} artifacts</a> · <a href="#global-memes">{gm} memes</a></span>
    </div>
    {neo_line}
    <div class="toolbar">
      <a href="/bride_of_charlie/">Refresh</a>
      <a href="?rebuild=1">Rebuild index</a>
      <a href="#global-nodes">Nodes list</a>
      <a href="#global-claims">Claims list</a>
      <a href="#global-artifacts">Artifacts list</a>
      <a href="#global-memes">Memes list</a>
      <a href="#episodes">Episodes</a>
      <a href="#boc-run-ops">Runs &amp; automation</a>
      <a href="/api/bride/hub/health">Health JSON</a>
      <a href="/api/bride/hub/validate-node-claims">Node↔claim screen</a>
      <a href="/">Draft editor home</a>
    </div>
    {run_ops_html}
    {entity_sections}
    <div id="episodes">
    {"".join(ep_blocks)}
    </div>
  </div>
{modal_block}
</body>
</html>"""


@app.route("/bride_of_charlie")
@app.route("/bride_of_charlie/")
@auth.login_required
def bride_hub_editor_landing():
    """Server-rendered Bride hub dashboard (episodes, file links into editor)."""
    _load_env()
    bride = _bride_project_dir()
    force = request.args.get("rebuild") == "1"
    try:
        doc = _bride_hub.get_or_build_index(bride, AGENT_LAB_ROOT, force=force)
    except Exception as e:
        app.logger.exception("bride dashboard index failed")
        return (
            Response(
                f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"/><title>Error</title></head>"
                f"<body style=\"font-family:system-ui;padding:2rem;\">"
                f"<h1>Dashboard failed</h1><pre>{html.escape(str(e))}</pre></body></html>",
                mimetype="text/html; charset=utf-8",
                status=500,
            )
        )

    exists = bride.is_dir()
    fp = _bride_hub.compute_fingerprint(bride) if exists else None
    ip = _bride_hub.index_path(AGENT_LAB_ROOT)
    cache_age: float | None = None
    if ip.is_file():
        cache_age = time.time() - ip.stat().st_mtime
    health = {
        "ok": exists,
        "fingerprint": fp,
        "index_cache_age_sec": cache_age,
    }
    neo = _bride_neo4j_hub.fetch_neo4j_summary(bride, validate=False)
    host = (request.host or "").split(":")[0].strip().lower()
    access_tip = (
        _bride_tunnel_fallback_banner_html()
        if _should_show_bride_local_fallback_banner(host)
        else ""
    )
    run_ops = _bride_run_ops.render_run_panel_html(
        AGENT_LAB_ROOT,
        bride,
        neo_available=bool(neo.get("available")),
    )
    body = _render_bride_hub_dashboard(
        doc,
        health,
        neo,
        rebuild_used=force,
        access_tip_html=access_tip,
        run_ops_html=run_ops,
    )
    return Response(body, mimetype="text/html; charset=utf-8")


@app.route("/bride_of_charlie/<file_id>")
@auth.login_required
def bride_hub_editor_page(file_id: str):
    """Minimal in-browser editor for a hub file_id."""
    fid = re.sub(r"[^a-fA-F0-9]", "", file_id or "")
    if len(fid) != 16:
        return jsonify({"error": "invalid file_id"}), 400
    bride = _bride_project_dir()
    _p, rel = _bride_hub.resolve_file_id(fid, bride, AGENT_LAB_ROOT)
    if not rel:
        return jsonify({"error": "unknown file_id"}), 404
    tpl_path = APP_DIR / "static" / "bride_charlie_editor.html"
    if not tpl_path.is_file():
        return jsonify({"error": "editor template missing"}), 500
    html = tpl_path.read_text(encoding="utf-8").replace("__FILE_ID__", fid)
    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/api/bride/transcript-overrides/<item_id>/accept", methods=["POST"])
@auth.login_required
def bride_transcript_overrides_accept(item_id: str):
    mod, script = _load_bride_transcript_overrides_module()
    if mod is None:
        return jsonify({"error": "Bride scripts not found", "path": str(script)}), 404
    data = mod.load_store()
    old = next((x for x in (data.get("items") or []) if x.get("id") == item_id), None)
    if not old:
        return jsonify({"error": "Not found"}), 404
    merged = {**old, "status": "accepted"}
    item, err = mod.validate_item_body(merged)
    if err:
        return jsonify({"error": err}), 400
    mod.upsert_item(None, item)
    rc = subprocess.run(
        [sys.executable, str(script), "--apply", "--id", item_id],
        cwd=str(AGENT_LAB_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    sync_out = ""
    if rc.returncode == 0:
        sync_script = _bride_project_dir() / "scripts" / "sync_transcript_hashes.py"
        if sync_script.is_file():
            sr = subprocess.run(
                [sys.executable, str(sync_script)],
                cwd=str(AGENT_LAB_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
            sync_out = (sr.stdout or "")[-2000:]
    return jsonify(
        {
            "ok": rc.returncode == 0,
            "item": item,
            "apply_stdout": (rc.stdout or "")[-4000:],
            "apply_stderr": (rc.stderr or "")[-2000:],
            "returncode": rc.returncode,
            "sync_tail": sync_out,
        }
    )


@app.route("/api/bride/transcript-overrides/apply-all", methods=["POST"])
@auth.login_required
def bride_transcript_overrides_apply_all():
    _, script = _load_bride_transcript_overrides_module()
    if not script.is_file():
        return jsonify({"error": "Bride scripts not found", "path": str(script)}), 404
    body = request.get_json(silent=True) or {}
    ep = body.get("episode")
    cmd = [sys.executable, str(script), "--apply"]
    if ep is not None:
        cmd.extend(["--episode", str(int(ep))])
    rc = subprocess.run(cmd, cwd=str(AGENT_LAB_ROOT), capture_output=True, text=True, timeout=300)
    sync_out = ""
    if rc.returncode == 0:
        sync_script = _bride_project_dir() / "scripts" / "sync_transcript_hashes.py"
        if sync_script.is_file():
            sr = subprocess.run(
                [sys.executable, str(sync_script)],
                cwd=str(AGENT_LAB_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
            )
            sync_out = (sr.stdout or "")[-2000:]
    return jsonify(
        {
            "ok": rc.returncode == 0,
            "stdout": (rc.stdout or "")[-8000:],
            "stderr": (rc.stderr or "")[-4000:],
            "returncode": rc.returncode,
            "sync_tail": sync_out,
        }
    )


@app.route("/api/replies", methods=["GET"])
@auth.login_required
def list_replies():
    """Return unreplied comments and reply drafts. ?publication=X"""
    from .substack_comments import load_replies_cache
    from .store import list_reply_drafts

    pub_id = request.args.get("publication", "metaweb")
    cache = load_replies_cache()
    comments = cache.get("comments", [])
    replied_ids = set(cache.get("replied_ids", []))
    reply_drafts = list_reply_drafts()
    draft_by_comment = {d.get("metadata", {}).get("parent_comment_id"): d for d in reply_drafts}
    unreplied = [c for c in comments if c.get("id") not in replied_ids and c.get("id") not in draft_by_comment]
    return jsonify({
        "comments": comments,
        "unreplied": unreplied,
        "reply_drafts": reply_drafts,
        "updated_at": cache.get("updated_at"),
    })


@app.route("/api/replies/fetch", methods=["POST"])
@auth.login_required
def fetch_replies():
    """Fetch comments from Substack published posts. Runs in background."""
    import threading
    from .substack_comments import fetch_all_comments, load_replies_cache, save_replies_cache

    pub_id = (request.get_json() or {}).get("publication", "metaweb")
    def _run():
        try:
            comments = fetch_all_comments(pub_id)
            cache = load_replies_cache()
            replied = cache.get("replied_ids", [])
            save_replies_cache(comments, replied)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "fetching", "message": "Fetching comments in background. Refresh replies tab in ~30s."}), 202


@app.route("/api/replies/draft", methods=["POST"])
@auth.login_required
def create_reply_draft():
    """Create a reply draft for a comment. Saves to draft store."""
    from .store import create_draft
    from .substack_comments import load_replies_cache, save_replies_cache

    data = request.get_json() or {}
    cid = data.get("comment_id", "")
    post_url = data.get("post_url", "")
    post_title = data.get("post_title", "")
    author = data.get("author", "")
    text = data.get("text", "")
    suggested = data.get("suggested_reply", "")

    if not cid or not post_url:
        return jsonify({"error": "comment_id and post_url required"}), 400

    content = f'<p>{suggested}</p>' if suggested else f'<p>Reply to {author}: </p>'
    meta = {
        "draft_type": "reply",
        "parent_post_url": post_url,
        "parent_post_title": post_title,
        "parent_comment_id": cid,
        "comment_author": author,
        "comment_text": text[:300],
    }
    draft = create_draft(
        content=content,
        platform="substack_reply",
        metadata=meta,
        author="system",
        destination=f"Substack reply · {post_title[:40]}",
    )
    return jsonify(draft), 201


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/<path:path>")
def static_files(path: str):
    # No API or bride editor route matched — avoid serving these as static files.
    if path.startswith("api/") or path.startswith("bride_of_charlie/"):
        hint = (
            "No handler for this path (check URL spelling and method). "
            "Editor is /bride_of_charlie/<16-char-hex-file_id> with no extra segments."
        )
        if path.startswith("api/bride/"):
            hint = (
                "This URL is a Bride API route in current agent-lab, but it was not registered in "
                "this running process — almost always an outdated Draft Editor deploy. "
                "Redeploy from the repo that includes apps/draft_editor/app.py (e.g. GET /api/bride/hub/episodes). "
                "The static catch-all matched because the hub route is missing in this build."
            )
        return (
            jsonify(
                {
                    "error": "Not found",
                    "hint": hint,
                    "path": f"/{path}",
                }
            ),
            404,
        )
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
