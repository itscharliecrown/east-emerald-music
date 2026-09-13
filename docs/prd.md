# East Emerald Sample Engine: Product Requirements Document

| | |
|---|---|
| Version | 1.1 (adds MiniMax Music 3 evaluation, single-app hosting, cost re-plan) |
| Date | 2026-09-12 |
| Owner | Charlie Crown (product) · Claude (music lead + engineering) |
| Status | Draft, pre-Phase 0 |
| Model facts verified | 2026-09-12 against the Stable Audio 3 and MiniMax Music 3 repos, Hugging Face model cards, tech report, and provider pricing pages (§20) |

Abbreviations are defined on first use and collected in the Glossary (§19).

---

## 1. Summary

The East Emerald Sample Engine is a private browser app that turns a musician's plain-English request into **DAW-ready loops and stems** (DAW = Digital Audio Workstation: Ableton, Logic, FL Studio). "Lo-fi piano, warm, soft chords, E minor, 90 BPM (beats per minute)" becomes four sample-accurate 4 or 8 bar candidates. You audition them, keep the best, and download a 24-bit WAV (plus MIDI where available).

It is a **song-starter engine, not a song generator.** Every loop is raw material a human producer chops, arranges, and finishes into royalty-free records for East Emerald's YouTube content.

The sound source is **Stable Audio 3 Medium** (SA3), running on a serverless cloud GPU. The generator is not the product. The product is everything around it:

1. **Musical intent parsing.** Claude turns loose language into a precise musical spec.
2. **A music theory engine.** Harmony, voicing, and feel are chosen for the emotion requested.
3. **A strict prompt compiler.** It speaks the model's training vocabulary.
4. **A conformance pipeline.** It guarantees every delivered loop is in tempo, in key, in tune, on the grid, and seamless.

---

## 2. Goals, Non-Goals, Success Metrics

### 2.1 Goals
1. Generate beautiful, emotionally specific instrument loops, pianos and guitars first, that a working producer would pay for.
2. Guarantee technical correctness: exact bar length, requested tempo and key, A440 tuning, seamless loop point, consistent level.
3. Fast iteration: from submitting a request to auditioning four candidates in under 20 seconds when the engine is warm.
4. A searchable library of kept loops with full provenance.
5. Expand to more instruments, textures, and sound design without re-architecting.
6. Cloud-hosted, usable from any browser, affordable under heavy daily use.

### 2.2 Non-Goals (hard)
- Full songs, arrangements, song sections (verse/chorus), lyrics, vocals, voice cloning.
- Loops longer than 8 bars.
- Mixing or mastering finished tracks.
- A public, multi-user SaaS (Software as a Service). This is a private East Emerald tool. If that changes, revisit §15 first.
- Drum loops in Phases 1–2. They need transient-aware conformance, so they come in Phase 3+.

### 2.3 Success Metrics
| Metric | Definition | Phase 1 target | Phase 2 target |
|---|---|---|---|
| Keeper rate | % of requests where at least one candidate is kept | ≥ 60% | ≥ 80% |
| Conformance | % of delivered loops that pass the DAW Loop Test (§16.5) | 100% | 100% |
| Time to audition, warm | Request submitted → 4 candidates playable (p50, median) | ≤ 20 s | ≤ 15 s |
| Time to audition, cold | Same, with the engine asleep | ≤ 90 s | ≤ 60 s |
| Running cost | GPU + Claude API + storage at ~30 requests/day | ≤ $60/mo (GPU inside Modal's free credit) | ≤ $80/mo |
| Real usage | Kept loops later marked `used_in_track` | Tracked | Tracked |

Latency and cost targets are estimates. Phase 0 measures them for real.

---

## 3. Lead's Calls: Where I'm Pushing Back

These decisions are made. Each has a reason, and each can be reopened with evidence.

| Idea on the table | My call | Why |
|---|---|---|
| `lo-fi piano, warm, vinyl crackle, soft chords, 80 BPM, TrackType: Instrument` | Split it into **a piano loop plus a separate vinyl-crackle texture loop**, and put `TrackType:` first. | Baked-in crackle can't be turned down, EQ'd, or muted in the drop. Every producer wants textures on their own fader. The official SA3 convention puts TrackType at the start. We follow it, and Phase 0 A/B tests prefix vs suffix. |
| An "agent" that does everything | A **deterministic pipeline with exactly one LLM step** (intent + composition). | Audio correctness has to be measurable and repeatable. An LLM deciding stretch ratios or trim points adds latency, cost, and randomness where math already has the right answer. Claude does what it is best at: musical judgment and language. |
| Trust the model to hit "E minor at 90 BPM" | **Never trust it. Measure and correct.** | SA3 has no BPM or key conditioning. Tempo and key are just words in the prompt, and the tech report doesn't evaluate tempo or key accuracy at all. |
| Run it on the Mac | **Cloud GPU on Modal.** | SA3 Medium needs CUDA + Flash Attention (NVIDIA only). Its weights are ~10.4 GB, and the dev Mac (M1 Pro, 16 GB RAM) has 5.5 GB of disk free. An Apple Silicon MLX build exists as a later offline option (§14.5). |
| "Best in the world" from text prompts alone | Text-to-audio is the floor. The ceiling is **Composed mode, heavy curation, strict gates, and a LoRA trained on recordings we own.** | Reviews say SA3 music "can feel correct without feeling interesting," and different seeds give near-identical melodies. Taste has to be injected on purpose. |
| Any length from 4 to 8 bars | **Exactly 4 or 8 bars.** | 5, 6, and 7-bar loops break phrase structure and don't tile against 4/8-bar arrangements. |
| "Royalty-free for YouTube" means we're covered | **Safe to use, not automatically ownable.** The human production is what makes the finished record ours. | U.S. Copyright Office guidance says works lacking human authorship aren't protectable. Don't register raw loops in Content ID. Keep provenance. See §15. |
| Start with the Large model for best quality | **Start with Medium, and blind-test Large in Phase 0.** | Large is API-only: no LoRA, less pipeline control, reportedly $0.26 per generation. We pay for it only if our ears prefer it blind. |
| Write chord symbols in a Phase 1 prompt ("Em9 – Cmaj7") | Accept them, but **tell the user they aren't guaranteed until Composed mode (Phase 2).** | A text encoder can't enforce a chord sequence. Composed mode can, because the harmony comes from MIDI we write. |
| Use MiniMax Music 3 instead of, or alongside, SA3 | **SA3 stays the core. MiniMax gets one blind test via fal.ai, never self-hosted.** | MiniMax is a full-song model: 32 kHz output, no stems, no audio-to-audio or inpainting, ~27 GB of weights needing 24 GB+ VRAM (the repo recommends two GPUs), and its license requires "MiniMax-Music3" displayed in the UI. Its one edge is an 8B language model composing the music, which may give more interesting harmony. If it wins the blind test on musicality, it becomes an optional "idea sketch" provider whose output still passes through stem extraction and every gate. See §14.5. |
| A cheap or free VPS instead of Modal | **No VPS. Modal's Starter plan ($30/month of free compute, no card) covers Phase 0–1 GPU time.** | A CPU VPS can't run SA3 Medium (CUDA + Flash Attention required). The cheapest always-on 24 GB GPU is ~$195/mo (RunPod) or ~€184/mo (Hetzner GEX44). Our workload is bursty, so per-second serverless at ~35–40 GPU hours/month lands inside the free credit. Free notebook GPUs (Kaggle, Colab) are T4s, which lack Flash Attention 2. See §14.4–14.5. |
| Next.js on Vercel + Supabase for a private tool | **One Modal app serves the API, the static frontend, and SQLite on a volume.** | Two fewer services, no row-level security, no proxy routes, $0. Supabase + Vercel return only when a second user is a written requirement (§18). |
| Use Fable 5.1 (the model we're planning with) at runtime | **Build with Fable. Run on `claude-opus-5`, configurable per route.** | Fable costs $10/$50 per million tokens vs $5/$25. Intent parsing 30 times a day doesn't need it. Composed mode can be promoted to Fable if the harmony eval shows a difference worth 2× the price. |

---

## 4. Users & Workflows

**Primary user:** Charlie (producer, A&R). **Possible secondary users:** East Emerald producers (open question, §18).

### 4.1 Core loop
1. Open the app. The engine starts waking in the background while you type.
2. Type a request. Optional chips override instrument, key, BPM, bars, and mode.
3. Read Claude's short notes: assumptions made ("chose E minor") and pushback ("split vinyl crackle into its own texture").
4. Audition up to 4 candidates. Each has a waveform, gapless loop playback, an optional click, requested vs delivered key/BPM, and the corrections applied.
5. Keep or reject, and star the good ones.
6. Refine with **More like this** (variation), **Fix bars 3–4** (inpaint), **Same idea, different instrument**, or **Add a texture**.
7. Download a 24-bit WAV (plus MIDI in Composed mode) and drop it into the DAW.
8. Browse the library later by instrument, key, BPM, and mood, and find key-compatible loops to layer.

### 4.2 User stories
- As a producer, I type "sad nylon guitar, A minor, 85" and get loops I can drop into a session **without warping**.
- As a producer, I hear a great tone with one wrong bar, so I regenerate just that bar.
- As a producer, I find a piano I love and ask for "a guitar that fits this," and the engine inherits key, BPM, and bars.
- As a producer, I hum or play a rough idea into my phone and get it back played by a real-sounding instrument (Re-skin, Phase 2).
- As A&R, I see which engine loops ended up in released tracks.

---

## 5. Scope by Phase

| Capability | P0 Spike | P1 MVP | P2 Craft | P3 Signature |
|---|---|---|---|---|
| SA3 Medium on Modal + benchmark runner | ✅ | | | |
| Analysis module (tempo, key, tuning, LUFS, purity) | ✅ | | | |
| Prompt mode end-to-end in the browser | | ✅ | | |
| Conformance pipeline + quality gates | | ✅ | | |
| Library, keep/reject, stars, downloads | | ✅ | | |
| Variation (audio-to-audio) + Fix bars (inpaint) | | | ✅ | |
| Composed mode (theory → MIDI → SA3) + MIDI export | | | ✅ | |
| Re-skin (upload a rough idea) | | | ✅ | |
| Textures (vinyl, tape hiss, room tone, rain) | | | ✅ | |
| CLAP ranking + learning from keep/reject history | | | ✅ | |
| Inpaint seam healing | | | ✅ | |
| East Emerald signature LoRA | | | | ✅ |
| More families (strings, pads, bass, synths, mallets, world) | | | | ✅ |
| One-shots + sound design (risers, impacts, foley) | | | | ✅ |
| Pack export (zip of key-compatible sets) | | | | ✅ |
| Drum loops (transient-aware conform) | | | | ✅ |

**Instrument roster, Phase 1:** grand piano, upright piano, felt piano, Rhodes, Wurlitzer, nylon-string guitar, steel-string acoustic (fingerstyle and strummed), clean electric guitar, jazz archtop.

---

## 6. Architecture

```
┌────────────────────────── Browser ──────────────────────────┐
│ Next.js static export · Web Audio gapless looper · wavesurfer│
└──────────────┬──────────────────────────────────────────────┘
               │ HTTPS + bearer token (ENGINE_API_TOKEN)
┌──────────────▼────────────── Modal (one app) ───────────────┐
│ FastAPI web container (CPU, max 1)                           │
│   serves engine/static/ (the frontend) and /v1/*             │
│   owns SQLite on volume "ee-data" (WAL mode)                 │
│         │ .spawn()                                           │
│         ▼                                                    │
│ Engine class (GPU: L4, 2-min idle window, max 2)             │
│   ├ intent  (Claude API, structured outputs)                 │
│   ├ compose (theory → MIDI → FluidSynth render)              │
│   ├ prompts (deterministic compiler)                         │
│   ├ generate (SA3 Medium; fal / Stability / MiniMax optional)│
│   ├ analyze (Beat This!, Essentia, Demucs, pyloudnorm)       │
│   ├ conform (Rubber Band R3)                                 │
│   ├ gate / rank                                              │
│   └ export → volume "ee-data": loops/ raw/ midi/ uploads/    │
│ Volume "sa3-weights": Hugging Face cache, pre-downloaded     │
└─────────────────────────────────────────────────────────────┘
```

**Design principles**
- **One deployable.** `modal deploy` ships the frontend, API, database, storage, and GPU engine together. No Vercel, no Supabase, no VPS.
- **Single LLM step.** Claude outputs a validated `LoopSpec`. Everything after that is deterministic code.
- **Provider-agnostic generation.** The pipeline doesn't care whether audio came from Modal, fal.ai, the Stability API, or MiniMax.
- **Measure everything, store everything.** Analysis runs before and after conforming, and all provenance is persisted.
- **Reject rather than ship.** A missing candidate is better than a wrong one.
- **Free until it isn't.** GPU time is sized to stay inside Modal's $30/month credit. The upgrade path (Supabase, Vercel, paid GPU) exists on paper only.

---

## 7. Generation Pipeline

### 7.1 Intent (Claude)
- **Input:** raw text, UI overrides, mode, and the parent loop's spec when refining.
- **Model:** `claude-opus-5` by default, via the Anthropic Python SDK, using structured outputs (`client.messages.parse()` against the Pydantic `LoopSpec`) and adaptive thinking. The model is configured per route (`LLM_MODEL_INTENT`, `LLM_MODEL_COMPOSE`), so Composed mode can be promoted to `claude-fable-5-1` if the harmony eval (§16.4) justifies 2× the token price.
- **Effort per route:** `medium` for Prompt mode, `high` for Composed mode. Tune both against the intent eval (§16.3).
- **Refusal fallback:** server-side fallbacks enabled (`fallbacks: "default"` with the `server-side-fallback-2026-07-01` beta).
- **System prompt:** stable and cached (prompt caching). It holds the music-lead persona, the §9 vocabulary, the §10 theory rules, and 10–15 worked examples. Volatile content (the request) goes last, so the cache prefix never changes.
- **Claude's responsibilities:**
  - Fill defaults (§8.2) and record every choice in `assumptions`.
  - Split textures out of instrument requests into `texture_suggestions`.
  - Write 4 **descriptor variants** (structured fields, not free strings) for the prompt compiler.
  - Write `pushback` when a request is musically weak. Example: "trap piano at 70 BPM" becomes 140 BPM with a half-time feel, because that's how the genre is counted.
  - Write the harmony plan (degrees, qualities, durations, rationale).
- **Precedence:** UI overrides always win over parsed text.
- **Failure handling:** if validation fails, retry once with the validation error attached. If it fails again, fail the request with a readable message.
- **Logging:** store `usage` (input, output, cache tokens) in `requests.llm_usage` from day one. This is the largest variable cost.

### 7.2 Compose (Composed mode, Phase 2)
1. **Voicing:** Claude's harmony plan goes to the deterministic voicing engine (§10.3), which outputs concrete MIDI notes.
2. **Pattern:** a pattern template is applied per instrument (block chords, broken chords, arpeggios, Travis picking, strum patterns), followed by humanization (§10.6).
3. **Validation:** check bar math, instrument range, low-interval limits, guitar playability, and the turnaround (§10.8).
4. **Render:** render the MIDI with FluidSynth and a General MIDI SoundFont at the target tempo, with 1 bar of pre-roll. The render only needs correct pitch and timing. SA3 supplies the tone.
5. **Re-voice:** run SA3 audio-to-audio with the instrument prompt at the `init_noise_level` chosen in the Phase 0 sweep (start range 0.5–0.8). Lower values keep the harmony more faithfully but sound less realistic. Higher values sound more real but drift harmonically.
6. **Harmony check:** compare per-bar chroma of output vs MIDI. Reject when similarity is too low (§7.7).
7. **Deliver:** the MIDI ships alongside the WAV, so the producer can double the part with their own instruments.

### 7.3 Prompt compile
Deterministic. See §9.

### 7.4 Generate
- **Interface:** `Generator.generate(prompts[], duration_s, seeds[], init_audio=None, init_noise_level=None, inpaint=None)`. Implementations:
  - `SA3MediumModal`: the default.
  - `SA3MediumFal`: fallback and Phase 0 baseline.
  - `SA3LargeStability`: only if the Phase 0 blind test justifies it.
  - `MiniMaxMusic3Fal`: Phase 0 experiment only. It takes a structured caption (genre, BPM, key, solo instrument arrangement) with the instrumental flag, receives a 32 kHz full mix, upsamples to 44.1 kHz, and runs Demucs to isolate the requested stem before analysis. Not available for audio-to-audio, inpaint, or LoRA.
- **Checkpoint:** `medium` (post-trained), 8 steps. `cfg_scale` and `negative_prompt` aren't sent because post-trained checkpoints ignore them.
- **Duration:** `(bars + 2) × bar_seconds`, rounded up to 0.1 s. That's 1 bar of pre-roll for the loop-window search plus 1 bar of tail for the reverb wrap.
- **Batch:** 4 candidates in one call, one prompt variant each (`prompt` accepts a per-batch list). Seeds are random and all logged.
- **Retry:** if fewer than 2 candidates pass the gate, run one more batch with 4 new variants. Maximum 2 batches per request. After that, return whatever passed, with an explanation.
- **Raw output:** 32-bit float, 44.1 kHz stereo. Stored for provenance and for sound-design downloads.

### 7.5 Analyze
| Measurement | Tool | Notes |
|---|---|---|
| Beats + downbeats | Beat This! (CPJKU) | Tempo = 60 / median inter-beat interval. Drift = coefficient of variation of the intervals. |
| Tempo octave | Folding logic | Fold ×2 / ×0.5 to whichever is closest to the requested BPM. |
| Key + strength | Essentia `KeyExtractor` | Profile type chosen in Phase 0 by calibrating against rendered fixtures with known keys. |
| Tonic confirmation | Bass chroma (low-passed < 250 Hz) histogram | Resolves relative major/minor confusion (E minor vs G major share every note). |
| Tuning offset | Essentia `TuningFrequency` (or librosa `estimate_tuning`) | Cents relative to A440. |
| Loudness | pyloudnorm (ITU-R BS.1770) | Integrated LUFS. True peak via 4× oversampled peak. |
| Stem purity + vocal leakage | Demucs `htdemucs_6s` (drums, bass, other, vocals, guitar, piano) | Heuristic only: the 6-stem piano separation is known to be weak. Calibrate thresholds in Phase 0. |
| Stereo health | Left/right correlation | A mean below 0 means mono phone speakers risk cancellation. |
| Silence / clipping | NumPy | RMS per bar, and flat-topped sample runs. |

### 7.6 Conform (order matters)
1. **Tempo + pitch in ONE Rubber Band R3 pass** (`--fine` engine). One pass means fewer artifacts than two.
   - **Time ratio:** detected BPM / target BPM. Allowed only within ±6% after octave folding.
   - **Pitch shift:** key correction (≤ 2 semitones) plus tuning correction to A440.
   - **Free-time material:** if `feel.rhythmic = false` (ambient, rubato), skip the tempo correction. Length still comes from BPM, so the loop still tiles.
2. **Re-track beats** on the conformed audio.
3. **Loop-window search.** For every candidate downbeat where `start + bars` plus 250 ms fits in the audio, score:
   - onset strength at the start
   - spectral continuity across the seam (last frame vs first frame)
   - energy stability across the window
   - no cut pickup notes

   Pick the best-scoring window.
4. **Exact length:** `samples = round(bars × quarters_per_bar × 60 / BPM × 44100)`. BPM is always quarter-note BPM, the DAW convention: 4/4 → 4, 3/4 → 3, 6/8 → 3. Worked example: 8 bars of 4/4 at 90 BPM = 940,800 samples (21.333 s).
5. **Tail wrap.** Audio after the loop end (reverb, sustain) is faded into the first bar, so the loop sounds like it has already been playing. A pickup (anacrusis) before the start is wrapped onto the end. Finish with a 3 ms equal-power fade at the boundary.
6. **Level.** Remove DC offset, apply a 20 Hz subsonic high-pass, then normalize to **-16 LUFS integrated with true peak ≤ -1 dBTP.** If the peak ceiling binds, lower the gain. **Never limit.** Dynamics belong to the producer.
7. **Seam heal (Phase 2 alternative to the wrap):** circular-shift the loop by half, inpaint ~0.5 s across the old seam with the same prompt, then shift back. Inpaint resolution is about 93 ms per latent frame. Re-run the analysis afterward.

### 7.7 Gate & Rank
All thresholds are **initial values to calibrate in Phase 0.** Rejected candidates are stored with their reasons and can be viewed in the UI. They are the calibration data.

| Reason code | Check | Initial threshold |
|---|---|---|
| `silence` | Any full bar below threshold | RMS < -45 dBFS |
| `clipping` | Flat-topped runs in raw output | ≥ 4 consecutive samples at \|x\| ≥ 0.99 |
| `tempo_out_of_range` | Octave-folded tempo error | > 6% |
| `tempo_drift` | Coefficient of variation of inter-beat intervals | > 3% |
| `key_mismatch` | Tonic/mode vs requested | > 2 semitones, or a different mode |
| `key_ambiguous` | Key strength (instrument loops only) | < 0.6 |
| `stem_bleed` | Requested stem's share of energy | < 70% |
| `vocal_texture` | Vocal stem's share of energy | ≥ 10% |
| `seam_discontinuity` | Spectral flux at the seam vs the clip median | > 3× |
| `harmony_drift` | Composed mode: per-bar chroma cosine vs MIDI | < 0.75 |
| `mono_risk` (warn only) | Mean L/R correlation | < 0 |

A relative major/minor detection (G major for requested E minor) passes only if the bass-tonic histogram confirms E. Otherwise it's `key_mismatch`.

**Ranking survivors**
- **Phase 1:** a composite of gate margins (purity, key strength, beat stability, seam score).
- **Phase 2:** adds LAION-CLAP text-audio similarity and a preference model learned from keep/reject history.

### 7.8 Export
- **Audio:** WAV, 24-bit PCM, 44.1 kHz, stereo.
- **Filename:** `EE_{Instrument}_{Descriptor}_{Key}_{BPM}BPM_{Bars}bar_{id4}.wav`, e.g. `EE_UprightPiano_Warm_Emin_80BPM_8bar_7f3a.wav`. Modes other than major/minor are spelled out: `Ddorian`.
- **Embedded metadata:** ACID chunk (tempo, root note, beat count) and a RIFF `INFO` comment with the loop ID.
- **MIDI (Composed mode):** Type 1, 480 PPQ (pulses per quarter note), tempo and time-signature meta events, one track per hand or voice.
- **Web assets:** MP3 preview for fast playback, plus precomputed waveform peaks JSON.
- **Raw:** the unconformed audio as FLAC, for sound-design use.

---

## 8. LoopSpec Schema

`LoopSpec` is the contract between every stage. It's defined once in Pydantic (`engine/engine/spec.py`) and exported as JSON Schema to the frontend.

### 8.1 Example (Prompt mode)
```json
{
  "category": "instrument",
  "instrument": { "family": "piano", "type": "upright_piano", "techniques": ["soft sustained chords", "felt-muted hammers"], "register": "mid" },
  "genre": "Lo-Fi Hip Hop",
  "moods": ["warm", "nostalgic"],
  "key": { "tonic": "E", "mode": "minor" },
  "bpm": 80,
  "time_signature": "4/4",
  "bars": 8,
  "feel": { "rhythmic": true, "swing_pct": 58, "half_time": false, "static": false },
  "leave_low_end": true,
  "production": { "space": "small wooden room", "chain": ["close-miked", "cassette tape saturation"] },
  "harmony": {
    "progression": [
      { "degree": "i", "quality": "m9", "beats": 8 },
      { "degree": "VI", "quality": "maj7", "beats": 8 },
      { "degree": "III", "quality": "maj7", "beats": 8 },
      { "degree": "VII", "quality": "6", "beats": 8 }
    ],
    "harmonic_rhythm": "one_chord_per_2_bars",
    "rationale": "Aeolian with major-seventh color: sad but warm. VII pulls back to i for a seamless turnaround."
  },
  "variants": [
    { "axis": "register", "techniques": ["low-mid voicings", "soft sustained chords"], "chain": ["close-miked", "cassette tape saturation"] },
    { "axis": "articulation", "techniques": ["gently broken chords", "felt-muted hammers"], "chain": ["close-miked", "cassette tape saturation"] },
    { "axis": "recording", "techniques": ["soft sustained chords"], "chain": ["roomy mono microphone", "worn tape wobble"] },
    { "axis": "intensity", "techniques": ["very soft, sparse chords with space"], "chain": ["close-miked", "warm tape"] }
  ],
  "texture_suggestions": [{ "type": "vinyl_crackle", "reason": "requested in prompt; delivered as a separate loop" }],
  "assumptions": ["No bar count given: 8 bars at 80 BPM (21 s) lets the progression breathe."],
  "pushback": "Vinyl crackle is split into its own texture loop so you can mix it independently."
}
```

### 8.2 Validation & Defaults
| Field | Constraint | Default when not stated |
|---|---|---|
| `category` | `instrument` \| `texture` \| `one_shot` (P3) | `instrument` |
| `bars` | 4 \| 8 | 8 below 100 BPM, 4 at 100 BPM and above |
| `bpm` | 50–180 | Genre-typical (§10.5) |
| `time_signature` | `4/4` \| `3/4` \| `6/8` | `4/4` |
| `key.tonic` | 12 pitch classes, spelled for the key signature (Bb not A#, F# not Gb) | Chosen for mood + instrument idiom (§10.7) |
| `key.mode` | major, minor, dorian, mixolydian, lydian, phrygian | Chosen for mood (§10.2) |
| `feel.swing_pct` | 50–70 (50 = straight, 66.7 = triplet) | Genre-typical |
| `leave_low_end` | bool | `true` for hip hop, lo-fi, R&B, and trap contexts |
| `variants` | Exactly 4 | Required |
| candidates (request) | 1–4 | 4 |

---

## 9. Prompt Compiler

Deterministic Python. Claude chooses the words, and the compiler guarantees the format.

### 9.1 Template
```
TrackType: Instrument, Genre: {genre}, {solo?} {instrument phrase} {technique phrase} in {Key} {mode}, {mood phrase}, {recording chain}, {space}, {bpm} BPM
```
Textures:
```
TrackType: SFX, {source}, {behavior over time}, {character}
```

### 9.2 Rules
1. `TrackType:` comes first. BPM comes last as `N BPM`. This follows the model-card convention.
2. **No negations.** The encoder can't read "no". Say `solo upright piano`, never `piano, no drums`.
3. No artist, band, or song names.
4. One sound source per loop. Duo formats (`Format: Duo`) arrive in Phase 3 only.
5. Concrete sonic words beat hype words. Use `close-miked, felt-muted hammers`, never `amazing, high quality`.
6. The 4 variants each change **one or two axes** from the base: register/voicing, articulation/density, recording chain/space, or mood intensity. Variety comes from prompt variants, not seeds.

### 9.3 Vocabulary (Phase 1)
| Instrument | Type phrases | Technique phrases | Recording phrases |
|---|---|---|---|
| Grand piano | concert grand piano, warm grand piano | flowing arpeggios, sustained chords, gentle melody over chords | stereo pair of condenser microphones, concert hall |
| Upright piano | upright piano, old upright piano | soft chords, felt-muted hammers, broken chords | close-miked, cassette tape saturation, small wooden room |
| Felt piano | felt piano, muted felt piano | intimate, soft attack, pedal resonance | very close microphones, mechanical key noise, soft room |
| Rhodes | Rhodes electric piano | warm tremolo chords, bell-like tines, neo-soul voicings | direct recording, subtle chorus, amp |
| Wurlitzer | Wurlitzer electric piano | slightly driven chords, reedy bark | tape saturation, small amp |
| Nylon guitar | nylon-string classical guitar | fingerpicked arpeggios, bossa nova comping, soft thumb bass | close condenser microphone, intimate room |
| Steel acoustic | steel-string acoustic guitar | fingerstyle, alternating thumb bass, open-voiced arpeggios, gentle strumming | stereo pair of small-diaphragm condensers, dry studio room |
| Clean electric | clean electric guitar, neck pickup | neo-soul chord slides, hammer-ons, muted plucks | clean tube amp, spring reverb, light chorus |
| Jazz archtop | hollow-body jazz guitar | soft chord melody, warm thumb plucks | amp microphone, small club room |
| Texture | vinyl record surface noise, cassette tape hiss, room tone, gentle rain on a window | soft continuous crackle, steady and even | warm, distant, intimate |

### 9.4 Worked examples

**Charlie's lo-fi request:** "lo-fi piano, warm, vinyl crackle, soft chords, 80 BPM, TrackType: Instrument"

The piano loop:
```
TrackType: Instrument, Genre: Lo-Fi Hip Hop, solo upright piano playing soft jazzy minor-ninth and major-seventh chords in E minor, felt-muted hammers, gentle laid-back swing, warm and nostalgic, close-miked through cassette tape saturation, small wooden room, 80 BPM
```
A separate texture loop:
```
TrackType: SFX, vinyl record surface noise, soft continuous crackle and gentle hiss from a spinning turntable, warm, steady and even
```

**Charlie's guitar request:** "acoustic fingerstyle guitar, intimate, studio recording". No key or BPM was given, so Claude chooses and logs the assumptions.
```
TrackType: Instrument, Genre: Acoustic Folk, solo steel-string acoustic guitar, intimate fingerstyle with alternating thumb bass and open-voiced arpeggios in D major, gentle and hopeful, stereo pair of small-diaphragm condenser microphones, dry studio room, 96 BPM
```

---

## 10. Music Theory Engine

### 10.1 Principles
1. **Emotion first.** Choose harmony for the feeling asked, not the textbook default. Borrowed chords, suspensions, and inner-voice motion beat a stock I–V–vi–IV.
2. **One idea per loop.** A starter is a seed, not a finished arrangement.
3. **Leave room for the producer.** Don't fill the whole spectrum. When `leave_low_end` is on, keep the left hand light and above C3 so the bass or 808 has space. Rests are part of the phrase.
4. **Every loop has a turnaround.** The last bar must pull back to bar 1.
5. **Voice leading is the beauty.** Keep common tones, move inner voices by step, and let the top voice sing.

### 10.2 Mood → Harmonic Palette
| Mood | Mode / center | Archetype (degrees) | Example |
|---|---|---|---|
| Melancholic, nostalgic | Aeolian | i9 – VImaj7 – IIImaj7 – VII6 | E minor: Em9 – Cmaj7 – Gmaj7 – D6 |
| Warm, lo-fi, jazzy | Major, ii–V motion | ii9 – V13 – Imaj9 – vi9 | F major: Gm9 – C13 – Fmaj9 – Dm9 |
| Hopeful, uplifting | Ionian, stepwise bass | I – V/3 – vi7 – IVmaj9 | D major: D – A/C# – Bm7 – Gmaj9 |
| Bittersweet | Major with borrowed iv | I – iii – IV – iv | C major: C – Em – F – Fm |
| Dreamy, floating | Lydian vamp | Imaj7 – II/I | F Lydian: Fmaj7 – G/F |
| Dark, tense | Harmonic minor | i – bVI – V7(b9) | A minor: Am – F – E7b9 |
| Cinematic, epic | Aeolian | i – bVI – bIII – bVII | D minor: Dm – Bb – F – C |
| Soulful, neo-soul | Major, deceptive pull | IVmaj9 – iii7 – ii9 – V13sus4 | Eb major: Abmaj9 – Gm7 – Fm9 – Bb13sus4 |

These are starting palettes, not templates. Claude varies inversions, extensions, and harmonic rhythm, and explains its choices in `rationale`.

### 10.3 Voicing Rules
**Piano**
- Low-interval limits: no 2nds or 3rds below C3. 5ths and octaves are fine lower down.
- Left hand: root, root + 5th, root + 7th, or root + 10th, within C2–C4. When `leave_low_end`, stay at or above C3, or go rootless.
- Right hand: 3–4 notes within C4–C6. Include the guide tones (3rd and 7th) unless the chord is sus. Add 9, 11, and 13 as color. Avoid b9 intervals between voices except on dominant b9 chords.
- Voice leading: keep common tones, move other voices by step, and resolve leaps in the opposite direction.
- The top voice forms a singable line: mostly stepwise, at most one leap per bar.

**Guitar**
- Practical range E2–E5 in standard tuning. Fingerstyle stays mostly below the 12th fret.
- Playability: span of 4 frets or fewer (5 with open strings), one note per string, 6 notes max.
- Keys with open-string resonance: E, A, D, G, C major and E, A, B, D minor. Use capo shapes for bright keys (capo 2 + G shapes = A major).
- Idioms: Travis picking (thumb alternates bass on the beats, fingers play melody off the beat), p-i-m-a arpeggios, strum patterns (down strums low→high, up strums lighter and high→low), hammer-ons, slides.

### 10.4 Harmonic Rhythm & Loop Form
- **4 bars:** one chord per bar, or two per bar in bars 3–4 for forward motion.
- **8 bars:** A (bars 1–4) then A′ (bars 5–8), with a variation in bars 7–8: a new voicing, a passing chord, or a suspension. This is what stops an 8-bar loop from sounding like a 4-bar loop copied twice.
- **Turnaround:** the final chord must pull to bar 1. Allowed functions: V, V7sus, bVII, iv (minor plagal), a split ii–V, or a suspension resolving into bar 1.
- **Static loops:** ending on the same root-position tonic that bar 1 starts on is forbidden, unless `feel.static = true` (drones, vamps).

### 10.5 Tempo & Feel by Genre
| Genre | BPM (quarter note) | Feel |
|---|---|---|
| Lo-fi hip hop | 70–90 | Swung 16ths (55–62%), laid back |
| Boom bap | 85–95 | Swing 54–60% |
| Chillhop / jazz-hop | 80–95 | Light swing |
| Neo-soul / R&B | 65–90 | Behind the beat, 16th swing |
| Trap soul | 130–160 | Straight, half-time feel (`half_time: true`) |
| Acoustic folk | 80–120 | Straight, or 6/8 |
| Bossa nova | 120–140 | Straight 8ths, syncopated |
| Pop ballad | 60–80 | Straight 8ths |
| Cinematic / ambient | 60–80 or free time | Rubato → `rhythmic: false` |
| House (keys) | 118–128 | Straight |
| Afrobeats (guitar/keys) | 100–115 | Syncopated 16ths, slight swing |

### 10.6 Humanization (Composed mode MIDI)
- **Velocity:** follow a phrase arc (swell into bars 2–3 of a 4-bar phrase, relax into the turnaround) with ±6–10 of random variance. The melody voice sits 8–12 velocity above the inner voices.
- **Timing:** ±5–12 ms random. For lo-fi and neo-soul, lay chords back +10–25 ms. On soft ballads, roll piano chords bottom-up over 8–25 ms.
- **Sustain pedal (CC64):** lift just before a chord change and re-press 30–60 ms after the new onset (legato pedaling), so harmonies never smear.
- **Guitar strums:** 12–30 ms between strings.

### 10.7 Key Selection
- **Guitar:** prefer the open-string keys (§10.3) unless the user asks otherwise.
- **Piano:** any key. Flat keys (Eb, Ab, Db) sit naturally under the hands for jazz and neo-soul voicings.
- **Refinements ("a guitar that fits this"):** inherit key, BPM, and bars from the parent loop.
- **Library "compatible" filter:** same key, relative key, or ±1 on the Camelot wheel, at an equal or half/double BPM.

### 10.8 Deterministic Validators (code, not LLM)
- Chord durations sum to `bars × beats_per_bar`.
- Every note is within the instrument's range.
- Low-interval limits are respected.
- Guitar voicings are playable.
- Notes are diatonic to the key and mode, unless a chord is flagged `borrowed` or `chromatic` with a reason.
- The turnaround rule is satisfied unless `static`.

---

## 11. Web App

### 11.1 Screens
1. **Create:** prompt bar, override chips (instrument, key, BPM, bars, mode), engine status dot (asleep / waking / warm), and a panel for Claude's assumptions and pushback.
2. **Results (inline on Create):** up to 4 candidate cards, plus a "show rejected (with reasons)" toggle.
3. **Library:** filters by family, instrument, key, mode, BPM range, mood, bars, and kept/favorite, plus the "compatible with…" filter.
4. **Loop detail:** full provenance, analysis before and after conform, all downloads, and the request lineage (parent and child loops).

### 11.2 Candidate Card
- Waveform (wavesurfer.js) with bar lines.
- **Gapless looping through the Web Audio API** (`AudioBufferSourceNode` with `loop = true`). The HTML `<audio loop>` element leaves audible gaps, so it's not used.
- Click-track toggle at the loop's BPM, to hear the grid.
- Badges for requested vs delivered key and BPM. Corrections shown plainly: "stretched +2.1%, tuned −14 cents."
- Actions: Keep, Reject, stars (1–5), Variation (subtle / medium / bold), Fix bars, Download (WAV / MIDI / raw).

### 11.3 Interaction details
- Keyboard: `Space` play/stop · `1–4` select candidate · `K` keep · `R` reject · `D` download.
- On page load, call `POST /v1/wake`, so the GPU cold start happens while the user is typing.
- Desktop-first, usable on mobile.
- Auth: a single bearer token (`ENGINE_API_TOKEN`) entered once and kept in `localStorage`. Modal's proxy auth can front the whole app as a second layer. Magic-link auth arrives only with multi-user (§18).

---

## 12. Data Model (SQLite on a Modal Volume)

SQLite in WAL (write-ahead logging) mode at `/data/ee.db`, written only by the single FastAPI container. GPU containers return results to it over Modal function calls, so there's one writer. Schema versions are managed by plain numbered SQL migrations in `engine/migrations/`. The schema is written so a later move to Postgres is a copy, not a rewrite.

```sql
pragma journal_mode = wal;
pragma foreign_keys = on;

create table requests (
  id              text primary key,                  -- uuid4
  created_at      text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  completed_at    text,
  mode            text not null check (mode in ('prompt','composed','reskin','variation','fix')),
  raw_text        text not null,
  overrides       text not null default '{}',        -- json
  spec            text,                              -- json LoopSpec; null until parsed
  parent_loop_id  text references loops (id) on delete set null,
  upload_path     text,                              -- re-skin source audio
  status          text not null default 'queued'
                  check (status in ('queued','parsing','composing','generating','conforming','done','failed')),
  error           text,
  llm_model       text,
  llm_usage       text,                              -- json: input / output / cache tokens
  gpu_seconds     real,
  batches_run     integer not null default 0
);

create table loops (
  id                 text primary key,
  request_id         text not null references requests (id) on delete cascade,
  created_at         text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  candidate_index    integer not null,
  status             text not null check (status in ('passed','rejected')),
  reject_reasons     text not null default '[]',     -- json array

  -- what the delivered file is
  category           text not null check (category in ('instrument','texture','one_shot')),
  instrument_family  text,
  instrument_type    text,
  genre              text,
  moods              text not null default '[]',     -- json array
  key_tonic          text,                           -- 'E', 'Bb', 'F#'
  key_mode           text,                           -- 'minor', 'major', 'dorian', ...
  bpm                real,
  time_signature     text not null default '4/4',
  bars               integer check (bars in (4, 8)),
  length_samples     integer,
  filename           text,

  -- provenance
  provider           text not null,                  -- 'sa3-medium-modal' | 'sa3-medium-fal' | 'sa3-large-api' | 'minimax-music3-fal'
  model_revision     text not null,                  -- HF revision + repo commit SHA
  gen_prompt         text not null,                  -- SA3 prompt, or MiniMax structured caption
  seed               integer,
  steps              integer,
  duration_s         real,
  init_noise_level   real,
  init_audio_sha256  text,
  lora               text,                           -- json [{id, strength}]

  -- analysis + processing
  analysis_raw       text,                           -- json: bpm, drift, key, strength, tuning, lufs, true peak, purity, vocal, stereo
  conform_ops        text,                           -- json: stretch ratio, semitones, cents, window start, tail wrap, gain
  analysis_final     text,                           -- json, re-measured after conform
  score              real,

  -- files (paths under /data)
  wav_path           text,
  raw_path           text,
  midi_path          text,
  preview_path       text,
  peaks              text,                           -- json
  files_purged_at    text,

  -- curation
  kept               integer,                        -- null / 0 / 1
  stars              integer check (stars between 1 and 5),
  favorite           integer not null default 0,
  used_in_track      text,
  notes              text
);

-- Phase 3
create table loras (
  id               text primary key,
  created_at       text not null default (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  name             text not null unique,
  base_checkpoint  text not null,                    -- 'medium-base'
  dataset_manifest text not null,                    -- json: files, captions, ownership proof
  train_config     text not null,                    -- json
  storage_path     text not null,
  notes            text
);

create index loops_library_idx on loops (status, kept, instrument_family, key_tonic, key_mode, bpm);
create index loops_request_idx on loops (request_id);
create index requests_created_idx on requests (created_at desc);
```

- **Backups:** a nightly Modal cron copies `ee.db` plus kept loops to a dated folder on the volume, and `modal volume get` can pull everything to local disk. Volumes persist independently of deploys.
- **Retention:** full audio for passed-but-not-kept and rejected candidates is purged after 7 days (`files_purged_at` is set). Metadata, prompt, and seed stay forever for learning and reproducibility. Kept loops are never purged.
- **Folders on `ee-data`:** `loops/` (WAV, MP3, peaks), `raw/` (FLAC), `midi/`, `uploads/`, `loras/`, `backups/`.
- **Multi-user later:** `requests` gains `user_id`, and the whole schema ports to Supabase Postgres with row-level security. Nothing in the app assumes SQLite beyond `db.py`.

---

## 13. API (FastAPI on Modal)

The browser calls the Modal web endpoint directly with `Authorization: Bearer ENGINE_API_TOKEN`. The same FastAPI app serves the static frontend at `/`.

| Method | Path | Body / Query | Returns |
|---|---|---|---|
| POST | `/v1/wake` | none | `202`, spawns a GPU container warm-up |
| POST | `/v1/requests` | `{text, mode, overrides, candidates}` | `202 {request_id}` |
| GET | `/v1/requests/{id}` | none | status, spec (assumptions, pushback), loops |
| POST | `/v1/uploads` | multipart WAV ≤ 30 s (P2) | `{upload_path}` |
| POST | `/v1/loops/{id}/variations` | `{strength: subtle\|medium\|bold, text?}` (P2) | `202 {request_id}` |
| POST | `/v1/loops/{id}/fix` | `{start_bar, end_bar, text?}` (P2) | `202 {request_id}` |
| POST | `/v1/loops/{id}/companion` | `{text}` e.g. "a guitar that fits" | `202 {request_id}` |
| GET | `/v1/loops` | `family, instrument, key, mode, bpm_min, bpm_max, mood, bars, kept, favorite, compatible_with, cursor` | paginated loops |
| PATCH | `/v1/loops/{id}` | `{kept, stars, favorite, used_in_track, notes}` | loop |
| GET | `/v1/loops/{id}/download` | `?format=wav\|midi\|raw` | file stream with `Content-Disposition` |
| GET | `/v1/health` | none | versions, model revision, warm state |

- **Job lifecycle:** `queued → parsing → (composing) → generating → conforming → done | failed`. The GPU function reports each transition back to the web container, which writes it to SQLite. The frontend polls `GET /v1/requests/{id}` every second (a request lasts 15–60 s, so polling is fine).
- **Downloads:** `/v1/loops/{id}/download` streams the file from the volume with a `Content-Disposition` filename. No signed URLs needed.
- **Variation strength → `init_noise_level`:** subtle 0.4, medium 0.6, bold 0.8. Initial values based on the SA3 MLX guidance of "0.4–0.8 typical"; calibrate in Phase 2.
- **Fix bars:** inpaints the conformed loop at exact bar boundaries with the same prompt (or a new `text`), then re-conforms.

---

## 14. Tech Stack, Hosting & Cost

### 14.1 Stack
| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js (App Router, latest stable, `output: 'export'`), TypeScript, Tailwind CSS | Same stack as Charlie's other projects; static export needs no Node server |
| Waveforms / playback | wavesurfer.js + Web Audio API | Bar-accurate display, gapless loops |
| Frontend hosting | Served as static files by the FastAPI app on Modal | One deployable, $0 |
| Backend | Python 3.11, FastAPI, Pydantic v2, `uv` | SA3 is Python. Pydantic gives one schema for LLM, API, and DB |
| Database + storage | SQLite (WAL) + files on a Modal Volume | Single user, single writer, zero services |
| GPU hosting | Modal (serverless, per-second billing), L4 GPU, inside the $30/mo Starter credit | Zero idle cost, Python-native deploys, volumes for weights |
| Generator | `stable-audio-3` from GitHub, pinned commit SHA · checkpoint `medium` · PyTorch 2.7.1 · Flash Attention 2 | Best open-weights stem-capable model |
| LLM | Anthropic Python SDK · `claude-opus-5` default, per-route override · structured outputs · prompt caching | Strong musical reasoning; schema-valid output; half Fable's price |
| Beat / downbeat | Beat This! | State-of-the-art beat and downbeat tracking |
| Key / tuning | Essentia | Mature key profiles, tuning frequency |
| Loudness | pyloudnorm | ITU-R BS.1770 compliant |
| Stem purity | Demucs `htdemucs_6s` | Has piano and guitar stems |
| Time/pitch | Rubber Band v3 (R3 engine) | Best-in-class transparent stretching and shifting |
| MIDI | `pretty_midi`, FluidSynth + GM SoundFont | Composed-mode render |
| Ranking (P2) | LAION-CLAP | Text-audio similarity |
| Monitoring | Modal logs + Sentry free tier | Error visibility |

### 14.2 Repository Layout
```
east-emerald-music/
├── CLAUDE.md
├── docs/prd.md
├── web/                          Next.js app, static export → engine/static/
│   ├── app/                      (create, library, loops/[id])
│   ├── components/               (PromptBar, CandidateCard, LoopPlayer, Waveform, Filters)
│   └── lib/                      (engine client, audio engine)
└── engine/
    ├── pyproject.toml
    ├── app.py                    Modal app: image, volumes, secrets, web app, GPU class, cron
    ├── static/                   built frontend (gitignored, produced by `npm run build`)
    ├── migrations/               001_init.sql …
    ├── engine/
    │   ├── spec.py               LoopSpec
    │   ├── db.py                 SQLite access + migrations
    │   ├── intent.py             Claude call + system prompt
    │   ├── prompts.py            Prompt compiler
    │   ├── compose/              theory.py · voicing.py · patterns.py · humanize.py · midi.py · render.py
    │   ├── generate/             base.py · sa3_modal.py · sa3_fal.py · sa3_large_stability.py · minimax_fal.py
    │   ├── analyze/              tempo.py · key.py · tuning.py · loudness.py · purity.py · stereo.py
    │   ├── conform/              stretch.py · window.py · seam.py · level.py
    │   ├── gate.py
    │   ├── export.py
    │   └── bench/                suite.yaml · run.py · report.py · listening_sheet.py
    └── tests/                    fixtures rendered from MIDI with known BPM/key
```

### 14.3 Modal Deployment Design
- **App:** a single Modal app, `east-emerald-engine`.
- **Image:**
  - CUDA 12.6, Python 3.11 (confirm against the SA3 repo's `.python-version`)
  - PyTorch 2.7.1 + torchaudio 2.7.1, plus a prebuilt Flash Attention 2 wheel matching torch, CUDA, and Python
  - `stable-audio-3` pinned to a commit SHA
  - System packages: `rubberband-cli`, `ffmpeg`, `fluidsynth`
  - Python packages: `essentia`, `beat_this`, `demucs`, `pyloudnorm`, `soundfile`, `librosa`, `pretty_midi`, `anthropic`, `fastapi`, `fal-client`
- **Weights volume:** `sa3-weights` holds the Hugging Face cache. A one-time `download_weights` function populates it using `HF_TOKEN` from a Modal Secret. Cold starts never download.
- **Data volume:** `ee-data` holds `ee.db` and all audio. Mounted read-write on the web container and the GPU class; `volume.commit()` after every write.
- **GPU class `Engine`:** runs on an L4 (Ada generation, 24 GB, supports Flash Attention 2).
  - At container start it loads SA3 Medium, Beat This!, and Demucs.
  - Idle scale-down window of **2 minutes** (the biggest lever on cost), max 2 containers.
  - Evaluate Modal memory snapshots to cut cold starts.
- **Startup self-test:** generate a 2 s clip and check spectral flatness to catch the "static glitch" Flash Attention failure. If it fails, the container fails fast.
- **CPU web app:** FastAPI mounted as an ASGI app, `max_containers=1` (the single SQLite writer). It serves `static/`, validates the bearer token, and dispatches GPU work with `.spawn()`.
- **Cron:** nightly backup of `ee.db` + kept loops to `backups/`, and the 7-day purge of unkept audio.
- **Why not T4:** it's Turing-generation and has no Flash Attention 2 support. A10G is an acceptable alternative to L4.
- **Starter plan limits that matter:** $30/mo credit, no rollover, 8 web endpoints, 5 cron jobs, 10-way GPU concurrency. All well above what we need. When credits run out with no card on file, workloads stop rather than bill, which is a safe default for Phase 0.

### 14.4 Cost Model (estimates, validate in Phase 0)
GPU usage per request on a warm L4: ~15 s of generation + conform, plus the 2-minute idle window, so a request costs ~2.25 minutes of GPU unless another request lands inside the window. At 30 requests/day, that's ~34 GPU hours/month worst case.

| Item | Basis | Estimate |
|---|---|---|
| GPU | Modal L4 at $0.000222/s ≈ $0.80/hr × ~34 hrs | ≈ $27, **inside the $30/mo Starter credit → $0** |
| Web container + volume | CPU at $0.0000131/core-s (0.125 core minimum) while serving; storage $0.09/GiB-month after 1 TiB free | ≈ $1–3, also inside the credit |
| Claude | Opus 5 at $5 / $25 per million input / output tokens (thinking bills as output). ~$0.03–0.05 per Prompt-mode request, ~$0.08–0.15 per Composed request | ≈ $30–60/mo at 30 requests/day, with cached system prompt |
| Frontend | Static files served by the engine | $0 |
| **Total** | | **≈ $30–60/mo, all of it Claude tokens** |

If usage doubles, GPU spills past the credit by ~$25/mo. That is still cheaper than any always-on GPU.

**Takeaway:** GPU time is effectively free at our scale. **Claude tokens are the only real cost.** Measure `usage` from day one, cache the system prompt, and tune effort per route before cutting anything else.

### 14.5 Alternatives Considered
| Option | Verdict |
|---|---|
| **fal.ai hosted SA3 Medium** ($0.0376 per generation ≈ $4.50/mo at our volume) | Fallback provider and Phase 0 baseline. Zero ops and nearly free, but no LoRA, no custom container, and less control of the inpaint pipeline and batching. If Phase 0 shows Modal cold starts hurt, fal becomes the Phase 1 default and Modal returns for LoRA in Phase 3. |
| **Stability API, SA3 Large** (26 credits ≈ $0.26 per generation, reported) | Only if it wins the Phase 0 blind test. API-only, no LoRA. |
| **MiniMax Music 3 via fal.ai** (`minimax/music-3`; MiniMax's own API is closed to new users since 2026-08-20) | Phase 0 blind test only, as an "idea sketch" provider: instrumental flag, solo-instrument caption, Demucs isolation, then the normal gates. Self-hosting is rejected: ~27 GB weights, 24 GB+ VRAM, the repo recommends two GPUs, autoregressive generation runs near realtime, 32 kHz output, and no a2a/inpaint/LoRA. Any UI that ships MiniMax output must display "MiniMax-Music3" per its license. |
| **GPU VPS: RunPod pod, Hetzner GEX44, Vast.ai** | Rejected. Always-on 24 GB GPUs cost ~$195/mo (RunPod A5000), ~€184/mo + setup (Hetzner GEX44, 20 GB), or ~$0.22/hr on Vast.ai with hosts able to reclaim the machine. Our workload is bursty, so per-second serverless wins by an order of magnitude. |
| **CPU VPS (Hetzner CX22 ≈ €4/mo)** | Can't run SA3 Medium (CUDA + Flash Attention required). Could host the web app and SQLite, but that only adds a server to maintain when Modal serves them for free. |
| **RunPod Serverless** | Viable second choice (flex workers from ~$0.58/hr for 16 GB class), no free credit, more ops work than Modal. Revisit if Modal pricing or limits change. |
| **Free notebook GPUs (Kaggle 30 hrs/week, Colab)** | T4 GPUs, no Flash Attention 2, so SA3 Medium can't run. Not an app backend in any case. |
| **Lightning AI free tier (15 credits/mo ≈ 8 hrs on A10G/L4)** | Fine for one-off Phase 0 benchmark runs if Modal credit runs short. Not an app backend (4-hour restarts). |
| **Hugging Face Space on ZeroGPU** | Free-ish demo hosting on shared H200s with daily quotas and queueing. Worth a look for a public demo later. Not chosen for a private production tool because of quotas and no persistent app state. |
| **Local Mac via the SA3 MLX build** | Official Apple Silicon build. Medium on an 8 GB M1 does ~5 s per 10 s clip at 3.8 GB peak RAM, with ~6.7 GB of weights. Not viable until ≥ 20 GB of disk is freed. Later use: offline sketching, and the repo's Ableton AudioInserter. |
| **SA3 Small models** | Rejected for music. The tech report says Small "performs noticeably worse." Retest `small-sfx` for one-shots in Phase 3. |
| **Supabase + Vercel** | Deferred until multi-user. See §12 for the port path. |

### 14.6 Environment Variables
| Name | Where |
|---|---|
| `ANTHROPIC_API_KEY` | Modal Secret |
| `HF_TOKEN` | Modal Secret (gated model download) |
| `ENGINE_API_TOKEN` | Modal Secret; the user pastes it into the app once |
| `LLM_MODEL_INTENT`, `LLM_MODEL_COMPOSE` | Modal Secret or app config, default `claude-opus-5` |
| `FAL_KEY`, `STABILITY_API_KEY` | Modal Secret (optional providers, incl. MiniMax via fal) |

---

## 15. Licensing, Copyright & YouTube

Not legal advice. Confirm with a music attorney before selling sample packs, licensing loops to third parties, or registering anything in Content ID.

1. **Stable Audio 3 Community License** (Small and Medium weights):
   - Free commercial use for individuals and organizations under **$1M annual revenue**, and Stability's terms count affiliated entities together. Above that, an Enterprise License is required.
   - Per the license, **you own the outputs.**
   - Register for commercial use per the license terms.
   - Output may not be used to train a competing foundation model. Fine-tunes and LoRAs are allowed.
   - Large is governed by Stability's API terms.
2. **Human authorship.** Current U.S. Copyright Office guidance says material lacking human authorship isn't copyrightable. So a raw engine loop is effectively unownable. What we own is the finished record: the producer's chops, arrangement, added parts, and mix. **Every East Emerald track must have substantial human production on top of engine starters.**
3. **Content ID.** Never register raw loops or lightly-edited loops. Other users of the same model can produce similar material, and false claims burn the channel. Only consider registering finished tracks with substantial human authorship, and expect distributor scrutiny.
4. **YouTube monetization.** YouTube's policy against mass-produced, inauthentic content requires human creative direction. Our workflow (engine starter + human producer) is the right side of that line. Follow YouTube's current disclosure requirements for synthetic content.
5. **Provenance is our evidence.** The `loops` table records prompt, seed, model revision, timestamps, and conform ops, and `used_in_track` links starters to releases. Keep it forever.
6. **Training data.** SA3 was trained on 806,284 licensed AudioSparx recordings and 472,618 Creative Commons Freesound recordings, with copyrighted music filtered out. That lowers infringement risk but doesn't eliminate it. Anything that sounds like a known song gets rejected by ear.
7. **Dependency licenses.** Rubber Band (GPL-2.0) and Essentia (AGPL-3.0) are fine for a private, internal service. If the engine is ever sold or offered to outside users, license Rubber Band commercially and replace Essentia or comply with AGPL first.
9. **MiniMax Music 3 Community License** (if the provider is ever enabled beyond Phase 0): commercial use is allowed under $20M annual revenue, and the product UI must display "MiniMax-Music3". Since MiniMax output is a full mix that we stem-separate, treat it with the same human-authorship rules as SA3 output.
8. **LoRA datasets.** Use only recordings East Emerald owns outright: our own playing, or session players under written work-for-hire or assignment agreements. Store proof in `loras.dataset_manifest`.

---

## 16. Roadmap & Acceptance Gates

### 16.1 Phase 0: Validation Spike (target: 2–3 days of build, then listening)
**Goal:** prove a model can make loops worth keeping before we build a UI. Runs entirely inside Modal's free credit plus a few dollars of fal.ai and Stability API calls.

**Deliverables**
- A Modal GPU function running SA3 Medium, with the weights volume and startup self-test.
- The analysis module, with CPU unit tests against MIDI-rendered fixtures of known BPM and key.
- `generate/` providers for fal (SA3 Medium and MiniMax Music 3) and Stability (Large), each behind the same interface.
- The benchmark runner and a blind listening sheet (candidates shuffled, provider hidden).
- `docs/phase0-report.md` with the measured results, calibrated thresholds, cost per request per provider, and go/no-go per gate.

**Core benchmark suite** (12 prompts × 4 candidates = 48 clips):

| # | Request | Key | BPM | Bars |
|---|---|---|---|---|
| 1 | Lo-fi upright piano, soft jazzy chords, tape (§9.4) | E minor | 80 | 8 |
| 2 | Felt piano, intimate, cinematic | D minor | 70 | 8 |
| 3 | Rhodes, neo-soul voicings, warm tremolo | Eb major | 78 | 8 |
| 4 | Grand piano, emotional ballad arpeggios | Db major | 72 | 8 |
| 5 | Wurlitzer, chillhop chords | F major | 88 | 8 |
| 6 | House piano chord stabs | A minor | 124 | 4 |
| 7 | Steel-string fingerstyle, hopeful (§9.4) | D major | 96 | 8 |
| 8 | Nylon-string bossa nova comping | A minor | 130 | 4 |
| 9 | Clean electric neo-soul chord slides | C minor | 84 | 8 |
| 10 | Jazz archtop chord melody, lo-fi | G major | 85 | 8 |
| 11 | Strummed acoustic folk in 6/8 | E major | 100 | 8 |
| 12 | Ambient electric guitar swells, free time | E minor | 70 | 8 |

**A/B experiments**
- `TrackType:` prefix vs suffix (prompts 1, 7)
- Key named in the prompt vs omitted (all 12, measure key hit rate)
- The word "loop" included vs omitted (prompts 1, 5, 8)
- Medium on Modal vs Medium on fal.ai (sanity parity, prompts 1–3)
- Medium vs Large via API, blind (prompts 1, 3, 4, 7, 9, 10)
- **SA3 Medium vs MiniMax Music 3 (via fal), blind, on prompts 1, 3, 4, 7, 9, 10.** MiniMax gets a structured caption (genre, BPM, key, "solo <instrument> only, no drums, no bass, no vocals" arrangement, instrumental flag) and its output is Demucs-isolated before scoring. Score separately on (a) tone realism, (b) harmonic interest, (c) stem purity after isolation, (d) tempo/key hit rate. Decision rule: MiniMax earns a place only if it wins (b) by a clear margin AND passes (c) ≥ 70% of the time. Otherwise it's dropped and the provider file stays as reference.
- Composed-mode `init_noise_level` sweep 0.4 / 0.5 / 0.6 / 0.7 / 0.8 on progressions from §10.2 (melancholic, warm lo-fi, hopeful)
- Vinyl crackle texture: `medium` vs `small-sfx`
- Cold-start timing on Modal with and without memory snapshots, vs fal.ai queue time, to decide the Phase 1 default provider

### 16.2 Phase 0 Gates
| Gate | Pass criterion | If it fails |
|---|---|---|
| G1 Tone | ≥ 50% of raw candidates score ≥ 4/5 "usable sound" in blind listening | Blind-test Large. If Large clearly wins, add it as a "premium render" provider. If neither passes, stop and rethink. |
| G2 Tempo | ≥ 70% of rhythmic candidates within ±6% (octave-folded) with drift ≤ 3% | Raise the batch count, add time-map (variable) stretching, or lean on Composed mode earlier. |
| G3 Key | ≥ 60% of candidates within correctable range (≤ 2 semitones, same mode) | Composed mode becomes Phase 1 instead of Phase 2. |
| G4 Stem purity | ≥ 80% of `TrackType: Instrument` candidates contain only the requested instrument (ear check, then calibrate Demucs) | Add Demucs extraction as a conform step. |
| G5 Composed | At the best noise level, ≥ 80% keep the chord roots (chroma vs MIDI) AND ≥ 4/5 realism | Drop Composed mode. Move the LoRA-on-real-recordings work earlier. |
| G6 Latency | Warm L4: 4 × 8-bar candidates generated + conformed in ≤ 15 s | Try A10G/L40S, TensorRT, or fewer candidates per batch. |
| G7 Cost | Full benchmark (≈ 120 clips across experiments) costs ≤ $15 total, and the projected monthly GPU spend at 30 requests/day fits inside the $30 credit | Shorten the idle window, or make fal.ai the Phase 1 default and keep Modal for LoRA work only. |

### 16.3 Phase 1: MVP (Prompt mode)
- Everything in §5's P1 column.
- **Intent eval:** 30 fixed requests with programmatic checks. All must pass hard constraints: bars ∈ {4, 8}, overrides honored, textures split out, no negations or artist names in compiled prompts, 4 variants present, assumptions logged when fields were missing.
- **Acceptance:**
  - 100% of delivered loops pass the DAW Loop Test.
  - Keeper rate is measured over 2 weeks of real use.
  - Warm and cold latency targets are met (§2.3).

### 16.4 Phases 2 & 3
- **Phase 2 (Craft):** Composed mode + MIDI export, Re-skin, Variation, Fix bars, companion loops ("fits this"), textures, CLAP + preference ranking, inpaint seam healing. Acceptance: keeper rate ≥ 80%, and every Composed candidate passes `harmony_drift`.
- **Phase 3 (Signature):**
  - **East Emerald LoRA:** 50–150 owned clips (4–8 bars, captioned in the §9 format; the repo's minimum is ~20–50). Train on `medium-base` with `dora-rows` rank 16 for 1,000–2,000 steps on a Modal GPU (~6.5 GB VRAM). Exclude the `seconds_total` conditioner if the dataset is small. Blind A/B against no-LoRA at strengths 0.5 / 0.75 / 1.0.
  - **Expansion:** more instrument families, one-shots and sound design, pack export, drum loops with transient-aware conformance, and DAW integration exploration.

### 16.5 DAW Loop Test (definition)
1. Import the delivered WAV into a DAW project set to the loop's BPM, with **warping/time-stretch off**.
2. Loop it 16 times against the DAW metronome.
3. **Pass** only if all of these hold:
   - no audible click at the seam
   - drift vs the click ≤ 5 ms after 16 repeats
   - file length exactly equals the §7.6 formula
   - key matches the filename
   - tuning is within ±5 cents

---

## 17. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Model quality ceiling ("correct, not interesting") | High | High | Composed mode, curation, prompt variants, LoRA, Large blind test |
| Tempo drift within a clip | Medium | High | Drift gate. Time-map stretching in Phase 2. Composed mode. |
| Key/harmony not controllable by text | High | Medium | Conformance for Prompt mode; Composed mode for exact harmony |
| Instrument bleed or vocal textures | Medium | Medium | Demucs gates; "solo" phrasing; extraction fallback |
| Near-identical candidates | High | Medium | Per-batch prompt variants across defined axes |
| Flash Attention install breaks silently | Medium | High | Pinned wheel, startup spectral self-test |
| Cold-start latency | Medium | Low | Wake on page load, weights volume, memory snapshots |
| Claude token costs creep | Medium | Medium | Usage logging, prompt caching, per-route effort |
| License terms or pricing change | Low | High | Pin model revision; provider interface allows swaps; re-check terms quarterly |
| YouTube / Content ID policy shifts | Medium | High | Human-produced finished tracks only; provenance; no raw-loop registration |
| Dev Mac disk is full (5.5 GB free) | Certain | Medium | Nothing heavy runs locally; free space for DAW work regardless |
| Modal free credit shrinks or Starter limits change | Low | Medium | fal.ai provider is a drop-in at ~$4.50/mo; RunPod Serverless is the second option |
| SQLite on a network volume misbehaves (locking, latency) | Low | Medium | Single writer container, WAL mode, nightly backups; port to Postgres is a copy |

**Removed from v1.0:** Supabase and Vercel risks, since neither is in the stack anymore.

---

## 18. Open Questions (for Charlie)

1. **Users:** just you, or East Emerald producers too? A second user is the only thing that brings Supabase, Vercel, and magic-link auth back into the stack.
2. **Primary DAW?** This affects export metadata, drag-and-drop behavior, and whether we explore the repo's Ableton integration later.
3. **Revenue threshold:** is the combined annual revenue of all your entities comfortably under $1M? This decides Community vs Enterprise license.
4. **LoRA dataset (Phase 3):** who can record 50–150 short clips of piano and guitar that East Emerald owns outright?
5. **Budget ceiling:** the plan is ~$30–60/month, nearly all Claude tokens, with GPU inside Modal's free credit. Acceptable? And do you want a card on Modal (spend continues past $30) or no card (workloads stop at $30)?
6. **Git:** this folder currently sits inside a git repository rooted at your home directory. Initialize a dedicated repo for this project before Phase 0?
7. **Accounts to create before Phase 0:** Modal (free), Hugging Face (accept the SA3 gated-model terms, create a token), fal.ai (a few dollars of credit), and Stability API (only for the Large blind test, ~$2).

---

## 19. Glossary

| Term | Meaning |
|---|---|
| A440 | Standard tuning: the A above middle C = 440 Hz |
| ACID chunk | WAV metadata block storing tempo, root note, and beat count, which some DAWs and sample managers read |
| Anacrusis / pickup | Notes that lead into bar 1 from before the downbeat |
| ASGI | Asynchronous Server Gateway Interface, how FastAPI runs on Modal |
| Audio-to-audio (a2a) | Generating new audio guided by an input recording plus a text prompt |
| BPM | Beats per minute, always quarter-note based in this project |
| Camelot wheel | DJ key-compatibility system; neighbors mix harmonically |
| CFG | Classifier-free guidance, a prompt-adherence strength knob (ignored by post-trained SA3) |
| CLAP | Contrastive Language-Audio Pretraining, a model scoring how well audio matches text |
| Chroma | 12-bin pitch-class energy profile used for key and harmony analysis |
| CUDA | NVIDIA's GPU computing platform |
| dBFS / dBTP | Decibels relative to full scale / true peak (inter-sample peak) |
| DAW | Digital Audio Workstation (Ableton, Logic, FL Studio) |
| DiT | Diffusion Transformer, SA3's generator network |
| Flash Attention 2 | Fast attention implementation required by SA3 Medium |
| Inpainting | Regenerating a selected time range while keeping the rest |
| LoRA / DoRA | Low-Rank Adaptation (and its weight-decomposed variant), small fine-tunes that add a style to a base model |
| LUFS | Loudness Units relative to Full Scale, perceived loudness per ITU-R BS.1770 |
| MIDI | Musical Instrument Digital Interface, note data rather than audio |
| MLX | Apple's machine learning framework for Apple Silicon |
| p50 | Median (50th percentile) |
| PPQ | Pulses per quarter note, MIDI timing resolution |
| R3 | Rubber Band's highest-quality ("finer") time-stretch engine |
| RLS | Row Level Security in Postgres |
| SA3 | Stable Audio 3 |
| SAME | Semantic-Acoustic Music Encoder, SA3's audio autoencoder |
| Stem | An isolated single-instrument audio part |
| Turnaround | The final bar's harmonic pull back to bar 1 |
| VRAM | GPU memory |

---

## 20. Sources (verified 2026-09-12)

- Stable Audio 3 repository: https://github.com/Stability-AI/stable-audio-3
- Inference guide: https://github.com/Stability-AI/stable-audio-3/blob/main/docs/workflows/inference.md
- Prompting guide: https://github.com/Stability-AI/stable-audio-3/blob/main/docs/guides/prompting.md
- LoRA guide: https://github.com/Stability-AI/stable-audio-3/blob/main/docs/workflows/lora.md
- MLX (Apple Silicon) build: https://github.com/Stability-AI/stable-audio-3/blob/main/optimized/mlx/README.md
- SA3 Medium model card: https://huggingface.co/stabilityai/stable-audio-3-medium
- Stable Audio 3 tech report: https://arxiv.org/abs/2605.17991
- Stability AI Community License: https://stability.ai/license
- Stability API pricing: https://platform.stability.ai/pricing
- fal.ai SA3 Medium endpoint: https://fal.ai/models/fal-ai/stable-audio-3/medium/text-to-audio
- Modal pricing: https://modal.com/pricing
- MiniMax Music 3 repository: https://github.com/MiniMax-AI/MiniMax-Music3
- MiniMax Music 3 model card: https://huggingface.co/MiniMaxAI/MiniMax-Music3
- MiniMax Music 3 on fal.ai: https://fal.ai/models/minimax/music-3
- MiniMax API pricing (closed to new users since 2026-08-20): https://platform.minimax.io/docs/guides/pricing-paygo
- RunPod pricing: https://www.runpod.io/pricing
- Dubspot review: https://blog.dubspot.com/stable-audio-3-review
- Release coverage: https://www.digitalmusicnews.com/2026/05/21/stability-ai-3-0-release/
