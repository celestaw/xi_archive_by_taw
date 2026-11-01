import assert from 'node:assert/strict';
import {datePosition, dateRange, firstPublicRecord, layoutTimeline, ROW_HEIGHT, PLOT_PADDING as PADDING} from '../web/lib/timeline-layout.ts';
const asOf='2026-10-31';
const record=(date,precision='day')=>({id:date,date,precision});
const entry=(id,preview,release,extra={})=>({id,title:id,preview,release,reference:null,audio_status:'unverified',full_audio_links:[],...extra});
assert.equal(ROW_HEIGHT,16);
assert.equal(datePosition(record('2024','year')),2024.5);
assert.deepEqual(dateRange(record('2024','year')),[2024,2025]);
assert.ok(dateRange(record('2024-02','month'))[1]-dateRange(record('2024-02','month'))[0]>28/366);
assert.equal(layoutTimeline([],60,asOf).rows.length,0);
const data=[
 entry('historical',null,record('2006-01-01')),
 entry('paired',record('2025-12-31'),record('2026-01-01'),{audio_status:'available',full_audio_links:[{url:'https://example.com/full'}]}),
 entry('preview-only',record('2026-02-01'),null),
 entry('full-only',null,record('2026-03-01'),{audio_status:'available',full_audio_links:[{url:'https://example.com/full'}]}),
 entry('unverified-link',null,record('2026-04-01'),{full_audio_links:[{url:'https://example.com/full'}]}),
 entry('closed',null,record('2026-05-01'),{audio_status:'unavailable'}),
 entry('undated',null,null),
 {...entry('earlier-reference',record('2026-06-01'),null),reference:record('2025-06-01')},
];
assert.equal(firstPublicRecord(data.at(-1)).date,'2025-06-01');
for(const scale of [48,600,2400]) {
 const layout=layoutTimeline(data,scale,asOf);
 assert.equal(layout.rows.length,7);
 assert.equal(layout.height,7*16);
 assert.deepEqual(layout.rows.map(row=>row.entry.id),['historical','earlier-reference','paired','preview-only','full-only','unverified-link','closed']);
 for(const [index,row] of layout.rows.entries()) {
  assert.equal(row.y,index*16+8);
  assert.ok(layout.points.filter(point=>point.entry.id===row.entry.id).every(point=>point.y===row.y));
 }
 const points=id=>layout.points.filter(point=>point.entry.id===id);
 const lines=id=>layout.connections.filter(line=>line.entryId===id);
 assert.equal(points('historical').length,2);
 assert.ok(points('historical').every(point=>!point.filled));
 assert.deepEqual(lines('historical').map(line=>line.kind),['pending']);
 assert.equal(points('historical').at(-1).date,asOf);
 assert.equal(points('paired').length,3);
 assert.deepEqual(lines('paired').map(line=>line.kind),['pending','public']);
 assert.ok(points('paired').at(-1).filled);
 assert.equal(points('paired').at(-1).date,asOf);
 assert.deepEqual(lines('full-only').map(line=>line.kind),['public']);
 assert.ok(points('full-only').every(point=>point.filled));
 assert.deepEqual(lines('preview-only').map(line=>line.kind),['pending']);
 assert.ok(points('preview-only').every(point=>!point.filled));
 assert.ok(points('unverified-link').every(point=>!point.filled));
 assert.ok(lines('unverified-link').every(line=>line.kind==='pending'));
 assert.equal(points('closed').length,2);
 assert.deepEqual(lines('closed').map(line=>line.kind),['pending']);
 assert.ok(points('closed').every(point=>!point.filled));
 assert.ok(layout.connections.every(line=>line.start.x<line.end.x&&line.start.y===line.end.y));
 assert.ok(layout.points.every(point=>point.x>=PADDING&&point.x<=layout.width-PADDING));
}
const soundcloud=layoutTimeline([entry('soundcloud',null,null,{reference:record('2026-04-01'),full_record:record('2026-04-01'),audio_status:'available'})],600,asOf);
assert.ok(soundcloud.rows[0].canListen);
assert.ok(soundcloud.connections.some(line=>line.kind==='public'));
const loose=layoutTimeline(data,600,asOf,32);
assert.equal(loose.height,7*32);
for (const preview of [record('2026','year'),record('2026-04','month')]) {
 const overlap=layoutTimeline([entry('overlap',preview,record('2026-04-26'),{audio_status:'available',connect_preview:false})],600,asOf);
 assert.ok(!overlap.connections.some(line=>line.kind==='pending'),'Overlapping uncertain dates must not invent a pre-release interval');
}
const adjacent=layoutTimeline([entry('adjacent',record('2025-12','month'),record('2026-01-01'),{audio_status:'available'})],600,asOf);
assert.ok(adjacent.connections.some(line=>line.kind==='pending'));
console.log('Timeline periods: compact chronological rows, unknown audio dotted through today, full periods, precision overlap and density passed.');
