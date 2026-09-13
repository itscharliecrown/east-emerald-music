from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


@dataclass
class GenerateRequest:
    prompts: list[str]
    duration_s: float
    seeds: list[int] | None = None
    steps: int = 8
    init_audio: tuple[int, np.ndarray] | None = None     # (sr, (ch, n))
    init_noise_level: float | None = None
    inpaint_ranges_s: list[tuple[float, float]] | None = None
    lora: list[dict] = field(default_factory=list)


@dataclass
class RawClip:
    audio: np.ndarray            # float32 (2, n) at sr
    sr: int
    prompt: str
    seed: int
    provider: str
    model_revision: str
    duration_s: float
    steps: int
    gen_seconds: float           # wall time for the batch / batch size
    extra: dict = field(default_factory=dict)


class Generator(Protocol):
    name: str

    def generate(self, req: GenerateRequest) -> list[RawClip]: ...
