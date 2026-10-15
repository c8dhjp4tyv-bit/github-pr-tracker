"""Minimal GitHub REST API client; no third-party runtime dependencies."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class GitHubAPIError(Exception):
    """A GitHub API or network error suitable for displaying to a user."""


class GitHubClient:
    """Read-only client: fixed HTTPS API host, optional GITHUB_TOKEN."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None, timeout: float = 20.0) -> None:
        self.token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
        self.timeout = timeout

    def get(self, path: str, params: dict[str, object] | None = None) -> Any:
        """GET JSON from a relative GitHub REST API path."""
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("GitHub API path must begin with a single '/'")
        url = self.BASE_URL + path
        if params:
            url += "?" + urlencode(params)

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-pr-tracker/0.1.0",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token

        try:
            with urlopen(Request(url, headers=headers, method="GET"), timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            message = exc.reason
            try:
                payload = json.loads(exc.read().decode("utf-8"))
                message = payload.get("message", message)
            except (ValueError, UnicodeError):
                pass
            if exc.code in (403, 429) and exc.headers.get("X-RateLimit-Remaining") == "0":
                message = "GitHub API rate limit exceeded; set GITHUB_TOKEN or retry later"
            raise GitHubAPIError(f"GitHub API returned HTTP {exc.code}: {message}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise GitHubAPIError(f"Unable to reach GitHub API: {exc}") from exc
        except (UnicodeError, ValueError) as exc:
            raise GitHubAPIError("GitHub API returned invalid JSON") from exc
