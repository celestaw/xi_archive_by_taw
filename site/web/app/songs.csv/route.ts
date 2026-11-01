import { songTitlesCsv } from "@/lib/song-titles";

export const dynamic = "force-static";

export function GET() {
  return new Response(songTitlesCsv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": 'attachment; filename="xi-song-titles.csv"',
    },
  });
}
