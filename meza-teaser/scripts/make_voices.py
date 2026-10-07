"""Generate the two voice lines with ElevenLabs.

Requires ELEVENLABS_API_KEY in the environment (never commit the key).
Optional overrides: MEZA_VOICE_ID, CHEF_VOICE_ID, ELEVEN_MODEL.
Usage: python3 scripts/make_voices.py
Writes public/voice-meza.mp3 and public/voice-chef.mp3; the composition picks them up automatically.
"""
import json
import os
import sys
import urllib.request

KEY = os.environ.get("ELEVENLABS_API_KEY")
if not KEY:
    sys.exit("ELEVENLABS_API_KEY is not set")

MODEL = os.environ.get("ELEVEN_MODEL", "eleven_multilingual_v2")
LINES = [
    {
        "out": "public/voice-meza.mp3",
        # Default: "Sarah" — young, calm, natural female voice
        "voice": os.environ.get("MEZA_VOICE_ID", "EXAVITQu4vr4xnSDxMaL"),
        "text": "Здравствуйте, шеф. Какие задачи на сегодня?",
        "settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True, "speed": 0.95},
    },
    {
        "out": "public/voice-chef.mp3",
        # Default: "Brian" — low, calm, confident male voice
        "voice": os.environ.get("CHEF_VOICE_ID", "nPczCjzI2devNBz1zQrb"),
        "text": "Давай покажем всем, на что ты способна.",
        "settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.2, "use_speaker_boost": True, "speed": 0.92},
    },
]

for line in LINES:
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{line['voice']}?output_format=mp3_44100_192",
        data=json.dumps({"text": line["text"], "model_id": MODEL, "voice_settings": line["settings"]}).encode(),
        headers={"xi-api-key": KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    with open(line["out"], "wb") as f:
        f.write(data)
    print("wrote", line["out"], len(data), "bytes")
