"use client";
import Link from "next/link";
import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { JobsTray } from "./JobsTray";
import { Player } from "./Player";
import { Settings } from "./Settings";
import { player } from "@/lib/player";

const NAV = [
  ["/", "Create"],
  ["/sessions/", "Sessions"],
  ["/library/", "Library"],
  ["/history/", "History"],
] as const;

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  useEffect(() => {
    // Space play/pause, ← → previous/next, L loop. Ignored while typing.
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
      if (e.code === "Space") { e.preventDefault(); player.toggle(); }
      else if (e.key === "ArrowRight") player.next();
      else if (e.key === "ArrowLeft") player.prev();
      else if (e.key.toLowerCase() === "l") player.setLoop(!player.get().loop);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-line px-4 py-6 md:flex">
        <Link href="/" className="serif text-2xl leading-none text-paper">East Emerald</Link>
        <div className="mt-1 text-xs text-dust">Sample engine</div>
        <nav className="mt-8 flex flex-col gap-1">
          {NAV.map(([href, label]) => {
            const on = href === "/" ? path === "/" : path.startsWith(href);
            return (
              <Link key={href} href={href} className={`rounded-md px-3 py-2 text-sm ${on ? "bg-felt text-paper" : "text-dust hover:text-paper"}`}>{label}</Link>
            );
          })}
        </nav>
        <div className="mt-auto space-y-3">
          <div className="text-[11px] leading-5 text-dust">Space play · ← → prev/next · L loop</div>
          <Settings />
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-4 border-b border-line px-4 py-3 md:hidden">
          <Link href="/" className="serif text-xl">East Emerald</Link>
          <nav className="ml-auto flex gap-3 text-sm">{NAV.map(([h, l]) => <Link key={h} href={h} className="text-dust">{l}</Link>)}</nav>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-32 pt-8 md:px-10"><div className="mb-6"><JobsTray /></div>{children}</main>
      </div>
      <Player />
    </div>
  );
}
