"""Automation module — scheduled tasks, watchers, morning briefing."""

import json
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger


@dataclass
class ScheduledJob:
    id: str
    name: str
    schedule: str
    action: str
    enabled: bool = True
    last_run: str | None = None
    next_run: str | None = None


class AutomationManager:
    """Manage scheduled tasks, recurring actions, and automation rules."""

    def __init__(self, db_path: Path, notify_callback=None):
        self.db_path = db_path
        self._notify = notify_callback  # function(title, message) for macOS notif
        self.scheduler = BackgroundScheduler(daemon=True)
        self._results: dict[str, str] = {}  # job_id -> last result
        self._custom_jobs: dict[str, dict] = {}  # job_id -> job metadata
        self._init_db()

    def _init_db(self):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    action TEXT NOT NULL,
                    action_args TEXT DEFAULT '{}',
                    enabled INTEGER DEFAULT 1,
                    last_run TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

    def start(self):
        """Start the scheduler and reload persisted jobs."""
        if not self.scheduler.running:
            self.scheduler.start()
        self._reload_jobs()

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    # ═══════════════════════════ JOB MANAGEMENT ═══════════════════════════

    def add_recurring_job(
        self,
        name: str,
        schedule: str,
        action: str,
        action_args: dict | None = None,
    ) -> str:
        """Add a recurring job.

        schedule format:
        - "every 5m"  → every 5 minutes
        - "every 1h"  → every hour
        - "every day at 08:00" → daily at 8am
        - "every monday at 09:00" → weekly
        - cron string: "0 8 * * *" → 8am daily
        """
        import sqlite3

        job_id = f"job_{name.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"

        trigger = self._parse_schedule(schedule)
        if trigger is None:
            return f"❌ Format de planning invalide: '{schedule}'. Exemples: 'every 5m', 'every day at 08:00', '0 8 * * *'"

        # Store metadata
        self._custom_jobs[job_id] = {
            "name": name,
            "schedule": schedule,
            "action": action,
            "action_args": action_args or {},
        }

        # Add to scheduler (the actual execution is handled externally via polling)
        self.scheduler.add_job(
            self._execute_job,
            trigger=trigger,
            id=job_id,
            args=[job_id, action, action_args or {}],
            replace_existing=True,
        )

        # Persist to DB
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scheduled_jobs (id, name, schedule, action, action_args, enabled) VALUES (?, ?, ?, ?, ?, 1)",
                (job_id, name, schedule, action, json.dumps(action_args or {})),
            )

        next_run = self.scheduler.get_job(job_id)
        next_str = str(next_run.next_run_time.strftime("%d/%m %H:%M")) if next_run and next_run.next_run_time else "?"

        return (
            f"✅ Job planifié: **{name}**\n"
            f"   ID: {job_id}\n"
            f"   Planning: {schedule}\n"
            f"   Action: {action}\n"
            f"   Prochaine exécution: {next_str}"
        )

    def remove_job(self, job_id: str) -> str:
        """Remove a scheduled job."""
        import sqlite3
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

        self._custom_jobs.pop(job_id, None)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))

        return f"🗑️ Job **{job_id}** supprimé."

    def list_jobs(self) -> str:
        """List all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        if not jobs:
            return "Aucun job planifié."

        lines = []
        for job in jobs:
            meta = self._custom_jobs.get(job.id, {})
            name = meta.get("name", job.id)
            schedule = meta.get("schedule", "?")
            next_run = job.next_run_time.strftime("%d/%m %H:%M") if job.next_run_time else "—"
            last_result = self._results.get(job.id, "—")
            lines.append(
                f"⏰ **{name}**\n"
                f"   ID: {job.id}\n"
                f"   Planning: {schedule}\n"
                f"   Prochain: {next_run}\n"
                f"   Dernier résultat: {last_result[:100]}"
            )

        return "\n\n".join(lines)

    def pause_job(self, job_id: str) -> str:
        """Pause a scheduled job."""
        try:
            self.scheduler.pause_job(job_id)
            return f"⏸️ Job **{job_id}** mis en pause."
        except Exception as e:
            return f"Erreur: {e}"

    def resume_job(self, job_id: str) -> str:
        """Resume a paused job."""
        try:
            self.scheduler.resume_job(job_id)
            return f"▶️ Job **{job_id}** repris."
        except Exception as e:
            return f"Erreur: {e}"

    # ═══════════════════════════ ONE-OFF REMINDERS ═══════════════════════════

    def add_reminder(self, message: str, remind_at: str) -> str:
        """Set a one-time reminder.

        remind_at: ISO 8601 datetime or relative like "in 30m", "in 2h", "in 1d"
        """
        import sqlite3

        run_time = self._parse_reminder_time(remind_at)
        if run_time is None:
            return f"❌ Format de temps invalide: '{remind_at}'. Exemples: 'in 30m', 'in 2h', '2025-12-25T10:00:00'"

        if run_time <= datetime.now():
            return "❌ Le rappel doit être dans le futur."

        job_id = f"reminder_{int(datetime.now().timestamp())}"

        self.scheduler.add_job(
            self._send_reminder,
            trigger=DateTrigger(run_date=run_time),
            id=job_id,
            args=[message],
        )

        self._custom_jobs[job_id] = {
            "name": f"Rappel: {message[:30]}",
            "schedule": f"once at {run_time.strftime('%d/%m %H:%M')}",
            "action": "reminder",
        }

        # Persist to DB so reminder survives restart
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scheduled_jobs (id, name, schedule, action, action_args, enabled) VALUES (?, ?, ?, ?, ?, 1)",
                (job_id, f"Rappel: {message[:50]}", run_time.isoformat(), "reminder", json.dumps({"message": message})),
            )

        return (
            f"⏰ Rappel planifié: **{message}**\n"
            f"   {run_time.strftime('%d/%m/%Y à %H:%M')}"
        )

    # ═══════════════════════════ MORNING BRIEFING ═══════════════════════════

    def setup_morning_briefing(self, time: str = "08:00") -> str:
        """Schedule a daily morning briefing."""
        import sqlite3

        parts = time.split(":")
        hour, minute = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0

        job_id = "morning_briefing"
        schedule = f"every day at {time}"

        self.scheduler.add_job(
            self._morning_briefing_trigger,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_id,
            replace_existing=True,
        )

        self._custom_jobs[job_id] = {
            "name": "Morning Briefing",
            "schedule": schedule,
            "action": "morning_briefing",
        }

        # Persist to DB
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scheduled_jobs (id, name, schedule, action, action_args, enabled) VALUES (?, ?, ?, ?, ?, 1)",
                (job_id, "Morning Briefing", schedule, "morning_briefing", "{}"),
            )

        return f"☀️ Morning briefing planifié chaque jour à **{time}**."

    # ═══════════════════════════ INTERNAL ═══════════════════════════

    def _execute_job(self, job_id: str, action: str, args: dict):
        """Execute a scheduled job and store the result."""
        import sqlite3
        try:
            result = f"Job '{action}' exécuté à {datetime.now().strftime('%H:%M')}"
            self._results[job_id] = result

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE scheduled_jobs SET last_run = ? WHERE id = ?",
                    (datetime.now().isoformat(), job_id),
                )

            # Send notification
            if self._notify:
                meta = self._custom_jobs.get(job_id, {})
                self._notify("ONDES Bot — Job", f"{meta.get('name', job_id)}: terminé")

        except Exception as e:
            self._results[job_id] = f"Erreur: {e}"

    def _send_reminder(self, message: str):
        """Send a macOS notification for a reminder."""
        import sqlite3

        if self._notify:
            self._notify("⏰ ONDES Rappel", message)
        self._results[f"reminder_{message[:20]}"] = f"Rappel envoyé: {message}"

        # Clean up fired reminder from DB
        # Find the job_id for this reminder in _custom_jobs
        fired_id = None
        for jid, meta in list(self._custom_jobs.items()):
            if meta.get("action") == "reminder" and jid.startswith("reminder_"):
                args = meta.get("action_args", {})
                # Match by checking if this job has already fired (no longer in scheduler)
                if not self.scheduler.get_job(jid):
                    fired_id = jid
                    break

        if fired_id:
            self._custom_jobs.pop(fired_id, None)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM scheduled_jobs WHERE id = ?", (fired_id,))

    def _morning_briefing_trigger(self):
        """Trigger for morning briefing — stores flag for chat to pick up."""
        self._results["morning_briefing"] = "PENDING"
        if self._notify:
            self._notify("☀️ ONDES Bot", "Ton briefing du matin est prêt ! Ouvre le chat.")

    def get_pending_briefing(self) -> bool:
        """Check if a morning briefing is pending."""
        if self._results.get("morning_briefing") == "PENDING":
            self._results["morning_briefing"] = "DELIVERED"
            return True
        return False

    def _reload_jobs(self):
        """Reload persisted jobs from SQLite on startup."""
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, name, schedule, action, action_args, enabled FROM scheduled_jobs WHERE enabled = 1"
            ).fetchall()

        reloaded = 0
        expired = []

        for row in rows:
            job_id = row["id"]
            name = row["name"]
            schedule = row["schedule"]
            action = row["action"]
            action_args = json.loads(row["action_args"] or "{}")

            # Skip if already in scheduler (shouldn't happen, but safe)
            if self.scheduler.get_job(job_id):
                continue

            if action == "reminder":
                # schedule contains the ISO datetime for the reminder
                try:
                    run_time = datetime.fromisoformat(schedule)
                except ValueError:
                    expired.append(job_id)
                    continue

                if run_time <= datetime.now():
                    # Reminder expired while bot was off — notify and clean up
                    expired.append(job_id)
                    message = action_args.get("message", name)
                    if self._notify:
                        self._notify("⏰ ONDES Rappel (retardé)", message)
                    continue

                self.scheduler.add_job(
                    self._send_reminder,
                    trigger=DateTrigger(run_date=run_time),
                    id=job_id,
                    args=[action_args.get("message", name)],
                )
                self._custom_jobs[job_id] = {
                    "name": name,
                    "schedule": f"once at {run_time.strftime('%d/%m %H:%M')}",
                    "action": "reminder",
                }
            elif action == "morning_briefing":
                trigger = self._parse_schedule(schedule)
                if trigger:
                    self.scheduler.add_job(
                        self._morning_briefing_trigger,
                        trigger=trigger,
                        id=job_id,
                        replace_existing=True,
                    )
                    self._custom_jobs[job_id] = {
                        "name": name,
                        "schedule": schedule,
                        "action": action,
                    }
                    reloaded += 1
            else:
                # Recurring job
                trigger = self._parse_schedule(schedule)
                if trigger is None:
                    continue

                self.scheduler.add_job(
                    self._execute_job,
                    trigger=trigger,
                    id=job_id,
                    args=[job_id, action, action_args],
                    replace_existing=True,
                )
                self._custom_jobs[job_id] = {
                    "name": name,
                    "schedule": schedule,
                    "action": action,
                    "action_args": action_args,
                }
                reloaded += 1

        # Clean up expired reminders from DB
        if expired:
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany(
                    "DELETE FROM scheduled_jobs WHERE id = ?",
                    [(jid,) for jid in expired],
                )

    def _parse_schedule(self, schedule: str):
        """Parse a human-friendly schedule string into an APScheduler trigger."""
        schedule = schedule.strip().lower()

        # "every 5m", "every 30m"
        import re
        m = re.match(r"every\s+(\d+)\s*m(?:in(?:utes?)?)?$", schedule)
        if m:
            return IntervalTrigger(minutes=int(m.group(1)))

        # "every 2h", "every 1h"
        m = re.match(r"every\s+(\d+)\s*h(?:ours?)?$", schedule)
        if m:
            return IntervalTrigger(hours=int(m.group(1)))

        # "every day at 08:00"
        m = re.match(r"every\s+day\s+at\s+(\d{1,2}):(\d{2})$", schedule)
        if m:
            return CronTrigger(hour=int(m.group(1)), minute=int(m.group(2)))

        # "every monday at 09:00"
        days = {"monday": "mon", "tuesday": "tue", "wednesday": "wed", "thursday": "thu",
                "friday": "fri", "saturday": "sat", "sunday": "sun",
                "lundi": "mon", "mardi": "tue", "mercredi": "wed", "jeudi": "thu",
                "vendredi": "fri", "samedi": "sat", "dimanche": "sun"}
        m = re.match(r"every\s+(\w+)\s+at\s+(\d{1,2}):(\d{2})$", schedule)
        if m and m.group(1) in days:
            return CronTrigger(day_of_week=days[m.group(1)], hour=int(m.group(2)), minute=int(m.group(3)))

        # Cron string: "0 8 * * *"
        parts = schedule.split()
        if len(parts) == 5:
            try:
                return CronTrigger.from_crontab(schedule)
            except Exception:
                pass

        return None

    def _parse_reminder_time(self, remind_at: str) -> datetime | None:
        """Parse a reminder time: 'in 30m', 'in 2h', 'in 1d', or ISO datetime."""
        import re
        remind_at = remind_at.strip().lower()

        # "in 30m", "in 2h", "in 1d"
        m = re.match(r"in\s+(\d+)\s*m(?:in)?$", remind_at)
        if m:
            return datetime.now() + timedelta(minutes=int(m.group(1)))

        m = re.match(r"in\s+(\d+)\s*h(?:ours?)?$", remind_at)
        if m:
            return datetime.now() + timedelta(hours=int(m.group(1)))

        m = re.match(r"in\s+(\d+)\s*d(?:ays?)?$", remind_at)
        if m:
            return datetime.now() + timedelta(days=int(m.group(1)))

        # ISO datetime
        try:
            return datetime.fromisoformat(remind_at)
        except ValueError:
            pass

        return None
