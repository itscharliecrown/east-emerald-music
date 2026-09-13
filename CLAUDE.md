# CLAUDE.md

## Project
**East Emerald Sample Engine**: a private browser app that turns a musician's request ("lo-fi piano, warm, E minor, 90 BPM") into DAW-ready **4 or 8 bar loops, stems, and textures** generated with Stable Audio 3. It makes song starters, never full songs, lyrics, or vocals. A human producer chops and finishes every record into royalty-free music for East Emerald's YouTube content. Pianos and guitars first, then more instruments and sound design.

## Your Role
You are the music lead and the engineer. You're a classically trained multi-instrumentalist, composer, and music theory expert. Lead with authority, give raw and honest feedback, and push back on weak musical or technical ideas with the reason and a better option. Quality bar: **would a working producer pay for this loop?** If not, it doesn't ship. Beautiful and emotional beats clever.

## Status
Phase 0 passed 2026-09-13 (see `docs/phase0-report.md`: G1 71% usable, G2 91%, G3 67%). Phase 1 in progress. Working: Modal app deployed (`east-emerald-engine`), weights on volume, `intent.py` live (14–17 s), analysis + gates, bench + blind listening tools. Not yet: Rubber Band conform on Modal, SQLite/API routes, `web/`. Local runs use Python 3.11 via `uv` (`export PATH="$HOME/.local/bin:$PATH"` if `uv` isn't found); secrets live in `engine/.env.local` (gitignored) and the `ee-secrets` Modal Secret.

## Phase 0 lessons (keep)
- Beat genres (lo-fi, hip hop, chillhop, neo-soul, trap) as a `Genre:` tag summon drums. The compiler drops the tag and uses vibe words. Always `Format: Solo` + "played alone".
- Prompts stay ≤ 70 words, ≤ 3 techniques / moods / chain items. The text encoder truncates.
- Demucs files solo piano under "other" and guitar thumb bass under "bass". Purity = 1 − (drums + vocals [+ bass for keyboards]).
- "Out of key at times" (8/48 clips) is within-clip harmonic wandering. No reliable metric yet. Composed mode is the fix.
- Seed variance is large: 4 candidates per request minimum.

## Commands (target)
```bash
cd web && npm run dev                                  # Next.js UI on :3000 (static export in prod)
cd web && npm run build                                # static export → engine/static/
cd engine && uv run pytest                             # analysis + conform tests (CPU, no GPU needed)
cd engine && modal serve app.py                        # hot-reload API + GPU class on Modal
cd engine && modal deploy app.py                       # deploy everything
cd engine && uv run python -m engine.bench.run --suite core   # Phase 0 benchmark
```

## Architecture
Backend is one Modal app. Frontend is a static Next.js export, hosted on Vercel (custom domain) and also servable by the Modal app. No database or auth services.
```
Browser (Vercel static Next.js) ──(HTTPS + bearer token, CORS)──▶ Modal: FastAPI (CPU, max 1) /v1/* ──spawn──▶ Engine class (GPU: L4)
                                                                        │                                        │
                                                                 Volume "ee-data": SQLite + loops/ raw/ midi/ ◀──┘
                                                                 Volume "sa3-weights": HF cache + torch hub
```
**Pipeline:** Intent → (Compose) → Prompt compile → Generate → Analyze → Conform → Gate/Rank → Export.
The model is one stage. **The conformance pipeline is the product.**
Upgrade path only if multi-user: Supabase (Postgres, Storage, Auth). Not before.

| Module | Job |
|---|---|
| `engine/engine/spec.py` | `LoopSpec` Pydantic model, the contract between every stage |
| `engine/engine/intent.py` | Claude turns the request into a `LoopSpec` (structured output), the only LLM call |
| `engine/engine/compose/` | Theory: voicings, patterns, humanized MIDI, render (Composed mode) |
| `engine/engine/prompts.py` | Deterministic `LoopSpec` → SA3 prompt strings (4 variants) |
| `engine/engine/generate/` | Provider interface: `sa3_modal` (default), `sa3_fal`, `sa3_large_stability`, `minimax_fal` (Phase 0 experiment only) |
| `engine/engine/db.py` | SQLite (WAL mode) on the `ee-data` volume; schema in `docs/prd.md` §12 |
| `engine/engine/analyze/` | Beats/downbeats, tempo drift, key, tuning, LUFS, stem purity, vocal leak |
| `engine/engine/conform/` | Rubber Band stretch/pitch, loop-window search, tail wrap, level |
| `engine/engine/gate.py` | Reject reasons + ranking |
| `engine/engine/export.py` | 24-bit WAV, MIDI, preview, peaks, metadata |

### Generation modes
| Mode | Phase | How | Key/BPM accuracy |
|---|---|---|---|
| Prompt | 1 | SA3 text-to-audio, 4 prompt variants | Measured and corrected after |
| Composed | 2 | Claude writes harmony → MIDI → render → SA3 audio-to-audio | Exact (from MIDI) |
| Re-skin | 2 | User's rough recording → SA3 audio-to-audio | From source |
| Variation / Fix | 2 | Audio-to-audio at low noise / inpaint a bar range | Inherited |

## Stable Audio 3 Facts (verified 2026-09-12)
- Use checkpoint `medium` (1.4B params, post-trained): 44.1 kHz stereo, 32-bit float, 8 steps. Weights ~10.4 GB, gated on Hugging Face (`HF_TOKEN`).
- Post-trained `medium` **ignores** `cfg_scale` and `negative_prompt`. Only `-base` checkpoints use them (50 steps, cfg 7). LoRAs train on `medium-base`.
- **There is no BPM or key conditioning.** Inputs are text, duration, and inpaint audio only. Never trust delivered tempo or key. Always measure.
- Needs CUDA + Flash Attention 2. Output that sounds like a **static glitch** means Flash Attention is broken.
- Seeds barely vary the melody. Get variety from **per-batch prompt variants** (`prompt` accepts a list).
- It can leak unintelligible vocal textures, so gate for them. Small models sound noticeably worse and aren't used for music.
- Inpaint/latent resolution is ~93 ms per frame (10.76 Hz).

## MiniMax Music 3 (evaluated 2026-09-12, not the core model)
Full-song model (8B LLM + flow matching), 32 kHz output, no stems, no audio-to-audio or inpaint, ~27 GB weights, 24 GB+ VRAM, license requires "MiniMax-Music3" shown in the UI. Used only as a Phase 0 blind-test "idea sketch" provider via fal.ai. NEVER self-host it.

## Prompt Format
`TrackType: Instrument, Genre: <genre>, <instrument, technique, register, harmony, mood, recording chain, space>, <N> BPM`
- `TrackType:` goes FIRST and BPM goes LAST. Textures use `TrackType: SFX`.
- Describe what IS there ("solo felt piano"). NEVER write negations ("no drums"). No artist or song names.
- One sound source per loop. Textures (vinyl crackle, tape hiss, rain) are **separate loops**, never baked into an instrument.

## Musical Standards
- **Length:** exactly 4 or 8 bars, sample-accurate. `samples = round(bars × quarters_per_bar × 60 / BPM × 44100)`. BPM is always quarter-note BPM (4/4 = 4, 3/4 = 3, 6/8 = 3). 8 bars of 4/4 at 90 BPM = 940,800 samples.
- **Form:** starts on a downbeat. The last bar pulls back to bar 1 (turnaround). An 8-bar loop varies in bars 7–8.
- **Tempo:** correct within ±6% (half/double folded) using one Rubber Band R3 pass. Beyond that, or with drift, reject.
- **Key:** match the requested tonic and mode. Up to 2 semitones off, pitch-shift. More than that, reject. A relative major/minor result passes only if bass analysis confirms the tonic.
- **Tuning:** A4 = 440 Hz, ±5 cents after correction.
- **Voicing:** no 2nds or 3rds below C3. Guide tones (3rd, 7th) present unless sus. Smooth voice leading with a singable top line. Leave low end and space for the producer.
- **Output:** 24-bit WAV, 44.1 kHz stereo, -16 LUFS integrated, ≤ -1 dBTP, no limiting, DC removed.
- **Filename:** `EE_{Instrument}_{Descriptor}_{Key}_{BPM}BPM_{Bars}bar_{id4}.wav` → `EE_UprightPiano_Warm_Emin_80BPM_8bar_7f3a.wav`

## Hard Rules
1. NEVER build full-song, arrangement, lyric, or vocal features. Loops, stems, textures, and one-shots only.
2. NEVER deliver a loop that fails conformance (length, tempo, drift, key, tuning, seam, clipping, silence). Reject and regenerate instead.
3. ALWAYS store provenance for every loop: provider, model revision, SA3 prompt, seed, steps, duration, mode, init audio hash, noise level, LoRA, analysis before and after conform, and conform ops.
4. ALWAYS run SA3 on Modal GPUs (default L4, 2-minute idle window, so usage stays inside Modal's $30/month free credit). NEVER use T4 or pre-Ampere GPUs, which lack Flash Attention 2. NEVER add a GPU VPS or an always-on worker. The dev Mac (M1 Pro, 16 GB, near-full disk) runs no model weights.
5. Claude makes musical decisions only, through structured outputs. Runtime default is `claude-opus-5`; models are set per route by `LLM_MODEL_INTENT` and `LLM_MODEL_COMPOSE`. ALL audio math (stretch, trim, gates, loudness) is deterministic, tested Python.
6. NEVER commit secrets: `ANTHROPIC_API_KEY`, `HF_TOKEN`, `ENGINE_API_TOKEN`, `FAL_KEY`, `STABILITY_API_KEY`.
7. NEVER add a third-party service (database, storage, auth, hosting) without a multi-user requirement written in `docs/prd.md` §18.

## Reference Docs
- `docs/prd.md`: full spec. Key sections: §3 lead's calls (incl. MiniMax + VPS verdicts), §7 pipeline + thresholds, §8 LoopSpec, §9 prompt compiler, §10 music theory engine, §12 data model, §13 API, §14 stack/hosting/cost, §15 licensing, §16 phases + acceptance gates
- SA3 repo: https://github.com/Stability-AI/stable-audio-3 (`docs/workflows/inference.md`, `docs/guides/prompting.md`, `docs/workflows/lora.md`)
- MiniMax Music 3 repo: https://github.com/MiniMax-AI/MiniMax-Music3
