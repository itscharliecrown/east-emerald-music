from engine.compose.melody import _MNote, enforce, melody_prompt
from tests.test_compose import _spec


def test_enforce_snaps_strong_beats_and_limits_repeats():
    s = _spec()  # E minor, Em9 Am7 Dmaj7 Cmaj7 B7sus4 over 8 bars
    notes = [_MNote(degree="2", octave=0, start=0, dur=1, vel=80)]        # F# on beat 1 of Em9: chord tone (9th)
    notes += [_MNote(degree="4", octave=0, start=2, dur=1, vel=80)]       # A on beat 3 over Em9: not a chord tone → snapped
    notes += [_MNote(degree="1", octave=0, start=4 + i * 0.5, dur=0.4, vel=70) for i in range(6)]  # 6 repeats
    out, fixes = enforce(notes, s, 60, 84)
    assert out[1].pitch % 12 in {4, 7, 11, 2, 6}
    assert any("repeat" in f for f in fixes)
    pitches = [n.pitch for n in out]
    assert max(pitches) - min(pitches) <= 19
    assert out[-1].pitch % 12 in {4, 7, 11, 2, 6}


def test_melody_prompt_is_valid():
    s = _spec()
    p = melody_prompt(s)
    assert p.startswith("TrackType: Instrument") and p.endswith("80 BPM") and "melody" in p
