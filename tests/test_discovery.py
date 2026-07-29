import pytest

from app.discovery import discover_articles
from app.errors import NoArticlesFoundError

FIXTURES_DIR = "tests/fixtures"


def _load(name: str) -> str:
    path = f"{FIXTURES_DIR}/{name}"
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestDiscoverArticles:
    def test_homepage_discovers_articles(self):
        html = _load("homepage.html")
        urls = discover_articles(html, "https://tech-weekly.beehiiv.com")
        assert len(urls) == 3
        for url in urls:
            assert "/p/" in url

    def test_homepage_removes_duplicates(self):
        html = _load("homepage_duplicates.html")
        urls = discover_articles(html, "https://tech-weekly.beehiiv.com")
        assert len(urls) == 2

    def test_no_articles_raises_error(self):
        html = _load("homepage_no_articles.html")
        with pytest.raises(NoArticlesFoundError):
            discover_articles(html, "https://empty.beehiiv.com")

    def test_excludes_subscribe_links(self):
        html = _load("homepage.html")
        urls = discover_articles(html, "https://tech-weekly.beehiiv.com")
        assert not any("subscribe" in url for url in urls)

    def test_excludes_login_links(self):
        html = _load("homepage.html")
        urls = discover_articles(html, "https://tech-weekly.beehiiv.com")
        assert not any("login" in url for url in urls)

    def test_excludes_social_links(self):
        html = _load("homepage.html")
        urls = discover_articles(html, "https://tech-weekly.beehiiv.com")
        assert not any("twitter.com" in url for url in urls)

    def test_canonical_urls_dedup(self):
        html = _load("homepage_duplicates.html")
        urls = discover_articles(html, "https://tech-weekly.beehiiv.com")
        for url in urls:
            assert not url.endswith("/")
            assert url == url.rstrip("/")

    def test_article_urls_have_correct_base(self):
        html = _load("homepage.html")
        urls = discover_articles(html, "https://tech-weekly.beehiiv.com")
        for url in urls:
            assert url.startswith("https://tech-weekly.beehiiv.com/p/")
