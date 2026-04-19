"""Web crawler service for competitor analysis."""

import ipaddress
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx


# Private/reserved IP ranges blocked to prevent SSRF
_PRIVATE_IP_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("224.0.0.0/4"),
]


def _is_private_host(hostname: str) -> bool:
    """Check whether a hostname resolves to a private/reserved IP or is localhost-like."""
    if not hostname:
        return True
    lower = hostname.lower()
    if lower in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
        return True
    # Block internal/local-like hostnames without DNS lookup
    if lower.endswith((".local", ".internal", ".localhost")):
        return True
    # Try to interpret as an IP address directly
    try:
        addr = ipaddress.ip_address(hostname)
        for net in _PRIVATE_IP_NETWORKS:
            if addr in net:
                return True
    except ValueError:
        pass
    return False


def _is_safe_url(url: str) -> bool:
    """Validate URL scheme and host to prevent SSRF."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if _is_private_host(parsed.hostname or ""):
        return False
    return True


class _TextExtractor(HTMLParser):
    """Extract visible text from HTML, ignoring script/style tags."""

    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []
        self._skip_depth = 0
        self._skip_tags = {"script", "style", "noscript", "iframe", "canvas", "svg"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._pieces.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._pieces)


def _build_url(competitor_name: str) -> str:
    """Construct a likely URL from the competitor name."""
    name = competitor_name.strip()
    if not name:
        return ""
    if name.startswith(("http://", "https://")):
        return name
    return f"https://{name}.com"


def _extract_meta_description(html: str) -> str:
    """Extract meta description from HTML."""
    match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    match = re.search(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
        html,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return ""


def _extract_title(html: str) -> str:
    """Extract title from HTML."""
    match = re.search(r"<title>([^<]*)</title>", html, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _strip_tags(html: str) -> str:
    """Strip HTML tags and return visible text."""
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        # Fallback to regex if parser fails
        return re.sub(r"<[^>]+>", "", html)
    return extractor.get_text()


async def fetch_competitor_info(competitor_name: str) -> dict:
    """Fetch public page info for a competitor.

    Returns a dict with name, url, title, description, content, success, and error.
    """
    url = _build_url(competitor_name)
    if not url:
        return {
            "name": competitor_name,
            "url": "",
            "title": "",
            "description": "",
            "content": "",
            "success": False,
            "error": "Invalid competitor name",
        }

    if not _is_safe_url(url):
        return {
            "name": competitor_name,
            "url": url,
            "title": "",
            "description": "",
            "content": "",
            "success": False,
            "error": "URL not allowed (SSRF protection)",
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            html = response.text
    except Exception as exc:
        return {
            "name": competitor_name,
            "url": url,
            "title": "",
            "description": "",
            "content": "",
            "success": False,
            "error": str(exc),
        }

    title = _extract_title(html)
    description = _extract_meta_description(html)
    visible_text = _strip_tags(html)
    content = visible_text[:1000]

    return {
        "name": competitor_name,
        "url": url,
        "title": title,
        "description": description,
        "content": content,
        "success": True,
        "error": "",
    }


class WebCrawlerService:
    """Service for crawling competitor websites."""

    async def search_competitor_info(self, competitors: list[str]) -> dict:
        """Fetch info for multiple competitors and aggregate results."""
        results: list[dict] = []
        for name in competitors:
            result = await fetch_competitor_info(name)
            results.append(result)
        return {"results": results}


web_crawler_service = WebCrawlerService()
