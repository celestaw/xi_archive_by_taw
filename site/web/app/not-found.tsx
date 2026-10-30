import Link from "next/link";

export default function NotFound() {
  return <main id="main" className="shell collection-page empty-state">
    <h1>ページが見つかりません。</h1>
    <p>URLを確認するか、一覧から探してください。</p>
    <Link className="text-link" href="/">作品年表</Link>
    <Link className="text-link" href="/albums">アルバム</Link>
    <Link className="text-link" href="/games">音楽ゲーム</Link>
  </main>;
}
