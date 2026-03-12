import json
import mimetypes
from datetime import datetime
from pathlib import Path


class SecurityError(Exception):
    pass


class ConfirmationRequired(Exception):
    pass


ALLOWED_BASES = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / "CODE",
    Path("/tmp"),
]


class FileManager:

    def _validate_path(self, path: Path) -> Path:
        resolved = path.resolve()
        for base in ALLOWED_BASES:
            try:
                if resolved.is_relative_to(base.resolve()):
                    return resolved
            except (ValueError, OSError):
                continue
        raise SecurityError(f"Accès refusé: {path} est hors des dossiers autorisés ({', '.join(str(b) for b in ALLOWED_BASES)})")

    def read_file(self, path: str) -> str:
        p = self._validate_path(Path(path))

        if not p.exists():
            return f"Fichier introuvable: {path}"

        if p.suffix == ".pdf":
            return self._read_pdf(p)
        elif p.suffix == ".csv":
            return self._read_csv(p)
        elif p.suffix in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            return f"[Image: {p.name} — {p.stat().st_size} octets — utiliser image_get_info pour les détails]"
        else:
            try:
                return p.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return f"Erreur lecture: {e}"

    def write_file(self, path: str, content: str, mode: str = "w") -> str:
        p = self._validate_path(Path(path))

        if p.exists() and mode == "w":
            # Confirmation is handled by the ConversationManager
            pass

        p.parent.mkdir(parents=True, exist_ok=True)

        if mode == "a":
            with open(p, "a", encoding="utf-8") as f:
                f.write(content)
        elif mode == "x":
            if p.exists():
                return f"Le fichier existe déjà: {path}"
            p.write_text(content, encoding="utf-8")
        else:
            p.write_text(content, encoding="utf-8")

        return f"Fichier écrit: {p} ({len(content)} caractères)"

    def list_directory(self, path: str, pattern: str = "*") -> str:
        p = self._validate_path(Path(path))
        if not p.is_dir():
            return f"Ce n'est pas un dossier: {path}"

        items = []
        for item in sorted(p.glob(pattern)):
            stat = item.stat()
            items.append({
                "name": item.name,
                "type": "dossier" if item.is_dir() else "fichier",
                "size": self._format_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
                "extension": item.suffix or "-",
            })

        if not items:
            return f"Dossier vide: {path}"

        lines = [f"📁 **{path}** ({len(items)} éléments)\n"]
        for item in items:
            icon = "📂" if item["type"] == "dossier" else "📄"
            lines.append(f"  {icon} {item['name']}  ({item['size']}, modifié {item['modified']})")
        return "\n".join(lines)

    def get_info(self, path: str) -> str:
        p = self._validate_path(Path(path))
        if not p.exists():
            return f"Fichier introuvable: {path}"

        stat = p.stat()
        mime, _ = mimetypes.guess_type(str(p))
        return json.dumps({
            "name": p.name,
            "path": str(p),
            "size": self._format_size(stat.st_size),
            "size_bytes": stat.st_size,
            "type": mime or "unknown",
            "extension": p.suffix,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "is_dir": p.is_dir(),
        }, indent=2, ensure_ascii=False)

    def search_content(self, directory: str, query: str, extension: str = "") -> str:
        p = self._validate_path(Path(directory))
        if not p.is_dir():
            return f"Ce n'est pas un dossier: {directory}"

        pattern = f"*{extension}" if extension else "*"
        matches = []

        for file_path in p.rglob(pattern):
            if file_path.is_dir():
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.splitlines(), 1):
                    if query.lower() in line.lower():
                        matches.append(f"  {file_path.relative_to(p)}:{i}: {line.strip()[:100]}")
            except (UnicodeDecodeError, PermissionError):
                continue

        if not matches:
            return f"Aucun résultat pour '{query}' dans {directory}"

        return f"**{len(matches)} résultats pour '{query}':**\n" + "\n".join(matches[:50])

    def _read_pdf(self, path: Path) -> str:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                return "\n\n--- Page ---\n\n".join(pages) if pages else "PDF vide ou non extractible."
        except ImportError:
            return "Module pdfplumber non installé. pip install pdfplumber"
        except Exception as e:
            return f"Erreur lecture PDF: {e}"

    def _read_csv(self, path: Path) -> str:
        try:
            import pandas as pd
            df = pd.read_csv(path)
            return f"**{len(df)} lignes × {len(df.columns)} colonnes**\n\n{df.to_string(index=False, max_rows=50)}"
        except ImportError:
            return "Module pandas non installé. pip install pandas"
        except Exception as e:
            return f"Erreur lecture CSV: {e}"

    def _format_size(self, size: int) -> str:
        for unit in ("o", "Ko", "Mo", "Go"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} To"
