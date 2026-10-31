#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 1. Đảm bảo server đang chạy trên port 3000
if ! lsof -i :3000 > /dev/null 2>&1; then
  echo "Đang khởi động máy chủ VietVoice Studio..."
  nohup /opt/homebrew/bin/node server.js > /tmp/vietvoice.log 2>&1 &
  sleep 1.5
fi

# 2. Vòng lặp tự động duy trì kết nối liên tục cho voiceviet.loca.lt
echo "=========================================================="
echo "🌐 Đang mở đường link rút gọn: https://voiceviet.loca.lt"
echo "⚡ Tự động duy trì và phục hồi kết nối nếu mạng ngắt"
echo "=========================================================="
while true; do
  ./node_modules/.bin/lt --port 3000 --subdomain voiceviet
  sleep 2
done
