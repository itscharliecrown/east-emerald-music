"""Spec → voicings → events → MIDI (+ context) → rendered seed WAV, ready for SA3 audio-to-audio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from engine.compose.midi import write_midi
from engine.compose.patterns import Note, compose_events
from engine.compose.render import render_midi
from engine.compose.voicing import Voicing, voice_guitar, voice_piano
from engine.spec import LoopSpec


@dataclass
class Composition:
    voicings: list[Voicing]
    notes: list[Note]
    midi_path: Path            # loop only (deliverable)
    seed_wav: Path             # pre-roll + loop + tail (for SA3)
    seed_audio: np.ndarray     # (2, n) float32


def default_pattern(spec: LoopSpec) -> str:
    fam, t = spec.instrument.family, spec.instrument.type
    g = spec.genre.lower()
    if fam == "guitar":
        return "strum" if "strum" in " ".join(spec.instrument.techniques).lower() else "fingerstyle"
    if "house" in g:
        return "stabs"
    if any(w in " ".join(spec.instrument.techniques).lower() for w in ("arpegg", "broken")):
        return "arpeggio" if "arpegg" in " ".join(spec.instrument.techniques).lower() else "broken"
    return "broken" if any(w in g for w in ("lo-fi", "lofi", "hip hop", "chillhop", "neo")) else "sustained"


def compose(spec: LoopSpec, out_dir: Path, *, seed: int = 0, render: bool = True) -> Composition:
    assert spec.harmony, "composed mode needs a harmony plan"
    if not spec.harmony.pattern or spec.harmony.pattern == "sustained" and spec.instrument.family == "guitar":
        spec.harmony.pattern = default_pattern(spec)  # type: ignore[assignment]
    if spec.instrument.family == "guitar":
        voicings = voice_guitar(spec.harmony.progression, spec.key, complexity=spec.harmony.complexity)
    else:
        voicings = voice_piano(spec.harmony.progression, spec.key, leave_low_end=spec.leave_low_end,
                               complexity=spec.harmony.complexity)
    notes = compose_events(spec, voicings, seed=seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    midi_path = write_midi(notes, spec, out_dir / "loop.mid")
    ctx_midi = write_midi(notes, spec, out_dir / "seed.mid", with_context=True)
    seed_wav = out_dir / "seed.wav"
    audio = render_midi(ctx_midi, seed_wav) if render else np.zeros((2, 1), dtype=np.float32)
    if render:
        # Exact seed length = generate_seconds so SA3's duration matches the context render.
        n = int(round(spec.generate_seconds * 44100))
        if audio.shape[1] < n:
            audio = np.pad(audio, ((0, 0), (0, n - audio.shape[1])))
        audio = audio[:, :n]
        peak = float(np.abs(audio).max()) + 1e-9
        audio = (audio / peak * 0.5).astype(np.float32)
    return Composition(voicings, notes, midi_path, seed_wav, audio)
