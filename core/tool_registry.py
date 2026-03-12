from typing import Any, Callable


CONFIRMATION_REQUIRED = {
    "calendar_create_event",
    "file_write",
    "telegram_send",
}


TOOL_DEFINITIONS = [
    # ═══ GMAIL ═══
    {
        "name": "gmail_get_emails",
        "description": "Récupère les derniers emails (lus ou non lus)",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "enum": ["unread", "all", "important"],
                    "description": "Filtre: unread, all, ou important",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Nombre max d'emails à récupérer (défaut: 10)",
                },
                "search_query": {
                    "type": "string",
                    "description": "Filtre Gmail ex: 'from:thomas@...' ou 'subject:facture'",
                },
            },
        },
    },
    {
        "name": "gmail_generate_reply",
        "description": "Génère un brouillon de réponse pour un email. Ne l'envoie PAS.",
        "input_schema": {
            "type": "object",
            "required": ["email_id"],
            "properties": {
                "email_id": {"type": "string", "description": "ID de l'email auquel répondre"},
                "instructions": {
                    "type": "string",
                    "description": "Instructions de Martin pour la réponse",
                },
                "tone": {
                    "type": "string",
                    "enum": ["professionnel", "amical", "succinct"],
                    "description": "Ton de la réponse",
                },
            },
        },
    },
    {
        "name": "gmail_search",
        "description": "Recherche dans les emails avec une requête Gmail",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "description": "Requête de recherche Gmail"},
            },
        },
    },
    {
        "name": "gmail_get_thread",
        "description": "Récupère un thread complet d'emails pour voir tout l'échange",
        "input_schema": {
            "type": "object",
            "required": ["thread_id"],
            "properties": {
                "thread_id": {"type": "string", "description": "ID du thread Gmail"},
            },
        },
    },
    # ═══ CALENDRIER ═══
    {
        "name": "calendar_get_events",
        "description": "Récupère les événements du calendrier Apple",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "tomorrow", "week", "month"],
                    "description": "Période à consulter",
                },
                "date": {
                    "type": "string",
                    "description": "Date spécifique format YYYY-MM-DD",
                },
            },
        },
    },
    {
        "name": "calendar_create_event",
        "description": "Crée un événement dans Apple Calendar. DEMANDE TOUJOURS CONFIRMATION.",
        "input_schema": {
            "type": "object",
            "required": ["title", "start_datetime", "end_datetime"],
            "properties": {
                "title": {"type": "string", "description": "Titre de l'événement"},
                "start_datetime": {
                    "type": "string",
                    "description": "Date/heure de début ISO 8601",
                },
                "end_datetime": {
                    "type": "string",
                    "description": "Date/heure de fin ISO 8601",
                },
                "location": {"type": "string", "description": "Lieu de l'événement"},
                "notes": {"type": "string", "description": "Notes de l'événement"},
                "calendar": {
                    "type": "string",
                    "description": "Nom du calendrier (défaut: Calendrier)",
                },
            },
        },
    },
    {
        "name": "calendar_find_free_slots",
        "description": "Trouve les créneaux libres dans le calendrier pour planifier",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date au format YYYY-MM-DD"},
                "duration_minutes": {
                    "type": "integer",
                    "description": "Durée souhaitée en minutes (défaut: 60)",
                },
            },
        },
    },
    {
        "name": "calendar_get_week_summary",
        "description": "Retourne un résumé lisible de la semaine en cours",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    # ═══ FICHIERS ═══
    {
        "name": "file_read",
        "description": "Lit le contenu d'un fichier local (txt, md, py, json, csv, pdf, etc.)",
        "input_schema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Chemin du fichier à lire"},
            },
        },
    },
    {
        "name": "file_write",
        "description": "Écrit du contenu dans un fichier. DEMANDE CONFIRMATION si le fichier existe.",
        "input_schema": {
            "type": "object",
            "required": ["path", "content"],
            "properties": {
                "path": {"type": "string", "description": "Chemin du fichier"},
                "content": {"type": "string", "description": "Contenu à écrire"},
                "mode": {
                    "type": "string",
                    "enum": ["w", "a", "x"],
                    "description": "Mode: w (écrase), a (append), x (crée seulement)",
                },
            },
        },
    },
    {
        "name": "file_list_directory",
        "description": "Liste le contenu d'un dossier avec métadonnées",
        "input_schema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Chemin du dossier"},
                "pattern": {
                    "type": "string",
                    "description": "Pattern glob pour filtrer (défaut: *)",
                },
            },
        },
    },
    {
        "name": "file_search_content",
        "description": "Recherche un pattern dans les fichiers d'un dossier",
        "input_schema": {
            "type": "object",
            "required": ["directory", "query"],
            "properties": {
                "directory": {"type": "string", "description": "Dossier à parcourir"},
                "query": {"type": "string", "description": "Texte à rechercher"},
                "extension": {
                    "type": "string",
                    "description": "Extension de fichier à filtrer (ex: .py)",
                },
            },
        },
    },
    {
        "name": "file_get_info",
        "description": "Retourne les métadonnées d'un fichier (taille, date modification, etc.)",
        "input_schema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Chemin du fichier"},
            },
        },
    },
    # ═══ WEB ═══
    {
        "name": "web_search",
        "description": "Fait une recherche web et retourne les résultats",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "description": "Requête de recherche"},
                "max_results": {
                    "type": "integer",
                    "description": "Nombre max de résultats (défaut: 5)",
                },
            },
        },
    },
    {
        "name": "web_get_page",
        "description": "Récupère et nettoie le contenu texte d'une page web",
        "input_schema": {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "description": "URL de la page à récupérer"},
            },
        },
    },
    {
        "name": "web_search_news",
        "description": "Recherche dans les actualités récentes",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "description": "Requête d'actualités"},
                "max_results": {
                    "type": "integer",
                    "description": "Nombre max de résultats (défaut: 5)",
                },
            },
        },
    },
    # ═══ CODE ═══
    {
        "name": "code_execute_python",
        "description": "Exécute du code Python dans un sandbox isolé et retourne stdout/stderr",
        "input_schema": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string", "description": "Code Python à exécuter"},
                "input_data": {
                    "type": "string",
                    "description": "Données d'entrée stdin optionnelles",
                },
            },
        },
    },
    {
        "name": "code_review_file",
        "description": "Fait une revue de code détaillée d'un fichier",
        "input_schema": {
            "type": "object",
            "required": ["file_path"],
            "properties": {
                "file_path": {"type": "string", "description": "Chemin du fichier à reviewer"},
            },
        },
    },
    {
        "name": "code_review_snippet",
        "description": "Fait une revue de code d'un extrait",
        "input_schema": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string", "description": "Code à reviewer"},
                "language": {
                    "type": "string",
                    "description": "Langage de programmation (défaut: python)",
                },
            },
        },
    },
    {
        "name": "code_explain",
        "description": "Explique en français ce que fait un morceau de code",
        "input_schema": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string", "description": "Code à expliquer"},
                "language": {"type": "string", "description": "Langage de programmation"},
            },
        },
    },
    {
        "name": "code_suggest_refactor",
        "description": "Propose une version refactorisée d'un fichier",
        "input_schema": {
            "type": "object",
            "required": ["file_path"],
            "properties": {
                "file_path": {"type": "string", "description": "Chemin du fichier à refactoriser"},
            },
        },
    },
    # ═══ IMAGES ═══
    {
        "name": "image_convert",
        "description": "Convertit une image d'un format à un autre (PNG→WEBP, etc.)",
        "input_schema": {
            "type": "object",
            "required": ["input_path", "output_format"],
            "properties": {
                "input_path": {"type": "string", "description": "Chemin de l'image source"},
                "output_format": {
                    "type": "string",
                    "description": "Format de sortie (webp, jpg, png, etc.)",
                },
                "output_path": {
                    "type": "string",
                    "description": "Chemin de sortie optionnel",
                },
            },
        },
    },
    {
        "name": "image_resize",
        "description": "Redimensionne une image",
        "input_schema": {
            "type": "object",
            "required": ["input_path", "width"],
            "properties": {
                "input_path": {"type": "string", "description": "Chemin de l'image"},
                "width": {"type": "integer", "description": "Largeur souhaitée en pixels"},
                "height": {"type": "integer", "description": "Hauteur (optionnel, ratio maintenu si vide)"},
                "maintain_ratio": {
                    "type": "boolean",
                    "description": "Maintenir le ratio (défaut: true)",
                },
            },
        },
    },
    {
        "name": "image_compress",
        "description": "Compresse une image JPEG/WEBP",
        "input_schema": {
            "type": "object",
            "required": ["input_path"],
            "properties": {
                "input_path": {"type": "string", "description": "Chemin de l'image"},
                "quality": {
                    "type": "integer",
                    "description": "Qualité 1-100 (défaut: 85)",
                },
            },
        },
    },
    {
        "name": "image_get_info",
        "description": "Retourne les métadonnées d'une image (dimensions, format, taille, EXIF)",
        "input_schema": {
            "type": "object",
            "required": ["image_path"],
            "properties": {
                "image_path": {"type": "string", "description": "Chemin de l'image"},
            },
        },
    },
    {
        "name": "image_batch_convert",
        "description": "Convertit toutes les images d'un dossier d'un format à un autre",
        "input_schema": {
            "type": "object",
            "required": ["directory", "from_format", "to_format"],
            "properties": {
                "directory": {"type": "string", "description": "Chemin du dossier"},
                "from_format": {"type": "string", "description": "Format source (ex: png)"},
                "to_format": {"type": "string", "description": "Format cible (ex: webp)"},
            },
        },
    },
    # ═══ TÂCHES ═══
    {
        "name": "task_create",
        "description": "Crée une nouvelle tâche avec titre, priorité, échéance, projet",
        "input_schema": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string", "description": "Titre de la tâche"},
                "description": {"type": "string", "description": "Description détaillée"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priorité (défaut: medium)",
                },
                "due_date": {
                    "type": "string",
                    "description": "Date d'échéance au format YYYY-MM-DD",
                },
                "project": {"type": "string", "description": "Nom du projet"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags associés",
                },
            },
        },
    },
    {
        "name": "task_list",
        "description": "Liste les tâches avec filtres optionnels",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["todo", "in_progress", "done", "cancelled", "all"],
                    "description": "Filtrer par statut",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Filtrer par priorité",
                },
                "project": {"type": "string", "description": "Filtrer par projet"},
            },
        },
    },
    {
        "name": "task_complete",
        "description": "Marque une tâche comme terminée",
        "input_schema": {
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {"type": "integer", "description": "ID de la tâche"},
            },
        },
    },
    {
        "name": "task_update",
        "description": "Met à jour une tâche existante",
        "input_schema": {
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {"type": "integer", "description": "ID de la tâche"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                "due_date": {"type": "string"},
                "project": {"type": "string"},
                "status": {"type": "string", "enum": ["todo", "in_progress", "done", "cancelled"]},
            },
        },
    },
    {
        "name": "task_get_today",
        "description": "Récupère les tâches dues aujourd'hui ou en retard",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "task_add_reminder",
        "description": "Planifie un rappel pour une tâche",
        "input_schema": {
            "type": "object",
            "required": ["task_id", "remind_at"],
            "properties": {
                "task_id": {"type": "integer", "description": "ID de la tâche"},
                "remind_at": {
                    "type": "string",
                    "description": "Date/heure du rappel ISO 8601",
                },
            },
        },
    },
    # ═══ TELEGRAM ═══
    {
        "name": "telegram_send",
        "description": "Envoie un message Telegram. DEMANDE TOUJOURS CONFIRMATION.",
        "input_schema": {
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": {"type": "string", "description": "Message à envoyer"},
                "chat_id": {
                    "type": "integer",
                    "description": "ID du chat (défaut: chat personnel)",
                },
            },
        },
    },
    {
        "name": "telegram_get_messages",
        "description": "Récupère les messages Telegram récents",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Nombre max de messages (défaut: 20)",
                },
            },
        },
    },
    # ═══ MÉMOIRE ═══
    {
        "name": "memory_save_fact",
        "description": "Sauvegarde un fait dans la mémoire persistante (préférence, contexte, personne, projet)",
        "input_schema": {
            "type": "object",
            "required": ["category", "key", "value"],
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["preference", "context", "person", "project"],
                    "description": "Catégorie du fait",
                },
                "key": {"type": "string", "description": "Clé identifiant le fait"},
                "value": {"type": "string", "description": "Valeur du fait"},
            },
        },
    },
    {
        "name": "memory_get_facts",
        "description": "Récupère les faits mémorisés, optionnellement filtrés par catégorie",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["preference", "context", "person", "project"],
                    "description": "Catégorie à filtrer",
                },
            },
        },
    },
    # ═══ SYSTÈME ═══
    {
        "name": "system_notify",
        "description": "Envoie une notification macOS native",
        "input_schema": {
            "type": "object",
            "required": ["message"],
            "properties": {
                "message": {"type": "string", "description": "Message de la notification"},
                "title": {"type": "string", "description": "Titre de la notification"},
            },
        },
    },
    {
        "name": "system_open_url",
        "description": "Ouvre une URL dans le navigateur par défaut",
        "input_schema": {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "description": "URL à ouvrir"},
            },
        },
    },
    {
        "name": "system_clipboard_set",
        "description": "Copie du texte dans le presse-papier macOS",
        "input_schema": {
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": {"type": "string", "description": "Texte à copier"},
            },
        },
    },
]


import re

# Tool groups for smart routing — only send relevant tools per message
TOOL_GROUPS = {
    "gmail": {
        "tools": {"gmail_get_emails", "gmail_search", "gmail_get_thread", "gmail_generate_reply"},
        "keywords": re.compile(
            r"mail|email|e-mail|inbox|boîte|gmail|courrier|message.*(lu|reç)|répondre.*mail|brouillon|draft",
            re.IGNORECASE,
        ),
    },
    "calendar": {
        "tools": {"calendar_get_events", "calendar_create_event", "calendar_find_free_slots", "calendar_get_week_summary"},
        "keywords": re.compile(
            r"calendrier|calendar|rdv|rendez.?vous|événement|event|créneau|planning|agenda|semaine|demain|aujourd",
            re.IGNORECASE,
        ),
    },
    "files": {
        "tools": {"file_read", "file_write", "file_list_directory", "file_search_content", "file_get_info"},
        "keywords": re.compile(
            r"fichier|file|dossier|répertoire|directory|lire|écrire|ouvrir|sauvegarder|csv|pdf|json|txt|chemin|path",
            re.IGNORECASE,
        ),
    },
    "web": {
        "tools": {"web_search", "web_get_page", "web_search_news"},
        "keywords": re.compile(
            r"cherch|search|web|internet|google|actu|news|url|site|page|lien|link",
            re.IGNORECASE,
        ),
    },
    "code": {
        "tools": {"code_execute_python", "code_review_file", "code_review_snippet", "code_explain", "code_suggest_refactor"},
        "keywords": re.compile(
            r"code|python|exécut|run|script|review|refactor|expliqu.*code|debug|programme",
            re.IGNORECASE,
        ),
    },
    "images": {
        "tools": {"image_convert", "image_resize", "image_compress", "image_get_info", "image_batch_convert"},
        "keywords": re.compile(
            r"image|photo|png|jpg|jpeg|webp|convert|resize|compress|redimensionn|thumbnail",
            re.IGNORECASE,
        ),
    },
    "tasks": {
        "tools": {"task_create", "task_list", "task_complete", "task_update", "task_get_today", "task_add_reminder"},
        "keywords": re.compile(
            r"tâche|task|todo|to.?do|rappel|remind|projet|deadline|échéance|priorit",
            re.IGNORECASE,
        ),
    },
    "telegram": {
        "tools": {"telegram_send", "telegram_get_messages"},
        "keywords": re.compile(
            r"telegram|tg|envoie.*message|notification",
            re.IGNORECASE,
        ),
    },
    "memory": {
        "tools": {"memory_save_fact", "memory_get_facts"},
        "keywords": re.compile(
            r"mémoris|retiens|souviens|mémoire|memory|rappelle.?toi|n'oublie",
            re.IGNORECASE,
        ),
    },
    "system": {
        "tools": {"system_notify", "system_open_url", "system_clipboard_set"},
        "keywords": re.compile(
            r"notif|ouvre.*url|clipboard|presse.?papier|copie.*texte",
            re.IGNORECASE,
        ),
    },
}


class ToolRegistry:
    """Tool registry with smart routing — only sends relevant tools based on user message."""

    def __init__(self):
        self.handlers: dict[str, Callable] = {}

    def register(self, name: str, handler: Callable):
        self.handlers[name] = handler

    def register_many(self, handlers: dict[str, Callable]):
        self.handlers.update(handlers)

    def requires_confirmation(self, tool_name: str) -> bool:
        return tool_name in CONFIRMATION_REQUIRED

    async def execute(self, tool_name: str, inputs: dict) -> Any:
        handler = self.handlers.get(tool_name)
        if not handler:
            return f"Outil inconnu: {tool_name}"
        try:
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                return await handler(**inputs)
            else:
                return handler(**inputs)
        except Exception as e:
            return f"Erreur lors de l'exécution de {tool_name}: {e}"

    def get_all_tools(self) -> list[dict]:
        return TOOL_DEFINITIONS

    def get_tools_for_message(self, message: str) -> list[dict]:
        """Return only the tool definitions relevant to the user's message."""
        needed: set[str] = set()
        for group in TOOL_GROUPS.values():
            if group["keywords"].search(message):
                needed |= group["tools"]

        # No tools matched = pure conversation, send nothing
        if not needed:
            return []

        return [t for t in TOOL_DEFINITIONS if t["name"] in needed]
