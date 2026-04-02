"""
Bride of Charlie — workflow run status, log tail, and background job helpers.

Used by the Draft Editor dashboard (/bride_of_charlie/) for monitoring and kickoff.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

_ERR_LINE = re.compile(
    r"(error|traceback|exception|failed|\bERR\b|⚠|exit [1-9]|non-zero)",
    re.IGNORECASE,
)


def _agent_lab_root(from_file: Path) -> Path:
    # apps/draft_editor/bride_run_ops.py -> agent-lab
    return from_file.resolve().parents[2]


def workflow_jobs_dir(agent_lab_root: Path) -> Path:
    d = agent_lab_root / ".draft-editor-cache" / "bride-workflow-jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def neo4j_ingest_state_path(agent_lab_root: Path) -> Path:
    return agent_lab_root / ".draft-editor-cache" / "bride_neo4j_ingest_state.json"


def drafts_mtime_signal_for_neo4j(bride_project: Path) -> tuple[float | None, int]:
    """Max mtime of ``drafts/episode_*.md`` (same sources as neo4j_ingest episode parse)."""
    d = bride_project / "drafts"
    if not d.is_dir():
        return None, 0
    paths = list(d.glob("episode_*.md"))
    if not paths:
        return None, 0
    max_m = 0.0
    for p in paths:
        try:
            max_m = max(max_m, p.stat().st_mtime)
        except OSError:
            continue
    return max_m, len(paths)


def read_neo4j_ingest_state(agent_lab_root: Path) -> dict[str, Any] | None:
    p = neo4j_ingest_state_path(agent_lab_root)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_neo4j_ingest_state(agent_lab_root: Path, payload: dict[str, Any]) -> None:
    p = neo4j_ingest_state_path(agent_lab_root)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def record_neo4j_ingest_after_success(
    agent_lab_root: Path,
    bride_project: Path,
    *,
    job_id: str,
    exit_code: int,
) -> None:
    """Snapshot draft mtimes after a successful ingest (dashboard + CLI ingest should stay in sync)."""
    max_m, n = drafts_mtime_signal_for_neo4j(bride_project)
    write_neo4j_ingest_state(
        agent_lab_root,
        {
            "updated_at": time.time(),
            "job_id": job_id,
            "exit_code": exit_code,
            "drafts_max_mtime_at_ingest": max_m,
            "episode_draft_count": n,
        },
    )


def compute_neo4j_draft_sync(
    agent_lab_root: Path,
    bride_project: Path,
) -> dict[str, Any]:
    """
    Compare current episode draft mtimes to the last successful ingest recorded on disk.

    State is written when dashboard-triggered ``neo4j_ingest.py --force`` exits 0.
    If you ingest only from the CLI, run ingest once from the dashboard (or touch state — not implemented)
    to establish a baseline, or the UI will treat drafts as needing ingest until then.
    """
    current_max, n_files = drafts_mtime_signal_for_neo4j(bride_project)
    state = read_neo4j_ingest_state(agent_lab_root)
    last_max = state.get("drafts_max_mtime_at_ingest") if state else None
    last_at = state.get("updated_at") if state else None

    out: dict[str, Any] = {
        "episode_draft_count": n_files,
        "current_drafts_max_mtime": current_max,
        "last_ingest_drafts_max_mtime": last_max,
        "last_ingest_at": last_at,
        "needs_reingest": False,
        "reason": "ok",
        "banner_text": "",
    }

    if current_max is None or n_files == 0:
        out["reason"] = "no_episode_drafts"
        return out

    if last_max is None:
        out["needs_reingest"] = True
        out["reason"] = "never_recorded_ingest"
        out["banner_text"] = (
            "No successful Neo4j ingest has been recorded yet (from this machine). "
            "After drafts are final, run neo4j_ingest.py --force so the graph matches "
            "drafts/episode_*.md."
        )
        return out

    try:
        if float(current_max) > float(last_max) + 1e-6:
            out["needs_reingest"] = True
            out["reason"] = "drafts_newer_than_last_ingest"
            out["banner_text"] = (
                "Episode drafts were modified after the last successful Neo4j ingest. "
                "Run neo4j_ingest.py --force (button below) to refresh the graph."
            )
    except (TypeError, ValueError):
        out["needs_reingest"] = True
        out["reason"] = "state_corrupt"
        out["banner_text"] = (
            "Could not compare draft mtimes to last ingest — run neo4j_ingest.py --force "
            "if the graph may be stale."
        )

    if not out["needs_reingest"]:
        out["reason"] = "synced"
    return out


def latest_workflow_logs(agent_lab_root: Path, *, limit: int = 5) -> list[dict[str, Any]]:
    """Most recently modified log files under logs/ that look like Bride workflow runs."""
    logs_dir = agent_lab_root / "logs"
    if not logs_dir.is_dir():
        return []
    candidates: list[Path] = []
    for pattern in ("bride_workflow*.log", "*workflow*.log", "bride*.log"):
        candidates.extend(logs_dir.glob(pattern))
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in candidates:
        rp = str(p.resolve())
        if rp in seen:
            continue
        seen.add(rp)
        uniq.append(p)
    uniq.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    for p in uniq[:limit]:
        try:
            st = p.stat()
        except OSError:
            continue
        out.append(
            {
                "path": str(p.relative_to(agent_lab_root)),
                "name": p.name,
                "mtime": st.st_mtime,
                "size": st.st_size,
            }
        )
    return out


def tail_file(path: Path, *, max_bytes: int = 48_000, max_lines: int = 80) -> str:
    if not path.is_file():
        return ""
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    if len(raw) > max_bytes:
        raw = raw[-max_bytes:]
        raw = raw.split(b"\n", 1)[-1]
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])


def grep_errorish_lines(text: str, *, max_items: int = 12) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        if _ERR_LINE.search(line):
            s = line.strip()
            if s and s not in out:
                out.append(s[:500])
            if len(out) >= max_items:
                break
    return out


def build_suggestions(
    *,
    neo_available: bool,
    validate_ok: bool | None,
    log_tail: str,
    error_lines: list[str],
) -> list[str]:
    """Human-readable next steps for the dashboard."""
    s: list[str] = []
    if not neo_available:
        s.append(
            "Neo4j is not connected — fix NEO4J_URI / Docker, then run graph ingest when drafts are ready."
        )
    if error_lines:
        s.append(
            "Latest log shows error-like lines — open the log file or re-run with a smaller scope (--stop-after)."
        )
    if validate_ok is False:
        s.append(
            "Node↔claim validation reported errors — open /api/bride/hub/validate-node-claims or re-run assign_ids after fixing Phase 1 JSON."
        )
    if "SKIP" in log_tail and "unanchored" in log_tail.lower():
        s.append(
            "Neo4j ingest skipped some claims (strict mode) — add artifact anchors in drafts or set NEO4J_INGEST_STRICT_CLAIMS=0 for permissive ingest."
        )
    if not s and not error_lines:
        s.append(
            "No automatic red flags — optional: run LLM sense scan on transcripts, export dual transcripts, then neo4j_ingest.py --force if drafts changed."
        )
    return s[:8]


def _uv_python_cmd(agent_lab_root: Path, script: Path, args: list[str]) -> list[str]:
    backend = agent_lab_root / "framework" / "deer-flow" / "backend"
    return [
        "uv",
        "run",
        "--project",
        str(backend),
        "python",
        str(script),
        *args,
    ]


def start_workflow_background(
    agent_lab_root: Path,
    bride_project: Path,
    options: dict[str, Any],
    *,
    on_complete: Any | None = None,
) -> tuple[str, Path]:
    """
    Start run_full_workflow.py in a daemon thread; stream combined output to a job log file.
    Returns (job_id, log_path).
    """
    job_id = uuid.uuid4().hex[:12]
    jdir = workflow_jobs_dir(agent_lab_root)
    log_path = jdir / f"{job_id}.log"
    status_path = jdir / f"{job_id}.json"

    wf_script = (
        bride_project / "scripts" / "run_full_workflow.py"
    ).resolve()
    if not wf_script.is_file():
        raise FileNotFoundError(f"run_full_workflow.py not found: {wf_script}")

    cmd: list[str] = _uv_python_cmd(agent_lab_root, wf_script, [])
    if options.get("skip_fetch"):
        cmd.append("--skip-fetch")
    if options.get("no_backup"):
        cmd.append("--no-backup")
    if options.get("skip_search"):
        cmd.append("--skip-search")
    sa = options.get("stop_after")
    if sa is not None:
        try:
            cmd.extend(["--stop-after", str(int(sa))])
        except (TypeError, ValueError):
            pass
    mp = options.get("max_passes")
    if mp is not None:
        try:
            cmd.extend(["--max-passes", str(int(mp))])
        except (TypeError, ValueError):
            pass

    env = os.environ.copy()
    if options.get("editorial_pass"):
        env["BRIDE_EDITORIAL_PASS"] = "1"
    if options.get("dual_transcripts"):
        env["BRIDE_EXPORT_DUAL_TRANSCRIPTS"] = "1"
    if options.get("display_clean"):
        env["BRIDE_EXPORT_DISPLAY_CLEAN"] = "1"
    if options.get("stop_after_green_validate"):
        env["BRIDE_STOP_AFTER_GREEN_VALIDATE"] = "1"

    def _run() -> None:
        meta = {
            "job_id": job_id,
            "kind": "workflow",
            "started_at": time.time(),
            "command": cmd,
            "status": "running",
            "log": str(log_path.relative_to(agent_lab_root)),
        }
        status_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        try:
            with open(log_path, "w", encoding="utf-8") as lf:
                lf.write(f"# bride_run_ops job {job_id}\n# cwd {agent_lab_root}\n# {' '.join(cmd)}\n\n")
                lf.flush()
                p = subprocess.Popen(
                    cmd,
                    cwd=str(agent_lab_root),
                    env=env,
                    stdout=lf,
                    stderr=subprocess.STDOUT,
                )
                code = p.wait()
            meta["finished_at"] = time.time()
            meta["exit_code"] = int(code)
            meta["status"] = "ok" if code == 0 else "failed"
        except Exception as e:
            meta["finished_at"] = time.time()
            meta["status"] = "error"
            meta["error"] = str(e)
            try:
                with open(log_path, "a", encoding="utf-8") as lf:
                    lf.write(f"\n[bride_run_ops] {e!r}\n")
            except OSError:
                pass
        status_path.write_text(json.dumps(meta, indent=2, default=str) + "\n", encoding="utf-8")
        # Last-run summary for dashboard without polling job dir
        last = agent_lab_root / ".draft-editor-cache" / "bride_workflow_last_run.json"
        try:
            last.parent.mkdir(parents=True, exist_ok=True)
            last.write_text(json.dumps(meta, indent=2, default=str) + "\n", encoding="utf-8")
        except OSError:
            pass
        if on_complete:
            try:
                on_complete(meta)
            except Exception:
                pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return job_id, log_path


def build_run_status_json(
    agent_lab_root: Path,
    bride_project: Path,
    *,
    neo_available: bool,
    skip_validate: bool = False,
) -> dict[str, Any]:
    """JSON payload for GET /api/bride/hub/run-status (polling)."""
    logs = latest_workflow_logs(agent_lab_root, limit=5)
    tail = ""
    err_lines: list[str] = []
    primary_log: str | None = None
    if logs:
        primary_log = logs[0]["name"]
        lp = agent_lab_root / logs[0]["path"]
        tail = tail_file(lp)
        err_lines = grep_errorish_lines(tail)
    validate_ok: bool | None = None
    if not skip_validate:
        try:
            if str(agent_lab_root) not in __import__("sys").path:
                __import__("sys").path.insert(0, str(agent_lab_root))
            from apps.draft_editor import bride_hub as bh

            bride = bride_project
            if bride.is_dir():
                out = bh.screen_node_claim_consistency(bride, include_backlinks=False)
                validate_ok = bool(out.get("ok")) and int(out.get("error_count") or 0) == 0
        except Exception:
            validate_ok = None
    last = read_last_run(agent_lab_root)
    draft_sync = compute_neo4j_draft_sync(agent_lab_root, bride_project)
    sug = build_suggestions(
        neo_available=neo_available,
        validate_ok=validate_ok,
        log_tail=tail,
        error_lines=err_lines,
    )
    if draft_sync.get("needs_reingest"):
        hint = (draft_sync.get("banner_text") or "").strip()
        if hint:
            sug = [hint] + [x for x in sug if x != hint][:7]
    return {
        "neo_available": neo_available,
        "latest_logs": logs,
        "primary_log": primary_log,
        "log_tail": tail[-8000:] if tail else "",
        "error_lines": err_lines,
        "suggestions": sug[:8],
        "last_run": last,
        "validate_ok": validate_ok,
        "draft_sync": draft_sync,
    }


def read_job_status(agent_lab_root: Path, job_id: str) -> dict[str, Any] | None:
    jid = re.sub(r"[^a-f0-9]", "", (job_id or "").lower())
    if len(jid) != 12:
        return None
    p = workflow_jobs_dir(agent_lab_root) / f"{jid}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def read_workflow_job_detail(agent_lab_root: Path, job_id: str) -> dict[str, Any] | None:
    """Job JSON plus tail of the job log (workflow or Neo4j ingest if log path matches)."""
    st = read_job_status(agent_lab_root, job_id)
    if not st:
        return None
    log_rel = st.get("log")
    tail = ""
    if isinstance(log_rel, str) and log_rel:
        lp = agent_lab_root / log_rel
        if lp.is_file():
            tail = tail_file(lp)
    out = dict(st)
    out["log_tail"] = tail
    return out


def render_run_panel_html(
    agent_lab_root: Path,
    bride_project: Path,
    *,
    neo_available: bool,
) -> str:
    """Server-rendered Operations card + client polling for /api/bride/hub/run-status."""
    data = build_run_status_json(
        agent_lab_root,
        bride_project,
        neo_available=neo_available,
        skip_validate=False,
    )
    logs = data.get("latest_logs") or []
    last = data.get("last_run")
    tail = data.get("log_tail") or ""
    err_lines = list(data.get("error_lines") or [])
    sug = list(data.get("suggestions") or [])
    sug_html = "".join(f"<li>{_esc(s)}</li>" for s in sug)
    err_html = "".join(f'<li class="err">{_esc(e)}</li>' for e in err_lines[:8])
    last_html = ""
    if last:
        st = last.get("status", "?")
        code = last.get("exit_code")
        last_html = (
            f'<p class="run-meta"><strong>Last dashboard workflow</strong> · '
            f"status <code>{_esc(str(st))}</code>"
            + (f" · exit <code>{code}</code>" if code is not None else "")
            + "</p>"
        )
    tail_esc = _esc(
        tail[-6000:]
        if tail
        else "(no log tail yet — run a workflow or add logs/bride_workflow*.log)"
    )
    log_name = _esc(logs[0]["name"]) if logs else "—"
    ds = data.get("draft_sync") or {}
    ban_class = "draft-sync-banner warn" if ds.get("needs_reingest") else "draft-sync-banner"
    ban_style = "" if ds.get("needs_reingest") else "display: none"
    ban_text = _esc(str(ds.get("banner_text") or ""))

    return f"""
<section class="card run-ops" id="boc-run-ops">
  <h2>Runs &amp; automation</h2>
  <p class="entity-desc">Monitor workflow logs, start a full pass from the browser, or re-ingest Neo4j. Telegram can still trigger runs; use this panel to see status and next steps.</p>
  <div id="boc-draft-sync-banner" class="{ban_class}" style="{ban_style}">{ban_text}</div>
  {last_html}
  <p class="run-meta">Latest log file: <code>{log_name}</code></p>
  <ul class="suggestions">{sug_html}</ul>
  {f'<ul class="err-list">{err_html}</ul>' if err_lines else ''}
  <details class="log-details"><summary>Recent log tail</summary><pre class="log-tail">{tail_esc}</pre></details>

  <h3 class="run-h3">Start full workflow</h3>
  <form id="boc-wf-form" class="wf-form">
    <label><input type="checkbox" name="skip_fetch" checked/> Skip fetch (use existing raw transcripts)</label>
    <label><input type="checkbox" name="editorial_pass" checked/> Editorial pass + hash sync</label>
    <label><input type="checkbox" name="dual_transcripts"/> Dual transcripts (verbatim + display)</label>
    <label><input type="checkbox" name="display_clean"/> Display-clean (uh/um strip; needs dual)</label>
    <label><input type="checkbox" name="stop_after_green_validate"/> Stop after green Neo4j validate</label>
    <label>Stop after stage <input type="number" name="stop_after" min="1" max="6" placeholder="optional" style="width:4rem"/></label>
    <button type="submit" class="btn-primary">Start workflow</button>
  </form>
  <p id="boc-wf-msg" class="run-msg wf-job-msg" aria-live="polite"></p>

  <h3 class="run-h3">Neo4j</h3>
  <p class="entity-desc">Re-parse <code>drafts/episode_*.md</code> into the graph (preserves NameCorrection).</p>
  <button type="button" class="btn-secondary" id="boc-neo4j-btn">Run neo4j_ingest.py --force</button>
  <p id="boc-neo4j-msg" class="run-msg wf-job-msg"></p>

  <h3 class="run-h3">LLM sense scan</h3>
  <p class="entity-desc">Uses API credits — same as Transcripts tab. Pick episode and open the main editor’s Transcripts view for full UI, or run a quick scan below.</p>
  <label>Episode <select id="boc-sense-ep"></select></label>
  <label><input type="checkbox" id="boc-sense-apply"/> Apply safe fixes</label>
  <button type="button" class="btn-secondary" id="boc-sense-btn">Run sense scan</button>
  <p id="boc-sense-msg" class="run-msg"></p>
</section>
<style>
  .run-ops .run-meta {{ font-size: 0.85rem; color: var(--muted); }}
  .run-ops .suggestions {{ margin: 0.5rem 0; padding-left: 1.2rem; }}
  .run-ops .err-list {{ margin: 0.35rem 0; padding-left: 1.2rem; color: #f87171; font-size: 0.85rem; }}
  .run-ops .log-details {{ margin: 0.75rem 0; }}
  .run-ops .log-tail {{
    max-height: 14rem; overflow: auto; background: #0a0a0c; padding: 0.6rem; border-radius: 6px;
    font-size: 0.72rem; white-space: pre-wrap; word-break: break-word;
  }}
  .run-ops .wf-form label {{ display: block; margin: 0.25rem 0; font-size: 0.88rem; }}
  .run-ops .btn-primary, .run-ops .btn-secondary {{
    margin-top: 0.5rem; padding: 0.4rem 0.85rem; border-radius: 6px; border: 1px solid var(--border);
    background: #1d4ed8; color: #fff; cursor: pointer; font-size: 0.9rem;
  }}
  .run-ops .btn-secondary {{ background: #27272f; color: var(--text); }}
  .run-ops .run-msg {{ font-size: 0.85rem; margin: 0.35rem 0; color: #86efac; }}
  .run-ops .wf-job-msg {{ white-space: pre-wrap; font-family: ui-monospace, monospace; max-height: 10rem; overflow: auto; }}
  .run-ops .draft-sync-banner.warn {{
    background: #422006; color: #fde68a; border: 1px solid #b45309; border-radius: 8px;
    padding: 0.65rem 0.85rem; margin: 0.5rem 0 0.75rem; font-size: 0.9rem; line-height: 1.45;
  }}
  .run-ops .run-h3 {{ font-size: 1rem; margin: 1rem 0 0.35rem; }}
</style>
<script>
(function() {{
  function esc(s) {{ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }}
  var bocPolls = {{ wf: null, neo: null }};
  function stopBocJobPoll(slot) {{
    var s = slot || 'wf';
    if (bocPolls[s]) {{ clearInterval(bocPolls[s]); bocPolls[s] = null; }}
  }}
  function pollBocHubJob(jobId, msgEl, label, slot) {{
    var sl = slot || 'wf';
    stopBocJobPoll(sl);
    function tick() {{
      fetch('/api/bride/hub/workflow/job/' + encodeURIComponent(jobId), {{ credentials: 'same-origin' }})
        .then(function(r) {{ return r.json(); }})
        .then(function(j) {{
          if (j.error) {{
            stopBocJobPoll(sl);
            if (msgEl) msgEl.textContent = j.error;
            return;
          }}
          var st = j.status;
          var lines = [label + ' · ' + st];
          if (j.exit_code !== undefined && j.exit_code !== null && st !== 'running')
            lines.push('exit ' + j.exit_code);
          var lt = j.log_tail || '';
          if (lt) lines.push(lt.slice(-1400));
          if (msgEl) msgEl.textContent = lines.join('\\n');
          if (st !== 'running') {{
            stopBocJobPoll(sl);
            refreshRunStatus();
          }}
        }})
        .catch(function(e) {{
          stopBocJobPoll(sl);
          if (msgEl) msgEl.textContent = String(e);
        }});
    }}
    tick();
    bocPolls[sl] = setInterval(tick, 2000);
  }}
  function refreshRunStatus() {{
    fetch('/api/bride/hub/run-status?skip_validate=1', {{ credentials: 'same-origin' }})
      .then(function(r) {{ return r.json(); }})
      .then(function(d) {{
        if (d.error) return;
        var ul = document.querySelector('#boc-run-ops .suggestions');
        if (ul && d.suggestions)
          ul.innerHTML = d.suggestions.map(function(s) {{ return '<li>' + esc(s) + '</li>'; }}).join('');
        var ban = document.getElementById('boc-draft-sync-banner');
        var ds = d.draft_sync;
        if (ban && ds) {{
          if (ds.needs_reingest && ds.banner_text) {{
            ban.style.display = 'block';
            ban.className = 'draft-sync-banner warn';
            ban.textContent = ds.banner_text;
          }} else {{
            ban.style.display = 'none';
            ban.textContent = '';
          }}
        }}
      }}).catch(function() {{}});
  }}
  fetch('/api/bride/hub/episodes', {{ credentials: 'same-origin' }})
    .then(r => r.json())
    .then(d => {{
      var sel = document.getElementById('boc-sense-ep');
      if (!sel || !d.episodes) return;
      d.episodes.forEach(function(n) {{
        var o = document.createElement('option');
        o.value = n; o.textContent = 'Episode ' + n;
        sel.appendChild(o);
      }});
    }}).catch(function() {{}});
  var wf = document.getElementById('boc-wf-form');
  if (wf) wf.addEventListener('submit', function(ev) {{
    ev.preventDefault();
    var fd = new FormData(wf);
    var body = {{
      skip_fetch: !!fd.get('skip_fetch'),
      editorial_pass: !!fd.get('editorial_pass'),
      dual_transcripts: !!fd.get('dual_transcripts'),
      display_clean: !!fd.get('display_clean'),
      stop_after_green_validate: !!fd.get('stop_after_green_validate'),
      stop_after: fd.get('stop_after') ? parseInt(fd.get('stop_after'), 10) : null
    }};
    var msg = document.getElementById('boc-wf-msg');
    if (msg) msg.textContent = 'Starting…';
    fetch('/api/bride/hub/workflow/run', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      credentials: 'same-origin',
      body: JSON.stringify(body)
    }}).then(function(r) {{ return r.json(); }}).then(function(j) {{
      if (!msg) return;
      if (j.job_id) {{
        msg.textContent = 'Workflow job ' + j.job_id + ' · running…';
        pollBocHubJob(j.job_id, msg, 'Workflow', 'wf');
      }} else
        msg.textContent = j.error || 'Error';
    }}).catch(function(e) {{ if (msg) msg.textContent = esc(e); }});
  }});
  var nb = document.getElementById('boc-neo4j-btn');
  if (nb) nb.addEventListener('click', function() {{
    var msg = document.getElementById('boc-neo4j-msg');
    if (msg) msg.textContent = 'Starting Neo4j ingest…';
    fetch('/api/bride/hub/neo4j-ingest', {{ method: 'POST', credentials: 'same-origin' }})
      .then(function(r) {{ return r.json(); }})
      .then(function(j) {{
        if (!msg) return;
        if (j.job_id) {{
          msg.textContent = 'Neo4j ingest ' + j.job_id + ' · running…';
          pollBocHubJob(j.job_id, msg, 'Neo4j ingest', 'neo');
        }} else
          msg.textContent = j.error || 'ok';
      }})
      .catch(function(e) {{ if (msg) msg.textContent = esc(e); }});
  }});
  var sb = document.getElementById('boc-sense-btn');
  if (sb) sb.addEventListener('click', function() {{
    var ep = parseInt((document.getElementById('boc-sense-ep') || {{}}).value, 10) || 1;
    var apply = document.getElementById('boc-sense-apply') && document.getElementById('boc-sense-apply').checked;
    var msg = document.getElementById('boc-sense-msg');
    if (msg) msg.textContent = 'Running sense scan…';
    fetch('/api/bride/transcript-sense-scan', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      credentials: 'same-origin',
      body: JSON.stringify({{ episode: ep, apply: apply }})
    }}).then(function(r) {{ return r.json(); }})
      .then(function(j) {{
        if (msg) msg.textContent = j.job_id ? ('Queued job ' + j.job_id + ' — poll /api/bride/transcript-sense-scan/job/' + j.job_id) : (j.error || JSON.stringify(j).slice(0, 200));
      }}).catch(function(e) {{ if (msg) msg.textContent = esc(e); }});
  }});
  setInterval(refreshRunStatus, 20000);
}})();
</script>
"""


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def read_last_run(agent_lab_root: Path) -> dict[str, Any] | None:
    p = agent_lab_root / ".draft-editor-cache" / "bride_workflow_last_run.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def start_neo4j_ingest_background(agent_lab_root: Path, bride_project: Path) -> tuple[str, Path]:
    """neo4j_ingest.py --force in background; returns (job_id, log_path)."""
    job_id = uuid.uuid4().hex[:12]
    jdir = workflow_jobs_dir(agent_lab_root)
    log_path = jdir / f"{job_id}_neo4j.log"
    status_path = jdir / f"{job_id}.json"
    script = (bride_project / "scripts" / "neo4j_ingest.py").resolve()
    if not script.is_file():
        raise FileNotFoundError(script)

    cmd = _uv_python_cmd(agent_lab_root, script, ["--force"])
    log_rel = str(log_path.relative_to(agent_lab_root))

    def _run() -> None:
        meta: dict[str, Any] = {
            "job_id": job_id,
            "kind": "neo4j_ingest",
            "started_at": time.time(),
            "command": cmd,
            "status": "running",
            "log": log_rel,
        }
        status_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        try:
            with open(log_path, "w", encoding="utf-8") as lf:
                lf.write(f"# neo4j ingest {job_id}\n# {' '.join(cmd)}\n\n")
                lf.flush()
                p = subprocess.Popen(
                    cmd,
                    cwd=str(agent_lab_root),
                    stdout=lf,
                    stderr=subprocess.STDOUT,
                )
                code = p.wait()
            meta["finished_at"] = time.time()
            meta["exit_code"] = int(code)
            meta["status"] = "ok" if code == 0 else "failed"
        except Exception as e:
            meta["finished_at"] = time.time()
            meta["status"] = "error"
            meta["error"] = str(e)
        status_path.write_text(json.dumps(meta, indent=2, default=str) + "\n", encoding="utf-8")
        if meta.get("status") == "ok":
            record_neo4j_ingest_after_success(
                agent_lab_root,
                bride_project,
                job_id=job_id,
                exit_code=int(meta.get("exit_code") or 0),
            )

    threading.Thread(target=_run, daemon=True).start()
    return job_id, log_path
