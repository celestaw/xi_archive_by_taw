import { Suspense } from "react";
import { ArchiveExplorer } from "@/components/ArchiveExplorer";

export default function HomePage() {
  return (
    <main id="main" className="shell">
      <Suspense fallback={<p className="loading-copy" role="status">作品の記録を読み込んでいます…</p>}><ArchiveExplorer /></Suspense>
    </main>
  );
}
