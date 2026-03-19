#!/usr/bin/env bash
# Start Hermes Agent with PATH configured
# Usage: ./scripts/hermes-start.sh [chat|gateway|doctor]

export PATH="$HOME/.hermes/hermes-agent/venv/bin:$PATH"

case "${1:-chat}" in
  chat)    hermes ;;
  gateway) hermes gateway ;;
  doctor)  hermes doctor ;;
  *)       hermes "$@" ;;
esac
