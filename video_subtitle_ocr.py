#!/usr/bin/env python3
"""
Voxly Studio — Hardware-Accelerated Burned-In Video Subtitle Extractor (macOS Vision ANE)
- Auto-locks onto the exact Dominant Subtitle Y-Band across the video, 100% rejecting floating
  cursive channel watermarks (e.g. '笼包动画'), top/side logos, news credits, and bilingual sub-lines!
- Processes in streaming 10-minute chunks so 1–5+ hour feature films use minimal disk/RAM (< 20 MB).
- Confidence-weighted majority voting across frames + Chinese glyph typo normalization.
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

import audio_speaker_analyzer

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_OCR_BIN_PATH = os.path.join(_SCRIPT_DIR, "subtitle_ocr_mac")
_OCR_SWIFT_PATH = os.path.join(_SCRIPT_DIR, "subtitle_ocr_mac.swift")

_CJK_CHAR_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
_CAPTION_META_PREFIX_RE = re.compile(
    r"^(?:声音来源|画面来源|视频来源|素材来源|图片来源|潮新闻主持人|潮新[间闻]主持人|主持人|记者)\s*[:：]?\s*\S+\s*"
)
_WATERMARK_NOISE_RE = re.compile(
    r"^(?:笼包动画|缆包动[潋画]|然包外道|包补途|笼包补鱼|公红补鱼|笼纱补|特包茶|袋包制|签包制险|笼包|包)$"
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


# Common visual glyph confusions in Chinese video subtitles (both OCR and sub-creator typos)
_ZH_VISUAL_OCR_FIXES: list[tuple[str, str]] = [
    ("两干万", "两千万"),
    ("三干万", "三千万"),
    ("五干万", "五千万"),
    ("一干万", "一千万"),
    ("几干万", "几千万"),
    ("三干多", "三千多"),
    ("五干多", "五千多"),
    ("几干", "几千"),
    ("干万别", "千万别"),
    ("干万要", "千万要"),
    ("成干上万", "成千上万"),
    ("静止把子", "静止靶子"),
    ("静止難子", "静止靶子"),
    ("拿证汉怎么样", "拿证又怎么样"),
    ("拿证汉怎公样", "拿证又怎么样"),
    ("济活", "齐活"),
    # Xianxia / drama visual glyph confusions
    ("筑基七重镜", "筑基七重境"),
    ("重镜", "重境"),
    ("井且", "并且"),
    ("特珠血脉", "特殊血脉"),
    ("宗问", "宗门"),
    ("藏金闾", "藏经阁"),
    ("藏金阁", "藏经阁"),
    ("平乎无奇", "平平无奇"),
    ("影装", "影袭"),
    ("帝玄龟", "地玄龟"),
    ("在外散生", "在外散修"),
    ("按下来的话", "接下来的话"),
    ("佳手你们想千什么", "住手你们想干什么"),
    ("想千什么", "想干什么"),
    ("佳手", "住手"),
    ("悲悯佛仔", "悲悯佛祖"),
    ("几于空白", "近乎空白"),
    ("那一首可把", "那一手可把"),
    ("买— 头", "买一头"),
    ("买—头", "买一头"),
    ("天天折了", "天夭折了"),
    ("独霜一方", "独霸一方"),
    ("这杰功法", "这本功法"),
    ("的修力", "的修为"),
    ("苟力先", "苟为先"),
    ("让你是收下", "让你收下"),
    ("苏阎主", "苏阁主"),
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
    s = re.sub(r"^[;；:：·•—\-_|~`()（）]+", "", s).strip()
    s = re.sub(r"[;；:：·•_|~`]+$", "", s).strip()
    if not s:
        return ""
    if is_zh_hint or bool(_CJK_CHAR_RE.search(s)):
        s = _to_simplified_zh(s)
        s = _CAPTION_META_PREFIX_RE.sub("", s).strip()
        for wrong, right in _ZH_VISUAL_OCR_FIXES:
            if wrong in s:
                s = s.replace(wrong, right)
    s = re.sub(r"\s+", " ", s).strip()
    if _WATERMARK_NOISE_RE.match(s):
        return ""
    return s


def _extract_candidate_rows_from_frame(items: list[dict], is_portrait: bool, is_zh_hint: bool) -> list[dict]:
    """
    Groups horizontally-centered OCR boxes into distinct vertical rows WITHOUT ever merging
    two vertically separated bands (e.g. a floating channel watermark above vs. the real subtitle below!).
    """
    boxes: list[dict] = []
    min_h = 0.055 if is_portrait else 0.14
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
        mid_y = 0.5 * (y0 + y1)
        box_h = y1 - y0

        if not (0.38 <= mid_x <= 0.62):
            continue
        if box_h < min_h:
            continue
        # Reject blurry cursive watermark ghost detections (almost always conf < 0.42)
        if conf < 0.42:
            continue
        boxes.append({"t": txt, "c": conf, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "mid_y": mid_y, "h": box_h})

    if not boxes:
        return []

    # Cluster boxes into vertical rows (same line if |mid_y difference| <= 0.14)
    boxes.sort(key=lambda b: (b["mid_y"], b["x0"]))
    rows_raw: list[list[dict]] = []
    for b in boxes:
        if rows_raw and abs(b["mid_y"] - rows_raw[-1][0]["mid_y"]) <= 0.14:
            rows_raw[-1].append(b)
        else:
            rows_raw.append([b])

    out_rows: list[dict] = []
    for grp in rows_raw:
        grp.sort(key=lambda b: b["x0"])
        raw_joined = " ".join(b["t"] for b in grp)
        norm_txt = _normalize_ocr_text(raw_joined, is_zh_hint=is_zh_hint)
        if not norm_txt:
            continue
        avg_y = sum(b["mid_y"] for b in grp) / len(grp)
        avg_c = sum(b["c"] for b in grp) / len(grp)
        avg_h = sum(b["h"] for b in grp) / len(grp)
        has_cjk = bool(_CJK_CHAR_RE.search(norm_txt))
        out_rows.append(
            {
                "text": norm_txt,
                "conf": avg_c,
                "mid_y": avg_y,
                "h": avg_h,
                "has_cjk": has_cjk,
            }
        )
    return out_rows


def _lock_dominant_subtitle_y_band(raw_frames: list[tuple[float, list[dict]]]) -> list[tuple[float, str, float]]:
    """
    Analyzes vertical positions (`mid_y`) of all high-confidence detections across the video
    to auto-lock onto the single true Subtitle Y-Band — completely eliminating floating channel
    watermarks (e.g. '笼包动画') sitting above or below the real subtitle line!
    """
    if not raw_frames:
        return []

    has_any_cjk = any(r["has_cjk"] for _, rows in raw_frames for r in rows if r["conf"] >= 0.50)

    # Histogram of mid_y in 0.05 bins weighted by confidence & real-dialogue length
    bin_weights: dict[int, float] = collections.defaultdict(float)
    for _, rows in raw_frames:
        for r in rows:
            if has_any_cjk and not r["has_cjk"]:
                continue
            if r["conf"] < 0.48 or len(r["text"]) < 2:
                continue
            b_idx = int(round(r["mid_y"] / 0.05))
            w = r["conf"] * min(len(r["text"]), 14)
            # Slightly prefer lower-half subtitle band (mid_y < 0.65) over upper watermark zone
            if r["mid_y"] <= 0.62:
                w *= 1.25
            bin_weights[b_idx] += w

    if not bin_weights:
        return []

    # Smooth adjacent bins to find the true peak center
    best_bin = max(
        bin_weights.keys(),
        key=lambda b: bin_weights.get(b - 1, 0.0) + bin_weights[b] * 1.4 + bin_weights.get(b + 1, 0.0),
    )
    dominant_y = best_bin * 0.05

    # Lock extraction strictly to rows within ±0.16 of dominant_y
    timeline: list[tuple[float, str, float]] = []
    for t_abs, rows in raw_frames:
        matched = [
            r for r in rows
            if abs(r["mid_y"] - dominant_y) <= 0.16
            and (not has_any_cjk or r["has_cjk"] or re.fullmatch(r"[0-9%.,+-]+", r["text"]))
        ]
        if not matched:
            continue
        # Pick the row closest to dominant_y with highest confidence
        best_row = max(matched, key=lambda r: (r["conf"] + 0.15 * min(len(r["text"]), 10) - abs(r["mid_y"] - dominant_y)))
        timeline.append((t_abs, best_row["text"], best_row["conf"]))

    return timeline


def _vote_best_card_text(samples: list[tuple[str, float]]) -> tuple[str, float, int]:
    if not samples:
        return "", 0.0, 0
    scores: dict[str, float] = collections.defaultdict(float)
    max_c = 0.0
    for txt, conf in samples:
        scores[txt] += conf + 0.35
        if conf > max_c:
            max_c = conf

    best_txt = max(scores.keys(), key=lambda k: (scores[k], min(len(k), 32)))
    avg_c = sum(c for _, c in samples) / len(samples)
    return best_txt, max(avg_c, max_c * 0.85), len(samples)


def _punctuate_single_card(text: str) -> str:
    t = (text or "").strip()
    if not t or re.search(r"[。！？.!?…]$", t):
        return t
    if not _CJK_CHAR_RE.search(t):
        return t
    if re.search(
        r"(?:吗|呢|咋了|啥|多少钱|切多少|卖不卖|先看看|好心|是不是|能不能|对不对|行不行|干嘛|干什么|上哪捡的|什么种水|什么玩意儿|你要全剥|什么狗屎运|什么价格|怎么了|如何|不成|是不是记错了)$",
        t,
    ) or re.match(r"^(?:难道|怎么会|为什么|凭什么|请问)", t):
        return t + "？"
    if re.fullmatch(r"(?:我去|卧槽|操|牛逼|齐活|赌个屁|涨个屁|成交|别急别急|等等|请进)", t):
        return t + "！"
    if re.search(
        r"(?:被人盯上|吃不进去|赌性大|我走了|两千万打底|颜色也进去了|自己留着|石头却废了|不能确定|两立方米了|没天理了|启动资金|神枪手|有把握的|就麻烦|卖掉|全取出来|眼下没事|这儿踏实|心里有数|概率不高|就不错了|能到糯冰|能到冰糯|真好啊|贡献点|惊着了|必须带走|先走了|投放开始)$",
        t,
    ):
        return t + "。"
    return t


def _coalesce_subtitle_cards(cards: list[dict], audio_16k=None) -> list[dict]:
    """
    Merges rapid consecutive short subtitle cards of the SAME speaker turn into natural,
    complete spoken sentences (target 2.0s–6.0s), AUTOMATICALLY SPLITTING whenever the
    original video audio shows a different actor speaking (e.g. Woman 235Hz vs Man 125Hz)!
    """
    if not cards:
        return []

    prep_cards = []
    for c in cards:
        cc = dict(c)
        cc["text"] = _punctuate_single_card(cc["text"])
        if audio_16k is not None and getattr(audio_16k, "size", 0) >= 1600:
            cc["_vf"] = audio_speaker_analyzer.extract_segment_voice_features(
                audio_16k, float(cc["start"]), float(cc["end"])
            )
        prep_cards.append(cc)

    merged: list[dict] = [dict(prep_cards[0])]
    for nxt in prep_cards[1:]:
        cur = merged[-1]
        gap = nxt["start"] - cur["end"]
        cur_txt = cur["text"].rstrip()
        nxt_txt = nxt["text"].strip()

        cur_bare = cur_txt.rstrip("。！？!?，, ")
        nxt_bare = nxt_txt.rstrip("。！？!?，, ")

        # Deduplicate exact or near-identical consecutive cards (e.g. same subtitle flashing across a cut!)
        if gap <= 1.20 and (
            cur_bare == nxt_bare
            or (len(nxt_bare) >= 4 and (nxt_bare in cur_bare or cur_bare.endswith(nxt_bare)))
            or (len(cur_bare) >= 4 and len(nxt_bare) >= 4 and difflib.SequenceMatcher(None, cur_bare, nxt_bare).ratio() >= 0.84)
        ):
            cur["end"] = round(max(cur["end"], nxt["end"]), 2)
            if len(nxt_bare) > len(cur_bare):
                cur["text"] = nxt_txt
            continue

        # Remove scrolling boundary overlap (e.g. '...曝光到网上' + '曝光到网上，7月31日...')
        for ov_len in range(min(len(cur_bare), len(nxt_bare), 14), 2, -1):
            if cur_bare.endswith(nxt_bare[:ov_len]):
                nxt_txt = nxt_txt[ov_len:].lstrip("，,。 ")
                break
        if not nxt_txt or not nxt_txt.strip("。！？!?,， "):
            cur["end"] = round(max(cur["end"], nxt["end"]), 2)
            continue

        # Acoustic Speaker-Change Guardrail: NEVER glue two different actors' voices into one line!
        speaker_changed = False
        if "_vf" in cur and "_vf" in nxt:
            speaker_changed = audio_speaker_analyzer.is_acoustic_speaker_change(cur["_vf"], nxt["_vf"])

        is_cjk = bool(_CJK_CHAR_RE.search(cur_txt + nxt_txt))
        combined_dur = nxt["end"] - cur["start"]
        cur_dur = cur["end"] - cur["start"]
        joiner = "，" if (is_cjk and not re.search(r"[，。？！、；：,.?!]$", cur_txt)) else ("" if is_cjk else " ")
        combined_txt = f"{cur_txt}{joiner}{nxt_txt}".strip()

        max_chars = 34 if is_cjk else 135
        cur_ends_strong = bool(re.search(r"[?？!！。][\"')\]»”’]*$", cur_txt))
        # Dialogue turn-end / Q&A switch detector for unpunctuated Chinese movie subtitles
        # (e.g. '你没事吧' -> '没事的', '我跟你一起' -> '有人进来了' -> '去看看' -> '好的长官')
        cur_is_complete_turn = bool(
            re.search(r"(?:吗|呢|吧|一起|看看|进来了|没事|好的|滚开|死了|分神了一下)$", cur_bare)
        )
        nxt_starts_new_turn = bool(
            re.match(
                r"^(?:我去|卧槽|操|牛逼|赌个屁|涨个屁|等等|好的|没事|有人|去看看|尝过|滚开|别|快|师姐|师兄|长官|大长老|"
                r"不好|怎么|什么|谁|哎|喂)",
                nxt_bare,
            )
        )
        nxt_is_exclam = bool(re.match(r"^(?:我去|卧槽|操|牛逼|赌个屁|涨个屁|等等|好的长官|没事的)[！!。]?$", nxt_txt))
        cur_card_count = int(cur.get("_cards", 1))

        should_join = False
        if (
            not speaker_changed
            and not cur_ends_strong
            and not nxt_is_exclam
            and not (cur_is_complete_turn and (gap >= 0.15 or nxt_starts_new_turn))
            and cur_card_count < 2
            and combined_dur <= 5.5
            and len(combined_txt) <= max_chars
        ):
            if gap <= 0.25:
                should_join = True
            elif gap <= 0.50 and not cur_is_complete_turn and (cur_dur < 1.8 or len(cur_bare) <= (8 if is_cjk else 24)):
                should_join = True

        if should_join:
            cur["end"] = round(max(cur["end"], nxt["end"]), 2)
            cur["text"] = combined_txt
            cur["conf"] = round(0.5 * (cur.get("conf", 0.8) + nxt.get("conf", 0.8)), 3)
            cur["_cards"] = cur_card_count + 1
        else:
            nxt_copy = dict(nxt)
            nxt_copy["text"] = nxt_txt
            nxt_copy["_cards"] = 1
            merged.append(nxt_copy)

    for seg in merged:
        seg.pop("_vf", None)
        seg.pop("_cards", None)
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
    Extracts burned-in subtitles across short videos OR multi-hour movies (in 10-min streaming chunks)
    with Dominant Subtitle Y-Band Auto-Locking to eliminate floating channel watermarks!
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

    # Tighter bottom 22% band on landscape (78%..100%) cuts off channel logos sitting at 70-78%!
    if is_portrait:
        vf_filter = f"crop=iw:ih*0.42:0:ih*0.50,fps={fps},scale='min(720,iw)':-2"
    else:
        vf_filter = f"crop=iw:ih*0.22:0:ih*0.78,fps={fps},scale='min(1024,iw)':-2"

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
                timeout=60,
            )
            pr = subprocess.run([ocr_bin, pdir, lang_csv], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=60)
            probe_hits = 0
            for ln in pr.stdout.decode("utf-8", errors="ignore").splitlines():
                try:
                    obj = json.loads(ln)
                    rows = _extract_candidate_rows_from_frame(obj.get("items") or [], is_portrait, is_zh_hint)
                    if any(r["conf"] >= 0.52 and len(r["text"]) >= 2 for r in rows):
                        probe_hits += 1
                except Exception:
                    pass
            if probe_hits < 6:
                return {"usable": False, "avgConf": 0.0, "coverageRatio": 0.0, "segments": []}

    chunk_sec = 600.0
    n_chunks = max(1, int((duration_sec + chunk_sec - 0.01) // chunk_sec))
    raw_frames: list[tuple[float, list[dict]]] = []

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
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=240)
            ocr_proc = subprocess.run(
                [ocr_bin, cdir, lang_csv],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=300,
            )
            for line in ocr_proc.stdout.decode("utf-8", errors="ignore").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    f_num = int(row.get("f", 1))
                    t_abs = t0 + max(0.0, (f_num - 1) * step_sec)
                    c_rows = _extract_candidate_rows_from_frame(row.get("items") or [], is_portrait, is_zh_hint)
                    if c_rows:
                        raw_frames.append((t_abs, c_rows))
                except Exception:
                    continue

    if not raw_frames:
        return {"usable": False, "avgConf": 0.0, "coverageRatio": 0.0, "segments": []}

    frame_timeline = _lock_dominant_subtitle_y_band(raw_frames)
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
        # Drop isolated 1-frame noise (e.g. stray 1-char flash '屏' / '包' on cut transitions)
        if n_f == 1 and (best_conf < 0.55 or len(best_txt) <= 1):
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

    try:
        speech_16k = audio_speaker_analyzer.load_speech_band_16k(media_path, ffmpeg_bin=ffmpeg_bin)
    except Exception:
        speech_16k = None
    segments = _coalesce_subtitle_cards(cards, audio_16k=speech_16k)
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
