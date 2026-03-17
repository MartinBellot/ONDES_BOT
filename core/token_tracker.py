from dataclasses import dataclass, field
from datetime import datetime
import sqlite3
from pathlib import Path


PRICING = {
    "claude-sonnet-4-6": {
        "input_per_mtok": 3.00,
        "output_per_mtok": 15.00,
        "cache_write_per_mtok": 3.75,
        "cache_read_per_mtok": 0.30,
    },
    "claude-sonnet-4-5": {
        "input_per_mtok": 3.00,
        "output_per_mtok": 15.00,
        "cache_write_per_mtok": 3.75,
        "cache_read_per_mtok": 0.30,
    },
    "claude-haiku-3-5": {
        "input_per_mtok": 0.80,
        "output_per_mtok": 4.00,
        "cache_write_per_mtok": 1.00,
        "cache_read_per_mtok": 0.08,
    },
}


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    model: str = "claude-sonnet-4-6"
    timestamp: datetime = field(default_factory=datetime.now)
    context: str = ""

    @property
    def cost_usd(self) -> float:
        p = PRICING.get(self.model, PRICING["claude-sonnet-4-6"])
        return (
            self.input_tokens * p["input_per_mtok"] / 1_000_000
            + self.output_tokens * p["output_per_mtok"] / 1_000_000
            + self.cache_write_tokens * p["cache_write_per_mtok"] / 1_000_000
            + self.cache_read_tokens * p["cache_read_per_mtok"] / 1_000_000
        )


class TokenTracker:
    def __init__(self, db_path: str | Path, monthly_budget_usd: float = 20.0):
        self.db_path = str(db_path)
        self.monthly_budget = monthly_budget_usd
        self.session_usage: list[TokenUsage] = []
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cache_write_tokens INTEGER DEFAULT 0,
                    cache_read_tokens INTEGER DEFAULT 0,
                    cost_usd REAL NOT NULL,
                    context TEXT DEFAULT ''
                )
            """)

    def record(self, usage: TokenUsage):
        self.session_usage.append(usage)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO token_logs
                (timestamp, model, input_tokens, output_tokens,
                 cache_write_tokens, cache_read_tokens, cost_usd, context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    usage.timestamp.isoformat(),
                    usage.model,
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.cache_write_tokens,
                    usage.cache_read_tokens,
                    usage.cost_usd,
                    usage.context,
                ),
            )

    @property
    def session_tokens(self) -> dict:
        return {
            "input": sum(u.input_tokens for u in self.session_usage),
            "output": sum(u.output_tokens for u in self.session_usage),
            "total": sum(u.input_tokens + u.output_tokens for u in self.session_usage),
            "cost_usd": sum(u.cost_usd for u in self.session_usage),
        }

    def monthly_stats(self) -> dict:
        first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    SUM(input_tokens), SUM(output_tokens),
                    SUM(cache_write_tokens), SUM(cache_read_tokens),
                    SUM(cost_usd), COUNT(*)
                FROM token_logs
                WHERE timestamp >= ?
                """,
                (first_of_month.isoformat(),),
            ).fetchone()
        cost = row[4] or 0.0
        return {
            "input_tokens": row[0] or 0,
            "output_tokens": row[1] or 0,
            "cache_write": row[2] or 0,
            "cache_read": row[3] or 0,
            "cost_usd": cost,
            "api_calls": row[5] or 0,
            "budget_pct": (cost / self.monthly_budget) * 100 if self.monthly_budget > 0 else 0,
        }

    def daily_breakdown(self, days: int = 7) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT DATE(timestamp) as day,
                       SUM(input_tokens + output_tokens) as tokens,
                       SUM(cost_usd) as cost,
                       COUNT(*) as calls
                FROM token_logs
                WHERE timestamp >= DATE('now', ?)
                GROUP BY day ORDER BY day DESC
                """,
                (f"-{days} days",),
            ).fetchall()
        return [{"day": r[0], "tokens": r[1], "cost_usd": r[2], "calls": r[3]} for r in rows]

    def top_consumers(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT context, SUM(cost_usd) as total_cost, COUNT(*) as calls
                FROM token_logs
                WHERE timestamp >= DATE('now', '-30 days')
                GROUP BY context ORDER BY total_cost DESC LIMIT 10
                """
            ).fetchall()
        return [{"context": r[0], "cost_usd": r[1], "calls": r[2]} for r in rows]

    def budget_warning(self) -> str | None:
        stats = self.monthly_stats()
        pct = stats["budget_pct"]
        if pct >= 100:
            return f"🚨 Budget mensuel dépassé ({stats['cost_usd']:.2f}$ / {self.monthly_budget}$)"
        elif pct >= 75:
            return f"⚠️ 75% du budget atteint ({stats['cost_usd']:.2f}$ / {self.monthly_budget}$)"
        return None

    def session_breakdown(self) -> dict:
        """Detailed breakdown of token usage by context label for this session."""
        breakdown: dict[str, dict] = {}
        for u in self.session_usage:
            ctx = u.context or "unknown"
            if ctx not in breakdown:
                breakdown[ctx] = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost": 0.0, "calls": 0}
            breakdown[ctx]["input"] += u.input_tokens
            breakdown[ctx]["output"] += u.output_tokens
            breakdown[ctx]["cache_read"] += u.cache_read_tokens
            breakdown[ctx]["cache_write"] += u.cache_write_tokens
            breakdown[ctx]["cost"] += u.cost_usd
            breakdown[ctx]["calls"] += 1
        return breakdown

    @property
    def session_cache_stats(self) -> dict:
        """Show how much prompt caching is saving."""
        total_cache_read = sum(u.cache_read_tokens for u in self.session_usage)
        total_cache_write = sum(u.cache_write_tokens for u in self.session_usage)
        total_input = sum(u.input_tokens for u in self.session_usage)
        cache_hit_rate = (total_cache_read / max(total_input + total_cache_read, 1)) * 100
        return {
            "cache_read_tokens": total_cache_read,
            "cache_write_tokens": total_cache_write,
            "cache_hit_rate_pct": round(cache_hit_rate, 1),
        }
