"""Stable Audio 3 Medium on fal.ai: fallback provider and Phase 0 baseline."""

from __future__ import annotations

import io
import secrets
import time

import httpx
import numpy as np
import soundfile as sf

from engine.generate.base import GenerateRequest, RawClip

ENDPOINT = "fal-ai/stable-audio-3/medium/text-to-audio"


class SA3MediumFal:
    name = "sa3-medium-fal"

    def generate(self, req: GenerateRequest) -> list[RawClip]:
        import fal_client

        clips: list[RawClip] = []
        for i, prompt in enumerate(req.prompts):
            seed = (req.seeds[i] if req.seeds else None) or secrets.randbits(31)
            t0 = time.time()
            result = fal_client.subscribe(
                ENDPOINT,
                arguments={"prompt": prompt, "seconds_total": req.duration_s, "seed": seed, "steps": req.steps},
            )
            url = result["audio_file"]["url"] if "audio_file" in result else result["audio"]["url"]
            data = httpx.get(url, timeout=120).content
            y, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
            clips.append(RawClip(
                audio=y.T, sr=sr, prompt=prompt, seed=seed, provider=self.name,
                model_revision=ENDPOINT, duration_s=req.duration_s, steps=req.steps,
                gen_seconds=time.time() - t0, extra={"fal_result_keys": list(result.keys())},
            ))
        return clips
