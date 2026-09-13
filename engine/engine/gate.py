"""Quality gate: reject reasons and ranking (PRD §7.7). Thresholds are Phase 0 initial values."""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.analyze import Analysis
from engine.analyze.key import semitone_distance
from engine.spec import PITCH_CLASS, LoopSpec


@dataclass
class Thresholds:
    tempo_error_pct: float = 6.0
    tempo_drift_cv: float = 0.03
    key_max_semitones: int = 2
    key_min_strength: float = 0.6
    stem_min_purity: float = 0.70
    vocal_max_share: float = 0.10
    seam_max_flux_ratio: float = 3.0
    harmony_min_chroma_cos: float = 0.75
    mono_min_correlation: float = 0.0


@dataclass
class GateResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    key_shift_semitones: int = 0
    time_ratio: float = 1.0


def evaluate(spec: LoopSpec, a: Analysis, *, t: Thresholds = Thresholds(), purity: float | None = None,
             vocal_share: float | None = None) -> GateResult:
    r = GateResult(passed=True)

    if a.silent_bars > 0:
        r.reasons.append("silence")
    if a.clipping_runs > 0:
        r.reasons.append("clipping")

    if spec.feel.rhythmic and a.tempo.bpm > 0:
        err = a.tempo.error_pct(spec.bpm)
        if err > t.tempo_error_pct:
            r.reasons.append("tempo_out_of_range")
        else:
            r.time_ratio = a.tempo.bpm / spec.bpm   # >1 means slow it down
        if a.tempo.drift_cv > t.tempo_drift_cv:
            r.reasons.append("tempo_drift")

    if spec.category == "instrument":
        target_pc = PITCH_CLASS[spec.key.tonic]
        detected_mode = a.key.mode
        target_mode = "major" if spec.key.mode in ("major", "lydian", "mixolydian") else "minor"
        if detected_mode != target_mode:
            # Relative major/minor: pass only if the bass confirms the requested tonic.
            rel_tonic, rel_mode = a.key.relative()
            if rel_mode == target_mode and a.key.bass_tonic == spec.key.tonic:
                r.warnings.append("relative_key_confirmed_by_bass")
                detected_pc = PITCH_CLASS[rel_tonic]
            else:
                r.reasons.append("key_mismatch")
                detected_pc = a.key.pitch_class
        else:
            detected_pc = a.key.pitch_class
        shift = semitone_distance(detected_pc, target_pc)
        if abs(shift) > t.key_max_semitones and "key_mismatch" not in r.reasons:
            r.reasons.append("key_mismatch")
        r.key_shift_semitones = shift
        if a.key.strength < t.key_min_strength:
            r.reasons.append("key_ambiguous")

    if purity is not None and purity < t.stem_min_purity:
        r.reasons.append("stem_bleed")
    if vocal_share is not None and vocal_share >= t.vocal_max_share:
        r.reasons.append("vocal_texture")
    if a.stereo_correlation < t.mono_min_correlation:
        r.warnings.append("mono_risk")

    r.passed = not r.reasons
    return r


def rank_score(a: Analysis, g: GateResult, spec: LoopSpec, *, seam_score: float = 0.5,
               purity: float | None = None) -> float:
    """Phase 1 composite of gate margins. Higher is better."""
    tempo_margin = 1.0 - min(1.0, a.tempo.error_pct(spec.bpm) / 6.0) if spec.feel.rhythmic else 1.0
    drift_margin = 1.0 - min(1.0, a.tempo.drift_cv / 0.03) if spec.feel.rhythmic else 1.0
    key_margin = min(1.0, max(0.0, (a.key.strength - 0.6) / 0.4)) + 0.5 * min(1.0, a.key.margin / 0.2)
    purity_margin = purity if purity is not None else 0.7
    return float(0.25 * tempo_margin + 0.15 * drift_margin + 0.25 * key_margin
                 + 0.20 * seam_score + 0.15 * purity_margin)
