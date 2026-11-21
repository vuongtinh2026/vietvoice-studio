#!/usr/bin/env python3
"""
VoiceViet Free Engine (Open Source TTS Hub)
Tích hợp các giọng AI mã nguồn mở miễn phí:
- Edge Neural AI (Hoài My, Nam Minh, Thiện Tâm, Ngọc Huyền, Minh Quân, Adam TikTok)
- Google Translate TTS (Chị Google)
- Các giọng quốc tế miễn phí (Mỹ, Anh, Nhật, Trung, Hàn)
"""
import sys
import json
import asyncio
import os
import shutil
import subprocess
import tempfile
import urllib.request
import urllib.parse

def resolve_ffmpeg():
    cmd = shutil.which("ffmpeg")
    if cmd:
        return cmd
    for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"]:
        if os.path.exists(p):
            return p
    return "ffmpeg"

FFMPEG_BIN = resolve_ffmpeg()

FREE_VOICES = [
    # --- Tiếng Việt Miễn Phí ---
    {
        "id": "free-vi-hoaimy",
        "name": "Hoài My (Neural)",
        "gender": "Nữ",
        "language": "vi",
        "useCase": "Đọc truyện tiểu thuyết, Ngôn tình, Review phim (Chuẩn Neural)",
        "tag": "Phổ biến nhất",
        "badge": "FREE NEURAL"
    },
    {
        "id": "free-vi-namminh",
        "name": "Nam Minh (Neural)",
        "gender": "Nam",
        "language": "vi",
        "useCase": "Phóng sự, Bình luận phim, Truyện kiếm hiệp (Chuẩn Neural)",
        "tag": "Trầm ấm",
        "badge": "FREE NEURAL"
    },
    {
        "id": "free-vi-thien-tam",
        "name": "Thiện Tâm",
        "gender": "Nam",
        "language": "vi",
        "useCase": "Truyện Phật pháp, Tâm linh, Sách nói sâu lắng, Đêm muộn",
        "tag": "Sâu lắng",
        "badge": "FREE SPECIAL"
    },
    {
        "id": "free-vi-ngoc-huyen",
        "name": "Ngọc Huyền",
        "gender": "Nữ",
        "language": "vi",
        "useCase": "Kể chuyện tâm sự, Video ngắn truyền cảm, Lồng tiếng",
        "tag": "Truyền cảm",
        "badge": "FREE SPECIAL"
    },
    {
        "id": "free-vi-minh-quan",
        "name": "Minh Quân",
        "gender": "Nam",
        "language": "vi",
        "useCase": "Review công nghệ, Tin tức thời sự, Bình luận thể thao",
        "tag": "Dõng dạc",
        "badge": "FREE SPECIAL"
    },
    {
        "id": "free-vi-adam-tiktok",
        "name": "Adam TikTok",
        "gender": "Nam",
        "language": "vi",
        "useCase": "TikTok Clip, Video ngắn bắt trend, Meme vui nhộn",
        "tag": "Hài hước",
        "badge": "FREE TIKTOK"
    },
    {
        "id": "free-vi-google",
        "name": "Chị Google",
        "gender": "Nữ",
        "language": "vi",
        "useCase": "Giọng đọc Google meme TikTok, Hài hước, Tin tức nhanh",
        "tag": "Huyền thoại",
        "badge": "FREE GOOGLE"
    },
    # --- Quốc Tế Miễn Phí ---
    {
        "id": "free-en-jenny",
        "name": "Jenny (US Neural)",
        "gender": "Nữ",
        "language": "en",
        "useCase": "Tiếng Anh Mỹ tự nhiên, Podcast, Hội thoại",
        "tag": "English US",
        "badge": "FREE NEURAL"
    },
    {
        "id": "free-en-guy",
        "name": "Guy (US Neural)",
        "gender": "Nam",
        "language": "en",
        "useCase": "Tiếng Anh Mỹ dõng dạc, Thuyết trình, Tin tức",
        "tag": "English US",
        "badge": "FREE NEURAL"
    },
    {
        "id": "free-ja-nanami",
        "name": "Nanami (Japanese)",
        "gender": "Nữ",
        "language": "ja",
        "useCase": "Tiếng Nhật Anime, Truyện tranh, Đàm thoại",
        "tag": "Japanese",
        "badge": "FREE NEURAL"
    },
    {
        "id": "free-zh-xiaoxiao",
        "name": "Xiaoxiao (Chinese)",
        "gender": "Nữ",
        "language": "zh",
        "useCase": "Tiếng Trung phổ thông, Phim ảnh, Lồng tiếng",
        "tag": "Chinese",
        "badge": "FREE NEURAL"
    }
]

async def synthesize_edge(text, voice_key, out_path, rate=1.0):
    import edge_tts
    tmp_path = out_path + ".raw.mp3"
    for attempt in range(3):
        try:
            c = edge_tts.Communicate(text, voice_key)
            await c.save(tmp_path)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                return tmp_path
        except Exception as e:
            if attempt == 2:
                return synthesize_google(text, tmp_path)
            await asyncio.sleep(0.4 * (attempt + 1))
    return tmp_path

def synthesize_google(text, out_path):
    # Google Translate TTS endpoint
    url = 'https://translate.google.com/translate_tts?' + urllib.parse.urlencode({
        'ie': 'UTF-8',
        'q': text,
        'tl': 'vi',
        'client': 'tw-ob'
    })
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=10) as res:
        data = res.read()
        with open(out_path, 'wb') as f:
            f.write(data)
    return out_path

async def run_synthesize(text, voice_id, rate=1.0):
    with tempfile.TemporaryDirectory() as tmpdir:
        target_mp3 = os.path.join(tmpdir, "output.mp3")

        if voice_id == "free-vi-google":
            synthesize_google(text, target_mp3)
        elif voice_id in ("free-vi-hoaimy", "free-vi-ngoc-huyen"):
            raw = await synthesize_edge(text, "vi-VN-HoaiMyNeural", target_mp3, rate)
            filter_str = []
            if voice_id == "free-vi-ngoc-huyen":
                filter_str.append("atempo=0.96")
            if rate != 1.0 and 0.5 <= rate <= 2.0:
                filter_str.append(f"atempo={rate:.2f}")
            if filter_str:
                try:
                    subprocess.run([FFMPEG_BIN, "-y", "-i", raw, "-filter:a", ",".join(filter_str), target_mp3], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    os.replace(raw, target_mp3)
            else:
                os.replace(raw, target_mp3)

        elif voice_id in ("free-vi-namminh", "free-vi-thien-tam", "free-vi-minh-quan", "free-vi-adam-tiktok"):
            raw = await synthesize_edge(text, "vi-VN-NamMinhNeural", target_mp3, rate)
            filter_str = []
            if voice_id == "free-vi-thien-tam":
                filter_str.append("atempo=0.92")
            elif voice_id == "free-vi-minh-quan":
                filter_str.append("atempo=1.06")
            elif voice_id == "free-vi-adam-tiktok":
                filter_str.append("asetrate=24000*1.08,atempo=1.05")

            if rate != 1.0 and 0.5 <= rate <= 2.0:
                filter_str.append(f"atempo={rate:.2f}")

            if filter_str:
                try:
                    subprocess.run([FFMPEG_BIN, "-y", "-i", raw, "-filter:a", ",".join(filter_str), target_mp3], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    os.replace(raw, target_mp3)
            else:
                os.replace(raw, target_mp3)

        elif voice_id == "free-en-jenny":
            raw = await synthesize_edge(text, "en-US-JennyNeural", target_mp3, rate)
            if rate != 1.0:
                try:
                    subprocess.run([FFMPEG_BIN, "-y", "-i", raw, "-filter:a", f"atempo={rate:.2f}", target_mp3], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    os.replace(raw, target_mp3)
            else:
                os.replace(raw, target_mp3)

        elif voice_id == "free-en-guy":
            raw = await synthesize_edge(text, "en-US-GuyNeural", target_mp3, rate)
            if rate != 1.0:
                try:
                    subprocess.run([FFMPEG_BIN, "-y", "-i", raw, "-filter:a", f"atempo={rate:.2f}", target_mp3], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    os.replace(raw, target_mp3)
            else:
                os.replace(raw, target_mp3)

        elif voice_id == "free-ja-nanami":
            raw = await synthesize_edge(text, "ja-JP-NanamiNeural", target_mp3, rate)
            if rate != 1.0:
                try:
                    subprocess.run([FFMPEG_BIN, "-y", "-i", raw, "-filter:a", f"atempo={rate:.2f}", target_mp3], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    os.replace(raw, target_mp3)
            else:
                os.replace(raw, target_mp3)

        elif voice_id == "free-zh-xiaoxiao":
            raw = await synthesize_edge(text, "zh-CN-XiaoxiaoNeural", target_mp3, rate)
            if rate != 1.0:
                try:
                    subprocess.run([FFMPEG_BIN, "-y", "-i", raw, "-filter:a", f"atempo={rate:.2f}", target_mp3], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    os.replace(raw, target_mp3)
            else:
                os.replace(raw, target_mp3)

        else:
            # Default fallback to Hoai My
            raw = await synthesize_edge(text, "vi-VN-HoaiMyNeural", target_mp3, rate)
            os.replace(raw, target_mp3)

        with open(target_mp3, "rb") as f:
            audio_bytes = f.read()

        sys.stdout.buffer.write(audio_bytes)
        sys.stdout.buffer.flush()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "voices":
        print(json.dumps({"success": True, "voices": FREE_VOICES}, ensure_ascii=False))
        return

    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            sys.exit(1)
        data = json.loads(raw_input)
        text = data.get("text", "").strip()
        voice_id = data.get("voice", "free-vi-hoaimy")
        rate = float(data.get("rate", 1.0))

        if not text:
            sys.stderr.write("Error: Text is required\n")
            sys.exit(1)

        asyncio.run(run_synthesize(text, voice_id, rate))
    except Exception as e:
        sys.stderr.write(f"Error in engine_free: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
