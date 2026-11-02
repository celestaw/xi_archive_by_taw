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
    def test_priority_publication_events_keep_dates_versions_and_partial_precision(self):
        expected = {
            'XI-065': '2015-08-16', 'XI-080': '2016-08-14', 'XI-084': '2016-11-09',
            'XI-116': '2019-12-31', 'XI-121': '2020-10-26', 'XI-152': '2024-10-27',
            'XI-156': '2025-10-26', 'XI-164': '2019-08-01',
            'XI-166': '2015-10-15', 'XI-167': '2021-08-13',
            'XI-168': '2023-08-09', 'XI-170': '2013-12-28', 'XI-177': '2018-03-29',
            'XI-181': '2026-05-29', 'XI-182': '2018-02-12', 'XI-183': '2021-03-18',
            'XI-184': '2018-08-09',
            'XI-185': '2014-03-06', 'XI-187': '2017-12-12', 'XI-188': '2016-05-26',
            'XI-190': '2016-08-10', 'XI-194': '2016-04-01',
            'XI-197': '2018-02-22', 'XI-198': '2019-01-12', 'XI-200': '2026-03-21',
            'XI-201': '2022-07-18', 'XI-203': '2026-09-08', 'XI-206': '2021-02-04',
            'XI-210': '2012',
            'XI-213': '2024-04-11',
            'XI-215': '2013-09-05', 'XI-216': '2021-12-23', 'XI-218': '2015-09-21',
            'XI-223': '2015-10-15', 'XI-225': '2018-03-08', 'XI-226': '2020-09-30',
            'XI-227': '2015-07-01', 'XI-234': '2016-07-14', 'XI-236': '2014-12-04',
            'XI-238': '2014-08-14', 'XI-243': '2020-02-27', 'XI-245': '2023-10-18',
            'XI-248': '2016-04-15',
        }
        for work_id, date in expected.items():
            with self.subTest(work=work_id):
                work = by_id[work_id]
                self.assertEqual(work.earliest_record.date, date)
                self.assertFalse(work.earliest_record.true_first_publication_confirmed)
                entry = timeline_entry(work)
                self.assertTrue(entry.preview or entry.release or entry.reference)
                self.assertEqual(len({r.id for r in work.records}), len(work.records))
        pandemonium = by_id['XI-210'].earliest_record
        self.assertEqual(pandemonium.precision, 'year')
        self.assertNotIn('2012-04-05', [r.date for r in by_id['XI-210'].records])
        self.assertNotIn('2026-03-26', [r.date for r in by_id['XI-200'].records])
        self.assertNotIn('2026-09-11', [r.date for r in by_id['XI-203'].records])
        self.assertEqual(len(expected), 43)
        # Exact author announcements resolve the remaining candidates while
        # preserving the distinction between an announcement and game delivery.
        self.assertNotIn('2019-08-29', [r.date for r in by_id['XI-164'].records])
        self.assertNotIn('2021-03-16', [r.date for r in by_id['XI-183'].records])
        self.assertEqual(by_id['XI-164'].earliest_record.source_url,
                         'https://x.com/com_giko_31/status/1156780702353879040')
        self.assertEqual(by_id['XI-183'].earliest_record.source_url,
                         'https://x.com/com_giko_31/status/1371723656552849408')

    def test_official_game_events_keep_cross_source_dates_and_later_introduction_separate(self):
        glorious = by_id['XI-188']
        self.assertEqual(glorious.earliest_record.date, '2016-05-26')
        self.assertIn('チャレンジトラック', glorious.earliest_record.kind)
        self.assertEqual(glorious.earliest_record.source_url,
                         'https://x.com/maimai_official/status/735365074014089216')
        self.assertNotIn('2016-05-25', [r.date for r in glorious.records])
        self.assertNotIn('2016-06-23', [r.date for r in glorious.records])
        self.assertEqual(timeline_entry(glorious).release.date, '2016-05-26')

        fortuna = by_id['XI-187']
        b1 = next(r for r in fortuna.records if r.id.endswith('B1-CROSS-SOURCE'))
        introduction = next(r for r in fortuna.records if r.id.endswith('OFFICIAL-INTRODUCTION'))
        preview_evidence = next(r for r in fortuna.records if r.id.endswith('PROGRAM-PREVIEW'))
        self.assertEqual((b1.date, introduction.date), ('2018-02-01', '2018-05-05'))
        self.assertEqual(preview_evidence.date, '2017-12-12')
        self.assertIn('資料照合', preview_evidence.kind)
        self.assertIn('再生未監査', preview_evidence.kind)
        self.assertIn('getnews.jp/livearchive2017', preview_evidence.evidence)
        self.assertNotIn('2017-12-04', [r.date for r in fortuna.records])
        self.assertFalse(preview_evidence.true_first_publication_confirmed)
        self.assertIn('資料照合', b1.kind)
        self.assertIn('958548093489766400', b1.evidence)
        self.assertIn('992691188074401792', b1.evidence)
        self.assertIn('紹介日', introduction.kind)
        self.assertFalse(b1.true_first_publication_confirmed)
        self.assertFalse(introduction.true_first_publication_confirmed)
        entry = timeline_entry(fortuna)
        self.assertEqual(entry.reference.date, '2017-12-12')
        self.assertIsNone(entry.release)
        self.assertIsNone(entry.full_record)
        self.assertEqual(entry.audio_status, 'unverified')
        self.assertEqual(entry.audio_sources, [])
        # Events remain unique, and neither an announcement nor an
        # official introduction is promoted to a verified full-audio listing.
        for work in [glorious, fortuna]:
            self.assertEqual(len({r.id for r in work.records}), len(work.records))
            self.assertEqual(work.checked_on, '2026-10-31')
            detail = TestClient(app).get('/api/v1/works/' + work.id).json()
            self.assertEqual([r['id'] for r in detail['records']], [r.id for r in work.records])
            self.assertEqual(detail['checked_on'], '2026-10-31')

    def test_game_ports_and_teasers_do_not_replace_original_publications_or_full_audio(self):
        freedom = by_id['XI-017']
        self.assertEqual(freedom.earliest_record.date, '2008-03-19')
        self.assertIn('2008-03-21', [r.date for r in freedom.records])
        chunithm = next(r for r in freedom.records if r.id == 'DATE-XI-017-CHUNITHM')
        self.assertEqual(chunithm.date, '2016-05-26')
        self.assertIn('移植', chunithm.kind)
        self.assertEqual(chunithm.source_url, 'https://x.com/chunithm/status/735365008234848257')
        self.assertEqual(timeline_entry(freedom).release.date, '2008-03-19')
        self.assertNotEqual(freedom.id, by_id['XI-188'].id)

        prima = by_id['XI-213']
        game = next(r for r in prima.records if r.id == 'DATE-XI-213-PHOENIX-108')
        self.assertEqual(game.date, '2024-04-18')
        self.assertIn('1.08.0', game.kind)
        self.assertIn('wNKu6nlKlgs', game.source_url)
        self.assertNotIn('2024-04-09', [r.date for r in prima.records])
        self.assertEqual(prima.earliest_record.date, '2024-04-11')
        bga = next(r for r in prima.records if r.id == 'DATE-XI-213-OFFICIAL-BGA')
        self.assertIn('公式動画公開日', bga.kind)
        self.assertIn('123秒', bga.evidence)
        entry = timeline_entry(prima)
        self.assertEqual(entry.audio_access, 'official')
        self.assertEqual(entry.release.date, '2024-04-11')
        self.assertEqual(entry.full_record.id, bga.id)
        self.assertEqual([source.url for source in entry.audio_sources],
                         ['https://www.youtube.com/watch?v=iIoKisgSjHs'])
        self.assertNotIn(game.source_url, [source.url for source in entry.audio_sources])
        self.assertIn('未実施', entry.audio_sources[0].evidence)

    def test_physical_cd_and_cross_source_milestones_do_not_become_other_editions(self):
        for work_id in ['XI-190', 'XI-215']:
            cd = next(r for r in by_id[work_id].records if r.id == f'DATE-{work_id}-PHYSICAL-CD')
            self.assertEqual(cd.date, '2018-12-30')
            self.assertIn('物理CD', cd.medium)
            self.assertEqual(cd.source_url, 'https://xi5th.diverse.jp/')
            self.assertIn('Bandcamp電子版から除外', cd.evidence)
            self.assertNotEqual(by_id[work_id].earliest_record.id, cd.id)
        angel = by_id['XI-167']
        self.assertEqual({r.date for r in angel.records if r.id.startswith('DATE-')}, {'2021-08-13', '2021-10-13'})
        storia = by_id['XI-227']
        chapter = next(r for r in storia.records if r.id.endswith('CYTUS-CHAPTER'))
        sc = next(r for r in storia.records if r.id.endswith('SOUNDCLOUD'))
        self.assertEqual((chapter.date, sc.date), ('2015-07-01', '2015-07-02'))
        self.assertIn('資料照合', chapter.kind)
        self.assertIn('共同作者SoundCloud', sc.kind)
        # Original Reasons and its named 2022 remaster stay separate.
        self.assertNotIn('2020-10-26', [r.date for r in by_id['XI-140'].records])

    def test_playlist_audio_publication_records_are_video_events_not_game_debuts(self):
        expected = {
            'XI-244': ('2025-11-28', 'kLs6UW43MsQ'),
            'XI-247': ('2022-08-26', 'n5ihQvx3mlc'),
            'XI-201': ('2022-07-18', 'qZm9hZgEqWk'),
            'XI-206': ('2021-02-04', '8vexmJlrPgc'),
            'XI-089': ('2020-03-26', 'FOQbWtauVrQ'),
        }
        for work_id, (published, video_id) in expected.items():
            with self.subTest(work=work_id):
                entry = timeline_entry(by_id[work_id])
                self.assertEqual(entry.audio_access, 'official')
                self.assertEqual(entry.audio_status, 'available')
                self.assertIsNotNone(entry.release)
                self.assertEqual(entry.release.date, published)
                self.assertEqual(entry.release.kind, '公式動画公開日（当該動画版・初出未確定）')
                self.assertFalse(entry.release.true_first_publication_confirmed)
                self.assertIn('ゲーム初収録日', entry.release.evidence)
                self.assertIn('確定したものではない', entry.release.evidence)
                self.assertIn(video_id, entry.release.source_url)
                self.assertEqual(entry.full_record.id, entry.release.id)
                sources = [source for source in entry.audio_sources if video_id in source.url]
                self.assertEqual(len(sources), 1)
                self.assertEqual(sources[0].origin, 'official')
                self.assertIn('未実施', sources[0].evidence)
                detail = TestClient(app).get('/api/v1/works/' + work_id).json()
                records = [record for record in detail['records'] if record['id'] == entry.release.id]
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0]['date'], published)
        # The official video announces the following day's planned game addition.
        # Its publishDate remains the video event date, not a fabricated debut.
        taiko = timeline_entry(by_id['XI-247'])
        self.assertNotEqual(taiko.release.date, '2022-08-27')

    def test_all_works_are_returned_in_one_request(self):
        response = TestClient(app).get('/api/v1/timeline')
        self.assertEqual(response.status_code, 200)
        result = TimelineList.model_validate(response.json())
        self.assertEqual({entry.id for entry in result.items}, {work.id for work in works})
        self.assertEqual(len(result.items), len(works))
        self.assertRegex(result.as_of, r'^\d{4}-\d{2}-\d{2}$')

    def test_historical_release_does_not_prove_current_playback(self):
        entry = timeline_entry(by_id['XI-001'])
        self.assertIsNotNone(entry.release)
        self.assertEqual(entry.audio_status, 'unverified')
        self.assertEqual(entry.full_audio_links, [])

    def test_existing_full_audio_pages_are_not_playback_verification(self):
        entry = timeline_entry(by_id['XI-017'])
        self.assertEqual(entry.audio_status, 'available')
        self.assertTrue(entry.full_audio_links)
        self.assertIn('実再生', entry.audio_note)
        self.assertIn('未検証', entry.audio_note)

    def test_previews_and_crossfades_do_not_count_as_full_audio(self):
        for work_id in ['XI-060', 'XI-159']:
            with self.subTest(work=work_id):
                entry = timeline_entry(by_id[work_id])
                self.assertEqual(entry.audio_status, 'unverified' if work_id == 'XI-060' else 'available')
                self.assertEqual(entry.full_audio_links, [])

    def test_verified_playback_and_closed_audio_remain_distinct(self):
        original = by_id['XI-017']
        for evidence, expected in [('全編再生確認済み', 'available'), ('全編再生確認済みという情報は未確認', 'available'), ('削除を確認', 'unavailable')]:
            with self.subTest(evidence=evidence):
                link = original.listening[0].model_copy(update={'availability': evidence})
                work = original.model_copy(update={'listening': [link], 'records': [original.records[0]]})
                self.assertEqual(timeline_entry(work).audio_status, expected)

    def test_album_counts_as_listenable_by_user_rule(self):
        original = by_id['XI-017']
        work = original.model_copy(update={'listening': []})
        self.assertEqual(timeline_entry(work).audio_status, 'available')

    def test_soundcloud_publication_has_a_full_record(self):
        entry = timeline_entry(by_id['XI-063'])
        self.assertEqual(entry.audio_status, 'available')
        self.assertIsNotNone(entry.full_record)
        self.assertEqual(entry.full_record.date, '2015-05-05')

    def test_game_listing_alone_is_not_current_audio(self):
        original = by_id['XI-205']
        historical = original.model_copy(update={'audio_sources': [], 'listening': [], 'has_unofficial_audio': False})
        self.assertEqual(timeline_entry(historical).audio_status, 'unverified')
        self.assertIn('ゲーム収録歴だけ', timeline_entry(historical).audio_note)

    def test_unofficial_listings_remain_separate_from_official_links(self):
        for work_id in ['XI-228', 'XI-205']:
            with self.subTest(work=work_id):
                work = by_id[work_id]
                entry = timeline_entry(work)
                self.assertEqual(entry.audio_status, 'available')
                self.assertEqual(entry.audio_access, 'unofficial')
                self.assertEqual(work.listening, [])
                self.assertFalse(work.has_official_listening)
                self.assertEqual(entry.audio_sources, [])
                self.assertTrue(work.has_unofficial_audio)

    def test_official_cd_and_label_videos_are_current_audio(self):
        for work_id in ['XI-239', 'XI-252', 'XI-192']:
            with self.subTest(work=work_id):
                entry = timeline_entry(by_id[work_id])
                self.assertEqual(entry.audio_status, 'available')
                self.assertEqual(entry.audio_access, 'official')
                self.assertTrue(any(source.origin == 'official' for source in entry.audio_sources))
        parallax = timeline_entry(by_id['XI-252'])
        self.assertEqual(parallax.preview.date, '2026-10-24')
        self.assertEqual(parallax.full_record.date, '2026-10-30')

    def test_audio_sources_do_not_promote_attribution(self):
        self.assertEqual(by_id['XI-228'].attribution, 'unverified')
        self.assertEqual(by_id['XI-239'].attribution, 'unverified')

    def test_corrected_youtube_listings_keep_titles_origins_and_versions(self):
        expected = {
            'XI-009': ('deathpiano ~for four pianos~', 'unofficial', 'UxGOfPbPBPw'),
            'XI-018': ('up in the air', 'unofficial', '6hba4NjMXV4'),
            'XI-023': ('Time files', 'unofficial', 'Q63_BLJw8Bs'),
            'XI-025': ('.357 Magnum', 'unofficial', 'OcmY0sdiOIY'),
            'XI-068': ('After Burner', 'official', 'eFZCw4_NYys'),
            'XI-162': ('ULTIM@TE☆BE∀M!! [Game Size]', 'official', 'V4RzqUmyfAQ'),
        }
        client = TestClient(app)
        for work_id, (title, origin, video_id) in expected.items():
            with self.subTest(work=work_id):
                entry = timeline_entry(by_id[work_id])
                self.assertEqual(entry.title, title)
                self.assertEqual(entry.audio_status, 'available')
                self.assertEqual(entry.audio_access, origin)
                host = 'music.youtube.com' if work_id == 'XI-162' else 'www.youtube.com'
                detail = client.get(f'/api/v1/works/{work_id}').json()
                if origin == 'unofficial':
                    self.assertEqual(entry.audio_sources, [])
                    self.assertEqual(detail['audio_sources'], [])
                    self.assertTrue(detail['has_unofficial_audio'])
                    self.assertNotIn(video_id, str(detail))
                else:
                    self.assertEqual([(s.origin, s.url) for s in entry.audio_sources],
                                     [(origin, f'https://{host}/watch?v={video_id}')])
                    self.assertEqual(detail['audio_sources'][0]['origin'], origin)
                    self.assertIn('未実施', detail['audio_sources'][0]['evidence'])
        long_version = timeline_entry(by_id['XI-108'])
        self.assertEqual(long_version.title, 'After Burner (Long Version)')
        self.assertTrue(by_id['XI-108'].is_variant)
        self.assertNotIn('https://www.youtube.com/watch?v=eFZCw4_NYys',
                         [source.url for source in long_version.audio_sources])
        self.assertEqual(by_id['XI-161'].title, 'ULTIM@TE☆BE∀M!!')
        self.assertNotIn('https://music.youtube.com/watch?v=V4RzqUmyfAQ',
                         [source.url for source in timeline_entry(by_id['XI-161']).audio_sources])

    def test_existing_osu_previews_alone_are_not_full_youtube_recordings(self):
        for work_id in ['XI-009', 'XI-023', 'XI-025']:
            with self.subTest(work=work_id):
                work = by_id[work_id]
                self.assertTrue(any(link.url == 'https://osu.ppy.sh/beatmaps/artists/727'
                                    for link in work.listening))
                preview_only = work.model_copy(update={'audio_sources': [], 'has_unofficial_audio': False})
                self.assertEqual(timeline_entry(preview_only).audio_status, 'unverified')

    def test_official_alea_short_edit_is_preserved_without_full_album_promotion(self):
        work = by_id['XI-119']
        self.assertEqual(work.title, 'Alea jacta est! (xi Remix)')
        short_links = [link for link in work.listening if link.url == 'https://www.youtube.com/watch?v=5UH02v_g6fQ']
        self.assertEqual(len(short_links), 1)
        self.assertEqual(short_links[0].version, 'Short Edit')
        entry = timeline_entry(work)
        self.assertEqual(entry.audio_status, 'unverified')
        self.assertEqual(entry.full_audio_links, [])
        self.assertIsNone(entry.full_record)

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
