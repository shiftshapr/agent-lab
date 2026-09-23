#!/usr/bin/env python3
"""Convert plain transcript text to transcripts_corrected episode_0NN_<id>.txt format."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
AGENT_TOOLS = Path("/home/ubuntu/.cursor/projects/workspace/agent-tools")

# monument_ep, youtube_id, source filename under agent-tools, optional duration seconds
EPISODES = [
    (9, "_dRaEO47-co", "44850ea4-6000-4d4e-aaff-e545dc27dc7a.txt", 23 * 60 + 48),
    (10, "czVBmqZP6Ss", "30f5f0ab-cf97-4cbb-99e0-087c5f922a06.txt", 69 * 60 + 53),
    (11, "q7f8r-THr84", "5c0738ff-0ce8-4330-ab03-08c63353f022.txt", None),
    (12, "2WEHTk0Xewg", "c21fbb0f-c95d-474e-9edb-53b1f15d56f8.txt", None),
    (13, "sreYYcID-QY", "16157da4-5b4b-4049-8391-a5083ce722a0.txt", None),
    (14, "aDlhjfW6hz8", "4bab91a2-3d69-473c-bdf1-bf2074ddf068.txt", None),
    (15, "ja26iltROkM", "3830d86d-5c98-449a-9011-d4afcfaff6dd.txt", None),
    (16, "UBkFkg4UNY8", "3a948baf-b69d-438a-8f7f-04fa8f0d0840.txt", None),
    (17, "QZWSsq8ZWzw", "2ccf575a-9816-4f17-86b4-8a08879bf4b7.txt", None),
    (18, "K5GjF53bfN4", "31967698-f698-49eb-b276-310707ebd6ef.txt", None),
]

WPM = 155
MAX_WORDS_PER_LINE = 14


def extract_body(text: str) -> str:
    if "## Transcript" in text:
        return text.split("## Transcript", 1)[1].strip()
    if text.startswith("# "):
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip() == "## Transcript":
                return "\n".join(lines[i + 1 :]).strip()
        # skip markdown header block until blank line after metadata
        start = 0
        for i, line in enumerate(lines):
            if i > 0 and line.strip() == "" and not lines[i - 1].startswith("-"):
                start = i + 1
                break
        return "\n".join(lines[start:]).strip()
    return text.strip()


def words_to_lines(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    raw_words = text.split(" ")
    lines: list[str] = []
    buf: list[str] = []
    for w in raw_words:
        buf.append(w)
        if len(buf) >= MAX_WORDS_PER_LINE and w.endswith((".", "?", "!", ",")):
            lines.append(" ".join(buf))
            buf = []
    if buf:
        lines.append(" ".join(buf))
    return lines


def format_ts(seconds: int) -> str:
    seconds = max(0, seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def stamp_lines(lines: list[str], duration_sec: int) -> str:
    total_words = sum(len(ln.split()) for ln in lines) or 1
    acc_words = 0
    out: list[str] = []
    for ln in lines:
        word_n = len(ln.split())
        ts = int(duration_sec * acc_words / total_words)
        acc_words += word_n
        out.append(f"[{format_ts(ts)}] {ln}")
    return "\n".join(out) + "\n"


def duration_for(text: str, explicit: int | None) -> int:
    if explicit is not None:
        return explicit
    m = re.search(r"- \*\*Length\*\*:\s*(\d+):(\d+)", text)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    words = len(re.findall(r"\w+", text))
    return max(600, int(words / WPM * 60))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tools-dir", type=Path, default=AGENT_TOOLS)
    args = ap.parse_args()
    raw_dir = PROJECT / "transcripts"
    corr_dir = PROJECT / "transcripts_corrected"
    raw_dir.mkdir(parents=True, exist_ok=True)
    corr_dir.mkdir(parents=True, exist_ok=True)
    for ep, vid, src_name, dur in EPISODES:
        src = args.tools_dir / src_name
        if not src.is_file():
            raise SystemExit(f"Missing source: {src}")
        text = src.read_text(encoding="utf-8")
        body = extract_body(text)
        duration = duration_for(text, dur)
        lines = words_to_lines(body)
        stamped = stamp_lines(lines, duration)
        name = f"episode_{ep:03d}_{vid}.txt"
        for d in (raw_dir, corr_dir):
            (d / name).write_text(stamped, encoding="utf-8")
        print(f"ep {ep:03d} {vid} lines={len(lines)} dur~{duration}s -> {name}")


if __name__ == "__main__":
    main()
