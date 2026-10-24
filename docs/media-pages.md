# アルバム・ゲーム別の収録情報

既存の白・青とライト／ダーク、コンパクトな一覧を引き継ぐ。目的は収録先と楽曲の相互参照（Operate / Read）。ジャケット、ヒーロー、宣伝文は追加しない。

- `/albums`: ソロアルバムと参加作品の一覧。作品名で検索。
- `/albums/[id]`: 資料上の発売・頒布日、曲順、名義、公式試聴、曲別ページ、根拠。
- `/games`: 保存済みの一次資料で照合できたゲーム別の一覧。
- `/games/[id]`: ゲーム別の曲名・名義、曲別ページ、根拠。

FastAPIの`GET /api/v1/albums`・`/albums/{id}`・`/games`・`/games/{id}`を同一オリジンのrewrite経由で参照する。生成したOpenAPIからTypeScript型を共有する。読み込み、0件、API失敗、再試行、存在しない収録先を区別する。

## データ

`site/scripts/build_collections.py`が既存の公式アルバム曲目と曲別公開記録、帰属根拠、保存したSEGA曲別ページ、本人動画のゲーム名表記から生成する。

- `xi_chronology/data/media_collections.json`: 更新用の収録情報。
- `xi_chronology/data/media_collection_review.json`: 紐付け方法と保留事項。
- `site/backend/data/collections.json`: API用の公開データ。

公式曲順に基づく番号付きの既存記録を優先し、次に曲名とxiを含む名義の完全一致で曲別ページへ紐付ける。曖昧一致は使わない。ソロアルバムのゲストや他者によるリミックスも元の名義で残し、新規作曲として数えない。曲IDがない収録曲も削除しない。参加作品はxi関連の曲目に限定するため、アルバム全曲数ではなく掲載曲数を表示する。

ゲームの移植・追加収録を、曲自体の初公開日にしない。ゲーム収録日は今回の資料から確定せず、日付を補わない。`osu! Featured Artist`の許諾曲一覧と大会向け提供だけの記録は、通常のゲーム内収録と区別して保留する。表示は保存済み資料の確認範囲で、網羅性や現在の配信状況を断定しない。

既存の`catalogue.json`の作品・公開日・帰属・原曲と別版の関係は、このページ追加のために変更しない。

## 確認した範囲

- 初期データは39アルバム（ソロ6作品・参加33作品）、ゲーム10タイトル・32件の収録関係。作品自体の新規追加ではない。
- APIテスト20件とNext.js本番ビルド・TypeScriptチェック通過。OpenAPI再生成後も既存作品JSONのSHA256は不変。
- ブラウザーで一覧→詳細→曲別記録を確認。アルバム検索の0件・クリア、World Fragments三部作の別ID、ゲスト名義、出典の開閉を確認。
- 320px・390px・1280pxでページ全体の横はみ出しなし。ブラウザーの実行時エラーなし。確認はChromiumの幅変更で、実機iOS Safariの操作確認ではない。
- 同一オリジンのAPIでアルバム39件・ゲーム10件・Parousia 12曲・maimai 5曲を取得。存在しないアルバムのAPIとHTMLは404。
- ブラウザーの確認記録と画像は`docs/verification/xi-media-pages.json`と`xi-album-tracks.png`・`xi-games-index.png`・`xi-game-tracks.png`。

今回の実装は`feat/media-pages`で保存し、表示を確認してからdevへ取り込む。alpha・mainへの昇格と公開は行っていない。
