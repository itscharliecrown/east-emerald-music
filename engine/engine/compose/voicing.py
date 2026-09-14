"""Piano and guitar voicings with low-interval limits and voice leading (PRD §10.3)."""

from __future__ import annotations

from dataclasses import dataclass

from engine.compose.theory import bass_pitch_class, chord_intervals, parse_degree
from engine.spec import Chord, Key

C2, C3, C4, C6 = 36, 48, 60, 84
E2, E5 = 40, 76


@dataclass
class Voicing:
    bass: list[int]        # MIDI notes, left hand / thumb
    upper: list[int]       # MIDI notes, right hand / fingers, low to high
    symbol: str = ""

    @property
    def all(self) -> list[int]:
        return sorted(set(self.bass + self.upper))


def _nearest(pc: int, around: int) -> int:
    """MIDI note with pitch class pc closest to `around`."""
    base = around - ((around - pc) % 12)
    cands = [base, base + 12, base - 12]
    return min(cands, key=lambda n: abs(n - around))


def _upper_candidates(root_pc: int, intervals: list[int], lo: int, hi: int, max_span: int = 14) -> list[list[int]]:
    """Enumerate 3–4 note upper structures inside [lo, hi]: guide tones + colors, root last.

    Every octave placement of each chosen pitch class is tried; keep sets that fit one hand
    (span ≤ max_span) with no minor-2nd clusters.
    """
    from itertools import product

    pcs = [(root_pc + i) % 12 for i in intervals]
    # Priority: 3rd/sus, 7th (or 6th), then extensions, then 5th, then root.
    ordered = list(dict.fromkeys(pcs[1:] + pcs[:1]))
    chosen = ordered[:4] if len(ordered) >= 4 else ordered
    placements = [[n for n in range(lo, hi + 1) if n % 12 == pc] for pc in chosen]
    out: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    for combo in product(*placements):
        notes = tuple(sorted(combo))
        if notes in seen or len(set(notes)) < len(notes):
            continue
        if notes[-1] - notes[0] > max_span:
            continue
        if any(b - a < 2 for a, b in zip(notes, notes[1:])):
            continue
        seen.add(notes)
        out.append(list(notes))
    return out


def _voice_leading_cost(prev: list[int] | None, cand: list[int]) -> float:
    if not prev:
        # Prefer sitting around the middle of the range.
        return abs(sum(cand) / len(cand) - 67) * 0.5
    a, b = sorted(prev), sorted(cand)
    n = min(len(a), len(b))
    inner = sum(abs(a[-1 - i] - b[-1 - i]) for i in range(n))
    top = abs(a[-1] - b[-1])
    # The top voice is the melody the listener follows: leaps there cost triple.
    return inner + 2 * top + abs(len(a) - len(b)) * 2


def _no_low_seconds_or_thirds(notes: list[int]) -> bool:
    s = sorted(notes)
    for x, y in zip(s, s[1:]):
        if y < C3 and (y - x) in (1, 2, 3, 4):
            return False
    return True


def voice_piano(progression: list[Chord], key: Key, *, leave_low_end: bool, complexity: str = "medium") -> list[Voicing]:
    out: list[Voicing] = []
    prev_upper: list[int] | None = None
    lh_floor = C3 if leave_low_end else C2 + 4
    for c in progression:
        root_pc, upper_case = parse_degree(c.degree, key)
        ivs = chord_intervals(c, upper_case)
        if complexity == "basic":
            ivs = ivs[:3] if len(ivs) >= 3 else ivs
        bass_pc = bass_pitch_class(c, key)
        bass = _nearest(bass_pc, lh_floor + 5)
        if bass < lh_floor:
            bass += 12
        lh = [bass]
        if not leave_low_end and complexity != "basic":
            lh.append(bass + 7)          # root + 5th
        cands = [v for v in _upper_candidates(root_pc, ivs, C4, C6) if _no_low_seconds_or_thirds(lh + v)]
        if not cands:
            cands = _upper_candidates(root_pc, ivs, C4, C6) or [[bass + 12, bass + 16, bass + 19]]
        # Avoid doubling the bass note an octave up when the hand is already full.
        best = min(cands, key=lambda v: _voice_leading_cost(prev_upper, v) + (2 if (bass + 12) in v else 0))
        out.append(Voicing(bass=lh, upper=best, symbol=c.degree + c.quality))
        prev_upper = best
    return out


def voice_guitar(progression: list[Chord], key: Key, *, complexity: str = "medium") -> list[Voicing]:
    """Open-ish 4–5 note shapes in E2–E5; thumb bass on the root, fingers on 3rd/7th/color."""
    out: list[Voicing] = []
    prev: list[int] | None = None
    for c in progression:
        root_pc, upper_case = parse_degree(c.degree, key)
        ivs = chord_intervals(c, upper_case)
        if complexity == "basic":
            ivs = ivs[:3]
        bass = _nearest(bass_pitch_class(c, key), E2 + 7)
        if bass < E2:
            bass += 12
        cands = _upper_candidates(root_pc, ivs, bass + 3, min(E5, bass + 24), max_span=19)
        if not cands:
            cands = [[bass + 12 + i for i in ivs[1:4]]]   # closed shape from the chord's own intervals
        best = min(cands, key=lambda v: _voice_leading_cost(prev, v))
        out.append(Voicing(bass=[bass], upper=best[:4], symbol=c.degree + c.quality))
        prev = best
    return out
