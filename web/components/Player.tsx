"use client";
import { api } from "@/lib/api";
import { mmss, loopTitle, signature, instrumentName } from "@/lib/format";
import { current, player, usePlayer } from "@/lib/player";
import { Waveform } from "./Waveform";

export function Player() {
  const s = usePlayer();
  const l = current();
  if (!l) return null;
  const pct = s.duration ? s.position / s.duration : 0;
  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-ink/95 backdrop-blur md:left-56">
      <div className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3 md:px-10">
        <div className="flex items-center gap-1">
          <button className="btn btn-ghost" aria-label="Previous" onClick={() => player.prev()}>⏮</button>
          <button className="btn btn-primary h-10 w-10 justify-center rounded-full text-base" aria-label={s.playing ? "Pause" : "Play"} onClick={() => player.toggle()}>{s.loading ? "…" : s.playing ? "❚❚" : "▶"}</button>
          <button className="btn btn-ghost" aria-label="Next" onClick={() => player.next()}>⏭</button>
          <button className={`btn btn-ghost ${s.loop ? "text-jade" : "text-dust"}`} aria-pressed={s.loop} title="Loop" onClick={() => player.setLoop(!s.loop)}>⟳</button>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-3">
            <span className="serif truncate text-lg">{loopTitle(l)}</span>
            <span className="sig text-lg">{signature(l)}</span>
            <span className="hidden truncate text-xs text-dust sm:inline">{instrumentName(l.instrument_type)} · {l.bars} bars · {l.genre}</span>
          </div>
          <div className="relative mt-1 h-10 cursor-pointer" onClick={(e) => { const r = e.currentTarget.getBoundingClientRect(); player.seek(((e.clientX - r.left) / r.width) * s.duration); }}>
            <Waveform peaks={l.peaks} bars={l.bars} active={s.playing} progress={pct} compact />
          </div>
          <div className="mt-0.5 flex justify-between text-[11px] text-dust"><span>{mmss(s.position)}</span><span>{mmss(s.duration)}</span></div>
        </div>
        <a className="btn" href={api.downloadUrl(l.id, "wav")} title={l.filename}>Download</a>
      </div>
    </div>
  );
}
