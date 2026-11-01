import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from main import app, by_id, collections
from models import WorkContext


class WorkContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def context(self, work_id):
        response = self.client.get(f"/api/v1/works/{work_id}/context")
        self.assertEqual(response.status_code, 200)
        return WorkContext.model_validate(response.json())

    def test_every_membership_matches_exact_work_id_and_preserves_track_status(self):
        for work_id in by_id:
            with self.subTest(work_id=work_id):
                context = self.context(work_id)
                actual = {
                    (item.collection.kind, item.collection.id): item.tracks
                    for item in context.albums + context.games
                }
                expected = {
                    (collection.kind, collection.id): [t for t in collection.tracks if t.work_id == work_id]
                    for collection in collections if any(t.work_id == work_id for t in collection.tracks)
                }
                self.assertEqual(actual, expected)
                self.assertTrue(all(item.collection.kind == "album" for item in context.albums))
                self.assertTrue(all(item.collection.kind == "game" for item in context.games))

    def test_guest_remixes_link_to_original_without_becoming_original_recordings(self):
        halcyon = self.context("XI-026")
        self.assertEqual({remix.title for remix in halcyon.remixes}, {"Halcyon (lapix Remix)", "Halcyon (現役JK Remix)"})
        self.assertTrue(all(remix.source_url and remix.album_id and remix.credited_name for remix in halcyon.remixes))
        for membership in halcyon.albums:
            self.assertTrue(all("Remix" not in track.title for track in membership.tracks))
        parousia = self.context("XI-034")
        self.assertEqual([remix.title for remix in parousia.remixes], ["Parousia (Blacklolita Remix)"])
        self.assertEqual([remix.title for remix in self.context("XI-039").remixes], ["天衣無縫 (EmoCo Remix)"])

    def test_remix_direction_excludes_originals_and_other_versions(self):
        self.assertEqual([remix.work_id for remix in self.context("XI-072").remixes], ["XI-251"])
        self.assertEqual(self.context("XI-251").remixes, [])
        self.assertEqual(self.context("XI-166").remixes, [])  # Aiolos long version / remaster
        freedom = self.context("XI-017")
        self.assertEqual([remix.work_id for remix in freedom.remixes], ["XI-103"])
        self.assertIn("未確定", freedom.remixes[0].evidence_status)
        self.assertEqual(self.context("XI-103").remixes, [])

    def test_missing_work_and_empty_context(self):
        self.assertEqual(self.client.get("/api/v1/works/not-a-work/context").status_code, 404)
        empty_id = next(work_id for work_id in by_id if not any(t.work_id == work_id for c in collections for t in c.tracks)
                        and not by_id[work_id].relationships)
        self.assertEqual(self.context(empty_id).model_dump(), {"albums": [], "games": [], "remixes": []})


if __name__ == "__main__":
    unittest.main()
