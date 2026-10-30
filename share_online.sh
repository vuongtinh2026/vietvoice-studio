#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 1. Đảm bảo server đang chạy trên port 3000
if ! lsof -i :3000 > /dev/null 2>&1; then
  echo "Đang khởi động máy chủ VietVoice Studio..."
  nohup /opt/homebrew/bin/node server.js > /tmp/vietvoice.log 2>&1 &
  sleep 1.5
fi

# 2. Chạy Cloudflare Tunnel
echo "=========================================================="
echo "🌐 Đang tạo đường link chia sẻ online ra toàn thế giới..."
echo "=========================================================="
/opt/homebrew/bin/cloudflared tunnel --url http://localhost:3000
