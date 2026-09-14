"""Render MIDI to audio with FluidSynth + a General MIDI SoundFont. Pitch and timing only; SA3 supplies tone."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

SOUNDFONTS = [
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/soundfonts/FluidR3_GM.sf2",
    "/opt/homebrew/share/soundfonts/default.sf2",
]


def find_soundfont() -> str | None:
    for p in SOUNDFONTS:
        if Path(p).exists():
            return p
    return None


def fluidsynth_available() -> bool:
    return shutil.which("fluidsynth") is not None and find_soundfont() is not None


def render_midi(midi_path: Path, wav_path: Path, *, sr: int = 44100, gain: float = 0.6) -> np.ndarray:
    sf2 = find_soundfont()
    if not sf2 or not shutil.which("fluidsynth"):
        raise RuntimeError("fluidsynth or a GM soundfont is missing")
    subprocess.run(
        ["fluidsynth", "-ni", "-g", str(gain), "-r", str(sr), "-F", str(wav_path), sf2, str(midi_path)],
        check=True, capture_output=True,
    )
    y, got_sr = sf.read(wav_path, dtype="float32", always_2d=True)
    assert got_sr == sr
    return y.T
