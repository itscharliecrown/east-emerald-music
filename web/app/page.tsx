"use client";
import { useEffect, useRef, useState } from "react";
import { api, type Loop, type RequestState } from "@/lib/api";
import { CandidateCard } from "@/components/CandidateCard";
import { Settings } from "@/components/Settings";

const GENRES = ["Lo-Fi Hip Hop", "Chillhop", "Boom Bap", "Neo-Soul", "R&B", "Trap Soul", "House", "Acoustic Folk", "Bossa Nova", "Pop Ballad", "Cinematic", "Ambient", "Jazz"];
const INSTRUMENTS: [string, string][] = [["", "any"], ["upright_piano", "upright piano"], ["felt_piano", "felt piano"], ["grand_piano", "grand piano"], ["rhodes", "Rhodes"], ["wurlitzer", "Wurlitzer"], ["nylon_guitar", "nylon guitar"], ["steel_acoustic_guitar", "steel acoustic"], ["clean_electric_guitar", "clean electric"], ["jazz_archtop", "jazz archtop"]];
const TONICS = ["", "C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
const MODES = ["minor", "major", "dorian", "mixolydian", "lydian"];
const FAMILY: Record<string, string> = { upright_piano: "piano", felt_piano: "piano", grand_piano: "piano", rhodes: "keys", wurlitzer: "keys", nylon_guitar: "guitar", steel_acoustic_guitar: "guitar", clean_electric_guitar: "guitar", jazz_archtop: "guitar" };

export default function Create() {
  const [text, setText] = useState("");
  const [genre, setGenre] = useState("Lo-Fi Hip Hop");
  const [instrument, setInstrument] = useState("");
  const [tonic, setTonic] = useState("");
  const [mode, setMode] = useState("minor");
  const [bpm, setBpm] = useState("");
  const [bars, setBars] = useState("");
  const [genMode, setGenMode] = useState<"prompt" | "composed">("composed");
  const [complexity, setComplexity] = useState("medium");
  const [pattern, setPattern] = useState("");
  const [progression, setProgression] = useState("");
  const [noise, setNoise] = useState("0.45");
  const [req, setReq] = useState<RequestState | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [engineState, setEngineState] = useState<"unknown" | "waking" | "ready">("unknown");
  const [showRejected, setShowRejected] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => { api.wake().then(() => setEngineState("waking")).catch(() => setEngineState("unknown")); }, []);

  const poll = (id: string) => {
    if (timer.current) window.clearInterval(timer.current);
    timer.current = window.setInterval(async () => {
      try {
        const r = await api.request(id); setReq(r);
        if (r.status === "done" || r.status === "failed") { window.clearInterval(timer.current!); setBusy(false); setEngineState("ready"); }
      } catch (e) { setErr((e as Error).message); }
    }, 1000);
  };

  const submit = async (extra: { text?: string; parent_loop_id?: string } = {}) => {
    setErr(""); setBusy(true); setReq(null);
    const overrides: Record<string, unknown> = { genre };
    if (instrument) { overrides.instrument_type = instrument; overrides.instrument_family = FAMILY[instrument]; }
    if (tonic) overrides.key = { tonic, mode };
    if (bpm) overrides.bpm = Number(bpm);
    if (bars) overrides.bars = Number(bars);
    overrides.generation_mode = genMode;
    overrides.complexity = complexity;
    if (pattern) overrides.pattern = pattern;
    if (progression.trim()) overrides.progression = progression.trim();
    if (genMode === "composed") overrides.init_noise_level = Number(noise);
    try {
      const { request_id } = await api.create({ text: extra.text ?? text, overrides, parent_loop_id: extra.parent_loop_id });
      poll(request_id);
    } catch (e) { setErr((e as Error).message); setBusy(false); }
  };

  const refine = (l: Loop, kind: "variation" | "companion") => {
    const t = kind === "companion" ? `A different instrument that fits this ${l.instrument_type.replace(/_/g, " ")} loop` : `More like this`;
    setText(t); submit({ text: t, parent_loop_id: l.id });
  };

  const update = (l: Loop) => setReq((r) => r && { ...r, loops: r.loops.map((x) => (x.id === l.id ? l : x)) });
  const passed = req?.loops.filter((l) => l.status === "passed") ?? [];
  const rejected = req?.loops.filter((l) => l.status === "rejected") ?? [];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between"><Settings /><span className="font-mono text-xs opacity-50">engine: {engineState}</span></div>

      <div className="rounded-xl border border-white/10 bg-white/2 p-4">
        <textarea className="inp h-20 w-full text-base" placeholder="lo-fi piano, warm, soft chords, E minor, 80 BPM" value={text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(); }} />
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <select className="inp" value={genre} onChange={(e) => setGenre(e.target.value)}>{GENRES.map((g) => <option key={g}>{g}</option>)}</select>
          <select className="inp" value={instrument} onChange={(e) => setInstrument(e.target.value)}>{INSTRUMENTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
          <select className="inp" value={tonic} onChange={(e) => setTonic(e.target.value)}>{TONICS.map((t) => <option key={t} value={t}>{t || "key: auto"}</option>)}</select>
          <select className="inp" value={mode} onChange={(e) => setMode(e.target.value)} disabled={!tonic}>{MODES.map((m) => <option key={m}>{m}</option>)}</select>
          <input className="inp w-24" placeholder="BPM auto" value={bpm} onChange={(e) => setBpm(e.target.value.replace(/\D/g, ""))} />
          <select className="inp" value={bars} onChange={(e) => setBars(e.target.value)}><option value="">bars: auto</option><option value="4">4 bars</option><option value="8">8 bars</option></select>
          <button className="btn ml-auto bg-emerald-700! px-4! py-2! text-sm" disabled={busy || text.trim().length < 2} onClick={() => submit()}>{busy ? "generating…" : "Generate ⌘↵"}</button>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-white/10 pt-3 text-xs">
          <span className="opacity-50">harmony</span>
          <select className="inp" value={genMode} onChange={(e) => setGenMode(e.target.value as "prompt" | "composed")}>
            <option value="composed">composed (exact chords + MIDI)</option>
            <option value="prompt">prompt (free, model decides)</option>
          </select>
          <select className="inp" value={complexity} onChange={(e) => setComplexity(e.target.value)}>
            <option value="basic">basic: triads</option>
            <option value="medium">medium: 7ths + 9ths</option>
            <option value="complex">complex: extended + borrowed</option>
          </select>
          <select className="inp" value={pattern} onChange={(e) => setPattern(e.target.value)}>
            <option value="">pattern: auto</option><option value="sustained">sustained</option><option value="broken">broken (lo-fi comp)</option>
            <option value="arpeggio">arpeggio</option><option value="stabs">stabs</option><option value="fingerstyle">fingerstyle</option><option value="strum">strum</option>
          </select>
          <input className="inp w-72" placeholder="chords (optional): im9 · ivm7 · bVIImaj7 · v7sus4" value={progression} onChange={(e) => setProgression(e.target.value)} />
          {genMode === "composed" && (
            <label className="flex items-center gap-1 opacity-70">timbre freedom
              <input type="range" min="0.25" max="0.75" step="0.05" value={noise} onChange={(e) => setNoise(e.target.value)} /> {noise}
            </label>
          )}
        </div>
      </div>

      {err && <div className="rounded border border-red-900 bg-red-950/30 p-3 text-sm text-red-200">{err}</div>}

      {req && (
        <div className="space-y-3">
          <div className="flex items-center gap-3 text-sm">
            <span className="font-mono text-xs uppercase tracking-wide text-emerald-300">{req.status}</span>
            {req.spec && <span className="opacity-70">{req.spec.instrument?.type.replace(/_/g, " ")} · {req.spec.key?.tonic} {req.spec.key?.mode} · {req.spec.bpm} BPM · {req.spec.bars} bars · {req.spec.genre}</span>}
            {req.gpu_seconds !== undefined && req.gpu_seconds !== null && <span className="ml-auto font-mono text-xs opacity-40">gpu {req.gpu_seconds}s · {req.batches_run} batch</span>}
          </div>
          {req.error && <div className="text-sm text-red-300">{req.error}</div>}
          {req.spec && (
            <div className="grid gap-2 text-xs md:grid-cols-2">
              {req.spec.pushback && <div className="rounded border border-amber-900/50 bg-amber-950/20 p-2 text-amber-100"><b>Pushback:</b> {req.spec.pushback}</div>}
              {req.spec.harmony?.progression && (
                <div className="rounded border border-white/10 p-2"><b>Harmony ({req.spec.harmony.complexity}, {req.spec.harmony.pattern}):</b> <span className="font-mono">{req.spec.harmony.progression.map((c) => `${c.degree}${c.quality}`).join(" · ")}</span>
                  {req.voicings && <div className="mt-1 font-mono opacity-60">{req.voicings.join(" · ")}</div>}
                  <div className="mt-1 opacity-60">{req.spec.harmony.rationale}</div></div>
              )}
              {req.spec.assumptions && req.spec.assumptions.length > 0 && (
                <div className="rounded border border-white/10 p-2 opacity-80"><b>Assumed:</b> {req.spec.assumptions.join(" · ")}</div>
              )}
            </div>
          )}
          {passed.map((l, i) => <CandidateCard key={l.id} loop={l} index={i} onChange={update} onRefine={refine} warnings={req.warnings?.[l.id]} />)}
          {req.status === "done" && passed.length === 0 && <div className="text-sm opacity-70">Nothing passed the gates. Try again, or loosen the request.</div>}
          {rejected.length > 0 && (
            <div>
              <button className="text-xs opacity-50 hover:opacity-100" onClick={() => setShowRejected(!showRejected)}>{showRejected ? "hide" : "show"} {rejected.length} rejected</button>
              {showRejected && <div className="mt-2 space-y-2">{rejected.map((l) => <CandidateCard key={l.id} loop={l} />)}</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
