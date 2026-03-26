"""
app.py - PR Lens Gradio UI
"""

import gradio as gr
from dotenv import load_dotenv
from pr_agents.triage_agent import run_triage
from agents import InputGuardrailTripwireTriggered

load_dotenv()


async def run(pr_url: str):
    """
    Simple async generator
    Streams agent activity + final report into a single markdown output.
    """
    try:
        async for chunk in run_triage(pr_url):
            yield chunk
    except InputGuardrailTripwireTriggered:
        yield "❌ Invalid input. Please provide a valid GitHub PR URL.\n\nExample: `https://github.com/owner/repo/pull/123`"
    except Exception as e:
        yield f"❌ Error during analysis: `{str(e)}`"


with gr.Blocks(theme=gr.themes.Default(primary_hue="sky")) as ui:
    gr.Markdown(
        """
        # 🔍 PR Lens
        ### Multi-agent PR summarizer & code reviewer
        **Powered by OpenAI Agents SDK** 
        """
    )
    pr_url_textbox = gr.Textbox(
        label="GitHub PR URL",
        placeholder="https://github.com/fastapi/fastapi/pull/1234",
    )
    run_button = gr.Button("Analyze →", variant="primary")
    report = gr.Markdown(label="Review Report")

    run_button.click(fn=run, inputs=pr_url_textbox, outputs=report)
    pr_url_textbox.submit(fn=run, inputs=pr_url_textbox, outputs=report)

ui.launch(inbrowser=True)