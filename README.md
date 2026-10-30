# xi archive

初回公開の設定と確認手順は [はじめてのVercel公開](docs/deploy-vercel.md) にまとめています。

xiの作品と公開履歴をたどる非公式アーカイブ。Next.js / TypeScriptとFastAPIによる読み取り専用サイトです。曲名一覧253件、個別・一括コピー、CSV、出典と読み方を含みます。帰属未確認の候補・別バージョンも保持しています。

## ローカル実行

Node.js 24.22.1以上の24系、Python 3.12以上を使い、`site/` で実行します。

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-lock.txt
npm ci
npm run dev
```

macOS/LinuxのPythonは `backend/.venv/bin/python`。既定URLは http://127.0.0.1:3000 、APIは8000番です。`PORT` と `XI_API_PORT` で変更できます。

## 検証

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v
npm run contracts
npm run typecheck
npm run build
```

`npm run contracts` は同梱の公開用JSONを使ってOpenAPIとTypeScript型だけを生成します。元の研究資料や収集スクリプトはこの配布用プロジェクトに含めません。新しい調査結果は別管理の正本でレビューして公開用JSONへ書き出してから同期します。研究専用の3検査を分け、配布用プロジェクトでは52テストを実行します。

## データと公開

`site/backend/data/catalogue.json` と `collections.json` は公開専用データです。内部メモ・入力履歴・人物照合過程は含めません。公開モデルは未知のフィールドや既知の私的情報形式を拒否します。自由記述の更新は公開用本文としてレビューしてください。

上部の「全曲一覧」(`/songs`) から1行1曲の全文をコピーでき、`/songs.csv` でUTF-8 BOM付きCSVを取得できます。曲のコピーには読み方を混ぜません。

VercelのRoot Directoryを `site` とし、`site/vercel.json` のServicesでNext.jsとFastAPIを同時に扱います。ServicesはBetaです。公開先への接続と実環境確認は別途必要で、リポジトリへの保存だけでサイトが公開されるわけではありません。現在の機能にDBや秘密のAPIキーは必要ありません。
