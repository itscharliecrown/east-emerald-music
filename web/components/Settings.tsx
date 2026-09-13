"use client";
import { useEffect, useState } from "react";
import { api, getConfig, setConfig } from "@/lib/api";

export function Settings() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    const c = getConfig(); setUrl(c.url); setToken(c.token);
    if (!c.url || !c.token) setOpen(true);
  }, []);

  const save = async () => {
    setConfig(url, token);
    try { const h = await api.health(); setStatus(`connected · ${h.loops} loops`); setOpen(false); }
    catch (e) { setStatus(`error: ${(e as Error).message}`); }
  };

  return (
    <div className="text-xs">
      <button className="opacity-60 hover:opacity-100" onClick={() => setOpen(!open)}>⚙ engine {status && `· ${status}`}</button>
      {open && (
        <div className="mt-2 flex flex-wrap gap-2 rounded border border-white/10 p-3">
          <input className="inp w-96" placeholder="https://…modal.run" value={url} onChange={(e) => setUrl(e.target.value)} />
          <input className="inp w-72" placeholder="ENGINE_API_TOKEN" type="password" value={token} onChange={(e) => setToken(e.target.value)} />
          <button className="btn" onClick={save}>save + test</button>
        </div>
      )}
    </div>
  );
}
