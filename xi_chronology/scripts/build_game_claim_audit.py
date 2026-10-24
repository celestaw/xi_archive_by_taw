"""Keep every input claim and its reviewed result, including unresolved claims."""
import csv
import io
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
CHECKED='2026-10-25'


def load(path): return json.loads(path.read_text(encoding='utf-8'))


def build():
    original=load(DATA/'note_entries_raw.json')
    works=load(DATA/'works.json')['works']
    public=load(ROOT.parent/'site/backend/data/catalogue.json')['works']
    by_id={w['id']:w for w in public}
    games=[g for g in load(DATA/'media_collections.json')['collections'] if g['kind']=='game']
    groups={
        'osu!収録':['osu'],'beatmania ⅡDX収録':['iidx','iidx-infinitas'],
        'SDVX':['sdvx'],'太鼓の達人':['taiko-dondaful','taiko-pop-tap-beat'],
        'Sevens code':['sevens-code'],'Deemo/Deemo2':['deemo','deemo2','deemo-reborn'],
        'Cytus':['cytus'],'Chrono Circle':['chrono-circle'],'ダンカグ':['danmaku'],
        'CHUNITHM':['chunithm'],'maimai':['maimai'],'オンゲキ':['ongeki'],
        'プロジェクトセカイ':['project-sekai'],'Cross x beats':['crossbeats'],
        'CrossbeatsREV.':['crossbeats-rev'],'Paradigm: Reboot':['paradigm-reboot'],
        'ノスタルジア':['nostalgia','nostalgia-konaste'],'In Falsus':['in-falsus']}
    next_sources={
        'osu!収録':'osu! Featured Artistの個別音源と曲名・版を再照合。譜面の公認状況は別調査。',
        'beatmania ⅡDX収録':'IIDX公式曲別紹介・更新告知・本人の楽曲告知。別名義は本人への直接リンクが必要。',
        '太鼓の達人':'バンダイナムコのアーケード公式曲目・当時の追加告知で、版別の初収録日を調べる。',
        'Deemo/Deemo2':'Rayarkの曲別紹介・更新告知・公式xi Collection曲目。DEEMOとDEEMO IIを分ける。',
        'Cytus':'Rayarkの当時の曲別紹介・チャプター更新告知、公式サイトの保存版。',
        'Cross x beats':'旧カプコン公式CROSS×BEATSの曲別紹介・RPショップ告知の保存版。非公式転記の原文へ遡る。',
        'CrossbeatsREV.':'メーカー原ページの保存版、または本人のMinerva提供告知で人物を再照合。',
    }
    rows=[]
    for entry in original:
        if entry['section']!='音ゲー収録': continue
        ids=[w['id'] for w in works if entry['id'] in w['note_entry_ids']]
        assert ids,entry['id']
        allowed=groups[entry['subsection']]
        matches=[dict(game_id=g['id'],game=g['title'],**t) for g in games if g['id'] in allowed for t in g['tracks'] if t['work_id'] in ids]
        adopted={m['work_id'] for m in matches}
        unresolved=[]
        if not matches:
            status='収録未確認'
            unresolved.append('この元記載のゲームでは曲別根拠が未取得。別ゲームの存在だけで補完しない。')
        elif any(m['source_kind']!='secondary' for m in matches):
            status='メーカー資料転載で確認' if any(m['source_kind']=='primary_reproduction' for m in matches) else '一次資料確認'
            if any(m['source_kind']=='secondary' for m in matches): status='別版で一次資料確認・元版は候補'
            kinds={m['listing_kind'] for m in matches}
            if kinds=={'公式許諾曲'}: status='公式許諾音源を確認'
            if kinds=={'大会向け提供'}: status='大会向け提供を確認'
            if kinds=={'追加告知'}: status='追加告知を確認'
            if entry['subsection']=='太鼓の達人': status='家庭用・配信版で確認'
            if entry['id']=='NOTE-108': status='INFINITAS版で確認'
        else:
            status='二次資料の収録候補'
            unresolved.append('ゲーム側の曲別一次資料が未取得。二次資料の記載を収録確定・初収録日へ昇格しない。')
        missing=[id for id in ids if id not in adopted]
        if missing:
            unresolved.append('元の参照先のうち当該ゲームで未照合：'+', '.join(missing))
        if entry['id']=='NOTE-110':
            unresolved.append('MasterstrokeのSDVX収録は公式確認済みだが、IIDX欄のMaster strokeは裏付け未取得。同じ曲とする元の対応判断も再検討する。')
        if entry['id']=='NOTE-067':
            unresolved.append('確認したFeatured Artistの40曲との対応が取れない。公式アルバムでの存在確認をosu!許諾の根拠へ転用しない。別表記・現在の許諾範囲も再確認。')
        if entry['id']=='NOTE-148':
            unresolved.append('MESSiΛH COMPL3XはCytus IIの開発元更新履歴に存在する。元のDeemo/Deemo2欄への収録は未確認。')
        if entry['id']=='NOTE-103':
            unresolved.append('公式クレジットはHekatoncheir。xiの別名義とする一次資料は未取得。')
        if entry['id']=='NOTE-179':
            unresolved.append('大会向け提供は本人MVで確認。通常配信の収録実施とは区別。')
        if entry['subsection']=='osu!収録':
            unresolved.append('Featured Artist音源の許諾であり、標準搭載曲や公式譜面の収録を意味しない。')
        unresolved.append('初収録日・現在の入手可否は曲別に追加確認。')
        attempts=[dict(url=m['source_url'],result=m['evidence']) for m in matches]
        if entry['id']=='NOTE-110':
            attempts.append(dict(url='https://p.eagate.573.jp/game/infinitas/2/music/index.html',result='取得した公式INFINITAS曲目とIIDX 29〜34の公式紹介を確認したがMasterstrokeの裏付けを得られなかった。未掲載だけから不収録とは断定しない。'))
        if entry['id']=='NOTE-148':
            attempts.append(dict(url='https://apps.apple.com/jp/app/cytus-ii/id1290687550',result='開発元提供のCytus II更新履歴では確認。DEEMO曲目の二次一覧には見当たらず、DEEMO系への収録は保留。'))
        if entry['id']=='NOTE-067':
            attempts.append(dict(url='https://osu.ppy.sh/beatmaps/artists/727',result='保存済みFeatured Artist許諾曲40項目と照合。当該曲への対応未確認。'))
        rows.append(dict(input=entry,work_ids=ids,canonical_titles=[by_id[id]['title'] for id in ids],
            status=status,matched_records=matches,unmatched_work_ids=missing,
            xi_identity={id:by_id[id]['attribution'] for id in ids},
            checked_on=CHECKED,unresolved=unresolved,attempts=attempts,
            next_source=next_sources.get(entry['subsection'],'ゲーム運営の曲別追加告知・初出バージョンの公式保存版。')))
    assert len(rows)==123
    all_works=[]
    for work in public:
        records=[dict(game_id=g['id'],game=g['title'],**t) for g in games for t in g['tracks'] if t['work_id']==work['id']]
        all_works.append(dict(work_id=work['id'],title=work['title'],
            input_claim_ids=[r['input']['id'] for r in rows if work['id'] in r['work_ids']],
            game_records=records,status='収録・提供関係あり' if records else '掲載根拠未取得（不収録とは断定しない）',
            checked_on=CHECKED))
    result=dict(checked_on=CHECKED,input_claim_count=len(rows),work_count=len(all_works),
        status_counts=dict(Counter(r['status'] for r in rows)),claims=rows,works=all_works,
        rules=['入力123行を保持。World Fragmentsの1行はI・II・IIIの3項目に対応する。',
            '全251項目を台帳に残す。掲載根拠未取得は全ゲームでの不収録を意味しない。',
            '確認したゲーム別一覧の範囲と、全作品の全収録先の網羅調査は区別する。'])
    (DATA/'game_claim_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    out=io.StringIO(newline=''); writer=csv.writer(out,lineterminator='\n')
    writer.writerow(['元ID','元のゲーム欄','元の記載','作品ID','整理した曲名','判定','確認した版・収録先','根拠URL','xi帰属','未解決点','次に当たる資料','確認日'])
    for r in rows:
        writer.writerow([r['input']['id'],r['input']['subsection'],r['input']['original_text'],
            ' / '.join(r['work_ids']),' / '.join(r['canonical_titles']),r['status'],
            ' / '.join(dict.fromkeys(m['edition'] or m['game'] for m in r['matched_records'])),
            '\n'.join(dict.fromkeys(m['source_url'] for m in r['matched_records'])),
            ' / '.join(k+':'+v for k,v in r['xi_identity'].items()),'\n'.join(r['unresolved']),r['next_source'],r['checked_on']])
    (DATA/'game_claim_audit.csv').write_text(out.getvalue(),encoding='utf-8-sig')
    report=[
        '# 音楽ゲーム・曲別照合記録（2026-10-25）','',
        f'元noteの音楽ゲーム欄123行を一曲ずつ照合し、元の記載を全行保持した。作品台帳は{len(all_works)}項目を保持。ゲーム別一覧は{len(games)}項目・{sum(g["entry_count"] for g in games)}件の関係を掲載する。版ごとの一覧、BMS登録、公式許諾音源、収録候補を含む延べ件数であり、ゲーム32機種や新規楽曲196曲を意味しない。','',
        '一次資料で確認できたゲームとの関係と、対象xi本人への帰属は別の判定。初収録日と真の初公開日を確定した一覧ではない。全作品の全収録先を網羅した調査も未完了。','',
        '## 元リストの123行の判定','', '|判定|元の行数|','|---|---:|',
    ]
    report += [f'|{status}|{count}|' for status,count in result['status_counts'].items()]
    report += ['', 'World Fragmentsの元1行はI・II・IIIの3曲に対応させる。元行数と掲載曲数は同じではない。', '',
        '## 採用・保留の重要な判断','',
        '- CROSS×BEATSのHesperides・Keraunosは非公式曲目に基づく収録候補。公式アルバムの存在だけからゲーム収録を確定しない。カプコンの旧公式ページのCDX照会は503で取得失敗。',
        '- crossbeats REV. SUNRISEのMinervaは、ファミ通記事の「以下、リリースより。」以降のメーカー配布資料で確認。2017-01-05 4:00は楽曲実装日時として保存し、メーカー原ページへの直接確認とは区別。本人への直接リンクによる再照合は未完了。',
        '- MasterstrokeはSDVX公式で確認。IIDX欄のMaster strokeは裏付け未取得で、削除・自動訂正しない。',
        '- MESSiΛH COMPL3XはCytus IIの開発元更新履歴で確認。元のDeemo/Deemo2欄への収録は確認できていない。',
        '- 天衣無縫は公式アルバムで曲自体を確認済みだが、osu! Featured Artistの確認済み40項目との対応が取れず保留。',
        '- Beyond Evolutionの公式名義はHekatoncheir。xiの別名義とする一次根拠は未取得なので、公式曲目の存在をもって本人への帰属を確定しない。',
        '- Innocent TempestはDiceros Bicornis名義。SDVX公式のЯeviveR作者コメントでxi・BlackYの合作との対応を補強。Innocent Tempest自体の個別工程を創作しない。',
        '- HypnosはDiverse System公式曲別動画、NoctilucaはTunerGames公式曲別動画で本人com_giko_31への直接リンクを確認し、曲別帰属根拠・公式試聴へ追加。音声は未聴取なので曲調のコメントは加えていない。',
        '- SEGAの公式公開曲目を全件取得し、CHUNITHM 1763行・maimai 1605行・オンゲキ1112行から曲名と名義を照合。SHIKIのLapisをxiの同名曲へ対応させない。追加のWORLD’S END・宴・LUNATIC譜面を別の曲として数えない。',
        '- maimaiのHeavenly Blastは原曲への収録関係。Long Version・2022 Remasterを独立したゲーム収録として計上しない。Mjölnirのゲーム音源とGame Size版との同定は未了。',
        '- ArcaeaのWorld Fragments III(radio edit)は関連する版として候補に保持。アルバム版と同じ音源とは確定しない。Parallaxは二次資料上2026-10-29追加予定で、確認日より未来のため現在の収録へ加えない。',
        '- ノスタルジアの2021-12-22は告知日、2021-12-23 10:00はイベント解禁開始。公開ニュース本文のdata-dateと本文の日時を分けて確認。',
        '- 太鼓の達人は今回Nintendo Switch・Apple Arcade版を確認。アーケードへの初収録日へ転用しない。プロセカの大会向け提供・追加告知も通常収録と区別する。','',
        '## 追加調査の順序','',
        '1. 収録未確認の3行とHekatoncheirの人物照合。元のゲーム欄と異なる媒体で見つかった記録を明示したまま、本人・運営の曲別告知を探す。',
        '2. DEEMO・Cytus・CROSS×BEATS・Arcaeaの収録候補22件について、運営の当時の曲紹介・パック告知・保存版へ遡る。非公式転記は原文が得られるまで二次資料のまま保持。',
        '3. クロノサークルのAragami・FREEDOM DiVE↓・Halcyon・Qualia Crystalは旧段階の探索候補。公式曲目がSSOへ転送され取得できず、今回も確定情報として加えていない。',
        '4. 元リスト外の収録先を曲別に継続探索。VOEZはSwitch版Ascension to Heavenを販売元曲目で確認。Tone Sphere、Lanota、Muse Dash、WACCA、DJMAX等は代表曲だけから全曲へ広げず、曲別・版別の一次資料を取得する。',
        '5. 収録関係が分かった曲も、最古のゲーム追加告知・BMS登録・先行試聴を日付の種類ごとに調べる。現在のプレイ可否は別調査。','',
        '## 元123行の照合結果','',
        '元表記・全根拠・人物照合・試みた資料・次に当たる資料はCSV/JSONに保持。以下のリンクは曲別に確認した掲載根拠。', '',
        '|元ID|元ゲーム欄|元表記|判定|根拠|','|---|---|---|---|---|',
    ]
    for r in rows:
        e=r['input']; source=r['matched_records'][0]['source_url'] if r['matched_records'] else ''
        title=e['original_text'].replace('|','\\|').replace('\n',' ')
        report.append(f'|{e["id"]}|{e["subsection"]}|{title}|{r["status"]}|'+(f'[資料]({source})' if source else '未取得')+'|')
    report += ['', '## 保存・再生成','',
        '- `xi_chronology/data/game_claim_audit.csv`：元123行の照合表。Excel等で読めるUTF-8 BOM付き。',
        '- `xi_chronology/data/game_claim_audit.json`：全123行と全251項目の収録関係台帳。元の入力オブジェクトを保持。掲載根拠未取得は不収録と断定しない。',
        '- `xi_chronology/data/game_song_findings.json`：今回の曲別判断114件。一次・メーカー資料転載・二次を区別。前段階のgame_research.jsonを上書きしない。',
        '- `xi_chronology/sources/game-song-audit-20261025/`：URL、取得日時、成否、原バイト、SHA256、抽出テキスト。取得原文は無変更。HTTPの文字コード宣言と本文が食い違うページは原バイトをUTF-8優先・CP932補完で再読している。',
        '- 再生成順：`research_game_song_audit.py` → `site/scripts/generate-contracts.mjs`。後者は公開データ・API契約に加え、`build_game_claim_audit.py`で本台帳・本稿も更新する。',
        '- `docs/verification/xi-game-song-audit.json`：実際のプレビューの全ゲームAPI照合・テスト・ビルド・ブラウザー確認。',
        '- 実装はfeat/media-pagesに保存。dev・alpha・mainへの取り込み、公開は別段階。','']
    (ROOT.parent/'docs/game-song-audit-20261025.md').write_text('\n'.join(report),encoding='utf-8')
    print(json.dumps(result['status_counts'],ensure_ascii=False))
    print('Unconfirmed inputs:', [(r['input']['id'],r['input']['original_text']) for r in rows if r['status']=='収録未確認'])


if __name__=='__main__': build()
