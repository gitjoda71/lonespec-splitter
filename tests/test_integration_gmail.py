"""Integration tests for Gmail drafting with split PDF."""
from pathlib import Path

from lonespec_splitter.__main__ import main


def test_cli_with_gmail_flag_no_config(tmp_path):
    """Test --with-gmail without --gmail-config returns error."""
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    argv = [str(dummy_pdf), str(output_dir), "--with-gmail"]
    result = main(argv)

    assert result == 3  # EXIT_INVALID_INPUT


def test_cli_with_gmail_config_missing_file(tmp_path):
    """Test --with-gmail with missing config file — graceful degradation."""
    fixture_path = Path(__file__).parent / "fixtures" / "fixture_visma_3personer.pdf"

    if not fixture_path.exists():
        # Skip test if fixture doesn't exist
        return

    test_pdf = tmp_path / "test.pdf"
    test_pdf.write_bytes(fixture_path.read_bytes())

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    missing_config = tmp_path / "missing_config.yaml"

    argv = [
        str(test_pdf),
        str(output_dir),
        "--with-gmail",
        "--gmail-config",
        str(missing_config),
    ]
    result = main(argv)

    # Should succeed (0) because Gmail init fails gracefully, split still works
    assert result == 0
