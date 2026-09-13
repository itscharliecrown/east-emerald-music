"use client";
import { useEffect, useRef } from "react";

export function Waveform({ peaks, bars, active }: { peaks?: number[]; bars: number; active?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const w = c.clientWidth, h = c.clientHeight;
    c.width = w * dpr; c.height = h * dpr;
    const g = c.getContext("2d")!; g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
    const p = peaks && peaks.length ? peaks : new Array(200).fill(0.05);
    const bw = w / p.length;
    g.fillStyle = active ? "#6ee7b7" : "#3f6b58";
    p.forEach((v, i) => { const bh = Math.max(1, v * h * 0.95); g.fillRect(i * bw, (h - bh) / 2, Math.max(1, bw - 0.5), bh); });
    g.strokeStyle = "rgba(255,255,255,0.18)";
    for (let b = 1; b < bars; b++) { const x = (w / bars) * b; g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke(); }
  }, [peaks, bars, active]);
  return <canvas ref={ref} className="h-14 w-full rounded bg-black/30" />;
}
