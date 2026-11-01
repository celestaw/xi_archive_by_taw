import type { Metadata } from "next";
import { CollectionRecord } from "@/components/CollectionRecord";
import { notFound } from "next/navigation";
import ids from "@/lib/collection-ids.json";

export const metadata: Metadata = { title: "アルバム収録曲" };

export default async function AlbumPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!ids.albums.includes(id)) notFound();
  return <CollectionRecord key={`album:${id}`} kind="album" id={id} />;
}
