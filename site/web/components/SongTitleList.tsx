"use client";

import { useRef, useState } from "react";
import { CopyButton } from "./CopyButton";

export function SongTitleList({ titles }: { titles: string[] }) {
  const panel = useRef<HTMLDetailsElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  const [status, setStatus] = useState("");
  const text = titles.join("\n");

  function selectAll() {
    if (panel.current) panel.current.open = true;
    field.current?.focus({ preventScroll: true });
    field.current?.select();
    field.current?.setSelectionRange(0, text.length);
  }

  return <section aria-label="曲名のコピーとダウンロード">
    <div className="song-list-actions">
      <CopyButton text={text} label="全曲名をコピー" onManualCopy={selectAll} onStatus={setStatus}>全曲名をコピー</CopyButton>
      <button type="button" className="text-link" onClick={selectAll}>全文を選択</button>
      <a className="text-link" href="/songs.csv" download="xi-song-titles.csv">CSVをダウンロード</a>
    </div>
    <p className="song-list-status" role="status" aria-live="polite">{status}</p>
    <p className="song-list-help" id="song-list-help">コピーは曲名のみ、1行1曲です。CSVには「曲名」の見出しが付きます。</p>
    <details ref={panel} className="song-titles-panel" open>
      <summary>曲名一覧<span>1行1曲</span></summary>
      <label className="sr-only" htmlFor="song-titles">全{titles.length}件の曲名</label>
      <textarea ref={field} id="song-titles" aria-describedby="song-list-help" readOnly value={text} wrap="off" rows={18} spellCheck={false} />
    </details>
  </section>;
}
