"""Deterministic LoopSpec → Stable Audio 3 prompt compiler (PRD §9).

Format:
  TrackType: Instrument, Genre: {genre}, {solo} {instrument} {technique} in {Key} {mode},
  {mood}, {chain}, {space}, {bpm} BPM
"""

from __future__ import annotations

import re

from engine.spec import LoopSpec, Variant

# Words the encoder can't use. We fail loudly rather than ship a weak prompt.
_NEGATION = re.compile(r"\b(no|not|without|never|avoid)\b", re.IGNORECASE)
_HYPE = {"amazing", "high quality", "best", "professional", "masterpiece", "hq", "4k"}

_TYPE_PHRASE: dict[str, str] = {
    "grand_piano": "concert grand piano",
    "upright_piano": "upright piano",
    "felt_piano": "felt piano",
    "rhodes": "Rhodes electric piano",
    "wurlitzer": "Wurlitzer electric piano",
    "nylon_guitar": "nylon-string classical guitar",
    "steel_acoustic_guitar": "steel-string acoustic guitar",
    "clean_electric_guitar": "clean electric guitar, neck pickup",
    "jazz_archtop": "hollow-body jazz guitar",
}

_TEXTURE_PHRASE: dict[str, tuple[str, str, str]] = {
    "vinyl_crackle": (
        "vinyl record surface noise",
        "soft continuous crackle and gentle hiss from a spinning turntable",
        "warm, steady and even",
    ),
    "tape_hiss": ("cassette tape hiss", "steady broadband hiss with faint wow", "warm, even"),
    "room_tone": ("quiet studio room tone", "steady air and distant hum", "intimate, even"),
    "rain": ("gentle rain on a window", "steady soft rainfall without thunder", "calm, distant"),
}


def _join(parts: list[str]) -> str:
    return ", ".join(p.strip() for p in parts if p and p.strip())


def _validate(prompt: str) -> str:
    if _NEGATION.search(prompt):
        raise ValueError(f"prompt contains a negation: {prompt!r}")
    low = prompt.lower()
    for word in _HYPE:
        if word in low:
            raise ValueError(f"prompt contains hype word {word!r}: {prompt!r}")
    if not prompt.startswith("TrackType:"):
        raise ValueError("prompt must start with TrackType:")
    return prompt


def key_phrase(spec: LoopSpec) -> str:
    return f"in {spec.key.tonic} {spec.key.mode}"


def instrument_prompt(spec: LoopSpec, variant: Variant | None = None) -> str:
    inst = spec.instrument
    techniques = (variant.techniques if variant and variant.techniques else inst.techniques)
    chain = variant.chain if variant and variant.chain else spec.production.chain
    moods = [variant.mood_override] if variant and variant.mood_override else spec.moods

    body = _join([
        f"solo {_TYPE_PHRASE.get(inst.type, inst.type.replace('_', ' '))}",
        " and ".join(techniques) if techniques else "",
    ])
    parts = [
        "TrackType: Instrument",
        f"Genre: {spec.genre}",
        f"{body} {key_phrase(spec)}",
        _feel_phrase(spec),
        " and ".join(moods) if moods else "",
        _join(chain),
        spec.production.space,
        f"{int(round(spec.bpm))} BPM",
    ]
    return _validate(_join(parts))


def _feel_phrase(spec: LoopSpec) -> str:
    f = spec.feel
    if not f.rhythmic:
        return "free time, rubato"
    bits = []
    if f.swing_pct >= 60:
        bits.append("swung sixteenth-note feel")
    elif f.swing_pct > 52:
        bits.append("gentle laid-back swing")
    if f.half_time:
        bits.append("half-time feel")
    return ", ".join(bits)


def texture_prompt(texture_type: str) -> str:
    source, behavior, character = _TEXTURE_PHRASE[texture_type]
    return _validate(_join(["TrackType: SFX", source, behavior, character]))


def compile_prompts(spec: LoopSpec) -> list[str]:
    """One prompt per variant (4), or a single base prompt if no variants."""
    if spec.category == "texture":
        return [texture_prompt(spec.instrument.type)]
    if not spec.variants:
        return [instrument_prompt(spec)]
    return [instrument_prompt(spec, v) for v in spec.variants]
