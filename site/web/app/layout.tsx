import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import { ThemeToggle } from "@/components/ThemeToggle";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "xi archive — 作品と公開の記録", template: "%s | xi archive" },
  description: "xiの作品と公開履歴をたどる非公式アーカイブ。公開記録の日付・公式試聴・出典をまとめています。調査途中の試作版です。",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja" data-scroll-behavior="smooth" suppressHydrationWarning>
      <body>
        <Script id="theme-init" strategy="beforeInteractive" dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <a className="skip-link" href="#main">本文へ移動</a>
        <header className="site-header">
          <div className="header-inner shell">
            <Link className="brand" href="/" aria-label="xi archive トップ">xi archive</Link>
            <nav aria-label="メインナビゲーション">
              <Link href="/#chronology">作品年表</Link>
              <Link href="/timeline">グラフ年表</Link>
              <Link href="/songs">全曲一覧</Link>
              <Link href="/albums">アルバム</Link>
              <Link href="/games">音楽ゲーム</Link>
              <Link href="/about">このサイトについて</Link>
            </nav>
            <ThemeToggle />
          </div>
        </header>
        {children}
        <footer className="site-footer shell">
          <Link className="footer-mark" href="/">xi archive</Link>
          <p>非公式・個人制作。xi本人・各権利者とは関係ありません。</p>
          <Link href="/about">調査・掲載の方針 <span aria-hidden="true">↗</span></Link>
        </footer>
      </body>
    </html>
  );
}
