"""
Transcript Protocol
Converts raw transcript files into structured markdown for inscription.

Output format per file:
  - Title
  - Summary
  - Key Ideas
  - Important Quotes
  - Structured Notes
  - Tags
"""

from __future__ import annotations

import os
import re
import textwrap
from datetime import datetime
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY  = os.getenv("OPENAI_API_KEY",  "fake")
MODEL_NAME      = os.getenv("MODEL_NAME",       "qwen2.5:7b")

INPUT_DIR  = Path(__file__).parent / "input"
OUTPUT_DIR = Path(__file__).parent / "output"
LOG_DIR    = Path(__file__).parent / "logs"

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        api_key=OLLAMA_API_KEY,
        temperature=0.2,
        max_tokens=4096,
    )

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""
    You are a precise transcript analyst. Your task is to convert raw transcript
    text into a structured markdown document.

    Output ONLY the following markdown structure — no preamble, no commentary:

    # [Title]

    ## Summary
    [2–4 sentence summary of the entire transcript]

    ## Key Ideas
    - [Idea 1]
    - [Idea 2]
    - [Idea 3]
    (3–7 items)

    ## Important Quotes
    > "[Quote 1]"
    > "[Quote 2]"
    (2–5 direct quotes)

    ## Structured Notes
    ### [Topic A]
    [notes]

    ### [Topic B]
    [notes]
    (2–4 topics)

    ## Tags
    `tag1` `tag2` `tag3` `tag4` `tag5`
    (5–8 lowercase hyphenated tags)
""").strip()

def build_user_message(transcript: str) -> str:
    return f"Convert this transcript into the required structured markdown:\n\n---\n{transcript}\n---"

# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_transcript(path: Path, llm: ChatOpenAI) -> str:
    """Run the transcript protocol on a single file and return markdown."""
    raw = path.read_text(encoding="utf-8")
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_user_message(raw)),
    ]
    response = llm.invoke(messages)
    return response.content.strip()


def derive_title(markdown: str, fallback: str) -> str:
    """Extract title from first H1 heading or fall back to filename."""
    match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def run_transcript_protocol() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    transcripts = sorted(INPUT_DIR.glob("*.txt")) + sorted(INPUT_DIR.glob("*.md"))

    if not transcripts:
        print(f"[protocol] No transcript files found in {INPUT_DIR}")
        print("[protocol] Place .txt or .md files there and re-run.")
        return

    llm = get_llm()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"run_{timestamp}.log"
    log_lines: list[str] = []

    print(f"[protocol] Found {len(transcripts)} transcript(s) — processing…")

    for i, path in enumerate(transcripts, 1):
        print(f"  [{i}/{len(transcripts)}] {path.name}")
        try:
            markdown = process_transcript(path, llm)
            title    = derive_title(markdown, path.stem)
            out_name = re.sub(r"[^\w\-]", "_", title.lower())[:60]
            out_path = OUTPUT_DIR / f"{out_name}.md"
            out_path.write_text(markdown, encoding="utf-8")
            log_lines.append(f"OK  {path.name} → {out_path.name}")
            print(f"       → {out_path.name}")
        except Exception as exc:
            log_lines.append(f"ERR {path.name}: {exc}")
            print(f"       ERR: {exc}")

    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\n[protocol] Done. Log: {log_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_transcript_protocol()
