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
        self.assertNotIn('osu! Featured Artist', [c.title for c in games.items])

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
        self.assertNotIn('XI-161', game_ids)  # Championship evidence alone is not normal game inclusion.
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


if __name__ == '__main__':
    unittest.main()
