import unittest
from unittest.mock import patch

from adapters.base import AdapterError, Job
from watcher import _fetch_all, _notify_adapter_errors


class _HealthyAdapter:
    name = "healthy"

    def fetch(self) -> list[Job]:
        return [
            Job(
                key="healthy-key",
                source="healthy",
                company="Example",
                role="Software Intern",
                location="Ottawa, ON",
                url="https://example.test/job",
                posted="Today",
            )
        ]


class _BrokenAdapter:
    name = "broken"

    def fetch(self) -> list[Job]:
        raise AdapterError("temporary upstream failure")


class WatcherTests(unittest.TestCase):
    def test_broken_adapter_does_not_block_healthy_sources(self) -> None:
        jobs, counts, errors = _fetch_all(
            [_HealthyAdapter(), _BrokenAdapter()],
            {"healthy": 1, "broken": 1},
        )

        self.assertEqual([job.key for job in jobs], ["healthy-key"])
        self.assertEqual(counts["healthy"], 1)
        self.assertEqual(counts["broken"], 1)
        self.assertEqual(errors, {"broken": "ADAPTER BROKEN: broken: temporary upstream failure"})

    def test_adapter_error_is_not_notified_twice_during_same_outage(self) -> None:
        errors = {"broken": "ADAPTER BROKEN: broken: temporary upstream failure"}

        with patch("watcher.notify.create_issue") as create_issue:
            next_errors, notification_failed = _notify_adapter_errors(errors, {})

        create_issue.assert_called_once()
        self.assertEqual(next_errors, errors)
        self.assertFalse(notification_failed)

        with patch("watcher.notify.create_issue") as create_issue:
            next_errors, notification_failed = _notify_adapter_errors(errors, errors)

        create_issue.assert_not_called()
        self.assertEqual(next_errors, errors)
        self.assertFalse(notification_failed)


if __name__ == "__main__":
    unittest.main()
