"""Reproduce individually reviewed game claims from preserved source bytes.

The explicit maps are reviewed title/credit correspondences, not fuzzy matching.
This does not establish game first-release dates or convert aliases into xi.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SAVED = ROOT / 'sources/game-song-audit-20261025'
CHECKED = '2026-10-25'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def saved(url):
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    meta = load(SAVED / (key + '.meta.json'))
    assert meta['status'] == 'retrieved', url
    data = (SAVED / (key + '.bin')).read_bytes()
    assert hashlib.sha256(data).hexdigest() == meta['sha256']
    # Several KONAMI responses declare Shift_JIS while their body is UTF-8.
    # Read the preserved bytes without changing the originally saved derivatives.
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('cp932')


def plain(text):
    return ' '.join(unescape(re.sub(r'<[^>]*>', ' ', text)).split())


def enrich_research(games, works):
    additions=load(DATA/'research_additions.json')
    for game in games:
        for track in game['tracks']:
            if track['source_kind']=='secondary':
                continue
            id=track['work_id']
            extra=additions.setdefault(id,dict(title=works[id]['title'],sources=[],records=[],listening=[],issues=[]))
            extra['checked_on']=CHECKED
            kind='primary' if track['source_kind']=='primary' else 'secondary'
            prefix='メーカー原資料の転載。' if track['source_kind']=='primary_reproduction' else ''
            evidence=dict(kind=kind,label=track['source_label'],url=track['source_url'],
                locator=track['edition'],credit=track['credited_name'],summary=prefix+track['evidence'],
                identity_note=track['identity_note'] or '公式の曲別名義を確認。対象xi本人への帰属は別に判定し、未確認の別名義を自動昇格させない。',checked_on=CHECKED)
            extra.setdefault('sources',[])
            if not any(s['url']==evidence['url'] and s['locator']==evidence['locator'] for s in extra['sources']):
                extra['sources'].append(evidence)
            for supporting in track['extra_sources']:
                if supporting['kind']!='primary': continue
                support=dict(kind='primary',label=supporting['label'],url=supporting['url'],
                    locator=track['title']+'・関連する公式コメント',credit=track['credited_name'],summary=supporting['summary'],
                    identity_note='同じ公式イベント内の作者コメントで名義の対応を補強。',checked_on=CHECKED)
                if not any(s['url']==support['url'] and s['locator']==support['locator'] for s in extra['sources']):
                    extra['sources'].append(support)
            if id in {'XI-193','XI-208'}:
                assert 'com_giko_31' in saved(track['source_url'])
                extra.update(verified_credit=True,credited_name=track['credited_name'],role=track['role'])
            for link in [track['listening']] if track['listening'] else []:
                if not any(x['url']==link['url'] for x in extra.setdefault('listening',[])):
                    extra['listening'].append(link)
            if track.get('publication_record'):
                record=track['publication_record']
                if not any(r['id']==record['id'] for r in extra.setdefault('records',[])):
                    extra['records'].append(record)
                issue='動画公開日をゲーム初収録日・作曲日・真の初公開日とはしない。先行公開の有無は未確認。'
                if issue not in extra['issues']: extra['issues'].append(issue)
            if id=='XI-171':
                extra['credited_name']='Hekatoncheir'
                issue='IIDX公式のBeyond Evolution名義はHekatoncheir。対象xi本人との対応を示す一次資料は未取得。'
                if issue not in extra['issues']: extra['issues'].append(issue)
            if id in {'XI-205','XI-232'}:
                date='2017-01-05' if id=='XI-205' else '2021-12-23'
                record_id='GAME-AUDIT-'+id
                record=dict(id=record_id,date=date,precision='day',kind='ゲーム楽曲実装日（メーカー資料転載）' if id=='XI-205' else 'ゲームイベント解禁開始日',
                    medium=game['title'],source_url=track['source_url'],evidence=track['evidence'],version=track['title'],checked_on=CHECKED,
                    true_first_publication_confirmed=False)
                if not any(r['id']==record_id for r in extra.setdefault('records',[])):
                    extra['records'].append(record)
                issue='確認できたゲームの公開記録。作曲日・真の初公開日、先行試聴の有無は未確認。'
                if issue not in extra['issues']: extra['issues'].append(issue)
    (DATA/'research_additions.json').write_text(json.dumps(additions,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def build():
    works = {w['id']: w for w in load(DATA / 'works.json')['works']}
    games = []

    def game(id, title, note):
        value = dict(id=id, title=title, note=note, tracks=[])
        games.append(value)
        return value['tracks']

    def add(tracks, number, title, credit, url, evidence, *, kind='primary',
            edition='', role='', note='', listing='収録', label='', listening=None,
            identity='', extra_sources=None):
        id = f'XI-{number:03}'
        assert id in works
        assert not any(t['work_id'] == id for t in tracks), (id, title)
        tracks.append(dict(work_id=id, title=title, credited_name=credit, role=role,
            source_url=url, evidence=evidence, checked_on=CHECKED, source_kind=kind,
            source_label=label, edition=edition, note=note, listing_kind=listing,
            listening=listening, identity_note=identity, extra_sources=extra_sources or []))

    sega_map = {
        'Crimson Phoenix':177, 'Longinus':96, 'Aragami':59, 'Halcyon':26,
        'FREEDOM DiVE':17, 'Dreadnought':69, 'Parousia':34,
        'Ascension to Heaven':21, 'Aiolos':166, 'Titania':141,
        'Stargazing Dreamer':226, 'DOMiNUS_GRAiL':158, 'Sparking Revolver':225,
        '創 -汝ら新世界へ歩む者なり-':244, 'Glorious Crown':188,
        'Lunar Mare':198, 'Heavenly Blast':192, 'Mjölnir':123,
        'KHYMΞXΛ':196, 'Xaleid◆scopiX':154, 'ANiMA':72, 'RE!NCARN4T10N':155,
        'ナイト・オブ・ナイツ (xi Remix)':116, 'Op.I《fear-TITΛN-》':209,
        'Got more raves? -xiRemix-':84,
    }
    catalogue_rows = []
    for id, name, url, expected in [
        ('chunithm','CHUNITHM','https://chunithm.sega.jp/storage/json/music.json',14),
        ('maimai','maimai','https://maimai.sega.jp/data/maimai_songs.json',12),
        ('ongeki','オンゲキ','https://ongeki.sega.jp/assets/json/music/music.json',10),
    ]:
        tracks = game(id, name, '公式公開曲目で曲名・名義を照合。追加譜面は同じ曲にまとめています。初収録日と音源の版は別途確認中です。')
        rows = json.loads(saved(url))
        selected = [r for r in rows if re.search(r'(?<![a-z])xi(?![a-z])',r['artist'],re.I) or r['title']=='KHYMΞXΛ']
        grouped = {}
        for row in selected:
            title = row['title'].removeprefix('[蔵]')
            assert title in sega_map, title
            grouped.setdefault(title, []).append(row)
        assert len(grouped) == expected
        for title, matching in grouped.items():
            credit = matching[0]['artist']
            row_ids = [str(r.get('id', r.get('sort'))) for r in matching]
            evidence = f'SEGA公式{name}の公開曲目に「{title} / {credit}」を確認。対応する一覧レコード：{", ".join(row_ids)}。'
            note = '公開データのdate・release・version値は初収録日に採用していない。'
            if len(matching)>1:
                note += ' 追加譜面のレコードを新曲として数えず、同じ作品IDへ関連付けた。'
            if title=='Mjölnir':
                note += ' ゲームサイズ版XI-134との音源同定は保留。曲名だけから別バージョンIDへ結び付けない。'
            add(tracks, sega_map[title], title, credit, url, evidence,
                edition=name, label=f'{name}公式・公開曲目データ', note=note)
        catalogue_rows.append(dict(game_id=id, source_url=url, total_rows=len(rows),
            selected_rows=len(selected), unique_works=len(grouped)))

    sdvx = game('sdvx','SOUND VOLTEX', '公式曲検索を曲ごとに照合。曲別クレジットとxi本人への帰属は区別して記録しています。初収録日は未確認です。')
    sdvx_ids = [200,173,189,241,239,168,228,216,183,99,164,184,197,190,234,194,236,238,185,215,195,223]
    urls = load(DATA / 'game-song-audit-sdvx-urls.json')[1:]
    for number, url in zip(sdvx_ids, urls, strict=True):
        rows = re.findall(r'<div class="info">\s*<p>(.*?)</p>\s*<p>(.*?)</p>',saved(url),re.S)
        assert len(rows)==1,(url,len(rows))
        title, credit = map(plain,rows[0])
        add(sdvx, number,title,credit,url,
            f'KONAMI公式曲検索の当該曲結果に「{title} / {credit}」を確認。検索語だけでなく返された曲別クレジットを照合。',
            edition='SOUND VOLTEX（アーケード）',label='SOUND VOLTEX公式・曲別検索結果',
            note='検索結果には初収録日がないため、日付は未採用。')
    extra = {'FREEDOM DiVE':17,'Aragami':59,'Dreadnought':69,'Halcyon':26,'Parousia':34}
    url='https://p.eagate.573.jp/game/sdvx/vii/music/index.html?search_name=xi'
    rows=re.findall(r'<div class="info">\s*<p>(.*?)</p>\s*<p>(.*?)</p>',saved(url),re.S)
    for t,c in rows:
        title,credit=plain(t),plain(c)
        if title in extra:
            add(sdvx,extra[title],title,credit,url,
                f'KONAMI公式検索の実際の曲目に「{title} / {credit}」を確認。',
                label='SOUND VOLTEX公式曲検索',edition='SOUND VOLTEX（アーケード）')
    assert len(sdvx)==27
    alias='https://p.eagate.573.jp/game/sdvx/sv/p/floor/original/26/index_2.html'
    assert 'Innocent Tempest' in saved(alias) and 'BlackY' in saved(alias) and 'xi' in saved(alias)
    tempest=next(t for t in sdvx if t['work_id']=='XI-195')
    tempest['role']='合作（Diceros Bicornis：xi・BlackY）。Innocent Tempest自体の工程別分担は未確認。'
    tempest['extra_sources']=[dict(url=alias,kind='primary',label='SDVX公式・ЯeviveR採用コメント',
        summary='BlackYがInnocent Tempest以来6年ぶりのxiとの合作と説明。Diceros Bicornisとxi・BlackYの対応を補強。')]

    iidx=game('iidx','beatmania IIDX','曲別の公式紹介・本人動画を照合。Hekatoncheir名義とxi本人の対応は未確認として残しています。')
    for version, song, number, title in [
        (29,'09',167,"Angel's Ladder"),(29,'32',221,'Silver Bullet'),
        (30,'44',171,'Beyond Evolution'),(30,'09',249,'響花水月'),
        (31,'24',245,'夢縁'),(32,'19',219,'Satellite Burst'),(33,'23',242,'ιgniЯRuina')]:
        url=f'https://p.eagate.573.jp/game/2dx/{version}/newsong/song{song}.html'
        text=plain(saved(url)); assert title in text
        credit='Hekatoncheir' if number==171 else ('xi feat. Risa Yuzuki' if number in {249,245,242} else 'xi')
        assert credit in text
        add(iidx,number,title,credit,url,f'KONAMI公式IIDX {version}の曲別紹介に「{title} / {credit}」と制作コメントを確認。',
            edition=f'beatmania IIDX {version}',label='IIDX公式・曲別紹介',
            note='公式表記はHekatoncheir。xi本人の別名義とする一次根拠は未取得。' if number==171 else '')
    # This work's creator video already existed, but verify its complete metadata.
    url='https://www.youtube.com/watch?v=phiCv9e4fZA'
    assert 'UCwzcz476gcGbMnXyxWDUpaA' in saved(url) and '泡沫と月' in saved(url)
    add(iidx,250,'泡沫と月','xi feat. Risa Yuzuki',url,
        '本人xi Officialの作曲者プレイ動画・説明欄にIIDX 34 ZINRAI書き下ろし、曲名・名義を確認。',
        edition='beatmania IIDX 34 ZINRAI',label='xi Official・作曲者プレイ動画',note='動画公開日を稼働日・初収録日とはしない。')

    url='https://p.eagate.573.jp/game/infinitas/2/music/index.html'
    infinitas=game('iidx-infinitas','beatmania IIDX INFINITAS','INFINITAS公式曲目で確認。アーケード版とは別の収録記録です。')
    mapping={"Angel's Ladder":167,'Silver Bullet':221,'響花水月':249,'夢縁':245,
        'Satellite Burst':219,'Grand Chariot':190,'SOLID STATE SQUAD -RISEN RELIC REMIX-':224}
    found=set()
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',saved(url),re.S):
        cells=[plain(c) for c in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)]
        if len(cells)>=2 and cells[0] in mapping and 'xi' in cells[1]:
            title,credit=cells[:2]; found.add(title)
            add(infinitas,mapping[title],title,credit,url,
                f'INFINITAS公式曲目のタイトル・アーティスト欄に「{title} / {credit}」を確認。',
                label='INFINITAS公式・楽曲一覧',edition='beatmania IIDX INFINITAS',
                role='リミックス（Remixed by xi）' if mapping[title]==224 else '')
    assert found==set(mapping),(found,set(mapping))

    url='https://www.famitsu.com/news/201701/05124256.html'
    assert all(t in saved(url) for t in ['Minerva','xi','以下、リリースより'])
    rev=game('crossbeats-rev','crossbeats REV. SUNRISE','メーカー配布資料の転載にある曲別クレジットを掲載。CROSS×BEATSとは区別しています。')
    add(rev,205,'Minerva','xi',url,
        'ファミ通記事の「以下、リリースより。」以降のカプコン配布資料にMinerva / xi、実装日2017年1月5日4:00〜を確認。',
        kind='primary_reproduction',label='カプコン配布資料の転載（ファミ通）',edition='crossbeats REV. SUNRISE / REV.SHOP',
        note='メーカー原ページは現行トップへ転送。転載であることを区別する。曲別名義はxiだが本人への直接リンクでの再照合は未完了。')

    cross=game('crossbeats','CROSS×BEATS','収録候補は二次資料に基づく記録です。公式の収録資料が未取得のため、確定した収録と区別しています。')
    url='https://wiki.maplia.jp/cbiOS/music'
    assert 'Hesperides' in saved(url) and 'Keraunos' in saved(url)
    for n,t,c in [(74,'Hesperides','xi'),(80,'Keraunos','Xiphoid Sphere')]:
        add(cross,n,t,c,url,f'【二次資料】CROSS×BEATS Wikiの曲別一覧に「{t} / {c}」を確認。公式ゲーム側の原資料は未取得。',
            kind='secondary',label='CROSS×BEATS Wiki（非公式）',edition='CROSS×BEATS（iOS）',listing='収録候補',
            note='曲自体の帰属は公式アルバム等で別途確認。二次資料の追加日を初収録日として採用しない。',
            extra_sources=[dict(url='https://wiki.maplia.jp/cbiOS/music/comment',kind='secondary',label='非公式・ライナーノーツ転記',summary='原文掲載元は未取得。本人による直接の公式発言とは扱わない。')])

    def video(tracks,n,url,channel,words,edition,role='',identity='',basis=''):
        html=saved(url)
        m=re.search(r'var ytInitialPlayerResponse\s*=\s*(\{.*?\});',html)
        assert m,url
        player=json.loads(m[1])
        d=player['videoDetails']
        assert d['channelId']==channel
        assert all(word in d['title']+'\n'+d['shortDescription'] for word in words)
        title=works[f'XI-{n:03}']['title']
        credit='xi VS Sakuzyo' if n==163 else 'xi'
        add(tracks,n,title,credit,url,
            f'公式動画「{d["title"]}」の曲名・制作クレジットを説明欄まで確認。',edition=edition,role=role,
            label=d['author']+'・公式動画',identity=identity,
            listening=dict(url=url,label=d['author']+'公式YouTube',version='公式公開音源',
                official_basis=basis,officialness_source_url=url,
                availability='動画ページと公式公開の根拠を確認。音声の聴取は未実施。'))
        timestamp=player['microformat']['playerMicroformatRenderer']['publishDate']
        published=datetime.fromisoformat(timestamp)
        assert published.tzinfo is not None
        date=published.astimezone(timezone(timedelta(hours=9))).date().isoformat()
        tracks[-1]['publication_record']=dict(id=f'GAME-VIDEO-XI-{n:03}',date=date,precision='day',
            kind='公式動画公開日（日本時間）',medium=edition+'・公式YouTube',source_url=url,
            evidence=f'公式曲別動画のpublishDate={timestamp}を日本時間に換算。曲別のクレジット・公式公開元も照合。ゲームの初収録日は未確認。',
            version=title,checked_on=CHECKED,true_first_publication_confirmed=False)

    seven=game('sevens-code',"SEVEN’s CODE",'公式楽曲動画で作曲・編曲担当を確認。初収録日は未確認です。')
    anchor='https://felion-e.jp/svczero/discography/'
    assert 'UC-OPMM87wdZrlxlHQAGSIjA' in saved(anchor)
    video(seven,174,'https://www.youtube.com/watch?v=8Lo6ZH2NKUc','UC-OPMM87wdZrlxlHQAGSIjA',
        ['Ceyx','作曲：xi','編曲：xi'],"SEVEN’s CODE",role='作曲・編曲：xi。ジャケット：Saty.。',
        basis='ゲーム公式サイト・開発元へのリンクに加え、Felion Soundsの公式サウンドトラック案内が同じYouTubeチャンネルへリンク。')
    seven[0]['extra_sources']=[dict(url=anchor,kind='primary',label='Felion Sounds公式サウンドトラック案内',summary='Ceyx / xiと公式チャンネルへのリンクを確認。サントラ配信開始日をゲーム収録日へ転用しない。')]
    paradigm=game('paradigm-reboot','Paradigm: Reboot','TunerGamesの公式曲別動画で確認。合作の個別分担と初収録日は未確認です。')
    for n,url in [(163,'https://www.youtube.com/watch?v=XLRzISm_Y18'),(208,'https://www.youtube.com/watch?v=sWUyYtR1gCc')]:
        video(paradigm,n,url,'UCvQYCVddcnnC0FcobCV6XRw',['Composed by','xi','Paradigm'], 'Paradigm: Reboot',
            role='合作（xi VS Sakuzyo）。個別の工程別分担は未確認。' if n==163 else '作曲：xi',
            identity='Noctilucaの説明欄にxi Official Xとしてcom_giko_31への直接リンク。' if n==208 else '',
            basis='開発元TunerGamesの動画。ゲームの著作権表記・正規アプリへのリンクを確認。Noctilucaでは本人com_giko_31への直接リンクも確認。')

    url='https://p.eagate.573.jp/game/nostalgia/op3/news/news.html'
    text=saved(url)
    block=re.search(r'<dl class="cl_news" data-date="20211222-02".*?</dl>',text,re.S)[0]
    assert all(x in block for x in ['12月23日(木)10:00','The Dynamics of an Asteroid / xi'])
    nos=game('nostalgia','ノスタルジア Op.3','公式イベント告知で楽曲と解禁開始日時を確認。告知日と解禁開始日は別の記録です。')
    add(nos,232,'The Dynamics of an Asteroid','xi',url,
        '公式ニュースdata-date=20211222-02で、12月23日(木)10:00よりイベント特典として解禁可能、The Dynamics of an Asteroid / xiと明記。',
        label='ノスタルジア公式・2021-12-22告知',edition='ノスタルジア Op.3 / 絢爛なるピアノの調べ',
        note='2021-12-22は告知日、2021-12-23 10:00は解禁開始。作曲日や真の初公開日とはしない。')
    url='https://p.eagate.573.jp/game/eacnostalgia/op3/info/music.html'
    assert 'The Dynamics of an Asteroid' in saved(url) and 'xi' in saved(url)
    nosec=game('nostalgia-konaste','コナステ ノスタルジア','家庭用の曲目をアーケードと区別して掲載。')
    add(nosec,232,'The Dynamics of an Asteroid','xi',url,
        'コナステ公式曲目「楽曲パック vol.7」のタイトル・アーティスト欄でThe Dynamics of an Asteroid / xiを確認。',
        edition='コナステ ノスタルジア / 楽曲パック vol.7',label='コナステ ノスタルジア公式・楽曲一覧')

    url='https://dondafulfestival-20th.taiko-ch.net/music/musicpass_list.php'
    taiko=game('taiko-dondaful','太鼓の達人 ドンダフルフェスティバル','太鼓ミュージックパス公式曲目で確認。アーケードの収録日へ転用しません。')
    text=saved(url)
    for n,t,c in [(143,'疾風怒濤','xi'),(247,'狂瀾怒濤','xi'),(248,'超絶技巧系少女','ねこかぶりサイクロン(xi＋ねこみりん)')]:
        p=text.index(t); segment=plain(text[p:p+600]);assert 'xi' in segment,(t,segment)
        add(taiko,n,t,c,url,f'バンダイナムコ公式ミュージックパス曲目の「{t}」と同じ曲枠にxiを含む名義を確認。',
            edition='Nintendo Switch / 太鼓ミュージックパス',label='太鼓ミュージックパス公式曲目',
            role='合作（ねこかぶりサイクロン：xi＋ねこみりん）。分担未確認。' if n==248 else '',
            note='疾風怒濤はStorm and Impulseの日本語曲名。アルバムのロング版XI-127をこのゲームの別曲として登録しない。' if n==143 else '')
    pop=game('taiko-pop-tap-beat','太鼓の達人 Pop Tap Beat','Apple Arcade版の公式曲目で確認。ほかの版とは別の記録です。')
    url='https://poptapbeat.taiko-ch.net/list/'
    assert '狂瀾怒濤' in saved(url) and 'xi' in saved(url)
    add(pop,247,'狂瀾怒濤','xi',url,'バンダイナムコ公式Pop Tap Beat曲目に狂瀾怒濤 / xiを確認。',
        edition='Apple Arcade / Pop Tap Beat',label='Pop Tap Beat公式曲目')

    deemo=game('deemo','DEEMO','Hypnosはレーベル公式動画で確認。収録候補の項目は非公式Wikiに基づき、ゲーム側の一次資料を照合中です。')
    video(deemo,193,'https://www.youtube.com/watch?v=_r2zheyqHT8','UCsFFRVLzFxS7YTNHW-Ks-qA',
        ['Hypnos','xi Collection','com_giko_31'],'DEEMO / xi Collection',role='作曲者表記：xi',
        identity='レーベルDiverse Systemの曲別動画がArtist xiとして本人com_giko_31へ直接リンク。',
        basis='Diverse System公式チャンネル。公式サイト・レーベルBandcamp、Artist xi本人のcom_giko_31へリンク、Rayark / DEEMO著作権表記。')
    url='https://wikiwiki.jp/deemo/%E6%9B%B2%E5%90%8D%E3%83%AA%E3%82%B9%E3%83%88'
    text=saved(url)
    for n,t,credit,edition in [(34,'Parousia','xi','Cytus selection Vol.2'),(51,'Niflheimr','xi','Cytus selection Vol.2'),
        (72,'ANiMA','xi',"Deemo’s Collection Vol.2"),(107,'To Live','xi','xi Collection'),
        (66,'Cloud9','xi','xi Collection'),(99,'Bad Elixir','xi','xi Collection'),(206,'Mistilteinn','xi','xi Collection'),
        (220,'Scherzo -pain in rain-','xi vs Ice','Ice Collection'),(59,'Aragami','xi','Samsara Collection'),
        (182,'Dusk to Dawn','xi','Funkot Collection'),(96,'Longinus','xi','AD:PIANO Collection')]:
        assert t in text,t
        add(deemo,n,t,credit,url,f'【二次資料】DEEMO Wiki曲目の「{t} / {credit}」を曲別に照合。ゲーム側の曲別一次資料は未取得。',
            kind='secondary',label='DEEMO Wiki（非公式）',edition='DEEMO / '+edition,listing='収録候補',
            note='Wikiの更新日・記載追加日を初収録日に採用しない。原リストのDeemo/Deemo2を両方に割り当てていない。')
    url='https://store.playstation.com/en-cz/product/EP2678-CUSA13139_00-DMVRDLC000000006'
    assert all(t in saved(url) for t in ['Parousia','Niflheimr','Sony Music','Cytus Selection'])
    reborn=game('deemo-reborn','DEEMO -Reborn-','PS4版の販売元提供DLC説明で曲目を確認。モバイル版DEEMOの収録資料とは別の記録です。')
    for n,t in [(34,'Parousia'),(51,'Niflheimr')]:
        add(reborn,n,t,'xi',url,f'正規PlayStation StoreのCytus Selection vol.2商品説明に{t}とTV/VR譜面を確認。作曲名義は既存の公式アルバム資料で照合。',
            edition='PS4 / Cytus Selection vol.2',label='Sony Music提供・PlayStation Store DLC説明',
            note='販売地域の表示発売日を日本版や楽曲自体の初公開日に転用しない。')
    cytus=game('cytus','Cytus','公式資料で確認した曲と、非公式Wikiに基づく収録候補を区別して掲載しています。')
    url='https://wikiwiki.jp/cytus/%E6%9B%B2%E5%90%8D%E3%83%AA%E3%82%B9%E3%83%88'
    for n,t in [(34,'Parousia'),(52,'Zauberkugel'),(51,'Niflheimr'),(218,'REVOLUXIONIST'),(17,'FREEDOM DiVE')]:
        assert t in saved(url)
        add(cytus,n,t,'xi',url,f'【二次資料】Cytus Wiki曲目の{t}とxi名義を曲別に照合。ゲーム側の原資料は未取得。',
            kind='secondary',label='Cytus Wiki（非公式）',edition='Cytus',listing='収録候補',
            note='公式OSTが存在しても、それだけから収録版・初収録日を確定しない。')
    voez=game('voez-switch','VOEZ（Nintendo Switch）','国内販売元の公式曲目で確認。モバイル版への収録を意味しません。')
    url='https://flyhighworks.heteml.net/games_b/gallery/voez'
    assert 'Ascension to Heaven' in saved(url)
    add(voez,21,'Ascension to Heaven','xi',url,
        'フライハイワークス公式Nintendo Switch版VOEZの曲目、第116曲にAscension to Heaven / xiを確認。',
        edition='Nintendo Switch / Ver1.0以降収録曲',label='フライハイワークス公式VOEZ曲目',
        note='パッケージ発売日・サイトの著作権年を楽曲の初公開日にしない。')

    arcaea=game('arcaea','Arcaea','OverwhelmはNintendo Switch版の公式曲目で確認。収録候補は非公式Wikiによる別の記録です。')
    for n,t,c,url in [
        (26,'Halcyon','xi','https://wikiwiki.jp/arcaea/Halcyon'),
        (75,'Tiferet','xi + Sta','https://wikiwiki.jp/arcaea/Tiferet'),
        (69,'Dreadnought','Mastermind (xi + nora2r)','https://wikiwiki.jp/arcaea/Dreadnought'),
        (78,'World Fragments III(radio edit)','xi','https://wikiwiki.jp/arcaea/World%20Fragments%20III%28radio%20edit%29')]:
        assert t in unescape(saved(url)),t
        add(arcaea,n,t,c,url,f'【二次資料】Arcaea Wikiの曲別ページ「{t}」でゲーム内収録の記述を照合。運営の曲別一次資料は未取得。',
            kind='secondary',label='Arcaea Wiki（非公式）',edition='Arcaea（モバイル版）',listing='収録候補',
            note='radio editは原曲World Fragments IIIとの関連として保持し、アルバム版と同一音源と確定しない。' if n==78 else 'Wiki記載の追加日を初収録日として確定しない。')

    result=dict(checked_on=CHECKED,games=games,catalogue_scans=catalogue_rows,
        limitations=['二次資料の収録候補を一次資料確認済みへ昇格させない。',
            '収録の証拠と対象xi本人への帰属の証拠を別に管理。別名義から自動で帰属を確定しない。',
            '初収録日と現行配信状況は曲別に追加調査。全媒体・全作品を網羅したという主張ではない。'])
    (DATA/'game_song_findings.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    enrich_research(games, works)
    print('Reviewed findings:',len(games),'collections,',sum(len(g['tracks']) for g in games),'relationships')


if __name__=='__main__':
    build()
