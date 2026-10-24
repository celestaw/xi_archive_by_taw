import Link from "next/link";
import { WorkRecord } from "@/components/WorkRecord";

export default async function WorkPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <main id="main" className="shell"><Link className="back-link" href="/#chronology">← 作品年表へ</Link><WorkRecord id={id} /></main>;
}
