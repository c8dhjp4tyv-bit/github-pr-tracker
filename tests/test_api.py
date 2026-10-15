"""Tests for request construction and error handling (no network calls)."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from github_pr_tracker.api import GitHubAPIError, GitHubClient


class GitHubClientTests(unittest.TestCase):
    @patch("github_pr_tracker.api.urlopen")
    def test_request_has_expected_headers_and_query(self, open_url):
        open_url.return_value = io.BytesIO(json.dumps({"ok": True}).encode())
        client = GitHubClient(token="not-a-real-token")
        self.assertEqual(client.get("/search/issues", {"q": "is:pr author:example"}), {"ok": True})
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.github.com/search/issues?q=is%3Apr+author%3Aexample")
        self.assertEqual(request.get_header("Authorization"), "Bearer not-a-real-token")
        self.assertEqual(request.get_method(), "GET")

    def test_rejects_absolute_urls(self):
        client = GitHubClient(token="secret")
        with self.assertRaises(ValueError):
            client.get("https://other.example/")
        with self.assertRaises(ValueError):
            client.get("//other.example/path")

    @patch("github_pr_tracker.api.urlopen")
    def test_rate_limit_error(self, open_url):
        open_url.side_effect = HTTPError(
            "https://api.github.com/user",
            403,
            "Forbidden",
            {"X-RateLimit-Remaining": "0"},
            io.BytesIO(b'{"message":"API rate limit exceeded"}'),
        )
        with self.assertRaisesRegex(GitHubAPIError, "rate limit exceeded"):
            GitHubClient(token="").get("/user")

    @patch("github_pr_tracker.api.urlopen")
    def test_network_error(self, open_url):
        open_url.side_effect = URLError("offline")
        with self.assertRaisesRegex(GitHubAPIError, "Unable to reach"):
            GitHubClient(token="").get("/user")

    @patch("github_pr_tracker.api.urlopen")
    def test_invalid_json(self, open_url):
        open_url.return_value = io.BytesIO(b"{")
        with self.assertRaisesRegex(GitHubAPIError, "invalid JSON"):
            GitHubClient(token="").get("/user")


if __name__ == "__main__":
    unittest.main()
