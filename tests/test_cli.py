"""CLI tests that run without a GitHub token or network access."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from github_pr_tracker.cli import main
from github_pr_tracker.models import TrackedPR


FAKE_PR = TrackedPR(
    repository="acme/widget",
    number=3,
    title="Fix something",
    url="https://github.com/acme/widget/pull/3",
    updated_at="2026-10-15T12:00:00Z",
    head_sha="abc123",
    ci_status="failing",
    review_status="requested",
    reviewers_requested=1,
)


class CLITests(unittest.TestCase):
    @patch("github_pr_tracker.cli.get_open_prs", return_value=[FAKE_PR])
    @patch("github_pr_tracker.cli.resolve_username", return_value="example")
    @patch("github_pr_tracker.cli.GitHubClient")
    def test_json_output(self, client, username, get_prs):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["--user", "example", "--json"])
        self.assertEqual(result, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["pull_requests"][0]["ci_status"], "failing")

    @patch("github_pr_tracker.cli.get_open_prs", return_value=[FAKE_PR])
    @patch("github_pr_tracker.cli.resolve_username", return_value="example")
    @patch("github_pr_tracker.cli.GitHubClient")
    def test_failing_ci_exit_code(self, client, username, get_prs):
        with contextlib.redirect_stdout(io.StringIO()):
            result = main(["--user", "example", "--fail-on-ci"])
        self.assertEqual(result, 2)

    @patch("github_pr_tracker.cli.resolve_username", side_effect=ValueError("missing username"))
    @patch("github_pr_tracker.cli.GitHubClient")
    def test_error_exit_code(self, client, username):
        with contextlib.redirect_stderr(io.StringIO()):
            result = main([])
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
