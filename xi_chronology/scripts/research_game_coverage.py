"""Reproduce the reviewed 2026-10-25 game additions from saved primary pages.

This is a reviewed selection, not an automatic assertion that every xi string
on the web belongs to this composer. No game inclusion dates are inferred.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SAVED = ROOT / 'sources/game-coverage-20261025'
CHECKED = '2026-10-25'


def saved(url):
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    meta = json.loads((SAVED / (key + '.meta.json')).read_text(encoding='utf-8'))
    if meta['status'] != 'retrieved':
        raise ValueError(f'Page not retrieved: {url}')
    return (SAVED / (key + '.html')).read_text(encoding='utf-8')


def build():
    games = []

    def game(id, title, note):
        item = dict(id=id, title=title, note=note, tracks=[])
        games.append(item)
        return item['tracks']

    def add(tracks, id, title, credit, url, evidence, *, listing='収録', edition='',
            role='', listening=None, identity='', label='', note=''):
        tracks.append(dict(work_id=id, title=title, credited_name=credit, role=role,
            source_url=url, evidence=evidence, checked_on=CHECKED, listing_kind=listing,
            edition=edition, listening=listening, identity_note=identity,
            source_label=label, note=note))

    music_api = 'https://mypage.musicdiver.jp/api/music?lang=ja'
    music = json.loads(saved(music_api))['response']['music_list']
    md = game('music-diver', 'MUSIC DIVER', '公式公開曲目から確認した4曲。初収録日は未確認です。')
    matches = {'FREEDOM DiVE↓': 'XI-017', 'Halcyon': 'XI-026',
               'Qualia Crystal': 'XI-214', 'Solar Storm': 'XI-223'}
    for item in music:
        if item['artist_name'] != 'xi':
            continue
        title = item['music_title']
        if title not in matches:
            raise ValueError(f'Unreviewed MUSIC DIVER title: {title}')
        evidence = f'タイトー公式の公開楽曲一覧データ（music_id={item["music_id"]}）に曲名とartist_name: xiを確認。'
        add(md, matches[title], title, 'xi', music_api, evidence,
            label='MUSIC DIVER公式・公開曲目データ',
            note='全収録曲ページが参照する公開API。deliver_start_dateには2021-01-01等の内部値があるため、初収録日に採用しない。',
            identity='公式一覧の同一artist_id=51に既知のFREEDOM DiVE↓・Halcyonと掲載。Qualia Crystalの公式紹介動画は本人xi Officialへリンク。')
    assert len(md) == 4

    video = 'https://www.youtube.com/watch?v=_02OtxIa0xM'
    html = saved(video)
    assert 'UCK1f3UVewDaiLTvUuNqaBHA' in html and 'www.youtube.com/c/xiOfficial' in html
    qualia = next(t for t in md if t['work_id'] == 'XI-214')
    qualia['credit_source_url'] = video
    qualia['listening'] = dict(url=video, label='タイトー公式YouTube', version='公式楽曲紹介映像',
        official_basis='taitochannelのMUSIC DIVER紹介。説明欄にタイトー著作権表記・ゲーム公式サイト・xi本人チャンネルへのリンク。',
        officialness_source_url='https://musicdiver.jp/', availability='紹介映像の掲載を確認。全曲フル尺の公開とはしない。')

    cy = game('cytus', 'Cytus', '公式試聴一覧と日本公式サウンドトラック案内で確認した曲を掲載。ほかの曲は照合中です。')
    url = 'https://rayark.com/g/cytus/mobile/pv.html'
    assert 'Halcyon' in saved(url) and 'by Xi' in saved(url)
    add(cy, 'XI-026', 'Halcyon', 'Xi', url, 'Rayark公式Cytus Song Preview ListでHalcyon / by Xiを確認。',
        label='Rayark公式Cytus試聴一覧', edition='Cytus（モバイル版）',
        listening=dict(url='https://youtu.be/laTdlSCf7mc', label='Rayark公式サイト掲載の試聴', version='Cytus公式紹介映像',
            official_basis='Rayark公式Song Preview ListのHalcyon項目から直接リンク。',
            officialness_source_url=url, availability='公式サイト上のリンク掲載を確認。現在の再生可否は未検証。'))
    url = 'https://cytusjapan.com/music/'
    assert 'Storia' in saved(url) and 'xi vs sakuzyo' in saved(url)
    add(cy, 'XI-227', 'Storia', 'xi vs sakuzyo', url,
        'Cytus日本公式のChapter M-MILLION全10曲を含むサウンドトラック案内にStoria / xi vs sakuzyoを確認。',
        edition='Cytus / Chapter M-MILLION', role='合作（名義：xi vs sakuzyo）。個別の分担は未確認。',
        label='Cytus日本公式・M-MILLION案内', note='CD発売日をゲーム初収録日に使わない。店別CD特典の曲目はゲーム収録の証拠にしていない。')

    url = 'https://apps.apple.com/jp/app/cytus-ii/id1290687550'
    assert 'MESSiΛH COMPL3X / xi' in saved(url)
    cy2 = game('cytus2', 'Cytus II', '開発元提供の更新履歴で確認した曲を掲載。Cytusとの収録関係は別に扱います。')
    add(cy2, 'XI-203', 'MESSiΛH COMPL3X', 'xi', url,
        'RayarkのApp Store掲載更新履歴「Rayark 15th Anniversary Update」に無料追加曲MESSiΛH COMPL3X / xiを確認。',
        label='Cytus II・開発元提供のApp Store更新履歴', edition='Cytus II（iOS版）',
        note='更新履歴の告知と初収録日は別に調べる。Cytus初代への収録を意味しない。')

    cc = game('chrono-circle', 'クロノサークル', '公式BGAで曲名と作曲者を確認。公式曲目ページは取得できず、ほかの収録曲は照合中です。')
    url = 'https://www.youtube.com/watch?v=qZm9hZgEqWk'
    html = saved(url)
    assert 'UC_mBSb1ej-xt0674n86vLow' in html and 'Composer -  xi' in html
    add(cc, 'XI-201', 'MEGALØDON', 'xi', url,
        'CHRONO CIRCLE OFFICIALのBGA説明にTitle - MEGALØDON、Composer - xi、ver.1.270 Updated Songを確認。',
        role='作曲（Composer）：xi。映像：yusi.', label='CHRONO CIRCLE公式BGA',
        identity='公式ゲームの曲別Composer欄と、提供リストのChrono Circle項目を照合。本人への直接リンクによる再照合は未完了。',
        note='公式チャンネルの表示名・Andamiro著作権表記・公式ドメインへのリンクを確認。動画公開日を初収録日にしない。')

    ar = game('arcaea', 'Arcaea', '現在の確認範囲はNintendo Switch版の追加パック。モバイル版とほかの曲は照合中です。')
    url = 'https://www.nintendo.com/us/store/products/esoteric-order-pack-70050000030010-switch/'
    html = saved(url)
    assert 'Overwhelm' in html and 'xi' in html
    add(ar, 'XI-135', 'Overwhelm', 'xi', url,
        'Nintendo公式ストアのArcaea「Esoteric Order Pack」内容にOverwhelm by xiを確認。',
        edition='Nintendo Switch / Esoteric Order Pack', label='Nintendo公式ストア・Arcaea追加パック',
        note='Switch版のパック収録根拠。モバイル版の収録日や、アルバムのLong Versionとは混同しない。')

    gc = game('groove-coaster', 'グルーヴコースター（アプリ版）', 'アプリ版の公式曲目を照合。AC表記はアプリ内アーケードモードへの対応を表します。')
    url = 'https://groovecoaster.com/apps/music.html'
    html = saved(url)
    for id, title in [('XI-026', 'Halcyon'), ('XI-041', 'Valhalla'), ('XI-223', 'Solar Storm')]:
        assert title + ' / xi' in html
        add(gc, id, title, 'xi', url, f'タイトーのアプリ版公式曲目に{title} / xiを確認。',
            label='グルーヴコースター・アプリ版公式曲目', edition='iOS / Android アプリ版',
            note='このページのACはアプリのアーケードモード対応という意味。筐体版の収録根拠へ読み替えない。')
    gcs = game('groove-coaster-switch', 'グルーヴコースター ワイワイパーティー!!!!', 'Nintendo Switch版の公式DLC案内で確認した曲を掲載。ほかのパックも照合中です。')
    url = 'https://groovecoaster.com/switch/dlc.html'
    assert 'Solar Storm / xi' in saved(url)
    add(gcs, 'XI-223', 'Solar Storm', 'xi', url,
        'タイトー公式DLC「オリジナル パック8（アーケードメモリアル特集）」の説明と収録曲目にSolar Storm / xiを確認。',
        edition='Nintendo Switch / オリジナル パック8', label='ワイワイパーティー!!!!公式DLC案内')

    ps = game('project-sekai', 'プロジェクトセカイ', 'ANiMAの追加告知と大会向け提供を掲載。通常配信の実施日・現状は別途確認中です。')
    url = 'https://prtimes.jp/main/html/rd/p/000007397.000005397.html'
    assert 'ANiMA' in saved(url) and '6月25日' in saved(url)
    add(ps, 'XI-072', 'ANiMA', 'xi', url,
        'セガ発表のDEEMO×Cytusタイアップ追加予定にANiMA（作曲：xi）を確認。予定日は2026年6月25日。',
        listing='追加告知', role='作曲：xi', label='株式会社セガ・タイアップ発表',
        note='追加予定の一次発表を確認。実装済みとする二次報道もあるが、実施日を確定する一次資料は追加確認。6月23日は同発表のSaikaでありANiMAの日付ではない。')
    add(ps, 'XI-161', 'ULTIM@TE☆BE∀M!!', 'xi feat. 初音ミク', 'https://www.youtube.com/watch?v=VNK8leVFy-g',
        '保存済みのxi本人動画タイトル・説明欄にプロジェクトセカイChampionship 2026決勝向け書き下ろしと記載。',
        listing='大会向け提供', role='作詞・作曲等：xi。歌唱：初音ミク', label='xi Official・大会向け本人MV',
        note='大会向け提供の根拠。通常ゲーム内配信とその開始日は未確認。')

    # Unresolved input claims remain reviewable without being certified as game inclusion.
    raw = json.loads((DATA / 'note_entries_raw.json').read_text(encoding='utf-8'))
    candidates = [dict(game=i['subsection'], original=i['original_text'], input_id=i['id'],
        source_url=i['source_url'], status='一次資料の追加照合が必要') for i in raw
        if i['subsection'] == 'Cytus' and i['title_token'].casefold() not in {'halcyon', 'storia'}]
    for title in ['Halcyon', 'Tiferet', 'Dreadnought', 'World Fragments III(radio edit)', 'Parallax']:
        candidates.append(dict(game='Arcaea', original=title, source_url='https://wikiwiki.jp/arcaea/',
            status='Wikiは探索用。曲別のゲーム運営一次資料を追加照合。radio editをアルバム版と同一音源にしない。'))
    for title in ['Aragami', 'FREEDOM DiVE↓', 'Halcyon', 'Qualia Crystal']:
        candidates.append(dict(game='クロノサークル', original=title,
            source_url='https://vgost.fandom.com/wiki/Xi', status='二次資料の探索候補。公式曲目ページはSSOへの転送で取得できず。'))
    result = dict(checked_on=CHECKED, games=games, candidates=candidates, limitations=[
        '挙げられた機種の一次資料を追加照合した途中成果であり、全収録曲の調査完了ではない。',
        'プロセカ公式楽曲JSONは65曲のみでANiMA等を含まず、現行全曲一覧とは扱わない。',
        'Arcaeaの探索先ALbxibB7X0Qは個人プレイ動画だったため、公式試聴・一次資料には採用しない。',
        'その他の元リスト機種（太鼓、DEEMO、SEVENS CODE、Crossbeats等）も今後の調査対象。'])
    (DATA / 'game_research.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Reviewed {len(games)} added game collections, {sum(len(g["tracks"]) for g in games)} relationships; {len(candidates)} held candidates')


if __name__ == '__main__':
    build()
