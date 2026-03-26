"""
pr_agents/triage_agent.py

Triage Agent — single agent, single run, all SDK features genuine.

Flow inside ONE Runner.run_streamed call:
  1. input_guardrail        validates PR URL before any LLM token consumed
  2. get_pr_metadata        @function_tool — LLM fetches PR metadata
  3. run_all_specialists    @function_tool — asyncio.gather fires inside
  4. handoff(synthesis)     LLM hands off with specialist results

synthesis_agent then:
  - assembles ReviewReport (Pydantic)
  - output_guardrail enforces verdict
  - calls send_email(@function_tool)
  - returns ReviewReport as final_output

run_triage converts ReviewReport → markdown and yields to Gradio.
"""

import asyncio
import json
from agents import (
    Agent,
    Runner,
    RunContextWrapper,
    input_guardrail,
    GuardrailFunctionOutput,
    function_tool,
    handoff,
)
from models.schemas import PRContext, SummaryOutput, SecurityOutput, QualityOutput
from pr_agents.summary_agent import summary_agent
from pr_agents.security_agent import security_agent
from pr_agents.quality_agent import quality_agent
from pr_agents.synthesis_agent import synthesis_agent
from tools.github_tools import get_pr_metadata
from utils.pr_parser import is_valid_pr_input, parse_pr_input



# ── Input guardrail ────────────────────────────────────────────────────────────

@input_guardrail
async def validate_pr_input(
    ctx: RunContextWrapper[PRContext],
    agent: Agent,
    input,
) -> GuardrailFunctionOutput:
    """
    Fires before any LLM call. Rejects if input is not a valid GitHub PR URL.
    Zero tokens wasted on bad input.
    The SDK passes input as a list of message dicts — extract the string content.
    """
    # SDK passes messages list — extract text content
    if isinstance(input, list):
        input = input[-1].get("content", "") if input else ""
    elif isinstance(input, dict):
        input = input.get("content", "")
    input = str(input).strip()
    if not is_valid_pr_input(input):
        return GuardrailFunctionOutput(
            output_info=(
                "Input is not a valid GitHub PR URL or reference. "
                "Expected: https://github.com/owner/repo/pull/123 or owner/repo#123"
            ),
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(
        output_info="Valid PR input",
        tripwire_triggered=False,
    )


# ── @function_tool — wraps asyncio.gather ─────────────────────────────────────

@function_tool
async def run_all_specialists(
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    pr_title: str,
    author: str,
    base_branch: str,
    changed_files: int,
    additions: int,
    deletions: int,
) -> str:
    """
    Runs summary, security, and quality agents IN PARALLEL using asyncio.gather.
    Called by triage LLM after get_pr_metadata returns all required fields.
    Returns combined specialist results as JSON string.
    """
    pr_prompt = (
        f"Review this PR: {owner}/{repo}#{pr_number}\n"
        f"Title: {pr_title}\n"
        f"Author: {author}\n"
        f"Base branch: {base_branch}\n"
        f"Head SHA: {head_sha}\n"
        f"Changed files: {changed_files}\n"
        f"Additions: {additions}, Deletions: {deletions}\n"
        f"Owner: {owner}, Repo: {repo}, PR number: {pr_number}"
    )

    context = PRContext(owner=owner, repo=repo, pr_number=pr_number)

    # All three fire simultaneously — Python controls concurrency
    async def run_summary() -> SummaryOutput:
        result = await Runner.run(summary_agent, input=pr_prompt, context=context)
        return result.final_output

    async def run_security() -> SecurityOutput:
        result = await Runner.run(security_agent, input=pr_prompt, context=context)
        return result.final_output

    async def run_quality() -> QualityOutput:
        result = await Runner.run(quality_agent, input=pr_prompt, context=context)
        return result.final_output

    summary_out, security_out, quality_out = await asyncio.gather(
        run_summary(),
        run_security(),
        run_quality(),
    )

    return json.dumps({
        "summary":  json.loads(summary_out.model_dump_json()),
        "security": json.loads(security_out.model_dump_json()),
        "quality":  json.loads(quality_out.model_dump_json()),
    }, indent=2)


# ── Triage agent ───────────────────────────────────────────────────────────────

triage_agent = Agent(
    name="Triage Agent",
    model="gpt-4o",
    instructions="""
You are the triage orchestrator in a multi-agent PR review pipeline.

When you receive a PR URL, follow these steps IN ORDER:

1. Call get_pr_metadata with owner, repo, pr_number parsed from the URL.
   This returns head_sha, title, author, base_branch, changed_files,
   additions, deletions — all required for the next step.

2. Call run_all_specialists passing ALL metadata fields from step 1.
   This runs summary, security, and quality agents in parallel
   and returns their combined results as JSON.

3. Hand off to the synthesis agent passing the full results JSON
   so synthesis can assemble the final ReviewReport and verdict.

Do not analyse results yourself. Your job is orchestration only.
Always complete all three steps in order.
""",
    tools=[get_pr_metadata, run_all_specialists],
    handoffs=[handoff(synthesis_agent)],
    input_guardrails=[validate_pr_input],
)


# ── Public run function ────────────────────────────────────────────────────────

async def run_triage(user_input: str):
    """
    Single entry point called by app.py.

    ONE Runner.run_streamed call — everything happens inside:
      - input_guardrail validates
      - LLM calls get_pr_metadata (@function_tool)
      - LLM calls run_all_specialists (@function_tool + asyncio.gather)
      - LLM hands off to synthesis_agent
      - synthesis assembles ReviewReport, output_guardrail enforces verdict
      - synthesis calls send_email(@function_tool)

    result.final_output is ReviewReport (Pydantic) from synthesis.
    Converted to markdown here and yielded to Gradio.
    """
    pr_details = parse_pr_input(user_input)
    context = PRContext(
        owner=pr_details.owner,
        repo=pr_details.repo,
        pr_number=pr_details.pr_number,
    )

    yield f"🔍 PR detected: `{context.pr_ref}`"
    yield "🛡️  Firing input guardrail..."

    result = Runner.run_streamed(
        triage_agent,
        input=user_input,
        context=context,
    )

    async for event in result.stream_events():

        if event.type == "agent_updated_stream_event":
            agent_name = event.new_agent.name
            yield f"🔀 Handoff fired → **{agent_name}** now running"

        elif event.type == "run_item_stream_event":
            item = event.item

            if item.type == "tool_call_item":
                tool_name = getattr(item.raw_item, "name", None) or getattr(item, "title", "unknown")
                if tool_name == "get_pr_metadata":
                    yield "📡 Fetching PR metadata from GitHub..."
                elif tool_name == "run_all_specialists":
                    yield "⚡ Launching specialists in parallel via asyncio.gather..."
                elif tool_name == "send_email":
                    yield "📧 Synthesis sending review email..."
                else:
                    yield f"🔧 Tool call: `{tool_name}`"

            elif item.type == "tool_call_output_item":
                tool_name = getattr(item.raw_item, "name", "") if hasattr(item, "raw_item") else ""
                if tool_name == "get_pr_metadata":
                    yield "✅ Metadata fetched"
                elif tool_name == "run_all_specialists":
                    yield "✅ All specialists complete"
                elif tool_name == "send_email":
                    yield "✅ Email sent!"

    # synthesis_agent returns ReviewReport (Pydantic)
    # markdown_report field generated by LLM as part of structured output
    report = result.final_output
    if report:
        yield "🏁 Review complete.\n\n---\n\n" + report.markdown_report
    else:
        yield "❌ No report generated."