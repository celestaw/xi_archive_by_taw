"use client";

import Link from "next/link";
import { useCallback } from "react";
import { api, formatDate, type CollectionKind } from "@/lib/api";
import { useResource } from "@/lib/useResource";
import { CopyButton } from "./CopyButton";

export function CollectionRecord({ kind, id }: { kind: CollectionKind; id: string }) {
  const load = useCallback((signal: AbortSignal) => api.collection(kind, id, signal), [kind, id]);
  const { data, pending, error, retry } = useResource(load);
  const base = kind === "album" ? "/albums" : "/games";
  return <main id="main" className="shell collection-page">
    <Link href={base} className="collection-back">{kind === "album" ? "アルバム" : "音楽ゲーム"}一覧へ</Link>
    {pending && <p className="loading-copy" role="status">収録情報を読み込んでいます…</p>}
    {!pending && error && <div className="empty-state" role="alert"><h1>収録情報を取得できませんでした。</h1><p>{error}</p><button className="text-link" onClick={retry}>もう一度読み込む</button></div>}
    {!pending && data && <>
      <div className="collection-title-row"><h1>{data.title}</h1><span>{data.entry_count}曲</span></div>
      <p className="collection-notice">{data.note}</p>
      {data.release_records.length > 0 && <dl className="collection-releases">{data.release_records.map(record => <div key={record.id}>
        <dt>{record.kind}</dt><dd><time>{formatDate(record)}</time><a href={record.source_url} target="_blank" rel="noopener noreferrer" aria-label={`${record.kind}の出典（新しいタブ）`}>出典</a></dd>
      </div>)}</dl>}
      <div className="collection-track-heading"><h2>{kind === "album" ? "収録曲" : "楽曲一覧"}</h2><a href={data.source_url} target="_blank" rel="noopener noreferrer">{kind === "album" ? "公式資料" : "掲載根拠"}<span className="sr-only">（新しいタブ）</span></a></div>
      <ol className={`collection-track-list${kind === "game" ? " is-game" : ""}`}>{data.tracks.map((track, index) => <li key={`${track.work_id ?? track.title}:${track.disc}:${track.track_number}:${index}`}>
        {kind === "album" && <span className="collection-track-number" aria-label={track.track_number === null ? "曲順未確認" : `${track.disc ? `Disc ${track.disc} ` : ""}第${track.track_number}曲`}>{track.disc ? `${track.disc}.` : ""}{track.track_number?.toString().padStart(2, "0") ?? "—"}</span>}
        <div className="collection-track-info">
          <div className="title-with-copy"><h3>{track.work_id ? <Link href={`/works/${track.work_id}`}>{track.title}</Link> : track.title}</h3><CopyButton text={track.title} /></div>
          <p>{track.credited_name}{track.role.startsWith("他者") && <> / {track.role}</>}{track.listing_kind !== "収録" && <span className="inline-label">{track.listing_kind}</span>}{track.work_id && track.attribution === "unverified" && <span className="inline-label unverified">帰属未確認</span>}</p>
          <details><summary>出典・担当</summary><p>{track.evidence}</p>{track.edition && <p>版・収録先：{track.edition}</p>}{track.role && track.role !== "担当未確認" && <p>担当：{track.role}</p>}{track.note && <p>{track.note}</p>}{track.genre && <p>ジャンル：{track.genre.label}（{track.genre.medium}の表記） <a href={track.genre.source_url} target="_blank" rel="noopener noreferrer">ジャンルの出典<span className="sr-only">（新しいタブ）</span></a></p>}<p>資料確認日：{track.checked_on.replaceAll("-", ".")}</p><a href={track.source_url} target="_blank" rel="noopener noreferrer">資料を開く<span className="sr-only">（新しいタブ）</span></a></details>
        </div>
        {(track.genre || track.listening) && <div className="collection-track-meta">
          {track.genre && <span className="track-genre" title={`${track.genre.medium}でのジャンル表記`}><span className="sr-only">ジャンル：</span>{track.genre.label}</span>}
          {track.listening && <a className="collection-listen" href={track.listening.url} target="_blank" rel="noopener noreferrer" aria-label={`${track.title}の公式試聴（新しいタブ）`}>試聴</a>}
        </div>}
      </li>)}</ol>
    </>}
  </main>;
}
