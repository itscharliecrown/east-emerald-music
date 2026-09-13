"""Integrated loudness (ITU-R BS.1770) and true peak (PRD §7.5, §7.6)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import resample_poly


@dataclass
class LoudnessInfo:
    lufs: float
    true_peak_dbtp: float
    sample_peak_dbfs: float


def true_peak_dbtp(x: np.ndarray, oversample: int = 4) -> float:
    """4× oversampled peak, the standard true-peak approximation."""
    up = resample_poly(x, oversample, 1, axis=-1)
    peak = float(np.max(np.abs(up)) + 1e-12)
    return 20 * np.log10(peak)


def measure_loudness(x: np.ndarray, sr: int) -> LoudnessInfo:
    import pyloudnorm as pyln

    data = x.T if x.ndim == 2 else x[:, None]   # pyloudnorm wants (samples, channels)
    meter = pyln.Meter(sr)
    try:
        lufs = float(meter.integrated_loudness(data))
    except ValueError:  # too short
        lufs = -70.0
    if not np.isfinite(lufs):
        lufs = -70.0
    sample_peak = 20 * np.log10(float(np.max(np.abs(x))) + 1e-12)
    return LoudnessInfo(lufs=lufs, true_peak_dbtp=true_peak_dbtp(x), sample_peak_dbfs=sample_peak)
