"""
Gmail tests — IMAP/App Password based.
Skip when not configured.
"""
import pytest


def test_gmail_import():
    from integrations.gmail.client import GmailClient, Email
    assert GmailClient is not None
    assert Email is not None


def test_email_dataclass():
    from integrations.gmail.client import Email

    email = Email(
        id="test123",
        thread_id="thread456",
        subject="Test Subject",
        sender="test@example.com",
        to="me@example.com",
        date="2026-03-12",
        body="Hello world",
        snippet="Hello...",
        is_unread=True,
    )
    assert email.id == "test123"
    assert email.is_unread is True
    assert email.subject == "Test Subject"


def test_html_to_text():
    from integrations.gmail.client import GmailClient

    client = GmailClient("test@gmail.com", "fake_password")
    text = client._html_to_text("<p>Hello <b>World</b></p><br/>New line")
    assert "Hello" in text
    assert "World" in text
