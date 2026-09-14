"""LoopSpec: the contract between every pipeline stage (PRD §8)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from engine import SAMPLE_RATE

Tonic = Literal["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
Mode = Literal["major", "minor", "dorian", "mixolydian", "lydian", "phrygian"]
TimeSignature = Literal["4/4", "3/4", "6/8"]
Category = Literal["instrument", "texture", "one_shot"]
VariantAxis = Literal["register", "articulation", "recording", "intensity"]

# Quarter notes per bar, the DAW convention (PRD §7.6). BPM is always quarter-note BPM.
QUARTERS_PER_BAR: dict[str, int] = {"4/4": 4, "3/4": 3, "6/8": 3}

PITCH_CLASS: dict[str, int] = {
    "C": 0, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5,
    "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11,
}
PITCH_NAME: dict[int, str] = {v: k for k, v in PITCH_CLASS.items()}


class Key(BaseModel):
    tonic: Tonic
    mode: Mode = "minor"

    @property
    def pitch_class(self) -> int:
        return PITCH_CLASS[self.tonic]

    def label(self) -> str:
        """'Emin', 'Dbmaj', 'Ddorian' for filenames."""
        short = {"major": "maj", "minor": "min"}.get(self.mode, self.mode)
        return f"{self.tonic}{short}"


class Instrument(BaseModel):
    family: str = Field(description="piano | guitar | keys | texture | ...")
    type: str = Field(description="upright_piano, nylon_guitar, ...")
    techniques: list[str] = Field(default_factory=list)
    range_: Literal["low", "low-mid", "mid", "mid-high", "high"] = Field("mid", alias="register")

    model_config = {"populate_by_name": True}


class Feel(BaseModel):
    rhythmic: bool = True
    swing_pct: float = Field(50, ge=50, le=70)
    half_time: bool = False
    static: bool = False


class Production(BaseModel):
    space: str = ""
    chain: list[str] = Field(default_factory=list)


class Chord(BaseModel):
    degree: str = Field(description="Roman numeral, e.g. 'i', 'VI', 'bVII', 'V/3'")
    quality: str = Field(description="m9, maj7, 7, sus4, 6, ...")
    beats: float = Field(gt=0)
    borrowed: bool = False
    note: str = ""


Complexity = Literal["basic", "medium", "complex"]
Pattern = Literal["sustained", "broken", "arpeggio", "stabs", "fingerstyle", "strum"]


class Harmony(BaseModel):
    progression: list[Chord]
    complexity: Complexity = "medium"
    pattern: Pattern = "sustained"
    harmonic_rhythm: str = ""
    rationale: str = ""

    def symbols(self, key: "Key") -> list[str]:
        from engine.compose.theory import chord_symbol
        return [chord_symbol(c, key) for c in self.progression]


class Variant(BaseModel):
    axis: VariantAxis
    techniques: list[str] = Field(default_factory=list)
    chain: list[str] = Field(default_factory=list)
    mood_override: str | None = None


class TextureSuggestion(BaseModel):
    type: str
    reason: str = ""


class LoopSpec(BaseModel):
    category: Category = "instrument"
    generation_mode: Literal["prompt", "composed"] = "prompt"
    instrument: Instrument
    genre: str
    moods: list[str] = Field(default_factory=list)
    key: Key
    bpm: float = Field(ge=50, le=180)
    time_signature: TimeSignature = "4/4"
    bars: Literal[4, 8] = 8
    feel: Feel = Field(default_factory=Feel)
    leave_low_end: bool = True
    production: Production = Field(default_factory=Production)
    harmony: Harmony | None = None
    variants: list[Variant] = Field(default_factory=list)
    texture_suggestions: list[TextureSuggestion] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    pushback: str = ""

    @field_validator("variants")
    @classmethod
    def _four_variants(cls, v: list[Variant]) -> list[Variant]:
        if v and len(v) != 4:
            raise ValueError("variants must be empty or exactly 4")
        return v

    @model_validator(mode="after")
    def _harmony_fits_bars(self) -> "LoopSpec":
        if self.harmony:
            total = sum(c.beats for c in self.harmony.progression)
            expected = self.bars * QUARTERS_PER_BAR[self.time_signature]
            if abs(total - expected) > 1e-6:
                raise ValueError(f"harmony spans {total} beats, loop needs {expected}")
        return self

    # --- bar math (PRD §7.6) ---
    @property
    def quarters_per_bar(self) -> int:
        return QUARTERS_PER_BAR[self.time_signature]

    @property
    def bar_seconds(self) -> float:
        return self.quarters_per_bar * 60.0 / self.bpm

    @property
    def loop_seconds(self) -> float:
        return self.bars * self.bar_seconds

    @property
    def loop_samples(self) -> int:
        return loop_samples(self.bars, self.bpm, self.time_signature)

    @property
    def generate_seconds(self) -> float:
        """(bars + 2) bars: 1 bar pre-roll + 1 bar tail, rounded up to 0.1 s (PRD §7.4)."""
        import math
        return math.ceil((self.bars + 2) * self.bar_seconds * 10) / 10


def loop_samples(bars: int, bpm: float, time_signature: str = "4/4", sr: int = SAMPLE_RATE) -> int:
    """Exact loop length. 8 bars of 4/4 at 90 BPM = 940,800 samples."""
    return round(bars * QUARTERS_PER_BAR[time_signature] * 60.0 / bpm * sr)
