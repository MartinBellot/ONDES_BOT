"""Telegram interface for ONDES Bot — acts as a second UI alongside the terminal."""

import asyncio
import logging
from datetime import datetime

import httpx
from telegram import Bot, Update
from telegram.error import Conflict
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
)

logger = logging.getLogger(__name__)


class _ConflictFilter(logging.Filter):
    """Drop all log records that mention Telegram Conflict errors."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(getattr(record, "msg", ""))
        if "Conflict" in msg or "terminated by other getUpdates" in msg:
            return False
        if record.exc_info and record.exc_info[1]:
            if "Conflict" in str(record.exc_info[1]):
                return False
        return True


# Silence Conflict spam from python-telegram-bot's polling loop.
# The lib's get_logger() maps _utils modules to parent name "telegram.ext".
_conflict_filter = _ConflictFilter()
for _name in ("telegram.ext", "telegram", "telegram.ext.Updater"):
    _lg = logging.getLogger(_name)
    _lg.addFilter(_conflict_filter)
# Also install on root logger handlers so it's caught regardless of config.
logging.getLogger().addFilter(_conflict_filter)


class TelegramInterface:
    """Runs the Telegram bot as a chat interface to ONDES, alongside the terminal."""

    def __init__(self, token: str, allowed_chat_id: int):
        self.token = token
        self.allowed_chat_id = allowed_chat_id
        self._conversation = None  # Set via set_conversation()
        self._app: Application | None = None

    def set_conversation(self, conversation):
        """Inject the ConversationManager so messages are routed through Claude."""
        self._conversation = conversation

    async def _handle_message(self, update: Update, context) -> None:
        """Process an incoming Telegram message through the ConversationManager."""
        if not update.message or not update.message.text:
            return

        # Only respond to the authorized user
        if update.message.chat_id != self.allowed_chat_id:
            return

        user_text = update.message.text.strip()
        if not user_text:
            return

        if not self._conversation:
            await update.message.reply_text("⚠️ Bot pas encore prêt, réessaye dans quelques secondes.")
            return

        try:
            # Route through the same ConversationManager as the terminal
            response = self._conversation.chat(user_text)

            # Telegram messages have a 4096 char limit — split if needed
            for chunk in _split_message(response):
                await update.message.reply_text(chunk, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Telegram handler error: {e}")
            try:
                await update.message.reply_text(f"❌ Erreur: {e}")
            except Exception:
                pass

    async def _handle_start(self, update: Update, context) -> None:
        """Handle /start command."""
        if update.message and update.message.chat_id == self.allowed_chat_id:
            await update.message.reply_text(
                "👋 *ONDES Bot* est connecté !\n\n"
                "Envoie-moi n'importe quel message et je le traiterai "
                "exactement comme dans le terminal.",
                parse_mode="Markdown",
            )

    def start(self) -> None:
        """Start the Telegram bot polling in a background thread (non-blocking)."""
        import threading

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._run_polling())

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    async def _run_polling(self) -> None:
        """Build the Application and start polling, retrying on Conflict errors."""
        # Force-kill any stale polling session via raw HTTP call.
        # This is more reliable than using the Bot class which may itself conflict.
        api_url = f"https://api.telegram.org/bot{self.token}"
        async with httpx.AsyncClient() as http:
            try:
                await http.post(f"{api_url}/deleteWebhook", json={"drop_pending_updates": True})
                await http.post(f"{api_url}/getUpdates", json={"offset": -1, "timeout": 1}, timeout=10)
            except Exception:
                pass

        # Wait for Telegram servers to release the old long-poll connection
        await asyncio.sleep(3)

        self._app = (
            Application.builder()
            .token(self.token)
            .build()
        )
        self._app.add_handler(CommandHandler("start", self._handle_start))
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )

        # Keep running forever (daemon thread will be killed on exit)
        stop_event = asyncio.Event()
        await stop_event.wait()


def _split_message(text: str, max_len: int = 4096) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to split on a newline
        split_at = text.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks
