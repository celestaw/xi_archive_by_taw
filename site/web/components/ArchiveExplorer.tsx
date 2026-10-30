"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { api, formatDate, type Meta, type Work, type WorkList, type WorkQuery } from "@/lib/api";
import { YearNavigation } from "@/components/YearNavigation";
import { CopyButton } from "@/components/CopyButton";

export function ArchiveExplorer() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const search = params.toString();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [result, setResult] = useState<WorkList | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadedSearch, setLoadedSearch] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState("");
  const [nextOffset, setNextOffset] = useState(0);
  const moreRequest = useRef<AbortController | null>(null);
  const activeQuery = useRef<string | null>(null);
  const sentinel = useRef<HTMLDivElement | null>(null);
  const resultsHeading = useRef<HTMLDivElement | null>(null);
  const jumpToResults = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    const parsed = new URLSearchParams(search);
    const query = Object.fromEntries(parsed) as unknown as WorkQuery;
    activeQuery.current = null;
    moreRequest.current?.abort();
    moreRequest.current = null;
    setLoadingMore(false);
    setMoreError("");
    setNextOffset(0);
    setLoading(true);
    setError("");
    Promise.all([api.meta(controller.signal), api.works({ ...query, limit: 40, offset: 0 }, controller.signal)])
      .then(([newMeta, newResult]) => {
        if (controller.signal.aborted) return;
        setMeta(newMeta);
        setResult(newResult);
        setNextOffset(newResult.offset + newResult.items.length);
        activeQuery.current = `${retry}:${search}`;
      })
      .catch((err: Error) => { if (!controller.signal.aborted) { setError(err.message === "Failed to fetch" ? "記録に接続できませんでした。接続を確認して、もう一度お試しください。" : err.message); setResult(null); } })
      .finally(() => { if (!controller.signal.aborted) { setLoadedSearch(search); setLoading(false); } });
    return () => { activeQuery.current = null; controller.abort(); moreRequest.current?.abort(); };
  }, [search, retry]);

  const pending = loading || loadedSearch !== search;
  const hasMore = !!result && nextOffset < result.total;
  useEffect(() => {
    if (pending || !jumpToResults.current) return;
    jumpToResults.current = false;
    resultsHeading.current?.scrollIntoView({ block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
    resultsHeading.current?.focus({ preventScroll: true });
  }, [pending, search]);
  const loadMore = useCallback(async () => {
    if (pending || !hasMore || moreRequest.current || activeQuery.current !== `${retry}:${search}`) return;
    const controller = new AbortController();
    moreRequest.current = controller;
    setLoadingMore(true);
    setMoreError("");
    try {
      const query = Object.fromEntries(new URLSearchParams(search)) as unknown as WorkQuery;
      const page = await api.works({ ...query, limit: 40, offset: nextOffset }, controller.signal);
      if (controller.signal.aborted) return;
      if (page.items.length === 0 && nextOffset < page.total) {
        throw new Error("続きの記録を取得できませんでした。もう一度お試しください。");
      }
      setResult(current => {
        if (!current) return current;
        const existing = new Set(current.items.map(work => work.id));
        return { ...current, total: page.total, items: [...current.items, ...page.items.filter(work => !existing.has(work.id))] };
      });
      setNextOffset(page.offset + page.items.length);
    } catch (err) {
      if (!controller.signal.aborted) setMoreError(err instanceof Error && err.message !== "Failed to fetch" ? err.message : "続きの記録に接続できませんでした。");
    } finally {
      if (moreRequest.current === controller) {
        moreRequest.current = null;
        if (!controller.signal.aborted) setLoadingMore(false);
      }
    }
  }, [pending, hasMore, search, retry, nextOffset]);

  useEffect(() => {
    if (pending || !hasMore || loadingMore || moreError || !sentinel.current || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) void loadMore();
    }, { rootMargin: "300px 0px" });
    observer.observe(sentinel.current);
    return () => observer.disconnect();
  }, [pending, hasMore, loadingMore, moreError, loadMore]);

  function update(key: string, value: string) {
    const next = new URLSearchParams(search);
    next.delete("offset");
    if (value) next.set(key, value); else next.delete(key);
    if (key === "year") next.delete("date_status");
    if (key === "date_status") next.delete("year");
    router.push(`${pathname}${next.size ? `?${next}` : ""}#chronology`, { scroll: false });
  }

  function selectYear(value: string) {
    const selected = params.get("date_status") === "undated" ? "undated" : params.get("year") ?? "";
    if (value === selected && (value !== "" || !params.size)) {
      resultsHeading.current?.scrollIntoView({ block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
      resultsHeading.current?.focus({ preventScroll: true });
      return;
    }
    jumpToResults.current = true;
    if (!value) router.push(`${pathname}#chronology`, { scroll: false });
    else update(value === "undated" ? "date_status" : "year", value);
  }

  const groups = new Map<string, Work[]>();
  // Hide stale results while a new query is in flight.
  if (!pending) for (const work of result?.items ?? []) {
    const year = work.earliest_record?.date?.slice(0, 4) ?? "日付未確認";
    groups.set(year, [...(groups.get(year) ?? []), work]);
  }

  return (
    <section id="chronology" className="archive-section" aria-labelledby="index-title">
      <YearNavigation meta={meta} selected={params.get("date_status") === "undated" ? "undated" : params.get("year") ?? ""} onSelect={selectYear} />
      <div className="catalogue">
        <form className="search-form" role="search" onSubmit={event => { event.preventDefault(); update("q", String(new FormData(event.currentTarget).get("q") ?? "").trim()); }}>
          <span className="search-icon" aria-hidden="true" />
          <label htmlFor="work-search" className="sr-only">曲名・別名で検索</label>
          <input key={params.get("q") ?? ""} id="work-search" name="q" defaultValue={params.get("q") ?? ""} placeholder="曲名・別名で探す" maxLength={120} />
          <button type="submit">検索 <span aria-hidden="true">↗</span></button>
        </form>
        <div className="filter-row">
          <label>媒体 <select value={params.get("medium") ?? ""} onChange={e => update("medium", e.target.value)}><option value="">すべて</option>{meta?.mediums.map(m => <option key={m} value={m}>{m}</option>)}</select></label>
          <label>帰属 <select value={params.get("attribution") ?? ""} onChange={e => update("attribution", e.target.value)}><option value="">すべて</option><option value="credited">一次資料のクレジットあり</option><option value="unverified">帰属未確認</option></select></label>
          {params.size > 0 && <Link href="/#chronology" className="clear-filter">条件をクリア ×</Link>}
        </div>
        <div className="catalogue-note"><span className="note-mark" aria-hidden="true">※</span><p>日付は、確認できた最も早い公開記録。<br />作曲日・真の初公開日とは限りません。</p><Link href="/about">このサイトについて <span aria-hidden="true">↗</span></Link></div>
        <div className="results-heading" ref={resultsHeading} tabIndex={-1} role="status" aria-live="polite"><span>{pending ? "読み込み中…" : result ? `${result.total}件` : "記録を取得できませんでした"}</span><span>確認できた記録の古い順</span></div>
        <div aria-busy={pending}>
          {pending && <div className="loading-copy">作品の記録を読み込んでいます<span className="loading-dot">…</span></div>}
          {!pending && error && <div className="empty-state" role="alert"><h3>記録を読み込めませんでした。</h3><p>{error}</p><button className="text-link" onClick={() => setRetry(r => r + 1)}>もう一度読み込む ↗</button></div>}
          {!pending && !error && result?.total === 0 && <div className="empty-state"><span className="empty-mark">∅</span><h3>該当する記録がありません。</h3><p>曲名の一部で探すか、絞り込み条件を変えてみてください。</p><Link className="text-link" href="/#chronology">すべての記録を見る ↗</Link></div>}
          {[...groups].map(([year, items]) => <section className="year-group" key={year} aria-label={`${year}の記録`}>
            <div className="year-heading"><h2>{year}</h2><span>{items.length}件</span></div>
            <ol className="work-list">{items.map(work => <li key={work.id}>
              <div className={`work-row${work.genre ? " has-genre" : ""}`}>
                <Link href={`/works/${work.id}`} className="work-row-link" aria-labelledby={`work-title-${work.id}`} />
                <div className="work-date"><time>{formatDate(work.earliest_record)}</time><span>{work.id}</span></div>
                <div className="work-info">
                  <div className="title-with-copy"><h3 id={`work-title-${work.id}`}>{work.title}</h3><CopyButton text={work.title} /></div>
                  <p>{work.earliest_record?.medium ?? "媒体・日付を調査中"}{work.is_variant && <span className="inline-label">別バージョン</span>}{work.attribution === "unverified" && <span className="inline-label unverified">帰属未確認</span>}</p><span className="date-kind">{work.earliest_record?.kind ?? "日付未確認"}</span>
                </div>
                {work.genre && <span className="track-genre work-genre" title={`${work.genre.medium}でのジャンル表記`}><span className="sr-only">ジャンル：</span>{work.genre.label}</span>}
                <span className="work-open" aria-hidden="true">↗</span>
              </div>
            </li>)}</ol>
          </section>)}
        </div>
        {!pending && result && result.total > 0 && <div className="list-continuation" ref={sentinel}>
          <p role="status" aria-live="polite">{loadingMore ? "続きを読み込み中…" : `${result.items.length} / ${result.total}件を表示`}</p>
          {moreError && <p className="continuation-error" role="alert">{moreError}</p>}
          {hasMore && <button className="text-link" disabled={loadingMore} onClick={() => void loadMore()}>{moreError ? "もう一度読み込む" : "続きを読み込む"}</button>}
        </div>}
      </div>
    </section>
  );
}
