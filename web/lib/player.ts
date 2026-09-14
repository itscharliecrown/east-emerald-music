"use client";
import { useSyncExternalStore } from "react";
import { api, type Loop } from "./api";

// Global player: one queue, one AudioContext, gapless looping, seek, prev/next.
type State = {
  queue: Loop[]; index: number; playing: boolean; loop: boolean; position: number; duration: number; loading: boolean;
};
let state: State = { queue: [], index: -1, playing: false, loop: true, position: 0, duration: 0, loading: false };
const subs = new Set<() => void>();
const emit = () => subs.forEach((f) => f());
const set = (p: Partial<State>) => { state = { ...state, ...p }; emit(); };

let ctx: AudioContext | null = null;
const buffers = new Map<string, AudioBuffer>();
let src: AudioBufferSourceNode | null = null;
let startedAt = 0;   // ctx time when playback started
let offset = 0;      // seconds into the buffer at start
let raf = 0;

const audio = () => (ctx ??= new AudioContext({ sampleRate: 44100 }));
export const current = () => state.queue[state.index];

async function buffer(l: Loop) {
  if (buffers.has(l.id)) return buffers.get(l.id)!;
  set({ loading: true });
  try {
    const res = await fetch(api.audioUrl(l.id));
    const b = await audio().decodeAudioData(await res.arrayBuffer());
    buffers.set(l.id, b);
    return b;
  } finally { set({ loading: false }); }
}

function tick() {
  const b = current() && buffers.get(current().id);
  if (state.playing && b) {
    let pos = offset + (audio().currentTime - startedAt);
    if (state.loop) pos = pos % b.duration;
    else if (pos >= b.duration) { next(); return; }
    set({ position: pos, duration: b.duration });
  }
  raf = requestAnimationFrame(tick);
}

function stopSource() {
  if (src) { try { src.stop(); } catch { /* noop */ } src.disconnect(); src = null; }
}

async function start(from = 0) {
  const l = current(); if (!l) return;
  const c = audio(); if (c.state === "suspended") await c.resume();
  const b = await buffer(l);
  stopSource();
  src = c.createBufferSource(); src.buffer = b; src.loop = state.loop; src.connect(c.destination);
  offset = from % b.duration; startedAt = c.currentTime;
  src.start(0, offset);
  src.onended = () => { if (!state.loop && src) { /* handled in tick */ } };
  set({ playing: true, duration: b.duration, position: offset });
  cancelAnimationFrame(raf); raf = requestAnimationFrame(tick);
}

export const player = {
  subscribe(fn: () => void) { subs.add(fn); return () => { subs.delete(fn); }; },
  get: () => state,
  /** Play a loop; `queue` becomes the prev/next context. */
  play(l: Loop, queue?: Loop[]) {
    const q = queue ?? (state.queue.some((x) => x.id === l.id) ? state.queue : [l]);
    const i = q.findIndex((x) => x.id === l.id);
    const same = current()?.id === l.id;
    set({ queue: q, index: i });
    if (same && state.playing) return player.pause();
    if (same && !state.playing) return player.resume();
    return start(0);
  },
  pause() { if (!state.playing) return; offset = state.position; stopSource(); cancelAnimationFrame(raf); set({ playing: false }); },
  resume() { if (!current()) return; return start(state.position); },
  toggle() { return state.playing ? player.pause() : player.resume(); },
  seek(sec: number) { const b = current() && buffers.get(current().id); if (!b) return; if (state.playing) start(sec); else set({ position: Math.max(0, Math.min(sec, b.duration)) }); },
  setLoop(v: boolean) { set({ loop: v }); if (src) src.loop = v; },
  next() { return next(); },
  prev() { if (state.position > 2) return start(0); if (state.index > 0) { set({ index: state.index - 1 }); return start(0); } return start(0); },
  setQueue(q: Loop[]) { const cur = current(); const i = cur ? q.findIndex((x) => x.id === cur.id) : -1; set({ queue: q, index: i >= 0 ? i : state.index }); },
};

function next() {
  if (state.index < state.queue.length - 1) { set({ index: state.index + 1 }); return start(0); }
  player.pause();
}

export function usePlayer() {
  return useSyncExternalStore(player.subscribe, player.get, player.get);
}
