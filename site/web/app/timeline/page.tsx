import type { Metadata } from "next";
import { TimelineExplorer } from "@/components/TimelineExplorer";

export const metadata: Metadata = { title: "グラフ年表" };

export default function TimelinePage() {
  return <main id="main" className="shell timeline-shell"><TimelineExplorer /></main>;
}
