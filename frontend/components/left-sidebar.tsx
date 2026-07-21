"use client";

import Link from "next/link";
import { ReactNode, useState } from "react";

type LeftSidebarProps = {
  active: "learn" | "sessions" | "parent";
  onLearn?: () => void;
  onSessions?: () => void;
  onParent?: () => void;
  children?: ReactNode;
};

const itemClass = "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors";

function SidebarIcon({ type }: { type: "learn" | "sessions" | "parent" }) {
  const svgClass = "h-4 w-4 fill-none stroke-current";
  return <span aria-hidden="true" className="grid h-6 w-6 shrink-0 place-items-center rounded-md border border-current/50">
    {type === "learn" && <svg viewBox="0 0 20 20" className={svgClass} strokeWidth="1.7"><path d="M3.5 4.5A2.5 2.5 0 0 1 6 2h8v14H6a2.5 2.5 0 0 0-2.5 2.5v-14Z" strokeLinejoin="round" /><path d="M3.5 15.5A2.5 2.5 0 0 1 6 13h8" /></svg>}
    {type === "sessions" && <svg viewBox="0 0 20 20" className={svgClass} strokeWidth="1.7"><circle cx="10" cy="10" r="6.5" /><path d="M10 6.5V10l2.6 1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>}
    {type === "parent" && <svg viewBox="0 0 20 20" className={svgClass} strokeWidth="1.7"><circle cx="10" cy="6.5" r="2.5" /><path d="M4.5 17c.5-3 2.3-4.5 5.5-4.5s5 1.5 5.5 4.5" strokeLinecap="round" /><path d="M4 8.5a2 2 0 0 0-1.5 2M16 8.5a2 2 0 0 1 1.5 2" strokeLinecap="round" /></svg>}
  </span>;
}

export function LeftSidebar({ active, onLearn, onSessions, onParent, children }: LeftSidebarProps) {
  const [open, setOpen] = useState(true);
  const activeClass = "bg-white/10 text-[var(--text-inverse)]";
  const inactiveClass = "text-[#d4dcdf] hover:bg-white/10 hover:text-white";
  const learnControl = onLearn ? (
    <button onClick={onLearn} aria-current={active === "learn" ? "page" : undefined} className={`${itemClass} ${active === "learn" ? activeClass : inactiveClass}`}>
      <SidebarIcon type="learn" />
      <span className={open ? "" : "sr-only"}>Learn</span>
    </button>
  ) : (
    <Link href="/?continue=1" aria-current={active === "learn" ? "page" : undefined} className={`${itemClass} ${active === "learn" ? activeClass : inactiveClass}`}>
      <SidebarIcon type="learn" />
      <span className={open ? "" : "sr-only"}>Learn</span>
    </Link>
  );
  const sessionsControl = onSessions ? (
    <button onClick={onSessions} aria-current={active === "sessions" ? "page" : undefined} className={`${itemClass} ${active === "sessions" ? activeClass : inactiveClass}`}>
      <SidebarIcon type="sessions" />
      <span className={open ? "" : "sr-only"}>Sessions</span>
    </button>
  ) : (
    <Link href="/sessions" aria-current={active === "sessions" ? "page" : undefined} className={`${itemClass} ${active === "sessions" ? activeClass : inactiveClass}`}>
      <SidebarIcon type="sessions" />
      <span className={open ? "" : "sr-only"}>Sessions</span>
    </Link>
  );
  const parentControl = onParent ? (
    <button onClick={onParent} aria-current={active === "parent" ? "page" : undefined} className={`${itemClass} ${active === "parent" ? activeClass : inactiveClass}`}>
      <SidebarIcon type="parent" />
      <span className={open ? "" : "sr-only"}>Parent</span>
    </button>
  ) : (
    <Link href="/parent" aria-current={active === "parent" ? "page" : undefined} className={`${itemClass} ${active === "parent" ? activeClass : inactiveClass}`}>
      <SidebarIcon type="parent" />
      <span className={open ? "" : "sr-only"}>Parent</span>
    </Link>
  );

  return (
    <aside className={`fixed inset-y-0 left-0 z-30 hidden border-r border-white/10 bg-[var(--bg-primary)] shadow-[8px_0_28px_rgba(28,43,58,.18)] lg:flex ${open ? "w-[286px]" : "w-[60px]"} flex-col overflow-hidden transition-[width] duration-300 ease-out`} aria-label="Learning navigation">
      <div className="flex h-[78px] items-center justify-between border-b border-white/10 px-3">
        <div className={`min-w-0 transition-opacity duration-200 ${open ? "opacity-100" : "sr-only"}`}><p className="tutor-display text-2xl font-semibold text-[var(--text-inverse)]">Mypedia</p><p className="mt-0.5 text-[10px] font-semibold uppercase tracking-[.14em] text-[#b7c1c6]">Learning space</p></div>
        <button onClick={() => setOpen((value) => !value)} aria-label={open ? "Collapse sidebar" : "Expand sidebar"} aria-expanded={open} className="ml-auto grid h-8 w-8 place-items-center rounded-lg border border-white/25 bg-white/5 text-sm text-white transition hover:bg-white/15">
          <span aria-hidden="true">{open ? "‹" : "›"}</span>
        </button>
      </div>
      <nav className="space-y-1 p-2" aria-label="Primary navigation">
        {learnControl}
        {sessionsControl}
        {parentControl}
      </nav>
      {children && <div className={`min-h-0 flex-1 overflow-y-auto border-t border-[var(--border)] px-5 py-6 transition-opacity duration-200 ${open ? "opacity-100" : "pointer-events-none opacity-0"}`}>{children}</div>}
    </aside>
  );
}
