"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Sequence

from .api import GitHubAPIError, GitHubClient
from .tracker import get_open_prs, resolve_username


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="github-pr-tracker",
        description="Track your open GitHub pull requests and CI/review status.",
    )
    parser.add_argument("--user", help="GitHub username (or use GITHUB_TOKEN)")
    parser.add_argument(
        "--limit", type=int, default=10,
        help="Maximum open PRs to inspect, from 1 to 100 (default: 10)",
    )
    parser.add_argument("--json", action="store_true", help="Output structured JSON")
    parser.add_argument(
        "--fail-on-ci", action="store_true",
        help="Exit 2 when an inspected PR has failing CI",
    )
    args = parser.parse_args(argv)

    try:
        client = GitHubClient()
        username = resolve_username(client, args.user)
        pull_requests = get_open_prs(client, username, args.limit)
    except (GitHubAPIError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {"username": username, "count": len(pull_requests),
                 "pull_requests": [asdict(pr) for pr in pull_requests]},
                indent=2,
            )
        )
    else:
        print(f"Open pull requests by {username}: {len(pull_requests)}")
        for pr in pull_requests:
            print(
                f"\n[{pr.ci_status}] [{pr.review_status}] "
                f"{pr.repository}#{pr.number} — {pr.title}"
            )
            print(pr.url)
        if not pull_requests:
            print("No open pull requests found.")

    return 2 if args.fail_on_ci and any(pr.ci_status == "failing" for pr in pull_requests) else 0


if __name__ == "__main__":
    raise SystemExit(main())
