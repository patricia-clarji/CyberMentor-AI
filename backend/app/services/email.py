import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.core.config import Settings


class EmailProvider(Protocol):
    def send(self, recipient: str, subject: str, text: str) -> None: ...


class MailpitEmailProvider:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    def send(self, recipient: str, subject: str, text: str) -> None:
        message = EmailMessage()
        message["From"] = "CyberMentor Local <noreply@cybermentor.local>"
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(text)
        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            smtp.send_message(message)


class ConsoleEmailProvider:
    def send(self, recipient: str, subject: str, text: str) -> None:
        print(
            {
                "level": "warning",
                "event": "development_email",
                "recipient": recipient,
                "subject": subject,
                "body": text,
            }
        )


class UnconfiguredProductionEmailProvider:
    def send(self, recipient: str, subject: str, text: str) -> None:
        raise RuntimeError("Production email provider is not configured.")


def get_email_provider(settings: Settings) -> EmailProvider:
    if settings.email_backend == "mailpit":
        return MailpitEmailProvider(settings.mailpit_host, settings.mailpit_port)
    if settings.email_backend == "console":
        return ConsoleEmailProvider()
    return UnconfiguredProductionEmailProvider()
