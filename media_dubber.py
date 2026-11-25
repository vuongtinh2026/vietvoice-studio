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
import urllib.error
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


_TS_LINE_RE = re.compile(r"^\s*\[(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*-\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]\s*(.*)$")


def format_timestamped_script(segments: list[dict], text_key: str = "text") -> str:
    lines: list[str] = []
    for seg in segments or []:
        txt = re.sub(r"\s+", " ", str(seg.get(text_key) or seg.get("text") or "")).strip()
        if not txt:
            continue
        st = format_timestamp_sec(seg.get("start", 0.0))
        en = format_timestamp_sec(seg.get("end", 0.0))
        lines.append(f"[{st} - {en}] {txt}")
    return "\n".join(lines)


def parse_timestamped_script(raw_script: str) -> tuple[list[dict], str, bool]:
    """
    Parses `[mm:ss.d - mm:ss.d] Spoken line` lines into structured segments.
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
            txt = m.group(3).strip()
            if txt:
                parsed.append({"start": st, "end": en, "text": txt})
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
) -> tuple[list[dict], str]:
    """Translates utterance segments 1-to-1 while preserving exact [start, end] timestamps."""
    if not segments:
        return [], source_lang or "auto"

    if not target_lang or target_lang == "same":
        out = [{**s, "translatedText": s.get("text", "")} for s in segments]
        return out, source_lang or "auto"

    sl_norm = normalize_translate_lang_code(source_lang) if source_lang and source_lang != "auto" else "auto"
    tl_norm = normalize_translate_lang_code(target_lang)
    if sl_norm != "auto" and sl_norm.lower() == tl_norm.lower():
        out = [{**s, "translatedText": s.get("text", "")} for s in segments]
        return out, sl_norm

    # Group into safe <=700-char line batches for fast 1-to-1 newline-preserved POST translation
    batches: list[list[int]] = []
    cur_batch: list[int] = []
    cur_len = 0
    for idx, seg in enumerate(segments):
        t = re.sub(r"\s+", " ", str(seg.get("text", ""))).strip()
        if cur_batch and (len(cur_batch) >= 8 or cur_len + len(t) + 2 > 700):
            batches.append(cur_batch)
            cur_batch = []
            cur_len = 0
        cur_batch.append(idx)
        cur_len += len(t) + 2
    if cur_batch:
        batches.append(cur_batch)

    translated_map: dict[int, str] = {}
    detected_holder = [sl_norm]

    def _run_batch(idxs: list[int]) -> None:
        src_lines = [re.sub(r"\s+", " ", str(segments[i].get("text", ""))).strip() for i in idxs]
        joined = "\n".join(src_lines)
        tr_joined, det = _translate_single_chunk_gtx(joined, sl_norm, tl_norm)
        if det and det != "auto":
            detected_holder[0] = det
        out_lines = [ln.strip() for ln in (tr_joined or "").split("\n") if ln.strip()]
        if len(out_lines) == len(idxs):
            for k, seg_idx in enumerate(idxs):
                translated_map[seg_idx] = out_lines[k]
        else:
            # Strict per-segment fallback guarantees 100% 1-to-1 timestamp alignment!
            for k, seg_idx in enumerate(idxs):
                tr_one, det_one = _translate_single_chunk_gtx(src_lines[k], sl_norm, tl_norm)
                if det_one and det_one != "auto":
                    detected_holder[0] = det_one
                translated_map[seg_idx] = (tr_one or src_lines[k]).strip()

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, max(1, len(batches)))) as pool:
        list(pool.map(_run_batch, batches))

    enriched = []
    for i, seg in enumerate(segments):
        enriched.append(
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "translatedText": translated_map.get(i, seg["text"]),
            }
        )
    return enriched, detected_holder[0]


def translate_script_preserving_timestamps(
    raw_text: str,
    source_lang: str = "auto",
    target_lang: str = "vi",
) -> tuple[str, str]:
    segs, plain, has_ts = parse_timestamped_script(raw_text)
    if has_ts and segs:
        tr_segs, det = translate_segments_multilingual(segs, source_lang=source_lang, target_lang=target_lang)
        return format_timestamped_script(tr_segs, text_key="translatedText"), det
    return translate_text_multilingual(plain, source_lang=source_lang, target_lang=target_lang)


def _extract_utterance_segments(segments_iter) -> list[dict]:
    """
    Uses word-level timestamps (with segment fallback) to capture exact speech start/end
    and split naturally across pauses >= 0.55s so intro music, laughter & scene pauses stay clean!
    """
    words_flat: list[dict] = []
    fallback_segs: list[dict] = []

    for seg in segments_iter:
        t = (seg.text or "").strip()
        if t:
            fallback_segs.append(
                {
                    "start": round(float(seg.start), 2),
                    "end": round(max(float(seg.end), float(seg.start) + 0.25), 2),
                    "text": t,
                }
            )
        seg_words = getattr(seg, "words", None)
        if seg_words:
            for w in seg_words:
                wt = (getattr(w, "word", "") or "")
                if wt.strip():
                    words_flat.append(
                        {
                            "start": float(w.start),
                            "end": max(float(w.end), float(w.start) + 0.06),
                            "word": wt,
                        }
                    )

    if not words_flat:
        return fallback_segs

    utterances: list[dict] = []
    cur_words: list[str] = []
    cur_start = 0.0
    cur_end = 0.0

    def _flush():
        nonlocal cur_words, cur_start, cur_end
        if not cur_words:
            return
        txt = re.sub(r"\s+", " ", "".join(cur_words)).strip()
        if txt:
            utterances.append(
                {
                    "start": round(max(0.0, cur_start), 2),
                    "end": round(max(cur_start + 0.25, cur_end), 2),
                    "text": txt,
                }
            )
        cur_words = []

    for item in words_flat:
        ws, we, wd = item["start"], item["end"], item["word"]
        if not cur_words:
            cur_start = ws
            cur_end = we
            cur_words = [wd]
            continue

        gap = ws - cur_end
        dur = cur_end - cur_start
        prev_txt = "".join(cur_words).rstrip()
        ends_sent = bool(re.search(r"[.!?。？！…][\"')\]»”’]*$", prev_txt))
        ends_clause = bool(re.search(r"[,;:，；：—\-]$", prev_txt))
        char_len = len(prev_txt)

        should_split = (
            gap >= 0.55
            or (ends_sent and (gap >= 0.18 or dur >= 2.0 or char_len >= 45))
            or (dur >= 7.5 and (ends_clause or gap >= 0.22))
            or dur >= 12.0
            or char_len >= 190
        )
        if should_split:
            _flush()
            cur_start = ws
            cur_end = we
            cur_words = [wd]
        else:
            cur_end = max(cur_end, we)
            cur_words.append(wd)

    _flush()
    return utterances if utterances else fallback_segs


def _compute_media_fast_fingerprint(media_path: str, source_lang: str) -> str:
    st = os.stat(media_path)
    h = hashlib.sha256()
    h.update(f"v2:{st.st_size}:{source_lang}:".encode("utf-8"))
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
) -> dict:
    meta = probe_media_info(media_path, ffmpeg_bin=ffmpeg_bin)
    cache_dir = os.path.join("/tmp", "voxly_dub_sessions")
    os.makedirs(cache_dir, exist_ok=True)
    fp_key = _compute_media_fast_fingerprint(media_path, source_lang or "auto")
    stt_cache_path = os.path.join(cache_dir, f"stt_v2_{fp_key}.json")

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
                word_timestamps=True,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 280, "speech_pad_ms": 120},
            )
            segs = _extract_utterance_segments(segments_iter)
            plain_source = re.sub(r"\s+", " ", " ".join(s["text"] for s in segs)).strip()
            detected_lang = getattr(info, "language", None) or (w_lang or "vi")
            duration_sec = meta["durationSec"] or float(getattr(info, "duration", 0.0) or 0.0)

            if not plain_source or not segs:
                raise ValueError("Không nhận diện được giọng nói trong file này. Vui lòng kiểm tra lại âm lượng file!")

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
        finally:
            if os.path.exists(tmp_wav):
                try:
                    os.remove(tmp_wav)
                except OSError:
                    pass

    tr_segs, _ = translate_segments_multilingual(
        segs,
        source_lang=detected_lang,
        target_lang=target_lang,
    )
    effective_target = detected_lang if (not target_lang or target_lang == "same") else target_lang
    formatted_source = format_timestamped_script(tr_segs, text_key="text")
    formatted_translated = format_timestamped_script(tr_segs, text_key="translatedText")

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


def trim_tts_silence_48k(samples: np.ndarray, sr: int = 48000, thresh: float = 0.0045, pad_ms: int = 26) -> np.ndarray:
    if samples.size == 0:
        return samples
    active = np.flatnonzero(np.abs(samples) > thresh)
    if active.size == 0:
        return samples[: int(sr * 0.1)]
    pad = int(sr * (pad_ms / 1000.0))
    i0 = max(0, int(active[0]) - pad)
    i1 = min(samples.size, int(active[-1]) + pad)
    trimmed = samples[i0:i1].copy()
    fade = min(int(sr * 0.010), trimmed.size // 4)
    if fade > 4:
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        trimmed[:fade] *= ramp
        trimmed[-fade:] *= ramp[::-1]
    return trimmed


def time_stretch_samples_48k(samples: np.ndarray, ratio: float, ffmpeg_bin: str = "ffmpeg") -> np.ndarray:
    if samples.size < 480 or abs(ratio - 1.0) < 0.035:
        return samples
    r = max(0.65, min(1.65, float(ratio)))
    in_wav = _f32_48k_to_wav_bytes(samples, sr=48000)
    proc = subprocess.run(
        [
            ffmpeg_bin, "-nostdin", "-f", "wav", "-i", "pipe:0",
            "-af", f"atempo={r:.4f}",
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
    return trim_tts_silence_48k(out, sr=48000, pad_ms=16)


def assemble_synced_voice_track(
    rendered_segments: list[dict],
    target_duration_sec: float = 0.0,
    auto_fit_timing: bool = True,
    ffmpeg_bin: str = "ffmpeg",
) -> tuple[np.ndarray, list[list[float]]]:
    """
    Places each synthesized segment at its exact [start, end] cue on a 48kHz timeline!
    Automatically adjusts per-segment pace (up to 1.55x) so lines fit their dialogue windows
    without overlapping or leaving the rest of the video silent.
    """
    sr = 48000
    if not rendered_segments:
        n_empty = max(int(sr * max(0.5, target_duration_sec)), 4800)
        return np.zeros(n_empty, dtype=np.float32), []

    placements: list[tuple[float, np.ndarray]] = []
    speech_intervals: list[list[float]] = []
    cursor_sec = 0.0
    n_segs = len(rendered_segments)

    for idx, item in enumerate(rendered_segments):
        raw_samples = trim_tts_silence_48k(item["samples"], sr=sr)
        if raw_samples.size == 0:
            continue

        seg_start = max(0.0, float(item.get("start", 0.0)))
        seg_end = max(seg_start + 0.30, float(item.get("end", seg_start + 1.5)))
        orig_win = max(0.35, seg_end - seg_start)

        placed_start = max(cursor_sec, seg_start)

        if idx + 1 < n_segs:
            next_cue = max(placed_start + 0.35, float(rendered_segments[idx + 1].get("start", seg_end)))
            hard_slot = max(0.35, next_cue - placed_start - 0.05)
        elif target_duration_sec > placed_start + 0.35:
            hard_slot = max(0.35, target_duration_sec - placed_start - 0.04)
        else:
            hard_slot = max(orig_win * 1.4, raw_samples.size / sr)

        soft_slot = min(hard_slot, max(orig_win * 1.22, orig_win + 0.55))
        cur_dur = raw_samples.size / sr

        if auto_fit_timing and cur_dur > soft_slot + 0.06:
            desired_slot = min(hard_slot, max(orig_win * 1.08, soft_slot * 0.96))
            ratio = min(1.55, cur_dur / max(0.30, desired_slot))
            samples = time_stretch_samples_48k(raw_samples, ratio, ffmpeg_bin=ffmpeg_bin)
        elif cur_dur > hard_slot + 0.08:
            ratio = min(1.50, cur_dur / max(0.30, hard_slot))
            samples = time_stretch_samples_48k(raw_samples, ratio, ffmpeg_bin=ffmpeg_bin)
        else:
            samples = raw_samples

        final_dur = samples.size / sr
        placed_end = placed_start + final_dur
        placements.append((placed_start, samples))
        speech_intervals.append([round(placed_start, 3), round(placed_end, 3)])
        cursor_sec = placed_end + 0.04

    total_sec = max(float(target_duration_sec or 0.0), cursor_sec + 0.15, 0.5)
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
    with open(pure_voice_wav_path, "rb") as vf:
        voice_mono = wav_bytes_to_f32_48k(vf.read(), ffmpeg_bin=ffmpeg_bin)

    orig_vol = float(max(0.0, min(1.0, orig_volume)))
    has_orig = bool(orig_media_path and os.path.exists(orig_media_path))
    orig_meta = probe_media_info(orig_media_path, ffmpeg_bin=ffmpeg_bin) if has_orig else {"hasAudio": False, "durationSec": 0.0}
    vid_dur = float(orig_meta.get("durationSec") or 0.0)

    target_frames = voice_mono.size
    if is_video and vid_dur > 0.5:
        target_frames = max(int(round(vid_dur * sr)), 1)
    elif has_orig and vid_dur > 0.5:
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

        # Build 100Hz control envelope for smooth fader automation
        ctrl_hz = 100
        n_ctrl = max(4, int(np.ceil((target_frames / sr) * ctrl_hz)) + 1)
        env_ctrl = np.full(n_ctrl, orig_vol, dtype=np.float32)

        if smart_ducking and speech_intervals:
            duck_level = orig_vol * 0.24
            for iv in speech_intervals:
                if len(iv) >= 2:
                    c0 = max(0, int(np.floor((float(iv[0]) - 0.12) * ctrl_hz)))
                    c1 = min(n_ctrl, int(np.ceil((float(iv[1]) + 0.16) * ctrl_hz)))
                    if c1 > c0:
                        env_ctrl[c0:c1] = duck_level

            # Smooth with 260ms Hann fader window so transitions sound natural & musical
            win_len = 27
            if n_ctrl > win_len:
                kernel = np.hanning(win_len).astype(np.float32)
                kernel /= kernel.sum()
                padded = np.pad(env_ctrl, (win_len // 2, win_len // 2), mode="edge")
                env_ctrl = np.convolve(padded, kernel, mode="valid")[:n_ctrl]

        x_ctrl = np.linspace(0.0, 1.0, n_ctrl, dtype=np.float32)
        x_full = np.linspace(0.0, 1.0, target_frames, dtype=np.float32)
        gain_full = np.interp(x_full, x_ctrl, env_ctrl).astype(np.float32)

        mixed_stereo = orig_aligned * gain_full[:, None] + (voice_aligned * 1.06)[:, None]
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
    subprocess.run(mp3_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=180, check=True)

    dubbed_mp4_ready = False
    if is_video and has_orig and out_mp4_path:
        ext = os.path.splitext(orig_media_path)[1].lower()
        can_copy = ext in (".mp4", ".mov", ".m4v")
        v_codec = ["-c:v", "copy"] if can_copy else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22"]
        dur_args = ["-t", f"{vid_dur:.2f}"] if vid_dur > 0.5 else ["-shortest"]
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
        proc = subprocess.run(mp4_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=240)
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


def _validate_safe_public_video_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if not url:
        raise ValueError("Vui lòng dán đường link YouTube hoặc video cần dịch!")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Đường link không hợp lệ! Vui lòng dán link bắt đầu bằng https:// (VD: https://www.youtube.com/watch?v=...).")
    host = parsed.hostname.strip().lower()
    if host in ("localhost", "0.0.0.0") or host.endswith(".local"):
        raise ValueError("Chỉ hỗ trợ đường link video công khai trên Internet (YouTube, Shorts, TikTok, Vimeo...).")
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


def download_online_video_url(
    raw_url: str,
    out_dir: str,
    download_mode: str = "video",
    ffmpeg_bin: str = "ffmpeg",
) -> dict:
    """
    Downloads YouTube / Shorts / TikTok / public online video or audio via yt-dlp
    with local URL-hash caching so re-translating the same URL is instantaneous!
    """
    clean_url = _validate_safe_public_video_url(raw_url)
    os.makedirs(out_dir, exist_ok=True)
    mode = "audio" if download_mode == "audio" else "video"
    url_hash = hashlib.sha256(f"{clean_url}|{mode}".encode("utf-8")).hexdigest()[:16]
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
        "max_filesize": 260 * 1024 * 1024,
        "socket_timeout": 20,
        "outtmpl": f"{cache_prefix}.%(ext)s",
    }
    if ffmpeg_dir and os.path.isdir(ffmpeg_dir):
        ydl_opts["ffmpeg_location"] = ffmpeg_dir

    if mode == "audio":
        ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    else:
        ydl_opts["format"] = (
            "bestvideo[height<=720][vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/"
            "best[height<=720][ext=mp4]/best[ext=mp4]/best"
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
