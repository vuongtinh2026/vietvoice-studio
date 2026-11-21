#!/usr/bin/env python3
"""
VoiceViet Engine Pro Bridge
Connects VoiceViet Node.js backend to Cheap-TTS Python SDK 0.3.0+
Supports all 24 new Vietnamese Pro voices and standard voices.
"""

import sys
import json
import os
from cheap_tts import CheapTTS

DEFAULT_KEY = "sk_live_I_cohehhbgkJqZjJiB-JifshNNcIgSCumq07SIpMsIQ"

def get_voices(key):
    with CheapTTS(secret_key=key) as tts:
        voices = tts.voices()
        result = []
        for v in voices:
            result.append({
                "id": v.id,
                "name": v.name,
                "language": getattr(v, "language", ""),
                "useCase": getattr(v, "use_case", "")
            })
        return result

def synthesize(text, voice, rate=1.0, key=DEFAULT_KEY):
    with CheapTTS(secret_key=key) as tts:
        res = tts.synthesize(text=text, voice=voice, rate=rate)
        return res.audio, res.seconds

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "voices":
        key = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_KEY
        try:
            voices = get_voices(key)
            sys.stdout.write(json.dumps({"success": True, "voices": voices}, ensure_ascii=False))
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(str(e))
            sys.exit(1)
        return

    # Synthesis mode: reads JSON from stdin
    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            sys.stderr.write("No input JSON provided.")
            sys.exit(1)

        payload = json.loads(input_data)
        text = payload.get("text", "")
        voice = payload.get("voice", "vi-pro-podcast")
        rate = float(payload.get("rate", 1.0))
        key = payload.get("key") or DEFAULT_KEY

        audio_bytes, seconds = synthesize(text, voice, rate, key)
        # Write binary WAV to stdout
        sys.stdout.buffer.write(audio_bytes)
        sys.stdout.buffer.flush()
    except Exception as e:
        sys.stderr.write(f"Synthesis failed: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
