# はじめてのVercel公開

この手順は、公開用アプリだけを保存した `celestaw/xi_archive_by_taw` 用です。研究用フォルダーをVercelへ追加する必要はありません。画面はNext.js、APIはFastAPIで、同じサイトのURLから利用します。DBや秘密のAPIキーは現在の機能には不要です。

このガイドを準備した時点では、GitHubの既定ブランチは `initial/xi-archive`、SHAは `b38a01c` です。mainはまだありません。公開準備の追加変更はローカルの `prep/vercel-hosting` にあり、まだGitHubへ送っていません。

## 公開先を決める

先に、利用するVercelアカウント／チーム名と、本番にするブランチを決めます。mainでリリースを管理する場合は、利用者がmainの作成・変更の取り込みを決めてから進めます。現在の既定ブランチを、そのまま本番ブランチと扱う必要はありません。

Vercelのプロジェクト作成や最初のDeployは、ここではまだ実施していません。利用するアカウントが決まるまで、新しいプロジェクト、GitHub認証、契約を作りません。

## Importで設定する値

Vercelの「Add New → Project」で、決めたアカウント／チームとGitHubリポジトリを選びます。GitHubへのアクセス承認が表示されたら、許可する対象を確認して利用者が操作します。

| 項目 | 設定 |
| --- | --- |
| Git Repository | `celestaw/xi_archive_by_taw` |
| Root Directory | **`site`** |
| Production Branch | 利用者が決めたブランチ。mainで管理するならmainを用意した後に指定 |
| Node.js | 24系。各package.jsonでも指定済み |
| Python | backendの `.python-version` は3.12 |
| Framework・Build | `site/vercel.json` のServices設定を使用 |
| Output Directory | 自動設定のまま |
| Environment Variables | アプリ用の追加設定は不要 |

Root Directoryを `site/web` にすると、FastAPIと同梱データが対象外になるため、`site` を指定します。トップレベルのBuild Commandに `npm run contracts` を指定する必要はありません。公開JSON・OpenAPI・型はリポジトリに同梱されています。

ServicesはBetaです。webは `web/` のNext.jsとして、backendは `backend/main.py` の `app` として別々にビルドされ、同じデプロイになります。UIでサービス設定を確認できる場合は、この2つが対象になっていることを確認します。Build Commandなどを上書きする場合も、トップレベルへ混ぜず対象のサービスに設定します。

最初のImport時のDeployも本番になることがあります。実行前に、対象アカウントとProduction Branchが意図どおりか確認します。自分でマージを管理したい場合、mainへ取り込む判断まで自動で行う必要はありません。

## APIの配線

`https://サイトのURL/api/v1/...` はFastAPIへ、その他はNext.jsへ渡します。たとえば `/api/v1/works` はFastAPIにも同じパスで届きます。

追加のAPIホスト名・CORS全許可・APIキーは使いません。ローカル用の `XI_BACKEND_ORIGIN` に `127.0.0.1` を入れた値をVercelへ設定しないでください。Vercelではローカル用Next rewriteが外れ、Services側の配線を使います。

## Buildが終わったら

Build Logsでwebとbackendの両方が成功したこと、Nodeが24系・Pythonが3.12系であることを確認します。Pythonは依存関係の解決結果も確認します。ローカルは固定したrequirementsの環境で検証済みですが、Vercel上の解決・パッケージ同梱は初回Previewでの確認が必要です。

生成されたURLで、まず次を開きます。

1. `/api/v1/health`：`status` が `ok`。
2. `/songs`：「全曲一覧」が全253件で表示される。
3. `/songs.csv`：曲名1列のCSVがダウンロードできる。
4. `/works/XI-025`：.357 Magnumの解説が表示される。

CLIでまとめて確認する場合は、`site/` で次を実行します。

```powershell
python scripts/check_deployment.py https://実際のサイトURL
```

このコマンドはGETだけを使い、API・年表・全曲一覧のHTML・CSV・読み方と解説・静的JS・非公開パスの404を照合します。URLにはページパス、認証情報、クエリを付けず、サイトの先頭だけを渡します。Previewがログインで保護されて401になる場合は、保護を解除したりトークンを作ったりせず、所有者の通常のアクセスで確認します。

コピー操作そのものとモーションはHTTP検査だけでは確認できません。公開URLで個別コピー・全曲コピー・手動選択・スマートフォン幅・「動きを減らす」設定を一度確認します。既存のローカルブラウザ検査は通過していますが、Vercel上とSafari/iOS実機は未確認です。

## よくある見え方

| 症状 | 確認する場所 |
| --- | --- |
| 画面は出るが曲が読めない | `/api/v1/health` とbackendのログ。Root Directoryが `site` か |
| APIが404 | ServicesのAPI向けrewriteが、web向けcatch-allより前か。FastAPIへ元のパスが届いているか |
| `/songs` は出るが他の一覧が失敗 | 静的な全曲一覧だけではAPIの成功を判定しない。APIのhealthも確認 |
| CSVの曲数が違う | 古いデプロイや別のブランチでないか。確認コマンドの照合結果を見る |
| Python依存のインストールが失敗 | backendのBuild LogsとPythonの版。別の有料サービスやDBを追加する前に原因を読む |

現在は検索エンジンのindexを無効にしています。公開URLから使うことはできます。indexの変更、独自ドメイン購入、有料プランへの変更は、この公開準備には含めていません。

公式資料：[Services](https://vercel.com/docs/services)、[Service設定](https://vercel.com/docs/services/config-reference)、[Node.js](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions)、[Python](https://vercel.com/docs/functions/runtimes/python)。
