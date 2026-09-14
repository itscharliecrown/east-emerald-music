"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Player } from "./Player";
import { Settings } from "./Settings";

const NAV = [
  ["/", "Create"],
  ["/library/", "Library"],
  ["/history/", "History"],
] as const;

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
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
        <div className="mt-auto"><Settings /></div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-4 border-b border-line px-4 py-3 md:hidden">
          <Link href="/" className="serif text-xl">East Emerald</Link>
          <nav className="ml-auto flex gap-3 text-sm">{NAV.map(([h, l]) => <Link key={h} href={h} className="text-dust">{l}</Link>)}</nav>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-32 pt-8 md:px-10">{children}</main>
      </div>
      <Player />
    </div>
  );
}
