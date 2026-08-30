import json
import unittest
from unittest.mock import MagicMock, patch

from adapters.base import AdapterError
from adapters.workday import PAGE_SIZE, WorkdayAdapter, parse_page


class WorkdayTests(unittest.TestCase):
    def test_parses_external_path_and_locations(self) -> None:
        jobs = parse_page(
            {
                "total": 1,
                "jobPostings": [
                    {
                        "title": "Embedded Software Developer (New Grad)",
                        "locationsText": "Canada-Ottawa",
                        "postedOn": "Posted 5 Days Ago",
                        "externalPath": "/job/Embedded-Software-Developer_R031481",
                    }
                ],
            },
            "Careers",
            "Ciena",
            "https://ciena.wd5.myworkdayjobs.com/en-US/Careers",
        )
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].company, "Ciena")
        self.assertIn("Ottawa", jobs[0].location)
        self.assertEqual(
            jobs[0].url,
            "https://ciena.wd5.myworkdayjobs.com/en-US/Careers/job/Embedded-Software-Developer_R031481",
        )
        self.assertTrue(jobs[0].key)

    def test_endpoint_and_page_size(self) -> None:
        adapter = WorkdayAdapter("ciena", "Careers", "Ciena")
        self.assertEqual(
            adapter.endpoint,
            "https://ciena.wd5.myworkdayjobs.com/wday/cxs/ciena/Careers/jobs",
        )
        self.assertEqual(
            adapter.board_url,
            "https://ciena.wd5.myworkdayjobs.com/en-US/Careers",
        )
        self.assertEqual(PAGE_SIZE, 20)

    def test_fetch_paginates_and_keeps_first_total(self) -> None:
        first_page = {
            "total": 21,
            "jobPostings": [
                {
                    "title": f"Intern {index}",
                    "locationsText": "Canada-Ottawa",
                    "externalPath": f"/job/intern-{index}",
                }
                for index in range(20)
            ],
        }
        second_page = {
            "total": 0,
            "jobPostings": [
                {
                    "title": "Intern 20",
                    "locationsText": "Canada-Ottawa",
                    "externalPath": "/job/intern-20",
                }
            ],
        }
        responses = []
        for payload in (first_page, second_page):
            response = MagicMock()
            response.__enter__.return_value = response
            response.read.return_value = json.dumps(payload).encode("utf-8")
            responses.append(response)

        adapter = WorkdayAdapter("ciena", "Careers", "Ciena")
        with patch(
            "adapters.workday.urllib.request.urlopen", side_effect=responses
        ) as urlopen:
            jobs = adapter.fetch()

        self.assertEqual(len(jobs), 21)
        self.assertEqual(urlopen.call_count, 2)
        first_request = urlopen.call_args_list[0].args[0]
        second_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(
            json.loads(first_request.data),
            {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
        )
        self.assertEqual(
            json.loads(second_request.data),
            {"appliedFacets": {}, "limit": 20, "offset": 20, "searchText": ""},
        )

    def test_missing_postings_list_raises(self) -> None:
        with self.assertRaises(AdapterError):
            parse_page({}, "Careers", "Ciena", "https://example.test/Careers")


if __name__ == "__main__":
    unittest.main()
