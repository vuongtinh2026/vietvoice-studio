#!/usr/bin/env python3
"""
Cryptographic Private Voice Vault for VoiceViet Studio
- Encrypts personal cloned voice vectors (speaker_emb + codes) on disk using
  PBKDF2-HMAC-SHA256 (200,000 iterations) + HMAC-SHA256 stream cipher + EtM MAC tag.
- Enforces per-request X-Owner-Token authorization so NO unauthorized user
  (even on the same server/network) can synthesize with private voices without the Owner PIN!
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import tempfile
import time
from typing import Any

import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_DIR = os.path.join(BASE_DIR, "private_voices")
VAULT_FILE = os.path.join(VAULT_DIR, "vault.json")
DEFAULT_INITIAL_PIN = "888888"


def _derive_keys(pin: str, salt: bytes) -> tuple[bytes, bytes, bytes]:
    pin_bytes = pin.encode("utf-8")
    verifier = hashlib.pbkdf2_hmac("sha256", pin_bytes, salt + b":verify", 200_000, dklen=32)
    enc_key = hashlib.pbkdf2_hmac("sha256", pin_bytes, salt + b":enc", 200_000, dklen=32)
    mac_key = hashlib.pbkdf2_hmac("sha256", pin_bytes, salt + b":mac", 200_000, dklen=32)
    return verifier, enc_key, mac_key


def _xor_keystream(data: bytes, enc_key: bytes, nonce: bytes) -> bytes:
    out = bytearray(len(data))
    offset = 0
    counter = 0
    while offset < len(data):
        block = hmac.new(enc_key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        take = min(32, len(data) - offset)
        for i in range(take):
            out[offset + i] = data[offset + i] ^ block[i]
        offset += take
        counter += 1
    return bytes(out)


def encrypt_payload(obj: dict[str, Any], enc_key: bytes, mac_key: bytes) -> dict[str, str]:
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    nonce = secrets.token_bytes(16)
    ct = _xor_keystream(raw, enc_key, nonce)
    tag = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
    return {
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ct).decode("ascii"),
        "tag": base64.b64encode(tag).decode("ascii"),
    }


def decrypt_payload(blob: dict[str, str], enc_key: bytes, mac_key: bytes) -> dict[str, Any]:
    nonce = base64.b64decode(blob["nonce"])
    ct = base64.b64decode(blob["ct"])
    tag = base64.b64decode(blob["tag"])
    expected_tag = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Mật khẩu / Mã PIN Chủ Sở Hữu không chính xác hoặc dữ liệu bị từ chối!")
    raw = _xor_keystream(ct, enc_key, nonce)
    return json.loads(raw.decode("utf-8"))


class PrivateVoiceVault:
    def __init__(self, ffmpeg_bin: str = "ffmpeg") -> None:
        self.ffmpeg_bin = ffmpeg_bin
        os.makedirs(VAULT_DIR, exist_ok=True)
        try:
            os.chmod(VAULT_DIR, 0o700)
        except OSError:
            pass
        self._unlocked_vectors: dict[str, dict[str, Any]] = {}
        self._active_tokens: set[str] = set()
        self._cached_enc_key: bytes | None = None
        self._cached_mac_key: bytes | None = None
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        if os.path.exists(VAULT_FILE):
            return
        salt = secrets.token_bytes(16)
        verifier, _, _ = _derive_keys(DEFAULT_INITIAL_PIN, salt)
        data = {
            "version": 1,
            "salt": base64.b64encode(salt).decode("ascii"),
            "verifier": base64.b64encode(verifier).decode("ascii"),
            "voices": {},
        }
        self._save_vault_file(data)

    def _load_vault_file(self) -> dict[str, Any]:
        self._ensure_initialized()
        with open(VAULT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_vault_file(self, data: dict[str, Any]) -> None:
        os.makedirs(VAULT_DIR, exist_ok=True)
        tmp = f"{VAULT_FILE}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, VAULT_FILE)

    def verify_pin(self, pin: str) -> tuple[bool, bytes, bytes]:
        if not pin:
            return False, b"", b""
        vault = self._load_vault_file()
        salt = base64.b64decode(vault["salt"])
        expected = base64.b64decode(vault["verifier"])
        verifier, enc_key, mac_key = _derive_keys(pin, salt)
        if hmac.compare_digest(verifier, expected):
            return True, enc_key, mac_key
        return False, b"", b""

    def is_valid_token(self, token: str | None) -> bool:
        return bool(token and token in self._active_tokens)

    def unlock(self, pin: str) -> str:
        ok, enc_key, mac_key = self.verify_pin(pin)
        if not ok:
            raise PermissionError("Mã PIN / Mật khẩu Chủ Sở Hữu không đúng!")
        vault = self._load_vault_file()
        unlocked: dict[str, dict[str, Any]] = {}
        for vid, entry in vault.get("voices", {}).items():
            dec = decrypt_payload(entry["encrypted"], enc_key, mac_key)
            unlocked[vid] = {
                "speaker_emb": np.asarray(dec["speaker_emb"], dtype=np.float32),
                "codes": np.asarray(dec["codes"], dtype=np.int64) if dec.get("codes") is not None else None,
            }
        self._unlocked_vectors = unlocked
        self._cached_enc_key = enc_key
        self._cached_mac_key = mac_key
        token = secrets.token_urlsafe(32)
        self._active_tokens.add(token)
        return token

    def lock(self) -> None:
        self._unlocked_vectors.clear()
        self._active_tokens.clear()
        self._cached_enc_key = None
        self._cached_mac_key = None

    def change_pin(self, current_pin: str, new_pin: str) -> str:
        if not new_pin or len(new_pin.strip()) < 4:
            raise ValueError("Mật khẩu / Mã PIN mới cần tối thiểu 4 ký tự!")
        ok, old_enc, old_mac = self.verify_pin(current_pin)
        if not ok:
            raise PermissionError("Mật khẩu / Mã PIN hiện tại không đúng!")

        vault = self._load_vault_file()
        # Decrypt all existing voices with old key, then re-encrypt with brand-new salt & key!
        decrypted_map = {}
        for vid, entry in vault.get("voices", {}).items():
            decrypted_map[vid] = decrypt_payload(entry["encrypted"], old_enc, old_mac)

        new_salt = secrets.token_bytes(16)
        new_verifier, new_enc, new_mac = _derive_keys(new_pin.strip(), new_salt)
        vault["salt"] = base64.b64encode(new_salt).decode("ascii")
        vault["verifier"] = base64.b64encode(new_verifier).decode("ascii")
        for vid, plain_obj in decrypted_map.items():
            vault["voices"][vid]["encrypted"] = encrypt_payload(plain_obj, new_enc, new_mac)

        self._save_vault_file(vault)
        # Rotate session tokens so any old session is invalidated
        self.lock()
        return self.unlock(new_pin.strip())

    def list_private_voices_public(self) -> list[dict[str, Any]]:
        vault = self._load_vault_file()
        items = []
        for vid, entry in vault.get("voices", {}).items():
            items.append(
                {
                    "id": vid,
                    "name": entry["name"],
                    "gender": entry.get("gender", "Nam"),
                    "language": "vi",
                    "country": "🔒 Giọng Nhân Bản Độc Quyền",
                    "provider": "private_clone",
                    "featured": True,
                    "isPrivate": True,
                    "useCase": entry.get("description", "Giọng nhân bản cá nhân độc quyền (48kHz Studio)"),
                    "badge": "🔒 ĐỘC QUYỀN",
                    "createdAt": entry.get("createdAt", ""),
                    "sampleText": (
                        "Chào mừng các bạn quay trở lại với kênh Truyện Dị Giới TV... "
                        "Giữa tầng mây mù vạn trượng, Lâm Uy chậm rãi bước ra, ánh mắt sắc lạnh nhìn thẳng về phía trước!"
                        if "di-gioi" in vid
                        else f"Xin chào các bạn... Đây là giọng đọc nhân bản độc quyền 48kHz của {entry['name']} trên VoiceViet Studio."
                    ),
                }
            )
        return items

    def get_authorized_voice_preset(self, voice_id: str, owner_token: str | None) -> dict[str, Any]:
        if not self.is_valid_token(owner_token):
            raise PermissionError(
                "🔒 Giọng đọc riêng tư đang được KHÓA bảo vệ! Chỉ Chủ Sở Hữu có Mật khẩu / Mã PIN mới được phép sử dụng giọng này."
            )
        vec = self._unlocked_vectors.get(voice_id)
        if vec is None:
            raise ValueError(f"Không tìm thấy dữ liệu giọng riêng tư: {voice_id}")
        return {
            "description": "Private Owner Voice",
            "gender": "Nam",
            "style": "tu_nhien",
            "speaker_emb": vec["speaker_emb"],
            "codes": vec["codes"],
        }

    def enroll_new_private_voice(
        self,
        vieneu_tts: Any,
        audio_bytes: bytes,
        name: str,
        gender: str = "Nam",
        description: str = "Giọng nhân bản cá nhân độc quyền 48kHz",
        pin_or_token: str = "",
        custom_id: str | None = None,
    ) -> dict[str, Any]:
        # Verify authorization via either active owner token or direct PIN
        enc_key = self._cached_enc_key
        mac_key = self._cached_mac_key
        if not (self.is_valid_token(pin_or_token) and enc_key and mac_key):
            ok, ek, mk = self.verify_pin(pin_or_token)
            if not ok:
                raise PermissionError("Vui lòng mở khóa hoặc nhập đúng Mã PIN Chủ Sở Hữu để thêm giọng nhân bản!")
            enc_key, mac_key = ek, mk

        import soundfile as sf

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_in = os.path.join(tmpdir, "upload_input")
            clean_full = os.path.join(tmpdir, "clean_44k.wav")
            with open(raw_in, "wb") as f:
                f.write(audio_bytes)

            # Convert any input format (mp3/wav/m4a/webm/ogg) to clean 44.1kHz mono WAV with rumble filter + gentle leveling
            subprocess.run(
                [
                    self.ffmpeg_bin, "-y", "-i", raw_in,
                    "-af", "highpass=f=75,acompressor=threshold=-20dB:ratio=1.8:attack=15:release=200:makeup=1.2",
                    "-ar", "44100", "-ac", "1", clean_full,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            wav_data, sr = sf.read(clean_full, dtype="float32", always_2d=False)
            wav_data = np.asarray(wav_data, dtype=np.float32).reshape(-1)
            total_sec = wav_data.size / float(sr)
            if total_sec < 2.5:
                raise ValueError("File âm thanh mẫu quá ngắn! Vui lòng cung cấp đoạn thu âm tối thiểu từ 4 giây trở lên.")

            # Multi-window studio x-vector averaging for long recordings (>14s) for maximum vocal fidelity!
            win_sec = 7.5
            win_samples = int(win_sec * sr)
            embs = []
            primary_codes = None

            if wav_data.size <= int(12.0 * sr):
                emb, codes = vieneu_tts.encode_reference(clean_full, denoise=True)
                embs.append(np.asarray(emb, dtype=np.float32))
                primary_codes = np.asarray(codes, dtype=np.int64)
            else:
                # Score candidate 7.5s windows across the recording by active speech RMS energy (avoiding dead silence or clipping)
                step = max(int(4.0 * sr), (wav_data.size - win_samples) // 16)
                candidates = []
                pos = int(1.0 * sr)
                while pos + win_samples <= wav_data.size - int(0.5 * sr):
                    seg = wav_data[pos : pos + win_samples]
                    rms = float(np.sqrt(np.mean(seg * seg)))
                    peak = float(np.max(np.abs(seg)))
                    # Active speech fraction (> -38 dB)
                    frame_len = int(0.05 * sr)
                    frames = seg[: (seg.size // frame_len) * frame_len].reshape(-1, frame_len)
                    frame_rms = np.sqrt(np.mean(frames * frames, axis=1))
                    active_ratio = float(np.mean(frame_rms > 0.012))
                    if 0.02 < rms < 0.65 and peak < 0.99 and active_ratio > 0.62:
                        score = active_ratio * 2.0 + min(rms * 5.0, 1.0)
                        candidates.append((score, pos))
                    pos += step

                # Pick up to 4 well-spaced top-scoring windows
                candidates.sort(key=lambda x: x[0], reverse=True)
                chosen_positions: list[int] = []
                for _, c_pos in candidates:
                    if all(abs(c_pos - prev) >= int(6.5 * sr) for prev in chosen_positions):
                        chosen_positions.append(c_pos)
                    if len(chosen_positions) >= 4:
                        break

                if not chosen_positions:
                    chosen_positions = [min(int(2.0 * sr), max(0, wav_data.size - win_samples))]

                for i, c_pos in enumerate(chosen_positions):
                    seg_path = os.path.join(tmpdir, f"win_{i}.wav")
                    sf.write(seg_path, wav_data[c_pos : c_pos + win_samples], sr)
                    emb, codes = vieneu_tts.encode_reference(seg_path, denoise=True)
                    embs.append(np.asarray(emb, dtype=np.float32))
                    if i == 0:
                        primary_codes = np.asarray(codes, dtype=np.int64)

            avg_emb = np.mean(np.stack(embs, axis=0), axis=0)
            ref_norm = float(np.linalg.norm(embs[0]))
            cur_norm = float(np.linalg.norm(avg_emb))
            if cur_norm > 1e-6:
                avg_emb = avg_emb * (ref_norm / cur_norm)

        voice_id = custom_id or f"private-voice-{secrets.token_hex(4)}"
        plain_payload = {
            "speaker_emb": [round(float(x), 6) for x in avg_emb.reshape(-1)],
            "codes": primary_codes.tolist() if primary_codes is not None else None,
        }
        encrypted_blob = encrypt_payload(plain_payload, enc_key, mac_key)

        vault = self._load_vault_file()
        vault.setdefault("voices", {})[voice_id] = {
            "name": name.strip(),
            "gender": gender,
            "description": description.strip(),
            "createdAt": time.strftime("%Y-%m-%d %H:%M"),
            "encrypted": encrypted_blob,
        }
        self._save_vault_file(vault)

        # If currently unlocked in memory, also update memory map
        if self._active_tokens:
            self._unlocked_vectors[voice_id] = {
                "speaker_emb": avg_emb.astype(np.float32),
                "codes": primary_codes,
            }

        return {
            "id": voice_id,
            "name": name.strip(),
            "gender": gender,
            "useCase": description.strip(),
            "badge": "🔒 ĐỘC QUYỀN",
            "isPrivate": True,
        }

    def delete_private_voice(self, voice_id: str, pin_or_token: str) -> None:
        if not self.is_valid_token(pin_or_token):
            ok, _, _ = self.verify_pin(pin_or_token)
            if not ok:
                raise PermissionError("Cần mở khóa Mã PIN Chủ Sở Hữu để xóa giọng riêng tư!")
        vault = self._load_vault_file()
        if voice_id in vault.get("voices", {}):
            del vault["voices"][voice_id]
            self._save_vault_file(vault)
        self._unlocked_vectors.pop(voice_id, None)
