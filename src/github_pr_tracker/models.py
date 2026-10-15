"""Serializable result types for pull request tracking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackedPR:
    repository: str
    number: int
    title: str
    url: str
    updated_at: str
    head_sha: str
    ci_status: str
    review_status: str
    reviewers_requested: int
