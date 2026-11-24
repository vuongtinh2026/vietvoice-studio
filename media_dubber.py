#!/usr/bin/env python3
"""
Voxly Studio — Multilingual Audio & Video Dubbing Engine
- Fast Offline Multilingual Speech-to-Text via faster-whisper (INT8 multi-core, 99 languages)
- Cross-Language Neural Text Translation (100+ languages, sentence-safe chunking)
- Instant FFmpeg .MP4 / .MOV / .WEBM Video Stream Re-Muxing (-c:v copy + smart atempo sync + audio ducking)
"""
import json
import os
import re
import shutil
import subprocess
import threading
import urllib.parse
import urllib.request
import wave

import numpy as np

_WHISPER_LOCK = threading.Lock()
_WHISPER_MODEL = None


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


def get_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL
    with _WHISPER_LOCK:
        if _WHISPER_MODEL is None:
            from faster_whisper import WhisperModel
            model_size = os.environ.get("VOXLY_WHISPER_MODEL", "base")
            whisper_cache = os.path.expanduser(
                f"~/.cache/huggingface/hub/models--Systran--faster-whisper-{model_size}/snapshots"
            )
            has_local = os.path.isdir(whisper_cache) and bool(os.listdir(whisper_cache))
            prev_offline = os.environ.get("HF_HUB_OFFLINE")
            if not has_local:
                os.environ["HF_HUB_OFFLINE"] = "0"
                try:
                    import huggingface_hub.constants as hf_const
                    hf_const.HF_HUB_OFFLINE = False
                except Exception:
                    pass
            try:
                _WHISPER_MODEL = WhisperModel(
                    model_size,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=4,
                    local_files_only=has_local,
                )
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


def extract_16k_wav(media_path: str, out_wav_path: str, ffmpeg_bin: str = "ffmpeg") -> None:
    cmd = [
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
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=180)
    if proc.returncode != 0 or not os.path.exists(out_wav_path) or os.path.getsize(out_wav_path) < 200:
        err_txt = proc.stderr.decode("utf-8", errors="ignore")[-300:]
        raise RuntimeError(f"Không thể tách âm thanh từ file tải lên ({err_txt.strip() or 'FFmpeg error'}).")


def normalize_whisper_lang_code(lang: str) -> str | None:
    if not lang or lang in ("auto", "detect", ""):
        return None
    base = lang.split("-")[0].split("_")[0].lower().strip()
    return base or None


def normalize_translate_lang_code(lang: str) -> str:
    if not lang:
        return "vi"
    clean = lang.strip()
    lower = clean.lower()
    if lower in ("zh", "zh-cn", "zh-hans", "cmn"):
        return "zh-CN"
    if lower in ("zh-tw", "zh-hk", "zh-hant", "yue"):
        return "zh-TW"
    return clean.split("-")[0].lower()


def _translate_single_chunk_gtx(chunk: str, source_lang: str, target_lang: str) -> tuple[str, str]:
    sl = "auto" if not source_lang or source_lang == "auto" else normalize_translate_lang_code(source_lang)
    tl = normalize_translate_lang_code(target_lang)
    if sl != "auto" and sl.lower() == tl.lower():
        return chunk, sl

    params = urllib.parse.urlencode({"client": "gtx", "sl": sl, "tl": tl, "dt": "t", "q": chunk})
    url = f"https://translate.googleapis.com/translate_a/single?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        },
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    pieces = []
    if isinstance(data, list) and data and isinstance(data[0], list):
        for seg in data[0]:
            if isinstance(seg, list) and seg and seg[0]:
                pieces.append(str(seg[0]))
    detected = data[2] if isinstance(data, list) and len(data) > 2 and isinstance(data[2], str) else sl
    return "".join(pieces).strip(), detected


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

    # Split into <= 1600-char sentence-preserving chunks so long videos translate cleanly
    sentences = re.findall(r"[^.!?\n。？！]+(?:[.!?\n。？！]+|$)", raw) or [raw]
    chunks: list[str] = []
    cur = ""
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        if len(cur) + len(s_clean) + 1 <= 1600:
            cur = f"{cur} {s_clean}".strip() if cur else s_clean
        else:
            if cur:
                chunks.append(cur)
            cur = s_clean
    if cur:
        chunks.append(cur)

    translated_parts: list[str] = []
    detected_final = sl_norm
    for ch in chunks:
        tr, det = _translate_single_chunk_gtx(ch, sl_norm, tl_norm)
        translated_parts.append(tr or ch)
        if det and detected_final == "auto":
            detected_final = det

    return " ".join(translated_parts).strip(), detected_final


def transcribe_and_translate_media(
    media_path: str,
    source_lang: str = "auto",
    target_lang: str = "vi",
    ffmpeg_bin: str = "ffmpeg",
) -> dict:
    meta = probe_media_info(media_path, ffmpeg_bin=ffmpeg_bin)
    tmp_wav = f"{media_path}.16k.wav"
    try:
        extract_16k_wav(media_path, tmp_wav, ffmpeg_bin=ffmpeg_bin)
        with wave.open(tmp_wav, "rb") as wf:
            raw_pcm = wf.readframes(wf.getnframes())
        audio_f32 = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0
        model = get_whisper_model()
        w_lang = normalize_whisper_lang_code(source_lang)
        segments_iter, info = model.transcribe(
            audio_f32,
            language=w_lang,
            beam_size=2,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 350},
        )
        segs = []
        texts = []
        for seg in segments_iter:
            t = (seg.text or "").strip()
            if t:
                segs.append(
                    {
                        "start": round(float(seg.start), 2),
                        "end": round(float(seg.end), 2),
                        "text": t,
                    }
                )
                texts.append(t)

        full_source = re.sub(r"\s+", " ", " ".join(texts)).strip()
        detected_lang = getattr(info, "language", None) or (w_lang or "vi")
        duration_sec = meta["durationSec"] or float(getattr(info, "duration", 0.0) or 0.0)

        if not full_source:
            raise ValueError("Không nhận diện được giọng nói trong file này. Vui lòng kiểm tra lại âm lượng file!")

        if not target_lang or target_lang == "same":
            translated = full_source
            effective_target = detected_lang
        else:
            translated, _ = translate_text_multilingual(
                full_source,
                source_lang=detected_lang,
                target_lang=target_lang,
            )
            effective_target = target_lang

        return {
            "success": True,
            "isVideo": bool(meta["hasVideo"]),
            "durationSec": round(duration_sec, 2),
            "detectedLang": detected_lang,
            "targetLang": effective_target,
            "sourceText": full_source,
            "translatedText": translated,
            "segments": segs,
            "segmentsCount": len(segs),
        }
    finally:
        if os.path.exists(tmp_wav):
            try:
                os.remove(tmp_wav)
            except OSError:
                pass


def _build_atempo_chain(ratio: float) -> str:
    """Build valid FFmpeg atempo filter chain (each stage 0.5..2.0)."""
    r = max(0.50, min(2.0, ratio))
    if abs(r - 1.0) < 0.03:
        return "anull"
    return f"atempo={r:.4f}"


def mux_dubbed_audio_into_video(
    orig_video_path: str,
    dub_wav_path: str,
    out_mp4_path: str,
    bg_mix_mode: str = "mute",
    auto_fit_timing: bool = True,
    ffmpeg_bin: str = "ffmpeg",
) -> dict:
    v_meta = probe_media_info(orig_video_path, ffmpeg_bin=ffmpeg_bin)
    a_meta = probe_media_info(dub_wav_path, ffmpeg_bin=ffmpeg_bin)
    vid_dur = v_meta.get("durationSec") or 0.0
    dub_dur = a_meta.get("durationSec") or 0.0

    # Gently match speech pace if dubbed audio is slightly longer/shorter than original video (0.78x..1.38x)
    atempo_filter = "anull"
    if auto_fit_timing and vid_dur > 1.0 and dub_dur > 1.0:
        ratio = dub_dur / vid_dur
        if 0.78 <= ratio <= 1.38 and abs(ratio - 1.0) >= 0.04:
            atempo_filter = _build_atempo_chain(ratio)
        elif ratio > 1.38:
            atempo_filter = _build_atempo_chain(1.38)

    ext = os.path.splitext(orig_video_path)[1].lower()
    can_stream_copy_video = ext in (".mp4", ".mov", ".m4v")
    v_codec_args = ["-c:v", "copy"] if can_stream_copy_video else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22"]

    if bg_mix_mode == "duck15" and v_meta.get("hasAudio"):
        # Keep 15% original ambient sound mixed with 100% crisp 48kHz dubbed voice!
        fc = (
            f"[0:a]aresample=48000,volume=0.15[bg];"
            f"[1:a]aresample=48000,{atempo_filter},apad,volume=1.05[dub];"
            f"[bg][dub]amix=inputs=2:duration=first:dropout_transition=0[aout]"
        )
        cmd = [
            ffmpeg_bin, "-nostdin", "-y",
            "-i", orig_video_path,
            "-i", dub_wav_path,
            "-filter_complex", fc,
            "-map", "0:v:0",
            "-map", "[aout]",
            *v_codec_args,
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
            "-movflags", "+faststart",
            out_mp4_path,
        ]
    else:
        # 100% clean voice replacement, padded with silence or trimmed neatly to video end
        af = f"aresample=48000,{atempo_filter},apad"
        dur_args = ["-t", f"{vid_dur:.2f}"] if vid_dur > 0.5 else ["-shortest"]
        cmd = [
            ffmpeg_bin, "-nostdin", "-y",
            "-i", orig_video_path,
            "-i", dub_wav_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            *v_codec_args,
            "-af", af,
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
            *dur_args,
            "-movflags", "+faststart",
            out_mp4_path,
        ]

    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=240)
    if proc.returncode != 0 or not os.path.exists(out_mp4_path) or os.path.getsize(out_mp4_path) < 1000:
        err_txt = proc.stderr.decode("utf-8", errors="ignore")[-350:]
        raise RuntimeError(f"Lỗi ghép lồng tiếng vào video MP4: {err_txt.strip()}")

    out_meta = probe_media_info(out_mp4_path, ffmpeg_bin=ffmpeg_bin)
    return {"success": True, "durationSec": round(out_meta.get("durationSec") or vid_dur, 2)}
