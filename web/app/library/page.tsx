"use client";
import { useCallback, useEffect, useState } from "react";
import { api, type Loop } from "@/lib/api";
import { LoopRow } from "@/components/LoopRow";
import { player } from "@/lib/player";

const TONICS = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];

export default function Library() {
  const [loops, setLoops] = useState<Loop[]>([]);
  const [liked, setLiked] = useState(true);
  const [family, setFamily] = useState("");
  const [key, setKey] = useState("");
  const [genre, setGenre] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.loops({ family, key, genre, kept: liked ? true : undefined, limit: 200 });
      setLoops(r.loops); setErr(""); player.setQueue(r.loops);
    } catch (e) { setErr((e as Error).message); } finally { setLoading(false); }
  }, [family, key, genre, liked]);
  useEffect(() => { load(); }, [load]);

  const update = (l: Loop) => setLoops((xs) => xs.map((x) => (x.id === l.id ? { ...x, ...l } : x)));
  const genres = Array.from(new Set(loops.map((l) => l.genre))).sort();

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div><h1 className="serif text-4xl leading-tight">Library</h1><p className="mt-1 text-sm text-dust">{loops.length} loop{loops.length === 1 ? "" : "s"}{liked ? " you liked" : ""}</p></div>
        <div className="flex gap-1 rounded-full border border-line p-0.5 text-xs">
          <button className={`rounded-full px-3 py-1 ${liked ? "bg-felt-2 text-paper" : "text-dust"}`} onClick={() => setLiked(true)}>Liked</button>
          <button className={`rounded-full px-3 py-1 ${!liked ? "bg-felt-2 text-paper" : "text-dust"}`} onClick={() => setLiked(false)}>Everything</button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {[["", "All instruments"], ["piano", "Piano"], ["keys", "Keys"], ["guitar", "Guitar"]].map(([v, l]) => <button key={v} className={`chip ${family === v ? "chip-on" : ""}`} onClick={() => setFamily(v)}>{l}</button>)}
        <span className="w-2" />
        <select className="inp py-1 text-xs" value={key} onChange={(e) => setKey(e.target.value)}><option value="">Any key</option>{TONICS.map((t) => <option key={t}>{t}</option>)}</select>
        <select className="inp py-1 text-xs" value={genre} onChange={(e) => setGenre(e.target.value)}><option value="">Any genre</option>{genres.map((g) => <option key={g}>{g}</option>)}</select>
      </div>
      {err && <div className="rounded-lg border border-ember/40 bg-ember/10 p-3 text-sm">{err.includes("disabled") ? "The engine is offline, so the library can’t load. Check the Modal workspace." : err}</div>}
      {!err && !loading && loops.length === 0 && (
        <p className="text-sm text-dust">{liked ? "Nothing liked yet. Tap ♡ on a take you’d build a track on." : "No loops yet. Generate something."}</p>
      )}
      <div className="divide-y divide-line/60">{loops.map((l) => <LoopRow key={l.id} loop={l} queue={loops} onChange={update} />)}</div>
    </div>
  );
}
