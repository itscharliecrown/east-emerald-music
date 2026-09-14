"use client";
import { useSyncExternalStore } from "react";
import { api, type RequestState } from "./api";

// Background requests started from anywhere (variation, companion, adjust). Polled here so the
// user can keep browsing; the Create page and the player pick results up when done.
export type Job = { id: string; label: string; state?: RequestState; done: boolean; error?: string; started: number };
let jobs: Job[] = [];
const subs = new Set<() => void>();
const emit = () => subs.forEach((f) => f());
const timers = new Map<string, number>();

export const jobsStore = {
  subscribe(fn: () => void) { subs.add(fn); return () => { subs.delete(fn); }; },
  get: () => jobs,
  track(id: string, label: string) {
    jobs = [{ id, label, done: false, started: Date.now() }, ...jobs].slice(0, 20); emit();
    const t = window.setInterval(async () => {
      try {
        const r = await api.request(id);
        const done = r.status === "done" || r.status === "failed";
        jobs = jobs.map((j) => (j.id === id ? { ...j, state: r, done, error: r.error ?? undefined } : j)); emit();
        if (done) { window.clearInterval(t); timers.delete(id); }
      } catch (e) {
        jobs = jobs.map((j) => (j.id === id ? { ...j, done: true, error: (e as Error).message } : j)); emit();
        window.clearInterval(t); timers.delete(id);
      }
    }, 1500);
    timers.set(id, t);
  },
  dismiss(id: string) { jobs = jobs.filter((j) => j.id !== id); emit(); },
};

export const useJobs = () => useSyncExternalStore(jobsStore.subscribe, jobsStore.get, jobsStore.get);
