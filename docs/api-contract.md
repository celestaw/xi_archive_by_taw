# xi archive API v1

正本はFastAPIのPydanticモデル（`site/backend/models.py`）。OpenAPIは`site/contracts/openapi.json`、生成されたTypeScript型は`site/web/lib/schema.d.ts`。双方を手で二重管理しない。

## 通信経路

ブラウザ → 同一オリジンの`/api/v1/*` → FastAPI → 公開用JSON → 型付きJSONレスポンス → 画面。

- 開発時：Next.jsのrewritesがローカルFastAPIへ転送する。既定はフロント3000番・API8000番。`PORT`と`XI_API_PORT`で変更できる。
- Vercel：Servicesのトップレベルrewriteで`/api/v1/*`をbackendサービスへ、残りをwebサービスへ送る。ServicesはBeta。設定は準備済み、本番未検証。
- API側は`/api/v1`を含むパスを受け取る。パスの自動除去は想定しない。
- ブラウザはバックエンドのホスト名・ポートを直接参照しない。公開APIキーやCORSの全許可は不要。
- 現段階は読み取り専用。ログイン・書き込み・DB・音源ホスティングなし。

## エンドポイント

| メソッド・パス | 内容 |
| --- | --- |
| `GET /api/v1/health` | `{status: "ok", api_version: "v1"}` |
| `GET /api/v1/meta` | 件数、年・媒体の選択肢、調査確認日、日付の注意書き |
| `GET /api/v1/works` | 作品・別版・候補の一覧と総件数、ページ情報 |
| `GET /api/v1/works/{id}` | 公開履歴、制作記録、公式試聴、別名、関連する版、未確認事項 |
| `GET /api/v1/openapi.json` | 機械可読の通信契約 |
| `GET /api/v1/docs` | Swagger UI |

一覧のクエリはすべて任意。AND条件で組み合わせる。

| パラメーター | 意味 |
| --- | --- |
| `q` | 曲名・別名の部分一致。NFKC正規化と大文字小文字の同一視。最大120文字 |
| `year` | 最古の確認済み公開記録の年。1900〜2100の整数 |
| `date_status` | `all`（既定）、`dated`、`undated` |
| `attribution` | `all`（既定）、`credited`（一次資料のクレジットあり）、`unverified`（帰属未確認） |
| `medium` | 公開履歴中の媒体名との完全一致。候補はmetaで取得 |
| `limit` | 1〜100、既定40 |
| `offset` | 0〜100000、既定0 |

並び順は最古の確認記録の日付、同日の場合は作品ID。日付不明は後ろ。年だけの記録に便宜上の月日を足さない。同一年の中で精度が違う記録の厳密な前後関係までは確定しない。一覧の総件数は絞り込み後・ページング前の数。媒体の絞り込みは後年の収録記録も対象にするが、年は最古の確認記録を指す。

## データの意味

- `id`：調査データから引き継ぐXI-番号。曲名から生成し直さない。
- `earliest_record`：確認できた最も早い公開記録。不明ならnull。真の初公開とは限らない。
- `date`：`YYYY`、`YYYY-MM`、`YYYY-MM-DD`またはnull。`precision`は`year`、`month`、`day`またはnull。モデルで組を検証。
- `kind`：muzie登録、BMSイベント登録、アルバム発売、ゲーム収録などの日付の種類。
- `records`：公開・収録記録。日付のない公式クレジットも含む。
- `creation_records`：作曲年・リマスター年などの制作記録。公開履歴とは分け、年表の並べ替えには使用しない。
- `true_first_publication_confirmed`：その記録を真の初公開として確認したか。未確認ならfalse。
- `attribution: credited`：一次資料にクレジットがある意味。全制作工程や初出日の確定ではない。
- `attribution_basis`（詳細）：掲載に至った入力資料、帰属判断の要約、曲別の根拠資料、資料中の名義と該当箇所、本人との照合説明、確認日、未解決点。`sources[].kind`は`primary`（一次資料）、`secondary`（二次資料）、`lead`（未検証の調査先）。入力資料は`inclusion`に分け、入力だけでは一次確認に昇格させない。`reviewed_on`は整理日で、各資料の再取得日ではない。
- `is_variant`：原曲に関連付けた別版か。別版もIDを保持するが新規作曲数として数えない。原曲側からも関連版へ移動できる。
- `aliases[].evidence_status`：利用者補足など、外部一次資料で未検証の別名の根拠を保持。
- `listening`：公式性の根拠を持つリンクのみ。対象の版、確認範囲と公式性の出典も保持。試聴不可は空配列で示す。
- `total_entries`等：作品・別版・候補の件数であり、独立した新規作曲の総数ではない。

元Excelの行、照合用の原文、ローカルパス、候補URL、保存HTMLは公開JSONに含めない。`export_public.py`で許可したフィールドだけを書き出す。

## エラーと画面の状態

エラー形式：`{"error":{"code":"not_found","message":"該当する作品の記録がありません。"}}`

- 404：存在しない作品ID。`not_found`。
- 422：不正なクエリ値。`invalid_request`。
- 500：API内の予期しない例外。`internal_error`。詳細はサーバーログに残し、レスポンスに内部例外を出さない。
- 0件：200で`items: []`、`total: 0`。通信失敗とは区別する。
- 読み込み中：古い検索結果を新しい条件の結果として見せない。
- 通信失敗：内容を捏造するフォールバックなし。エラーと再読み込み操作を表示。
- 条件変更や画面移動：古いリクエストをAbortControllerで取り消す。
- 接続待ちは10秒で打ち切り、再読み込み操作を表示する。自動で繰り返し送信しない。

一覧は40件ずつ取得する無限スクロール。末尾の300px手前で次のoffsetを取得し、同じ年の見出しに追加する。URLのoffsetによる画面のページ送りは使わず、条件変更時はoffset=0から読み直す。同時追加取得と古い条件の応答混入を防ぎ、作品IDの重複を除く。追加取得の失敗時は既存の一覧を残し、その場の再試行ボタンで再開する。キーボード操作やIntersectionObserver非対応環境でも「続きを読み込む」で追加可能。全件取得後は追加取得を終了する。

## 更新と契約の検証

`site/`で`npm run contracts`を実行すると、公開JSON→OpenAPI→TypeScript型を順に再生成する。モデル変更後は必ず生成し直し、APIテスト・型チェック・ビルドを通す。契約の破壊的変更は`v2`へ分ける。現時点のv1は試作段階。

APIテストは公開／制作の区別、日付精度、別名検索、未確認項目の保持、ページング、エラー形式、内部情報の除外、OpenAPIスナップショットを確認する。

2026-10-24追記：全251項目の帰属根拠を`xi_chronology/scripts/review_attribution.py`で整理し、JSON・CSV・Markdownを保存。APIの帰属判定はそのレビューを採用する。旧`works.json`の判定は履歴として保持し、変更理由を`attribution_overrides.json`に記録。Xiphoid Sphereとxi本人の関係が未確認のXI-049を保留へ戻し、現時点は一次クレジット135項目・帰属未確認116項目。Giudizio Universaleの利用者提示動画は第三者投稿の二次資料として保持し、日付確定や公式試聴への昇格はしない。
