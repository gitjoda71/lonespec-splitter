"""Gmail-drafting: skapa utkast i Gmail med bifogad PDF för varje lönespec-mottagare.

Designprinciper:
- Service Account + Domain-Wide Delegation impersonerar användarens egen Gmail
  (delegated_user) så att utkastet hamnar i *din* utkast-mapp — inte i SA:s mailbox.
- PDF:en för respektive person bifogas som application/pdf.
- Mailet skickas EJ — det skapas som DRAFT så användaren kan granska och trycka skicka.
- Email-lookup försöker både 'Förnamn Efternamn' och 'Efternamn, Förnamn' (Kontek).
"""
from __future__ import annotations

import base64
import logging
import mimetypes
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
]


class GmailDrafter:
    def __init__(
        self,
        service_account_key_path: str,
        workspace_domain: str,
        delegated_user: str | None = None,
        gmail_service=None,
        directory_service=None,
    ):
        """
        Initialize Gmail drafter with Service Account + Domain-Wide Delegation.

        Args:
            service_account_key_path: Path to service account JSON key file.
            workspace_domain: Workspace domain (e.g., "workspace.se").
            delegated_user: Email address of the Workspace user to impersonate.
                           Drafts will be created in this user's Gmail mailbox.
                           If None, defaults to using the SA's own context (rarely useful).
            gmail_service: Optional mock/override for Gmail service (testing).
            directory_service: Optional mock/override for Directory service (testing).
        """
        self.workspace_domain = workspace_domain
        self.delegated_user = delegated_user

        if gmail_service is not None and directory_service is not None:
            self.gmail_service = gmail_service
            self.directory_service = directory_service
        else:
            self.credentials = self._get_credentials(
                service_account_key_path, delegated_user
            )
            self.gmail_service = build("gmail", "v1", credentials=self.credentials)
            self.directory_service = build(
                "admin", "directory_v1", credentials=self.credentials
            )

    @staticmethod
    def _get_credentials(
        key_path: str, delegated_user: str | None
    ) -> service_account.Credentials:
        creds = service_account.Credentials.from_service_account_file(
            key_path, scopes=SCOPES
        )
        if delegated_user:
            # Domain-Wide Delegation: SA agerar som denna användare.
            creds = creds.with_subject(delegated_user)
        return creds

    # ------------------------------------------------------------------
    # Directory: namn → email
    # ------------------------------------------------------------------

    def _query_directory(self, query: str) -> str | None:
        """Kör en enskild Directory API-query och returnera första träffen."""
        try:
            results = (
                self.directory_service.users()
                .list(customer="my_customer", query=query, maxResults=10)
                .execute()
            )
            users = results.get("users", []) or []
            if users:
                return users[0].get("primaryEmail")
            return None
        except Exception as e:
            logger.error(f"Directory query failed ({query!r}): {e}")
            return None

    def lookup_email(
        self, name: str | None = None, *, first: str | None = None, last: str | None = None
    ) -> Optional[str]:
        """
        Slå upp email i Google Workspace Directory.

        Försöksordning (första träff vinner):
          1. fullName:"Förnamn Efternamn"  (om vi har båda eller name="Förnamn Efternamn")
          2. fullName:"Efternamn, Förnamn" (Kontek-stil)
          3. givenName:"Förnamn" familyName:"Efternamn"  (mer toleranta fält)
          4. fullName:"<name>" som user gav
        """
        # Härled first/last om bara `name` är angivet
        if (not first or not last) and name:
            parts = name.strip().split()
            if len(parts) >= 2:
                first = first or parts[0]
                last = last or parts[-1]

        candidates: list[str] = []
        if first and last:
            candidates.append(f'fullName:"{first} {last}"')
            candidates.append(f'fullName:"{last}, {first}"')
            candidates.append(f'givenName:"{first}" familyName:"{last}"')
        if name:
            candidates.append(f'fullName:"{name}"')

        # Avduplicera bevarat ordningen
        seen: set[str] = set()
        ordered: list[str] = []
        for q in candidates:
            if q not in seen:
                seen.add(q)
                ordered.append(q)

        for q in ordered:
            email = self._query_directory(q)
            if email:
                logger.debug(f"Email-lookup OK via {q!r} → {email}")
                return email

        logger.warning(
            f"Email not found for name={name!r} first={first!r} last={last!r}"
        )
        return None

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def render_template(
        self,
        name: str,
        pay_date: str,
        pay_period: str | None = None,
    ) -> tuple[str, str]:
        """Render email subject and body."""
        subject = f"Lönespecifikation {pay_date}"
        period_str = f" för period {pay_period}" if pay_period else ""
        body = (
            f"Hej {name},\n\n"
            f"Se bifogad lönespecifikation{period_str}. "
            f"Utbetalning sker {pay_date}.\n\n"
            f"Med vänlig hälsning"
        )
        return subject, body

    # ------------------------------------------------------------------
    # Draft creation
    # ------------------------------------------------------------------

    def _build_message(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: list[Path] | None = None,
    ) -> MIMEMultipart | MIMEText:
        """Bygg MIME-meddelande med eller utan bilagor."""
        if not attachments:
            msg = MIMEText(body, "plain", "utf-8")
            msg["to"] = to
            msg["subject"] = subject
            return msg

        msg = MIMEMultipart()
        msg["to"] = to
        msg["subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        for path in attachments:
            path = Path(path)
            ctype, _ = mimetypes.guess_type(path.name)
            if ctype is None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            with open(path, "rb") as f:
                data = f.read()
            if maintype == "application":
                part = MIMEApplication(data, _subtype=subtype)
            else:
                # Vi förväntar oss PDF (application/pdf), men var tolerant
                part = MIMEApplication(data, _subtype="octet-stream")
            part.add_header(
                "Content-Disposition", "attachment", filename=path.name
            )
            msg.attach(part)
        return msg

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: list[Path] | None = None,
    ) -> Optional[str]:
        """Skapa ett Gmail-utkast (skickas EJ). Returnerar draft-ID eller None."""
        try:
            message = self._build_message(to, subject, body, attachments)
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            # userId='me' refererar till impersonerad användare när
            # Domain-Wide Delegation är konfigurerad.
            result = (
                self.gmail_service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )
            draft_id = result.get("id")
            logger.info(f"Draft skapat för {to}: {draft_id}")
            return draft_id
        except Exception as e:
            logger.error(f"Misslyckades skapa draft för {to}: {e}")
            return None

    def create_draft_for_person(
        self,
        name: str,
        pay_date: str,
        pay_period: str | None = None,
        first: str | None = None,
        last: str | None = None,
        pdf_path: Path | None = None,
    ) -> Optional[str]:
        """
        Bekväm helper: slå upp email → render template → skapa draft med bilaga.

        Args:
            name:       Helt namn ("Förnamn Efternamn") — används för template.
            pay_date:   Utbetalningsdatum YYYY-MM-DD.
            pay_period: Valfri lönperiod ("YYYY-MM-DD — YYYY-MM-DD").
            first/last: Valfria explicita delar för bättre Directory-lookup.
            pdf_path:   Sökväg till persons lönespec-PDF — bifogas till utkastet.
        """
        email = self.lookup_email(name=name, first=first, last=last)
        if not email:
            logger.warning(f"Hoppar över draft för {name} (email saknas)")
            return None

        subject, body = self.render_template(name, pay_date, pay_period)
        attachments = [pdf_path] if pdf_path else None
        return self.create_draft(email, subject, body, attachments=attachments)
