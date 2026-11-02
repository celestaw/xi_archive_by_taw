"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useLayoutEffect, useMemo, useRef, useState, type FocusEvent, type PointerEvent } from "react";
import { api, formatDate } from "@/lib/api";
import { useResource } from "@/lib/useResource";
import { CopyButton } from "./CopyButton";
import { layoutTimeline, PLOT_PADDING, ROW_HEIGHT, type TimelineRow } from "@/lib/timeline-layout";

const loadTimeline = (signal: AbortSignal) => api.timeline(signal);
const normalize = (value: string) => value.normalize("NFKC").toLocaleLowerCase("ja");
const accessLabel = (entry: TimelineRow["entry"]) => entry.audio_access === "official" ? "公式音源・アルバムあり" : entry.audio_access === "unofficial" ? "非公式投稿で聴取可能（リンク非掲載）" : "音源未確認";

export function TimelineExplorer() {
  const { data, pending, error, retry } = useResource(loadTimeline);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(normalize(query.trim()));
  const [filter, setFilter] = useState("all");
  const [scale, setScale] = useState("overview");
  const [rowHeight, setRowHeight] = useState(ROW_HEIGHT);
  const [viewportWidth, setViewportWidth] = useState(1100);
  const [active, setActive] = useState<TimelineRow | null>(null);
  const [position, setPosition] = useState({ left: 16, top: 16, width: 320 });
  const [anchor, setAnchor] = useState<{ rect: DOMRect; pointer: boolean } | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const popup = useRef<HTMLDivElement>(null);
  const activeLink = useRef<HTMLAnchorElement | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const entries = useMemo(() => (data?.items ?? []).filter(entry => {
    if (deferredQuery && !normalize([entry.title, ...entry.aliases.map(alias => alias.title)].join(" ")).includes(deferredQuery)) return false;
    const canListen = entry.audio_status === "available";
    return filter === "all" || filter === "preview" && !!entry.preview || filter === "available" && canListen || filter === "official" && entry.audio_access === "official" || filter === "unofficial" && entry.audio_access === "unofficial" || filter === "unverified" && !canListen;
  }), [data, deferredQuery, filter]);
  const years = entries.flatMap(entry => [entry.preview, entry.release, entry.reference].flatMap(record => record?.date ? [Number(record.date.slice(0, 4))] : []));
  const span = years.length && data ? Math.max(1, Number(data.as_of.slice(0, 4)) - Math.min(...years) + 1) : 1;
  const yearWidth = scale === "overview" ? Math.max(8, (viewportWidth - PLOT_PADDING * 2) / span) : scale === "month" ? 2400 : scale === "year" ? 1200 : 600;
  const layout = useMemo(() => layoutTimeline(entries, yearWidth, data?.as_of ?? "", rowHeight), [entries, yearWidth, data?.as_of, rowHeight]);
  const undated = entries.filter(entry => !entry.preview && !entry.release && !entry.reference);
  const firstYear = layout.years[0];

  useEffect(() => {
    const element = scroller.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setViewportWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, [pending, error, layout.rows.length > 0]);

  useEffect(() => {
    setActive(null);
    const firstX = layout.rows[0]?.startX ?? 0;
    scroller.current?.scrollTo({ left: scale === "overview" ? 0 : Math.max(0, firstX - PLOT_PADDING - 60), top: 0, behavior: "instant" });
  }, [deferredQuery, filter, scale, rowHeight, pending]);

  useEffect(() => () => { if (closeTimer.current) clearTimeout(closeTimer.current); }, []);

  useEffect(() => {
    if (!active) return;
    const dismiss = (event: globalThis.PointerEvent) => {
      if (!popup.current?.contains(event.target as Node) && !activeLink.current?.contains(event.target as Node)) setActive(null);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") { activeLink.current?.focus({ preventScroll: true }); setActive(null); }
    };
    const onScroll = (event: Event) => {
      if (popup.current?.contains(event.target as Node)) return;
      const element = activeLink.current;
      if (element && document.activeElement === element) {
        const rect = element.getBoundingClientRect();
        const viewport = scroller.current?.getBoundingClientRect();
        const center = Math.max(viewport?.left ?? 16, Math.min((rect.left + rect.right) / 2, viewport?.right ?? window.innerWidth - 16));
        setAnchor({ rect: new DOMRect(center, rect.top, 0, rect.height), pointer: false });
      } else setActive(null);
    };
    const close = () => setActive(null);
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", close);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", close);
    };
  }, [active]);

  useLayoutEffect(() => {
    if (!active || !anchor || !popup.current) return;
    const { rect, pointer } = anchor;
    const margin = 16;
    const gap = 16;
    const preferredWidth = Math.max(1, Math.min(320, window.innerWidth - margin * 2));
    const rightSpace = Math.max(0, window.innerWidth - rect.left - gap - margin);
    const leftSpace = Math.max(0, rect.left - gap - margin);
    const onRight = rightSpace >= preferredWidth || leftSpace < preferredWidth && rightSpace >= leftSpace;
    // Keep a clear vertical path beside the pointer, including narrow viewports.
    const width = pointer ? Math.max(1, Math.min(preferredWidth, onRight ? rightSpace : leftSpace)) : preferredWidth;
    if (position.width !== width) {
      setPosition(current => ({ ...current, width }));
      return;
    }
    const height = popup.current.offsetHeight;
    const left = pointer ? onRight ? rect.left + gap : rect.left - width - gap : Math.max(margin, Math.min(rect.left - width / 2, window.innerWidth - width - margin));
    const below = rect.bottom + 12;
    const top = pointer ? Math.max(margin, Math.min(rect.top - margin, window.innerHeight - height - margin)) : below + height <= window.innerHeight - margin ? below : Math.max(margin, rect.top - height - 12);
    setPosition({ left, top, width });
  }, [active, anchor, position.width]);

  function keepOpen() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = null;
  }
  function scheduleClose() {
    keepOpen();
    if (popup.current?.contains(document.activeElement)) return;
    closeTimer.current = setTimeout(() => setActive(null), 180);
  }
  function show(row: TimelineRow, element: HTMLAnchorElement, pointer?: { clientX: number; clientY: number }) {
    keepOpen();
    const rect = element.getBoundingClientRect();
    const viewport = scroller.current?.getBoundingClientRect();
    const center = Math.max(viewport?.left ?? 16, Math.min((rect.left + rect.right) / 2, viewport?.right ?? window.innerWidth - 16));
    setAnchor({ rect: new DOMRect(pointer?.clientX ?? center, pointer?.clientY ?? rect.top, 0, pointer ? 0 : rect.height), pointer: !!pointer });
    activeLink.current = element;
    setActive(row);
  }
  function leaveLine(event: PointerEvent<HTMLAnchorElement>) {
    if (event.pointerType === "mouse" && document.activeElement !== event.currentTarget) scheduleClose();
  }
  function blurLine(event: FocusEvent<HTMLAnchorElement>) {
    if (!popup.current?.contains(event.relatedTarget as Node)) scheduleClose();
  }
  function jumpToYear(value: string) {
    if (!value) return;
    const year = Number(value);
    const row = layout.rows.find(item => Number(item.firstRecord.date!.slice(0, 4)) >= year) ?? layout.rows.at(-1);
    setActive(null);
    scroller.current?.scrollTo({ left: scale === "overview" ? 0 : Math.max(0, (year - firstYear) * yearWidth), top: row ? row.y - rowHeight / 2 : 0, behavior: "instant" });
  }

  const undatedList = <ul>{undated.map(entry => <li key={entry.id}><span className="title-with-copy"><Link href={`/works/${entry.id}`} prefetch={false}>{entry.title}<span>{entry.id}</span></Link><CopyButton text={entry.title} label="曲名をコピー" /></span></li>)}</ul>;

  return <section className="timeline-explorer" aria-labelledby="timeline-title">
    <div className="timeline-heading"><h1 id="timeline-title">グラフ年表</h1><Link className="text-link" href="/#chronology">文字の年表を見る ↗</Link></div>
    <p className="timeline-intro">曲が世に出た順に、公開の時期と期間を見渡す。</p>
    <p className="timeline-review-note"><strong>この年表は現在作成・確認中です。</strong>掲載内容の確認は完了しておらず、日付や情報に誤り・抜けがある可能性があります。</p>
    <ul className="timeline-legend" aria-label="グラフの凡例">
      <li><span className="timeline-symbol" aria-hidden="true" />仮公開・音源未確認</li>
      <li><span className="timeline-symbol is-release" aria-hidden="true" />全曲を聴ける音源あり</li>
      <li><span className="timeline-dash" aria-hidden="true" />本公開まで・未確認の期間</li>
      <li><span className="timeline-solid" aria-hidden="true" />全曲の公開期間</li>
    </ul>
    <div className="timeline-controls">
      <div className="search-form timeline-search"><span className="search-icon" aria-hidden="true" /><label htmlFor="timeline-search" className="sr-only">グラフの曲名・別名で検索</label><input id="timeline-search" type="search" placeholder="曲名・別名で探す" value={query} maxLength={120} onChange={event => setQuery(event.target.value)} /></div>
      <label>表示する作品<select value={filter} onChange={event => setFilter(event.target.value)}><option value="all">すべて</option><option value="preview">仮公開の記録あり</option><option value="available">聴ける音源あり</option><option value="official">公式音源・アルバムあり</option><option value="unofficial">非公式投稿のみ確認</option><option value="unverified">音源未確認</option></select></label>
      <label>横軸の縮尺<select value={scale} onChange={event => setScale(event.target.value)}><option value="overview">全期間を見渡す</option><option value="standard">横に広く表示</option><option value="year">さらに拡大</option><option value="month">月を大きく表示</option></select></label>
      <label>行の間隔<select value={rowHeight} onChange={event => setRowHeight(Number(event.target.value))}><option value={16}>コンパクト</option><option value={24}>標準</option><option value={32}>広め</option></select></label>
      <label>年へ移動<select value="" onChange={event => jumpToYear(event.target.value)} disabled={!layout.years.length}><option value="">年を選ぶ</option>{layout.years.map(year => <option key={year} value={year}>{year}年</option>)}</select></label>
    </div>
    <div className="timeline-status" role="status" aria-live="polite"><span>{pending ? "公開記録を読み込み中…" : error ? "記録を取得できませんでした" : `全${data?.items.length ?? 0}曲中 ${entries.length}曲が一致 · 年表 ${layout.rows.length}曲 · 日付未確認 ${undated.length}曲`}</span>{layout.years.length > 0 && <span>{firstYear}–{layout.years.at(-1)}</span>}</div>
    {pending && <p className="loading-copy" aria-busy="true">公開の記録を読み込んでいます…</p>}
    {!pending && error && <div className="empty-state" role="alert"><h2>グラフを読み込めませんでした。</h2><p>{error}</p><button className="text-link" onClick={retry}>もう一度読み込む ↗</button></div>}
    {!pending && !error && <>
      {layout.rows.length > 0 ? <>
        <p id="timeline-help" className="timeline-help">1行に1曲、上から古い順。線や丸にマウスを重ねると曲名を表示し、クリックすると作品の記録へ進みます。</p>
        <div ref={scroller} className="timeline-scroll" role="region" aria-label="楽曲の公開時期と公開期間のグラフ" aria-describedby="timeline-help timeline-date-note" tabIndex={0}>
          <div className="timeline-canvas" style={{ width: layout.width }}>
            <div className="timeline-axis" aria-hidden="true">
              {layout.years.map((year, index) => <div className="timeline-year-tick" key={year} style={{ left: PLOT_PADDING + (year - firstYear) * yearWidth, width: yearWidth }}><span>{index % Math.max(1, Math.ceil(48 / yearWidth)) === 0 ? year : ""}</span>{yearWidth >= 240 && <div className="timeline-months">{Array.from({ length: 12 }, (_, index) => <span key={index}>{index + 1}月</span>)}</div>}</div>)}
              <span className="timeline-now-label" style={{ left: layout.nowX }}>現在</span>
            </div>
            <div className="timeline-plot" style={{ height: layout.height }}>
              <svg className="timeline-connections" width={layout.width} height={layout.height} aria-hidden="true">
                {layout.connections.map((line, index) => <line key={`${line.entryId}-${index}`} x1={line.start.x} y1={line.start.y} x2={line.end.x} y2={line.end.y} className={`is-${line.kind}${active?.entry.id === line.entryId ? " is-active" : ""}`} />)}
                {layout.points.map((point, index) => <circle key={`${point.entry.id}-${index}`} cx={point.x} cy={point.y} r={active?.entry.id === point.entry.id ? 4 : 3.2} className={`timeline-dot${point.filled ? " is-filled" : ""}`} />)}
              </svg>
              {layout.rows.map((row, index) => <Link key={row.entry.id} href={`/works/${row.entry.id}`} prefetch={false} className="timeline-work-line" style={{ left: row.startX - 8, top: row.y - rowHeight / 2, width: Math.max(24, row.endX - row.startX + 16), height: rowHeight }} aria-label={`${row.entry.title} · ${formatDate(row.firstRecord)} · ${row.canListen ? "全曲公開" : "全曲再生未確認"}`} aria-describedby={active?.entry.id === row.entry.id ? "timeline-popup" : undefined} onPointerEnter={event => { if (event.pointerType === "mouse") show(row, event.currentTarget, event); }} onPointerLeave={leaveLine} onFocus={event => show(row, event.currentTarget)} onBlur={blurLine} onKeyDown={event => {
                const step = event.key === "ArrowDown" ? 1 : event.key === "ArrowUp" ? -1 : 0;
                if (!step) return;
                event.preventDefault();
                const links = scroller.current?.querySelectorAll<HTMLAnchorElement>(".timeline-work-line");
                links?.[(index + step + layout.rows.length) % layout.rows.length]?.focus();
              }}><span className="sr-only">{row.entry.title}</span></Link>)}
            </div>
          </div>
        </div>
        <p id="timeline-date-note" className="timeline-date-note">YouTube・アルバム・SoundCloudなどに全曲の掲載があるものは、現在も聴ける扱いです。公式・非公式はポップアップで区別し、非公式投稿のリンクは掲載しません。音源未確認の曲は白丸と点線で現在まで表示します。ゲーム収録歴だけでは聴取可能と判定しません。実再生・地域制限、過去からの連続公開は未検証。月日不明の点は既知期間の中央に配置します。</p>
      </> : entries.length === 0 && <div className="empty-state"><h2>該当する記録がありません。</h2><p>曲名の一部で探すか、表示する作品を変えてみてください。</p>{(query || filter !== "all") && <button className="text-link" onClick={() => { setQuery(""); setFilter("all"); }}>条件をクリア</button>}</div>}
      {undated.length > 0 && (deferredQuery || !layout.rows.length
        ? <section className="timeline-undated" aria-labelledby="timeline-undated-title"><h2 id="timeline-undated-title">日付未確認の作品 {undated.length}曲</h2><p>公開時期の記録がないため、グラフには配置していません。曲名から作品の記録を開けます。</p>{undatedList}</section>
        : <details className="timeline-undated"><summary>日付未確認の作品 {undated.length}曲</summary><p>公開時期を推測してグラフに配置せず、作品の記録を掲載しています。</p>{undatedList}</details>)}
      {data && <p className="timeline-checked">調査確認日 {data.checked_on.replaceAll("-", ".")} · グラフ基準日 {data.as_of.replaceAll("-", ".")}</p>}
    </>}
    {active && <div ref={popup} id="timeline-popup" className="timeline-popup" role="dialog" aria-label={`${active.entry.title}の公開記録`} style={position} onPointerEnter={keepOpen} onPointerLeave={scheduleClose} onFocus={keepOpen} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget as Node)) scheduleClose(); }}>
      <div className="timeline-popup-heading"><h2><Link href={`/works/${active.entry.id}`}>{active.entry.title}</Link></h2><CopyButton text={active.entry.title} label="曲名をコピー" /><button aria-label="ポップアップを閉じる" onClick={() => { activeLink.current?.focus({ preventScroll: true }); setActive(null); }}>×</button></div>
      <dl><div><dt>最も早い公開記録</dt><dd>{formatDate(active.firstRecord)}</dd></div>{active.entry.preview && <div><dt>仮公開</dt><dd>{formatDate(active.entry.preview)}</dd></div>}{active.entry.release && <div><dt>本公開の記録</dt><dd>{formatDate(active.entry.release)}</dd></div>}<div><dt>現在の音源</dt><dd>{accessLabel(active.entry)}</dd></div></dl>
      <p className="timeline-popup-record">{active.firstRecord.kind} · {active.firstRecord.medium}<br />{active.entry.audio_note}{active.firstRecord.precision !== "day" && <><br />最初の記録は{active.firstRecord.precision === "year" ? "年のみ（月日未確認）" : "年月のみ（日未確認）"}。</>}</p>
      <div className="timeline-popup-links"><Link href={`/works/${active.entry.id}`}>作品の記録 ↗</Link><a href={active.firstRecord.source_url} target="_blank" rel="noreferrer">公開記録の出典 ↗</a></div>
      {!!active.entry.audio_sources?.length && <ul className="timeline-audio-sources">{active.entry.audio_sources.slice(0, 3).map(source => <li key={`${source.origin}-${source.url}`}><a href={source.url} target="_blank" rel="noreferrer">{source.origin === "official" ? "公式" : "非公式"} · {source.label} ↗</a></li>)}</ul>}
    </div>}
  </section>;
}
