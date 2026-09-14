"""Stem purity + vocal leakage via Demucs htdemucs_6s (GPU only; PRD §7.5)."""

from __future__ import annotations

import numpy as np

STEMS = ("drums", "bass", "other", "vocals", "guitar", "piano")


_MODELS: dict[str, object] = {}


def _model(name: str):
    if name not in _MODELS:
        from demucs.pretrained import get_model
        m = get_model(name)
        m.cuda().eval()
        _MODELS[name] = m
    return _MODELS[name]


def stem_shares(x: np.ndarray, sr: int, model_name: str = "htdemucs_6s") -> dict[str, float]:
    """Energy share of each stem, summing to 1. Heuristic: the 6s piano stem is known to be weak."""
    import torch
    from demucs.apply import apply_model

    model = _model(model_name)
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
    """Share of energy that is NOT foreign material (drums, bass, vocals).

    Phase 0 calibration (2026-09-12): htdemucs_6s files most solo piano under "other" (piano
    stem 0.23–0.67 on clips with zero drums), so "requested stem share" punished clean takes.
    Bleed from drums/bass/vocals is the signal that matters for a solo instrument loop.
    """
    if family == "drums":
        return shares.get("drums", 0.0) + 0.5 * shares.get("other", 0.0)   # percussion often lands in "other"
    foreign = shares.get("drums", 0.0) + shares.get("vocals", 0.0)
    # Demucs files a guitar's thumb bass / low strings as "bass" (Charlie rated those clips
    # 4–5, no bass instrument present). Only count bass as foreign for keyboard families.
    if family not in ("guitar", "bass"):
        foreign += shares.get("bass", 0.0)
    return max(0.0, 1.0 - foreign)
