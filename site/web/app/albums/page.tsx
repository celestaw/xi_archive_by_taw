import type { Metadata } from "next";
import { CollectionIndex } from "@/components/CollectionIndex";

export const metadata: Metadata = { title: "アルバム" };

export default function AlbumsPage() {
  return <CollectionIndex key="album" kind="album" />;
}
