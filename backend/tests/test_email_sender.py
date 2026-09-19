import pytest
from backend.app.services.email_sender import email_sender
from backend.app.core.config import settings

def test_dry_run_sending():
    # Save previous setting
    prev_dry_run = settings.DRY_RUN
    settings.DRY_RUN = True

    try:
        result = email_sender.send_single_message(
            recipient="candidate@example.com",
            subject="Test Dry Run",
            html_body="<p>Test</p>",
            text_body="Test"
        )
        assert result["success"] is True
        assert result["mode"] == "DRY_RUN"
        assert result["message_id"] is not None
    finally:
        settings.DRY_RUN = prev_dry_run

def test_email_test_mode_redirect():
    prev_dry_run = settings.DRY_RUN
    prev_test_mode = settings.EMAIL_TEST_MODE
    prev_test_addr = settings.TEST_EMAIL_ADDRESS

    settings.DRY_RUN = True
    settings.EMAIL_TEST_MODE = True
    settings.TEST_EMAIL_ADDRESS = "admin-test@sponsorajobs.com"

    try:
        result = email_sender.send_single_message(
            recipient="candidate@real-domain.com",
            subject="Test Redirect",
            html_body="<p>Test</p>",
            text_body="Test"
        )
        assert result["success"] is True
        assert result["actual_recipient"] == "admin-test@sponsorajobs.com"
        assert result["intended_recipient"] == "candidate@real-domain.com"
    finally:
        settings.DRY_RUN = prev_dry_run
        settings.EMAIL_TEST_MODE = prev_test_mode
        settings.TEST_EMAIL_ADDRESS = prev_test_addr
