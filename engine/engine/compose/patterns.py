"""Rhythmic patterns + humanization → note events (PRD §10.4, §10.6)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from engine.compose.voicing import Voicing
from engine.spec import Chord, LoopSpec


@dataclass
class Note:
    pitch: int
    start: float      # beats (quarter notes) from loop start
    dur: float        # beats
    vel: int


def _swing(beat_pos: float, swing_pct: float, grid: float = 0.5) -> float:
    """Delay off-grid 8ths by swing amount. 50% = straight, 66.7% = triplet."""
    frac = (beat_pos / grid) % 2
    if abs(frac - 1) < 1e-6:
        return beat_pos + (swing_pct - 50) / 100 * grid * 2 * 0.5
    return beat_pos


def _events_for(spec: LoopSpec, voicings: list[Voicing], rng: random.Random) -> list[Note]:
    pattern = spec.harmony.pattern if spec.harmony else "sustained"
    swing = spec.feel.swing_pct
    notes: list[Note] = []
    t = 0.0
    for c, v in zip(spec.harmony.progression, voicings):
        L = float(c.beats)
        if pattern == "sustained":
            # Bass on beat 1, chord rolled bottom-up on 1; re-strike softly on beat 3 of long chords.
            for n in v.bass:
                notes.append(Note(n, t, L * 0.98, 62))
            for i, n in enumerate(v.upper):
                notes.append(Note(n, t + i * 0.03, L * 0.97 - i * 0.03, 58 + (6 if i == len(v.upper) - 1 else 0)))
            if L >= 4:
                for i, n in enumerate(v.upper):
                    notes.append(Note(n, t + 2.0 + i * 0.02, 1.8, 46))
        elif pattern == "broken":
            # LH root on 1, chord on 1 and the "and" of 2 (lo-fi comping), sparse.
            for n in v.bass:
                notes.append(Note(n, t, L * 0.95, 64))
            hits = [0.0, 1.5] + ([2.5, 3.5] if L >= 4 and rng.random() < 0.6 else [])
            for h in hits:
                if h < L:
                    for i, n in enumerate(v.upper):
                        notes.append(Note(n, _swing(t + h, swing) + i * 0.015, 0.9, 54 if h else 62))
        elif pattern == "arpeggio":
            seq = v.bass + v.upper + v.upper[-2:-1]
            step = 0.5
            k = 0
            pos = 0.0
            while pos < L - 1e-6:
                n = seq[k % len(seq)]
                notes.append(Note(n, _swing(t + pos, swing), step * 1.6, 52 + (10 if k % len(seq) == 0 else 0)))
                pos += step
                k += 1
        elif pattern == "stabs":
            # House: off-beat chord stabs (the "and" of each beat), bass only on 1.
            for n in v.bass:
                notes.append(Note(n, t, 0.5, 70))
            pos = 0.5
            while pos < L:
                for n in v.upper:
                    notes.append(Note(n, t + pos, 0.28, 78))
                pos += 1.0
        elif pattern == "fingerstyle":
            # Travis: thumb alternates bass/5th on beats, fingers pick upper notes off the beat.
            b = v.bass[0]
            fifth = b + 7
            pos = 0.0
            i = 0
            while pos < L - 1e-6:
                notes.append(Note(b if i % 2 == 0 else fifth, t + pos, 0.9, 60))
                up = v.upper[(i) % len(v.upper)]
                notes.append(Note(up, _swing(t + pos + 0.5, swing), 0.7, 50))
                if i % 2 == 1 and len(v.upper) > 1:
                    notes.append(Note(v.upper[-1], t + pos + 0.25, 0.4, 44))
                pos += 1.0
                i += 1
        elif pattern == "strum":
            # Down on beats, up on off-beats, 20 ms between strings, down = low→high.
            pos = 0.0
            while pos < L - 1e-6:
                down = (pos % 1.0) == 0
                order = v.all if down else list(reversed(v.all))
                for i, n in enumerate(order):
                    notes.append(Note(n, _swing(t + pos, swing) + i * 0.02, 0.45, (64 if down else 48) - (0 if down else 4)))
                pos += 0.5
        t += L
    return notes


def humanize(notes: list[Note], spec: LoopSpec, rng: random.Random) -> list[Note]:
    bpm = spec.bpm
    ms = bpm / 60000.0  # beats per ms
    lay_back = 12 if spec.feel.swing_pct > 52 else 4  # ms behind the grid
    total = spec.loop_seconds * bpm / 60
    out = []
    for n in notes:
        # Phrase arc: swell into the middle of each 4-bar phrase, relax into the turnaround.
        phrase_pos = (n.start % (4 * spec.quarters_per_bar)) / (4 * spec.quarters_per_bar)
        arc = 1.0 + 0.10 * (0.5 - abs(phrase_pos - 0.5)) * 2
        vel = int(max(20, min(110, n.vel * arc + rng.gauss(0, 4))))
        jitter = rng.gauss(0, 6) + lay_back
        start = max(0.0, n.start + jitter * ms)
        if start >= total:
            continue
        out.append(Note(n.pitch, start, max(0.1, n.dur + rng.gauss(0, 0.02)), vel))
    return out


def compose_events(spec: LoopSpec, voicings: list[Voicing], seed: int = 0) -> list[Note]:
    rng = random.Random(seed)
    return humanize(_events_for(spec, voicings, rng), spec, rng)
