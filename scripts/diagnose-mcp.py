#!/usr/bin/env python3
"""
Diagnose MCP connectivity — test each configured server individually.

Usage:
  cd /path/to/agent-lab
  source .env  # or use run-deerflow-with-env
  python scripts/diagnose-mcp.py
"""

from __future__ import annotations

import asyncio
import os
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


async def main() -> None:
    load_env()
    # Must run from backend with uv for deerflow package
    os.chdir(BACKEND_DIR)
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault("DEER_FLOW_CONFIG_PATH", str(DEER_FLOW_DIR / "config.yaml"))
    os.environ.setdefault("DEER_FLOW_EXTENSIONS_CONFIG_PATH", str(DEER_FLOW_DIR / "extensions_config.json"))

    from deerflow.config.extensions_config import ExtensionsConfig
    from deerflow.mcp.client import build_servers_config

    config = ExtensionsConfig.from_file()
    servers = build_servers_config(config)
    if not servers:
        print("No enabled MCP servers configured.")
        return

    print(f"\nTesting {len(servers)} MCP server(s)...\n")

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

        # Pre-check
        if transport in ("http", "sse", "streamable_http") and not has_url:
            print(f"  {name}: SKIP (no URL — env var unresolved?)")
            continue
        if "slack" in name.lower():
            token = env.get("SLACK_BOT_TOKEN", "")
            if not token:
                print(f"  {name}: SKIP (SLACK_BOT_TOKEN empty)")
                continue

        try:
            client = MultiServerMCPClient({name: params}, tool_name_prefix=True)
            tools = await client.get_tools()
            print(f"  {name}: OK — {len(tools)} tool(s)")
        except Exception as e:
            print(f"  {name}: FAIL — {e}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
