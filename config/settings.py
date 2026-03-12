from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- API Keys ---
    anthropic_api_key: str = ""

    # --- Modèle Claude ---
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 8096

    # --- Code Runner ---
    code_runner_timeout: int = 30

    # --- Emails ---
    max_email_results: int = 20

    # --- Budget ---
    monthly_budget_usd: float = 20.0

    # --- Répertoires autorisés pour l'accès fichiers ---
    allowed_file_paths: list[str] = [
        "~/Documents",
        "~/Desktop",
        "~/Downloads",
        "~/CODE",
        "/tmp",
    ]

    # --- Paths internes ---
    db_path: str = "data/nietz.db"

    # --- Conversation ---
    max_history: int = 50

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    def get_db_path(self) -> Path:
        return Path(self.db_path)

    def get_allowed_paths(self) -> list[Path]:
        return [Path(p).expanduser().resolve() for p in self.allowed_file_paths]
