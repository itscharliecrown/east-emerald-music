"""Did the audio keep the composed harmony? Per-chord chroma of output vs the MIDI seed (PRD §7.7 harmony_drift)."""

from __future__ import annotations

import numpy as np

from engine.compose.theory import chord_pitch_classes
from engine.spec import LoopSpec


def chord_targets(spec: LoopSpec) -> list[tuple[float, float, np.ndarray]]:
    """[(start_s, end_s, 12-dim target profile)] for each chord in the loop."""
    out = []
    t = 0.0
    spb = 60.0 / spec.bpm
    for c in spec.harmony.progression:
        _, pcs = chord_pitch_classes(c, spec.key)
        prof = np.zeros(12)
        for i, pc in enumerate(pcs):
            prof[pc] = 1.0 if i < 3 else 0.6     # root, 3rd, 7th weigh more than colors
        out.append((t * spb, (t + c.beats) * spb, prof / np.linalg.norm(prof)))
        t += c.beats
    return out


def harmony_similarity(loop: np.ndarray, sr: int, spec: LoopSpec) -> dict:
    """Mean and min cosine similarity between each chord's audio chroma and its target."""
    import librosa

    mono = loop.mean(axis=0) if loop.ndim == 2 else loop
    hop = 2048
    C = librosa.feature.chroma_cqt(y=mono, sr=sr, hop_length=hop)
    sims = []
    for s, e, target in chord_targets(spec):
        a, b = int(s * sr / hop), max(int(s * sr / hop) + 1, int(e * sr / hop))
        seg = C[:, a:b].mean(axis=1)
        seg = seg / (np.linalg.norm(seg) + 1e-9)
        sims.append(float(np.dot(seg, target)))
    return {"per_chord": sims, "mean": float(np.mean(sims)), "min": float(np.min(sims))}
