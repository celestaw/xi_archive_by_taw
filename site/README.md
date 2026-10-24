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

## Vercel

`site/`をプロジェクトルートとして扱う設定案を`vercel.json`に置いている。Services（Beta）でwebとbackendを同時に公開し、`/api/v1/*`をFastAPIへ振り分ける。Node.jsは24系、Pythonは3.12以上。ホスティングへの登録・デプロイ・Services上での検証はまだ行っていない。

開発時のNext.js rewriteは`VERCEL`環境では無効になる。公開JSONと生成した型はコミット対象で、Vercelのビルド時に生の調査資料や起動済みFastAPIへ依存しない。

試作中のため`robots: noindex, nofollow`。公開時はデータと文言を確認した上で変更する。
