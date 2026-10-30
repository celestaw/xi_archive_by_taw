import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from main import app, by_id, works
from models import TimelineList
from timeline import timeline_entry


class TimelineTests(unittest.TestCase):
    def test_all_works_are_returned_in_one_request(self):
        response = TestClient(app).get('/api/v1/timeline')
        self.assertEqual(response.status_code, 200)
        result = TimelineList.model_validate(response.json())
        self.assertEqual({entry.id for entry in result.items}, {work.id for work in works})
        self.assertEqual(len(result.items), len(works))

    def test_crossfade_is_separate_from_album_release(self):
        entry = timeline_entry(by_id['XI-159'])
        self.assertEqual(entry.preview.date, '2026-04-09')
        self.assertEqual(entry.release.date, '2026-04-26')
        self.assertTrue(entry.connect_preview)
        self.assertIsNone(entry.reference)

    def test_preview_only_does_not_invent_release(self):
        entry = timeline_entry(by_id['XI-060'])
        self.assertEqual(entry.preview.date, '2014-12-13')
        self.assertIsNone(entry.release)
        self.assertFalse(entry.connect_preview)

    def test_release_only_uses_earliest_not_later_album(self):
        entry = timeline_entry(by_id['XI-017'])
        self.assertEqual(entry.release.date, '2008-03-19')
        self.assertIsNone(entry.preview)
        self.assertFalse(entry.connect_preview)

    def test_release_qualification_is_not_misread_as_preview(self):
        entry = timeline_entry(by_id['XI-027'])
        self.assertIsNotNone(entry.release)
        self.assertIsNone(entry.preview)

    def test_undated_and_creation_records_are_not_plotted(self):
        for work in works:
            entry = timeline_entry(work)
            for record in (entry.preview, entry.release, entry.reference):
                if record:
                    self.assertTrue(record.date)
                    self.assertIn(record, work.records)
                    self.assertNotIn(record, work.creation_records)
            if not any(record.date for record in work.records):
                self.assertIsNone(entry.preview)
                self.assertIsNone(entry.release)
                self.assertIsNone(entry.reference)

    def test_uncertain_publication_type_stays_unconfirmed(self):
        entry = timeline_entry(by_id['XI-235'])
        self.assertEqual(entry.reference.date, '2024')
        self.assertEqual(entry.reference.precision, 'year')
        self.assertEqual(entry.release.date, '2025-03-01')
        gameplay = timeline_entry(by_id['XI-219'])
        self.assertIsNotNone(gameplay.reference)
        self.assertIsNone(gameplay.release)

    def test_no_connection_for_overlapping_imprecise_dates_or_later_preview(self):
        original = by_id['XI-159']
        for preview_date, precision, release_date, connect in [
            ('2026', 'year', '2026-04-26', False),
            ('2026-04', 'month', '2026-04-26', False),
            ('2026-04-26', 'day', '2026-04-26', False),
            ('2026-05-01', 'day', '2026-04-26', False),
            ('2025-12', 'month', '2026-01-01', True),
        ]:
            with self.subTest(preview=preview_date, release=release_date):
                release = original.records[0].model_copy(update={'date': release_date})
                preview = original.records[1].model_copy(update={'date': preview_date, 'precision': precision})
                work = original.model_copy(update={'records': [release, preview]})
                self.assertEqual(timeline_entry(work).connect_preview, connect)


if __name__ == '__main__':
    unittest.main()
