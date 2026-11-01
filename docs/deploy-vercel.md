# Vercel公開手順

元のGit履歴を保持した `celestaw/xi_archive_by_taw` を使う。`dev` は開発、`alpha` は公開前確認、`main` は本番。以前のアプリ専用2ブランチとの無関係な履歴マージは行わない。

## 対象

- チーム: `celes-projects3` / `team_BLecCv5EMmUh0TKqV4Hb1jg0`
- 既存プロジェクト: `xi-archive` / `prj_Ajfn8lmocNvCSepnhJx3Aqnk1WCE`
- Root Directory: `site`
- 本番ブランチ: `main`。デプロイ時はレビューした完全なコミットSHAも確認する。
- Node.js 24系、Python 3.12。DBやアプリ用の秘密キーは不要。

`site/vercel.json` のServicesで `web`（Next.js）と `backend`（FastAPI）をビルドする。`/api/v1/*` は元のパスのままbackendへ、その他はwebへ渡す。Vercel上ではNext.jsのlocalhost向けrewriteを使わない。

公開JSONと型はコミット済みのものを使う。VercelのBuild Commandで `npm run contracts` を実行する必要はない。`xi_chronology/` の研究資料、保存Webページ、監査出力をサイト配信へ含めない。`.vercelignore` で依存物・仮想環境・ローカルビルド・テストを除外する。

## リリース前

`site/`で次を確認し、`alpha`の検証済み変更を`main`へ取り込む。

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v
npm run typecheck
npm run build
node scripts/check-timeline-layout.mjs
```

研究データを変更した場合は公開用本文・根拠・精度をレビューしてから `npm run contracts` で再生成する。GitHubに研究資料を含める判断と、APIが公開する項目の許可リストは別の境界である。

## 公開後

デプロイがREADY、targetがproduction、gitSourceが意図したmainのSHAであることを確認する。Git接続が未設定の場合、mainへのpushだけで自動デプロイされたとは扱わない。

```powershell
backend/.venv/Scripts/python.exe scripts/check_deployment.py https://実際の本番URL
```

このGET専用検査はAPI・全253曲・最新の年表イベント・CSVの表記と順序・読み方と解説・静的JS・研究資料への404を照合する。件数は実データから計算する。

ブラウザで検索、未確認日付の一致曲、連続ホバーと右端・下端のポップアップ、全曲／個別コピー、手動コピー代替、モバイル表示とreduced motionも確認する。動画の音声再生や地域制限を、このサイトのリンク検査だけで確認済みとはしない。

ログイン保護がある場合は、既存の正規認証で確認した範囲と、ログインなしで確認した範囲を区別する。公開のためのアクセス保護変更、新しい資格情報、課金は別の承認が必要。

公式資料: [Services](https://vercel.com/docs/services)、[Gitと本番ブランチ](https://vercel.com/docs/git)、[デプロイAPI](https://vercel.com/docs/rest-api/deployments/create-a-new-deployment)。
