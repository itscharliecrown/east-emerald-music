"""Single-pass tempo + pitch correction with Rubber Band R3 (PRD §7.6 step 1).

Uses the `rubberband` CLI (rubberband-cli package) so the GPL library never links into our
process. Missing CLI → RuntimeError with a clear message.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


def rubberband_available() -> bool:
    return shutil.which("rubberband") is not None


def rubberband(
    x: np.ndarray,
    sr: int,
    *,
    time_ratio: float = 1.0,
    semitones: float = 0.0,
) -> np.ndarray:
    """time_ratio > 1 makes the audio longer (slower). semitones may be fractional (tuning)."""
    if abs(time_ratio - 1.0) < 1e-6 and abs(semitones) < 1e-3:
        return x
    if not rubberband_available():
        raise RuntimeError("rubberband CLI not found (apt install rubberband-cli)")
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / "in.wav", Path(d) / "out.wav"
        sf.write(src, x.T if x.ndim == 2 else x, sr, subtype="FLOAT")
        cmd = [
            "rubberband", "-3", "--fine",      # R3 engine
            "--pitch-hq",
            "--time", f"{time_ratio:.6f}",
            "--pitch", f"{semitones:.4f}",
            str(src), str(dst),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        y, _ = sf.read(dst, dtype="float32", always_2d=True)
    return y.T
