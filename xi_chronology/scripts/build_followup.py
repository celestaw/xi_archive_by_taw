"""Curated additions from downloaded page bodies; input originals stay untouched."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
RAW = ROOT / 'sources/followup-20261024'
DAY = '2026-10-24'
sources = {s['url']: s for p in RAW.glob('*.meta.json') if (s := json.loads(p.read_text(encoding='utf-8')))['status'] == 'retrieved'}
works = {w['id']: w for w in json.loads((DATA / 'works.json').read_text(encoding='utf-8'))['works']}
additions = {}


def text(url):
    return (RAW / (sources[url]['key'] + '.txt')).read_text(encoding='utf-8')


def add(key, url, credit, medium, locator, summary, *, role=None, dates=(), kind='primary',
        identity='曲別の担当表記と、その資料の音楽ゲーム／同人音楽の文脈を照合。名前の一致だけから他分野の同名人物を取り込んでいない。', expect=(), verified=True, version=None):
    body = text(url)
    for token in expect:
        assert token in body, (key, url, token)
    assert credit in body, (key, credit)
    item = additions.setdefault(key, dict(title=works[key]['title'], checked_on=DAY, sources=[], records=[], listening=[], issues=[]))
    evidence = dict(kind=kind, label=sources[url]['title'], url=url, locator=locator, credit=credit,
                    summary=summary, identity_note=identity, checked_on=DAY)
    item['sources'].append(evidence)
    if verified and kind == 'primary':
        item['verified_credit'] = True
        item['credited_name'] = credit
        if role:
            item['role'] = role
    for date, date_kind in dates:
        assert kind == 'primary', 'Secondary dates remain claims, not verified chronology events'
        assert date in body or date.replace('-', '/') in body or date.replace('-', '/') in re.sub(r'(?<=/)(\d)(?=/|\D|$)', r'0\1', body) or date_kind.startswith('アルバム頒布日'), (key, date)
        item['records'].append(dict(id=f"FOLLOW-{key}-{len(item['records'])+1}", date=date, precision='day', kind=date_kind,
            medium=medium, source_url=url, evidence=summary, version=version or works[key]['title'], checked_on=DAY,
            true_first_publication_confirmed=False))
    if not dates and kind == 'primary' and verified:
        item['records'].append(dict(id=f"FOLLOW-{key}-{len(item['records'])+1}", date=None, precision=None,
            kind='公式クレジット・収録掲載（初収録日未確認）', medium=medium, source_url=url, evidence=summary,
            version=version or works[key]['title'], checked_on=DAY, true_first_publication_confirmed=False))
    return item


archive = 'https://web.archive.org/web/20160117174204id_/http://www.music-side.com/disco/011_tiyes-1stcd.htm'
x = add('XI-027', archive, 'xi', 'synchro', 'Disc.2 Remix Side 第10曲',
    '旧100sec Records公式の保存本文で、Disc.2第10曲の曲名・xi名義・原曲Tetrapodを確認。本文の頒布日は2010年12月29日。保存日時ではない。',
    role='リミックス／編曲。原曲：Tetrapod（原曲の個人別作曲担当は追加確認）',
    dates=[('2010-12-29', 'アルバム頒布日（先行試聴の該当曲は未同定）')],
    expect=['10.Tetrapod -vanished waves mix- / xi', '頒布日2010年12月29日'])
x['issues'].append('更新履歴には発売前のDisc.2試聴公開が複数あるが、この曲がどの日に含まれたかは未確認。頒布日を初公開日とはしない。')

url = 'https://booth.pm/ja/items/167603'
x = add('XI-071', url, 'xi', 'LOSTAIR EP', '第4曲・商品説明',
    'Third Brain RecordsのBOOTH曲目と説明で、Nardis原曲のLOSTAIRをxiがリミックスしたことを確認。',
    role='リミックス担当：xi。原曲：Nardis', expect=['LOSTAIR (xi Remix)', '"xi", "NIKITA"によるLOSTAIRのリミックス'])
retail = 'https://www.diverse.direct/third-brain-records/3bcd-0002/'
add('XI-071', retail, 'xi', 'LOSTAIR EP', '第4曲・Release Date',
    '販売店の第4曲にLOSTAIR (xi Remix)／xi、Release Dateに2015/10/25と記載。発売日は販売店の記録として保持。曲の初公開日は未確認。',
    kind='secondary', verified=False, expect=['LOSTAIR (xi Remix)', '2015/10/25'])

add('XI-055', 'https://booth.pm/ja/items/59725', 'xi', 'WBC:DAIDA', '第10曲・商品説明',
    'Diderse SystemのBOOTHで、第10曲Healing World／xiと参加者一覧のxiを確認。Diverse Systemとは綴りが異なる頒布元。本文から発売日は確定しない。',
    expect=['Healing World', 'Tr.10 xi - Healing World'])

nora = 'https://www.nekomirin.com/nmcd0016/'
for key, number, credit, role in [
    ('XI-108', 17, 'ねこかぶりサイクロン(xi+ねこみりん) feat.えみゅう。', '作曲：xi・ねこみりん。編曲：xi。作詞：ねこみりん。歌唱：えみゅう。'),
    ('XI-109', 15, 'xi', '楽曲クレジット：xi。ロング版'),
    ('XI-110', 16, 'Mastermind(xi+nora2r)', 'xi・nora2rの合作曲のExtended Mix。工程の内訳は未確認'),
    ('XI-111', 12, 'xi', '楽曲クレジット：xi。個別の工程は未確認'),
    ('XI-112', 21, 'Festa', 'Lemuriaのロング版。Festa名義。原曲とxiの対応は既存の本人動画・BMS試聴リンクの記録を併用')]:
    title = works[key]['title']
    add(key, nora, credit, 'のらねこさい まとめ', f'楽曲Track {number:02}・インフォメーション',
        f'頒布元公式のTrack {number:02}に『{title}』と『{credit}』を掲載。頒布日は2019年8月12日。原曲の公開日とは区別する。',
        role=role, dates=[('2019-08-12', 'アルバム頒布日（該当収録版・初公開未確定）')],
        expect=[f'Track {number:02}\n{title}', '2019年8月12日'])
additions['XI-108']['comment'] = '公式特設では作曲をxi・ねこみりん、編曲をxiと記載。ゲームサイズとは別の収録版。'

sdvx = 'https://p.eagate.573.jp/game/eacsdvx/iii/p/common/info/sdvx_mlist.html'
for key, credit in [('XI-164','xi'), ('XI-184','xi'), ('XI-185','xi'), ('XI-194','xi'), ('XI-197','xi'), ('XI-234','xi'), ('XI-238','xi')]:
    title = works[key]['title']
    assert re.search(r'(?:^|\n)' + re.escape(title) + r'\n' + re.escape(credit) + r'(?:\n|$)', text(sdvx)), key
    add(key, sdvx, credit, 'コナステ SOUND VOLTEX III', f'曲目一覧／{title}',
        f'KONAMI公式の曲目一覧で『{title}』と対応するアーティスト欄xiを確認。コナステ収録を示す資料で、アーケード初収録日は確定しない。', expect=[title+'\nxi'])
floor = 'https://p.eagate.573.jp/game/sdvx/sv/p/floor/original/10/index.html'
add('XI-195', floor, 'Diceros Bicornis', 'SOUND VOLTEX FLOOR', 'ORIGINAL MUSIC FILE NO.001・xi/BlackYの本人コメント',
    '公式採用ページに曲名とDiceros Bicornis名義があり、xiとBlackYの本人コメントで合作と制作分担を確認。xiはピアノと曲構成、BlackYはそれ以外を主に担当したと説明。',
    role='合作：xi・BlackY。xiは主にピアノ・曲構成（本人コメント）。',
    expect=['Innocent Tempest', 'ピアノとか曲構成とか担当しました。xiです', 'BlackY'])
add('XI-236', sdvx, 'xi underground', 'コナステ SOUND VOLTEX III', '曲目一覧／TU-MA-MI△ALL-NIGHTER',
    '公式曲目にTU-MA-MI△ALL-NIGHTER／xi undergroundを確認。xi undergroundとxi本人の対応を直接示す資料は追加確認。',
    verified=False, expect=['TU-MA-MI△ALL-NIGHTER\nxi underground'])

for key, song_id in [('XI-166','00079'), ('XI-192','01596'), ('XI-225','01966'), ('XI-226','01906')]:
    url = f'https://music-am.sega.jp/songs/song-{song_id}/'
    title = works[key]['title']
    x = add(key, url, 'xi', 'ゲキチュウマイ公式楽曲ポータル', '曲名・ARTIST欄',
        f'SEGA運営の曲別ページで『{title}』とARTIST: xiを確認。ポータルの登録日時をゲーム初収録日に転用しない。', expect=[title, 'ARTIST :xi'])
    links = [u for u in sources[url]['links'] if u.startswith('https://music.apple.com/jp/song/')]
    if links:
        x['listening'].append(dict(url=links[0], label='SEGA公式が案内する正規配信', version='公式ポータルが案内する配信版。初期ゲーム音源との同一性は未確認',
            official_basis='SEGA公式の曲別ページからリンクされた正規配信ページ。', officialness_source_url=url,
            availability='公式ページの案内を確認。実再生・地域制限は未検証'))

for key, number, original, first, general, tr in [
    ('XI-145','0021','Signal of Abydos','2023-04-16','2023-04-30',9),
    ('XI-146','0022','OperationD','2023-10-22','2023-10-29',10),
    ('XI-153','0026','Usagi Flap',None,'2025-04-27',1)]:
    url = f'https://www.nekomirin.com/nmcd{number}/index.html'
    medium = {'0021':'Clippings of youth vol.1','0022':'Clippings of youth vol.2','0026':'Clippings of youth vol.4'}[number]
    dates = [(first, 'アルバム先行頒布日（初公開未確定）'), (general, 'アルバム一般頒布日')] if first else [(general, 'アルバム頒布日（初公開未確定）')]
    x = add(key, url, 'xi', medium, f'Tracklist・Arrangement (tr.{tr})・Release Date',
        f'公式特設の曲目に『{works[key]["title"]}』、StaffにArrangement (tr.{tr})／xi、原曲に{original}を記載。先行販売と一般販売のある巻では両日付を分けた。',
        role=f'編曲／リミックス：xi。原曲：{original}（Blue Archive）', dates=dates,
        expect=[works[key]['title'], f'Arrangement (tr.{tr})', '[Original] '+original])
    x['comment'] = f'『{medium}』収録のブルーアーカイブ楽曲アレンジ。公式特設にxiの編曲担当を記載。'

for key, url, official_title, credit, medium in [
    ('XI-064','https://www.diverse.direct/nekomimi-style/nmcd-0009/',"Let's madness?",'xi underground','竹山風'),
    ('XI-081','https://www.diverse.direct/nekomimi-style/nmcd-0012/','Twinkle Candy','xi','竹山風 弐'),
    ('XI-093','https://www.diverse.direct/nekomimi-style/nmcd-0013/','Tabata Park','xi underground','竹山風 参'),
    ('XI-120','https://www.diverse.direct/nekomimi-style/nmcd-0019/','Leaps and Bounds','xi','竹山風 肆'),
    ('XI-149','https://www.diverse.direct/nekomimi-style/nmcd-0024/','[Library || Codex] of Omen (xi Remix)','xi','Clippings of youth vol.3')]:
    x = add(key, url, credit, medium, '販売店の曲別リスト・頒布元特設へのリンク',
        f'販売店曲目に『{official_title}』／『{credit}』を掲載。入力資料の表記は『{works[key]["title"]}』として保持。名義や表記の対応は別途確認する。',
        kind='secondary', verified=False, expect=[official_title, credit])
    x['issues'].append('販売店の曲目を探索の手がかりとして追加。頒布元の曲別原文・名義対応の確認を継続。')

# The official vol.3 page names both originals and the arranger; keep spelling differences explicit.
key = 'XI-149'; url = 'https://www.nekomirin.com/nmcd0024/index.html'
add(key, url, 'xi', 'Clippings of youth vol.3', 'Tracklist第3曲・Arrangement (tr.3)',
    '公式特設には[Library || Codex] of Omen (xi Remix)、原曲Library of OmenとCodex of Omen、編曲担当xiを記載。入力表記のIIと公式の||の違いを残し、同一項目への対応は要確認とする。',
    verified=False, expect=['[Library || Codex] of Omen (xi Remix)', 'Arrangement (tr.3)'])

url = 'https://blackysbeatfloor.bandcamp.com/album/p-d-m-brillante'
x = add('XI-114', url, 'xi', 'P.D.M.[β] -brillante-', '公式Bandcamp第7曲・credits',
    'BlackYのBandcamp曲目で第7曲Artificial Satellite／xiと、released October 27, 2019を確認。ソロアルバムではなくBlackYの企画への参加曲。',
    dates=[('2019-10-27','アルバム頒布日（初公開未確定）')], expect=['xi - Artificial Satellite','released October 27, 2019'])
html = (RAW / (sources[url]['key'] + '.html')).read_text(encoding='utf-8')
match = re.search(r'href="([^"]*?/track/artificial-satellite[^"]*)"', html)
if match:
    target = match.group(1)
    if target.startswith('/'):
        target = 'https://blackysbeatfloor.bandcamp.com' + target
    x['listening'].append(dict(url=target, label='BlackY公式Bandcamp', version='P.D.M.[β] -brillante-収録版',
        official_basis='BlackYのレーベルBandcamp曲目からの曲別リンク。', officialness_source_url=url,
        availability='曲別ページへの公式リンクを確認。実再生・地域制限は未検証'))

(DATA / 'research_additions.json').write_text(json.dumps(additions, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f"Saved {len(additions)} work additions, {sum(len(x['sources']) for x in additions.values())} sources")
