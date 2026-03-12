"""
Cross-episode analysis.
Reads ALL episode inscriptions from drafts/ (or output/), produces synthesis for review.
Always uses every episode_*.md file present at run time.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent.parent.parent / ".env")
except ImportError:
    pass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

PROJECT_DIR = Path(__file__).parent.parent
DRAFTS_DIR = PROJECT_DIR / "drafts"
OUTPUT_DIR = PROJECT_DIR / "output"

SYSTEM_PROMPT = """You are an investigative analyst performing CROSS-EPISODE synthesis.

You will receive N episode analyses (each with Artifacts, Nodes, Claims). You MUST synthesize across ALL of them.

Your output must be a NEW document that:
1. **Patterns** — Identifies themes, connections, and recurring evidence across ALL episodes
2. **Investigative pressure** — Where evidence converges on specific nodes/claims across multiple episodes
3. **Contradictions** — Surfaces contradictions (only when both sides are artifact-anchored) across the series
4. **Cumulative ledger** — Summary of total artifacts, claims, nodes across all episodes
5. **Open questions** — Gaps, unresolved threads, or areas needing further investigation

CRITICAL: Do NOT repeat or reproduce a single episode's analysis. Your output is a SYNTHESIS across all episodes. Reference specific episode numbers and artifact IDs when citing evidence."""


def get_llm():
    """Use MiniMax if MINIMAX_API_KEY is set; otherwise Ollama."""
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


def main() -> None:
    # Prefer drafts, fallback to output — always use ALL episode_*.md files present
    source_dir = DRAFTS_DIR if DRAFTS_DIR.exists() else OUTPUT_DIR
    source_dir.mkdir(parents=True, exist_ok=True)

    episodes = sorted(source_dir.glob("episode_*.md"))
    if not episodes:
        print(f"[cross-episode] No episode inscriptions in {source_dir}")
        print("  Run episode analysis first.")
        return

    print(f"[cross-episode] Using {len(episodes)} episode(s): {[p.name for p in episodes]}")

    combined = []
    for i, path in enumerate(episodes, 1):
        combined.append(f"## Episode {i}: {path.stem}\n\n{path.read_text(encoding='utf-8')}\n")

    user_msg = (
        f"CROSS-EPISODE ANALYSIS — Synthesize across ALL {len(episodes)} episodes below.\n\n"
        + "\n---\n".join(combined)
    )

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])

    text = response.content.strip()
    # Strip <think>...</think>
    if "<think>" in text and "</think>" in text:
        end_tag = "</think>"
        idx = text.find(end_tag)
        if idx >= 0:
            text = text[idx + len(end_tag) :].strip()

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DRAFTS_DIR / "cross_episode_analysis_draft.md"
    out_path.write_text(text, encoding="utf-8")

    print(f"[cross-episode] Draft saved: {out_path}")
    print("  Review and log any changes in protocol_updates/")


if __name__ == "__main__":
    main()
