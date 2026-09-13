"""Stem purity + vocal leakage via Demucs htdemucs_6s (GPU only; PRD §7.5)."""

from __future__ import annotations

import numpy as np

STEMS = ("drums", "bass", "other", "vocals", "guitar", "piano")


def stem_shares(x: np.ndarray, sr: int, model_name: str = "htdemucs_6s") -> dict[str, float]:
    """Energy share of each stem, summing to 1. Heuristic: the 6s piano stem is known to be weak."""
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model

    model = get_model(model_name)
    model.cuda().eval()
    wav = torch.tensor(x, dtype=torch.float32)
    if wav.ndim == 1:
        wav = wav[None].repeat(2, 1)
    if sr != model.samplerate:
        import torchaudio
        wav = torchaudio.functional.resample(wav, sr, model.samplerate)
    with torch.no_grad():
        sources = apply_model(model, wav[None].cuda(), split=True, overlap=0.25)[0].cpu().numpy()
    energies = {name: float(np.mean(src ** 2)) for name, src in zip(model.sources, sources)}
    total = sum(energies.values()) + 1e-12
    return {k: v / total for k, v in energies.items()}


def purity_for(shares: dict[str, float], family: str) -> float:
    key = {"piano": "piano", "keys": "piano", "guitar": "guitar"}.get(family, "other")
    return shares.get(key, 0.0)
