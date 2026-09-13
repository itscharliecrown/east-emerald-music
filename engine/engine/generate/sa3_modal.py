"""Client for the Modal-hosted SA3 Medium engine (the GPU code is in engine/app.py)."""

from __future__ import annotations

import numpy as np

from engine.generate.base import GenerateRequest, RawClip


class SA3MediumModal:
    name = "sa3-medium-modal"

    def __init__(self, app_name: str = "east-emerald-engine"):
        import modal

        self._cls = modal.Cls.from_name(app_name, "Engine")

    def generate(self, req: GenerateRequest) -> list[RawClip]:
        out = self._cls().generate.remote(
            prompts=req.prompts,
            duration_s=req.duration_s,
            seeds=req.seeds,
            steps=req.steps,
            init_audio=None if req.init_audio is None else (req.init_audio[0], req.init_audio[1].tolist()),
            init_noise_level=req.init_noise_level,
            inpaint_ranges_s=req.inpaint_ranges_s,
        )
        return [
            RawClip(
                audio=np.asarray(c["audio"], dtype=np.float32), sr=c["sr"], prompt=c["prompt"],
                seed=c["seed"], provider=self.name, model_revision=c["model_revision"],
                duration_s=req.duration_s, steps=req.steps, gen_seconds=c["gen_seconds"],
            )
            for c in out
        ]
