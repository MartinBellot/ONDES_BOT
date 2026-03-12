import base64
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from datetime import datetime
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
    def __init__(self, service):
        self.service = service

    def get_unread_emails(self, max_results: int = 20) -> list[Email]:
        return self._get_emails(query="is:unread", max_results=max_results)

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
        return self._get_emails(query=query, max_results=max_results)

    def search(self, query: str, max_results: int = 10) -> list[Email]:
        return self._get_emails(query=query, max_results=max_results)

    def get_email_thread(self, thread_id: str) -> list[Email]:
        thread = (
            self.service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )
        return [self._parse_message(msg) for msg in thread.get("messages", [])]

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
    ) -> str:
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        draft_body: dict = {"message": {"raw": raw}}
        if reply_to:
            draft_body["message"]["threadId"] = reply_to

        draft = (
            self.service.users()
            .drafts()
            .create(userId="me", body=draft_body)
            .execute()
        )

        return f"Brouillon créé (ID: {draft['id']})"

    def get_stats(self) -> dict:
        labels = self.service.users().labels().list(userId="me").execute()
        stats = {}
        for label in labels.get("labels", []):
            if label["id"] in ("INBOX", "UNREAD", "SPAM", "TRASH"):
                detail = (
                    self.service.users()
                    .labels()
                    .get(userId="me", id=label["id"])
                    .execute()
                )
                stats[label["name"]] = {
                    "total": detail.get("messagesTotal", 0),
                    "unread": detail.get("messagesUnread", 0),
                }
        return stats

    def _get_emails(self, query: str = "", max_results: int = 10) -> list[Email]:
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
        except Exception as e:
            return []

        emails = []
        for msg in results.get("messages", []):
            try:
                full_msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )
                emails.append(self._parse_message(full_msg))
            except Exception:
                continue
        return emails

    def _parse_message(self, msg: dict) -> Email:
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

        body = self._extract_body(msg.get("payload", {}))

        label_ids = msg.get("labelIds", [])
        attachments = self._extract_attachment_names(msg.get("payload", {}))

        return Email(
            id=msg["id"],
            thread_id=msg.get("threadId", ""),
            subject=headers.get("subject", "(sans objet)"),
            sender=headers.get("from", ""),
            to=headers.get("to", ""),
            date=headers.get("date", ""),
            body=body,
            snippet=msg.get("snippet", ""),
            labels=label_ids,
            attachments=attachments,
            is_unread="UNREAD" in label_ids,
        )

    def _extract_body(self, payload: dict) -> str:
        """Extrait le corps du message, préfère text/plain."""
        if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

        # Fallback: try HTML
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                return self._html_to_text(html)

        # Nested multipart
        for part in payload.get("parts", []):
            if "parts" in part:
                result = self._extract_body(part)
                if result:
                    return result

        return ""

    def _html_to_text(self, html: str) -> str:
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = unescape(text)
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    def _extract_attachment_names(self, payload: dict) -> list[str]:
        names = []
        for part in payload.get("parts", []):
            if part.get("filename"):
                names.append(part["filename"])
            if "parts" in part:
                names.extend(self._extract_attachment_names(part))
        return names
