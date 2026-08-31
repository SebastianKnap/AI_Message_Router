"""Sends the routed message to the target department via SMTP.

Reply-To is set to the original sender's address so a human replying to the
department mailbox reaches the person who filed the request, not `router@`.
"""

from email.message import EmailMessage

import aiosmtplib

from app.config import get_settings
from app.domain.departments import Department, email_for


async def send_to_department(
    department: Department,
    subject: str,
    body: str,
    sender_email: str,
) -> None:
    settings = get_settings()

    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = email_for(department)
    message["Reply-To"] = sender_email
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
    )
