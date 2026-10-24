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

    def test_distinct_registration_dates(self):
        work = WorkDetail.model_validate(self.client.get('/api/v1/works/XI-017').json())
        self.assertEqual(work.earliest_record.date, '2008-03-19')
        self.assertFalse(work.earliest_record.true_first_publication_confirmed)
        self.assertIn('2008-03-21', [r.date for r in work.records])
        self.assertTrue(all(r.source_url.startswith(('http://', 'https://')) for r in work.records))

    def test_each_work_has_traceable_attribution_and_inclusion(self):
        for work in works:
            basis = work.attribution_basis
            self.assertTrue(basis.summary, work.id)
            self.assertTrue(basis.inclusion, work.id)
            self.assertEqual(work.attribution == 'credited', basis.verdict == 'primary_credit', work.id)
            if work.attribution == 'credited':
                self.assertTrue(any(s.kind == 'primary' and s.url for s in basis.sources), work.id)
            for source in basis.sources:
                self.assertNotEqual(source.kind, 'input', work.id)
                self.assertTrue(source.summary and source.identity_note and source.checked_on, work.id)

    def test_third_party_video_does_not_promote_attribution_or_listening(self):
        work = WorkDetail.model_validate(self.client.get('/api/v1/works/XI-029').json())
        self.assertEqual(work.attribution, 'unverified')
        self.assertIsNone(work.earliest_record)
        self.assertEqual(work.listening, [])
        source = next(s for s in work.attribution_basis.sources if s.url and 'zeQWTuJRDGU' in s.url)
        self.assertEqual(source.kind, 'secondary')
        self.assertIn('CHAGGERS Gaming', source.label)
        self.assertTrue(any('要確認候補' in s.locator and '10行目' in s.locator for s in work.attribution_basis.inclusion))
        self.assertFalse(any(s.url and 'note.com' in s.url for s in work.attribution_basis.inclusion))

    def test_alias_credit_does_not_prove_xi_identity(self):
        work = WorkDetail.model_validate(self.client.get('/api/v1/works/XI-049').json())
        self.assertEqual(work.title, 'HEAVENLY GALAXiES')
        self.assertIn(work.title, work.attribution_basis.summary)
        self.assertEqual(work.attribution, 'unverified')
        self.assertTrue(any(s.kind == 'primary' and s.credit == 'Xiphoid Sphere' for s in work.attribution_basis.sources))

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
