import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

    @classmethod
    def from_str(cls, s: str) -> "Priority":
        mapping = {"low": cls.LOW, "medium": cls.MEDIUM, "high": cls.HIGH, "urgent": cls.URGENT}
        return mapping.get(s.lower(), cls.MEDIUM)


@dataclass
class Task:
    id: int
    title: str
    description: str
    priority: Priority
    due_date: datetime | None
    project: str | None
    tags: list[str]
    status: str
    created_at: datetime


PRIORITY_ICONS = {
    Priority.URGENT: "🚨 URG",
    Priority.HIGH: "🔴 HAUTE",
    Priority.MEDIUM: "🟡 MOY.",
    Priority.LOW: "🟢 BASSE",
}


class TaskManager:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    priority INTEGER DEFAULT 2,
                    due_date TEXT,
                    project TEXT,
                    tags TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'todo',
                    created_at TEXT NOT NULL
                )
            """)

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: str | None = None,
        project: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        now = datetime.now().isoformat()
        p = Priority.from_str(priority)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO tasks (title, description, priority, due_date, project, tags, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'todo', ?)""",
                (title, description, p.value, due_date, project, json.dumps(tags or []), now),
            )
            task_id = cursor.lastrowid

        return f"✅ Tâche #{task_id} créée: **{title}** ({PRIORITY_ICONS[p]})"

    def get_tasks(
        self,
        status: str = "todo",
        priority: str | None = None,
        project: str | None = None,
    ) -> str:
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM tasks WHERE 1=1"
            params: list = []

            if status and status != "all":
                query += " AND status = ?"
                params.append(status)
            if priority:
                p = Priority.from_str(priority)
                query += " AND priority = ?"
                params.append(p.value)
            if project:
                query += " AND project = ?"
                params.append(project)

            query += " ORDER BY priority DESC, due_date ASC"
            rows = conn.execute(query, params).fetchall()

        if not rows:
            return "Aucune tâche trouvée."

        return self._format_tasks(rows)

    def get_today(self) -> str:
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT * FROM tasks
                   WHERE status IN ('todo', 'in_progress')
                   AND (due_date <= ? OR due_date IS NULL)
                   ORDER BY priority DESC, due_date ASC""",
                (today,),
            ).fetchall()

        if not rows:
            return "Aucune tâche pour aujourd'hui."

        return self._format_tasks(rows)

    def complete_task(self, task_id: int) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE tasks SET status = 'done' WHERE id = ?",
                (task_id,),
            )
            if cursor.rowcount == 0:
                return f"Tâche #{task_id} introuvable."

            row = conn.execute("SELECT title FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return f"✅ Tâche #{task_id} terminée: **{row[0]}**"

    def update_task(self, task_id: int, **kwargs) -> str:
        allowed = {"title", "description", "priority", "due_date", "project", "status", "tags"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}

        if not updates:
            return "Rien à mettre à jour."

        if "priority" in updates:
            updates["priority"] = Priority.from_str(updates["priority"]).value
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [task_id]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE tasks SET {set_clause} WHERE id = ?",
                values,
            )
            if cursor.rowcount == 0:
                return f"Tâche #{task_id} introuvable."

        return f"✅ Tâche #{task_id} mise à jour."

    def add_reminder(self, task_id: int, remind_at: str) -> str:
        # APScheduler integration for reminders
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            scheduler = BackgroundScheduler()
            remind_dt = datetime.fromisoformat(remind_at)
            scheduler.add_job(
                self._send_reminder,
                "date",
                run_date=remind_dt,
                args=[task_id],
            )
            scheduler.start()
            return f"⏰ Rappel planifié pour la tâche #{task_id} à {remind_dt.strftime('%d/%m/%Y %H:%M')}"
        except ImportError:
            return "Module APScheduler non installé."

    def _send_reminder(self, task_id: int):
        import subprocess
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT title FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row:
            # macOS notification
            subprocess.run([
                "osascript", "-e",
                f'display notification "{row[0]}" with title "NIETZ BOT — Rappel"',
            ])

    def get_projects(self) -> str:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT project, COUNT(*) as total,
                       SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done
                FROM tasks
                WHERE project IS NOT NULL
                GROUP BY project
                ORDER BY total DESC
            """).fetchall()

        if not rows:
            return "Aucun projet trouvé."

        lines = ["**Projets:**\n"]
        for r in rows:
            lines.append(f"  • **{r[0]}**: {r[2]}/{r[1]} terminées")
        return "\n".join(lines)

    def _format_tasks(self, rows: list) -> str:
        lines = []
        for row in rows:
            task_id, title, desc, priority_val, due_date, project, tags_json, status, created = row
            p = Priority(priority_val)
            icon = PRIORITY_ICONS[p]
            due_str = self._format_due_date(due_date) if due_date else "Pas d'échéance"
            project_str = f" [{project}]" if project else ""
            status_icon = {"todo": "⬜", "in_progress": "🔄", "done": "✅", "cancelled": "❌"}.get(status, "⬜")
            lines.append(f"  {status_icon} **#{task_id}** {title} — {icon}{project_str} — {due_str}")
        return "\n".join(lines)

    def _format_due_date(self, due_str: str) -> str:
        try:
            due = datetime.fromisoformat(due_str).date()
            today = date.today()
            delta = (due - today).days
            if delta < 0:
                return f"**⚠️ En retard ({abs(delta)}j)**"
            elif delta == 0:
                return "Aujourd'hui"
            elif delta == 1:
                return "Demain"
            else:
                return due.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return due_str
