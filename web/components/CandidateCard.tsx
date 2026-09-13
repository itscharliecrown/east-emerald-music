"use client";
import { useEffect, useState } from "react";
import { api, keyLabel, type Loop } from "@/lib/api";
import { onPlayingChange, play, playingId } from "@/lib/audio";
import { Waveform } from "./Waveform";

const fmt = (n: unknown, d = 1) => (typeof n === "number" ? n.toFixed(d) : "–");

export function CandidateCard({ loop, index, onChange, onRefine, warnings = [] }: {
  loop: Loop; index?: number; onChange?: (l: Loop) => void; onRefine?: (l: Loop, kind: "variation" | "companion") => void; warnings?: string[];
}) {
  const [playing, setPlaying] = useState(playingId() === loop.id);
  const [click, setClick] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => onPlayingChange((id) => setPlaying(id === loop.id)), [loop.id]);

  const passed = loop.status === "passed";
  const ops = (loop.conform_ops || {}) as { time_ratio?: number; semitones?: number; key_shift?: number; tuning_cents_in?: number; seam_score?: number };
  const raw = (loop.analysis_raw || {}) as { tempo?: { bpm?: number }; key?: { tonic?: string; mode?: string; strength?: number }; purity?: number };
  const corrections: string[] = [];
  if (ops.time_ratio && Math.abs(ops.time_ratio - 1) > 0.002) corrections.push(`stretched ${((ops.time_ratio - 1) * 100).toFixed(1)}%`);
  if (ops.key_shift) corrections.push(`shifted ${ops.key_shift > 0 ? "+" : ""}${ops.key_shift} st`);
  if (typeof ops.tuning_cents_in === "number" && Math.abs(ops.tuning_cents_in) > 3) corrections.push(`tuned ${ops.tuning_cents_in > 0 ? "-" : "+"}${Math.abs(ops.tuning_cents_in).toFixed(0)}c`);

  const patch = async (body: Record<string, unknown>) => {
    setBusy(true);
    try { const l = await api.patch(loop.id, body); onChange?.({ ...loop, ...l }); } finally { setBusy(false); }
  };

  return (
    <div className={`rounded-lg border p-3 ${passed ? "border-white/10 bg-white/3" : "border-red-900/40 bg-red-950/10 opacity-70"}`}>
      <div className="flex items-center gap-3 text-sm">
        {index !== undefined && <span className="font-mono text-xs opacity-50">{index + 1}</span>}
        <span className="font-mono text-emerald-300">{keyLabel(loop)} · {Math.round(loop.bpm)} BPM · {loop.bars} bar</span>
        <span className="opacity-70">{loop.instrument_type.replace(/_/g, " ")}</span>
        {passed && <span className="ml-auto font-mono text-xs opacity-50">score {fmt(loop.score, 2)}</span>}
        {!passed && <span className="ml-auto font-mono text-xs text-red-300">{loop.reject_reasons.join(", ")}</span>}
      </div>
      {passed && (
        <>
          <div className="mt-2 cursor-pointer" onClick={() => play(loop.id, api.audioUrl(loop.id), { bpm: loop.bpm, click })}>
            <Waveform peaks={loop.peaks} bars={loop.bars} active={playing} />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <button className="btn" onClick={() => play(loop.id, api.audioUrl(loop.id), { bpm: loop.bpm, click })}>{playing ? "■ stop" : "▶ loop"}</button>
            <label className="flex items-center gap-1 opacity-70"><input type="checkbox" checked={click} onChange={(e) => setClick(e.target.checked)} /> click</label>
            <span className="opacity-50">got {fmt(raw.tempo?.bpm)} BPM · {raw.key?.tonic}{raw.key?.mode === "minor" ? "min" : "maj"} ({fmt(raw.key?.strength, 2)}) · purity {fmt(raw.purity, 2)}</span>
            {corrections.length > 0 && <span className="rounded bg-amber-900/40 px-1.5 py-0.5 text-amber-200">{corrections.join(" · ")}</span>}
            {warnings.map((w) => <span key={w} className="rounded bg-white/10 px-1.5 py-0.5 opacity-70">{w}</span>)}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <button disabled={busy} className={`btn ${loop.kept ? "bg-emerald-700!" : ""}`} onClick={() => patch({ kept: !loop.kept })}>{loop.kept ? "✓ kept" : "keep"}</button>
            <button disabled={busy} className="btn" onClick={() => patch({ kept: false })}>reject</button>
            <span className="ml-1">{[1, 2, 3, 4, 5].map((s) => <button key={s} disabled={busy} onClick={() => patch({ stars: s })} className={`px-0.5 ${loop.stars && s <= loop.stars ? "text-amber-300" : "opacity-30"}`}>★</button>)}</span>
            <button disabled={busy} className={`btn ${loop.favorite ? "bg-pink-800!" : ""}`} onClick={() => patch({ favorite: !loop.favorite })}>♥</button>
            <a className="btn" href={api.downloadUrl(loop.id, "wav")}>↓ WAV</a>
            <a className="btn" href={api.downloadUrl(loop.id, "raw")}>↓ raw</a>
            {onRefine && <button className="btn" onClick={() => onRefine(loop, "companion")}>+ companion</button>}
          </div>
          {loop.filename && <div className="mt-1 font-mono text-[10px] opacity-40">{loop.filename}</div>}
        </>
      )}
      <details className="mt-1 text-[11px] opacity-50"><summary className="cursor-pointer">prompt</summary><div className="font-mono">{loop.gen_prompt}</div></details>
    </div>
  );
}
