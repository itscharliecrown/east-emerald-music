"""Tuning offset from A440 in cents (PRD §7.5)."""

from __future__ import annotations

import numpy as np


def estimate_tuning_cents(mono: np.ndarray, sr: int) -> float:
    import librosa

    # librosa returns the fractional bin offset in [-0.5, 0.5) at 100 cents per bin.
    offset_bins = librosa.estimate_tuning(y=mono, sr=sr, resolution=0.01)
    return float(offset_bins * 100.0)


def cents_to_ratio(cents: float) -> float:
    return float(2 ** (cents / 1200.0))


def combined_semitones(key_shift: int, tuning_cents: float) -> float:
    """Total pitch shift to apply: key correction plus tuning correction back to A440."""
    return key_shift - tuning_cents / 100.0
