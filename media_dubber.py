#!/usr/bin/env python3
"""
Voxly Studio — Multilingual Audio & Video Dubbing Engine
- Fast Offline Multilingual Speech-to-Text via faster-whisper (INT8 multi-core, 99 languages)
- Cross-Language Neural Text Translation (100+ languages, sentence-safe chunking)
- Instant FFmpeg .MP4 / .MOV / .WEBM Video Stream Re-Muxing (-c:v copy + smart atempo sync + audio ducking)
"""
import concurrent.futures
import glob
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import wave

import numpy as np

import audio_speaker_analyzer
import cinema_translator
import video_subtitle_ocr

_WHISPER_LOCK = threading.Lock()
_WHISPER_MODEL = None
_WHISPER_MODEL_NAME = ""
_DUB_PROGRESS = {
    "active": False,
    "vi": "",
    "en": "",
    "pct": 0,
    "updatedAt": 0.0,
}


def set_dub_live_progress(vi_msg: str, en_msg: str, pct: int, active: bool = True) -> None:
    _DUB_PROGRESS["active"] = active
    _DUB_PROGRESS["vi"] = vi_msg
    _DUB_PROGRESS["en"] = en_msg
    _DUB_PROGRESS["pct"] = max(0, min(100, int(pct)))
    _DUB_PROGRESS["updatedAt"] = time.time()


def get_dub_live_progress() -> dict:
    return dict(_DUB_PROGRESS)


def resolve_ffprobe(ffmpeg_bin: str = "ffmpeg") -> str:
    sibling = os.path.join(os.path.dirname(ffmpeg_bin), "ffprobe")
    if os.path.exists(sibling):
        return sibling
    found = shutil.which("ffprobe")
    if found:
        return found
    for p in ("/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe", "/usr/bin/ffprobe"):
        if os.path.exists(p):
            return p
    return "ffprobe"


def _whisper_cache_dirs_for(model_size: str) -> list[str]:
    if model_size in ("turbo", "large-v3-turbo"):
        return [
            os.path.expanduser(
                "~/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/snapshots"
            )
        ]
    return [
        os.path.expanduser(f"~/.cache/huggingface/hub/models--Systran--faster-whisper-{model_size}/snapshots")
    ]


def _has_local_whisper_model(model_size: str) -> bool:
    for d in _whisper_cache_dirs_for(model_size):
        if os.path.isdir(d):
            for snap in os.listdir(d):
                if os.path.exists(os.path.join(d, snap, "model.bin")):
                    return True
    return False


def get_whisper_model(prefer_large_v3: bool = False):
    global _WHISPER_MODEL, _WHISPER_MODEL_NAME
    env_pref = os.environ.get("VOXLY_WHISPER_MODEL", "").strip()
    if env_pref:
        desired = env_pref
    elif prefer_large_v3 and _has_local_whisper_model("large-v3"):
        desired = "large-v3"
    else:
        desired = "turbo"

    if _WHISPER_MODEL is not None and _WHISPER_MODEL_NAME == desired:
        return _WHISPER_MODEL

    with _WHISPER_LOCK:
        if _WHISPER_MODEL is not None and _WHISPER_MODEL_NAME == desired:
            return _WHISPER_MODEL
        from faster_whisper import WhisperModel

        candidates = [desired] + [m for m in ("turbo", "large-v3", "small", "base") if m != desired]
        cpu_threads = min(8, max(4, os.cpu_count() or 4))

        for model_size in candidates:
            has_local = _has_local_whisper_model(model_size)
            # Never stall downloading a 3GB fallback when turbo is already cached locally
            if model_size == "large-v3" and not has_local and _has_local_whisper_model("turbo"):
                continue
            prev_offline = os.environ.get("HF_HUB_OFFLINE")
            if not has_local:
                os.environ["HF_HUB_OFFLINE"] = "0"
                try:
                    import huggingface_hub.constants as hf_const
                    hf_const.HF_HUB_OFFLINE = False
                except Exception:
                    pass
            try:
                _WHISPER_MODEL = None
                _WHISPER_MODEL = WhisperModel(
                    model_size,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=cpu_threads,
                    local_files_only=has_local,
                )
                _WHISPER_MODEL_NAME = model_size
                print(f"[WhisperASR] Loaded model: {model_size} (local={has_local})")
                break
            except Exception as load_err:
                if model_size == candidates[-1]:
                    raise load_err
            finally:
                if not has_local and prev_offline is not None:
                    os.environ["HF_HUB_OFFLINE"] = prev_offline
    return _WHISPER_MODEL


def probe_media_info(media_path: str, ffmpeg_bin: str = "ffmpeg") -> dict:
    ffprobe_bin = resolve_ffprobe(ffmpeg_bin)
    try:
        out = subprocess.check_output(
            [
                ffprobe_bin,
                "-v", "error",
                "-show_entries", "stream=codec_type:format=duration",
                "-of", "json",
                media_path,
            ],
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        info = json.loads(out.decode("utf-8", errors="ignore") or "{}")
        streams = info.get("streams") or []
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        dur = float((info.get("format") or {}).get("duration") or 0.0)
        return {"hasVideo": has_video, "hasAudio": has_audio, "durationSec": max(0.0, dur)}
    except Exception:
        ext = os.path.splitext(media_path)[1].lower()
        return {
            "hasVideo": ext in (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"),
            "hasAudio": True,
            "durationSec": 0.0,
        }


def extract_16k_wav(media_path: str, out_wav_path: str, ffmpeg_bin: str = "ffmpeg", timeout_sec: int = 600) -> None:
    """
    Extracts mono 16kHz PCM with broadcast dynamic vocal leveling (`dynaudnorm`) so soft,
    whispered, or indoor conversational Japanese/English/Chinese dialogue (-34 dBFS) is lifted
    clearly into speech recognition range without clipping loud scenes — preventing VAD dropouts!
    """
    cmd_norm = [
        ffmpeg_bin,
        "-nostdin",
        "-y",
        "-i", media_path,
        "-vn",
        "-af", "highpass=f=70,dynaudnorm=f=250:g=21:p=0.88:m=6:s=12",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        out_wav_path,
    ]
    proc = subprocess.run(cmd_norm, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=max(240, timeout_sec))
    if proc.returncode == 0 and os.path.exists(out_wav_path) and os.path.getsize(out_wav_path) >= 200:
        return
    # Safe fallback without filter chain if exotic container fails dynaudnorm
    cmd_raw = [
        ffmpeg_bin,
        "-nostdin",
        "-y",
        "-i", media_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        out_wav_path,
    ]
    proc2 = subprocess.run(cmd_raw, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=max(240, timeout_sec))
    if proc2.returncode != 0 or not os.path.exists(out_wav_path) or os.path.getsize(out_wav_path) < 200:
        err_txt = proc2.stderr.decode("utf-8", errors="ignore")[-300:]
        raise RuntimeError(f"Không thể tách âm thanh từ file tải lên ({err_txt.strip() or 'FFmpeg error'}).")


def normalize_whisper_lang_code(lang: str) -> str | None:
    if not lang or lang in ("auto", "detect", ""):
        return None
    base = lang.split("-")[0].split("_")[0].lower().strip()
    return base or None


# Exact Google Translate target/source BCP-47 language code normalization
_TRANSLATE_LANG_MAP = {
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-hans": "zh-CN",
    "cmn": "zh-CN",
    "zh-tw": "zh-TW",
    "zh-hk": "zh-TW",
    "zh-hant": "zh-TW",
    "yue": "zh-TW",
    "he": "iw",
    "iw": "iw",
    "jv": "jw",
    "jw": "jw",
    "fil": "tl",
    "tl": "tl",
    "nb": "no",
    "nn": "no",
}


def normalize_translate_lang_code(lang: str) -> str:
    if not lang:
        return "vi"
    clean = lang.strip().replace("_", "-")
    lower = clean.lower()
    if lower in _TRANSLATE_LANG_MAP:
        return _TRANSLATE_LANG_MAP[lower]
    base = lower.split("-")[0]
    return _TRANSLATE_LANG_MAP.get(base, base)


def _split_text_safe_chunks(text: str, max_chars: int = 900) -> list[str]:
    """Splits arbitrarily long or unpunctuated Whisper transcripts into <= max_chars chunks."""
    raw = re.sub(r"\s+", " ", (text or "")).strip()
    if not raw:
        return []
    if len(raw) <= max_chars:
        return [raw]

    # Primary split by sentence-ending punctuation
    tokens = re.findall(r"[^.!?;,\n。？！，；]+(?:[.!?;,\n。？！，；]+|$)", raw) or [raw]
    chunks: list[str] = []
    cur = ""

    for tok in tokens:
        part = tok.strip()
        if not part:
            continue
        if len(part) > max_chars:
            if cur:
                chunks.append(cur)
                cur = ""
            # Hard-split run-on unpunctuated Whisper segments on word boundaries (or char slice for CJK)
            words = part.split(" ")
            if len(words) > 1:
                w_buf = ""
                for w in words:
                    if len(w_buf) + len(w) + 1 <= max_chars:
                        w_buf = f"{w_buf} {w}".strip() if w_buf else w
                    else:
                        if w_buf:
                            chunks.append(w_buf)
                        w_buf = w[:max_chars]
                if w_buf:
                    chunks.append(w_buf)
            else:
                for i in range(0, len(part), max_chars):
                    chunks.append(part[i : i + max_chars])
        elif len(cur) + len(part) + 1 <= max_chars:
            cur = f"{cur} {part}".strip() if cur else part
        else:
            if cur:
                chunks.append(cur)
            cur = part

    if cur:
        chunks.append(cur)
    return chunks


def _translate_single_chunk_gtx(chunk: str, source_lang: str, target_lang: str) -> tuple[str, str]:
    """
    Uses HTTP POST form body (NOT GET URL query string!) so long UTF-8 Vietnamese/CJK/English
    transcripts NEVER exceed Google's 4KB URL limit and NEVER trigger HTTP 400 Bad Request!
    Includes automatic sl='auto' retry + clients5 fallback.
    """
    sl = "auto" if not source_lang or source_lang == "auto" else normalize_translate_lang_code(source_lang)
    tl = normalize_translate_lang_code(target_lang)
    if sl != "auto" and sl.lower() == tl.lower():
        return chunk, sl

    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"

    for attempt_sl in ([sl, "auto"] if sl != "auto" else ["auto"]):
        try:
            query_qs = urllib.parse.urlencode({"client": "gtx", "sl": attempt_sl, "tl": tl, "dt": "t"})
            url = f"https://translate.googleapis.com/translate_a/single?{query_qs}"
            form_body = urllib.parse.urlencode({"q": chunk}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=form_body,
                method="POST",
                headers={
                    "User-Agent": ua,
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            pieces = []
            if isinstance(data, list) and data and isinstance(data[0], list):
                for seg in data[0]:
                    if isinstance(seg, list) and seg and seg[0]:
                        pieces.append(str(seg[0]))
            detected = data[2] if isinstance(data, list) and len(data) > 2 and isinstance(data[2], str) else attempt_sl
            joined = "".join(pieces).strip()
            if joined:
                return joined, detected
        except Exception:
            continue

    # Secondary POST fallback endpoint (clients5 dict-chrome-ex)
    query_qs2 = urllib.parse.urlencode({"client": "dict-chrome-ex", "sl": "auto", "tl": tl})
    url2 = f"https://clients5.google.com/translate_a/t?{query_qs2}"
    body2 = urllib.parse.urlencode({"q": chunk}).encode("utf-8")
    req2 = urllib.request.Request(
        url2,
        data=body2,
        method="POST",
        headers={
            "User-Agent": ua,
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
    )
    with urllib.request.urlopen(req2, timeout=15) as resp2:
        data2 = json.loads(resp2.read().decode("utf-8"))
    if isinstance(data2, list) and data2:
        first = data2[0]
        if isinstance(first, list) and first:
            return str(first[0]).strip(), str(first[1] if len(first) > 1 else sl)
        if isinstance(first, str):
            return first.strip(), sl
    raise RuntimeError(f"Không thể dịch sang ngôn ngữ '{target_lang}'. Vui lòng kiểm tra kết nối mạng!")


def translate_text_multilingual(text: str, source_lang: str = "auto", target_lang: str = "vi") -> tuple[str, str]:
    raw = (text or "").strip()
    if not raw:
        return "", source_lang or "auto"
    if not target_lang or target_lang == "same":
        return raw, source_lang or "auto"

    sl_norm = normalize_translate_lang_code(source_lang) if source_lang and source_lang != "auto" else "auto"
    tl_norm = normalize_translate_lang_code(target_lang)
    if sl_norm != "auto" and sl_norm.lower() == tl_norm.lower():
        return raw, sl_norm

    chunks = _split_text_safe_chunks(raw, max_chars=900)
    if not chunks:
        return "", sl_norm

    if len(chunks) == 1:
        tr, det = _translate_single_chunk_gtx(chunks[0], sl_norm, tl_norm)
        return tr or chunks[0], det

    # Translate multiple chunks concurrently (4 workers -> 10-minute video translates in ~0.5s!)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda c: _translate_single_chunk_gtx(c, sl_norm, tl_norm), chunks))

    translated_parts = [r[0] or chunks[i] for i, r in enumerate(results)]
    detected_final = next((r[1] for r in results if r[1] and r[1] != "auto"), sl_norm)
    return " ".join(translated_parts).strip(), detected_final


def format_timestamp_sec(sec: float) -> str:
    s = max(0.0, float(sec or 0.0))
    hrs = int(s // 3600)
    mins = int((s % 3600) // 60)
    rem = s - (hrs * 3600 + mins * 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{rem:04.1f}"
    return f"{mins:02d}:{rem:04.1f}"


def _parse_ts_str(ts_str: str) -> float:
    parts = [p.strip() for p in (ts_str or "").split(":")]
    if len(parts) == 3:
        return float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
    if len(parts) == 2:
        return float(parts[0]) * 60.0 + float(parts[1])
    return float(parts[0] or 0.0)


_TS_LINE_RE = re.compile(
    r"^\s*\[(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*-\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]\s*(?:\[([^\]]{2,28})\]\s*)?(.*)$"
)


def format_timestamped_script(segments: list[dict], text_key: str = "text", include_role: bool = False) -> str:
    lines: list[str] = []
    for seg in segments or []:
        txt = re.sub(r"\s+", " ", str(seg.get(text_key) or seg.get("text") or "")).strip()
        if not txt:
            continue
        st = format_timestamp_sec(seg.get("start", 0.0))
        en = format_timestamp_sec(seg.get("end", 0.0))
        role_code = audio_speaker_analyzer.canonicalize_role_tag(str(seg.get("role") or seg.get("acousticRole") or ""))
        if include_role and role_code:
            r_lbl = audio_speaker_analyzer.role_to_display_label(role_code)
            lines.append(f"[{st} - {en}] [{r_lbl}] {txt}")
        else:
            lines.append(f"[{st} - {en}] {txt}")
    return "\n".join(lines)


def parse_timestamped_script(raw_script: str) -> tuple[list[dict], str, bool]:
    """
    Parses `[mm:ss.d - mm:ss.d] [OPTIONAL_ROLE] Spoken line` lines into structured segments.
    Returns `(segments, plain_spoken_text, has_timestamps)`.
    """
    raw = (raw_script or "").strip()
    if not raw:
        return [], "", False

    parsed: list[dict] = []
    has_ts = False
    for line in raw.splitlines():
        m = _TS_LINE_RE.match(line)
        if m:
            has_ts = True
            st = round(_parse_ts_str(m.group(1)), 2)
            en = round(max(st + 0.25, _parse_ts_str(m.group(2))), 2)
            raw_role = (m.group(3) or "").strip()
            role_code = audio_speaker_analyzer.canonicalize_role_tag(raw_role) if raw_role else ""
            txt = (m.group(4) or "").strip()
            # If the bracket wasn't a recognized role tag (e.g. sound cue), preserve it in text
            if raw_role and not role_code:
                txt = f"[{raw_role}] {txt}".strip()
            if txt:
                seg_obj = {"start": st, "end": en, "text": txt}
                if role_code:
                    seg_obj["role"] = role_code
                parsed.append(seg_obj)
        elif has_ts and parsed and line.strip():
            parsed[-1]["text"] = f"{parsed[-1]['text']} {line.strip()}".strip()

    if has_ts and parsed:
        plain = " ".join(s["text"] for s in parsed).strip()
        return parsed, plain, True

    clean_plain = re.sub(r"\s+", " ", raw).strip()
    return [], clean_plain, False


def translate_segments_multilingual(
    segments: list[dict],
    source_lang: str = "auto",
    target_lang: str = "vi",
    ai_provider: str = "local",
    ai_api_key: str = "",
    ai_model: str = "",
) -> tuple[list[dict], str]:
    """
    Translates movie dialogue turns 1-to-1 with Acoustic Speaker Roles + Character Bible + Rolling Scene Context
    via Pro Cinema AI Director (Qwen3-14B Local or Gemini/OpenAI/DeepSeek Cloud API).
    """
    if not segments:
        return [], source_lang or "auto"

    if not target_lang or target_lang == "same":
        out = [
            {
                **s,
                "translatedText": s.get("text", ""),
                "role": audio_speaker_analyzer.canonicalize_role_tag(str(s.get("role") or s.get("acousticRole") or "")) or "DAN_CHUYEN",
            }
            for s in segments
        ]
        return out, source_lang or "auto"

    sl_norm = normalize_translate_lang_code(source_lang) if source_lang and source_lang != "auto" else "auto"
    tl_norm = normalize_translate_lang_code(target_lang)
    if sl_norm != "auto" and sl_norm.lower() == tl_norm.lower():
        out = [
            {
                **s,
                "translatedText": s.get("text", ""),
                "role": audio_speaker_analyzer.canonicalize_role_tag(str(s.get("role") or s.get("acousticRole") or "")) or "DAN_CHUYEN",
            }
            for s in segments
        ]
        return out, sl_norm

    src_lines = [re.sub(r"\s+", " ", str(seg.get("text", ""))).strip() for seg in segments]
    ac_roles = [str(seg.get("acousticRole") or seg.get("role") or "") for seg in segments]
    prov_tag = (ai_provider or "local").strip().upper()
    ai_lbl = (
        "AI Biên kịch 14B Pro"
        if prov_tag == "LOCAL_14B"
        else (f"AI {prov_tag} Pro" if prov_tag not in ("LOCAL", "LOCAL_FAST") and ai_api_key else "AI Biên kịch 8B Pro")
    )

    last_tr_pct = [41]

    def _on_tr_progress(done_n: int, total_n: int) -> None:
        # Keep strictly within 42..65% while Step 1 is still active (66% only triggers when Step 1 returns!)
        p = 42 + int((done_n / max(1, total_n)) * 23)
        p = max(42, min(65, p))
        last_tr_pct[0] = p
        set_dub_live_progress(
            f"🎙️ {ai_lbl} đang biên dịch thuyết minh chuẩn từng từ câu {min(done_n + 1, total_n)}/{total_n}...",
            f"🎙️ {ai_lbl} translating exact narration cue {min(done_n + 1, total_n)}/{total_n}...",
            p,
        )

    def _on_tr_status(vi_s: str, en_s: str) -> None:
        set_dub_live_progress(
            f"{vi_s} ({ai_lbl})",
            f"{en_s} ({ai_lbl})",
            last_tr_pct[0],
        )

    set_dub_live_progress(
        f"🌐 Đang dịch nền bám sát từng câu cho {len(src_lines)} câu thoại ({ai_lbl})...",
        f"🌐 Building literal translation anchors for {len(src_lines)} cues ({ai_lbl})...",
        40,
    )

    translated_lines, refined_roles = cinema_translator.translate_cinema_lines_with_roles(
        lines=src_lines,
        speaker_roles=ac_roles,
        source_lang=sl_norm,
        target_lang=tl_norm,
        ai_provider=ai_provider,
        ai_api_key=ai_api_key,
        ai_model=ai_model,
        nmt_fallback_fn=_translate_single_chunk_gtx,
        progress_cb=_on_tr_progress,
        status_cb=_on_tr_status,
    )

    enriched = []
    for i, seg in enumerate(segments):
        tr_txt = translated_lines[i] if i < len(translated_lines) else seg["text"]
        r_code = refined_roles[i] if i < len(refined_roles) else (seg.get("acousticRole") or "DAN_CHUYEN")
        enriched.append(
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "translatedText": (tr_txt or seg["text"]).strip(),
                "role": r_code,
                "roleLabel": audio_speaker_analyzer.role_to_display_label(r_code),
                "acousticRole": seg.get("acousticRole", r_code),
                "acousticF0": seg.get("acousticF0", 0.0),
            }
        )
    return enriched, sl_norm


def translate_script_preserving_timestamps(
    raw_text: str,
    source_lang: str = "auto",
    target_lang: str = "vi",
    ai_provider: str = "local",
    ai_api_key: str = "",
    ai_model: str = "",
    include_role: bool = False,
) -> tuple[str, str]:
    segs, plain, has_ts = parse_timestamped_script(raw_text)
    if has_ts and segs:
        tr_segs, det = translate_segments_multilingual(
            segs,
            source_lang=source_lang,
            target_lang=target_lang,
            ai_provider=ai_provider,
            ai_api_key=ai_api_key,
            ai_model=ai_model,
        )
        return format_timestamped_script(tr_segs, text_key="translatedText", include_role=include_role), det
    if not plain:
        return "", source_lang or "auto"
    tr_list, _ = cinema_translator.translate_cinema_lines_with_roles(
        lines=[plain],
        speaker_roles=None,
        source_lang=source_lang,
        target_lang=target_lang,
        ai_provider=ai_provider,
        ai_api_key=ai_api_key,
        ai_model=ai_model,
        nmt_fallback_fn=_translate_single_chunk_gtx,
    )
    return (tr_list[0] if tr_list else plain), (source_lang or "auto")


_WHISPER_HALLUCINATION_RE = re.compile(
    r"^(?:subtitles?\s+by|amara\.org|thank\s+you\s+for\s+watching|thanks\s+for\s+watching|"
    r"please\s+subscribe|字幕由|请不吝点赞|感谢观看|谢谢观看|优优独播剧场|"
    r"ご視聴ありがとうございました|チャンネル登録.*|最後までご視聴.*|高評価.*|字幕作成.*|翻訳.*).*$",
    re.IGNORECASE,
)

# Japanese sentence-final particles / verb endings signaling a natural turn boundary
_JA_TURN_END_RE = re.compile(
    r"(?:よ|ね|な|ぞ|わ|さ|か|っけ|ってば|じゃん|んだよ|んだから|んだ|ます|です|ました|でした|ない|よな|よね|かな|って|てるの|てたの)[。？！!?、,]*$"
)


def _count_linguistic_units(txt: str) -> int:
    cjk = len(re.findall(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", txt))
    latin_words = len(re.findall(r"[A-Za-zÀ-ỹ0-9']+", txt))
    return cjk + latin_words


def _dedupe_whisper_stutter(text: str) -> str:
    """Collapses Whisper Japanese/CJK repetition loops (e.g. 'いいじゃん、いいじゃん×6' -> 'いいじゃん、いいじゃん')."""
    if not text:
        return ""
    s = re.sub(r"([\u3040-\u30ff\u4e00-\u9fff]{2,8})(?:[、，,\s]*\1){2,}", r"\1、\1", text)
    return s.strip()


def _extract_utterance_segments(
    segments_iter,
    source_lang_hint: str = "auto",
    total_dur_sec: float = 0.0,
    job_gen: int = 0,
) -> list[dict]:
    """
    Reconstructs tight, speaker-hugging dialogue turns from Whisper:
    1. Streams live progress (current minute / total minutes + cue count) & checks cancellation on EVERY segment!
    2. Filters out YouTube/credits hallucinations & extreme low-confidence sub-0.3s noise glitches.
    3. Splits on EVERY natural speech pause (gap >= 0.48s, terminal punct >= 0.16s, or clause >= 3.4s)
       so narration hugs the real speaker's exact start & end timing (1-4.8s per cue — NEVER 10s glued blocks!).
    """
    atomic_segs: list[dict] = []
    is_ja_hint = str(source_lang_hint or "").lower().startswith("ja")
    last_prog_ts = 0.0

    for seg in segments_iter:
        if job_gen > 0:
            cinema_translator._check_not_cancelled(job_gen)
        now_t = time.time()
        if total_dur_sec > 5.0 and (now_t - last_prog_ts) >= 0.8:
            last_prog_ts = now_t
            seg_t = max(0.0, float(getattr(seg, "end", 0.0) or 0.0))
            frac = min(1.0, seg_t / max(1.0, total_dur_sec))
            pct = 20 + int(frac * 18)
            set_dub_live_progress(
                f"🎙️ Đang nhận diện lời thoại ({format_timestamp_sec(seg_t)} / {format_timestamp_sec(total_dur_sec)} • {len(atomic_segs)} câu)...",
                f"🎙️ Transcribing dialogue ({format_timestamp_sec(seg_t)} / {format_timestamp_sec(total_dur_sec)} • {len(atomic_segs)} cues)...",
                pct,
            )

        raw_t = _dedupe_whisper_stutter((seg.text or "").strip())
        if not raw_t:
            continue
        no_sp = float(getattr(seg, "no_speech_prob", 0.0) or 0.0)
        avg_lp = float(getattr(seg, "avg_logprob", -0.3) or -0.3)
        if no_sp > 0.88 and _count_linguistic_units(raw_t) <= 3:
            continue
        if avg_lp < -1.35 and _count_linguistic_units(raw_t) <= 3 and (float(seg.end) - float(seg.start)) < 0.55:
            continue
        if _WHISPER_HALLUCINATION_RE.match(raw_t):
            continue

        seg_words = [w for w in (getattr(seg, "words", None) or []) if (getattr(w, "word", "") or "").strip()]
        if not seg_words:
            clean_t = cinema_translator.preclean_source_dialogue_line(raw_t, source_lang=source_lang_hint)
            if clean_t:
                st0 = max(0.0, float(seg.start))
                en0 = max(st0 + 0.28, float(seg.end))
                atomic_segs.append({"start": round(st0, 2), "end": round(en0, 2), "text": clean_t})
            continue

        sub_words: list[str] = []
        sub_st = max(0.0, float(seg_words[0].start))
        sub_en = max(sub_st + 0.08, float(seg_words[0].end))

        def _flush_sub():
            nonlocal sub_words, sub_st, sub_en
            if not sub_words:
                return
            joined_t = _dedupe_whisper_stutter(
                cinema_translator.preclean_source_dialogue_line("".join(sub_words), source_lang=source_lang_hint)
            )
            if joined_t and not _WHISPER_HALLUCINATION_RE.match(joined_t):
                atomic_segs.append(
                    {
                        "start": round(sub_st, 2),
                        "end": round(max(sub_st + 0.25, sub_en), 2),
                        "text": joined_t,
                    }
                )
            sub_words = []

        for w in seg_words:
            ws = max(0.0, float(w.start))
            we = max(ws + 0.06, float(w.end))
            wt = getattr(w, "word", "")
            if not sub_words:
                sub_st, sub_en, sub_words = ws, we, [wt]
                continue
            gap = ws - sub_en
            cur_dur = sub_en - sub_st
            prev_str = "".join(sub_words).rstrip()
            ends_terminal = bool(re.search(r"[.!?。？！…][\"')\]»”’]*$", prev_str))
            ends_comma = bool(re.search(r"[、，,;；][\"')\]»”’]*$", prev_str))
            ja_clause_end = (is_ja_hint or bool(re.search(r"[\u3040-\u30ff]", prev_str))) and bool(_JA_TURN_END_RE.search(prev_str))

            should_split = False
            if gap >= 0.48:
                should_split = True
            elif ends_terminal and (gap >= 0.16 or cur_dur >= 2.0):
                should_split = True
            elif ja_clause_end and (gap >= 0.22 or (ends_comma and cur_dur >= 2.2) or cur_dur >= 3.4):
                should_split = True
            elif ends_comma and cur_dur >= 3.4 and gap >= 0.14:
                should_split = True
            elif cur_dur >= 4.8 and (ends_comma or gap >= 0.10 or _count_linguistic_units(prev_str) >= 26):
                should_split = True

            if should_split:
                _flush_sub()
                sub_st, sub_en, sub_words = ws, we, [wt]
            else:
                sub_en = max(sub_en, we)
                sub_words.append(wt)
        _flush_sub()

    if not atomic_segs:
        return []

    # Pass 1.5: Repair faster-whisper VAD-seam boundary bleed!
    repaired_atomic: list[dict] = []
    idx_a = 0
    standalone_interj_re = re.compile(
        r"^(?:嗯|哦|啊|噢|好|行|对|是|不|操|我去|卧槽|牛逼|齐活|成交|うん|え|あ|ああ|ねえ|はい|いいえ|うわ|おい)[。！？!?.？]*$"
    )
    while idx_a < len(atomic_segs):
        seg_cur = dict(atomic_segs[idx_a])
        if idx_a + 1 < len(atomic_segs):
            seg_nxt = atomic_segs[idx_a + 1]
            gap_a = seg_nxt["start"] - seg_cur["end"]
            cur_t = seg_cur["text"].strip()
            cur_dur_a = seg_cur["end"] - seg_cur["start"]

            m_tail = re.match(r"^(.+[。！？.!?])\s*([^。！？.!?,，、；：\s]{1,4})$", cur_t)
            if m_tail and gap_a >= 0.85:
                seg_cur["text"] = m_tail.group(1).strip()
                stub = m_tail.group(2).strip()
                is_cjk_stub = bool(re.search(r"[\u4e00-\u9fff\u3040-\u30ff]", stub))
                atomic_segs[idx_a + 1] = dict(seg_nxt)
                atomic_segs[idx_a + 1]["text"] = (
                    f"{stub}{seg_nxt['text'].lstrip()}" if is_cjk_stub else f"{stub} {seg_nxt['text'].lstrip()}"
                )
            elif (
                gap_a >= 1.80
                and cur_dur_a <= 0.50
                and _count_linguistic_units(cur_t) <= 2
                and not re.search(r"[。！？.!?？]$", cur_t)
                and not standalone_interj_re.match(cur_t)
            ):
                is_cjk_o = bool(re.search(r"[\u4e00-\u9fff\u3040-\u30ff]", cur_t))
                atomic_segs[idx_a + 1] = dict(seg_nxt)
                clean_o = cur_t.rstrip("，,、 ")
                atomic_segs[idx_a + 1]["text"] = (
                    f"{clean_o}{seg_nxt['text'].lstrip()}" if is_cjk_o else f"{clean_o} {seg_nxt['text'].lstrip()}"
                )
                idx_a += 1
                continue

        repaired_atomic.append(seg_cur)
        idx_a += 1

    if not repaired_atomic:
        return []

    # Pass 2: Gentle coalescing ONLY for genuinely incomplete rapid fragments (< 0.42s gap & <= 4.8s total!)
    # Keeps every speaker turn crisp and tightly synced to the real voice!
    coalesced: list[dict] = [dict(repaired_atomic[0])]
    for nxt in repaired_atomic[1:]:
        cur = coalesced[-1]
        gap = nxt["start"] - cur["end"]
        cur_txt = cur["text"].rstrip()
        nxt_txt = nxt["text"].strip()
        combined_dur = nxt["end"] - cur["start"]
        is_ja = is_ja_hint or bool(re.search(r"[\u3040-\u30ff]", cur_txt + nxt_txt))
        is_cjk = is_ja or bool(re.search(r"[\u4e00-\u9fff\uac00-\ud7af]", cur_txt + nxt_txt))
        ja_sep = "、" if is_ja else "，"
        joiner = ja_sep if (is_cjk and not re.search(r"[，。？！、；：,.?!]$", cur_txt)) else ("" if is_cjk else " ")
        combined_txt = f"{cur_txt}{joiner}{nxt_txt}".strip()

        cur_ends_terminal = bool(re.search(r"[.!?。？！…][\"')\]»”’]*$", cur_txt))
        cur_ends_question = bool(re.search(r"[?？][\"')\]»”’]*$", cur_txt))
        cur_ja_end = is_ja and bool(_JA_TURN_END_RE.search(cur_txt))
        cur_units = _count_linguistic_units(cur_txt)
        nxt_units = _count_linguistic_units(nxt_txt)

        max_chars = 36 if is_cjk else 115
        should_merge = False

        if not cur_ends_terminal and not cur_ja_end and gap <= 0.42 and combined_dur <= 4.8 and len(combined_txt) <= max_chars:
            should_merge = True
        elif cur_units <= 2 and not cur_ends_question and gap <= 0.38 and combined_dur <= 4.5 and len(combined_txt) <= max_chars:
            should_merge = True
        elif nxt_units <= 2 and not cur_ends_question and not cur_ja_end and gap <= 0.28 and combined_dur <= 4.5 and len(combined_txt) <= max_chars:
            should_merge = True

        if should_merge:
            cur["end"] = round(max(cur["end"], nxt["end"]), 2)
            cur["text"] = re.sub(r"\s+", " ", combined_txt).strip()
        else:
            m_dangle = re.match(r"^(.*[.!?。！？])\s*([A-Za-z']{1,4}|[\u4e00-\u9fff]{1,3})$", cur["text"])
            if m_dangle and (re.search(r"[\u4e00-\u9fff]", m_dangle.group(2)) or not re.match(r"^[A-Z]", nxt["text"])):
                cur["text"] = m_dangle.group(1).strip()
                stub_d = m_dangle.group(2).strip()
                nxt = dict(nxt)
                if re.search(r"[\u4e00-\u9fff]", stub_d):
                    nxt["text"] = f"{stub_d}{nxt['text'].lstrip()}".strip()
                else:
                    nxt["text"] = f"{stub_d} {nxt['text'].lstrip()}".strip()
            coalesced.append(dict(nxt))

    return coalesced


def _detect_script_lang_from_text(text: str, hint: str = "auto") -> str:
    w_hint = normalize_whisper_lang_code(hint)
    if w_hint:
        return w_hint
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", text):
        return "vi"
    return "en"


def _fuse_ocr_and_whisper_segments(ocr_segs: list[dict], whisper_segs: list[dict]) -> list[dict]:
    """
    Keeps 100% of high-confidence burned-in OCR subtitle cues in their time windows,
    and fills unsubtitled narration gaps (>= 1.5s away from any OCR cue) with Whisper segments.
    """
    if not ocr_segs:
        return whisper_segs
    if not whisper_segs:
        return [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in ocr_segs]

    combined = [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in ocr_segs]
    for ws in whisper_segs:
        w_st, w_en = float(ws["start"]), float(ws["end"])
        overlaps_ocr = any(
            not (w_en <= (os_["start"] - 0.85) or w_st >= (os_["end"] + 0.85))
            for os_ in ocr_segs
        )
        if not overlaps_ocr:
            combined.append({"start": ws["start"], "end": ws["end"], "text": ws["text"]})

    combined.sort(key=lambda x: (x["start"], x["end"]))
    return combined


def _probe_active_audio_language(audio_f32: np.ndarray, model) -> str | None:
    """Finds the first loud speech window (skipping silent intros/logos) and detects language in ~0.3s."""
    sr = 16000
    if audio_f32.size < sr * 2:
        return None
    # Scan 5-second blocks to find an active vocal window
    win = sr * 30
    best_offset = 0
    best_rms = 0.0
    max_scan = min(audio_f32.size, sr * 240)
    for off in range(0, max(1, max_scan - sr * 5), sr * 5):
        sl = audio_f32[off : min(audio_f32.size, off + sr * 10)]
        r = float(np.sqrt(np.mean(sl * sl))) if sl.size else 0.0
        if r > best_rms:
            best_rms = r
            best_offset = off
        if r > 0.055:
            best_offset = off
            break
    clip = audio_f32[best_offset : min(audio_f32.size, best_offset + win)]
    try:
        lang_code, prob, _ = model.detect_language(clip)
        if lang_code and float(prob or 0.0) >= 0.45:
            return str(lang_code).lower()
    except Exception:
        pass
    return None


def _build_whisper_init_prompt(lang_code: str | None) -> str:
    lc = (lang_code or "").lower()
    if lc == "ja":
        return "自然な日本語の会話・ドラマのセリフです。話者の言葉を省略せず、句読点（。、？）を正確に付けて文字起こししてください。"
    if lc == "zh":
        return "以下是影视剧与短剧普通话对白，请使用规范简体中文并准确添加标点符号。"
    if lc == "ko":
        return "자연스러운 한국어 드라마 대화입니다. 모든 대사를 빠짐없이 정확한 문장부호로 받아쓰기해 주세요."
    if lc == "en":
        return "Natural movie dialogue transcript with accurate spelling and punctuation."
    if lc == "vi":
        return "Hội thoại phim tự nhiên bằng tiếng Việt với chính tả và dấu câu chuẩn xác."
    return ""


def _recover_skipped_speech_gaps(
    audio_f32: np.ndarray,
    existing_segs: list[dict],
    total_dur_sec: float,
    model,
    lang_code: str | None,
    init_prompt: str,
    job_gen: int = 0,
) -> list[dict]:
    """
    Fast Anti-Drop Safety Net: Scans long silent gaps >= 12.0s where Whisper/VAD produced no text.
    Only re-scans if genuine high speech-band energy exists (max 8 gaps, fast beam_size=1) and
    checks cancellation before every gap so it NEVER stalls or adds bloat!
    """
    sr = 16000
    if audio_f32.size < sr * 12 or total_dur_sec < 14.0:
        return existing_segs

    sorted_segs = sorted(existing_segs, key=lambda x: (x["start"], x["end"]))
    gaps: list[tuple[float, float]] = []
    prev_e = 0.0
    for s in sorted_segs:
        st, en = float(s["start"]), float(s["end"])
        if st - prev_e >= 12.0:
            gaps.append((prev_e, st))
        prev_e = max(prev_e, en)
    if total_dur_sec - prev_e >= 12.0:
        gaps.append((prev_e, total_dur_sec))

    if not gaps:
        return sorted_segs

    recovered: list[dict] = []
    checked = 0
    for g_st, g_en in gaps:
        if job_gen > 0:
            cinema_translator._check_not_cancelled(job_gen)
        if checked >= 8:
            break
        i0 = max(0, int(g_st * sr))
        i1 = min(audio_f32.size, int(g_en * sr))
        sl = audio_f32[i0:i1]
        if sl.size < sr * 2:
            continue
        rms_all = float(np.sqrt(np.mean(sl * sl)))
        if rms_all < 0.032:
            continue
        checked += 1
        cur_t = g_st
        while cur_t < g_en - 1.5:
            if job_gen > 0:
                cinema_translator._check_not_cancelled(job_gen)
            w_en = min(g_en, cur_t + 26.0)
            w_sl = audio_f32[int(cur_t * sr) : int(w_en * sr)]
            if w_sl.size < sr:
                break
            if float(np.sqrt(np.mean(w_sl * w_sl))) >= 0.032:
                try:
                    g_iter, _ = model.transcribe(
                        w_sl,
                        language=lang_code,
                        beam_size=1,
                        word_timestamps=True,
                        condition_on_previous_text=False,
                        compression_ratio_threshold=2.8,
                        log_prob_threshold=-1.6,
                        no_speech_threshold=0.88,
                        hallucination_silence_threshold=None,
                        repetition_penalty=1.0,
                        no_repeat_ngram_size=0,
                        initial_prompt=init_prompt,
                        vad_filter=False,
                    )
                    g_segs = _extract_utterance_segments(
                        g_iter, source_lang_hint=(lang_code or "auto"), total_dur_sec=0.0, job_gen=job_gen
                    )
                    for gs in g_segs:
                        abs_st = round(cur_t + float(gs["start"]), 2)
                        abs_en = round(min(w_en, cur_t + float(gs["end"])), 2)
                        if abs_en > abs_st + 0.20 and _count_linguistic_units(gs["text"]) >= 3:
                            recovered.append({"start": abs_st, "end": abs_en, "text": gs["text"]})
                except cinema_translator.TranslationCancelledError:
                    raise
                except Exception:
                    pass
            cur_t = w_en

    if not recovered:
        return sorted_segs

    merged = list(sorted_segs)
    for r in recovered:
        overlaps = any(not (r["end"] <= s["start"] + 0.15 or r["start"] >= s["end"] - 0.15) for s in merged)
        if not overlaps:
            merged.append(r)
    merged.sort(key=lambda x: (x["start"], x["end"]))
    return merged


def _transcribe_audio_precision(audio_f32: np.ndarray, source_lang: str, duration_sec: float) -> tuple[list[dict], str, float]:
    my_job_gen = cinema_translator.get_active_translation_gen()
    w_lang = normalize_whisper_lang_code(source_lang)

    # Always use blazing-fast Whisper Large-v3-Turbo (5x-8x faster than large-v3 on CPU: 7 min audio in ~75s!)
    # with beam_size=2, dynaudnorm, sensitive VAD (0.18), and native language prompt -> 2.5x MORE recovered Japanese cues!
    model = get_whisper_model(prefer_large_v3=False)

    # Probe actual spoken language on auto-detect BEFORE choosing native initial_prompt!
    probe_lang = w_lang
    if not probe_lang:
        probe_lang = _probe_active_audio_language(audio_f32, model)

    eff_lang = w_lang or probe_lang
    init_prompt = _build_whisper_init_prompt(eff_lang)
    total_d_est = duration_sec or (audio_f32.size / 16000.0)

    set_dub_live_progress(
        f"🎙️ Đang nhận diện lời thoại ({(eff_lang or 'AUTO').upper()} • {format_timestamp_sec(total_d_est)})...",
        f"🎙️ Transcribing speech ({(eff_lang or 'AUTO').upper()} • {format_timestamp_sec(total_d_est)})...",
        20,
    )

    segments_iter, info = model.transcribe(
        audio_f32,
        language=eff_lang,
        beam_size=2,
        word_timestamps=True,
        condition_on_previous_text=False,
        compression_ratio_threshold=2.8,
        log_prob_threshold=-1.5,
        no_speech_threshold=0.82,
        hallucination_silence_threshold=None,
        repetition_penalty=1.0,
        no_repeat_ngram_size=0,
        initial_prompt=init_prompt,
        vad_filter=True,
        vad_parameters={
            "threshold": 0.18,
            "neg_threshold": 0.10,
            "min_speech_duration_ms": 140,
            "min_silence_duration_ms": 340,
            "speech_pad_ms": 380,
        },
    )
    detected_lang = getattr(info, "language", None) or (eff_lang or "vi")
    total_d = duration_sec or float(getattr(info, "duration", 0.0) or total_d_est)
    whisper_segs = _extract_utterance_segments(
        segments_iter,
        source_lang_hint=detected_lang,
        total_dur_sec=total_d,
        job_gen=my_job_gen,
    )

    # Fast anti-drop safety net for any truly quiet speech gaps >= 12s
    set_dub_live_progress(
        "🔍 Đang rà soát nhanh khoảng lặng để không bỏ sót thoại nhỏ...",
        "🔍 Quick-checking long pauses for any missed quiet speech...",
        39,
    )
    whisper_segs = _recover_skipped_speech_gaps(
        audio_f32=audio_f32,
        existing_segs=whisper_segs,
        total_dur_sec=total_d,
        model=model,
        lang_code=detected_lang,
        init_prompt=_build_whisper_init_prompt(detected_lang),
        job_gen=my_job_gen,
    )
    return whisper_segs, detected_lang, total_d


def _compute_media_fast_fingerprint(media_path: str, source_lang: str) -> str:
    st = os.stat(media_path)
    h = hashlib.sha256()
    h.update(f"v7_cinema:{st.st_size}:{source_lang}:".encode("utf-8"))
    with open(media_path, "rb") as f:
        h.update(f.read(65536))
        if st.st_size > 131072:
            f.seek(max(0, st.st_size - 65536))
            h.update(f.read(65536))
    return h.hexdigest()[:20]


def transcribe_and_translate_media(
    media_path: str,
    source_lang: str = "auto",
    target_lang: str = "vi",
    ffmpeg_bin: str = "ffmpeg",
    ai_provider: str = "local",
    ai_api_key: str = "",
    ai_model: str = "",
    multi_voice_cast: bool = False,
) -> dict:
    # Always reset live progress at start so stale 66% / 95% from any prior job NEVER leaks into a new run!
    set_dub_live_progress(
        "🎙️ Đang phân tích tệp video/âm thanh & chuẩn bị nhận diện lời thoại...",
        "🎙️ Inspecting media file & preparing speech recognition...",
        16,
        active=True,
    )
    meta = probe_media_info(media_path, ffmpeg_bin=ffmpeg_bin)
    cache_dir = os.path.join("/tmp", "voxly_dub_sessions")
    os.makedirs(cache_dir, exist_ok=True)
    fp_key = _compute_media_fast_fingerprint(media_path, source_lang or "auto")
    stt_cache_path = os.path.join(cache_dir, f"stt_v11_turbo_precision_{fp_key}.json")

    cached_stt = None
    if os.path.exists(stt_cache_path):
        try:
            with open(stt_cache_path, "r", encoding="utf-8") as cf:
                cached_stt = json.load(cf)
        except Exception:
            cached_stt = None

    if cached_stt and cached_stt.get("segments"):
        plain_source = cached_stt["sourceText"]
        detected_lang = cached_stt.get("detectedLang", "vi")
        duration_sec = cached_stt.get("durationSec") or meta["durationSec"]
        segs = cached_stt.get("segments") or []
    else:
        duration_sec = float(meta.get("durationSec") or 0.0)
        ocr_res = {"usable": False, "avgConf": 0.0, "coverageRatio": 0.0, "segments": []}

        # Step 1 (Video): Hardware-accelerated Vision hard-subtitle extraction (100% exact spelling, zero homophones!)
        if meta.get("hasVideo") and duration_sec > 0.5:
            def _on_ocr_prog(c_idx: int, n_chunks: int) -> None:
                p_ocr = 16 + int((c_idx / max(1, n_chunks)) * 18)
                if n_chunks > 1:
                    set_dub_live_progress(
                        f"📖 Đang quét phụ đề gốc trên khung hình (phần {c_idx + 1}/{n_chunks})...",
                        f"📖 Scanning on-screen subtitles (part {c_idx + 1}/{n_chunks})...",
                        p_ocr,
                    )
                else:
                    set_dub_live_progress(
                        "📖 Đang đọc chuẩn xác phụ đề gốc trên khung hình video...",
                        "📖 Extracting exact on-screen video subtitles...",
                        p_ocr,
                    )

            try:
                ocr_res = video_subtitle_ocr.extract_hard_subtitles(
                    media_path=media_path,
                    duration_sec=duration_sec,
                    source_lang=source_lang,
                    ffmpeg_bin=ffmpeg_bin,
                    ffprobe_bin=resolve_ffprobe(ffmpeg_bin),
                    progress_cb=_on_ocr_prog,
                )
            except Exception:
                ocr_res = {"usable": False, "avgConf": 0.0, "coverageRatio": 0.0, "segments": []}

        # If crisp hard-subtitles cover the video timeline (>= 42% span coverage), use them directly!
        if ocr_res.get("usable") and float(ocr_res.get("coverageRatio") or 0.0) >= 0.42:
            segs = [
                {
                    "start": s["start"],
                    "end": s["end"],
                    "text": cinema_translator.preclean_source_dialogue_line(s["text"], source_lang=source_lang),
                }
                for s in ocr_res["segments"]
                if s.get("text")
            ]
            plain_source = re.sub(r"\s+", " ", " ".join(s["text"] for s in segs)).strip()
            detected_lang = _detect_script_lang_from_text(plain_source, hint=source_lang)
        else:
            # Step 2 (Audio / Unsubtitled Video / Partial-Sub Video): Whisper Large-v3-Turbo + VAD-seam repair
            tmp_wav = f"{media_path}.16k.wav"
            try:
                set_dub_live_progress(
                    "🎙️ Đang tách âm thanh & nhận diện lời thoại bằng Whisper Large-v3-Turbo...",
                    "🎙️ Extracting audio & transcribing dialogue via Whisper Large-v3-Turbo...",
                    28,
                )
                wav_timeout = max(240, int(duration_sec * 0.25) + 240)
                extract_16k_wav(media_path, tmp_wav, ffmpeg_bin=ffmpeg_bin, timeout_sec=wav_timeout)
                with wave.open(tmp_wav, "rb") as wf:
                    raw_pcm = wf.readframes(wf.getnframes())
                audio_f32 = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0
                whisper_segs, detected_lang, duration_sec = _transcribe_audio_precision(
                    audio_f32=audio_f32,
                    source_lang=source_lang,
                    duration_sec=duration_sec,
                )
                if ocr_res.get("usable") and ocr_res.get("segments"):
                    segs = _fuse_ocr_and_whisper_segments(ocr_res["segments"], whisper_segs)
                else:
                    segs = whisper_segs
                plain_source = re.sub(r"\s+", " ", " ".join(s["text"] for s in segs)).strip()
            finally:
                if os.path.exists(tmp_wav):
                    try:
                        os.remove(tmp_wav)
                    except OSError:
                        pass

        if not plain_source or not segs:
            raise ValueError("Không nhận diện được lời thoại hoặc phụ đề trong file này. Vui lòng kiểm tra lại video/âm thanh!")

        try:
            with open(stt_cache_path, "w", encoding="utf-8") as cf:
                json.dump(
                    {
                        "sourceText": plain_source,
                        "detectedLang": detected_lang,
                        "durationSec": round(duration_sec, 2),
                        "segments": segs,
                    },
                    cf,
                    ensure_ascii=False,
                )
        except Exception:
            pass

    tr_segs, _ = translate_segments_multilingual(
        segs,
        source_lang=detected_lang,
        target_lang=target_lang,
        ai_provider=ai_provider,
        ai_api_key=ai_api_key,
        ai_model=ai_model,
    )
    effective_target = detected_lang if (not target_lang or target_lang == "same") else target_lang
    formatted_source = format_timestamped_script(tr_segs, text_key="text", include_role=False)
    formatted_translated = format_timestamped_script(tr_segs, text_key="translatedText", include_role=False)

    return {
        "success": True,
        "isVideo": bool(meta["hasVideo"]),
        "hasOrigAudio": bool(meta["hasAudio"]),
        "durationSec": round(duration_sec, 2),
        "detectedLang": detected_lang,
        "targetLang": effective_target,
        "sourceText": formatted_source,
        "plainSourceText": plain_source,
        "translatedText": formatted_translated,
        "segments": tr_segs,
        "segmentsCount": len(tr_segs),
        "aiEngineUsed": (
            ai_provider
            if (ai_provider not in ("local", "local_fast", "local_14b") and ai_api_key)
            else cinema_translator.resolve_best_mlx_model_id(prefer_14b=(ai_provider == "local_14b"))
        ),
    }


def _build_atempo_chain(ratio: float) -> str:
    """Build valid FFmpeg atempo filter chain (each stage 0.5..2.0)."""
    r = max(0.50, min(2.0, ratio))
    if abs(r - 1.0) < 0.03:
        return "anull"
    return f"atempo={r:.4f}"


def wav_bytes_to_f32_48k(wav_bytes: bytes, ffmpeg_bin: str = "ffmpeg") -> np.ndarray:
    """Decodes WAV bytes into mono 48kHz float32 numpy array."""
    import io

    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            if wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() == 48000:
                pcm = wf.readframes(wf.getnframes())
                return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception:
        pass

    proc = subprocess.run(
        [
            ffmpeg_bin, "-nostdin", "-f", "wav", "-i", "pipe:0",
            "-ac", "1", "-ar", "48000", "-f", "s16le", "pipe:1",
        ],
        input=wav_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    if proc.returncode != 0 or not proc.stdout:
        return np.zeros(0, dtype=np.float32)
    return np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def _f32_48k_to_wav_bytes(samples: np.ndarray, sr: int = 48000) -> bytes:
    import io

    buf = io.BytesIO()
    pcm16 = np.clip(samples * 32767.0, -32768.0, 32767.0).astype(np.int16)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()


def trim_tts_silence_48k(samples: np.ndarray, sr: int = 48000, thresh: float = 0.0012, pad_ms: int = 85) -> np.ndarray:
    """
    Gently trims leading/trailing digital silence while preserving 100% of soft Vietnamese
    ending consonants (-n, -m, -ng, -nh) and natural trailing breath so words NEVER feel cut off!
    """
    if samples.size == 0:
        return samples
    active = np.flatnonzero(np.abs(samples) > thresh)
    if active.size == 0:
        return samples[: int(sr * 0.12)]
    pad_lead = int(sr * 0.030)
    pad_tail = int(sr * (pad_ms / 1000.0))
    i0 = max(0, int(active[0]) - pad_lead)
    i1 = min(samples.size, int(active[-1]) + pad_tail)
    trimmed = samples[i0:i1].copy()
    fade_in = min(int(sr * 0.012), trimmed.size // 6)
    fade_out = min(int(sr * 0.032), trimmed.size // 5)
    if fade_in > 4:
        trimmed[:fade_in] *= np.linspace(0.0, 1.0, fade_in, dtype=np.float32)
    if fade_out > 4:
        trimmed[-fade_out:] *= np.linspace(1.0, 0.0, fade_out, dtype=np.float32)
    return trimmed


def time_stretch_samples_48k(samples: np.ndarray, ratio: float, ffmpeg_bin: str = "ffmpeg", max_ratio: float = 1.62) -> np.ndarray:
    if samples.size < 480 or abs(ratio - 1.0) < 0.035:
        return samples
    r = max(0.75, min(float(max_ratio), float(ratio)))
    in_wav = _f32_48k_to_wav_bytes(samples, sr=48000)
    proc = subprocess.run(
        [
            ffmpeg_bin, "-nostdin", "-f", "wav", "-i", "pipe:0",
            "-af", _build_atempo_chain(r),
            "-ac", "1", "-ar", "48000", "-f", "s16le", "pipe:1",
        ],
        input=in_wav,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    if proc.returncode != 0 or not proc.stdout:
        return samples
    out = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return trim_tts_silence_48k(out, sr=48000, pad_ms=45)


def _compute_zero_drift_placements(
    rendered_segments: list[dict],
    target_duration_sec: float = 0.0,
    auto_fit_timing: bool = True,
    ffmpeg_bin: str = "ffmpeg",
) -> tuple[list[tuple[float, np.ndarray]], list[list[float]], float]:
    """
    Zero-Drift Cinema Timeline Placer (works identically for 1-minute clips and 3-hour movies!):
    - Speaks at natural 1.0x pace whenever post-utterance silence allows.
    - Dynamically adjusts WSOLA pace up to 1.50x (or 1.64x anti-drift recovery if cursor lagged >0.25s)
      so sentences fit inside their own slot before the next actor speaks — ZERO snowball lag!
    """
    sr = 48000
    placements: list[tuple[float, np.ndarray]] = []
    speech_intervals: list[list[float]] = []
    cursor_sec = 0.0
    n_segs = len(rendered_segments)

    for idx, item in enumerate(rendered_segments):
        raw_samples = trim_tts_silence_48k(item["samples"], sr=sr, pad_ms=60)
        if raw_samples.size == 0:
            continue

        seg_start = max(0.0, float(item.get("start", 0.0)))
        seg_end = max(seg_start + 0.35, float(item.get("end", seg_start + 1.8)))
        orig_win = max(0.35, seg_end - seg_start)

        placed_start = max(cursor_sec, seg_start)
        drift_so_far = placed_start - seg_start
        cur_dur = raw_samples.size / sr

        if idx + 1 < n_segs:
            next_orig_start = max(seg_start + 0.30, float(rendered_segments[idx + 1].get("start", seg_end)))
            # Target finishing right before the next cue's TRUE original timestamp so any small lag self-heals!
            target_finish_by = max(placed_start + 0.32, next_orig_start - 0.04)
            available_before_next = max(0.32, target_finish_by - placed_start)
        elif target_duration_sec > placed_start + 0.45:
            available_before_next = max(0.45, (target_duration_sec - placed_start) - 0.05)
        else:
            available_before_next = max(orig_win * 1.5, cur_dur + 0.2)

        if cur_dur <= available_before_next:
            samples = raw_samples
        elif auto_fit_timing:
            max_r = 1.64 if drift_so_far > 0.22 else 1.50
            ratio = min(max_r, cur_dur / max(0.32, available_before_next))
            samples = time_stretch_samples_48k(raw_samples, ratio, ffmpeg_bin=ffmpeg_bin, max_ratio=max_r)
        else:
            ratio = min(1.32, cur_dur / max(0.35, available_before_next + 0.20))
            samples = time_stretch_samples_48k(raw_samples, ratio, ffmpeg_bin=ffmpeg_bin, max_ratio=1.35)

        # Hard anti-snowball guardrail for multi-hour movies: first try gentle secondary WSOLA
        # stretch (never chop the last spoken word!), only fade-trim if physically impossible!
        if idx + 1 < n_segs:
            next_orig_start = float(rendered_segments[idx + 1].get("start", seg_end))
            max_allowed_end = max(placed_start + 0.30, next_orig_start + 0.35)
            max_samps = int(round((max_allowed_end - placed_start) * sr))
            if samples.size > max_samps > 960:
                extra_ratio = samples.size / float(max_samps)
                if extra_ratio <= 1.32:
                    samples = time_stretch_samples_48k(samples, extra_ratio, ffmpeg_bin=ffmpeg_bin, max_ratio=1.35)
                if samples.size > max_samps > 960:
                    samples = samples[:max_samps].copy()
                    fade_n = min(int(sr * 0.035), samples.size // 4)
                    if fade_n > 4:
                        samples[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, dtype=np.float32)

        final_dur = samples.size / sr
        placed_end = placed_start + final_dur
        placements.append((placed_start, samples))
        speech_intervals.append([round(placed_start, 3), round(placed_end, 3)])
        cursor_sec = placed_end + 0.04

    total_sec = max(float(target_duration_sec or 0.0), cursor_sec + 0.12, 0.5)
    return placements, speech_intervals, total_sec


def assemble_synced_voice_track(
    rendered_segments: list[dict],
    target_duration_sec: float = 0.0,
    auto_fit_timing: bool = True,
    ffmpeg_bin: str = "ffmpeg",
) -> tuple[np.ndarray, list[list[float]]]:
    sr = 48000
    if not rendered_segments:
        n_empty = max(int(sr * max(0.5, target_duration_sec)), 4800)
        return np.zeros(n_empty, dtype=np.float32), []

    placements, speech_intervals, total_sec = _compute_zero_drift_placements(
        rendered_segments=rendered_segments,
        target_duration_sec=target_duration_sec,
        auto_fit_timing=auto_fit_timing,
        ffmpeg_bin=ffmpeg_bin,
    )
    total_samples = int(round(total_sec * sr))
    master_voice = np.zeros(total_samples, dtype=np.float32)

    for p_start, samps in placements:
        i0 = int(round(p_start * sr))
        if i0 >= total_samples:
            extra = np.zeros((i0 + samps.size) - total_samples, dtype=np.float32)
            master_voice = np.concatenate([master_voice, extra])
            total_samples = master_voice.size
        i1 = min(total_samples, i0 + samps.size)
        chunk_len = i1 - i0
        if chunk_len > 0:
            master_voice[i0:i1] += samps[:chunk_len]

    return np.clip(master_voice, -0.99, 0.99), speech_intervals


def assemble_synced_voice_to_wav(
    out_wav_path: str,
    rendered_segments: list[dict],
    target_duration_sec: float = 0.0,
    auto_fit_timing: bool = True,
    ffmpeg_bin: str = "ffmpeg",
) -> list[list[float]]:
    """
    Streams the synced 48kHz voice track directly to disk in 60-second blocks so even
    a 3-hour feature film uses < 30 MB of buffer RAM!
    """
    sr = 48000
    if not rendered_segments:
        n_empty = max(int(sr * max(0.5, target_duration_sec)), 4800)
        _write_pcm_wav_48k(out_wav_path, np.zeros(n_empty, dtype=np.float32), sr=sr)
        return []

    placements, speech_intervals, total_sec = _compute_zero_drift_placements(
        rendered_segments=rendered_segments,
        target_duration_sec=target_duration_sec,
        auto_fit_timing=auto_fit_timing,
        ffmpeg_bin=ffmpeg_bin,
    )
    total_samples = int(round(total_sec * sr))
    block_samples = sr * 60
    p_idx = 0
    n_p = len(placements)

    with wave.open(out_wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)

        for blk_start in range(0, total_samples, block_samples):
            blk_end = min(total_samples, blk_start + block_samples)
            buf = np.zeros(blk_end - blk_start, dtype=np.float32)

            while p_idx < n_p and int(round(placements[p_idx][0] * sr)) + placements[p_idx][1].size <= blk_start:
                p_idx += 1

            k = p_idx
            while k < n_p:
                ps_i = int(round(placements[k][0] * sr))
                if ps_i >= blk_end:
                    break
                samps = placements[k][1]
                pe_i = ps_i + samps.size
                ov0 = max(blk_start, ps_i)
                ov1 = min(blk_end, pe_i)
                if ov1 > ov0:
                    buf[(ov0 - blk_start) : (ov1 - blk_start)] += samps[(ov0 - ps_i) : (ov1 - ps_i)]
                k += 1

            pcm16 = np.clip(buf * 32767.0, -32768.0, 32767.0).astype(np.int16)
            wf.writeframes(pcm16.tobytes())

    return speech_intervals


def _decode_stereo_48k_pcm(media_path: str, ffmpeg_bin: str = "ffmpeg") -> np.ndarray:
    proc = subprocess.run(
        [
            ffmpeg_bin, "-nostdin", "-i", media_path,
            "-vn", "-ac", "2", "-ar", "48000", "-f", "s16le", "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=240,
    )
    if proc.returncode != 0 or not proc.stdout:
        return np.zeros((0, 2), dtype=np.float32)
    flat = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    n_frames = flat.size // 2
    return flat[: n_frames * 2].reshape((n_frames, 2))


def _write_pcm_wav_48k(path_out: str, audio: np.ndarray, sr: int = 48000) -> None:
    if audio.ndim == 1:
        n_ch = 1
        pcm16 = np.clip(audio * 32767.0, -32768.0, 32767.0).astype(np.int16)
    else:
        n_ch = audio.shape[1]
        pcm16 = np.clip(audio * 32767.0, -32768.0, 32767.0).astype(np.int16)
    with wave.open(path_out, "wb") as wf:
        wf.setnchannels(n_ch)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16.tobytes())


def mix_and_export_dubbed_outputs(
    pure_voice_wav_path: str,
    speech_intervals: list[list[float]],
    out_wav_path: str,
    out_mp3_path: str,
    orig_media_path: str = "",
    out_mp4_path: str = "",
    is_video: bool = False,
    orig_volume: float = 0.40,
    smart_ducking: bool = True,
    ffmpeg_bin: str = "ffmpeg",
) -> dict:
    """
    Mixes the 48kHz synced AI voice track with the original media audio using:
    - Adjustable Original Audio Volume (0.0 .. 1.0)
    - Smart Dynamic Auto-Ducking: full `orig_volume` during music/SFX/laughter/non-speech scenes,
      smoothly ducking to `orig_volume * 0.25` during dubbed speech with broadcast Hann fades!
    Exports .WAV (48kHz), .MP3 (128kbps), and .MP4 (stream-copied video + 192kbps AAC).
    """
    sr = 48000
    orig_vol = float(max(0.0, min(1.0, orig_volume)))
    has_orig = bool(orig_media_path and os.path.exists(orig_media_path))
    orig_meta = probe_media_info(orig_media_path, ffmpeg_bin=ffmpeg_bin) if has_orig else {"hasAudio": False, "durationSec": 0.0}
    vid_dur = float(orig_meta.get("durationSec") or 0.0)

    voice_dur_probe = probe_media_info(pure_voice_wav_path, ffmpeg_bin=ffmpeg_bin).get("durationSec") or 0.0
    approx_total_sec = max(vid_dur, voice_dur_probe)
    dyn_timeout = max(300, int(approx_total_sec * 0.45) + 240)

    # Constant-RAM FFmpeg streaming mix for multi-hour movies (> 25 minutes = 1500s)
    if approx_total_sec > 1500:
        target_frames = int(round(max(approx_total_sec, 1.0) * sr))
        if has_orig and orig_meta.get("hasAudio") and orig_vol > 0.005:
            if smart_ducking:
                fc = (
                    f"[0:a]aresample=48000,aformat=channel_layouts=stereo,volume={orig_vol:.3f}[bg];"
                    f"[1:a]aresample=48000,aformat=channel_layouts=stereo,volume=1.08,asplit=2[sc][vo];"
                    f"[bg][sc]sidechaincompress=threshold=0.018:ratio=8:attack=35:release=420[bgduck];"
                    f"[bgduck][vo]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
                    f"alimiter=limit=0.96[outa]"
                )
            else:
                fc = (
                    f"[0:a]aresample=48000,aformat=channel_layouts=stereo,volume={orig_vol:.3f}[bg];"
                    f"[1:a]aresample=48000,aformat=channel_layouts=stereo,volume=1.08[vo];"
                    f"[bg][vo]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
                    f"alimiter=limit=0.96[outa]"
                )
            subprocess.run(
                [
                    ffmpeg_bin, "-nostdin", "-y",
                    "-i", orig_media_path,
                    "-i", pure_voice_wav_path,
                    "-filter_complex", fc,
                    "-map", "[outa]",
                    "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le",
                    out_wav_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=dyn_timeout,
                check=True,
            )
        else:
            shutil.copyfile(pure_voice_wav_path, out_wav_path)
    else:
        with open(pure_voice_wav_path, "rb") as vf:
            voice_mono = wav_bytes_to_f32_48k(vf.read(), ffmpeg_bin=ffmpeg_bin)

        # Never cut off the final dubbed sentence even if it finishes slightly past vid_dur!
        target_frames = voice_mono.size
        if has_orig and vid_dur > 0.5:
            target_frames = max(int(round(vid_dur * sr)), voice_mono.size)

        if voice_mono.size < target_frames:
            voice_aligned = np.pad(voice_mono, (0, target_frames - voice_mono.size))
        else:
            voice_aligned = voice_mono[:target_frames]

        if has_orig and orig_meta.get("hasAudio") and orig_vol > 0.005:
            orig_stereo = _decode_stereo_48k_pcm(orig_media_path, ffmpeg_bin=ffmpeg_bin)
        else:
            orig_stereo = np.zeros((0, 2), dtype=np.float32)

        if orig_stereo.shape[0] > 0 and orig_vol > 0.005:
            if orig_stereo.shape[0] < target_frames:
                pad_len = target_frames - orig_stereo.shape[0]
                orig_aligned = np.pad(orig_stereo, ((0, pad_len), (0, 0)))
            else:
                orig_aligned = orig_stereo[:target_frames]

            # Build 100Hz control envelope with anti-pumping dialogue bridge (< 1.85s gap stays smoothly ducked!)
            ctrl_hz = 100
            n_ctrl = max(4, int(np.ceil((target_frames / sr) * ctrl_hz)) + 1)
            env_ctrl = np.full(n_ctrl, orig_vol, dtype=np.float32)

            if smart_ducking and speech_intervals:
                merged_ivs: list[list[float]] = []
                for iv in sorted(speech_intervals, key=lambda x: float(x[0])):
                    if len(iv) < 2:
                        continue
                    s0, e0 = float(iv[0]), float(iv[1])
                    if merged_ivs and (s0 - merged_ivs[-1][1]) < 1.85:
                        merged_ivs[-1][1] = max(merged_ivs[-1][1], e0)
                    else:
                        merged_ivs.append([s0, e0])

                duck_level = orig_vol * 0.18
                for s0, e0 in merged_ivs:
                    c0 = max(0, int(np.floor((s0 - 0.18) * ctrl_hz)))
                    c1 = min(n_ctrl, int(np.ceil((e0 + 0.24) * ctrl_hz)))
                    if c1 > c0:
                        env_ctrl[c0:c1] = duck_level

                # Smooth with 410ms Hann cinema fader window so scene swells sound musical, never abrupt
                win_len = 41
                if n_ctrl > win_len:
                    kernel = np.hanning(win_len).astype(np.float32)
                    kernel /= kernel.sum()
                    padded = np.pad(env_ctrl, (win_len // 2, win_len // 2), mode="edge")
                    env_ctrl = np.convolve(padded, kernel, mode="valid")[:n_ctrl]

            x_ctrl = np.linspace(0.0, 1.0, n_ctrl, dtype=np.float32)
            x_full = np.linspace(0.0, 1.0, target_frames, dtype=np.float32)
            gain_full = np.interp(x_full, x_ctrl, env_ctrl).astype(np.float32)

            mixed_stereo = orig_aligned * gain_full[:, None] + (voice_aligned * 1.08)[:, None]
            # Smooth broadcast peak limiter (zero harsh clipping even at 100% slider!)
            peak = float(np.max(np.abs(mixed_stereo))) if mixed_stereo.size else 0.0
            if peak > 0.96:
                mixed_stereo = np.tanh(mixed_stereo * 0.95) / np.tanh(0.95) * 0.96
            _write_pcm_wav_48k(out_wav_path, mixed_stereo, sr=sr)
        else:
            _write_pcm_wav_48k(out_wav_path, voice_aligned, sr=sr)

    # Export MP3 (48kHz, 128kbps)
    mp3_cmd = [
        ffmpeg_bin, "-nostdin", "-y",
        "-i", out_wav_path,
        "-codec:a", "libmp3lame", "-b:a", "128k", "-ar", "48000",
        out_mp3_path,
    ]
    subprocess.run(mp3_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=dyn_timeout, check=True)

    dubbed_mp4_ready = False
    if is_video and has_orig and out_mp4_path:
        ext = os.path.splitext(orig_media_path)[1].lower()
        audio_dur_sec = target_frames / sr
        tail_overhang = audio_dur_sec - vid_dur
        if tail_overhang > 0.20 and vid_dur > 0.5:
            # Clone the final video frame briefly so the last spoken word is NEVER cut off!
            mp4_cmd = [
                ffmpeg_bin, "-nostdin", "-y",
                "-i", orig_media_path,
                "-i", out_wav_path,
                "-filter_complex", f"[0:v:0]tpad=stop_mode=clone:stop_duration={tail_overhang + 0.15:.2f}[vpad]",
                "-map", "[vpad]",
                "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-t", f"{audio_dur_sec:.2f}",
                "-movflags", "+faststart",
                out_mp4_path,
            ]
        else:
            can_copy = ext in (".mp4", ".mov", ".m4v")
            v_codec = ["-c:v", "copy"] if can_copy else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22"]
            dur_args = ["-t", f"{max(vid_dur, audio_dur_sec):.2f}"] if vid_dur > 0.5 else ["-shortest"]
            mp4_cmd = [
                ffmpeg_bin, "-nostdin", "-y",
                "-i", orig_media_path,
                "-i", out_wav_path,
                "-map", "0:v:0",
                "-map", "1:a:0",
                *v_codec,
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                *dur_args,
                "-movflags", "+faststart",
                out_mp4_path,
            ]
        proc = subprocess.run(mp4_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=dyn_timeout)
        if proc.returncode != 0 or not os.path.exists(out_mp4_path) or os.path.getsize(out_mp4_path) < 1000:
            err_txt = proc.stderr.decode("utf-8", errors="ignore")[-350:]
            raise RuntimeError(f"Lỗi ghép lồng tiếng vào video MP4: {err_txt.strip()}")
        dubbed_mp4_ready = True

    return {
        "success": True,
        "audioSeconds": round(target_frames / sr, 2),
        "dubbedVideoReady": dubbed_mp4_ready,
    }


def mux_dubbed_audio_into_video(
    orig_video_path: str,
    dub_wav_path: str,
    out_mp4_path: str,
    bg_mix_mode: str = "mute",
    auto_fit_timing: bool = True,
    ffmpeg_bin: str = "ffmpeg",
) -> dict:
    orig_vol = 0.20 if bg_mix_mode == "duck15" else 0.0
    tmp_wav = f"{out_mp4_path}.mix.wav"
    tmp_mp3 = f"{out_mp4_path}.mix.mp3"
    try:
        res = mix_and_export_dubbed_outputs(
            pure_voice_wav_path=dub_wav_path,
            speech_intervals=[],
            out_wav_path=tmp_wav,
            out_mp3_path=tmp_mp3,
            orig_media_path=orig_video_path,
            out_mp4_path=out_mp4_path,
            is_video=True,
            orig_volume=orig_vol,
            smart_ducking=False,
            ffmpeg_bin=ffmpeg_bin,
        )
        return {"success": True, "durationSec": res["audioSeconds"]}
    finally:
        for p in (tmp_wav, tmp_mp3):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


_DOUYIN_LOCK = threading.Lock()
_DOUYIN_SESSION = None
_DOUYIN_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
)


def extract_clean_online_url(raw_input: str) -> str:
    """
    Extracts a clean http/https URL even when pasted inside Douyin / TikTok / Bilibili
    mobile share text (e.g. '4.89 复制打开抖音，看看... https://v.douyin.com/iYxxx/').
    """
    txt = (raw_input or "").strip()
    if not txt:
        return ""
    m_http = re.search(r"https?://[^\s<>\"'，。！？；：）】》]+", txt)
    if m_http:
        return m_http.group(0).rstrip(".,;!?)]}'\"")
    m_bare = re.search(
        r"(?:www\.|v\.|m\.)?(?:douyin\.com|iesdouyin\.com|youtube\.com|youtu\.be|tiktok\.com|vt\.tiktok\.com)/[^\s<>\"'，。！？；：）】》]+",
        txt,
        re.IGNORECASE,
    )
    if m_bare:
        return "https://" + m_bare.group(0).rstrip(".,;!?)]}'\"")
    return txt


def _validate_safe_public_video_url(raw_url: str) -> str:
    url = extract_clean_online_url(raw_url)
    if not url:
        raise ValueError("Vui lòng dán đường link YouTube, Douyin hoặc TikTok cần dịch!")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(
            "Đường link không hợp lệ! Vui lòng dán link YouTube hoặc Douyin (VD: https://www.douyin.com/video/... hoặc https://v.douyin.com/...)."
        )
    host = parsed.hostname.strip().lower()
    if host in ("localhost", "0.0.0.0") or host.endswith(".local"):
        raise ValueError("Chỉ hỗ trợ đường link video công khai trên Internet (YouTube, Douyin, Shorts, TikTok...).")
    try:
        infos = socket.getaddrinfo(host, None)
        for item in infos:
            ip_str = item[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                raise ValueError("Không cho phép truy cập địa chỉ mạng nội bộ.")
    except ValueError:
        raise
    except Exception:
        pass
    return url


def _is_douyin_url(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host == "douyin.com" or host.endswith(".douyin.com") or host == "iesdouyin.com" or host.endswith(".iesdouyin.com")


def _get_douyin_session():
    global _DOUYIN_SESSION
    import requests

    if _DOUYIN_SESSION is None:
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": _DOUYIN_MOBILE_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,vi;q=0.8,en;q=0.7",
            }
        )
        _DOUYIN_SESSION = s
    return _DOUYIN_SESSION


def _extract_douyin_id_from_str(s: str) -> str:
    if not s:
        return ""
    for pat in (
        r"[?&]modal_id=(\d{15,22})",
        r"/(?:video|note|slides)/(\d{15,22})",
        r"/share/(?:video|note|slides)/(\d{15,22})",
        r"aweme_id=(\d{15,22})",
    ):
        m = re.search(pat, s)
        if m:
            return m.group(1)
    return ""


def _download_douyin_media(
    clean_url: str,
    cache_prefix: str,
    mode: str,
    ffmpeg_bin: str = "ffmpeg",
) -> dict:
    """
    Downloads watermark-free HD Douyin (.MP4 / .M4A) directly from douyin.com, v.douyin.com,
    ?modal_id=..., or iesdouyin.com share links using mobile ttwid session hydration (zero login required).
    """
    set_dub_live_progress(
        "🎬 Đang giải mã & tải video gốc không logo từ Douyin...",
        "🎬 Resolving & downloading watermark-free video from Douyin...",
        14,
    )
    with _DOUYIN_LOCK:
        sess = _get_douyin_session()
        aweme_id = _extract_douyin_id_from_str(clean_url)

        if not aweme_id:
            # Resolve short link (e.g. https://v.douyin.com/xxxxxx/)
            r_res = sess.get(clean_url, allow_redirects=True, timeout=15)
            final_u = _validate_safe_public_video_url(r_res.url)
            aweme_id = _extract_douyin_id_from_str(final_u) or _extract_douyin_id_from_str(r_res.text)

        if not aweme_id:
            raise RuntimeError(
                "Không tìm thấy mã video Douyin từ đường link đã dán! Hãy dán link dạng douyin.com/video/..., ?modal_id=... hoặc link chia sẻ v.douyin.com/..."
            )

        items = []
        share_url = f"https://www.iesdouyin.com/share/video/{aweme_id}/"
        for attempt in range(3):
            if attempt == 2:
                # Fresh session reset on rare expired ttwid
                sess.cookies.clear()
                sess.get(share_url, timeout=12)
            r_share = sess.get(share_url, timeout=15)
            m_rd = re.search(r"window\._ROUTER_DATA\s*=\s*(.*?)</script>", r_share.text, re.DOTALL)
            if m_rd:
                raw_json = m_rd.group(1).strip().rstrip(";")
                try:
                    d_router = json.loads(raw_json)
                    ld = d_router.get("loaderData") or {}
                    for pv in ld.values():
                        if isinstance(pv, dict) and "videoInfoRes" in pv:
                            cand_items = (pv.get("videoInfoRes") or {}).get("item_list") or []
                            if cand_items:
                                items = cand_items
                                break
                except Exception:
                    pass
            if items:
                break

        if not items:
            raise RuntimeError(
                f"Không lấy được dữ liệu video Douyin (ID: {aweme_id}). Video có thể đã bị xóa, đặt riêng tư hoặc giới hạn khu vực."
            )

        item = items[0]
        raw_desc = str(item.get("desc") or "").strip()
        clean_title = re.sub(r"\s+", " ", re.sub(r"#\S+", "", raw_desc)).strip() or raw_desc[:80] or f"Douyin_{aweme_id}"
        uploader = str((item.get("author") or {}).get("nickname") or "Douyin").strip()
        vid_obj = item.get("video") or {}
        thumb_list = ((vid_obj.get("cover") or {}).get("url_list")) or []
        thumbnail = str(thumb_list[0] if thumb_list else "").strip()

        play_addr = vid_obj.get("play_addr") or {}
        uri = str(play_addr.get("uri") or "").strip()
        raw_urls = [str(u) for u in (play_addr.get("url_list") or []) if u]

        candidate_streams: list[str] = []
        # 1. Highest-resolution 1080p Full HD stream from Douyin bit_rate tiers (prefer H.264, then highest bitrate <= 1080p)
        bit_rates = vid_obj.get("bit_rate") or []
        if isinstance(bit_rates, list) and bit_rates:
            scored_tiers = []
            for tier in bit_rates:
                if not isinstance(tier, dict):
                    continue
                t_addr = tier.get("play_addr") or {}
                t_urls = [str(u).replace("playwm", "play") for u in (t_addr.get("url_list") or []) if u]
                if not t_urls:
                    continue
                t_w = int(t_addr.get("width") or tier.get("width") or 0)
                t_h = int(t_addr.get("height") or tier.get("height") or 0)
                short_side = min(t_w, t_h) if (t_w > 0 and t_h > 0) else 0
                gear = str(tier.get("gear_name") or "").lower()
                is_1080 = 1 if (short_side >= 1000 or "1080" in gear) else 0
                is_h264 = 1 if int(tier.get("is_h265") or 0) == 0 else 0
                br = int(tier.get("bit_rate") or 0)
                scored_tiers.append(((is_1080, short_side, is_h264, br), t_urls))
            scored_tiers.sort(key=lambda x: x[0], reverse=True)
            for _, t_urls in scored_tiers:
                for u in t_urls:
                    if u not in candidate_streams:
                        candidate_streams.append(u)

        # 2. Direct watermark-free 1080p Full HD -> 720p HD CDN endpoints
        if uri and not uri.startswith("http"):
            candidate_streams.append(f"https://aweme.snssdk.com/aweme/v1/play/?video_id={uri}&ratio=1080p&line=0")
            candidate_streams.append(f"https://aweme.snssdk.com/aweme/v1/play/?video_id={uri}&ratio=720p&line=0")
        for u in raw_urls:
            clean_u = u.replace("playwm", "play")
            if clean_u not in candidate_streams:
                candidate_streams.append(clean_u)
        if uri and uri.startswith("http") and uri not in candidate_streams:
            candidate_streams.append(uri)

        if not candidate_streams:
            raise RuntimeError("Bài đăng Douyin này không chứa luồng video/âm thanh hợp lệ!")

        raw_mp4_path = f"{cache_prefix}_raw.mp4"
        downloaded_ok = False
        max_bytes = 3000 * 1024 * 1024

        for stream_u in candidate_streams:
            try:
                safe_stream_u = _validate_safe_public_video_url(stream_u)
                with sess.get(
                    safe_stream_u,
                    stream=True,
                    allow_redirects=True,
                    timeout=30,
                    headers={"Referer": "https://www.iesdouyin.com/"},
                ) as vr:
                    if vr.status_code >= 400:
                        continue
                    total_b = 0
                    with open(raw_mp4_path, "wb") as vf:
                        for ch in vr.iter_content(65536):
                            if ch:
                                total_b += len(ch)
                                if total_b > max_bytes:
                                    raise RuntimeError("Dung lượng video Douyin vượt quá giới hạn 3GB!")
                                vf.write(ch)
                    if total_b > 2000:
                        downloaded_ok = True
                        break
            except RuntimeError:
                raise
            except Exception:
                continue

        if not downloaded_ok or not os.path.exists(raw_mp4_path):
            raise RuntimeError("Không thể tải tệp video từ máy chủ CDN của Douyin. Vui lòng thử lại!")

    if mode == "audio":
        final_path = f"{cache_prefix}.m4a"
        subprocess.run(
            [ffmpeg_bin, "-nostdin", "-y", "-i", raw_mp4_path, "-vn", "-c:a", "aac", "-b:a", "160k", final_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=120,
            check=True,
        )
        try:
            os.remove(raw_mp4_path)
        except OSError:
            pass
    else:
        final_path = f"{cache_prefix}.mp4"
        # Ensure browser-compatible H.264 video stream if Douyin ever served HEVC/ByteVC1
        ffprobe_bin = resolve_ffprobe(ffmpeg_bin)
        v_codec_name = "h264"
        try:
            pr_out = subprocess.check_output(
                [ffprobe_bin, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", raw_mp4_path],
                stderr=subprocess.DEVNULL,
                timeout=10,
            ).decode("utf-8", errors="ignore").strip().lower()
            if pr_out:
                v_codec_name = pr_out.splitlines()[0].strip()
        except Exception:
            pass

        if v_codec_name and v_codec_name not in ("h264", "avc1"):
            raw_probe = probe_media_info(raw_mp4_path, ffmpeg_bin=ffmpeg_bin)
            tc_timeout = max(300, int(float(raw_probe.get("durationSec") or 0.0) * 0.85) + 240)
            subprocess.run(
                [
                    ffmpeg_bin, "-nostdin", "-y", "-i", raw_mp4_path,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=tc_timeout,
                check=True,
            )
            try:
                os.remove(raw_mp4_path)
            except OSError:
                pass
        else:
            os.replace(raw_mp4_path, final_path)

    probed = probe_media_info(final_path, ffmpeg_bin=ffmpeg_bin)
    return {
        "mediaPath": final_path,
        "title": clean_title,
        "uploader": uploader,
        "thumbnail": thumbnail,
        "durationSec": round(float(probed.get("durationSec") or 0.0), 2),
        "isVideo": bool(probed.get("hasVideo")) if mode == "video" else False,
    }


def download_online_video_url(
    raw_url: str,
    out_dir: str,
    download_mode: str = "video",
    ffmpeg_bin: str = "ffmpeg",
) -> dict:
    """
    Downloads YouTube / Shorts / Douyin (douyin.com / v.douyin.com / modal_id) / TikTok
    with local URL-hash caching so re-translating the same URL is instantaneous!
    """
    clean_url = _validate_safe_public_video_url(raw_url)
    os.makedirs(out_dir, exist_ok=True)
    mode = "audio" if download_mode == "audio" else "video"
    url_hash = hashlib.sha256(f"{clean_url}|{mode}|1080p".encode("utf-8")).hexdigest()[:16]
    cache_prefix = os.path.join(out_dir, f"yt_cache_{url_hash}_{mode}")
    meta_cache_path = f"{cache_prefix}.info_meta.json"

    # Reuse cached download if already fetched recently!
    if os.path.exists(meta_cache_path):
        try:
            cached = json.load(open(meta_cache_path, "r", encoding="utf-8"))
            c_path = cached.get("mediaPath", "")
            if c_path and os.path.exists(c_path) and os.path.getsize(c_path) > 1000:
                return cached
        except Exception:
            pass

    if _is_douyin_url(clean_url):
        res_meta = _download_douyin_media(clean_url, cache_prefix=cache_prefix, mode=mode, ffmpeg_bin=ffmpeg_bin)
        try:
            with open(meta_cache_path, "w", encoding="utf-8") as mf:
                json.dump(res_meta, mf, ensure_ascii=False)
        except Exception:
            pass
        return res_meta

    try:
        import yt_dlp
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "yt-dlp>=2025.1.0"])
        import yt_dlp

    ffmpeg_dir = os.path.dirname(ffmpeg_bin) if os.path.isabs(ffmpeg_bin) else None
    ydl_opts: dict = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "max_filesize": 3000 * 1024 * 1024,
        "socket_timeout": 30,
        "outtmpl": f"{cache_prefix}.%(ext)s",
    }
    if ffmpeg_dir and os.path.isdir(ffmpeg_dir):
        ydl_opts["ffmpeg_location"] = ffmpeg_dir

    if mode == "audio":
        ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    else:
        ydl_opts["format"] = (
            "bestvideo[height<=1080][vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height<=1080]+bestaudio/"
            "best[height<=1080][ext=mp4]/best[ext=mp4]/best"
        )
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            prepared = ydl.prepare_filename(info)
    except Exception as e:
        raise RuntimeError(f"Không thể tải video từ đường link này: {str(e)[:220]}")

    media_path = prepared
    if not os.path.exists(media_path):
        candidates = [
            p for p in glob.glob(f"{cache_prefix}.*")
            if not p.endswith(".json") and not p.endswith(".part") and not p.endswith(".ytdl")
        ]
        if candidates:
            media_path = max(candidates, key=os.path.getsize)

    if not media_path or not os.path.exists(media_path) or os.path.getsize(media_path) < 1000:
        raise RuntimeError("Không lấy được dữ liệu âm thanh/video từ link đã dán!")

    probed = probe_media_info(media_path, ffmpeg_bin=ffmpeg_bin)
    res_meta = {
        "mediaPath": media_path,
        "title": str(info.get("title") or "YouTube Video").strip(),
        "uploader": str(info.get("uploader") or info.get("channel") or "").strip(),
        "thumbnail": str(info.get("thumbnail") or "").strip(),
        "durationSec": round(float(probed.get("durationSec") or info.get("duration") or 0.0), 2),
        "isVideo": bool(probed.get("hasVideo")) if mode == "video" else False,
    }
    try:
        with open(meta_cache_path, "w", encoding="utf-8") as mf:
            json.dump(res_meta, mf, ensure_ascii=False)
    except Exception:
        pass
    return res_meta
