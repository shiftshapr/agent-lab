"""
Episode Analysis Protocol
Processes episode transcripts into structured investigative records for inscription.
Supports global ledger continuation across episodes.

Projects: projects/monuments/{project_name}/
  - brief/       Project briefing (protocol context)
  - templates/   Output format template
  - input/       Raw episode transcripts
  - output/      Structured episode analyses
  - logs/        Run logs
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

AGENT_LAB_ROOT = Path(__file__).parent.parent.parent
PROTOCOLS_DIR  = Path(__file__).parent
PROJECTS_DIR   = AGENT_LAB_ROOT / "projects" / "monuments"


def get_project_path(project: str) -> Path:
    path = PROJECTS_DIR / project
    if not path.is_dir():
        raise FileNotFoundError(f"Project not found: {path}")
    return path


# ---------------------------------------------------------------------------
# Ledger state (cross-episode numbering)
# ---------------------------------------------------------------------------

ID_PATTERNS = {
    "artifact": re.compile(r"A-(\d+(?:\.\d+)?)"),
    "claim":    re.compile(r"C-(\d+)"),
    "node":     re.compile(r"N-(\d+)"),
}


def scan_output_for_ids(output_dir: Path) -> dict[str, float]:
    """Scan episode output files for highest A-, C-, N- IDs. Excludes cross_episode_*.md."""
    highest = {"artifact": 1000.0, "claim": 1000, "node": 0, "node_investigation": 1000}

    for path in output_dir.glob("episode_*.md"):
        text = path.read_text(encoding="utf-8")
        for kind, pattern in ID_PATTERNS.items():
            for m in pattern.finditer(text):
                try:
                    val = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
                    if kind == "node":
                        if val >= 1000:
                            if val > highest["node_investigation"]:
                                highest["node_investigation"] = val
                            continue
                    current = highest[kind]
                    if val > current:
                        highest[kind] = val
                except (ValueError, TypeError):
                    pass

    return highest


def format_ledger_context(highest: dict[str, float]) -> str:
    next_artifact = highest["artifact"] + 0.01
    next_claim = int(highest["claim"]) + 1
    next_node = int(highest["node"]) + 1
    next_node_inv = int(highest["node_investigation"]) + 1
    # Use 2 decimal places (e.g. A-1001.90) to avoid ambiguity with A-1001.9 vs A-1001.10
    art_str = f"A-{next_artifact:.2f}"
    return (
        f"LEDGER CONTINUATION (do not restart numbering):\n"
        f"- Next Artifact ID: {art_str}\n"
        f"- Next Claim ID: C-{next_claim}\n"
        f"- Next Node ID (people): N-{next_node}\n"
        f"- Next Node ID (investigation targets): N-{next_node_inv}\n"
        f"- Reuse existing node IDs when referencing known entities. Never renumber.\n"
    )


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

def get_llm() -> ChatOpenAI:
    """Use MiniMax if MINIMAX_API_KEY is set (faster); otherwise Ollama."""
    if os.getenv("MINIMAX_API_KEY"):
        return ChatOpenAI(
            model=os.getenv("MINIMAX_MODEL", "MiniMax-M2.5"),
            base_url="https://api.minimax.io/v1",
            api_key=os.getenv("MINIMAX_API_KEY"),
            temperature=0.2,
            max_tokens=8192,
        )
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "qwen2.5:7b"),
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "fake"),
        temperature=0.2,
        max_tokens=8192,
    )


# ---------------------------------------------------------------------------
# Protocol execution
# ---------------------------------------------------------------------------

def build_system_prompt(protocol_md: str, template_md: str, ledger_context: str) -> str:
    return (
        "You are an investigative analysis agent following the Episode Analysis Protocol.\n\n"
        "PROTOCOL RULES (follow exactly):\n"
        "---\n"
        f"{protocol_md}\n"
        "---\n\n"
        f"{ledger_context}\n\n"
        "OUTPUT FORMAT (use this structure):\n"
        "---\n"
        f"{template_md}\n"
        "---\n\n"
        "Output ONLY the structured markdown. No preamble, no commentary. "
        "Preserve exact names. Artifact-first. No rhetorical drift."
    )


def process_episode(
    transcript: str,
    episode_num: int,
    llm: ChatOpenAI,
    system_prompt: str,
) -> str:
    user_msg = (
        f"Analyze Episode {episode_num} using the protocol.\n\n"
        f"TRANSCRIPT:\n---\n{transcript}\n---"
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_msg),
    ]
    response = llm.invoke(messages)
    text = response.content.strip()
    # Strip <think>...</think>
    if "<think>" in text and "</think>" in text:
        end_tag = "</think>"
        idx = text.find(end_tag)
        if idx >= 0:
            text = text[idx + len(end_tag) :].strip()
    return text


def run_episode_analysis_protocol(project: str | None = None) -> None:
    project = project or os.getenv("EPISODE_ANALYSIS_PROJECT", "bride_of_charlie")
    proj_path = get_project_path(project)
    input_subdir  = os.getenv("EPISODE_ANALYSIS_INPUT", "input")
    output_subdir  = os.getenv("EPISODE_ANALYSIS_OUTPUT", "output")
    input_dir  = proj_path / input_subdir
    output_dir = proj_path / output_subdir
    log_dir    = proj_path / "logs"
    brief_dir  = proj_path / "brief"
    tmpl_dir   = proj_path / "templates"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Load protocol (prefer project brief, fallback to shared protocol)
    protocol_path = brief_dir / "monument_zero_briefing.md"
    if not protocol_path.exists():
        protocol_path = PROTOCOLS_DIR / "ep_protocol_v1.md"
    protocol_md = protocol_path.read_text(encoding="utf-8")

    # Load template
    template_path = tmpl_dir / "bride_charlie_episode_analysis.md"
    if not template_path.exists():
        template_path = next(tmpl_dir.glob("*.md"), None)
    template_md = template_path.read_text(encoding="utf-8") if template_path else ""

    # Ledger state
    highest = scan_output_for_ids(output_dir)
    ledger_context = format_ledger_context(highest)

    transcripts = sorted(input_dir.glob("*.txt")) + sorted(input_dir.glob("*.md"))
    if not transcripts:
        print(f"[episode-analysis] No transcripts in {input_dir}")
        print("  Place .txt or .md files there and re-run.")
        return

    llm = get_llm()
    system_prompt = build_system_prompt(protocol_md, template_md, ledger_context)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"run_{timestamp}.log"
    log_lines = []

    print(f"[episode-analysis] Project: {project}")
    print(f"[episode-analysis] Ledger: A-{highest['artifact']}, C-{highest['claim']}, N-{highest['node']}, N-{highest['node_investigation']}+")
    print(f"[episode-analysis] Processing {len(transcripts)} episode(s)...")

    force = os.getenv("EPISODE_ANALYSIS_FORCE", "").lower() in ("1", "true", "yes")
    if force:
        print("[episode-analysis] FORCE mode: re-running all episodes (ignoring existing drafts)")

    for i, path in enumerate(transcripts, 1):
        episode_num = i
        out_name = f"episode_{episode_num:03d}_{path.stem}.md"
        out_path = output_dir / out_name
        if out_path.exists() and not force:
            print(f"  [{i}/{len(transcripts)}] {path.name} — SKIP (already done)")
            log_lines.append(f"SKIP {path.name} (exists)")
            continue
        print(f"  [{i}/{len(transcripts)}] {path.name}")
        try:
            raw = path.read_text(encoding="utf-8")
            markdown = process_episode(raw, episode_num, llm, system_prompt)
            out_path.write_text(markdown, encoding="utf-8")
            log_lines.append(f"OK  {path.name} -> {out_name}")
            print(f"       -> {out_name}")

            # Update ledger for next episode (re-scan this output)
            highest = scan_output_for_ids(output_dir)
            ledger_context = format_ledger_context(highest)
            system_prompt = build_system_prompt(protocol_md, template_md, ledger_context)
        except Exception as exc:
            log_lines.append(f"ERR {path.name}: {exc}")
            print(f"       ERR: {exc}")

    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\n[episode-analysis] Done. Log: {log_path}")


if __name__ == "__main__":
    run_episode_analysis_protocol()
