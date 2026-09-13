import pytest

from engine.spec import Instrument, Key, LoopSpec, loop_samples


def _spec(**kw) -> LoopSpec:
    base = dict(instrument=Instrument(family="piano", type="upright_piano"), genre="Lo-Fi Hip Hop",
                key=Key(tonic="E", mode="minor"), bpm=90, bars=8)
    base.update(kw)
    return LoopSpec(**base)


def test_loop_samples_worked_example():
    # PRD §7.6: 8 bars of 4/4 at 90 BPM = 940,800 samples
    assert loop_samples(8, 90) == 940_800
    assert _spec().loop_samples == 940_800


def test_three_four_uses_three_quarters():
    assert loop_samples(4, 120, "3/4") == round(4 * 3 * 0.5 * 44100)


def test_generate_seconds_adds_two_bars():
    s = _spec(bpm=80, bars=8)
    assert s.generate_seconds == pytest.approx(30.0)


def test_bars_must_be_4_or_8():
    with pytest.raises(Exception):
        _spec(bars=6)


def test_variants_must_be_four():
    from engine.spec import Variant
    with pytest.raises(Exception):
        _spec(variants=[Variant(axis="register")])


def test_harmony_must_fill_loop():
    from engine.spec import Chord, Harmony
    with pytest.raises(Exception):
        _spec(harmony=Harmony(progression=[Chord(degree="i", quality="m9", beats=8)]))
    ok = _spec(harmony=Harmony(progression=[Chord(degree="i", quality="m9", beats=16),
                                            Chord(degree="VI", quality="maj7", beats=16)]))
    assert ok.harmony is not None


def test_key_label():
    assert Key(tonic="E", mode="minor").label() == "Emin"
    assert Key(tonic="Db", mode="major").label() == "Dbmaj"
    assert Key(tonic="D", mode="dorian").label() == "Ddorian"
