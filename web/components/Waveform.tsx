"use client";
import { useEffect, useRef } from "react";

export function Waveform({ peaks, bars, active, progress = 0, compact = false }: { peaks?: number[]; bars: number; active?: boolean; progress?: number; compact?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const w = c.clientWidth, h = c.clientHeight;
    c.width = w * dpr; c.height = h * dpr;
    const g = c.getContext("2d")!; g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
    const p = peaks && peaks.length ? peaks : new Array(160).fill(0.06);
    const bw = w / p.length;
    p.forEach((v, i) => {
      const played = i / p.length < progress;
      g.fillStyle = played ? "#c9a86a" : active ? "#4fb286" : "#3a4a42";
      const bh = Math.max(1, v * h * 0.9);
      g.fillRect(i * bw, (h - bh) / 2, Math.max(1, bw - 0.6), bh);
    });
    g.strokeStyle = "rgba(233,228,216,0.12)";
    for (let b = 1; b < bars; b++) { const x = (w / bars) * b; g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke(); }
  }, [peaks, bars, active, progress]);
  return <canvas ref={ref} className={`${compact ? "h-10" : "h-12"} w-full`} />;
}
