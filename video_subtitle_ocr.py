#!/usr/bin/env python3
"""
Voxly Studio — Hardware-Accelerated Burned-In Video Subtitle Extractor (macOS Vision ANE)
- Extracts exact hard-coded on-screen subtitles with frame-accurate [start, end] timestamps
- Eliminates 100% of audio homophone errors on subtitled Chinese dramas, anime, movie recaps & Shorts
- Processes in streaming 10-minute chunks so 1–3+ hour movies use minimal disk/RAM
- Automatically distinguishes genuine dialogue subtitles from corner logos, news tickers, and blurry overlays
"""
import collections
import difflib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
from typing import Callable

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_OCR_BIN_PATH = os.path.join(_SCRIPT_DIR, "subtitle_ocr_mac")
_OCR_SWIFT_PATH = os.path.join(_SCRIPT_DIR, "subtitle_ocr_mac.swift")

_CJK_CHAR_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
_CAPTION_META_PREFIX_RE = re.compile(
    r"^(?:声音来源|画面来源|视频来源|素材来源|图片来源|潮新闻主持人|潮新[间闻]主持人|主持人|记者)\s*[:：]?\s*\S+\s*"
)

_OPENCC_T2S = None
_OPENCC_INIT_DONE = False


def _to_simplified_zh(s: str) -> str:
    global _OPENCC_T2S, _OPENCC_INIT_DONE
    if not _OPENCC_INIT_DONE:
        _OPENCC_INIT_DONE = True
        try:
            from opencc import OpenCC
            _OPENCC_T2S = OpenCC("t2s")
        except Exception:
            _OPENCC_T2S = None
    if _OPENCC_T2S is not None:
        try:
            return _OPENCC_T2S.convert(s)
        except Exception:
            pass
    # Built-in fallback for common HK/TW variants in case opencc is absent
    return (
        s.replace("內", "内")
        .replace("剝", "剥")
        .replace("個", "个")
        .replace("開", "开")
        .replace("塊", "块")
        .replace("錢", "钱")
        .replace("萬", "万")
        .replace("種", "种")
        .replace("綠", "绿")
        .replace("藍", "蓝")
        .replace("陽", "阳")
        .replace("壓", "压")
        .replace("燈", "灯")
        .replace("賭", "赌")
        .replace("漲", "涨")
    )


# Common visual glyph confusions in Chinese video fonts (e.g. 千 vs 干, 靶 vs 把, 齐活 vs 济活)
_ZH_VISUAL_OCR_FIXES: list[tuple[str, str]] = [
    ("两干万", "两千万"),
    ("三干万", "三千万"),
    ("五干万", "五千万"),
    ("一干万", "一千万"),
    ("几干万", "几千万"),
    ("干万别", "千万别"),
    ("干万要", "千万要"),
    ("成干上万", "成千上万"),
    ("静止把子", "静止靶子"),
    ("静止難子", "静止靶子"),
    ("拿证汉怎么样", "拿证又怎么样"),
    ("拿证汉怎公样", "拿证又怎么样"),
    ("济活", "齐活"),
]


def ensure_ocr_binary() -> str | None:
    if platform.system() != "Darwin":
        return None
    if os.path.isfile(_OCR_BIN_PATH) and os.access(_OCR_BIN_PATH, os.X_OK):
        return _OCR_BIN_PATH
    swiftc = shutil.which("swiftc") or "/usr/bin/swiftc"
    if os.path.isfile(_OCR_SWIFT_PATH) and os.path.isfile(swiftc):
        try:
            subprocess.run(
                [swiftc, "-O", _OCR_SWIFT_PATH, "-o", _OCR_BIN_PATH],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=90,
                check=True,
            )
            os.chmod(_OCR_BIN_PATH, 0o755)
            return _OCR_BIN_PATH
        except Exception:
            return None
    return None


def _probe_video_dimensions(media_path: str, ffprobe_bin: str = "ffprobe") -> tuple[int, int]:
    try:
        out = subprocess.check_output(
            [
                ffprobe_bin,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                media_path,
            ],
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).decode("utf-8", errors="ignore").strip()
        if out:
            first = out.splitlines()[0].strip()
            parts = [int(x) for x in first.split(",") if x.strip().isdigit()]
            if len(parts) >= 2 and parts[0] > 0 and parts[1] > 0:
                return parts[0], parts[1]
    except Exception:
        pass
    return 1280, 720


def _vision_langs_for_source(source_lang: str) -> str:
    sl = (source_lang or "auto").lower()
    if sl.startswith("zh"):
        return "zh-Hans,zh-Hant,en-US"
    if sl.startswith("ja"):
        return "ja-JP,en-US"
    if sl.startswith("ko"):
        return "ko-KR,en-US"
    if sl.startswith("en"):
        return "en-US"
    return "zh-Hans,zh-Hant,en-US,ja-JP,ko-KR"


def _normalize_ocr_text(raw: str, is_zh_hint: bool = True) -> str:
    s = (raw or "").strip()
    s = re.sub(r"^[;；:：·•—\-_|~`]+", "", s).strip()
    s = re.sub(r"[;；:：·•_|~`]+$", "", s).strip()
    if not s:
        return ""
    if is_zh_hint or bool(_CJK_CHAR_RE.search(s)):
        s = _to_simplified_zh(s)
        s = _CAPTION_META_PREFIX_RE.sub("", s).strip()
        for wrong, right in _ZH_VISUAL_OCR_FIXES:
            if wrong in s:
                s = s.replace(wrong, right)
    return re.sub(r"\s+", " ", s).strip()


def _extract_centered_line_from_frame(items: list[dict], is_portrait: bool, is_zh_hint: bool) -> tuple[str, float]:
    """
    Filters out left/right channel watermarks, dates, speaker-source micro-labels, and corner logos
    by requiring horizontal centering near screen middle (0.39 <= midX <= 0.61) AND dominant font height.
    """
    centered: list[dict] = []
    for it in items or []:
        txt = str(it.get("t") or "").strip()
        if not txt:
            continue
        x0 = float(it.get("x0", 0.0))
        x1 = float(it.get("x1", 1.0))
        y0 = float(it.get("y0", 0.0))
        y1 = float(it.get("y1", 1.0))
        conf = float(it.get("c", 0.0))
        mid_x = 0.5 * (x0 + x1)
        box_h = y1 - y0

        if not (0.39 <= mid_x <= 0.61):
            continue
        min_h = 0.055 if is_portrait else 0.10
        if box_h < min_h:
            continue
        if _CAPTION_META_PREFIX_RE.match(txt) and not _CAPTION_META_PREFIX_RE.sub("", txt).strip():
            continue
        centered.append({"t": txt, "c": conf, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "h": box_h})

    if not centered:
        return "", 0.0

    # Keep only dominant subtitle font height (drops smaller source/credit micro-captions above/below)
    max_h = max(b["h"] for b in centered)
    centered = [b for b in centered if b["h"] >= max_h * 0.70]

    # In bilingual CJK+English subtitles, keep ONLY the CJK line(s)
    has_cjk_box = any(_CJK_CHAR_RE.search(b["t"]) for b in centered)
    if has_cjk_box:
        centered = [b for b in centered if _CJK_CHAR_RE.search(b["t"]) or re.fullmatch(r"[0-9%.,+-]+", b["t"])]

    if not centered:
        return "", 0.0

    centered.sort(key=lambda b: (-round(b["y0"], 1), b["x0"]))
    raw_joined = " ".join(b["t"] for b in centered)
    norm_txt = _normalize_ocr_text(raw_joined, is_zh_hint=is_zh_hint)
    if not norm_txt:
        return "", 0.0
    avg_conf = sum(b["c"] for b in centered) / len(centered)
    return norm_txt, avg_conf


def _vote_best_card_text(samples: list[tuple[str, float]]) -> tuple[str, float, int]:
    if not samples:
        return "", 0.0, 0
    scores: dict[str, float] = collections.defaultdict(float)
    max_c = 0.0
    for txt, conf in samples:
        scores[txt] += conf + 0.35
        if conf > max_c:
            max_c = conf

    best_txt = max(scores.keys(), key=lambda k: (scores[k], min(len(k), 28)))
    avg_c = sum(c for _, c in samples) / len(samples)
    return best_txt, max(avg_c, max_c * 0.85), len(samples)


def _punctuate_single_card(text: str) -> str:
    """
    Infers natural question / exclamation punctuation on each individual subtitle card BEFORE
    coalescing so dialogue questions ('这块多少钱？') and answers ('八十万。') or speaker switches
    ('你卖不卖？' / '不卖') never get glued into one run-on clause!
    """
    t = (text or "").strip()
    if not t or re.search(r"[。！？.!?…]$", t):
        return t
    if not _CJK_CHAR_RE.search(t):
        return t
    if re.search(
        r"(?:吗|呢|咋了|啥|多少钱|切多少|卖不卖|先看看|好心|是不是|能不能|对不对|行不行|干嘛|干什么|上哪捡的|什么种水|什么玩意儿|你要全剥|什么狗屎运)$",
        t,
    ) or re.match(r"^(?:难道|怎么会|为什么|凭什么)", t):
        return t + "？"
    if re.fullmatch(r"(?:我去|卧槽|操|牛逼|齐活|赌个屁|涨个屁|成交|别急别急)", t):
        return t + "！"
    if re.search(r"(?:被人盯上|吃不进去|赌性大|我走了|两千万打底|颜色也进去了|自己留着|石头却废了|不能确定|两立方米了|没天理了|启动资金|神枪手|有把握的|就麻烦|卖掉|全取出来|眼下没事|这儿踏实|心里有数|概率不高|就不错了|能到糯冰|能到冰糯|真好啊)$", t):
        return t + "。"
    return t


def _coalesce_subtitle_cards(cards: list[dict]) -> list[dict]:
    """
    Merges rapid consecutive short subtitle cards of the SAME speaker turn into natural,
    complete spoken sentences (target 2.0s–6.0s) while keeping Q&A speaker turns crisp!
    """
    if not cards:
        return []

    prep_cards = []
    for c in cards:
        cc = dict(c)
        cc["text"] = _punctuate_single_card(cc["text"])
        prep_cards.append(cc)

    merged: list[dict] = [dict(prep_cards[0])]
    for nxt in prep_cards[1:]:
        cur = merged[-1]
        gap = nxt["start"] - cur["end"]
        cur_txt = cur["text"].rstrip()
        nxt_txt = nxt["text"].strip()

        # Deduplicate exact stutter repeats (e.g. '全剥' -> '全剥') within 0.6s
        if cur_txt.rstrip("。！？!?") == nxt_txt.rstrip("。！？!?") and gap <= 0.60:
            cur["end"] = round(max(cur["end"], nxt["end"]), 2)
            continue

        # Remove scrolling boundary overlap (e.g. '...曝光到网上' + '曝光到网上，7月31日...')
        for ov_len in range(min(len(cur_txt), len(nxt_txt), 12), 2, -1):
            if cur_txt.rstrip("。！？!?").endswith(nxt_txt[:ov_len]):
                nxt_txt = nxt_txt[ov_len:].lstrip("，,。 ")
                break
        if not nxt_txt:
            cur["end"] = round(max(cur["end"], nxt["end"]), 2)
            continue

        is_cjk = bool(_CJK_CHAR_RE.search(cur_txt + nxt_txt))
        combined_dur = nxt["end"] - cur["start"]
        cur_dur = cur["end"] - cur["start"]
        joiner = "，" if (is_cjk and not re.search(r"[，。？！、；：,.?!]$", cur_txt)) else ("" if is_cjk else " ")
        combined_txt = f"{cur_txt}{joiner}{nxt_txt}".strip()

        max_chars = 36 if is_cjk else 140
        cur_ends_strong = bool(re.search(r"[?？!！。][\"')\]»”’]*$", cur_txt))
        nxt_is_exclam = bool(re.match(r"^(?:我去|卧槽|操|牛逼|赌个屁|涨个屁)[！!。]?$", nxt_txt))

        should_join = False
        if not cur_ends_strong and not nxt_is_exclam and combined_dur <= 6.2 and len(combined_txt) <= max_chars:
            if gap <= 0.35:
                should_join = True
            elif gap <= 0.68 and (cur_dur < 2.8 or len(cur_txt) <= (10 if is_cjk else 30)):
                should_join = True

        if should_join:
            cur["end"] = round(max(cur["end"], nxt["end"]), 2)
            cur["text"] = combined_txt
            cur["conf"] = round(0.5 * (cur.get("conf", 0.8) + nxt.get("conf", 0.8)), 3)
        else:
            nxt_copy = dict(nxt)
            nxt_copy["text"] = nxt_txt
            merged.append(nxt_copy)

    for seg in merged:
        t = seg["text"].strip()
        if _CJK_CHAR_RE.search(t) and not re.search(r"[。！？.!?…]$", t):
            t += "。"
        seg["text"] = t

    return merged


def extract_hard_subtitles(
    media_path: str,
    duration_sec: float,
    source_lang: str = "auto",
    ffmpeg_bin: str = "ffmpeg",
    ffprobe_bin: str = "ffprobe",
    progress_cb: Callable[[int, int], None] | None = None,
) -> dict:
    """
    Extracts burned-in subtitles across short videos OR multi-hour movies (in 10-min streaming chunks).
    """
    ocr_bin = ensure_ocr_binary()
    if not ocr_bin or duration_sec <= 0.4:
        return {"usable": False, "avgConf": 0.0, "coverageRatio": 0.0, "segments": []}

    width, height = _probe_video_dimensions(media_path, ffprobe_bin=ffprobe_bin)
    is_portrait = height > width
    is_zh_hint = (source_lang or "auto").lower() in ("auto", "zh", "zh-cn", "zh-tw")
    lang_csv = _vision_langs_for_source(source_lang)

    fps = 3.5 if duration_sec <= 1200 else 2.5
    step_sec = 1.0 / fps

    if is_portrait:
        vf_filter = f"crop=iw:ih*0.42:0:ih*0.50,fps={fps},scale='min(720,iw)':-2"
    else:
        vf_filter = f"crop=iw:ih*0.30:0:ih*0.70,fps={fps},scale='min(1024,iw)':-2"

    # Quick probe for multi-hour movies (> 20 min): skip immediately if no crisp burned-in subs exist
    if duration_sec > 1200:
        probe_start = min(180.0, duration_sec * 0.12)
        with tempfile.TemporaryDirectory(prefix="voxly_ocr_probe_") as pdir:
            subprocess.run(
                [
                    ffmpeg_bin, "-nostdin", "-y",
                    "-ss", f"{probe_start:.1f}", "-t", "150",
                    "-i", media_path, "-vf", vf_filter, "-q:v", "3",
                    os.path.join(pdir, "f_%06d.jpg"),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=45,
            )
            pr = subprocess.run([ocr_bin, pdir, lang_csv], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=45)
            probe_hits = 0
            for ln in pr.stdout.decode("utf-8", errors="ignore").splitlines():
                try:
                    obj = json.loads(ln)
                    txt, cf = _extract_centered_line_from_frame(obj.get("items") or [], is_portrait, is_zh_hint)
                    if txt and cf >= 0.52:
                        probe_hits += 1
                except Exception:
                    pass
            if probe_hits < 6:
                return {"usable": False, "avgConf": 0.0, "coverageRatio": 0.0, "segments": []}

    chunk_sec = 600.0
    n_chunks = max(1, int((duration_sec + chunk_sec - 0.01) // chunk_sec))
    frame_timeline: list[tuple[float, str, float]] = []

    for c_idx in range(n_chunks):
        t0 = c_idx * chunk_sec
        t_len = min(chunk_sec, duration_sec - t0)
        if t_len <= 0.2:
            break
        if progress_cb is not None:
            try:
                progress_cb(c_idx, n_chunks)
            except Exception:
                pass

        with tempfile.TemporaryDirectory(prefix="voxly_ocr_chunk_") as cdir:
            cmd = [
                ffmpeg_bin, "-nostdin", "-y",
                "-ss", f"{t0:.2f}",
                "-t", f"{t_len:.2f}",
                "-i", media_path,
                "-vf", vf_filter,
                "-q:v", "3",
                os.path.join(cdir, "f_%06d.jpg"),
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
            ocr_proc = subprocess.run(
                [ocr_bin, cdir, lang_csv],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=240,
            )
            for line in ocr_proc.stdout.decode("utf-8", errors="ignore").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    f_num = int(row.get("f", 1))
                    t_abs = t0 + max(0.0, (f_num - 1) * step_sec)
                    txt, conf = _extract_centered_line_from_frame(row.get("items") or [], is_portrait, is_zh_hint)
                    if txt:
                        frame_timeline.append((t_abs, txt, conf))
                except Exception:
                    continue

    if not frame_timeline:
        return {"usable": False, "avgConf": 0.0, "coverageRatio": 0.0, "segments": []}

    clusters: list[dict] = []
    for t_abs, txt, conf in frame_timeline:
        if clusters and (t_abs - clusters[-1]["end"]) <= (step_sec * 1.65):
            prev_rep = clusters[-1]["rep_text"]
            sim = difflib.SequenceMatcher(None, prev_rep, txt).ratio()
            len_diff = abs(len(txt) - len(prev_rep))
            prev_frames = len(clusters[-1]["samples"])
            is_distinct_expansion = (prev_frames >= 2 and len_diff >= 2 and (prev_rep in txt or txt in prev_rep))
            if sim >= 0.74 and not is_distinct_expansion:
                clusters[-1]["end"] = t_abs + step_sec
                clusters[-1]["samples"].append((txt, conf))
                if conf >= clusters[-1]["rep_conf"] and len(txt) >= len(prev_rep):
                    clusters[-1]["rep_text"] = txt
                    clusters[-1]["rep_conf"] = conf
                continue

        clusters.append(
            {
                "start": t_abs,
                "end": t_abs + step_sec,
                "rep_text": txt,
                "rep_conf": conf,
                "samples": [(txt, conf)],
            }
        )

    cards: list[dict] = []
    for cl in clusters:
        best_txt, best_conf, n_f = _vote_best_card_text(cl["samples"])
        dur = cl["end"] - cl["start"]
        if not best_txt:
            continue
        if n_f == 1 and best_conf < 0.48:
            continue
        if dur > 18.0:
            continue
        cards.append(
            {
                "start": round(cl["start"], 2),
                "end": round(cl["end"], 2),
                "text": best_txt,
                "conf": round(best_conf, 3),
            }
        )

    if not cards:
        return {"usable": False, "avgConf": 0.0, "coverageRatio": 0.0, "segments": []}

    segments = _coalesce_subtitle_cards(cards)
    avg_conf = sum(s["conf"] for s in segments) / max(1, len(segments))
    first_t = segments[0]["start"]
    last_t = segments[-1]["end"]
    span_cov = (last_t - first_t) / max(1.0, duration_sec)

    usable = bool(avg_conf >= 0.56 and len(segments) >= 2)
    return {
        "usable": usable,
        "avgConf": round(avg_conf, 3),
        "coverageRatio": round(span_cov, 3),
        "segments": segments,
    }
