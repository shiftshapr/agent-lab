#!/usr/bin/env bash
# Install Chromium for the same Playwright version that @playwright/mcp ships with.
# Uses scripts/playwright-mcp-browsers/ (local npm package) so `playwright install` does not
# warn about missing project dependencies. Run after @playwright/mcp updates, or if MCP fails
# with "browser not found".
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_DIR="$SCRIPT_DIR/playwright-mcp-browsers"
PW_VER=$(npm view @playwright/mcp@latest dependencies.playwright)

cd "$PKG_DIR"
CURRENT=$(node -p "require('./package.json').dependencies?.playwright || ''" 2>/dev/null || echo "")

if [ "$CURRENT" != "$PW_VER" ]; then
  echo "Syncing playwright dependency to ${PW_VER} (was ${CURRENT:-unset})..."
  npm pkg set "dependencies.playwright=${PW_VER}"
  npm install
elif [ ! -d node_modules/playwright ]; then
  echo "Installing npm dependencies in playwright-mcp-browsers..."
  npm install
fi

echo "Ensuring Chromium for Playwright ${PW_VER} (matches @playwright/mcp@latest)..."
npm run install-browsers
