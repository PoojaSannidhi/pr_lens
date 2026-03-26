"""
tools/github_tools.py

GitHub REST API calls exposed as @function_tool so agents can call them directly.
All functions are async and accept owner/repo/pr_number explicitly so they work
cleanly when called by agents that receive PRContext via RunContextWrapper.

Tools defined here:
  - get_pr_metadata       → title, author, description, file/line counts
  - get_pr_diff           → raw unified diff
  - get_changed_files     → list of changed files with patch snippets
  - get_commit_messages   → all commit messages on the PR
  - read_file_content     → raw content of a specific file at head SHA
"""

import requests
from agents import function_tool


def _github_headers() -> dict:
    # Public repos only — no auth needed
    # Rate limit: 60 requests/hour unauthenticated (fine for a POC)
    return {"Accept": "application/vnd.github+json"}


def _get(url: str, accept: str | None = None) -> dict | str:
    headers = _github_headers()
    if accept:
        headers["Accept"] = accept
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    if headers.get("Accept", "").endswith("json"):
        return response.json()
    return response.text


# ── Tools ──────────────────────────────────────────────────────────────────────

@function_tool
def get_pr_metadata(owner: str, repo: str, pr_number: int) -> dict:
    """
    Fetch metadata for a GitHub pull request.
    Returns title, author, body, base branch, head branch,
    number of changed files, additions, and deletions.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    data = _get(url, accept="application/vnd.github+json")
    return {
        "title":         data.get("title", ""),
        "author":        data.get("user", {}).get("login", "unknown"),
        "body":          data.get("body") or "",
        "base_branch":   data.get("base", {}).get("ref", ""),
        "head_branch":   data.get("head", {}).get("ref", ""),
        "head_sha":      data.get("head", {}).get("sha", ""),
        "state":         data.get("state", ""),
        "changed_files": data.get("changed_files", 0),
        "additions":     data.get("additions", 0),
        "deletions":     data.get("deletions", 0),
        "created_at":    data.get("created_at", ""),
        "updated_at":    data.get("updated_at", ""),
    }


@function_tool
def get_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """
    Fetch the raw unified diff for a pull request.
    Returns a string containing the full diff across all changed files.
    Truncated to 12 000 characters to stay within context limits.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    diff = _get(url, accept="application/vnd.github.v3.diff")
    if isinstance(diff, str):
        return diff[:12_000]
    return str(diff)[:12_000]


@function_tool
def get_changed_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    """
    Fetch the list of files changed in a pull request.
    Each entry contains filename, status (added/modified/removed),
    additions, deletions, and the patch snippet if available.
    Returns up to 30 files.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    data = _get(url, accept="application/vnd.github+json")
    if not isinstance(data, list):
        return []
    return [
        {
            "filename":  f.get("filename", ""),
            "status":    f.get("status", ""),
            "additions": f.get("additions", 0),
            "deletions": f.get("deletions", 0),
            "patch":     (f.get("patch") or "")[:2_000],  # cap per-file patch
        }
        for f in data[:30]
    ]


@function_tool
def get_commit_messages(owner: str, repo: str, pr_number: int) -> list[str]:
    """
    Fetch all commit messages on a pull request.
    Returns a list of commit message strings (subject + body).
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/commits"
    data = _get(url, accept="application/vnd.github+json")
    if not isinstance(data, list):
        return []
    return [
        c.get("commit", {}).get("message", "").strip()
        for c in data
        if c.get("commit", {}).get("message")
    ]


@function_tool
def read_file_content(owner: str, repo: str, file_path: str, ref: str) -> str:
    """
    Fetch the raw content of a specific file at a given git ref (branch or SHA).
    Use the head_sha from get_pr_metadata as the ref to read the post-PR state.
    Returns raw file content as a string, truncated to 8 000 characters.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={ref}"
    data = _get(url, accept="application/vnd.github+json")
    if isinstance(data, dict) and data.get("encoding") == "base64":
        import base64
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return content[:8_000]
    return ""