"""One request end to end, on the GPU container (PRD §7). Writes a job file the API reads.

Modes:
  prompt    intent → compile → generate → analyze → conform → export (+ chord MIDI as written)
  composed  intent → compose (MIDI + seed render) → SA3 audio-to-audio → harmony gate → export
  midi      intent → compose → MIDI only (no GPU; see midi_request)
  variation parent loop audio → SA3 audio-to-audio at low noise → known-grid conform (no Claude)
"""

from __future__ import annotations

import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from engine.analyze import analyze
from engine.analyze.purity import purity_for, stem_shares
from engine.conform.pipeline import conform_clip
from engine.export import loop_filename, write_raw_flac, write_wav24
from engine.generate.base import GenerateRequest
from engine.intent import parse_intent
from engine.prompts import compile_prompts
from engine.spec import LoopSpec

STRENGTH_NOISE = {"subtle": 0.35, "medium": 0.5, "bold": 0.65}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _peaks(x: np.ndarray, n: int = 400) -> list[float]:
    mono = np.abs(x).max(axis=0)
    step = max(1, len(mono) // n)
    return [float(mono[i:i + step].max()) for i in range(0, len(mono) - step + 1, step)][:n]


class JobWriter:
    def __init__(self, data_root: Path, request_id: str, commit=None):
        self.path = data_root / "jobs" / f"{request_id}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.commit = commit
        self.state: dict = {"id": request_id, "status": "queued", "loops": [], "created_at": _now()}

    def update(self, **kw):
        self.state.update(kw)
        self.path.write_text(json.dumps(self.state))
        if self.commit:
            self.commit()


def _loop_context_audio(loop_wav: Path, spec: LoopSpec, sr: int = 44100) -> np.ndarray:
    """Parent loop as SA3 seed: pre-roll = its last bar, tail = its first bar (same as the MIDI seed)."""
    import soundfile as sf

    y, got = sf.read(loop_wav, dtype="float32", always_2d=True)
    y = y.T
    bar = int(round(spec.bar_seconds * sr))
    ctx = np.concatenate([y[:, -bar:], y, y[:, :bar]], axis=1)
    n = int(round(spec.generate_seconds * sr))
    if ctx.shape[1] < n:
        ctx = np.pad(ctx, ((0, 0), (0, n - ctx.shape[1])))
    return ctx[:, :n]


def _loop_record(spec: LoopSpec, request_id: str, idx: int, clip, a, shares, pur, res, harmony, midi_rel, noise) -> dict:
    return {
        "id": uuid.uuid4().hex, "request_id": request_id, "created_at": _now(), "candidate_index": idx,
        "status": "passed" if res.gate.passed else "rejected",
        "reject_reasons": res.gate.reasons, "warnings": res.gate.warnings,
        "category": spec.category, "instrument_family": spec.instrument.family,
        "instrument_type": spec.instrument.type, "genre": spec.genre, "moods": spec.moods,
        "key_tonic": spec.key.tonic, "key_mode": spec.key.mode, "bpm": spec.bpm,
        "time_signature": spec.time_signature, "bars": spec.bars,
        "length_samples": spec.loop_samples if res.loop is not None else None,
        "provider": clip.provider, "model_revision": clip.model_revision, "gen_prompt": clip.prompt,
        "seed": clip.seed, "steps": clip.steps, "duration_s": clip.duration_s,
        "init_noise_level": noise, "midi_path": midi_rel,
        "analysis_raw": {**a.to_dict(), "stem_shares": shares, "purity": pur, "harmony": harmony},
        "conform_ops": res.ops,
        "analysis_final": res.analysis_final.to_dict() if res.analysis_final else None,
        "score": res.score,
    }


def run_request(
    *,
    request_id: str,
    text: str,
    overrides: dict,
    mode: str,
    parent: dict | None,
    generator,
    data_root: Path,
    candidates: int = 4,
    max_batches: int = 2,
    commit=None,
    session_id: str | None = None,
) -> dict:
    job = JobWriter(data_root, request_id, commit)
    job.update(status="parsing", mode=mode, raw_text=text, overrides=overrides, session_id=session_id,
               parent_loop_id=(parent or {}).get("id"))
    t_gpu = 0.0
    try:
        # --- spec: from Claude, or inherited verbatim for variations / melodies
        melody = None
        if mode in ("variation", "melody") and parent and parent.get("spec"):
            spec = LoopSpec.model_validate(parent["spec"])
            spec.generation_mode = "composed"
            intent_model, usage = None, None
            if mode == "melody":
                from engine.compose.melody import compose_melody
                if not spec.harmony:
                    raise RuntimeError("melody needs a loop with a chord progression")
                lead = overrides.get("instrument_type") or spec.instrument.type
                spec.instrument.type = lead
                spec.instrument.family = {"rhodes": "keys", "wurlitzer": "keys"}.get(lead, "guitar" if "guitar" in lead or lead == "jazz_archtop" else "piano")
                spec.instrument.techniques = ["single-note melody line", "expressive phrasing"]
                spec.variants = []
                job.update(status="composing")
                melody = compose_melody(spec, instruction=str(overrides.get("text", "")))
                intent_model, usage = "claude-opus-5", melody.usage
                job.update(melody=melody.description, melody_fixes=melody.fixes)
        else:
            intent = parse_intent(text, overrides=overrides, parent=parent)
            spec, intent_model, usage = intent.spec, intent.model, intent.usage
            if mode == "companion" and overrides.get("companion") == "drums":
                spec.category = "drums"
                spec.instrument.family = "drums"
                spec.instrument.type = f"{spec.genre.lower().replace(' ', '_')}_drums"
                spec.generation_mode = "prompt"
        job.update(status="generating", spec=spec.model_dump(by_alias=True), llm_model=intent_model, llm_usage=usage)

        # --- seed audio: composed MIDI render, or the parent loop for variations
        composition, midi_rel, seed_audio, noise = None, None, None, None
        if mode == "melody" and melody is not None:
            from engine.compose.midi import write_midi
            from engine.compose.render import render_midi
            mdir = data_root / "midi" / request_id
            mdir.mkdir(parents=True, exist_ok=True)
            prog = {"rhodes": 4, "wurlitzer": 5, "nylon_guitar": 24, "steel_acoustic_guitar": 25, "jazz_archtop": 26,
                    "clean_electric_guitar": 27}.get(spec.instrument.type, 0)
            midi_path = write_midi(melody.notes, spec, mdir / "melody.mid", program=prog, pedal=False, name="melody")
            ctx = write_midi(melody.notes, spec, mdir / "melody_seed.mid", with_context=True, program=prog, pedal=False, name="melody")
            seed_audio = render_midi(ctx, mdir / "melody_seed.wav")
            n = int(round(spec.generate_seconds * 44100))
            seed_audio = np.pad(seed_audio, ((0, 0), (0, max(0, n - seed_audio.shape[1]))))[:, :n]
            seed_audio = (seed_audio / (float(np.abs(seed_audio).max()) + 1e-9) * 0.5).astype(np.float32)
            midi_rel = str(midi_path.relative_to(data_root))
            noise = float(overrides.get("init_noise_level") or 0.4)
            known_grid = True
            job.update(midi_path=midi_rel)
        elif mode == "variation" and parent:
            seed_audio = _loop_context_audio(data_root / parent["wav_path"], spec)
            noise = STRENGTH_NOISE.get(str(overrides.get("strength", "medium")), 0.5)
            midi_rel = parent.get("midi_path")
            known_grid = True
        elif spec.generation_mode == "composed" and spec.harmony and spec.category != "drums":
            from engine.compose.pipeline import compose
            job.update(status="composing")
            composition = compose(spec, data_root / "midi" / request_id, seed=secrets.randbits(16))
            midi_rel = str(composition.midi_path.relative_to(data_root))
            seed_audio = composition.seed_audio
            noise = float(overrides.get("init_noise_level") or 0.45)
            known_grid = True
            job.update(midi_path=midi_rel, voicings=[v.symbol for v in composition.voicings])
        else:
            known_grid = False
            if spec.harmony and spec.category != "drums":
                # Prompt mode still ships the chords as written, as MIDI (no render).
                from engine.compose.pipeline import compose
                comp = compose(spec, data_root / "midi" / request_id, seed=0, render=False)
                midi_rel = str(comp.midi_path.relative_to(data_root))
                job.update(midi_path=midi_rel, voicings=[v.symbol for v in comp.voicings])

        passed: list[dict] = []
        rejected: list[dict] = []
        batches = 0
        while batches < max_batches and len(passed) < 2:
            batches += 1
            if mode == "melody":
                from engine.compose.melody import melody_prompt
                prompts = [melody_prompt(spec)] * candidates
            else:
                prompts = compile_prompts(spec)[:candidates]
            t0 = time.time()
            req = GenerateRequest(prompts=prompts, duration_s=spec.generate_seconds)
            if seed_audio is not None:
                req.init_audio = (44100, seed_audio)
                req.init_noise_level = noise
            clips = generator.generate(req)
            t_gpu += time.time() - t0
            job.update(status="conforming", batches_run=batches)
            for k, clip in enumerate(clips):
                idx = (batches - 1) * candidates + k
                t0 = time.time()
                a = analyze(clip.audio, clip.sr, target_bpm=spec.bpm, rhythmic=spec.feel.rhythmic and not known_grid)
                shares = stem_shares(clip.audio, clip.sr)
                pur = purity_for(shares, spec.instrument.family)
                res = conform_clip(spec, clip.audio, clip.sr, a, purity=pur, vocal_share=shares.get("vocals", 0.0),
                                   known_grid=known_grid)
                harmony = None
                if (composition is not None or mode == "melody") and res.loop is not None:
                    from engine.compose.harmony_check import harmony_similarity
                    harmony = harmony_similarity(res.loop, clip.sr, spec)
                    lo_mean, lo_min = (0.55, 0.3) if mode == "melody" else (0.75, 0.5)   # a single line has sparse chroma
                    if harmony["mean"] < lo_mean or harmony["min"] < lo_min:
                        res.gate.passed = False
                        res.gate.reasons.append("harmony_drift")
                        res.loop = None
                t_gpu += time.time() - t0
                rec = _loop_record(spec, request_id, idx, clip, a, shares, pur, res, harmony, midi_rel, noise)
                raw_path = data_root / "raw" / f"{rec['id']}.flac"
                write_raw_flac(raw_path, clip.audio, clip.sr)
                rec["raw_path"] = str(raw_path.relative_to(data_root))
                if res.loop is not None:
                    fname = loop_filename(spec, descriptor="Melody" if mode == "melody" else None, id4=rec["id"][:4])
                    wav_path = data_root / "loops" / fname
                    write_wav24(wav_path, res.loop, clip.sr)
                    rec.update({"filename": fname, "wav_path": str(wav_path.relative_to(data_root)), "peaks": _peaks(res.loop)})
                    passed.append(rec)
                else:
                    rejected.append(rec)
                job.update(loops=passed + rejected)
        passed.sort(key=lambda r: -r["score"])
        job.update(status="done", loops=passed + rejected, completed_at=_now(), gpu_seconds=round(t_gpu, 2),
                   batches_run=batches)
    except Exception as e:  # noqa: BLE001
        job.update(status="failed", error=f"{type(e).__name__}: {e}", completed_at=_now())
        raise
    return job.state


def midi_request(*, request_id: str, text: str, overrides: dict, parent: dict | None, data_root: Path,
                 commit=None, session_id: str | None = None) -> dict:
    """Chord-progression MIDI generator: Claude writes the harmony, we voice it. No GPU, ~15 s."""
    from engine.compose.pipeline import compose

    job = JobWriter(data_root, request_id, commit)
    job.update(status="parsing", mode="midi", raw_text=text, overrides=overrides, session_id=session_id)
    try:
        intent = parse_intent(text, overrides={**overrides, "generation_mode": "composed"}, parent=parent)
        spec = intent.spec
        spec.generation_mode = "midi"
        if not spec.harmony:
            raise RuntimeError("no harmony plan returned")
        job.update(status="composing", spec=spec.model_dump(by_alias=True), llm_model=intent.model, llm_usage=intent.usage)
        comp = compose(spec, data_root / "midi" / request_id, seed=secrets.randbits(16), render=False)
        midi_rel = str(comp.midi_path.relative_to(data_root))
        rec = {
            "id": uuid.uuid4().hex, "request_id": request_id, "created_at": _now(), "candidate_index": 0,
            "status": "passed", "reject_reasons": [], "warnings": [], "category": "instrument",
            "instrument_family": spec.instrument.family, "instrument_type": spec.instrument.type, "genre": spec.genre,
            "moods": spec.moods, "key_tonic": spec.key.tonic, "key_mode": spec.key.mode, "bpm": spec.bpm,
            "time_signature": spec.time_signature, "bars": spec.bars, "length_samples": spec.loop_samples,
            "provider": "midi", "model_revision": "compose-v1", "gen_prompt": " · ".join(spec.harmony.symbols(spec.key)),
            "seed": None, "steps": None, "duration_s": spec.loop_seconds, "midi_path": midi_rel,
            "filename": loop_filename(spec, id4=request_id[:4]).replace(".wav", ".mid"),
            "analysis_raw": None, "conform_ops": {"midi_only": True}, "analysis_final": None, "score": 1.0, "peaks": None,
        }
        job.update(status="done", loops=[rec], midi_path=midi_rel, voicings=[v.symbol for v in comp.voicings],
                   completed_at=_now(), gpu_seconds=0.0, batches_run=0)
    except Exception as e:  # noqa: BLE001
        job.update(status="failed", error=f"{type(e).__name__}: {e}", completed_at=_now())
        raise
    return job.state
