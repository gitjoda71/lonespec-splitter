"""Tester för Gmail-drafting (mockade services)."""
from __future__ import annotations

import base64
from email import message_from_bytes
from email.header import decode_header, make_header
from pathlib import Path
from unittest.mock import MagicMock


def _decoded_header(msg, key: str) -> str:
    """Decode RFC 2047-encoded headers (Lönespecifikation → utf-8)."""
    raw = msg[key]
    if raw is None:
        return ""
    return str(make_header(decode_header(raw)))

from lonespec_splitter.gmail_draft import GmailDrafter


def _make_drafter(gmail=None, directory=None) -> GmailDrafter:
    return GmailDrafter(
        service_account_key_path="fake.json",
        workspace_domain="workspace.se",
        delegated_user="joel@workspace.se",
        gmail_service=gmail or MagicMock(),
        directory_service=directory or MagicMock(),
    )


# ---------------- Templates ----------------

def test_render_template():
    drafter = _make_drafter()
    subject, body = drafter.render_template(
        name="Anna Andersson",
        pay_date="2026-04-25",
        pay_period="2026-04-01 — 2026-04-30",
    )
    assert subject == "Lönespecifikation 2026-04-25"
    assert "Anna Andersson" in body
    assert "2026-04-01 — 2026-04-30" in body
    assert "2026-04-25" in body


def test_render_template_no_period():
    drafter = _make_drafter()
    subject, body = drafter.render_template(
        name="Bo Bengtsson", pay_date="2026-05-01", pay_period=None
    )
    assert subject == "Lönespecifikation 2026-05-01"
    assert "Bo Bengtsson" in body
    assert "för period" not in body


# ---------------- Email lookup ----------------

def test_lookup_email_found_full_name():
    mock_dir = MagicMock()
    mock_dir.users().list().execute.return_value = {
        "users": [{"primaryEmail": "anna@workspace.se"}]
    }
    drafter = _make_drafter(directory=mock_dir)
    assert drafter.lookup_email("Anna Andersson") == "anna@workspace.se"


def test_lookup_email_not_found():
    mock_dir = MagicMock()
    mock_dir.users().list().execute.return_value = {"users": []}
    drafter = _make_drafter(directory=mock_dir)
    assert drafter.lookup_email("Helt Okänd") is None


def test_lookup_email_api_error():
    mock_dir = MagicMock()
    mock_dir.users().list().execute.side_effect = Exception("API Error")
    drafter = _make_drafter(directory=mock_dir)
    assert drafter.lookup_email("Anna Andersson") is None


def test_lookup_email_kontek_falls_back_to_komma_format():
    """Kontek lagrar 'Efternamn, Förnamn' — vi måste hitta på andra försöket."""
    mock_dir = MagicMock()

    call_log: list[str] = []

    def fake_list(customer, query, maxResults):
        call_log.append(query)
        # Första försöket ('fullName:"Joel Danielsson"') → tomt.
        # Andra försöket ('fullName:"Danielsson, Joel"') → match.
        execute_mock = MagicMock()
        if "Danielsson, Joel" in query:
            execute_mock.execute.return_value = {
                "users": [{"primaryEmail": "joel@workspace.se"}]
            }
        else:
            execute_mock.execute.return_value = {"users": []}
        return execute_mock

    mock_dir.users().list = fake_list
    drafter = _make_drafter(directory=mock_dir)

    email = drafter.lookup_email(first="Joel", last="Danielsson")
    assert email == "joel@workspace.se"
    # Verifiera att vi försökte 'Joel Danielsson' först
    assert any("Joel Danielsson" in q for q in call_log)
    assert any("Danielsson, Joel" in q for q in call_log)


def test_lookup_email_double_lastname():
    """Dubbla efternamn ska skickas in oförändrat."""
    mock_dir = MagicMock()
    captured_queries: list[str] = []

    def fake_list(customer, query, maxResults):
        captured_queries.append(query)
        execute_mock = MagicMock()
        if "Danielsson Svensson" in query:
            execute_mock.execute.return_value = {
                "users": [{"primaryEmail": "joel.ds@workspace.se"}]
            }
        else:
            execute_mock.execute.return_value = {"users": []}
        return execute_mock

    mock_dir.users().list = fake_list
    drafter = _make_drafter(directory=mock_dir)

    email = drafter.lookup_email(first="Joel", last="Danielsson Svensson")
    assert email == "joel.ds@workspace.se"


# ---------------- Draft creation ----------------

def test_create_draft_no_attachment():
    mock_gmail = MagicMock()
    mock_gmail.users().drafts().create().execute.return_value = {"id": "draft_123"}
    drafter = _make_drafter(gmail=mock_gmail)
    draft_id = drafter.create_draft(
        to="anna@workspace.se", subject="Test", body="Body"
    )
    assert draft_id == "draft_123"


def test_create_draft_with_pdf_attachment(tmp_path: Path):
    """Verifiera att PDF:en inkluderas som application/pdf-attachment."""
    pdf = tmp_path / "Anna Andersson 2026-04-25.pdf"
    # Minimal PDF
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")

    captured = {}

    mock_gmail = MagicMock()

    def fake_create(userId, body):
        captured["raw"] = body["message"]["raw"]
        execute_mock = MagicMock()
        execute_mock.execute.return_value = {"id": "draft_with_pdf"}
        return execute_mock

    mock_gmail.users().drafts().create = fake_create

    drafter = _make_drafter(gmail=mock_gmail)
    draft_id = drafter.create_draft(
        to="anna@workspace.se",
        subject="Lönespecifikation 2026-04-25",
        body="Hej Anna,\n\nSe bifogad lönespecifikation.",
        attachments=[pdf],
    )
    assert draft_id == "draft_with_pdf"

    # Decode raw → MIME → kolla att PDF:en är där
    raw_bytes = base64.urlsafe_b64decode(captured["raw"].encode())
    msg = message_from_bytes(raw_bytes)
    assert msg.is_multipart(), "Mail med bilaga ska vara multipart"

    parts = list(msg.walk())
    pdf_parts = [
        p for p in parts if p.get_content_type() == "application/pdf"
    ]
    assert len(pdf_parts) == 1, "Förväntade exakt 1 PDF-bilaga"
    assert pdf_parts[0].get_filename() == "Anna Andersson 2026-04-25.pdf"


def test_create_draft_failure():
    mock_gmail = MagicMock()
    mock_gmail.users().drafts().create().execute.side_effect = Exception("Gmail Error")
    drafter = _make_drafter(gmail=mock_gmail)
    assert (
        drafter.create_draft(to="x@y.se", subject="s", body="b") is None
    )


def test_create_draft_for_person_includes_pdf(tmp_path: Path):
    """End-to-end (mockad): lookup → render → attach PDF → draft."""
    pdf = tmp_path / "Joel Danielsson 2026-05-25.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")

    mock_gmail = MagicMock()
    captured = {}

    def fake_create(userId, body):
        captured["raw"] = body["message"]["raw"]
        execute_mock = MagicMock()
        execute_mock.execute.return_value = {"id": "draft_e2e"}
        return execute_mock

    mock_gmail.users().drafts().create = fake_create

    mock_dir = MagicMock()
    mock_dir.users().list().execute.return_value = {
        "users": [{"primaryEmail": "joel@workspace.se"}]
    }

    drafter = _make_drafter(gmail=mock_gmail, directory=mock_dir)
    draft_id = drafter.create_draft_for_person(
        name="Joel Danielsson",
        pay_date="2026-05-25",
        first="Joel",
        last="Danielsson",
        pdf_path=pdf,
    )
    assert draft_id == "draft_e2e"

    raw = base64.urlsafe_b64decode(captured["raw"].encode())
    msg = message_from_bytes(raw)
    assert _decoded_header(msg, "to") == "joel@workspace.se"
    assert _decoded_header(msg, "subject") == "Lönespecifikation 2026-05-25"
    assert msg.is_multipart()
    pdfs = [p for p in msg.walk() if p.get_content_type() == "application/pdf"]
    assert len(pdfs) == 1
    assert pdfs[0].get_filename() == "Joel Danielsson 2026-05-25.pdf"


def test_create_draft_for_person_no_email_skips():
    mock_dir = MagicMock()
    mock_dir.users().list().execute.return_value = {"users": []}
    drafter = _make_drafter(directory=mock_dir)
    draft_id = drafter.create_draft_for_person(
        name="Helt Okänd", pay_date="2026-05-25"
    )
    assert draft_id is None
