"""Interactive Gmail setup wizard with Rich UI — IMAP + App Password."""

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

CONFIG_PATH = Path("data/gmail_config.json")


def load_gmail_config() -> dict | None:
    """Load saved Gmail config, or None if not configured."""
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if data.get("email") and data.get("app_password"):
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def save_gmail_config(email: str, app_password: str) -> None:
    """Save Gmail config to JSON file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps({"email": email, "app_password": app_password}, indent=2),
        encoding="utf-8",
    )


def delete_gmail_config() -> None:
    """Remove saved Gmail config."""
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()


def run_setup_wizard(console: Console) -> dict | None:
    """
    Interactive Gmail setup — just email + app password.
    Returns config dict {"email", "app_password"} or None if skipped.
    """
    console.print()
    console.print(
        Panel(
            "[bold cyan]📧  Configuration Gmail[/]\n\n"
            "ONDES peut lire tes emails, chercher, rédiger des brouillons\n"
            "et analyser ta boîte de réception.\n\n"
            "[dim]Connexion via IMAP avec un mot de passe d'application Google.\n"
            "Ton mot de passe principal n'est jamais utilisé.[/]",
            border_style="cyan",
            padding=(1, 3),
        )
    )

    if not Confirm.ask("\n  Configurer Gmail maintenant ?", default=True):
        console.print("[dim]  → Gmail ignoré. Tu pourras le configurer plus tard avec [bold]/gmail_setup[/][/]\n")
        return None

    # ── Guide: create an App Password ──
    console.print()
    console.print(
        Panel(
            "[bold yellow]Étape 1 · Créer un mot de passe d'application[/]\n\n"
            "1. Va sur [bold link=https://myaccount.google.com/apppasswords]myaccount.google.com/apppasswords[/]\n"
            "   [dim](la vérification en 2 étapes doit être activée)[/]\n\n"
            "2. Donne un nom à l'app (ex: « ONDES Bot »)\n\n"
            "3. Clique [bold]Créer[/] → copie le mot de passe de 16 caractères\n\n"
            "[dim]Ce mot de passe ne donne accès qu'aux emails,\n"
            "pas aux paramètres de ton compte Google.[/]",
            border_style="yellow",
            padding=(1, 3),
            title="[bold]Google App Password[/]",
            title_align="left",
        )
    )

    # ── Collect credentials ──
    console.print()
    email_addr = Prompt.ask("  [bold]Ton adresse Gmail[/]").strip()
    if not email_addr or "@" not in email_addr:
        console.print("  [red]✗ Adresse email invalide.[/]")
        return None

    app_password = Prompt.ask("  [bold]Mot de passe d'application[/] [dim](16 caractères)[/]").strip()
    if not app_password:
        console.print("  [red]✗ Mot de passe requis.[/]")
        return None

    # Remove spaces (Google shows app passwords as "xxxx xxxx xxxx xxxx")
    app_password = app_password.replace(" ", "")

    # ── Test credentials ──
    console.print("\n  ⏳ Test de connexion...")

    from integrations.gmail.auth import validate_credentials

    if not validate_credentials(email_addr, app_password):
        console.print("  [red]✗ Connexion échouée.[/]")
        console.print("  [dim]Vérifie ton email et mot de passe d'application.[/]")
        console.print("  [dim]La vérification en 2 étapes doit être activée.[/]\n")
        return None

    console.print(f"  [green]✓ Connecté à [bold]{email_addr}[/] ![/]")

    # ── Save ──
    config = {"email": email_addr, "app_password": app_password}
    save_gmail_config(**config)

    console.print()
    console.print(
        Panel(
            f"[bold green]Gmail configuré avec succès ![/]\n\n"
            f"  Email  :  {email_addr}\n"
            f"  Auth   :  Mot de passe d'application\n\n"
            "[dim]Utilise /mail dans le chat pour accéder à tes emails.[/]",
            border_style="green",
            padding=(1, 3),
        )
    )

    return config


def run_reconfigure(console: Console) -> dict | None:
    """Reconfigure or disconnect Gmail. Called from /gmail_setup."""
    existing = load_gmail_config()
    if existing:
        console.print(
            Panel(
                f"[bold]Gmail est actuellement configuré[/]\n\n"
                f"  Email :  {existing.get('email', '?')}",
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
            delete_gmail_config()
            console.print("  [green]✓ Gmail déconnecté.[/]\n")
            return None
    return run_setup_wizard(console)
