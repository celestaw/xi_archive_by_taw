"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type FocusEvent, type PointerEvent } from "react";
import { api, formatDate } from "@/lib/api";
import { useResource } from "@/lib/useResource";
import { CopyButton } from "./CopyButton";
import { dateRange, layoutTimeline, PLOT_PADDING, ROW_HEIGHT, type Stage, type TimelinePoint } from "@/lib/timeline-layout";

const loadTimeline = (signal: AbortSignal) => api.timeline(signal);
const labels: Record<Stage, string> = { preview: "プレビュー", release: "本公開", reference: "公開形態未確認" };
const normalize = (value: string) => value.normalize("NFKC").toLocaleLowerCase("ja");

export function TimelineExplorer() {
  const { data, pending, error, retry } = useResource(loadTimeline);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(normalize(query.trim()));
  const [filter, setFilter] = useState("all");
  const [scale, setScale] = useState("standard");
  const [viewportWidth, setViewportWidth] = useState(1000);
  const [active, setActive] = useState<TimelinePoint | null>(null);
  const [position, setPosition] = useState({ left: 16, top: 16 });
  const scroller = useRef<HTMLDivElement>(null);
  const popup = useRef<HTMLDivElement>(null);
  const anchor = useRef<DOMRect | null>(null);
  const activeButton = useRef<HTMLButtonElement | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const entries = useMemo(() => (data?.items ?? []).filter(entry => {
    if (deferredQuery && !normalize([entry.title, ...entry.aliases.map(alias => alias.title)].join(" ")).includes(deferredQuery)) return false;
    return filter === "all" || filter === "preview" && !!entry.preview || filter === "pair" && entry.connect_preview;
  }), [data, deferredQuery, filter]);
  const dated = entries.filter(entry => entry.preview || entry.release || entry.reference);
  const undated = entries.filter(entry => !entry.preview && !entry.release && !entry.reference);
  const labelWidth = viewportWidth < 600 ? 160 : 240;
  const yearWidth = scale === "month" ? 2400 : scale === "year" ? 1200 : 600;
  const layout = useMemo(() => layoutTimeline(entries, yearWidth, labelWidth), [entries, yearWidth, labelWidth]);

  useEffect(() => {
    const element = scroller.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setViewportWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, [pending, error, layout.points.length > 0]);

  useEffect(() => {
    setActive(null);
    const firstEntryId = layout.rows[0]?.entry.id;
    const firstX = Math.min(...layout.points.filter(point => point.entry.id === firstEntryId).map(point => point.x));
    scroller.current?.scrollTo({ left: Number.isFinite(firstX) ? Math.max(0, firstX - labelWidth - PLOT_PADDING - 60) : 0, top: 0, behavior: "instant" });
  }, [deferredQuery, filter, scale, labelWidth, pending]);

  useEffect(() => () => { if (closeTimer.current) clearTimeout(closeTimer.current); }, []);

  useEffect(() => {
    if (!active) return;
    const dismiss = (event: globalThis.PointerEvent) => {
      if (!popup.current?.contains(event.target as Node) && !activeButton.current?.contains(event.target as Node)) setActive(null);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") { activeButton.current?.focus({ preventScroll: true }); setActive(null); }
    };
    const onScroll = (event: Event) => {
      if (popup.current?.contains(event.target as Node) || !activeButton.current) return;
      anchor.current = activeButton.current.getBoundingClientRect();
      const viewport = scroller.current?.getBoundingClientRect();
      const rect = anchor.current;
      if (rect.bottom < Math.max(0, viewport?.top ?? 0) || rect.top > Math.min(window.innerHeight, viewport?.bottom ?? window.innerHeight) || rect.right < (viewport?.left ?? 0) || rect.left > (viewport?.right ?? window.innerWidth)) setActive(null);
      else positionPopup();
    };
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", close);
    function close() { setActive(null); }
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", close);
    };
  }, [active]);

  useLayoutEffect(() => { if (active) positionPopup(); }, [active]);

  function positionPopup() {
    if (!anchor.current || !popup.current) return;
    const rect = anchor.current;
    const width = popup.current.offsetWidth;
    const height = popup.current.offsetHeight;
    const left = Math.max(16, Math.min(rect.left + rect.width / 2 - width / 2, window.innerWidth - width - 16));
    const below = rect.bottom + 8;
    const top = below + height <= window.innerHeight - 16 ? below : Math.max(16, rect.top - height - 8);
    setPosition({ left, top });
  }

  function keepOpen() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = null;
  }

  function scheduleClose() {
    keepOpen();
    if (popup.current?.contains(document.activeElement)) return;
    closeTimer.current = setTimeout(() => setActive(null), 180);
  }

  function show(point: TimelinePoint, element: HTMLButtonElement) {
    keepOpen();
    anchor.current = element.getBoundingClientRect();
    activeButton.current = element;
    setActive(point);
  }

  function leavePoint(event: PointerEvent<HTMLButtonElement>) {
    if (event.pointerType === "mouse" && document.activeElement !== event.currentTarget) scheduleClose();
  }

  function blurPoint(event: FocusEvent<HTMLButtonElement>) {
    if (!popup.current?.contains(event.relatedTarget as Node)) scheduleClose();
  }

  const firstYear = layout.years[0];

  function jumpToYear(value: string) {
    if (!value) return;
    const year = Number(value);
    const row = layout.rows.find(item => Number(item.firstRecord.date!.slice(0, 4)) >= year) ?? layout.rows.at(-1);
    const firstX = Math.min(...layout.points.filter(point => point.entry.id === row?.entry.id).map(point => point.x));
    setActive(null);
    scroller.current?.scrollTo({ left: Math.max((year - firstYear) * yearWidth, Number.isFinite(firstX) ? firstX - labelWidth - PLOT_PADDING - 60 : 0), top: row ? row.y - ROW_HEIGHT / 2 : 0, behavior: "instant" });
  }

  return <section className="timeline-explorer" aria-labelledby="timeline-title">
    <div className="timeline-heading"><h1 id="timeline-title">グラフ年表</h1><Link className="text-link" href="/#chronology">文字の年表を見る ↗</Link></div>
    <p className="timeline-intro">世に出た日付の古い順に、1行に1曲ずつ。</p>
    <ul className="timeline-legend" aria-label="グラフの凡例">
      <li><span className="timeline-symbol is-preview" aria-hidden="true" />プレビュー</li>
      <li><span className="timeline-symbol is-release" aria-hidden="true" />本公開</li>
      <li><span className="timeline-dash" aria-hidden="true" />本公開までの期間</li>
      <li><span className="timeline-symbol is-reference" aria-hidden="true" />公開形態未確認</li>
    </ul>
    <div className="timeline-controls">
      <div className="search-form timeline-search"><span className="search-icon" aria-hidden="true" /><label htmlFor="timeline-search" className="sr-only">グラフの曲名・別名で検索</label><input id="timeline-search" type="search" placeholder="曲名・別名で探す" value={query} maxLength={120} onChange={event => setQuery(event.target.value)} /></div>
      <label>表示する作品<select value={filter} onChange={event => setFilter(event.target.value)}><option value="all">すべて</option><option value="preview">プレビューの記録あり</option><option value="pair">プレビューと本公開のペア</option></select></label>
      <label>横軸の縮尺<select value={scale} onChange={event => setScale(event.target.value)}><option value="standard">標準（横に広く表示）</option><option value="year">さらに拡大</option><option value="month">月を大きく表示</option></select></label>
      <label>年へ移動<select value="" onChange={event => jumpToYear(event.target.value)} disabled={!layout.years.length}><option value="">年を選ぶ</option>{layout.years.map(year => <option key={year} value={year}>{year}年</option>)}</select></label>
    </div>
    <div className="timeline-status" role="status" aria-live="polite"><span>{pending ? "公開記録を読み込み中…" : error ? "記録を取得できませんでした" : `${dated.length}件をグラフに表示${undated.length ? ` · 日付未確認 ${undated.length}件` : ""}`}</span>{layout.years.length > 0 && <span>{firstYear}–{layout.years.at(-1)}</span>}</div>
    {pending && <p className="loading-copy" aria-busy="true">プレビューと本公開の記録を読み込んでいます…</p>}
    {!pending && error && <div className="empty-state" role="alert"><h2>グラフを読み込めませんでした。</h2><p>{error}</p><button className="text-link" onClick={retry}>もう一度読み込む ↗</button></div>}
    {!pending && !error && <>
      {layout.points.length > 0 ? <>
        <p id="timeline-help" className="timeline-help">上から古い順に1曲ずつ配置しています。横にスクロールして日付をたどれます。「年へ移動」でその年の曲と目盛りへ移動します。点にマウスを重ねると公開記録を表示します。</p>
        <div ref={scroller} className="timeline-scroll" role="region" aria-label="楽曲の公開時期のグラフ" aria-describedby="timeline-help timeline-date-note" tabIndex={0}>
          <div className="timeline-canvas" style={{ width: layout.width, "--timeline-label-width": `${labelWidth}px` } as CSSProperties}>
            <div className="timeline-axis" style={{ height: 66 }} aria-hidden="true"><div className="timeline-axis-label">楽曲 / 最も早い公開記録</div>{layout.years.map(year => <div className="timeline-year-tick" key={year} style={{ left: labelWidth + PLOT_PADDING + (year - firstYear) * yearWidth, width: yearWidth }}><span>{year}</span><div className="timeline-months">{Array.from({ length: 12 }, (_, index) => <span key={index}>{index + 1}月</span>)}</div></div>)}</div>
            <div className="timeline-plot" style={{ height: layout.height }}>
              {layout.rows.map(row => <div key={row.entry.id} className={`timeline-track${active?.entry.id === row.entry.id ? " is-active" : ""}`} style={{ height: ROW_HEIGHT }}><div className="timeline-row-label"><Link className="timeline-title-link" href={`/works/${row.entry.id}`} prefetch={false} title={row.entry.title}><strong>{row.entry.title}</strong><time dateTime={row.firstRecord.date ?? undefined}>{formatDate(row.firstRecord)}</time></Link><CopyButton text={row.entry.title} /></div></div>)}
              {layout.years.map(year => <div className="timeline-gridline" aria-hidden="true" key={year} style={{ left: labelWidth + PLOT_PADDING + (year - firstYear) * yearWidth }} />)}
              <svg className="timeline-connections" width={layout.width} height={layout.height} aria-hidden="true">
                {layout.connections.map(line => <line key={line.entryId} x1={line.start.x} y1={line.start.y} x2={line.end.x} y2={line.end.y} className={active?.entry.id === line.entryId ? "is-active" : ""} />)}
                {layout.points.filter(point => point.record.precision !== "day").map(point => {
                  const [start, end] = dateRange(point.record);
                  return <line key={`${point.entry.id}-${point.stage}`} className="timeline-precision-range" x1={labelWidth + PLOT_PADDING + (start - firstYear) * yearWidth} x2={labelWidth + PLOT_PADDING + (end - firstYear) * yearWidth} y1={point.y} y2={point.y} />;
                })}
              </svg>
              {layout.points.map((point, index) => <button key={`${point.entry.id}-${point.stage}`} className={`timeline-point is-${point.stage}${active?.entry.id === point.entry.id ? " is-active" : ""}`} style={{ left: point.x, top: point.y, width: point.hitWidth }} aria-label={`${point.entry.title} · ${labels[point.stage]} · ${formatDate(point.record)}`} aria-haspopup="dialog" aria-expanded={active === point} aria-controls={active === point ? "timeline-popup" : undefined} onPointerEnter={event => { if (event.pointerType === "mouse") show(point, event.currentTarget); }} onPointerLeave={leavePoint} onFocus={event => show(point, event.currentTarget)} onBlur={blurPoint} onClick={event => {
                show(point, event.currentTarget);
                if (event.detail === 0) requestAnimationFrame(() => popup.current?.querySelector<HTMLAnchorElement>("a")?.focus({ preventScroll: true }));
              }} onKeyDown={event => {
                const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 0;
                if (!step) return;
                event.preventDefault();
                const buttons = scroller.current?.querySelectorAll<HTMLButtonElement>(".timeline-point");
                buttons?.[(index + step + layout.points.length) % layout.points.length]?.focus();
              }}><span className="timeline-symbol" aria-hidden="true" /></button>)}
            </div>
          </div>
        </div>
        <p id="timeline-date-note" className="timeline-date-note">プレビューを含む最も早い公開記録で並べています。同じ日付は作品ID順です。点線は、確認できたプレビューから本公開までの期間です。本公開の点は真の初公開日とは限りません。年・月のみの記録は、その範囲を細い帯で示します。</p>
      </> : <div className="empty-state"><h2>{undated.length ? "該当する作品は日付が未確認です。" : "該当する記録がありません。"}</h2><p>{undated.length ? "公開時期を確認できた作品からグラフに表示します。" : "曲名の一部で探すか、表示する作品を変えてみてください。"}</p>{(query || filter !== "all") && <button className="text-link" onClick={() => { setQuery(""); setFilter("all"); }}>条件をクリア</button>}</div>}
      {undated.length > 0 && <details className="timeline-undated"><summary>日付未確認の作品 {undated.length}件</summary><p>日付を推測してグラフに配置せず、作品の記録へのリンクを掲載しています。</p><ul>{undated.map(entry => <li key={entry.id}><div className="title-with-copy"><Link href={`/works/${entry.id}`} prefetch={false}>{entry.title}<span>{entry.id}</span></Link><CopyButton text={entry.title} /></div></li>)}</ul></details>}
      {data && <p className="timeline-checked">調査確認日 {data.checked_on.replaceAll("-", ".")}</p>}
    </>}
    {active && <div ref={popup} id="timeline-popup" className="timeline-popup" role="dialog" aria-label={`${active.entry.title}の公開記録`} style={position} onPointerEnter={keepOpen} onPointerLeave={scheduleClose} onFocus={keepOpen} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget as Node)) scheduleClose(); }}>
      <div className="timeline-popup-heading"><h2>{active.entry.title}</h2><CopyButton text={active.entry.title} /><button aria-label="ポップアップを閉じる" onClick={() => { activeButton.current?.focus({ preventScroll: true }); setActive(null); }}>×</button></div>
      {(active.entry.is_variant || active.entry.attribution === "unverified") && <p className="timeline-popup-flags">{active.entry.is_variant && <span>別バージョン</span>}{active.entry.attribution === "unverified" && <span>帰属未確認</span>}</p>}
      <dl>{(["preview", "release", "reference"] as Stage[]).map(stage => {
        const record = active.entry[stage];
        return record ? <div key={stage} className={stage === active.stage ? "is-selected" : ""}><dt><span className={`timeline-symbol is-${stage}`} aria-hidden="true" />{labels[stage]}</dt><dd><time dateTime={record.date ?? undefined}>{formatDate(record)}</time>{record.precision !== "day" && <span>（{record.precision === "year" ? "月日" : "日"}未確認）</span>}</dd></div> : stage === "release" && active.entry.preview ? <div key={stage}><dt>本公開</dt><dd>時期未確認</dd></div> : null;
      })}</dl>
      <p className="timeline-popup-record">{active.record.medium}<br />{active.record.kind}</p>
      <div className="timeline-popup-links"><Link href={`/works/${active.entry.id}`}>作品の記録 ↗</Link><a href={active.record.source_url} target="_blank" rel="noreferrer">この点の出典 ↗</a></div>
    </div>}
  </section>;
}
