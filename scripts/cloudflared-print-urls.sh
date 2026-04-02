#!/usr/bin/env bash
# Print current trycloudflare.com URLs from tunnel logs (after cloudflared-tunnels.sh is running).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOGDIR="${ROOT}/.cloudflared-logs"

if [[ ! -d "$LOGDIR" ]]; then
  echo "No logs yet. Run ./scripts/cloudflared-tunnels.sh first."
  exit 1
fi

found=0
for f in "$LOGDIR"/*.log; do
  [[ -e "$f" ]] || continue
  url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$f" 2>/dev/null | head -1 || true)
  if [[ -n "$url" ]]; then
    echo "$(basename "$f" .log): $url"
    found=1
  fi
done

if [[ "$found" -eq 0 ]]; then
  echo "No trycloudflare.com URL found yet — wait a few seconds and retry, or tail a log:"
  ls -la "$LOGDIR"
fi
