# GitHub PR Tracker

A small, dependency-free Python CLI for tracking your open GitHub pull requests, CI checks, and review decisions using the **GitHub REST API**.

## Features

- Finds open pull requests authored by a GitHub user, across repositories.
- Displays the latest CI check-run and commit-status results: **passing**, **failing**, **pending**, or **unknown**.
- Summarizes review state: **changes requested**, **approved**, **review requested**, or **none**.
- Offers human-readable output and machine-readable `--json`.
- Uses standard-library HTTP only; no third-party runtime dependencies.
- Supports fine-grained tokens via the `GITHUB_TOKEN` environment variable; never stores credentials.

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/c8dhjp4tyv-bit/github-pr-tracker.git
cd github-pr-tracker
python -m pip install -e .
github-pr-tracker --user c8dhjp4tyv-bit
```

To inspect more pull requests, or use JSON output:

```bash
github-pr-tracker --user c8dhjp4tyv-bit --limit 30
github-pr-tracker --user c8dhjp4tyv-bit --json
github-pr-tracker --user c8dhjp4tyv-bit --fail-on-ci
```

For higher GitHub API limits, or to resolve your user automatically, set a token:

```bash
export GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
github-pr-tracker
```

Do not commit tokens to this repository or share them in screenshots. A fine-grained token with read-only **Pull requests** and **Metadata** access is suitable for public repository data; reading commit checks or statuses may require additional read-only **Checks** / **Commit statuses** permissions for private repositories. Access to private repositories depends on the token's repository selection and permissions.

## Command-line options

| Option | Description |
| --- | --- |
| `--user USER` | GitHub username; optional if `GITHUB_TOKEN` is set |
| `--limit N` | Maximum number of open PRs to inspect (default 10, max 100) |
| `--json` | Emit structured JSON |
| `--fail-on-ci` | Exit with code 2 when any inspected PR has failing CI |
| `--help` | Show CLI help |

Exit codes: `0` success, `1` error, `2` failing CI when `--fail-on-ci` is enabled.

## How it works

This project integrates with the [GitHub REST API](https://docs.github.com/en/rest):

1. `GET /search/issues` searches for open PRs authored by a user.
2. `GET /repos/{owner}/{repo}/pulls/{number}` obtains the PR's current head commit and requested reviewers.
3. `GET /repos/{owner}/{repo}/commits/{sha}/check-runs` and `GET /repos/{owner}/{repo}/commits/{sha}/status` inspect checks and legacy statuses.
4. `GET /repos/{owner}/{repo}/pulls/{number}/reviews` summarizes submitted review decisions.

**Notes:** The tool reads only data available to your token. It does not modify repositories, request reviews, or automatically poll in the background. GitHub API rate limits apply; without a token the public API has a much lower limit. Check-runs and legacy statuses are read from the first 100 entries per endpoint, while reviews are paginated up to 1,000 entries; unusually large histories may be incomplete.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

GitHub Actions runs tests on Python 3.10 and 3.13 for pushes and pull requests.

## GitHub Developer Program

This is a real GitHub REST API integration that can be used as an example of an in-development application. Participation in the [GitHub Developer Program](https://github.com/developer) depends on GitHub's current eligibility criteria and registration flow. **Publishing this repository does not itself guarantee a Developer Program badge.**

## Support

Open an [issue](https://github.com/c8dhjp4tyv-bit/github-pr-tracker/issues) to report a bug or request a feature. For program registration, provide a valid email address you control if GitHub requests one.
