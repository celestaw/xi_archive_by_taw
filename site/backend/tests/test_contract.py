import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from main import app, works
from models import ApiError, PublicationRecord, WorkDetail, WorkList
from pydantic import ValidationError


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_counts_preserve_unknowns_and_variants(self):
        meta = self.client.get('/api/v1/meta').json()
        self.assertEqual(meta['total_entries'], len(works))
        self.assertEqual(meta['dated_entries'] + meta['undated_entries'], len(works))
        result = WorkList.model_validate(self.client.get('/api/v1/works?date_status=undated&limit=100').json())
        self.assertEqual(result.total, meta['undated_entries'])
        self.assertTrue(all(w.earliest_record is None for w in result.items))

    def test_genres_keep_original_labels_and_sources_without_guessing(self):
        result = WorkList.model_validate(self.client.get('/api/v1/works?q=FREEDOM%20DiVE').json())
        original = next(work for work in result.items if work.id == 'XI-017')
        self.assertEqual(original.genre.label, 'HAPPY HARDCORE')
        self.assertEqual(original.genre.medium, 'BMSイベント')
        self.assertIn('event=50&num=15', original.genre.source_url)
        self.assertEqual(self.client.get('/api/v1/works/XI-221').json()['genre']['label'],
                         'PIANO CONCERTINO + JAZZ FUSION')
        # A new release and an unidentified work must not inherit a guessed genre.
        for work_id in ['XI-001', 'XI-252']:
            self.assertIsNone(self.client.get(f'/api/v1/works/{work_id}').json()['genre'])

    def test_bms_genre_followup_does_not_infer_other_versions_or_dates(self):
        expected = {
            'XI-019': 'postrock', 'XI-025': 'JAZZ FUSION', 'XI-033': 'マジックジャズ',
            'XI-037': 'SYMPHONIC SCHRANZ', 'XI-169': 'DARKSTEP MIX',
            'XI-186': 'ANTHEM SPEEDCORE', 'XI-210': '無調音楽',
        }
        for work_id, label in expected.items():
            with self.subTest(work=work_id):
                work = self.client.get(f'/api/v1/works/{work_id}').json()
                self.assertEqual(work['genre']['label'], label)
                self.assertEqual(work['genre']['checked_on'], '2026-10-27')
                self.assertTrue(work['genre']['source_url'].startswith('https://'))
        peace = self.client.get('/api/v1/works/XI-037').json()
        self.assertEqual(peace['earliest_record']['date'], '2011-10-30')
        acid = self.client.get('/api/v1/works/XI-028').json()
        self.assertEqual(acid['genre']['label'], "DRUM'N'BASS")

    def test_distinct_registration_dates(self):
        work = WorkDetail.model_validate(self.client.get('/api/v1/works/XI-017').json())
        self.assertEqual(work.earliest_record.date, '2008-03-19')
        self.assertFalse(work.earliest_record.true_first_publication_confirmed)
        self.assertIn('2008-03-21', [r.date for r in work.records])
        self.assertTrue(all(r.source_url.startswith(('http://', 'https://')) for r in work.records))

    def test_new_x_announcements_keep_first_publication_and_release_separate(self):
        for key, first in [('XI-252', '2026-10-24'), ('XI-253', '2026-10-23')]:
            with self.subTest(work=key):
                work = WorkDetail.model_validate(self.client.get(f'/api/v1/works/{key}').json())
                self.assertEqual(work.earliest_record.date, first)
                self.assertTrue(work.earliest_record.true_first_publication_confirmed)
                self.assertIn('利用者補足', work.earliest_record.evidence)
                self.assertEqual(work.attribution, 'credited')
        remix = WorkDetail.model_validate(self.client.get('/api/v1/works/XI-253').json())
        self.assertTrue(remix.is_variant)
        self.assertIn('2026-10-25', [r.date for r in remix.records])

    def test_future_arcaea_release_is_an_announcement(self):
        game = self.client.get('/api/v1/games/arcaea').json()
        track = next(t for t in game['tracks'] if t['work_id'] == 'XI-252')
        self.assertEqual(track['listing_kind'], '追加告知')
        self.assertIn('10月29日', track['evidence'])
        work = WorkDetail.model_validate(self.client.get('/api/v1/works/XI-252').json())
        self.assertFalse(any(r.date == '2026-10-29' for r in work.records))

    def test_public_citations_preserve_attribution_without_inclusion_notes(self):
        for work in works:
            if work.attribution == 'credited':
                self.assertTrue(any(s.kind == 'primary' and s.url for s in work.sources), work.id)
            for source in work.sources:
                self.assertIn(source.kind, {'primary', 'secondary'}, work.id)
                self.assertTrue(source.label and source.checked_on, work.id)
            self.assertNotIn('attribution_basis', work.model_dump())
            self.assertNotIn('issues', work.model_dump())

    def test_third_party_video_does_not_promote_attribution_or_listening(self):
        work = WorkDetail.model_validate(self.client.get('/api/v1/works/XI-029').json())
        self.assertEqual(work.attribution, 'unverified')
        self.assertIsNone(work.earliest_record)
        self.assertEqual(work.listening, [])
        source = next(s for s in work.sources if 'zeQWTuJRDGU' in s.url)
        self.assertEqual(source.kind, 'secondary')
        self.assertIn('CHAGGERS Gaming', source.label)
        self.assertNotIn('inclusion', work.model_dump())

    def test_alias_credit_does_not_prove_xi_identity(self):
        work = WorkDetail.model_validate(self.client.get('/api/v1/works/XI-049').json())
        self.assertEqual(work.title, 'HEAVENLY GALAXiES')
        self.assertEqual(work.attribution, 'unverified')
        self.assertTrue(any(s.kind == 'primary' and s.credit == 'Xiphoid Sphere' for s in work.sources))

    def test_creation_year_is_separate_and_not_padded(self):
        work = WorkDetail.model_validate(self.client.get('/api/v1/works/XI-076').json())
        self.assertEqual(work.creation_records[0].date, '2015')
        self.assertEqual(work.creation_records[0].precision, 'year')
        self.assertTrue(all('作曲年' not in r.kind for r in work.records))

    def test_english_alias_matches_same_work(self):
        result = self.client.get('/api/v1/works', params={'q': 'ＳＴＯＲＭ and impulse'}).json()
        self.assertEqual([w['id'] for w in result['items']], ['XI-143'])
        self.assertEqual(result['items'][0]['title'], '疾風怒濤')

    def test_world_fragments_parts_are_independent(self):
        result = self.client.get('/api/v1/works', params={'q': 'World Fragments'}).json()
        parts = [w for w in result['items'] if w['id'] in ['XI-076', 'XI-077', 'XI-078']]
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(not w['is_variant'] for w in parts))

    def test_pagination_and_filters(self):
        first = self.client.get('/api/v1/works?limit=40').json()
        second = self.client.get('/api/v1/works?limit=40&offset=40').json()
        self.assertFalse(set(w['id'] for w in first['items']) & set(w['id'] for w in second['items']))
        year = self.client.get('/api/v1/works?year=2008&attribution=credited').json()
        self.assertGreater(year['total'], 0)
        self.assertTrue(all(w['earliest_record']['date'].startswith('2008') and w['attribution'] == 'credited' for w in year['items']))
        empty = self.client.get('/api/v1/works?q=never-a-real-song-12345678').json()
        self.assertEqual(empty['total'], 0)

    def test_uniform_validation_and_not_found_errors(self):
        for query in ['limit=101', 'offset=-1', 'year=banana', 'date_status=bad', 'attribution=bad']:
            response = self.client.get('/api/v1/works?' + query)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(ApiError.model_validate(response.json()).error.code, 'invalid_request')
        response = self.client.get('/api/v1/works/XI-missing')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ApiError.model_validate(response.json()).error.code, 'not_found')

    def test_date_precision_validation(self):
        record = works[0].earliest_record.model_dump()
        for date, precision in [('2005', 'day'), ('2005-13', 'month'), (None, 'year')]:
            with self.assertRaises(ValidationError):
                PublicationRecord.model_validate({**record, 'date': date, 'precision': precision})

    def test_export_contains_no_research_only_keys(self):
        data = json.loads((ROOT / 'data/catalogue.json').read_text(encoding='utf-8'))
        forbidden = {'original_workbook_claim', 'original_row', 'original_sheet', 'note_entry_ids', 'source_urls_candidates', 'original_text'}
        def visit(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden & value.keys())
                for item in value.values(): visit(item)
            elif isinstance(value, list):
                for item in value: visit(item)
            elif isinstance(value, str):
                self.assertNotIn('C:\\Users\\', value)
        visit(data)

    def test_openapi_snapshot_is_current(self):
        snapshot = json.loads((ROOT.parent / 'contracts/openapi.json').read_text(encoding='utf-8'))
        self.assertEqual(snapshot, app.openapi())
        self.assertIn('creation_records', snapshot['components']['schemas']['WorkDetail']['required'])


if __name__ == '__main__':
    unittest.main()
