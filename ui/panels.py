from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.markdown import Markdown

from core.token_tracker import TokenTracker


def render_email_panel(email_data: dict, show_body: bool = False) -> Panel:
    header = Table.grid(padding=(0, 1))
    header.add_column(style="bold", width=8)
    header.add_column()

    header.add_row("De", email_data.get("sender", ""))
    header.add_row("Objet", f"[bold white]{email_data.get('subject', '')}[/]")
    header.add_row("Date", f"[dim]{email_data.get('date', '')}[/]")

    if show_body:
        body = email_data.get("body", "")[:500]
        if len(email_data.get("body", "")) > 500:
            body += "..."
        content = f"{header}\n\n{body}"
    else:
        content = header

    return Panel(
        content,
        title=f"[bold cyan]📧 Email[/]",
        border_style="cyan",
    )


def render_status_bar(tracker: TokenTracker) -> Text:
    sess = tracker.session_tokens
    monthly = tracker.monthly_stats()
    pct = monthly["budget_pct"]

    budget_color = "green" if pct < 75 else ("yellow" if pct < 100 else "red")
    budget_indicator = "■" if pct < 75 else ("▲" if pct < 100 else "✕")

    bar = Text()
    bar.append("  ONDES BOT  ", style="bold cyan")
    bar.append("· ", style="dim")
    bar.append(f"Session: {sess['total']:,} tok", style="white")
    bar.append("  ", style="dim")
    bar.append(f"~${sess['cost_usd']:.4f}", style="yellow")
    bar.append("  ", style="dim")
    bar.append(
        f"Mois: ${monthly['cost_usd']:.2f} / ${tracker.monthly_budget:.0f}",
        style=budget_color,
    )
    bar.append(f"  {budget_indicator}  ", style=budget_color)
    return bar


def render_stats_panel(tracker: TokenTracker) -> Panel:
    sess = tracker.session_tokens
    monthly = tracker.monthly_stats()
    top = tracker.top_consumers()

    content = Text()

    content.append("SESSION EN COURS\n", style="bold underline")
    content.append(f"  Tokens input    : {sess['input']:>8,}\n")
    content.append(f"  Tokens output   : {sess['output']:>8,}\n")
    content.append(f"  Coût session    : ${sess['cost_usd']:.4f}\n\n")

    content.append("MOIS EN COURS\n", style="bold underline")
    content.append(f"  Total tokens    : {monthly['input_tokens'] + monthly['output_tokens']:>8,}\n")
    content.append(f"  Appels API      : {monthly['api_calls']:>8,}\n")
    pct = monthly["budget_pct"]
    content.append(f"  Coût total      : ${monthly['cost_usd']:.2f}  /  ${tracker.monthly_budget:.0f}  ({pct:.1f}%)\n")

    bar_filled = int(pct / 100 * 15)
    bar_empty = 15 - bar_filled
    content.append(f"  [{'█' * bar_filled}{'░' * bar_empty}]  {pct:.1f}%\n\n")

    if top:
        content.append("TOP CONSOMMATEURS (30 jours)\n", style="bold underline")
        for i, t in enumerate(top[:5], 1):
            content.append(f"  {i}. {t['context']:<20} ${t['cost_usd']:.2f}  ({t['calls']} appels)\n")

    return Panel(
        content,
        title="[bold]📊 STATISTIQUES D'UTILISATION[/]",
        border_style="bright_blue",
        padding=(1, 2),
    )


def render_help_panel() -> Panel:
    content = Text()
    content.append(" COMMANDES DISPONIBLES\n\n", style="bold underline cyan")

    commands = [
        ("/mail", "Afficher les derniers mails"),
        ("/mail unread", "Emails non lus uniquement"),
        ("/cal today", "Événements d'aujourd'hui"),
        ("/cal week", "Vue hebdomadaire"),
        ("/tasks", "Tâches actives"),
        ("/tasks done <id>", "Marquer une tâche comme faite"),
        ("/run <code>", "Exécuter du Python inline"),
        ("/review <fichier>", "Revue de code"),
        ("/tg <message>", "Envoyer un message Telegram"),
        ("/search <query>", "Recherche web"),
        ("/docker", "Gérer Docker (containers, images, compose)"),
        ("/gh", "GitHub (repos, issues, PRs, actions)"),
        ("/music", "Contrôler Apple Music"),
        ("/auto", "Gérer les automatisations"),
        ("/memory", "Visualiser la mémoire (faits, actions, résumés)"),
        ("/memory facts", "Faits mémorisés uniquement"),
        ("/memory actions", "Actions récentes uniquement"),
        ("/stats", "Statistiques tokens & coûts"),
        ("/clear", "Vider l'historique"),
        ("/gmail_setup", "Configurer/reconfigurer Gmail"),
        ("/telegram_setup", "Configurer/reconfigurer Telegram"),
        ("/help", "Cette aide"),
    ]

    for cmd, desc in commands:
        content.append(f"  {cmd:<22}", style="bold green")
        content.append(f"  {desc}\n", style="white")

    content.append("\n Sinon, parle-moi en langage naturel !", style="dim italic")

    return Panel(
        content,
        title="[bold cyan]❓ AIDE[/]",
        border_style="cyan",
        padding=(1, 2),
    )
