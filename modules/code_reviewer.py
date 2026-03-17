from pathlib import Path

from modules.file_manager import FileManager


class CodeReviewer:
    """Returns file/code content as tool results — Claude does the review inline
    in the main conversation, avoiding costly sub-API calls."""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    def review_file(self, file_path: str) -> str:
        content = self.file_manager.read_file(file_path)
        if content.startswith("Fichier introuvable") or content.startswith("Erreur"):
            return content
        language = self._detect_language(file_path)
        # Return content for Claude to review inline — no sub-API call
        return (
            f"[CODE REVIEW DEMANDÉE]\n"
            f"Fichier: {file_path} | Langage: {language}\n\n"
            f"```{language}\n{content[:8000]}\n```\n\n"
            f"Fais une revue selon: bugs, sécurité, perf, architecture, style."
        )

    def review_snippet(self, code: str, language: str = "python") -> str:
        return (
            f"[CODE REVIEW DEMANDÉE]\n"
            f"Langage: {language}\n\n"
            f"```{language}\n{code[:8000]}\n```\n\n"
            f"Fais une revue selon: bugs, sécurité, perf, architecture, style."
        )

    def explain_code(self, code: str, language: str = "python") -> str:
        return (
            f"[EXPLICATION DEMANDÉE]\n"
            f"Langage: {language}\n\n"
            f"```{language}\n{code[:8000]}\n```\n\n"
            f"Explique ce code en français de manière claire et concise."
        )

    def suggest_refactor(self, file_path: str) -> str:
        content = self.file_manager.read_file(file_path)
        if content.startswith("Fichier introuvable") or content.startswith("Erreur"):
            return content
        language = self._detect_language(file_path)
        return (
            f"[REFACTORING DEMANDÉ]\n"
            f"Fichier: {file_path} | Langage: {language}\n\n"
            f"```{language}\n{content[:8000]}\n```\n\n"
            f"Propose une version refactorisée avec explications des changements."
        )

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
