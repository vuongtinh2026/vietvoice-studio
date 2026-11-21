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

from private_vault import PrivateVoiceVault

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
        "name": "Hoài My (Neural)",
        "gender": "Nữ",
        "language": "vi",
        "country": "🇻🇳 Tiếng Việt",
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
        "country": "🇻🇳 Tiếng Việt",
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
        "country": "🇻🇳 Tiếng Việt",
        "provider": "google",
        "model": "vi",
        "featured": True,
        "useCase": "Giọng Chị Google huyền thoại — Meme TikTok, Tin nhanh hài hước",
        "badge": "FREE GOOGLE",
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
    # === NHÓM 3: GIỌNG VIỆT ĐẶC TRƯNG SIÊU TỐC OFFLINE (MASTERED 48KHZ) ===
    {"id": "free-vi-ngoc-ngan", "name": "Ngọc Ngạn (Truyện ma đêm khuya)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "ngocngan3701.onnx", "featured": False, "useCase": "Giọng đọc Truyện ma, Kể chuyện đêm khuya huyền thoại", "badge": "FAST OFFLINE"},
    {"id": "free-vi-tai-an", "name": "Tài An (CD Media Lịch sử)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "taian4.onnx", "featured": False, "useCase": "Phân tích Lịch sử, Địa chính trị, Kinh tế", "badge": "FAST OFFLINE"},
    {"id": "free-vi-manh-dung", "name": "Mạnh Dũng (Quảng cáo TVC)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "manhdung.onnx", "featured": False, "useCase": "Quảng cáo TVC hào sảng, Giới thiệu sản phẩm", "badge": "FAST OFFLINE"},
    {"id": "free-vi-ban-mai", "name": "Ban Mai (Chuẩn giọng Bắc)", "gender": "Nữ", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "banmai.onnx", "featured": False, "useCase": "Giọng Nữ miền Bắc chuẩn mực đọc sách báo dài", "badge": "FAST OFFLINE"},
    {"id": "free-vi-duy-oryx", "name": "Duy Oryx (Nam Siêu Trầm)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "duyoryx3175.onnx", "featured": False, "useCase": "Giọng Nam siêu trầm điện ảnh, Trailer, Podcast", "badge": "FAST OFFLINE"},
    {"id": "free-vi-minh-khang", "name": "Minh Khang (Kiến Giải Mã)", "gender": "Nam", "language": "vi", "country": "🇻🇳 Tiếng Việt", "provider": "piper", "model": "minhkhang.onnx", "featured": False, "useCase": "Thuyết minh Khoa học, Khám phá bí ẩn", "badge": "FAST OFFLINE"},

    # ==============================================================================
    # NHÓM 4: THƯ VIỆN ĐA NGÔN NGỮ QUỐC TẾ CHUẨN ELEVENLABS (32 NGÔN NGỮ TOÀN CẦU)
    # ==============================================================================
    # 1. English (US)
    {"id": "free-intl-en-us-ava", "name": "Ava (English US - Studio Female)", "gender": "Nữ", "language": "en-US", "country": "🇺🇸 Tiếng Anh (Mỹ)", "provider": "edge", "model": "en-US-AvaNeural", "featured": False, "useCase": "Storytelling, Audiobook, Conversational Podcast", "badge": "GLOBAL HD", "sampleText": "Welcome back to our channel! Today, a legendary hero awakens from a thousand-year slumber."},
    {"id": "free-intl-en-us-andrew", "name": "Andrew (English US - Studio Male)", "gender": "Nam", "language": "en-US", "country": "🇺🇸 Tiếng Anh (Mỹ)", "provider": "edge", "model": "en-US-AndrewNeural", "featured": False, "useCase": "Warm Narrator, Documentary, Movie Recap, Fantasy", "badge": "GLOBAL HD", "sampleText": "Deep beneath the ancient mountains, an unstoppable power began to rise once again."},
    {"id": "free-intl-en-us-brian", "name": "Brian (English US - Deep Male)", "gender": "Nam", "language": "en-US", "country": "🇺🇸 Tiếng Anh (Mỹ)", "provider": "edge", "model": "en-US-BrianNeural", "featured": False, "useCase": "Epic Trailer, Action Manhua Narration, YouTube Shorts", "badge": "GLOBAL HD", "sampleText": "Nobody believed he could survive the forbidden realm, until the sky turned crimson."},
    {"id": "free-intl-en-us-emma", "name": "Emma (English US - Expressive)", "gender": "Nữ", "language": "en-US", "country": "🇺🇸 Tiếng Anh (Mỹ)", "provider": "edge", "model": "en-US-EmmaNeural", "featured": False, "useCase": "Romance Novel, Vlog, E-Learning", "badge": "GLOBAL HD", "sampleText": "Hi everyone! Thank you so much for listening, let's dive right into chapter one."},
    # 2. English (UK)
    {"id": "free-intl-en-gb-ryan", "name": "Ryan (British English - Male)", "gender": "Nam", "language": "en-GB", "country": "🇬🇧 Tiếng Anh (Anh)", "provider": "edge", "model": "en-GB-RyanNeural", "featured": False, "useCase": "British Classic Fantasy, History, BBC Style", "badge": "GLOBAL HD", "sampleText": "Good evening. Tonight's tale takes us across the misty streets of Victorian London."},
    {"id": "free-intl-en-gb-sonia", "name": "Sonia (British English - Female)", "gender": "Nữ", "language": "en-GB", "country": "🇬🇧 Tiếng Anh (Anh)", "provider": "edge", "model": "en-GB-SoniaNeural", "featured": False, "useCase": "British Audiobook, News, Elegant Narration", "badge": "GLOBAL HD", "sampleText": "Welcome to London. Every ancient castle holds a secret waiting to be told."},
    # 3. English (Australia)
    {"id": "free-intl-en-au-william", "name": "William (Australian - Male)", "gender": "Nam", "language": "en-AU", "country": "🇦🇺 Tiếng Anh (Úc)", "provider": "edge", "model": "en-AU-WilliamMultilingualNeural", "featured": False, "useCase": "Travel, Documentary, Friendly Narration", "badge": "GLOBAL HD", "sampleText": "G'day mate! Let's explore some of the most breathtaking landscapes on Earth."},
    {"id": "free-intl-en-au-natasha", "name": "Natasha (Australian - Female)", "gender": "Nữ", "language": "en-AU", "country": "🇦🇺 Tiếng Anh (Úc)", "provider": "edge", "model": "en-AU-NatashaNeural", "featured": False, "useCase": "Lifestyle, Podcast, Commercial", "badge": "GLOBAL HD", "sampleText": "Hello there! Welcome to a brand new episode of our storytelling podcast."},
    # 4. Chinese Mandarin (Trung Quốc Đại Lục - Tiên Hiệp / Hoạt Hình 3D!)
    {"id": "free-intl-zh-cn-yunjian", "name": "Yunjian 云健 (Nam Tiên Hiệp / Donghua)", "gender": "Nam", "language": "zh-CN", "country": "🇨🇳 Tiếng Trung (Phổ thông)", "provider": "edge", "model": "zh-CN-YunjianNeural", "featured": False, "useCase": "Thuyết minh Tiên hiệp, Huyền huyễn, Hoạt hình 3D Trung Quốc", "badge": "GLOBAL HD", "sampleText": "苍穹之上，风云变幻！林威缓缓踏出一步，眼中闪过一道凌厉的寒芒。"},
    {"id": "free-intl-zh-cn-xiaoxiao", "name": "Xiaoxiao 晓晓 (Nữ Ngôn Tình / Douyin)", "gender": "Nữ", "language": "zh-CN", "country": "🇨🇳 Tiếng Trung (Phổ thông)", "provider": "edge", "model": "zh-CN-XiaoxiaoNeural", "featured": False, "useCase": "Giọng Nữ Trung Quốc tự nhiên số 1 — Douyin, Ngôn tình, Review", "badge": "GLOBAL HD", "sampleText": "大家好，欢迎来到我的频道，今天给大家讲一个非常精彩的玄幻故事。"},
    {"id": "free-intl-zh-cn-yunxi", "name": "Yunxi 云希 (Nam Trẻ Trung / Truyện Tranh)", "gender": "Nam", "language": "zh-CN", "country": "🇨🇳 Tiếng Trung (Phổ thông)", "provider": "edge", "model": "zh-CN-YunxiNeural", "featured": False, "useCase": "Nam chính truyện tranh Manhua, Giải thích phim", "badge": "GLOBAL HD", "sampleText": "没想到短短三年时间，他竟然已经突破到了传说中的至尊境界！"},
    # 5. Chinese Taiwan & Cantonese
    {"id": "free-intl-zh-tw-hsiaochen", "name": "HsiaoChen 曉臻 (Đài Loan - Nữ)", "gender": "Nữ", "language": "zh-TW", "country": "🇹🇼 Tiếng Trung (Đài Loan)", "provider": "edge", "model": "zh-TW-HsiaoChenNeural", "featured": False, "useCase": "Giọng Nữ Đài Loan dịu dàng, Podcast, Phim ảnh", "badge": "GLOBAL HD", "sampleText": "哈囉大家好，歡迎收聽今天的節目，祝你有個美好的一天。"},
    {"id": "free-intl-zh-tw-yunjhe", "name": "YunJhe 雲哲 (Đài Loan - Nam)", "gender": "Nam", "language": "zh-TW", "country": "🇹🇼 Tiếng Trung (Đài Loan)", "provider": "edge", "model": "zh-TW-YunJheNeural", "featured": False, "useCase": "Giọng Nam Đài Loan ấm áp, Thuyết minh", "badge": "GLOBAL HD", "sampleText": "歡迎回來，今天我們一起來看看這個不可思議的奇幻世界。"},
    {"id": "free-intl-zh-hk-hiumaan", "name": "HiuMaan 曉曼 (Quảng Đông - Nữ)", "gender": "Nữ", "language": "zh-HK", "country": "🇭🇰 Tiếng Quảng Đông (HK)", "provider": "edge", "model": "zh-HK-HiuMaanNeural", "featured": False, "useCase": "Phim TVB Hồng Kông, Review ẩm thực, Tin tức", "badge": "GLOBAL HD", "sampleText": "大家好，歡迎嚟到我嘅頻道，今日同大家分享一個好精彩嘅故事。"},
    {"id": "free-intl-zh-hk-wanlung", "name": "WanLung 雲龍 (Quảng Đông - Nam)", "gender": "Nam", "language": "zh-HK", "country": "🇭🇰 Tiếng Quảng Đông (HK)", "provider": "edge", "model": "zh-HK-WanLungNeural", "featured": False, "useCase": "Nam Hồng Kông TVB, Kể chuyện hành động", "badge": "GLOBAL HD", "sampleText": "各位觀眾大家好，多謝你哋一直以嚟嘅支持同埋收睇。"},
    # 6. Japanese (Nhật Bản - Anime / Light Novel)
    {"id": "free-intl-ja-nanami", "name": "Nanami 七海 (Nhật Bản - Nữ Anime)", "gender": "Nữ", "language": "ja-JP", "country": "🇯🇵 Tiếng Nhật", "provider": "edge", "model": "ja-JP-NanamiNeural", "featured": False, "useCase": "Anime, Light Novel Isekai, Vlog Nhật Bản", "badge": "GLOBAL HD", "sampleText": "こんにちは！異世界物語チャンネルへようこそ。今日も新しい冒険を始めましょう！"},
    {"id": "free-intl-ja-keita", "name": "Keita 圭太 (Nhật Bản - Nam)", "gender": "Nam", "language": "ja-JP", "country": "🇯🇵 Tiếng Nhật", "provider": "edge", "model": "ja-JP-KeitaNeural", "featured": False, "useCase": "Nam dẫn chuyện Manga / Isekai, Thuyết minh", "badge": "GLOBAL HD", "sampleText": "皆さんこんにちは。その日、世界はかつてない大きな変化を迎えようとしていた。"},
    # 7. Korean (Hàn Quốc - Webtoon / Manhwa)
    {"id": "free-intl-ko-sunhi", "name": "SunHi 선희 (Hàn Quốc - Nữ)", "gender": "Nữ", "language": "ko-KR", "country": "🇰🇷 Tiếng Hàn", "provider": "edge", "model": "ko-KR-SunHiNeural", "featured": False, "useCase": "Review Webtoon, K-Drama, Kể chuyện cảm xúc", "badge": "GLOBAL HD", "sampleText": "안녕하세요 여러분! 오늘 함께 만나볼 웹툰 이야기는 정말 흥미진진합니다."},
    {"id": "free-intl-ko-hyunsu", "name": "Hyunsu 현수 (Hàn Quốc - Nam Trầm)", "gender": "Nam", "language": "ko-KR", "country": "🇰🇷 Tiếng Hàn", "provider": "edge", "model": "ko-KR-HyunsuMultilingualNeural", "featured": False, "useCase": "Manhwa Solo Leveling Style, Thuyết minh phim Hàn", "badge": "GLOBAL HD", "sampleText": "그날 이후, 모든 것이 변하기 시작했습니다. 지금 바로 이야기를 시작하겠습니다."},
    # 8. French (Pháp)
    {"id": "free-intl-fr-vivienne", "name": "Vivienne (Tiếng Pháp - Nữ)", "gender": "Nữ", "language": "fr-FR", "country": "🇫🇷 Tiếng Pháp", "provider": "edge", "model": "fr-FR-VivienneMultilingualNeural", "featured": False, "useCase": "Văn học Pháp, Kể chuyện lãng mạn, Du lịch", "badge": "GLOBAL HD", "sampleText": "Bonjour à tous et bienvenue ! Aujourd'hui, nous plongeons dans une histoire extraordinaire."},
    {"id": "free-intl-fr-remy", "name": "Rémy (Tiếng Pháp - Nam)", "gender": "Nam", "language": "fr-FR", "country": "🇫🇷 Tiếng Pháp", "provider": "edge", "model": "fr-FR-RemyMultilingualNeural", "featured": False, "useCase": "Phóng sự, Sách nói, Điện ảnh Pháp", "badge": "GLOBAL HD", "sampleText": "Bonsoir à tous. Au cœur de la forêt ancienne, une légende oubliée reprend vie."},
    # 9. German (Đức)
    {"id": "free-intl-de-tanja", "name": "Tanja (Tiếng Đức - Nữ)", "gender": "Nữ", "language": "de-DE", "country": "🇩🇪 Tiếng Đức", "provider": "edge", "model": "de-DE-TanjaNeural", "featured": False, "useCase": "Sách nói, Tin tức, Kể chuyện tiếng Đức", "badge": "GLOBAL HD", "sampleText": "Hallo und herzlich willkommen! Schön, dass Sie heute wieder eingeschaltet haben."},
    {"id": "free-intl-de-christoph", "name": "Christoph (Tiếng Đức - Nam)", "gender": "Nam", "language": "de-DE", "country": "🇩🇪 Tiếng Đức", "provider": "edge", "model": "de-DE-ChristophNeural", "featured": False, "useCase": "Tài liệu khoa học, Lịch sử, Thuyết minh", "badge": "GLOBAL HD", "sampleText": "Willkommen zurück auf unserem Kanal. Heute erwartet Sie ein spannendes Kapitel."},
    # 10. Spanish (Spain & Latin America)
    {"id": "free-intl-es-ximena", "name": "Ximena (Tây Ban Nha - Nữ)", "gender": "Nữ", "language": "es-ES", "country": "🇪🇸 Tiếng Tây Ban Nha", "provider": "edge", "model": "es-ES-XimenaNeural", "featured": False, "useCase": "Kể chuyện, YouTube tiếng Tây Ban Nha Châu Âu", "badge": "GLOBAL HD", "sampleText": "¡Hola a todos y bienvenidos! Hoy vamos a descubrir una historia fascinante."},
    {"id": "free-intl-es-alvaro", "name": "Álvaro (Tây Ban Nha - Nam)", "gender": "Nam", "language": "es-ES", "country": "🇪🇸 Tiếng Tây Ban Nha", "provider": "edge", "model": "es-ES-AlvaroNeural", "featured": False, "useCase": "Thuyết minh phim, Kịch tính, Thể thao", "badge": "GLOBAL HD", "sampleText": "En aquel antiguo reino, nadie imaginaba el poder que estaba a punto de despertar."},
    {"id": "free-intl-es-mx-dalia", "name": "Dalia (Tây Ban Nha Mỹ Latinh - Nữ)", "gender": "Nữ", "language": "es-MX", "country": "🇲🇽 Tiếng TBN (Mỹ Latinh)", "provider": "edge", "model": "es-MX-DaliaNeural", "featured": False, "useCase": "Kênh YouTube thị trường Mỹ Latinh & Mexico", "badge": "GLOBAL HD", "sampleText": "¡Bienvenidos amigos! Gracias por acompañarnos en un nuevo episodio lleno de emoción."},
    {"id": "free-intl-es-mx-jorge", "name": "Jorge (Tây Ban Nha Mỹ Latinh - Nam)", "gender": "Nam", "language": "es-MX", "country": "🇲🇽 Tiếng TBN (Mỹ Latinh)", "provider": "edge", "model": "es-MX-JorgeNeural", "featured": False, "useCase": "Tóm tắt phim, Truyện tranh Manhua tiếng TBN", "badge": "GLOBAL HD", "sampleText": "Prepárate, porque el capítulo de hoy cambiará el destino de nuestro protagonista."},
    # 11. Portuguese (Brazil)
    {"id": "free-intl-pt-thalita", "name": "Thalita (Bồ Đào Nha Brazil - Nữ)", "gender": "Nữ", "language": "pt-BR", "country": "🇧🇷 Tiếng Bồ Đào Nha", "provider": "edge", "model": "pt-BR-ThalitaMultilingualNeural", "featured": False, "useCase": "Audiobook, Giải trí, Kênh YouTube Brazil", "badge": "GLOBAL HD", "sampleText": "Olá pessoal, sejam muito bem-vindos ao nosso canal de histórias incríveis!"},
    {"id": "free-intl-pt-antonio", "name": "Antônio (Bồ Đào Nha Brazil - Nam)", "gender": "Nam", "language": "pt-BR", "country": "🇧🇷 Tiếng Bồ Đào Nha", "provider": "edge", "model": "pt-BR-AntonioNeural", "featured": False, "useCase": "Thuyết minh hành động, Phóng sự", "badge": "GLOBAL HD", "sampleText": "Naquele momento decisivo, o guerreiro ergueu sua espada contra a tempestade."},
    # 12. Italian (Ý)
    {"id": "free-intl-it-isabella", "name": "Isabella (Tiếng Ý - Nữ)", "gender": "Nữ", "language": "it-IT", "country": "🇮🇹 Tiếng Ý", "provider": "edge", "model": "it-IT-IsabellaNeural", "featured": False, "useCase": "Nghệ thuật, Văn học, Kể chuyện tiếng Ý", "badge": "GLOBAL HD", "sampleText": "Ciao a tutti e benvenuti! Oggi vi racconterò una leggenda davvero straordinaria."},
    {"id": "free-intl-it-giuseppe", "name": "Giuseppe (Tiếng Ý - Nam)", "gender": "Nam", "language": "it-IT", "country": "🇮🇹 Tiếng Ý", "provider": "edge", "model": "it-IT-GiuseppeMultilingualNeural", "featured": False, "useCase": "Lịch sử La Mã, Điện ảnh, Podcast", "badge": "GLOBAL HD", "sampleText": "Benvenuti nel nostro viaggio attraverso i misteri delle antiche civiltà."},
    # 13. Russian (Nga)
    {"id": "free-intl-ru-svetlana", "name": "Svetlana Светлана (Tiếng Nga - Nữ)", "gender": "Nữ", "language": "ru-RU", "country": "🇷🇺 Tiếng Nga", "provider": "edge", "model": "ru-RU-SvetlanaNeural", "featured": False, "useCase": "Sách nói, Văn học Nga, Review phim", "badge": "GLOBAL HD", "sampleText": "Здравствуйте, дорогие друзья! Добро пожаловать на наш канал удивительных историй."},
    {"id": "free-intl-ru-dmitry", "name": "Dmitry Дмитрий (Tiếng Nga - Nam)", "gender": "Nam", "language": "ru-RU", "country": "🇷🇺 Tiếng Nga", "provider": "edge", "model": "ru-RU-DmitryNeural", "featured": False, "useCase": "Giọng Nam Nga trầm hùng, Huyền huyễn, Lịch sử", "badge": "GLOBAL HD", "sampleText": "Среди ледяных вершин древнего мира пробудилась великая сила."},
    # 14. Thai (Thái Lan)
    {"id": "free-intl-th-premwadee", "name": "Premwadee เปรมวดี (Tiếng Thái - Nữ)", "gender": "Nữ", "language": "th-TH", "country": "🇹🇭 Tiếng Thái Lan", "provider": "edge", "model": "th-TH-PremwadeeNeural", "featured": False, "useCase": "Review phim, Kể chuyện cổ trang & tiên hiệp Thái Lan", "badge": "GLOBAL HD", "sampleText": "สวัสดีค่ะทุกคน ยินดีต้อนรับเข้าสู่ช่องนิยายแฟนตาซีสุดเข้มข้นของเราค่ะ"},
    {"id": "free-intl-th-niwat", "name": "Niwat นิวัฒน์ (Tiếng Thái - Nam)", "gender": "Nam", "language": "th-TH", "country": "🇹🇭 Tiếng Thái Lan", "provider": "edge", "model": "th-TH-NiwatNeural", "featured": False, "useCase": "Nam thuyết minh Manhua / Tiên hiệp thị trường Thái", "badge": "GLOBAL HD", "sampleText": "ท่ามกลางหมอกหนาบนยอดเขาสูง ตำนานบทใหม่กำลังจะเริ่มต้นขึ้น ณ บัดนี้"},
    # 15. Indonesian (Indonesia - Thị trường YouTube Đông Nam Á cực lớn!)
    {"id": "free-intl-id-gadis", "name": "Gadis (Tiếng Indonesia - Nữ)", "gender": "Nữ", "language": "id-ID", "country": "🇮🇩 Tiếng Indonesia", "provider": "edge", "model": "id-ID-GadisNeural", "featured": False, "useCase": "Alur Cerita Film / Manhua thị trường Indonesia", "badge": "GLOBAL HD", "sampleText": "Halo semuanya, selamat datang kembali di channel cerita fantasi favorit kita!"},
    {"id": "free-intl-id-ardi", "name": "Ardi (Tiếng Indonesia - Nam)", "gender": "Nam", "language": "id-ID", "country": "🇮🇩 Tiếng Indonesia", "provider": "edge", "model": "id-ID-ArdiNeural", "featured": False, "useCase": "Nam thuyết minh Donghua / Manhua Indonesia", "badge": "GLOBAL HD", "sampleText": "Di balik kabut tebal pegunungan kuno, pendekar legendaris itu akhirnya bangkit kembali."},
    # 16. Malay & Filipino
    {"id": "free-intl-ms-yasmin", "name": "Yasmin (Tiếng Malaysia - Nữ)", "gender": "Nữ", "language": "ms-MY", "country": "🇲🇾 Tiếng Malaysia", "provider": "edge", "model": "ms-MY-YasminNeural", "featured": False, "useCase": "Kể chuyện, Tin tức tiếng Mã Lai", "badge": "GLOBAL HD", "sampleText": "Selamat datang ke saluran kami! Mari kita ikuti kisah pengembaraan hari ini."},
    {"id": "free-intl-ms-osman", "name": "Osman (Tiếng Malaysia - Nam)", "gender": "Nam", "language": "ms-MY", "country": "🇲🇾 Tiếng Malaysia", "provider": "edge", "model": "ms-MY-OsmanNeural", "featured": False, "useCase": "Nam thuyết minh Malaysia", "badge": "GLOBAL HD", "sampleText": "Terima kasih kerana menonton, kisah epik kita bermula sekarang."},
    {"id": "free-intl-fil-blessica", "name": "Blessica (Tiếng Philippines - Nữ)", "gender": "Nữ", "language": "fil-PH", "country": "🇵🇭 Tiếng Philippines", "provider": "edge", "model": "fil-PH-BlessicaNeural", "featured": False, "useCase": "Tagalog Storytelling & Vlog", "badge": "GLOBAL HD", "sampleText": "Kumusta kayong lahat! Maligayang pagbabalik sa ating kwento ngayong araw."},
    {"id": "free-intl-fil-angelo", "name": "Angelo (Tiếng Philippines - Nam)", "gender": "Nam", "language": "fil-PH", "country": "🇵🇭 Tiếng Philippines", "provider": "edge", "model": "fil-PH-AngeloNeural", "featured": False, "useCase": "Tagalog Action & Fantasy Recap", "badge": "GLOBAL HD", "sampleText": "Sa gitna ng kadiliman, isang bagong bayani ang handang lumaban."},
    # 17. Hindi (Ấn Độ)
    {"id": "free-intl-hi-swara", "name": "Swara स्वरा (Tiếng Hindi Ấn Độ - Nữ)", "gender": "Nữ", "language": "hi-IN", "country": "🇮🇳 Tiếng Hindi (Ấn Độ)", "provider": "edge", "model": "hi-IN-SwaraNeural", "featured": False, "useCase": "Kể chuyện & Tóm tắt phim thị trường Ấn Độ tỷ dân", "badge": "GLOBAL HD", "sampleText": "नमस्ते दोस्तों! हमारे चैनल में आपका स्वागत है, आज की कहानी बेहद रोमांचक है।"},
    {"id": "free-intl-hi-madhur", "name": "Madhur मधुर (Tiếng Hindi Ấn Độ - Nam)", "gender": "Nam", "language": "hi-IN", "country": "🇮🇳 Tiếng Hindi (Ấn Độ)", "provider": "edge", "model": "hi-IN-MadhurNeural", "featured": False, "useCase": "Nam thuyết minh sử thi & hành động Hindi", "badge": "GLOBAL HD", "sampleText": "हजारों साल बाद, उस रहस्यमयी योद्धा की शक्ति फिर से जाग उठी।"},
    # 18. Arabic (Ả Rập)
    {"id": "free-intl-ar-zariyah", "name": "Zariyah زارية (Tiếng Ả Rập - Nữ)", "gender": "Nữ", "language": "ar-SA", "country": "🇸🇦 Tiếng Ả Rập", "provider": "edge", "model": "ar-SA-ZariyahNeural", "featured": False, "useCase": "Kể chuyện, Tin tức & Tài liệu Trung Đông", "badge": "GLOBAL HD", "sampleText": "مرحباً بكم جميعاً في قناتنا، نأخذكم اليوم في رحلة خيالية مذهلة."},
    {"id": "free-intl-ar-hamed", "name": "Hamed حامد (Tiếng Ả Rập - Nam)", "gender": "Nam", "language": "ar-SA", "country": "🇸🇦 Tiếng Ả Rập", "provider": "edge", "model": "ar-SA-HamedNeural", "featured": False, "useCase": "Nam thuyết minh tiếng Ả Rập trầm ấm", "badge": "GLOBAL HD", "sampleText": "في أعماق الصحراء القديمة، بدأت أسطورة جديدة تكتب فصولها."},
    # 19. Turkish, Dutch, Polish, Swedish, Czech, Greek, Ukrainian, Romanian, Hungarian, Nordic
    {"id": "free-intl-tr-emel", "name": "Emel (Tiếng Thổ Nhĩ Kỳ - Nữ)", "gender": "Nữ", "language": "tr-TR", "country": "🇹🇷 Tiếng Thổ Nhĩ Kỳ", "provider": "edge", "model": "tr-TR-EmelNeural", "featured": False, "useCase": "Phim truyền hình & Kể chuyện Thổ Nhĩ Kỳ", "badge": "GLOBAL HD", "sampleText": "Merhaba arkadaşlar, kanalımıza hoş geldiniz! Bugün harika bir hikayemiz var."},
    {"id": "free-intl-tr-ahmet", "name": "Ahmet (Tiếng Thổ Nhĩ Kỳ - Nam)", "gender": "Nam", "language": "tr-TR", "country": "🇹🇷 Tiếng Thổ Nhĩ Kỳ", "provider": "edge", "model": "tr-TR-AhmetNeural", "featured": False, "useCase": "Nam thuyết minh Thổ Nhĩ Kỳ", "badge": "GLOBAL HD", "sampleText": "Kadim dağların zirvesinde unutulmuş bir efsane yeniden uyanıyor."},
    {"id": "free-intl-nl-fenna", "name": "Fenna (Tiếng Hà Lan - Nữ)", "gender": "Nữ", "language": "nl-NL", "country": "🇳🇱 Tiếng Hà Lan", "provider": "edge", "model": "nl-NL-FennaNeural", "featured": False, "useCase": "Podcast & Audiobook tiếng Hà Lan", "badge": "GLOBAL HD", "sampleText": "Hallo allemaal en welkom terug bij een gloednieuw verhaal!"},
    {"id": "free-intl-nl-maarten", "name": "Maarten (Tiếng Hà Lan - Nam)", "gender": "Nam", "language": "nl-NL", "country": "🇳🇱 Tiếng Hà Lan", "provider": "edge", "model": "nl-NL-MaartenNeural", "featured": False, "useCase": "Thuyết minh & Tin tức Hà Lan", "badge": "GLOBAL HD", "sampleText": "Goedenavond, vandaag nemen we u mee op een bijzondere reis."},
    {"id": "free-intl-pl-zofia", "name": "Zofia (Tiếng Ba Lan - Nữ)", "gender": "Nữ", "language": "pl-PL", "country": "🇵🇱 Tiếng Ba Lan", "provider": "edge", "model": "pl-PL-ZofiaNeural", "featured": False, "useCase": "Sách nói & Kể chuyện Ba Lan", "badge": "GLOBAL HD", "sampleText": "Cześć wszystkim! Witajcie ponownie na naszym kanale pełnym niezwykłych opowieści."},
    {"id": "free-intl-pl-marek", "name": "Marek (Tiếng Ba Lan - Nam)", "gender": "Nam", "language": "pl-PL", "country": "🇵🇱 Tiếng Ba Lan", "provider": "edge", "model": "pl-PL-MarekNeural", "featured": False, "useCase": "Nam dẫn truyện Fantasy Ba Lan", "badge": "GLOBAL HD", "sampleText": "W mrokach dawnego świata przebudziła się potężna, zapomniana magia."},
    {"id": "free-intl-sv-sofie", "name": "Sofie (Tiếng Thụy Điển - Nữ)", "gender": "Nữ", "language": "sv-SE", "country": "🇸🇪 Tiếng Thụy Điển", "provider": "edge", "model": "sv-SE-SofieNeural", "featured": False, "useCase": "Audiobook Bắc Âu", "badge": "GLOBAL HD", "sampleText": "Hej och varmt välkomna till dagens spännande berättelse!"},
    {"id": "free-intl-cs-vlasta", "name": "Vlasta (Tiếng Séc - Nữ)", "gender": "Nữ", "language": "cs-CZ", "country": "🇨🇿 Tiếng Séc", "provider": "edge", "model": "cs-CZ-VlastaNeural", "featured": False, "useCase": "Kể chuyện & Tin tức Cộng hòa Séc", "badge": "GLOBAL HD", "sampleText": "Dobrý den, vítejte u poslechu našeho dnešního příběhu."},
    {"id": "free-intl-el-athina", "name": "Athina (Tiếng Hy Lạp - Nữ)", "gender": "Nữ", "language": "el-GR", "country": "🇬🇷 Tiếng Hy Lạp", "provider": "edge", "model": "el-GR-AthinaNeural", "featured": False, "useCase": "Thần thoại Hy Lạp & Lịch sử", "badge": "GLOBAL HD", "sampleText": "Γεια σας και καλώς ήρθατε! Σήμερα θα ανακαλύψουμε έναν αρχαίο μύθο."},
    {"id": "free-intl-uk-polina", "name": "Polina (Tiếng Ukraina - Nữ)", "gender": "Nữ", "language": "uk-UA", "country": "🇺🇦 Tiếng Ukraina", "provider": "edge", "model": "uk-UA-PolinaNeural", "featured": False, "useCase": "Kể chuyện & Podcast tiếng Ukraina", "badge": "GLOBAL HD", "sampleText": "Привіт усім! Ласкаво просимо до нашої нової захопливої історії."},
    {"id": "free-intl-ro-alina", "name": "Alina (Tiếng Romania - Nữ)", "gender": "Nữ", "language": "ro-RO", "country": "🇷🇴 Tiếng Romania", "provider": "edge", "model": "ro-RO-AlinaNeural", "featured": False, "useCase": "Truyền thuyết & Sách nói Romania", "badge": "GLOBAL HD", "sampleText": "Salutare tuturor și bine ați venit la o nouă poveste captivantă!"},
    {"id": "free-intl-hu-noemi", "name": "Noémi (Tiếng Hungary - Nữ)", "gender": "Nữ", "language": "hu-HU", "country": "🇭🇺 Tiếng Hungary", "provider": "edge", "model": "hu-HU-NoemiNeural", "featured": False, "useCase": "Kể chuyện tiếng Hungary", "badge": "GLOBAL HD", "sampleText": "Sziasztok! Üdvözlök mindenkit a mai különleges történetünkben."},
    {"id": "free-intl-da-christel", "name": "Christel (Tiếng Đan Mạch - Nữ)", "gender": "Nữ", "language": "da-DK", "country": "🇩🇰 Tiếng Đan Mạch", "provider": "edge", "model": "da-DK-ChristelNeural", "featured": False, "useCase": "Truyện cổ tích & Podcast Đan Mạch", "badge": "GLOBAL HD", "sampleText": "Hej alle sammen, og hjertelig velkommen til dagens eventyr!"},
    {"id": "free-intl-fi-noora", "name": "Noora (Tiếng Phần Lan - Nữ)", "gender": "Nữ", "language": "fi-FI", "country": "🇫🇮 Tiếng Phần Lan", "provider": "edge", "model": "fi-FI-NooraNeural", "featured": False, "useCase": "Sách nói & Thuyết minh Phần Lan", "badge": "GLOBAL HD", "sampleText": "Hei kaikki ja lämpimästi tervetuloa kuuntelemaan tämän päivän tarinaa!"},
]

VOICE_MAP = {v["id"]: v for v in FREE_VOICES}

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
            if len(rem) > 280:
                sents = re.split(r"(?<=[.?!。？！])\s*", rem)
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
                if rem[-1] not in ".?!。？！":
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


def synthesize_vieneu_48k(text: str, voice_or_preset, rate: float = 1.0, pause_sec: float = 0.40) -> bytes:
    tts = get_vieneu()
    blocks = split_dramatic_blocks(text, base_pause=pause_sec)
    if not blocks:
        return encode_float32_to_wav_bytes(np.zeros(int(0.2 * TARGET_SR), dtype=np.float32), TARGET_SR)

    pieces: list[np.ndarray] = []
    for idx, (phrase, after_pause) in enumerate(blocks):
        clean_phrase = re.sub(r"[“”\"«»]", "", phrase).strip()
        if not clean_phrase:
            continue
        audio_f32 = tts.infer(clean_phrase, voice=voice_or_preset)
        seg = trim_and_smooth_float32(audio_f32, TARGET_SR)
        pieces.append(seg)
        if idx < len(blocks) - 1 and after_pause > 0:
            pieces.append(np.zeros(int(after_pause * TARGET_SR), dtype=np.float32))

    if not pieces:
        full = np.zeros(int(0.2 * TARGET_SR), dtype=np.float32)
    else:
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


async def synthesize_edge_48k(text: str, edge_voice: str, lang_code: str = "vi", rate: float = 1.0, pause_sec: float = 0.40) -> bytes:
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
                    await asyncio.sleep(0.40 * (attempt + 1))

            if last_err is not None or not os.path.exists(raw_mp3) or os.path.getsize(raw_mp3) <= 100:
                # For international languages, gracefully fallback to native Google TTS for that exact locale if Microsoft throttles
                if not lang_code.startswith("vi"):
                    g_lang = lang_code if lang_code in ("zh-CN", "zh-TW") else lang_code.split("-")[0]
                    if g_lang == "fil":
                        g_lang = "tl"
                    return synthesize_google_48k(text, lang=g_lang, rate=rate, pause_sec=pause_sec)
                raise RuntimeError(
                    "Máy chủ Microsoft Edge Neural đang bận tạm thời. "
                    "Bạn hãy chọn các giọng Studio 48kHz hoặc Giọng Nhân Bản Độc Quyền để chạy Offline 100% siêu mượt nhé!"
                )

            arr = mp3_to_float32_48k(raw_mp3, rate=rate)
            pieces.append(trim_and_smooth_float32(arr, TARGET_SR))
            if idx < len(blocks) - 1 and after_pause > 0:
                pieces.append(np.zeros(int(after_pause * TARGET_SR), dtype=np.float32))

    if not pieces:
        pieces.append(np.zeros(int(0.2 * TARGET_SR), dtype=np.float32))
    return encode_float32_to_wav_bytes(np.concatenate(pieces), TARGET_SR)


def dispatch_synthesize(
    text: str,
    voice_id: str,
    rate: float = 1.0,
    pause_sec: float = 0.40,
    owner_token: str | None = None,
) -> bytes:
    if voice_id.startswith("private-"):
        preset_dict = VAULT.get_authorized_voice_preset(voice_id, owner_token)
        with _ENGINE_LOCK:
            return synthesize_vieneu_48k(text, preset_dict, rate=rate, pause_sec=pause_sec)

    info = VOICE_MAP.get(voice_id) or VOICE_MAP["free-vi-ngoc-huyen"]
    provider = info["provider"]
    model = info["model"]
    lang_code = info.get("language", "vi")

    with _ENGINE_LOCK:
        if provider == "vieneu":
            return synthesize_vieneu_48k(text, model, rate=rate, pause_sec=pause_sec)
        elif provider == "piper":
            return synthesize_piper_mastered_48k(text, model, rate=rate, pause_sec=pause_sec)
        elif provider == "edge":
            return asyncio.run(synthesize_edge_48k(text, model, lang_code=lang_code, rate=rate, pause_sec=pause_sec))
        elif provider == "google":
            return synthesize_google_48k(text, lang=model, rate=rate, pause_sec=pause_sec)
        else:
            return synthesize_vieneu_48k(text, "Ngọc Huyền", rate=rate, pause_sec=pause_sec)


def get_public_voices() -> list[dict]:
    private_items = VAULT.list_private_voices_public()
    public_items = [
        {
            "id": v["id"],
            "name": v["name"],
            "gender": v["gender"],
            "language": v["language"],
            "country": v.get("country", v["language"].upper()),
            "provider": v["provider"],
            "featured": v["featured"],
            "isPrivate": False,
            "useCase": v["useCase"],
            "badge": v["badge"],
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
            self._send_json(200, {"ok": True, "warm": _VIENEU_INSTANCE is not None})
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
                with _ENGINE_LOCK:
                    tts = get_vieneu()
                    created = VAULT.enroll_new_private_voice(
                        vieneu_tts=tts,
                        audio_bytes=audio_bytes,
                        name=name,
                        gender=gender,
                        description=desc,
                        pin_or_token=tok,
                    )
                self._send_json(200, {"success": True, "voice": created, "voices": VAULT.list_private_voices_public()})
                return

            if self.path == "/private/delete":
                data = self._read_json()
                tok = self.headers.get("X-Owner-Token") or str(data.get("pin", ""))
                vid = str(data.get("voiceId", ""))
                VAULT.delete_private_voice(vid, tok)
                self._send_json(200, {"success": True, "voices": VAULT.list_private_voices_public()})
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
        except PermissionError as pe:
            self._send_json(403, {"success": False, "code": "private_locked", "error": str(pe)})
        except Exception as e:
            self._send_json(500, {"success": False, "error": str(e)})


def run_daemon(port: int = 3099) -> None:
    def _warmup():
        try:
            with _ENGINE_LOCK:
                get_vieneu()
            sys.stderr.write(f"[VoiceViet Daemon v4.0] VieNeu 48kHz + Private Vault + 32 Global Languages ready on port {port}!\n")
        except Exception as e:
            sys.stderr.write(f"[VoiceViet Daemon] Warmup note: {e}\n")

    threading.Thread(target=_warmup, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), EngineDaemonHandler)
    sys.stderr.write(f"[VoiceViet Daemon v4.0] Listening at http://127.0.0.1:{port}\n")
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
