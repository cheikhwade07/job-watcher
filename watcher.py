"""Scheduled job-posting watcher entry point."""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import notify
from adapters.base import Adapter, AdapterError, Job
from adapters.ashby import AshbyAdapter
from adapters.gh_aggregator import GitHubAggregatorAdapter
from adapters.workday import WorkdayAdapter
from filters import matches


ROOT = Path(__file__).resolve().parent
SEEN_PATH = ROOT / "state" / "seen.json"
COUNTS_PATH = ROOT / "state" / "counts.json"


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fetch_all(
    adapters: list[Adapter], counts: dict[str, int]
) -> tuple[list[Job], dict[str, int]]:
    jobs: list[Job] = []
    next_counts = dict(counts)
    for adapter in adapters:
        try:
            adapter_jobs = adapter.fetch()
        except AdapterError as exc:
            raise RuntimeError(f"ADAPTER BROKEN: {adapter.name}: {exc}") from exc

        previous_count = counts.get(adapter.name, 0)
        if not adapter_jobs and previous_count > 0:
            raise RuntimeError(f"ADAPTER BROKEN: {adapter.name}")
        if adapter_jobs:
            next_counts[adapter.name] = len(adapter_jobs)
        jobs.extend(adapter_jobs)
    return jobs, next_counts


def _digest_body(jobs: list[Job]) -> str:
    by_company: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        by_company[job.company].append(job)

    sections: list[str] = []
    for company, company_jobs in by_company.items():
        lines = [f"## {company}"]
        for job in company_jobs:
            destination = job.url if job.url else "no url in feed"
            lines.append(
                f"- [ ] **{job.role}** - {job.location} - "
                f"posted {job.posted} - {destination}"
            )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def _title(count: int) -> str:
    return f"{count} new posting(s) - {date.today().isoformat()}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch the job aggregator feed.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--seed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    adapters: list[Adapter] = [
        GitHubAggregatorAdapter(),
        AshbyAdapter("cohere", "Cohere"),
        AshbyAdapter("solink", "Solink"),
        WorkdayAdapter("ciena", "Careers", "Ciena"),
    ]
    seen = _load_json(SEEN_PATH)
    counts = _load_json(COUNTS_PATH)

    if not args.dry_run and not args.seed:
        try:
            notify.validate_configuration()
        except RuntimeError as exc:
            print(f"Watcher error: {exc}", file=sys.stderr)
            return 1

    try:
        all_jobs, next_counts = _fetch_all(adapters, counts)
    except RuntimeError as exc:
        if args.dry_run:
            print(f"DRY RUN: {exc}")
            return 1
        message = str(exc)
        if message.startswith("ADAPTER BROKEN:"):
            adapter_name = message.split(":", 2)[1].strip()
            try:
                notify.create_issue(
                    f"ADAPTER BROKEN: {adapter_name}",
                    message,
                    "broken",
                )
            except RuntimeError as notify_error:
                print(f"Watcher error: {notify_error}", file=sys.stderr)
            else:
                print(message, file=sys.stderr)
            return 1
        print(f"Watcher error: {exc}", file=sys.stderr)
        return 1

    filtered = [job for job in all_jobs if matches(job)]
    new_jobs = [job for job in filtered if job.key not in seen]

    if args.dry_run:
        print(f"DRY RUN: {len(filtered)} posting(s) passed the filter.")
        print(f"DRY RUN: {len(new_jobs)} new posting(s) would be posted.")
        if new_jobs:
            print(f"Title: {_title(len(new_jobs))}")
            print("Body:")
            print(_digest_body(new_jobs))
        return 0

    if args.seed:
        for job in all_jobs:
            seen[job.key] = date.today().isoformat()
        _write_json(SEEN_PATH, seen)
        _write_json(COUNTS_PATH, next_counts)
        print(f"Seeded {len(all_jobs)} posting(s).")
        return 0

    if new_jobs:
        try:
            notify.create_issue(
                _title(len(new_jobs)),
                _digest_body(new_jobs),
                "new-postings",
            )
        except RuntimeError as exc:
            print(f"Watcher error: {exc}", file=sys.stderr)
            return 1
        for job in new_jobs:
            seen[job.key] = date.today().isoformat()

    _write_json(SEEN_PATH, seen)
    _write_json(COUNTS_PATH, next_counts)
    print(f"Fetched {len(all_jobs)} posting(s); {len(new_jobs)} new after filtering.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
