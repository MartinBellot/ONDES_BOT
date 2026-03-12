import asyncio
import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from config.settings import Settings
from core.claude_client import ClaudeClient
from core.conversation import ConversationManager
from core.memory import Memory
from core.token_tracker import TokenTracker
from core.tool_registry import ToolRegistry
from integrations.apple_calendar.client import AppleCalendarClient
from integrations.web.scraper import WebScraper
from integrations.web.search import WebSearcher
from modules.code_runner import PythonCodeRunner
from modules.code_reviewer import CodeReviewer
from modules.file_manager import FileManager
from modules.image_processor import ImageProcessor
from modules.task_manager import TaskManager
from ui.chat import ChatInterface
from ui.dashboard import Dashboard


def setup_services(settings: Settings, console: Console):
    """Initialize all services and wire them together."""
    db_path = settings.get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Core
    token_tracker = TokenTracker(db_path, settings.monthly_budget_usd)
    claude_client = ClaudeClient(settings, token_tracker)
    memory = Memory(db_path)

    # Modules
    file_manager = FileManager()
    code_runner = PythonCodeRunner(timeout=settings.code_runner_timeout)
    code_reviewer = CodeReviewer(claude_client, file_manager)
    task_manager = TaskManager(db_path)
    image_processor = ImageProcessor()
    web_searcher = WebSearcher()
    web_scraper = WebScraper()
    calendar_client = AppleCalendarClient()

    # Gmail (optional — config interactive via setup wizard)
    gmail_client = None
    reply_generator = None
    from integrations.gmail.setup import load_gmail_config, run_setup_wizard as run_gmail_wizard
    gmail_cfg = load_gmail_config()
    if gmail_cfg:
        try:
            from integrations.gmail.auth import get_gmail_service
            from integrations.gmail.client import GmailClient
            from integrations.gmail.reply_generator import ReplyGenerator

            service = get_gmail_service(gmail_cfg["credentials_path"], gmail_cfg["token_path"])
            gmail_client = GmailClient(service)
            reply_generator = ReplyGenerator(claude_client, gmail_client)
            console.print(f"[green]✓[/] Gmail connecté ({gmail_cfg.get('email', '?')})")
        except Exception as e:
            console.print(f"[yellow]⚠ Gmail: {e}[/]")
    else:
        console.print("[dim]○ Gmail non configuré — tape [bold]/gmail_setup[/bold] dans le chat[/]")

    # Telegram (optional — config interactive via setup wizard)
    telegram_client = None
    from integrations.telegram.setup import load_telegram_config, run_setup_wizard
    tg_config = load_telegram_config()
    if tg_config:
        try:
            from integrations.telegram.client import TelegramClient
            telegram_client = TelegramClient(tg_config["bot_token"], tg_config["chat_id"])
            console.print(f"[green]✓[/] Telegram connecté (@{tg_config.get('bot_username', '?')})")
        except Exception as e:
            console.print(f"[yellow]⚠ Telegram: {e}[/]")
    else:
        console.print("[dim]○ Telegram non configuré — tape [bold]/telegram_setup[/bold] dans le chat[/]")

    # Tool Registry — wire all handlers
    registry = ToolRegistry()

    # Gmail tools
    if gmail_client:
        registry.register("gmail_get_emails", lambda filter="all", max_results=10, search_query="": _format_emails(gmail_client.get_emails(filter, max_results, search_query)))
        registry.register("gmail_search", lambda query: _format_emails(gmail_client.search(query)))
        registry.register("gmail_get_thread", lambda thread_id: _format_thread(gmail_client.get_email_thread(thread_id)))
    else:
        registry.register("gmail_get_emails", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
        registry.register("gmail_search", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
        registry.register("gmail_get_thread", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")

    if reply_generator:
        registry.register("gmail_generate_reply", lambda email_id, instructions="", tone="professionnel": reply_generator.generate_reply(email_id, instructions, tone))
    else:
        registry.register("gmail_generate_reply", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")

    # Calendar tools
    registry.register("calendar_get_events", lambda period="today", date=None: _format_calendar_events(calendar_client.get_events(period, date)))
    registry.register("calendar_create_event", lambda title, start_datetime, end_datetime, location="", notes="", calendar="Calendrier": calendar_client.create_event(title, start_datetime, end_datetime, location, notes, calendar))
    registry.register("calendar_find_free_slots", lambda date=None, duration_minutes=60: calendar_client.find_free_slots(date, duration_minutes))
    registry.register("calendar_get_week_summary", lambda: calendar_client.get_week_summary())

    # File tools
    registry.register("file_read", lambda path: file_manager.read_file(path))
    registry.register("file_write", lambda path, content, mode="w": file_manager.write_file(path, content, mode))
    registry.register("file_list_directory", lambda path, pattern="*": file_manager.list_directory(path, pattern))
    registry.register("file_search_content", lambda directory, query, extension="": file_manager.search_content(directory, query, extension))
    registry.register("file_get_info", lambda path: file_manager.get_info(path))

    # Web tools
    registry.register("web_search", lambda query, max_results=5: web_searcher.search(query, max_results))
    registry.register("web_get_page", lambda url: web_scraper.get_page_content(url))
    registry.register("web_search_news", lambda query, max_results=5: web_searcher.search_news(query, max_results))

    # Code tools
    registry.register("code_execute_python", lambda code, input_data="": code_runner.execute(code, input_data))
    registry.register("code_review_file", lambda file_path: code_reviewer.review_file(file_path))
    registry.register("code_review_snippet", lambda code, language="python": code_reviewer.review_snippet(code, language))
    registry.register("code_explain", lambda code, language="python": code_reviewer.explain_code(code, language))
    registry.register("code_suggest_refactor", lambda file_path: code_reviewer.suggest_refactor(file_path))

    # Image tools
    registry.register("image_convert", lambda input_path, output_format, output_path=None: image_processor.convert(input_path, output_format, output_path))
    registry.register("image_resize", lambda input_path, width, height=None, maintain_ratio=True: image_processor.resize(input_path, width, height, maintain_ratio))
    registry.register("image_compress", lambda input_path, quality=85: image_processor.compress(input_path, quality))
    registry.register("image_get_info", lambda image_path: image_processor.get_info(image_path))
    registry.register("image_batch_convert", lambda directory, from_format, to_format: image_processor.batch_convert(directory, from_format, to_format))

    # Task tools
    registry.register("task_create", lambda title, description="", priority="medium", due_date=None, project=None, tags=None: task_manager.create_task(title, description, priority, due_date, project, tags))
    registry.register("task_list", lambda status="todo", priority=None, project=None: task_manager.get_tasks(status, priority, project))
    registry.register("task_complete", lambda task_id: task_manager.complete_task(task_id))
    registry.register("task_update", lambda task_id, **kwargs: task_manager.update_task(task_id, **kwargs))
    registry.register("task_get_today", lambda: task_manager.get_today())
    registry.register("task_add_reminder", lambda task_id, remind_at: task_manager.add_reminder(task_id, remind_at))

    # Telegram tools
    if telegram_client:
        registry.register("telegram_send", lambda text, chat_id=None: asyncio.run(telegram_client.send_message(text, chat_id)))
        registry.register("telegram_get_messages", lambda limit=20: asyncio.run(_format_telegram(telegram_client, limit)))
    else:
        registry.register("telegram_send", lambda **kwargs: "Telegram non configuré.")
        registry.register("telegram_get_messages", lambda **kwargs: "Telegram non configuré.")

    # Memory tools
    registry.register("memory_save_fact", lambda category, key, value: (memory.save_fact(category, key, value), f"Fait mémorisé: [{category}] {key} = {value}")[1])
    registry.register("memory_get_facts", lambda category=None: memory.get_relevant_facts())

    # System tools
    registry.register("system_notify", lambda message, title="NIETZ BOT": _system_notify(title, message))
    registry.register("system_open_url", lambda url: _system_open_url(url))
    registry.register("system_clipboard_set", lambda text: _system_clipboard(text))

    return {
        "token_tracker": token_tracker,
        "claude_client": claude_client,
        "memory": memory,
        "registry": registry,
        "file_manager": file_manager,
        "code_runner": code_runner,
        "code_reviewer": code_reviewer,
        "task_manager": task_manager,
        "image_processor": image_processor,
        "web_searcher": web_searcher,
        "web_scraper": web_scraper,
        "calendar_client": calendar_client,
        "gmail_client": gmail_client,
        "telegram_client": telegram_client,
    }


# ─── Helper formatters ───


def _format_emails(emails) -> str:
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


def _format_thread(emails) -> str:
    if not emails:
        return "Thread vide."
    lines = []
    for email in emails:
        lines.append(
            f"--- De: {email.sender} | {email.date} ---\n"
            f"Objet: {email.subject}\n\n{email.body[:1500]}"
        )
    return "\n\n".join(lines)


def _format_calendar_events(events) -> str:
    if not events:
        return "Aucun événement trouvé."
    lines = []
    for event in events:
        time_str = f"{event.start.strftime('%H:%M')}-{event.end.strftime('%H:%M')}"
        loc = f" @ {event.location}" if event.location else ""
        lines.append(f"  • {time_str} — {event.title}{loc}")
    return "\n".join(lines)


async def _format_telegram(telegram_client, limit: int) -> str:
    messages = await telegram_client.get_recent_messages(limit)
    return telegram_client.format_messages(messages)


def _system_notify(title: str, message: str) -> str:
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"',
        ], timeout=5)
        return f"Notification envoyée: {title} — {message}"
    except Exception as e:
        return f"Erreur notification: {e}"


def _system_open_url(url: str) -> str:
    try:
        subprocess.run(["open", url], timeout=5)
        return f"URL ouverte: {url}"
    except Exception as e:
        return f"Erreur: {e}"


def _system_clipboard(text: str) -> str:
    try:
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(text.encode("utf-8"))
        return f"Texte copié dans le presse-papier ({len(text)} caractères)"
    except Exception as e:
        return f"Erreur clipboard: {e}"


def main():
    console = Console()

    # Load settings
    try:
        settings = Settings()
    except Exception as e:
        console.print(f"[red]Erreur de configuration: {e}[/]")
        console.print("[dim]Créez un fichier .env à partir de .env.example[/]")
        return

    # Show splash
    dashboard = Dashboard(console)
    dashboard.show_splash()

    # Model selection
    console.print()
    console.print("  [bold cyan]Choisis ton modèle Claude :[/]")
    console.print("    [bold]1[/]  claude-sonnet-4-6  [dim](dernier, août 2025)[/]")
    console.print("    [bold]2[/]  claude-sonnet-4-5  [dim](stable, juin 2025)[/]")
    choice = Prompt.ask("\n  [bold]Modèle[/]", choices=["1", "2"], default="1")
    model_map = {"1": "claude-sonnet-4-6", "2": "claude-sonnet-4-5"}
    settings.claude_model = model_map[choice]
    console.print(f"  [green]✓[/] Modèle : [bold]{settings.claude_model}[/]\n")

    # Init services
    console.print("[bold]Initialisation des services...[/]\n")
    services = setup_services(settings, console)
    console.print()

    # Show dashboard
    email_summary = dashboard.get_email_summary(services["gmail_client"]) if services["gmail_client"] else ""
    calendar_summary = dashboard.get_calendar_summary(services["calendar_client"])
    task_summary = dashboard.get_task_summary(services["task_manager"])
    dashboard.show_dashboard(email_summary, calendar_summary, task_summary)

    # Create conversation manager
    conversation = ConversationManager(
        claude_client=services["claude_client"],
        tool_registry=services["registry"],
        memory=services["memory"],
        console=console,
    )

    # Start chat loop
    chat = ChatInterface(
        console=console,
        conversation=conversation,
        token_tracker=services["token_tracker"],
        code_runner=services["code_runner"],
        task_manager=services["task_manager"],
        services=services,
    )
    chat.run()


if __name__ == "__main__":
    main()
