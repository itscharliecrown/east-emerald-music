"use client";

// Gapless looper. <audio loop> leaves audible gaps; AudioBufferSourceNode does not.
let ctx: AudioContext | null = null;
const cache = new Map<string, AudioBuffer>();
let current: { id: string; src: AudioBufferSourceNode; click?: number } | null = null;
const listeners = new Set<(id: string | null) => void>();

function context() {
  if (!ctx) ctx = new AudioContext({ sampleRate: 44100 });
  return ctx;
}

export function onPlayingChange(fn: (id: string | null) => void) {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}
const emit = () => listeners.forEach((f) => f(current?.id ?? null));

export async function load(id: string, url: string) {
  if (cache.has(id)) return cache.get(id)!;
  const res = await fetch(url);
  const buf = await context().decodeAudioData(await res.arrayBuffer());
  cache.set(id, buf);
  return buf;
}

export function stop() {
  if (current) {
    try { current.src.stop(); } catch { /* already stopped */ }
    if (current.click) window.clearInterval(current.click);
    current = null;
    emit();
  }
}

export async function play(id: string, url: string, opts: { bpm?: number; click?: boolean } = {}) {
  const c = context();
  if (c.state === "suspended") await c.resume();
  if (current?.id === id) { stop(); return; }
  stop();
  const buf = await load(id, url);
  const src = c.createBufferSource();
  src.buffer = buf;
  src.loop = true;
  src.connect(c.destination);
  const start = c.currentTime + 0.05;
  src.start(start);
  current = { id, src };
  if (opts.click && opts.bpm) {
    const beat = 60 / opts.bpm;
    let n = 0;
    const schedule = () => {
      // schedule clicks a bar ahead, phase-locked to the loop start
      while (start + n * beat < c.currentTime + 1.0) {
        const t = start + n * beat;
        const osc = c.createOscillator(); const g = c.createGain();
        osc.frequency.value = n % 4 === 0 ? 1600 : 1000;
        g.gain.setValueAtTime(0.25, t); g.gain.exponentialRampToValueAtTime(0.001, t + 0.04);
        osc.connect(g).connect(c.destination); osc.start(t); osc.stop(t + 0.05);
        n++;
      }
    };
    schedule();
    current.click = window.setInterval(schedule, 250);
  }
  emit();
}

export const playingId = () => current?.id ?? null;
