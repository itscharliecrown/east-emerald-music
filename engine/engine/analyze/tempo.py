"""Tempo, beat, and downbeat estimation with octave folding (PRD §7.5).

Backends:
  - beat_this (GPU, Modal image): state-of-the-art beats + downbeats
  - librosa (CPU fallback, local tests): beats only, downbeats inferred from onset strength
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class TempoEstimate:
    bpm: float
    drift_cv: float                      # coefficient of variation of inter-beat intervals
    beats: list[float] = field(default_factory=list)      # seconds
    downbeats: list[float] = field(default_factory=list)  # seconds
    folded_from: float | None = None     # raw bpm before octave folding
    backend: str = "none"

    @classmethod
    def free(cls) -> "TempoEstimate":
        return cls(bpm=0.0, drift_cv=0.0, backend="free-time")

    def error_pct(self, target_bpm: float) -> float:
        if self.bpm <= 0:
            return 100.0
        return abs(self.bpm - target_bpm) / target_bpm * 100.0


def fold_to_target(bpm: float, target: float) -> float:
    """Fold ×2 / ×0.5 (and ×3 / ÷3 for 6/8 vs 4/4 confusion) to whichever is closest to target."""
    if bpm <= 0 or target <= 0:
        return bpm
    candidates = [bpm * f for f in (0.25, 1 / 3, 0.5, 2 / 3, 1.0, 1.5, 2.0, 3.0, 4.0)]
    return min(candidates, key=lambda c: abs(np.log(c / target)))


def _intervals_stats(beats: np.ndarray) -> tuple[float, float]:
    if len(beats) < 3:
        return 0.0, 1.0
    ibi = np.diff(beats)
    # Median is robust to a single dropped/doubled beat.
    med = float(np.median(ibi))
    if med <= 0:
        return 0.0, 1.0
    # Drift: spread of intervals relative to the median, after removing octave outliers.
    clean = ibi[(ibi > med * 0.6) & (ibi < med * 1.6)]
    cv = float(np.std(clean) / np.mean(clean)) if len(clean) >= 2 else 1.0
    return 60.0 / med, cv


def estimate_tempo(
    mono: np.ndarray, sr: int, *, target_bpm: float | None = None, backend: str = "auto"
) -> TempoEstimate:
    if backend in ("auto", "beat_this"):
        try:
            return _beat_this(mono, sr, target_bpm)
        except ImportError:
            if backend == "beat_this":
                raise
    return _librosa(mono, sr, target_bpm)


def _beat_this(mono: np.ndarray, sr: int, target_bpm: float | None) -> TempoEstimate:
    from beat_this.inference import File2Beats  # type: ignore

    import torch  # noqa: F401

    f2b = File2Beats(checkpoint_path="final0", device="cuda", dbn=False)
    # beat_this expects 22.05 kHz mono
    import librosa

    y = librosa.resample(mono, orig_sr=sr, target_sr=22050)
    beats, downbeats = f2b.process_audio(y, 22050)
    beats = np.asarray(beats, dtype=float)
    bpm, cv = _intervals_stats(beats)
    raw = bpm
    if target_bpm:
        bpm = fold_to_target(bpm, target_bpm)
    return TempoEstimate(
        bpm=bpm, drift_cv=cv, beats=beats.tolist(), downbeats=list(map(float, downbeats)),
        folded_from=raw if raw != bpm else None, backend="beat_this",
    )


def _librosa(mono: np.ndarray, sr: int, target_bpm: float | None) -> TempoEstimate:
    import librosa

    hop = 512
    onset_env = librosa.onset.onset_strength(y=mono, sr=sr, hop_length=hop)
    start_bpm = target_bpm or 100.0
    _, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env, sr=sr, hop_length=hop, start_bpm=start_bpm, tightness=100
    )
    beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
    bpm, cv = _intervals_stats(beats)
    raw = bpm
    if target_bpm:
        bpm = fold_to_target(bpm, target_bpm)
    downbeats = _infer_downbeats(beats, onset_env, sr, hop)
    return TempoEstimate(
        bpm=bpm, drift_cv=cv, beats=beats.tolist(), downbeats=downbeats,
        folded_from=raw if raw != bpm else None, backend="librosa",
    )


def _infer_downbeats(beats: np.ndarray, onset_env: np.ndarray, sr: int, hop: int, meter: int = 4) -> list[float]:
    """Pick the beat phase (0..meter-1) with the strongest average onset as the downbeat."""
    if len(beats) < meter:
        return beats[:1].tolist()
    frames = np.clip((beats * sr / hop).astype(int), 0, len(onset_env) - 1)
    strengths = onset_env[frames]
    best_phase = max(range(meter), key=lambda p: strengths[p::meter].mean())
    return beats[best_phase::meter].tolist()
