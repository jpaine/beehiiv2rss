import json
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.models import Article, Publication

logger = logging.getLogger(__name__)


def parse_publication(html: str, url: str) -> Publication:
    soup = BeautifulSoup(html, "lxml")
    title = _extract_publication_title(soup, url)
    description = _extract_publication_description(soup)
    language = _extract_language(soup)
    return Publication(title=title, url=url, description=description, language=language)


def parse_article(html: str, url: str) -> Article | None:
    soup = BeautifulSoup(html, "lxml")
    title = _extract_title(soup)
    if not title:
        return None

    canonical_url = _extract_canonical_url(soup) or url
    guid = canonical_url
    published_at = _extract_published_at(soup) or _extract_published_at_json_ld(soup)
    author = _extract_author(soup)
    hero_image = _extract_hero_image(soup, url)
    html_content = _extract_content(soup, url)
    description = _extract_description(soup)

    return Article(
        title=title,
        url=canonical_url,
        guid=guid,
        published_at=published_at,
        author=author,
        hero_image_url=hero_image,
        html_content=html_content,
        description=description,
    )


def _extract_publication_title(soup: BeautifulSoup, fallback_url: str) -> str:
    og = soup.find("meta", property="og:site_name")
    if og and og.get("content"):
        return og["content"].strip()
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        return title_tag.string.strip()
    parsed = urlparse(fallback_url)
    return parsed.netloc


def _extract_publication_description(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        return og["content"].strip()
    return ""


def _extract_language(soup: BeautifulSoup) -> str | None:
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        return html_tag["lang"].strip()
    meta = soup.find("meta", attrs={"http-equiv": "content-language"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    return None


def _extract_title(soup: BeautifulSoup) -> str | None:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        return title_tag.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return None


def _extract_canonical_url(soup: BeautifulSoup) -> str | None:
    link = soup.find("link", rel="canonical")
    if link and link.get("href"):
        return link["href"].strip()
    og = soup.find("meta", property="og:url")
    if og and og.get("content"):
        return og["content"].strip()
    return None


def _extract_published_at(soup: BeautifulSoup) -> datetime | None:
    for attr in ("datePublished", "date", "pubdate"):
        meta = soup.find("meta", attrs={"name": attr})
        if meta and meta.get("content"):
            result = _parse_date(meta["content"].strip())
            if result:
                return result

    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        result = _parse_date(time_tag["datetime"].strip())
        if result:
            return result
    return None


def _parse_date(value: str) -> datetime | None:
    try:
        return parsedate_to_datetime(value)
    except (ValueError, TypeError):
        pass
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass
    return None


def _extract_published_at_json_ld(soup: BeautifulSoup) -> datetime | None:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            date_str = _json_ld_date(data)
            if date_str:
                return _parse_date(date_str)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return None


def _json_ld_date(data: dict) -> str | None:
    if isinstance(data, list):
        for item in data:
            result = _json_ld_date(item)
            if result:
                return result
        return None
    for key in ("datePublished", "dateCreated"):
        if data.get(key):
            return data[key]
    if data.get("@graph"):
        for item in data["@graph"]:
            result = _json_ld_date(item)
            if result:
                return result
    return None


def _extract_author(soup: BeautifulSoup) -> str | None:
    for attr in ("author", "article:author"):
        meta = soup.find("meta", attrs={"name": attr})
        if meta and meta.get("content") and attr == "author":
            return meta["content"].strip()

    og = soup.find("meta", property="article:author")
    if og and og.get("content"):
        return og["content"].strip()

    author_link = soup.find("a", href=re.compile(r"/authors?/", re.IGNORECASE))
    if author_link:
        text = author_link.get_text(strip=True)
        if text:
            return text

    author_span = soup.find(["span", "div"], class_=re.compile(r"author", re.IGNORECASE))
    if author_span:
        text = author_span.get_text(strip=True)
        if text:
            return text

    return None


def _extract_hero_image(soup: BeautifulSoup, base_url: str) -> str | None:
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return urljoin(base_url, og["content"].strip())
    meta = soup.find("meta", attrs={"name": "twitter:image"})
    if meta and meta.get("content"):
        return urljoin(base_url, meta["content"].strip())
    img = soup.find("img", class_=re.compile(r"hero|featured|cover", re.IGNORECASE))
    if img and img.get("src"):
        return urljoin(base_url, img["src"].strip())
    return None


def _extract_content(soup: BeautifulSoup, base_url: str) -> str:
    article = (
        soup.find("article")
        or soup.find("main")
        or soup.find("div", class_=re.compile(r"content|post|article", re.IGNORECASE))
    )
    if not article:
        body = soup.find("body")
        if not body:
            return ""
        article = body

    remove_tags = ["script", "style", "nav", "header", "footer", "aside", "form", "iframe"]
    for tag in article.find_all(remove_tags):
        tag.decompose()

    for tag in article.find_all(
        class_=re.compile(
            r"(subscribe|signup|newsletter|social-?share|recommended|related|sidebar|popup|modal|overlay|menu|cta|ad-?)",
            re.IGNORECASE,
        )
    ):
        tag.decompose()

    _make_absolute(article, base_url, "a", "href")
    _make_absolute(article, base_url, "img", "src")

    inner = article.encode_contents().decode("utf-8")
    return inner.strip()


def _make_absolute(soup: BeautifulSoup, base_url: str, tag_name: str, attr: str):
    for tag in soup.find_all(tag_name, **{attr: True}):
        value = tag[attr]
        if value.startswith(("http://", "https://", "//")):
            continue
        tag[attr] = urljoin(base_url, value)


def _extract_description(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        return og["content"].strip()
    return ""
