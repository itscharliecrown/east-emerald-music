"""Melody over a known progression: Claude writes notes as data, code enforces the craft.

Rules enforced here, not by prompt (PRD §10.1 spirit):
  - range ≤ 19 semitones, inside the lead instrument's comfortable register
  - strong beats (1 and 3) land on chord tones; off-beat non-chord tones are fine
  - no pitch repeated more than 3 times in a row
  - at least 15% of the loop is rest (a melody breathes)
  - ends on a chord tone of the last chord, on or before the final beat
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import anthropic
from pydantic import BaseModel

from engine.compose.patterns import Note
from engine.compose.theory import SCALES, chord_pitch_classes
from engine.spec import LoopSpec

DEFAULT_MODEL = "claude-opus-5"

LEAD_RANGE = {  # comfortable single-line register per instrument (MIDI)
    "felt_piano": (60, 84), "upright_piano": (60, 84), "grand_piano": (60, 86), "rhodes": (60, 84), "wurlitzer": (60, 84),
    "nylon_guitar": (52, 76), "steel_acoustic_guitar": (52, 76), "clean_electric_guitar": (55, 79), "jazz_archtop": (52, 76),
}

SYSTEM = """You write toplines for lo-fi and soul song starters. You get a chord progression, key, tempo, and bar count. Return a melody as note events.

Craft:
- One idea, developed. A 2-bar motif, repeated or answered, with one climax (highest note) in bar 3 of a 4-bar phrase or bar 6-7 of 8.
- Mostly stepwise. One or two leaps, each followed by a step back.
- Strong beats (beat 1 and 3 of each bar) sit on chord tones of the chord sounding there. Passing tones on weak beats and offbeats.
- Rhythm: mix long notes and short runs. Leave rests; a melody breathes. Start after the downbeat sometimes.
- Land the final note on a chord tone of the last chord, and let it ring.
- Range: about an octave and a half. Never more.

Output: notes with `degree` as a scale step 1-7 with optional accidental (e.g. "3", "b7", "#4"), `octave` relative to the lead register (0 = middle, -1 lower, 1 higher), `start` in beats from the loop start (quarter notes, 0-based; a bar of 4/4 is 4 beats; you may use halves and quarters of beats like 1.5 or 2.25, and swing is added later), `dur` in beats, `vel` 40-100. Notes must not overlap. Total span must stay inside the loop length."""


class _MNote(BaseModel):
    degree: str
    octave: int
    start: float
    dur: float
    vel: int


class MelodyOut(BaseModel):
    notes: list[_MNote]
    motif_description: str
    climax_bar: int


@dataclass
class MelodyResult:
    notes: list[Note]
    description: str
    usage: dict
    fixes: list[str]


def _degree_to_semitones(degree: str, mode: str) -> int:
    acc = 0
    d = degree.strip()
    while d and d[0] in "b#":
        acc += -1 if d[0] == "b" else 1
        d = d[1:]
    step = int(d) if d.isdigit() else 1
    scale = SCALES.get(mode, SCALES["minor"])
    return scale[(step - 1) % 7] + 12 * ((step - 1) // 7) + acc


def _chord_at(spec: LoopSpec, beat: float) -> list[int]:
    t = 0.0
    for c in spec.harmony.progression:
        if t <= beat < t + c.beats:
            return chord_pitch_classes(c, spec.key)[1]
        t += c.beats
    return chord_pitch_classes(spec.harmony.progression[-1], spec.key)[1]


def _snap_to(pitch: int, pcs: list[int]) -> int:
    """Nearest MIDI pitch whose pitch class is in pcs (ties go down)."""
    best = pitch
    for d in range(0, 7):
        for cand in (pitch - d, pitch + d):
            if cand % 12 in pcs:
                return cand
    return best


def enforce(notes: list[_MNote], spec: LoopSpec, lo: int, hi: int) -> tuple[list[Note], list[str]]:
    fixes: list[str] = []
    total = float(spec.bars * spec.quarters_per_bar)
    # Register anchor: the tonic (degree 1, octave 0) sits on the tonic pitch nearest the lower-middle of the range.
    mid = (lo + hi) // 2 - 4
    base = mid - ((mid - spec.key.pitch_class) % 12)
    if base < lo:
        base += 12
    out: list[Note] = []
    last_pitch, repeats = None, 0
    for n in sorted(notes, key=lambda x: x.start):
        if n.start < 0 or n.start >= total or n.dur <= 0:
            continue
        pitch = base + 12 * n.octave + _degree_to_semitones(n.degree, spec.key.mode)
        while pitch < lo:
            pitch += 12
        while pitch > hi:
            pitch -= 12
        beat_in_bar = n.start % spec.quarters_per_bar
        if abs(beat_in_bar - round(beat_in_bar)) < 1e-6 and int(round(beat_in_bar)) in (0, 2):
            snapped = _snap_to(pitch, _chord_at(spec, n.start))
            if snapped != pitch:
                fixes.append(f"beat {n.start:g}: {pitch}→{snapped} chord tone")
                pitch = snapped
        if pitch == last_pitch:
            repeats += 1
            if repeats >= 3:
                fixes.append(f"beat {n.start:g}: broke a 4th repeat")
                pitch = _snap_to(pitch + 2, _chord_at(spec, n.start))
                repeats = 0
        else:
            repeats = 0
        last_pitch = pitch
        dur = min(float(n.dur), total - n.start)
        out.append(Note(pitch, float(n.start), dur, int(max(30, min(110, n.vel)))))
    # no overlaps: trim each note at the next onset
    for a, b in zip(out, out[1:]):
        if a.start + a.dur > b.start:
            a.dur = max(0.1, b.start - a.start - 0.02)
    # range clamp
    if out:
        pitches = [n.pitch for n in out]
        if max(pitches) - min(pitches) > 19:
            fixes.append("range folded to 19 semitones")
            top = min(pitches) + 19
            for n in out:
                while n.pitch > top:
                    n.pitch -= 12
    # breathing room
    sounding = sum(n.dur for n in out)
    if out and sounding > 0.85 * total:
        fixes.append("shortened notes to leave rests")
        for n in out:
            n.dur *= 0.8
    # final note on a chord tone
    if out:
        last = out[-1]
        pcs = _chord_at(spec, last.start)
        if last.pitch % 12 not in pcs:
            last.pitch = _snap_to(last.pitch, pcs)
            fixes.append("final note moved to a chord tone")
    return out, fixes


def compose_melody(spec: LoopSpec, *, instruction: str = "", model: str | None = None,
                   client: anthropic.Anthropic | None = None) -> MelodyResult:
    assert spec.harmony, "melody needs a progression"
    client = client or anthropic.Anthropic()
    model = model or os.environ.get("LLM_MODEL_COMPOSE", DEFAULT_MODEL)
    lo, hi = LEAD_RANGE.get(spec.instrument.type, (60, 84))
    chords = " | ".join(f"{sym} ({c.beats:g} beats)" for sym, c in zip(spec.harmony.symbols(spec.key), spec.harmony.progression))
    brief = (f"Key: {spec.key.tonic} {spec.key.mode}. Tempo: {spec.bpm:g} BPM. {spec.bars} bars of {spec.time_signature} "
             f"({spec.bars * spec.quarters_per_bar} beats). Genre: {spec.genre}. Mood: {', '.join(spec.moods) or 'warm'}.\n"
             f"Chords: {chords}\nLead instrument: {spec.instrument.type.replace('_', ' ')}.\n"
             f"{('Direction: ' + instruction) if instruction else ''}")
    resp = client.messages.parse(
        model=model, max_tokens=4000,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        thinking={"type": "adaptive"}, output_config={"effort": "medium"},
        messages=[{"role": "user", "content": brief}], output_format=MelodyOut,
    )
    out = resp.parsed_output
    if out is None or not out.notes:
        raise RuntimeError("melody: no notes returned")
    notes, fixes = enforce(out.notes, spec, lo, hi)
    usage = resp.usage.to_dict() if hasattr(resp.usage, "to_dict") else dict(resp.usage)
    return MelodyResult(notes=notes, description=out.motif_description, usage=usage, fixes=fixes)


def melody_prompt(spec: LoopSpec) -> str:
    """SA3 prompt for the lead: single-note line, same key/tempo, same production world."""
    from engine.prompts import MAX_WORDS, _TYPE_PHRASE, _feel_phrase, _join, _validate, genre_parts

    tag, vibe = genre_parts(spec)
    parts = ["TrackType: Instrument", "Format: Solo", tag,
             f"solo {_TYPE_PHRASE.get(spec.instrument.type, spec.instrument.type.replace('_', ' '))} playing a single-note melody line alone, expressive phrasing, held notes with space between phrases",
             f"in {spec.key.tonic} {spec.key.mode}", _feel_phrase(spec), ", ".join((vibe[:1] + spec.moods)[:3]),
             ", ".join(spec.production.chain[:2]), spec.production.space, f"{int(round(spec.bpm))} BPM"]
    p = _join(parts)
    return _validate(" ".join(p.split()[:MAX_WORDS]))
