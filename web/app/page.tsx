"use client";
import { useEffect, useRef, useState } from "react";
import { api, type Loop, type RequestState } from "@/lib/api";
import { LoopRow } from "@/components/LoopRow";
import { player } from "@/lib/player";

const GENRES = ["Lo-Fi Hip Hop", "Chillhop", "Boom Bap", "Neo-Soul", "R&B", "Trap Soul", "House", "Acoustic Folk", "Bossa Nova", "Pop Ballad", "Cinematic", "Ambient", "Jazz"];
const INSTRUMENTS: [string, string][] = [["", "Any instrument"], ["felt_piano", "Felt piano"], ["upright_piano", "Upright piano"], ["grand_piano", "Grand piano"], ["rhodes", "Rhodes"], ["wurlitzer", "Wurlitzer"], ["nylon_guitar", "Nylon guitar"], ["steel_acoustic_guitar", "Steel-string guitar"], ["clean_electric_guitar", "Clean electric"], ["jazz_archtop", "Jazz archtop"]];
const TONICS = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
const FAMILY: Record<string, string> = { upright_piano: "piano", felt_piano: "piano", grand_piano: "piano", rhodes: "keys", wurlitzer: "keys", nylon_guitar: "guitar", steel_acoustic_guitar: "guitar", clean_electric_guitar: "guitar", jazz_archtop: "guitar" };
const STEPS: Record<string, string> = { queued: "Waking the engine", parsing: "Reading the brief", composing: "Writing the harmony", generating: "Recording takes", conforming: "Tuning, cutting, leveling" };

export default function Create() {
  const [text, setText] = useState("");
  const [genre, setGenre] = useState("Lo-Fi Hip Hop");
  const [instrument, setInstrument] = useState("");
  const [tonic, setTonic] = useState("");
  const [keyMode, setKeyMode] = useState("minor");
  const [bpm, setBpm] = useState("");
  const [bars, setBars] = useState("");
  const [genMode, setGenMode] = useState<"prompt" | "composed">("composed");
  const [complexity, setComplexity] = useState("medium");
  const [pattern, setPattern] = useState("");
  const [progression, setProgression] = useState("");
  const [noise, setNoise] = useState("0.45");
  const [more, setMore] = useState(false);
  const [req, setReq] = useState<RequestState | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [showRejected, setShowRejected] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => { api.wake().catch(() => {}); return () => { if (timer.current) window.clearInterval(timer.current); }; }, []);

  const poll = (id: string) => {
    if (timer.current) window.clearInterval(timer.current);
    timer.current = window.setInterval(async () => {
      try {
        const r = await api.request(id); setReq(r);
        if (r.status === "done" || r.status === "failed") { window.clearInterval(timer.current!); setBusy(false); }
      } catch (e) { setErr((e as Error).message); window.clearInterval(timer.current!); setBusy(false); }
    }, 1500);
  };

  const submit = async () => {
    setErr(""); setBusy(true); setReq(null);
    const overrides: Record<string, unknown> = { genre, generation_mode: genMode, complexity };
    if (instrument) { overrides.instrument_type = instrument; overrides.instrument_family = FAMILY[instrument]; }
    if (tonic) overrides.key = { tonic, mode: keyMode };
    if (bpm) overrides.bpm = Number(bpm);
    if (bars) overrides.bars = Number(bars);
    if (pattern) overrides.pattern = pattern;
    if (progression.trim()) overrides.progression = progression.trim();
    if (genMode === "composed") overrides.init_noise_level = Number(noise);
    try { const { request_id } = await api.create({ text, overrides }); poll(request_id); }
    catch (e) { setErr((e as Error).message); setBusy(false); }
  };

  const update = (l: Loop) => setReq((r) => r && { ...r, loops: r.loops.map((x) => (x.id === l.id ? l : x)) });
  const passed = req?.loops.filter((l) => l.status === "passed") ?? [];
  const rejected = req?.loops.filter((l) => l.status === "rejected") ?? [];
  useEffect(() => { if (passed.length) player.setQueue(passed); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [req?.status]);
  const sp = req?.spec;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="serif text-4xl leading-tight">What do you need?</h1>
        <p className="mt-1 text-sm text-dust">Describe it like you would to a session player: instrument, how it’s played, the feeling, key and tempo.</p>
      </div>

      <section className="rounded-xl border border-line bg-felt p-4">
        <textarea className="inp h-24 w-full resize-none bg-transparent text-lg" placeholder="felt piano, soft broken chords, nostalgic, E minor, 78" value={text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(); }} />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select className="inp" value={genre} onChange={(e) => setGenre(e.target.value)}>{GENRES.map((g) => <option key={g}>{g}</option>)}</select>
          <select className="inp" value={instrument} onChange={(e) => setInstrument(e.target.value)}>{INSTRUMENTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
          <select className="inp" value={tonic} onChange={(e) => setTonic(e.target.value)}><option value="">Key: let Claude pick</option>{TONICS.map((t) => <option key={t} value={t}>{t}</option>)}</select>
          {tonic && <select className="inp" value={keyMode} onChange={(e) => setKeyMode(e.target.value)}>{["minor", "major", "dorian", "mixolydian", "lydian"].map((m) => <option key={m}>{m}</option>)}</select>}
          <input className="inp w-24" placeholder="BPM" inputMode="numeric" value={bpm} onChange={(e) => setBpm(e.target.value.replace(/\D/g, ""))} />
          <select className="inp" value={bars} onChange={(e) => setBars(e.target.value)}><option value="">Bars: auto</option><option value="4">4 bars</option><option value="8">8 bars</option></select>
          <button className="chip ml-auto" onClick={() => setMore(!more)}>{more ? "Fewer options" : "Harmony options"}</button>
          <button className="btn btn-primary px-4" disabled={busy || text.trim().length < 2} onClick={submit}>{busy ? "Working…" : "Generate"}</button>
        </div>
        {more && (
          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
            <select className="inp" value={genMode} onChange={(e) => setGenMode(e.target.value as "prompt" | "composed")}>
              <option value="composed">Composed: exact chords, MIDI included</option>
              <option value="prompt">Free: the model improvises</option>
            </select>
            <select className="inp" value={complexity} onChange={(e) => setComplexity(e.target.value)}>
              <option value="basic">Basic harmony</option><option value="medium">Medium harmony</option><option value="complex">Complex harmony</option>
            </select>
            <select className="inp" value={pattern} onChange={(e) => setPattern(e.target.value)}>
              <option value="">Pattern: auto</option><option value="sustained">Sustained</option><option value="broken">Broken chords</option><option value="arpeggio">Arpeggio</option><option value="stabs">Stabs</option><option value="fingerstyle">Fingerstyle</option><option value="strum">Strum</option>
            </select>
            <input className="inp w-72" placeholder="Your chords (optional): im9 · ivm7 · bVIImaj7 · v7sus4" value={progression} onChange={(e) => setProgression(e.target.value)} />
            {genMode === "composed" && (
              <label className="flex items-center gap-2 text-xs text-dust">Timbre freedom <input type="range" className="seek w-28" min="0.25" max="0.75" step="0.05" value={noise} onChange={(e) => setNoise(e.target.value)} /> {noise}</label>
            )}
          </div>
        )}
      </section>

      {err && <div className="rounded-lg border border-ember/40 bg-ember/10 p-3 text-sm">{err.includes("disabled") ? "The engine is offline. Check the Modal workspace." : err}</div>}

      {req && (
        <section className="space-y-3">
          {req.status !== "done" && req.status !== "failed" && (
            <div className="flex items-center gap-3 text-sm text-dust"><span className="h-2 w-2 animate-pulse rounded-full bg-jade" />{STEPS[req.status] ?? req.status}…</div>
          )}
          {req.error && <div className="text-sm text-ember">{req.error}</div>}
          {sp && (
            <div className="rounded-xl border border-line p-4">
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <span className="serif text-2xl">{sp.instrument?.type.replace(/_/g, " ")}</span>
                <span className="sig text-2xl">{sp.key?.tonic}{sp.key?.mode === "major" ? "maj" : sp.key?.mode === "minor" ? "min" : sp.key?.mode} {sp.bpm}</span>
                <span className="text-sm text-dust">{sp.bars} bars · {sp.genre}</span>
              </div>
              {sp.harmony?.progression && (
                <div className="mt-2 text-sm">
                  <span className="text-dust">Chords </span><span className="font-mono">{sp.harmony.progression.map((c) => `${c.degree}${c.quality}`).join("  ")}</span>
                  {req.voicings && <div className="mt-1 text-xs text-dust">{req.voicings.join("  ")}</div>}
                  {sp.harmony.rationale && <p className="mt-2 max-w-prose text-sm text-dust">{sp.harmony.rationale}</p>}
                </div>
              )}
              {sp.pushback && <p className="mt-2 max-w-prose text-sm text-brass">{sp.pushback}</p>}
              {sp.assumptions && sp.assumptions.length > 0 && <p className="mt-2 max-w-prose text-xs text-dust">Assumed: {sp.assumptions.join(" ")}</p>}
            </div>
          )}
          <div className="divide-y divide-line/60">
            {passed.map((l) => <LoopRow key={l.id} loop={l} queue={passed} onChange={update} showDate={false} />)}
          </div>
          {req.status === "done" && passed.length === 0 && <p className="text-sm text-dust">Every take failed a check. Generate again, or loosen the request.</p>}
          {rejected.length > 0 && (
            <div className="text-xs text-dust">
              <button className="hover:text-paper" onClick={() => setShowRejected(!showRejected)}>{showRejected ? "Hide" : "Show"} {rejected.length} rejected take{rejected.length > 1 ? "s" : ""}</button>
              {showRejected && <ul className="mt-2 space-y-1">{rejected.map((l) => <li key={l.id} className="font-mono">take {l.candidate_index + 1}: {l.reject_reasons.join(", ")}</li>)}</ul>}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
