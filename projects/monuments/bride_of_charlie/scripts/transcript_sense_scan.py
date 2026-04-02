#!/usr/bin/env python3
"""
LLM pass: find stretches of transcript that read like garbled STT / nonsense (not “I disagree”).

Uses the same OpenAI-compatible stack as agent-lab:
  MINIMAX_API_KEY (+ MINIMAX_MODEL)  OR  OPENAI_BASE_URL + OPENAI_API_KEY + MODEL_NAME

Env:
  TRANSCRIPT_SENSE_MAX_BATCHES   default 0  (= scan entire episode; set N>0 to cap)
  TRANSCRIPT_SENSE_TEMPERATURE   default 0.05
  TRANSCRIPT_SENSE_MAX_TOKENS    default 4096 per request

Canonical spellings: config/transcript_canonical_glossary.json (injected into system prompt).

Importable: sense_scan_episode(project_dir, episode, **kwargs) -> dict

Apply (optional): after scan, replace transcript text only when each finding's excerpt
appears exactly once (safe literal replace). Use CLI --apply-inscription or API body.apply.
Run sync_transcript_hashes.py after a real apply so episode JSON hashes stay valid.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent.parent

_CAPTION_LINE = re.compile(
    r"^\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]\s*(.*)$",
)


def _segment_seconds(g1: str, g2: str, g3: str | None) -> int:
    if g3 is not None:
        return int(g1) * 3600 + int(g2) * 60 + int(g3)
    return int(g1) * 60 + int(g2)


def segment_transcript(text: str) -> list[dict[str, Any]]:
    """Split into caption-timed segments (preserves order)."""
    segments: list[dict[str, Any]] = []
    cur: dict[str, Any] = {"label": None, "seconds": 0, "lines": []}
    for line in text.splitlines():
        m = _CAPTION_LINE.match(line)
        if m:
            if cur["lines"]:
                t = "\n".join(cur["lines"]).strip()
                if t:
                    segments.append(
                        {
                            "label": cur["label"],
                            "seconds": cur["seconds"],
                            "text": t,
                        }
                    )
            g1, g2, g3, rest = m.group(1), m.group(2), m.group(3), (m.group(4) or "").strip()
            label = f"[{g1}:{g2}" + (f":{g3}]" if g3 else "]")
            cur = {
                "label": label,
                "seconds": _segment_seconds(g1, g2, g3),
                "lines": [rest] if rest else [],
            }
        else:
            cur["lines"].append(line)
    if cur["lines"]:
        t = "\n".join(cur["lines"]).strip()
        if t:
            segments.append(
                {
                    "label": cur["label"],
                    "seconds": cur["seconds"],
                    "text": t,
                }
            )
    return segments


def _batch_segments(
    segments: list[dict[str, Any]],
    *,
    max_segments_per_batch: int = 4,
    max_chars_per_batch: int = 3200,
) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    cur_len = 0
    for s in segments:
        piece = (s.get("text") or "") + "\n"
        if cur and (
            len(cur) >= max_segments_per_batch
            or cur_len + len(piece) > max_chars_per_batch
        ):
            batches.append(cur)
            cur = []
            cur_len = 0
        cur.append(s)
        cur_len += len(piece)
    if cur:
        batches.append(cur)
    return batches


def _get_llm_config() -> tuple[str, str, str]:
    if os.getenv("MINIMAX_API_KEY"):
        return (
            "https://api.minimax.io/v1",
            os.getenv("MINIMAX_API_KEY", ""),
            os.getenv("MINIMAX_MODEL", "MiniMax-M2.5"),
        )
    return (
        os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1").rstrip("/"),
        os.getenv("OPENAI_API_KEY", "fake"),
        os.getenv("MODEL_NAME", "qwen2.5:7b"),
    )


def _chat(messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str:
    try:
        import urllib.error
        import urllib.request
    except ImportError:
        raise RuntimeError("urllib not available")
    base, key, model = _get_llm_config()
    if not key or key == "fake":
        raise RuntimeError(
            "No API key: set MINIMAX_API_KEY or OPENAI_API_KEY (see agent-lab .env)"
        )
    url = base + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""


def _strip_think(text: str) -> str:
    """Strip <think>…</think> wrapper (same convention as episode_analysis_protocol)."""
    open_t = chr(60) + "think" + chr(62)
    close_t = chr(60) + "/think" + chr(62)
    if open_t in text and close_t in text:
        idx = text.rfind(close_t)
        if idx >= 0:
            return text[idx + len(close_t) :].strip()
    return text.strip()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    t = _strip_think(text)
    if "```" in t:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t, re.I)
        if m:
            t = m.group(1).strip()
    t = t.strip()
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    i = t.find("{")
    j = t.rfind("}")
    if i >= 0 and j > i:
        try:
            return json.loads(t[i : j + 1])
        except json.JSONDecodeError:
            return None
    return None


def _load_glossary_block(project: Path) -> str:
    path = project / "config" / "transcript_canonical_glossary.json"
    if not path.is_file():
        return ""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    lines: list[str] = []
    if doc.get("series"):
        lines.append(f"Series context: {doc['series']}")
    h = doc.get("host")
    if isinstance(h, dict) and h.get("canonical"):
        stt = ", ".join(h.get("stt_often") or [])
        lines.append(f"Host: {h['canonical']}" + (f" (STT may write: {stt})" if stt else ""))
    for p in doc.get("family_core") or []:
        if not isinstance(p, dict):
            continue
        c = p.get("canonical", "")
        if not c:
            continue
        oft = ", ".join(p.get("stt_often") or [])
        note = p.get("notes") or ""
        lines.append(f"- {c}" + (f" — often misheard as: {oft}" if oft else "") + (f" — {note}" if note else ""))
    inst = doc.get("institutions_and_programs") or []
    if inst:
        lines.append("Institutions / programs (canonical spellings; flag STT variants):")
        for p in inst:
            if not isinstance(p, dict):
                continue
            c = p.get("canonical", "")
            if not c:
                continue
            oft = ", ".join(p.get("stt_often") or [])
            note = p.get("notes") or ""
            lines.append(f"- {c}" + (f" ← STT: {oft}" if oft else "") + (f" ({note})" if note else ""))
    lines.append("Surname / STT:")
    for s in doc.get("surname_stt") or []:
        if not isinstance(s, dict):
            continue
        c = s.get("canonical", "")
        oft = ", ".join(s.get("stt_often") or [])
        note = s.get("notes") or ""
        if c:
            lines.append(f"- {c}" + (f" ← STT: {oft}" if oft else "") + (f" ({note})" if note else ""))
    sk = doc.get("swedish_kinship") or []
    if sk:
        lines.append("Swedish kinship (correct): " + ", ".join(str(x) for x in sk))
    for ins in doc.get("instructions_for_model") or []:
        lines.append(f"• {ins}")
    return "\n".join(lines)


def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip(), 10)
    except ValueError:
        return default


def _parse_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def build_system_prompt(
    project: Path | None = None,
    glossary_block: str | None = None,
) -> str:
    project = project or PROJECT_DIR
    if glossary_block is None:
        glossary_block = _load_glossary_block(project)
    base = """You are a transcript quality checker for a long-form spoken podcast (YouTube captions).
Find text that does NOT read like plausible fluent English because of speech-to-text (STT) errors.

ALWAYS use the CANONICAL GLOSSARY below when deciding if a word is a mishearing vs a correct name.
- If transcript text matches a known STT corruption for a canonical name, flag it (usually severity "high") and set suggested_fix to the canonical wording.
- Do NOT flag correct canonical spellings, correct Swedish kinship terms, or intentional wordplay you recognize from glossary notes.
- Do NOT flag political opinions, sarcasm, or rhetorical style.

Also flag (any severity): word salad, nonsense phrases, obvious merged/dropped words, absurd grammar from STT, stutter-duplication artifacts — even if not in the glossary.

When in doubt between "unusual proper noun" and "STT garbage", prefer flagging only if it breaks English grammar or matches glossary STT patterns."""
    if glossary_block:
        return base + "\n\n--- CANONICAL GLOSSARY ---\n" + glossary_block
    return base


def _build_user_prompt(batch_index: int, batch: list[dict[str, Any]]) -> str:
    parts = [
        f"Batch index: {batch_index}",
        "Each segment has time_label (caption time) and text (spoken content).",
        "",
    ]
    for i, seg in enumerate(batch):
        lab = seg.get("label") or "[?]"
        parts.append(f"--- segment {i} | {lab} ---")
        parts.append(seg.get("text", "").strip())
        parts.append("")
    parts.append(
        'Return ONLY valid JSON with this shape:\n'
        '{"issues":[\n'
        '  {"segment":0,"severity":"low|med|high","reason":"short","excerpt":"verbatim quote from that segment","suggested_fix":""}\n'
        "]}\n"
        "Rules:\n"
        "- Flag incoherent / garbled STT, obvious wrong-word salad, broken repetition, OR glossary-backed name corruptions — NOT opinions or rhetoric.\n"
        "- excerpt MUST be copied verbatim from the segment text (short).\n"
        "- suggested_fix: when the issue is a wrong name or word, give the canonical fix from the system glossary when applicable.\n"
        "- If nothing is wrong, return {\"issues\":[]}.\n"
        "- segment is the segment index (0..n-1) within THIS batch only."
    )
    return "\n".join(parts)


def _severity_rank(sev: str) -> int:
    s = (sev or "").lower()
    return {"high": 3, "med": 2, "medium": 2, "low": 1}.get(s, 0)


def apply_sense_findings_to_text(
    text: str,
    findings: list[dict[str, Any]],
    *,
    min_severity: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Apply LLM suggested_fix via literal replace when excerpt is unique in the current text.
    Longer excerpts first (reduces accidental sub-string collisions).
    Skips error/raw_tail rows and empty excerpt/fix.
    """
    floor = _severity_rank(min_severity) if min_severity else 0
    candidates: list[dict[str, Any]] = []
    for f in findings:
        if f.get("error") or f.get("raw_tail"):
            continue
        if floor and _severity_rank(str(f.get("severity", ""))) < floor:
            continue
        ex = str(f.get("excerpt") or "").strip()
        fix = str(f.get("suggested_fix") or "").strip()
        if not ex or not fix or ex == fix:
            continue
        candidates.append({**f, "_ex": ex, "_fix": fix})

    candidates.sort(key=lambda x: len(x["_ex"]), reverse=True)

    out_text = text
    report: list[dict[str, Any]] = []
    for f in candidates:
        ex = f["_ex"]
        fix = f["_fix"]
        n = out_text.count(ex)
        base = {
            "caption_label": f.get("caption_label"),
            "severity": f.get("severity"),
            "reason": (f.get("reason") or "")[:200],
        }
        if n == 1:
            out_text = out_text.replace(ex, fix, 1)
            report.append({**base, "status": "applied", "excerpt": ex[:120], "suggested_fix": fix[:120]})
        elif n == 0:
            report.append({**base, "status": "skipped_not_found", "excerpt": ex[:120]})
        else:
            report.append({**base, "status": "skipped_ambiguous", "count": n, "excerpt": ex[:120]})

    return out_text, report


def inscription_transcript_path(project: Path, episode: int) -> Path:
    return project / "inscription" / f"episode_{int(episode):03d}_transcript.txt"


def sense_scan_apply_inscription(
    project: Path | None,
    episode: int,
    findings: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    min_severity: str | None = None,
) -> dict[str, Any]:
    """Read inscription transcript, apply safe fixes, optionally write."""
    project = project or PROJECT_DIR
    path = inscription_transcript_path(project, episode)
    if not path.is_file():
        return {"error": "missing_transcript", "path": str(path), "apply_report": []}
    text = path.read_text(encoding="utf-8")
    new_text, report = apply_sense_findings_to_text(
        text, findings, min_severity=min_severity
    )
    applied = sum(1 for r in report if r.get("status") == "applied")
    if not dry_run and new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return {
        "path": str(path.relative_to(project)),
        "dry_run": dry_run,
        "text_changed": new_text != text,
        "apply_report": report,
        "applied_count": applied,
        "written": (not dry_run) and new_text != text,
    }


def sense_scan_episode(
    project: Path | None = None,
    episode: int = 1,
    *,
    max_batches: int | None = None,
) -> dict[str, Any]:
    project = project or PROJECT_DIR
    path = project / "inscription" / f"episode_{int(episode):03d}_transcript.txt"
    if not path.is_file():
        return {
            "error": "missing_transcript",
            "path": str(path),
            "findings": [],
            "batches_scanned": 0,
        }

    text = path.read_text(encoding="utf-8")
    segments = segment_transcript(text)
    batches = _batch_segments(segments)

    raw_mb = max_batches
    if raw_mb is None:
        raw_mb = _parse_int_env("TRANSCRIPT_SENSE_MAX_BATCHES", 0)
    if raw_mb is None or int(raw_mb) <= 0:
        max_batch_count = len(batches)
    else:
        max_batch_count = min(int(raw_mb), len(batches))
    max_batch_count = max(1, max_batch_count) if batches else 0

    findings: list[dict[str, Any]] = []

    temp = _parse_float_env("TRANSCRIPT_SENSE_TEMPERATURE", 0.05)
    mt = _parse_int_env("TRANSCRIPT_SENSE_MAX_TOKENS", 4096)
    max_excerpt = _parse_int_env("TRANSCRIPT_SENSE_MAX_EXCERPT_LEN", 2000)

    glossary_block = _load_glossary_block(project)
    system_prompt = build_system_prompt(project, glossary_block)

    for bi, batch in enumerate(batches[:max_batch_count]):
        user = _build_user_prompt(bi, batch)
        try:
            content = _chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user},
                ],
                max_tokens=mt,
                temperature=temp,
            )
        except Exception as e:
            findings.append(
                {
                    "batch": bi,
                    "severity": "med",
                    "reason": f"LLM request failed: {e}",
                    "excerpt": "",
                    "suggested_fix": "",
                    "caption_label": batch[0].get("label"),
                    "caption_seconds": batch[0].get("seconds"),
                    "error": True,
                }
            )
            continue

        obj = _extract_json_object(content)
        if not obj:
            findings.append(
                {
                    "batch": bi,
                    "severity": "low",
                    "reason": "Unparseable model response (skipped)",
                    "excerpt": (content or "")[:200],
                    "suggested_fix": "",
                    "caption_label": batch[0].get("label"),
                    "caption_seconds": batch[0].get("seconds"),
                    "raw_tail": True,
                }
            )
            continue

        for issue in obj.get("issues") or []:
            if not isinstance(issue, dict):
                continue
            try:
                si = int(issue.get("segment", -1))
            except (TypeError, ValueError):
                si = -1
            if not (0 <= si < len(batch)):
                seg = batch[0]
            else:
                seg = batch[si]
            findings.append(
                {
                    "batch": bi,
                    "segment": si,
                    "severity": str(issue.get("severity", "med")),
                    "reason": str(issue.get("reason", ""))[:500],
                    "excerpt": str(issue.get("excerpt", ""))[:max_excerpt],
                    "suggested_fix": str(issue.get("suggested_fix", ""))[:max_excerpt],
                    "caption_label": seg.get("label"),
                    "caption_seconds": seg.get("seconds"),
                }
            )

    _, _, model = _get_llm_config()
    return {
        "episode": int(episode),
        "file": str(path.relative_to(project)),
        "model": model,
        "batches_total": len(batches),
        "batches_scanned": max_batch_count,
        "segments_total": len(segments),
        "findings": findings,
        "count": len([f for f in findings if not f.get("error") and not f.get("raw_tail")]),
        "glossary_loaded": bool(glossary_block),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("episode", type=int, help="Episode number")
    ap.add_argument("--max-batches", type=int, default=None)
    ap.add_argument(
        "--apply-inscription",
        action="store_true",
        help="After scan, apply suggested_fix only where excerpt matches exactly once in inscription transcript",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="With --apply-inscription: show apply_report but do not write",
    )
    ap.add_argument(
        "--apply-min-severity",
        default=None,
        metavar="SEV",
        help="Only apply findings with at least this severity: low|med|high (default: all)",
    )
    args = ap.parse_args()
    # Load agent-lab .env if present
    try:
        from dotenv import load_dotenv

        root = PROJECT_DIR.parent.parent.parent
        load_dotenv(root / ".env", override=False)
    except ImportError:
        pass

    out = sense_scan_episode(PROJECT_DIR, args.episode, max_batches=args.max_batches)
    if args.apply_inscription and not out.get("error"):
        apply_out = sense_scan_apply_inscription(
            PROJECT_DIR,
            args.episode,
            out.get("findings") or [],
            dry_run=args.dry_run,
            min_severity=args.apply_min_severity,
        )
        out["apply"] = apply_out
        if apply_out.get("written") and not args.dry_run:
            sync = PROJECT_DIR / "scripts" / "sync_transcript_hashes.py"
            if sync.is_file():
                import subprocess

                r = subprocess.run(
                    [sys.executable, str(sync)],
                    cwd=str(PROJECT_DIR),
                    capture_output=True,
                    text=True,
                )
                out["sync_transcript_hashes"] = {
                    "returncode": r.returncode,
                    "stderr": (r.stderr or "")[-2000:],
                }
    print(json.dumps(out, indent=2))
    return 0 if not out.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
