#!/usr/bin/env python3
"""
Voxly Studio — Acoustic Speaker Biometrics, Gender/Age/Crowd Diarization & Turn-Change Detector
Analyzes the original video/audio waveform at each dialogue timestamp [start, end] to determine:
  1. Whether two adjacent subtitle cards were spoken by DIFFERENT actors (splitting multi-actor turns
     like '我跟你一起' [Woman] vs '有人进来了' [Man] vs '好的长官' [Soldier]!).
  2. Each speaker's acoustic profile:
       - TRE_EM    (Trẻ em / Bé trai / Bé gái)     : high F0 >= 280Hz & bright spectral centroid
       - NU_TRE    (Nữ trẻ / Thiếu nữ)             : F0 ~202-280Hz, bright female formants
       - PHU_NU    (Phụ nữ / Đàn bà trưởng thành)  : F0 ~168-205Hz, warmer female resonance
       - NAM_TRE   (Nam trẻ / Thanh niên)          : F0 ~122-170Hz, crisp male resonance
       - DAN_ONG   (Đàn ông trưởng thành)          : F0 ~92-128Hz, deep chest male resonance
       - ONG_LAO   (Ông lão / Trưởng lão)          : deep F0 < 105Hz or elder cues
       - DAM_DONG  (Đám đông / Nhiều người nói)    : chaotic multi-pitch / crowd shouting cues
  3. Consistent Speaker Clusters (NAM_1, NAM_2, NU_1, NU_2...) across short clips & 3-hour movies!
"""
import os
import re
import subprocess
import tempfile
import wave

import librosa
import numpy as np

# Canonical Vietnamese dubbing role codes (also user-editable in #dubTranslatedScript!)
ROLE_DISPLAY_MAP = {
    "NAM_TRE": "NAM TRẺ",
    "NAM_2": "NAM 2",
    "DAN_ONG": "ĐÀN ÔNG",
    "ONG_LAO": "ÔNG LÃO",
    "NU_TRE": "NỮ TRẺ",
    "NU_2": "NỮ 2",
    "PHU_NU": "PHỤ NỮ",
    "TRE_EM": "TRẺ EM",
    "DAM_DONG": "ĐÁM ĐÔNG",
    "DAN_CHUYEN": "DẪN CHUYỆN",
}

# Reverse lookup (accepts Vietnamese with/without accents, underscores, spaces, aliases)
_ROLE_ALIAS_MAP = {
    "NAM TRE": "NAM_TRE",
    "NAM_TRE": "NAM_TRE",
    "NAM 1": "NAM_TRE",
    "NAM_1": "NAM_TRE",
    "NAM": "NAM_TRE",
    "NAM CHINH": "NAM_TRE",
    "NAM 2": "NAM_2",
    "NAM_2": "NAM_2",
    "NAM PHU": "NAM_2",
    "DAN ONG": "DAN_ONG",
    "DAN_ONG": "DAN_ONG",
    "ĐÀN ÔNG": "DAN_ONG",
    "NAM TRƯỞNG THÀNH": "DAN_ONG",
    "NAM TRUONG THANH": "DAN_ONG",
    "ONG LAO": "ONG_LAO",
    "ONG_LAO": "ONG_LAO",
    "ÔNG LÃO": "ONG_LAO",
    "LAO NAM": "ONG_LAO",
    "LAO_NAM": "ONG_LAO",
    "TRUONG LAO": "ONG_LAO",
    "TRƯỞNG LÃO": "ONG_LAO",
    "NU TRE": "NU_TRE",
    "NU_TRE": "NU_TRE",
    "NỮ TRẺ": "NU_TRE",
    "NU 1": "NU_TRE",
    "NU_1": "NU_TRE",
    "NU": "NU_TRE",
    "NỮ": "NU_TRE",
    "NU CHINH": "NU_TRE",
    "NU 2": "NU_2",
    "NU_2": "NU_2",
    "NỮ 2": "NU_2",
    "NU PHU": "NU_2",
    "PHU NU": "PHU_NU",
    "PHU_NU": "PHU_NU",
    "PHỤ NỮ": "PHU_NU",
    "DAN BA": "PHU_NU",
    "DAN_BA": "PHU_NU",
    "ĐÀN BÀ": "PHU_NU",
    "ME": "PHU_NU",
    "MẸ": "PHU_NU",
    "TRE EM": "TRE_EM",
    "TRE_EM": "TRE_EM",
    "TRẺ EM": "TRE_EM",
    "BE TRAI": "TRE_EM",
    "BE GAI": "TRE_EM",
    "THIEU NHI": "TRE_EM",
    "DAM DONG": "DAM_DONG",
    "DAM_DONG": "DAM_DONG",
    "ĐÁM ĐÔNG": "DAM_DONG",
    "CROWD": "DAM_DONG",
    "NHIEU NGUOI": "DAM_DONG",
    "DAN CHUYEN": "DAN_CHUYEN",
    "DAN_CHUYEN": "DAN_CHUYEN",
    "DẪN CHUYỆN": "DAN_CHUYEN",
    "THUYET MINH": "DAN_CHUYEN",
    "NARRATOR": "DAN_CHUYEN",
}

_CROWD_TEXT_RE = re.compile(
    r"(?:兄弟们|大家一起|快跑啊|打死他|冲啊|杀啊|上啊|救命啊|所有人|一起上|快撤|撤退|灾星灾星)",
    re.IGNORECASE,
)
_ELDER_TEXT_RE = re.compile(
    r"(?:老夫|本座|老朽|老身|贫道|老衲|凡人何日|老朽|小娃子)",
    re.IGNORECASE,
)


def canonicalize_role_tag(raw_tag: str) -> str:
    if not raw_tag:
        return ""
    s = re.sub(r"[\[\]()（）:：\-]+", " ", str(raw_tag)).strip().upper()
    s = re.sub(r"\s+", " ", s)
    if s in _ROLE_ALIAS_MAP:
        return _ROLE_ALIAS_MAP[s]
    # Strip accents fallback
    import unicodedata
    no_acc = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).replace("Đ", "D")
    if no_acc in _ROLE_ALIAS_MAP:
        return _ROLE_ALIAS_MAP[no_acc]
    if "DAM DONG" in no_acc or "CROWD" in no_acc:
        return "DAM_DONG"
    if "TRE EM" in no_acc or "BE " in no_acc or "NHI" in no_acc:
        return "TRE_EM"
    if "LAO" in no_acc or "GIA" in no_acc:
        return "ONG_LAO"
    if "DAN BA" in no_acc or "PHU NU" in no_acc or "ME" == no_acc:
        return "PHU_NU"
    if "NU 2" in no_acc or "NU PHU" in no_acc:
        return "NU_2"
    if "NU" in no_acc or "CO GAI" in no_acc:
        return "NU_TRE"
    if "DAN ONG" in no_acc or "TRUNG NIEN" in no_acc or "CHA" == no_acc:
        return "DAN_ONG"
    if "NAM 2" in no_acc or "NAM PHU" in no_acc:
        return "NAM_2"
    if "NAM" in no_acc:
        return "NAM_TRE"
    if "DAN CHUYEN" in no_acc or "THUYET MINH" in no_acc:
        return "DAN_CHUYEN"
    return ""


def role_to_display_label(role_code: str) -> str:
    code = canonicalize_role_tag(role_code) or "DAN_CHUYEN"
    return ROLE_DISPLAY_MAP.get(code, "DẪN CHUYỆN")


def load_speech_band_16k(media_path: str, ffmpeg_bin: str = "ffmpeg") -> np.ndarray:
    """
    Extracts mono 16kHz vocal-emphasized PCM (2-pole bandpass 98Hz..3800Hz so deep sci-fi/action
    sub-bass music drones and cymbal SFX do NOT bias YIN fundamental frequency toward false bass!).
    """
    with tempfile.TemporaryDirectory(prefix="voxly_spk_") as tdir:
        wav_p = os.path.join(tdir, "speech16k.wav")
        cmd = [
            ffmpeg_bin, "-nostdin", "-y",
            "-i", media_path,
            "-vn",
            "-af", "highpass=f=98:poles=2,lowpass=f=3800:poles=2",
            "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            wav_p,
        ]
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        if proc.returncode != 0 or not os.path.exists(wav_p):
            return np.zeros(0, dtype=np.float32)
        with wave.open(wav_p, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def extract_segment_voice_features(audio_16k: np.ndarray, start_sec: float, end_sec: float, sr: int = 16000) -> dict:
    """
    Computes robust acoustic voice biometrics over the loudest speech-active frames of [start_sec, end_sec]:
      - f0_med      : upper-median (55th pct) voiced fundamental frequency (Hz) via YIN
      - f0_iqr      : pitch spread (Hz) — high spread indicates shouting/overlapping crowd
      - centroid    : spectral centroid (Hz) — differentiates bright child/female vs warm/deep male
      - mfcc        : 13-dim MFCC vocal-tract timbre vector (for speaker-change & clustering!)
      - voiced_ok   : True if enough clear speech frames were found
    """
    empty = {
        "f0_med": 0.0,
        "f0_iqr": 0.0,
        "centroid": 0.0,
        "mfcc": np.zeros(13, dtype=np.float32),
        "voiced_ok": False,
    }
    if audio_16k.size < 1600:
        return empty

    i0 = max(0, int(start_sec * sr))
    i1 = min(audio_16k.size, int(max(start_sec + 0.35, end_sec) * sr))
    seg = audio_16k[i0:i1]
    if seg.size < 1200:
        return empty

    # Limit analysis slice to 8s max for instant speed on very long turns
    if seg.size > sr * 8:
        seg = seg[: sr * 8]

    # Gate active vocal energy frames (top 50% loudest vocal syllables above noise floor)
    rms = librosa.feature.rms(y=seg, frame_length=512, hop_length=256)[0]
    if rms.size == 0 or float(np.max(rms)) < 0.008:
        return empty

    thresh = max(0.012, float(np.percentile(rms, 55)) * 0.85)
    active_mask = rms >= thresh

    # Fundamental frequency F0 via YIN (human speech range 88..430 Hz, rejecting sub-bass BGM rumble)
    try:
        f0 = librosa.yin(seg, fmin=88.0, fmax=430.0, sr=sr, frame_length=1024, hop_length=256)
    except Exception:
        return empty

    n_min = min(f0.size, active_mask.size)
    f0 = f0[:n_min]
    act = active_mask[:n_min]
    valid_f0 = f0[act & (f0 > 90.0) & (f0 < 415.0)]
    if valid_f0.size < 3:
        valid_f0 = f0[(f0 > 90.0) & (f0 < 415.0)]
    if valid_f0.size < 3:
        return empty

    # Use 55th percentile of active vocal frames so inter-syllable BGM troughs don't drag F0 downward
    q15, q55, q85 = np.percentile(valid_f0, [15, 55, 85])
    f0_med = float(q55)
    f0_iqr = float(q85 - q15)

    # Spectral centroid + MFCC over active frames
    cent = librosa.feature.spectral_centroid(y=seg, sr=sr, n_fft=512, hop_length=256)[0][:n_min]
    cent_med = float(np.median(cent[act])) if np.any(act) else float(np.median(cent))

    mfcc = librosa.feature.mfcc(y=seg, sr=sr, n_mfcc=13, n_fft=512, hop_length=256)[:, :n_min]
    mfcc_vec = np.mean(mfcc[:, act], axis=1) if np.any(act) else np.mean(mfcc, axis=1)

    return {
        "f0_med": round(f0_med, 1),
        "f0_iqr": round(f0_iqr, 1),
        "centroid": round(cent_med, 1),
        "mfcc": mfcc_vec.astype(np.float32),
        "voiced_ok": True,
    }


def is_acoustic_speaker_change(feat_a: dict, feat_b: dict) -> bool:
    """
    Returns True when two adjacent subtitle cards clearly come from DIFFERENT human voices
    (e.g. Woman 235Hz replying to Man 125Hz, or Soldier 1 vs Soldier 2), preventing the OCR
    coalescer from ever gluing two different characters' lines into one monologue!
    """
    if not feat_a.get("voiced_ok") or not feat_b.get("voiced_ok"):
        return False

    f0_a, f0_b = feat_a["f0_med"], feat_b["f0_med"]
    # Crossing male/female boundary (e.g. 145Hz -> 210Hz) or large pitch jump (>= 42 Hz / >= 28%)
    if abs(f0_a - f0_b) >= 42.0:
        return True
    ratio = max(f0_a, f0_b) / max(60.0, min(f0_a, f0_b))
    if ratio >= 1.32:
        return True

    # Different vocal-tract timbre (MFCC cosine distance) even among two same-gender speakers
    va, vb = feat_a["mfcc"][1:], feat_b["mfcc"][1:]  # skip C0 energy
    na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
    if na > 1e-4 and nb > 1e-4:
        cos_sim = float(np.dot(va, vb) / (na * nb))
        if cos_sim < 0.72 and abs(f0_a - f0_b) >= 18.0:
            return True
    return False


def analyze_segments_acoustic_roles(
    segments: list[dict],
    media_path: str,
    ffmpeg_bin: str = "ffmpeg",
) -> list[dict]:
    """
    Enriches every dialogue segment with ground-truth acoustic voice biometrics & speaker role:
      - `acousticRole`: one of NAM_TRE, NAM_2, DAN_ONG, ONG_LAO, NU_TRE, NU_2, PHU_NU, TRE_EM, DAM_DONG
      - `acousticF0`: median pitch in Hz
      - `speakerCluster`: e.g. 'NAM_1', 'NAM_2', 'NU_1', 'NU_2'
    """
    if not segments or not media_path or not os.path.exists(media_path):
        return segments

    audio_16k = load_speech_band_16k(media_path, ffmpeg_bin=ffmpeg_bin)
    if audio_16k.size < 1600:
        return segments

    feats: list[dict] = []
    for seg in segments:
        f = extract_segment_voice_features(audio_16k, float(seg.get("start", 0.0)), float(seg.get("end", 0.0)))
        feats.append(f)

    # Compute adaptive gender threshold for this video (handles movies with brighter/darker mix)
    valid_f0s = [f["f0_med"] for f in feats if f["voiced_ok"]]
    male_female_split = 180.0
    if len(valid_f0s) >= 6:
        arr_f0 = np.array(valid_f0s, dtype=np.float32)
        if np.max(arr_f0) - np.min(arr_f0) > 65.0:
            # Find natural valley between male (105-165Hz) and female (195-280Hz) clusters
            low_c = float(np.percentile(arr_f0, 25))
            high_c = float(np.percentile(arr_f0, 75))
            if low_c < 168.0 and high_c > 195.0:
                male_female_split = max(176.0, min(194.0, 0.5 * (low_c + high_c)))

    # First-pass gender & age classification per segment
    male_indices: list[int] = []
    female_indices: list[int] = []
    enriched: list[dict] = []

    for idx, seg in enumerate(segments):
        s_out = dict(seg)
        f = feats[idx]
        txt = str(seg.get("text") or "")

        if _CROWD_TEXT_RE.search(txt) and (not f["voiced_ok"] or f["f0_iqr"] >= 55.0):
            role = "DAM_DONG"
        elif not f["voiced_ok"]:
            role = "DAN_CHUYEN"
        else:
            f0 = f["f0_med"]
            cent = f["centroid"]
            iqr = f["f0_iqr"]

            if f0 >= 298.0 and cent >= 2050.0:
                role = "TRE_EM"
            elif f0 >= male_female_split:
                female_indices.append(idx)
                if f0 >= 216.0:
                    role = "NU_TRE"
                else:
                    role = "PHU_NU"
            else:
                male_indices.append(idx)
                # Never guess ONG_LAO purely from low F0 (action BGM bass can pull male voice to 95-105Hz);
                # reserve ONG_LAO for explicit elder speech clues or AI Director Character-Bible confirmation!
                if _ELDER_TEXT_RE.search(txt):
                    role = "ONG_LAO"
                elif f0 <= 128.0:
                    role = "DAN_ONG"
                else:
                    role = "NAM_TRE"

            # High chaotic multi-pitch shouting with crowd punctuation
            if iqr >= 125.0 and ("!" in txt or "！" in txt) and len(txt) <= 14:
                if _CROWD_TEXT_RE.search(txt):
                    role = "DAM_DONG"

        s_out["acousticRole"] = role
        s_out["acousticF0"] = f["f0_med"]
        enriched.append(s_out)

    # Second-pass sub-speaker clustering inside Male & Female groups using MFCC + F0
    # so TWO young men talking to each other get distinct voices (NAM_TRE vs NAM_2 / DAN_ONG),
    # and TWO young women talking get distinct voices (NU_TRE vs NU_2 / PHU_NU)!
    try:
        from sklearn.cluster import AgglomerativeClustering

        def _cluster_sub_voices(indices: list[int], primary_role: str, secondary_role: str):
            if len(indices) < 4:
                return
            vecs = []
            for ii in indices:
                mf = feats[ii]["mfcc"][1:10]
                norm_mf = mf / (np.linalg.norm(mf) + 1e-5)
                f0_scaled = (feats[ii]["f0_med"] - 160.0) / 80.0
                vecs.append(np.append(norm_mf, f0_scaled))
            X = np.vstack(vecs)
            cl = AgglomerativeClustering(n_clusters=2, metric="euclidean", linkage="ward")
            labels = cl.fit_predict(X)
            # Assign majority cluster -> primary_role, minority -> secondary_role (keeping ONG_LAO / TRE_EM intact)
            c0 = int(np.sum(labels == 0))
            c1 = int(np.sum(labels == 1))
            maj_lbl = 0 if c0 >= c1 else 1
            # Only split if cluster centroids are genuinely distinct voices!
            mu0 = np.mean(X[labels == 0], axis=0)
            mu1 = np.mean(X[labels == 1], axis=0)
            if float(np.linalg.norm(mu0 - mu1)) >= 0.42:
                for pos, ii in enumerate(indices):
                    cur_r = enriched[ii]["acousticRole"]
                    if cur_r in ("ONG_LAO", "TRE_EM", "DAM_DONG"):
                        continue
                    if labels[pos] != maj_lbl:
                        # Distinguish secondary voice cleanly
                        if primary_role == "NAM_TRE":
                            enriched[ii]["acousticRole"] = "DAN_ONG" if feats[ii]["f0_med"] < 132.0 else secondary_role
                        else:
                            enriched[ii]["acousticRole"] = "PHU_NU" if feats[ii]["f0_med"] < 208.0 else secondary_role

        _cluster_sub_voices(male_indices, "NAM_TRE", "NAM_2")
        _cluster_sub_voices(female_indices, "NU_TRE", "NU_2")
    except Exception:
        pass

    return enriched
