from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ui.themes import SPLASH_ART


class Dashboard:
    def __init__(self, console: Console):
        self.console = console

    def show_splash(self):
        self.console.print(SPLASH_ART)
        self.console.print()

    def show_dashboard(
        self,
        email_summary: str = "",
        calendar_summary: str = "",
        task_summary: str = "",
    ):
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", size=12),
        )

        # Header
        now = datetime.now().strftime("%A %d %B %Y, %H:%M")
        header = Text()
        header.append("  ONDES BOT  ", style="bold cyan on black")
        header.append(f"  ·  Claude Sonnet  ·  {now}  ", style="dim")
        layout["header"].update(Panel(header, style="bold"))

        # Body: 3 columns
        layout["body"].split_row(
            Layout(name="emails"),
            Layout(name="calendar"),
            Layout(name="tasks"),
        )

        layout["emails"].update(Panel(
            email_summary or "[dim]Gmail non configuré[/]",
            title="[bold]📧 EMAILS[/]",
            border_style="cyan",
        ))

        layout["calendar"].update(Panel(
            calendar_summary or "[dim]Aucun événement[/]",
            title="[bold]📅 AUJOURD'HUI[/]",
            border_style="bright_blue",
        ))

        layout["tasks"].update(Panel(
            task_summary or "[dim]Aucune tâche[/]",
            title="[bold]✅ TÂCHES DU JOUR[/]",
            border_style="green",
        ))

        self.console.print(layout)
        self.console.print()

    def get_email_summary(self, gmail_client) -> str:
        try:
            emails = gmail_client.get_unread_emails(max_results=5)
            if not emails:
                return "Pas de nouveaux emails"
            lines = [f"Non lus: {len(emails)}\n"]
            for email in emails[:5]:
                sender = email.sender.split("<")[0].strip()
                lines.append(f"› {sender}: {email.subject[:30]}")
            return "\n".join(lines)
        except Exception:
            return "[dim]Gmail non connecté[/]"

    def get_calendar_summary(self, calendar_client) -> str:
        try:
            events = calendar_client.get_events_today()
            if not events:
                return "Journée libre !"
            lines = []
            for event in events:
                time_str = event.start.strftime("%H:%M")
                lines.append(f"{time_str} — {event.title}")
            return "\n".join(lines)
        except Exception:
            return "[dim]Erreur calendrier[/]"

    def get_task_summary(self, task_manager) -> str:
        try:
            result = task_manager.get_today()
            return result
        except Exception:
            return "[dim]Aucune tâche[/]"
