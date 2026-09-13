import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const sans = Geist({ variable: "--font-sans", subsets: ["latin"] });
const mono = Geist_Mono({ variable: "--font-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "East Emerald Sample Engine",
  description: "Loops and stems on demand. Song starters, never songs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[#0b0f0d] text-[#e6ebe8]">
        <header className="border-b border-white/10">
          <nav className="mx-auto flex max-w-6xl items-center gap-6 px-5 py-3 text-sm">
            <Link href="/" className="font-semibold tracking-tight text-emerald-300">East Emerald</Link>
            <Link href="/" className="opacity-80 hover:opacity-100">Create</Link>
            <Link href="/library/" className="opacity-80 hover:opacity-100">Library</Link>
            <span className="ml-auto font-mono text-xs opacity-50">sample engine · v0.1</span>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-5 py-6">{children}</main>
      </body>
    </html>
  );
}
