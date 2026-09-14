"""Note events → MIDI file, with a pre-roll bar (last bar of the loop) and a tail bar (first bar)."""

from __future__ import annotations

from pathlib import Path

from engine.compose.patterns import Note
from engine.spec import LoopSpec

GM_PROGRAM = {
    "grand_piano": 0, "upright_piano": 0, "felt_piano": 0, "rhodes": 4, "wurlitzer": 5,
    "nylon_guitar": 24, "steel_acoustic_guitar": 25, "jazz_archtop": 26, "clean_electric_guitar": 27,
}


def _wrap_notes(notes: list[Note], spec: LoopSpec) -> list[Note]:
    """Pre-roll = the loop's last bar, tail = the loop's first bar. Everything shifts by one bar."""
    bar = float(spec.quarters_per_bar)
    total = spec.bars * bar
    out = []
    for n in notes:
        out.append(Note(n.pitch, n.start + bar, n.dur, n.vel))                      # main loop
        if n.start >= total - bar:                                                # last bar → pre-roll
            out.append(Note(n.pitch, n.start - (total - bar), n.dur, n.vel))
        if n.start < bar:                                                          # first bar → tail
            out.append(Note(n.pitch, n.start + bar + total, n.dur, n.vel))
    return out


def write_midi(notes: list[Note], spec: LoopSpec, path: Path, *, with_context: bool = False) -> Path:
    import pretty_midi

    pm = pretty_midi.PrettyMIDI(initial_tempo=spec.bpm, resolution=480)
    num, den = spec.time_signature.split("/")
    pm.time_signature_changes.append(pretty_midi.TimeSignature(int(num), int(den), 0))
    inst = pretty_midi.Instrument(program=GM_PROGRAM.get(spec.instrument.type, 0), name=spec.instrument.type)
    spb = 60.0 / spec.bpm
    seq = _wrap_notes(notes, spec) if with_context else notes
    limit_beats = (spec.bars + (2 if with_context else 0)) * spec.quarters_per_bar
    for n in seq:
        end = min(n.start + n.dur, limit_beats)
        if end - n.start < 0.05:
            continue
        inst.notes.append(pretty_midi.Note(velocity=n.vel, pitch=n.pitch, start=n.start * spb, end=end * spb))
    # Legato pedal: down just after each chord onset; simplest reliable version = pedal on the beat grid.
    if spec.instrument.family in ("piano", "keys") and spec.harmony and spec.harmony.pattern in ("sustained", "broken", "arpeggio"):
        t = 0.0
        offset = spec.quarters_per_bar if with_context else 0
        for c in ([spec.harmony.progression[-1]] if with_context else []) + spec.harmony.progression + ([spec.harmony.progression[0]] if with_context else []):
            inst.control_changes.append(pretty_midi.ControlChange(64, 0, max(0.0, t * spb - 0.03)))
            inst.control_changes.append(pretty_midi.ControlChange(64, 100, t * spb + 0.04))
            t += float(c.beats)
        _ = offset
    pm.instruments.append(inst)
    path.parent.mkdir(parents=True, exist_ok=True)
    pm.write(str(path))
    return path
