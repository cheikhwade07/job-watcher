"""Adapter for Ashby's public job-posting feed."""

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

from adapters.base import AdapterError, Job


API_URL = "https://api.ashbyhq.com/posting-api/job-board/{board_name}"
SOURCE_PREFIX = "ashby"


def _job_key(board_name: str, job: Job) -> str:
    identity = "|".join(
        [
            SOURCE_PREFIX,
            board_name,
            job.company,
            job.role,
            job.location,
            job.url or "",
            job.posted,
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _text(value: object, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _locations(item: dict) -> str:
    values: list[str] = []
    primary = _text(item.get("location"))
    if primary:
        values.append(primary)

    secondary = item.get("secondaryLocations", [])
    if isinstance(secondary, list):
        for location in secondary:
            if isinstance(location, str) and location.strip():
                values.append(location.strip())
            elif isinstance(location, dict):
                label = _text(location.get("location")) or _text(
                    location.get("name")
                )
                if label:
                    values.append(label)

    return ", ".join(dict.fromkeys(values)) or "Unspecified"


def parse_job_board(payload: dict, board_name: str, company: str) -> list[Job]:
    """Parse an Ashby public job-board response into shared jobs."""
    postings = payload.get("jobs")
    if not isinstance(postings, list):
        raise AdapterError(f"{SOURCE_PREFIX}_{board_name} response has no jobs list")

    jobs: list[Job] = []
    for index, item in enumerate(postings):
        if not isinstance(item, dict):
            raise AdapterError(
                f"{SOURCE_PREFIX}_{board_name} job {index} is not an object"
            )
        role = _text(item.get("title"))
        if not role:
            raise AdapterError(f"{SOURCE_PREFIX}_{board_name} job {index} has no title")

        if item.get("isListed") is False:
            continue
        url = _text(item.get("jobUrl")) or _text(item.get("applyUrl")) or None
        posted = _text(item.get("publishedAt"), "Unknown")
        job = Job(
            key="",
            source=f"{SOURCE_PREFIX}_{board_name}",
            company=company,
            role=role,
            location=_locations(item),
            url=url,
            posted=posted,
        )
        jobs.append(
            Job(
                key=_job_key(board_name, job),
                source=job.source,
                company=job.company,
                role=job.role,
                location=job.location,
                url=job.url,
                posted=job.posted,
            )
        )
    return jobs


class AshbyAdapter:
    """Fetch one Ashby board, such as ``cohere`` or ``solink``."""

    def __init__(self, board_name: str, company: str, include_compensation: bool = True):
        if not board_name or not company:
            raise ValueError("board_name and company are required")
        self.board_name = board_name
        self.company = company
        self.include_compensation = include_compensation
        self.name = f"{SOURCE_PREFIX}_{board_name}"

    @property
    def source_url(self) -> str:
        query = urllib.parse.urlencode(
            {"includeCompensation": str(self.include_compensation).lower()}
        )
        return API_URL.format(
            board_name=urllib.parse.quote(self.board_name, safe="")
        ) + "?" + query

    def fetch(self) -> list[Job]:
        request = urllib.request.Request(
            self.source_url,
            headers={"Accept": "application/json", "User-Agent": "job-watcher"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdapterError(f"{self.name} fetch failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise AdapterError(f"{self.name} response is not a JSON object")
        return parse_job_board(payload, self.board_name, self.company)
