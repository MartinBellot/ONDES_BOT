"""Gmail client using IMAP/SMTP with App Password — no OAuth needed."""

import imaplib
import smtplib
import email as email_lib
from email.mime.text import MIMEText
from email.header import decode_header as _decode_header
from dataclasses import dataclass, field
from html import unescape
import re


@dataclass
class Email:
    id: str
    thread_id: str
    subject: str
    sender: str
    to: str
    date: str
    body: str
    snippet: str
    labels: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    is_unread: bool = False


class GmailClient:
    """Gmail client via IMAP/SMTP. Uses Gmail extensions (X-GM-RAW, X-GM-THRID)."""

    IMAP_HOST = "imap.gmail.com"
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(self, email_addr: str, app_password: str):
        self.email = email_addr
        self.app_password = app_password

    # ─── Public API (same interface as before) ───

    def get_unread_emails(self, max_results: int = 20) -> list[Email]:
        return self._search_emails("is:unread", max_results)

    def get_emails(
        self,
        filter: str = "all",
        max_results: int = 10,
        search_query: str = "",
    ) -> list[Email]:
        query = search_query
        if filter == "unread":
            query = f"is:unread {query}".strip()
        elif filter == "important":
            query = f"is:important {query}".strip()
        return self._search_emails(query or "in:inbox", max_results)

    def search(self, query: str, max_results: int = 10) -> list[Email]:
        return self._search_emails(query, max_results)

    def get_email(self, email_id: str) -> Email | None:
        """Fetch a single email by its Gmail message ID (X-GM-MSGID)."""
        try:
            imap = self._connect()
            status, data = imap.uid("SEARCH", None, "X-GM-MSGID", email_id)
            if status == "OK" and data[0]:
                uid = data[0].split()[0]
                result = self._fetch_email(imap, uid)
                imap.logout()
                return result
            imap.logout()
        except Exception:
            pass
        return None

    def get_email_thread(self, thread_id: str) -> list[Email]:
        """Fetch all emails in a Gmail thread using X-GM-THRID."""
        try:
            imap = self._connect("\"[Gmail]/All Mail\"")
            status, data = imap.uid("SEARCH", None, "X-GM-THRID", thread_id)
            if status != "OK" or not data[0]:
                imap.logout()
                return []
            uids = data[0].split()
            emails = []
            for uid in uids:
                email_obj = self._fetch_email(imap, uid)
                if email_obj:
                    emails.append(email_obj)
            imap.logout()
            return emails
        except Exception:
            return []

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
    ) -> str:
        """Create a draft via IMAP APPEND to the Drafts folder."""
        msg = MIMEText(body, _charset="utf-8")
        msg["To"] = to
        msg["From"] = self.email
        msg["Subject"] = subject

        try:
            imap = imaplib.IMAP4_SSL(self.IMAP_HOST)
            imap.login(self.email, self.app_password)
            drafts = self._find_folder_by_flag(imap, "\\Drafts", "[Gmail]/Drafts")
            imap.append(drafts, "\\Draft", None, msg.as_bytes())
            imap.logout()
            return f"Brouillon créé → {to} | Objet: {subject}"
        except Exception as e:
            return f"Erreur création brouillon: {e}"

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
    ) -> str:
        """Send an email via SMTP."""
        msg = MIMEText(body, _charset="utf-8")
        msg["To"] = to
        msg["From"] = self.email
        msg["Subject"] = subject

        try:
            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as server:
                server.starttls()
                server.login(self.email, self.app_password)
                server.send_message(msg)
            return f"✉️ Email envoyé → {to} | Objet: {subject}"
        except Exception as e:
            return f"Erreur envoi email: {e}"

    def get_stats(self) -> dict:
        """Get mailbox statistics (inbox, spam, trash)."""
        try:
            imap = self._connect()
            stats = {}

            # INBOX
            status, data = imap.status("INBOX", "(MESSAGES UNSEEN)")
            if status == "OK":
                parsed = self._parse_status(data[0])
                stats["INBOX"] = {
                    "total": parsed.get("MESSAGES", 0),
                    "unread": parsed.get("UNSEEN", 0),
                }

            # Spam & Trash (find by IMAP flag, locale-independent)
            for flag, label in [("\\Junk", "SPAM"), ("\\Trash", "TRASH")]:
                folder = self._find_folder_by_flag(imap, flag)
                if folder:
                    try:
                        status, data = imap.status(f'"{folder}"', "(MESSAGES)")
                        if status == "OK":
                            parsed = self._parse_status(data[0])
                            stats[label] = {"total": parsed.get("MESSAGES", 0), "unread": 0}
                    except Exception:
                        pass

            imap.logout()
            return stats
        except Exception:
            return {}

    # ─── Private helpers ───

    def _connect(self, folder: str = "INBOX") -> imaplib.IMAP4_SSL:
        imap = imaplib.IMAP4_SSL(self.IMAP_HOST)
        imap.login(self.email, self.app_password)
        imap.select(folder)
        return imap

    def _search_emails(self, query: str, max_results: int = 10) -> list[Email]:
        """Search using Gmail's X-GM-RAW extension (full Gmail search syntax)."""
        try:
            imap = self._connect()
            safe_query = query.replace('"', "'")
            status, data = imap.uid("SEARCH", None, "X-GM-RAW", f'"{safe_query}"')
            if status != "OK" or not data[0]:
                imap.logout()
                return []

            uids = data[0].split()
            uids = uids[-max_results:]  # Keep most recent
            uids.reverse()

            emails = []
            for uid in uids:
                email_obj = self._fetch_email(imap, uid)
                if email_obj:
                    emails.append(email_obj)

            imap.logout()
            return emails
        except Exception:
            return []

    def _fetch_email(self, imap: imaplib.IMAP4_SSL, uid: bytes) -> Email | None:
        """Fetch and parse a single email by UID, including Gmail extensions."""
        try:
            status, data = imap.uid("FETCH", uid, "(RFC822 FLAGS X-GM-THRID X-GM-MSGID)")
            if status != "OK" or not data or not data[0]:
                return None

            raw_response = data[0]
            if not isinstance(raw_response, tuple) or len(raw_response) < 2:
                return None

            metadata = raw_response[0].decode("utf-8", errors="replace")
            raw_email = raw_response[1]

            # Extract Gmail thread ID & message ID
            thread_id = ""
            thrid_match = re.search(r"X-GM-THRID (\d+)", metadata)
            if thrid_match:
                thread_id = thrid_match.group(1)

            msgid_match = re.search(r"X-GM-MSGID (\d+)", metadata)
            msg_id = msgid_match.group(1) if msgid_match else uid.decode()

            is_unread = b"\\Seen" not in raw_response[0]

            # Parse email content
            msg = email_lib.message_from_bytes(raw_email)

            subject = self._safe_decode_header(msg.get("Subject", "(sans objet)"))
            sender = self._safe_decode_header(msg.get("From", ""))
            to = self._safe_decode_header(msg.get("To", ""))
            date = msg.get("Date", "")

            body = self._extract_body(msg)
            snippet = body[:200].replace("\n", " ").strip() if body else ""

            attachments = []
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    filename = part.get_filename()
                    if filename:
                        attachments.append(self._safe_decode_header(filename))

            return Email(
                id=msg_id,
                thread_id=thread_id,
                subject=subject,
                sender=sender,
                to=to,
                date=date,
                body=body,
                snippet=snippet,
                attachments=attachments,
                is_unread=is_unread,
            )
        except Exception:
            return None

    def _safe_decode_header(self, header: str) -> str:
        if not header:
            return ""
        try:
            parts = _decode_header(header)
            decoded = []
            for content, charset in parts:
                if isinstance(content, bytes):
                    decoded.append(content.decode(charset or "utf-8", errors="replace"))
                else:
                    decoded.append(content)
            return " ".join(decoded)
        except Exception:
            return str(header)

    def _extract_body(self, msg: email_lib.message.Message) -> str:
        """Extract text body, prefer text/plain over HTML."""
        if not msg.is_multipart():
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
                if content_type == "text/html":
                    return self._html_to_text(text)
                return text
            return ""

        plain_text = ""
        html_text = ""
        for part in msg.walk():
            content_type = part.get_content_type()
            if part.get_content_disposition() == "attachment":
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if content_type == "text/plain" and not plain_text:
                plain_text = text
            elif content_type == "text/html" and not html_text:
                html_text = text
        return plain_text or (self._html_to_text(html_text) if html_text else "")

    def _html_to_text(self, html: str) -> str:
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = unescape(text)
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    def _find_folder_by_flag(self, imap: imaplib.IMAP4_SSL, flag: str, fallback: str = "") -> str:
        """Find an IMAP folder by its special-use flag (locale-independent)."""
        try:
            status, folders = imap.list()
            if status == "OK":
                for folder_data in folders:
                    decoded = folder_data.decode("utf-8", errors="replace") if isinstance(folder_data, bytes) else str(folder_data)
                    if flag in decoded:
                        matches = re.findall(r'"([^"]*)"', decoded)
                        if len(matches) >= 2:
                            return matches[-1]
        except Exception:
            pass
        return fallback

    def _parse_status(self, status_line: bytes | str) -> dict:
        line = status_line.decode("utf-8", errors="replace") if isinstance(status_line, bytes) else status_line
        result = {}
        for key in ("MESSAGES", "UNSEEN", "RECENT"):
            match = re.search(rf"{key}\s+(\d+)", line)
            if match:
                result[key] = int(match.group(1))
        return result
