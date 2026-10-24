import collections, csv, datetime, html, json, re, urllib.parse
from collect import ROOT,RAW,TODAY,dump
from prepare import DATA,table,norm,loose

OUT=ROOT/'manuscript';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def iso(v):return str(v)[:10] if v else None
def clean_title(t):return t.split(' - ',1)[1] if ' - ' in t else t
def comparable(t):
    import unicodedata
    return loose(''.join(c for c in unicodedata.normalize('NFD',t) if not unicodedata.combining(c)))
def write_csv(name,rows,fields=None):
    if not rows:return
    fields=fields or list(rows[0])
    with (DATA/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
        for r in rows:w.writerow({k:json.dumps(r.get(k),ensure_ascii=False) if isinstance(r.get(k),(list,dict)) else r.get(k) for k in fields})

sources={}
for name in ('fetch_evidence.json','fetch_archive_raw.json','fetch_extras.json','fetch_extras2.json','fetch_extras3.json','fetch_note.json'):
    for m in read(RAW/name):sources[m['url']]=m
def content(url):return (RAW/(sources[url]['key']+'.txt')).read_text(encoding='utf-8')
def source_for(url):
    if 'web.archive.org' in url and 'id_/' not in url:
        raw=re.sub(r'/web/(\d+)/',r'/web/\1id_/',url)
        if raw in sources:return raw
    return url
def sid(url):return 'SRC-'+sources[url]['key']
def event_sort(e):
    capture=re.search(r'/web/(\d{14})',e['source_url'])
    return (e['date'] or '9999',capture.group(1) if capture else '99999999999999',e['event_id'])
albums=read(DATA/'album_metadata.json')
album_by_url={a['url']:a for a in albums}
works={w['id']:dict(w,original_list_spellings=[],note_entry_ids=[],events=[],official_listening=[],relationships=[],issues=[],comment='',credited_name=None,role=None,identity_status='帰属未確認',first_medium=None) for w in read(DATA/'workbook_items.json')}
works['XI-250']={'id':'XI-250','title':'泡沫と月','original_sheet':None,'notes_claim':None,'original_list_spellings':[],'note_entry_ids':[],'events':[],'official_listening':[],'relationships':[],'issues':[],'comment':'','credited_name':None,'role':None,'identity_status':'帰属未確認','first_medium':None}
works['XI-251']={'id':'XI-251','title':'ANiMAtion','original_sheet':None,'notes_claim':None,'original_list_spellings':[],'note_entry_ids':[],'events':[],'official_listening':[],'relationships':[],'issues':[],'comment':'','credited_name':None,'role':None,'identity_status':'帰属未確認','first_medium':None}

overrides=read(DATA/'matching_overrides.json');note=read(DATA/'note_entries_raw.json')
user_clarifications=read(DATA/'user_clarifications.json')
decisions=[];unmatched=[]
for e in note:
    n=norm(e['title_token']);method='正規化一致（大小文字・空白）';reason='原文を残し、照合用に大小文字・空白・Unicode互換字形のみ正規化。作品の帰属や初出の確定とは別。'
    exact=[k for k,w in works.items() if norm(w['title'])==n]
    if e['id'] in overrides:
        ids=overrides[e['id']];method='個別照合判断';reason='綴り・注記・媒体文脈を照合。正式曲名は一次資料で別途確認し、出典のない項目は候補として維持。'
    elif exact:ids=exact
    else:
        ids=[k for k,w in works.items() if loose(w['title'])==loose(e['title_token'])]
        method='句読・記号差の照合';reason='記号差・空白差として対応付け。別バージョンを意味する接尾辞は削除していない。'
    if not ids:
        unmatched.append(e)
        reason='対応先を特定できない。'
    special_reasons={
      'NOTE-021':'アルバム文脈とosu!公式許諾曲一覧の英語表題から、ハッピーエンドオブザワールドへ対応付け。',
      'NOTE-030':'利用者補足に基づき、World Fragments I・II・IIIの三部作へのまとめた参照として対応付け。アルバム名もWorld Fragmentsだが、アルバムを別曲として数えない。',
      'NOTE-051':'利用者が太鼓の達人の疾風怒濤の英語タイトルStorm and Impulseと明示したため、XI-143へ対応付け。元のStorm and inpulse表記は保全する。',
      'NOTE-065':'英語表題の綴り差。osu!公式許諾曲一覧のHappy End of the Worldを介して日本語表題へ対応付け。',
      'NOTE-096':'osu!公式許諾曲一覧のxi respect for F.F.Chopin - Fと、旧muzieの幻想即興曲remix説明を照合。',
      'NOTE-099':'原文がI・II・IIIを明示するため3曲のIDへ分割。公式アルバム曲目と照合。',
      'NOTE-134':'原文が疾風怒濤を明記。括弧内のStorm and Impulseは利用者補足で同曲の英語タイトルと確認。別曲を新設しない。',
      'NOTE-194':'公式曲目のxi remixed by Sakuzyo - ANiMAtionと一致。xi自身による新規リミックスとは扱わない。',
      'NOTE-195':'Binary Blueという収録文脈からBlue quartzへ候補対応。原文の#2A64B0との同一性は未確認。',
      'NOTE-232':'cosMo@暴走P関連・xi Remixという原文注記と公式曲目を照合し、ギリシャ文字の表記差を残して対応付け。'}
    if e['id'] in special_reasons:reason=special_reasons[e['id']]
    d=dict(e,target_ids=ids,decision_type=method,decision_reason=reason,checked_on=TODAY)
    d['reference_type']='group_reference' if e['id'] in ('NOTE-030','NOTE-099') else 'work_reference'
    d['user_clarification_ids']=['USER-20261023-001'] if e['id'] in ('NOTE-030','NOTE-051','NOTE-134') else []
    decisions.append(d)
    for k in ids:
        works[k]['original_list_spellings'].append(e['original_text']);works[k]['note_entry_ids'].append(e['id'])
dump(DATA/'reconciliation.json',decisions);write_csv('reconciliation.csv',decisions)

groups=[{'id':'GROUP-WORLD-FRAGMENTS','title':'World Fragments','group_type':'三部作（各曲は独立した項目）','album_title':'World Fragments','member_ids':['XI-076','XI-077','XI-078'],'note_entry_ids':['NOTE-030','NOTE-099'],'source_urls':['https://diversesystem.bandcamp.com/album/world-fragments','https://www.youtube.com/watch?v=G-nmpgBn7-8'],'user_clarification_ids':['USER-20261023-001'],'counting_rule':'アルバム名・三部作の総称から追加の曲IDを作成しない。I・II・IIIを別バージョンとして統合しない。'}]
dump(DATA/'work_groups.json',groups)
for w in works.values():
    w['aliases']=[];w['group_ids']=[];w['user_clarification_ids']=[]
for k in ('XI-076','XI-077','XI-078'):
    works[k]['group_ids']=['GROUP-WORLD-FRAGMENTS'];works[k]['user_clarification_ids']=['USER-20261023-001']
works['XI-143']['aliases']=[{'title':'Storm and Impulse','language':'en','alias_type':'英語タイトル','source_type':'user_clarification','source_id':'USER-20261023-001','verification_status':'利用者補足として採用。外部一次資料の表記は今回新たに検証していない。','checked_on':TODAY}]
works['XI-143']['user_clarification_ids']=['USER-20261023-001']
works['XI-143']['issues'].append('英語タイトルの外部出典URLを追記する。別名関係は利用者補足として採用済み。')

events=[]
def add_event(k,date,kind,medium,url,summary,credit=None,original=None,confidence='一次資料を今回確認',version=None):
    ev={'event_id':original['B'] if original else f'NEW-{len(events)+1:03}','work_id':k,'date':iso(date),'date_precision':('year' if len(str(date))==4 else 'day') if date else None,'date_type':kind,'medium':medium,'source_url':url,'source_id':sid(url),'evidence_summary':summary,'verification_status':confidence,'checked_on':TODAY,'true_first_publication_confirmed':False,'is_publication_record':True,'recording_version':version or '音源の同一性・版は未同定','original_workbook_claim':original}
    events.append(ev);works[k]['events'].append(ev['event_id'])
    if confidence.startswith('一次'):
        works[k]['identity_status']='一次資料にクレジットあり'
        if credit and not works[k]['credited_name']:works[k]['credited_name']=credit
    return ev
def listen(k,url,label,source_url,version=None):
    basis='運営公式ページ、または公式紹介ページからの本人リンクを確認'
    proof=source_url
    if 'bandcamp' in url:basis='レーベル公式サイトのBandcampリンクと収録曲プレイヤーを確認';proof='https://diverse.jp/'
    if 'youtube.com/watch' in url:basis='公式配信案内のYouTubeチャンネルリンクと各動画のchannelIdが一致';proof='https://linkco.re/09QH755a?lang=ja'
    if 'soundcloud.com/xi_com_giko_31' in url:basis='osu!公式Featured Artistページがリンクする本人SoundCloudと一致';proof='https://osu.ppy.sh/beatmaps/artists/727'
    item={'url':url,'label':label,'source_url':source_url,'source_id':sid(source_url),'official_basis':basis,'officialness_source_url':proof,'recording_version':version or '収録版。初期公開版と同一音源とは未確認','availability':'ページと試聴データの存在を確認。実再生・地域制限は未検証','checked_on':TODAY}
    if item['url'] not in [x['url'] for x in works[k]['official_listening']]:works[k]['official_listening'].append(item)

for row in table('公開記録と出典'):
    v=row['values'];eid=v.get('B','')
    if not eid.startswith('EV-'):continue
    k=v['C'];url=source_for(v['J']);t=content(url);date=iso(v.get('D'));verified=False;summary='';credit=v.get('H');version=None
    if 'bandcamp.com' in url:
        a=album_by_url[url]
        hits=[x for x in a['tracks'] if comparable(clean_title(x['title']))==comparable(v['E'])]
        if len(hits)==1:
            tr=hits[0];actual=datetime.datetime.strptime(a['release_date'],'%d %b %Y %H:%M:%S %Z').date().isoformat()
            verified=actual==date
            summary=f"公式曲目の第{tr['track_number']}曲『{clean_title(tr['title'])}』と released {actual} を確認。これはアルバム表示の発売日で、初公開日は未確定。"
            credit=tr['artist'] or (tr['title'].split(' - ',1)[0] if ' - ' in tr['title'] else a['artist'])
            if tr['streaming']:listen(k,tr['url'],'レーベル公式Bandcamp',url,clean_title(tr['title']))
        else:summary='曲目の一意一致が得られず要確認。'
    elif 'manbow.nothing.sh' in url:
        reg=re.search(r'Regist Time\s*\n(\d{4}/\d{2}/\d{2})[^\n]*',t)
        titles=re.findall(r'\nTitle\s*\n([^\n]+)',t)
        verified=bool(reg and reg.group(1).replace('/','-')==date and any(comparable(title)==comparable(v['E']) for title in titles))
        summary=f"作者欄・Title欄とRegist Time {reg.group(1) if reg else '未抽出'}を確認。Last Updateと区別。イベント登録より前の公開有無は別問題。"
    elif 'web.archive.org' in url:
        if '20120309072238' in url:
            blocks=re.findall(r'([^\n]+)\n\(ジャンル：[^\n]*\n\(登録日:(\d{4}-\d{2}-\d{2})\)',t)
            hits=[(title,d) for title,d in blocks if comparable(title)==comparable(v['E'])]
            verified=bool(hits and hits[0][1]==date)
            summary=f"muzie ID a037818の保存本文で『{hits[0][0] if hits else v['E']}』の登録日 {date} を照合。保存日時は曲の日付に使わない。"
        else:
            blocks=re.findall(r'(?:title|TITLE):\s*([^\n]+)\n(.*?)(\d{4}\.\d{2}\.\d{2}) update',t,re.S)
            hits=[(title,d) for title,body,d in blocks if comparable('Church Bell' if title=='Churth Bell' else title)==comparable(v['E'])]
            verified=bool(hits and hits[0][1].replace('.','-')==date)
            summary=f"muzie ID a037818の本文の『{hits[0][0] if hits else v['E']}』とupdate {date} を照合。作曲日・厳密な初公開日とはしない。"
    elif 'linkco.re/' in url:
        match=re.search(r'リリース日:\s*(\d{4}/\d{2}/\d{2})',t)
        verified=bool(match and match.group(1).replace('/','-')==date and v['E'].split(' [')[0] in t)
        summary=f"配信ページのリリース日 {date} とxiの作曲クレジットを確認。ゲーム・大会での先行公開日は未確定。"
        if verified:listen(k,url,'本人の正規配信案内（TuneCore）',url)
    else:
        verified=v['E'] in t and ('xi' in t)
        summary='運営公式の曲名・名義を照合。楽曲ごとの初収録日の記載は確認できず。'
        if verified and 'music-am.sega.jp' in url:
            links=sources[url]['links']; ls=[x for x in links if x.startswith(('https://music.apple.com/jp/song/','https://open.spotify.com/','https://music.youtube.com/'))]
            for li in ls[:2]:listen(k,li,'SEGA公式が案内する正規配信',url)
    status='一次資料を今回確認' if verified else '既存表の記録・今回の自動照合未成立'
    ev=add_event(k,date,v['F'],v['G'],url,summary,credit,v,status,version)
    if verified and 'BMS作品登録日'==v['F'] and 'Original・Self' in t:
        works[k]['role']='作曲（BMS登録欄はOriginal・Self）'

# Explicit secondary-source claims remain separate from primary evidence.
for w in works.values():
    if w.get('candidate_url'):w['issues'].append('既存表の候補URLは探索用。一次資料による帰属・初公開日の確認が必要。')

# Official album credits absent from the prior chronology.
for k,album_title,title in [('XI-251','Triangle – C89 Special Remixes EP','ANiMAtion')]:
    a=next(a for a in albums if a['title']==album_title);tr=next(x for x in a['tracks'] if clean_title(x['title'])==title)
    date=datetime.datetime.strptime(a['release_date'],'%d %b %Y %H:%M:%S %Z').date().isoformat()
    add_event(k,date,'アルバム発売日（初出未確定）',album_title,a['url'],'公式第1曲のxi remixed by Sakuzyoクレジットを確認。xiの新規作曲として別加算しない。',tr['artist'])
    listen(k,tr['url'],'レーベル公式Bandcamp',a['url'],title)

# Licensed osu! previews. updated_at is deliberately never used as a release date.
osu='https://osu.ppy.sh/beatmaps/artists/727';oh=(RAW/(sources[osu]['key']+'.html')).read_text(encoding='utf-8')
osu_tracks=[]
for attrs,body in re.findall(r'<script([^>]*)>(.*?)</script>',oh,re.S):
    if 'album-json' in attrs or 'singles-json' in attrs:osu_tracks.extend(json.loads(body))
special={'xi respect for F.F.Chopin - F':'XI-014','Garyou Tensei':'XI-013','Happy End of the World':'XI-053','Mjolnir':'XI-123'}
for tr in osu_tracks:
    k=special.get(tr['title'])
    if not k:
        ids=[k for k,w in works.items() if comparable(w['title'])==comparable(tr['title'])]
        k=ids[0] if len(ids)==1 else None
    if not k:continue
    listen(k,osu,'osu! Featured Artist公式ページの試聴',osu,tr['title'])
    # No media file is downloaded or linked directly; the licensed player page is supplied.
    add_event(k,None,'公式クレジット・試聴掲載（掲載開始日未確認）','osu! Featured Artist',osu,f"公式許諾曲一覧に『{tr['title']}』を確認。API内部のupdated_atは公開日に転用しない。",'xi')
dump(DATA/'osu_tracks_metadata.json',[{k:v for k,v in t.items() if k not in ('osz','preview')} for t in osu_tracks])

# SoundCloud dates from the visible first-party track/profile pages; convert UTC to JST.
sc='https://soundcloud.com/xi_com_giko_31'
sc_records=[('XI-094','2017-12-18T14:28:33Z','https://soundcloud.com/xi_com_giko_31/leveilbelieve-in-your-mindc93-1','Believe in your mind','本人SoundCloud掲載日（公開音源の版未確認）'),('XI-063','2015-05-04T16:05:21Z','https://soundcloud.com/xi_com_giko_31/barrage-is-the-power','Barrage is the power','本人SoundCloud掲載日（公開音源の版未確認）')]
for k,stamp,url,title,kind in sc_records:
    text=content(url)
    # Both direct pages are retained; profile metadata is used only to establish ownership.
    timestamp=stamp
    dt=datetime.datetime.fromisoformat(timestamp.replace('Z','+00:00')).astimezone(datetime.timezone(datetime.timedelta(hours=9)))
    ev=add_event(k,dt.date().isoformat(),kind,'SoundCloud（本人）',url,f"本人公開ページの published on {timestamp} を確認。年表日は日本時間へ換算。全長版の初公開とは未確定。",'xi')
    ev['source_timestamp']=timestamp;ev['source_timezone']='UTC';ev['display_timezone']='Asia/Tokyo'
    listen(k,url,'本人SoundCloud',url,'公開音源の版未同定')

for k,url,preview in [
 ('XI-060','https://soundcloud.com/xi_com_giko_31/freezing-ray_pv',True),
 ('XI-212','https://soundcloud.com/xi_com_giko_31/powder-snowfield-1',False),
 ('XI-233','https://soundcloud.com/xi_com_giko_31/the-wind-of-gold-xiremix',False)]:
    match=re.search(r'published on ([0-9TZ:\-]+)',content(url));stamp=match.group(1)
    dt=datetime.datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(datetime.timezone(datetime.timedelta(hours=9)))
    ev=add_event(k,dt.date().isoformat(),'PV公開日（曲の一部・全長初出未確定）' if preview else '本人SoundCloud掲載日（公開音源の版未確認）','SoundCloud（本人）',url,f'本人ページのpublished on {stamp}を確認。日本時間へ換算。コメント投稿日時は曲の公開日に使わない。','xi')
    ev['source_timestamp']=stamp;ev['source_timezone']='UTC';ev['display_timezone']='Asia/Tokyo'
    ev['recording_version']='PV／抜粋' if preview else '本人公開版（初期版との同一性未確認）'
    listen(k,url,'本人SoundCloud（PV／抜粋）' if preview else '本人SoundCloud',url,ev['recording_version'])

# Artist YouTube: channel linked by the verified TuneCore artist page.
video_map={
 '_K3LNlaGmY4':['XI-175'],'VNK8leVFy-g':['XI-161'],'phiCv9e4fZA':['XI-250'],
 'Fhw7jUOTm40':['XI-158'],'VxisX358Mmk':['XI-242'],'tpYLJpl5UZU':['XI-207'],
 '-PTe8zkYt9A':['XI-154'],'G-nmpgBn7-8':['XI-076','XI-077','XI-078'],
 'FGy4oACAAbc':['XI-240'],'ZtLe9EC_KcQ':['XI-235'],'q_7qM96gSNg':['XI-219'],
 'tjfzgAVvxqk':['XI-196'],'6jIiA5t11No':['XI-139'],'MAxz5k_R-_w':['XI-249'],
 '0372jx-bTzA':['XI-059'],'CRpuzsNRBsU':['XI-034'],'5UH02v_g6fQ':['XI-119'],
 'GHhkJ4PCaBI':['XI-083'],'wlYGZx0R8KE':['XI-021'],'N3JVN7NhIAM':['XI-209']}
for v in read(DATA/'youtube_metadata.json'):
    assert v['channel']=='UCwzcz476gcGbMnXyxWDUpaA'
    vid=urllib.parse.parse_qs(urllib.parse.urlparse(v['url']).query)['v'][0]
    stamp=v['publishDate'];dt=datetime.datetime.fromisoformat(stamp).astimezone(datetime.timezone(datetime.timedelta(hours=9)))
    gameplay='作曲者がプレイ' in v['title'];version='本人によるゲームプレイ動画内のゲーム音源' if gameplay else ('連結版 I～III mix' if vid=='G-nmpgBn7-8' else ('Short Edit' if vid=='5UH02v_g6fQ' else '本人MV／動画公開版'))
    if vid=='CRpuzsNRBsU':version='2018年リマスター音源（本人説明）'
    if vid=='GHhkJ4PCaBI':version='リマスター版（本人説明）'
    for k in video_map[vid]:
        ev=add_event(k,dt.date().isoformat(),'本人動画公開日（ゲームプレイ）' if gameplay else '本人動画公開日（公開版・初出未確定）','YouTube（xi Official）',v['url'],f"本人チャンネルIDと動画タイトル『{v['title']}』、publishDate {stamp}を確認。日本時間へ換算。ゲーム初収録日と区別。",'xi',version=version)
        ev['source_timestamp']=stamp;ev['source_timezone']='動画メタデータのUTCオフセット';ev['display_timezone']='Asia/Tokyo'
        listen(k,v['url'],'本人公式YouTube（ゲームプレイ）' if gameplay else '本人公式YouTube',v['url'],version)
        # Promote the artist's explicit retrospective composition years without inventing month/day.
        year_by_video={'0372jx-bTzA':'2014','CRpuzsNRBsU':'2011','GHhkJ4PCaBI':'2016','wlYGZx0R8KE':'2009','G-nmpgBn7-8':'2015'}
        if vid in year_by_video:
            yr=year_by_video[vid]
            ce=add_event(k,yr,'作曲年（本人による回顧説明）','YouTube（xi Official）',v['url'],f'動画説明欄で{yr}年に作曲した旨を確認。月日は未確認。','xi')
            ce['is_publication_record']=False;ce['recording_version']='作曲年の記述（公開音源の発売日ではない）'
        if vid=='CRpuzsNRBsU':
            ce=add_event(k,'2018','リマスター年（本人による回顧説明）','YouTube（xi Official）',v['url'],'動画説明欄で2018年にリマスターした音源と明記。リマスター版の2018年公開までは意味しない。','xi')
            ce['is_publication_record']=False
        if vid=='ZtLe9EC_KcQ':
            add_event(k,'2024','イベント公開年（本人回顧・月日未確認）','FRENZ 2024／M→Fes 2024',v['url'],'本人説明に2024年の両イベントで公開した映像の編集版と明記。会場での公開年は確認できるが、日程中の実際の上映日は未確認。','xi')
        if vid=='5UH02v_g6fQ':
            add_event(k,'2020-12-18','イベントでの音源使用日（本人回顧）','maimai ALL PERFECT COLLECTiON RELEASE PARTY',v['url'],'本人説明に2020/12/18のイベントで流したShort Edit音源と明記。フル版の初公開日とはしない。','xi',version='Short Edit')

neko='https://www.nekomirin.com/nmcd0028/index.html'
add_event('XI-159','2026-04-26','アルバム発売日（先行クロスフェードあり）','Clippings of youth Ex.',neko,'公式特設で発売日2026/04/26、PACHADを原曲とするtr.7、Arrangement担当xiを確認。','xi')
cross='https://soundcloud.com/nekomimi_style/nekomimi-style-nmcd0028-crossfade'
ev=add_event('XI-159','2026-04-09','クロスフェード公開日（全曲初公開ではない）','SoundCloud（nekomimi style）',cross,'レーベル公開クロスフェードのpublished on 2026-04-08T16:51:48Z。日本時間は4月9日。曲の一部の公開記録として扱う。','xi')
ev['source_timestamp']='2026-04-08T16:51:48Z';ev['source_timezone']='UTC';ev['display_timezone']='Asia/Tokyo';ev['recording_version']='アルバムクロスフェード内の抜粋'
listen('XI-159',neko,'レーベル公式特設のクロスフェード',neko,'クロスフェードの抜粋。全曲試聴ではない')

# Explicit variant relationships: keep every original workbook ID.
parents={'XI-095':'XI-094','XI-108':'XI-068','XI-109':'XI-059','XI-110':'XI-069','XI-112':'XI-083','XI-118':'XI-117','XI-127':'XI-166','XI-128':'XI-166','XI-129':'XI-122','XI-131':'XI-111','XI-132':'XI-192','XI-133':'XI-192','XI-134':'XI-123','XI-136':'XI-135','XI-138':'XI-137','XI-140':'XI-121','XI-142':'XI-141','XI-144':'XI-143','XI-148':'XI-171','XI-162':'XI-161','XI-230':'XI-229','XI-251':'XI-072','XI-103':'XI-017'}
for child,parent in parents.items():
    w=works[child];relation='別バージョン'
    if child in ('XI-251','XI-103'):relation='他者による編曲・リミックス'
    if 'Remaster' in w['title']:relation='リマスター'
    if 'Long' in w['title'] or 'Extended' in w['title']:relation='ロング／拡張版'
    if 'instrument' in w['title'].lower():relation='インスト版'
    if 'Game Size' in w['title']:relation='ゲームサイズ'
    primary=any(e['work_id']==child and e['verification_status'].startswith('一次') for e in events)
    w['relationships'].append({'parent_id':parent,'type':relation,'status':'一次資料の曲名・クレジットから確認' if primary else '曲名からの関係候補・一次資料要確認','reason':'版名・クレジットを保持し、独立した新規作曲件数に加算しない。原音源との比較は未実施。'})

roles={
 'XI-014':('xi respect for F.F.Chopin','編曲／リミックス（原曲：幻想即興曲）'),
 'XI-028':('owl-light / xi','作曲。匿名名義でのBMS投稿'),
 'XI-068':('ねこかぶりサイクロン(xi+ねこみりん) feat.えみゅう。','合作。個別の制作工程は未確認'),
 'XI-069':('Mastermind(xi+nora2r)','合作。個別の制作工程は未確認'),
 'XI-073':('Feryquitous remixed by xi','xiがリミックス。原曲側：Feryquitous'),
 'XI-079':('Diceros Bicornis(xi+BlackY)','合作。個別の制作工程は未確認'),
 'XI-087':('Diceros Bicornis(xi+BlackY)','合作。個別の制作工程は未確認'),
 'XI-090':('xi + Sta','合作。個別の制作工程は未確認'),
 'XI-098':('Feryquitous vs xi','合作。個別の制作工程は未確認'),
 'XI-100':('xi vs sakuzyo','合作。個別の制作工程は未確認'),
 'XI-102':('xi vs Feryquitous','合作。個別の制作工程は未確認'),
 'XI-104':('Diceros Bicornis (xi+BlackY)','合作。個別の制作工程は未確認'),
 'XI-106':('Xista(xi + Sta)','合作。個別の制作工程は未確認'),
 'XI-113':('cosMo@暴走P Remixed by xi','xiがリミックス。原曲側：cosMo@暴走P'),
 'XI-140':('Xista (xi & Sta)','合作曲のリマスター'),
 'XI-159':('xi','編曲／リミックス。原曲：PACHAD（Blue Archive）'),
 'XI-060':('xi','東方アレンジ。原曲：おてんば恋娘（東方紅魔郷）'),
 'XI-119':('BlackY fused with WAiKURO - xi Remix','リミックス担当：xi。公式動画はShort Edit'),
 'XI-175':('xi vs かねこちはる','合作。個別の制作工程は未確認'),
 'XI-196':('のらねこさい feat.ricono','作曲：xi。編曲：xi・nora2r。作詞：ねこみりん。歌唱：ricono'),
 'XI-209':('xi vs かねこちはる','合作。個別の制作工程は未確認'),
 'XI-233':('The Wind Of Gold-xiRemix- / xi','xiがリミックス。原曲の作曲者は追加確認'),
 'XI-240':('xi (Diverse System)','リミックス担当：xi。原曲：ネクロファンタジア／作曲：ZUN'),
 'XI-242':('xi feat. Risa Yuzuki','作曲：xi（本人の作曲者プレイ動画）。歌唱名義：Risa Yuzuki'),
 'XI-249':('xi feat. Risa Yuzuki','作曲：xi（本人の作曲者プレイ動画）。歌唱名義：Risa Yuzuki'),
 'XI-250':('xi feat. Risa Yuzuki','作曲：xi（本人の作曲者プレイ動画）。歌唱名義：Risa Yuzuki'),
 'XI-244':('BlackY VS Yooh VS siromaru VS xi VS モリモリあつし','5名の合作。個別の制作工程は未確認'),
 'XI-251':('xi remixed by Sakuzyo','原曲側：xi。リミックス担当：Sakuzyo')}
for k,(credit,role) in roles.items():works[k]['credited_name']=credit;works[k]['role']=role
for k in ('XI-154','XI-158'):works[k]['role']='作曲・プロデュース・プログラミング（配信クレジット）'
for k in ('XI-161','XI-162'):works[k]['role']='作詞・作曲・プロデュース等：xi。歌唱：初音ミク';works[k]['credited_name']='xi feat. 初音ミク'
works['XI-049']['issues'].append('Xiphoid Sphere名義を確認。名義の構成・本人との関係の明示資料を追加確認。')
works['XI-103']['issues'].append('アルバム曲目だけでは編曲者の役割が明示されない。既存表はcosMo@暴走P編曲を注記しているが、別資料で役割の確認が必要。')
works['XI-103']['role']='原曲：xi。編曲者クレジットは追加確認'
works['XI-103']['relationships'][0]['status']='FREEDOM DiVE由来の版として関連付け。編曲者は未確定'

comments={
 'XI-001':'2006年の保存版に掲載が残る初期曲。2012年の一覧では確認できない。',
 'XI-004':'2006年の保存版に掲載が残る。後年の一覧だけでは拾えない初期曲。',
 'XI-009':'旧muzieでは文字間を空けた曲名表記が使われていた。',
 'XI-011':'2007年保存版の曲名は「Churth Bell」。2012年版では「Church Bell」。',
 'XI-014':'旧muzieの本人説明で「幻想即興曲」のremixとされる。2006年説は未検証。',
 'XI-015':'2007年11月5日付の掲載記録があり、FREEDOM DiVE↓より前に遡る。',
 'XI-017':'本人がBMS初制作と説明した作品。muzie登録とイベント登録は2日違う。',
 'XI-018':'BMSイベント登録は9月27日、muzie登録は10月5日と別の記録。',
 'XI-019':'旧muzieに登録記録が残る。元noteリストには見当たらない補助表由来の項目。',
 'XI-023':'公式イベントとosu! Featured Artistの表記は「Time files」。',
 'XI-028':'匿名イベントではowl-light名義。現在の登録ページにxiの名が示される。',
 'XI-051':'アルバム『Agartha』収録を確認。ゲームでの先行公開日は別途調査中。',
 'XI-070':'『Binary Blue : Answer』の公式曲目は「Blue quartz」。#2A64B0との関係は未確認。',
 'XI-072':'『World Fragments』への収録を確認。DEEMOでの先行公開日を追加調査中。',
 'XI-083':'BMS投稿時はFesta名義。本人SoundCloudへの試聴リンクが登録されている。',
 'XI-094':'本人の告知はSennzai『L’éveil』参加曲。公開音源の版は未同定。',
 'XI-123':'フル収録とGame Sizeを別音源として記録する。',
 'XI-130':'osu!公式許諾曲一覧にも掲載。内部更新日時は初公開日には採用していない。',
 'XI-159':'発売前に公式クロスフェードが公開された例。抜粋公開と発売を分ける。',
 'XI-215':'SOUND VOLTEX公式に曲名とxi名義がある。同名アルバムの表題と区別する。',
 'XI-250':'本人の作曲者プレイ動画で曲名・名義を確認。動画公開日は個別曲のゲーム初収録日とは区別する。',
 'XI-251':'「xi remixed by Sakuzyo」と明記。xiによる新規リミックスとは数えない。'
}
for k,c in comments.items():works[k]['comment']=c
for k in ('XI-076','XI-077','XI-078'):
    works[k]['comment']='同名アルバム『World Fragments』に収録された三部作の一曲。I・II・IIIはそれぞれ独立した曲として整理する。'
works['XI-143']['comment']='太鼓の達人収録曲。英語タイトルは「Storm and Impulse」（利用者補足として採用）。同名アルバムと区別する。'
works['XI-196']['comment']='本人動画で、のらねこさい名義の制作分担を確認できる。'
works['XI-240']['comment']='本人説明で原曲とリミックス担当が明記されている。新規のオリジナル作曲と区別する。'
works['XI-235']['comment']='本人動画は2025年公開だが、説明欄に2024年のイベントでの先行公開が記されている。'
works['XI-060']['comment']='確認できた本人公開音源はPV版。全長音源の初公開日ではない。'
works['XI-154']['comment']='本人動画は配信発売より2日前に公開されている。ゲーム初収録日は別途確認する。'
works['XI-158']['comment']='本人動画は配信発売より3日前の公開。決勝での最初の公開時刻は別途確認する。'
works['XI-161']['comment']='本人MVは10月3日公開、正規配信は10月5日。決勝での初披露時刻は別途確認する。'
works['XI-014']['issues'].append('Fの2006年説は採用していない。採用するなら当時の音源公開資料が必要。')
works['XI-011']['issues'].append('Churth Bell→Church Bellは同じ登録日・同じアーティストIDに基づき同一曲として整理。音源の完全一致は未確認。')
for k in ('XI-046','XI-065','XI-030'):
    works[k]['issues'].append('osu!公式許諾曲一覧で存在・試聴先は確認できたが、登録データのupdated_atを公開日に転用しない。')

# Derive the editorial date from verified observations only, never from unverified list years.
for k,w in works.items():
    evs=[e for e in events if e['work_id']==k and e['verification_status'].startswith('一次')]
    dated=sorted([e for e in evs if e['date'] and e['is_publication_record']],key=event_sort)
    w['earliest_verified_record']=dict(dated[0]) if dated else None
    w['date']=dated[0]['date'] if dated else None;w['date_type']=dated[0]['date_type'] if dated else '日付未確認'
    w['first_medium']=dated[0]['medium'] if dated else None
    w['first_medium_status']='確認できた最も早い記録の媒体。真の初出媒体は未確定' if dated else '初出媒体未確認'
    w['confidence']='日付の種類を限定して一次資料で確認。初公開日は未確定' if dated else ('存在・クレジット確認済み／日付未確認' if evs else '帰属・日付とも一次資料要確認')
    w['checked_on']=TODAY;w['first_publication_date']=None
    w['date_precision']=dated[0]['date_precision'] if dated else None
    w['composition_records']=[e for e in evs if e['date_type'].startswith('作曲年')]
    w['composition_date']=w['composition_records'][0]['date'] if w['composition_records'] else None
    w['composition_date_precision']='year' if w['composition_records'] else None
    w['role']=w['role'] or ('楽曲クレジットあり（制作工程の内訳は未確認）' if evs else '担当未確認')
    if not w['credited_name']:w['credited_name']='名義未確認'
    w['source_urls']=list(dict.fromkeys(e['source_url'] for e in evs))
    w['source_urls_candidates']=[w['candidate_url']] if w.get('candidate_url') else []
    w['evidence_summary']=[e['evidence_summary'] for e in evs]
    w['original_list_spellings']=list(dict.fromkeys(w['original_list_spellings']))
    w['issues'].append('真の初公開日は未確定。作曲日は'+('年のみ本人説明で確認。月日は未確認。' if w['composition_records'] else '未確認。'))
    if not dated:w['issues'].append('日付未確認。曲を削除せず保留。')
    if not w['official_listening']:w['issues'].append('掲載できる公式試聴先が未確認。非公式転載は採用していない。')
    if dated and 'アルバム' in w['date_type']:w['issues'].append('ゲームや本人サイトでの先行公開の有無を追加調査。')
    w['family_id']=parents.get(k,k)
    w['count_as_independent_new_composition']=False if k in parents else None

dump(DATA/'works.json',{'schema_version':1,'checked_on':TODAY,'scope':'提供noteと補助Excelの照合、一次資料による第1次調査と利用者による表記・参照関係の補足。全曲初公開日確定版ではない。','user_clarifications':user_clarifications,'work_groups':groups,'works':list(works.values())})
dump(DATA/'publication_events.json',events);write_csv('publication_events.csv',events)
write_csv('works.csv',list(works.values()),['id','title','aliases','group_ids','user_clarification_ids','original_list_spellings','note_entry_ids','original_sheet','original_row','credited_name','role','identity_status','family_id','relationships','date','date_precision','date_type','first_medium','first_medium_status','composition_date','composition_date_precision','composition_records','first_publication_date','source_urls','source_urls_candidates','evidence_summary','confidence','official_listening','checked_on','issues','comment'])
dump(DATA/'sources.json',[dict(source_id=sid(u),**m) for u,m in sources.items()])

confirmed=[w for w in works.values() if w['date']]
unknown=[w for w in works.values() if not w['date']]
stats={'note_appearances':len(note),'note_distinct_tokens_normalized':len({norm(e['title_token']) for e in note}),'workbook_items':249,'workbook_dated_items':111,'workbook_candidate_items':138,'workbook_evidence_records':168,'new_note_items':2,'total_item_records':len(works),'note_mapped_appearances':sum(bool(d['target_ids']) for d in decisions),'note_ambiguous_appearances':len(unmatched),'note_referenced_item_ids':len({k for d in decisions for k in d['target_ids']}),'workbook_only_ids':sum(not w['note_entry_ids'] for k,w in works.items() if k not in ('XI-250','XI-251')),'dated_item_records':len(confirmed),'undated_item_records':len(unknown),'primary_credit_item_records':sum(w['identity_status'].startswith('一次') for w in works.values()),'items_with_official_listening':sum(bool(w['official_listening']) for w in works.values()),'variant_relationships':len(parents),'source_pages_saved':len(sources),'verified_events':sum(e['verification_status'].startswith('一次') for e in events),'unverified_original_events':sum(not e['verification_status'].startswith('一次') for e in events)}
stats['source_pages_saved']=sum(m['status']=='retrieved' for m in sources.values())
stats['source_fetch_failures']=sum(m['status']=='failed' for m in sources.values())
dump(DATA/'summary.json',stats)
print(json.dumps(stats,ensure_ascii=False,indent=2))
print('Unverified events:',[(e['event_id'],e['work_id'],e['source_url']) for e in events if not e['verification_status'].startswith('一次')])

# Complete editable manuscript: date-verified chronology, then all undated items.
parts=['# xi 非公式作品年表（調査・編集稿）','',f'確認日：{TODAY}。提供された楽曲リストを起点に、保存された本人ページ、BMSイベント、レーベル、ゲーム運営、正規配信の記録を整理しました。','',
 '対象はFREEDOM DiVE↓などで知られる音楽ゲーム作曲家のxiです。Musical／Musicals関連を含む同名アーティストの作品は、名前の一致だけでは取り込みません。', '',
 '年表の日付は「今回確認できた最も早い公開・収録記録」です。真の初公開日とは限りません。作曲年が本人説明で確認できたものは別に記します。アルバムにしか日付の根拠がない曲は発売記録として掲載します。SoundCloud・YouTubeは日本時間に換算し、クロスフェード・PV・ゲームプレイ音源は全長音源と区別します。','',
 '初出媒体は未確定のため、以下では「確認媒体」と記します。ロング版・ゲームサイズ・リマスター・他者による編曲は同じ原曲の関連記録として扱い、独立した新規作曲数には加算しません。','',
 '『World Fragments』はアルバム名であり、同時にWorld Fragments I・II・IIIの三部作があります。この原稿では3曲を別々の項目として掲載しています。','',
 '公式試聴先は公開元と試聴データの存在まで確認したものです。地域制限や実際の再生可否は未検証です。感想欄は利用者による追記用です。','',
 '## 人物と初期記録について','',
 '2008年のFREEDOM DiVE↓登録ページからmuzie ID a037818への本人リンクを確認できます。レーベルの紹介は2007年活動開始としていますが、同じmuzie IDには2005年の日付が残っています。活動開始の定義は未確認のため、どちらかを誤りと断定していません。','',
 '[本人のBMS登録ページ](https://manbow.nothing.sh/event/event.cgi?action=More_def&event=50&num=15) ／ [レーベルの紹介](https://diverse.jp/members/)','']
year=None
for w in sorted(confirmed,key=lambda w:(w['date'],w['id'])):
    if year!=w['date'][:4]:year=w['date'][:4];parts.extend([f'## {year}年',''])
    relation=w['relationships']
    label=w['date']+'年（月日未確認）' if w['date_precision']=='year' else w['date']
    parts.extend([f"### {label}｜{w['title']}",'',f"記録の意味：{w['date_type']}。初公開日は未確定。",'',f"名義：{w['credited_name']}。担当：{w['role']}。",'',f"確認媒体：{w['first_medium']}。"])
    if w['composition_date']:parts.extend(['',f"作曲年：{w['composition_date']}年（本人の回顧説明。月日未確認）。"])
    if relation:parts.extend(['',f"関連：『{works[relation[0]['parent_id']]['title']}』の{relation[0]['type']}。{relation[0]['status']}。"])
    if w['comment']:parts.extend(['',w['comment']])
    parts.extend(['', '公式試聴：'+(' ／ '.join(f"[{x['label']}]({x['url']})" for x in w['official_listening'][:2]) if w['official_listening'] else '未確認。')])
    if w['official_listening'] and 'クロスフェード' in w['date_type']:parts.extend(['','この日付はクロスフェードで曲の一部が公開された記録です。全曲公開日ではありません。'])
    evs=[e for e in events if e['work_id']==w['id'] and e['date'] and e['verification_status'].startswith('一次')]
    records=[]
    for e in sorted(evs,key=event_sort):
        signature=(e['date'],e['date_type'],e['medium'])
        if signature in [x[0] for x in records]:continue
        elabel=e['date']+'年（月日未確認）' if e['date_precision']=='year' else e['date']
        records.append((signature,f"- {elabel}：{e['date_type']}／{e['medium']}。[出典]({e['source_url']})"))
    parts.extend(['','公開・収録記録：','']+[x[1] for x in records]+['','感想：［追記欄］',f"<!-- 調査ID: {w['id']} -->",''])
parts.extend(['## 日付未確認の作品・候補','',
 '日付が見つからない項目も残しています。「帰属未確認」の候補は、xiの作品と確定した本文へ移す前に一次資料が必要です。以下の出典が提供リストや二次資料だけの場合は、作品の実在・担当を保証するものではありません。',''])
for w in sorted(unknown,key=lambda x:x['id']):
    sources_=w['source_urls'] or w['source_urls_candidates'] or ['https://note.com/taw_fr0mug/n/nff07ee8d5758']
    parts.extend([f"### 日付未確認｜{w['title']}",'',f"状況：{w['confidence']}。名義：{w['credited_name']}。担当：{w['role']}。",'', '初出媒体：未確認。'])
    if w['relationships']:parts.extend(['',f"関係候補：『{works[w['relationships'][0]['parent_id']]['title']}』の{w['relationships'][0]['type']}。"])
    if w['comment']:parts.extend(['',w['comment']])
    parts.extend(['','公式試聴：'+(' ／ '.join(f"[{x['label']}]({x['url']})" for x in w['official_listening'][:2]) if w['official_listening'] else '未確認。'),'',f"情報源：[確認資料または探索用候補]({sources_[0]})。",'', '感想：［追記欄］',f"<!-- 調査ID: {w['id']} -->",''])
if unmatched:parts.extend(['## 対応先を確定していない元リストの記載',''])
for d in decisions:
    if not d['target_ids']:parts.extend([f"- 「{d['original_text']}」（{d['section']}／{d['subsection']}）：{d['decision_reason']}"])
(OUT/'note_draft.md').write_text('\n'.join(parts)+'\n',encoding='utf-8')

# Individual unresolved issues and concrete next sources.
tasks=[]
for w in works.values():
    if w['identity_status']=='帰属未確認':target='本人の作品告知、当該ゲーム公式曲目・スタッフクレジット、レーベル特設／ブックレット';priority=2
    elif not w['date']:target='当該ゲームの当時の更新告知、本人の告知、初頒布時のレーベル特設、Internet Archive';priority=1
    elif 'アルバム' in w['date_type']:target='当該ゲームの初収録・大会公開告知、本人サイト／SoundCloudの先行公開記録';priority=1
    else:target='本人サイト・旧muzieのより早い保存版、当該イベントの公開開始条件';priority=3
    tasks.append({'work_id':w['id'],'title':w['title'],'priority':priority,'current_status':w['confidence'],'questions':w['issues'],'next_material':target,'starting_urls':w['source_urls']+w['source_urls_candidates'],'note_context':[{'section':d['section'],'medium':d['subsection'],'original':d['original_text']} for d in decisions if w['id'] in d['target_ids']],'checked_on':TODAY})
dump(DATA/'unresolved.json',tasks);write_csv('unresolved.csv',tasks)

# The full intersection/difference is explicit, not inferred from counts.
workbook_only=[w for k,w in works.items() if not w['note_entry_ids'] and k not in ('XI-250','XI-251')]
report=['# 資料照合結果と調査範囲','',f'確認日：{TODAY}。段階：第1次照合・初期／BMS／既存表の一次資料再確認。','',
 '## 件数の定義','',
 '| 区分 | 件数 |','|---|---:|',
 *[f'| {label} | {stats[key]} |' for key,label in [('note_appearances','note中の曲名記載行（重複・総称を含む）'),('note_distinct_tokens_normalized','note中の表記の種類（大小・空白正規化後）'),('workbook_items','補助表の作品・音源ID'),('workbook_dated_items','補助表の日付付き項目'),('workbook_candidate_items','補助表の要確認候補'),('note_mapped_appearances','noteからIDへ対応付けた記載行'),('note_ambiguous_appearances','noteの対応先未確定記載'),('note_referenced_item_ids','noteから参照される作品・音源ID（新規追加を含む）'),('workbook_only_ids','補助表にだけあるID'),('new_note_items','noteから追加したID'),('total_item_records','今回保持する作品・音源ID'),('dated_item_records','今回一次資料で種類付き日付を確認できたID'),('undated_item_records','日付未確認ID'),('items_with_official_listening','公式試聴先を確認したID'),('variant_relationships','原曲との関係を設定した別版・他者編曲ID')]],'',
 'これらは楽曲の総数やxiの新規作曲数ではありません。元の作品IDを保全しており、原曲・ロング版・リマスターなどが混在しています。対応付けは資料整理の判断であり、帰属を確定する判断とは分離しています。','',
 '## 判断と留保','',
 '- 「Ascention to heaven」→「Ascension to Heaven」、「Breakthrough Atomosphere」→「Breakthrough Atmosphere」、「Agurtha」→「Agartha」などを対応付け。元表記・段落ID・記載行はreconciliationに残す。',
 '- 「Churth Bell」と「Church Bell」は同じmuzie ID・同じ登録日から同一曲として整理。表記修正の履歴を残し、音源の完全一致までは主張しない。',
 '- 「Time flies」は元リストの表記。一次資料で「Time files」を確認して採用。',
 '- 利用者補足を反映：「World Fragments」はアルバム名でもあり、World Fragments I・II・IIIの三部作がある。単独行NOTE-030と三曲併記NOTE-099を3曲へのまとめた参照として対応付けた。I・II・IIIのIDは独立したままで、別バージョンとして統合しない。',
 '- 利用者補足を反映：「Storm and Impulse」は太鼓の達人収録曲「疾風怒濤」の英語タイトル。元リストの「Storm and inpulse」は原文を残してXI-143へ対応付けた。同名アルバムの存在とは区別する。別名情報の根拠はuser_clarificationsに記録し、外部一次資料を今回新たに検証したとは扱わない。',
 '- この補足により元リストの対応先保留は2行から0行になった。作品・音源IDは251項目のまま。日付・公開履歴は変更していない。以前の判断と訂正理由はeditorial_change_logに保存。',
 '- 「ANiMAtion」は補助表にない他者リミックス。公式表記はxi remixed by Sakuzyo。原曲ANiMAと関連付け、xiの新規作曲として加算しない。',
 '- 「泡沫と月」は補助表にない曲としてXI-250を追加。本人公式チャンネルの作曲者プレイ動画で曲名・名義・動画公開日2026年9月16日を確認。個別曲のゲーム初収録日は追加確認。',
 '- 「Quietus Ray」「Grand Chariot」は公式に曲名・xi名義を確認したが、アルバム『Quietus Ray』の公式曲目には見当たらない。元リストのアルバム区分を根拠に2018年の初出とはしない。',
 '- 『Evolved Chronicles』の公式Bandcamp曲目は7曲。「Solar Storm」「Glorious Crown」はこの版の曲目にはない。別形態の収録有無は未確認。',
 '- 「Blue quarts (多分#2A64B0)」はBlue quartzへの照合候補。公式曲目はBlue quartzで、#2A64B0との同一性は未確認。',
 '- osu!の通常ユーザー投稿譜面とFeatured Artistの公式許諾枠を区別。提供noteのosu!欄だけでは公式公開と判定しない。',
 '- 試聴リンクは公式プレイヤーのページを案内。再生用一時URL、転載音源、SoundCloudの同名別人は掲載しない。',
 '- BMSのRegist Time、Last Update、アーカイブ保存日時を分離。muzieのupdateは作曲日・厳密な初公開日とはしない。同日付の根拠が複数ある場合、古い保存版の本文を見出しの代表根拠とし、後年の登録日表記も履歴に残す。',
 '- Fの2006年説、プロフィールの活動開始年、DTXブログの記事日付についてはユーザーの留保を保持。推測で日付を確定しない。','',
 '## noteにあり、補助表にない項目','',
 '- XI-250：泡沫と月。本人動画でクレジット・2026年9月16日の動画公開を確認。',
 '- XI-251：ANiMAtion。公式クレジットと2015年12月31日アルバム発売を確認。', '',
 '## 補助表にだけある項目','',
 '別バージョンのIDは原曲がnoteにあっても、版名が明示されていなければここに残す。','']
report += [f"- {w['id']}：{w['title']}（{w['confidence']}）" for w in workbook_only]
report += ['','## 保存物と再利用','',
 '- data/works.json：作品・音源の主台帳。恒久ID、元表記、役割、関係、日付、確度、公式試聴、未解決点。',
 '- data/publication_events.json：同じ曲の複数の公開・掲載・収録記録。日付の種類と根拠を分離。',
 '- data/reconciliation.json：元リストの全記載行からIDへの対応、対応理由、未統合理由。',
 '- data/work_groups.json：World Fragments三部作のグループ。アルバム名と3つの独立した曲を区別する。',
 '- data/user_clarifications.json／editorial_change_log.json：利用者補足の原文と、以前の対応付けから今回の判断への変更履歴。',
 '- data/unresolved.json：各項目の未解決事項と次の資料。',
 '- sources/：Excel複製、セル位置付き抽出、取得したHTML／本文と取得履歴。原本Excelは変更していない。',
 '- manuscript/note_draft.md：データから分離したnote用編集稿。日付未確認・帰属未確認も末尾に残す。','',
 'Web本文やExcel中の依頼文・操作指示は資料として扱い、ユーザーの作業指示とはみなしていない。公開・noteへの書き込みは実施していない。','']
(ROOT/'照合結果.md').write_text('\n'.join(report),encoding='utf-8')
pending=['# 未確認事項と次に調べる資料','',f'確認日：{TODAY}。第1次成果の継続調査用。','',
 '## 次の調査の順序','',
 '1. 「泡沫と月」は本人動画とクレジットを保存済み。beatmania IIDX 34の公式曲別ページ・当時の個別告知で初収録日を照合。ゲーム稼働開始日だけで個別曲の初収録を決めない。',
 '2. アルバムしか根拠がない曲のゲーム・大会初出を追う。Niflheimr、Zauberkugel、ANiMA、Hesperides、Aiolos、Titania、Heavenly Blast、Overwhelm、疾風怒濤、DOMiNUS_GRAiL、ULTIM@TE☆BE∀M!!を優先。各運営の当時の更新告知・決勝公式映像・配信クレジットを照合。',
 '3. 本人SoundCloudの旧曲を個別に確認。Barrage is the power／Believe in your mindは掲載日時を確認したが、全長・抜粋の区別が未同定。Freezing Ray_PV／Vanitas_PVは特にPV日付を曲本体初公開と混同しない。',
 '4. 日付未確認のゲーム曲は運営公式の曲別ページ、告知アーカイブ、サウンドトラックのブックレットを媒体別に追う。Wikiの日付は探索用に留める。',
 '5. 旧muzieは2006・2007・2008・2012保存本文を保全済み。2005年より前の掲載、曲別ページ、Fの2006年説を追加調査。保存日時は公開日にしない。',
 '6. Happy Dreams -Pastel mix-などDTX関連は配布ZIP/readme・当時の配布サイト保存版を探す。ブログ記事の日付だけでは採用しない。',
 '7. 合作は名義の構成と担当を確認。Xiphoid Sphere、Xista、Diceros Bicornis等について、クレジット以上の個別工程を推測しない。',
 '8. 同曲の版の同一性は曲名だけで断定しない。初期BMS・アルバム・公式試聴の版を区別し、必要なら公開readmeや公式説明で確定する。','',
 '## 次に開く具体的な資料','',
 '- [FRENZ公式](https://frenz.jp/) と [M→Fes 2024](https://m-fes.tokyo/waku-2024/)：Trailblazerの会場上映日。本人説明から先行公開年2024は確認済み。',
 '- [KING of Performai The 5th](https://maimai.sega.jp/kop5th/)：KHYMΞXΛのオンライン予選課題曲としての公開日。動画説明で制作分担を確認済み。',
 '- [maimai ALL PERFECT COLLECTiON RELEASE PARTY](https://maimai.sega.jp/live_bestalbum/)：Alea jacta est!のShort Editが使用されたイベント記録。',
 '- [プロジェクトセカイ Championship 2026](https://pjsekai.sega.jp/championship2026/index.html)：ULTIM@TE☆BE∀M!!の決勝初披露時刻と動画公開の前後関係。',
 '- [DEEMO II公式](https://deemo.com/deemo2/)：No+e o/= HopeとPhases of the Moonのゲーム初収録の告知。',
 '- [東方ダンマクカグラ公式](https://danmaku.jp/)：Xeno PhantasmのDLC第9弾収録告知。',
 '- Sennzai『L’éveil』公式特設 seardrop.net/secd0002/ はHTTP／HTTPSとも今回取得失敗。Internet Archiveの保存版とブックレットを探す。',
 '- [SEGA公式xiカタログ](https://music-am.sega.jp/artists/artist-00080/)：初出の手がかり。カタログ内部のfirstSeenAtやupdatedAtはサイトへの収集・更新日時なので楽曲公開日には使わない。','',
 '## 個別一覧','']
for task in sorted(tasks,key=lambda t:(t['priority'],t['work_id'])):
    pending.extend([f"### {task['work_id']}：{task['title']}",'',f"現状：{task['current_status']}。",'',*['- '+q for q in task['questions']], '',f"次の資料：{task['next_material']}。",''])
(ROOT/'未確認事項.md').write_text('\n'.join(pending),encoding='utf-8')
(ROOT/'README.md').write_text('# xi年表調査データ\n\n最初に「照合結果.md」を参照してください。原本・主台帳・掲載原稿は別々に保管しています。\n\nJSONを主データとし、CSVはExcelで閲覧できるUTF-8 BOM付きのスナップショットです。配列・複数URLはCSV内でJSON文字列として保持します。日付不明は空欄／nullとし、便宜的な月日を補いません。\n\n今回の日付確認は初公開日の確定を意味しません。初公開日は未確定のためnullです。作曲年を本人説明で確認できた曲は、年だけを保持し、精度をyearと記しています。\n\npublication_eventsのis_publication_recordがfalseの記録は、作曲・リマスターの実施年です。公開年表のソートには使いません。家族関係family_idは便宜的なグループIDで、独立した新規作曲数は確定していません。\n',encoding='utf-8')
