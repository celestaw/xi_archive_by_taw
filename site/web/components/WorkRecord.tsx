"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiFailure, formatDate, type WorkDetail } from "@/lib/api";

const sourceKinds = { primary: "一次資料", secondary: "二次資料", lead: "未検証の調査先", input: "入力資料" };

function AttributionSource({ source }: { source: WorkDetail["attribution_basis"]["sources"][number] }) {
  return <li>
    <h3>{source.label}</h3>
    <p className="muted">{sourceKinds[source.kind]} · {source.locator}</p>
    {source.credit && <p>資料の名義：{source.credit}</p>}
    <p>{source.summary}</p>
    <p>{source.identity_note}</p>
    {source.url && <a className="text-link" href={source.url} target="_blank" rel="noopener noreferrer">{source.kind === "lead" ? "調査先を開く" : "根拠資料を開く"}<span aria-hidden="true">↗</span><span className="sr-only">（新しいタブ）</span></a>}
    <p className="attribution-checked">資料確認日 {source.checked_on.replaceAll("-", ".")}</p>
  </li>;
}

export function WorkRecord({ id }: { id: string }) {
  const [work, setWork] = useState<WorkDetail | null>(null);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setWork(null); setError(""); setNotFound(false);
    api.work(id, controller.signal).then(setWork).catch((err: Error) => {
      if (controller.signal.aborted) return;
      setNotFound(err instanceof ApiFailure && err.status === 404);
      setError(err.message);
    });
    return () => controller.abort();
  }, [id, retry]);

  if (error) return <div className="empty-state" role="alert"><h1>{notFound ? "この作品の記録はありません。" : "記録を読み込めませんでした。"}</h1><p>{error}</p>{!notFound && <button className="text-link" onClick={() => setRetry(r => r + 1)}>もう一度読み込む ↗</button>}<Link className="text-link" href="/#chronology">作品年表へ戻る ↗</Link></div>;
  if (!work) return <p className="loading-copy" role="status">作品の記録を読み込んでいます…</p>;
  return (
    <article className="record-page">
      <header className="detail-heading"><p className="eyebrow">COMPOSITION RECORD / {work.id}</p><h1>{work.title}</h1><p className="detail-credit">{work.credited_name}<span>{work.role}</span></p>{work.attribution === "unverified" && <p className="attribution-notice">帰属未確認の候補です。xiの作品と確定した項目ではありません。</p>}</header>
      <div className="detail-grid">
        <aside className="detail-aside"><p className="eyebrow">EARLIEST FOUND RECORD</p><p className="detail-date">{formatDate(work.earliest_record)}</p><p>{work.earliest_record?.kind ?? "日付未確認"}</p><p className="muted">確認できた公開記録のうち最も早い日付です。作曲日・真の初公開日とは限りません。</p><p className="checked-on">調査確認日 {work.checked_on.replaceAll("-", ".")}</p></aside>
        <div className="detail-body">
          {work.attribution_basis && <section className="attribution-basis" aria-labelledby="attribution-title">
            <h2 id="attribution-title">xiとの関係・掲載の根拠</h2>
            <p>{work.attribution_basis.summary}</p>
            <details open={work.attribution === "unverified"}>
              <summary>調査対象に入れた経緯</summary>
              <ul className="attribution-sources">{work.attribution_basis.inclusion.map((source, i) => <AttributionSource key={i} source={source} />)}</ul>
            </details>
            {work.attribution_basis.sources.length > 0 ? <ul className="attribution-sources">{work.attribution_basis.sources.map((source, i) => <AttributionSource key={`${source.url}-${i}`} source={source} />)}</ul> : <p className="muted">曲名とxiの担当を裏付ける資料は、まだ確認できていません。</p>}
            <ul className="attribution-limitations">{work.attribution_basis.limitations.map(note => <li key={note}>{note}</li>)}</ul>
          </section>}
          {work.comment && <p className="detail-comment">{work.comment}</p>}
          {work.aliases.length > 0 && <section><h2>別名・表記</h2>{work.aliases.map(a => <div className="alias" key={a.title}><h3>{a.title}<span>{a.kind}</span></h3><p>{a.evidence_status}</p></div>)}</section>}
          <section><div className="detail-section-label"><h2>公開・収録の記録</h2><span>PUBLICATION HISTORY</span></div>{work.records.length === 0 ? <p className="muted">根拠のある公開記録は、まだ確認できていません。</p> : <ol className="publication-list">{work.records.map(record => <li key={record.id}><time>{formatDate(record)}</time><div><p className="publication-kind">{record.kind}</p><h3>{record.medium}</h3><p>{record.evidence}</p>{record.true_first_publication_confirmed && <p>初公開として確認した記録</p>}<a className="text-link" href={record.source_url} target="_blank" rel="noopener noreferrer">出典を開く <span aria-hidden="true">↗</span><span className="sr-only">（新しいタブ）</span></a></div></li>)}</ol>}</section>
          <section><div className="detail-section-label"><h2>公式の試聴先</h2><span>LISTEN OFFICIALLY</span></div>{work.listening.length ? <ul className="listening-list">{work.listening.map(link => <li key={link.url}><a href={link.url} target="_blank" rel="noopener noreferrer"><span>{link.label}<small>{link.version}</small></span><span aria-hidden="true">↗</span><span className="sr-only">（新しいタブ）</span></a><details><summary>公式性と音源の確認範囲</summary><p>{link.official_basis}</p><p>{link.availability}</p><a href={link.officialness_source_url} target="_blank" rel="noopener noreferrer">公式性の根拠 ↗<span className="sr-only">（新しいタブ）</span></a></details></li>)}</ul> : <p className="muted">掲載できる公式の試聴先は未確認です。</p>}</section>
          {work.creation_records.length > 0 && <section><div className="detail-section-label"><h2>制作についての記録</h2><span>CREATION NOTES</span></div><p className="muted">公開日とは区別した、作曲・リマスター等の記録です。</p><ul className="publication-list">{work.creation_records.map(record => <li key={record.id}><time>{formatDate(record)}</time><div><p className="publication-kind">{record.kind}</p><p>{record.evidence}</p><a className="text-link" href={record.source_url} target="_blank" rel="noopener noreferrer">出典を開く ↗<span className="sr-only">（新しいタブ）</span></a></div></li>)}</ul></section>}
          {work.relationships.length > 0 && <section><h2>関連する作品・バージョン</h2><ul className="relationship-list">{work.relationships.map(r => <li key={`${r.work_id}-${r.kind}`}><Link className="text-link" href={`/works/${r.work_id}`}>{r.title} ↗</Link><p>{r.kind} / {r.evidence_status}</p></li>)}</ul></section>}
          {work.issues.length > 0 && <section className="research-notes"><h2>調査メモ</h2><ul>{work.issues.map(issue => <li key={issue}>{issue}</li>)}</ul></section>}
        </div>
      </div>
    </article>
  );
}
