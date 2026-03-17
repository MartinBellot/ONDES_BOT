"""Docker integration — full container, image, volume, network & compose management."""

import json
import subprocess
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Container:
    id: str
    name: str
    image: str
    status: str
    ports: str
    created: str


@dataclass
class DockerImage:
    id: str
    repository: str
    tag: str
    size: str
    created: str


def _run(args: list[str], timeout: int = 30, input_data: str | None = None) -> tuple[str, str, int]:
    """Run a docker CLI command safely and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_data,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout dépassé", 1
    except FileNotFoundError:
        return "", "Docker n'est pas installé ou pas dans le PATH", 127


class DockerClient:
    """Full Docker management: containers, images, volumes, networks, compose."""

    def __init__(self):
        self._docker = shutil.which("docker")
        self._compose = shutil.which("docker-compose") or self._docker  # docker compose v2

    def is_available(self) -> bool:
        """Check if Docker is installed and the daemon is running."""
        if not self._docker:
            return False
        stdout, _, rc = _run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=5)
        return rc == 0

    # ═══════════════════════════ CONTAINERS ═══════════════════════════

    def list_containers(self, all: bool = True) -> str:
        """List containers with status, ports, image info."""
        cmd = ["docker", "ps", "--format", "{{json .}}"]
        if all:
            cmd.append("-a")
        stdout, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"
        if not stdout:
            return "Aucun container trouvé."

        lines = []
        for line in stdout.strip().split("\n"):
            try:
                c = json.loads(line)
                status = c.get("Status", "")
                state_emoji = "🟢" if "Up" in status else "🔴"
                ports = c.get("Ports", "—")
                lines.append(
                    f"{state_emoji} **{c.get('Names', '?')}**\n"
                    f"   Image: {c.get('Image', '?')} | Status: {status}\n"
                    f"   Ports: {ports} | ID: {c.get('ID', '?')[:12]}"
                )
            except json.JSONDecodeError:
                continue

        return "\n\n".join(lines) if lines else "Aucun container trouvé."

    def start_container(self, name_or_id: str) -> str:
        _, stderr, rc = _run(["docker", "start", name_or_id])
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"✅ Container **{name_or_id}** démarré."

    def stop_container(self, name_or_id: str) -> str:
        _, stderr, rc = _run(["docker", "stop", name_or_id], timeout=30)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"🛑 Container **{name_or_id}** arrêté."

    def restart_container(self, name_or_id: str) -> str:
        _, stderr, rc = _run(["docker", "restart", name_or_id], timeout=30)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"🔄 Container **{name_or_id}** redémarré."

    def remove_container(self, name_or_id: str, force: bool = False) -> str:
        cmd = ["docker", "rm", name_or_id]
        if force:
            cmd.append("-f")
        _, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"🗑️ Container **{name_or_id}** supprimé."

    def container_logs(self, name_or_id: str, tail: int = 50) -> str:
        stdout, stderr, rc = _run(
            ["docker", "logs", "--tail", str(tail), name_or_id],
            timeout=10,
        )
        if rc != 0:
            return f"Erreur: {stderr}"
        return stdout[:3000] if stdout else "(logs vides)"

    def container_stats(self, name_or_id: str | None = None) -> str:
        """Get resource usage stats (CPU, RAM, network)."""
        cmd = ["docker", "stats", "--no-stream", "--format",
               "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.PIDs}}"]
        if name_or_id:
            cmd.append(name_or_id)
        stdout, stderr, rc = _run(cmd, timeout=10)
        if rc != 0:
            return f"Erreur: {stderr}"
        return stdout if stdout else "Aucune stats disponible."

    def run_container(
        self,
        image: str,
        name: str | None = None,
        ports: dict[str, str] | None = None,
        volumes: dict[str, str] | None = None,
        env: dict[str, str] | None = None,
        detach: bool = True,
        restart_policy: str = "unless-stopped",
        extra_args: str = "",
    ) -> str:
        """Run a new container with full configuration."""
        cmd = ["docker", "run"]

        if detach:
            cmd.append("-d")

        if name:
            cmd.extend(["--name", name])

        if restart_policy:
            cmd.extend(["--restart", restart_policy])

        if ports:
            for host_port, container_port in ports.items():
                cmd.extend(["-p", f"{host_port}:{container_port}"])

        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(["-v", f"{host_path}:{container_path}"])

        if env:
            for key, value in env.items():
                cmd.extend(["-e", f"{key}={value}"])

        if extra_args:
            cmd.extend(extra_args.split())

        cmd.append(image)

        stdout, stderr, rc = _run(cmd, timeout=120)
        if rc != 0:
            return f"Erreur: {stderr}"

        container_id = stdout[:12]
        result = f"✅ Container créé: **{name or container_id}**\n   Image: {image}"
        if ports:
            port_str = ", ".join(f"{h}→{c}" for h, c in ports.items())
            result += f"\n   Ports: {port_str}"
        return result

    def exec_in_container(self, name_or_id: str, command: str) -> str:
        """Execute a command inside a running container."""
        cmd = ["docker", "exec", name_or_id] + command.split()
        stdout, stderr, rc = _run(cmd, timeout=30)
        if rc != 0:
            return f"Erreur: {stderr}"
        return stdout[:3000] if stdout else "(pas de sortie)"

    # ═══════════════════════════ IMAGES ═══════════════════════════

    def list_images(self) -> str:
        stdout, stderr, rc = _run(
            ["docker", "images", "--format", "{{json .}}"]
        )
        if rc != 0:
            return f"Erreur: {stderr}"
        if not stdout:
            return "Aucune image trouvée."

        lines = []
        for line in stdout.strip().split("\n"):
            try:
                img = json.loads(line)
                lines.append(
                    f"📦 **{img.get('Repository', '?')}:{img.get('Tag', '?')}**\n"
                    f"   Taille: {img.get('Size', '?')} | ID: {img.get('ID', '?')[:12]} | Créé: {img.get('CreatedSince', '?')}"
                )
            except json.JSONDecodeError:
                continue

        return "\n\n".join(lines) if lines else "Aucune image trouvée."

    def pull_image(self, image: str) -> str:
        stdout, stderr, rc = _run(["docker", "pull", image], timeout=300)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"✅ Image **{image}** téléchargée.\n{stdout[-200:]}"

    def remove_image(self, image: str, force: bool = False) -> str:
        cmd = ["docker", "rmi", image]
        if force:
            cmd.append("-f")
        _, stderr, rc = _run(cmd)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"🗑️ Image **{image}** supprimée."

    # ═══════════════════════════ VOLUMES ═══════════════════════════

    def list_volumes(self) -> str:
        stdout, stderr, rc = _run(
            ["docker", "volume", "ls", "--format", "{{json .}}"]
        )
        if rc != 0:
            return f"Erreur: {stderr}"
        if not stdout:
            return "Aucun volume trouvé."

        lines = []
        for line in stdout.strip().split("\n"):
            try:
                vol = json.loads(line)
                lines.append(f"💾 **{vol.get('Name', '?')}** — Driver: {vol.get('Driver', '?')}")
            except json.JSONDecodeError:
                continue

        return "\n\n".join(lines) if lines else "Aucun volume trouvé."

    def create_volume(self, name: str) -> str:
        _, stderr, rc = _run(["docker", "volume", "create", name])
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"✅ Volume **{name}** créé."

    def remove_volume(self, name: str) -> str:
        _, stderr, rc = _run(["docker", "volume", "rm", name])
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"🗑️ Volume **{name}** supprimé."

    # ═══════════════════════════ NETWORKS ═══════════════════════════

    def list_networks(self) -> str:
        stdout, stderr, rc = _run(
            ["docker", "network", "ls", "--format", "{{json .}}"]
        )
        if rc != 0:
            return f"Erreur: {stderr}"
        if not stdout:
            return "Aucun réseau trouvé."

        lines = []
        for line in stdout.strip().split("\n"):
            try:
                net = json.loads(line)
                lines.append(
                    f"🌐 **{net.get('Name', '?')}** — Driver: {net.get('Driver', '?')} | Scope: {net.get('Scope', '?')}"
                )
            except json.JSONDecodeError:
                continue

        return "\n\n".join(lines) if lines else "Aucun réseau trouvé."

    # ═══════════════════════════ DOCKER COMPOSE ═══════════════════════════

    def compose_up(self, compose_file: str, project_name: str | None = None, detach: bool = True) -> str:
        """Start a docker-compose stack."""
        cmd = ["docker", "compose", "-f", compose_file]
        if project_name:
            cmd.extend(["-p", project_name])
        cmd.append("up")
        if detach:
            cmd.append("-d")

        stdout, stderr, rc = _run(cmd, timeout=300)
        if rc != 0:
            return f"Erreur compose up: {stderr}"
        return f"✅ Stack Compose démarrée.\n{stdout[-500:]}"

    def compose_down(self, compose_file: str, project_name: str | None = None, remove_volumes: bool = False) -> str:
        """Stop and remove a compose stack."""
        cmd = ["docker", "compose", "-f", compose_file]
        if project_name:
            cmd.extend(["-p", project_name])
        cmd.append("down")
        if remove_volumes:
            cmd.append("-v")

        stdout, stderr, rc = _run(cmd, timeout=60)
        if rc != 0:
            return f"Erreur compose down: {stderr}"
        return f"🛑 Stack Compose arrêtée.\n{stdout[-300:]}"

    def compose_status(self, compose_file: str, project_name: str | None = None) -> str:
        """Get status of a compose stack."""
        cmd = ["docker", "compose", "-f", compose_file]
        if project_name:
            cmd.extend(["-p", project_name])
        cmd.extend(["ps", "--format", "table {{.Name}}\t{{.Status}}\t{{.Ports}}"])

        stdout, stderr, rc = _run(cmd, timeout=10)
        if rc != 0:
            return f"Erreur: {stderr}"
        return stdout if stdout else "Aucun service trouvé."

    def compose_logs(self, compose_file: str, service: str | None = None, tail: int = 50) -> str:
        """Get logs from a compose stack."""
        cmd = ["docker", "compose", "-f", compose_file, "logs", "--tail", str(tail)]
        if service:
            cmd.append(service)

        stdout, stderr, rc = _run(cmd, timeout=10)
        if rc != 0:
            return f"Erreur: {stderr}"
        return stdout[:3000] if stdout else "(logs vides)"

    # ═══════════════════════════ TEMPLATES ═══════════════════════════

    def generate_compose_file(self, template: str, output_dir: str, **kwargs) -> str:
        """Generate a docker-compose.yml from a known template (e.g., minecraft)."""
        templates = self._get_templates()
        if template not in templates:
            available = ", ".join(templates.keys())
            return f"Template inconnu: '{template}'. Disponibles: {available}"

        compose_content = templates[template](kwargs)
        output_path = Path(output_dir).expanduser().resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        compose_file = output_path / "docker-compose.yml"
        compose_file.write_text(compose_content)

        return f"✅ Fichier Compose généré: {compose_file}\n\nContenu:\n```yaml\n{compose_content}\n```"

    def _get_templates(self) -> dict:
        return {
            "minecraft": self._template_minecraft,
            "minecraft-bedrock": self._template_minecraft_bedrock,
            "postgres": self._template_postgres,
            "redis": self._template_redis,
            "nginx": self._template_nginx,
            "mongodb": self._template_mongodb,
            "mysql": self._template_mysql,
            "portainer": self._template_portainer,
        }

    @staticmethod
    def _template_minecraft(opts: dict) -> str:
        server_name = opts.get("server_name", "minecraft-server")
        memory = opts.get("memory", "4G")
        port = opts.get("port", "25565")
        version = opts.get("version", "LATEST")
        gamemode = opts.get("gamemode", "survival")
        difficulty = opts.get("difficulty", "normal")
        max_players = opts.get("max_players", "20")
        motd = opts.get("motd", "Un serveur Minecraft géré par ONDES Bot!")
        server_type = opts.get("server_type", "VANILLA").upper()
        mods = opts.get("mods", "")
        modpack = opts.get("modpack", "")

        env_lines = [
            f'      EULA: "TRUE"',
            f'      VERSION: "{version}"',
            f'      MEMORY: "{memory}"',
            f'      TYPE: "{server_type}"',
            f'      GAMEMODE: "{gamemode}"',
            f'      DIFFICULTY: "{difficulty}"',
            f'      MAX_PLAYERS: "{max_players}"',
            f'      MOTD: "{motd}"',
            f'      ENABLE_RCON: "true"',
            f'      RCON_PASSWORD: "ondes_rcon"',
            f'      RCON_PORT: "25575"',
        ]

        # Modded server support
        if server_type in ("FORGE", "NEOFORGE", "FABRIC", "QUILT"):
            if mods:
                # Comma-separated list of CurseForge/Modrinth URLs or slugs
                env_lines.append(f'      MODRINTH_PROJECTS: "{mods}"')
                env_lines.append(f'      MODRINTH_DOWNLOAD_DEPENDENCIES: "required"')
            if modpack:
                env_lines.append(f'      CF_PAGE_URL: "{modpack}"')
            # More RAM for modded
            if opts.get("memory") is None:
                env_lines = [l for l in env_lines if 'MEMORY:' not in l]
                env_lines.insert(3, f'      MEMORY: "6G"')

        env_block = "\n".join(env_lines)

        return f"""version: "3.8"

services:
  minecraft:
    image: itzg/minecraft-server
    container_name: {server_name}
    ports:
      - "{port}:25565"
    environment:
{env_block}
    volumes:
      - minecraft_data:/data
    restart: unless-stopped
    stdin_open: true
    tty: true

volumes:
  minecraft_data:
    driver: local
"""

    @staticmethod
    def _template_minecraft_bedrock(opts: dict) -> str:
        server_name = opts.get("server_name", "minecraft-bedrock")
        port = opts.get("port", "19132")
        gamemode = opts.get("gamemode", "survival")
        difficulty = opts.get("difficulty", "normal")
        max_players = opts.get("max_players", "10")

        return f"""version: "3.8"

services:
  bedrock:
    image: itzg/minecraft-bedrock-server
    container_name: {server_name}
    ports:
      - "{port}:19132/udp"
    environment:
      EULA: "TRUE"
      GAMEMODE: "{gamemode}"
      DIFFICULTY: "{difficulty}"
      MAX_PLAYERS: "{max_players}"
      SERVER_NAME: "{server_name}"
    volumes:
      - bedrock_data:/data
    restart: unless-stopped

volumes:
  bedrock_data:
    driver: local
"""

    @staticmethod
    def _template_postgres(opts: dict) -> str:
        password = opts.get("password", "postgres")
        port = opts.get("port", "5432")
        db_name = opts.get("db_name", "mydb")
        return f"""version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    ports:
      - "{port}:5432"
    environment:
      POSTGRES_PASSWORD: "{password}"
      POSTGRES_DB: "{db_name}"
    volumes:
      - pg_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  pg_data:
    driver: local
"""

    @staticmethod
    def _template_redis(opts: dict) -> str:
        port = opts.get("port", "6379")
        return f"""version: "3.8"

services:
  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "{port}:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

volumes:
  redis_data:
    driver: local
"""

    @staticmethod
    def _template_nginx(opts: dict) -> str:
        port = opts.get("port", "8080")
        return f"""version: "3.8"

services:
  nginx:
    image: nginx:alpine
    container_name: nginx
    ports:
      - "{port}:80"
    volumes:
      - ./html:/usr/share/nginx/html:ro
    restart: unless-stopped
"""

    @staticmethod
    def _template_mongodb(opts: dict) -> str:
        port = opts.get("port", "27017")
        password = opts.get("password", "mongo")
        return f"""version: "3.8"

services:
  mongodb:
    image: mongo:7
    container_name: mongodb
    ports:
      - "{port}:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: "{password}"
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

volumes:
  mongo_data:
    driver: local
"""

    @staticmethod
    def _template_mysql(opts: dict) -> str:
        password = opts.get("password", "mysql")
        port = opts.get("port", "3306")
        db_name = opts.get("db_name", "mydb")
        return f"""version: "3.8"

services:
  mysql:
    image: mysql:8
    container_name: mysql
    ports:
      - "{port}:3306"
    environment:
      MYSQL_ROOT_PASSWORD: "{password}"
      MYSQL_DATABASE: "{db_name}"
    volumes:
      - mysql_data:/var/lib/mysql
    restart: unless-stopped

volumes:
  mysql_data:
    driver: local
"""

    @staticmethod
    def _template_portainer(opts: dict) -> str:
        port = opts.get("port", "9443")
        return f"""version: "3.8"

services:
  portainer:
    image: portainer/portainer-ce:latest
    container_name: portainer
    ports:
      - "8000:8000"
      - "{port}:9443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    restart: unless-stopped

volumes:
  portainer_data:
    driver: local
"""

    def get_available_templates(self) -> str:
        """List all available docker-compose templates."""
        templates = {
            "minecraft": "Serveur Minecraft Java — vanilla ou moddé (Forge/Fabric/NeoForge/Quilt). Utilise server_type et mods pour les mods.",
            "minecraft-bedrock": "Serveur Minecraft Bedrock Edition",
            "postgres": "PostgreSQL 16",
            "redis": "Redis 7 avec persistance",
            "nginx": "Nginx (serveur web)",
            "mongodb": "MongoDB 7",
            "mysql": "MySQL 8",
            "portainer": "Portainer CE (UI Docker)",
        }
        lines = ["**Templates Docker Compose disponibles:**\n"]
        for name, desc in templates.items():
            lines.append(f"  • **{name}** — {desc}")
        return "\n".join(lines)

    # ═══════════════════════════ SYSTEM ═══════════════════════════

    def system_info(self) -> str:
        """Get Docker system information."""
        stdout, stderr, rc = _run(
            ["docker", "system", "df", "--format", "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}"],
            timeout=10,
        )
        if rc != 0:
            return f"Erreur: {stderr}"

        version_out, _, _ = _run(
            ["docker", "version", "--format", "Client: {{.Client.Version}}, Server: {{.Server.Version}}"],
            timeout=5,
        )
        return f"**Docker Version:** {version_out}\n\n**Utilisation disque:**\n{stdout}"

    def system_prune(self, all: bool = False) -> str:
        """Clean up unused Docker resources."""
        cmd = ["docker", "system", "prune", "-f"]
        if all:
            cmd.append("-a")
        stdout, stderr, rc = _run(cmd, timeout=60)
        if rc != 0:
            return f"Erreur: {stderr}"
        return f"🧹 Nettoyage Docker effectué.\n{stdout[-300:]}"
