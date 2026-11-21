#!/usr/bin/env python3
"""
VoiceViet Studio AI Free Engine v3.0 (48kHz Studio Human-Grade + Persistent Daemon)
- VieNeu-TTS v3 Turbo (48kHz Studio Pro, 25 giọng gốc Bắc-Trung-Nam + [cười], [thở dài], [hắng giọng])
- Piper ONNX + Studio Condenser Mastering 48kHz (Minh Quân, Ngọc Ngạn, Tài An, Ban Mai, Duy Oryx...)
- Microsoft Edge Neural + Google Translate TTS (48kHz chuẩn đồng bộ)
- Bộ xử lý nhịp thở & ngắt nghỉ tự nhiên chuẩn diễn viên lồng tiếng cho dấu "..." / "…" / xuống dòng!
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
import threading
import urllib.parse
import urllib.request
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OPEN_MODELS_DIR = os.path.join(BASE_DIR, "open_models")
HF_PIPER_BASE = "https://huggingface.co/doof-ferb/nghitts-copy/resolve/main/piper-tts"
TARGET_SR = 48000


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
    # === NHÓM 1: TOP GIỌNG AI STUDIO PRO 48KHZ CHÂN THẬT NHƯ NGƯỜI THẬT (VIENEU V3 TURBO) ===
    {
        "id": "free-vi-ngoc-huyen",
        "name": "Ngọc Huyền (Studio 48kHz)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "vieneu",
        "model": "Ngọc Huyền",
        "featured": True,
        "useCase": "Nữ Bắc tự nhiên, truyền cảm — Review phim, Kể chuyện, Tóm tắt truyện",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-thien-tam",
        "name": "Thiện Tâm (Studio 48kHz)",
        "gender": "Nam",
        "language": "vi",
        "provider": "vieneu",
        "model": "Thiền Tâm Đức",
        "featured": True,
        "useCase": "Nam trầm ấm, khoan thai — Phật pháp, Tâm linh, Sách nói đêm khuya",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-minh-quan",
        "name": "Minh Quân (Studio 48kHz)",
        "gender": "Nam",
        "language": "vi",
        "provider": "vieneu",
        "model": "Minh Đức",
        "featured": True,
        "useCase": "Nam Bắc dõng dạc, sắc bén — Bình luận phim, Công nghệ, Thời sự",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-adam-tiktok",
        "name": "Adam TikTok (Studio 48kHz)",
        "gender": "Nam",
        "language": "vi",
        "provider": "vieneu",
        "model": "Adam bựa",
        "featured": True,
        "useCase": "Nam hài hước, tự nhiên — TikTok / Reels / Shorts (hỗ trợ [cười])",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-hoaimy",
        "name": "Hoài My (Neural)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "edge",
        "model": "vi-VN-HoaiMyNeural",
        "featured": True,
        "useCase": "Nữ Microsoft Neural ngọt ngào — Tiểu thuyết, Ngôn tình, Đời sống",
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
        "useCase": "Nam Microsoft Neural đĩnh đạc — Phóng sự, Ký sự, Thuyết minh",
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
        "useCase": "Giọng Chị Google huyền thoại — Meme TikTok, Tin nhanh hài hước",
        "badge": "FREE GOOGLE",
    },
    # === NHÓM 2: BỘ SƯU TẬP GIỌNG STUDIO 48KHZ ĐA VÙNG MIỀN (BẮC - TRUNG - NAM) ===
    {
        "id": "free-vi-truc-ly",
        "name": "Trúc Ly (Podcast 48kHz)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "vieneu",
        "model": "Trúc Ly",
        "featured": False,
        "useCase": "Nữ Bắc trò chuyện gần gũi — Podcast, Chữa lành, Radio tâm sự",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-pham-tuyen",
        "name": "Phạm Tuyên (Kiếm hiệp 48kHz)",
        "gender": "Nam",
        "language": "vi",
        "provider": "vieneu",
        "model": "Phạm Tuyên",
        "featured": False,
        "useCase": "Nam Bắc hào sảng, nội lực — Kiếm hiệp, Tiên hiệp, Lịch sử",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-my-duyen",
        "name": "Mỹ Duyên (Ngôn tình 48kHz)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "vieneu",
        "model": "Mỹ Duyên",
        "featured": False,
        "useCase": "Nữ miền Nam dịu dàng, truyền cảm — Ngôn tình, Truyện ngắn",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-hai-dang",
        "name": "Hải Đăng (Thời sự 48kHz)",
        "gender": "Nam",
        "language": "vi",
        "provider": "vieneu",
        "model": "Hải Đăng",
        "featured": False,
        "useCase": "Nam Bắc chuẩn phát thanh viên VTV — Bản tin, Thuyết trình",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-mai-anh",
        "name": "Mai Anh (Tin tức 48kHz)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "vieneu",
        "model": "Mai Anh",
        "featured": False,
        "useCase": "Nữ Bắc phát thanh viên sắc nét — Tin tức, Báo chí, Kinh tế",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-thien-minh",
        "name": "Thiện Minh (Kể chuyện 48kHz)",
        "gender": "Nam",
        "language": "vi",
        "provider": "vieneu",
        "model": "Thiện Minh",
        "featured": False,
        "useCase": "Nam Bắc kể chuyện ấm áp — Audiobook, Truyện đêm khuya, Trinh thám",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-thai-son",
        "name": "Thái Sơn (Miền Nam 48kHz)",
        "gender": "Nam",
        "language": "vi",
        "provider": "vieneu",
        "model": "Thái Sơn",
        "featured": False,
        "useCase": "Nam miền Nam kể chuyện trầm ấm — Lịch sử, Ký sự, Đời thường",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-ngoc-linh",
        "name": "Ngọc Linh (Cổ trang 48kHz)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "vieneu",
        "model": "Ngọc Linh",
        "featured": False,
        "useCase": "Nữ Bắc thanh tao, kể chuyện — Nữ hiệp, Cổ trang, Văn học",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-adam-nam",
        "name": "Adam Miền Nam (48kHz)",
        "gender": "Nam",
        "language": "vi",
        "provider": "vieneu",
        "model": "Adam",
        "featured": False,
        "useCase": "Nam miền Nam trẻ trung, tự nhiên — Vlog, Review, Livestream",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-quang-son",
        "name": "Quang Sơn (Miền Trung 48kHz)",
        "gender": "Nam",
        "language": "vi",
        "provider": "vieneu",
        "model": "Quang Sơn",
        "featured": False,
        "useCase": "Nam miền Trung mộc mạc, chân thật — Ký sự quê hương, Kể chuyện",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-ngoc-tran",
        "name": "Ngọc Trân (Miền Trung 48kHz)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "vieneu",
        "model": "Ngọc Trân",
        "featured": False,
        "useCase": "Nữ miền Trung ngọt ngào, sâu lắng — Tản văn, Du lịch, Ẩm thực",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-thuy-dung",
        "name": "Thùy Dung (Miền Nam 48kHz)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "vieneu",
        "model": "Thùy Dung",
        "featured": False,
        "useCase": "Nữ miền Nam chuẩn tin tức — Bản tin, Tổng đài, Thuyết minh",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-duc-tri",
        "name": "Đức Trí (Đọc truyện 48kHz)",
        "gender": "Nam",
        "language": "vi",
        "provider": "vieneu",
        "model": "Đức Trí",
        "featured": False,
        "useCase": "Nam miền Nam đọc truyện truyền cảm — Tiểu thuyết, Sách kỹ năng",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-kim-thanh",
        "name": "Kim Thanh (Đọc truyện 48kHz)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "vieneu",
        "model": "Kim Thanh",
        "featured": False,
        "useCase": "Nữ miền Nam ấm áp — Đọc truyện gia đình, Tâm lý, Thiếu nhi",
        "badge": "STUDIO 48kHz",
    },
    # === NHÓM 3: GIỌNG AI ĐẶC TRƯNG SIÊU TỐC OFFLINE (MASTERED 48KHZ) ===
    {
        "id": "free-vi-ngoc-ngan",
        "name": "Ngọc Ngạn (Truyện ma đêm khuya)",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "ngocngan3701.onnx",
        "featured": False,
        "useCase": "Giọng đọc Truyện ma, Kể chuyện đêm khuya huyền thoại (Siêu tốc)",
        "badge": "FAST OFFLINE",
    },
    {
        "id": "free-vi-tai-an",
        "name": "Tài An (CD Media Lịch sử)",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "taian4.onnx",
        "featured": False,
        "useCase": "Phân tích Lịch sử, Địa chính trị, Kinh tế (Siêu tốc Offline)",
        "badge": "FAST OFFLINE",
    },
    {
        "id": "free-vi-thien-tam-nam",
        "name": "Thiện Tâm Miền Nam (Siêu tốc)",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "thientam.onnx",
        "featured": False,
        "useCase": "Giọng Nam miền Nam đọc truyện dài siêu tốc (~0.3s/đoạn)",
        "badge": "FAST OFFLINE",
    },
    {
        "id": "free-vi-minh-quan-fast",
        "name": "Minh Quân (Bản Siêu Tốc)",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "minhquang.onnx",
        "featured": False,
        "useCase": "Bình luận nhanh hàng vạn từ siêu tốc (~0.3s/đoạn)",
        "badge": "FAST OFFLINE",
    },
    {
        "id": "free-vi-manh-dung",
        "name": "Mạnh Dũng (Quảng cáo TVC)",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "manhdung.onnx",
        "featured": False,
        "useCase": "Quảng cáo TVC hào sảng, Giới thiệu sản phẩm (Siêu tốc)",
        "badge": "FAST OFFLINE",
    },
    {
        "id": "free-vi-ban-mai",
        "name": "Ban Mai (Chuẩn giọng Bắc)",
        "gender": "Nữ",
        "language": "vi",
        "provider": "piper",
        "model": "banmai.onnx",
        "featured": False,
        "useCase": "Giọng Nữ miền Bắc chuẩn mực đọc sách báo dài (Siêu tốc)",
        "badge": "FAST OFFLINE",
    },
    {
        "id": "free-vi-duy-oryx",
        "name": "Duy Oryx (Nam Siêu Trầm)",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "duyoryx3175.onnx",
        "featured": False,
        "useCase": "Giọng Nam siêu trầm điện ảnh, Trailer, Podcast (Siêu tốc)",
        "badge": "FAST OFFLINE",
    },
    {
        "id": "free-vi-minh-khang",
        "name": "Minh Khang (Kiến Giải Mã)",
        "gender": "Nam",
        "language": "vi",
        "provider": "piper",
        "model": "minhkhang.onnx",
        "featured": False,
        "useCase": "Thuyết minh Khoa học, Khám phá bí ẩn (Siêu tốc)",
        "badge": "FAST OFFLINE",
    },
    # === NHÓM 4: GIỌNG QUỐC TẾ MIỄN PHÍ ===
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

# Global singletons for persistent warm daemon mode
_ENGINE_LOCK = threading.Lock()
_VIENEU_INSTANCE = None
_PIPER_CACHE: dict[str, object] = {}


def get_vieneu():
    global _VIENEU_INSTANCE
    if _VIENEU_INSTANCE is None:
        from vieneu import Vieneu
        _VIENEU_INSTANCE = Vieneu()
    return _VIENEU_INSTANCE


def download_file_atomic(url: str, dest_path: str, min_bytes: int = 500) -> None:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) >= min_bytes:
        return
    tmp_path = f"{dest_path}.part.{os.getpid()}.{threading.get_ident()}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VoiceVietStudio/3.0"})
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


def get_piper_voice(onnx_filename: str):
    if onnx_filename not in _PIPER_CACHE:
        from piper import PiperVoice
        cfg_path = os.path.join(OPEN_MODELS_DIR, "config.json")
        model_path = os.path.join(OPEN_MODELS_DIR, onnx_filename)
        download_file_atomic(f"{HF_PIPER_BASE}/config.json", cfg_path, min_bytes=500)
        download_file_atomic(f"{HF_PIPER_BASE}/{onnx_filename}", model_path, min_bytes=5_000_000)
        _PIPER_CACHE[onnx_filename] = PiperVoice.load(model_path, config_path=cfg_path)
    return _PIPER_CACHE[onnx_filename]


# ==============================================================================
# PROSODIC PAUSE & AUDIO MASTERING HELPERS
# ==============================================================================
def trim_and_smooth_float32(arr: np.ndarray, sr: int, thresh: float = 0.003) -> np.ndarray:
    """Trims dead leading/trailing silence while keeping natural breath tail + cosine micro-fades."""
    if arr.size == 0:
        return np.zeros(int(0.05 * sr), dtype=np.float32)
    arr = np.asarray(arr, dtype=np.float32).reshape(-1)
    idx = np.where(np.abs(arr) > thresh)[0]
    if idx.size == 0:
        return np.zeros(int(0.05 * sr), dtype=np.float32)
    pad_lead = int(0.010 * sr)
    pad_tail = int(0.025 * sr)
    start = max(0, int(idx[0]) - pad_lead)
    end = min(arr.size, int(idx[-1]) + pad_tail)
    out = arr[start:end].copy()

    fi = min(int(0.010 * sr), out.size // 4)
    fo = min(int(0.024 * sr), out.size // 3)
    if fi > 1:
        out[:fi] *= 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, fi, dtype=np.float32)))
    if fo > 1:
        out[-fo:] *= 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, fo, dtype=np.float32)))
    return out


def encode_float32_to_wav_bytes(samples: np.ndarray, sr: int = TARGET_SR) -> bytes:
    pcm16 = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16).tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16)
    return buf.getvalue()


def split_dramatic_blocks(text: str, base_pause: float = 0.40) -> list[tuple[str, float]]:
    """
    Splits text at dramatic boundaries that require explicit natural human pauses:
    - '...' / '…' / '..' (Ellipsis -> deep 1.95x lingering pause ~0.78s-0.85s!)
    - Paragraph breaks '\n' (-> 2.15x scene breath pause ~0.86s)
    - Long paragraphs > 280 chars split safely at sentence boundaries (. ? !) -> 1.15x pause
    While keeping natural internal sentence flow intact!
    """
    t = text.replace("\r\n", "\n").strip()
    if not t:
        return []

    # Normalize ellipsis variants (..., .., …) into explicit marker
    t = re.sub(r"(?:…|\.{2,})", " <ELLIPSIS> ", t)

    blocks: list[tuple[str, float]] = []
    paragraphs = [p.strip() for p in re.split(r"\n+", t) if p.strip()]

    for p_idx, para in enumerate(paragraphs):
        parts = re.split(r"(<ELLIPSIS>)", para)
        cur = ""
        for tok in parts:
            if tok == "<ELLIPSIS>":
                phrase = cur.strip(" ,;:-")
                if phrase:
                    if phrase[-1] not in ".?!":
                        phrase += "."
                    blocks.append((phrase, max(0.55, base_pause * 1.95)))
                cur = ""
            else:
                cur += tok

        rem = cur.strip(" ,;:-")
        if rem:
            # Split long continuous blocks (> 280 chars) by sentence so prosody stays crisp
            if len(rem) > 280:
                sents = re.split(r"(?<=[.?!])\s+", rem)
                buf_s = ""
                for s in sents:
                    s = s.strip()
                    if not s:
                        continue
                    if len(buf_s) + len(s) + 1 <= 260:
                        buf_s = f"{buf_s} {s}".strip() if buf_s else s
                    else:
                        if buf_s:
                            blocks.append((buf_s, max(0.30, base_pause * 1.15)))
                        buf_s = s
                if buf_s:
                    blocks.append((buf_s, max(0.30, base_pause * 1.15)))
            else:
                if rem[-1] not in ".?!":
                    rem += "."
                blocks.append((rem, max(0.30, base_pause * 1.15)))

        if blocks and p_idx < len(paragraphs) - 1:
            last_txt, last_p = blocks[-1]
            blocks[-1] = (last_txt, max(last_p, base_pause * 2.15))

    return blocks


def apply_rate_ffmpeg(wav_bytes: bytes, rate: float) -> bytes:
    if abs(rate - 1.0) <= 0.02 or not (0.5 <= rate <= 2.0):
        return wav_bytes
    with tempfile.TemporaryDirectory() as tmpdir:
        in_p = os.path.join(tmpdir, "in.wav")
        out_p = os.path.join(tmpdir, "out.wav")
        with open(in_p, "wb") as f:
            f.write(wav_bytes)
        subprocess.run(
            [
                FFMPEG_BIN, "-y", "-i", in_p,
                "-filter:a", f"atempo={rate:.2f}",
                "-ar", str(TARGET_SR), "-ac", "1", "-sample_fmt", "s16",
                out_p,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with open(out_p, "rb") as f:
            return f.read()


# ==============================================================================
# 1. VIENEU-TTS V3 TURBO 48KHZ STUDIO PRO SYNTHESIS
# ==============================================================================
def synthesize_vieneu_48k(text: str, preset_voice: str, rate: float = 1.0, pause_sec: float = 0.40) -> bytes:
    tts = get_vieneu()
    blocks = split_dramatic_blocks(text, base_pause=pause_sec)
    if not blocks:
        return encode_float32_to_wav_bytes(np.zeros(int(0.2 * TARGET_SR), dtype=np.float32), TARGET_SR)

    pieces: list[np.ndarray] = []
    for idx, (phrase, after_pause) in enumerate(blocks):
        # Clean stray smart quotes that aren't emotion tags [cười]/[thở dài]/[hắng giọng]
        clean_phrase = re.sub(r"[“”\"«»]", "", phrase).strip()
        if not clean_phrase:
            continue
        audio_f32 = tts.infer(clean_phrase, voice=preset_voice)
        seg = trim_and_smooth_float32(audio_f32, TARGET_SR)
        pieces.append(seg)
        if idx < len(blocks) - 1 and after_pause > 0:
            pieces.append(np.zeros(int(after_pause * TARGET_SR), dtype=np.float32))

    if not pieces:
        full = np.zeros(int(0.2 * TARGET_SR), dtype=np.float32)
    else:
        full = np.concatenate(pieces)
        # Gentle peak normalization to -1.0 dBFS for broadcast consistency
        peak = float(np.max(np.abs(full)))
        if peak > 0.01:
            full = full * (0.89 / peak)

    wav_bytes = encode_float32_to_wav_bytes(full, TARGET_SR)
    return apply_rate_ffmpeg(wav_bytes, rate)


# ==============================================================================
# 2. PIPER ONNX + 48KHZ STUDIO CONDENSER MASTERING
# ==============================================================================
def segment_piper_prosody(text: str, base_pause: float = 0.40) -> list[tuple[str, float]]:
    t = text.replace("\r\n", "\n")
    # Fix espeak-ng bug reading "(" as "chấm"
    t = re.sub(r"\(\s*([^)]*?)\s*\)", r", \1, ", t)
    t = re.sub(r"[“”\"«»]", " ", t)
    t = re.sub(r"(?:…|\.{2,})", " <ELLIPSIS> ", t)
    t = re.sub(r"(?:^|\s)[—–\-](?=\s)", " <DASH> ", t)

    segments: list[tuple[str, float]] = []
    paragraphs = [p.strip() for p in re.split(r"\n+", t) if p.strip()]
    for p_idx, para in enumerate(paragraphs):
        tokens = re.split(r"(<ELLIPSIS>|<DASH>|[.?!;:])", para)
        buf = ""
        for tok in tokens:
            if not tok:
                continue
            if tok == "<ELLIPSIS>":
                phr = buf.strip(" ,;:-")
                if phr:
                    segments.append((phr + ".", max(0.55, base_pause * 1.95)))
                buf = ""
            elif tok == "<DASH>":
                phr = buf.strip(" ,;:-")
                if phr:
                    segments.append((phr + ",", base_pause * 0.85))
                buf = ""
            elif tok in (".", "?", "!"):
                phr = buf.strip(" ,;:-")
                if phr:
                    mult = 1.30 if tok in ("?", "!") else 1.15
                    segments.append((phr + tok, base_pause * mult))
                buf = ""
            elif tok in (";", ":"):
                phr = buf.strip(" ,;:-")
                if phr:
                    segments.append((phr + ",", base_pause * 0.85))
                buf = ""
            else:
                buf += tok
        rem = buf.strip(" ,;:-")
        if rem:
            segments.append((rem + ".", base_pause * 1.15))
        if segments and p_idx < len(paragraphs) - 1:
            s_txt, s_p = segments[-1]
            segments[-1] = (s_txt, max(s_p, base_pause * 2.15))
    return segments


def synthesize_piper_mastered_48k(text: str, onnx_filename: str, rate: float = 1.0, pause_sec: float = 0.40) -> bytes:
    from piper import SynthesisConfig

    voice = get_piper_voice(onnx_filename)
    safe_rate = max(0.5, min(2.0, rate))
    # Slight 1.04 base length_scale gives natural human diction instead of rushed VITS cadence
    syn_conf = SynthesisConfig(
        length_scale=1.04 / safe_rate,
        noise_scale=0.60,
        noise_w_scale=0.45,
    )

    segs = segment_piper_prosody(text, base_pause=pause_sec)
    sr = voice.config.sample_rate or 22050
    pieces: list[np.ndarray] = []

    for idx, (phr, after_pause) in enumerate(segs):
        chunks = list(voice.synthesize(phr, syn_config=syn_conf))
        if chunks:
            sr = chunks[0].sample_rate
            raw_b = b"".join(c.audio_int16_bytes for c in chunks if c.audio_int16_bytes)
            if raw_b:
                arr = np.frombuffer(raw_b, dtype=np.int16).astype(np.float32) / 32768.0
                pieces.append(trim_and_smooth_float32(arr, sr))
                if idx < len(segs) - 1 and after_pause > 0:
                    pieces.append(np.zeros(int(after_pause * sr), dtype=np.float32))

    if not pieces:
        pieces.append(np.zeros(int(0.2 * sr), dtype=np.float32))

    raw_wav = encode_float32_to_wav_bytes(np.concatenate(pieces), sr)

    # Studio condenser EQ + 48kHz upsampling + gentle broadcast compressor
    with tempfile.TemporaryDirectory() as tmpdir:
        in_p = os.path.join(tmpdir, "piper_raw.wav")
        out_p = os.path.join(tmpdir, "piper_master.wav")
        with open(in_p, "wb") as f:
            f.write(raw_wav)
        af_chain = (
            "highpass=f=70,"
            f"aresample={TARGET_SR},"
            "equalizer=f=165:t=q:w=1.0:g=1.8,"
            "equalizer=f=3300:t=q:w=1.2:g=1.4,"
            "lowpass=f=10200,"
            "acompressor=threshold=-19dB:ratio=2.0:attack=15:release=180:makeup=1.4,"
            "alimiter=limit=0.91:level=false"
        )
        subprocess.run(
            [FFMPEG_BIN, "-y", "-i", in_p, "-af", af_chain, "-ar", str(TARGET_SR), "-ac", "1", "-sample_fmt", "s16", out_p],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with open(out_p, "rb") as f:
            return f.read()


# ==============================================================================
# 3. EDGE NEURAL & GOOGLE TRANSLATE WITH TRUE ELLIPSIS PAUSES (48KHZ WAV)
# ==============================================================================
def mp3_to_float32_48k(mp3_path: str, rate: float = 1.0) -> np.ndarray:
    out_wav = mp3_path + ".48k.wav"
    cmd = [FFMPEG_BIN, "-y", "-i", mp3_path, "-ar", str(TARGET_SR), "-ac", "1", "-sample_fmt", "s16"]
    if abs(rate - 1.0) > 0.02 and 0.5 <= rate <= 2.0:
        cmd.extend(["-filter:a", f"atempo={rate:.2f}"])
    cmd.append(out_wav)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with wave.open(out_wav, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


async def synthesize_edge_48k(text: str, edge_voice: str, rate: float = 1.0, pause_sec: float = 0.40) -> bytes:
    import edge_tts

    blocks = split_dramatic_blocks(text, base_pause=pause_sec)
    pieces: list[np.ndarray] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, (phrase, after_pause) in enumerate(blocks):
            clean_phrase = re.sub(r"\[(?:cười|thở dài|hắng giọng)\]", "", phrase)
            raw_mp3 = os.path.join(tmpdir, f"edge_{idx}.mp3")
            last_err = None
            for attempt in range(5):
                try:
                    comm = edge_tts.Communicate(clean_phrase, edge_voice)
                    await comm.save(raw_mp3)
                    if os.path.exists(raw_mp3) and os.path.getsize(raw_mp3) > 100:
                        last_err = None
                        break
                except Exception as e:
                    last_err = e
                    await asyncio.sleep(0.45 * (attempt + 1))

            if last_err is not None or not os.path.exists(raw_mp3) or os.path.getsize(raw_mp3) <= 100:
                raise RuntimeError(
                    f"Máy chủ Microsoft Edge Neural đang bận tạm thời. "
                    f"Bạn hãy chọn các giọng Studio 48kHz (Ngọc Huyền, Thiện Tâm, Minh Quân, Trúc Ly...) để chạy Offline 100% siêu mượt nhé!"
                )

            arr = mp3_to_float32_48k(raw_mp3, rate=rate)
            pieces.append(trim_and_smooth_float32(arr, TARGET_SR))
            if idx < len(blocks) - 1 and after_pause > 0:
                pieces.append(np.zeros(int(after_pause * TARGET_SR), dtype=np.float32))

    if not pieces:
        pieces.append(np.zeros(int(0.2 * TARGET_SR), dtype=np.float32))
    return encode_float32_to_wav_bytes(np.concatenate(pieces), TARGET_SR)


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
            words = sent.split()
            cur = ""
            for w in words:
                if len(cur) + len(w) + 1 <= max_len:
                    cur = f"{cur} {w}".strip()
                else:
                    if cur:
                        chunks.append(cur)
                    cur = w
            if cur:
                chunks.append(cur)
    return chunks or [text[:max_len]]


def synthesize_google_48k(text: str, lang: str = "vi", rate: float = 1.0, pause_sec: float = 0.40) -> bytes:
    blocks = split_dramatic_blocks(text, base_pause=pause_sec)
    pieces: list[np.ndarray] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for b_idx, (phrase, after_pause) in enumerate(blocks):
            clean_phrase = re.sub(r"\[(?:cười|thở dài|hắng giọng)\]", "", phrase)
            sub_chunks = split_for_google_tts(clean_phrase, max_len=175)
            raw_mp3 = os.path.join(tmpdir, f"g_{b_idx}.mp3")
            with open(raw_mp3, "wb") as out_f:
                for ch in sub_chunks:
                    url = "https://translate.google.com/translate_tts?" + urllib.parse.urlencode(
                        {"ie": "UTF-8", "q": ch, "tl": lang, "client": "tw-ob"}
                    )
                    for attempt in range(3):
                        try:
                            req = urllib.request.Request(
                                url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
                            )
                            with urllib.request.urlopen(req, timeout=12) as res:
                                out_f.write(res.read())
                            break
                        except Exception:
                            if attempt == 2:
                                raise
            arr = mp3_to_float32_48k(raw_mp3, rate=rate)
            pieces.append(trim_and_smooth_float32(arr, TARGET_SR))
            if b_idx < len(blocks) - 1 and after_pause > 0:
                pieces.append(np.zeros(int(after_pause * TARGET_SR), dtype=np.float32))

    if not pieces:
        pieces.append(np.zeros(int(0.2 * TARGET_SR), dtype=np.float32))
    return encode_float32_to_wav_bytes(np.concatenate(pieces), TARGET_SR)


def dispatch_synthesize(text: str, voice_id: str, rate: float = 1.0, pause_sec: float = 0.40) -> bytes:
    info = VOICE_MAP.get(voice_id) or VOICE_MAP["free-vi-ngoc-huyen"]
    provider = info["provider"]
    model = info["model"]

    with _ENGINE_LOCK:
        if provider == "vieneu":
            return synthesize_vieneu_48k(text, model, rate=rate, pause_sec=pause_sec)
        elif provider == "piper":
            return synthesize_piper_mastered_48k(text, model, rate=rate, pause_sec=pause_sec)
        elif provider == "edge":
            return asyncio.run(synthesize_edge_48k(text, model, rate=rate, pause_sec=pause_sec))
        elif provider == "google":
            return synthesize_google_48k(text, lang=model, rate=rate, pause_sec=pause_sec)
        else:
            return synthesize_vieneu_48k(text, "Ngọc Huyền", rate=rate, pause_sec=pause_sec)


def get_public_voices() -> list[dict]:
    return [
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


# ==============================================================================
# PERSISTENT WARM HTTP DAEMON (ZERO COLD-START LATENCY!)
# ==============================================================================
class EngineDaemonHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"ok": True, "warm": _VIENEU_INSTANCE is not None}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/voices":
            body = json.dumps({"success": True, "voices": get_public_voices()}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/synthesize":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw or "{}")
            text = data.get("text", "").strip()
            voice_id = data.get("voice", "free-vi-ngoc-huyen")
            rate = float(data.get("rate", 1.0))
            pause_sec = float(data.get("pause", 0.40))
            if not text:
                raise ValueError("Vui lòng nhập văn bản.")

            wav_bytes = dispatch_synthesize(text, voice_id, rate=rate, pause_sec=pause_sec)
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav_bytes)))
            self.end_headers()
            self.wfile.write(wav_bytes)
        except Exception as e:
            err_body = json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)


def run_daemon(port: int = 3099) -> None:
    # Pre-warm VieNeu v3 Turbo in background thread so /health responds immediately
    def _warmup():
        try:
            with _ENGINE_LOCK:
                get_vieneu()
            sys.stderr.write(f"[VoiceViet Daemon] VieNeu v3 Turbo 48kHz warmed up in RAM on port {port}!\n")
        except Exception as e:
            sys.stderr.write(f"[VoiceViet Daemon] Warmup note: {e}\n")

    threading.Thread(target=_warmup, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), EngineDaemonHandler)
    sys.stderr.write(f"[VoiceViet Daemon] Listening at http://127.0.0.1:{port}\n")
    server.serve_forever()


def main() -> None:
    if len(sys.argv) > 1:
        if sys.argv[1] == "voices":
            print(json.dumps({"success": True, "voices": get_public_voices()}, ensure_ascii=False))
            return
        if sys.argv[1] == "daemon":
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 3099
            run_daemon(port)
            return

    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            sys.exit(1)
        data = json.loads(raw_input)
        text = data.get("text", "").strip()
        voice_id = data.get("voice", "free-vi-ngoc-huyen")
        rate = float(data.get("rate", 1.0))
        pause_sec = float(data.get("pause", 0.40))
        if not text:
            sys.stderr.write("Error: Text is required\n")
            sys.exit(1)

        wav_bytes = dispatch_synthesize(text, voice_id, rate=rate, pause_sec=pause_sec)
        sys.stdout.buffer.write(wav_bytes)
        sys.stdout.buffer.flush()
    except Exception as e:
        sys.stderr.write(f"{str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
