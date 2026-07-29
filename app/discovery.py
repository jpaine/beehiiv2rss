import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.errors import NoArticlesFoundError

logger = logging.getLogger(__name__)

ARTICLE_LINK_RE = re.compile(
    r"/(?:p(?:ost)?|articles?|news(?:letter)?|edition|issue)/",
    re.IGNORECASE,
)

EXCLUDE_KEYWORDS = re.compile(
    r"(login|signup|subscribe|privacy|terms|about|contact|tag/|author/|category/|"
    r"facebook\.com|twitter\.com|x\.com|linkedin\.com|instagram\.com)",
    re.IGNORECASE,
)


def discover_articles(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    urls: list[str] = []

    candidates = _collect_links(soup, base_url)

    for url in candidates:
        normalized = _normalise_url(url, base_url)
        if not normalized:
            continue
        if _is_article_link(normalized) and not _is_excluded(normalized):
            canonical = _canonicalise(normalized)
            if canonical and canonical not in seen:
                seen.add(canonical)
                urls.append(canonical)

    if not urls:
        raise NoArticlesFoundError()

    return urls


def _collect_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        links.append(href)

    return links


def _normalise_url(href: str, base_url: str) -> str | None:
    full = urljoin(base_url, href)
    parsed = urlparse(full)
    if parsed.scheme not in ("http", "https"):
        return None
    return full


def _is_article_link(url: str) -> bool:
    path = urlparse(url).path
    return bool(ARTICLE_LINK_RE.search(path))


def _is_excluded(url: str) -> bool:
    return bool(EXCLUDE_KEYWORDS.search(url))


def _canonicalise(url: str) -> str:
    parsed = urlparse(url)
    cleaned = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    return cleaned
