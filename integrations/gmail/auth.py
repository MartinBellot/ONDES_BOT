"""Simple Gmail credential validation via IMAP."""

import imaplib

IMAP_HOST = "imap.gmail.com"


def validate_credentials(email_addr: str, app_password: str) -> bool:
    """Test IMAP login with an app password. Returns True if credentials are valid."""
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
            imap.login(email_addr, app_password)
        return True
    except imaplib.IMAP4.error:
        return False
