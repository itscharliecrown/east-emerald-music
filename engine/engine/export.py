"""Export: 24-bit WAV with filename convention (PRD §7.8)."""

from __future__ import annotations

import re
import secrets
from pathlib import Path

import numpy as np
import soundfile as sf

from engine.spec import LoopSpec


def _camel(s: str) -> str:
    return "".join(w.capitalize() for w in re.split(r"[\s_\-]+", s) if w)


def loop_filename(spec: LoopSpec, descriptor: str | None = None, id4: str | None = None) -> str:
    inst = _camel(spec.instrument.type)
    desc = _camel(descriptor or (spec.moods[0] if spec.moods else spec.genre))
    id4 = id4 or secrets.token_hex(2)
    return f"EE_{inst}_{desc}_{spec.key.label()}_{int(round(spec.bpm))}BPM_{spec.bars}bar_{id4}.wav"


def write_wav24(path: Path, x: np.ndarray, sr: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = x.T if x.ndim == 2 else x
    sf.write(path, np.clip(data, -1.0, 1.0), sr, subtype="PCM_24")
    return path


def write_raw_flac(path: Path, x: np.ndarray, sr: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = x.T if x.ndim == 2 else x
    sf.write(path, np.clip(data, -1.0, 1.0), sr, format="FLAC", subtype="PCM_24")
    return path
