"use client";
import { useEffect, useState } from "react";
import { api, getConfig, setConfig } from "@/lib/api";

export function Settings() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [status, setStatus] = useState<"unknown" | "ok" | "error">("unknown");
  const [msg, setMsg] = useState("");

  const test = async () => {
    try { const h = await api.health(); setStatus("ok"); setMsg(`${h.loops} loops`); return true; }
    catch (e) { setStatus("error"); setMsg((e as Error).message.slice(0, 80)); return false; }
  };
  useEffect(() => {
    const c = getConfig(); setUrl(c.url); setToken(c.token);
    if (!c.url || !c.token) setOpen(true); else test();
  }, []);

  const save = async () => { setConfig(url, token); if (await test()) setOpen(false); };
  const dot = status === "ok" ? "bg-jade" : status === "error" ? "bg-ember" : "bg-dust";

  return (
    <div className="text-xs">
      <button className="flex items-center gap-2 text-dust hover:text-paper" onClick={() => setOpen(!open)}>
        <span className={`h-2 w-2 rounded-full ${dot}`} /> Engine {status === "ok" ? "connected" : status === "error" ? "unreachable" : ""}
      </button>
      {msg && status === "error" && <div className="mt-1 text-ember/80">{msg}</div>}
      {open && (
        <div className="mt-2 flex flex-col gap-2">
          <input className="inp" placeholder="Engine URL (…modal.run)" value={url} onChange={(e) => setUrl(e.target.value)} />
          <input className="inp" placeholder="Access token" type="password" value={token} onChange={(e) => setToken(e.target.value)} />
          <button className="btn" onClick={save}>Connect</button>
        </div>
      )}
    </div>
  );
}
