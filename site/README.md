# xi archive site

TypeScript / Next.jsとPython / FastAPIによる非公式年表の試作。調査データは親フォルダーの`xi_chronology/`に保持し、このアプリは許可したフィールドだけを公開JSONへ書き出して読む。

## 初回準備

Node.js 24.22.1以上の24系、Python 3.12以上を利用する。`site/`で実行する。

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-lock.txt
npm ci
npm run contracts
npm run dev
```

macOS/LinuxはPythonのパスを`backend/.venv/bin/python`に読み替える。Pythonを別の場所に置く場合は環境変数`XI_PYTHON`で指定できる。

フロント：<http://127.0.0.1:3000>。API：<http://127.0.0.1:8000/api/v1/docs>。`npm run dev`は両プロセスを起動し、終了時に停止する。APIの変更後はこのコマンドを再起動する。`PORT`、`XI_API_PORT`でポートを変更できる。

## チェック

```powershell
npm run contracts
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v
npm run typecheck
npm run build
```

OpenAPIは`contracts/openapi.json`、TypeScript型は`web/lib/schema.d.ts`に生成する。契約の詳細は`../docs/api-contract.md`、見た目の意図は`../docs/visual-direction.md`を参照。

## 収録先から探す

曲別ページは「日付 → 収録アルバム → 収録ゲーム → 経緯 → これをもとにリミックスされた曲 → 補足コメント」の順で表示する。経緯には公開・制作記録、別名、関連する版、公式試聴をまとめる。収録先は`GET /api/v1/works/{work_id}/context`で既存の曲IDと完全一致するものを取得し、追加告知・収録候補などの状態を保持する。他者によるリミックスは原曲から派生した方向だけを掲載し、ロング版やリマスターとは区別する。

内部の掲載経緯・帰属判断メモ・issuesは公開APIのモデルと生成JSONから除外する。開発／本番の表示条件には依存しない。元資料・履歴は親の調査フォルダーへ保持する。曲名・名義の公開出典は、一次／二次資料の区別・URL・資料の名義・確認日のみに絞って詳細から開ける。

公開用の解説は `../xi_chronology/data/public_annotations.json`、収録情報の説明文は `public_collection_annotations.json` へ明示的に登録する。元の調査コメントや承認履歴は自動で公開しない。曲や曲目を追加した際は対応する公開用説明をレビューし、`npm run contracts` で公開JSONと型を更新する。未知のフィールド・非公開のパスや資格情報形式は公開スキーマが拒否する。

`/timeline`は独立した「グラフ年表」タブ。プレビューを白抜き、本公開を塗りつぶした点で示し、確認できた前後関係のあるペアだけを点線で結ぶ。点にホバー、フォーカス、タップすると曲名・日付・出典・作品詳細へのリンクを表示する。検索、プレビューのある曲の絞り込み、年・月単位への拡大に対応。日付未確認の作品はグラフ下の一覧から参照できる。

グラフの配置確認は`node scripts/check-timeline-layout.mjs`、公開段階の分類確認はバックエンドの`tests/test_timeline.py`で行う。

`/albums`はアルバム別、`/games`は音楽ゲーム別の収録情報。各一覧から曲順・名義・根拠を持つ詳細ページへ進める。生成元と確認範囲は`../docs/media-pages.md`を参照する。

上部の「全曲一覧」（`/songs`）では公開用台帳の全収録曲を登録順・1行1曲で表示し、全文の選択、曲名だけの一括コピー、曲名1列のCSVダウンロード（`/songs.csv`、UTF-8 BOM付き）に対応する。検索・年・媒体の絞り込みと一覧のページングには依存しない。別バージョンや未確認候補を統合・除外しない。

作品年表、曲の詳細、アルバム・ゲームの曲目、グラフ年表は共通の曲名コピーボタンを使う。コピーするのは表示どおりの原題のみ。自動コピーが許可されない場合も手動選択へ進め、成功通知による一覧の移動を避ける。モーションは短い色・不透明度の切替に限り、`prefers-reduced-motion`を尊重する。

読み方は`../xi_chronology/data/work_pronunciations.json`から任意の詳細フィールドへ書き出し、値のある曲だけ作者の提案・確定指定を区別して出典と日付を表示する。表示用の読み方を曲名コピーやCSVへ混ぜない。

`npm run contracts`は作品データに加えて`build_collections.py`による収録情報とページIDを生成し、OpenAPI・TypeScript型を更新する。公開用のJSONとIDもコミットするため、ビルド環境に調査用資料をコピーする必要はない。

## Vercel

`site/`をプロジェクトルートとして扱う設定を`vercel.json`に置いている。Services（Beta）でwebとbackendを同時に公開し、`/api/v1/*`をFastAPIへ振り分ける。Node.jsは24系、Pythonは3.12。本番のソースは`main`、公開前確認は`alpha`。設定と検証は`../docs/deploy-vercel.md`を参照する。

開発時のNext.js rewriteは`VERCEL`環境では無効になる。公開JSONと生成した型はコミット対象で、Vercelのビルド時に生の調査資料や起動済みFastAPIへ依存しない。

試作中のため`robots: noindex, nofollow`。公開時はデータと文言を確認した上で変更する。
