
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional, List
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_chat_summary_email(recipient_email: str, subject: str, body: str, pdf_content: Optional[bytes] = None, filename: str = "summary.pdf"):
    """
    Sends an email with an optional PDF attachment.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP settings not configured. Email not sent.")
        return False

    try:
        message = MIMEMultipart()
        message["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        message["To"] = recipient_email
        message["Subject"] = subject

        message.attach(MIMEText(body, "plain"))

        if pdf_content:
            part = MIMEApplication(pdf_content, Name=filename)
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            message.attach(part)

        # Connect and send
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
            
        logger.info(f"Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
