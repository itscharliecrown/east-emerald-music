import pytest

from engine.compose.midi import write_midi
from engine.compose.patterns import compose_events
from engine.compose.theory import chord_pitch_classes, chord_symbol, parse_degree
from engine.compose.voicing import C3, voice_guitar, voice_piano
from engine.spec import Chord, Harmony, Instrument, Key, LoopSpec


def _spec(fam="piano", typ="felt_piano", complexity="complex", pattern="broken") -> LoopSpec:
    prog = [Chord(degree="i", quality="m9", beats=8), Chord(degree="iv", quality="m7", beats=8),
            Chord(degree="bVII", quality="maj7", beats=8), Chord(degree="bVI", quality="maj7", beats=4),
            Chord(degree="v", quality="7sus4", beats=4)]
    return LoopSpec(instrument=Instrument(family=fam, type=typ), genre="Lo-Fi Hip Hop", moods=["warm"],
                    key=Key(tonic="E", mode="minor"), bpm=80, bars=8,
                    harmony=Harmony(progression=prog, complexity=complexity, pattern=pattern))


def test_degrees_and_symbols_in_e_minor():
    key = Key(tonic="E", mode="minor")
    assert parse_degree("bVII", key)[0] == 2            # D
    assert parse_degree("bVI", key)[0] == 0             # C
    assert parse_degree("iv", key)[0] == 9              # A
    s = _spec()
    assert s.harmony.symbols(key) == ["Em9", "Am7", "Dmaj7", "Cmaj7", "B7sus4"]
    root, pcs = chord_pitch_classes(Chord(degree="i", quality="m9", beats=4), key)
    assert root == 4 and set(pcs) == {4, 7, 2, 6, 11}   # E G D F# B


def test_piano_voicing_respects_low_interval_limit_and_leaves_low_end():
    s = _spec()
    vs = voice_piano(s.harmony.progression, s.key, leave_low_end=True, complexity="complex")
    assert len(vs) == 5
    for v in vs:
        assert all(n >= C3 for n in v.bass)
        notes = sorted(v.all)
        for a, b in zip(notes, notes[1:]):
            assert not (b < C3 and (b - a) <= 4)
        assert 3 <= len(v.upper) <= 4
    # voice leading: consecutive top notes move ≤ 7 semitones
    tops = [v.upper[-1] for v in vs]
    assert all(abs(a - b) <= 7 for a, b in zip(tops, tops[1:]))


def test_guitar_voicing_in_range():
    s = _spec("guitar", "steel_acoustic_guitar", pattern="fingerstyle")
    for v in voice_guitar(s.harmony.progression, s.key):
        assert 40 <= min(v.all) and max(v.all) <= 76 and (max(v.all) - min(v.all)) <= 24


@pytest.mark.parametrize("pattern", ["sustained", "broken", "arpeggio", "stabs", "fingerstyle", "strum"])
def test_patterns_fill_loop_and_stay_inside(pattern, tmp_path):
    fam = "guitar" if pattern in ("fingerstyle", "strum") else "piano"
    s = _spec(fam, "nylon_guitar" if fam == "guitar" else "felt_piano", pattern=pattern)
    vs = voice_guitar(s.harmony.progression, s.key) if fam == "guitar" else voice_piano(s.harmony.progression, s.key, leave_low_end=True)
    notes = compose_events(s, vs, seed=1)
    total = s.bars * 4
    assert notes and all(0 <= n.start < total for n in notes)
    assert min(n.start for n in notes) < 0.1            # something on the downbeat
    p = write_midi(notes, s, tmp_path / "x.mid", with_context=True)
    import pretty_midi
    pm = pretty_midi.PrettyMIDI(str(p))
    assert abs(pm.get_end_time() - (s.bars + 2) * 3.0) < 1.5   # 10 bars at 80 BPM ≈ 30 s
