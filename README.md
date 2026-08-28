# Job watcher

This repository runs a twice-daily GitHub Actions job that watches the
marker-bounded internships table in the Canadian Tech Internships 2027
aggregator. Matching new postings are grouped into a GitHub issue with task
list checkboxes.

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
- `adapters/gh_aggregator.py` is the only data source in v1.
- `filters.py` applies independent title and location matches.
- `notify.py` creates GitHub Issues.
- `state/` stores seen keys and the last non-zero adapter row count.

The job key is derived from source, company, role, and location, so edits to
an aggregator URL do not create duplicate notifications.
