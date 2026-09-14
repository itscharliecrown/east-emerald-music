"""SQLite library index on the ee-data volume (PRD §12). Single writer: the web container."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # FastAPI runs sync endpoints on a threadpool; one connection, serialized by the caller's lock.
    con = sqlite3.connect(str(path), timeout=30, isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("pragma journal_mode = wal")
    con.execute("pragma foreign_keys = on")
    con.execute("pragma busy_timeout = 30000")
    migrate(con)
    return con


def migrate(con: sqlite3.Connection) -> None:
    con.execute("create table if not exists schema_version (v integer primary key)")
    have = {r[0] for r in con.execute("select v from schema_version")}
    for f in sorted(MIGRATIONS.glob("*.sql")):
        v = int(f.name.split("_")[0])
        if v in have:
            continue
        con.executescript(f.read_text())
        con.execute("insert into schema_version (v) values (?)", (v,))


def _j(v: Any) -> str:
    return json.dumps(v, separators=(",", ":"))


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def upsert_request(con: sqlite3.Connection, r: dict) -> None:
    cols = ("id", "created_at", "completed_at", "mode", "raw_text", "overrides", "spec", "parent_loop_id",
            "status", "error", "llm_model", "llm_usage", "gpu_seconds", "batches_run")
    row = {c: r.get(c) for c in cols}
    for c in ("overrides", "spec", "llm_usage"):
        if row[c] is not None and not isinstance(row[c], str):
            row[c] = _j(row[c])
    if row["overrides"] is None:
        row["overrides"] = "{}"
    row["created_at"] = row["created_at"] or _now()
    row["batches_run"] = row["batches_run"] or 0
    con.execute(
        f"insert into requests ({','.join(cols)}) values ({','.join('?' * len(cols))}) "
        "on conflict(id) do update set " + ", ".join(f"{c}=excluded.{c}" for c in cols if c not in ("id", "created_at")),
        [row[c] for c in cols],
    )


def upsert_loop(con: sqlite3.Connection, l: dict) -> None:
    cols = ("id", "request_id", "created_at", "candidate_index", "status", "reject_reasons", "category",
            "instrument_family", "instrument_type", "genre", "moods", "key_tonic", "key_mode", "bpm",
            "time_signature", "bars", "length_samples", "filename", "provider", "model_revision", "gen_prompt",
            "seed", "steps", "duration_s", "init_noise_level", "init_audio_sha256", "lora", "analysis_raw",
            "conform_ops", "analysis_final", "score", "wav_path", "raw_path", "midi_path", "preview_path",
            "peaks", "files_purged_at")
    row = {c: l.get(c) for c in cols}
    for c in ("reject_reasons", "moods", "lora", "analysis_raw", "conform_ops", "analysis_final", "peaks"):
        if row[c] is not None and not isinstance(row[c], str):
            row[c] = _j(row[c])
    row["reject_reasons"] = row["reject_reasons"] or "[]"
    row["moods"] = row["moods"] or "[]"
    row["time_signature"] = row["time_signature"] or "4/4"
    row["created_at"] = row["created_at"] or _now()
    con.execute(
        f"insert into loops ({','.join(cols)}) values ({','.join('?' * len(cols))}) "
        "on conflict(id) do update set " + ", ".join(f"{c}=excluded.{c}" for c in cols if c not in ("id", "created_at")),
        [row[c] for c in cols],
    )


def update_curation(con: sqlite3.Connection, loop_id: str, fields: dict) -> None:
    allowed = {"kept", "stars", "favorite", "used_in_track", "notes"}
    upd = {k: v for k, v in fields.items() if k in allowed}
    if not upd:
        return
    con.execute(f"update loops set {', '.join(f'{k}=?' for k in upd)} where id=?", [*upd.values(), loop_id])


def get_request(con: sqlite3.Connection, rid: str) -> dict | None:
    r = con.execute("select * from requests where id=?", (rid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["loops"] = [dict(x) for x in con.execute(
        "select * from loops where request_id=? order by status desc, score desc, candidate_index", (rid,))]
    return d


def get_loop(con: sqlite3.Connection, lid: str) -> dict | None:
    r = con.execute("select * from loops where id=?", (lid,)).fetchone()
    return dict(r) if r else None


def list_loops(con: sqlite3.Connection, *, family=None, instrument=None, key=None, mode=None, bpm_min=None,
               bpm_max=None, genre=None, bars=None, kept=None, favorite=None, passed_only=True,
               limit=60, offset=0) -> list[dict]:
    where, args = [], []
    if passed_only:
        where.append("status='passed'")
    for col, val in (("instrument_family", family), ("instrument_type", instrument), ("key_tonic", key),
                     ("key_mode", mode), ("genre", genre), ("bars", bars)):
        if val is not None:
            where.append(f"{col}=?"); args.append(val)
    if bpm_min is not None:
        where.append("bpm>=?"); args.append(bpm_min)
    if bpm_max is not None:
        where.append("bpm<=?"); args.append(bpm_max)
    if kept is not None:
        where.append("kept=?"); args.append(int(kept))
    if favorite:
        where.append("favorite=1")
    sql = "select * from loops" + (" where " + " and ".join(where) if where else "") + \
          " order by created_at desc limit ? offset ?"
    return [dict(r) for r in con.execute(sql, [*args, limit, offset])]


def list_requests(con: sqlite3.Connection, *, limit=50, offset=0) -> list[dict]:
    rows = [dict(r) for r in con.execute(
        "select r.*, "
        "(select count(*) from loops l where l.request_id=r.id and l.status='passed') as passed_count, "
        "(select count(*) from loops l where l.request_id=r.id and l.kept=1) as liked_count "
        "from requests r order by created_at desc limit ? offset ?", (limit, offset))]
    return rows
