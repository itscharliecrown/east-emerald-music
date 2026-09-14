import json

from engine import db


def test_migrate_and_roundtrip(tmp_path):
    con = db.connect(tmp_path / "t.db")
    db.upsert_request(con, {"id": "r1", "mode": "prompt", "raw_text": "lo-fi piano", "status": "queued"})
    db.upsert_loop(con, {"id": "l1", "request_id": "r1", "candidate_index": 0, "status": "passed",
                         "category": "instrument", "instrument_family": "piano", "instrument_type": "upright_piano",
                         "key_tonic": "E", "key_mode": "minor", "bpm": 80, "bars": 8, "provider": "sa3",
                         "model_revision": "x", "gen_prompt": "TrackType: ...", "score": 0.7,
                         "reject_reasons": [], "moods": ["warm"], "peaks": [0.1, 0.2]})
    # upsert again with a status change
    db.upsert_request(con, {"id": "r1", "mode": "prompt", "raw_text": "lo-fi piano", "status": "done"})
    r = db.get_request(con, "r1")
    assert r["status"] == "done" and len(r["loops"]) == 1
    assert json.loads(r["loops"][0]["moods"]) == ["warm"]
    db.update_curation(con, "l1", {"kept": 1, "stars": 5, "bogus": "x"})
    assert db.get_loop(con, "l1")["stars"] == 5
    assert db.list_loops(con, family="piano", kept=True)[0]["id"] == "l1"
    assert db.list_loops(con, family="guitar") == []


def test_migrations_are_idempotent(tmp_path):
    con = db.connect(tmp_path / "t.db")
    db.migrate(con)
    assert con.execute("select count(*) from schema_version").fetchone()[0] == len(list(db.MIGRATIONS.glob("*.sql")))
