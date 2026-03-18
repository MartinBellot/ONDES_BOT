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
from integrations.apple_music.client import AppleMusicClient
from integrations.docker.client import DockerClient
from integrations.github.client import GitHubClient
from integrations.web.scraper import WebScraper
from integrations.web.search import WebSearcher
from modules.automation import AutomationManager
from modules.code_runner import PythonCodeRunner
from modules.code_reviewer import CodeReviewer
from modules.file_manager import FileManager
from modules.image_processor import ImageProcessor
from modules.task_manager import TaskManager
from ui.chat import ChatInterface
from ui.dashboard import Dashboard


def setup_services(settings: Settings, console: Console):
    """Initialize all services and wire them together."""
    from ui.themes import C

    db_path = settings.get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Core
    token_tracker = TokenTracker(db_path, settings.monthly_budget_usd)
    claude_client = ClaudeClient(settings, token_tracker)
    memory = Memory(db_path)

    # Modules
    file_manager = FileManager()
    code_runner = PythonCodeRunner(timeout=settings.code_runner_timeout)
    code_reviewer = CodeReviewer(file_manager)
    task_manager = TaskManager(db_path)
    image_processor = ImageProcessor()
    web_searcher = WebSearcher()
    web_scraper = WebScraper()
    calendar_client = AppleCalendarClient()
    music_client = AppleMusicClient()
    docker_client = DockerClient()
    github_client = GitHubClient()
    automation = AutomationManager(db_path, notify_callback=_system_notify)

    # Gmail (optional — config interactive via setup wizard)
    gmail_client = None
    reply_generator = None
    from integrations.gmail.setup import load_gmail_config, run_setup_wizard as run_gmail_wizard
    gmail_cfg = load_gmail_config()
    if gmail_cfg:
        try:
            from integrations.gmail.client import GmailClient
            from integrations.gmail.reply_generator import ReplyGenerator

            gmail_client = GmailClient(gmail_cfg["email"], gmail_cfg["app_password"])
            reply_generator = ReplyGenerator(gmail_client)
            console.print(f"[{C['emerald']}]✓[/] [{C['text_dim']}]Gmail connecté ({gmail_cfg.get('email', '?')})[/]")
        except Exception as e:
            console.print(f"[{C['amber']}]⚠ Gmail: {e}[/]")
    else:
        console.print(f"[{C['text_muted']}]○ Gmail non configuré — tape [bold]/gmail_setup[/bold] dans le chat[/]")

    # Telegram interface (optional — config interactive via setup wizard)
    telegram_interface = None
    from integrations.telegram.setup import load_telegram_config, run_setup_wizard
    tg_config = load_telegram_config()
    if tg_config:
        try:
            from integrations.telegram.client import TelegramInterface
            telegram_interface = TelegramInterface(tg_config["bot_token"], tg_config["chat_id"])
            console.print(f"[{C['emerald']}]✓[/] [{C['text_dim']}]Telegram connecté (@{tg_config.get('bot_username', '?')})[/]")
        except Exception as e:
            console.print(f"[{C['amber']}]⚠ Telegram: {e}[/]")
    else:
        console.print(f"[{C['text_muted']}]○ Telegram non configuré — tape [bold]/telegram_setup[/bold] dans le chat[/]")

    # Tool Registry — wire all handlers
    registry = ToolRegistry()

    # Gmail tools
    if gmail_client:
        registry.register("gmail_get_emails", lambda filter="all", max_results=10, search_query="": _format_emails(gmail_client.get_emails(filter, max_results, search_query)))
        registry.register("gmail_read_email", lambda email_id: _format_email_detail(gmail_client.get_email(email_id)))
        registry.register("gmail_search", lambda query: _format_emails(gmail_client.search(query)))
        registry.register("gmail_get_thread", lambda thread_id: _format_thread(gmail_client.get_email_thread(thread_id)))
        registry.register("gmail_send_email", lambda to, subject, body: gmail_client.send_email(to, subject, body))
    else:
        registry.register("gmail_get_emails", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
        registry.register("gmail_read_email", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
        registry.register("gmail_search", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
        registry.register("gmail_get_thread", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")
        registry.register("gmail_send_email", lambda **kwargs: "Gmail non configuré. Tape /gmail_setup pour le configurer.")

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

    # Memory tools (with conversation reference for cache invalidation)
    _conversation_ref = [None]  # Will be set after ConversationManager is created

    def _save_fact_and_invalidate(category, key, value):
        memory.save_fact(category, key, value)
        if _conversation_ref[0]:
            _conversation_ref[0].invalidate_facts_cache()
        return f"Fait mémorisé: [{category}] {key} = {value}"

    registry.register("memory_save_fact", _save_fact_and_invalidate)
    registry.register("memory_get_facts", lambda category=None: memory.get_relevant_facts())

    # System tools
    registry.register("system_notify", lambda message, title="ONDES BOT": _system_notify(title, message))
    registry.register("system_open_url", lambda url: _system_open_url(url))
    registry.register("system_clipboard_set", lambda text: _system_clipboard(text))

    # Docker tools
    if docker_client.is_available():
        registry.register("docker_list_containers", lambda all=True: docker_client.list_containers(all))
        registry.register("docker_run", lambda image, name=None, ports=None, volumes=None, env=None, restart_policy="unless-stopped", extra_args="": docker_client.run_container(image, name, ports, volumes, env, True, restart_policy, extra_args))
        registry.register("docker_start", lambda name_or_id: docker_client.start_container(name_or_id))
        registry.register("docker_stop", lambda name_or_id: docker_client.stop_container(name_or_id))
        registry.register("docker_restart", lambda name_or_id: docker_client.restart_container(name_or_id))
        registry.register("docker_remove", lambda name_or_id, force=False: docker_client.remove_container(name_or_id, force))
        registry.register("docker_logs", lambda name_or_id, tail=50: docker_client.container_logs(name_or_id, tail))
        registry.register("docker_stats", lambda name_or_id=None: docker_client.container_stats(name_or_id))
        registry.register("docker_exec", lambda name_or_id, command: docker_client.exec_in_container(name_or_id, command))
        registry.register("docker_list_images", lambda: docker_client.list_images())
        registry.register("docker_pull", lambda image: docker_client.pull_image(image))
        registry.register("docker_list_volumes", lambda: docker_client.list_volumes())
        registry.register("docker_list_networks", lambda: docker_client.list_networks())
        registry.register("docker_compose_up", lambda compose_file, project_name=None: docker_client.compose_up(compose_file, project_name))
        registry.register("docker_compose_down", lambda compose_file, project_name=None, remove_volumes=False: docker_client.compose_down(compose_file, project_name, remove_volumes))
        registry.register("docker_compose_status", lambda compose_file, project_name=None: docker_client.compose_status(compose_file, project_name))
        registry.register("docker_compose_logs", lambda compose_file, service=None, tail=50: docker_client.compose_logs(compose_file, service, tail))
        registry.register("docker_generate_compose", lambda template, output_dir, **kwargs: docker_client.generate_compose_file(template, output_dir, **kwargs))
        registry.register("docker_templates", lambda: docker_client.get_available_templates())
        registry.register("docker_system_info", lambda: docker_client.system_info())
        registry.register("docker_system_prune", lambda all=False: docker_client.system_prune(all))
        console.print(f"[{C['emerald']}]✓[/] [{C['text_dim']}]Docker connecté[/]")
    else:
        console.print(f"[{C['text_muted']}]○ Docker non disponible (daemon non lancé ou non installé)[/]")
        _docker_unavailable = lambda **kwargs: "Docker n'est pas disponible. Lance Docker Desktop ou installe Docker."
        for tool_name in [
            "docker_list_containers", "docker_run", "docker_start", "docker_stop",
            "docker_restart", "docker_remove", "docker_logs", "docker_stats",
            "docker_exec", "docker_list_images", "docker_pull", "docker_list_volumes",
            "docker_list_networks", "docker_compose_up", "docker_compose_down",
            "docker_compose_status", "docker_compose_logs", "docker_generate_compose",
            "docker_templates", "docker_system_info", "docker_system_prune",
        ]:
            registry.register(tool_name, _docker_unavailable)

    # GitHub tools
    if github_client.is_available():
        registry.register("github_list_repos", lambda limit=10, sort="updated": github_client.list_repos(limit, sort))
        registry.register("github_repo_info", lambda repo: github_client.repo_info(repo))
        registry.register("github_list_issues", lambda repo=None, state="open", limit=10: github_client.list_issues(repo, state, limit))
        registry.register("github_create_issue", lambda title, body="", repo=None, labels="": github_client.create_issue(title, body, repo, labels))
        registry.register("github_view_issue", lambda issue_number, repo=None: github_client.view_issue(issue_number, repo))
        registry.register("github_close_issue", lambda issue_number, repo=None: github_client.close_issue(issue_number, repo))
        registry.register("github_list_prs", lambda repo=None, state="open", limit=10: github_client.list_prs(repo, state, limit))
        registry.register("github_create_pr", lambda title, body="", base="main", repo=None: github_client.create_pr(title, body, base, repo))
        registry.register("github_view_pr", lambda pr_number, repo=None: github_client.view_pr(pr_number, repo))
        registry.register("github_merge_pr", lambda pr_number, method="squash", repo=None: github_client.merge_pr(pr_number, method, repo))
        registry.register("github_actions_runs", lambda repo=None, limit=5: github_client.list_runs(repo, limit))
        registry.register("github_notifications", lambda limit=10: github_client.notifications(limit))
        registry.register("github_git_status", lambda path=None: github_client.git_status(path))
        registry.register("github_git_diff", lambda path=None, staged=False: github_client.git_diff(path, staged))
        console.print(f"[{C['emerald']}]✓[/] [{C['text_dim']}]GitHub connecté (gh CLI)[/]")
    else:
        console.print(f"[{C['text_muted']}]○ GitHub CLI non disponible — installe avec: brew install gh && gh auth login[/]")
        _gh_unavailable = lambda **kwargs: "GitHub CLI (gh) non disponible. Installe avec: brew install gh && gh auth login"
        for tool_name in [
            "github_list_repos", "github_repo_info", "github_list_issues",
            "github_create_issue", "github_view_issue", "github_close_issue",
            "github_list_prs", "github_create_pr", "github_view_pr",
            "github_merge_pr", "github_actions_runs", "github_notifications",
            "github_git_status", "github_git_diff",
        ]:
            registry.register(tool_name, _gh_unavailable)

    # Apple Music tools
    registry.register("music_play", lambda: music_client.play())
    registry.register("music_pause", lambda: music_client.pause())
    registry.register("music_next", lambda: music_client.next_track())
    registry.register("music_previous", lambda: music_client.previous_track())
    registry.register("music_now_playing", lambda: music_client.now_playing())
    registry.register("music_volume", lambda level: music_client.set_volume(level))
    registry.register("music_search_play", lambda query: music_client.search_and_play(query))
    registry.register("music_playlists", lambda: music_client.list_playlists())
    registry.register("music_play_playlist", lambda name: music_client.play_playlist(name))
    registry.register("music_shuffle", lambda enabled: music_client.set_shuffle(enabled))
    console.print(f"[{C['emerald']}]✓[/] [{C['text_dim']}]Apple Music prêt[/]")

    # Automation tools
    automation.start()
    registry.register("automation_add_job", lambda name, schedule, action, action_args=None: automation.add_recurring_job(name, schedule, action, action_args))
    registry.register("automation_remove_job", lambda job_id: automation.remove_job(job_id))
    registry.register("automation_list_jobs", lambda: automation.list_jobs())
    registry.register("automation_add_reminder", lambda message, remind_at: automation.add_reminder(message, remind_at))
    registry.register("automation_morning_briefing", lambda time="08:00": automation.setup_morning_briefing(time))
    console.print(f"[{C['emerald']}]✓[/] [{C['text_dim']}]Automatisation démarrée[/]")

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
        "music_client": music_client,
        "docker_client": docker_client,
        "github_client": github_client,
        "automation": automation,
        "_conversation_ref": _conversation_ref,
        "gmail_client": gmail_client,
        "telegram_interface": telegram_interface,
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


def _format_email_detail(email) -> str:
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

    from ui.themes import C, BORDERS, BOX

    # Show splash
    dashboard = Dashboard(console)
    dashboard.show_splash()

    # Model selection
    console.print()
    console.print(f"  [bold {C['violet_bright']}]Choisis ton modèle Claude :[/]")
    console.print(f"    [bold {C['text']}]1[/]  claude-sonnet-4-6  [{C['text_dim']}](dernier, août 2025)[/]")
    console.print(f"    [bold {C['text']}]2[/]  claude-sonnet-4-5  [{C['text_dim']}](stable, juin 2025)[/]")
    choice = Prompt.ask(f"\n  [bold {C['violet_bright']}]Modèle[/]", choices=["1", "2"], default="1")
    model_map = {"1": "claude-sonnet-4-6", "2": "claude-sonnet-4-5"}
    settings.claude_model = model_map[choice]
    console.print(f"  [{C['emerald']}]✓[/] Modèle : [bold {C['text']}]{settings.claude_model}[/]\n")

    # Init services
    console.print(f"[bold {C['violet']}]Initialisation des services...[/]\n")
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

    # Wire the conversation reference for facts cache invalidation
    services["_conversation_ref"][0] = conversation

    # Start Telegram interface if configured
    tg_interface = services.get("telegram_interface")
    if tg_interface:
        tg_interface.set_conversation(conversation)
        tg_interface.start()
        console.print(f"[{C['emerald']}]✓[/] [{C['text_dim']}]Interface Telegram démarrée (polling en arrière-plan)[/]")

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
