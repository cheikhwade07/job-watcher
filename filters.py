"""Permissive title and location filters for relevant postings."""

import re

from adapters.base import Job


TITLE_RE = re.compile(
    r"co-?op|intern(ship)?|student|new ?grad|stagiaire|[ée]tudiant",
    re.IGNORECASE,
)
LOCATION_RE = re.compile(r"Ottawa|Kanata|Toronto|Montr[eé]al|Remote", re.IGNORECASE)


def matches(job: Job) -> bool:
    """Return whether both the title and location match."""
    return bool(TITLE_RE.search(job.role) and LOCATION_RE.search(job.location))
