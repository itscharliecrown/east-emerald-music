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


# SA3's T5Gemma encoder sees 256 tokens. Past that the prompt is silently truncated and the
# BPM (last) is the first casualty. Budgets keep every prompt well inside the window.
MAX_TECHNIQUES = 3
MAX_MOODS = 3
MAX_CHAIN = 3
MAX_WORDS = 80


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        k = it.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(it.strip())
    return out


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
    if len(prompt.split()) > MAX_WORDS:
        raise ValueError(f"prompt has {len(prompt.split())} words, budget is {MAX_WORDS}: {prompt!r}")
    return prompt


def key_phrase(spec: LoopSpec) -> str:
    return f"in {spec.key.tonic} {spec.key.mode}"


# Genres whose tag summons a drum beat into a "solo" prompt. Phase 0 (2026-09-12): the lo-fi
# piano item carried 49% drum energy and Charlie marked 3/4 clips "has drums, unusable"; every
# other genre measured 0%. For these, the vibe is carried by descriptive words instead.
_BEAT_GENRES = {"lo-fi hip hop", "lofi hip hop", "lo-fi", "lofi", "boom bap", "hip hop", "trap",
                "trap soul", "chillhop", "jazz-hop", "jazzhop", "r&b", "neo-soul", "neo soul"}
_GENRE_VIBE = {
    "lo-fi hip hop": ["lo-fi", "dusty", "unquantized and human"],
    "lofi hip hop": ["lo-fi", "dusty", "unquantized and human"],
    "lo-fi": ["lo-fi", "dusty"], "lofi": ["lo-fi", "dusty"],
    "boom bap": ["dusty", "sample-ready"],
    "chillhop": ["mellow", "sample-ready"], "jazz-hop": ["jazzy", "sample-ready"], "jazzhop": ["jazzy", "sample-ready"],
    "trap": ["dark", "sparse"], "trap soul": ["smooth", "sparse"],
    "r&b": ["smooth", "soulful"], "neo-soul": ["soulful", "smooth"], "neo soul": ["soulful", "smooth"],
}


def genre_parts(spec: LoopSpec) -> tuple[str, list[str]]:
    """(genre tag or '', extra vibe words). Beat genres drop the tag."""
    g = spec.genre.strip().lower()
    if g in _BEAT_GENRES:
        return "", _GENRE_VIBE.get(g, [g])
    return f"Genre: {spec.genre}", []


def harmony_phrase(spec: LoopSpec) -> str:
    """Words the encoder can act on. Chord symbols mean nothing to it; chord *character* does."""
    if not spec.harmony:
        return ""
    quals = " ".join(c.quality for c in spec.harmony.progression).lower()
    rich = any(q in quals for q in ("9", "11", "13", "maj7", "#11", "b9"))
    if spec.harmony.complexity == "complex" or rich:
        return "rich jazzy extended chords with ninths and major sevenths, smooth voice leading"
    if spec.harmony.complexity == "medium" or "7" in quals:
        return "warm seventh chords, smooth voice leading"
    return "simple open triads"


def instrument_prompt(spec: LoopSpec, variant: Variant | None = None) -> str:
    inst = spec.instrument
    # Variants ADD to the base description; they never drop the musical instruction.
    # Order matters under the caps: the variant's own words come first, then the base.
    techniques = _dedupe((variant.techniques if variant else []) + list(inst.techniques))[:MAX_TECHNIQUES]
    chain = _dedupe(variant.chain if variant and variant.chain else spec.production.chain)[:MAX_CHAIN]
    moods = [variant.mood_override] if variant and variant.mood_override else list(spec.moods)
    genre_tag, vibe = genre_parts(spec)
    moods = _dedupe(vibe[:1] + moods)[:MAX_MOODS]

    body = _join([
        f"solo {_TYPE_PHRASE.get(inst.type, inst.type.replace('_', ' '))} played alone",
        ", ".join(techniques) if techniques else "",
    ])
    parts = [
        "TrackType: Instrument",
        "Format: Solo",
        genre_tag,
        f"{body} {key_phrase(spec)}",
        harmony_phrase(spec),
        _feel_phrase(spec),
        ", ".join(moods) if moods else "",
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


_DRUM_KITS = {
    "lo-fi hip hop": "dusty lo-fi boom bap drum kit, soft swung kick and snare, crisp hats, vinyl-warm",
    "chillhop": "laid-back chillhop drum kit, soft kick, brushed snare, light hats",
    "boom bap": "hard-hitting boom bap drum break, punchy kick, cracking snare, swung hats",
    "neo-soul": "neo-soul drum kit, loose pocket, rimshots, ghost-note hats",
    "r&b": "smooth r&b drum kit, tight kick, snappy snare, light hats",
    "trap soul": "trap drum kit, 808 kick, sharp snare, rolling hi-hats, half-time",
    "house": "four-on-the-floor house drum kit, punchy kick, open hat on the offbeat, clap",
}


def drums_prompt(spec: LoopSpec, variant: Variant | None = None) -> str:
    g = spec.genre.strip().lower()
    kit = _DRUM_KITS.get(g, f"{spec.genre} drum kit")
    extra = ", ".join(_dedupe((variant.techniques if variant else []) + list(spec.instrument.techniques)))[:80]
    parts = ["TrackType: Instrument", "Format: Solo", f"Genre: {spec.genre}", f"solo drum loop played alone, {kit}",
             extra, _feel_phrase(spec), ", ".join(spec.moods[:2]), f"{int(round(spec.bpm))} BPM"]
    return _validate(_join(parts))


def compile_prompts(spec: LoopSpec) -> list[str]:
    """One prompt per variant (4), or a single base prompt if no variants."""
    if spec.category == "texture":
        return [texture_prompt(spec.instrument.type)]
    if spec.category == "drums" or spec.instrument.family == "drums":
        return [drums_prompt(spec, v) for v in spec.variants] if spec.variants else [drums_prompt(spec)]
    if not spec.variants:
        return [instrument_prompt(spec)]
    return [instrument_prompt(spec, v) for v in spec.variants]
