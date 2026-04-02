"""
Shiftshapr — your digital twin via Telegram.

Runs on MacMini with webhook. Knows you via data/shiftshapr_context.json.
Logs all actions and decisions to logs/shiftshapr_audit.log.

Commands: /deadlines, /opportunities, /brief, /add, /remember, /bride, free-form
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = AGENT_LAB_ROOT / "data"
LOGS_DIR = AGENT_LAB_ROOT / "logs"
VOICES_DIR = AGENT_LAB_ROOT / "voices"
KNOWLEDGE_DIR = AGENT_LAB_ROOT / "knowledge"
DOCS_DIR = KNOWLEDGE_DIR / "docs"
URLS_DIR = KNOWLEDGE_DIR / "urls"
AUDIT_LOG = LOGS_DIR / "shiftshapr_audit.log"

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
LEDGER_PATH = DATA_DIR / "opportunities.json"
CONTEXT_PATH = DATA_DIR / "shiftshapr_context.json"
SCRIPTS_DIR = AGENT_LAB_ROOT / "scripts"
BRIDE_PROJECT_DIR = AGENT_LAB_ROOT / "projects" / "monuments" / "bride_of_charlie"
BRIDE_LINKS_FILE = BRIDE_PROJECT_DIR / "input" / "youtube_links.txt"
BRIDE_WORKFLOW_SCRIPT = BRIDE_PROJECT_DIR / "scripts" / "run_full_workflow.py"

VOICE_FILES = {"meta_layer": "meta_layer_voice.md", "canopi": "canopi_voice.md", "substack": "substack_voice.md", "grant": "grant_voice.md"}
KNOWLEDGE_MAX_CHARS = 16_000  # ~4k tokens total for knowledge

_DEERFLOW_BACKEND = AGENT_LAB_ROOT / "framework" / "deer-flow" / "backend"
if str(_DEERFLOW_BACKEND) not in sys.path:
    sys.path.insert(0, str(_DEERFLOW_BACKEND))
from app.utils.channel_message_format import format_channel_message


def _load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def _audit(action: str, details: dict) -> None:
    """Log every action and decision."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action,
        **details,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _load_context() -> dict:
    if not CONTEXT_PATH.exists():
        return {}
    try:
        return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_ledger() -> dict:
    if not LEDGER_PATH.exists():
        return {"opportunities": []}
    try:
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"opportunities": []}


def _extract_pdf(path: Path) -> str:
    """Extract text from PDF. Requires pymupdf or pypdf (uv add pypdf)."""
    try:
        import pymupdf
        doc = pymupdf.open(path)
        text = "\n\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip()
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n\n".join(p.extract_text() or "" for p in reader.pages).strip()
    except ImportError:
        return ""


def _extract_url(text: str) -> str | None:
    """Extract first URL from text."""
    m = _URL_RE.search(text)
    return m.group(0).rstrip(".,;:)") if m else None


def _youtube_video_id(url: str) -> str | None:
    """11-char video id from youtube.com/watch?v= or youtu.be/ (same idea as fetch_transcripts)."""
    patterns = [
        r"(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _telegram_cmd_and_tail(text: str) -> tuple[str, str]:
    """First token as command (strip @BotName suffix), and the rest of the message."""
    parts = text.split(maxsplit=1)
    if not parts:
        return "", ""
    first = parts[0].lower()
    if "@" in first:
        first = first.split("@", 1)[0]
    tail = parts[1].strip() if len(parts) > 1 else ""
    return first, tail


def _message_is_bride_episode_request(text: str) -> bool:
    """Natural language: Bride of Charlie + new episode / process …"""
    t = (text or "").lower().strip()
    if t.startswith("/bride"):
        return True
    if "bride" not in t:
        return False
    if "charlie" in t:
        return True
    if "process" in t and "episode" in t:
        return True
    return False


def _append_bride_youtube_link(url: str) -> tuple[bool, str]:
    """
    Append URL to bride youtube_links.txt if not already listed (by video id).
    Returns (ok_for_workflow, user_message). ok False => do not run workflow.
    """
    vid = _youtube_video_id(url)
    if not vid:
        return False, "Need a YouTube URL: `youtube.com/watch?v=…` or `youtu.be/…`."

    if not BRIDE_LINKS_FILE.parent.is_dir():
        return False, f"Bride project folder missing: `{BRIDE_LINKS_FILE.parent}`"

    existing = ""
    if BRIDE_LINKS_FILE.exists():
        existing = BRIDE_LINKS_FILE.read_text(encoding="utf-8")
        for line in existing.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if _youtube_video_id(line) == vid:
                return False, f"That episode is already in `youtube_links.txt` (video `{vid}`). Re-run the workflow on your Mac if you need a full re-process."

    with BRIDE_LINKS_FILE.open("a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(url.strip() + "\n")

    return True, f"Added Bride of Charlie episode `{vid}` to `youtube_links.txt`."


def _fetch_url_content(url: str, timeout: int = 30) -> str:
    """Fetch URL and extract main text from HTML."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Shiftshapr/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"Fetch failed: {e}") from e
    # Strip HTML to text
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    from html import unescape
    text = unescape(html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:100_000]  # Cap size


def _download_telegram_file(file_id: str) -> Path | None:
    """Download file from Telegram, return temp path. Caller must delete."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return None
    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        if not data.get("ok"):
            return None
        file_path = data["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        out = LOGS_DIR / f"tg_download_{file_id.replace('/', '_')[:40]}.pdf"
        urllib.request.urlretrieve(url, out)
        return out
    except Exception:
        return None


def _send_telegram(text: str, chat_id: str | None = None) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not cid:
        return False
    try:
        import urllib.request
        text = format_channel_message(text)
        chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            data = json.dumps({"chat_id": cid, "text": chunk}).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status != 200:
                    raise RuntimeError(str(r.status))
        return True
    except Exception as e:
        _audit("SEND_FAILED", {"error": str(e)[:200]})
        return False


def _load_knowledge_from_files() -> str:
    """Load knowledge base files into a single string, respecting token limits."""
    ctx = _load_context()
    sources = ctx.get("knowledge_sources")
    if not sources:
        return ""
    if not KNOWLEDGE_DIR.exists():
        return ""
    total = 0
    chunks = []
    if sources == ["*"] or (len(sources) == 1 and sources[0] == "*"):
        files = [p for p in KNOWLEDGE_DIR.rglob("*.md") if p.name != "README.md"]
    else:
        files = [KNOWLEDGE_DIR / s for s in sources if isinstance(s, str)]
    for path in files:
        if not path.exists() or path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        if not text or total >= KNOWLEDGE_MAX_CHARS:
            break
        take = min(len(text), KNOWLEDGE_MAX_CHARS - total)
        chunks.append(f"### {path.name}\n{text[:take]}")
        total += take
    if not chunks:
        return ""
    return "**Knowledge base** (your writing, book, Substack, canvases):\n\n" + "\n\n---\n\n".join(chunks)


def _load_knowledge(query: str | None = None) -> str:
    """Load knowledge: prefer graph RAG when Neo4j has content, else fall back to files."""
    try:
        if str(AGENT_LAB_ROOT) not in sys.path:
            sys.path.insert(0, str(AGENT_LAB_ROOT))
        from agents.shiftshapr.meta_layer_retrieval import retrieve
        graph_content = retrieve(query=query)
        if graph_content:
            return graph_content
    except Exception:
        pass
    return _load_knowledge_from_files()


def _user_context_prompt(query: str | None = None) -> str:
    """Build context string for DeerFlow from user profile, voice, and knowledge."""
    ctx = _load_context()
    parts = []

    # Voice / way of thinking — load from voices/ (e.g. meta_layer_voice.md)
    voice_name = ctx.get("voice_profile")
    if voice_name and VOICE_FILES.get(voice_name):
        path = VOICES_DIR / VOICE_FILES[voice_name]
        if path.exists():
            parts.append(f"**Your voice / way of thinking** (from {path.name}):\n{path.read_text(encoding='utf-8')}")

    # Knowledge base — graph RAG when available, else files
    knowledge = _load_knowledge(query=query)
    if knowledge:
        parts.append(knowledge)

    if ctx.get("communication_style"):
        parts.append(f"Communication style: {ctx['communication_style']}")
    if ctx.get("meta_layer_lens"):
        parts.append(f"Meta-layer lens (judgment filter): {ctx['meta_layer_lens']}")
    if ctx.get("priorities"):
        parts.append(f"Priorities: {', '.join(ctx['priorities'])}")
    if ctx.get("key_projects"):
        parts.append(f"Key projects: {', '.join(ctx['key_projects'])}")
    if ctx.get("preferences"):
        parts.append(f"Preferences: {'; '.join(ctx['preferences'])}")
    if ctx.get("linkedin_mentions"):
        mentions = ctx["linkedin_mentions"]
        if isinstance(mentions, list) and mentions:
            parts.append(f"LinkedIn @mentions (people to tag when posting): {', '.join(mentions)}")
    if ctx.get("publish_profiles"):
        profs = ctx["publish_profiles"]
        if isinstance(profs, list) and profs:
            lines = [f"  - {p.get('destination', '')} (platform={p.get('platform', '')})" for p in profs if isinstance(p, dict) and p.get("destination")]
            if lines:
                parts.append("**Publish profiles** (use these exact destination values in save_draft):\n" + "\n".join(lines))
    if ctx.get("drafts_ready"):
        drafts = ctx["drafts_ready"]
        if isinstance(drafts, list) and drafts:
            blocks = []
            for d in drafts:
                if isinstance(d, dict):
                    name = d.get("name", "?")
                    aliases = d.get("aliases", [])
                    alias_str = f" (aliases: {', '.join(aliases)})" if aliases else ""
                    content = f"**{name}**{alias_str}:\n"
                    if d.get("linkedin_meta_layer_post"):
                        content += "LinkedIn Meta-Layer post text:\n" + d["linkedin_meta_layer_post"] + "\n\n"
                    if d.get("linkedin_personal_quote"):
                        content += "Personal quote: " + d["linkedin_personal_quote"] + "\n\n"
                    if d.get("image"):
                        full_img = str(AGENT_LAB_ROOT / d["image"]) if d["image"] else ""
                        content += f"Image (full path): {full_img}\n"
                    blocks.append(content)
            if blocks:
                instruction = "When user asks to post this draft, use the text above directly. Do NOT ask for clarification — the content is provided. Use Playwright to post to LinkedIn (Meta-Layer page first, then quote from personal)."
                parts.append("**Drafts ready for publishing** — " + instruction + "\n\n" + "\n---\n".join(blocks))
    if ctx.get("notes"):
        parts.append(f"Notes: {ctx['notes']}")
    if not parts:
        return ""
    return "\n\n".join(parts)


def _run_deerflow(prompt: str, timeout: int | None = None) -> str:
    """Invoke DeerFlow for free-form queries.

    Timeout: ``SHIFTSHAPR_DEERFLOW_TIMEOUT`` (seconds) or default 420. Long DP /
    multi-tool runs often need 900–1800+; set in ``.env`` and restart Shiftshapr.
    """
    if timeout is None:
        timeout = int(os.environ.get("SHIFTSHAPR_DEERFLOW_TIMEOUT", "420"))
    user_ctx = _user_context_prompt(query=prompt)
    if user_ctx:
        prompt = f"""You are the user's digital twin (Shiftshapr). You know them well. Use this context:

{user_ctx}

---

**Learn/adjust**: When the user says "remember X", "add to my preferences", "from now on", "adjust", or "learn" — you MUST call shiftshapr_remember(preference="X") first to persist it, then confirm in one short sentence.

**Meta-layer graph**: When the user wants to add a concept, framework, excerpt, or idea to their meta-layer world model — use meta_layer_graph_add(content=..., node_type=concept|framework|chunk|primitive, name=..., source=..., relates_to=...). Use for: "add this to my graph", "capture this concept", "add to meta-layer", "store this framework".

**Subagents**: When delegating tasks, include relevant excerpts from the knowledge base in the task prompt when it would help the subagent reason in the user's voice or use their frameworks.

**LinkedIn/X**: Use Playwright MCP to post to LinkedIn or X (Twitter). Navigate to linkedin.com/feed or x.com, use the post composer, type the content. For @mentions, use the linkedin_mentions list from context.

**Event promo drafts (lu.ma)**: When the user sends a lu.ma event link and asks to create or stage posts:
1. Use Playwright to open the lu.ma URL, extract event title, description, host, and any individual event links
2. Draft LinkedIn posts (Meta-Layer page first, then personal quote) and X posts (main + quote) in Meta-Layer voice
3. Call save_draft for each variant — ALWAYS set destination so the user sees where it will publish:
   - destination="LinkedIn · Meta-Layer Initiative", title="Meta-Layer post"
   - destination="LinkedIn · Daveed Benjamin (personal)", title="Personal quote"
   - destination="X · @shiftshapr", title="Main post"
   - destination="X · @themetalayer (quote)", title="Quote tweet"
4. Include the lu.ma calendar link (e.g. lu.ma/ai-doc) in every post. For known events, use image_path if a promo image exists (e.g. drafts/After_the_Film.png for ai-doc)

**Images**: Use Playwright to open chat.openai.com and ask ChatGPT to generate an image (e.g. "Generate an image of X"). No API key — uses ChatGPT login. Session must include chat.openai.com (log in when running x-login-via-chrome).

---

{prompt}

Respond concisely. Match their communication style."""

    # Ensure PATH includes uv (launchd has minimal env)
    env = dict(os.environ)
    path_parts = env.get("PATH", "").split(os.pathsep)
    for prefix in ("/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/.local/bin")):
        if prefix and prefix not in path_parts:
            path_parts.insert(0, prefix)
    env["PATH"] = os.pathsep.join(filter(None, path_parts))

    # Subprocess guard: allow headroom above DeerFlow's internal timeout (MCP cold start, many steps).
    sub_guard = timeout + max(120, min(timeout // 2, 600))
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "run-deerflow-task.py"), prompt, "--timeout", str(timeout)],
            cwd=str(AGENT_LAB_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=sub_guard,
        )
    except subprocess.TimeoutExpired:
        return "Request timed out. Try a shorter query or try again later."
    if result.returncode != 0:
        err = (result.stderr or "").strip()
        _audit("DEERFLOW_FAILED", {"returncode": result.returncode, "stderr_preview": err[:800]})
        if "timed out" in err.lower() or "TimeoutExpired" in err:
            return "DeerFlow timed out. Try a shorter query or try again."
        # Prefer our one-line summary: "DeerFlow task failed (1): ..."
        for line in err.split("\n"):
            if "DeerFlow task failed (" in line and "):" in line:
                msg = line.split("):", 1)[-1].strip()
                return f"Something went wrong: {msg[:400]}"
        # Fallback: skip boilerplate
        lines = [l for l in err.split("\n") if l.strip() and "[run-deerflow-task]" not in l]
        if lines:
            err = "\n".join(lines[-5:]) if "Traceback" in err else "\n".join(lines[-3:])
        return f"Something went wrong: {err[:400]}" if err else "DeerFlow failed. Check logs/shiftshapr_audit.log — is LangGraph (2024) running?"
    return _clean_deerflow_response(result.stdout.strip() or "No response.")


def _clean_deerflow_response(text: str) -> str:
    """Strip thinking blocks, memory logs, and other debug noise from DeerFlow output."""
    import re

    original = (text or "").strip()
    # Remove <think>...</think> blocks (model reasoning)
    text = re.sub(r"<think>.*?</think>", "", original, flags=re.DOTALL | re.IGNORECASE)
    # Remove memory queue log lines
    text = re.sub(r"Memory update (timer set|queued|Processing).*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Updating memory for thread.*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Memory updated (successfully|skipped).*\n?", "", text, flags=re.IGNORECASE)
    out = text.strip()
    if out:
        return out
    # Whole visible reply was inside  thinking /think  blocks only
    if original:
        blocks = re.findall(r"<think>(.*?)</think>", original, flags=re.DOTALL | re.IGNORECASE)
        inner = "\n\n".join(b.strip() for b in blocks if b.strip())
        if inner:
            return inner[:12000]
        return original[:12000]
    return "No response."


def _cmd_deadlines() -> str:
    data = _load_ledger()
    opps = [o for o in data.get("opportunities", []) if o.get("status") == "open" and o.get("deadline")]
    if not opps:
        return "No open opportunities with deadlines."
    opps.sort(key=lambda x: x.get("deadline", ""))
    lines = ["**Upcoming deadlines**\n"]
    for o in opps[:15]:
        lines.append(f"• {o['deadline']} — {o['name']} ({o.get('type', '')})")
    return "\n".join(lines)


def _cmd_opportunities() -> str:
    data = _load_ledger()
    opps = [o for o in data.get("opportunities", []) if o.get("status") == "open"]
    if not opps:
        return "No open opportunities."
    by_type = {}
    for o in opps:
        t = o.get("type", "other")
        by_type.setdefault(t, []).append(o)
    lines = ["**Open opportunities**\n"]
    for t, items in sorted(by_type.items()):
        lines.append(f"_{t}_")
        for o in items[:5]:
            d = o.get("deadline", "no date")
            lines.append(f"  • {o['name']} — {d}")
    return "\n".join(lines)


def _cmd_brief() -> str:
    """Run daily prep and return/send brief."""
    date_str = datetime.now().strftime("%Y%m%d")
    out_path = LOGS_DIR / f"daily_prep_{date_str}.md"
    try:
        subprocess.run(
            [sys.executable, str(AGENT_LAB_ROOT / "agents" / "protocol" / "protocol_agent.py"), "--protocol", "daily-prep"],
            cwd=str(AGENT_LAB_ROOT),
            capture_output=True,
            timeout=420,
        )
    except subprocess.TimeoutExpired:
        return "Daily prep timed out."
    if out_path.exists():
        return out_path.read_text(encoding="utf-8")[:4000]
    return "Brief not generated. Check logs."


def _cmd_add(args: str) -> str:
    """Add opportunity: /add Name | type | deadline"""
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 2:
        return "Usage: /add Name | type | YYYY-MM-DD\nExample: /add XYZ Grant | grant | 2025-04-15"
    name = parts[0]
    type_ = parts[1] if len(parts) > 1 else "other"
    deadline = parts[2] if len(parts) > 2 else ""
    if not deadline or not re.match(r"\d{4}-\d{2}-\d{2}", deadline):
        return "Deadline must be YYYY-MM-DD"
    try:
        subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "ledger-add.py"), name, "--type", type_, "--deadline", deadline, "--source", "telegram"],
            cwd=str(AGENT_LAB_ROOT),
            capture_output=True,
            timeout=5,
        )
        return f"Added: {name} ({type_}) due {deadline}"
    except Exception as e:
        return f"Failed: {e}"


def _cmd_remember(args: str) -> str:
    """Add to user context: /remember I prefer X"""
    if not args.strip():
        return "Usage: /remember <preference or note>"
    ctx = _load_context() or {}
    prefs = list(ctx.get("preferences", []))
    prefs.append(f"{datetime.now().strftime('%Y-%m-%d')}: {args.strip()}")
    ctx["preferences"] = prefs[-20:]  # Keep last 20
    ctx["updated_at"] = datetime.utcnow().isoformat() + "Z"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONTEXT_PATH.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
    _audit("REMEMBER", {"preference": args.strip()[:200]})
    return "Noted."


def _cmd_add_mention(args: str) -> str:
    """Add person to LinkedIn @mentions: /add_mention John Smith"""
    if not args.strip():
        return "Usage: /add_mention <name> — adds to LinkedIn tagging list"
    ctx = _load_context() or {}
    mentions = list(ctx.get("linkedin_mentions", []))
    name = args.strip()
    if name not in mentions:
        mentions.append(name)
        ctx["linkedin_mentions"] = mentions
        ctx["updated_at"] = datetime.utcnow().isoformat() + "Z"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONTEXT_PATH.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        _audit("ADD_MENTION", {"name": name})
        return f"Added '{name}' to LinkedIn mentions."
    return f"'{name}' already in mentions."


def _cmd_linkedin_mentions() -> str:
    """List LinkedIn @mentions."""
    ctx = _load_context() or {}
    mentions = ctx.get("linkedin_mentions", [])
    if not mentions:
        return "No LinkedIn mentions yet. Use /add_mention Name to add."
    return "**LinkedIn mentions:** " + ", ".join(mentions)


def _run_enrichment(md_path: Path, chat_id: str, source_name: str, n_chunks: str) -> None:
    """Run enrichment script, then send final Telegram message."""
    env = dict(os.environ)
    env["AGENT_LAB_ROOT"] = str(AGENT_LAB_ROOT)
    for prefix in ("/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/.local/bin")):
        if prefix and prefix not in env.get("PATH", "").split(os.pathsep):
            env["PATH"] = f"{prefix}:{env.get('PATH', '')}"
    backend_dir = AGENT_LAB_ROOT / "framework" / "deer-flow" / "backend"
    enrich_cmd = ["uv", "run", "--project", str(backend_dir), "python", str(SCRIPTS_DIR / "enrich-meta-layer-graph.py"), "--file", str(md_path)]
    try:
        result = subprocess.run(enrich_cmd, cwd=str(AGENT_LAB_ROOT), env=env, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        _send_telegram("Enrichment timed out. Chunks are in the graph; run 'enrich graph' later for full extraction.", chat_id)
        return
    except Exception as e:
        _send_telegram(f"Enrichment failed: {e}. Chunks are in the graph.", chat_id)
        return
    out = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    n_nodes = "?"
    m = re.search(r"(\d+)\s+node", stderr)
    if m:
        n_nodes = m.group(1)
    nodes_section = ""
    if "NODES:" in out:
        nodes_section = "\n\n" + out.split("NODES:", 1)[1].strip()
        if len(nodes_section) > 1500:
            nodes_section = nodes_section[:1500] + "\n…"
    msg = f"Done. {n_chunks} chunk(s), {n_nodes} enriched nodes. Ready for retrieval and drafting.{nodes_section}"
    _send_telegram(msg, chat_id)
    _audit("ENRICHED", {"source": source_name, "nodes": n_nodes})


def _handle_document(chat_id: str, document: dict, caption: str) -> None:
    """Process PDF document: download, extract, add to graph if caption says so."""
    if not document:
        return
    file_id = document.get("file_id")
    file_name = document.get("file_name", "document.pdf")
    mime = document.get("mime_type", "")
    if not file_id:
        return
    if "pdf" not in mime.lower() and not file_name.lower().endswith(".pdf"):
        _send_telegram("Only PDFs are supported. Send a PDF with caption 'add to my graph' to ingest.", chat_id)
        return

    caption_lower = (caption or "").lower()
    add_to_graph = "add" in caption_lower and "graph" in caption_lower

    if not add_to_graph:
        _send_telegram("Send with caption 'add to my graph' to ingest this PDF into your meta-layer world model.", chat_id)
        return

    _audit("PDF_RECEIVED", {"chat_id": chat_id, "file_name": file_name})
    _send_telegram("Downloading and extracting PDF…", chat_id)

    tmp_path = _download_telegram_file(file_id)
    if not tmp_path or not tmp_path.exists():
        _send_telegram("Could not download the file. Try again.", chat_id)
        return

    try:
        text = _extract_pdf(tmp_path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    if not text:
        _send_telegram("Could not extract text from this PDF. It may be scanned or image-based.", chat_id)
        return

    # Write to knowledge/docs/
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^\w\-.]", "_", Path(file_name).stem)[:80]
    md_path = DOCS_DIR / f"{safe_name}.md"
    md_path.write_text(f"# {safe_name}\n\n{text}", encoding="utf-8")
    _audit("PDF_SAVED", {"path": str(md_path), "chars": len(text)})

    # Ingest into graph
    env = dict(os.environ)
    env["AGENT_LAB_ROOT"] = str(AGENT_LAB_ROOT)
    path_parts = env.get("PATH", "").split(os.pathsep)
    for prefix in ("/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/.local/bin")):
        if prefix and prefix not in path_parts:
            path_parts.insert(0, prefix)
    env["PATH"] = os.pathsep.join(filter(None, path_parts))

    backend_dir = AGENT_LAB_ROOT / "framework" / "deer-flow" / "backend"
    ingest_cmd = ["uv", "run", "--project", str(backend_dir), "python", str(SCRIPTS_DIR / "ingest-meta-layer-knowledge.py"), "--file", str(md_path)]
    try:
        result = subprocess.run(
            ingest_cmd,
            cwd=str(AGENT_LAB_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        _send_telegram("Ingestion timed out. The PDF may be very large.", chat_id)
        return
    except Exception as e:
        _send_telegram(f"Ingestion failed: {e}", chat_id)
        return

    if result.returncode != 0:
        err = (result.stderr or "").strip()[:300]
        _send_telegram(f"Ingestion failed. Check Neo4j is running (docker compose up -d). {err}", chat_id)
        return

    # Parse output for chunk count
    out = (result.stdout or "").strip()
    n_match = re.search(r"(\d+)\s+chunk", out)
    n_chunks = n_match.group(1) if n_match else "?"
    _send_telegram(f"Added {file_name}. {n_chunks} chunk(s). Enriching (orgs, concepts, opportunities)…", chat_id)
    _run_enrichment(md_path, chat_id, file_name, n_chunks)


def _handle_url_add_to_graph(chat_id: str, url: str, full_text: str) -> None:
    """Fetch URL, extract text, save to knowledge/urls/, ingest into graph. Optionally add opportunity."""
    _audit("URL_ADD_REQUESTED", {"chat_id": chat_id, "url": url[:200]})
    _send_telegram("Fetching and extracting…", chat_id)

    try:
        text = _fetch_url_content(url)
    except Exception as e:
        _send_telegram(f"Could not fetch URL: {e}", chat_id)
        return

    if len(text) < 100:
        _send_telegram("Too little text extracted. The page may be JS-rendered or behind a paywall.", chat_id)
        return

    # Save to knowledge/urls/
    URLS_DIR.mkdir(parents=True, exist_ok=True)
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")[:40]
    path_slug = re.sub(r"[^\w\-]", "_", urlparse(url).path)[:30]
    safe_name = f"{domain}_{path_slug}".strip("_") or "url"
    md_path = URLS_DIR / f"{safe_name}.md"
    md_path.write_text(f"# {url}\n\nSource: {url}\n\n{text}", encoding="utf-8")
    _audit("URL_SAVED", {"path": str(md_path), "chars": len(text)})

    # Ingest into graph
    env = dict(os.environ)
    env["AGENT_LAB_ROOT"] = str(AGENT_LAB_ROOT)
    for prefix in ("/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/.local/bin")):
        if prefix and prefix not in env.get("PATH", "").split(os.pathsep):
            env["PATH"] = f"{prefix}:{env.get('PATH', '')}"
    backend_dir = AGENT_LAB_ROOT / "framework" / "deer-flow" / "backend"
    ingest_cmd = ["uv", "run", "--project", str(backend_dir), "python", str(SCRIPTS_DIR / "ingest-meta-layer-knowledge.py"), "--file", str(md_path)]
    try:
        result = subprocess.run(ingest_cmd, cwd=str(AGENT_LAB_ROOT), env=env, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        _send_telegram("Ingestion timed out.", chat_id)
        return
    except Exception as e:
        _send_telegram(f"Ingestion failed: {e}", chat_id)
        return

    if result.returncode != 0:
        err = (result.stderr or "").strip()[:300]
        _send_telegram(f"Ingestion failed. Is Neo4j running? {err}", chat_id)
        return

    n_match = re.search(r"(\d+)\s+chunk", (result.stdout or ""))
    n_chunks = n_match.group(1) if n_match else "?"
    _send_telegram(f"Added. {n_chunks} chunk(s). Enriching (orgs, concepts, opportunities)…", chat_id)
    _run_enrichment(md_path, chat_id, safe_name, n_chunks)

    _audit("URL_INGESTED", {"url": url[:200], "chunks": n_chunks})


def _handle_bride_episode(chat_id: str, url: str, raw_text: str) -> None:
    """Append YouTube URL to Bride links file; optionally run full monument workflow (long)."""
    _audit("BRIDE_EPISODE_REQUEST", {"url": url[:200], "text": raw_text[:300]})
    ok, msg = _append_bride_youtube_link(url)
    if not ok:
        _send_telegram(msg, chat_id)
        return

    run_wf = os.environ.get("BRIDE_TG_RUN_WORKFLOW", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    _send_telegram(
        msg
        + (
            "\n\nStarting **full Bride workflow** on this machine (fetch → drafts → Neo4j; can take 1–3+ hours). "
            "I’ll send the tail of the log when it finishes."
            if run_wf
            else "\n\n`BRIDE_TG_RUN_WORKFLOW=0` — link saved only. Run `run_ideal_workflow.sh` when ready."
        ),
        chat_id,
    )

    if not run_wf:
        _audit("BRIDE_LINK_ONLY", {"url": url[:120]})
        return

    if not BRIDE_WORKFLOW_SCRIPT.is_file():
        _send_telegram(f"Workflow script missing: `{BRIDE_WORKFLOW_SCRIPT}`", chat_id)
        return

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"bride_workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log"
    env = dict(os.environ)
    env["AGENT_LAB_ROOT"] = str(AGENT_LAB_ROOT)
    for prefix in ("/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/.local/bin")):
        if prefix and prefix not in env.get("PATH", "").split(os.pathsep):
            env["PATH"] = f"{prefix}:{env.get('PATH', '')}"
    backend_dir = AGENT_LAB_ROOT / "framework" / "deer-flow" / "backend"
    cmd = ["uv", "run", "--project", str(backend_dir), "python", "-u", str(BRIDE_WORKFLOW_SCRIPT)]

    try:
        with open(log_path, "w", encoding="utf-8") as logf:
            result = subprocess.run(
                cmd,
                cwd=str(AGENT_LAB_ROOT),
                env=env,
                stdout=logf,
                stderr=subprocess.STDOUT,
                timeout=None,
            )
        try:
            full = log_path.read_text(encoding="utf-8", errors="replace")
            tail = full[-3200:] if len(full) > 3200 else full
        except OSError:
            tail = "(could not read log)"
        code = result.returncode
        status = "Finished OK." if code == 0 else f"Exited with code {code}."
        _send_telegram(f"{status}\nLog file: `{log_path.name}`\n\n--- tail ---\n{tail}", chat_id)
        _audit("BRIDE_WORKFLOW_DONE", {"returncode": code, "log": str(log_path)})
    except Exception as e:
        _send_telegram(f"Bride workflow error: {e}", chat_id)
        _audit("BRIDE_WORKFLOW_ERR", {"error": str(e)[:300]})


def _handle_message(chat_id: str, text: str) -> None:
    """Process message and send reply. Runs in background thread."""
    _audit("MESSAGE_RECEIVED", {"chat_id": chat_id, "text": text[:500]})

    text = (text or "").strip()
    if not text:
        return

    reply = ""
    cmd, cmd_tail = _telegram_cmd_and_tail(text)

    if cmd == "/deadlines":
        reply = _cmd_deadlines()
        _audit("CMD_DEADLINES", {})
    elif cmd == "/opportunities":
        reply = _cmd_opportunities()
        _audit("CMD_OPPORTUNITIES", {})
    elif cmd == "/brief":
        reply = _cmd_brief()
        _audit("CMD_BRIEF", {})
    elif cmd == "/add":
        reply = _cmd_add(cmd_tail)
        _audit("CMD_ADD", {"args": cmd_tail[:200]})
    elif cmd == "/remember":
        reply = _cmd_remember(cmd_tail)
    elif cmd == "/bride":
        # `/bride`, `/bride help`, or `/bride@BotName` → show options; URL on same line → run
        wants_help = cmd_tail.lower() in ("", "help", "options", "?")
        b_url = None if wants_help else _extract_url(cmd_tail)
        if wants_help or not b_url:
            reply = (
                "**Bride of Charlie** — options\n\n"
                "• `/bride` — show this help (same as `/bride help`)\n"
                "• `/bride <YouTube URL>` — queue episode + run full workflow on this server\n"
                "  Example: `/bride https://www.youtube.com/watch?v=xxxxxxxxxxx`\n"
                "• One message with **Bride** + **Charlie** and a YouTube link also works\n"
                "• `BRIDE_TG_RUN_WORKFLOW=0` in `.env` = only append link, you run workflow yourself\n"
                "• Logs: `logs/bride_workflow_*.log` — I’ll send a tail when a run finishes\n"
            )
        else:
            threading.Thread(target=_handle_bride_episode, args=(chat_id, b_url, text), daemon=True).start()
            return
    elif cmd == "/add_mention":
        reply = _cmd_add_mention(cmd_tail)
        _audit("CMD_ADD_MENTION", {"args": cmd_tail[:100]})
    elif cmd == "/linkedin_mentions":
        reply = _cmd_linkedin_mentions()
        _audit("CMD_LINKEDIN_MENTIONS", {})
    elif cmd == "/help":
        reply = """**Shiftshapr** — your digital twin
/deadlines — Upcoming deadlines
/opportunities — Open opportunities
/brief — Daily prep (calendar + email)
/add Name | type | YYYY-MM-DD — Add opportunity
/remember <note> — Add to your profile
/add_mention Name — Add to LinkedIn tagging list
/linkedin_mentions — List people to tag on LinkedIn
/bride — Bride of Charlie options; `/bride <YouTube URL>` queues episode + workflow (BRIDE_TG_RUN_WORKFLOW=0 = link only)
**URL/PDF + add to graph** — Paste URL or send PDF with caption "add to my graph" → ingest + enrich (orgs, concepts, opportunities)
Or just ask anything — I'll use DeerFlow."""
        _audit("CMD_HELP", {})
    else:
        # Bride of Charlie: natural language + YouTube URL
        url = _extract_url(text)
        if url and _youtube_video_id(url) and _message_is_bride_episode_request(text):
            threading.Thread(target=_handle_bride_episode, args=(chat_id, url, text), daemon=True).start()
            return
        # URL + add to graph?
        txt_lower = text.lower()
        if url and ("add" in txt_lower and "graph" in txt_lower):
            _handle_url_add_to_graph(chat_id, url, text)
            return
        # Free-form: DeerFlow
        _audit("FREE_FORM", {"text": text[:300]})
        if os.environ.get("SHIFTSHAPR_DEERFLOW_ACK", "").strip().lower() in ("1", "true", "yes", "on"):
            _send_telegram("Working on it — long DeerFlow jobs can take several minutes.", chat_id)
        reply = _run_deerflow(text)
        _audit("DEERFLOW_RESPONSE", {"length": len(reply)})

    if reply:
        _send_telegram(reply, chat_id)
        _audit("REPLY_SENT", {"length": len(reply)})


def _process_update(update: dict) -> None:
    """Extract message and dispatch."""
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    chat_id = str(msg.get("chat", {}).get("id", ""))
    if not chat_id:
        return

    # Optional: restrict to TELEGRAM_CHAT_ID
    allowed = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if allowed and chat_id != allowed:
        _audit("REJECTED_CHAT", {"chat_id": chat_id, "reason": "not_allowed"})
        return

    # Document (e.g. PDF) with optional caption
    doc = msg.get("document")
    if doc:
        caption = msg.get("caption", "")
        threading.Thread(target=_handle_document, args=(chat_id, doc, caption), daemon=True).start()
        return

    text = msg.get("text", "")
    threading.Thread(target=_handle_message, args=(chat_id, text), daemon=True).start()


def create_app():
    """Flask app for webhook."""
    try:
        from flask import Flask, request
    except ImportError:
        print("[shiftshapr] Install flask: pip install flask", file=sys.stderr)
        sys.exit(1)

    app = Flask(__name__)

    @app.route("/webhook", methods=["POST"])
    def webhook():
        # Return 200 immediately; process in background
        try:
            data = request.get_json(force=True, silent=True) or {}
        except Exception:
            data = {}
        threading.Thread(target=_process_update, args=(data,), daemon=True).start()
        return "", 200

    @app.route("/health", methods=["GET"])
    def health():
        return "ok", 200

    return app


def run_webhook(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run webhook server."""
    _load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[shiftshapr] Set TELEGRAM_BOT_TOKEN in .env", file=sys.stderr)
        sys.exit(1)

    app = create_app()
    _audit("START", {"host": host, "port": port})
    print(f"[shiftshapr] Webhook on http://{host}:{port}/webhook", file=sys.stderr)
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8080)
    run_webhook(host=p.parse_args().host, port=p.parse_args().port)
