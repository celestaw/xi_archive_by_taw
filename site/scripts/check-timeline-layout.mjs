import assert from 'node:assert/strict';
import { datePosition, dateRange, firstPublicRecord, layoutTimeline, ROW_HEIGHT } from '../web/lib/timeline-layout.ts';

const record = (date, precision = 'day') => ({ id: date, date, precision });
const entry = (id, preview, release, connect_preview = false) => ({ id, preview, release, reference: null, connect_preview });

assert.equal(datePosition(record('2024', 'year')), 2024.5);
assert.deepEqual(dateRange(record('2024', 'year')), [2024, 2025]);
const month = dateRange(record('2024-02', 'month'));
assert.ok(month[1] - month[0] > 28 / 366, 'leap-year February keeps its 29-day range');
assert.equal(layoutTimeline([], 60).points.length, 0);

const data = [
  entry('release-only', null, record('2026-03-01')),
  {...entry('earlier-reference', record('2026-04-01'), record('2026-05-01'), true), reference:record('2025-06-01')},
  entry('paired', record('2025-12-31'), record('2026-01-01'), true),
  entry('same-day', null, record('2026-01-01')),
  entry('preview-only', record('2026-02-01'), null),
  entry('year-only', null, record('2026', 'year')),
  entry('later-preview', record('2026-06-01'), record('2025-01-01')),
  entry('undated', null, null),
];
for (const scale of [600, 1200, 2400]) {
  const layout = layoutTimeline(data, scale);
  assert.equal(layout.points.length, 11);
  assert.equal(layout.connections.length, 2);
  assert.equal(layout.rows.length, 7);
  assert.equal(layout.height, 7 * ROW_HEIGHT);
  assert.deepEqual(layout.years, [2025, 2026]);
  assert.deepEqual(layout.rows.map(row => row.entry.id), ['later-preview', 'earlier-reference', 'paired', 'year-only', 'same-day', 'preview-only', 'release-only']);
  assert.equal(firstPublicRecord(data[1]).date, '2025-06-01', 'earlier reference participates in chronological sorting');
  for (const [index, row] of layout.rows.entries()) {
    assert.equal(row.y, index * ROW_HEIGHT + ROW_HEIGHT / 2);
    assert.ok(layout.points.filter(point => point.entry.id === row.entry.id).every(point => point.y === row.y), 'every milestone for a song stays on its single row');
    assert.equal(layout.rows.filter(other => other.y === row.y).length, 1, 'one song per row, including identical dates');
  }
  for (const point of layout.points) {
    assert.ok(point.x >= 22 && point.x <= layout.width - 22);
    assert.ok(point.y >= 22 && point.y <= layout.height - 22);
    for (const other of layout.points) {
      if (point === other || point.entry.id === other.entry.id) continue;
      assert.ok(Math.abs(point.y - other.y) >= ROW_HEIGHT, 'different songs never share a row');
    }
  }
  const pair = layout.points.filter(point => point.entry.id === 'paired');
  assert.equal(pair[0].y, pair[1].y, 'close preview/release points stay on the same song row');
  assert.ok(pair[1].x > pair[0].x, 'date scale remains chronological');
}
const pachad = layoutTimeline([entry('pachad',record('2026-04-09'),record('2026-04-26'),true)],600);
assert.ok(pachad.points[0].hitWidth >= 24, 'the real preview/release pair has separate selectable hit areas');
assert.ok(pachad.width > 600);
console.log('Timeline layout: first-publication ordering, one song per row, shared milestone rows, wide date scale and date precision passed.');
