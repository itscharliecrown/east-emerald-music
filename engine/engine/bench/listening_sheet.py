"""Build a blind listening sheet: shuffled clips, provider hidden, CSV to fill in.

    uv run python -m engine.bench.listening_sheet --suite core
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
from pathlib import Path

from engine.bench.run import OUT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="core")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    root = OUT / args.suite
    rows = []
    for results in root.glob("*/results.jsonl"):
        for line in results.read_text().splitlines():
            r = json.loads(line)
            if r.get("loop"):
                rows.append(r)
    random.Random(args.seed).shuffle(rows)

    blind = root / "blind"
    blind.mkdir(exist_ok=True)
    key_path = root / "blind_key.json"
    sheet_path = root / "listening_sheet.csv"
    key = {}
    with sheet_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["clip", "item", "tone_1_5", "musical_interest_1_5", "usable_1_5", "notes"])
        for i, r in enumerate(rows):
            name = f"clip_{i:03d}.wav"
            shutil.copy(r["loop"], blind / name)
            key[name] = {"provider": r["provider"], "item": r["item"], "k": r["k"], "seed": r["seed"]}
            w.writerow([name, r["item"], "", "", "", ""])
    key_path.write_text(json.dumps(key, indent=2))
    print(f"{len(rows)} clips → {blind}\nsheet: {sheet_path}\nkey (don't peek): {key_path}")


if __name__ == "__main__":
    main()
