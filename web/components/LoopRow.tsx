"use client";
import { useState } from "react";
import { api, type Loop } from "@/lib/api";
import { fullDate, instrumentName, loopTitle, signature, when } from "@/lib/format";
import { jobsStore } from "@/lib/jobs";
import { current, player, usePlayer } from "@/lib/player";

const fmt = (n: unknown, d = 1) => (typeof n === "number" ? n.toFixed(d) : "–");
const COMPANIONS: [string, string][] = [["drums", "Drums"], ["felt_piano", "Felt piano"], ["rhodes", "Rhodes"], ["nylon_guitar", "Nylon guitar"], ["steel_acoustic_guitar", "Steel guitar"], ["clean_electric_guitar", "Clean electric"]];

export function LoopRow({ loop, queue, onChange, showDate = true }: { loop: Loop; queue: Loop[]; onChange?: (l: Loop) => void; showDate?: boolean }) {
  const s = usePlayer();
  const isCurrent = current()?.id === loop.id;
  const playing = isCurrent && s.playing;
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState<"" | "vary" | "add" | "melody">("");
  const [melodyText, setMelodyText] = useState("");
  const midiOnly = loop.provider === "midi";
  const ops = (loop.conform_ops || {}) as { time_ratio?: number; key_shift?: number; tuning_cents_in?: number };
  const raw = (loop.analysis_raw || {}) as { tempo?: { bpm?: number }; key?: { tonic?: string; mode?: string }; purity?: number; harmony?: { mean?: number } | null };
  const fixes: string[] = [];
  if (ops.time_ratio && Math.abs(ops.time_ratio - 1) > 0.002) fixes.push(`stretched ${((ops.time_ratio - 1) * 100).toFixed(1)}%`);
  if (ops.key_shift) fixes.push(`shifted ${ops.key_shift > 0 ? "+" : ""}${ops.key_shift} st`);
  if (typeof ops.tuning_cents_in === "number" && Math.abs(ops.tuning_cents_in) > 3) fixes.push(`retuned ${Math.abs(ops.tuning_cents_in).toFixed(0)}c`);

  const like = async () => {
    setBusy(true);
    try { const l = await api.patch(loop.id, { kept: !loop.kept }); onChange?.({ ...loop, ...l }); } finally { setBusy(false); }
  };
  const vary = async (strength: "subtle" | "medium" | "bold") => {
    setMenu(""); const { request_id } = await api.variation(loop.id, strength);
    jobsStore.track(request_id, `${strength} variation of ${loopTitle(loop)}`);
  };
  const add = async (kind: string) => {
    setMenu(""); const { request_id } = await api.companion(loop.id, kind);
    jobsStore.track(request_id, `${kind === "drums" ? "Drums" : instrumentName(kind)} for ${loopTitle(loop)}`);
  };
  const melody = async (kind: string) => {
    setMenu(""); const { request_id } = await api.melody(loop.id, kind === "same" ? "" : kind, melodyText.trim()); setMelodyText("");
    jobsStore.track(request_id, `Melody${kind === "same" ? "" : " on " + instrumentName(kind).toLowerCase()} for ${loopTitle(loop)}`);
  };
  // Chrome: drag the WAV straight to Finder/desktop (and DAWs that accept file drops).
  const onDrag = (e: React.DragEvent) => {
    const url = api.downloadUrl(loop.id, midiOnly ? "midi" : "wav");
    const name = loop.filename || "loop.wav";
    e.dataTransfer.setData("DownloadURL", `${midiOnly ? "audio/midi" : "audio/wav"}:${name}:${url}`);
    e.dataTransfer.setData("text/uri-list", url);
    e.dataTransfer.effectAllowed = "copy";
  };

  return (
    <div className={`row ${isCurrent ? "row-active" : ""}`} draggable onDragStart={onDrag} title="Drag to your desktop or DAW">
      {midiOnly ? (
        <span className="flex h-9 w-9 items-center justify-center rounded-full border border-line text-[10px] text-brass">MIDI</span>
      ) : (
        <button className={`flex h-9 w-9 items-center justify-center rounded-full border ${playing ? "border-jade bg-jade text-ink" : "border-line text-paper hover:border-jade"}`}
          aria-label={playing ? "Pause" : "Play"} onClick={() => player.play(loop, queue.filter((q) => q.provider !== "midi"))}>{playing ? "❚❚" : "▶"}</button>
      )}
      <div className="min-w-0">
        <div className="flex items-baseline gap-3">
          <span className="serif truncate text-[17px]">{loopTitle(loop)}</span>
          <span className="sig shrink-0 text-[17px]">{signature(loop)}</span>
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-dust">
          <span>{midiOnly ? "Chord MIDI" : instrumentName(loop.instrument_type)}</span>
          <span>{loop.bars} bars</span>
          <span>{loop.genre}</span>
          {showDate && <span title={fullDate(loop.created_at)}>{when(loop.created_at)}</span>}
          {fixes.length > 0 && <span className="text-brass/80">{fixes.join(", ")}</span>}
          <button className="hover:text-paper" onClick={() => setOpen(!open)}>{open ? "less" : "details"}</button>
        </div>
        {open && (
          <div className="mt-2 space-y-1 text-xs text-dust">
            {raw.tempo && <div>Measured {fmt(raw.tempo?.bpm)} BPM, {raw.key?.tonic}{raw.key?.mode === "minor" ? "min" : "maj"}, purity {fmt(raw.purity, 2)}{raw.harmony && `, harmony ${fmt(raw.harmony.mean, 2)}`}</div>}
            <div>{loop.seed != null && `Seed ${loop.seed} · `}created {fullDate(loop.created_at)}</div>
            <div className="font-mono text-[11px] leading-relaxed">{loop.gen_prompt}</div>
            <div className="font-mono text-[11px]">{loop.filename}</div>
          </div>
        )}
        {menu === "vary" && (
          <div className="mt-2 flex gap-1 text-xs">{(["subtle", "medium", "bold"] as const).map((k) => <button key={k} className="chip" onClick={() => vary(k)}>{k}</button>)}<button className="chip" onClick={() => setMenu("")}>cancel</button></div>
        )}
        {menu === "melody" && (
          <div className="mt-2 space-y-2 text-xs">
            <input className="inp w-full" placeholder="Direction (optional): sparse and singable · climb into bar 6 · bluesy" value={melodyText} onChange={(e) => setMelodyText(e.target.value)} />
            <div className="flex flex-wrap gap-1">
              <button className="chip" onClick={() => melody("same")}>Same instrument</button>
              {COMPANIONS.filter(([k]) => k !== "drums" && k !== loop.instrument_type).map(([k, l]) => <button key={k} className="chip" onClick={() => melody(k)}>{l}</button>)}
              <button className="chip" onClick={() => setMenu("")}>cancel</button>
            </div>
          </div>
        )}
        {menu === "add" && (
          <div className="mt-2 flex flex-wrap gap-1 text-xs">{COMPANIONS.filter(([k]) => k !== loop.instrument_type).map(([k, l]) => <button key={k} className="chip" onClick={() => add(k)}>{l}</button>)}<button className="chip" onClick={() => setMenu("")}>cancel</button></div>
        )}
      </div>
      <div className="flex items-center gap-1">
        <button disabled={busy} className={`btn btn-ghost text-base ${loop.kept ? "text-ember" : "text-dust"}`} aria-pressed={!!loop.kept} aria-label={loop.kept ? "Unlike" : "Like"} onClick={like}>{loop.kept ? "♥" : "♡"}</button>
        {!midiOnly && <button className="btn btn-ghost text-xs" title="More like this" onClick={() => setMenu(menu === "vary" ? "" : "vary")}>Vary</button>}
        {!midiOnly && loop.category !== "drums" && <button className="btn btn-ghost text-xs" title="Write a melody over this loop" onClick={() => setMenu(menu === "melody" ? "" : "melody")}>Melody</button>}
        {!midiOnly && <button className="btn btn-ghost text-xs" title="Add a companion part" onClick={() => setMenu(menu === "add" ? "" : "add")}>Add</button>}
        {loop.midi_path && <a className="btn btn-ghost text-xs" href={api.downloadUrl(loop.id, "midi")}>MIDI</a>}
        {!midiOnly && <a className="btn" href={api.downloadUrl(loop.id, "wav")}>WAV</a>}
      </div>
    </div>
  );
}
