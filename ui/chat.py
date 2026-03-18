from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from core.conversation import ConversationManager
from core.token_tracker import TokenTracker
from modules.code_runner import PythonCodeRunner
from modules.task_manager import TaskManager
from ui.panels import render_status_bar, render_stats_panel, render_help_panel
from ui.themes import C, S, BORDERS, BOX


def _format_emails_for_registry(emails) -> str:
    """Format emails for tool registry (used by /gmail_setup re-registration)."""
    if not emails:
        return "Aucun email trouvé."
    lines = []
    for email in emails:
        sender = email.sender.split("<")[0].strip()
        unread = "🔵 " if email.is_unread else ""
        lines.append(
            f"{unread}**{sender}** — {email.subject}\n"
            f"   ID: {email.id} | Thread: {email.thread_id}\n"
            f"   {email.snippet[:100]}"
        )
    return "\n\n".join(lines)


def _format_thread_for_registry(emails) -> str:
    """Format thread for tool registry (used by /gmail_setup re-registration)."""
    if not emails:
        return "Thread vide."
    lines = []
    for email in emails:
        lines.append(
            f"--- De: {email.sender} | {email.date} ---\n"
            f"Objet: {email.subject}\n\n{email.body[:1500]}"
        )
    return "\n\n".join(lines)


def _format_email_detail_for_registry(email) -> str:
    """Format a single email detail for tool registry."""
    if not email:
        return "Email introuvable."
    attachments = f"\nPièces jointes: {', '.join(email.attachments)}" if email.attachments else ""
    return (
        f"**De:** {email.sender}\n"
        f"**À:** {email.to}\n"
        f"**Objet:** {email.subject}\n"
        f"**Date:** {email.date}\n"
        f"**ID:** {email.id} | **Thread:** {email.thread_id}\n"
        f"{attachments}\n\n"
        f"{email.body}"
    )


class ChatInterface:
    def __init__(
        self,
        console: Console,
        conversation: ConversationManager,
        token_tracker: TokenTracker,
        code_runner: PythonCodeRunner,
        task_manager: TaskManager,
        services: dict | None = None,
    ):
        self.console = console
        self.conversation = conversation
        self.tracker = token_tracker
        self.code_runner = code_runner
        self.task_manager = task_manager
        self.services = services or {}

    def run(self):
        self.console.print(
            Panel(
                f"[bold {C['violet_bright']}]Que puis-je faire pour toi ?[/]\n[{C['text_dim']}]Tape /help pour voir les commandes disponibles[/]",
                border_style=BORDERS["prompt"],
                box=BOX,
                padding=(1, 2),
            )
        )

        while True:
            try:
                status = render_status_bar(self.tracker)
                self.console.print(status)

                user_input = self.console.input(f"[bold {C['violet_bright']}]›[/] ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ("/quit", "/exit", "/q"):
                    self.console.print(f"[{C['text_dim']}]À bientôt ! 👋[/]")
                    break

                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # Chat with Claude
                response = self.conversation.chat(user_input)

                self.console.print(Panel(
                    Markdown(response),
                    title=f"[bold {C['violet']}]◉ ONDES[/]",
                    title_align="left",
                    border_style=BORDERS["response"],
                    box=BOX,
                    padding=(1, 2),
                ))

            except KeyboardInterrupt:
                self.console.print(f"\n[{C['text_dim']}]Ctrl+C — tape /quit pour quitter[/]")
            except EOFError:
                break

    def _handle_command(self, command: str):
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            self.console.print(render_help_panel())

        elif cmd == "/clear":
            self.conversation.clear_history()
            self.console.print(f"[{C['text_dim']}]Historique vidé.[/]")

        elif cmd == "/stats":
            self.console.print(render_stats_panel(self.tracker))

        elif cmd == "/run":
            if not args:
                self.console.print(f"[{C['red']}]Usage: /run <code python>[/]")
                return
            with self.console.status(f"[bold {C['amber']}]Exécution...[/]"):
                result = self.code_runner.execute(args)
            self.console.print(Panel(
                Markdown(result),
                title=f"[bold {C['blue']}]🐍 Python[/]",
                title_align="left",
                border_style=C["blue"],
                box=BOX,
                padding=(1, 2),
            ))

        elif cmd == "/tasks":
            if args.startswith("done"):
                try:
                    task_id = int(args.split()[1])
                    result = self.task_manager.complete_task(task_id)
                except (IndexError, ValueError):
                    result = "Usage: /tasks done <id>"
                self.console.print(result)
            else:
                with self.console.status(f"[bold {C['amber']}]Chargement...[/]"):
                    result = self.task_manager.get_tasks(status=args if args else "todo")
                self.console.print(Panel(
                    Markdown(result),
                    title=f"[bold {C['emerald']}]✅ Tâches[/]",
                    title_align="left",
                    border_style=BORDERS["task"],
                    box=BOX,
                    padding=(1, 2),
                ))

        elif cmd in ("/mem", "/memory"):
            self._handle_memory(args)

        elif cmd == "/gmail_setup":
            self._handle_gmail_setup()

        elif cmd == "/telegram_setup":
            self._handle_telegram_setup()

        elif cmd in ("/mail", "/cal", "/review", "/search", "/docker", "/gh", "/music", "/auto"):
            # Route these through Claude for natural processing
            natural_queries = {
                "/mail": f"Montre-moi mes emails {args}".strip(),
                "/cal": f"Montre-moi mon calendrier {args}".strip(),
                "/review": f"Fais une revue de code du fichier {args}" if args else "De quel fichier ?",
                "/search": f"Recherche sur le web: {args}" if args else "Que veux-tu chercher ?",
                "/docker": f"Docker: {args}" if args else "Liste mes containers Docker",
                "/gh": f"GitHub: {args}" if args else "Montre mes repos GitHub",
                "/music": f"Musique: {args}" if args else "Quel morceau est en cours ?",
                "/auto": f"Automatisation: {args}" if args else "Liste mes jobs planifiés",
            }
            query = natural_queries.get(cmd, args)
            response = self.conversation.chat(query)
            self.console.print(Panel(
                Markdown(response),
                title=f"[bold {C['violet']}]◉ ONDES[/]",
                title_align="left",
                border_style=BORDERS["response"],
                box=BOX,
                padding=(1, 2),
            ))

        else:
            self.console.print(f"[{C['red']}]Commande inconnue: {cmd}. Tape /help pour l'aide.[/]")

    def _handle_memory(self, args: str):
        """Display memory contents in a rich panel."""
        memory = self.conversation.memory
        sub = args.strip().lower()

        if sub == "facts":
            self._show_memory_facts(memory)
        elif sub == "actions":
            self._show_memory_actions(memory)
        else:
            self._show_memory_full(memory)

    def _show_memory_facts(self, memory):
        facts = memory.get_facts(limit=50)
        if not facts:
            self.console.print(Panel(f"[{C['text_dim']}]Aucun fait mémorisé.[/]", title=f"[bold {C['violet']}]🧠 Mémoire · Faits[/]", title_align="left", border_style=C["violet_dim"], box=BOX))
            return

        # Group by category
        categories: dict[str, list] = {}
        for f in facts:
            categories.setdefault(f["category"], []).append(f)

        content = Text()
        for cat, items in sorted(categories.items()):
            emoji = {"preference": "⚙️", "context": "📌", "person": "👤", "project": "📁"}.get(cat, "📝")
            content.append(f"\n {emoji} {cat.upper()}\n", style=f"bold {C['violet_bright']}")
            for item in items:
                content.append(f"   {item['key']}", style=f"bold {C['text']}")
                content.append(f" → {item['value']}\n", style=C["text_dim"])

        self.console.print(Panel(content, title=f"[bold {C['violet']}]🧠 Mémoire · Faits[/]", title_align="left", border_style=C["violet_dim"], box=BOX, padding=(1, 2)))

    def _show_memory_actions(self, memory):
        actions = memory.get_recent_actions(limit=15)
        if not actions:
            self.console.print(Panel(f"[{C['text_dim']}]Aucune action enregistrée.[/]", title=f"[bold {C['violet']}]🧠 Mémoire · Actions[/]", title_align="left", border_style=C["violet_dim"], box=BOX))
            return

        table = Table(show_header=True, header_style=f"bold {C['violet_bright']}", border_style=C["border"], padding=(0, 1))
        table.add_column("Heure", style=C["text_dim"], width=16)
        table.add_column("Action", style=C["cyan"], width=25)
        table.add_column("Détails", ratio=1, style=C["text"])

        for a in actions:
            ts = a["executed_at"][:16].replace("T", " ")
            desc = a["description"][:60] + "…" if len(a["description"]) > 60 else a["description"]
            table.add_row(ts, a["action_type"], desc)

        self.console.print(Panel(table, title=f"[bold {C['violet']}]🧠 Mémoire · Actions récentes[/]", title_align="left", border_style=C["violet_dim"], box=BOX, padding=(1, 1)))

    def _show_memory_full(self, memory):
        """Show a combined overview: facts + actions + summaries."""
        facts = memory.get_facts(limit=30)
        actions = memory.get_recent_actions(limit=10)
        summaries = memory.get_recent_summaries(limit=3)

        content = Text()

        # ── Facts ──
        content.append(" FAITS MÉMORISÉS", style=f"bold {C['violet_bright']}")
        if facts:
            categories: dict[str, list] = {}
            for f in facts:
                categories.setdefault(f["category"], []).append(f)
            for cat, items in sorted(categories.items()):
                emoji = {"preference": "⚙️", "context": "📌", "person": "👤", "project": "📁"}.get(cat, "📝")
                content.append(f"\n  {emoji} {cat.upper()}\n", style=f"bold {C['cyan']}")
                for item in items:
                    content.append(f"    {item['key']}", style=f"bold {C['text']}")
                    content.append(f" → {item['value']}\n", style=C["text_dim"])
        else:
            content.append(f"\n  [aucun fait]\n", style=C["text_dim"])

        # ── Actions ──
        content.append("\n ACTIONS RÉCENTES", style=f"bold {C['violet_bright']}")
        if actions:
            for a in actions[:10]:
                ts = a["executed_at"][11:16]
                content.append(f"\n  {ts} ", style=C["text_dim"])
                content.append(f"{a['action_type']}", style=C["cyan"])
                desc = a["description"][:50]
                if desc:
                    content.append(f" — {desc}", style=C["text"])
        else:
            content.append(f"\n  [aucune action]", style=C["text_dim"])

        # ── Summaries ──
        if summaries:
            content.append(f"\n\n RÉSUMÉS DE CONVERSATIONS", style=f"bold {C['violet_bright']}")
            for s in summaries:
                content.append(f"\n  {s['date']} ", style=C["text_dim"])
                content.append(f"{s['summary'][:80]}\n", style=C["text"])

        self.console.print(Panel(content, title=f"[bold {C['violet']}]🧠 MÉMOIRE[/]", title_align="left", border_style=C["violet_dim"], box=BOX, padding=(1, 2)))

    def _handle_gmail_setup(self):
        """Interactive Gmail setup/reconfigure."""
        from integrations.gmail.setup import run_reconfigure as gmail_reconfigure

        config = gmail_reconfigure(self.console)

        # Update the live gmail services
        if config:
            try:
                from integrations.gmail.client import GmailClient
                from integrations.gmail.reply_generator import ReplyGenerator

                gmail_client = GmailClient(config["email"], config["app_password"])
                self.services["gmail_client"] = gmail_client

                reply_gen = ReplyGenerator(gmail_client)

                registry = self.services.get("registry")
                if registry:
                    registry.register("gmail_get_emails", lambda filter="all", max_results=10, search_query="": _format_emails_for_registry(gmail_client.get_emails(filter, max_results, search_query)))
                    registry.register("gmail_read_email", lambda email_id: _format_email_detail_for_registry(gmail_client.get_email(email_id)))
                    registry.register("gmail_search", lambda query: _format_emails_for_registry(gmail_client.search(query)))
                    registry.register("gmail_get_thread", lambda thread_id: _format_thread_for_registry(gmail_client.get_email_thread(thread_id)))
                    registry.register("gmail_send_email", lambda to, subject, body: gmail_client.send_email(to, subject, body))
                    if reply_gen:
                        registry.register("gmail_generate_reply", lambda email_id, instructions="", tone="professionnel": reply_gen.generate_reply(email_id, instructions, tone))
                self.console.print("[green]✓ Gmail est maintenant actif pour cette session.[/]\n")
            except Exception as e:
                self.console.print(f"[red]Erreur initialisation Gmail: {e}[/]")
        else:
            self.services["gmail_client"] = None
            registry = self.services.get("registry")
            if registry:
                registry.register("gmail_get_emails", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
                registry.register("gmail_read_email", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
                registry.register("gmail_search", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
                registry.register("gmail_get_thread", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
                registry.register("gmail_send_email", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
                registry.register("gmail_generate_reply", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")

    def _handle_telegram_setup(self):
        """Interactive Telegram setup/reconfigure."""
        from integrations.telegram.setup import run_reconfigure, load_telegram_config

        config = run_reconfigure(self.console)

        if config:
            try:
                from integrations.telegram.client import TelegramInterface
                interface = TelegramInterface(config["bot_token"], config["chat_id"])
                # Wire conversation and start polling
                conversation = self.conversation
                interface.set_conversation(conversation)
                interface.start()
                self.services["telegram_interface"] = interface
                self.console.print("[green]✓ Telegram est maintenant actif — interface démarrée.[/]\n")
            except Exception as e:
                self.console.print(f"[red]Erreur initialisation Telegram: {e}[/]")
        else:
            self.services["telegram_interface"] = None
