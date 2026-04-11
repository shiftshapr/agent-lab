#!/usr/bin/env python3
"""
Telegram completion notifier for Bride of Charlie pipeline.

Sends a Telegram message when episode analysis finishes (after two-phase **Phase 2**),
or manually via CLI counts.

Reads ``TELEGRAM_BOT_TOKEN`` and ``TELEGRAM_CHAT_ID`` from **agent-lab** ``.env`` first,
then fills missing keys from ``~/.openclaw/.env`` (OpenClaw gateway).

Env:
    BRIDE_NOTIFY_TELEGRAM   Optional. Set to ``0`` / ``false`` / ``no`` to disable
                            auto notifications from the episode protocol (default: enabled
                            when Telegram vars are set).

Usage (import):
    from notify_completion import notify_episode_complete
    notify_episode_complete(episode=1, artifacts=23, claims=16)

Usage (CLI):
    python3 scripts/notify_completion.py --episode 1 --artifacts 23 --claims 16
"""

from __future__ import annotations

import os
import sys
import urllib.request
import urllib.error
import json
import re
from pathlib import Path
from typing import Optional


def _agent_lab_root() -> Path:
    # scripts → bride_of_charlie → monuments → projects → agent-lab
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def _parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _load_env() -> dict[str, str]:
    """Agent-lab ``.env`` first; then ``~/.openclaw/.env`` for missing Telegram keys only."""
    env = _parse_env_file(_agent_lab_root() / ".env")
    oc = Path.home() / ".openclaw" / ".env"
    oc_map = _parse_env_file(oc)
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if not (env.get(key) or "").strip() and (oc_map.get(key) or "").strip():
            env[key] = oc_map[key]
    return env


def _telegram_disabled_by_env() -> bool:
    v = os.getenv("BRIDE_NOTIFY_TELEGRAM", "").strip().lower()
    return v in ("0", "false", "no", "off")


def _telegram_credentials() -> tuple[str, str] | None:
    env = _load_env()
    tok, cid = env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_CHAT_ID", "")
    if not tok or not cid:
        return None
    return tok, cid


def count_artifacts_and_claims_phase1(data: dict) -> tuple[int, int]:
    """Count artifact sub-items and claims from a phase1_output JSON object."""
    n_art = 0
    for fam in data.get("artifacts") or []:
        if isinstance(fam, dict):
            n_art += len(fam.get("sub_items") or [])
    n_claim = len(data.get("claims") or [])
    return n_art, n_claim


def notify_after_phase2_batch(phase1_paths: list[Path]) -> None:
    """
    After assign_ids Phase 2, send one Telegram per phase1 JSON (episode analysis done).

    No-op if ``BRIDE_NOTIFY_TELEGRAM`` disables, or Telegram credentials missing
    (no stderr spam for missing config).
    """
    if _telegram_disabled_by_env():
        return
    creds = _telegram_credentials()
    if not creds:
        return
    bot_token, chat_id = creds
    for p in sorted(phase1_paths, key=lambda x: x.name):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"[notify_completion] skip {p.name}: {e}", file=sys.stderr)
            continue
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        ep = meta.get("episode")
        if ep is None:
            m = re.search(r"episode_(\d+)", p.name, re.I)
            ep = int(m.group(1)) if m else None
        if ep is None:
            continue
        try:
            ep_i = int(ep)
        except (TypeError, ValueError):
            continue
        ac, cc = count_artifacts_and_claims_phase1(data)
        msg = (
            f"✅ <b>Episode {ep_i} analysis complete</b>\n"
            f"• {ac} artifacts\n"
            f"• {cc} claims"
        )
        ok = send_telegram_message(bot_token, chat_id, msg)
        if ok:
            print(f"[notify_completion] Telegram sent for episode {ep_i}")
        else:
            print(f"[notify_completion] Telegram failed for episode {ep_i}", file=sys.stderr)


def notify_single_pass_draft_complete(episode: int) -> bool:
    """
    Single-phase run wrote ``episode_NNN_*.md`` only (no phase1 JSON yet).
    """
    if _telegram_disabled_by_env():
        return False
    creds = _telegram_credentials()
    if not creds:
        return False
    bot_token, chat_id = creds
    msg = (
        f"✅ <b>Episode {episode}</b> markdown draft written "
        f"(single-phase). Two-phase run gives artifact/claim counts in Telegram."
    )
    return send_telegram_message(bot_token, chat_id, msg)


def run_smoke_check() -> int:
    """Verify env merge + phase1 counting (no network if Telegram unset)."""
    env = _load_env()
    tok_ok = bool((env.get("TELEGRAM_BOT_TOKEN") or "").strip())
    cid_ok = bool((env.get("TELEGRAM_CHAT_ID") or "").strip())
    print(
        "[smoke] agent-lab + openclaw merge:",
        "TELEGRAM_BOT_TOKEN=" + ("set" if tok_ok else "(empty)"),
        "TELEGRAM_CHAT_ID=" + ("set" if cid_ok else "(empty)"),
    )
    sample = {
        "artifacts": [{"sub_items": [{"x": 1}, {"x": 2}]}],
        "claims": [{"id": "a"}, {"id": "b"}],
    }
    ac, cc = count_artifacts_and_claims_phase1(sample)
    assert ac == 2 and cc == 2, (ac, cc)
    print("[smoke] count_artifacts_and_claims_phase1 ok (2, 2)")
    return 0


def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    timeout: int = 10,
) -> bool:
    """POST a message to the Telegram Bot API. Returns True on success."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "BrideOfCharlie-Pipeline/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            result = json.loads(body)
            return result.get("ok", False)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
        print(f"[notify_completion] Telegram error: {exc}", file=sys.stderr)
        return False


def notify_episode_complete(
    episode: int,
    artifacts: int,
    claims: int,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """
    Send a Telegram notification that an episode analysis is complete.

    Args:
        episode: Episode number
        artifacts: Total artifact items (including sub-items)
        claims: Total claim count
        bot_token: Telegram bot token (reads from .env if not provided)
        chat_id: Telegram chat ID (reads from .env if not provided)

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    env = _load_env()
    bot_token = bot_token or env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = chat_id or env.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        print(
            "[notify_completion] TELEGRAM_* not set (agent-lab or ~/.openclaw/.env) — skipping.",
            file=sys.stderr,
        )
        return False

    message = (
        f"✅ <b>Episode {episode} analysis complete</b>\n"
        f"• {artifacts} artifacts\n"
        f"• {claims} claims"
    )

    return send_telegram_message(bot_token, chat_id, message)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Send Telegram completion notification")
    parser.add_argument("--smoke", action="store_true", help="Verify env merge + counters (no send)")
    parser.add_argument("--episode", type=int, default=None)
    parser.add_argument("--artifacts", type=int, default=None)
    parser.add_argument("--claims", type=int, default=None)
    args = parser.parse_args()

    if args.smoke:
        sys.exit(run_smoke_check())

    if args.episode is None or args.artifacts is None or args.claims is None:
        parser.error("use --episode, --artifacts, --claims (or --smoke)")
    ok = notify_episode_complete(args.episode, args.artifacts, args.claims)
    sys.exit(0 if ok else 1)
