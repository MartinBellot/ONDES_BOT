from pathlib import Path

from config.prompts import CODE_REVIEW_PROMPT
from core.claude_client import ClaudeClient
from modules.file_manager import FileManager


class CodeReviewer:
    def __init__(self, claude_client: ClaudeClient, file_manager: FileManager):
        self.claude = claude_client
        self.file_manager = file_manager

    def review_file(self, file_path: str) -> str:
        content = self.file_manager.read_file(file_path)
        if content.startswith("Fichier introuvable") or content.startswith("Erreur"):
            return content

        language = self._detect_language(file_path)
        return self._do_review(content, language, file_path)

    def review_snippet(self, code: str, language: str = "python") -> str:
        return self._do_review(code, language)

    def explain_code(self, code: str, language: str = "python") -> str:
        prompt = f"Explique en français ce que fait ce code {language}:\n\n```{language}\n{code}\n```"
        response = self.claude.simple_chat(
            messages=[{"role": "user", "content": prompt}],
            system="Tu es un expert en programmation. Explique le code de manière claire et concise en français.",
            context_label="code_explain",
        )
        return response.content[0].text

    def suggest_refactor(self, file_path: str) -> str:
        content = self.file_manager.read_file(file_path)
        if content.startswith("Fichier introuvable") or content.startswith("Erreur"):
            return content

        language = self._detect_language(file_path)
        prompt = f"Propose une version refactorisée de ce fichier {language}:\n\n```{language}\n{content}\n```\n\nDonne le code complet refactorisé avec des explications des changements."

        response = self.claude.simple_chat(
            messages=[{"role": "user", "content": prompt}],
            system="Tu es un senior developer expert en refactoring. Propose un code propre, lisible et idiomatique.",
            context_label="code_refactor",
        )
        return response.content[0].text

    def _do_review(self, code: str, language: str, file_path: str = "") -> str:
        header = f"Fichier: {file_path}\n" if file_path else ""
        prompt = f"""{header}Langage: {language}

```{language}
{code}
```

Fais une revue de code complète."""

        response = self.claude.simple_chat(
            messages=[{"role": "user", "content": prompt}],
            system=CODE_REVIEW_PROMPT,
            context_label="code_review",
        )
        return response.content[0].text

    def _detect_language(self, file_path: str) -> str:
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".sh": "bash",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
            ".rb": "ruby",
            ".swift": "swift",
        }
        return ext_map.get(Path(file_path).suffix, "text")
