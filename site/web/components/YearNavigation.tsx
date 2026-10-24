"use client";

import { useEffect, useRef, useState } from "react";
import type { Meta } from "@/lib/api";

type Props = { meta: Meta | null; selected: string; onSelect: (year: string) => void };

export function YearNavigation({ meta, selected, onSelect }: Props) {
  const dialog = useRef<HTMLDialogElement | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [open, setOpen] = useState(false);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    if (!open) return;
    const previous = document.documentElement.style.overflow;
    document.documentElement.style.overflow = "hidden";
    return () => { document.documentElement.style.overflow = previous; };
  }, [open]);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const closeOnDesktop = () => {
      if (media.matches) return;
      if (timer.current) clearTimeout(timer.current);
      dialog.current?.close();
    };
    media.addEventListener("change", closeOnDesktop);
    return () => { media.removeEventListener("change", closeOnDesktop); if (timer.current) clearTimeout(timer.current); };
  }, []);

  function showDrawer() {
    if (!dialog.current || dialog.current.open) return;
    setClosing(false);
    dialog.current.showModal();
    setOpen(true);
    dialog.current.querySelector<HTMLButtonElement>('[aria-pressed="true"]')?.focus();
  }

  function closeDrawer(year?: string) {
    if (timer.current) clearTimeout(timer.current);
    const finish = () => {
      dialog.current?.close();
      if (year !== undefined) onSelect(year);
    };
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) finish();
    else { setClosing(true); timer.current = setTimeout(finish, 180); }
  }

  function buttons(inDrawer = false) {
    const choose = (year: string) => inDrawer ? closeDrawer(year) : onSelect(year);
    return <>
      <button aria-pressed={selected === ""} onClick={() => choose("")}>すべての年</button>
      {meta?.years.map(year => <button key={year} aria-pressed={selected === String(year)} onClick={() => choose(String(year))}>{year}<span aria-hidden="true">↗</span></button>)}
      <button aria-pressed={selected === "undated"} onClick={() => choose("undated")}>日付未確認 <span aria-hidden="true">—</span></button>
    </>;
  }

  return <aside className="year-index">
    <div className="year-toolbar">
      <h1 id="index-title">作品年表</h1>
      <button className="year-menu-toggle" aria-haspopup="dialog" aria-expanded={open} aria-controls="year-drawer" onClick={showDrawer}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
        年を選ぶ<span>{selected === "undated" ? "日付未確認" : selected || "すべて"}</span>
      </button>
    </div>
    <nav className="year-links desktop-year-links" aria-label="記録の年で絞り込む">{buttons()}</nav>
    {meta && <p className="index-footnote">{meta.total_entries}件の作品・別版・候補<br />日付未確認 {meta.undated_entries}件を含む<br /><span>調査確認日 {meta.checked_on.replaceAll("-", ".")}</span></p>}
    <dialog ref={dialog} id="year-drawer" className={`year-drawer${closing ? " is-closing" : ""}`} aria-labelledby="year-drawer-title"
      onCancel={event => { event.preventDefault(); closeDrawer(); }}
      onClose={() => { setOpen(false); setClosing(false); }}
      onClick={event => {
        if (event.target !== event.currentTarget) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeDrawer();
      }}>
      <div className="year-drawer-heading">
        <h2 id="year-drawer-title">年を選ぶ</h2>
        <button aria-label="年の選択を閉じる" onClick={() => closeDrawer()}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg></button>
      </div>
      <nav className="year-links" aria-label="記録の年で絞り込む（パネル）">{buttons(true)}</nav>
    </dialog>
  </aside>;
}
