#!/usr/bin/env bash
# Expose **only** the Draft Editor via quick tunnel (same as before).
# For Draft Editor + DeerFlow Gateway together, use:
#   ./scripts/cloudflared-tunnels.sh
#
# Copy URL → CALENDAR_PUBLIC_BASE_URL in .env (see .cloudflared-logs/draft-editor.log)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${DRAFT_EDITOR_PORT:-8081}"
export CLOUDFLARED_TUNNELS="${CLOUDFLARED_TUNNELS:-${PORT}:draft-editor}"
exec "$SCRIPT_DIR/cloudflared-tunnels.sh"
