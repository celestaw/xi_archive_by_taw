import type { Metadata } from "next";
import { SongTitleList } from "@/components/SongTitleList";
import { songTitles } from "@/lib/song-titles";

export const metadata: Metadata = { title: "全曲一覧" };

export default function SongsPage() {
  return <main id="main" className="shell collection-page song-list-page">
    <h1>全曲一覧</h1>
    <p className="collection-notice">アーカイブに登録している全{songTitles.length}件。別バージョン・調査中の候補も含め、登録順で掲載しています。</p>
    <SongTitleList titles={songTitles} />
  </main>;
}
