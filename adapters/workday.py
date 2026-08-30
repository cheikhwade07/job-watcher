"""Adapter for Workday's public CXS job-posting endpoint."""

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

from adapters.base import AdapterError, Job


PAGE_SIZE = 20
MAX_PAGES = 100
SOURCE_PREFIX = "workday"


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
    locations_text = _text(item.get("locationsText"))
    if locations_text:
        return locations_text

    locations = item.get("locations", [])
    if isinstance(locations, list):
        values = []
        for location in locations:
            if isinstance(location, str) and location.strip():
                values.append(location.strip())
            elif isinstance(location, dict):
                label = _text(location.get("descriptor")) or _text(
                    location.get("name")
                )
                if label:
                    values.append(label)
        if values:
            return ", ".join(dict.fromkeys(values))
    return "Unspecified"


def _posting_url(board_url: str, external_path: object) -> str | None:
    path = _text(external_path)
    if not path:
        return None
    base = urllib.parse.urlsplit(board_url)
    base_path = base.path.rstrip("/")
    relative_path = path.lstrip("/")
    if relative_path.startswith(base_path.lstrip("/") + "/"):
        relative_path = relative_path[len(base_path.lstrip("/")) + 1 :]
    return urllib.parse.urlunsplit(
        (base.scheme, base.netloc, f"{base_path}/{relative_path}", "", "")
    )


def parse_page(
    payload: dict, board_name: str, company: str, board_url: str
) -> list[Job]:
    """Parse one Workday CXS page response."""
    postings = payload.get("jobPostings")
    if not isinstance(postings, list):
        raise AdapterError(f"{SOURCE_PREFIX}_{board_name} response has no jobPostings list")

    jobs: list[Job] = []
    for index, item in enumerate(postings):
        if not isinstance(item, dict):
            raise AdapterError(
                f"{SOURCE_PREFIX}_{board_name} job {index} is not an object"
            )
        role = _text(item.get("title"))
        if not role:
            raise AdapterError(f"{SOURCE_PREFIX}_{board_name} job {index} has no title")
        url = _posting_url(board_url, item.get("externalPath"))
        posted = _text(item.get("postedOn"), "Unknown")
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


class WorkdayAdapter:
    """Fetch all pages from one public Workday job board."""

    def __init__(
        self,
        tenant: str,
        site: str,
        company: str,
        host_suffix: str = "wd5.myworkdayjobs.com",
        locale: str = "en-US",
    ):
        if not tenant or not site or not company or not locale:
            raise ValueError("tenant, site, company, and locale are required")
        self.tenant = tenant
        self.site = site
        self.company = company
        self.host_suffix = host_suffix
        self.locale = locale
        self.name = f"{SOURCE_PREFIX}_{tenant}_{site}"
        self.board_url = f"https://{tenant}.{host_suffix}/{locale}/{site}"
        self.endpoint = (
            f"https://{tenant}.{host_suffix}/wday/cxs/{tenant}/{site}/jobs"
        )

    def _fetch_page(self, offset: int) -> dict:
        body = json.dumps(
            {
                "appliedFacets": {},
                "limit": PAGE_SIZE,
                "offset": offset,
                "searchText": "",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Accept-Language": f"{self.locale},en;q=0.9",
                "Content-Type": "application/json",
                "User-Agent": "job-watcher",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdapterError(f"{self.name} fetch failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise AdapterError(f"{self.name} response is not a JSON object")
        return payload

    def fetch(self) -> list[Job]:
        jobs: list[Job] = []
        offset = 0
        total: int | None = None
        for _ in range(MAX_PAGES):
            payload = self._fetch_page(offset)
            page_jobs = parse_page(payload, self.site, self.company, self.board_url)
            jobs.extend(page_jobs)

            if total is None and isinstance(payload.get("total"), int):
                total = payload["total"]
            if not page_jobs or len(page_jobs) < PAGE_SIZE:
                break
            if total is not None and offset + len(page_jobs) >= total:
                break
            offset += len(page_jobs)
        else:
            raise AdapterError(f"{self.name} exceeded {MAX_PAGES} pages")
        return jobs
