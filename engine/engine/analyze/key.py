"""Key estimation: Krumhansl-Schmuckler on CQT chroma, plus bass-tonic confirmation (PRD §7.5).

Pure numpy/librosa so it runs identically on the laptop and on Modal.
Relative major/minor share a pitch set, so `bass_tonic` is used to break the tie.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from engine.spec import PITCH_NAME

# Krumhansl & Kessler (1982) key profiles.
_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

# Mode → rotation of the major scale (for reporting modal keys the LLM may request).
MODE_OFFSETS = {"major": 0, "dorian": 2, "phrygian": 4, "lydian": 5, "mixolydian": 7, "minor": 9}


@dataclass
class KeyEstimate:
    tonic: str
    mode: str                # "major" | "minor"
    strength: float          # correlation of the winner
    margin: float            # winner minus runner-up correlation
    bass_tonic: str | None   # most common bass pitch class
    chroma: list[float]

    @property
    def pitch_class(self) -> int:
        from engine.spec import PITCH_CLASS
        return PITCH_CLASS[self.tonic]

    def relative(self) -> tuple[str, str]:
        """The relative major/minor of this key."""
        pc = self.pitch_class
        if self.mode == "major":
            return PITCH_NAME[(pc + 9) % 12], "minor"
        return PITCH_NAME[(pc + 3) % 12], "major"


def _correlate_profiles(chroma: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    maj = np.array([np.corrcoef(np.roll(_MAJOR, i), chroma)[0, 1] for i in range(12)])
    mnr = np.array([np.corrcoef(np.roll(_MINOR, i), chroma)[0, 1] for i in range(12)])
    return maj, mnr


def estimate_key(mono: np.ndarray, sr: int) -> KeyEstimate:
    import librosa

    chroma = librosa.feature.chroma_cqt(y=mono, sr=sr, bins_per_octave=36)
    profile = chroma.mean(axis=1)
    if profile.sum() <= 0:
        return KeyEstimate("C", "major", 0.0, 0.0, None, [0.0] * 12)
    profile = profile / profile.sum()

    maj, mnr = _correlate_profiles(profile)
    scores = np.concatenate([maj, mnr])
    order = np.argsort(scores)[::-1]
    best, second = int(order[0]), int(order[1])
    mode = "major" if best < 12 else "minor"
    tonic_pc = best % 12

    bass = _bass_tonic(mono, sr)
    # Relative-key tie break. Aeolian progressions (i–VI–III–VII) correlate better with the
    # relative MAJOR profile, so a pure profile match calls E minor "G major". Loops start on
    # the tonic (PRD §10.1), so time-weighted bass evidence decides when the two are close.
    rel_pc = (tonic_pc + (9 if mode == "major" else 3)) % 12
    rel_idx = rel_pc + (12 if mode == "major" else 0)
    if bass is not None and bass == rel_pc and scores[best] - scores[rel_idx] < 0.25:
        best, second = rel_idx, best
        mode = "major" if best < 12 else "minor"
        tonic_pc = best % 12

    return KeyEstimate(
        tonic=PITCH_NAME[tonic_pc],
        mode=mode,
        strength=float(scores[best]),
        margin=float(scores[best] - scores[second]),
        bass_tonic=PITCH_NAME[bass] if bass is not None else None,
        chroma=[float(v) for v in profile],
    )


def _bass_tonic(mono: np.ndarray, sr: int, cutoff_hz: float = 250.0, head_frac: float = 0.15,
                head_weight: float = 4.0) -> int | None:
    """Dominant bass pitch class, with the opening of the clip weighted heavily.

    The first bar is structurally the tonic in a loop, so the first `head_frac` of the audio
    counts `head_weight` times. Uses the fundamental band only (C1..C3) so chord tones an
    octave up don't vote.
    """
    import librosa
    from scipy.signal import butter, sosfiltfilt

    sos = butter(4, cutoff_hz, btype="low", fs=sr, output="sos")
    low = sosfiltfilt(sos, mono).astype(np.float32)
    if np.max(np.abs(low)) < 1e-4:
        return None
    hop = 2048
    chroma = librosa.feature.chroma_cqt(y=low, sr=sr, hop_length=hop, fmin=librosa.note_to_hz("C1"),
                                        n_octaves=2, bins_per_octave=12)
    n = chroma.shape[1]
    weights = np.ones(n)
    weights[: max(1, int(n * head_frac))] = head_weight
    hist = (chroma * weights).sum(axis=1)
    if hist.sum() <= 0:
        return None
    return int(np.argmax(hist))


def semitone_distance(from_pc: int, to_pc: int) -> int:
    """Signed shortest distance in semitones, in [-6, 6]."""
    d = (to_pc - from_pc) % 12
    return d - 12 if d > 6 else d
