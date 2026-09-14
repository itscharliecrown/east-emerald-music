"use client";
import { useCallback, useEffect, useState } from "react";
import { api, type Loop, type Session } from "@/lib/api";
import { LoopRow } from "@/components/LoopRow";
import { fullDate, when } from "@/lib/format";
import { player } from "@/lib/player";

export default function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [liked, setLiked] = useState(true);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { const r = await api.sessions(liked); setSessions(r.sessions); setErr(""); if (!open && r.sessions[0]) setOpen(r.sessions[0].id); }
    catch (e) { setErr((e as Error).message); }
  }, [liked, open]);
  useEffect(() => { load(); }, [load]);

  const update = (sid: string) => (l: Loop) => setSessions((ss) => ss.map((s) => (s.id === sid ? { ...s, loops: s.loops.map((x) => (x.id === l.id ? { ...x, ...l } : x)) } : s)));

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <div><h1 className="serif text-4xl leading-tight">Sessions</h1><p className="mt-1 text-sm text-dust">One song idea per session: the loop you started from and everything built on it.</p></div>
        <div className="flex gap-1 rounded-full border border-line p-0.5 text-xs">
          <button className={`rounded-full px-3 py-1 ${liked ? "bg-felt-2 text-paper" : "text-dust"}`} onClick={() => setLiked(true)}>Liked</button>
          <button className={`rounded-full px-3 py-1 ${!liked ? "bg-felt-2 text-paper" : "text-dust"}`} onClick={() => setLiked(false)}>Everything</button>
        </div>
      </div>
      {err && <div className="rounded-lg border border-ember/40 bg-ember/10 p-3 text-sm">{err}</div>}
      {!err && sessions.length === 0 && <p className="text-sm text-dust">{liked ? "No liked loops yet. Like a take and it becomes a session." : "No sessions yet."}</p>}
      <div className="space-y-3">
        {sessions.map((s) => {
          const on = open === s.id;
          return (
            <div key={s.id} className={`rounded-xl border ${on ? "border-line" : "border-transparent"}`}>
              <button className="flex w-full items-baseline gap-3 rounded-xl px-4 py-3 text-left hover:bg-felt" onClick={() => { setOpen(on ? null : s.id); if (!on) player.setQueue(s.loops.filter((l) => l.provider !== "midi")); }}>
                <span className="serif min-w-0 flex-1 truncate text-xl">{s.title}</span>
                {s.key && <span className="sig text-xl">{s.key.tonic}{s.key.mode === "major" ? "maj" : s.key.mode === "minor" ? "min" : s.key.mode} {s.bpm}</span>}
                <span className="shrink-0 text-xs text-dust">{s.loops.length} loop{s.loops.length === 1 ? "" : "s"} · {s.genre} · <span title={fullDate(s.updated_at)}>{when(s.updated_at)}</span></span>
              </button>
              {on && (
                <div className="px-2 pb-3">
                  <div className="mb-2 flex justify-end px-2"><a className="btn" href={api.sessionZipUrl(s.id, liked)}>Download session (WAV + MIDI)</a></div>
                  <div className="divide-y divide-line/60">{s.loops.map((l) => <LoopRow key={l.id} loop={l} queue={s.loops} onChange={update(s.id)} />)}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
