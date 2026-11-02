import copy
import json
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SITE = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(SITE / "scripts"))
from fastapi.testclient import TestClient
from pydantic import ValidationError
from main import app, by_id, collections
from models import AudioSupplement, PublicCatalogue, PublicCollections, WorkDetail
from export_public import build_payload, link_comment
from public_annotations import apply_collection_annotations
from public_text import public_url

FORBIDDEN_KEYS = {
    "attribution_basis", "issues", "inclusion", "identity_note", "locator", "original_text",
    "original_workbook_claim", "approval_note", "approved_on", "interpretation_note",
    "verification_notes", "amendments", "revision_history", "local_path", "private_note",
}


def assert_public(test, value):
    if isinstance(value, dict):
        test.assertFalse(FORBIDDEN_KEYS.intersection(value))
        for child in value.values():
            assert_public(test, child)
    elif isinstance(value, list):
        for child in value:
            assert_public(test, child)
    elif isinstance(value, str):
        for marker in ["調査メモ：", "補助Excel", "追加照合は曲別ページで継続中", "INTERNAL_ONLY_CANARY"]:
            test.assertNotIn(marker, value)


class PublicBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_unofficial_audio_stays_available_without_public_upload_urls(self):
        audio = json.loads((BACKEND / "data/audio_sources.json").read_text(encoding="utf-8"))
        hidden = {source['url'] for item in audio for source in item['sources']
                  if source['origin'] == 'unofficial'}
        timeline = self.client.get('/api/v1/timeline').json()
        entries = {entry['id']: entry for entry in timeline['items']}
        for item in audio:
            if not any(source['origin'] == 'unofficial' for source in item['sources']):
                continue
            work_id = item['work_id']
            detail = self.client.get(f'/api/v1/works/{work_id}').json()
            self.assertTrue(detail['has_unofficial_audio'])
            self.assertEqual(entries[work_id]['audio_status'], 'available')
            self.assertIn('リンク非掲載', entries[work_id]['audio_note'])
        urls = ['/api/v1/timeline', '/api/v1/works?limit=100',
                '/api/v1/works?limit=100&offset=100', '/api/v1/works?limit=100&offset=200']
        urls += [f'/api/v1/works/{work_id}{suffix}' for work_id in by_id for suffix in ['', '/context']]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            for hidden_url in hidden:
                self.assertNotIn(hidden_url, response.text, url)

    def test_every_api_response_has_only_public_fields(self):
        urls = ["/api/v1/health", "/api/v1/meta", "/api/v1/timeline", "/api/v1/openapi.json",
                "/api/v1/works?limit=100", "/api/v1/works?limit=100&offset=100",
                "/api/v1/works?limit=100&offset=200", "/api/v1/works?q=Halcyon",
                "/api/v1/works?attribution=unverified", "/api/v1/albums", "/api/v1/games"]
        urls += [f"/api/v1/works/{work_id}{suffix}" for work_id in by_id for suffix in ["", "/context"]]
        urls += [f"/api/v1/{'albums' if collection.kind == 'album' else 'games'}/{collection.id}" for collection in collections]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                assert_public(self, response.json())
        schema = json.dumps(app.openapi())
        self.assertNotIn('AttributionBasis', schema)
        self.assertNotIn('AttributionSource', schema)

    def test_errors_and_private_paths_do_not_echo_inputs(self):
        for url, status in [("/api/v1/works/not-a-work", 404), ("/api/v1/works?limit=private-input", 422),
                            ("/xi_chronology/data/listener_comments.json", 404),
                            ("/backend/data/catalogue.json", 404), ("/.git/config", 404), ("/.env", 404)]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status)
            self.assertNotIn('private-input', response.text)
            assert_public(self, response.json())

    def test_distributed_json_has_strict_top_level_and_nested_schemas(self):
        catalogue = json.loads((BACKEND / "data/catalogue.json").read_text(encoding="utf-8"))
        collection_data = json.loads((BACKEND / "data/collections.json").read_text(encoding="utf-8"))
        PublicCatalogue.model_validate(catalogue)
        PublicCollections.model_validate(collection_data)
        audio = json.loads((BACKEND / "data/audio_sources.json").read_text(encoding="utf-8"))
        for supplement in audio:
            AudioSupplement.model_validate(supplement)
        assert_public(self, audio)
        assert_public(self, catalogue)
        assert_public(self, collection_data)
        for location in ["root", "work", "source"]:
            bad = copy.deepcopy(catalogue)
            target = bad if location == "root" else bad["works"][0] if location == "work" else bad["works"][0]["sources"][0]
            target["private_note"] = "INTERNAL_ONLY_CANARY"
            with self.assertRaises(ValidationError):
                PublicCatalogue.model_validate(bad)

    def test_raw_research_prose_and_citation_internals_cannot_enter_export(self):
        marker = "INTERNAL_ONLY_CANARY"
        work = {"id": "XI-TEST", "title": "Public title", "credited_name": "xi", "role": "作曲",
                "comment": marker, "issues": [marker], "aliases": [], "relationships": [],
                "official_listening": [], "checked_on": "2026-10-30"}
        source = {"kind": "primary", "label": "Author page", "url": "https://example.com/author",
                  "credit": "xi", "checked_on": "2026-10-30", "locator": marker,
                  "summary": marker, "identity_note": marker, "private_note": marker}
        reviews = {"XI-TEST": {"verdict": "unverified", "summary": marker, "inclusion": [source],
                               "sources": [source, {**source, "kind": "lead"}, {**source, "kind": "input"}]}}
        payload = build_payload({"works": [work]}, [], reviews,
                                {"XI-TEST": {"comment": marker, "issues": [marker]}}, {}, {},
                                {"XI-TEST": {"comment": "Reviewed public explanation."}})
        value = payload.model_dump()
        self.assertNotIn(marker, json.dumps(value))
        self.assertEqual(value["works"][0]["comment"], "Reviewed public explanation.")
        self.assertEqual(len(value["works"][0]["sources"]), 1)
        self.assertEqual(set(value["works"][0]["sources"][0]), {"kind", "label", "url", "credit", "checked_on"})

    def test_collection_notes_require_review_and_ignore_internal_prose(self):
        track = {"work_id": "XI-TEST", "title": "Public title", "disc": None, "track_number": 1,
                 "evidence": "INTERNAL_ONLY_CANARY", "note": "INTERNAL_ONLY_CANARY"}
        raw = [{"id": "test", "note": "INTERNAL_ONLY_CANARY", "tracks": [track]}]
        approved = {"schema_version": 1, "entries": {"test": {"note": "Public album note", "tracks": [
            {**track, "evidence": "Official track list", "note": "Version unknown"}]}}}
        value = apply_collection_annotations(raw, approved)
        self.assertNotIn('INTERNAL_ONLY_CANARY', json.dumps(value))
        raw[0]["tracks"].append({**track, "title": "Unreviewed addition"})
        with self.assertRaises(ValueError):
            apply_collection_annotations(raw, approved)

    def test_private_text_and_nonpublic_urls_fail_closed(self):
        work = by_id["XI-025"].model_dump()
        for text in ["C:/Users/test/private.txt", "file:///private.txt", "test@example.invalid",
                     "ghp_" + "0" * 40, "-----BEGIN PRIVATE KEY-----"]:
            with self.subTest(pattern_type=text.split(':')[0][:8]):
                with self.assertRaises(ValidationError):
                    WorkDetail.model_validate({**work, "comment": text})
        for url in ["file:///private.txt", "http://127.0.0.1/data", "http://localhost/data",
                    "https://user:password@example.com/source", "https://example.com/?access_token=private"]:
            with self.assertRaises(ValueError):
                public_url(url)

    def test_public_titles_editorial_notes_readings_and_sources_are_preserved(self):
        data = SITE.parent / "xi_chronology/data"
        notes = json.loads((data / "public_annotations.json").read_text(encoding="utf-8"))["entries"]
        listeners = json.loads((data / "listener_comments.json").read_text(encoding="utf-8"))["entries"]
        raw_works = json.loads((data / "works.json").read_text(encoding="utf-8"))["works"]
        raw_works += json.loads((data / "additional_works.json").read_text(encoding="utf-8"))["works"]
        self.assertEqual(len(by_id), 253)
        self.assertEqual({wid: work.title for wid, work in by_id.items()}, {work['id']: work['title'] for work in raw_works})
        self.assertEqual(sum(work.attribution == "credited" for work in by_id.values()), 165)
        self.assertEqual(sum(bool(work.pronunciation) for work in by_id.values()), 3)
        for work_id, entry in listeners.items():
            if entry["status"] == "written":
                self.assertIn(link_comment(entry["text"], work_id, raw_works), by_id[work_id].comment)
        self.assertIn("後の『[Halcyon](/works/XI-026)』を思わせる", by_id["XI-025"].comment)
        self.assertIn("ピアノ中心のハードルネッサンス", by_id["XI-072"].comment)
        self.assertIn("https://x.com/com_giko_31/status/616629483831865345", by_id["XI-072"].comment)
        self.assertTrue(any(source.url.startswith("https://") for source in by_id["XI-025"].sources))
        self.assertEqual(set(notes), {work_id for work_id, work in by_id.items() if work.comment})


if __name__ == "__main__":
    unittest.main()
