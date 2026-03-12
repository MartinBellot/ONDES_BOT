from dataclasses import dataclass, field
from datetime import datetime

from telegram import Bot


@dataclass
class TelegramMessage:
    from_name: str
    text: str
    date: datetime
    chat_id: int


class TelegramClient:
    def __init__(self, token: str, your_chat_id: int):
        self.bot = Bot(token=token)
        self.your_chat_id = your_chat_id
        self.pending_messages: list[TelegramMessage] = []
        self._enabled = bool(token)

    async def send_message(self, text: str, chat_id: int | None = None) -> str:
        if not self._enabled:
            return "Telegram non configuré."
        target = chat_id or self.your_chat_id
        await self.bot.send_message(
            chat_id=target,
            text=text,
            parse_mode="Markdown",
        )
        return f"Message envoyé à {target}"

    async def get_recent_messages(self, limit: int = 20) -> list[TelegramMessage]:
        if not self._enabled:
            return []
        updates = await self.bot.get_updates(limit=limit)
        messages = []
        for update in updates:
            if update.message and update.message.text:
                messages.append(TelegramMessage(
                    from_name=update.effective_user.full_name if update.effective_user else "Inconnu",
                    text=update.message.text,
                    date=update.message.date,
                    chat_id=update.message.chat_id,
                ))
        return messages

    async def send_to_self(self, message: str) -> str:
        return await self.send_message(message, self.your_chat_id)

    def format_messages(self, messages: list[TelegramMessage]) -> str:
        if not messages:
            return "Aucun message récent."
        lines = []
        for msg in messages:
            lines.append(
                f"**{msg.from_name}** ({msg.date.strftime('%d/%m %H:%M')}):\n{msg.text}"
            )
        return "\n\n".join(lines)
