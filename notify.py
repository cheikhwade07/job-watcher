"""GitHub Issues notification client."""

import json
import os
import urllib.error
import urllib.request


def _configuration() -> tuple[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")
    if not repository:
        raise RuntimeError("GITHUB_REPOSITORY is required")
    return token, repository


def validate_configuration() -> None:
    """Raise if the environment cannot support an issue notification."""
    _configuration()


def create_issue(title: str, body: str, label: str) -> dict:
    """Create an issue in the repository configured by the Actions environment."""
    token, repository = _configuration()
    endpoint = f"https://api.github.com/repos/{repository}/issues"
    payload = json.dumps({"title": title, "body": body, "labels": [label]}).encode(
        "utf-8"
    )
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "job-watcher",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub issue creation failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("GitHub issue creation failed") from exc
    return json.loads(response_body.decode("utf-8")) if response_body else {}
