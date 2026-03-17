from dataclasses import dataclass

from integrations.gmail.client import Email, GmailClient


@dataclass
class ReplyDraft:
    to: str
    subject: str
    body: str
    original_email_id: str
    thread_id: str


class ReplyGenerator:
    """Prepares email thread context for Claude to reply inline — no sub-API call."""

    def __init__(self, gmail_client: GmailClient):
        self.gmail = gmail_client

    def generate_reply(
        self,
        email_id: str,
        instructions: str = "",
        tone: str = "professionnel",
    ) -> str:
        # Get the email by its Gmail message ID
        email = self.gmail.get_email(email_id)

        if not email:
            # Fallback: try search
            results = self.gmail.search(f"rfc822msgid:{email_id}", max_results=1)
            email = results[0] if results else None

        if not email:
            return f"Email introuvable: {email_id}"

        thread = self.gmail.get_email_thread(email.thread_id)
        thread_context = self._format_thread(thread)
        language = self._detect_language(email.body)

        # Return context for Claude to compose the reply inline — no sub-API call
        return (
            f"[RÉPONSE EMAIL DEMANDÉE]\n"
            f"Ton: {tone} | Langue: {language}\n"
            f"Instructions de Martin: {instructions or 'aucune'}\n"
            f"Destinataire: {email.sender}\n"
            f"Objet: Re: {email.subject}\n"
            f"Thread ID: {email.thread_id}\n\n"
            f"Thread complet:\n{thread_context}\n\n"
            f"RÈGLES:\n"
            f"- Répondre en {language}\n"
            f"- Ton {tone}\n"
            f"- Ne pas signer (Martin ajoutera sa signature)\n"
            f"- Signaler [INFO MANQUANTE: ...] si nécessaire\n"
            f"- Rédige UNIQUEMENT le corps de la réponse"
        )

    def _format_thread(self, thread: list[Email]) -> str:
        parts = []
        for email in thread[-3:]:  # Only keep last 3 emails max
            parts.append(
                f"--- De: {email.sender} | Date: {email.date} ---\n"
                f"Objet: {email.subject}\n\n{email.body[:1000]}\n"
            )
        return "\n".join(parts)

    def _detect_language(self, text: str) -> str:
        french_words = {"le", "la", "les", "de", "du", "des", "un", "une", "et", "est", "dans", "pour", "avec", "sur", "que", "qui", "pas", "ne", "ce", "se"}
        words = set(text.lower().split()[:100])
        french_count = len(words & french_words)
        return "français" if french_count > 3 else "anglais"
