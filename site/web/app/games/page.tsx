import type { Metadata } from "next";
import { CollectionIndex } from "@/components/CollectionIndex";

export const metadata: Metadata = { title: "音楽ゲーム" };

export default function GamesPage() {
  return <CollectionIndex key="game" kind="game" />;
}
