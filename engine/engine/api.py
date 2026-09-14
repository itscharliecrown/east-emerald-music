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
    text: str = Field(min_length=1, max_length=600)
    mode: str = "prompt"   # prompt | composed | midi | variation | companion | adjust
    overrides: dict = Field(default_factory=dict)
    candidates: int = Field(4, ge=1, le=4)
    parent_loop_id: str | None = None


class VariationRequest(BaseModel):
    strength: str = "medium"   # subtle | medium | bold


class CompanionRequest(BaseModel):
    kind: str = "drums"        # drums | any instrument type
    text: str = ""


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
            "session_id": j.get("session_id"),
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

    def _parent_payload(con, loop_id: str | None) -> tuple[dict | None, str | None]:
        """Parent loop info for the job + the session it belongs to."""
        if not loop_id:
            return None, None
        loop = db.get_loop(con, loop_id)
        if not loop:
            raise HTTPException(404, "parent loop not found")
        req = db.get_request(con, loop["request_id"]) or {}
        spec = req.get("spec")
        if isinstance(spec, str):
            spec = json.loads(spec)
        parent = {k: loop.get(k) for k in ("id", "key_tonic", "key_mode", "bpm", "bars", "time_signature",
                                            "instrument_type", "instrument_family", "genre", "gen_prompt",
                                            "wav_path", "midi_path", "seed")}
        parent["spec"] = spec
        return parent, req.get("session_id") or loop["request_id"]

    def _launch(con, *, text: str, mode: str, overrides: dict, parent_loop_id: str | None, candidates: int = 4) -> str:
        rid = uuid.uuid4().hex
        parent, session_id = _parent_payload(con, parent_loop_id)
        session_id = session_id or rid
        gen_mode = overrides.get("generation_mode")
        job_mode = "midi" if gen_mode == "midi" else mode
        db.upsert_request(con, {"id": rid, "mode": "prompt" if job_mode in ("adjust", "companion", "midi") else job_mode,
                                "raw_text": text, "overrides": overrides, "status": "queued",
                                "parent_loop_id": parent_loop_id, "session_id": session_id})
        spawn_job(rid, text, overrides, job_mode, parent, candidates, session_id)
        return rid

    @app.post("/v1/requests", status_code=202, dependencies=[Depends(auth)])
    async def create(body: CreateRequest):
        with conn() as con:
            rid = _launch(con, text=body.text, mode=body.mode, overrides=body.overrides,
                          parent_loop_id=body.parent_loop_id, candidates=body.candidates)
        return {"request_id": rid}

    @app.post("/v1/loops/{lid}/variations", status_code=202, dependencies=[Depends(auth)])
    async def variations(lid: str, body: VariationRequest):
        with conn() as con:
            rid = _launch(con, text=f"Variation ({body.strength})", mode="variation",
                          overrides={"strength": body.strength}, parent_loop_id=lid)
        return {"request_id": rid}

    @app.post("/v1/loops/{lid}/companion", status_code=202, dependencies=[Depends(auth)])
    async def companion(lid: str, body: CompanionRequest):
        with conn() as con:
            loop = db.get_loop(con, lid)
            if not loop:
                raise HTTPException(404)
            if body.kind == "drums":
                text = body.text or f"A drum loop that sits under this {loop['instrument_type'].replace('_', ' ')} loop, same tempo and feel"
                overrides = {"companion": "drums", "genre": loop["genre"], "bpm": loop["bpm"], "bars": loop["bars"],
                             "generation_mode": "prompt"}
            else:
                text = body.text or f"A {body.kind.replace('_', ' ')} part that fits this {loop['instrument_type'].replace('_', ' ')} loop, same key, tempo, and chords"
                overrides = {"instrument_type": body.kind, "genre": loop["genre"], "bpm": loop["bpm"], "bars": loop["bars"],
                             "key": {"tonic": loop["key_tonic"], "mode": loop["key_mode"]}, "generation_mode": "composed"}
            rid = _launch(con, text=text, mode="companion", overrides=overrides, parent_loop_id=lid)
        return {"request_id": rid}

    @app.get("/v1/sessions", dependencies=[Depends(auth)])
    async def sessions(liked: bool = False):
        with conn() as con:
            rows = db.list_sessions(con, liked_only=liked)
        for s in rows:
            sp = s.pop("spec", None)
            if isinstance(sp, str):
                sp = json.loads(sp)
            sp = sp or {}
            s["key"] = sp.get("key"); s["bpm"] = sp.get("bpm"); s["genre"] = sp.get("genre")
            for l in s["loops"]:
                for k in ("reject_reasons", "moods", "peaks", "conform_ops"):
                    if isinstance(l.get(k), str):
                        l[k] = json.loads(l[k])
                l.pop("analysis_raw", None); l.pop("analysis_final", None)
        return {"sessions": rows}

    @app.get("/v1/sessions/{sid}/download", dependencies=[Depends(auth)])
    async def session_zip(sid: str, liked: bool = True):
        import io
        import zipfile

        from fastapi.responses import StreamingResponse

        with conn(reload=True) as con:
            rows = [s for s in db.list_sessions(con, liked_only=liked, limit=1000) if s["id"] == sid]
        if not rows:
            raise HTTPException(404)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for l in rows[0]["loops"]:
                for key in ("wav_path", "midi_path"):
                    rel = l.get(key)
                    if rel and (data_root / rel).exists():
                        name = l["filename"] if key == "wav_path" else (l["filename"] or "loop.wav").rsplit(".", 1)[0] + ".mid"
                        z.write(data_root / rel, arcname=name)
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/zip",
                                 headers={"Content-Disposition": f'attachment; filename="EE_session_{sid[:6]}.zip"'})

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

    @app.get("/v1/requests", dependencies=[Depends(auth)])
    async def list_requests(limit: int = Query(50, le=200), offset: int = 0):
        with conn() as con:
            rows = db.list_requests(con, limit=limit, offset=offset)
        for r in rows:
            for k in ("spec", "overrides", "llm_usage"):
                if isinstance(r.get(k), str):
                    r[k] = json.loads(r[k])
            sp = r.get("spec") or {}
            r["summary"] = {"instrument": (sp.get("instrument") or {}).get("type"), "key": sp.get("key"),
                            "bpm": sp.get("bpm"), "bars": sp.get("bars"), "genre": sp.get("genre"),
                            "mode": sp.get("generation_mode")}
            r.pop("spec", None); r.pop("llm_usage", None)
        return {"requests": rows}

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
        name = l["filename"] if format == "wav" else ((l.get("filename") or "loop.wav").rsplit(".", 1)[0] + ".mid" if format == "midi" else Path(rel).name)
        media = {"wav": "audio/wav", "midi": "audio/midi"}.get(format, "application/octet-stream")
        return FileResponse(path, filename=name, media_type=media)

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
