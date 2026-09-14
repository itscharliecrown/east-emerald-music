"""Roman numerals + chord qualities → pitch classes and symbols (PRD §10)."""

from __future__ import annotations

import re

from engine.spec import PITCH_CLASS, PITCH_NAME, Chord, Key

# Scale degrees (semitones from tonic) per mode.
SCALES: dict[str, list[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
}

ROMAN = {"i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6}

# Quality → intervals above the root (semitones). Ordered so guide tones come first after root.
QUALITIES: dict[str, list[int]] = {
    "": [0, 4, 7], "maj": [0, 4, 7], "m": [0, 3, 7], "min": [0, 3, 7], "dim": [0, 3, 6], "aug": [0, 4, 8],
    "6": [0, 4, 7, 9], "m6": [0, 3, 7, 9], "add9": [0, 4, 7, 14], "madd9": [0, 3, 7, 14],
    "sus2": [0, 2, 7], "sus4": [0, 5, 7],
    "maj7": [0, 4, 11, 7], "m7": [0, 3, 10, 7], "7": [0, 4, 10, 7], "dim7": [0, 3, 6, 9], "m7b5": [0, 3, 6, 10],
    "mmaj7": [0, 3, 11, 7], "7sus4": [0, 5, 10, 7], "7sus2": [0, 2, 10, 7],
    "maj9": [0, 4, 11, 14, 7], "m9": [0, 3, 10, 14, 7], "9": [0, 4, 10, 14, 7], "9sus4": [0, 5, 10, 14, 7],
    "m11": [0, 3, 10, 14, 17], "11": [0, 4, 10, 14, 17], "maj7#11": [0, 4, 11, 18, 7], "maj9#11": [0, 4, 11, 14, 18],
    "13": [0, 4, 10, 14, 21], "m13": [0, 3, 10, 14, 21], "maj13": [0, 4, 11, 14, 21], "13sus4": [0, 5, 10, 14, 21],
    "7b9": [0, 4, 10, 13, 7], "7#9": [0, 4, 10, 15, 7], "7b13": [0, 4, 10, 20, 7], "m9b5": [0, 3, 6, 10, 14],
    "6/9": [0, 4, 7, 9, 14], "m6/9": [0, 3, 7, 9, 14],
}

_DEG_RE = re.compile(r"^(?P<acc>[b#]?)(?P<num>vii|vi|iv|v|iii|ii|i)(?P<rest>.*)$", re.IGNORECASE)


def parse_degree(degree: str, key: Key) -> tuple[int, bool]:
    """'bVII' in E minor → (pitch class of D, is_upper). Slash bass ('V/3') is ignored here."""
    d = degree.split("/")[0].strip()
    m = _DEG_RE.match(d)
    if not m:
        raise ValueError(f"bad degree {degree!r}")
    num = m.group("num")
    idx = ROMAN[num.lower()]
    acc = m.group("acc")
    # Chart convention: an accidental is relative to the MAJOR scale degree ("bVII" = lowered
    # major 7th = D in E minor), while a bare numeral uses the key's own mode ("VII" in E
    # minor is also D, "VI" is C).
    scale = SCALES["major"] if acc else SCALES[key.mode]
    pc = (key.pitch_class + scale[idx]) % 12
    if acc == "b":
        pc = (pc - 1) % 12
    elif acc == "#":
        pc = (pc + 1) % 12
    return pc, num.isupper()


def chord_intervals(c: Chord, is_upper: bool) -> list[int]:
    q = c.quality.strip()
    if q in QUALITIES:
        ivs = QUALITIES[q]
    else:
        # Unknown quality: fall back to the triad implied by the numeral case.
        ivs = QUALITIES["maj" if is_upper else "m"]
    # Lower-case numeral with an ambiguous quality ("7", "9", "6", "add9") means minor.
    if not is_upper and q in ("", "7", "9", "6", "add9", "11", "13"):
        ivs = QUALITIES.get("m" + q, QUALITIES["m"])
    return list(ivs)


def chord_pitch_classes(c: Chord, key: Key) -> tuple[int, list[int]]:
    root, upper = parse_degree(c.degree, key)
    return root, [(root + i) % 12 for i in chord_intervals(c, upper)]


def chord_symbol(c: Chord, key: Key) -> str:
    root, upper = parse_degree(c.degree, key)
    q = c.quality.strip()
    if not upper and q in ("", "7", "9", "6", "add9", "11", "13"):
        q = "m" + q
    return f"{PITCH_NAME[root]}{q}"


def bass_pitch_class(c: Chord, key: Key) -> int:
    """Honors slash-degree basses like 'V/3' (third in the bass) and 'I/5'."""
    root, upper = parse_degree(c.degree, key)
    if "/" in c.degree:
        which = c.degree.split("/")[1].strip()
        ivs = chord_intervals(c, upper)
        if which == "3" and len(ivs) > 1:
            return (root + ivs[1]) % 12
        if which == "5":
            return (root + 7) % 12
    return root
