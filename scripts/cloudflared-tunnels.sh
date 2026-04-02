#!/usr/bin/env bash
# Run multiple Cloudflare Quick Tunnels in parallel (one process per local service).
# Quick tunnels = new trycloudflare.com URL each run — update .env after restart.
#
# Default: Draft Editor (8081) + DeerFlow Gateway (8001).
# Override:
#   CLOUDFLARED_TUNNELS="8081:draft-editor 3000:deerflow-ui" ./scripts/cloudflared-tunnels.sh
#
# Logs: agent-lab/.cloudflared-logs/<label>.log — grep trycloudflare.com for the URL.
#
# Typical .env after copying URLs:
#   CALENDAR_PUBLIC_BASE_URL=https://....trycloudflare.com   # draft-editor log
#   (optional) public URLs for mobile clients hitting Gateway — use the 8001 tunnel URL

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOGDIR="${ROOT}/.cloudflared-logs"
mkdir -p "$LOGDIR"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Install: brew install cloudflare/cloudflare/cloudflared"
  echo "Docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
  exit 1
fi

# Space-separated "PORT:label" (label = safe filename, no spaces)
CLOUDFLARED_TUNNELS="${CLOUDFLARED_TUNNELS:-8081:draft-editor 8001:deerflow-gateway}"

PIDS=()
cleanup() {
  echo ""
  echo "Stopping tunnels…"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "Starting ${CLOUDFLARED_TUNNELS// / + } tunnel(s). Logs under .cloudflared-logs/"
echo ""

for spec in $CLOUDFLARED_TUNNELS; do
  case "$spec" in
    *:*)
      port="${spec%%:*}"
      label="${spec#*:}"
      ;;
    *)
      echo "Bad spec '$spec' — use PORT:label (e.g. 8081:draft-editor)" >&2
      exit 1
      ;;
  esac
  if ! [[ "$port" =~ ^[0-9]+$ ]]; then
    echo "Bad port in '$spec'" >&2
    exit 1
  fi
  log="${LOGDIR}/${label}.log"
  url="http://127.0.0.1:${port}"
  echo "  [$label] $url  →  $log"
  : >"$log"
  cloudflared tunnel --url "$url" >>"$log" 2>&1 &
  PIDS+=($!)
done

echo ""
echo "URLs (wait a few seconds, then):"
for spec in $CLOUDFLARED_TUNNELS; do
  label="${spec#*:}"
  echo "  grep -o 'https://[^ ]*trycloudflare.com' \"${LOGDIR}/${label}.log\" | head -1\""
done
echo ""
echo "Or: tail -f .cloudflared-logs/draft-editor.log"
echo "Press Ctrl+C to stop all tunnels."
echo ""

wait
