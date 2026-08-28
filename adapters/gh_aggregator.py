"""Adapter for the Canadian Tech Internships GitHub aggregator."""

import hashlib
import re
import urllib.error
import urllib.request

from adapters.base import AdapterError, Job


SOURCE_URL = (
    "https://raw.githubusercontent.com/negarprh/"
    "Canadian-Tech-Internships-2027/main/README.md"
)
BEGIN_MARKER = "<!-- BEGIN:INTERNSHIPS_TABLE -->"
END_MARKER = "<!-- END:INTERNSHIPS_TABLE -->"
SOURCE_NAME = "gh_aggregator"
CONTINUATION_MARKER = "↳"
LINK_RE = re.compile(r"\]\(([^)]*)\)")
SEPARATOR_RE = re.compile(r":?-+:?")


def _job_key(
    company: str,
    role: str,
    location: str,
    url: str | None,
    posted: str,
) -> str:
    tail = url if url else posted
    identity = f"{SOURCE_NAME}|{company}|{role}|{location}|{tail}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _parse_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None

    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if not any(cells):
        return None
    if all(SEPARATOR_RE.fullmatch(cell) for cell in cells):
        return None
    if cells == ["Company", "Role", "Location", "Apply", "Date Posted"]:
        return None
    if len(cells) != 5:
        raise AdapterError(f"{SOURCE_NAME} row has {len(cells)} columns, expected 5")
    return cells


def parse_readme(markdown: str) -> list[Job]:
    """Parse the marker-bounded internships table from a README."""
    begin = markdown.find(BEGIN_MARKER)
    end = markdown.find(END_MARKER)
    if begin == -1 or end == -1 or end < begin:
        raise AdapterError(f"{SOURCE_NAME} table markers not found")

    table = markdown[begin + len(BEGIN_MARKER) : end]
    jobs: list[Job] = []
    previous_company: str | None = None

    for line in table.splitlines():
        cells = _parse_row(line)
        if cells is None:
            continue

        company, role, location, apply_cell, posted = cells
        if company == CONTINUATION_MARKER:
            if previous_company is None:
                raise AdapterError(
                    f"{SOURCE_NAME} continuation row has no preceding company"
                )
            company = previous_company
        elif not company:
            raise AdapterError(f"{SOURCE_NAME} row has an empty company")
        else:
            previous_company = company

        links = LINK_RE.findall(apply_cell)
        url = links[-1] if links else None
        jobs.append(
            Job(
                key=_job_key(company, role, location, url, posted),
                source=SOURCE_NAME,
                company=company,
                role=role,
                location=location,
                url=url,
                posted=posted,
            )
        )

    return jobs


class GitHubAggregatorAdapter:
    name = SOURCE_NAME

    def __init__(self, source_url: str = SOURCE_URL) -> None:
        self.source_url = source_url

    def fetch(self) -> list[Job]:
        request = urllib.request.Request(
            self.source_url,
            headers={"User-Agent": "job-watcher"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                markdown = response.read().decode("utf-8")
        except (urllib.error.URLError, UnicodeDecodeError) as exc:
            raise AdapterError(f"{SOURCE_NAME} fetch failed: {exc}") from exc
        return parse_readme(markdown)
