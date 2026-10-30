import type { Metadata } from "next";
import { CollectionRecord } from "@/components/CollectionRecord";
import { notFound } from "next/navigation";
import ids from "@/lib/collection-ids.json";

export const metadata: Metadata = { title: "ゲーム収録曲" };

export default async function GamePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!ids.games.includes(id)) notFound();
  return <CollectionRecord key={`game:${id}`} kind="game" id={id} />;
}
