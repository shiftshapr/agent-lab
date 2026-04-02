#!/usr/bin/env bash
# Wrapper for Playwright MCP that injects LinkedIn storage state when available.
# Used by DeerFlow extensions_config. Requires LINKEDIN_STORAGE_STATE in env.
# If the MCP fails to launch Chromium, run: ./scripts/ensure-playwright-mcp-browsers.sh
if [ -n "$LINKEDIN_STORAGE_STATE" ] && [ -f "$LINKEDIN_STORAGE_STATE" ]; then
  exec npx -y @playwright/mcp@latest --storage-state="$LINKEDIN_STORAGE_STATE" "$@"
else
  exec npx -y @playwright/mcp@latest "$@"
fi
