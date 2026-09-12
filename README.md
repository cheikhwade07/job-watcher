# Job watcher

This repository runs a scheduled GitHub Actions job that watches the
marker-bounded internships table in the Canadian Tech Internships 2027
aggregator plus public ATS feeds for Cohere, Solink, and Ciena. Matching new
postings are grouped into a GitHub issue with task list checkboxes.

## Run locally

The watcher uses only the Python standard library. From this directory:

```text
python -m unittest discover tests -v
python watcher.py --dry-run
python watcher.py --seed
```

`--dry-run` does not write state or create an issue. `--seed` records every
current feed row as seen without creating an issue. A normal run needs
`GITHUB_TOKEN` and `GITHUB_REPOSITORY` in its environment.

## Structure

- `adapters/base.py` defines the shared job record and adapter protocol.
- `adapters/gh_aggregator.py` reads the upstream internship table.
- `adapters/ashby.py` reads Ashby's public Job Postings API. Board slugs are
  configured in `watcher.py`.
- `adapters/workday.py` reads Workday's public CXS postings endpoint.
- `filters.py` applies independent title and location matches.
- `notify.py` creates GitHub Issues.
- `state/` stores seen keys, the last non-zero adapter row count, and active
  adapter outages. A transient Workday failure is retried; a persistently
  failing source is reported once and does not block healthy sources.

Job keys use stable posting identity fields. In particular, Workday keys use
the posting URL rather than its changing `postedOn` label, so an unchanged job
is not announced again as "Posted Today" becomes "Posted Yesterday."
