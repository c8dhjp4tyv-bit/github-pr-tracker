"""Aggregate GitHub PR search results, checks, statuses, and reviews."""

from __future__ import annotations

import re
from urllib.parse import urlsplit
from typing import Any

from .api import GitHubAPIError, GitHubClient
from .models import TrackedPR


_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+$")
_FAILURE_CONCLUSIONS = {
    "failure", "timed_out", "cancelled", "action_required",
    "startup_failure", "stale",
}
_SUCCESS_CONCLUSIONS = {"success", "neutral", "skipped"}


def resolve_username(client: GitHubClient, username: str | None) -> str:
    """Validate an explicit username or retrieve the authenticated account."""
    if not username:
        if not client.token:
            raise ValueError("Specify --user or set GITHUB_TOKEN")
        payload = client.get("/user")
        username = payload.get("login", "")
    if not isinstance(username, str) or not _LOGIN.fullmatch(username):
        raise ValueError("Invalid GitHub username")
    return username


def _repo_from_issue(issue: dict[str, Any]) -> str:
    """Extract and validate owner/repository from a GitHub search hit."""
    parsed = urlsplit(str(issue.get("repository_url", "")))
    if parsed.scheme != "https" or parsed.netloc != "api.github.com":
        raise GitHubAPIError("Invalid repository URL in GitHub search result")
    segments = parsed.path.split("/")
    if len(segments) != 4 or segments[1] != "repos":
        raise GitHubAPIError("Invalid repository path in GitHub search result")
    owner, name = segments[2], segments[3]
    if not _LOGIN.fullmatch(owner) or not _REPOSITORY.fullmatch(name):
        raise GitHubAPIError("Invalid repository name in GitHub search result")
    return owner + "/" + name


def summarize_ci(check_runs: list[dict[str, Any]], statuses: list[dict[str, Any]]) -> str:
    """Aggregate checks and commit statuses; failures take precedence."""
    results: list[str] = []
    for check in check_runs:
        if check.get("status") != "completed":
            results.append("pending")
        else:
            conclusion = check.get("conclusion")
            if conclusion in _FAILURE_CONCLUSIONS:
                results.append("failing")
            elif conclusion in _SUCCESS_CONCLUSIONS:
                results.append("passing")
            else:
                results.append("pending")
    for status in statuses:
        state = status.get("state")
        if state in ("failure", "error"):
            results.append("failing")
        elif state == "success":
            results.append("passing")
        else:
            results.append("pending")

    if not results:
        return "unknown"
    if "failing" in results:
        return "failing"
    if "pending" in results:
        return "pending"
    return "passing"


def summarize_reviews(reviews: list[dict[str, Any]], reviewers_requested: int) -> str:
    """Use the latest decision per reviewer; ignore non-decision comments."""
    latest: dict[str, str] = {}
    for review in reviews:
        user = review.get("user") or {}
        login = user.get("login")
        state = review.get("state")
        if login and state in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            latest[login] = state

    if "CHANGES_REQUESTED" in latest.values():
        return "changes_requested"
    if "APPROVED" in latest.values():
        return "approved"
    if reviewers_requested:
        return "requested"
    return "none"


def list_reviews(client: GitHubClient, path: str) -> list[dict[str, Any]]:
    """Read review history, capped at ten 100-result API pages."""
    reviews: list[dict[str, Any]] = []
    for page in range(1, 11):
        batch = client.get(path, {"per_page": 100, "page": page})
        if not isinstance(batch, list):
            raise GitHubAPIError("Unexpected reviews response from GitHub")
        reviews.extend(batch)
        if len(batch) < 100:
            break
    return reviews


def get_open_prs(client: GitHubClient, username: str, limit: int = 10) -> list[TrackedPR]:
    """Get recently updated open PRs, with live CI and review metadata."""
    if not 1 <= limit <= 100:
        raise ValueError("--limit must be between 1 and 100")

    results: list[TrackedPR] = []
    page = 1
    while len(results) < limit:
        per_page = min(100, limit - len(results))
        payload = client.get(
            "/search/issues",
            {"q": f"is:pr is:open author:{username}", "per_page": per_page,
             "page": page, "sort": "updated", "order": "desc"},
        )
        issues = payload.get("items", [])
        if not isinstance(issues, list):
            raise GitHubAPIError("Unexpected search response from GitHub")
        if not issues:
            break

        for issue in issues:
            repo = _repo_from_issue(issue)
            number = int(issue["number"])
            root = f"/repos/{repo}"
            pull = client.get(f"{root}/pulls/{number}")
            sha = str(pull["head"]["sha"])
            checks_payload = client.get(
                f"{root}/commits/{sha}/check-runs",
                {"per_page": 100, "filter": "latest"},
            )
            commit_payload = client.get(f"{root}/commits/{sha}/status")
            reviews = list_reviews(client, f"{root}/pulls/{number}/reviews")
            requested = len(pull.get("requested_reviewers") or [])
            requested += len(pull.get("requested_teams") or [])

            results.append(
                TrackedPR(
                    repository=repo,
                    number=number,
                    title=str(issue["title"]),
                    url=str(issue["html_url"]),
                    updated_at=str(issue["updated_at"]),
                    head_sha=sha,
                    ci_status=summarize_ci(
                        checks_payload.get("check_runs", []),
                        commit_payload.get("statuses", []),
                    ),
                    review_status=summarize_reviews(reviews, requested),
                    reviewers_requested=requested,
                )
            )
            if len(results) >= limit:
                break
        if len(issues) < per_page:
            break
        page += 1
    return results
