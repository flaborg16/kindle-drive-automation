from __future__ import annotations

import mimetypes
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from .config import Settings


def send_to_kindle(path: Path, settings: Settings) -> None:
    settings.validate_email_config()
    size = path.stat().st_size
    if size > settings.max_email_attachment_bytes:
        raise RuntimeError(
            f"{path.name} is {size / 1024 / 1024:.1f} MB, above configured email limit "
            f"of {settings.max_email_attachment_mb} MB"
        )

    msg = EmailMessage()
    msg["From"] = formataddr((settings.email_from_name, settings.smtp_username))
    msg["To"] = settings.kindle_email
    msg["Subject"] = f"Send to Kindle: {path.stem}"
    msg.set_content("Attached by Kindle Drive Automation.")

    ctype, encoding = mimetypes.guess_type(path.name)
    if ctype is None or encoding is not None:
        maintype, subtype = "application", "octet-stream"
    else:
        maintype, subtype = ctype.split("/", 1)
    msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=60) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_app_password)
        smtp.send_message(msg)
