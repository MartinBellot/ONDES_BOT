import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


class WebScraper:

    def get_page_content(self, url: str) -> str:
        self._validate_url(url)

        response = httpx.get(
            url,
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
        )

        soup = BeautifulSoup(response.text, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "aside", "noscript", "iframe"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # Aggressive cleaning: remove short lines (nav, breadcrumbs, etc.)
        lines = [line.strip() for line in text.splitlines()]
        cleaned = []
        for line in lines:
            if not line:
                continue
            # Skip very short lines likely to be UI noise
            if len(line) < 15 and not any(c in line for c in '.!?:'):
                continue
            cleaned.append(line)
        text = "\n".join(cleaned)

        # Limit size for Claude context — 5000 chars ≈ 1250 tokens
        return text[:5000]

    def _validate_url(self, url: str):
        """Prevent SSRF — reject internal/localhost URLs."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Seuls les URLs http/https sont autorisés")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("URL invalide: pas de hostname")

        # Block known private hostnames
        blocked = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}
        if hostname.lower() in blocked:
            raise ValueError(f"Accès refusé: {hostname}")

        # Resolve and check for private IPs
        try:
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                raise ValueError(f"Accès refusé à l'IP privée: {ip_str}")
        except socket.gaierror:
            raise ValueError(f"Hostname non résolu: {hostname}")
