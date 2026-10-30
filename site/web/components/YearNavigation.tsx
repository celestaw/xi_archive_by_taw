"use client";

import { useEffect, useRef, useState } from "react";
import type { Meta } from "@/lib/api";

type Props = { meta: Meta | null; selected: string; onSelect: (year: string) => void };

export function YearNavigation({ meta, selected, onSelect }: Props) {
  const original = useRef<HTMLElement | null>(null);
  const floatingNav = useRef<HTMLElement | null>(null);
  const [floating, setFloating] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const cleanups: (() => void)[] = [];
    for (const nav of [original.current, floatingNav.current]) {
      if (!nav) continue;
      const onWheel = (event: WheelEvent) => {
        // Keep trackpad horizontal gestures, Shift+wheel, and browser zoom native.
        if (!media.matches || event.ctrlKey || event.shiftKey || !event.cancelable || Math.abs(event.deltaX) >= Math.abs(event.deltaY)) return;
        const unit = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? 16 : event.deltaMode === WheelEvent.DOM_DELTA_PAGE ? nav.clientWidth : 1;
        const next = Math.max(0, Math.min(nav.scrollWidth - nav.clientWidth, nav.scrollLeft + event.deltaY * unit));
        // At either end, let the wheel scroll the page again.
        if (Math.abs(next - nav.scrollLeft) < 1) return;
        event.preventDefault();
        nav.scrollTo({ left: next, behavior: "instant" });
      };
      nav.addEventListener("wheel", onWheel, { passive: false });
      cleanups.push(() => nav.removeEventListener("wheel", onWheel));
    }
    return () => { for (const cleanup of cleanups) cleanup(); };
  }, []);

  useEffect(() => {
    if (!original.current) return;
    const media = window.matchMedia("(max-width: 760px)");
    const observer = new IntersectionObserver(([entry]) => {
      setFloating(media.matches && !entry.isIntersecting && entry.boundingClientRect.bottom <= 0);
    });
    const refresh = () => {
      if (original.current) setFloating(media.matches && original.current.getBoundingClientRect().bottom <= 0);
    };
    observer.observe(original.current);
    media.addEventListener("change", refresh);
    return () => { observer.disconnect(); media.removeEventListener("change", refresh); };
  }, []);

  useEffect(() => {
    if (!window.matchMedia("(max-width: 760px)").matches) return;
    for (const nav of [original.current, floatingNav.current]) {
      const button = nav?.querySelector<HTMLButtonElement>('[aria-pressed="true"]');
      if (!nav || !button) continue;
      nav.scrollTo({ left: button.offsetLeft - (nav.clientWidth - button.offsetWidth) / 2, behavior: "instant" });
    }
  }, [floating, selected]);

  function buttons() {
    return <>
      <button aria-pressed={selected === ""} onClick={() => onSelect("")}>すべての年</button>
      {meta?.years.map(year => <button key={year} aria-pressed={selected === String(year)} onClick={() => onSelect(String(year))}>{year}<span aria-hidden="true">↗</span></button>)}
      <button aria-pressed={selected === "undated"} onClick={() => onSelect("undated")}>日付未確認 <span aria-hidden="true">—</span></button>
    </>;
  }

  return <>
    <aside className="year-index">
      <h1 id="index-title">作品年表</h1>
      <nav ref={original} className="year-links" aria-label="記録の年で絞り込む">{buttons()}</nav>
      {meta && <p className="index-footnote">{meta.total_entries}件の作品・別版・候補<br />日付未確認 {meta.undated_entries}件を含む<br /><span>調査確認日 {meta.checked_on.replaceAll("-", ".")}</span></p>}
    </aside>
    <div className={`floating-years${floating ? " is-visible" : ""}`} aria-hidden={!floating} inert={!floating}>
      <nav ref={floatingNav} className="year-links" aria-label="記録の年で絞り込む（追従バー）">{buttons()}</nav>
    </div>
  </>;
}
