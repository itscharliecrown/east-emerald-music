"""DC removal, subsonic high-pass, loudness normalize with a true-peak ceiling. Never limits (PRD §7.6 step 6)."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt

from engine.analyze.loudness import measure_loudness


def normalize_level(
    x: np.ndarray,
    sr: int,
    *,
    target_lufs: float = -16.0,
    ceiling_dbtp: float = -1.0,
) -> tuple[np.ndarray, dict]:
    y = x.astype(np.float32)
    y = y - y.mean(axis=-1, keepdims=True)                      # DC
    sos = butter(2, 20.0, btype="high", fs=sr, output="sos")     # subsonic
    y = sosfiltfilt(sos, y, axis=-1).astype(np.float32)

    info = measure_loudness(y, sr)
    gain_db = target_lufs - info.lufs
    # If the peak ceiling binds, lower the gain instead of limiting.
    max_gain_db = ceiling_dbtp - info.true_peak_dbtp
    applied_db = min(gain_db, max_gain_db)
    y = y * (10 ** (applied_db / 20))
    return y, {
        "lufs_before": info.lufs,
        "true_peak_before": info.true_peak_dbtp,
        "gain_db": float(applied_db),
        "ceiling_bound": bool(applied_db < gain_db),
    }
