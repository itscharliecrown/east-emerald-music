# East Emerald Sample Engine

Private tool that turns a musician's request ("lo-fi piano, warm, E minor, 90 BPM") into DAW-ready 4 or 8 bar loops, stems, and textures with Stable Audio 3. Song starters only, never full songs.

- `CLAUDE.md`: pocket reference for working on this repo
- `docs/prd.md`: full product requirements
- `engine/`: Python engine (Modal GPU app, analysis, conformance, benchmark)
- `web/`: Next.js frontend (Phase 1)

## Phase 0 quickstart

```bash
cd engine
uv sync                              # local, CPU-only deps
uv run pytest                        # analysis + conform tests
modal token new                      # once, opens a browser
modal secret create ee-secrets HF_TOKEN=... ANTHROPIC_API_KEY=... ENGINE_API_TOKEN=...
modal run app.py::download_weights   # once, fills the weights volume
modal run app.py::selftest           # generates a 2 s clip and checks it isn't static
uv run python -m engine.bench.run --suite core --provider sa3-modal
```
