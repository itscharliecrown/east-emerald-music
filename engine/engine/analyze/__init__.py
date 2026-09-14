"""Audio analysis: everything the gate and the conform stage need (PRD §7.5).

All functions take float32 arrays shaped (channels, samples) at 44.1 kHz unless noted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from engine.analyze.key import KeyEstimate, estimate_key
from engine.analyze.loudness import LoudnessInfo, measure_loudness
from engine.analyze.tempo import TempoEstimate, estimate_tempo
from engine.analyze.tuning import estimate_tuning_cents


@dataclass
class Analysis:
    tempo: TempoEstimate
    key: KeyEstimate
    tuning_cents: float
    loudness: LoudnessInfo
    stereo_correlation: float
    clipping_runs: int
    silent_bars: int
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Analysis":
        return cls(
            tempo=TempoEstimate(**d["tempo"]),
            key=KeyEstimate(**d["key"]),
            tuning_cents=d["tuning_cents"],
            loudness=LoudnessInfo(**d["loudness"]),
            stereo_correlation=d["stereo_correlation"],
            clipping_runs=d["clipping_runs"],
            silent_bars=d["silent_bars"],
            extra=d.get("extra", {}),
        )


def to_mono(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=0) if x.ndim == 2 else x


def stereo_correlation(x: np.ndarray) -> float:
    if x.ndim != 2 or x.shape[0] != 2:
        return 1.0
    l, r = x[0], x[1]
    if l.std() < 1e-9 or r.std() < 1e-9:
        return 1.0
    return float(np.corrcoef(l, r)[0, 1])


def clipping_runs(x: np.ndarray, threshold: float = 0.95, min_run: int = 4) -> int:
    """Count flat-topped runs: >= min_run consecutive near-identical samples at |x| >= threshold.

    Float audio above 1.0 is loud, not clipped. Clipping is a flat top, so we require the
    sample-to-sample difference to vanish as well (PRD §7.7).
    """
    mono = x if x.ndim == 1 else x
    hot = np.abs(mono) >= threshold * np.max(np.abs(mono))
    flat = np.abs(np.diff(mono, axis=-1)) < 1e-4
    both = hot[..., 1:] & flat
    if both.ndim == 2:
        both = both.any(axis=0)
    runs, count = 0, 0
    for v in both:
        if v:
            count += 1
            if count == min_run:
                runs += 1
        else:
            count = 0
    return runs


def silent_bars(x: np.ndarray, bar_samples: int, threshold_db: float = -55.0) -> int:
    """A bar counts as silent below -55 dBFS RMS. -45 rejected sparse felt-piano bars (2026-09-14)."""
    mono = to_mono(x)
    n_bars = max(1, len(mono) // bar_samples)
    silent = 0
    for b in range(n_bars):
        seg = mono[b * bar_samples:(b + 1) * bar_samples]
        rms = float(np.sqrt(np.mean(seg ** 2)) + 1e-12)
        if 20 * np.log10(rms) < threshold_db:
            silent += 1
    return silent


def analyze(
    x: np.ndarray,
    sr: int,
    *,
    target_bpm: float | None = None,
    bar_samples: int | None = None,
    rhythmic: bool = True,
) -> Analysis:
    mono = to_mono(x).astype(np.float32)
    tempo = estimate_tempo(mono, sr, target_bpm=target_bpm) if rhythmic else TempoEstimate.free()
    key = estimate_key(mono, sr)
    tuning = estimate_tuning_cents(mono, sr)
    loud = measure_loudness(x, sr)
    return Analysis(
        tempo=tempo,
        key=key,
        tuning_cents=tuning,
        loudness=loud,
        stereo_correlation=stereo_correlation(x),
        clipping_runs=clipping_runs(x),
        silent_bars=silent_bars(x, bar_samples) if bar_samples else 0,
    )
