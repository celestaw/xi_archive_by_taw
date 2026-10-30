import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "このサイトについて" };

export default function AboutPage() {
  return (
    <main id="main" className="shell prose-page">
      <section aria-labelledby="about-position">
        <h1 id="about-position" className="about-heading">このサイトの立場</h1>
        <p>xi本人、レーベル、ゲーム運営、その他の権利者とは関係のない個人制作の非公式サイトです。曲名や作品の権利はそれぞれの権利者に帰属します。</p>
        <p>原曲、ロング版、ゲームサイズ、リマスター、再収録は関連付けて扱います。合作や編曲は担当を区別し、他者によるxi楽曲のアレンジを、xiの新規作曲として数えません。</p>
      </section>
      <Link className="text-link" href="/#chronology">作品年表へ戻る ↗</Link>
    </main>
  );
}
