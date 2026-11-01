import type { RecordDate, TimelineEntry } from "./api";

export type Stage = "preview" | "release" | "reference";
export type TimelinePoint = { entry: TimelineEntry; record: RecordDate | null; date: string; x: number; y: number; filled: boolean; current: boolean };
export type TimelineRow = { entry: TimelineEntry; firstRecord: RecordDate; y: number; startX: number; endX: number; canListen: boolean };
export type TimelineSegment = { entryId: string; kind: "pending" | "public"; start: TimelinePoint; end: TimelinePoint };
export type TimelineLayout = {
  width: number; height: number; years: number[]; yearWidth: number; nowX: number;
  rows: TimelineRow[]; points: TimelinePoint[]; connections: TimelineSegment[];
};

export const PLOT_PADDING = 32;
export const ROW_HEIGHT = 16;
const STAGES: Stage[] = ["preview", "release", "reference"];

export function firstPublicRecord(entry: TimelineEntry): RecordDate | null {
  return STAGES.map(stage => entry[stage]).filter((record): record is RecordDate => !!record?.date)
    .sort((a, b) => a.date!.localeCompare(b.date!) || a.id.localeCompare(b.id))[0] ?? null;
}

// Partial dates occupy the middle of their known interval, never an invented
// January 1 / first-of-month date.
export function datePosition(record: RecordDate): number {
  const [year, month, day] = record.date!.split("-").map(Number);
  if (!month) return year + .5;
  const start = Date.UTC(year, 0, 1);
  const end = Date.UTC(year + 1, 0, 1);
  const time = day ? Date.UTC(year, month - 1, day) : (Date.UTC(year, month - 1, 1) + Date.UTC(year, month, 1)) / 2;
  return year + (time - start) / (end - start);
}

export function dateRange(record: RecordDate): [number, number] {
  const [year, month] = record.date!.split("-").map(Number);
  if (record.precision === "year") return [year, year + 1];
  if (record.precision === "month") {
    const start = Date.UTC(year, 0, 1);
    const span = Date.UTC(year + 1, 0, 1) - start;
    return [year + (Date.UTC(year, month - 1, 1) - start) / span, year + (Date.UTC(year, month, 1) - start) / span];
  }
  const position = datePosition(record);
  return [position, position];
}

export function layoutTimeline(entries: TimelineEntry[], yearWidth: number, asOf: string, rowHeight = ROW_HEIGHT): TimelineLayout {
  const dated = entries.flatMap(entry => STAGES.flatMap(stage => entry[stage]?.date ? [{ entry, stage, record: entry[stage]! }] : []));
  if (!dated.length || !asOf) return { width: 0, height: 0, years: [], yearWidth, nowX: 0, rows: [], points: [], connections: [] };
  const firstYear = Math.min(...dated.map(point => Number(point.record.date!.slice(0, 4))));
  const lastYear = Math.max(Number(asOf.slice(0, 4)), ...dated.map(point => Number(point.record.date!.slice(0, 4))));
  const years = Array.from({ length: lastYear - firstYear + 1 }, (_, index) => firstYear + index);
  const x = (position: number) => PLOT_PADDING + (position - firstYear) * yearWidth;
  const nowX = x(datePosition({ date: asOf } as RecordDate));
  const rows: TimelineRow[] = [];
  const points: TimelinePoint[] = [];
  const connections: TimelineLayout["connections"] = [];
  const groups = entries.map(entry => ({ entry, firstRecord: firstPublicRecord(entry), points: dated.filter(point => point.entry.id === entry.id) }))
    .filter((group): group is typeof group & { firstRecord: RecordDate } => !!group.firstRecord)
    .sort((a, b) => a.firstRecord.date!.localeCompare(b.firstRecord.date!) || a.entry.id.localeCompare(b.entry.id));

  for (const group of groups) {
    const { entry, firstRecord } = group;
    const y = rows.length * rowHeight + rowHeight / 2;
    const canListen = entry.audio_status === "available";
    const fullRecord = entry.full_record ?? entry.release;
    const full = canListen && fullRecord?.date && fullRecord.date <= asOf ? fullRecord : null;
    const firstX = x(datePosition(firstRecord));
    const fullX = full ? x(datePosition(full)) : null;
    const first: TimelinePoint = { entry, record: firstRecord, date: firstRecord.date!, x: firstX, y, filled: !!full && firstRecord.date === full.date, current: false };
    const placed = [first];
    if (full && fullX !== null) {
      const published: TimelinePoint = first.filled ? first : { entry, record: full, date: full.date!, x: fullX, y, filled: true, current: false };
      if (published !== first) placed.push(published);
      const firstRange = dateRange(firstRecord);
      const fullRange = dateRange(full);
      if (firstX < fullX && firstRange[1] <= fullRange[0]) connections.push({ entryId: entry.id, kind: "pending", start: first, end: published });
      if (nowX > fullX) {
        const current: TimelinePoint = { entry, record: null, date: asOf, x: nowX, y, filled: true, current: true };
        placed.push(current);
        connections.push({ entryId: entry.id, kind: "public", start: published, end: current });
      }
    } else if (nowX > firstX) {
      // An unverified link is not proof of a full release. No solid period or
      // filled point is inferred; its missing full-publication history stays open.
      const current: TimelinePoint = { entry, record: null, date: asOf, x: nowX, y, filled: canListen, current: true };
      placed.push(current);
      connections.push({ entryId: entry.id, kind: "pending", start: first, end: current });
    }
    points.push(...placed);
    rows.push({ entry, firstRecord, y, startX: Math.min(...placed.map(point => point.x)), endX: Math.max(...placed.map(point => point.x)), canListen });
  }
  return { width: Math.max(nowX, ...points.map(point => point.x)) + PLOT_PADDING, height: rows.length * rowHeight, years, yearWidth, nowX, rows, points, connections };
}
