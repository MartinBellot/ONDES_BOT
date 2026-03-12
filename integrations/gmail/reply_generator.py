from dataclasses import dataclass

from integrations.gmail.client import Email, GmailClient
from core.claude_client import ClaudeClient


@dataclass
class ReplyDraft:
    to: str
    subject: str
    body: str
    original_email_id: str
    thread_id: str


class ReplyGenerator:
    def __init__(self, claude_client: ClaudeClient, gmail_client: GmailClient):
        self.claude = claude_client
        self.gmail = gmail_client

    def generate_reply(
        self,
        email_id: str,
        instructions: str = "",
        tone: str = "professionnel",
    ) -> str:
        # Get the email and its thread
        emails = self.gmail._get_emails(query=f"rfc822msgid:{email_id}", max_results=1)

        # Fallback: get by ID directly
        if not emails:
            try:
                full_msg = (
                    self.gmail.service.users()
                    .messages()
                    .get(userId="me", id=email_id, format="full")
                    .execute()
                )
                email = self.gmail._parse_message(full_msg)
            except Exception as e:
                return f"Email introuvable: {email_id}"
        else:
            email = emails[0]

        thread = self.gmail.get_email_thread(email.thread_id)
        thread_context = self._format_thread(thread)
        language = self._detect_language(email.body)

        prompt = f"""Tu dois rédiger une réponse à cet email pour Martin.
Ton: {tone}
Contexte fourni par Martin: {instructions}

Thread complet:
{thread_context}

RÈGLES:
- Répondre en {language} (même langue que l'email)
- Être {tone}
- Ne pas signer au nom de Martin (il ajoutera sa signature)
- Si des informations manquent, signaler [INFO MANQUANTE: ...]
"""

        response = self.claude.simple_chat(
            messages=[{"role": "user", "content": prompt}],
            system="Tu es un assistant qui rédige des réponses d'emails professionnelles.",
            context_label="gmail_reply",
        )

        draft_text = response.content[0].text

        # Create draft in Gmail
        draft_result = self.gmail.create_draft(
            to=email.sender,
            subject=f"Re: {email.subject}",
            body=draft_text,
            reply_to=email.thread_id,
        )

        return f"**Brouillon généré:**\n\n{draft_text}\n\n---\n{draft_result}"

    def _format_thread(self, thread: list[Email]) -> str:
        parts = []
        for email in thread:
            parts.append(
                f"--- De: {email.sender} | Date: {email.date} ---\n"
                f"Objet: {email.subject}\n\n{email.body[:2000]}\n"
            )
        return "\n".join(parts)

    def _detect_language(self, text: str) -> str:
        french_words = {"le", "la", "les", "de", "du", "des", "un", "une", "et", "est", "dans", "pour", "avec", "sur", "que", "qui", "pas", "ne", "ce", "se"}
        words = set(text.lower().split()[:100])
        french_count = len(words & french_words)
        return "français" if french_count > 3 else "anglais"
