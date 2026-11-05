"""Small SMTP adapter used for transactional authentication email."""

import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import Settings


class EmailDeliveryError(RuntimeError):
    """Raised when configured SMTP cannot deliver a message."""


def send_otp_email(settings: Settings, recipient: str, code: str) -> None:
    if not settings.smtp_host or not settings.smtp_from:
        raise EmailDeliveryError("SMTP is not configured. Set SMTP_HOST and SMTP_FROM in .env.")

    message = EmailMessage()
    message["Subject"] = "Your DocuMind verification code"
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message.set_content(
        f"Your DocuMind verification code is {code}. It expires in 10 minutes.\n\n"
        "If you did not request this code, you can safely ignore this email."
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
            client.ehlo()
            if settings.smtp_starttls:
                client.starttls(context=context)
                client.ehlo()
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("SMTP could not deliver the verification email.") from exc
