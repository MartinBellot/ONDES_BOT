from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.markdown import Markdown
from rich.rule import Rule

from core.token_tracker import TokenTracker
from ui.themes import C, S, BORDERS, BOX


def render_email_panel(email_data: dict, show_body: bool = False) -> Panel:
    header = Table.grid(padding=(0, 1))
    header.add_column(style=f"bold {C['text_dim']}", width=8)
    header.add_column()

    header.add_row("De", f"[{C['text']}]{email_data.get('sender', '')}[/]")
    header.add_row("Objet", f"[bold {C['text']}]{email_data.get('subject', '')}[/]")
    header.add_row("Date", f"[{C['text_dim']}]{email_data.get('date', '')}[/]")

    if show_body:
        body = email_data.get("body", "")[:500]
        if len(email_data.get("body", "")) > 500:
            body += "..."
        content = f"{header}\n\n{body}"
    else:
        content = header

    return Panel(
        content,
        title=f"[bold {C['cyan']}]📧 Email[/]",
        title_align="left",
        border_style=BORDERS["email"],
        box=BOX,
        padding=(1, 2),
    )


def render_status_bar(tracker: TokenTracker) -> Text:
    sess = tracker.session_tokens
    monthly = tracker.monthly_stats()
    pct = monthly["budget_pct"]

    budget_color = C["emerald"] if pct < 75 else (C["amber"] if pct < 100 else C["red"])
    budget_icon = "●" if pct < 75 else ("▲" if pct < 100 else "✕")

    bar = Text()
    bar.append("  ◉ ", style=C["violet"])
    bar.append(f"{sess['total']:,} tok", style=C["text_dim"])
    bar.append("  ", style="dim")
    bar.append(f"~${sess['cost_usd']:.4f}", style=C["amber_dim"])
    bar.append("  │  ", style=C["border"])
    bar.append(
        f"${monthly['cost_usd']:.2f}/${tracker.monthly_budget:.0f}$",
        style=budget_color,
    )
    bar.append(f"  {budget_icon} ", style=budget_color)

    # Mini progress bar
    filled = min(int(pct / 100 * 10), 10)
    empty = 10 - filled
    bar.append(f"{'━' * filled}", style=budget_color)
    bar.append(f"{'╌' * empty}", style=C["border"])

    return bar


def render_stats_panel(tracker: TokenTracker) -> Panel:
    sess = tracker.session_tokens
    monthly = tracker.monthly_stats()
    top = tracker.top_consumers()

    content = Text()

    content.append("  SESSION EN COURS\n", style=f"bold {C['violet_bright']}")
    content.append(f"    Tokens input    : ", style=C["text_dim"])
    content.append(f"{sess['input']:>8,}\n", style=C["text"])
    content.append(f"    Tokens output   : ", style=C["text_dim"])
    content.append(f"{sess['output']:>8,}\n", style=C["text"])
    content.append(f"    Coût session    : ", style=C["text_dim"])
    content.append(f"${sess['cost_usd']:.4f}\n\n", style=C["amber"])

    content.append("  MOIS EN COURS\n", style=f"bold {C['violet_bright']}")
    content.append(f"    Total tokens    : ", style=C["text_dim"])
    content.append(f"{monthly['input_tokens'] + monthly['output_tokens']:>8,}\n", style=C["text"])
    content.append(f"    Appels API      : ", style=C["text_dim"])
    content.append(f"{monthly['api_calls']:>8,}\n", style=C["text"])

    pct = monthly["budget_pct"]
    pct_color = C["emerald"] if pct < 75 else (C["amber"] if pct < 100 else C["red"])
    content.append(f"    Coût total      : ", style=C["text_dim"])
    content.append(f"${monthly['cost_usd']:.2f}", style=pct_color)
    content.append(f"  /  ${tracker.monthly_budget:.0f}", style=C["text_dim"])
    content.append(f"  ({pct:.1f}%)\n", style=pct_color)

    # Progress bar
    bar_filled = int(pct / 100 * 20)
    bar_empty = 20 - bar_filled
    content.append(f"    [", style=C["text_dim"])
    content.append(f"{'━' * bar_filled}", style=pct_color)
    content.append(f"{'╌' * bar_empty}", style=C["border"])
    content.append(f"]  {pct:.1f}%\n\n", style=pct_color)

    if top:
        content.append("  TOP CONSOMMATEURS (30j)\n", style=f"bold {C['violet_bright']}")
        for i, t in enumerate(top[:5], 1):
            content.append(f"    {i}. ", style=C["text_dim"])
            content.append(f"{t['context']:<20}", style=C["cyan"])
            content.append(f" ${t['cost_usd']:.2f}", style=C["amber"])
            content.append(f"  ({t['calls']} appels)\n", style=C["text_dim"])

    return Panel(
        content,
        title=f"[bold {C['blue']}]📊 STATISTIQUES D'UTILISATION[/]",
        title_align="left",
        border_style=BORDERS["stats"],
        box=BOX,
        padding=(1, 1),
    )


def render_help_panel() -> Panel:
    content = Text()
    content.append(" COMMANDES DISPONIBLES\n\n", style=f"bold {C['violet_bright']}")

    commands = [
        ("/mail", "Afficher les derniers mails"),
        ("/mail unread", "Emails non lus uniquement"),
        ("/cal today", "Événements d'aujourd'hui"),
        ("/cal week", "Vue hebdomadaire"),
        ("/tasks", "Tâches actives"),
        ("/tasks done <id>", "Marquer une tâche comme faite"),
        ("/run <code>", "Exécuter du Python inline"),
        ("/review <fichier>", "Revue de code"),
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
        ("/telegram_setup", "Configurer Telegram comme interface"),
        ("/help", "Cette aide"),
    ]

    for cmd, desc in commands:
        content.append(f"  {cmd:<22}", style=f"bold {C['emerald']}")
        content.append(f"  {desc}\n", style=C["text_dim"])

    content.append(f"\n [{C['text_muted']}]Sinon, parle-moi en langage naturel ![/]")

    return Panel(
        content,
        title=f"[bold {C['cyan']}]❓ AIDE[/]",
        title_align="left",
        border_style=BORDERS["help"],
        box=BOX,
        padding=(1, 2),
    )


def render_thinking_panel(message: str = "Réflexion en cours", tools_used: list[str] | None = None) -> Panel:
    """Render the ephemeral thinking/reflection panel."""
    content = Text()

    # Animated dots effect (static in render, animation handled by caller)
    content.append(f"  {message}", style=f"italic {C['pink']}")
    content.append(" ···", style=f"bold {C['pink_dim']}")

    if tools_used:
        content.append("\n")
        for tool in tools_used:
            content.append(f"\n  ⚡ ", style=C["amber"])
            content.append(tool, style=C["text_dim"])

    return Panel(
        content,
        title=f"[{C['pink']}]💭 RÉFLEXION[/]",
        title_align="left",
        border_style=BORDERS["thinking"],
        box=BOX,
        padding=(0, 1),
    )
