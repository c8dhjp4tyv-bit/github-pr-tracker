"""Unit tests for PR status aggregation and API pagination."""

import unittest

from github_pr_tracker.api import GitHubAPIError
from github_pr_tracker.tracker import (
    get_open_prs,
    resolve_username,
    summarize_ci,
    summarize_reviews,
)


class FakeClient:
    token = "test-token"

    def __init__(self):
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        if path == "/user":
            return {"login": "example"}
        if path == "/search/issues":
            if params["page"] != 1:
                return {"items": []}
            return {
                "items": [
                    {
                        "number": 3,
                        "title": "Fix something",
                        "html_url": "https://github.com/acme/widget/pull/3",
                        "updated_at": "2026-10-15T12:00:00Z",
                        "repository_url": "https://api.github.com/repos/acme/widget",
                    }
                ]
            }
        if path == "/repos/acme/widget/pulls/3":
            return {
                "head": {"sha": "abc123"},
                "requested_reviewers": [{"login": "maintainer"}],
                "requested_teams": [],
            }
        if path == "/repos/acme/widget/commits/abc123/check-runs":
            return {
                "check_runs": [
                    {"status": "completed", "conclusion": "success"},
                    {"status": "completed", "conclusion": "failure"},
                ]
            }
        if path == "/repos/acme/widget/commits/abc123/status":
            return {"statuses": [{"state": "success"}]}
        if path == "/repos/acme/widget/pulls/3/reviews":
            return [{"user": {"login": "maintainer"}, "state": "CHANGES_REQUESTED"}]
        raise AssertionError(f"Unexpected path: {path}")


class TrackerTests(unittest.TestCase):
    def test_ci_prioritizes_failure_and_pending(self):
        self.assertEqual(summarize_ci([], []), "unknown")
        self.assertEqual(
            summarize_ci([{"status": "completed", "conclusion": "success"}], []),
            "passing",
        )
        self.assertEqual(summarize_ci([{"status": "in_progress"}], []), "pending")
        self.assertEqual(
            summarize_ci(
                [{"status": "in_progress"}],
                [{"state": "error"}],
            ),
            "failing",
        )
        self.assertEqual(
            summarize_ci([{"status": "completed", "conclusion": "skipped"}], []),
            "passing",
        )

    def test_review_last_decision_and_requested_fallback(self):
        reviews = [
            {"user": {"login": "alice"}, "state": "CHANGES_REQUESTED"},
            {"user": {"login": "alice"}, "state": "COMMENTED"},
            {"user": {"login": "alice"}, "state": "APPROVED"},
        ]
        self.assertEqual(summarize_reviews(reviews, 1), "approved")
        self.assertEqual(summarize_reviews([], 2), "requested")
        self.assertEqual(summarize_reviews([], 0), "none")
        self.assertEqual(
            summarize_reviews([{"user": {"login": "alice"}, "state": "DISMISSED"}], 0),
            "none",
        )

    def test_resolve_username(self):
        client = FakeClient()
        self.assertEqual(resolve_username(client, None), "example")
        self.assertEqual(resolve_username(client, "someone-1"), "someone-1")
        with self.assertRaises(ValueError):
            resolve_username(client, "not/valid")
        client.token = ""
        with self.assertRaisesRegex(ValueError, "GITHUB_TOKEN"):
            resolve_username(client, None)

    def test_get_open_prs_fetches_details(self):
        client = FakeClient()
        prs = get_open_prs(client, "example", limit=10)
        self.assertEqual(len(prs), 1)
        self.assertEqual(prs[0].repository, "acme/widget")
        self.assertEqual(prs[0].ci_status, "failing")
        self.assertEqual(prs[0].review_status, "changes_requested")
        self.assertEqual(prs[0].reviewers_requested, 1)
        paths = [path for path, _ in client.calls]
        self.assertIn("/repos/acme/widget/commits/abc123/check-runs", paths)
        self.assertIn("/repos/acme/widget/pulls/3/reviews", paths)

    def test_limit_validation(self):
        with self.assertRaisesRegex(ValueError, "--limit"):
            get_open_prs(FakeClient(), "example", limit=0)
        with self.assertRaisesRegex(ValueError, "--limit"):
            get_open_prs(FakeClient(), "example", limit=101)

    def test_rejects_untrusted_repository_url(self):
        class BadClient(FakeClient):
            def get(self, path, params=None):
                result = super().get(path, params)
                if path == "/search/issues":
                    result["items"][0]["repository_url"] = "https://evil.test/repos/acme/widget"
                return result
        with self.assertRaises(GitHubAPIError):
            get_open_prs(BadClient(), "example")


if __name__ == "__main__":
    unittest.main()
