"""Interactive Telegram bot setup wizard with Rich UI."""

import asyncio
import json
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text

CONFIG_PATH = Path("data/telegram_config.json")


def load_telegram_config() -> dict | None:
    """Load saved Telegram config, or None if not configured."""
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if data.get("bot_token") and data.get("chat_id"):
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def save_telegram_config(bot_token: str, chat_id: int, bot_username: str = "") -> None:
    """Save Telegram config to JSON file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(
            {"bot_token": bot_token, "chat_id": chat_id, "bot_username": bot_username},
            indent=2,
        ),
        encoding="utf-8",
    )


def delete_telegram_config() -> None:
    """Remove saved Telegram config."""
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()


async def _validate_token(token: str) -> dict | None:
    """Validate a bot token by calling getMe. Returns bot info or None."""
    from telegram import Bot
    try:
        bot = Bot(token=token)
        me = await bot.get_me()
        return {"id": me.id, "username": me.username, "first_name": me.first_name}
    except Exception:
        return None


async def _poll_for_chat_id(token: str, timeout: int = 120) -> int | None:
    """Poll getUpdates until we receive a message. Returns chat_id or None."""
    from telegram import Bot
    bot = Bot(token=token)
    # Clear old updates
    try:
        await bot.get_updates(offset=-1)
    except Exception:
        pass

    start = time.time()
    while time.time() - start < timeout:
        try:
            updates = await bot.get_updates(timeout=5)
            for update in updates:
                if update.message and update.message.chat:
                    # Acknowledge the update
                    await bot.get_updates(offset=update.update_id + 1)
                    return update.message.chat_id
        except Exception:
            pass
        await asyncio.sleep(1)
    return None


def run_setup_wizard(console: Console) -> dict | None:
    """
    Interactive Telegram setup wizard.
    Returns config dict {"bot_token", "chat_id", "bot_username"} or None if skipped.
    """
    console.print()
    console.print(
        Panel(
            "[bold cyan]🤖  Configuration Telegram[/]\n\n"
            "ONDES peut t'envoyer des messages sur Telegram :\n"
            "notifications, résumés, rappels, etc.\n\n"
            "[dim]Cette config est stockée localement dans data/telegram_config.json[/]",
            border_style="cyan",
            padding=(1, 3),
        )
    )

    if not Confirm.ask("\n  Configurer Telegram maintenant ?", default=True):
        console.print("[dim]  → Telegram ignoré. Tu pourras le configurer plus tard avec /telegram_setup[/]\n")
        return None

    # ── Step 1: Create a bot via BotFather ──
    console.print()
    console.print(
        Panel(
            "[bold yellow]Étape 1 · Créer un bot Telegram[/]\n\n"
            "1. Ouvre Telegram et cherche [bold]@BotFather[/]\n"
            "2. Envoie-lui :  [bold green]/newbot[/]\n"
            "3. Choisis un [bold]nom[/] pour ton bot (ex: Mon Assistant)\n"
            "4. Choisis un [bold]username[/] finissant par 'bot' (ex: ONDES_assistant_bot)\n"
            "5. BotFather te donnera un [bold]token[/] de cette forme :\n\n"
            "   [bold white on grey23] 123456789:ABCdEfGhIjKlMnOpQrStUvWxYz [/]\n\n"
            "[dim]Copie ce token et colle-le ci-dessous.[/]",
            border_style="yellow",
            padding=(1, 3),
            title="[bold]BotFather[/]",
            title_align="left",
        )
    )

    # ── Get and validate token ──
    bot_info = None
    while True:
        token = Prompt.ask("\n  [bold]Token du bot[/]").strip()
        if not token:
            if Confirm.ask("  Annuler la configuration ?", default=False):
                return None
            continue

        console.print("  [dim]Vérification du token...[/]", end="")
        bot_info = asyncio.run(_validate_token(token))
        if bot_info:
            console.print(f"\r  [green]✓ Bot trouvé :[/] [bold]@{bot_info['username']}[/] ({bot_info['first_name']})")
            break
        else:
            console.print("\r  [red]✗ Token invalide.[/] Vérifie que tu as copié le token complet depuis BotFather.")

    # ── Step 2: Get chat_id by asking user to message the bot ──
    console.print()
    console.print(
        Panel(
            "[bold yellow]Étape 2 · Lier ton compte[/]\n\n"
            f"1. Ouvre Telegram et cherche [bold]@{bot_info['username']}[/]\n"
            "2. Clique sur [bold]Start[/] ou envoie [bold green]/start[/]\n"
            "3. Envoie n'importe quel message (ex: [italic]hello[/])\n\n"
            "[dim]ONDES va détecter ton message automatiquement...[/]",
            border_style="yellow",
            padding=(1, 3),
            title="[bold]Liaison[/]",
            title_align="left",
        )
    )

    console.print(f"\n  ⏳ En attente d'un message sur @{bot_info['username']}...", end="")

    chat_id = asyncio.run(_poll_for_chat_id(token, timeout=120))

    if chat_id is None:
        console.print("\r  [red]✗ Timeout — aucun message reçu en 2 minutes.[/]")
        console.print("  [dim]Tu peux réessayer avec /telegram_setup[/]\n")
        return None

    console.print(f"\r  [green]✓ Compte lié ![/] (chat_id: [bold]{chat_id}[/])                    ")

    # ── Step 3: Send confirmation ──
    console.print("\n  [dim]Envoi d'un message de test...[/]", end="")
    try:
        from telegram import Bot
        bot = Bot(token=token)
        asyncio.run(
            bot.send_message(
                chat_id=chat_id,
                text="✅ *ONDES BOT connecté !*\n\nTu recevras ici tes notifications et messages.",
                parse_mode="Markdown",
            )
        )
        console.print("\r  [green]✓ Message de confirmation envoyé sur Telegram ![/]            ")
    except Exception:
        console.print("\r  [yellow]⚠ Message de test échoué, mais la config est OK[/]            ")

    # ── Save ──
    config = {
        "bot_token": token,
        "chat_id": chat_id,
        "bot_username": bot_info["username"],
    }
    save_telegram_config(**config)

    console.print()
    console.print(
        Panel(
            f"[bold green]Telegram configuré avec succès ![/]\n\n"
            f"  Bot     :  @{bot_info['username']}\n"
            f"  Chat ID :  {chat_id}\n"
            f"  Fichier :  {CONFIG_PATH}\n\n"
            "[dim]Utilise /tg dans le chat pour envoyer des messages Telegram.[/]",
            border_style="green",
            padding=(1, 3),
        )
    )

    return config


def run_reconfigure(console: Console) -> dict | None:
    """Reconfigure or disconnect Telegram. Called from /telegram_setup."""
    existing = load_telegram_config()
    if existing:
        console.print(
            Panel(
                f"[bold]Telegram est actuellement configuré[/]\n\n"
                f"  Bot     :  @{existing.get('bot_username', '?')}\n"
                f"  Chat ID :  {existing.get('chat_id', '?')}",
                border_style="cyan",
                padding=(1, 2),
            )
        )
        choice = Prompt.ask(
            "  Que veux-tu faire ?",
            choices=["reconfigurer", "déconnecter", "annuler"],
            default="annuler",
        )
        if choice == "annuler":
            return existing
        if choice == "déconnecter":
            delete_telegram_config()
            console.print("  [green]✓ Telegram déconnecté.[/]\n")
            return None
        # Fall through to full wizard for "reconfigurer"
    return run_setup_wizard(console)
