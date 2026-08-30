import json
import unittest
from unittest.mock import MagicMock, patch

from adapters.ashby import AshbyAdapter, parse_job_board
from adapters.base import AdapterError


class AshbyTests(unittest.TestCase):
    def test_parses_documented_fields(self) -> None:
        jobs = parse_job_board(
            {
                "apiVersion": "1",
                "jobs": [
                    {
                        "title": "Machine Learning Intern",
                        "location": "Ottawa, Ontario, Canada",
                        "secondaryLocations": ["Toronto, Ontario, Canada"],
                        "publishedAt": "2026-08-30T12:00:00.000Z",
                        "jobUrl": "https://jobs.ashbyhq.com/cohere/job-1",
                        "applyUrl": "https://jobs.ashbyhq.com/cohere/job-1/application",
                    }
                ],
            },
            "cohere",
            "Cohere",
        )
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].company, "Cohere")
        self.assertEqual(jobs[0].role, "Machine Learning Intern")
        self.assertIn("Ottawa", jobs[0].location)
        self.assertIn("Toronto", jobs[0].location)
        self.assertEqual(jobs[0].url, "https://jobs.ashbyhq.com/cohere/job-1")
        self.assertTrue(jobs[0].key)

    def test_source_url_uses_public_board_slug(self) -> None:
        adapter = AshbyAdapter("cohere", "Cohere")
        self.assertEqual(
            adapter.source_url,
            "https://api.ashbyhq.com/posting-api/job-board/cohere?includeCompensation=true",
        )

    def test_fetch_uses_json_feed(self) -> None:
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({"jobs": []}).encode("utf-8")
        with patch(
            "adapters.ashby.urllib.request.urlopen", return_value=response
        ) as urlopen:
            self.assertEqual(AshbyAdapter("cohere", "Cohere").fetch(), [])

        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(
            request.full_url,
            "https://api.ashbyhq.com/posting-api/job-board/cohere?includeCompensation=true",
        )

    def test_unlisted_posting_is_ignored(self) -> None:
        jobs = parse_job_board(
            {"jobs": [{"title": "Hidden", "isListed": False}]},
            "cohere",
            "Cohere",
        )
        self.assertEqual(jobs, [])

    def test_missing_jobs_list_raises(self) -> None:
        with self.assertRaises(AdapterError):
            parse_job_board({}, "cohere", "Cohere")


if __name__ == "__main__":
    unittest.main()
