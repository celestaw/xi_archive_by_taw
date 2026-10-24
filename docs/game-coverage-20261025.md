# 音楽ゲーム収録情報の追加照合（2026-10-25）

この文書は20一覧・101件へ拡張した前段階の記録。最新の曲別照合は[123行の照合記録](game-song-audit-20261025.md)を参照。

10項目32件だったゲーム別一覧を20項目101件に拡張した。内訳は通常収録45件、BMS登録14件、公式許諾曲40件、追加告知1件、大会向け提供1件。同じ曲の複数媒体への登場を含む延べ件数で、新規楽曲数ではない。アルバムは39作品を維持した。

## 今回反映した範囲

|一覧|掲載数|根拠と留保|
|---|---:|---|
|BMS|14|既存のイベント登録一次資料。FREEDOM DiVE↓はイベント登録2008-03-21とmuzie登録2008-03-19を区別。|
|osu!|40|[運営のFeatured Artistページ](https://osu.ppy.sh/beatmaps/artists/727)と保存済み曲目。公式許諾音源の一覧で、標準搭載譜面ではない。|
|MUSIC DIVER|4|[公式サイトから案内される公開曲目](https://mypage.musicdiver.jp/api/music?lang=ja)。FREEDOM DiVE↓、Halcyon、Qualia Crystal、Solar Storm。|
|Cytus|2|[Rayark試聴一覧](https://rayark.com/g/cytus/mobile/pv.html)のHalcyon、[日本公式M-MILLION案内](https://cytusjapan.com/music/)のStoria。後者はxi vs sakuzyo。ほかの曲は下表へ保留。|
|Cytus II|1|[開発元提供App Store更新履歴](https://apps.apple.com/jp/app/cytus-ii/id1290687550)のMESSiΛH COMPL3X / xi。初代とは分離。対象のxi本人への直接リンク照合は曲別記録で継続。|
|クロノサークル|1|[CHRONO CIRCLE公式BGA](https://www.youtube.com/watch?v=qZm9hZgEqWk)のMEGALØDON、Composer: xi。対象本人への直接リンク照合は未完了のため曲別帰属は保留を維持。|
|Arcaea|1|[Nintendo公式Esoteric Order Pack](https://www.nintendo.com/us/store/products/esoteric-order-pack-70050000030010-switch/)のOverwhelm。Switch版の根拠で、モバイル版やLong Versionへ外挿しない。|
|グルーヴコースター（アプリ版）|3|[公式曲目](https://groovecoaster.com/apps/music.html)のHalcyon、Valhalla、Solar Storm。AC表記はアプリのアーケードモード対応で、筐体版収録とは読み替えない。|
|グルーヴコースター ワイワイパーティー!!!!|1|[公式DLC案内](https://groovecoaster.com/switch/dlc.html)のオリジナル パック8：Solar Storm。版ごとに別ページ。|
|プロジェクトセカイ|2|[セガ発表](https://prtimes.jp/main/html/rd/p/000007397.000005397.html)のANiMA追加告知、[xi本人MV](https://www.youtube.com/watch?v=VNK8leVFy-g)のULTIM@TE☆BE∀M!!大会向け提供。通常配信の実施日は未確定。|

MUSIC DIVERの同一artist_id=51に既知のFREEDOM DiVE↓・Halcyonと新たな2曲を確認。さらに[Qualia Crystalのタイトー紹介動画](https://www.youtube.com/watch?v=_02OtxIa0xM)はxi Officialへリンクする。この照合をQualia Crystal・Solar Stormの曲別帰属根拠にも追記した。Qualia Crystalの動画公開日時は2025-04-26T20:00:38-07:00、日本時間2025-04-27。真の初公開日とはしない。

### 採用しなかった日付・探索先

- MUSIC DIVERのAPIにある`deliver_start_date=2021-01-01`等の内部値は初収録日に不採用。取得時の値は保存原文で追跡可能。
- プロセカのANiMAは一次発表では2026-06-25追加予定。2026-06-23は同発表のSaika。二次表の段組みや検索要約から取り違えない。今回は追加告知として掲載し、予定通り実装された日を示す一次発表を引き続き探す。
- プロセカ公式の楽曲表示用JSONは取得時65曲で、ANiMA等がない。欠落を非収録の根拠にしない。
- クロノサークル公式曲目ページはSSOへのリダイレクトで取得できなかった。取得失敗を保存し、検索要約だけでは曲目を確定しない。
- Arcaeaの探索で見つけたYouTube `ALbxibB7X0Q`は個人プレイ動画。公式試聴・一次根拠には不採用。
- MUSIC DIVERの表示用bundle.jsは取得上限5MBに達した部分保存（`read_limit_reached=true`）。楽曲判定には別途取得した全257件の公開API応答を使用した。
- CD特典・アルバム版・リミックスの存在だけでは、そのゲームへの収録を確定しない。

## 保留13件と次に当たる資料

|対象|未照合の曲|次の資料|
|---|---|---|
|Cytus|Parousia、Zauberkugel、Niflheimr、REVOLUXIONIST|提供noteの元表記を保持。Rayark公式の曲紹介・更新告知、当時の保存版。CD店別特典のみでは収録確定しない。|
|Arcaea|Halcyon、Tiferet、Dreadnought、World Fragments III(radio edit)、Parallax|Wikiを探索用に、lowiroの曲別告知・公式パック紹介へ遡る。radio editとアルバム版、合作名義を個別に確認。|
|クロノサークル|Aragami、FREEDOM DiVE↓、Halcyon、Qualia Crystal|公式曲目ページの保存版、Andamiroの更新告知・公式動画。二次資料のリストを確定情報に昇格しない。|

元リストには太鼓の達人、DEEMO、SEVENS CODE、Crossbeats、Paradigm: Reboot、ノスタルジア等もある。今回挙げられた範囲以外も調査対象から外していない。既存ページのSDVX、CHUNITHM等も全曲照合済みではない。

## 保存・再生成

- `xi_chronology/data/game_research.json`：一次根拠、元表記、名義・担当、版、確認日、保留候補、採否の留保。
- `xi_chronology/scripts/research_game_coverage.py`：保存した一次資料と今回の照合判断から上記JSONを再生成。新しい曲名は無条件に取り込まず停止する。
- `xi_chronology/data/research_additions.json`：曲別記録への追加根拠。原資料は変更しない。
- `xi_chronology/sources/game-coverage-20261025/`：取得原文・テキスト・URL・SHA256・取得成否。JSやJSONも取得した原文を保持。
- `site/scripts/generate-contracts.mjs`：公開用データとOpenAPI・TypeScript型を再生成。`listing_kind`と`edition`はAPIを通して表示する。
- `docs/verification/xi-game-coverage.json`：実際に動くプレビュー・API・ブラウザーの確認記録。

追加後はAPIテスト22件、本番ビルド・TypeScriptチェックを実施。feat/media-pagesで保存し、devへの取り込みは表示確認後とする。
