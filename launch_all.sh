#!/bin/bash

# CONFIG
SMEE_URL=""
GITHUB_BOT_PORT=5000
MCP_PORT=8000

# Track PIDs
PIDS=()

# Function to launch and track processes
start_process() {
  echo "Launching: $1"
  bash -c "$1" &
  PIDS+=($!)
}

# Trap EXIT and SIGINT to clean up
cleanup() {
  echo -e "\n[Shutdown] Killing all subprocesses..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null
  done
  wait
  echo "[Shutdown] Done."
  exit 0
}
trap cleanup EXIT SIGINT

# Launch  
start_process "uvicorn mcp_server.main:app --reload --port $MCP_PORT"
start_process "uvicorn github_bot.main:app --reload --port $GITHUB_BOT_PORT"
start_process "npx smee -u $SMEE_URL --target http://localhost:${GITHUB_BOT_PORT}/webhook"

# Wait forever until killed
wait
