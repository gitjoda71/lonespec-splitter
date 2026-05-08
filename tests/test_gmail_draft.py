from unittest.mock import MagicMock
from lonespec_splitter.gmail_draft import GmailDrafter


def test_render_template():
    """Test email template rendering."""
    drafter = GmailDrafter(
        "fake.json",
        "workspace.se",
        gmail_service=MagicMock(),
        directory_service=MagicMock(),
    )

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
    """Test template rendering without pay period."""
    drafter = GmailDrafter(
        "fake.json",
        "workspace.se",
        gmail_service=MagicMock(),
        directory_service=MagicMock(),
    )

    subject, body = drafter.render_template(
        name="Bo Bengtsson", pay_date="2026-05-01", pay_period=None
    )

    assert subject == "Lönespecifikation 2026-05-01"
    assert "Bo Bengtsson" in body
    assert "för period" not in body
    assert "2026-05-01" in body


def test_lookup_email_found():
    """Test successful email lookup."""
    mock_dir_service = MagicMock()
    mock_dir_service.users().list().execute.return_value = {
        "users": [{"primaryEmail": "anna@workspace.se"}]
    }

    drafter = GmailDrafter(
        "fake.json",
        "workspace.se",
        gmail_service=MagicMock(),
        directory_service=mock_dir_service,
    )
    email = drafter.lookup_email("Anna Andersson")

    assert email == "anna@workspace.se"


def test_lookup_email_not_found():
    """Test email lookup when user not found."""
    mock_dir_service = MagicMock()
    mock_dir_service.users().list().execute.return_value = {"users": []}

    drafter = GmailDrafter(
        "fake.json",
        "workspace.se",
        gmail_service=MagicMock(),
        directory_service=mock_dir_service,
    )
    email = drafter.lookup_email("Unknown Person")

    assert email is None


def test_lookup_email_api_error():
    """Test email lookup with API error."""
    mock_dir_service = MagicMock()
    mock_dir_service.users().list().execute.side_effect = Exception("API Error")

    drafter = GmailDrafter(
        "fake.json",
        "workspace.se",
        gmail_service=MagicMock(),
        directory_service=mock_dir_service,
    )
    email = drafter.lookup_email("Anna Andersson")

    assert email is None


def test_create_draft_success():
    """Test successful draft creation."""
    mock_gmail_service = MagicMock()
    mock_gmail_service.users().drafts().create().execute.return_value = {
        "id": "draft_123"
    }

    drafter = GmailDrafter(
        "fake.json",
        "workspace.se",
        gmail_service=mock_gmail_service,
        directory_service=MagicMock(),
    )
    draft_id = drafter.create_draft(
        to="anna@workspace.se", subject="Test Subject", body="Test body"
    )

    assert draft_id == "draft_123"


def test_create_draft_failure():
    """Test draft creation failure."""
    mock_gmail_service = MagicMock()
    mock_gmail_service.users().drafts().create().execute.side_effect = Exception(
        "Gmail API Error"
    )

    drafter = GmailDrafter(
        "fake.json",
        "workspace.se",
        gmail_service=mock_gmail_service,
        directory_service=MagicMock(),
    )
    draft_id = drafter.create_draft(
        to="anna@workspace.se", subject="Test Subject", body="Test body"
    )

    assert draft_id is None


def test_create_draft_for_person():
    """Test full workflow: lookup email -> render template -> create draft."""
    mock_gmail_service = MagicMock()
    mock_gmail_service.users().drafts().create().execute.return_value = {
        "id": "draft_456"
    }

    mock_dir_service = MagicMock()
    mock_dir_service.users().list().execute.return_value = {
        "users": [{"primaryEmail": "anna@workspace.se"}]
    }

    drafter = GmailDrafter(
        "fake.json",
        "workspace.se",
        gmail_service=mock_gmail_service,
        directory_service=mock_dir_service,
    )
    draft_id = drafter.create_draft_for_person(
        name="Anna Andersson", pay_date="2026-04-25"
    )

    assert draft_id == "draft_456"
