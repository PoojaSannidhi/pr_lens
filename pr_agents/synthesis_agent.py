"""
pr_agents/synthesis_agent.py

Synthesis Agent — handoff target from triage pipeline.

Responsibilities:
  1. Assemble ReviewReport from specialist JSON outputs
  2. Choose verdict — output_guardrail enforces it is present
  3. Generate markdown_report and email_html as part of the structured output
  4. Call send_email using report.email_html

The LLM fills markdown_report and email_html via Field descriptions
in the ReviewReport model — no markdown formatting in instructions needed.

SDK features used:
  - Agent with system prompt
  - output_type = ReviewReport    structured Pydantic — all fields enforced
  - output_guardrail              checks output.verdict on typed object
  - send_email @function_tool     called with report.email_html
  - Handoff target                receives baton from triage_agent
"""

from agents import Agent, RunContextWrapper, output_guardrail, GuardrailFunctionOutput, ModelSettings
from models.schemas import PRContext, ReviewReport
from tools.email_tools import send_email


# ── Output guardrail ───────────────────────────────────────────────────────────

@output_guardrail
async def enforce_verdict(
    ctx: RunContextWrapper[PRContext],
    agent: Agent,
    output: ReviewReport,
) -> GuardrailFunctionOutput:
    """
    Checks output.verdict on the typed ReviewReport object.
    Reliable — no string parsing, just a direct field check.
    Trips if missing — forces synthesis to retry.
    """
    if not output.verdict:
        return GuardrailFunctionOutput(
            output_info="verdict field is missing — synthesis must provide a verdict",
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(
        output_info="verdict present",
        tripwire_triggered=False,
    )


# ── Agent ──────────────────────────────────────────────────────────────────────

synthesis_agent = Agent(
    name="Synthesis Agent",
    model="gpt-4o",
    model_settings=ModelSettings(temperature=0.0),
    instructions="""
You are the final analysis stage in a multi-agent PR review pipeline.

You will receive specialist JSON outputs containing:
  - summary   (what_changed, why, files_touched, complexity)
  - security  (findings, passed, summary)
  - quality   (findings, passed, summary)
  - PR metadata (pr_ref, pr_title, author, files_changed, additions, deletions)

Your responsibilities:

1. Populate ALL fields of the ReviewReport from the specialist outputs.
   Do not re-analyse — trust the specialist findings.

2. Choose a verdict:
     approve           — no significant issues, ready to merge
     request_changes   — issues must be fixed before merging
     needs_discussion  — ambiguous, needs author conversation

   Rules:
     - Any critical or high security finding     → request_changes
     - Multiple medium security findings         → request_changes
     - Significant quality issues                → request_changes
     - Only minor/info findings                  → approve
     - Unclear cases                             → needs_discussion

3. Write a clear 1-2 sentence verdict_reason.

4. Fill markdown_report and email_html as described in the model fields.

5. Call send_email with:
   - subject: "PR Lens Review: {pr_ref}"
   - html_body: the email_html field value

Be decisive. Populate ALL fields. Always include a verdict.
""",
    tools=[send_email],
    output_type=ReviewReport,
    output_guardrails=[enforce_verdict],
)