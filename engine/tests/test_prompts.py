import pytest

from engine.prompts import compile_prompts, instrument_prompt, texture_prompt
from engine.spec import Feel, Instrument, Key, LoopSpec, Production, Variant


def _lofi() -> LoopSpec:
    return LoopSpec(
        instrument=Instrument(family="piano", type="upright_piano",
                              techniques=["soft jazzy minor-ninth chords", "felt-muted hammers"]),
        genre="Lo-Fi Hip Hop", moods=["warm", "nostalgic"], key=Key(tonic="E", mode="minor"),
        bpm=80, bars=8, feel=Feel(swing_pct=58),
        production=Production(space="small wooden room", chain=["close-miked", "cassette tape saturation"]),
    )


def test_prompt_shape():
    p = instrument_prompt(_lofi())
    assert p.startswith("TrackType: Instrument, Genre: Lo-Fi Hip Hop, solo upright piano")
    assert p.endswith("80 BPM")
    assert "in E minor" in p
    assert "gentle laid-back swing" in p


def test_negation_is_rejected():
    s = _lofi()
    s.instrument.techniques = ["soft chords, no drums"]
    with pytest.raises(ValueError, match="negation"):
        instrument_prompt(s)


def test_hype_is_rejected():
    s = _lofi()
    s.moods = ["amazing"]
    with pytest.raises(ValueError, match="hype"):
        instrument_prompt(s)


def test_four_variants_differ():
    s = _lofi()
    s.variants = [
        Variant(axis="register", techniques=["low-mid voicings"]),
        Variant(axis="articulation", techniques=["gently broken chords"]),
        Variant(axis="recording", chain=["roomy mono microphone"]),
        Variant(axis="intensity", mood_override="very soft and sparse"),
    ]
    ps = compile_prompts(s)
    assert len(ps) == 4 and len(set(ps)) == 4


def test_texture_prompt():
    p = texture_prompt("vinyl_crackle")
    assert p.startswith("TrackType: SFX, vinyl record surface noise")
