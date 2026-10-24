import collections, csv, hashlib, json, pathlib, re
from collect import ROOT,RAW,TODAY,dump
from prepare import DATA

def read(p):return json.loads(p.read_text(encoding='utf-8'))
works=read(DATA/'works.json')['works'];wm={w['id']:w for w in works}
events=read(DATA/'publication_events.json');em={e['event_id']:e for e in events}
sources=read(DATA/'sources.json');sm={s['source_id']:s for s in sources}
mapping=read(DATA/'reconciliation.json');raw=read(DATA/'note_entries_raw.json')
assert len(wm)==len(works)==251
assert len(em)==len(events)
assert len(mapping)==len(raw)==249
assert {e['id'] for e in mapping}=={e['id'] for e in raw}
assert all(k in wm for m in mapping for k in m['target_ids'])
assert all(e['work_id'] in wm and e['source_id'] in sm for e in events)
assert all(e['event_id'] in wm[e['work_id']]['events'] for e in events)
assert all(e['date'] is None or bool(re.fullmatch(r'\d{4}(-\d{2}-\d{2})?',e['date'])) for e in events)
assert all((e['date_precision']=='year')==(len(e['date'])==4) for e in events if e['date'])
assert all(w['first_publication_date'] is None for w in works)
assert all(w['date']==min(e['date'] for e in events if e['work_id']==w['id'] and e['date'] and e['is_publication_record'] and e['verification_status'].startswith('一次')) for w in works if w['date'])
for w in works:
    for r in w['relationships']:
        assert r['parent_id'] in wm and r['parent_id']!=w['id']
    for x in w['official_listening']:
        assert x['source_id'] in sm and x['url'].startswith('https://')
        assert any(h in x['url'] for h in ('diversesystem.bandcamp.com','osu.ppy.sh/beatmaps/artists/727','soundcloud.com/xi_com_giko_31/','www.youtube.com/watch?','music.apple.com/','open.spotify.com/','www.nekomirin.com/','linkco.re/'))
    assert w['confidence'] and w['issues'] and w['checked_on']==TODAY
expected=['2005-12-19','2005-12-23','2006-01-31','2006-02-08','2006-03-21','2006-07-24','2006-08-17','2006-09-01','2006-09-27','2006-12-15','2007-01-16','2007-02-23','2007-03-02','2007-04-02','2007-11-05','2008-01-16']
assert [wm[f'XI-{i:03}']['date'] for i in range(1,17)]==expected
assert wm['XI-002']['date_type']=='旧muzie掲載日付（update）'
assert wm['XI-017']['date']=='2008-03-19' and em['EV-049']['date']=='2008-03-21'
assert wm['XI-034']['date']=='2011-09-25' and wm['XI-034']['composition_date']=='2011'
assert wm['XI-154']['date']=='2025-07-25' and wm['XI-158']['date']=='2026-03-01' and wm['XI-161']['date']=='2026-10-03'
assert wm['XI-235']['date']=='2024' and wm['XI-235']['date_precision']=='year'
assert wm['XI-196']['date']=='2023-11-01' # UTC-offset conversion crosses midnight.
assert wm['XI-060']['date']=='2014-12-13' # UTC to JST crosses midnight.
assert wm['XI-251']['role']=='原曲側：xi。リミックス担当：Sakuzyo'
assert wm['XI-251']['family_id']=='XI-072' and wm['XI-251']['count_as_independent_new_composition'] is False
assert len([m for m in mapping if not m['target_ids']])==0
assert next(m for m in mapping if m['id']=='NOTE-030')['target_ids']==['XI-076','XI-077','XI-078']
assert next(m for m in mapping if m['id']=='NOTE-030')['reference_type']=='group_reference'
assert next(m for m in mapping if m['id']=='NOTE-051')['target_ids']==['XI-143']
assert wm['XI-143']['aliases'][0]['title']=='Storm and Impulse'
assert wm['XI-143']['aliases'][0]['source_type']=='user_clarification'
assert len({wm[k]['family_id'] for k in ('XI-076','XI-077','XI-078')})==3
assert len(next(m for m in mapping if m['id']=='NOTE-099')['target_ids'])==3
manuscript=(ROOT/'manuscript/note_draft.md').read_text(encoding='utf-8')
ids=re.findall(r'調査ID: (XI-\d+)',manuscript)
assert collections.Counter(ids)==collections.Counter(wm.keys())
for name,count in [('works.csv',251),('reconciliation.csv',249),('publication_events.csv',len(events)),('unresolved.csv',251)]:
    with (DATA/name).open(encoding='utf-8-sig',newline='') as f:assert len(list(csv.DictReader(f)))==count
sourcebook=read(RAW/'workbook_raw.json')
assert hashlib.sha256((RAW/'xi_composition_chronology_research.xlsx').read_bytes()).hexdigest()==sourcebook['sha256']
report={'checked_on':TODAY,'result':'pass','checks':['全251項目と元リスト249行を保持','全イベント・出典・原曲の参照先が実在','日付精度・初公開日未確定・作曲年分離','初期16曲の日付・FREEDOM DiVE↓の2登録日を照合','UTCと日本時間の日付越境を点検','他者リミックス・3曲併記・未統合行の処理を点検','原稿に全IDが一度ずつ存在','JSONとCSVの件数整合','元Excel複製のSHA-256一致'],'limitations':['全曲の初公開日は未確定','帰属が未確認の候補が残る','公式試聴ページの実再生・地域制限は未検証']}
dump(DATA/'validation.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
