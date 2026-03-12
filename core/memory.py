import sqlite3
import json
from datetime import datetime
from pathlib import Path


class Memory:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary TEXT NOT NULL,
                    date TEXT NOT NULL,
                    topics TEXT DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS email_cache (
                    message_id TEXT PRIMARY KEY,
                    subject TEXT,
                    sender TEXT,
                    received_at TEXT,
                    summary TEXT,
                    reply_draft TEXT,
                    status TEXT DEFAULT 'unread'
                );

                CREATE TABLE IF NOT EXISTS action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    description TEXT,
                    result TEXT,
                    executed_at TEXT NOT NULL
                );
            """)

    def save_fact(self, category: str, key: str, value: str, confidence: float = 1.0):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM facts WHERE category = ? AND key = ?",
                (category, key),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE facts SET value = ?, confidence = ?, updated_at = ? WHERE id = ?",
                    (value, confidence, now, existing[0]),
                )
            else:
                conn.execute(
                    "INSERT INTO facts (category, key, value, confidence, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (category, key, value, confidence, now, now),
                )

    def get_facts(self, category: str | None = None, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            if category:
                rows = conn.execute(
                    "SELECT category, key, value, confidence FROM facts WHERE category = ? ORDER BY updated_at DESC LIMIT ?",
                    (category, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT category, key, value, confidence FROM facts ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [
            {"category": r[0], "key": r[1], "value": r[2], "confidence": r[3]}
            for r in rows
        ]

    def get_relevant_facts(self, limit: int = 20) -> str:
        facts = self.get_facts(limit=limit)
        if not facts:
            return "Aucun fait mémorisé pour l'instant."
        lines = []
        for f in facts:
            lines.append(f"- [{f['category']}] {f['key']}: {f['value']}")
        return "\n".join(lines)

    def delete_fact(self, key: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM facts WHERE key = ?", (key,))
            return cursor.rowcount > 0

    def save_conversation_summary(self, summary: str, topics: list[str]):
        now = datetime.now().date().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversation_summaries (summary, date, topics) VALUES (?, ?, ?)",
                (summary, now, json.dumps(topics)),
            )

    def get_recent_summaries(self, limit: int = 5) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT summary, date, topics FROM conversation_summaries ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"summary": r[0], "date": r[1], "topics": json.loads(r[2])}
            for r in rows
        ]

    # --- Email cache ---
    def get_email_cache(self, message_id: str) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT message_id, subject, sender, received_at, summary, reply_draft, status FROM email_cache WHERE message_id = ?",
                (message_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "message_id": row[0],
            "subject": row[1],
            "sender": row[2],
            "received_at": row[3],
            "summary": row[4],
            "reply_draft": row[5],
            "status": row[6],
        }

    def save_email_cache(self, message_id: str, subject: str, sender: str, received_at: str, summary: str = "", status: str = "unread"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO email_cache
                   (message_id, subject, sender, received_at, summary, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (message_id, subject, sender, received_at, summary, status),
            )

    def save_email_draft(self, message_id: str, draft: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE email_cache SET reply_draft = ? WHERE message_id = ?",
                (draft, message_id),
            )

    # --- Action log ---
    def log_action(self, action_type: str, description: str, result: str = ""):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO action_log (action_type, description, result, executed_at) VALUES (?, ?, ?, ?)",
                (action_type, description, result, now),
            )

    def get_recent_actions(self, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT action_type, description, result, executed_at FROM action_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"action_type": r[0], "description": r[1], "result": r[2], "executed_at": r[3]}
            for r in rows
        ]
