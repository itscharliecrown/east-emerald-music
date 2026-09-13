"""Modal app: SA3 Medium on an L4 GPU, weights volume, self-test, and the Phase 0 entrypoints.

    modal run app.py::download_weights   # once
    modal run app.py::selftest
    modal deploy app.py
"""

from __future__ import annotations

import os
import time

import modal

APP_NAME = "east-emerald-engine"
SA3_REPO = "https://github.com/Stability-AI/stable-audio-3.git"
SA3_COMMIT = "779434a908193105335fd8d833418603625b2859"  # main @ 2026-09-01
# Official prebuilt wheel: torch 2.7 / CUDA 12 / cp311. Compiling from source takes ~1 h.
FLASH_ATTN_WHL = (
    "https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/"
    "flash_attn-2.7.4.post1+cu12torch2.7cxx11abiTRUE-cp311-cp311-linux_x86_64.whl"
)
HF_CACHE = "/weights"
DATA = "/data"

weights_vol = modal.Volume.from_name("sa3-weights", create_if_missing=True)
data_vol = modal.Volume.from_name("ee-data", create_if_missing=True)
secrets = [modal.Secret.from_name("ee-secrets")]

image = (
    modal.Image.from_registry("nvidia/cuda:12.6.3-devel-ubuntu22.04", add_python="3.11")
    .apt_install("git", "ffmpeg", "fluidsynth", "libsndfile1", "libsndfile1-dev", "libsamplerate0-dev",
                 "libfftw3-dev", "meson", "ninja-build", "pkg-config", "wget", "bzip2")
    # Ubuntu 22.04 ships Rubber Band 2 (no R3 engine). Build 3.3.0 from source (~1 min).
    .run_commands(
        "cd /tmp && wget -q https://breakfastquay.com/files/releases/rubberband-3.3.0.tar.bz2"
        " && tar xf rubberband-3.3.0.tar.bz2 && cd rubberband-3.3.0"
        " && meson setup build -Ddefault_library=static -Dfft=fftw -Dresampler=libsamplerate"
        " -Djni=disabled -Dladspa=disabled -Dlv2=disabled -Dvamp=disabled -Dtests=disabled"
        " && ninja -C build && ninja -C build install && ldconfig && rubberband --version"
    )
    .pip_install("torch==2.7.1", "torchaudio==2.7.1", index_url="https://download.pytorch.org/whl/cu126")
    .pip_install("packaging", "ninja", "wheel")
    .pip_install(FLASH_ATTN_WHL)   # a broken install produces static; the selftest catches it
    .pip_install(f"git+{SA3_REPO}@{SA3_COMMIT}")
    .pip_install(
        "scipy", "soundfile", "librosa", "pyloudnorm", "pydantic>=2.7", "pyyaml",
        "git+https://github.com/CPJKU/beat_this.git", "demucs", "fastapi[standard]", "anthropic",
    )
    .env({"HF_HOME": HF_CACHE, "HF_HUB_ENABLE_HF_TRANSFER": "0", "TORCH_HOME": f"{HF_CACHE}/torch"})
    .add_local_dir("migrations", remote_path="/root/migrations")
    .add_local_python_source("engine")
)

app = modal.App(APP_NAME, image=image, secrets=secrets)


@app.function(volumes={HF_CACHE: weights_vol}, timeout=60 * 60)
def download_weights():
    """Pull SA3 Medium (gated: needs HF_TOKEN with accepted terms) into the volume once."""
    from huggingface_hub import snapshot_download

    for repo in ("stabilityai/stable-audio-3-medium",):
        p = snapshot_download(repo, token=os.environ["HF_TOKEN"])
        print("downloaded", repo, "->", p)
    weights_vol.commit()


@app.cls(
    gpu="L4",
    volumes={HF_CACHE: weights_vol, DATA: data_vol},
    scaledown_window=120,
    max_containers=2,
    timeout=600,
)
class Engine:
    @modal.enter()
    def load(self):
        import torch
        from stable_audio_3 import StableAudioModel

        t0 = time.time()
        self.model = StableAudioModel.from_pretrained("medium", device="cuda")
        self.revision = f"stable-audio-3-medium@{SA3_COMMIT}"
        torch.cuda.synchronize()
        print(f"loaded SA3 medium in {time.time() - t0:.1f}s")
        self._selftest()

    def _selftest(self):
        """A broken flash-attn install yields static. Spectral flatness near 1 = noise."""
        import numpy as np

        y = self._run(["TrackType: Instrument, solo upright piano, soft chords, 80 BPM"], 2.0, [1], 8)[0]
        mono = y.mean(axis=0)
        spec = np.abs(np.fft.rfft(mono)) + 1e-9
        flatness = float(np.exp(np.mean(np.log(spec))) / np.mean(spec))
        print(f"selftest spectral flatness = {flatness:.3f}")
        if flatness > 0.5:
            raise RuntimeError(f"self-test failed: output looks like static (flatness {flatness:.2f}). Check flash-attn.")

    def _run(self, prompts, duration_s, seeds, steps, **kw):
        import torch

        outs = []
        for prompt, seed in zip(prompts, seeds):
            audio = self.model.generate(prompt=prompt, duration=duration_s, steps=steps, seed=seed, **kw)
            if isinstance(audio, torch.Tensor):
                audio = audio.detach().float().cpu().numpy()
            audio = audio.squeeze()
            if audio.ndim == 1:
                audio = audio[None, :].repeat(2, axis=0)
            outs.append(audio.astype("float32"))
        return outs

    @modal.method()
    def generate(self, prompts: list[str], duration_s: float, seeds: list[int] | None = None,
                 steps: int = 8, init_audio=None, init_noise_level: float | None = None,
                 inpaint_ranges_s=None) -> list[dict]:
        import secrets as _s

        import torch

        seeds = seeds or [_s.randbits(31) for _ in prompts]
        kw = {}
        if init_audio is not None:
            sr, arr = init_audio
            kw["init_audio"] = (sr, torch.tensor(arr))
            if inpaint_ranges_s:
                kw["inpaint_audio"] = kw.pop("init_audio")
                kw["inpaint_mask_start_seconds"] = [s for s, _ in inpaint_ranges_s]
                kw["inpaint_mask_end_seconds"] = [e for _, e in inpaint_ranges_s]
            elif init_noise_level is not None:
                kw["init_noise_level"] = init_noise_level
        t0 = time.time()
        outs = self._run(prompts, duration_s, seeds, steps, **kw)
        per = (time.time() - t0) / len(prompts)
        # Raw float32 bytes: ~10× faster to ship than nested Python lists.
        return [
            {"audio": o.astype("float32").tobytes(), "shape": list(o.shape), "sr": 44100, "prompt": p,
             "seed": s, "model_revision": self.revision, "gen_seconds": per}
            for o, p, s in zip(outs, prompts, seeds)
        ]

    @modal.method()
    def ping(self) -> bool:
        return True

    @modal.method()
    def run_job(self, request_id: str, text: str, overrides: dict, mode: str, parent: dict | None,
                candidates: int = 4) -> dict:
        """Whole request on this container: intent → generate → analyze → conform → export → job file."""
        from pathlib import Path

        from engine.generate.base import RawClip
        from engine.job import run_request

        engine = self

        class InProcess:
            name = "sa3-medium-modal"

            def generate(self_, req):
                import secrets as _s
                seeds = req.seeds or [_s.randbits(31) for _ in req.prompts]
                t0 = time.time()
                outs = engine._run(req.prompts, req.duration_s, seeds, req.steps)
                per = (time.time() - t0) / len(req.prompts)
                return [RawClip(audio=o, sr=44100, prompt=p, seed=s, provider=self_.name,
                                model_revision=engine.revision, duration_s=req.duration_s, steps=req.steps,
                                gen_seconds=per) for o, p, s in zip(outs, req.prompts, seeds)]

        return run_request(request_id=request_id, text=text, overrides=overrides, mode=mode, parent=parent,
                           generator=InProcess(), data_root=Path(DATA), candidates=candidates,
                           commit=data_vol.commit)

    @modal.method()
    def analyze_gpu(self, audio: bytes, shape: list[int], sr: int, target_bpm: float | None,
                    rhythmic: bool = True, family: str = "piano") -> dict:
        """GPU-side analysis: beat_this tempo/downbeats + Demucs stem purity. Laptop never needs torch."""
        import numpy as np

        from engine.analyze import analyze
        from engine.analyze.purity import purity_for, stem_shares

        x = np.frombuffer(audio, dtype="float32").reshape(shape)
        a = analyze(x, sr, target_bpm=target_bpm, rhythmic=rhythmic)
        shares = stem_shares(x, sr)
        d = a.to_dict()
        d["extra"] = {"stem_shares": shares, "purity": purity_for(shares, family),
                      "vocal_share": shares.get("vocals", 0.0)}
        return d


@app.function(volumes={DATA: data_vol}, max_containers=1, scaledown_window=300, timeout=3600)
@modal.concurrent(max_inputs=32)
@modal.asgi_app()
def web():
    from pathlib import Path

    from engine.api import build_app

    def spawn_job(rid, text, overrides, mode, parent, candidates):
        Engine().run_job.spawn(rid, text, overrides, mode, parent, candidates)

    def wake():
        Engine().ping.spawn()

    return build_app(data_root=Path(DATA), spawn_job=spawn_job, wake=wake, reload_volume=data_vol.reload)


@app.local_entrypoint()
def selftest():
    """Smoke test: cold start (load + flash-attn check) then a timed 4 × 30 s batch, saved locally."""
    import numpy as np
    import soundfile as sf

    prompt = ("TrackType: Instrument, Genre: Lo-Fi Hip Hop, solo upright piano playing soft jazzy chords "
              "in E minor, felt-muted hammers, warm and nostalgic, close-miked through cassette tape "
              "saturation, 80 BPM")
    t0 = time.time()
    out = Engine().generate.remote([prompt] * 4, duration_s=30.0)
    wall = time.time() - t0
    os.makedirs("bench/out/selftest", exist_ok=True)
    for i, c in enumerate(out):
        audio = np.frombuffer(c["audio"], dtype="float32").reshape(c["shape"])
        sf.write(f"bench/out/selftest/{i}.wav", audio.T, c["sr"], subtype="PCM_24")
    print(f"cold call: 4 × 30 s in {wall:.1f}s wall (incl. container start); "
          f"per clip {out[0]['gen_seconds']:.2f}s; saved bench/out/selftest/*.wav")
