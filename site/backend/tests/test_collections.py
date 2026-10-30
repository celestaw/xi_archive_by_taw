import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from main import app, by_id, collections
from models import ApiError, CollectionDetail, CollectionList


class CollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_index_counts_categories_and_source_dates(self):
        albums = CollectionList.model_validate(self.client.get('/api/v1/albums').json())
        self.assertEqual(sum(c.category == 'ソロアルバム' for c in albums.items), 6)
        self.assertTrue(all(c.kind == 'album' and c.entry_count > 0 for c in albums.items))
        self.assertTrue(all('アルバム' in r.kind for c in albums.items for r in c.release_records))
        games = CollectionList.model_validate(self.client.get('/api/v1/games').json())
        self.assertTrue(all(c.kind == 'game' and not c.release_records for c in games.items))
        self.assertTrue({'project-sekai', 'cytus', 'osu', 'bms', 'arcaea', 'chrono-circle',
                         'music-diver', 'groove-coaster'} <= {c.id for c in games.items})

    def test_game_genres_retain_provenance_across_ports(self):
        for game_id in ['bms', 'sdvx']:
            game = self.client.get(f'/api/v1/games/{game_id}').json()
            halcyon = next(track for track in game['tracks'] if track['work_id'] == 'XI-026')
            self.assertEqual(halcyon['genre']['label'], 'RENAISSANCE HARDCORE')
            self.assertEqual(halcyon['genre']['medium'], 'BMSイベント')
            self.assertIn('event=65&num=237', halcyon['genre']['source_url'])
        sdvx = self.client.get('/api/v1/games/sdvx').json()
        quietus = next(track for track in sdvx['tracks'] if track['work_id'] == 'XI-215')
        self.assertIsNone(quietus['genre'])  # FLOOR is a listing category, not a musical genre.
        album = self.client.get('/api/v1/albums/parousia').json()
        self.assertTrue(all(track['genre'] is None for track in album['tracks']))

    def test_album_order_and_reissue_do_not_change_work_chronology(self):
        album = CollectionDetail.model_validate(self.client.get('/api/v1/albums/parousia').json())
        self.assertEqual([t.track_number for t in album.tracks], list(range(1, 13)))
        freedom = next(t for t in album.tracks if t.work_id == 'XI-017')
        self.assertEqual(freedom.track_number, 12)
        self.assertEqual(album.release_records[0].date, '2011-10-30')
        self.assertEqual(by_id[freedom.work_id].earliest_record.date, '2008-03-19')

    def test_originals_variants_and_other_artists_are_not_collapsed(self):
        world = CollectionDetail.model_validate(self.client.get('/api/v1/albums/world-fragments').json())
        parts = [t.work_id for t in world.tracks if t.title.startswith('World Fragments ')]
        self.assertEqual(parts, ['XI-076', 'XI-077', 'XI-078'])
        self.assertTrue(any(t.credited_name == 'VILA' for t in world.tracks))
        quietus = CollectionDetail.model_validate(self.client.get('/api/v1/albums/quietus-ray').json())
        guest = next(t for t in quietus.tracks if t.title == 'Parousia (Blacklolita Remix)')
        self.assertIsNone(guest.work_id)
        self.assertIn('他者', guest.role)
        self.assertIn('新規作曲として数えない', guest.note)
        storm = CollectionDetail.model_validate(self.client.get('/api/v1/albums/storm-and-impulse').json())
        self.assertIn('XI-127', [t.work_id for t in storm.tracks])

    def test_game_membership_is_specific_to_source_not_album_versions(self):
        maimai = CollectionDetail.model_validate(self.client.get('/api/v1/games/maimai').json())
        chuni = CollectionDetail.model_validate(self.client.get('/api/v1/games/chunithm').json())
        self.assertIn('XI-166', [t.work_id for t in maimai.tracks])
        self.assertIn('XI-166', [t.work_id for t in chuni.tracks])
        game_ids = {t.work_id for c in collections if c.kind == 'game' for t in c.tracks}
        self.assertNotIn('XI-127', game_ids)
        championship = next(t for c in collections if c.id == 'project-sekai' for t in c.tracks if t.work_id == 'XI-161')
        self.assertEqual(championship.listing_kind, '大会向け提供')
        self.assertFalse(any(t.work_id == 'XI-161' and t.listing_kind == '収録' for c in collections for t in c.tracks))
        self.assertTrue(all(t.source_url and t.evidence and t.checked_on for c in collections for t in c.tracks))

    def test_advance_and_general_release_dates_are_kept_separate(self):
        album = next(c for c in collections if c.title == 'Clippings of youth vol.1')
        self.assertEqual([r.date for r in album.release_records], ['2023-04-16', '2023-04-30'])
        self.assertEqual(len(album.tracks), 1)

    def test_collection_ids_and_public_data_references_are_valid(self):
        ids = json.loads((ROOT.parent / 'web/lib/collection-ids.json').read_text(encoding='utf-8'))
        for kind, key in [('album', 'albums'), ('game', 'games')]:
            self.assertEqual(set(ids[key]), {c.id for c in collections if c.kind == kind})
        for collection in collections:
            self.assertEqual(collection.entry_count, len(collection.tracks))
            self.assertTrue(all(t.work_id is None or t.work_id in by_id for t in collection.tracks))
            linked_ids = [t.work_id for t in collection.tracks if t.work_id is not None]
            self.assertEqual(len(linked_ids), len(set(linked_ids)), collection.title)

    def test_missing_or_cross_kind_collection_is_not_found(self):
        for path in ['/albums/not-real', '/games/not-real', '/games/parousia', '/albums/maimai']:
            response = self.client.get('/api/v1' + path)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(ApiError.model_validate(response.json()).error.code, 'not_found')

    def test_licensed_tracks_bms_and_announcements_keep_their_meanings(self):
        osu = next(c for c in collections if c.id == 'osu')
        bms = next(c for c in collections if c.id == 'bms')
        self.assertEqual(len(osu.tracks), 40)
        self.assertTrue(all(t.listing_kind == '公式許諾曲' for t in osu.tracks))
        self.assertEqual(len(bms.tracks), 14)
        self.assertTrue(all(t.listing_kind == 'BMS登録' for t in bms.tracks))
        freedom = next(t for t in bms.tracks if t.work_id == 'XI-017')
        self.assertIn('2008-03-21', freedom.note)
        self.assertEqual(by_id['XI-017'].earliest_record.date, '2008-03-19')
        anima = next(t for c in collections if c.id == 'project-sekai' for t in c.tracks if t.work_id == 'XI-072')
        self.assertEqual(anima.listing_kind, '追加告知')

    def test_new_primary_sources_do_not_turn_internal_dates_into_first_release(self):
        md = next(c for c in collections if c.id == 'music-diver')
        self.assertEqual({t.work_id for t in md.tracks}, {'XI-017', 'XI-026', 'XI-214', 'XI-223'})
        qualia = by_id['XI-214']
        self.assertEqual(qualia.attribution, 'credited')
        self.assertEqual(qualia.earliest_record.date, '2025-04-27')
        self.assertIn('動画公開日', qualia.earliest_record.kind)
        self.assertFalse(qualia.earliest_record.true_first_publication_confirmed)
        self.assertTrue(any(s.kind == 'primary' and 'youtube.com/' in s.url for s in qualia.sources))
        self.assertTrue(all(r.date != '2021-01-01' for r in qualia.records))
        arcaea = next(c for c in collections if c.id == 'arcaea')
        overwhelm = next(t for t in arcaea.tracks if t.work_id == 'XI-135')
        self.assertIn('Nintendo Switch', overwhelm.edition)
        candidates = [t for t in arcaea.tracks if t.listing_kind == '収録候補']
        self.assertEqual(len(candidates), 4)
        self.assertEqual({t.work_id for t in candidates}, {'XI-026', 'XI-075', 'XI-069', 'XI-078'})
        self.assertTrue(all(t.source_kind == 'secondary' and t.listing_kind == '収録候補' for t in candidates))
        app = next(c for c in collections if c.id == 'groove-coaster')
        self.assertTrue(all('アプリ' in t.edition and 'アーケードモード' in t.note for t in app.tracks))


    def test_secondary_sources_and_aliases_do_not_become_primary_credit(self):
        for collection in collections:
            for track in collection.tracks:
                if track.source_kind == 'secondary':
                    self.assertEqual(track.listing_kind, '収録候補')
                    self.assertIsNone(track.listening)
        cross = next(c for c in collections if c.id == 'crossbeats')
        self.assertEqual({t.work_id for t in cross.tracks}, {'XI-074', 'XI-080'})
        rev = next(c for c in collections if c.id == 'crossbeats-rev')
        self.assertEqual(rev.tracks[0].source_kind, 'primary_reproduction')
        self.assertEqual(by_id['XI-171'].attribution, 'unverified')
        self.assertEqual(by_id['XI-171'].credited_name, 'Hekatoncheir')
        self.assertEqual(by_id['XI-193'].attribution, 'credited')
        self.assertEqual(by_id['XI-208'].attribution, 'credited')
        self.assertTrue(any(s.kind == 'primary' for s in by_id['XI-193'].sources))

    def test_extra_charts_and_internal_dates_do_not_create_new_works(self):
        chuni = next(c for c in collections if c.id == 'chunithm')
        self.assertEqual(sum(t.work_id == 'XI-017' for t in chuni.tracks), 1)
        self.assertNotIn('XI-010', {t.work_id for t in chuni.tracks})  # official Lapis is SHIKI
        maimai = next(c for c in collections if c.id == 'maimai')
        self.assertEqual(sum(t.work_id == 'XI-188' for t in maimai.tracks), 1)
        ongeki = next(c for c in collections if c.id == 'ongeki')
        self.assertEqual(sum(t.work_id == 'XI-026' for t in ongeki.tracks), 1)
        self.assertFalse(any(t.work_id in {'XI-132', 'XI-133', 'XI-134'} for c in collections if c.kind == 'game' for t in c.tracks))
        self.assertTrue(any(r.date == '2021-12-23' and r.kind == 'ゲームイベント解禁開始日' for r in by_id['XI-232'].records))
        self.assertTrue(any(r.date == '2017-01-05' and '転載' in r.kind for r in by_id['XI-205'].records))
        self.assertTrue(all(not r.true_first_publication_confirmed for r in by_id['XI-232'].records))
        hypnos = next(r for r in by_id['XI-193'].records if r.id == 'GAME-VIDEO-XI-193')
        self.assertEqual(hypnos.date, '2021-02-04')
        self.assertIn('2021-02-03T23:42:11-08:00', hypnos.evidence)
        self.assertIn('動画公開日', hypnos.kind)
        self.assertFalse(hypnos.true_first_publication_confirmed)


if __name__ == '__main__':
    unittest.main()
