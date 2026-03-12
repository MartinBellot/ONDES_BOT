"""Interactive Gmail setup wizard with Rich UI."""

import json
import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

CREDENTIALS_PATH = Path("data/credentials/google_oauth.json")
TOKEN_PATH = Path("data/credentials/gmail_token.json")
CONFIG_PATH = Path("data/gmail_config.json")


def load_gmail_config() -> dict | None:
    """Load saved Gmail config, or None if not configured."""
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if data.get("email") and CREDENTIALS_PATH.exists():
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def save_gmail_config(email: str, credentials_path: str, token_path: str) -> None:
    """Save Gmail config to JSON file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(
            {
                "email": email,
                "credentials_path": credentials_path,
                "token_path": token_path,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def delete_gmail_config() -> None:
    """Remove saved Gmail config and tokens."""
    for p in (CONFIG_PATH, TOKEN_PATH):
        if p.exists():
            p.unlink()


def _guide_credentials_download(console: Console) -> bool:
    """Guide the user through downloading OAuth credentials. Returns True if successful."""
    console.print()
    console.print(
        Panel(
            "[bold yellow]Étape 1 · Créer les identifiants OAuth Google[/]\n\n"
            "1. Va sur [bold link=https://console.cloud.google.com]console.cloud.google.com[/]\n\n"
            "2. [bold]Crée un projet[/] (ou utilise un projet existant)\n"
            "   → Menu hamburger ☰ → « Nouveau projet »\n\n"
            "3. [bold]Active l'API Gmail[/]\n"
            "   → APIs & Services → Bibliothèque\n"
            "   → Cherche « Gmail API » → clique sur [bold]Activer[/]\n\n"
            "4. [bold]Configure l'écran de consentement OAuth[/]\n"
            "   → APIs & Services → Écran de consentement OAuth\n"
            "   → Type : [bold]Externe[/] → Remplis le nom de l'app\n"
            "   → Ajoute [bold]ton email comme utilisateur test[/]\n\n"
            "5. [bold]Crée des identifiants OAuth[/]\n"
            "   → APIs & Services → Identifiants\n"
            "   → [bold]+ Créer des identifiants[/] → [bold]ID client OAuth[/]\n"
            "   → Type d'application : [bold]Application de bureau[/]\n"
            "   → Clique [bold]Créer[/] puis [bold]Télécharger le JSON[/] (bouton ⬇)\n\n"
            "[dim]Le fichier téléchargé s'appelle client_secret_xxx...xxx.json[/]",
            border_style="yellow",
            padding=(1, 3),
            title="[bold]Google Cloud Console[/]",
            title_align="left",
        )
    )

    while True:
        file_path = Prompt.ask(
            "\n  [bold]Chemin vers le fichier JSON téléchargé[/]\n"
            "  [dim](glisse le fichier dans le terminal, ou tape le chemin)[/]"
        ).strip().strip("'\"")

        if not file_path:
            if Confirm.ask("  Annuler la configuration ?", default=False):
                return False
            continue

        source = Path(file_path).expanduser().resolve()
        if not source.exists():
            console.print(f"  [red]✗ Fichier introuvable : {source}[/]")
            continue

        # Validate it's a proper OAuth JSON
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            if "installed" not in data and "web" not in data:
                console.print("  [red]✗ Ce fichier ne ressemble pas à des identifiants OAuth Google.[/]")
                console.print("  [dim]  Le JSON doit contenir une clé « installed » ou « web ».[/]")
                continue
        except (json.JSONDecodeError, OSError):
            console.print("  [red]✗ Fichier JSON invalide.[/]")
            continue

        # Copy to the expected location
        CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(CREDENTIALS_PATH))
        console.print(f"  [green]✓ Identifiants copiés dans [bold]{CREDENTIALS_PATH}[/][/]")
        return True


def run_setup_wizard(console: Console) -> dict | None:
    """
    Interactive Gmail setup wizard.
    Returns config dict {"email", "credentials_path", "token_path"} or None if skipped.
    """
    console.print()
    console.print(
        Panel(
            "[bold cyan]📧  Configuration Gmail[/]\n\n"
            "NIETZ peut lire tes emails, chercher, rédiger des brouillons\n"
            "et analyser ta boîte de réception.\n\n"
            "[dim]L'accès se fait via OAuth2 — tes identifiants ne sont jamais stockés.\n"
            "La config est sauvegardée dans data/gmail_config.json[/]",
            border_style="cyan",
            padding=(1, 3),
        )
    )

    if not Confirm.ask("\n  Configurer Gmail maintenant ?", default=True):
        console.print("[dim]  → Gmail ignoré. Tu pourras le configurer plus tard avec [bold]/gmail_setup[/][/]\n")
        return None

    # ── Step 1: Get OAuth credentials file ──
    if CREDENTIALS_PATH.exists():
        console.print(f"\n  [green]✓[/] Fichier OAuth déjà présent : [bold]{CREDENTIALS_PATH}[/]")
        if not Confirm.ask("  Utiliser ce fichier ?", default=True):
            if not _guide_credentials_download(console):
                return None
    else:
        if not _guide_credentials_download(console):
            return None

    if not CREDENTIALS_PATH.exists():
        console.print("\n  [red]✗ Fichier OAuth introuvable.[/]")
        console.print("  [dim]Tu peux réessayer avec /gmail_setup[/]\n")
        return None

    # ── Step 2: Run OAuth flow ──
    console.print()
    console.print(
        Panel(
            "[bold yellow]Étape 2 · Autorisation OAuth[/]\n\n"
            "Ton navigateur va s'ouvrir pour autoriser NIETZ BOT\n"
            "à accéder à ta boîte Gmail.\n\n"
            "[bold]Permissions demandées :[/]\n"
            "  • [dim]gmail.readonly[/]   → Lire tes emails\n"
            "  • [dim]gmail.compose[/]    → Créer des brouillons\n"
            "  • [dim]gmail.labels[/]     → Gérer les labels\n\n"
            "[dim]Aucun email ne sera envoyé sans ta confirmation explicite.[/]",
            border_style="yellow",
            padding=(1, 3),
            title="[bold]Google OAuth[/]",
            title_align="left",
        )
    )

    if not Confirm.ask("\n  Ouvrir le navigateur pour l'autorisation ?", default=True):
        console.print("[dim]  → Tu peux relancer avec /gmail_setup[/]\n")
        return None

    console.print("\n  ⏳ Ouverture du navigateur...\n")

    try:
        from integrations.gmail.auth import get_gmail_service

        service = get_gmail_service(str(CREDENTIALS_PATH), str(TOKEN_PATH))

        # Get the user's email address to confirm success
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "inconnu")

        console.print(f"  [green]✓ Connecté à [bold]{email}[/] ![/]")
    except FileNotFoundError as e:
        console.print(f"\n  [red]✗ {e}[/]")
        return None
    except Exception as e:
        console.print(f"\n  [red]✗ Erreur OAuth : {e}[/]")
        console.print("  [dim]Tu peux réessayer avec /gmail_setup[/]\n")
        return None

    # ── Save ──
    config = {
        "email": email,
        "credentials_path": str(CREDENTIALS_PATH),
        "token_path": str(TOKEN_PATH),
    }
    save_gmail_config(**config)

    console.print()
    console.print(
        Panel(
            f"[bold green]Gmail configuré avec succès ![/]\n\n"
            f"  Email  :  {email}\n"
            f"  OAuth  :  {CREDENTIALS_PATH}\n"
            f"  Token  :  {TOKEN_PATH}\n\n"
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
        # Fall through to full wizard for "reconfigurer"
    return run_setup_wizard(console)
