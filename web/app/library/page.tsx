"use client";
import { useCallback, useEffect, useState } from "react";
import { api, type Loop } from "@/lib/api";
import { CandidateCard } from "@/components/CandidateCard";

export default function Library() {
  const [loops, setLoops] = useState<Loop[]>([]);
  const [family, setFamily] = useState("");
  const [key, setKey] = useState("");
  const [mode, setMode] = useState("");
  const [genre, setGenre] = useState("");
  const [bars, setBars] = useState("");
  const [kept, setKept] = useState("");
  const [favorite, setFavorite] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      const r = await api.loops({ family, key, mode, genre, bars: bars ? Number(bars) : undefined, kept: kept === "" ? undefined : kept === "1", favorite, limit: 100 });
      setLoops(r.loops); setErr("");
    } catch (e) { setErr((e as Error).message); }
  }, [family, key, mode, genre, bars, kept, favorite]);
  useEffect(() => { load(); }, [load]);

  const update = (l: Loop) => setLoops((xs) => xs.map((x) => (x.id === l.id ? { ...x, ...l } : x)));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <select className="inp" value={family} onChange={(e) => setFamily(e.target.value)}><option value="">family: all</option><option value="piano">piano</option><option value="keys">keys</option><option value="guitar">guitar</option></select>
        <select className="inp" value={key} onChange={(e) => setKey(e.target.value)}><option value="">key: all</option>{["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"].map((k) => <option key={k}>{k}</option>)}</select>
        <select className="inp" value={mode} onChange={(e) => setMode(e.target.value)}><option value="">mode: all</option><option>minor</option><option>major</option><option>dorian</option></select>
        <input className="inp w-40" placeholder="genre" value={genre} onChange={(e) => setGenre(e.target.value)} />
        <select className="inp" value={bars} onChange={(e) => setBars(e.target.value)}><option value="">bars: all</option><option value="4">4</option><option value="8">8</option></select>
        <select className="inp" value={kept} onChange={(e) => setKept(e.target.value)}><option value="">kept: all</option><option value="1">kept</option><option value="0">rejected</option></select>
        <label className="flex items-center gap-1"><input type="checkbox" checked={favorite} onChange={(e) => setFavorite(e.target.checked)} /> ♥ only</label>
        <span className="ml-auto font-mono opacity-50">{loops.length} loops</span>
      </div>
      {err && <div className="text-sm text-red-300">{err}</div>}
      <div className="grid gap-3 lg:grid-cols-2">{loops.map((l) => <CandidateCard key={l.id} loop={l} onChange={update} />)}</div>
    </div>
  );
}
