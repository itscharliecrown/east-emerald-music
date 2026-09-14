"""FastAPI app (PRD §13). Mounted on Modal by app.py. Single SQLite writer lives here."""

import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from engine import db


class CreateRequest(BaseModel):
    text: str = Field(min_length=2, max_length=600)
    mode: str = "prompt"
    overrides: dict = Field(default_factory=dict)
    candidates: int = Field(4, ge=1, le=4)
    parent_loop_id: str | None = None


class Curation(BaseModel):
    kept: bool | None = None
    stars: int | None = Field(None, ge=1, le=5)
    favorite: bool | None = None
    used_in_track: str | None = None
    notes: str | None = None


def build_app(*, data_root: Path, spawn_job, wake, reload_volume) -> FastAPI:
    """spawn_job(request_id, text, overrides, mode, parent) → None; wake() warms the GPU class."""
    app = FastAPI(title="East Emerald Sample Engine")
    # Local dev, any Vercel deployment of this project, plus CORS_ORIGINS for the custom domain.
    origins = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o]
    origins += ["http://localhost:3000", "http://127.0.0.1:3000"]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_origin_regex=r"https://.*\.vercel\.app",
                       allow_methods=["*"], allow_headers=["*"])
    token = os.environ.get("ENGINE_API_TOKEN", "")
    db_path = data_root / "ee.db"

    @contextmanager
    def conn(reload: bool = False):
        # Modal Volumes can't reload while a file is open, so: reload first, open, use, close.
        if reload:
            reload_volume()
        con = db.connect(db_path)
        try:
            yield con
        finally:
            con.close()


    def auth(request: Request):
        if not token:
            return
        h = request.headers.get("authorization", "")
        q = request.query_params.get("token", "")
        if h != f"Bearer {token}" and q != token:
            raise HTTPException(401, "bad token")


    def sync_job(rid: str) -> dict | None:
        """Read the job file the GPU wrote and upsert into SQLite (single writer = this process)."""
        p = data_root / "jobs" / f"{rid}.json"
        with conn(reload=True) as con:
            if not p.exists():
                return db.get_request(con, rid)
            j = json.loads(p.read_text())
            return _ingest(con, rid, j)

    def _ingest(con, rid: str, j: dict) -> dict | None:
        db.upsert_request(con, {
            "id": rid, "created_at": j.get("created_at"), "completed_at": j.get("completed_at"),
            "mode": j.get("mode", "prompt"), "raw_text": j.get("raw_text", ""), "overrides": j.get("overrides", {}),
            "spec": j.get("spec"), "status": j.get("status", "queued"), "error": j.get("error"),
            "llm_model": j.get("llm_model"), "llm_usage": j.get("llm_usage"), "gpu_seconds": j.get("gpu_seconds"),
            "batches_run": j.get("batches_run", 0), "parent_loop_id": j.get("parent_loop_id"),
        })
        for l in j.get("loops", []):
            db.upsert_loop(con, l)
        out = db.get_request(con, rid)
        if out:
            out["warnings"] = {l["id"]: l.get("warnings", []) for l in j.get("loops", [])}
            out["voicings"] = j.get("voicings")
        return out

    @app.get("/v1/health")
    async def health():
        with conn() as con:
            return {"ok": True, "loops": con.execute("select count(*) from loops").fetchone()[0]}

    @app.post("/v1/wake", status_code=202, dependencies=[Depends(auth)])
    async def wake_endpoint():
        wake()
        return {"waking": True}

    @app.post("/v1/requests", status_code=202, dependencies=[Depends(auth)])
    async def create(body: CreateRequest):
        rid = uuid.uuid4().hex
        with conn() as con:
            parent = db.get_loop(con, body.parent_loop_id) if body.parent_loop_id else None
            if parent:
                parent = {k: parent[k] for k in ("key_tonic", "key_mode", "bpm", "bars", "time_signature",
                                                 "instrument_type", "genre", "gen_prompt")}
            db.upsert_request(con, {"id": rid, "mode": body.mode, "raw_text": body.text, "overrides": body.overrides,
                                    "status": "queued", "parent_loop_id": body.parent_loop_id})
        spawn_job(rid, body.text, body.overrides, body.mode, parent, body.candidates)
        return {"request_id": rid}

    @app.get("/v1/requests/{rid}", dependencies=[Depends(auth)])
    async def get_request(rid: str):
        r = sync_job(rid)
        if not r:
            raise HTTPException(404)
        for k in ("spec", "overrides", "llm_usage"):
            if isinstance(r.get(k), str):
                r[k] = json.loads(r[k])
        for l in r["loops"]:
            for k in ("reject_reasons", "moods", "analysis_raw", "conform_ops", "analysis_final", "peaks"):
                if isinstance(l.get(k), str):
                    l[k] = json.loads(l[k])
        return r

    @app.get("/v1/loops", dependencies=[Depends(auth)])
    async def loops(family: str | None = None, instrument: str | None = None, key: str | None = None,
              mode: str | None = None, genre: str | None = None, bars: int | None = None,
              bpm_min: float | None = None, bpm_max: float | None = None, kept: bool | None = None,
              favorite: bool = False, limit: int = Query(60, le=200), offset: int = 0):
        with conn() as con:
            rows = db.list_loops(con, family=family, instrument=instrument, key=key, mode=mode, genre=genre,
                             bars=bars, bpm_min=bpm_min, bpm_max=bpm_max, kept=kept, favorite=favorite,
                             limit=limit, offset=offset)
        for l in rows:
            for k in ("reject_reasons", "moods", "peaks"):
                if isinstance(l.get(k), str):
                    l[k] = json.loads(l[k])
            l.pop("analysis_raw", None); l.pop("analysis_final", None)
        return {"loops": rows}

    @app.patch("/v1/loops/{lid}", dependencies=[Depends(auth)])
    async def patch_loop(lid: str, body: Curation):
        with conn() as con:
            if not db.get_loop(con, lid):
                raise HTTPException(404)
            db.update_curation(con, lid, {k: (int(v) if isinstance(v, bool) else v)
                                          for k, v in body.model_dump(exclude_none=True).items()})
            return db.get_loop(con, lid)

    @app.get("/v1/loops/{lid}/download", dependencies=[Depends(auth)])
    async def download(lid: str, format: str = "wav"):
        with conn(reload=True) as con:
            l = db.get_loop(con, lid)
        if not l:
            raise HTTPException(404)
        rel = {"wav": l.get("wav_path"), "raw": l.get("raw_path"), "midi": l.get("midi_path")}.get(format)
        if not rel:
            raise HTTPException(404, f"no {format} for this loop")
        path = data_root / rel
        name = l["filename"] if format == "wav" else Path(rel).name
        return FileResponse(path, filename=name, media_type="audio/wav" if format == "wav" else "application/octet-stream")

    @app.get("/v1/loops/{lid}/audio", dependencies=[Depends(auth)])
    async def audio(lid: str):
        """Inline playback (no Content-Disposition attachment)."""
        with conn(reload=True) as con:
            l = db.get_loop(con, lid)
        if not l or not l.get("wav_path"):
            raise HTTPException(404)
        return FileResponse(data_root / l["wav_path"], media_type="audio/wav")

    static = Path(__file__).resolve().parents[1] / "static"
    if static.exists():
        app.mount("/", StaticFiles(directory=str(static), html=True), name="static")
    return app
