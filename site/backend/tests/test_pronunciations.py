import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from models import WorkDetail


class PronunciationTests(unittest.TestCase):
    def test_only_source_supported_reading_suggestions_are_published(self):
        works = [WorkDetail.model_validate(work) for work in json.loads((ROOT / 'data/catalogue.json').read_text(encoding='utf-8'))['works']]
        readings = {work.id: work for work in works if work.pronunciation is not None}
        self.assertEqual(set(readings), {'XI-034', 'XI-051', 'XI-052'})
        for work_id, title, reading in [('XI-034', 'Parousia', 'パルーシア'), ('XI-051', 'Niflheimr', 'ニヴルヘイム'), ('XI-052', 'Zauberkugel', 'ザウバークーゲル')]:
            work = readings[work_id]
            self.assertEqual(work.title, title)
            self.assertEqual(work.pronunciation.reading, reading)
            self.assertEqual(work.pronunciation.basis, 'author_suggestion')
            post_id = '119053529179631616' if work_id == 'XI-034' else '302655586108055552'
            self.assertEqual(work.pronunciation.source_url, f'https://x.com/com_giko_31/status/{post_id}')
            self.assertEqual(work.pronunciation.source_date, '2011-09-28' if work_id == 'XI-034' else '2013-02-16')

    def test_unattested_readings_remain_absent_and_titles_unchanged(self):
        data = json.loads((ROOT / 'data/catalogue.json').read_text(encoding='utf-8'))['works']
        magnum = next(work for work in data if work['id'] == 'XI-025')
        self.assertNotIn('pronunciation', magnum)
        self.assertIsNone(WorkDetail.model_validate(magnum).pronunciation)
        self.assertEqual(magnum['title'], '.357 Magnum')


if __name__ == '__main__':
    unittest.main()
