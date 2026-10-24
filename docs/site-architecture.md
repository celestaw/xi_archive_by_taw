# xi archive サイト構成案

更新日：2026-10-23。Next.js＋FastAPIによる画面と通信の初稿を`site/`に実装。Vercelへの登録・デプロイは未実施。

## 目的と位置づけ

xiの作品と公開履歴をたどる非公式アーカイブを、ポートフォリオとは独立したサイトとして制作する。ポートフォリオからリンクする。音楽への関心、調査の積み重ね、作品のつながりを見せることを中心に置く。

## 利用者から指定された方針

- 独立したサイトとして公開する。
- フロントエンドはTypeScriptを使う。
- バックエンドはFastAPIを使う。
- Node.jsを利用する。
- ホスティングはVercelを使う。
- 自分で管理するリバースプロキシは設けない。

FastAPIの実行環境はPythonになる。Node.jsはフロントエンドの開発・ビルド、およびフロントをNext.jsにした場合のサーバー実行で使う。FastAPIをNode.js上で動かす構成にはしない。

## 推奨する具体化

| 部分 | 構成案 | 役割 |
| --- | --- | --- |
| フロント | TypeScript + React + Next.js | 年表・検索・曲別ページ。曲別URLとメタデータを持たせる |
| フロント実行環境 | Node.js | 開発・ビルド、必要なサーバーレンダリング |
| API | Python + FastAPI | 公開用データの検証、曲・公開記録の検索、関連版の取得 |
| 公開 | Vercel Services | フロントとAPIを一つのVercelプロジェクトとしてデプロイ |
| URL振り分け | Vercelのrewrites | `/api/v1/*`をFastAPIへ、その他をフロントへ振り分け |
| 初期データ | 公開用JSON | 調査データから公開対象の項目だけを書き出す |

利用者の指定したTypeScript＋FastAPIを具体化し、初稿のフロントにはNext.jsを採用した。曲別URLと共有の入口を持たせるため。試作時点ではブラウザからAPIを取得し、検索エンジンのインデックスは無効化している。公開前のメタデータ・サーバー描画は次段階で見直す。

VercelはFastAPIをPython runtimeのVercel Functionsとして動かす。Servicesは確認日時点で全プラン向けBeta。フロントとバックエンドを同じ公開ドメインにまとめられ、Nginx等の別サーバーを管理する必要はない。

Servicesへの振り分けでは元のパスがバックエンドへ渡る。FastAPI側も`/api/v1`に対応させ、Next.js側のルートと区分する。

## 初期の画面案

1. トップ：アーカイブの趣旨と年代・作品への入口。
2. 年表：年代順の作品一覧。曲名検索、年・媒体・担当で絞り込む。
3. 曲別ページ：公開履歴、日付の意味、名義・担当、原曲と別版、公式試聴リンク、出典、短いコメント。
4. アルバム・媒体別一覧：収録と初出を区別して見られる入口。
5. About／調査方針：非公式アーカイブであること、日付・確度・出典の扱い、制作の動機。

技術構成の説明はAboutにまとめ、作品をたどる画面には楽曲情報と調査の根拠を置く。

## 調査データとの接続

`xi_chronology/`を調査の正本として保持する。元表記、判断履歴、保存したHTML、確認用スクリプトを、そのままサイトの公開APIや静的ファイルへ配信しない。

公開用データには曲ID・表題・別名・担当・公開記録・日付の種類と精度・出典URL・公式試聴先・コメント・確認状態を取り出す。曲IDは既存のXI-番号を引き継ぐ。

- 日付不明の曲を年表から消さず、日付未確認の一覧に残す。
- 年だけの記録に月日を補わない。
- 帰属未確認の候補は、確定したxi作品と区別して表示する。
- World FragmentsのアルバムとI・II・IIIの3曲を区別する。
- Storm and Impulseは疾風怒濤の英語タイトルとして扱う。
- 作曲、合作、xiによる編曲、他者によるxi曲の編曲、ロング版等の関係を保つ。
- 公開履歴の最古の確認日を、真の初公開日や作曲日へ読み替えない。

初期はJSON更新と再デプロイで運用する案とする。公開サイトでの編集・ログイン・投稿機能は初期要件に含めない。データベースは更新頻度や編集方法が必要になった時点で検討する。

静的ページ生成を使う場合は、ビルド時にも公開用JSONを使う。Vercelのservice bindingは実行時向けで、ビルド時にバックエンドを呼ぶ前提にはしない。

## 想定する配置

```text
xi archive/
  xi_chronology/          調査データ・原稿・出典・判断履歴
  docs/                  方針と設計
  site/                  Vercelのプロジェクトルート候補
    web/                 TypeScript / Next.js
    backend/             Python / FastAPI
      data/              配布用の公開データ
    scripts/             調査データからの公開用書き出し
    vercel.json          サービス定義とURL振り分け
```

`site/`配下に初稿を実装済み。公開用JSONの書き出し、FastAPI、OpenAPIからのTypeScript型生成、年表・検索・曲別ページ・Aboutを含む。通信の正本は`site/backend/models.py`で、詳しい契約は`docs/api-contract.md`に記録する。ポートフォリオ側へは公開URLができた段階でリンクを設ける。

## ポートフォリオからの導線

xiアーカイブとは別に、既存のB:ABLEにも紹介カードから誘導する。B:ABLEは公開済みのタスク管理アプリで、タスクを完了するとブロックを獲得し、塔を建てられる。

- 公開先：<https://bable-blond.vercel.app>
- ポートフォリオ実装：`C:/Users/matha/Documents/ChatGPT/セキュリティ更新/portfolio/`
- `data/projects.ts`に紹介文と公開URLを保持し、`WorkCard`の`externalLink`で直接開く。
- B:ABLEの紹介カードを実装済み。xiアーカイブの紹介カードは、サイトと公開URLができた段階で追加する。
- この記録はローカル実装の記録であり、ポートフォリオ本番への反映を示さない。

## 確認した公式資料

- [Vercel Services](https://vercel.com/docs/services)：複数ランタイムの構成、Betaでの提供、サービスへの振り分け。
- [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi)：Python runtimeとフロントの併設。
- [Service routing](https://vercel.com/docs/services/routing)：公開パスの振り分け。
- [Service bindings](https://vercel.com/docs/services/bindings)：実行時のサービス間通信。実装時に詳細を再確認する。
