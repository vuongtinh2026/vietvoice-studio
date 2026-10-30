#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if port 3000 is already running
if ! lsof -i :3000 > /dev/null 2>&1; then
  echo "Đang khởi động VietVoice Studio..."
  NODE_BIN="/opt/homebrew/bin/node"
  if [ ! -f "$NODE_BIN" ]; then
    NODE_BIN="$(which node)"
  fi
  nohup "$NODE_BIN" server.js > /tmp/vietvoice.log 2>&1 &
  sleep 1.5
fi

open http://localhost:3000
