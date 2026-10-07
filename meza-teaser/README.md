# MEZA — teaser 15s (9:16, 1080×1920, 60 fps)

Remotion project for the hidden launch teaser.

```bash
npm i
npm run dev                                  # Remotion Studio preview
python3 scripts/prep_assets.py               # images + particle cloud -> public/
python3 scripts/make_sfx.py                  # procedural sound design -> public/sfx.wav
ELEVENLABS_API_KEY=... python3 scripts/make_voices.py   # voice lines -> public/voice-*.mp3
npx remotion render MezaTeaser out/meza-teaser.mp4 --crf=16
```

Voice files are picked up automatically when present in `public/`.
Timeline cues live in `src/timeline.ts` (mirrored in `scripts/make_sfx.py`).
