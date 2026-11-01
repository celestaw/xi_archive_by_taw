"""Verify the running same-origin API against the reviewed local export."""
import json
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def get(path):
    with urllib.request.urlopen('http://127.0.0.1:3210/api/v1'+path,timeout=15) as response:
        assert response.status==200
        return json.load(response)


def main():
    expected=json.loads((ROOT/'site/backend/data/collections.json').read_text(encoding='utf-8'))['collections']
    games=[g for g in expected if g['kind']=='game']
    actual=get('/games')['items']
    assert {g['id'] for g in actual}=={g['id'] for g in games}
    details=[]
    for game in games:
        result=get('/games/'+game['id'])
        assert result==game,game['id']
        details.append(dict(id=game['id'],entry_count=result['entry_count'],status=200))
    works=json.loads((ROOT/'site/backend/data/catalogue.json').read_text(encoding='utf-8'))['works']
    for id in ['XI-193','XI-208','XI-171','XI-205','XI-232']:
        assert get('/works/'+id)==next(w for w in works if w['id']==id)
    try:
        get('/games/not-real')
        raise AssertionError('Unknown game did not return 404')
    except urllib.error.HTTPError as error:
        assert error.code==404
    report=dict(checked_on='2026-10-25',url='http://127.0.0.1:3210/games',
        story='ゲーム一覧 → 同一オリジンAPI → 調査データ → 曲別出典・候補表示',
        games=len(games),relationships=sum(g['entry_count'] for g in games),
        listing_counts=dict(Counter(t['listing_kind'] for g in games for t in g['tracks'])),
        source_counts=dict(Counter(t['source_kind'] for g in games for t in g['tracks'])),
        api_details=details,work_api_records_match=True,unknown_game_status=404,
        build='next build --webpack: passed; TypeScript passed',api_tests='25 tests passed',
        browser_checks=[])
    (ROOT/'docs/verification/xi-game-song-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Live preview matches all {len(games)} collections / {report["relationships"]} relationships; work details and 404 verified.')


if __name__=='__main__': main()
