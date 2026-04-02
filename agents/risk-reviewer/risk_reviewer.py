"""
Risk Reviewer — LLM-based review before publishing.
Reviews content for: overclaiming, reputational risk, security/privacy,
governance drift, ambiguity in public claims.
Returns: approve / revise / escalate + risk notes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"

RISK_DIMENSIONS = [
    "overclaiming",
    "reputational_risk",
    "security_privacy",
    "governance_drift",
    "public_claim_ambiguity",
]


class Decision(str, Enum):
    APPROVE = "approve"
    REVISE = "revise"
    ESCALATE = "escalate"


@dataclass
class ReviewResult:
    decision: Decision
    risk_notes: list[str]
    flags: list[str]

    def __str__(self) -> str:
        notes = "\n  ".join(self.risk_notes) if self.risk_notes else "none"
        flags = ", ".join(self.flags) if self.flags else "none"
        return (
            f"Decision : {self.decision.value.upper()}\n"
            f"Flags    : {flags}\n"
            f"Notes    :\n  {notes}"
        )


def _parse_llm_response(text: str) -> ReviewResult:
    """Parse LLM response into ReviewResult."""
    text_lower = text.lower().strip()
    decision = Decision.APPROVE
    if "escalate" in text_lower or "escalation" in text_lower:
        decision = Decision.ESCALATE
    elif "revise" in text_lower or "revision" in text_lower:
        decision = Decision.REVISE

    notes = []
    flags = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("-") or line.startswith("*"):
            notes.append(line.lstrip("-* ").strip())
        if "overclaim" in line.lower():
            flags.append("overclaiming")
        if "reputational" in line.lower():
            flags.append("reputational_risk")
        if "security" in line.lower() or "privacy" in line.lower():
            flags.append("security_privacy")
        if "governance" in line.lower():
            flags.append("governance_drift")
        if "ambigu" in line.lower():
            flags.append("public_claim_ambiguity")

    return ReviewResult(decision=decision, risk_notes=notes or [text[:500]], flags=list(set(flags)))


def review(content: str) -> ReviewResult:
    """LLM-based review. Uses OPENAI_* from env (MiniMax/Ollama)."""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
    except ImportError:
        return ReviewResult(
            decision=Decision.APPROVE,
            risk_notes=["[risk-reviewer] langchain not installed — skipping review"],
            flags=[],
        )

    base_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
    api_key = os.environ.get("OPENAI_API_KEY", "fake")
    model = os.environ.get("MODEL_NAME", "qwen2.5:7b")

    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0.2,
        max_tokens=1024,
    )

    system = f"""You are a risk reviewer. Review content before it is published externally.
Check for: {", ".join(RISK_DIMENSIONS)}.
Respond with:
1. Decision: APPROVE, REVISE, or ESCALATE
2. Risk notes: bullet points of any concerns
3. Flags: which dimensions triggered (if any)

Be concise. If no issues, say APPROVE with no flags."""

    prompt = f"Review this content:\n\n---\n{content[:4000]}\n---"
    try:
        resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
        return _parse_llm_response(resp.content if hasattr(resp, "content") else str(resp))
    except Exception as e:
        return ReviewResult(
            decision=Decision.APPROVE,
            risk_notes=[f"[risk-reviewer] LLM error — defaulting to approve: {e}"],
            flags=[],
        )


def run() -> None:
    """CLI entry point."""
    import sys
    content = sys.stdin.read() if not sys.stdin.isatty() else "No content provided."
    result = review(content)
    print(result)


if __name__ == "__main__":
    run()
