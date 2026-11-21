FROM node:20-slim

# Cài đặt ffmpeg cho tính năng nén file MP3 và python3 cho cheap-tts 24 Pro voices
RUN apt-get update && apt-get install -y ffmpeg python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt || pip3 install --no-cache-dir -r requirements.txt

COPY package*.json ./
RUN npm install --production

COPY . .

CMD ["node", "server.js"]
