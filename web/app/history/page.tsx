"use client";
import { useEffect, useState } from "react";
import { api, type Loop, type RequestSummary } from "@/lib/api";
import { LoopRow } from "@/components/LoopRow";
import { fullDate, when } from "@/lib/format";

export default function History() {
  const [rows, setRows] = useState<RequestSummary[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [loops, setLoops] = useState<Record<string, Loop[]>>({});
  const [err, setErr] = useState("");

  useEffect(() => { api.requests().then((r) => setRows(r.requests)).catch((e) => setErr((e as Error).message)); }, []);

  const toggle = async (id: string) => {
    if (open === id) return setOpen(null);
    setOpen(id);
    if (!loops[id]) { const r = await api.request(id); setLoops((m) => ({ ...m, [id]: r.loops.filter((l) => l.status === "passed") })); }
  };
  const update = (id: string) => (l: Loop) => setLoops((m) => ({ ...m, [id]: m[id].map((x) => (x.id === l.id ? { ...x, ...l } : x)) }));

  return (
    <div className="space-y-6">
      <div><h1 className="serif text-4xl leading-tight">History</h1><p className="mt-1 text-sm text-dust">Every request, newest first.</p></div>
      {err && <div className="rounded-lg border border-ember/40 bg-ember/10 p-3 text-sm">{err.includes("disabled") ? "The engine is offline. Check the Modal workspace." : err}</div>}
      <div className="divide-y divide-line/60">
        {rows.map((r) => {
          const s = r.summary || {};
          return (
            <div key={r.id} className="py-2">
              <button className="flex w-full items-baseline gap-3 rounded-lg px-3 py-2 text-left hover:bg-felt" onClick={() => toggle(r.id)}>
                <span className="w-20 shrink-0 text-xs text-dust" title={fullDate(r.created_at)}>{when(r.created_at)}</span>
                <span className="serif min-w-0 flex-1 truncate text-[17px]">{r.raw_text}</span>
                {s.key && <span className="sig shrink-0">{s.key.tonic}{s.key.mode === "major" ? "maj" : s.key.mode === "minor" ? "min" : s.key.mode} {s.bpm}</span>}
                <span className="shrink-0 text-xs text-dust">{r.status === "done" ? `${r.passed_count} kept${r.liked_count ? `, ${r.liked_count} liked` : ""}` : r.status}</span>
              </button>
              {open === r.id && (
                <div className="ml-3 mt-1 divide-y divide-line/60 border-l border-line pl-3">
                  {(loops[r.id] ?? []).map((l) => <LoopRow key={l.id} loop={l} queue={loops[r.id]} onChange={update(r.id)} showDate={false} />)}
                  {loops[r.id] && loops[r.id].length === 0 && <p className="py-2 text-xs text-dust">No take passed the checks.</p>}
                  {r.error && <p className="py-2 text-xs text-ember">{r.error}</p>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
