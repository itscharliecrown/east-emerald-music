"""One request end to end, on the GPU container (PRD §7). Writes a job file the API reads.

    intent → compile → generate → analyze → conform → gate/rank → export → job json
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from engine.analyze import analyze
from engine.analyze.purity import purity_for, stem_shares
from engine.conform.pipeline import conform_clip
from engine.export import loop_filename, write_raw_flac, write_wav24
from engine.generate.base import GenerateRequest
from engine.intent import parse_intent
from engine.prompts import compile_prompts
from engine.spec import LoopSpec


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _peaks(x: np.ndarray, n: int = 400) -> list[float]:
    mono = np.abs(x).max(axis=0)
    step = max(1, len(mono) // n)
    return [float(mono[i:i + step].max()) for i in range(0, len(mono) - step + 1, step)][:n]


class JobWriter:
    def __init__(self, data_root: Path, request_id: str, commit=None):
        self.path = data_root / "jobs" / f"{request_id}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.commit = commit
        self.state: dict = {"id": request_id, "status": "queued", "loops": [], "created_at": _now()}

    def update(self, **kw):
        self.state.update(kw)
        self.path.write_text(json.dumps(self.state))
        if self.commit:
            self.commit()


def run_request(
    *,
    request_id: str,
    text: str,
    overrides: dict,
    mode: str,
    parent: dict | None,
    generator,             # object with .generate(GenerateRequest) -> list[RawClip], running in-process
    data_root: Path,
    candidates: int = 4,
    max_batches: int = 2,
    commit=None,
) -> dict:
    job = JobWriter(data_root, request_id, commit)
    job.update(status="parsing", mode=mode, raw_text=text, overrides=overrides)
    t_gpu = 0.0
    try:
        intent = parse_intent(text, overrides=overrides, parent=parent)
        spec = intent.spec
        job.update(status="generating", spec=spec.model_dump(by_alias=True), llm_model=intent.model,
                   llm_usage=intent.usage)

        passed: list[dict] = []
        rejected: list[dict] = []
        batches = 0
        while batches < max_batches and len(passed) < 2:
            batches += 1
            prompts = compile_prompts(spec)[:candidates]
            t0 = time.time()
            clips = generator.generate(GenerateRequest(prompts=prompts, duration_s=spec.generate_seconds))
            t_gpu += time.time() - t0
            job.update(status="conforming", batches_run=batches)
            for k, clip in enumerate(clips):
                idx = (batches - 1) * candidates + k
                t0 = time.time()
                a = analyze(clip.audio, clip.sr, target_bpm=spec.bpm, rhythmic=spec.feel.rhythmic)
                shares = stem_shares(clip.audio, clip.sr)
                pur = purity_for(shares, spec.instrument.family)
                res = conform_clip(spec, clip.audio, clip.sr, a, purity=pur, vocal_share=shares.get("vocals", 0.0))
                t_gpu += time.time() - t0
                loop_id = uuid.uuid4().hex
                rec = {
                    "id": loop_id, "request_id": request_id, "created_at": _now(), "candidate_index": idx,
                    "status": "passed" if res.gate.passed else "rejected",
                    "reject_reasons": res.gate.reasons, "warnings": res.gate.warnings,
                    "category": spec.category, "instrument_family": spec.instrument.family,
                    "instrument_type": spec.instrument.type, "genre": spec.genre, "moods": spec.moods,
                    "key_tonic": spec.key.tonic, "key_mode": spec.key.mode, "bpm": spec.bpm,
                    "time_signature": spec.time_signature, "bars": spec.bars,
                    "length_samples": spec.loop_samples if res.loop is not None else None,
                    "provider": clip.provider, "model_revision": clip.model_revision, "gen_prompt": clip.prompt,
                    "seed": clip.seed, "steps": clip.steps, "duration_s": clip.duration_s,
                    "analysis_raw": {**a.to_dict(), "stem_shares": shares, "purity": pur},
                    "conform_ops": res.ops,
                    "analysis_final": res.analysis_final.to_dict() if res.analysis_final else None,
                    "score": res.score,
                }
                raw_path = data_root / "raw" / f"{loop_id}.flac"
                write_raw_flac(raw_path, clip.audio, clip.sr)
                rec["raw_path"] = str(raw_path.relative_to(data_root))
                if res.loop is not None:
                    fname = loop_filename(spec, id4=loop_id[:4])
                    wav_path = data_root / "loops" / fname
                    write_wav24(wav_path, res.loop, clip.sr)
                    rec.update({"filename": fname, "wav_path": str(wav_path.relative_to(data_root)),
                                "peaks": _peaks(res.loop)})
                    passed.append(rec)
                else:
                    rejected.append(rec)
                job.update(loops=passed + rejected)
        passed.sort(key=lambda r: -r["score"])
        job.update(status="done", loops=passed + rejected, completed_at=_now(), gpu_seconds=round(t_gpu, 2),
                   batches_run=batches)
    except Exception as e:  # noqa: BLE001
        job.update(status="failed", error=f"{type(e).__name__}: {e}", completed_at=_now())
        raise
    return job.state
