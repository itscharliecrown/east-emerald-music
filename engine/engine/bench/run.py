"""Phase 0 benchmark runner.

    uv run python -m engine.bench.run --suite core --provider sa3-fal --only 01_lofi_upright
    uv run python -m engine.bench.run --suite core --provider sa3-modal

Writes engine/bench/out/<suite>/<provider>/<item>/<k>.wav plus results.jsonl with analysis,
gate result, and timings. The listening sheet is built from results.jsonl by listening_sheet.py.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import yaml
from rich.console import Console
from rich.table import Table

from engine.analyze import analyze
from engine.conform.level import normalize_level
from engine.conform.window import cut_loop, find_loop_window
from engine.export import write_wav24
from engine.gate import evaluate, rank_score
from engine.generate.base import GenerateRequest
from engine.prompts import compile_prompts
from engine.spec import LoopSpec, Variant

OUT = Path(__file__).resolve().parents[2] / "bench" / "out"
console = Console()


def load_suite(name: str) -> tuple[dict, list[LoopSpec]]:
    data = yaml.safe_load((Path(__file__).parent / "suite.yaml").read_text())
    variants = [Variant(**v) for v in data["default_variants"]]
    specs = []
    for item in data["items"]:
        item = dict(item)
        item_id = item.pop("id")
        spec = LoopSpec(**item, variants=variants)
        spec.__dict__["_id"] = item_id
        specs.append(spec)
    return data, specs


def make_provider(name: str):
    if name == "sa3-fal":
        from engine.generate.sa3_fal import SA3MediumFal
        return SA3MediumFal()
    if name == "sa3-modal":
        from engine.generate.sa3_modal import SA3MediumModal
        return SA3MediumModal()
    raise SystemExit(f"unknown provider {name}")


def run_item(spec: LoopSpec, provider, out_dir: Path, candidates: int) -> list[dict]:
    prompts = compile_prompts(spec)[:candidates]
    req = GenerateRequest(prompts=prompts, duration_s=spec.generate_seconds)
    t0 = time.time()
    clips = provider.generate(req)
    gen_wall = time.time() - t0
    rows = []
    for k, clip in enumerate(clips):
        raw_path = out_dir / f"{k}_raw.wav"
        write_wav24(raw_path, clip.audio, clip.sr)
        a = analyze(clip.audio, clip.sr, target_bpm=spec.bpm,
                    bar_samples=int(round(spec.bar_seconds * clip.sr)), rhythmic=spec.feel.rhythmic)
        g = evaluate(spec, a)
        row = {
            "item": spec.__dict__.get("_id"), "k": k, "provider": clip.provider, "prompt": clip.prompt,
            "seed": clip.seed, "gen_seconds": clip.gen_seconds, "gen_wall_batch": gen_wall,
            "analysis": a.to_dict(), "gate": asdict(g), "raw": str(raw_path),
        }
        # Best-effort conformed cut (no stretch here; Phase 0 measures, Phase 1 corrects).
        try:
            mono = clip.audio.mean(axis=0)
            w = find_loop_window(mono, clip.sr, loop_samples=spec.loop_samples, bars=spec.bars,
                                 downbeats_s=a.tempo.downbeats)
            loop = cut_loop(clip.audio, clip.sr, start=w.start_sample, loop_samples=spec.loop_samples)
            loop, lvl = normalize_level(loop, clip.sr)
            loop_path = out_dir / f"{k}_loop.wav"
            write_wav24(loop_path, loop, clip.sr)
            row.update({"loop": str(loop_path), "window": asdict(w), "level": lvl,
                        "score": rank_score(a, g, spec, seam_score=w.seam_score)})
        except Exception as e:  # noqa: BLE001
            row.update({"loop": None, "window_error": str(e)})
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="core")
    ap.add_argument("--provider", default="sa3-fal")
    ap.add_argument("--only", nargs="*", help="item ids")
    ap.add_argument("--candidates", type=int, default=None)
    args = ap.parse_args()

    data, specs = load_suite(args.suite)
    candidates = args.candidates or data["candidates"]
    provider = make_provider(args.provider)
    out_root = OUT / args.suite / args.provider
    out_root.mkdir(parents=True, exist_ok=True)
    results = out_root / "results.jsonl"

    table = Table(title=f"{args.suite} / {args.provider}")
    for col in ("item", "k", "bpm req", "bpm got", "err%", "drift", "key req", "key got", "str", "gate", "gen s"):
        table.add_column(col)

    with results.open("a") as f:
        for spec in specs:
            sid = spec.__dict__["_id"]
            if args.only and sid not in args.only:
                continue
            console.print(f"[bold]{sid}[/] {spec.generate_seconds}s × {candidates}")
            rows = run_item(spec, provider, out_root / sid, candidates)
            for r in rows:
                f.write(json.dumps(r) + "\n")
                a, g = r["analysis"], r["gate"]
                table.add_row(
                    sid, str(r["k"]), f"{spec.bpm:.0f}", f"{a['tempo']['bpm']:.1f}",
                    f"{abs(a['tempo']['bpm'] - spec.bpm) / spec.bpm * 100:.1f}", f"{a['tempo']['drift_cv']:.3f}",
                    spec.key.label(), f"{a['key']['tonic']}{a['key']['mode'][:3]}", f"{a['key']['strength']:.2f}",
                    "PASS" if g["passed"] else ",".join(g["reasons"]), f"{r['gen_seconds']:.1f}",
                )
    console.print(table)
    console.print(f"results → {results}")


if __name__ == "__main__":
    main()
