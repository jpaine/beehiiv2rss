from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    title: str
    url: str
    guid: str
    published_at: datetime | None = None
    author: str | None = None
    hero_image_url: str | None = None
    html_content: str = ""
    description: str = ""


@dataclass
class Publication:
    title: str
    url: str
    description: str = ""
    language: str | None = None


@dataclass
class FeedResult:
    publication: Publication
    articles: list[Article] = field(default_factory=list)
