from datetime import datetime
import locale

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule

from ui.themes import SPLASH_ART, C, S, BORDERS, BOX


class Dashboard:
    def __init__(self, console: Console):
        self.console = console

    def show_splash(self):
        self.console.print(SPLASH_ART)

    def show_dashboard(
        self,
        email_summary: str = "",
        calendar_summary: str = "",
        task_summary: str = "",
    ):
        # ── Header bar ──
        now = datetime.now()
        try:
            locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
        except locale.Error:
            pass
        date_str = now.strftime("%A %d %B %Y, %H:%M").capitalize()

        header = Text()
        header.append("  ◉ ONDES BOT  ", style=f"bold {C['violet_bright']}")
        header.append("│", style=C["border"])
        header.append(f"  Claude Sonnet  ·  {date_str}  ", style=C["text_dim"])

        self.console.print(Panel(
            header,
            box=BOX,
            border_style=BORDERS["header"],
            padding=(0, 1),
        ))

        # ── Dashboard panels (auto-height via Table.grid) ──
        email_panel = Panel(
            email_summary or f"[{C['text_dim']}]Gmail non configuré[/]",
            title=f"[bold {C['cyan']}]📧 EMAILS[/]",
            title_align="left",
            border_style=BORDERS["email"],
            box=BOX,
            padding=(1, 1),
            expand=True,
        )

        calendar_panel = Panel(
            calendar_summary or f"[{C['text_dim']}]Aucun événement[/]",
            title=f"[bold {C['violet']}]📅 AUJOURD'HUI[/]",
            title_align="left",
            border_style=BORDERS["calendar"],
            box=BOX,
            padding=(1, 1),
            expand=True,
        )

        task_panel = Panel(
            task_summary or f"[{C['text_dim']}]Aucune tâche[/]",
            title=f"[bold {C['emerald']}]✅ TÂCHES DU JOUR[/]",
            title_align="left",
            border_style=BORDERS["task"],
            box=BOX,
            padding=(1, 1),
            expand=True,
        )

        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_row(email_panel, calendar_panel, task_panel)

        self.console.print(grid)

    def show_service_status(self, statuses: list[tuple[str, bool]]):
        """Show a compact service status line."""
        parts = Text()
        for i, (name, active) in enumerate(statuses):
            if i > 0:
                parts.append("  ·  ", style=C["border"])
            icon = "✓" if active else "○"
            style = C["emerald"] if active else C["text_muted"]
            parts.append(f"{icon} {name}", style=style)

        self.console.print(parts)
        self.console.print()

    def get_email_summary(self, gmail_client) -> str:
        try:
            emails = gmail_client.get_unread_emails(max_results=5)
            if not emails:
                return f"[{C['text_dim']}]Pas de nouveaux emails[/]"
            lines = [f"[bold {C['cyan']}]{len(emails)}[/] [{C['text']}]non lus[/]\n"]
            for email in emails[:5]:
                sender = email.sender.split("<")[0].strip()
                lines.append(f"[{C['text_dim']}]›[/] [{C['text']}]{sender}:[/] [{C['text_dim']}]{email.subject[:30]}[/]")
            return "\n".join(lines)
        except Exception:
            return f"[{C['text_dim']}]Gmail non connecté[/]"

    def get_calendar_summary(self, calendar_client) -> str:
        try:
            events = calendar_client.get_events_today()
            if not events:
                return f"[{C['text_dim']}]Journée libre ![/]"
            lines = []
            for event in events:
                time_str = event.start.strftime("%H:%M")
                lines.append(f"[{C['violet_bright']}]{time_str}[/] [{C['text_dim']}]—[/] [{C['text']}]{event.title}[/]")
            return "\n".join(lines)
        except Exception:
            return f"[{C['text_dim']}]Erreur calendrier[/]"

    def get_task_summary(self, task_manager) -> str:
        try:
            result = task_manager.get_today()
            return result
        except Exception:
            return f"[{C['text_dim']}]Aucune tâche[/]"
