from typing import Any, Callable


CONFIRMATION_REQUIRED = {
    "calendar_create_event",
    "file_write",
    "gmail_send_email",
    "docker_remove",
    "docker_compose_down",
    "docker_system_prune",
    "github_merge_pr",
}


TOOL_DEFINITIONS = [
    # ═══ GMAIL ═══
    {
        "name": "gmail_get_emails",
        "description": "Récupère les derniers emails",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {"type": "string", "enum": ["unread", "all", "important"]},
                "max_results": {"type": "integer", "description": "Max emails (défaut: 10)"},
                "search_query": {"type": "string", "description": "Filtre Gmail ex: 'from:x@...'"},
            },
        },
    },
    {
        "name": "gmail_generate_reply",
        "description": "Génère un brouillon de réponse email (ne l'envoie PAS)",
        "input_schema": {
            "type": "object",
            "required": ["email_id"],
            "properties": {
                "email_id": {"type": "string"},
                "instructions": {"type": "string", "description": "Instructions pour la réponse"},
                "tone": {"type": "string", "enum": ["professionnel", "amical", "succinct"]},
            },
        },
    },
    {
        "name": "gmail_send_email",
        "description": "Envoie un email (CONFIRMATION REQUISE)",
        "input_schema": {
            "type": "object",
            "required": ["to", "subject", "body"],
            "properties": {
                "to": {"type": "string", "description": "Adresse email du destinataire"},
                "subject": {"type": "string", "description": "Objet du mail"},
                "body": {"type": "string", "description": "Corps du mail (texte)"},
            },
        },
    },
    {
        "name": "gmail_search",
        "description": "Recherche emails avec requête Gmail",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
            },
        },
    },
    {
        "name": "gmail_read_email",
        "description": "Lit le contenu complet d'un email (corps, expéditeur, date, pièces jointes)",
        "input_schema": {
            "type": "object",
            "required": ["email_id"],
            "properties": {
                "email_id": {"type": "string", "description": "L'ID de l'email à lire"},
            },
        },
    },
    {
        "name": "gmail_get_thread",
        "description": "Récupère un thread complet d'emails",
        "input_schema": {
            "type": "object",
            "required": ["thread_id"],
            "properties": {
                "thread_id": {"type": "string"},
            },
        },
    },
    # ═══ CALENDRIER ═══
    {
        "name": "calendar_get_events",
        "description": "Récupère les événements du calendrier",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "enum": ["today", "tomorrow", "week", "month"]},
                "date": {"type": "string", "description": "Date YYYY-MM-DD"},
            },
        },
    },
    {
        "name": "calendar_create_event",
        "description": "Crée un événement calendrier (CONFIRMATION REQUISE)",
        "input_schema": {
            "type": "object",
            "required": ["title", "start_datetime", "end_datetime"],
            "properties": {
                "title": {"type": "string"},
                "start_datetime": {"type": "string", "description": "ISO 8601"},
                "end_datetime": {"type": "string", "description": "ISO 8601"},
                "location": {"type": "string"},
                "notes": {"type": "string"},
                "calendar": {"type": "string", "description": "Nom du calendrier"},
            },
        },
    },
    {
        "name": "calendar_find_free_slots",
        "description": "Trouve les créneaux libres",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "duration_minutes": {"type": "integer", "description": "Durée en min (défaut: 60)"},
            },
        },
    },
    {
        "name": "calendar_get_week_summary",
        "description": "Résumé de la semaine en cours",
        "input_schema": {"type": "object", "properties": {}},
    },
    # ═══ FICHIERS ═══
    {
        "name": "file_read",
        "description": "Lit un fichier local",
        "input_schema": {
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string"}},
        },
    },
    {
        "name": "file_write",
        "description": "Écrit dans un fichier (CONFIRMATION si existe)",
        "input_schema": {
            "type": "object",
            "required": ["path", "content"],
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "mode": {"type": "string", "enum": ["w", "a", "x"]},
            },
        },
    },
    {
        "name": "file_list_directory",
        "description": "Liste le contenu d'un dossier",
        "input_schema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string", "description": "Glob pattern"},
            },
        },
    },
    {
        "name": "file_search_content",
        "description": "Recherche un texte dans les fichiers d'un dossier",
        "input_schema": {
            "type": "object",
            "required": ["directory", "query"],
            "properties": {
                "directory": {"type": "string"},
                "query": {"type": "string"},
                "extension": {"type": "string", "description": "Ex: .py"},
            },
        },
    },
    {
        "name": "file_get_info",
        "description": "Métadonnées d'un fichier (taille, date, etc.)",
        "input_schema": {
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string"}},
        },
    },
    # ═══ WEB ═══
    {
        "name": "web_search",
        "description": "Recherche web",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "description": "Défaut: 5"},
            },
        },
    },
    {
        "name": "web_get_page",
        "description": "Récupère le contenu texte d'une page web",
        "input_schema": {
            "type": "object",
            "required": ["url"],
            "properties": {"url": {"type": "string"}},
        },
    },
    {
        "name": "web_search_news",
        "description": "Recherche actualités récentes",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer"},
            },
        },
    },
    # ═══ CODE ═══
    {
        "name": "code_execute_python",
        "description": "Exécute du Python en sandbox, retourne stdout/stderr",
        "input_schema": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string"},
                "input_data": {"type": "string", "description": "stdin optionnel"},
            },
        },
    },
    {
        "name": "code_review_file",
        "description": "Lit un fichier et retourne son contenu pour review (tu fais la review toi-même)",
        "input_schema": {
            "type": "object",
            "required": ["file_path"],
            "properties": {"file_path": {"type": "string"}},
        },
    },
    {
        "name": "code_review_snippet",
        "description": "Retourne un extrait de code pour review (tu fais la review toi-même)",
        "input_schema": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"},
            },
        },
    },
    {
        "name": "code_explain",
        "description": "Retourne du code pour que tu l'expliques",
        "input_schema": {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"},
            },
        },
    },
    {
        "name": "code_suggest_refactor",
        "description": "Lit un fichier et retourne son contenu pour refactoring (tu proposes le refactor toi-même)",
        "input_schema": {
            "type": "object",
            "required": ["file_path"],
            "properties": {"file_path": {"type": "string"}},
        },
    },
    # ═══ IMAGES ═══
    {
        "name": "image_convert",
        "description": "Convertit une image (ex: PNG→WEBP)",
        "input_schema": {
            "type": "object",
            "required": ["input_path", "output_format"],
            "properties": {
                "input_path": {"type": "string"},
                "output_format": {"type": "string", "description": "webp, jpg, png..."},
                "output_path": {"type": "string"},
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
                "input_path": {"type": "string"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
                "maintain_ratio": {"type": "boolean"},
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
                "input_path": {"type": "string"},
                "quality": {"type": "integer", "description": "1-100 (défaut: 85)"},
            },
        },
    },
    {
        "name": "image_get_info",
        "description": "Métadonnées d'une image (dimensions, format, EXIF)",
        "input_schema": {
            "type": "object",
            "required": ["image_path"],
            "properties": {"image_path": {"type": "string"}},
        },
    },
    {
        "name": "image_batch_convert",
        "description": "Convertit toutes les images d'un dossier",
        "input_schema": {
            "type": "object",
            "required": ["directory", "from_format", "to_format"],
            "properties": {
                "directory": {"type": "string"},
                "from_format": {"type": "string"},
                "to_format": {"type": "string"},
            },
        },
    },
    # ═══ TÂCHES ═══
    {
        "name": "task_create",
        "description": "Crée une tâche",
        "input_schema": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                "due_date": {"type": "string", "description": "YYYY-MM-DD"},
                "project": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "task_list",
        "description": "Liste les tâches",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["todo", "in_progress", "done", "cancelled", "all"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                "project": {"type": "string"},
            },
        },
    },
    {
        "name": "task_complete",
        "description": "Marque une tâche comme terminée",
        "input_schema": {
            "type": "object",
            "required": ["task_id"],
            "properties": {"task_id": {"type": "integer"}},
        },
    },
    {
        "name": "task_update",
        "description": "Met à jour une tâche",
        "input_schema": {
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {"type": "integer"},
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
        "description": "Tâches du jour et en retard",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "task_add_reminder",
        "description": "Planifie un rappel pour une tâche",
        "input_schema": {
            "type": "object",
            "required": ["task_id", "remind_at"],
            "properties": {
                "task_id": {"type": "integer"},
                "remind_at": {"type": "string", "description": "ISO 8601"},
            },
        },
    },
    # ═══ MÉMOIRE ═══
    {
        "name": "memory_save_fact",
        "description": "Sauvegarde un fait en mémoire persistante",
        "input_schema": {
            "type": "object",
            "required": ["category", "key", "value"],
            "properties": {
                "category": {"type": "string", "enum": ["preference", "context", "person", "project"]},
                "key": {"type": "string"},
                "value": {"type": "string"},
            },
        },
    },
    {
        "name": "memory_get_facts",
        "description": "Récupère les faits mémorisés",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["preference", "context", "person", "project"]},
            },
        },
    },
    # ═══ SYSTÈME ═══
    {
        "name": "system_notify",
        "description": "Notification macOS native",
        "input_schema": {
            "type": "object",
            "required": ["message"],
            "properties": {
                "message": {"type": "string"},
                "title": {"type": "string"},
            },
        },
    },
    {
        "name": "system_open_url",
        "description": "Ouvre une URL dans le navigateur",
        "input_schema": {
            "type": "object",
            "required": ["url"],
            "properties": {"url": {"type": "string"}},
        },
    },
    {
        "name": "system_clipboard_set",
        "description": "Copie du texte dans le presse-papier",
        "input_schema": {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string"}},
        },
    },
    # ═══ DOCKER ═══
    {
        "name": "docker_list_containers",
        "description": "Liste tous les containers Docker (actifs et stoppés)",
        "input_schema": {
            "type": "object",
            "properties": {
                "all": {"type": "boolean", "description": "Inclure les containers stoppés (défaut: true)"},
            },
        },
    },
    {
        "name": "docker_run",
        "description": "Créer et lancer un nouveau container Docker",
        "input_schema": {
            "type": "object",
            "required": ["image"],
            "properties": {
                "image": {"type": "string", "description": "Image Docker (ex: nginx:latest)"},
                "name": {"type": "string", "description": "Nom du container"},
                "ports": {"type": "object", "description": "Mapping de ports {host: container}"},
                "volumes": {"type": "object", "description": "Volumes {host_path: container_path}"},
                "env": {"type": "object", "description": "Variables d'environnement {key: value}"},
                "restart_policy": {"type": "string", "description": "Politique de redémarrage (défaut: unless-stopped)"},
                "extra_args": {"type": "string", "description": "Arguments Docker supplémentaires"},
            },
        },
    },
    {
        "name": "docker_start",
        "description": "Démarrer un container Docker existant",
        "input_schema": {
            "type": "object",
            "required": ["name_or_id"],
            "properties": {"name_or_id": {"type": "string"}},
        },
    },
    {
        "name": "docker_stop",
        "description": "Arrêter un container Docker",
        "input_schema": {
            "type": "object",
            "required": ["name_or_id"],
            "properties": {"name_or_id": {"type": "string"}},
        },
    },
    {
        "name": "docker_restart",
        "description": "Redémarrer un container Docker",
        "input_schema": {
            "type": "object",
            "required": ["name_or_id"],
            "properties": {"name_or_id": {"type": "string"}},
        },
    },
    {
        "name": "docker_remove",
        "description": "Supprimer un container Docker (CONFIRMATION REQUISE)",
        "input_schema": {
            "type": "object",
            "required": ["name_or_id"],
            "properties": {
                "name_or_id": {"type": "string"},
                "force": {"type": "boolean", "description": "Forcer la suppression"},
            },
        },
    },
    {
        "name": "docker_logs",
        "description": "Voir les logs d'un container Docker",
        "input_schema": {
            "type": "object",
            "required": ["name_or_id"],
            "properties": {
                "name_or_id": {"type": "string"},
                "tail": {"type": "integer", "description": "Nombre de lignes (défaut: 50)"},
            },
        },
    },
    {
        "name": "docker_stats",
        "description": "Stats CPU/RAM/réseau des containers Docker",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_or_id": {"type": "string", "description": "Container spécifique (optionnel)"},
            },
        },
    },
    {
        "name": "docker_exec",
        "description": "Exécuter une commande dans un container Docker en cours d'exécution",
        "input_schema": {
            "type": "object",
            "required": ["name_or_id", "command"],
            "properties": {
                "name_or_id": {"type": "string"},
                "command": {"type": "string", "description": "Commande à exécuter"},
            },
        },
    },
    {
        "name": "docker_list_images",
        "description": "Liste les images Docker locales",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "docker_pull",
        "description": "Télécharger une image Docker",
        "input_schema": {
            "type": "object",
            "required": ["image"],
            "properties": {"image": {"type": "string"}},
        },
    },
    {
        "name": "docker_list_volumes",
        "description": "Liste les volumes Docker",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "docker_list_networks",
        "description": "Liste les réseaux Docker",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "docker_compose_up",
        "description": "Lancer une stack Docker Compose",
        "input_schema": {
            "type": "object",
            "required": ["compose_file"],
            "properties": {
                "compose_file": {"type": "string", "description": "Chemin vers le docker-compose.yml"},
                "project_name": {"type": "string"},
            },
        },
    },
    {
        "name": "docker_compose_down",
        "description": "Arrêter une stack Docker Compose (CONFIRMATION REQUISE)",
        "input_schema": {
            "type": "object",
            "required": ["compose_file"],
            "properties": {
                "compose_file": {"type": "string"},
                "project_name": {"type": "string"},
                "remove_volumes": {"type": "boolean"},
            },
        },
    },
    {
        "name": "docker_compose_status",
        "description": "Voir le statut d'une stack Docker Compose",
        "input_schema": {
            "type": "object",
            "required": ["compose_file"],
            "properties": {
                "compose_file": {"type": "string"},
                "project_name": {"type": "string"},
            },
        },
    },
    {
        "name": "docker_compose_logs",
        "description": "Voir les logs d'une stack Docker Compose",
        "input_schema": {
            "type": "object",
            "required": ["compose_file"],
            "properties": {
                "compose_file": {"type": "string"},
                "service": {"type": "string", "description": "Service spécifique (optionnel)"},
                "tail": {"type": "integer", "description": "Nombre de lignes (défaut: 50)"},
            },
        },
    },
    {
        "name": "docker_generate_compose",
        "description": "Générer un docker-compose.yml à partir d'un template. Pour Minecraft moddé (Forge, Fabric, NeoForge, Quilt), utilise server_type et mods (slugs Modrinth séparés par virgules).",
        "input_schema": {
            "type": "object",
            "required": ["template", "output_dir"],
            "properties": {
                "template": {"type": "string", "description": "Nom du template: minecraft, minecraft-bedrock, postgres, redis, nginx, mongodb, mysql, portainer"},
                "output_dir": {"type": "string", "description": "Dossier de sortie pour le docker-compose.yml (ex: ~/Docker/minecraft)"},
                "server_name": {"type": "string"},
                "port": {"type": "string"},
                "memory": {"type": "string", "description": "RAM pour le serveur (ex: 4G, 6G pour moddé)"},
                "password": {"type": "string"},
                "version": {"type": "string", "description": "Version Minecraft (ex: 1.20.1)"},
                "gamemode": {"type": "string"},
                "difficulty": {"type": "string"},
                "max_players": {"type": "string"},
                "server_type": {"type": "string", "description": "Type de serveur: VANILLA, FORGE, NEOFORGE, FABRIC, QUILT (défaut: VANILLA)"},
                "mods": {"type": "string", "description": "Slugs Modrinth des mods séparés par virgules (ex: 'create,do-a-barrel-roll,fabric-api'). Nécessite server_type FORGE/FABRIC/etc."},
                "modpack": {"type": "string", "description": "URL CurseForge du modpack (optionnel)"},
            },
        },
    },
    {
        "name": "docker_templates",
        "description": "Liste les templates Docker Compose disponibles",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "docker_system_info",
        "description": "Informations système Docker (version, espace disque)",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "docker_system_prune",
        "description": "Nettoyer les ressources Docker inutilisées (CONFIRMATION REQUISE)",
        "input_schema": {
            "type": "object",
            "properties": {
                "all": {"type": "boolean", "description": "Supprimer aussi les images non utilisées"},
            },
        },
    },
    # ═══ GITHUB ═══
    {
        "name": "github_list_repos",
        "description": "Liste tes repos GitHub",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Nombre max (défaut: 10)"},
                "sort": {"type": "string", "description": "Tri: updated, created, name"},
            },
        },
    },
    {
        "name": "github_repo_info",
        "description": "Détails d'un repo GitHub",
        "input_schema": {
            "type": "object",
            "required": ["repo"],
            "properties": {"repo": {"type": "string", "description": "owner/repo ou juste repo"}},
        },
    },
    {
        "name": "github_list_issues",
        "description": "Liste les issues d'un repo GitHub",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "owner/repo (optionnel si dans un repo git)"},
                "state": {"type": "string", "enum": ["open", "closed", "all"]},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "github_create_issue",
        "description": "Créer une issue GitHub",
        "input_schema": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "repo": {"type": "string"},
                "labels": {"type": "string", "description": "Labels séparés par des virgules"},
            },
        },
    },
    {
        "name": "github_view_issue",
        "description": "Voir les détails d'une issue GitHub",
        "input_schema": {
            "type": "object",
            "required": ["issue_number"],
            "properties": {
                "issue_number": {"type": "integer"},
                "repo": {"type": "string"},
            },
        },
    },
    {
        "name": "github_close_issue",
        "description": "Fermer une issue GitHub",
        "input_schema": {
            "type": "object",
            "required": ["issue_number"],
            "properties": {
                "issue_number": {"type": "integer"},
                "repo": {"type": "string"},
            },
        },
    },
    {
        "name": "github_list_prs",
        "description": "Liste les pull requests d'un repo GitHub",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "state": {"type": "string", "enum": ["open", "closed", "merged", "all"]},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "github_create_pr",
        "description": "Créer une pull request GitHub",
        "input_schema": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "base": {"type": "string", "description": "Branche cible (défaut: main)"},
                "repo": {"type": "string"},
            },
        },
    },
    {
        "name": "github_view_pr",
        "description": "Voir les détails d'une PR GitHub",
        "input_schema": {
            "type": "object",
            "required": ["pr_number"],
            "properties": {
                "pr_number": {"type": "integer"},
                "repo": {"type": "string"},
            },
        },
    },
    {
        "name": "github_merge_pr",
        "description": "Merger une PR GitHub (CONFIRMATION REQUISE)",
        "input_schema": {
            "type": "object",
            "required": ["pr_number"],
            "properties": {
                "pr_number": {"type": "integer"},
                "method": {"type": "string", "enum": ["squash", "merge", "rebase"]},
                "repo": {"type": "string"},
            },
        },
    },
    {
        "name": "github_actions_runs",
        "description": "Voir les derniers runs GitHub Actions (CI/CD)",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "github_notifications",
        "description": "Voir les notifications GitHub",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Nombre max (défaut: 10)"},
            },
        },
    },
    {
        "name": "github_git_status",
        "description": "Git status du répertoire courant ou spécifié",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Chemin du repo (optionnel)"},
            },
        },
    },
    {
        "name": "github_git_diff",
        "description": "Voir le diff git (staged ou unstaged)",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "staged": {"type": "boolean", "description": "Voir le diff staged uniquement"},
            },
        },
    },
    # ═══ APPLE MUSIC ═══
    {
        "name": "music_play",
        "description": "Reprendre la lecture Apple Music",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "music_pause",
        "description": "Mettre en pause Apple Music",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "music_next",
        "description": "Passer au morceau suivant",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "music_previous",
        "description": "Revenir au morceau précédent",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "music_now_playing",
        "description": "Afficher le morceau en cours de lecture",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "music_volume",
        "description": "Régler le volume d'Apple Music (0-100)",
        "input_schema": {
            "type": "object",
            "required": ["level"],
            "properties": {"level": {"type": "integer", "description": "Volume 0-100"}},
        },
    },
    {
        "name": "music_search_play",
        "description": "Chercher et jouer un morceau/artiste dans la bibliothèque Apple Music",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {"query": {"type": "string", "description": "Artiste, morceau ou album à chercher"}},
        },
    },
    {
        "name": "music_playlists",
        "description": "Lister les playlists Apple Music",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "music_play_playlist",
        "description": "Jouer une playlist Apple Music par son nom",
        "input_schema": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        },
    },
    {
        "name": "music_shuffle",
        "description": "Activer/désactiver le mode aléatoire",
        "input_schema": {
            "type": "object",
            "required": ["enabled"],
            "properties": {"enabled": {"type": "boolean"}},
        },
    },
    # ═══ AUTOMATISATION ═══
    {
        "name": "automation_add_job",
        "description": "Planifier une tâche récurrente (ex: 'every 5m', 'every day at 08:00', 'every lundi at 09:00')",
        "input_schema": {
            "type": "object",
            "required": ["name", "schedule", "action"],
            "properties": {
                "name": {"type": "string", "description": "Nom du job"},
                "schedule": {"type": "string", "description": "Planning: 'every 5m', 'every day at 08:00', 'every lundi at 09:00', ou cron '0 8 * * *'"},
                "action": {"type": "string", "description": "Action à effectuer"},
                "action_args": {"type": "object", "description": "Arguments de l'action"},
            },
        },
    },
    {
        "name": "automation_remove_job",
        "description": "Supprimer un job planifié",
        "input_schema": {
            "type": "object",
            "required": ["job_id"],
            "properties": {"job_id": {"type": "string"}},
        },
    },
    {
        "name": "automation_list_jobs",
        "description": "Lister tous les jobs planifiés",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "automation_add_reminder",
        "description": "Ajouter un rappel unique (ex: 'in 30m', 'in 2h', datetime ISO)",
        "input_schema": {
            "type": "object",
            "required": ["message", "remind_at"],
            "properties": {
                "message": {"type": "string", "description": "Message du rappel"},
                "remind_at": {"type": "string", "description": "'in 30m', 'in 2h', 'in 1d' ou datetime ISO"},
            },
        },
    },
    {
        "name": "automation_morning_briefing",
        "description": "Configurer le briefing matinal quotidien automatique",
        "input_schema": {
            "type": "object",
            "properties": {
                "time": {"type": "string", "description": "Heure du briefing (défaut: 08:00)"},
            },
        },
    },
]


import re

# Tool groups for smart routing — only send relevant tools per message
TOOL_GROUPS = {
    "gmail": {
        "tools": {"gmail_get_emails", "gmail_read_email", "gmail_search", "gmail_get_thread", "gmail_generate_reply", "gmail_send_email"},
        "keywords": re.compile(
            r"mail|email|e-mail|inbox|boîte|gmail|courrier|message.*(lu|reç)|répondre.*mail|brouillon|draft",
            re.IGNORECASE,
        ),
    },
    "calendar": {
        "tools": {"calendar_get_events", "calendar_create_event", "calendar_find_free_slots", "calendar_get_week_summary"},
        "keywords": re.compile(
            r"calendrier|calendar|rdv|rendez.?vous|événement|event|créneau|planning|agenda"
            r"|semaine|demain|aujourd|ce\s*soir|ce\s*matin|cet\s*après.?midi|à\s*\d{1,2}[h:]"
            r"|pour\s*\d{1,2}[h:]|\d{1,2}h\d{0,2}|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche",
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
    "docker": {
        "tools": {
            "docker_list_containers", "docker_run", "docker_start", "docker_stop",
            "docker_restart", "docker_remove", "docker_logs", "docker_stats",
            "docker_exec", "docker_list_images", "docker_pull", "docker_list_volumes",
            "docker_list_networks", "docker_compose_up", "docker_compose_down",
            "docker_compose_status", "docker_compose_logs", "docker_generate_compose",
            "docker_templates", "docker_system_info", "docker_system_prune",
        },
        "keywords": re.compile(
            r"docker|container|image.*docker|volume.*docker|compose|minecraft|serveur"
            r"|postgres.*docker|redis.*docker|nginx.*docker|portainer|kubectl",
            re.IGNORECASE,
        ),
    },
    "github": {
        "tools": {
            "github_list_repos", "github_repo_info", "github_list_issues",
            "github_create_issue", "github_view_issue", "github_close_issue",
            "github_list_prs", "github_create_pr", "github_view_pr",
            "github_merge_pr", "github_actions_runs", "github_notifications",
            "github_git_status", "github_git_diff",
        },
        "keywords": re.compile(
            r"github|repo|issue|pull.?request|merge|pr\b|commit|branch|git\b|ci.?cd|actions|workflow",
            re.IGNORECASE,
        ),
    },
    "music": {
        "tools": {
            "music_play", "music_pause", "music_next", "music_previous",
            "music_now_playing", "music_volume", "music_search_play",
            "music_playlists", "music_play_playlist", "music_shuffle",
        },
        "keywords": re.compile(
            r"musique|music|mets.*(du|de\s+la|un)|joue|playlist|morceau|chanson|song|track"
            r"|pause.*musique|volume.*musique|artiste|album|shuffle|aléatoire"
            r"|spotify|apple\s*music|écouter|lecture|play\b|next\s*track|suivant",
            re.IGNORECASE,
        ),
    },
    "automation": {
        "tools": {
            "automation_add_job", "automation_remove_job", "automation_list_jobs",
            "automation_add_reminder", "automation_morning_briefing",
        },
        "keywords": re.compile(
            r"planifi|schedule|cron|autom|récurrent|briefing|matin.*résumé|résumé.*matin"
            r"|toutes?\s*les\s*\d|chaque\s*(jour|heure|minute|semaine|lundi|mardi)"
            r"|pr[ée]viens|rappel|remind|timer|minuterie|alarm|réveill"
            r"|dans\s*\d+\s*(mn|min|m|h|sec|s|d|minute|heure|seconde|jour)"
            r"|in\s*\d+\s*(min|hour|sec|day)",
            re.IGNORECASE,
        ),
    },
}

# Lightweight fallback: most commonly used tools for ambiguous messages
# instead of sending all 35 tools
FALLBACK_TOOLS = {
    "web_search", "web_get_page",
    "file_read", "file_write",
    "task_list", "task_create",
    "memory_save_fact",
    "calendar_get_events",
    "docker_list_containers",
    "github_git_status",
    "music_now_playing",
}


class ToolRegistry:
    """Tool registry with smart routing — only sends relevant tools based on user message."""

    def __init__(self):
        self.handlers: dict[str, Callable] = {}
        self._active_groups: set[str] = set()  # groups active in recent conversation

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
        # Check casual greetings first — these always reset context
        casual = re.compile(
            r"^(salut|hello|hi|hey|bonjour|bonsoir|coucou|ça va|comment vas|merci|ok|oui|non|"
            r"d'accord|super|cool|bye|au revoir|bonne nuit|quoi de neuf|yo)\b",
            re.IGNORECASE,
        )
        if casual.match(message.strip()) and len(message.strip()) < 60:
            self._active_groups.clear()
            return []

        needed: set[str] = set()
        matched_groups: set[str] = set()
        for group_name, group in TOOL_GROUPS.items():
            if group["keywords"].search(message):
                needed |= group["tools"]
                matched_groups.add(group_name)

        if matched_groups:
            self._active_groups = matched_groups
            return [t for t in TOOL_DEFINITIONS if t["name"] in needed]

        # No keyword matched — carry over tools from recent conversation context
        if self._active_groups:
            for group_name in self._active_groups:
                needed |= TOOL_GROUPS[group_name]["tools"]
            if needed:
                return [t for t in TOOL_DEFINITIONS if t["name"] in needed]

        # Ambiguous message — send lightweight fallback set instead of all 35 tools
        return [t for t in TOOL_DEFINITIONS if t["name"] in FALLBACK_TOOLS]
