"""Loop-window search, exact cut, and tail wrap (PRD §7.6 steps 3–5)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class LoopWindow:
    start_sample: int
    score: float
    onset_score: float
    seam_score: float
    energy_score: float


def _onset_strength_at(mono: np.ndarray, sr: int, sample: int, win: int = 2048) -> float:
    a = mono[max(0, sample - win): sample]
    b = mono[sample: sample + win]
    if len(a) < 64 or len(b) < 64:
        return 0.0
    ea, eb = np.sqrt(np.mean(a ** 2)) + 1e-9, np.sqrt(np.mean(b ** 2)) + 1e-9
    return float(np.clip(np.log(eb / ea), -3, 3) / 3)


def _spectral_seam(mono: np.ndarray, start: int, length: int, n: int = 4096) -> float:
    """1 = last frame and first frame have identical spectra. 0 = unrelated."""
    end = start + length
    if end > len(mono) or start < 0:
        return 0.0
    last = np.abs(np.fft.rfft(mono[end - n:end] * np.hanning(n)))
    first = np.abs(np.fft.rfft(mono[start:start + n] * np.hanning(n)))
    denom = np.linalg.norm(last) * np.linalg.norm(first) + 1e-9
    return float(np.dot(last, first) / denom)


def _energy_stability(mono: np.ndarray, start: int, length: int, bars: int) -> float:
    seg = mono[start:start + length]
    if len(seg) < length:
        return 0.0
    bar = length // bars
    rms = np.array([np.sqrt(np.mean(seg[i * bar:(i + 1) * bar] ** 2)) for i in range(bars)]) + 1e-9
    return float(1.0 - np.clip(np.std(rms) / np.mean(rms), 0, 1))


def find_loop_window(
    mono: np.ndarray,
    sr: int,
    *,
    loop_samples: int,
    bars: int,
    downbeats_s: list[float],
    tail_ms: float = 250.0,
) -> LoopWindow:
    """Score every downbeat that leaves room for the loop plus a short tail."""
    tail = int(sr * tail_ms / 1000)
    best: LoopWindow | None = None
    candidates = [int(round(d * sr)) for d in downbeats_s] or [0]
    for start in candidates:
        if start + loop_samples + tail > len(mono):
            continue
        onset = _onset_strength_at(mono, sr, start)
        seam = _spectral_seam(mono, start, loop_samples)
        energy = _energy_stability(mono, start, loop_samples, bars)
        score = 0.35 * onset + 0.45 * seam + 0.20 * energy
        w = LoopWindow(start, score, onset, seam, energy)
        if best is None or w.score > best.score:
            best = w
    if best is None:
        raise ValueError("no downbeat leaves room for the loop; generate longer audio")
    return best


def _equal_power_fade(n: int) -> tuple[np.ndarray, np.ndarray]:
    t = np.linspace(0, np.pi / 2, n, dtype=np.float32)
    return np.cos(t), np.sin(t)  # out, in


def cut_loop(
    x: np.ndarray,
    sr: int,
    *,
    start: int,
    loop_samples: int,
    wrap_tail: bool = True,
    fade_ms: float = 3.0,
) -> np.ndarray:
    """Cut exactly loop_samples from start, wrap the tail into the head, fade the seam."""
    stereo = x if x.ndim == 2 else x[None, :]
    loop = stereo[:, start:start + loop_samples].copy()
    if loop.shape[1] != loop_samples:
        raise ValueError("audio too short for requested loop")

    if wrap_tail:
        tail = stereo[:, start + loop_samples: start + loop_samples + loop_samples // 4]
        if tail.shape[1] > 0:
            n = tail.shape[1]
            fade = np.linspace(1.0, 0.0, n, dtype=np.float32) ** 2  # tail decays into the head
            loop[:, :n] += tail * fade

    n = max(8, int(sr * fade_ms / 1000))
    out, inn = _equal_power_fade(n)
    # Crossfade head with the audio that would precede it when looping (the loop's own end).
    head = loop[:, :n].copy()
    loop[:, :n] = head * inn + loop[:, -n:] * out * 0.0  # keep head; the fade shape avoids clicks
    loop[:, -n:] *= out
    loop[:, :n] *= inn
    return loop
