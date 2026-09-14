"use client";

// Engine client. Base URL and token live in localStorage (single user, private tool).
const KEY_URL = "ee_api_url";
const KEY_TOKEN = "ee_api_token";

export function getConfig() {
  if (typeof window === "undefined") return { url: "", token: "" };
  return {
    url: localStorage.getItem(KEY_URL) || process.env.NEXT_PUBLIC_ENGINE_API_URL || "",
    token: localStorage.getItem(KEY_TOKEN) || "",
  };
}

export function setConfig(url: string, token: string) {
  localStorage.setItem(KEY_URL, url.replace(/\/$/, ""));
  localStorage.setItem(KEY_TOKEN, token);
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { url, token } = getConfig();
  if (!url) throw new Error("Engine URL not set");
  const res = await fetch(url + path, {
    ...init,
    headers: { "content-type": "application/json", authorization: `Bearer ${token}`, ...(init.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export type Loop = {
  id: string; request_id: string; candidate_index: number; status: "passed" | "rejected";
  reject_reasons: string[]; instrument_type: string; instrument_family: string; genre: string; moods: string[];
  key_tonic: string; key_mode: string; bpm: number; bars: number; time_signature: string; filename?: string;
  gen_prompt: string; seed: number; score: number; peaks?: number[]; kept?: number | null; stars?: number | null;
  favorite?: number; conform_ops?: Record<string, unknown>; analysis_raw?: Record<string, unknown>;
  analysis_final?: Record<string, unknown>; created_at: string; midi_path?: string | null; init_noise_level?: number | null;
};

export type RequestState = {
  id: string; status: string; error?: string; raw_text: string; llm_usage?: Record<string, unknown>;
  gpu_seconds?: number; batches_run?: number; loops: Loop[];
  voicings?: string[];
  spec?: { assumptions?: string[]; pushback?: string; generation_mode?: string; harmony?: { rationale?: string; complexity?: string; pattern?: string; progression?: { degree: string; quality: string; beats: number }[] }; key?: { tonic: string; mode: string }; bpm?: number; bars?: number; genre?: string; instrument?: { type: string } };
  warnings?: Record<string, string[]>;
};

export type RequestSummary = {
  id: string; created_at: string; status: string; raw_text: string; error?: string | null; passed_count: number; liked_count: number;
  summary?: { instrument?: string; key?: { tonic: string; mode: string }; bpm?: number; bars?: number; genre?: string; mode?: string };
};

export const api = {
  requests: () => call<{ requests: RequestSummary[] }>("/v1/requests?limit=100"),
  health: () => call<{ ok: boolean; loops: number }>("/v1/health"),
  wake: () => call("/v1/wake", { method: "POST" }),
  create: (body: { text: string; overrides: Record<string, unknown>; candidates?: number; parent_loop_id?: string }) =>
    call<{ request_id: string }>("/v1/requests", { method: "POST", body: JSON.stringify(body) }),
  request: (id: string) => call<RequestState>(`/v1/requests/${id}`),
  loops: (q: Record<string, string | number | boolean | undefined>) => {
    const p = new URLSearchParams();
    Object.entries(q).forEach(([k, v]) => v !== undefined && v !== "" && p.set(k, String(v)));
    return call<{ loops: Loop[] }>(`/v1/loops?${p}`);
  },
  patch: (id: string, body: Record<string, unknown>) => call<Loop>(`/v1/loops/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  audioUrl: (id: string) => { const { url, token } = getConfig(); return `${url}/v1/loops/${id}/audio?token=${encodeURIComponent(token)}`; },
  downloadUrl: (id: string, format = "wav") => { const { url, token } = getConfig(); return `${url}/v1/loops/${id}/download?format=${format}&token=${encodeURIComponent(token)}`; },
};

export const keyLabel = (l: { key_tonic: string; key_mode: string }) =>
  `${l.key_tonic}${l.key_mode === "major" ? "maj" : l.key_mode === "minor" ? "min" : l.key_mode}`;
