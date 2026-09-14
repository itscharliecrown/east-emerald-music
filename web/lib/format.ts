import type { Loop } from "./api";

export const modeShort = (m: string) => (m === "major" ? "maj" : m === "minor" ? "min" : m);
export const signature = (l: { key_tonic: string; key_mode: string; bpm: number }) => `${l.key_tonic}${modeShort(l.key_mode)} ${Math.round(l.bpm)}`;

export const instrumentName = (t: string) =>
  ({ upright_piano: "Upright piano", felt_piano: "Felt piano", grand_piano: "Grand piano", rhodes: "Rhodes", wurlitzer: "Wurlitzer",
     nylon_guitar: "Nylon guitar", steel_acoustic_guitar: "Steel-string guitar", clean_electric_guitar: "Clean electric", jazz_archtop: "Jazz archtop" } as Record<string, string>)[t] ?? t.replace(/_/g, " ");

export function loopTitle(l: Loop) {
  const mood = l.moods?.[0];
  return `${mood ? mood[0].toUpperCase() + mood.slice(1) + " " : ""}${instrumentName(l.instrument_type).toLowerCase()}`;
}

export function when(iso: string) {
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 7 * 86400) return `${Math.floor(diff / 86400)} d ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: d.getFullYear() !== new Date().getFullYear() ? "numeric" : undefined });
}

export function fullDate(iso: string) {
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
