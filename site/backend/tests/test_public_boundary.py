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
from models import PublicCatalogue, PublicCollections, WorkDetail
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
        assert_public(self, catalogue)
        assert_public(self, collection_data)
        for location in ["root", "work", "source"]:
            bad = copy.deepcopy(catalogue)
            target = bad if location == "root" else bad["works"][0] if location == "work" else bad["works"][0]["sources"][0]
            target["private_note"] = "INTERNAL_ONLY_CANARY"
            with self.assertRaises(ValidationError):
                PublicCatalogue.model_validate(bad)



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



    def test_public_snapshot_preserves_titles_editorial_notes_and_readings(self):
        self.assertEqual(len(by_id), 253)
        self.assertEqual(sum(work.attribution == "credited" for work in by_id.values()), 165)
        self.assertEqual(sum(bool(work.pronunciation) for work in by_id.values()), 3)
        self.assertEqual(by_id["XI-025"].title, ".357 Magnum")
        self.assertIn("後の『[Halcyon](/works/XI-026)』を思わせる", by_id["XI-025"].comment)
        self.assertIn("ピアノ中心のハードルネッサンス", by_id["XI-072"].comment)
        self.assertIn("https://x.com/com_giko_31/status/616629483831865345", by_id["XI-072"].comment)
        self.assertEqual(by_id["XI-034"].pronunciation.reading, "パルーシア")
        self.assertTrue(any(source.url.startswith("https://") for source in by_id["XI-025"].sources))


if __name__ == "__main__":
    unittest.main()
