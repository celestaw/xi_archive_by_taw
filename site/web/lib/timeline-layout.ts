import type { RecordDate, TimelineEntry } from "./api";

export type Stage = "preview" | "release" | "reference";
export type TimelinePoint = { entry: TimelineEntry; stage: Stage; record: RecordDate; x: number; y: number; hitWidth: number };
export type TimelineRow = { entry: TimelineEntry; firstRecord: RecordDate; y: number };
export type TimelineLayout = {
  width: number; height: number; years: number[]; yearWidth: number;
  rows: TimelineRow[]; points: TimelinePoint[]; connections: { entryId: string; start: TimelinePoint; end: TimelinePoint }[];
};

export const PLOT_PADDING = 32;
export const ROW_HEIGHT = 56;
const STAGES: Stage[] = ["preview", "release", "reference"];

export function firstPublicRecord(entry: TimelineEntry): RecordDate | null {
  return STAGES.map(stage => entry[stage]).filter((record): record is RecordDate => !!record?.date)
    .sort((a, b) => a.date!.localeCompare(b.date!) || a.id.localeCompare(b.id))[0] ?? null;
}

// Partial dates occupy the middle of their known interval, never an invented
// January 1 / first-of-month date. Their full interval is drawn behind the dot.
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

export function layoutTimeline(entries: TimelineEntry[], yearWidth: number, labelWidth = 240): TimelineLayout {
  const dated = entries.flatMap(entry => STAGES.flatMap(stage => entry[stage]?.date ? [{ entry, stage, record: entry[stage]! }] : []));
  if (!dated.length) return { width: 0, height: 0, years: [], yearWidth, rows: [], points: [], connections: [] };
  const firstYear = Math.min(...dated.map(point => Number(point.record.date!.slice(0, 4))));
  const lastYear = Math.max(...dated.map(point => Number(point.record.date!.slice(0, 4))));
  const years = Array.from({ length: lastYear - firstYear + 1 }, (_, index) => firstYear + index);
  const x = (position: number) => labelWidth + PLOT_PADDING + (position - firstYear) * yearWidth;
  const rows: TimelineRow[] = [];
  const points: TimelinePoint[] = [];
  const connections: TimelineLayout["connections"] = [];
  const groups = entries.map(entry => ({ entry, firstRecord: firstPublicRecord(entry), points: dated.filter(point => point.entry.id === entry.id) }))
    .filter((group): group is typeof group & { firstRecord: RecordDate } => !!group.firstRecord)
    .sort((a, b) => a.firstRecord.date!.localeCompare(b.firstRecord.date!) || a.entry.id.localeCompare(b.entry.id));

  for (const group of groups) {
    const positions = group.points.map(point => x(datePosition(point.record)));
    const y = rows.length * ROW_HEIGHT + ROW_HEIGHT / 2;
    rows.push({ entry: group.entry, firstRecord: group.firstRecord, y });
    const placed = group.points.map((point, index) => ({
      ...point, x: positions[index], y,
      // Nearby stages share one row; narrow their hit areas horizontally rather
      // than shifting either date or putting the song on a second row.
      hitWidth: Math.min(44, ...positions.filter((_, otherIndex) => index !== otherIndex).map(other => Math.max(12, Math.abs(other - positions[index])))),
    }));
    points.push(...placed);
    const preview = placed.find(point => point.stage === "preview");
    const release = placed.find(point => point.stage === "release");
    if (group.entry.connect_preview && preview && release) connections.push({ entryId: group.entry.id, start: preview, end: release });
  }
  return { width: labelWidth + years.length * yearWidth + PLOT_PADDING * 2, height: rows.length * ROW_HEIGHT, years, yearWidth, rows, points, connections };
}
