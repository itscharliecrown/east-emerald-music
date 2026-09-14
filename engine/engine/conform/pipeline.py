"""Full conformance for one raw clip (PRD §7.6): correct → re-track → window → cut → level.

Runs where `rubberband` is installed (the Modal image). Pure functions, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from engine.analyze import Analysis, analyze, clipping_runs, silent_bars
from engine.analyze.tempo import estimate_tempo
from engine.analyze.tuning import combined_semitones
from engine.conform.level import normalize_level
from engine.conform.stretch import rubberband
from engine.conform.window import cut_loop, find_loop_window
from engine.gate import GateResult, Thresholds, evaluate, rank_score
from engine.spec import LoopSpec


@dataclass
class ConformResult:
    loop: np.ndarray | None          # (2, loop_samples) float32, or None if rejected
    gate: GateResult
    analysis_raw: Analysis
    analysis_final: Analysis | None
    ops: dict = field(default_factory=dict)
    score: float = 0.0


def conform_clip(
    spec: LoopSpec,
    audio: np.ndarray,
    sr: int,
    analysis: Analysis,
    *,
    purity: float | None = None,
    vocal_share: float | None = None,
    thresholds: Thresholds = Thresholds(),
    tempo_backend: str = "auto",
    known_grid: bool = False,
) -> ConformResult:
    gate = evaluate(spec, analysis, t=thresholds, purity=purity, vocal_share=vocal_share, known_grid=known_grid)
    ops: dict = {"known_grid": known_grid}
    if not gate.passed:
        return ConformResult(None, gate, analysis, None, ops)

    # 1. One Rubber Band pass: tempo ratio + (key shift + tuning) in semitones.
    #    Known grid (Composed): tempo and key come from the MIDI seed; only tuning is corrected.
    time_ratio = 1.0 if known_grid or not spec.feel.rhythmic else gate.time_ratio
    key_shift = 0 if known_grid else gate.key_shift_semitones
    semis = combined_semitones(key_shift, analysis.tuning_cents) if spec.category == "instrument" else 0.0
    ops.update({"time_ratio": float(time_ratio), "semitones": float(semis),
                "key_shift": key_shift, "tuning_cents_in": analysis.tuning_cents})
    y = rubberband(audio, sr, time_ratio=time_ratio, semitones=semis)
    mono = y.mean(axis=0)

    # 2. Downbeats: from the seed's pre-roll bar when known, else re-track the corrected audio.
    if known_grid:
        downbeats = [spec.bar_seconds * k for k in (1, 0, 2)]      # bar 1 first, alternatives after
    else:
        tempo = estimate_tempo(mono, sr, target_bpm=spec.bpm, backend=tempo_backend) if spec.feel.rhythmic else None
        downbeats = tempo.downbeats if tempo else [i * spec.bar_seconds for i in range(int(len(mono) / sr / spec.bar_seconds))]

    # 3–5. Window, exact cut, tail wrap, seam fade.
    try:
        if known_grid:
            from engine.conform.window import LoopWindow, _spectral_seam
            start = int(round(spec.bar_seconds * sr))
            seam = _spectral_seam(mono, start, spec.loop_samples)
            w = LoopWindow(start, seam, 1.0, seam, 1.0)
        else:
            w = find_loop_window(mono, sr, loop_samples=spec.loop_samples, bars=spec.bars, downbeats_s=downbeats)
    except ValueError:
        gate.passed = False
        gate.reasons.append("no_loop_window")
        return ConformResult(None, gate, analysis, None, ops)
    loop = cut_loop(y, sr, start=w.start_sample, loop_samples=spec.loop_samples)
    ops.update({"window_start_s": w.start_sample / sr, "seam_score": w.seam_score, "onset_score": w.onset_score})

    # 6. Level.
    loop, lvl = normalize_level(loop, sr)
    ops["level"] = lvl

    # Final measurement + gates that only make sense on the cut loop.
    final = analyze(loop, sr, target_bpm=spec.bpm, rhythmic=spec.feel.rhythmic)
    final.silent_bars = silent_bars(loop, int(round(spec.bar_seconds * sr)))
    final.clipping_runs = clipping_runs(loop)
    if final.silent_bars:
        gate.passed = False
        gate.reasons.append("silence")
    if w.seam_score < 0.15:
        gate.warnings.append("weak_seam")
    score = rank_score(final, gate, spec, seam_score=w.seam_score, purity=purity)
    return ConformResult(loop if gate.passed else None, gate, analysis, final, ops, score)
