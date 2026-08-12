import os
import tempfile
import unittest

from github_hot.models import TrendingRepo
from github_hot.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test.db")
        self.store = Store(self.db_path).connect()

    def tearDown(self):
        self.store.close()
        self.tmpdir.cleanup()

    def _repo(self, name, weekly):
        return TrendingRepo(
            full_name=name,
            url=f"https://github.com/{name}",
            description="LLM tool",
            language="Python",
            stars=weekly + 100,
            weekly_stars=weekly,
            source="trending:python",
        )

    def test_save_and_load_latest(self):
        self.store.save_repos(
            [self._repo("a/one", 200), self._repo("b/two", 800)],
            "2026-08-11T00:00:00+00:00",
        )
        rows = self.store.load_latest(limit=10)
        self.assertEqual([row["full_name"] for row in rows], ["b/two", "a/one"])
        self.assertEqual(rows[0]["weekly_stars"], 800)

    def test_second_collection_replaces_snapshot(self):
        self.store.save_repos([self._repo("a/one", 200)], "2026-08-10T00:00:00+00:00")
        self.store.save_repos([self._repo("a/one", 900)], "2026-08-11T00:00:00+00:00")
        rows = self.store.load_latest()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["weekly_stars"], 900)
        self.assertEqual(rows[0]["collected_at"], "2026-08-11T00:00:00+00:00")
