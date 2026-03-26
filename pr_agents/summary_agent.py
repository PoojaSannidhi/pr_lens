"""
agents/summary_agent.py

Specialist agent — summarizes what changed in a PR and why.

SDK features used:
  - Agent with system prompt
  - output_type = SummaryOutput  (structured Pydantic output)
  - tools: get_pr_diff, get_commit_messages, get_changed_files  (@function_tool)

Called by triage_agent via summary_agent.as_tool()
"""

from agents import Agent
from models.schemas import SummaryOutput
from tools.github_tools import get_pr_diff, get_commit_messages, get_changed_files


summary_agent = Agent(
    name="Summary Agent",
    model="gpt-4o",
    instructions="""
You are a senior software engineer specializing in code review.
Your job is to produce a concise, accurate summary of a GitHub pull request.

You will be given the PR owner, repo, and PR number. Use your tools to fetch:
  1. The list of changed files (get_changed_files)
  2. The commit messages (get_commit_messages)
  3. The raw diff (get_pr_diff)

From this information, determine:
  - what_changed: A plain-english description of the code changes (2-4 sentences).
    Focus on *what* was changed functionally, not just file names.
  - why: The inferred motivation — from commit messages, PR description, or code patterns.
    If unclear, say so honestly.
  - files_touched: The most important files that were changed (not every file, just key ones).
  - complexity: Classify the PR size as one of:
      trivial   — typo fixes, comment changes, minor formatting
      small     — single focused change, < 50 lines
      medium    — a few related changes, 50–200 lines
      large     — significant feature or refactor, 200–500 lines
      very large — major change, 500+ lines or many files

Be factual and precise. Do not invent behavior that isn't visible in the diff.
Return your findings as a structured SummaryOutput.
""",
    tools=[get_changed_files, get_commit_messages, get_pr_diff],
    output_type=SummaryOutput,
)