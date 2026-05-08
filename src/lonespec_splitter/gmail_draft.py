import base64
import logging
from typing import Optional
from email.mime.text import MIMEText

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GmailDrafter:
    def __init__(
        self,
        service_account_key_path: str,
        workspace_domain: str,
        gmail_service=None,
        directory_service=None,
    ):
        """
        Initialize Gmail drafter with Service Account credentials.

        Args:
            service_account_key_path: Path to service account JSON key file.
            workspace_domain: Workspace domain (e.g., "workspace.se").
            gmail_service: Optional mock/override for Gmail service (testing).
            directory_service: Optional mock/override for Directory service (testing).
        """
        self.workspace_domain = workspace_domain

        if gmail_service and directory_service:
            self.gmail_service = gmail_service
            self.directory_service = directory_service
        else:
            self.credentials = self._get_credentials(service_account_key_path)
            self.gmail_service = build("gmail", "v1", credentials=self.credentials)
            self.directory_service = build(
                "admin", "directory_v1", credentials=self.credentials
            )

    @staticmethod
    def _get_credentials(key_path: str) -> service_account.Credentials:
        scopes = [
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/admin.directory.user.readonly",
        ]
        return service_account.Credentials.from_service_account_file(
            key_path, scopes=scopes
        )

    def lookup_email(self, name: str) -> Optional[str]:
        """
        Look up employee email in Google Workspace Directory.

        Args:
            name: Employee name (e.g., "Anna Andersson").

        Returns:
            Email address if found, None otherwise.
        """
        try:
            query = f'fullName:"{name}"'
            results = (
                self.directory_service.users()
                .list(customer="my_customer", query=query, maxResults=10)
                .execute()
            )
            users = results.get("users", [])
            if users:
                return users[0]["primaryEmail"]
            logger.warning(f"Email not found for: {name}")
            return None
        except Exception as e:
            logger.error(f"Directory lookup failed for {name}: {e}")
            return None

    def render_template(
        self, name: str, pay_date: str, pay_period: str = None
    ) -> tuple[str, str]:
        """
        Render email subject and body.

        Args:
            name: Employee name.
            pay_date: Payment date (YYYY-MM-DD).
            pay_period: Payment period (e.g., "2026-04-01 — 2026-04-30").

        Returns:
            Tuple of (subject, body).
        """
        subject = f"Lönespecifikation {pay_date}"
        period_str = f" för period {pay_period}" if pay_period else ""
        body = f"""Hej {name},

Se bifogad lönespecifikation{period_str} (utbetald {pay_date}).

Med vänlig hälsning"""
        return subject, body

    def create_draft(
        self, to: str, subject: str, body: str
    ) -> Optional[str]:
        """
        Create a Gmail draft (not sent).

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body.

        Returns:
            Draft message ID if successful, None otherwise.
        """
        try:
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            result = (
                self.gmail_service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )
            draft_id = result.get("id")
            logger.info(f"Draft created for {to}: {draft_id}")
            return draft_id
        except Exception as e:
            logger.error(f"Failed to create draft for {to}: {e}")
            return None

    def create_draft_for_person(
        self, name: str, pay_date: str, pay_period: str = None
    ) -> Optional[str]:
        """
        Convenience method: look up email, render template, create draft.

        Args:
            name: Employee name.
            pay_date: Payment date (YYYY-MM-DD).
            pay_period: Payment period.

        Returns:
            Draft message ID if successful, None otherwise.
        """
        email = self.lookup_email(name)
        if not email:
            logger.warning(f"Skipping draft for {name} (email not found)")
            return None

        subject, body = self.render_template(name, pay_date, pay_period)
        return self.create_draft(email, subject, body)
