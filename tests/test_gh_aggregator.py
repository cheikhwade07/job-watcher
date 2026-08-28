import unittest
from pathlib import Path

from adapters.base import AdapterError
from adapters.gh_aggregator import parse_readme


FIXTURE = Path(__file__).parent / "fixtures" / "readme_sample.md"


class GitHubAggregatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.readme = FIXTURE.read_text(encoding="utf-8")
        self.jobs = parse_readme(self.readme)

    def test_continuation_row_inherits_company(self) -> None:
        self.assertEqual(self.jobs[1].company, "RTX")

    def test_nested_badge_extracts_apply_target(self) -> None:
        self.assertIsNotNone(self.jobs[0].url)
        self.assertIn("globalhr.wd5.myworkdayjobs.com", self.jobs[0].url)
        self.assertNotIn("img.shields.io", self.jobs[0].url)

    def test_missing_url_keeps_row(self) -> None:
        autodesk = self.jobs[-1]
        self.assertEqual(autodesk.company, "Autodesk")
        self.assertIsNone(autodesk.url)

    def test_leading_whitespace_before_pipe(self) -> None:
        self.assertEqual(self.jobs[1].role, "Customer Data Management and Analysis Intern")

    def test_missing_markers_raise(self) -> None:
        with self.assertRaises(AdapterError):
            parse_readme("| Company | Role | Location | Apply | Date Posted |")


if __name__ == "__main__":
    unittest.main()
