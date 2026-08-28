"""Shared types for job-posting adapters."""

from dataclasses import dataclass
from typing import Protocol


class AdapterError(RuntimeError):
    """Raised when an adapter cannot produce a trustworthy result."""


@dataclass(frozen=True)
class Job:
    key: str
    source: str
    company: str
    role: str
    location: str
    url: str | None
    posted: str


class Adapter(Protocol):
    name: str

    def fetch(self) -> list[Job]:
        """Fetch and parse all jobs from the adapter's source."""
