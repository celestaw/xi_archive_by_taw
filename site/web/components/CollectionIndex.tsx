"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { api, formatDate, type CollectionKind } from "@/lib/api";
import { useResource } from "@/lib/useResource";

export function CollectionIndex({ kind }: { kind: CollectionKind }) {
  const [query, setQuery] = useState("");
  const load = useCallback((signal: AbortSignal) => api.collections(kind, signal), [kind]);
  const { data, pending, error, retry } = useResource(load);
  const base = kind === "album" ? "/albums" : "/games";
  const title = kind === "album" ? "アルバム" : "音楽ゲーム";
  const term = query.normalize("NFKC").toLocaleLowerCase().trim();
  const items = data?.items.filter(item => item.title.normalize("NFKC").toLocaleLowerCase().includes(term)) ?? [];
  const groups = kind === "album" ? ["ソロアルバム", "参加作品"] : ["ゲーム"];

  return <main id="main" className="shell collection-page">
    <h1>{title}</h1>
    <p className="collection-notice">{kind === "game" ? "確認できた収録・提供・BMS登録・公式許諾の記録。全曲の照合は継続中です。" : "既存資料で確認できた収録情報を掲載しています。"}</p>
    <form className="search-form collection-search" role="search" onSubmit={event => event.preventDefault()}>
      <span className="search-icon" aria-hidden="true" />
      <label className="sr-only" htmlFor="collection-search">{title}名で検索</label>
      <input id="collection-search" type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={`${title}名で探す`} maxLength={120} />
    </form>
    <p className="collection-count" role="status" aria-live="polite">{pending ? "読み込み中…" : data ? `${items.length}${kind === "album" ? "作品" : "タイトル"}` : ""}</p>
    {pending && <p className="loading-copy">収録情報を読み込んでいます…</p>}
    {!pending && error && <div className="empty-state" role="alert"><p>{error}</p><button className="text-link" onClick={retry}>もう一度読み込む</button></div>}
    {!pending && !error && items.length === 0 && <div className="empty-state"><p>該当する{title}がありません。</p>{query && <button className="text-link" onClick={() => setQuery("")}>検索をクリア</button>}</div>}
    {!pending && !error && groups.map(group => {
      const members = items.filter(item => item.category === group);
      if (!members.length) return null;
      return <section className="collection-group" key={group} aria-label={group}>
        {kind === "album" && <h2>{group}</h2>}
        <ul className="collection-index-list">{members.map(item => <li key={item.id}>
          <Link className={`collection-row${kind === "game" ? " is-game" : ""}`} href={`${base}/${encodeURIComponent(item.id)}`}>
            {kind === "album" && <span className="collection-date">{formatDate(item.release_records[0])}</span>}
            <span className="collection-name">{item.title}</span>
            <span className="collection-size">{item.entry_count}曲</span>
            <svg className="collection-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" /></svg>
          </Link>
        </li>)}</ul>
      </section>;
    })}
  </main>;
}
