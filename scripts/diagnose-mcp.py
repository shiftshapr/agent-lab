#!/usr/bin/env python3
"""
Diagnose MCP connectivity — test each configured server individually.

Usage:
  cd /path/to/agent-lab
  python scripts/diagnose-mcp.py

Runs via uv from DeerFlow backend (same as run-deerflow-task).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent
DEER_FLOW_DIR = AGENT_LAB_ROOT / "framework" / "deer-flow"
BACKEND_DIR = DEER_FLOW_DIR / "backend"


def load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
        print(f"[diagnose] Loaded .env from {env_path}")
    else:
        print(f"[diagnose] No .env at {env_path}")


def check_zoho_urls() -> None:
    """Quick reachability check for Zoho MCP URLs."""
    for key in ("ZOHO_VIEW_MCP_URL", "ZOHO_PUBLISH_MCP_URL"):
        url = os.environ.get(key, "")
        if not url or not url.startswith("http"):
            print(f"[diagnose] {key}: not set or invalid")
            continue
        try:
            import urllib.request
            req = urllib.request.Request(url, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, data=b"{}", timeout=10) as r:
                print(f"[diagnose] {key}: reachable ({r.status})")
        except Exception as e:
            print(f"[diagnose] {key}: NOT reachable — {e}")
    print()


def main() -> None:
    load_env()
    print("[diagnose] Checking Zoho URL reachability...")
    check_zoho_urls()
    env = {**os.environ}
    env.setdefault("DEER_FLOW_CONFIG_PATH", str(DEER_FLOW_DIR / "config.yaml"))
    env.setdefault("DEER_FLOW_EXTENSIONS_CONFIG_PATH", str(DEER_FLOW_DIR / "extensions_config.json"))

    script = """
import asyncio
import os
from deerflow.config.extensions_config import ExtensionsConfig
from deerflow.mcp.client import build_servers_config

async def run():
    config = ExtensionsConfig.from_file()
    servers = build_servers_config(config)
    if not servers:
        print("No enabled MCP servers configured.")
        return
    print(f"\\nTesting {len(servers)} MCP server(s)...\\n")
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("langchain-mcp-adapters not installed")
        return
    for name, params in servers.items():
        transport = params.get("transport", "?")
        url = params.get("url", "")
        has_url = bool(url and url.strip())
        env = params.get("env") or {}
        if transport in ("http", "sse", "streamable_http") and not has_url:
            print(f"  {name}: SKIP (no URL — env var unresolved?)")
            continue
        if "slack" in name.lower() and not env.get("SLACK_BOT_TOKEN"):
            print(f"  {name}: SKIP (SLACK_BOT_TOKEN empty)")
            continue
        try:
            client = MultiServerMCPClient({name: params}, tool_name_prefix=True)
            tools = await client.get_tools()
            print(f"  {name}: OK — {len(tools)} tool(s)")
        except Exception as e:
            cause = getattr(e, "__cause__", None) or e
            print(f"  {name}: FAIL — {e}")
            if cause != e:
                print(f"    cause: {cause}")
    print()

asyncio.run(run())
"""
    result = subprocess.run(
        ["uv", "run", "python", "-c", script],
        cwd=str(BACKEND_DIR),
        env=env,
        timeout=60,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
