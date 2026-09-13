"""Synthetic fixtures with known BPM and key. No external renderers needed."""

from __future__ import annotations

import numpy as np

from engine.spec import PITCH_CLASS

SR = 44_100

_SCALE = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}


def midi_to_hz(m: float, a4: float = 440.0) -> float:
    return a4 * 2 ** ((m - 69) / 12)


def pluck(freq: float, n: int, sr: int = SR, decay: float = 3.0) -> np.ndarray:
    t = np.arange(n) / sr
    env = np.exp(-decay * t)
    # A few harmonics so chroma and onset detection behave like a real instrument.
    y = sum((0.6 ** k) * np.sin(2 * np.pi * freq * (k + 1) * t) for k in range(4))
    return (y * env).astype(np.float32)


def chord_loop(
    tonic: str,
    mode: str,
    bpm: float,
    bars: int = 4,
    *,
    sr: int = SR,
    a4: float = 440.0,
    pre_roll_bars: int = 0,
    tail_bars: int = 0,
) -> np.ndarray:
    """Stereo loop: bass root on every beat + a diatonic triad per bar (i, VI, III, VII style)."""
    beat = 60.0 / bpm
    beat_n = int(round(beat * sr))
    total_bars = pre_roll_bars + bars + tail_bars
    n = int(round(total_bars * 4 * beat * sr))
    out = np.zeros(n, dtype=np.float32)
    root = 48 + PITCH_CLASS[tonic]  # C3 region
    scale = _SCALE[mode]
    degrees = [0, 5, 2, 6] if mode == "minor" else [0, 4, 5, 3]
    for bar in range(total_bars):
        deg = degrees[bar % 4]
        chord_root = root + scale[deg]
        third = root + scale[(deg + 2) % 7] + (12 if (deg + 2) >= 7 else 0)
        fifth = root + scale[(deg + 4) % 7] + (12 if (deg + 4) >= 7 else 0)
        for b in range(4):
            start = bar * 4 * beat_n + b * beat_n
            seg = min(beat_n, n - start)
            if seg <= 0:
                break
            out[start:start + seg] += 0.5 * pluck(midi_to_hz(chord_root - 12, a4), seg, sr, decay=4)
            if b in (0, 2):
                for m in (chord_root + 12, third + 12, fifth + 12):
                    out[start:start + seg] += 0.25 * pluck(midi_to_hz(m, a4), seg, sr, decay=2)
    out /= max(1e-6, np.max(np.abs(out))) / 0.5
    return np.stack([out, out * 0.95])
