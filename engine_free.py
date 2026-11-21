#!/usr/bin/env python3
"""
VoiceViet Open-Source & Free AI TTS Engine (v2.0 - Authentic Models)
- Piper TTS ONNX (NGHI-TTS Apache-2.0): Ngọc Huyền, Thiện Tâm, Minh Quân, Adam TikTok,
  Mạnh Dũng, Ban Mai, Ngọc Ngạn, Tài An, Minh Khang, Duy Oryx, Chiêu Thành, Lạc Phi...
  (Chạy 100% Offline trên CPU, tự động tải model lần đầu và lưu cache vĩnh viễn)
- Microsoft Edge Neural TTS: Hoài My (vi-VN-HoaiMyNeural), Nam Minh (vi-VN-NamMinhNeural),
  Jenny, Guy, Nanami, Xiaoxiao (Chuẩn giọng gốc, tuyệt đối không tráo sang giọng khác)
- Google Translate TTS: Chị Google (Tự động chia nhỏ câu dài <= 175 ký tự không bao giờ lỗi)
Tất cả đều xuất chuẩn WAV 22050Hz 16-bit Mono PCM đồng nhất cho toàn hệ thống!
"""
import asyncio
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import wave

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OPEN_MODELS_DIR = os.path.join(BASE_DIR, "open_models")
HF_PIPER_BASE = "https://huggingface.co/doof-ferb/nghitts-copy/resolve/main/piper-tts"


def resolve_ffmpeg() -> str:
    cmd = shutil.which("ffmpeg")
    if cmd:
        return cmd
    for p in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"):
        if os.path.exists(p):
            return p
    return "ffmpeg"


FFMPEG_BIN = resolve_ffmpeg()

FREE_VOICES = [
    # === TOP 7 GIỌNG AI MIỄN PHÍ NỔI BẬT ===
    {
        "id": "free-vi-ngoc-huyen",
        "name": "Ngọc Huyền",
        "gender": "Nữ",
        "language": "vi",
        "provider": "piper",
        "model": "ngochuyennew.onnx",
        "featured": True,
        "useCase": "Review phim, Tóm tắt truyện, Kể chuyện cuốn hút (Giọng gốc chuẩn)",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-thien-tam",
        "name": "Thiện Tâm",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "thientam.onnx",
        "featured": True,
        "useCase": "Truyện Phật pháp, Tâm linh, Sách nói sâu lắng đêm khuya (Giọng gốc)",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-minh-quan",
        "name": "Minh Quân",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "minhquang.onnx",
        "featured": True,
        "useCase": "Bình luận phim, Tin tức công nghệ, Thời sự dõng dạc (Giọng gốc)",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-adam-tiktok",
        "name": "Adam TikTok",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "adam1.onnx",
        "featured": True,
        "useCase": "Giọng trầm Adam huyền thoại trên TikTok / Reels / Shorts (Giọng gốc)",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-hoaimy",
        "name": "Hoài My (Neural)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "edge",
        "model": "vi-VN-HoaiMyNeural",
        "featured": True,
        "useCase": "Giọng Nữ Microsoft Neural ngọt ngào, Tiểu thuyết, Ngôn tình",
        "badge": "FREE NEURAL",
    },
    {
        "id": "free-vi-namminh",
        "name": "Nam Minh (Neural)",
        "gender": "Nam",
        "language": "vi",
        "provider": "edge",
        "model": "vi-VN-NamMinhNeural",
        "featured": True,
        "useCase": "Giọng Nam Microsoft Neural đĩnh đạc, Phóng sự, Ký sự",
        "badge": "FREE NEURAL",
    },
    {
        "id": "free-vi-google",
        "name": "Chị Google",
        "gender": "Nữ",
        "language": "vi",
        "provider": "google",
        "model": "vi",
        "featured": True,
        "useCase": "Giọng Chị Google huyền thoại đọc Meme TikTok, Tin nhanh",
        "badge": "FREE GOOGLE",
    },
    # === KHO GIỌNG VIỆT MÃ NGUỒN MỞ MỞ RỘNG (PIPER ONNX OFFLINE) ===
    {
        "id": "free-vi-ngoc-ngan",
        "name": "Ngọc Ngạn",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "ngocngan3701.onnx",
        "featured": False,
        "useCase": "Kể chuyện đêm khuya, Truyện ma, Văn học truyền cảm",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-tai-an",
        "name": "Tài An (CD Media)",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "taian4.onnx",
        "featured": False,
        "useCase": "Phân tích Lịch sử, Địa chính trị, Kinh tế, Tài liệu",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-manh-dung",
        "name": "Mạnh Dũng",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "manhdung.onnx",
        "featured": False,
        "useCase": "Quảng cáo TVC, Thuyết minh hào sảng, Giới thiệu sản phẩm",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-ban-mai",
        "name": "Ban Mai",
        "gender": "Nữ",
        "language": "vi",
        "provider": "piper",
        "model": "banmai.onnx",
        "featured": False,
        "useCase": "Giọng Nữ miền Bắc chuẩn mực, Tin tức, Sách nói",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-minh-khang",
        "name": "Minh Khang (Kiến Giải Mã)",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "minhkhang.onnx",
        "featured": False,
        "useCase": "Thuyết minh Khoa học, Khám phá bí ẩn, Kiến thức thú vị",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-duy-oryx",
        "name": "Duy Oryx (Siêu trầm)",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "duyoryx3175.onnx",
        "featured": False,
        "useCase": "Giọng Nam siêu trầm điện ảnh, Podcast đêm muộn, Trailer",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-chieu-thanh",
        "name": "Chiêu Thành",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "chieuthanh.onnx",
        "featured": False,
        "useCase": "Truyện Kiếm hiệp, Tiên hiệp, Cổ phong hào hùng",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-lac-phi",
        "name": "Lạc Phi",
        "gender": "Nữ",
        "language": "vi",
        "provider": "piper",
        "model": "lacphi.onnx",
        "featured": False,
        "useCase": "Tiểu thuyết Ngôn tình, Cổ trang, Nữ hiệp thanh tao",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-kinh-phat",
        "name": "Kinh Phật Trang Nghiêm",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "kinhphat.onnx",
        "featured": False,
        "useCase": "Đọc Kinh kệ, Pháp thoại, Thiền định thanh tịnh",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-mai-phuong",
        "name": "Mai Phương",
        "gender": "Nữ",
        "language": "vi",
        "provider": "piper",
        "model": "maiphuong.onnx",
        "featured": False,
        "useCase": "Tâm sự tình cảm, Radio cảm xúc, Đọc truyện nhẹ nhàng",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-phuong-trang",
        "name": "Phương Trang",
        "gender": "Nữ",
        "language": "vi",
        "provider": "piper",
        "model": "phuongtrang.onnx",
        "featured": False,
        "useCase": "Giọng Nữ miền Nam ngọt ngào, Ẩm thực, Du lịch, Vlog",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-thanh-phuong",
        "name": "Thanh Phương",
        "gender": "Nữ",
        "language": "vi",
        "provider": "piper",
        "model": "thanhphuong2.onnx",
        "featured": False,
        "useCase": "Phát thanh viên chuẩn mực, Bài giảng E-learning, Thuyết trình",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-minh-thu",
        "name": "Minh Thư",
        "gender": "Nữ",
        "language": "vi",
        "provider": "piper",
        "model": "minhthu.onnx",
        "featured": False,
        "useCase": "Podcast trẻ trung, Chữa lành, Tâm lý đời sống",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-tran-thanh",
        "name": "Trấn Thành",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "tranthanh3870.onnx",
        "featured": False,
        "useCase": "Giàu cảm xúc, Chia sẻ góc nhìn đời sống, Kể chuyện",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-viet-thao",
        "name": "Việt Thảo",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "vietthao3886.onnx",
        "featured": False,
        "useCase": "Kể chuyện duyên dáng, Văn hóa, Ẩm thực, Chuyện đời thường",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-vu-nga",
        "name": "Vũ Nga",
        "gender": "Nữ",
        "language": "vi",
        "provider": "piper",
        "model": "vunga.onnx",
        "featured": False,
        "useCase": "Đọc truyện dài kỳ, Truyện gia đình, Tâm lý xã hội",
        "badge": "OFFLINE AI",
    },
    {
        "id": "free-vi-yan-news",
        "name": "YAN News",
        "gender": "Nữ",
        "language": "vi",
        "provider": "piper",
        "model": "yannew.onnx",
        "featured": False,
        "useCase": "Tin tức Giải trí, Showbiz, Xu hướng giới trẻ năng động",
        "badge": "OFFLINE AI",
    },
    # === GIỌNG QUỐC TẾ MIỄN PHÍ ===
    {
        "id": "free-en-jenny",
        "name": "Jenny (US Neural)",
        "gender": "Nữ",
        "language": "en",
        "provider": "edge",
        "model": "en-US-JennyNeural",
        "featured": False,
        "useCase": "Tiếng Anh Mỹ tự nhiên, Podcast, Hội thoại",
        "badge": "FREE NEURAL",
    },
    {
        "id": "free-en-guy",
        "name": "Guy (US Neural)",
        "gender": "Nam",
        "language": "en",
        "provider": "edge",
        "model": "en-US-GuyNeural",
        "featured": False,
        "useCase": "Tiếng Anh Mỹ trầm ấm, Thuyết trình, Tin tức",
        "badge": "FREE NEURAL",
    },
    {
        "id": "free-ja-nanami",
        "name": "Nanami (Japanese)",
        "gender": "Nữ",
        "language": "ja",
        "provider": "edge",
        "model": "ja-JP-NanamiNeural",
        "featured": False,
        "useCase": "Tiếng Nhật tự nhiên, Anime, Đàm thoại",
        "badge": "FREE NEURAL",
    },
    {
        "id": "free-zh-xiaoxiao",
        "name": "Xiaoxiao (Chinese)",
        "gender": "Nữ",
        "language": "zh",
        "provider": "edge",
        "model": "zh-CN-XiaoxiaoNeural",
        "featured": False,
        "useCase": "Tiếng Trung phổ thông biểu cảm, Review phim",
        "badge": "FREE NEURAL",
    },
]

VOICE_MAP = {v["id"]: v for v in FREE_VOICES}


def download_file_atomic(url: str, dest_path: str, min_bytes: int = 500) -> None:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) >= min_bytes:
        return
    tmp_path = f"{dest_path}.part.{os.getpid()}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VoiceVietStudio/2.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(tmp_path, "wb") as out:
            shutil.copyfileobj(resp, out)
        if os.path.getsize(tmp_path) < min_bytes:
            raise RuntimeError(f"Downloaded file too small: {dest_path}")
        os.replace(tmp_path, dest_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def ensure_piper_model(onnx_filename: str) -> tuple[str, str]:
    cfg_path = os.path.join(OPEN_MODELS_DIR, "config.json")
    model_path = os.path.join(OPEN_MODELS_DIR, onnx_filename)
    download_file_atomic(f"{HF_PIPER_BASE}/config.json", cfg_path, min_bytes=500)
    download_file_atomic(f"{HF_PIPER_BASE}/{onnx_filename}", model_path, min_bytes=5_000_000)
    return model_path, cfg_path


def synthesize_piper_wav(text: str, onnx_filename: str, rate: float = 1.0, pause_sec: float = 0.35) -> bytes:
    from piper import PiperVoice, SynthesisConfig

    model_path, cfg_path = ensure_piper_model(onnx_filename)
    voice = PiperVoice.load(model_path, config_path=cfg_path)

    safe_rate = max(0.5, min(2.0, rate))
    length_scale = 1.0 / safe_rate
    syn_conf = SynthesisConfig(
        length_scale=length_scale,
        noise_scale=0.667,
        noise_w_scale=0.8,
    )

    sample_rate = voice.config.sample_rate or 22050
    sent_silence = b"\x00\x00" * int(max(0.05, pause_sec) * sample_rate)
    para_silence = b"\x00\x00" * int(max(0.1, pause_sec * 1.6) * sample_rate)

    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    pcm_parts: list[bytes] = []

    for p_idx, para in enumerate(paragraphs):
        para_chunks: list[bytes] = []
        for chunk in voice.synthesize(para, syn_config=syn_conf):
            sample_rate = chunk.sample_rate
            if chunk.audio_int16_bytes:
                para_chunks.append(chunk.audio_int16_bytes)
        if para_chunks:
            pcm_parts.append(sent_silence.join(para_chunks))
            if p_idx < len(paragraphs) - 1:
                pcm_parts.append(para_silence)

    if not pcm_parts:
        pcm_parts.append(b"\x00\x00" * int(0.2 * sample_rate))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for part in pcm_parts:
            wf.writeframes(part)
    return buf.getvalue()


def mp3_to_wav_bytes(mp3_path: str, out_wav_path: str, rate: float = 1.0) -> bytes:
    cmd = [FFMPEG_BIN, "-y", "-i", mp3_path, "-ar", "22050", "-ac", "1", "-sample_fmt", "s16"]
    if abs(rate - 1.0) > 0.02 and 0.5 <= rate <= 2.0:
        cmd.extend(["-filter:a", f"atempo={rate:.2f}"])
    cmd.append(out_wav_path)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(out_wav_path, "rb") as f:
        return f.read()


async def synthesize_edge_wav(text: str, edge_voice: str, rate: float = 1.0) -> bytes:
    import edge_tts

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_mp3 = os.path.join(tmpdir, "edge_raw.mp3")
        out_wav = os.path.join(tmpdir, "edge_out.wav")

        last_err = None
        for attempt in range(5):
            try:
                comm = edge_tts.Communicate(text, edge_voice)
                await comm.save(raw_mp3)
                if os.path.exists(raw_mp3) and os.path.getsize(raw_mp3) > 100:
                    last_err = None
                    break
            except Exception as e:
                last_err = e
                await asyncio.sleep(0.45 * (attempt + 1))

        if last_err is not None or not os.path.exists(raw_mp3) or os.path.getsize(raw_mp3) <= 100:
            raise RuntimeError(
                f"Máy chủ Microsoft Edge Neural đang bận tạm thời ({last_err}). "
                f"Vui lòng bấm thử lại sau 2 giây hoặc dùng các giọng Offline AI (Ngọc Huyền, Thiện Tâm, Minh Quân, Adam TikTok)."
            )

        return mp3_to_wav_bytes(raw_mp3, out_wav, rate=rate)


def split_for_google_tts(text: str, max_len: int = 175) -> list[str]:
    sentences = re.split(r"(?<=[.?!;\n])\s+", text.strip())
    chunks: list[str] = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(sent) <= max_len:
            chunks.append(sent)
        else:
            # Split further by comma or space
            clauses = re.split(r"(?<=[,:])\s+", sent)
            cur = ""
            for cl in clauses:
                if len(cl) > max_len:
                    words = cl.split()
                    for w in words:
                        if len(cur) + len(w) + 1 <= max_len:
                            cur = f"{cur} {w}".strip()
                        else:
                            if cur:
                                chunks.append(cur)
                            cur = w
                elif len(cur) + len(cl) + 1 <= max_len:
                    cur = f"{cur} {cl}".strip()
                else:
                    if cur:
                        chunks.append(cur)
                    cur = cl
            if cur:
                chunks.append(cur)
    return chunks or [text[:max_len]]


def synthesize_google_wav(text: str, lang: str = "vi", rate: float = 1.0) -> bytes:
    chunks = split_for_google_tts(text, max_len=175)
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_mp3 = os.path.join(tmpdir, "google_raw.mp3")
        out_wav = os.path.join(tmpdir, "google_out.wav")

        with open(raw_mp3, "wb") as out_f:
            for ch in chunks:
                url = "https://translate.google.com/translate_tts?" + urllib.parse.urlencode(
                    {
                        "ie": "UTF-8",
                        "q": ch,
                        "tl": lang,
                        "client": "tw-ob",
                    }
                )
                for attempt in range(3):
                    try:
                        req = urllib.request.Request(
                            url,
                            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                        )
                        with urllib.request.urlopen(req, timeout=12) as res:
                            out_f.write(res.read())
                        break
                    except Exception:
                        if attempt == 2:
                            raise

        return mp3_to_wav_bytes(raw_mp3, out_wav, rate=rate)


async def run_synthesize(text: str, voice_id: str, rate: float = 1.0, pause_sec: float = 0.35) -> bytes:
    info = VOICE_MAP.get(voice_id) or VOICE_MAP["free-vi-ngoc-huyen"]
    provider = info["provider"]
    model = info["model"]

    if provider == "piper":
        return synthesize_piper_wav(text, model, rate=rate, pause_sec=pause_sec)
    elif provider == "edge":
        return await synthesize_edge_wav(text, model, rate=rate)
    elif provider == "google":
        return synthesize_google_wav(text, lang=model, rate=rate)
    else:
        return synthesize_piper_wav(text, "ngochuyennew.onnx", rate=rate, pause_sec=pause_sec)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "voices":
        public_voices = [
            {
                "id": v["id"],
                "name": v["name"],
                "gender": v["gender"],
                "language": v["language"],
                "provider": v["provider"],
                "featured": v["featured"],
                "useCase": v["useCase"],
                "badge": v["badge"],
            }
            for v in FREE_VOICES
        ]
        print(json.dumps({"success": True, "voices": public_voices}, ensure_ascii=False))
        return

    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            sys.exit(1)
        data = json.loads(raw_input)
        text = data.get("text", "").strip()
        voice_id = data.get("voice", "free-vi-ngoc-huyen")
        rate = float(data.get("rate", 1.0))
        pause_sec = float(data.get("pause", 0.35))

        if not text:
            sys.stderr.write("Error: Text is required\n")
            sys.exit(1)

        wav_bytes = asyncio.run(run_synthesize(text, voice_id, rate=rate, pause_sec=pause_sec))
        sys.stdout.buffer.write(wav_bytes)
        sys.stdout.buffer.flush()
    except Exception as e:
        sys.stderr.write(f"{str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
