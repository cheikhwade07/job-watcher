import json
import os
import unittest
from unittest.mock import MagicMock, patch

import notify


class NotifyTests(unittest.TestCase):
    def test_missing_token_raises(self) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "GITHUB_REPOSITORY": "owner/repo"}):
            with self.assertRaises(RuntimeError):
                notify.create_issue("title", "body", "label")

    def test_request_body_is_task_list_markdown(self) -> None:
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"{}"
        with patch.dict(
            os.environ,
            {"GITHUB_TOKEN": "test-token", "GITHUB_REPOSITORY": "owner/repo"},
        ):
            with patch("notify.urllib.request.urlopen", return_value=response) as urlopen:
                notify.create_issue(
                    "1 new posting(s) - 2026-08-28",
                    "## Example\n- [ ] **Intern** - Toronto, ON - posted Aug 28, 2026 - no url in feed",
                    "new-postings",
                )

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertRegex(payload["body"], r"(?m)^- \[ \] ")
        self.assertEqual(payload["labels"], ["new-postings"])


if __name__ == "__main__":
    unittest.main()
