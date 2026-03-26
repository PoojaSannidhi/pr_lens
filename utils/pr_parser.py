"""
utils/pr_parser.py

Parses a GitHub PR URL (or short-form input) into its components.

Supported formats:
  - https://github.com/owner/repo/pull/123
  - http://github.com/owner/repo/pull/123
  - github.com/owner/repo/pull/123
  - owner/repo#123
"""

import re
from dataclasses import dataclass


@dataclass
class PRDetails:
    owner: str
    repo: str
    pr_number: int

    def __str__(self) -> str:
        return f"{self.owner}/{self.repo}#{self.pr_number}"


# Matches full GitHub URLs
_URL_PATTERN = re.compile(
    r"(?:https?://)?github\.com/([^/]+)/([^/]+)/pull/(\d+)"
)

# Matches short form: owner/repo#123
_SHORT_PATTERN = re.compile(
    r"^([^/]+)/([^#]+)#(\d+)$"
)


def parse_pr_input(raw) -> PRDetails:
    if not isinstance(raw, str):
        raise ValueError(...)
    raw = raw.strip()

    # Try full URL first
    match = _URL_PATTERN.search(raw)
    if match:
        owner, repo, pr_number = match.groups()
        return PRDetails(owner=owner, repo=repo, pr_number=int(pr_number))

    # Try short form owner/repo#123
    match = _SHORT_PATTERN.match(raw)
    if match:
        owner, repo, pr_number = match.groups()
        return PRDetails(owner=owner, repo=repo.strip(), pr_number=int(pr_number))

    raise ValueError(
        f"Could not parse PR from input: '{raw}'\n"
        "Expected formats:\n"
        "  https://github.com/owner/repo/pull/123\n"
        "  owner/repo#123"
    )


def is_valid_pr_input(raw: str) -> bool:
    """
    Returns True if the input looks like a valid GitHub PR reference.
    Used by the input guardrail before passing to agents.
    """
    try:
        parse_pr_input(raw)
        return True
    except ValueError:
        return False