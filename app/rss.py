import logging
from datetime import datetime, timezone

from lxml import etree

from app.models import FeedResult

logger = logging.getLogger(__name__)

_CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
_ATOM_NS = "http://www.w3.org/2005/Atom"


def generate_rss(feed_result: FeedResult, feed_url: str | None = None) -> str:
    pub = feed_result.publication
    description = pub.description or f"RSS feed for {pub.title}"

    rss = etree.Element(
        "rss",
        version="2.0",
        nsmap={
            "atom": _ATOM_NS,
            "content": _CONTENT_NS,
        },
    )
    channel = etree.SubElement(rss, "channel")

    _add_text(channel, "title", pub.title)
    _add_text(channel, "link", pub.url)
    _add_text(channel, "description", description)

    if pub.language:
        _add_text(channel, "language", pub.language)

    _add_text(channel, "lastBuildDate", _rfc822(datetime.now(timezone.utc)))

    if feed_url:
        link = etree.SubElement(channel, f"{{{_ATOM_NS}}}link")
        link.set("href", feed_url)
        link.set("rel", "self")
        link.set("type", "application/rss+xml")

    articles = sorted(
        feed_result.articles,
        key=lambda a: a.published_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    for article in articles:
        item = etree.SubElement(channel, "item")
        _add_text(item, "title", article.title)
        _add_text(item, "link", article.url)

        guid = etree.SubElement(item, "guid")
        guid.set("isPermaLink", "true")
        guid.text = article.guid

        if article.published_at:
            _add_text(item, "pubDate", _rfc822(article.published_at))

        if article.description:
            _add_text(item, "description", article.description)

        if article.html_content:
            content = etree.SubElement(item, f"{{{_CONTENT_NS}}}encoded")
            content.text = etree.CDATA(article.html_content)

        if article.author:
            author = etree.SubElement(item, "author")
            author.text = article.author

    return etree.tostring(rss, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def _add_text(parent: etree.Element, tag: str, text: str):
    el = etree.SubElement(parent, tag)
    el.text = text


def _rfc822(dt: datetime) -> str:
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
