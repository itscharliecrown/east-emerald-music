"use client";
import { LoopRow } from "./LoopRow";
import { jobsStore, useJobs } from "@/lib/jobs";

const STEPS: Record<string, string> = { queued: "Waking the engine", parsing: "Reading the brief", composing: "Writing the harmony", generating: "Recording takes", conforming: "Tuning, cutting, leveling" };

export function JobsTray() {
  const jobs = useJobs();
  if (!jobs.length) return null;
  return (
    <section className="space-y-3">
      {jobs.map((j) => {
        const passed = j.state?.loops.filter((l) => l.status === "passed") ?? [];
        return (
          <div key={j.id} className="rounded-xl border border-line p-3">
            <div className="flex items-center gap-3 text-sm">
              {!j.done && <span className="h-2 w-2 animate-pulse rounded-full bg-jade" />}
              <span className="serif">{j.label}</span>
              <span className="text-xs text-dust">{j.done ? (j.error ? "failed" : `${passed.length} take${passed.length === 1 ? "" : "s"}`) : `${STEPS[j.state?.status ?? "queued"] ?? j.state?.status}…`}</span>
              <button className="ml-auto text-xs text-dust hover:text-paper" onClick={() => jobsStore.dismiss(j.id)}>dismiss</button>
            </div>
            {j.error && <p className="mt-1 text-xs text-ember">{j.error}</p>}
            {passed.length > 0 && <div className="mt-2 divide-y divide-line/60">{passed.map((l) => <LoopRow key={l.id} loop={l} queue={passed} showDate={false} />)}</div>}
          </div>
        );
      })}
    </section>
  );
}
