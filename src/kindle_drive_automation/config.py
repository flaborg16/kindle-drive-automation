from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    google_service_account_json: str | None = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    google_service_account_file: str | None = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")

    kindle_root_folder_name: str = os.getenv("KINDLE_ROOT_FOLDER_NAME", "Kindle_Automation")
    books_folder_name: str = os.getenv("BOOKS_FOLDER_NAME", "Books_To_Kindle")
    notebooks_folder_name: str = os.getenv("NOTEBOOKS_FOLDER_NAME", "Notebooks")
    sent_folder_name: str = os.getenv("SENT_FOLDER_NAME", "Sent_To_Kindle")
    processed_notebooks_folder_name: str = os.getenv("PROCESSED_NOTEBOOKS_FOLDER_NAME", "Processed_Notebooks")
    failed_folder_name: str = os.getenv("FAILED_FOLDER_NAME", "Failed")
    quotations_folder_name: str = os.getenv("QUOTATIONS_FOLDER_NAME", "Quotations")

    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = _int("SMTP_PORT", 587)
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_app_password: str = os.getenv("SMTP_APP_PASSWORD", "")
    kindle_email: str = os.getenv("KINDLE_EMAIL", "")
    email_from_name: str = os.getenv("EMAIL_FROM_NAME", "Kindle Drive Automation")

    max_email_attachment_mb: int = _int("MAX_EMAIL_ATTACHMENT_MB", 24)
    quote_image_width: int = _int("QUOTE_IMAGE_WIDTH", 1236)
    quote_image_height: int = _int("QUOTE_IMAGE_HEIGHT", 1648)
    process_notes_as_quotes: bool = _bool("PROCESS_NOTES_AS_QUOTES", False)
    delete_local_workdir_after_run: bool = _bool("DELETE_LOCAL_WORKDIR_AFTER_RUN", True)

    @property
    def max_email_attachment_bytes(self) -> int:
        return self.max_email_attachment_mb * 1024 * 1024

    def validate_email_config(self) -> None:
        missing = []
        for key, value in {
            "SMTP_USERNAME": self.smtp_username,
            "SMTP_APP_PASSWORD": self.smtp_app_password,
            "KINDLE_EMAIL": self.kindle_email,
        }.items():
            if not value:
                missing.append(key)
        if missing:
            raise RuntimeError("Missing email config: " + ", ".join(missing))


settings = Settings()
