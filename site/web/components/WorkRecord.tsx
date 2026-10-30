"use client";

import Link from "next/link";
import { CommentText } from "./CommentText";
import { CopyButton } from "./CopyButton";
import { useEffect, useState } from "react";
import { api, ApiFailure, formatDate, type WorkContext, type WorkDetail } from "@/lib/api";

const sectionIcons = {
  date: <><rect x="4" y="5" width="16" height="16" rx="2" /><path d="M8 3v4m8-4v4M4 11h16m-11 4h2m3 0h2m-7 3h2" /></>,
  albums: <><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="1" /></>,
  games: <><path d="M7 7h10c2 0 3 2 3.4 4l1 6c.3 2-1.8 3-3.1 1.7L15 16H9l-3.3 2.7C4.4 20 2.3 19 2.6 17l1-6C4 9 5 7 7 7Z" /><path d="M7 10v5m-2.5-2.5h5M16 11h.01M18 14h.01" /></>,
  history: <><path d="M7 5v14m4-14h9M11 12h7m-7 7h9" /><circle cx="7" cy="5" r="2" /><circle cx="7" cy="12" r="2" /><circle cx="7" cy="19" r="2" /></>,
  remixes: <><path d="M5 12h7c3 0 3-6 6-6h3m-4-4 4 4-4 4M12 12c3 0 3 6 6 6h3m-4-4 4 4-4 4" /><circle cx="4" cy="12" r="2" /></>,
  comment: <><path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 4V6a2 2 0 0 1 2-2Z" /><path d="M7 9h10M7 13h7" /></>,
};

function WorkSectionHeading({ id, kind, title }: { id: string; kind: keyof typeof sectionIcons; title: string }) {
  return <h2 id={id} className="work-section-heading">
    <span className="work-section-symbol" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" focusable="false">{sectionIcons[kind]}</svg></span>
    <span>{title}</span>
  </h2>;
}

function WorkCollections({ items, kind }: { items: WorkContext["albums"]; kind: "album" | "game" }) {
  if (!items.length) return <p className="muted">{kind === "album" ? "収録アルバム" : "収録ゲーム"}はまだ確認できていません。</p>;
  return <ul className="work-collection-list">{items.map(({ collection, tracks }) => <li key={collection.id}>
    <h3><Link className="text-link" href={`/${kind === "album" ? "albums" : "games"}/${collection.id}`}>{collection.title}</Link></h3>
    {tracks.map((track, index) => <div key={`${track.source_url}-${index}`}>
      <p className="muted">
        {kind === "album" && track.track_number !== null && <>{track.disc !== null ? `Disc ${track.disc} / ` : ""}第{track.track_number}曲 · </>}
        {track.title}{track.listing_kind !== "収録" && <span className="inline-label">{track.listing_kind}</span>}
      </p>
      {track.edition && <p className="muted">版・収録先：{track.edition}</p>}
      <details><summary>収録情報の出典</summary><p>{track.evidence}</p>{track.note && <p>{track.note}</p>}<a href={track.source_url} target="_blank" rel="noopener noreferrer">資料を開く<span className="sr-only">（新しいタブ）</span></a></details>
    </div>)}
  </li>)}</ul>;
}

export function WorkRecord({ id }: { id: string }) {
  const [data, setData] = useState<{ work: WorkDetail; context: WorkContext } | null>(null);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError(""); setNotFound(false);
    Promise.all([api.work(id, controller.signal), api.workContext(id, controller.signal)]).then(([work, context]) => {
      if (!controller.signal.aborted) setData({ work, context });
    }).catch((err: Error) => {
      if (controller.signal.aborted) return;
      setNotFound(err instanceof ApiFailure && err.status === 404);
      setError(err.message);
    });
    return () => controller.abort();
  }, [id, retry]);

  if (error) return <div className="empty-state" role="alert"><h1>{notFound ? "この作品の記録はありません。" : "記録を読み込めませんでした。"}</h1><p>{error}</p>{!notFound && <button className="text-link" onClick={() => setRetry(r => r + 1)}>もう一度読み込む ↗</button>}<Link className="text-link" href="/#chronology">作品年表へ戻る ↗</Link></div>;
  if (!data) return <p className="loading-copy" role="status">作品の記録を読み込んでいます…</p>;
  const { work, context } = data;
  const commentParagraphs = work.comment.split(/\n\s*\n/).filter(paragraph => paragraph.trim());
  const otherRelationships = work.relationships.filter(relationship => !context.remixes.some(remix => remix.work_id === relationship.work_id));
  return (
    <article className="record-page">
      <header className="detail-heading"><p className="eyebrow">COMPOSITION RECORD / {work.id}</p><div className="title-with-copy detail-title-with-copy"><h1>{work.title}</h1><CopyButton text={work.title} /></div>{work.pronunciation && <p className="detail-pronunciation"><span>読み方：<strong>{work.pronunciation.reading}</strong></span><span>{work.pronunciation.basis === "author_suggestion" ? "作者の読み方案" : "作者が示した読み"}</span><a href={work.pronunciation.source_url} target="_blank" rel="noopener noreferrer">作者の投稿{work.pronunciation.source_date && `（${work.pronunciation.source_date.replaceAll("-", ".")}）`}<span className="sr-only">（新しいタブ）</span></a></p>}<p className="detail-credit">{work.credited_name}<span>{work.role}</span></p>{work.attribution === "unverified" && <p className="attribution-notice">帰属未確認の候補です。xiの作品と確定した項目ではありません。</p>}</header>
      <div className="detail-grid">
        <aside className="detail-aside" aria-labelledby="date-title"><WorkSectionHeading id="date-title" kind="date" title="日付" /><p className="detail-date">{formatDate(work.earliest_record)}</p><p>{work.earliest_record?.kind ?? "日付未確認"}</p><p className="muted">確認できた公開記録のうち最も早い日付です。作曲日・真の初公開日とは限りません。</p><p className="checked-on">調査確認日 {work.checked_on.replaceAll("-", ".")}</p></aside>
        <div className="detail-body">
          <section aria-labelledby="albums-title"><WorkSectionHeading id="albums-title" kind="albums" title="収録アルバム" /><WorkCollections items={context.albums} kind="album" /></section>
          <section aria-labelledby="games-title"><WorkSectionHeading id="games-title" kind="games" title="収録ゲーム" /><WorkCollections items={context.games} kind="game" /></section>
          <section className="work-history" aria-labelledby="history-title">
            <WorkSectionHeading id="history-title" kind="history" title="経緯" />
            {work.aliases.length > 0 && <div><h3 className="work-subheading">別名・表記</h3>{work.aliases.map(a => <div className="alias" key={a.title}><h4>{a.title}<span>{a.kind}</span></h4><p>{a.evidence_status}</p></div>)}</div>}
            <div><h3 className="work-subheading">公開・収録の記録</h3>{work.records.length === 0 ? <p className="muted">根拠のある公開記録は、まだ確認できていません。</p> : <ol className="publication-list">{work.records.map(record => <li key={record.id}><time>{formatDate(record)}</time><div><p className="publication-kind">{record.kind}</p><h4>{record.medium}</h4><p>{record.evidence}</p>{record.true_first_publication_confirmed && <p>初公開として確認した記録</p>}<a className="text-link" href={record.source_url} target="_blank" rel="noopener noreferrer">出典を開く <span aria-hidden="true">↗</span><span className="sr-only">（新しいタブ）</span></a></div></li>)}</ol>}</div>
            {work.creation_records.length > 0 && <div><h3 className="work-subheading">制作についての記録</h3><p className="muted">公開日とは区別した、作曲・リマスター等の記録です。</p><ul className="publication-list">{work.creation_records.map(record => <li key={record.id}><time>{formatDate(record)}</time><div><p className="publication-kind">{record.kind}</p><p>{record.evidence}</p><a className="text-link" href={record.source_url} target="_blank" rel="noopener noreferrer">出典を開く<span className="sr-only">（新しいタブ）</span></a></div></li>)}</ul></div>}
            {otherRelationships.length > 0 && <div><h3 className="work-subheading">関連する作品・バージョン</h3><ul className="relationship-list">{otherRelationships.map(r => <li key={`${r.work_id}-${r.kind}`}><div className="title-with-copy"><Link className="text-link" href={`/works/${r.work_id}`}>{r.title}</Link><CopyButton text={r.title} /></div><p>{r.kind} / {r.evidence_status}</p></li>)}</ul></div>}
            <div><h3 className="work-subheading">公式の試聴先</h3>{work.listening.length ? <ul className="listening-list">{work.listening.map(link => <li key={link.url}><a href={link.url} target="_blank" rel="noopener noreferrer"><span>{link.label}<small>{link.version}</small></span><span aria-hidden="true">↗</span><span className="sr-only">（新しいタブ）</span></a><details><summary>公式性と音源の確認範囲</summary><p>{link.official_basis}</p><p>{link.availability}</p><a href={link.officialness_source_url} target="_blank" rel="noopener noreferrer">公式性の根拠<span className="sr-only">（新しいタブ）</span></a></details></li>)}</ul> : <p className="muted">掲載できる公式の試聴先は未確認です。</p>}</div>
            {work.sources.length > 0 && <details><summary>曲名・名義の出典</summary><ul>{work.sources.map(source => <li key={`${source.kind}-${source.url}-${source.credit}`}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.label}<span className="sr-only">（新しいタブ）</span></a><p className="muted">{source.kind === "primary" ? "一次資料" : "二次資料"}{source.credit && ` · 資料の名義：${source.credit}`} · 確認日 {source.checked_on.replaceAll("-", ".")}</p></li>)}</ul></details>}
          </section>
          <section aria-labelledby="remixes-title">
            <WorkSectionHeading id="remixes-title" kind="remixes" title="これをもとにリミックスされた曲" />
            {context.remixes.length > 0 ? <ul className="relationship-list">{context.remixes.map(remix => <li key={remix.work_id ?? `${remix.album_id}-${remix.title}`}>
              <div className="title-with-copy">{remix.work_id ? <Link className="text-link" href={`/works/${remix.work_id}`}>{remix.title}</Link> : <a className="text-link" href={remix.source_url!} target="_blank" rel="noopener noreferrer">{remix.title}<span className="sr-only">（新しいタブ）</span></a>}<CopyButton text={remix.title} /></div>
              <p>{remix.credited_name}</p><p>{remix.evidence_status}</p>
              {remix.album_id && <p>収録アルバム：<Link href={`/albums/${remix.album_id}`}>{remix.album_title}</Link></p>}
            </li>)}</ul> : <p className="muted">この曲をもとにしたリミックスは、まだ確認できていません。</p>}
          </section>
          <section aria-labelledby="comment-title">
            <WorkSectionHeading id="comment-title" kind="comment" title="補足コメント" />
            {commentParagraphs.length > 0 ? <div className="detail-comment">{commentParagraphs.map((paragraph, index) => <p key={index}><CommentText text={paragraph} /></p>)}</div> : <p className="muted">補足コメントはまだありません。</p>}
          </section>
        </div>
      </div>
    </article>
  );
}
