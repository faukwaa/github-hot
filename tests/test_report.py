import unittest

from github_hot.report import build_report


class ReportTests(unittest.TestCase):
    def test_ranking_and_growth(self):
        rows = [
            {
                "full_name": "a/one",
                "stars": 1000,
                "weekly_stars": 250,
                "language": "Python",
                "source": "trending:python",
                "collected_at": "2026-08-11T00:00:00+00:00",
                "ai_reasons": [],
            },
            {
                "full_name": "b/two",
                "stars": 5000,
                "weekly_stars": 5000,
                "language": "Go",
                "source": "search:ai",
                "collected_at": "2026-08-11T00:00:00+00:00",
                "ai_reasons": ["topic:ai"],
            },
        ]
        report = build_report(rows, limit=10)
        items = report["items"]
        self.assertEqual([item["full_name"] for item in items], ["b/two", "a/one"])
        self.assertIsNone(items[0]["weekly_growth"])
        self.assertAlmostEqual(items[1]["weekly_growth"], 33.3, places=1)
        self.assertEqual(report["meta"]["total_weekly_stars"], 5250)
        self.assertTrue(items[0]["is_ai"])
        self.assertFalse(items[1]["is_ai"])
        self.assertEqual(report["meta"]["ai_count"], 1)
