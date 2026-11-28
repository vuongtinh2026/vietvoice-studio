#!/usr/bin/env python3
"""
VoiceViet Studio AI Engine v4.0
- Encrypted Private Voice Clone Vault (48kHz Studio Pro Owner-Protected Cloning)
- VieNeu-TTS v3 Turbo (48kHz Studio Human-Grade Vietnamese Voices + [cười], [thở dài], [hắng giọng])
- Piper ONNX + 48kHz Studio Condenser Mastering
- ElevenLabs-Style 32 Global Languages Library (65+ Male & Female Native Neural Voices @ 48kHz)
- True Ellipsis "..." / "…" Prosodic Pause Engine
"""
import asyncio
import base64
import concurrent.futures
import ctypes
import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Prevent OpenMP / ONNX Runtime active spin-wait contention across parallel workers
os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")


def _boost_macos_interactive_qos() -> None:
    """Ensure macOS Apple Silicon schedules TTS threads on Performance (P) cores instead of 600MHz Background E-cores."""
    if sys.platform != "darwin":
        return
    try:
        libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        # Clear PRIO_DARWIN_BG (PRIO_DARWIN_PROCESS = 4) if inherited from launchd / background parent
        libc.setpriority(4, 0, 0)
        # QOS_CLASS_USER_INITIATED = 0x19
        libc.pthread_set_qos_class_self_np(0x19, 0)
    except Exception:
        pass


_boost_macos_interactive_qos()

# 1. Eliminate 45s broken-IPv6 blackhole timeouts on HuggingFace / Microsoft Edge / Google TTS
_ORIG_GETADDRINFO = socket.getaddrinfo


def _ipv4_first_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family in (0, socket.AF_UNSPEC):
        try:
            return _ORIG_GETADDRINFO(host, port, socket.AF_INET, type, proto, flags)
        except OSError:
            pass
    return _ORIG_GETADDRINFO(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_first_getaddrinfo

# 2. Auto-enable offline local loading when BOTH VieNeu ONNX & Whisper weights are already cached on disk
_HF_VIENEU_CACHE = os.path.expanduser(
    "~/.cache/huggingface/hub/models--pnnbao-ump--VieNeu-TTS-v3-Turbo/snapshots"
)
_HF_WHISPER_CACHE = os.path.expanduser(
    "~/.cache/huggingface/hub/models--Systran--faster-whisper-base/snapshots"
)
if (
    os.path.isdir(_HF_VIENEU_CACHE)
    and os.listdir(_HF_VIENEU_CACHE)
    and os.path.isdir(_HF_WHISPER_CACHE)
    and os.listdir(_HF_WHISPER_CACHE)
):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np

from global_voices_catalog import GLOBAL_INTL_VOICES
import audio_speaker_analyzer
import cinema_translator
import media_dubber
from private_vault import PrivateVoiceVault
import vn_number_normalizer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OPEN_MODELS_DIR = os.path.join(BASE_DIR, "open_models")
PREVIEW_CACHE_DIR = os.path.join(OPEN_MODELS_DIR, "preview_cache")
os.makedirs(PREVIEW_CACHE_DIR, exist_ok=True)
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
VAULT = PrivateVoiceVault(ffmpeg_bin=FFMPEG_BIN)

FREE_VOICES = [
    # === NHÓM 1: TOP GIỌNG AI TIẾNG VIỆT STUDIO PRO 48KHZ ===
    {
        "id": "free-vi-ngoc-huyen",
        "name": "Ngọc Huyền (Studio 48kHz)",
        "gender": "Nữ",
        "language": "vi",
        "country": "🇻🇳 Tiếng Việt",
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
        "country": "🇻🇳 Tiếng Việt",
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
        "country": "🇻🇳 Tiếng Việt",
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
        "country": "🇻🇳 Tiếng Việt",
        "provider": "vieneu",
        "model": "Adam bựa",
        "featured": True,
        "useCase": "Nam hài hước, tự nhiên — TikTok / Reels / Shorts (hỗ trợ [cười])",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-hoaimy",
        "name": "Hoài My (Neural HD)",
        "gender": "Nữ",
        "language": "vi",
        "country": "🇻🇳 Tiếng Việt",
        "provider": "edge",
        "model": "vi-VN-HoaiMyNeural",
        "featured": True,
        "useCase": "Nữ ngọt ngào, trong trẻo — Tiểu thuyết, Ngôn tình, Đời sống",
        "badge": "NEURAL 48kHz",
    },
    {
        "id": "free-vi-namminh",
        "name": "Nam Minh (Studio 48kHz)",
        "gender": "Nam",
        "language": "vi",
        "country": "🇻🇳 Tiếng Việt",
        "provider": "vieneu",
        "model": "Xuân Vĩnh",
        "featured": True,
        "useCase": "Nam Bắc đĩnh đạc, chuẩn mực — Phóng sự, Ký sự, Thuyết minh",
        "badge": "STUDIO 48kHz",
    },
    {
        "id": "free-vi-google",
        "name": "Chị Google",
        "gender": "Nữ",
        "language": "vi",
        "country": "🇻🇳 Tiếng Việt",
        "provider": "google",
        "model": "vi",
        "featured": True,
        "useCase": "Giọng Chị Google huyền thoại — Meme TikTok, Tin nhanh hài hước",
        "badge": "CLASSIC AI",
    },
    # === NHÓM 2: KHO GIỌNG VIỆT STUDIO 48KHZ ĐA VÙNG MIỀN ===
    {"id": "free-vi-truc-ly", "name": "Trúc Ly (Podcast 48kHz)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Trúc Ly", "featured": False, "useCase": "Nữ Bắc trò chuyện gần gũi — Podcast, Chữa lành, Radio tâm sự", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-pham-tuyen", "name": "Phạm Tuyên (Kiếm hiệp 48kHz)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Phạm Tuyên", "featured": False, "useCase": "Nam Bắc hào sảng, nội lực — Kiếm hiệp, Tiên hiệp, Huyền huyễn", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-my-duyen", "name": "Mỹ Duyên (Ngôn tình 48kHz)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Mỹ Duyên", "featured": False, "useCase": "Nữ miền Nam dịu dàng — Ngôn tình, Truyện ngắn", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-hai-dang", "name": "Hải Đăng (Thời sự 48kHz)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Hải Đăng", "featured": False, "useCase": "Nam Bắc chuẩn phát thanh viên VTV — Bản tin, Thuyết trình", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-mai-anh", "name": "Mai Anh (Tin tức 48kHz)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Mai Anh", "featured": False, "useCase": "Nữ Bắc phát thanh viên sắc nét — Tin tức, Báo chí, Kinh tế", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-thien-minh", "name": "Thiện Minh (Kể chuyện 48kHz)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Thiện Minh", "featured": False, "useCase": "Nam Bắc kể chuyện ấm áp — Audiobook, Truyện đêm khuya", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-thai-son", "name": "Thái Sơn (Miền Nam 48kHz)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Thái Sơn", "featured": False, "useCase": "Nam miền Nam kể chuyện trầm ấm — Lịch sử, Ký sự", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-ngoc-linh", "name": "Ngọc Linh (Cổ trang 48kHz)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Ngọc Linh", "featured": False, "useCase": "Nữ Bắc thanh tao — Nữ hiệp, Cổ trang, Văn học", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-adam-nam", "name": "Adam Miền Nam (48kHz)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Adam", "featured": False, "useCase": "Nam miền Nam trẻ trung, tự nhiên — Vlog, Review", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-quang-son", "name": "Quang Sơn (Miền Trung 48kHz)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Quang Sơn", "featured": False, "useCase": "Nam miền Trung mộc mạc — Ký sự quê hương, Kể chuyện", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-ngoc-tran", "name": "Ngọc Trân (Miền Trung 48kHz)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Ngọc Trân", "featured": False, "useCase": "Nữ miền Trung ngọt ngào — Tản văn, Du lịch", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-thuy-dung", "name": "Thùy Dung (Miền Nam 48kHz)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Thùy Dung", "featured": False, "useCase": "Nữ miền Nam chuẩn tin tức — Bản tin, Tổng đài", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-duc-tri", "name": "Đức Trí (Đọc truyện 48kHz)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Đức Trí", "featured": False, "useCase": "Nam miền Nam đọc truyện truyền cảm — Tiểu thuyết", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-kim-thanh", "name": "Kim Thanh (Đọc truyện 48kHz)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Kim Thanh", "featured": False, "useCase": "Nữ miền Nam ấm áp — Truyện gia đình, Tâm lý", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-quoc-tuan", "name": "Quốc Tuấn (Thuyết minh 48kHz)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Quốc Tuấn", "featured": False, "useCase": "Nam Bắc trầm ổn, rõ chữ — Thuyết minh, Tài liệu, Sách kinh doanh", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-thanh-binh", "name": "Thanh Bình (Kể chuyện 48kHz)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Thanh Bình", "featured": False, "useCase": "Nam Bắc kể chuyện truyền cảm — Văn học, Tản văn", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-minh-triet", "name": "Minh Triết (Tin tức Nam 48kHz)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Minh Triết", "featured": False, "useCase": "Nam miền Nam tin tức hiện đại — Điểm tin, Kinh tế, Review", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-quynh-anh", "name": "Quỳnh Anh (Đọc truyện 48kHz)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Quỳnh Anh", "featured": False, "useCase": "Nữ Bắc dịu dàng — Đọc truyện, Ngôn tình, Sách nói", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-doan-trang", "name": "Đoan Trang (Tự nhiên 48kHz)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Đoan Trang", "featured": False, "useCase": "Nữ Bắc thanh lịch — Giới thiệu sản phẩm, Giáo dục", "badge": "STUDIO 48kHz"},
    {"id": "free-vi-thuc-doan", "name": "Thục Đoan (Miền Nam 48kHz)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "vieneu", "model": "Thục Đoan", "featured": False, "useCase": "Nữ miền Nam truyền cảm — Kể chuyện đêm khuya, Tâm sự", "badge": "STUDIO 48kHz"},
    # === NHÓM 3: GIỌNG VIỆT ĐẶC TRƯNG SIÊU TỐC OFFLINE (MASTERED 48KHZ) ===
    {"id": "free-vi-ngoc-ngan", "name": "Ngọc Ngạn (Truyện ma đêm khuya)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "ngocngan3701.onnx", "featured": False, "useCase": "Giọng đọc Truyện ma, Kể chuyện đêm khuya huyền thoại", "badge": "FAST OFFLINE"},
    {"id": "free-vi-tai-an", "name": "Tài An (CD Media Lịch sử)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "taian4.onnx", "featured": False, "useCase": "Phân tích Lịch sử, Địa chính trị, Kinh tế", "badge": "FAST OFFLINE"},
    {"id": "free-vi-manh-dung", "name": "Mạnh Dũng (Quảng cáo TVC)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "manhdung.onnx", "featured": False, "useCase": "Quảng cáo TVC hào sảng, Giới thiệu sản phẩm", "badge": "FAST OFFLINE"},
    {"id": "free-vi-ban-mai", "name": "Ban Mai (Chuẩn giọng Bắc)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "banmai.onnx", "featured": False, "useCase": "Giọng Nữ miền Bắc chuẩn mực đọc sách báo dài", "badge": "FAST OFFLINE"},
    {"id": "free-vi-duy-oryx", "name": "Duy Oryx (Nam Siêu Trầm)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "duyoryx3175.onnx", "featured": False, "useCase": "Giọng Nam siêu trầm điện ảnh, Trailer, Podcast", "badge": "FAST OFFLINE"},
    {"id": "free-vi-minh-khang", "name": "Minh Khang (Kiến Giải Mã)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "minhkhang.onnx", "featured": False, "useCase": "Thuyết minh Khoa học, Khám phá bí ẩn", "badge": "FAST OFFLINE"},

    # ==============================================================================
    # NHÓM 4: THƯ VIỆN ĐA NGÔN NGỮ TOÀN CẦU v5.0 (1.021 GIỌNG • 141 NGÔN NGỮ & VÙNG)
    # ==============================================================================
    *GLOBAL_INTL_VOICES,
]

VOICE_MAP = {v["id"]: v for v in FREE_VOICES}


def resolve_voice_entry(voice_id: str) -> dict:
    if voice_id in VOICE_MAP:
        return VOICE_MAP[voice_id]
    alt = voice_id.replace("-multilingual", "multilingual").replace("-expressive", "expressive")
    if alt in VOICE_MAP:
        return VOICE_MAP[alt]
    # Support legacy shorthand IDs e.g. free-intl-ja-nanami -> free-intl-ja-jp-nanami
    if voice_id.startswith("free-intl-"):
        parts = voice_id.split("-")
        if len(parts) == 4:
            suffix = f"-{parts[3]}"
            lang_prefix = f"free-intl-{parts[2]}-"
            for vid, entry in VOICE_MAP.items():
                if vid.startswith(lang_prefix) and vid.endswith(suffix):
                    return entry
    return VOICE_MAP["free-vi-ngoc-huyen"]

_PIPER_LOCK = threading.Lock()
_VIENEU_POOL_SIZE = 4
_VIENEU_TLS = threading.local()
_VIENEU_WARM_READY = False
_VIENEU_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=_VIENEU_POOL_SIZE)
_PIPER_CACHE: dict[str, object] = {}
_PREVIEW_RAM_CACHE: dict[str, tuple[bytes, str, float]] = {}


def _get_thread_local_vieneu():
    """Each ThreadPool worker owns 1 dedicated INT8 VieNeu instance — 100% lock-free & deadlock-free!"""
    global _VIENEU_WARM_READY
    tts = getattr(_VIENEU_TLS, "tts", None)
    if tts is None:
        _boost_macos_interactive_qos()
        from vieneu import Vieneu
        try:
            tts = Vieneu(mode="v3turbo", precision="int8", threads=2, babble_retries=0)
        except Exception:
            tts = Vieneu(mode="v3turbo", threads=2, babble_retries=0)
        _VIENEU_TLS.tts = tts
        _VIENEU_WARM_READY = True
    return tts


def _tls_infer_task(text_str: str, voice_or_preset) -> np.ndarray:
    tts = _get_thread_local_vieneu()
    return tts.infer(text_str, voice=voice_or_preset)


def _tls_enroll_task(audio_bytes: bytes, name: str, gender: str, desc: str, tok: str) -> dict:
    tts = _get_thread_local_vieneu()
    return VAULT.enroll_new_private_voice(
        vieneu_tts=tts,
        audio_bytes=audio_bytes,
        name=name,
        gender=gender,
        description=desc,
        pin_or_token=tok,
    )


def run_vieneu_infer(text_str: str, voice_or_preset) -> np.ndarray:
    return _VIENEU_EXECUTOR.submit(_tls_infer_task, text_str, voice_or_preset).result()


def download_file_atomic(url: str, dest_path: str, min_bytes: int = 500) -> None:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) >= min_bytes:
        return
    tmp_path = f"{dest_path}.part.{os.getpid()}.{threading.get_ident()}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VoiceVietStudio/4.0"})
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


def trim_and_smooth_float32(arr: np.ndarray, sr: int, thresh: float = 0.003) -> np.ndarray:
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
    t = text.replace("\r\n", "\n").strip()
    if not t:
        return []
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
                    if phrase[-1] not in ".?!。？！":
                        phrase += "."
                    blocks.append((phrase, max(0.55, base_pause * 1.95)))
                cur = ""
            else:
                cur += tok

        rem = cur.strip(" ,;:-")
        if rem:
            if len(rem) > 95:
                sents = re.split(r"(?<=[.?!。？！])(?:\s+|$)", rem)
                buf_s = ""
                for s in sents:
                    s = s.strip()
                    if not s:
                        continue
                    if len(buf_s) + len(s) + 1 <= 115:
                        buf_s = f"{buf_s} {s}".strip() if buf_s else s
                    else:
                        if buf_s:
                            blocks.append((buf_s, max(0.28, base_pause * 1.05)))
                        buf_s = s
                if buf_s:
                    blocks.append((buf_s, max(0.28, base_pause * 1.05)))
            else:
                if rem[-1] not in ".?!。？！":
                    rem += "."
                blocks.append((rem, max(0.28, base_pause * 1.05)))

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


def polish_bilingual_for_vieneu(text: str) -> str:
    """
    Normalizes Vietnamese numbers (>= 1.000, decimals, dates, percentages) into spoken Vietnamese
    words so VieNeu-TTS NEVER reads '3.000' or '800.000' as 'ba không không không',
    and maps media extensions to natural English pronunciation.
    """
    t = text
    # File formats that sea_g2p would otherwise read letter-by-letter in Vietnamese ("mờ phê ba", "vê kép a vê")
    t = re.sub(r"(?:(?<=[\s(\"'«“])|^)\.?mp3\b", "em pee three", t, flags=re.IGNORECASE)
    t = re.sub(r"(?:(?<=[\s(\"'«“])|^)\.?mp4\b", "em pee four", t, flags=re.IGNORECASE)
    t = re.sub(r"(?:(?<=[\s(\"'«“])|^)\.?wav\b", "wave", t, flags=re.IGNORECASE)
    t = re.sub(r"(?:(?<=[\s(\"'«“])|^)\.docx\b", "file Word", t, flags=re.IGNORECASE)
    t = re.sub(r"\bctrl\s*\+\s*enter\b", "Ctrl Enter", t, flags=re.IGNORECASE)
    t = vn_number_normalizer.normalize_vietnamese_numbers_for_tts(t)
    return t


def _infer_single_vieneu_phrase(clean_phrase: str, voice_or_preset) -> np.ndarray:
    audio_f32 = _tls_infer_task(clean_phrase, voice_or_preset)
    return trim_and_smooth_float32(audio_f32, TARGET_SR)


def synthesize_vieneu_48k(text: str, voice_or_preset, rate: float = 1.0, pause_sec: float = 0.40) -> bytes:
    text = polish_bilingual_for_vieneu(text)
    blocks = split_dramatic_blocks(text, base_pause=pause_sec)
    if not blocks:
        return encode_float32_to_wav_bytes(np.zeros(int(0.2 * TARGET_SR), dtype=np.float32), TARGET_SR)

    valid_items: list[tuple[str, float]] = []
    for phrase, after_pause in blocks:
        clean_phrase = re.sub(r"[“”\"«»]", "", phrase).strip()
        if clean_phrase:
            valid_items.append((clean_phrase, after_pause))

    if not valid_items:
        return encode_float32_to_wav_bytes(np.zeros(int(0.2 * TARGET_SR), dtype=np.float32), TARGET_SR)

    # Dispatch leaf tasks directly to the 4 thread-local INT8 workers (never nested!)
    futs = [
        _VIENEU_EXECUTOR.submit(_infer_single_vieneu_phrase, phr, voice_or_preset)
        for phr, _ in valid_items
    ]
    segs = [f.result() for f in futs]

    pieces: list[np.ndarray] = []
    for idx, seg in enumerate(segs):
        pieces.append(seg)
        after_pause = valid_items[idx][1]
        if idx < len(segs) - 1 and after_pause > 0:
            pieces.append(np.zeros(int(after_pause * TARGET_SR), dtype=np.float32))

    full = np.concatenate(pieces)
    peak = float(np.max(np.abs(full)))
    if peak > 0.01:
        full = full * (0.89 / peak)

    wav_bytes = encode_float32_to_wav_bytes(full, TARGET_SR)
    return apply_rate_ffmpeg(wav_bytes, rate)


def segment_piper_prosody(text: str, base_pause: float = 0.40) -> list[tuple[str, float]]:
    t = text.replace("\r\n", "\n")
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

    text = vn_number_normalizer.normalize_vietnamese_numbers_for_tts(text)
    voice = get_piper_voice(onnx_filename)
    safe_rate = max(0.5, min(2.0, rate))
    syn_conf = SynthesisConfig(length_scale=1.04 / safe_rate, noise_scale=0.60, noise_w_scale=0.45)

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


def split_for_google_tts(text: str, max_len: int = 175) -> list[str]:
    sentences = re.split(r"(?<=[.?!;\n。？！])\s*", text.strip())
    chunks: list[str] = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(sent) <= max_len:
            chunks.append(sent)
        else:
            words = sent.split()
            if len(words) <= 1:
                # CJK without spaces
                for i in range(0, len(sent), max_len):
                    chunks.append(sent[i : i + max_len])
            else:
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
    if (lang or "").lower().startswith("vi"):
        text = vn_number_normalizer.normalize_vietnamese_numbers_for_tts(text)
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


def map_locale_to_google_lang(lang_code: str) -> str:
    if lang_code.startswith("zh-CN"):
        return "zh-CN"
    if lang_code in ("zh-TW", "zh-HK"):
        return "zh-TW"
    g_lang = lang_code.split("-")[0]
    return {"fil": "tl", "he": "iw", "jv": "jw", "nb": "no", "iu": "en"}.get(g_lang, g_lang)


def fetch_google_mp3_fast(text: str, lang: str = "vi") -> bytes:
    q = urllib.parse.quote(text[:195])
    url = f"https://translate.googleapis.com/translate_tts?ie=UTF-8&q={q}&tl={lang}&client=tw-ob"
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            )
            with urllib.request.urlopen(req, timeout=4) as res:
                data = res.read()
                if len(data) > 100:
                    return data
        except Exception:
            if attempt == 1:
                raise
    raise RuntimeError("Google TTS empty response")


_ASYNC_LOOP = asyncio.new_event_loop()
threading.Thread(target=_ASYNC_LOOP.run_forever, daemon=True).start()


def run_async(coro, timeout: float | None = None):
    fut = asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)
    try:
        return fut.result(timeout=timeout)
    except Exception:
        fut.cancel()
        raise


_SHARED_EDGE_CONNECTOR = None


def _get_shared_edge_connector():
    global _SHARED_EDGE_CONNECTOR
    if _SHARED_EDGE_CONNECTOR is None or _SHARED_EDGE_CONNECTOR.closed:
        import aiohttp
        _SHARED_EDGE_CONNECTOR = aiohttp.TCPConnector(
            family=socket.AF_INET,
            limit=32,
            ttl_dns_cache=600,
            keepalive_timeout=60,
        )
    return _SHARED_EDGE_CONNECTOR


async def _single_edge_mp3_attempt(text: str, edge_voice: str, rate_str: str) -> bytes:
    import edge_tts

    conn = _get_shared_edge_connector()
    comm = edge_tts.Communicate(
        text,
        edge_voice,
        rate=rate_str,
        connect_timeout=6,
        receive_timeout=16,
        connector=conn,
    )
    buf = bytearray()
    async for ch in comm.stream():
        if ch["type"] == "audio":
            buf.extend(ch["data"])
    if len(buf) <= 100:
        raise RuntimeError("Empty Edge MP3 stream")
    return bytes(buf)


async def fetch_edge_mp3_hedged(text: str, edge_voice: str, rate: float = 1.0) -> bytes:
    """Hedged parallel WebSocket racing on persistent keep-alive connector: ~0.4s warm, ~2.2s cold!"""
    pct = int(round((max(0.5, min(2.0, rate)) - 1.0) * 100))
    rate_str = f"{pct:+d}%"
    active_tasks: set[asyncio.Task] = set()

    try:
        t1 = asyncio.create_task(_single_edge_mp3_attempt(text, edge_voice, rate_str))
        active_tasks.add(t1)
        done, _ = await asyncio.wait(active_tasks, timeout=1.40, return_when=asyncio.FIRST_COMPLETED)
        for d in done:
            active_tasks.discard(d)
            if not d.exception():
                return d.result()

        t2 = asyncio.create_task(_single_edge_mp3_attempt(text, edge_voice, rate_str))
        active_tasks.add(t2)
        while active_tasks:
            done, _ = await asyncio.wait(active_tasks, timeout=9.0, return_when=asyncio.FIRST_COMPLETED)
            if not done:
                break
            for d in done:
                active_tasks.discard(d)
                if not d.exception():
                    return d.result()
        raise RuntimeError("Edge hedged attempts timed out")
    finally:
        for rem in active_tasks:
            rem.cancel()


async def synthesize_edge_48k(
    text: str,
    edge_voice: str,
    lang_code: str = "vi",
    gender: str = "Nữ",
    rate: float = 1.0,
    pause_sec: float = 0.40,
) -> bytes:
    if (lang_code or "").lower().startswith("vi"):
        text = vn_number_normalizer.normalize_vietnamese_numbers_for_tts(text)
    blocks = split_dramatic_blocks(text, base_pause=pause_sec)
    valid = []
    for phrase, after_pause in blocks:
        clean_phrase = re.sub(r"\[(?:cười|thở dài|hắng giọng)\]", "", phrase).strip()
        if clean_phrase:
            valid.append((clean_phrase, after_pause))

    if not valid:
        return encode_float32_to_wav_bytes(np.zeros(int(0.2 * TARGET_SR), dtype=np.float32), TARGET_SR)

    sem = asyncio.Semaphore(8)

    async def _fetch_idx(i: int, phr: str) -> bytes:
        async with sem:
            return await fetch_edge_mp3_hedged(phr, edge_voice, rate=rate)

    try:
        mp3_list = await asyncio.gather(*[_fetch_idx(i, p) for i, (p, _) in enumerate(valid)])
    except Exception:
        if not lang_code.startswith("vi"):
            g_lang = map_locale_to_google_lang(lang_code)
            return synthesize_google_48k(text, lang=g_lang, rate=rate, pause_sec=pause_sec)
        # Authentic Studio 48kHz gender-matched fallback if Edge cloud is ever offline!
        fb_studio = "Quỳnh Anh" if gender == "Nữ" else "Xuân Vĩnh"
        return synthesize_vieneu_48k(text, fb_studio, rate=rate, pause_sec=pause_sec)

    pieces: list[np.ndarray] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, mp3_bytes in enumerate(mp3_list):
            raw_mp3 = os.path.join(tmpdir, f"edge_{idx}.mp3")
            with open(raw_mp3, "wb") as f:
                f.write(mp3_bytes)
            arr = mp3_to_float32_48k(raw_mp3, rate=1.0)
            pieces.append(trim_and_smooth_float32(arr, TARGET_SR))
            after_pause = valid[idx][1]
            if idx < len(mp3_list) - 1 and after_pause > 0:
                pieces.append(np.zeros(int(after_pause * TARGET_SR), dtype=np.float32))

    return encode_float32_to_wav_bytes(np.concatenate(pieces), TARGET_SR)


SHORT_VI_PREVIEWS = {
    "free-vi-ngoc-huyen": "Xin chào các bạn, chào mừng bạn đến với giọng đọc Ngọc Huyền chuẩn phòng thu!",
    "free-vi-thien-tam": "Xin kính chào quý vị đang lắng nghe chuyên mục sách nói đêm khuya cùng Thiện Tâm.",
    "free-vi-minh-quan": "Xin chào quý vị khán giả, đây là bản tin bình luận cùng giọng đọc Minh Quân.",
    "free-vi-adam-tiktok": "[cười] Xin chào anh em, hôm nay mình kể cho anh em nghe câu chuyện cực cuốn nhé!",
    "free-vi-hoaimy": "Xin chào các bạn, tôi là Hoài My, giọng đọc truyền cảm dành cho tiểu thuyết.",
    "free-vi-namminh": "Xin kính chào quý vị, tôi là Nam Minh, giọng đọc thuyết minh phóng sự.",
    "free-vi-google": "Xin chào các bạn, đây là giọng đọc Chị Google huyền thoại trên mạng xã hội.",
    "free-vi-truc-ly": "Chào bạn, cảm ơn bạn đã ghé thăm góc podcast tâm sự chữa lành cùng Trúc Ly.",
    "free-vi-pham-tuyen": "Giữa tầng mây mù vạn trượng, một luồng kiếm khí bất ngờ bùng nổ vang dội!",
    "free-vi-my-duyen": "Chào bạn, hôm nay Mỹ Duyên sẽ kể cho bạn nghe một câu chuyện ngôn tình dịu dàng.",
    "free-vi-hai-dang": "Kính chào quý vị và các bạn đang theo dõi bản tin thời sự tổng hợp cùng Hải Đăng.",
    "free-vi-mai-anh": "Xin chào quý vị, đây là bản tin kinh tế và công nghệ mới nhất cùng Mai Anh.",
}


def get_fast_preview_prompt(voice_id: str, info: dict | None = None) -> str:
    if voice_id in SHORT_VI_PREVIEWS:
        return SHORT_VI_PREVIEWS[voice_id]
    if voice_id.startswith("private-"):
        return "Chào mừng các bạn quay trở lại với kênh Truyện Dị Giới TV!"
    if info:
        sample = info.get("sampleText", "").strip()
        if sample:
            return sample
        short_name = info.get("name", voice_id).split("(")[0].strip()
        return f"Xin chào các bạn, đây là giọng đọc {short_name} chuẩn phòng thu!"
    return "Xin chào các bạn, đây là bản nghe thử giọng đọc trên VoiceViet Studio!"


def dispatch_preview(
    voice_id: str,
    custom_text: str = "",
    rate: float = 1.0,
    owner_token: str | None = None,
) -> tuple[bytes, str, float]:
    """Ultra-low-latency audition engine: <0.02s cached, 0.4s-1.8s cold!"""
    rate_clamped = round(max(0.5, min(2.0, rate)), 1)

    # 1. Private Cloned Voice: ALWAYS enforce cryptographic Owner Token FIRST!
    if voice_id.startswith("private-"):
        preset_dict = VAULT.get_authorized_voice_preset(voice_id, owner_token)
        prompt = (custom_text or get_fast_preview_prompt(voice_id)).strip()
        cache_key = f"priv:{voice_id}:{rate_clamped}:{hashlib.md5(prompt.encode('utf-8')).hexdigest()[:8]}"
        if cache_key in _PREVIEW_RAM_CACHE:
            return _PREVIEW_RAM_CACHE[cache_key]
        audio_f32 = run_vieneu_infer(prompt, preset_dict)
        seg = trim_and_smooth_float32(audio_f32, TARGET_SR)
        peak = float(np.max(np.abs(seg)))
        if peak > 0.01:
            seg = seg * (0.89 / peak)
        wav_bytes = apply_rate_ffmpeg(encode_float32_to_wav_bytes(seg, TARGET_SR), rate_clamped)
        dur = max(0.3, (len(wav_bytes) - 44) / (TARGET_SR * 2))
        res_tuple = (wav_bytes, "audio/wav", dur)
        _PREVIEW_RAM_CACHE[cache_key] = res_tuple
        return res_tuple

    # 2. Public Voices: Check RAM cache, then persistent disk cache!
    info = resolve_voice_entry(voice_id)
    resolved_id = info["id"]
    prompt = (custom_text or get_fast_preview_prompt(resolved_id, info)).strip()
    cache_hash = hashlib.md5(f"{resolved_id}|{rate_clamped}|{prompt}".encode("utf-8")).hexdigest()[:12]
    provider = info["provider"]
    ext = "mp3" if provider in ("edge", "google") and abs(rate_clamped - 1.0) <= 0.05 else ("mp3" if provider == "edge" else "wav")
    mime = "audio/mpeg" if ext == "mp3" else "audio/wav"

    if cache_hash in _PREVIEW_RAM_CACHE:
        return _PREVIEW_RAM_CACHE[cache_hash]

    disk_path = os.path.join(PREVIEW_CACHE_DIR, f"{resolved_id}_{cache_hash}.{ext}")
    if os.path.exists(disk_path) and os.path.getsize(disk_path) > 200:
        with open(disk_path, "rb") as f:
            cached_bytes = f.read()
        est_sec = max(0.5, len(cached_bytes) / 6000.0) if ext == "mp3" else max(0.5, (len(cached_bytes) - 44) / (TARGET_SR * 2))
        res_tuple = (cached_bytes, mime, est_sec)
        _PREVIEW_RAM_CACHE[cache_hash] = res_tuple
        return res_tuple

    # 3. Cold fast synthesis (lock-free for Edge, Google & INT8 VieNeu Pool!)
    model = info["model"]
    lang_code = info.get("language", "vi")
    used_fallback = False

    if provider == "edge":
        clean_p = re.sub(r"\[(?:cười|thở dài|hắng giọng)\]", "", prompt).replace("...", ",").strip()
        try:
            audio_bytes = run_async(fetch_edge_mp3_hedged(clean_p, model, rate=rate_clamped), timeout=9.5)
            mime = "audio/mpeg"
            ext = "mp3"
            est_sec = max(0.8, len(audio_bytes) / 6000.0)
        except Exception:
            used_fallback = True
            if lang_code.startswith("vi"):
                # Keep authentic gender if Vietnamese Edge ever fails; NEVER substitute female Google for Male!
                fb_model = "Xuân Vĩnh" if info.get("gender") == "Nam" else "Quỳnh Anh"
                audio_f32 = run_vieneu_infer(clean_p, fb_model)
                seg = trim_and_smooth_float32(audio_f32, TARGET_SR)
                audio_bytes = apply_rate_ffmpeg(encode_float32_to_wav_bytes(seg, TARGET_SR), rate_clamped)
                mime = "audio/wav"
                ext = "wav"
                est_sec = max(0.5, (len(audio_bytes) - 44) / (TARGET_SR * 2))
            else:
                g_lang = map_locale_to_google_lang(lang_code)
                audio_bytes = fetch_google_mp3_fast(clean_p, lang=g_lang)
                mime = "audio/mpeg"
                ext = "mp3"
                est_sec = max(0.8, len(audio_bytes) / 4200.0)
    elif provider == "google":
        if abs(rate_clamped - 1.0) <= 0.05:
            audio_bytes = fetch_google_mp3_fast(prompt, lang=model)
            mime = "audio/mpeg"
            ext = "mp3"
            est_sec = max(0.8, len(audio_bytes) / 4200.0)
        else:
            audio_bytes = synthesize_google_48k(prompt, lang=model, rate=rate_clamped, pause_sec=0.25)
            mime = "audio/wav"
            ext = "wav"
            est_sec = max(0.5, (len(audio_bytes) - 44) / (TARGET_SR * 2))
    elif provider == "piper":
        with _PIPER_LOCK:
            audio_bytes = synthesize_piper_mastered_48k(prompt, model, rate=rate_clamped, pause_sec=0.25)
        mime = "audio/wav"
        ext = "wav"
        est_sec = max(0.5, (len(audio_bytes) - 44) / (TARGET_SR * 2))
    else:
        single_p = polish_bilingual_for_vieneu(prompt.replace("...", ",").strip())
        audio_f32 = run_vieneu_infer(single_p, model)
        seg = trim_and_smooth_float32(audio_f32, TARGET_SR)
        peak = float(np.max(np.abs(seg)))
        if peak > 0.01:
            seg = seg * (0.89 / peak)
        audio_bytes = apply_rate_ffmpeg(encode_float32_to_wav_bytes(seg, TARGET_SR), rate_clamped)
        mime = "audio/wav"
        ext = "wav"
        est_sec = max(0.5, (len(audio_bytes) - 44) / (TARGET_SR * 2))

    # Save public preview to RAM & disk cache ONLY when genuine (never persist fallback audio!)
    res_tuple = (audio_bytes, mime, est_sec)
    if not used_fallback:
        disk_out = os.path.join(PREVIEW_CACHE_DIR, f"{resolved_id}_{cache_hash}.{ext}")
        try:
            with open(disk_out, "wb") as f:
                f.write(audio_bytes)
        except OSError:
            pass
        _PREVIEW_RAM_CACHE[cache_hash] = res_tuple
    return res_tuple


def dispatch_synthesize(
    text: str,
    voice_id: str,
    rate: float = 1.0,
    pause_sec: float = 0.40,
    owner_token: str | None = None,
) -> bytes:
    if voice_id.startswith("private-"):
        preset_dict = VAULT.get_authorized_voice_preset(voice_id, owner_token)
        return synthesize_vieneu_48k(text, preset_dict, rate=rate, pause_sec=pause_sec)

    info = resolve_voice_entry(voice_id)
    provider = info["provider"]
    model = info["model"]
    lang_code = info.get("language", "vi")

    if provider == "vieneu":
        return synthesize_vieneu_48k(text, model, rate=rate, pause_sec=pause_sec)
    elif provider == "piper":
        with _PIPER_LOCK:
            return synthesize_piper_mastered_48k(text, model, rate=rate, pause_sec=pause_sec)
    elif provider == "edge":
        # Lock-free async I/O on persistent background loop!
        return run_async(
            synthesize_edge_48k(
                text,
                model,
                lang_code=lang_code,
                gender=info.get("gender", "Nữ"),
                rate=rate,
                pause_sec=pause_sec,
            )
        )
    elif provider == "google":
        return synthesize_google_48k(text, lang=model, rate=rate, pause_sec=pause_sec)
    else:
        return synthesize_vieneu_48k(text, "Ngọc Huyền", rate=rate, pause_sec=pause_sec)


# =========================================================================
# MULTI-CAST 48kHz CINEMA VOICE DUBBING ENGINE
# Automatically casts distinct 48kHz voices for Nam trẻ / Nam 2 / Đàn ông /
# Ông lão / Nữ trẻ / Nữ 2 / Phụ nữ / Trẻ em / Đám đông (3-voice layered mix)!
# =========================================================================
ROLE_CAST_MAP_VI: dict[str, tuple[str, float]] = {
    "NAM_TRE": ("free-vi-hai-dang", 0.0),      # Hải Đăng — Nam trẻ sáng rõ
    "NAM_2": ("free-vi-minh-quan", 0.0),       # Minh Quân — Nam thứ hai dõng dạc
    "DAN_ONG": ("free-vi-pham-tuyen", -0.45),  # Phạm Tuyên — Đàn ông trưởng thành uy lực
    "ONG_LAO": ("free-vi-thien-tam", -1.35),   # Thiện Tâm — Ông lão / Đại trưởng lão ấm trầm
    "NU_TRE": ("free-vi-ngoc-huyen", 0.0),     # Ngọc Huyền — Nữ trẻ truyền cảm
    "NU_2": ("free-vi-quynh-anh", 0.0),        # Quỳnh Anh — Nữ thứ hai dịu dàng
    "PHU_NU": ("free-vi-mai-anh", -0.50),      # Mai Anh — Phụ nữ / Đàn bà chín chắn
    "TRE_EM": ("free-vi-my-duyen", 2.45),      # Mỹ Duyên — Trẻ em / Bé trai / Bé gái trong trẻo
}


def _apply_pitch_character_48k(samples: np.ndarray, semitones: float) -> np.ndarray:
    """Subtle formant/pitch vocal character shaping for Elder (-1.35st) / Child (+2.45st) roles."""
    if samples.size < 480 or abs(semitones) < 0.15:
        return samples
    pitch_factor = float(2.0 ** (semitones / 12.0))
    tempo_comp = max(0.55, min(1.85, 1.0 / pitch_factor))
    sr_shifted = int(round(TARGET_SR * pitch_factor))
    in_wav = media_dubber._f32_48k_to_wav_bytes(samples, sr=TARGET_SR)
    try:
        proc = subprocess.run(
            [
                FFMPEG_BIN, "-nostdin", "-f", "wav", "-i", "pipe:0",
                "-af", f"asetrate={sr_shifted},aresample={TARGET_SR},atempo={tempo_comp:.4f}",
                "-ac", "1", "-ar", str(TARGET_SR), "-f", "s16le", "pipe:1",
            ],
            input=in_wav,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=25,
        )
        if proc.returncode == 0 and proc.stdout:
            return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception:
        pass
    return samples


def _pick_intl_role_voice(default_voice_id: str, role_code: str) -> str:
    if default_voice_id.startswith("private-"):
        return default_voice_id
    base_info = resolve_voice_entry(default_voice_id)
    lang = base_info.get("language", "vi")
    if lang.startswith("vi"):
        return default_voice_id
    want_gender = "Nam" if role_code in ("NAM_TRE", "NAM_2", "DAN_ONG", "ONG_LAO") else "Nữ"
    if base_info.get("gender") == want_gender:
        return default_voice_id
    for v in FREE_VOICES:
        if v.get("language") == lang and v.get("gender") == want_gender:
            return v["id"]
    return default_voice_id


def synthesize_role_segment_48k(
    text: str,
    role_tag: str,
    default_voice_id: str,
    multi_voice_cast: bool = True,
    rate: float = 1.0,
    pause_sec: float = 0.22,
    owner_token: str | None = None,
) -> tuple[np.ndarray, str]:
    """
    Synthesizes one dialogue cue using its casted multi-voice actor (or 3-voice staggered
    crowd mix for `DAM_DONG`), returning `(float32_48k_samples, used_role_code)`.
    """
    role_code = audio_speaker_analyzer.canonicalize_role_tag(role_tag or "")
    if not multi_voice_cast or not role_code or role_code == "DAN_CHUYEN":
        wb = dispatch_synthesize(text, default_voice_id, rate=rate, pause_sec=pause_sec, owner_token=owner_token)
        return media_dubber.wav_bytes_to_f32_48k(wb, ffmpeg_bin=FFMPEG_BIN), (role_code or "DAN_CHUYEN")

    is_vi_voice = True
    if not default_voice_id.startswith("private-"):
        is_vi_voice = resolve_voice_entry(default_voice_id).get("language", "vi").startswith("vi")

    # 3-Voice Layered Cinema Crowd Mix for [ĐÁM ĐÔNG]
    if role_code == "DAM_DONG" and is_vi_voice:
        crowd_specs = [
            ("free-vi-minh-quan", rate, 0.0, 0.62),
            ("free-vi-ngoc-huyen", min(1.85, rate * 1.05), 0.055, 0.50),
            ("free-vi-pham-tuyen", max(0.65, rate * 0.96), 0.115, 0.48),
        ]
        layers: list[tuple[int, float, np.ndarray]] = []
        max_len = 0
        for vid, r_v, delay_s, gain in crowd_specs:
            wb_c = dispatch_synthesize(text, vid, rate=r_v, pause_sec=min(pause_sec, 0.16), owner_token=owner_token)
            arr_c = media_dubber.trim_tts_silence_48k(
                media_dubber.wav_bytes_to_f32_48k(wb_c, ffmpeg_bin=FFMPEG_BIN), sr=TARGET_SR, pad_ms=35
            )
            off = int(round(delay_s * TARGET_SR))
            layers.append((off, gain, arr_c))
            max_len = max(max_len, off + arr_c.size)
        if max_len > 0:
            mix = np.zeros(max_len, dtype=np.float32)
            for off, gain, arr_c in layers:
                if arr_c.size > 0:
                    mix[off : off + arr_c.size] += arr_c * gain
            pk = float(np.max(np.abs(mix))) if mix.size else 0.0
            if pk > 0.02:
                mix = mix * (0.90 / pk)
            return np.clip(mix, -0.96, 0.96), "DAM_DONG"

    if is_vi_voice and role_code in ROLE_CAST_MAP_VI:
        cast_vid, pitch_st = ROLE_CAST_MAP_VI[role_code]
        wb = dispatch_synthesize(text, cast_vid, rate=rate, pause_sec=pause_sec, owner_token=owner_token)
        arr = media_dubber.wav_bytes_to_f32_48k(wb, ffmpeg_bin=FFMPEG_BIN)
        if abs(pitch_st) >= 0.15:
            arr = _apply_pitch_character_48k(arr, pitch_st)
        return arr, role_code

    # International language gender-matched casting
    intl_vid = _pick_intl_role_voice(default_voice_id, role_code)
    wb = dispatch_synthesize(text, intl_vid, rate=rate, pause_sec=pause_sec, owner_token=owner_token)
    arr = media_dubber.wav_bytes_to_f32_48k(wb, ffmpeg_bin=FFMPEG_BIN)
    if role_code == "TRE_EM":
        arr = _apply_pitch_character_48k(arr, 2.3)
    elif role_code == "ONG_LAO":
        arr = _apply_pitch_character_48k(arr, -1.3)
    return arr, role_code


def get_public_voices() -> list[dict]:
    private_items = VAULT.list_private_voices_public()
    public_items = [
        {
            "id": v["id"],
            "name": v["name"],
            "gender": v["gender"],
            "language": v["language"],
            "country": v.get("country", v["language"].upper()),
            "region": v.get("region", "vi"),
            "provider": v["provider"],
            "featured": v["featured"],
            "isPrivate": False,
            "useCase": v["useCase"],
            "badge": re.sub(r"^FREE\s+", "", str(v.get("badge", "48kHz")), flags=re.IGNORECASE).strip() or "48kHz",
            "sampleText": v.get("sampleText", ""),
        }
        for v in FREE_VOICES
    ]
    return private_items + public_items


class EngineDaemonHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, status: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        return json.loads(raw or "{}")

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"ok": True, "warm": _VIENEU_WARM_READY})
        elif self.path == "/dub/progress":
            self._send_json(200, {"success": True, **media_dubber.get_dub_live_progress()})
        elif self.path == "/voices":
            self._send_json(200, {"success": True, "voices": get_public_voices()})
        elif self.path == "/private/status":
            tok = self.headers.get("X-Owner-Token", "")
            self._send_json(
                200,
                {
                    "success": True,
                    "unlocked": VAULT.is_valid_token(tok),
                    "voices": VAULT.list_private_voices_public(),
                },
            )
        else:
            self._send_json(404, {"success": False, "error": "Not found"})

    def do_POST(self):
        try:
            if self.path == "/private/unlock":
                data = self._read_json()
                token = VAULT.unlock(str(data.get("pin", "")))
                self._send_json(200, {"success": True, "token": token, "voices": VAULT.list_private_voices_public()})
                return

            if self.path == "/private/lock":
                VAULT.lock()
                for k in [k for k in _PREVIEW_RAM_CACHE if k.startswith("priv:")]:
                    _PREVIEW_RAM_CACHE.pop(k, None)
                self._send_json(200, {"success": True})
                return

            if self.path == "/private/change-pin":
                data = self._read_json()
                new_tok = VAULT.change_pin(str(data.get("currentPin", "")), str(data.get("newPin", "")))
                self._send_json(200, {"success": True, "token": new_tok})
                return

            if self.path == "/private/enroll":
                data = self._read_json()
                tok = self.headers.get("X-Owner-Token") or str(data.get("pin", ""))
                audio_b64 = data.get("audioBase64", "")
                if not audio_b64:
                    raise ValueError("Vui lòng chọn file âm thanh giọng mẫu!")
                audio_bytes = base64.b64decode(audio_b64)
                name = str(data.get("name", "Giọng Cá Nhân Mới")).strip() or "Giọng Cá Nhân Mới"
                gender = str(data.get("gender", "Nam"))
                desc = str(data.get("description", "Giọng nhân bản cá nhân độc quyền (48kHz Studio)"))
                created = _VIENEU_EXECUTOR.submit(
                    _tls_enroll_task, audio_bytes, name, gender, desc, tok
                ).result()
                self._send_json(200, {"success": True, "voice": created, "voices": VAULT.list_private_voices_public()})
                return

            if self.path == "/private/delete":
                data = self._read_json()
                tok = self.headers.get("X-Owner-Token") or str(data.get("pin", ""))
                vid = str(data.get("voiceId", ""))
                VAULT.delete_private_voice(vid, tok)
                for k in [k for k in _PREVIEW_RAM_CACHE if k.startswith(f"priv:{vid}:")]:
                    _PREVIEW_RAM_CACHE.pop(k, None)
                self._send_json(200, {"success": True, "voices": VAULT.list_private_voices_public()})
                return

            if self.path == "/preview":
                data = self._read_json()
                voice_id = data.get("voice", "free-vi-ngoc-huyen")
                custom_text = data.get("text", "").strip()
                rate = float(data.get("rate", 1.0))
                owner_token = self.headers.get("X-Owner-Token") or data.get("ownerToken")

                audio_bytes, mime, est_sec = dispatch_preview(
                    voice_id=voice_id,
                    custom_text=custom_text,
                    rate=rate,
                    owner_token=owner_token,
                )
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(audio_bytes)))
                self.send_header("X-Audio-Seconds", f"{est_sec:.1f}")
                self.end_headers()
                self.wfile.write(audio_bytes)
                return

            if self.path == "/dub/cancel":
                new_gen = cinema_translator.cancel_active_translations()
                media_dubber.set_dub_live_progress("", "", 0, active=False)
                self._send_json(200, {"success": True, "cancelled": True, "gen": new_gen})
                return

            if self.path == "/dub/youtube-transcribe-translate":
                data = self._read_json()
                cinema_translator.cancel_active_translations()
                media_dubber.set_dub_live_progress(
                    "🎬 Đang khởi tạo tải link video & nhận diện lời thoại...",
                    "🎬 Starting online video download & transcription...",
                    16,
                    active=True,
                )
                yt_url = str(data.get("url", "")).strip()
                dl_mode = str(data.get("downloadMode", "video")).strip() or "video"
                out_dir = str(data.get("outDir", "/tmp/voxly_dub_sessions")).strip() or "/tmp/voxly_dub_sessions"
                source_lang = str(data.get("sourceLang", "auto")).strip() or "auto"
                target_lang = str(data.get("targetLang", "vi")).strip() or "vi"
                ai_provider = str(data.get("aiProvider", "local")).strip() or "local"
                ai_api_key = str(data.get("aiApiKey", "")).strip()
                ai_model = str(data.get("aiModel", "")).strip()
                multi_voice_cast = False

                try:
                    dl_info = media_dubber.download_online_video_url(
                        raw_url=yt_url,
                        out_dir=out_dir,
                        download_mode=dl_mode,
                        ffmpeg_bin=FFMPEG_BIN,
                    )
                    tr_info = media_dubber.transcribe_and_translate_media(
                        media_path=dl_info["mediaPath"],
                        source_lang=source_lang,
                        target_lang=target_lang,
                        ffmpeg_bin=FFMPEG_BIN,
                        ai_provider=ai_provider,
                        ai_api_key=ai_api_key,
                        ai_model=ai_model,
                        multi_voice_cast=multi_voice_cast,
                    )
                finally:
                    media_dubber.set_dub_live_progress("", "", 0, active=False)
                merged = {
                    **tr_info,
                    "mediaPath": dl_info["mediaPath"],
                    "title": dl_info.get("title", "YouTube Video"),
                    "uploader": dl_info.get("uploader", ""),
                    "thumbnail": dl_info.get("thumbnail", ""),
                    "isVideo": bool(dl_info.get("isVideo") and tr_info.get("isVideo")),
                }
                self._send_json(200, merged)
                return

            if self.path == "/dub/transcribe-translate":
                data = self._read_json()
                cinema_translator.cancel_active_translations()
                media_dubber.set_dub_live_progress(
                    "🎙️ Đang chuẩn bị nhận diện lời thoại & biên dịch thuyết minh...",
                    "🎙️ Preparing transcription & narration translation...",
                    16,
                    active=True,
                )
                media_path = str(data.get("mediaPath", "")).strip()
                if not media_path or not os.path.exists(media_path):
                    media_dubber.set_dub_live_progress("", "", 0, active=False)
                    raise ValueError("Không tìm thấy file âm thanh/video cần dịch.")
                source_lang = str(data.get("sourceLang", "auto")).strip() or "auto"
                target_lang = str(data.get("targetLang", "vi")).strip() or "vi"
                ai_provider = str(data.get("aiProvider", "local")).strip() or "local"
                ai_api_key = str(data.get("aiApiKey", "")).strip()
                ai_model = str(data.get("aiModel", "")).strip()
                multi_voice_cast = False
                try:
                    res_obj = media_dubber.transcribe_and_translate_media(
                        media_path=media_path,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        ffmpeg_bin=FFMPEG_BIN,
                        ai_provider=ai_provider,
                        ai_api_key=ai_api_key,
                        ai_model=ai_model,
                        multi_voice_cast=multi_voice_cast,
                    )
                finally:
                    media_dubber.set_dub_live_progress("", "", 0, active=False)
                self._send_json(200, res_obj)
                return

            if self.path == "/dub/translate-text":
                data = self._read_json()
                cinema_translator.cancel_active_translations()
                raw_text = str(data.get("text", "")).strip()
                source_lang = str(data.get("sourceLang", "auto")).strip() or "auto"
                target_lang = str(data.get("targetLang", "vi")).strip() or "vi"
                ai_provider = str(data.get("aiProvider", "local")).strip() or "local"
                ai_api_key = str(data.get("aiApiKey", "")).strip()
                ai_model = str(data.get("aiModel", "")).strip()
                multi_voice_cast = False
                translated, detected = media_dubber.translate_script_preserving_timestamps(
                    raw_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    ai_provider=ai_provider,
                    ai_api_key=ai_api_key,
                    ai_model=ai_model,
                    include_role=multi_voice_cast,
                )
                self._send_json(200, {"success": True, "translatedText": translated, "detectedLang": detected})
                return

            if self.path == "/dub/render-synced":
                data = self._read_json()
                raw_text = str(data.get("text", "")).strip()
                in_segments = data.get("segments") or []
                voice_id = str(data.get("voice", "free-vi-ngoc-huyen")).strip() or "free-vi-ngoc-huyen"
                rate = float(data.get("rate", 1.0))
                pause_sec = float(data.get("pause", 0.25))
                multi_voice_cast = False
                owner_token = self.headers.get("X-Owner-Token") or data.get("ownerToken")
                orig_media = str(data.get("origMediaPath", "")).strip()
                is_video = bool(data.get("isVideo", False))
                duration_sec = float(data.get("durationSec", 0.0) or 0.0)
                sync_timeline = bool(data.get("syncTimeline", True))
                auto_fit = bool(data.get("autoFitTiming", True))
                orig_volume = float(data.get("origVolume", 0.40))
                smart_ducking = bool(data.get("smartDucking", True))
                out_dir = str(data.get("outDir", "/tmp/voxly_dub_sessions")).strip() or "/tmp/voxly_dub_sessions"
                out_id = str(data.get("outId", f"out_{int(time.time() * 1000)}")).strip()
                os.makedirs(out_dir, exist_ok=True)

                parsed_segs = []
                if sync_timeline and isinstance(in_segments, list) and len(in_segments) > 0:
                    for s in in_segments:
                        t_clean = str(s.get("text", "")).strip()
                        if t_clean:
                            parsed_segs.append(
                                {
                                    "start": float(s.get("start", 0.0)),
                                    "end": float(s.get("end", 0.0)),
                                    "text": t_clean,
                                    "role": str(s.get("role", "") or s.get("acousticRole", "")).strip(),
                                }
                            )
                elif sync_timeline and raw_text:
                    ts_segs, _, has_ts = media_dubber.parse_timestamped_script(raw_text)
                    if has_ts and ts_segs:
                        parsed_segs = ts_segs

                pure_voice_wav = os.path.join(out_dir, f"{out_id}_pure_voice.wav")
                out_wav = os.path.join(out_dir, f"{out_id}.wav")
                out_mp3 = os.path.join(out_dir, f"{out_id}.mp3")
                out_mp4 = os.path.join(out_dir, f"{out_id}_dubbed.mp4") if is_video else ""

                used_roles_set: set[str] = set()
                if parsed_segs:
                    total_s = len(parsed_segs)
                    done_counter = [0]
                    cnt_lock = threading.Lock()
                    media_dubber.set_dub_live_progress(
                        f"🎙️ Đang thu giọng thuyết minh 48kHz câu 1/{total_s}...",
                        f"🎙️ Synthesizing 48kHz voice-over narration cue 1/{total_s}...",
                        68,
                    )

                    def _synth_one_seg(seg_obj: dict) -> dict:
                        wb = dispatch_synthesize(
                            seg_obj["text"],
                            voice_id,
                            rate=rate,
                            pause_sec=min(pause_sec, 0.22),
                            owner_token=owner_token,
                        )
                        arr = media_dubber.wav_bytes_to_f32_48k(wb, ffmpeg_bin=FFMPEG_BIN)
                        with cnt_lock:
                            done_counter[0] += 1
                            dn = done_counter[0]
                            pct = 68 + int((dn / max(1, total_s)) * 24)
                            media_dubber.set_dub_live_progress(
                                f"🎙️ Đang thu giọng thuyết minh 48kHz câu {dn}/{total_s}...",
                                f"🎙️ Synthesizing 48kHz voice-over narration cue {dn}/{total_s}...",
                                pct,
                            )
                        return {"start": seg_obj["start"], "end": seg_obj["end"], "samples": arr}

                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(parsed_segs))) as coord_pool:
                        rendered_segs = list(coord_pool.map(_synth_one_seg, parsed_segs))

                    media_dubber.set_dub_live_progress(
                        "🎞️ Đang căn mốc thời gian, trộn âm gốc & đóng gói Video .MP4 thuyết minh...",
                        "🎞️ Aligning timeline, mixing original audio & muxing narrated .MP4...",
                        95,
                    )

                    speech_intervals = media_dubber.assemble_synced_voice_to_wav(
                        out_wav_path=pure_voice_wav,
                        rendered_segments=rendered_segs,
                        target_duration_sec=duration_sec,
                        auto_fit_timing=auto_fit,
                        ffmpeg_bin=FFMPEG_BIN,
                    )
                else:
                    _, plain_txt, _ = media_dubber.parse_timestamped_script(raw_text)
                    speak_txt = plain_txt or raw_text
                    if not speak_txt:
                        raise ValueError("Vui lòng nhập nội dung bản dịch để lồng tiếng.")
                    wb = dispatch_synthesize(speak_txt, voice_id, rate=rate, pause_sec=pause_sec, owner_token=owner_token)
                    arr = media_dubber.wav_bytes_to_f32_48k(wb, ffmpeg_bin=FFMPEG_BIN)
                    media_dubber._write_pcm_wav_48k(pure_voice_wav, arr, sr=TARGET_SR)
                    speech_intervals = [[0.0, round(arr.size / TARGET_SR, 3)]] if arr.size > 0 else []

                mix_res = media_dubber.mix_and_export_dubbed_outputs(
                    pure_voice_wav_path=pure_voice_wav,
                    speech_intervals=speech_intervals,
                    out_wav_path=out_wav,
                    out_mp3_path=out_mp3,
                    orig_media_path=orig_media,
                    out_mp4_path=out_mp4,
                    is_video=is_video,
                    orig_volume=orig_volume,
                    smart_ducking=smart_ducking,
                    ffmpeg_bin=FFMPEG_BIN,
                )

                v_info = (
                    {"name": "Giọng Nhân Bản Độc Quyền"}
                    if voice_id.startswith("private-")
                    else resolve_voice_entry(voice_id)
                )
                cast_roles_disp = sorted(
                    audio_speaker_analyzer.role_to_display_label(rc)
                    for rc in used_roles_set
                    if rc and rc != "DAN_CHUYEN"
                )
                voice_summary = (
                    f"🎭 Đa giọng ({len(cast_roles_disp)} vai: {', '.join(cast_roles_disp[:5])})"
                    if (multi_voice_cast and len(cast_roles_disp) >= 2)
                    else v_info.get("name", voice_id)
                )
                media_dubber.set_dub_live_progress("", "", 0, active=False)
                self._send_json(
                    200,
                    {
                        "success": True,
                        "pureVoiceWavPath": pure_voice_wav,
                        "speechIntervals": speech_intervals,
                        "outWavFile": os.path.basename(out_wav),
                        "outMp3File": os.path.basename(out_mp3),
                        "outMp4File": os.path.basename(out_mp4) if mix_res.get("dubbedVideoReady") else "",
                        "audioSeconds": mix_res.get("audioSeconds", 0.0),
                        "voiceName": voice_summary,
                        "castRoles": cast_roles_disp,
                        "syncedSegmentsCount": len(parsed_segs),
                    },
                )
                return

            if self.path == "/dub/remix-volume":
                data = self._read_json()
                pure_voice_wav = str(data.get("pureVoiceWavPath", "")).strip()
                if not pure_voice_wav or not os.path.exists(pure_voice_wav):
                    raise ValueError("Không tìm thấy bản giọng lồng tiếng gốc để trộn lại âm lượng!")
                speech_intervals = data.get("speechIntervals") or []
                orig_media = str(data.get("origMediaPath", "")).strip()
                is_video = bool(data.get("isVideo", False))
                orig_volume = float(data.get("origVolume", 0.40))
                smart_ducking = bool(data.get("smartDucking", True))
                out_dir = str(data.get("outDir", "/tmp/voxly_dub_sessions")).strip() or "/tmp/voxly_dub_sessions"
                out_id = str(data.get("outId", f"remix_{int(time.time() * 1000)}")).strip()
                os.makedirs(out_dir, exist_ok=True)

                out_wav = os.path.join(out_dir, f"{out_id}.wav")
                out_mp3 = os.path.join(out_dir, f"{out_id}.mp3")
                out_mp4 = os.path.join(out_dir, f"{out_id}_dubbed.mp4") if is_video else ""

                mix_res = media_dubber.mix_and_export_dubbed_outputs(
                    pure_voice_wav_path=pure_voice_wav,
                    speech_intervals=speech_intervals,
                    out_wav_path=out_wav,
                    out_mp3_path=out_mp3,
                    orig_media_path=orig_media,
                    out_mp4_path=out_mp4,
                    is_video=is_video,
                    orig_volume=orig_volume,
                    smart_ducking=smart_ducking,
                    ffmpeg_bin=FFMPEG_BIN,
                )
                self._send_json(
                    200,
                    {
                        "success": True,
                        "outWavFile": os.path.basename(out_wav),
                        "outMp3File": os.path.basename(out_mp3),
                        "outMp4File": os.path.basename(out_mp4) if mix_res.get("dubbedVideoReady") else "",
                        "audioSeconds": mix_res.get("audioSeconds", 0.0),
                    },
                )
                return

            if self.path == "/dub/mux-video":
                data = self._read_json()
                orig_video = str(data.get("origVideoPath", "")).strip()
                dub_wav = str(data.get("dubWavPath", "")).strip()
                out_mp4 = str(data.get("outMp4Path", "")).strip()
                bg_mix = str(data.get("bgMixMode", "mute")).strip() or "mute"
                auto_fit = bool(data.get("autoFitTiming", True))
                res_mux = media_dubber.mux_dubbed_audio_into_video(
                    orig_video_path=orig_video,
                    dub_wav_path=dub_wav,
                    out_mp4_path=out_mp4,
                    bg_mix_mode=bg_mix,
                    auto_fit_timing=auto_fit,
                    ffmpeg_bin=FFMPEG_BIN,
                )
                self._send_json(200, res_mux)
                return

            if self.path != "/synthesize":
                self._send_json(404, {"success": False, "error": "Not found"})
                return

            data = self._read_json()
            text = data.get("text", "").strip()
            voice_id = data.get("voice", "free-vi-ngoc-huyen")
            rate = float(data.get("rate", 1.0))
            pause_sec = float(data.get("pause", 0.40))
            owner_token = self.headers.get("X-Owner-Token") or data.get("ownerToken")

            if not text:
                raise ValueError("Vui lòng nhập văn bản.")

            wav_bytes = dispatch_synthesize(text, voice_id, rate=rate, pause_sec=pause_sec, owner_token=owner_token)
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav_bytes)))
            self.end_headers()
            self.wfile.write(wav_bytes)
        except cinema_translator.TranslationCancelledError as ce:
            self._send_json(499, {"success": False, "cancelled": True, "error": str(ce)})
        except PermissionError as pe:
            self._send_json(403, {"success": False, "code": "private_locked", "error": str(pe)})
        except BrokenPipeError:
            pass
        except Exception as e:
            self._send_json(500, {"success": False, "error": str(e)})


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_daemon(port: int = 3099) -> None:
    orig_ppid = os.getppid()

    if orig_ppid > 1:
        def _parent_watchdog():
            while True:
                time.sleep(2.0)
                if os.getppid() != orig_ppid:
                    os._exit(0)

        threading.Thread(target=_parent_watchdog, daemon=True).start()

    def _warmup():
        try:
            # Lock-free, non-blocking INT8 worker warmup (zero cross-thread barriers or queues!)
            futs = [_VIENEU_EXECUTOR.submit(_tls_infer_task, "Chào.", "Ngọc Huyền") for _ in range(_VIENEU_POOL_SIZE)]
            for f in futs:
                f.result()
            sys.stderr.write(
                f"[VoiceViet Daemon v8.1] {_VIENEU_POOL_SIZE}x Parallel INT8 VieNeu 48kHz Workers + 142 Global Languages ready on port {port}!\n"
            )

            # Pre-cache popular Vietnamese & Flagship International previews on disk so clicks play in 0.01s!
            prewarm_ids = [
                "free-vi-ngoc-huyen", "free-vi-thien-tam", "free-vi-minh-quan",
                "free-vi-adam-tiktok", "free-vi-hoaimy", "free-vi-namminh",
                "free-vi-google", "free-vi-truc-ly", "free-vi-pham-tuyen",
                "free-vi-my-duyen", "free-vi-hai-dang", "free-vi-mai-anh",
                "free-vi-thien-minh", "free-vi-thai-son", "free-vi-ngoc-linh",
                "free-vi-adam-nam", "free-vi-quang-son", "free-vi-ngoc-tran",
                "free-vi-thuy-dung", "free-vi-duc-tri", "free-vi-kim-thanh",
                "free-intl-en-us-avamultilingual", "free-intl-en-us-andrewmultilingual",
                "free-intl-en-us-brianmultilingual", "free-intl-en-gb-ryan",
                "free-intl-zh-cn-yunjian", "free-intl-zh-cn-xiaoxiao",
                "free-intl-ja-jp-nanami", "free-intl-ja-jp-keita",
                "free-intl-ko-kr-sunhi", "free-intl-ko-kr-hyunsumultilingual",
                "free-intl-fr-fr-viviennemultilingual", "free-intl-de-de-tanja",
                "free-intl-es-es-ximena", "free-intl-ru-ru-dmitry",
                "free-intl-th-th-premwadee", "free-intl-id-id-gadis",
                "free-intl-hi-in-swara", "free-intl-km-kh-sreymom",
            ]
            for pid in prewarm_ids:
                try:
                    dispatch_preview(pid, custom_text="", rate=1.0)
                except Exception:
                    pass
            sys.stderr.write("[VoiceViet Daemon v8.1] Pre-cached instant 0.01s voice previews ready!\n")
        except Exception as e:
            sys.stderr.write(f"[VoiceViet Daemon] Warmup note: {e}\n")

    threading.Thread(target=_warmup, daemon=True).start()
    server = ReusableThreadingHTTPServer(("127.0.0.1", port), EngineDaemonHandler)
    sys.stderr.write(f"[VoiceViet Daemon v8.1] Listening at http://127.0.0.1:{port}\n")
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
        owner_token = data.get("ownerToken")
        if not text:
            sys.stderr.write("Error: Text is required\n")
            sys.exit(1)

        wav_bytes = dispatch_synthesize(text, voice_id, rate=rate, pause_sec=pause_sec, owner_token=owner_token)
        sys.stdout.buffer.write(wav_bytes)
        sys.stdout.buffer.flush()
    except Exception as e:
        sys.stderr.write(f"{str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
