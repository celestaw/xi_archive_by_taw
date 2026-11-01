# xi archive

作曲家xiの作品と公開履歴をたどる非公式アーカイブ。調査データ・掲載原稿と、公開サイトの実装を分けて管理する。

- `xi_chronology/`：調査データ、原稿、保存した一次資料、照合・判断履歴。
- `site/`：TypeScript / Next.js＋Python / FastAPIによるサイト初稿。[起動とチェック](site/README.md)。
- `docs/visual-direction.md`：見た目の方向。
- `docs/api-contract.md`：通信契約と日付・帰属などの意味。
- `docs/implementation-status.md`：実装と確認の記録、次の作業。

GitFlowは `dev`（開発）→ `alpha`（公開前確認）→ `main`（本番公開）。元の初期コミットからの履歴とブランチを保持する。以前のアプリ用スナップショットは `initial/xi-archive` と `prep/vercel-hosting` に残している。

Vercelでは `site/` だけをビルドする。調査ページの保存内容をサイトへ配信しない。設定と公開後の確認手順は [デプロイ手順](docs/deploy-vercel.md) を参照。
