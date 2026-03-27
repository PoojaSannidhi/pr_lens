"""
tools/email_tools.py

SendGrid email tool using the course pattern.
"""

import os
from typing import Dict
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from agents import function_tool


@function_tool
def send_email(subject: str, html_body: str) -> Dict[str, str]:
    """Send an email with the given subject and HTML body via SendGrid."""
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    from_email = Email(os.environ.get('SENDGRID_FROM_EMAIL'))
    to_email = To(os.environ.get('SENDGRID_TO_EMAIL'))
    content = Content("text/html", html_body)
    mail = Mail(from_email, to_email, subject, content).get()
    sg.client.mail.send.post(request_body=mail)
    return {"status": "success"}


