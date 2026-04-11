#!/usr/bin/env python3
"""
LLM pass: find stretches of transcript that read like garbled STT / nonsense (not “I disagree”).

Uses the same OpenAI-compatible stack as agent-lab:
  MINIMAX_API_KEY (+ MINIMAX_MODEL)  OR  OPENAI_BASE_URL + OPENAI_API_KEY + MODEL_NAME

Env:
  TRANSCRIPT_SENSE_MAX_BATCHES   default 0  (= scan entire episode; set N>0 to cap LLM calls / windows)
  TRANSCRIPT_SENSE_TEMPERATURE   default 0.05 (non-MiniMax); MiniMax recommends 1.0 — when this env is unset and the provider is MiniMax, default temperature is 1.0 unless overridden by TRANSCRIPT_SENSE_MINIMAX_TEMPERATURE
  TRANSCRIPT_SENSE_MAX_TOKENS    default 4096 per request
  TRANSCRIPT_SENSE_FLOW_CHUNK_CHARS  default 3600 — chars per transcript window
  TRANSCRIPT_SENSE_FLOW_OVERLAP      default 600 — overlap between windows (reduces edge misses)
  TRANSCRIPT_SENSE_MINIMAX_REASONING_SPLIT  default 1 — when using MINIMAX_API_KEY, send reasoning_split=True
    so JSON is not buried inside <think>…</think> (required for parseable responses).

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


def _get_llm_config() -> tuple[str, str, str]:
    # Prefer OPENAI_BASE_URL + OPENAI_API_KEY when both are present
    # (this matches how OpenClaw/agent-lab uses MiniMax via the OpenAI-compat stack).
    # Only fall back to the MINIMAX_API_KEY hardcoded path when no OPENAI_* config exists.
    openai_base = os.getenv("OPENAI_BASE_URL", "").strip().rstrip("/")
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_base and openai_key and openai_key != "fake":
        return (
            openai_base,
            openai_key,
            os.getenv("MODEL_NAME", os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")),
        )
    minimax_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if minimax_key:
        return (
            "https://api.minimax.io/v1",
            minimax_key,
            os.getenv("MINIMAX_MODEL", os.getenv("MODEL_NAME", "MiniMax-M2.5")),
        )
    return (
        openai_base or "http://localhost:11434/v1",
        openai_key or "fake",
        os.getenv("MODEL_NAME", "qwen2.5:7b"),
    )


def _minimax_openai_compatible(base: str, model: str) -> bool:
    """True when chat/completions is MiniMax — needs reasoning_split and/or redacted_thinking strip."""
    if os.getenv("TRANSCRIPT_SENSE_FORCE_MINIMAX", "").strip().lower() in ("1", "true", "yes"):
        return True
    b = (base or "").lower()
    m = (model or "").lower()
    return (
        bool(os.getenv("MINIMAX_API_KEY", "").strip())
        or "minimax" in b
        or "api.minimax.io" in b
        or "minimax" in m
        or m.startswith("minimax")
    )


def _first_dict_with_issues_key(s: str) -> dict[str, Any] | None:
    """Find first JSON object in *s* that contains an ``issues`` key (handles prose + trailing noise)."""
    if not s or "issues" not in s.lower():
        return None
    dec = json.JSONDecoder()
    i = 0
    n = len(s)
    while i < n:
        if s[i] == "{":
            try:
                obj, end = dec.raw_decode(s, i)
            except json.JSONDecodeError:
                i += 1
                continue
            if isinstance(obj, dict):
                for k in obj:
                    if str(k).lower() == "issues":
                        return obj
            i = max(i + 1, end)
            continue
        i += 1
    return None


def _minimax_sense_tools_enabled(base: str, model: str) -> bool:
    if not _minimax_openai_compatible(base, model):
        return False
    return os.getenv("TRANSCRIPT_SENSE_MINIMAX_TOOLS", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _minimax_sense_scan_tools() -> list[dict[str, Any]]:
    """OpenAI-format tools; MiniMax returns JSON in tool_calls[].function.arguments."""
    return [
        {
            "type": "function",
            "function": {
                "name": "submit_transcript_findings",
                "description": (
                    "Submit STT/coherence findings for this transcript chunk only. "
                    "Call exactly once per user message. Use an empty issues array if nothing is clearly wrong."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "issues": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "severity": {
                                        "type": "string",
                                        "enum": ["low", "med", "high"],
                                    },
                                    "reason": {"type": "string"},
                                    "excerpt": {
                                        "type": "string",
                                        "description": "Exact contiguous substring from the chunk; shorten if needed so JSON stays valid.",
                                    },
                                    "suggested_fix": {"type": "string"},
                                },
                                "required": ["severity", "reason", "excerpt", "suggested_fix"],
                            },
                        }
                    },
                    "required": ["issues"],
                },
            },
        }
    ]


def _coerce_tool_call_args(args: Any) -> dict[str, Any] | None:
    """Parse function.arguments into a dict (string JSON or already a dict)."""
    parsed: Any = None
    if isinstance(args, str):
        s = args.strip()
        if not s:
            return None
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            parsed = _extract_json_object(s)
    elif isinstance(args, dict):
        parsed = args
    if not isinstance(parsed, dict):
        return None
    for k, v in parsed.items():
        if str(k).lower() != "issues":
            continue
        if v is None:
            return {"issues": []}
        if isinstance(v, list):
            return {"issues": v}
        return None
    # Model returned {} or omitted issues — treat as no findings
    if parsed == {}:
        return {"issues": []}
    return None


def _tool_call_name_and_args(tc: dict[str, Any]) -> tuple[str | None, Any]:
    fn = tc.get("function")
    if isinstance(fn, dict):
        n = fn.get("name")
        name = n if isinstance(n, str) else None
        return name, fn.get("arguments")
    n = tc.get("name")
    name = n if isinstance(n, str) else None
    return name, tc.get("arguments")


def _issues_object_from_tool_calls(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Parse submit_transcript_findings from message.tool_calls (several provider shapes)."""
    raw = msg.get("tool_calls")
    if not isinstance(raw, list):
        return None

    def _try_named() -> dict[str, Any] | None:
        want = "submit_transcript_findings"
        for tc in raw:
            if not isinstance(tc, dict):
                continue
            name, args = _tool_call_name_and_args(tc)
            if name and name.casefold() != want.casefold():
                continue
            got = _coerce_tool_call_args(args)
            if got is not None:
                return got
        return None

    got = _try_named()
    if got is not None:
        return got
    # Single tool call: some gateways rename the function — still parse arguments
    if len(raw) == 1 and isinstance(raw[0], dict):
        _name, args = _tool_call_name_and_args(raw[0])
        return _coerce_tool_call_args(args)
    return None


def _issues_from_obj(obj: dict[str, Any]) -> list[Any]:
    for k, v in obj.items():
        if str(k).lower() == "issues" and isinstance(v, list):
            return v
    return []


def _walk_api_response_for_issues(node: Any, depth: int = 0) -> dict[str, Any] | None:
    """Try to parse ``{\"issues\": [...]}`` from any string nested in the HTTP JSON (MiniMax split fields)."""
    if depth > 40:
        return None
    if isinstance(node, str) and node.strip():
        found = _extract_json_object(node)
        if isinstance(found, dict) and any(str(k).lower() == "issues" for k in found):
            return found
        found = _first_dict_with_issues_key(node)
        if found:
            return found
        return None
    if isinstance(node, dict):
        for v in node.values():
            r = _walk_api_response_for_issues(v, depth + 1)
            if r is not None:
                return r
    elif isinstance(node, list):
        for v in node:
            r = _walk_api_response_for_issues(v, depth + 1)
            if r is not None:
                return r
    return None


def _assistant_message_parse_text(msg: dict[str, Any]) -> str:
    """
    Build the string we JSON-parse. When reasoning_split is on, MiniMax may return content as a list
    of parts; mixing reasoning + answer in one string breaks json.loads — skip reasoning-* parts.
    """
    pieces: list[str] = []

    def _append_str(x: Any) -> None:
        if isinstance(x, str) and x.strip():
            pieces.append(x.strip())

    raw = msg.get("content")
    if isinstance(raw, str):
        _append_str(raw)
    elif isinstance(raw, list):
        for p in raw:
            if not isinstance(p, dict):
                _append_str(str(p))
                continue
            ptype = str(p.get("type") or "").strip().lower()
            if ptype.startswith("reasoning") or ptype in (
                "thinking",
                "redacted_thinking",
                "internal_thinking",
            ):
                continue
            if isinstance(p.get("text"), str):
                _append_str(p["text"])
            elif isinstance(p.get("content"), str):
                _append_str(p["content"])
            elif ptype in ("text", "output_text", "") and isinstance(p.get("value"), str):
                _append_str(p["value"])
    return "\n".join(pieces)


def _chat(
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: Any | None = None,
    _suppress_reasoning_split: bool = False,
) -> tuple[str, dict[str, Any]]:
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
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # MiniMax M2.x: OpenAI SDK passes extra_body as merged TOP-LEVEL fields on the wire — not a nested
    # "extra_body" object. Sending nested extra_body may be ignored and leave reasoning inside content.
    if _minimax_openai_compatible(base, model) and not _suppress_reasoning_split:
        if os.getenv("TRANSCRIPT_SENSE_MINIMAX_REASONING_SPLIT", "1").strip().lower() not in (
            "0",
            "false",
            "no",
        ):
            payload["reasoning_split"] = True
    if tools is not None:
        payload["tools"] = tools
        if os.getenv("TRANSCRIPT_SENSE_PARALLEL_TOOL_CALLS", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            payload["parallel_tool_calls"] = False
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:4000]
        raise RuntimeError(f"HTTP {e.code} from chat/completions: {detail}") from e

    err = data.get("error")
    if isinstance(err, dict) and err.get("message"):
        raise RuntimeError(str(err.get("message")))
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("chat/completions: missing or empty choices")

    msg = choices[0].get("message") or {}
    if not isinstance(msg, dict):
        msg = {}

    joined = _assistant_message_parse_text(msg).strip()
    if joined:
        return joined, data

    # Empty message.content (MiniMax + some proxies): recover by scanning full HTTP JSON for {"issues":...}.
    try:
        return json.dumps(data, ensure_ascii=False), data
    except (TypeError, ValueError):
        return "", data


_THINK_WRAPPER_RES = (
    re.compile(r"<redacted_thinking[^>]*>[\s\S]*?</redacted_thinking>", re.I),
    re.compile(r"<think[^>]*>[\s\S]*?</think>", re.I),
    re.compile(r"<reasoning[^>]*>[\s\S]*?</reasoning>", re.I),
)


def _strip_think(text: str) -> str:
    """Remove model reasoning / scratchpad wrappers so JSON can be parsed."""
    t = text.strip()
    for _ in range(12):
        prev = t
        for rx in _THINK_WRAPPER_RES:
            t = rx.sub("", t).strip()
        if t == prev:
            break
    return t


def _tail_after_reasoning_markers(text: str) -> str:
    """If the model closed a think block then emitted JSON, keep only the tail (common MiniMax shape)."""
    t = text.strip()
    for marker in (
        "</redacted_thinking>",
        "</think>",
        "</reasoning>",
    ):
        i = t.rfind(marker)
        if i >= 0:
            t = t[i + len(marker) :].strip()
    return t


def _normalize_json_string_chars(s: str) -> str:
    """Replace common Unicode quotes that break json.loads."""
    return (
        s.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


def _extract_json_object(text: str) -> dict[str, Any] | None:
    t = _normalize_json_string_chars(_strip_think(text))
    t2 = _normalize_json_string_chars(_tail_after_reasoning_markers(_strip_think(text)))
    for candidate in (t, t2):
        got = _extract_json_object_inner(candidate)
        if got is not None:
            return got
    return None


def _extract_json_object_inner(text: str) -> dict[str, Any] | None:
    t = text
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
            parsed = json.loads(t[i : j + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    found = _first_dict_with_issues_key(t)
    return found


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


def _flow_concat_with_spans(
    segments: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Join segment texts with blank lines; spans record [start,end) in flow_text per segment."""
    flow_parts: list[str] = []
    spans: list[dict[str, Any]] = []
    pos = 0
    sep = "\n\n"
    for seg in segments:
        t = (seg.get("text") or "").strip()
        if not t:
            continue
        if flow_parts:
            pos += len(sep)
        start = pos
        flow_parts.append(t)
        pos += len(t)
        spans.append(
            {
                "start": start,
                "end": pos,
                "label": seg.get("label") or "[?]",
                "seconds": seg.get("seconds", 0),
                "text": t,
            }
        )
    flow_text = sep.join(flow_parts) if flow_parts else ""
    return flow_text, spans


def _flow_overlapping_chunks(
    flow_text: str,
    *,
    chunk_chars: int,
    overlap: int,
) -> list[tuple[int, str]]:
    """(global_start, chunk_text) windows with overlap."""
    if not flow_text or chunk_chars <= 0:
        return []
    step = max(1, chunk_chars - max(0, overlap))
    out: list[tuple[int, str]] = []
    i = 0
    n = len(flow_text)
    while i < n:
        end = min(n, i + chunk_chars)
        out.append((i, flow_text[i:end]))
        if end >= n:
            break
        i += step
    return out


def _map_flow_excerpt(
    flow_text: str,
    chunk_global_start: int,
    chunk: str,
    excerpt: str,
) -> tuple[int, int] | None:
    """Return (abs_start, abs_end) in flow_text, or None if excerpt not in chunk."""
    needle = (excerpt or "").strip()
    if not needle:
        return None
    local = chunk.find(needle)
    if local < 0:
        return None
    a = chunk_global_start + local
    b = a + len(needle)
    if b > len(flow_text):
        b = len(flow_text)
    return a, b


def _effective_llm_call_cap(max_batches_kw: int | None, total_calls: int) -> int:
    """Env/kw TRANSCRIPT_SENSE_MAX_BATCHES: 0 or unset means scan all windows; N>0 caps calls."""
    raw = max_batches_kw
    if raw is None:
        raw = _parse_int_env("TRANSCRIPT_SENSE_MAX_BATCHES", 0)
    try:
        raw_i = int(raw)
    except (TypeError, ValueError):
        raw_i = 0
    if total_calls <= 0:
        return 0
    if raw_i <= 0:
        return total_calls
    return min(raw_i, total_calls)


_FLOW_SYSTEM_APPEND = (
    "\n\n(TRANSCRIPT WINDOW MODE)\n"
    "The user message is a window of the episode with caption timestamps removed. "
    "A blank line separates what were separate captions in the source file; that boundary alone is not an error. "
    "Flag issues that remain broken when adjacent paragraphs are read together, clear STT/word errors, or glossary mishearings."
)


def _sense_scan_episode_continuous_flow(
    project: Path,
    episode: int,
    path: Path,
    segments: list[dict[str, Any]],
    *,
    max_batches_kw: int | None,
) -> dict[str, Any]:
    """De-timestamped flow text, overlapping windows, map issues back to caption labels."""
    findings: list[dict[str, Any]] = []
    base_url, _key, model_name = _get_llm_config()
    _raw_temp = os.getenv("TRANSCRIPT_SENSE_TEMPERATURE")
    if _raw_temp is None or not str(_raw_temp).strip():
        if _minimax_openai_compatible(base_url, model_name):
            temp = _parse_float_env("TRANSCRIPT_SENSE_MINIMAX_TEMPERATURE", 1.0)
        else:
            temp = 0.05
    else:
        temp = _parse_float_env("TRANSCRIPT_SENSE_TEMPERATURE", 0.05)
    mt = _parse_int_env("TRANSCRIPT_SENSE_MAX_TOKENS", 4096)
    max_excerpt = _parse_int_env("TRANSCRIPT_SENSE_MAX_EXCERPT_LEN", 2000)

    chunk_chars = _parse_int_env("TRANSCRIPT_SENSE_FLOW_CHUNK_CHARS", 3600)
    if chunk_chars < 400:
        chunk_chars = 400
    overlap = _parse_int_env("TRANSCRIPT_SENSE_FLOW_OVERLAP", 600)
    if overlap < 0:
        overlap = 0
    if overlap >= chunk_chars:
        overlap = max(0, chunk_chars // 6)

    flow_text, spans = _flow_concat_with_spans(segments)
    chunks = _flow_overlapping_chunks(flow_text, chunk_chars=chunk_chars, overlap=overlap)
    nchunks = len(chunks)
    max_chunk_count = _effective_llm_call_cap(max_batches_kw, nchunks)

    glossary_block = _load_glossary_block(project)
    system_prompt = build_system_prompt(project, glossary_block) + _FLOW_SYSTEM_APPEND

    use_tools = _minimax_sense_tools_enabled(base_url, model_name)
    _is_minimax = _minimax_openai_compatible(base_url, model_name)
    _debug_dir = os.getenv("TRANSCRIPT_SENSE_DEBUG_DIR", "").strip()
    _debug_ep_prefix = f"ep{episode:03d}"
    dedupe_keys: set[tuple[int, int, str, str]] = set()

    for ci, (gstart, chunk) in enumerate(chunks[:max_chunk_count]):
        user = _build_flow_chunk_prompt(ci, gstart, chunk, use_tools=use_tools)
        try:
            chat_kw: dict[str, Any] = {
                "max_tokens": mt,
                "temperature": temp,
            }
            if use_tools:
                chat_kw["tools"] = _minimax_sense_scan_tools()
                _tcq = os.getenv("TRANSCRIPT_SENSE_MINIMAX_TOOL_CHOICE", "required").strip().lower()
                if _tcq == "function":
                    chat_kw["tool_choice"] = {
                        "type": "function",
                        "function": {"name": "submit_transcript_findings"},
                    }
                else:
                    chat_kw["tool_choice"] = "required"
            # MiniMax: don't combine reasoning_split with tools — prefer tools path only
            if use_tools and _is_minimax:
                chat_kw["_suppress_reasoning_split"] = True
            content, raw_api = _chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user},
                ],
                **chat_kw,
            )
        except Exception as e:
            findings.append(
                {
                    "chunk": ci,
                    "batch": ci,
                    "severity": "med",
                    "reason": f"LLM request failed: {e}",
                    "excerpt": "",
                    "suggested_fix": "",
                    "caption_label": None,
                    "caption_seconds": None,
                    "error": True,
                }
            )
            continue

        # Dump raw API response for the first failing chunk when debug dir is set
        if _debug_dir and ci == 0:
            try:
                import pathlib as _pl
                _dd = _pl.Path(_debug_dir)
                _dd.mkdir(parents=True, exist_ok=True)
                _df = _dd / f"{_debug_ep_prefix}_chunk{ci:03d}_raw.json"
                _df.write_text(
                    json.dumps({"payload_tools": use_tools, "raw_api": raw_api, "content": content}, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception:
                pass

        msg = (raw_api.get("choices") or [{}])[0].get("message") or {}
        if not isinstance(msg, dict):
            msg = {}
        obj = _issues_object_from_tool_calls(msg)
        if not obj:
            obj = _extract_json_object(content)
        if not obj:
            obj = _walk_api_response_for_issues(raw_api)
        if not obj:
            ch0 = (raw_api.get("choices") or [{}])[0] if isinstance(raw_api, dict) else {}
            dbg_msg = ch0.get("message") if isinstance(ch0, dict) else {}
            if not isinstance(dbg_msg, dict):
                dbg_msg = {}
            tnames: list[str] = []
            tcr = dbg_msg.get("tool_calls")
            if isinstance(tcr, list):
                for tc in tcr:
                    if not isinstance(tc, dict):
                        continue
                    fn = tc.get("function")
                    if isinstance(fn, dict) and isinstance(fn.get("name"), str):
                        tnames.append(fn["name"])
                    elif isinstance(tc.get("name"), str):
                        tnames.append(tc["name"])
            findings.append(
                {
                    "chunk": ci,
                    "batch": ci,
                    "severity": "low",
                    "reason": "Unparseable model response (skipped)",
                    "excerpt": (content or "")[:200],
                    "suggested_fix": "",
                    "caption_label": None,
                    "caption_seconds": None,
                    "raw_tail": True,
                    "sense_debug_finish_reason": ch0.get("finish_reason") if isinstance(ch0, dict) else None,
                    "sense_debug_message_keys": sorted(dbg_msg.keys()) if dbg_msg else [],
                    "sense_debug_tool_names": tnames,
                }
            )
            continue

        for issue in _issues_from_obj(obj):
            if not isinstance(issue, dict):
                continue
            excerpt = str(issue.get("excerpt", ""))[:max_excerpt]
            fix = str(issue.get("suggested_fix", ""))[:max_excerpt]
            mapped = _map_flow_excerpt(flow_text, gstart, chunk, excerpt)
            if mapped is None:
                continue
            a, b = mapped
            dk = (a, b, excerpt[:160], fix[:160])
            if dk in dedupe_keys:
                continue
            dedupe_keys.add(dk)
            meta = _meta_for_flow_range(spans, a, b)
            findings.append(
                {
                    "chunk": ci,
                    "batch": ci,
                    "flow_char_start": a,
                    "flow_char_end": b,
                    "severity": str(issue.get("severity", "med")),
                    "reason": str(issue.get("reason", ""))[:500],
                    "excerpt": excerpt,
                    "suggested_fix": fix,
                    "caption_label": meta["caption_label"],
                    "caption_seconds": meta["caption_seconds"],
                    "prev_segment_text": meta.get("prev_segment_text") or "",
                    "next_segment_text": meta.get("next_segment_text") or "",
                }
            )

    _, _, model = _get_llm_config()
    return {
        "episode": int(episode),
        "file": str(path.relative_to(project)),
        "model": model,
        "scan_mode": "windows",
        "batches_total": nchunks,
        "batches_scanned": max_chunk_count,
        "segments_total": len(segments),
        "findings": findings,
        "count": len([f for f in findings if not f.get("error") and not f.get("raw_tail")]),
        "glossary_loaded": bool(glossary_block),
        "sense_scan_script": str(Path(__file__).resolve()),
        "minimax_tools": use_tools,
    }


def _meta_for_flow_range(
    spans: list[dict[str, Any]],
    a: int,
    b: int,
) -> dict[str, Any]:
    overlapping_idx: list[int] = []
    for i, s in enumerate(spans):
        if s["start"] < b and s["end"] > a:
            overlapping_idx.append(i)
    if not overlapping_idx:
        return {
            "caption_label": "[?]",
            "caption_seconds": None,
            "prev_segment_text": "",
            "next_segment_text": "",
        }
    fi = overlapping_idx[0]
    li = overlapping_idx[-1]
    sf = spans[fi]
    sl = spans[li]
    lab = sf["label"] if fi == li else f"{sf['label']}–{sl['label']}"
    prev_t = spans[fi - 1]["text"] if fi > 0 else ""
    next_t = spans[li + 1]["text"] if li + 1 < len(spans) else ""
    return {
        "caption_label": lab,
        "caption_seconds": sf.get("seconds"),
        "prev_segment_text": (prev_t or "")[:1200],
        "next_segment_text": (next_t or "")[:1200],
    }


def _build_flow_chunk_prompt(
    chunk_index: int, global_start: int, chunk: str, *, use_tools: bool = False
) -> str:
    head = (
        f"Chunk index: {chunk_index} · starts at character offset {global_start} in the full de-timestamped transcript.\n\n"
        "Transcript (caption timestamps REMOVED; a blank line separates what were separate caption segments in the source file):\n\n"
        f"{chunk}\n\n"
    )
    if use_tools:
        return head + (
            "Call the function submit_transcript_findings exactly once with your findings.\n"
            "Pass an `issues` array (empty if nothing is clearly wrong). Each issue: severity (low|med|high), "
            "reason, excerpt (EXACT contiguous substring from the chunk — shorten if needed so the tool arguments stay valid JSON), "
            "suggested_fix (canonical wording when applicable, else empty).\n"
            "Rules:\n"
            "- Do NOT flag text as wrong ONLY because it looks like a sentence fragment at a blank line; the next paragraph often completes the thought.\n"
            "- Only flag if it is still broken after mentally joining adjacent paragraphs, OR clear STT/word error / glossary issue.\n"
        )
    return (
        head
        + 'Return ONLY valid JSON: {"issues":[{"severity":"low|med|high","reason":"short text","excerpt":"verbatim from chunk","suggested_fix":""}]}\n'
        "Rules:\n"
        "- excerpt MUST be copied verbatim from the chunk above (contiguous substring).\n"
        "- Do NOT flag text as wrong ONLY because it looks like a sentence fragment at a blank line; the next paragraph often completes the thought. Only flag if it is still broken after mentally joining adjacent paragraphs, OR clear STT/word error / glossary issue.\n"
        "- suggested_fix: canonical wording when applicable; else empty.\n"
        "- If nothing is clearly wrong, return {\"issues\":[]}.\n"
    )


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


def primary_episode_transcript_path(project: Path, episode: int) -> Path | None:
    """Canonical on-disk transcript: transcripts_corrected when present, else inscription."""
    corr = sorted((project / "transcripts_corrected").glob(f"episode_{int(episode):03d}_*.txt"))
    if corr:
        return corr[0]
    ins = project / "inscription" / f"episode_{int(episode):03d}_transcript.txt"
    if ins.is_file():
        return ins
    return None


def inscription_transcript_path(project: Path, episode: int) -> Path:
    """Episode transcript file used by sense scan / apply (corrected preferred)."""
    p = primary_episode_transcript_path(project, episode)
    if p is not None:
        return p
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
    path = primary_episode_transcript_path(project, episode)
    if path is None or not path.is_file():
        fallback = project / "inscription" / f"episode_{int(episode):03d}_transcript.txt"
        return {
            "error": "missing_transcript",
            "path": str(path or fallback),
            "findings": [],
            "batches_scanned": 0,
        }

    text = path.read_text(encoding="utf-8")
    segments = segment_transcript(text)
    return _sense_scan_episode_continuous_flow(
        project,
        episode,
        path,
        segments,
        max_batches_kw=max_batches,
    )


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("episode", type=int, help="Episode number")
    ap.add_argument("--max-batches", type=int, default=None)
    ap.add_argument(
        "--apply-inscription",
        action="store_true",
        help="After scan, apply suggested_fix where excerpt matches once (writes transcripts_corrected/ when present, else inscription)",
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
